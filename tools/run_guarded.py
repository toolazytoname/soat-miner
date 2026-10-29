"""Bounded single-GPU experiments. Never starts automatically or changes clocks.

Run from a logged-in elevated Windows task. Uses the existing driver for telemetry
and power limits. Only the exact child process it creates may be stopped.
"""
import argparse
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time
from datetime import datetime, timezone
from gpu_telemetry import Gpu


def write_json(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def thermal_reason(d):
    for field, limit in [('Temperature', 80), ('Hotspot', 100), ('MemoryJunction', 96)]:
        value=d.get(field)
        if not isinstance(value,(int,float)) or not math.isfinite(value):
            return f'invalid_temperature_{field}'
        if value >= limit:
            return f'thermal_{field}_{value}'
    return None


def stop_owned(process):
    if process.poll() is not None:
        return 'already-exited'
    try:
        process.send_signal(signal.CTRL_BREAK_EVENT)
        process.wait(timeout=10)
        return 'console-break'
    except (OSError, subprocess.TimeoutExpired):
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=15)
        return 'terminated-owned-child'


def process_names():
    """Toolhelp exposes image basenames even when protected DWM paths are hidden."""
    from ctypes import wintypes as w
    class Entry(ctypes.Structure):
        _fields_=[('size',w.DWORD),('usage',w.DWORD),('pid',w.DWORD),
                  ('heap',ctypes.c_size_t),('module',w.DWORD),('threads',w.DWORD),
                  ('parent',w.DWORD),('priority',w.LONG),('flags',w.DWORD),
                  ('name',w.WCHAR*260)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes=[w.DWORD,w.DWORD]
    kernel.CreateToolhelp32Snapshot.restype=w.HANDLE
    kernel.Process32FirstW.argtypes=[w.HANDLE,ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes=[w.HANDLE,ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes=[w.HANDLE]
    handle=kernel.CreateToolhelp32Snapshot(2,0)
    if handle==ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    names={}
    try:
        entry=Entry();entry.size=ctypes.sizeof(Entry)
        ok=kernel.Process32FirstW(handle,ctypes.byref(entry))
        while ok:
            names[int(entry.pid)]=entry.name.lower()
            ok=kernel.Process32NextW(handle,ctypes.byref(entry))
    finally:
        kernel.CloseHandle(handle)
    return names


def gpu_processes():
    result = subprocess.run(['C:/Windows/System32/nvidia-smi.exe',
                             '--query-compute-apps=pid,process_name', '--format=csv,noheader'],
                            capture_output=True, text=True, timeout=8,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError('Cannot inspect other GPU processes')
    processes = {}
    for line in result.stdout.splitlines():
        fields = line.split(',', 1)
        if len(fields) == 2 and fields[0].strip().isdigit():
            processes[int(fields[0].strip())] = Path(fields[1].strip()).name.lower()
    if any(name.startswith('[') for name in processes.values()):
        names = process_names()
        processes = {pid: names.get(pid, name) if name.startswith('[') else name
                     for pid, name in processes.items()}
    return processes


DESKTOP_PROCESSES = {'dwm.exe', 'explorer.exe', 'shellhost.exe', 'msedge.exe',
                     'msedgewebview2.exe', 'chrome.exe', 'chatgpt.exe', 'orca.exe',
                     'applicationframehost.exe', 'textinputhost.exe', 'tabtip.exe',
                     'logonui.exe', 'armourycrate.exe', 'gameviewer.exe',
                     'phoneexperiencehost.exe', 'realtekaudiocontrol.exe',
                     'crossdeviceresume.exe', 'systemsettings.exe',
                     'startmenuexperiencehost.exe', 'searchhost.exe',
                     'shellexperiencehost.exe'}



def gpu_busy_before_start(g, *, utilization_limit=15, memory_limit=2500):
    """Keep original busy limits, except a verified low-clock/low-power desktop state.

    Callers must still reject non-desktop GPU clients independently.
    """
    def valid(value):
        return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value) and value>=0
    utilization=g.get("Utilization");memory=g.get("MemoryMiB")
    if not valid(utilization) or utilization>100 or not valid(memory):return True
    if memory>memory_limit:return True
    if utilization<=utilization_limit:return False
    power=g.get("Power");core=g.get("CoreClockMHz");memory_clock=g.get("MemoryClockMHz")
    idle_desktop=(all(valid(v) for v in (power,core,memory_clock)) and power<=30 and core<=405 and memory_clock<=810)
    return not idle_desktop

class MiningLease:
    """Coordinate with the existing KRig controller using its named mutex."""
    def __enter__(self):
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
        self.kernel.CreateMutexW.restype = ctypes.c_void_p
        self.kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        self.kernel.WaitForSingleObject.restype = ctypes.c_uint
        self.kernel.ReleaseMutex.argtypes = [ctypes.c_void_p]
        self.kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        self.handle = self.kernel.CreateMutexW(None, False, 'Global\\LazyPC-PearlMining')
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        result = self.kernel.WaitForSingleObject(self.handle, 0)
        if result not in (0, 0x80):
            self.kernel.CloseHandle(self.handle)
            raise RuntimeError('Another mining or GPU experiment session owns the GPU')
        return self
    def __exit__(self, *_exc):
        self.kernel.ReleaseMutex(self.handle)
        self.kernel.CloseHandle(self.handle)



def manual_cancel_token():
    path=Path('D:/Apps/KRig/Runtime/cancel.request')
    try:
        stat=path.stat();return (stat.st_mtime_ns,stat.st_size)
    except FileNotFoundError:return None

def wait_for_idle_gpu(gpu, out, initial_cancel):
    """Wait at most 30 seconds before any child or power change."""
    deadline = time.monotonic() + 30
    while True:
        if (out / 'stop.request').exists() or manual_cancel_token() != initial_cancel:
            raise RuntimeError('Manual stop requested during startup; no process or power change made')
        before = gpu.read()
        unsafe = thermal_reason(before)
        if unsafe:
            raise RuntimeError('Unsafe GPU temperature: ' + unsafe + '; no process started')
        power_limit = before.get('PowerLimit')
        if (isinstance(power_limit, bool) or not isinstance(power_limit, (int, float))
                or not math.isfinite(power_limit) or power_limit <= 0):
            raise RuntimeError('Invalid original GPU power limit; no process started')
        processes = gpu_processes()
        other = {pid: name for pid, name in processes.items()
                 if pid != os.getpid() and name not in DESKTOP_PROCESSES}
        if other:
            raise RuntimeError('Another GPU application is present; no process or power change made: ' + str(other))
        if not gpu_busy_before_start(before, utilization_limit=10, memory_limit=2048):
            return before, processes
        if time.monotonic() >= deadline:
            raise RuntimeError('GPU is busy; no process or power change made; last sample: ' + json.dumps(before))
        time.sleep(1)


def run(args):
    if os.name != 'nt':
        raise RuntimeError('This guard is for the single-GPU Windows workstation')
    if not 1 <= args.seconds <= 3600 or not 100 <= args.power <= 220:
        raise ValueError('Experiment must be 1..3600 seconds and 100..220 W')
    with MiningLease():
        return _run_owned(args)


def _run_owned(args):
    if os.name != 'nt':
        raise RuntimeError('This guard is for the single-GPU Windows workstation')
    initial_cancel = args.initial_manual_cancel if hasattr(args,'initial_manual_cancel') else manual_cancel_token()
    if manual_cancel_token()!=initial_cancel:
        raise RuntimeError('Manual stop requested before launch; no GPU or power change made')
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        raise ValueError('A child command is required after --')
    executable = Path(command[0]).resolve(strict=True)
    command[0] = str(executable)
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    state_path = out / 'guard-status.json'
    if state_path.exists():
        raise RuntimeError('Run directory already has a guard receipt; use a new directory')
    if (out / 'stop.request').exists():
        raise RuntimeError('Stop request already exists; use a new run directory')
    gpu = Gpu()
    before, initial_gpu_processes = wait_for_idle_gpu(gpu, out, initial_cancel)
    existing_gpu_pids = set(initial_gpu_processes)
    original_power = before['PowerLimit']
    state = {'status': 'preparing', 'started_at': datetime.now(timezone.utc).isoformat(),
             'command': command, 'binary_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
             'original_power_watts': original_power, 'test_power_watts': args.power,
             'duration_limit_seconds': args.seconds, 'child_pid': None,
             'clock_changes': False, 'power_restored': False,
             'environment_pins': {k: os.environ[k] for k in ('SOAT_PEARL_SHAPE', 'SOAT_PEARL_TILE', 'SOAT_PEARL_PROFILE') if k in os.environ}}
    write_json(state_path, state)
    process = None
    reason = 'duration-complete'
    stop_requested = False
    def handle_signal(_signum, _frame):
        nonlocal stop_requested
        stop_requested = True
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, handle_signal)
    try:
        gpu.power(args.power)
        with (out/'child.log').open('w', encoding='utf-8') as log, (out/'telemetry.jsonl').open('w', encoding='utf-8') as samples:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                       creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.BELOW_NORMAL_PRIORITY_CLASS,
                                       cwd=str(executable.parent))
            state.update(status='running', child_pid=process.pid)
            write_json(state_path, state)
            deadline = time.monotonic() + args.seconds
            errors = 0
            while process.poll() is None and time.monotonic() < deadline:
                if stop_requested or (out/'stop.request').exists() or manual_cancel_token()!=initial_cancel:
                    reason = 'manual-stop'; break
                try:
                    reading = gpu.read()
                    errors = 0
                    reading['time'] = datetime.now(timezone.utc).isoformat()
                    samples.write(json.dumps(reading)+'\n'); samples.flush()
                    incoming = {pid: name for pid, name in gpu_processes().items()
                                if pid not in existing_gpu_pids and pid != process.pid
                                and name not in DESKTOP_PROCESSES}
                    reason_now = ('other-gpu-process' if incoming else
                                  'external-power-change' if abs(reading['PowerLimit']-args.power)>1 else
                                  thermal_reason(reading))
                    state['last_telemetry'] = reading
                    write_json(state_path, state)
                    if reason_now:
                        reason = reason_now; break
                except Exception as exc:
                    errors += 1
                    state['telemetry_error'] = str(exc)
                    if errors >= 3:
                        reason = 'telemetry-unavailable'; break
                time.sleep(2)
            if process.poll() is not None:
                reason = 'child-exited'
            state['child_stop'] = stop_owned(process)
            state['child_exit_code'] = process.returncode
    except BaseException as exc:
        reason = 'guard-error'
        state['error'] = type(exc).__name__+': '+str(exc)
        raise
    finally:
        stop_error = None
        try:
            if process is not None and process.poll() is None:
                state['child_stop'] = stop_owned(process)
        except BaseException as exc:
            stop_error = exc
            state['child_stop_error'] = type(exc).__name__+': '+str(exc)
        still_alive = process is not None and process.poll() is None
        if still_alive:
            # A larger cap is unsafe while owned work has not actually stopped.
            state.update(status='stop-failed', stop_reason='owned-child-stop-failed',
                         owned_child_alive=True, power_restored=False,
                         ended_at=datetime.now(timezone.utc).isoformat())
            write_json(state_path, state)
            raise RuntimeError('Owned child is still alive; retaining reduced power limit') from stop_error
        try:
            current_power = gpu.read()['PowerLimit']
            if abs(current_power-args.power) <= 1:
                gpu.power(original_power)
            elif abs(current_power-original_power) > 1:
                state['external_power_preserved'] = current_power
            state['power_restored'] = abs(gpu.read()['PowerLimit']-original_power) <= 1
        except Exception as exc:
            state['recovery_error'] = str(exc)
        state.update(status='stopped', stop_reason=reason,
                     ended_at=datetime.now(timezone.utc).isoformat())
        write_json(state_path, state)
    if not state['power_restored']:
        raise RuntimeError('Original GPU power limit was not restored; inspect guard status')
    return 0 if reason in ['duration-complete', 'manual-stop'] or (reason=='child-exited' and state.get('child_exit_code')==0) else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--seconds', type=int, default=180)
    parser.add_argument('--power', type=int, default=220)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    opts = parser.parse_args()
    if not 1 <= opts.seconds <= 3600 or not 100 <= opts.power <= 220:
        parser.error('Experiment must be 1..3600 seconds and 100..220 W')
    raise SystemExit(run(opts))
