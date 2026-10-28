"""Bounded launch-metadata or counter calibration against an infeasible local job.
No real-pool credits; no production config changes; no global injection settings.
"""
import argparse,datetime,hashlib,json,math,os,pathlib,signal,socket,subprocess,sys,threading,time,traceback,urllib.request
from gpu_telemetry import Gpu
from run_guarded import MiningLease,gpu_processes,DESKTOP_PROCESSES,manual_cancel_token,thermal_reason
from owned_job import OwnedJob
from payout_policy import remaining_seconds,fetch
ROOT=pathlib.Path(__file__).resolve().parent.parent
APP=pathlib.Path("D:/Apps/KRig")
STATE=APP/"Runtime/payout-experience.json"
CUPTI=pathlib.Path("D:/Apps/CUPTI/13.1.115")
def save(path,value):
    tmp=path.with_suffix(".tmp");tmp.write_text(json.dumps(value,indent=2),encoding="utf-8")
    for attempt in range(20):
        try:tmp.replace(path);return
        except PermissionError:
            if attempt==19:raise
            time.sleep(.1)
def sha(path):
    with pathlib.Path(path).open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def tail(path):
    if not path.exists():return []
    with path.open("rb") as f:
        f.seek(max(0,path.stat().st_size-65536));data=f.read().decode("utf-8",errors="replace").splitlines()
    result=[]
    for line in data:
        try:result.append(json.loads(line))
        except ValueError:pass
    return result
class FixedJob:
    def __init__(self):
        self.done=threading.Event();self.errors=[];self.methods=[];self.client=None
        self.server=socket.socket();self.server.bind(("127.0.0.1",0));self.server.listen(1);self.server.settimeout(.5)
        self.port=self.server.getsockname()[1];self.thread=threading.Thread(target=self.serve,daemon=True)
    def send(self,obj):self.client.sendall((json.dumps(obj)+"\n").encode())
    def serve(self):
        try:
            while not self.done.is_set():
                try:self.client,peer=self.server.accept();break
                except socket.timeout:continue
            if not self.client:return
            if peer[0]!="127.0.0.1":raise RuntimeError("Non-loopback client")
            self.client.settimeout(.5);buffer=b"";authorized=False
            while not self.done.is_set():
                try:part=self.client.recv(65536)
                except socket.timeout:continue
                if not part:break
                buffer+=part
                if len(buffer)>1024*1024:raise RuntimeError("Oversized mock protocol record")
                while b"\n" in buffer:
                    line,buffer=buffer.split(b"\n",1)
                    if not line.strip():continue
                    obj=json.loads(line);method=obj.get("method");self.methods.append(method)
                    if method=="mining.authorize":
                        self.send({"id":obj.get("id"),"result":True,"error":None});authorized=True
                        self.send({"id":None,"method":"mining.notify","params":{"job_id":"unit-calibration-fixed","header":"01"*76,"target":"0"*63+"1","height":1,"cert_version":3}})
                    elif method in ("mining.configure","mining.extranonce.subscribe"):
                        self.send({"id":obj.get("id"),"result":{} if method=="mining.configure" else True,"error":None})
                    elif method=="mining.submit":
                        self.errors.append("Unexpected submit against an infeasible target")
                        self.send({"id":obj.get("id"),"result":False,"error":[20,"diagnostic has no credited shares",None]})
                    else:raise RuntimeError("Unsupported mock method: "+str(method))
            if not authorized and not self.done.is_set():raise RuntimeError("No authorize")
        except (ConnectionResetError,ConnectionAbortedError):
            # An owned child terminated after a completed capture resets TCP.
            # Unexpected early child exit is rejected by the outer capture guard.
            pass
        except (OSError,ValueError,RuntimeError) as exc:
            if not self.done.is_set():self.errors.append(str(exc))
        finally:
            if self.client:
                try:self.client.close()
                except OSError:pass
    def start(self):self.thread.start()
    def close(self):
        self.done.set()
        try:self.server.close()
        except OSError:pass
        if self.client:
            try:self.client.shutdown(socket.SHUT_RDWR)
            except OSError:pass
        self.thread.join(timeout=3)
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--backend",choices=["soat","krig"],required=True);ap.add_argument("--mode",choices=["trace","counter"],required=True);ap.add_argument("--output",type=pathlib.Path,required=True);ap.add_argument("--seconds",type=int,default=30);ap.add_argument("--kernel");ap.add_argument("--check-only",action="store_true");a=ap.parse_args()
    if not 10<=a.seconds<=90:raise ValueError("Capture must be 10..90 seconds")
    if a.mode=="counter" and not a.kernel:raise ValueError("Counter calibration needs an observed exact mangled kernel name")
    cfg=json.loads((APP/"mining-config.json").read_text(encoding="utf-8-sig"))
    source=cfg["source_backend"];exe=pathlib.Path(source["executable"]) if a.backend=="soat" else APP/"1.5.12/krig-miner.exe"
    expected=source["sha256"] if a.backend=="soat" else cfg["exe_sha256"]
    if sha(exe)!=expected:raise RuntimeError("Pinned miner hash mismatch")
    dll=ROOT/"build/cupti-trace/cuda-activity-trace.dll";receipt=json.loads((dll.parent/"build-receipt.json").read_text(encoding="utf-8-sig"))
    if sha(dll)!=receipt["Sha256"]:raise RuntimeError("Pinned trace helper hash mismatch")
    ncu=pathlib.Path(json.loads(pathlib.Path("D:/Apps/NsightCompute/2025.4.1.2/install-receipt.json").read_text(encoding="utf-8-sig"))["ncu"])
    if a.check_only:print(json.dumps({"backend":a.backend,"mode":a.mode,"miner_sha256":expected,"trace_sha256":receipt["Sha256"],"seconds":a.seconds,"local_mock_only":True,"gpu_started":False}));return 0
    if not a.output.is_absolute():raise ValueError("Expected absolute Windows playground output")
    a.output.mkdir(parents=True,exist_ok=True);status=a.output/"status.json"
    if status.exists():raise RuntimeError("Refusing to overwrite a prior run")
    state={"status":"preparing","time":datetime.datetime.now(datetime.timezone.utc).isoformat(),"backend":a.backend,"mode":a.mode,"miner":str(exe),"miner_sha256":expected,"scope":"synthetic local job, no pool credits or paid-hashrate claim","configured_vendor_fee_percent":3 if a.backend=="krig" else 0,"production_config_changed":False,"power_restored":False,"clock_changes":False}
    cancel=manual_cancel_token();stop=[False]
    for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGBREAK):signal.signal(sig,lambda *_:stop.__setitem__(0,True))
    job=None;mock=None;changed=False;stopped=False
    with MiningLease():
        gpu=Gpu();initial=gpu.read();original=initial["PowerLimit"];state["original_power_watts"]=original
        try:
            if stop[0] or manual_cancel_token()!=cancel or (a.output/"stop.request").exists():raise RuntimeError("Manual stop before capture")
            if remaining_seconds(STATE)<a.seconds+90:raise RuntimeError("Original experience deadline too close")
            balance=fetch(cfg["wallet"]);state["initial_pool"]=balance
            if balance["goal_reached"]:raise RuntimeError("Original payout experience is already complete")
            if thermal_reason(initial):raise RuntimeError("Unsafe initial telemetry")
            if initial["Utilization"]>10 or initial["MemoryMiB"]>2048:raise RuntimeError("GPU busy")
            if any(pid!=os.getpid() and name not in DESKTOP_PROCESSES for pid,name in gpu_processes().items()):raise RuntimeError("Other GPU client present")
            if a.backend=="krig":
                with socket.socket() as probe:
                    probe.settimeout(.5)
                    if probe.connect_ex(("127.0.0.1",18490))==0:raise RuntimeError("KRig API port already active")
            mock=FixedJob();mock.start();endpoint=f"127.0.0.1:{mock.port}"
            if a.backend=="soat":cmd=[str(exe),"--algo","pearl-pow","--device","0","--pool",endpoint,"--wallet",cfg["wallet"],"--worker","UnitCalibration","--plain","--interval","5"]
            else:cmd=[str(exe),"--coin","pearl","--url","stratum+tcp://"+endpoint,"--user",cfg["wallet"]+"/UnitCalibration","--devices-pci","01:00.0","--no-rocm","--no-intel","--api-host","127.0.0.1","--api-port","18490","--no-tui","--log-level","debug"]
            env=os.environ.copy()
            for key in ("CUDA_INJECTION64_PATH","NVTX_INJECTION64_PATH","SOAT_PEARL_SHAPE","SOAT_PEARL_TILE","SOAT_PEARL_PROFILE"):env.pop(key,None)
            env.update(SOAT_PEARL_SHAPE=source["shape"],SOAT_PEARL_TILE=source["tile"])
            if a.mode=="trace":
                env.update(CUDA_INJECTION64_PATH=str(dll),SOAT_CUDA_TRACE_FILE=str(a.output/"launches.jsonl"),SOAT_CUDA_TRACE_SECONDS=str(a.seconds))
                env["PATH"]=str(CUPTI/"lib")+";"+env.get("PATH","")
            else:
                cmd=[str(ncu),"--clock-control","none","--cache-control","none","--target-processes","application-only","--kernel-name-base","mangled","--kernel-name",a.kernel,"--launch-skip","8","--launch-count","3","--kill","yes","--metrics","sm__ops_path_tensor_src_int8.sum,launch__grid_size,launch__block_size","--export",str(a.output/"counter"),*cmd]
            state.update(command=cmd,original_deadline=json.loads(STATE.read_text(encoding="utf-8-sig"))["MiningDeadline"])
            changed=True;gpu.power(220);job=OwnedJob(cmd,a.output/"child.log",cwd=ROOT,env=env);state.update(status="running",owned_root_pid=job.pid);save(status,state);started=time.monotonic();last_api=0
            while True:
                if not job.active_count():
                    state.update(stop_reason="owned_job_exited",child_exit_code=job.poll());job.stop();stopped=True;break
                if stop[0] or (a.output/"stop.request").exists() or manual_cancel_token()!=cancel:raise RuntimeError("Manual stop")
                if remaining_seconds(STATE)<=0:raise RuntimeError("Original deadline reached")
                if time.monotonic()-started>a.seconds+45:raise RuntimeError("Bounded capture timeout")
                g=gpu.read();state["last_telemetry"]=g
                if not all(math.isfinite(g[k]) for k in ("PowerLimit","Temperature","Hotspot","MemoryJunction")):raise RuntimeError("Invalid telemetry")
                if thermal_reason(g):raise RuntimeError("Thermal guard")
                if abs(g["PowerLimit"]-220)>2:raise RuntimeError("External power cap change")
                for pid,name in gpu_processes().items():
                    if pid!=os.getpid() and name not in DESKTOP_PROCESSES and not job.contains(pid):raise RuntimeError("Other GPU task; yield")
                with (a.output/"telemetry.jsonl").open("a",encoding="utf-8") as f:f.write(json.dumps({"time":datetime.datetime.now(datetime.timezone.utc).isoformat(),**g})+"\n")
                if a.backend=="krig" and time.monotonic()-last_api>=2:
                    last_api=time.monotonic()
                    try:
                        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                        with opener.open("http://127.0.0.1:18490/",timeout=.5) as response:data=json.load(response)
                        if data.get("miner_name")!="krig-miner" or data.get("miner_version")!="1.5.12":raise ValueError("API identity mismatch")
                        with (a.output/"native-api.jsonl").open("a",encoding="utf-8") as f:f.write(json.dumps({"time":datetime.datetime.now(datetime.timezone.utc).isoformat(),"unix_ns":time.time_ns(),"response":data})+"\n")
                    except (OSError,ValueError):pass
                if a.mode=="trace":
                    ends=[r for r in tail(a.output/"launches.jsonl") if r.get("event")=="trace_end"]
                    if ends:
                        state["trace_end"]=ends[-1]
                        if ends[-1]["errors"] or ends[-1]["dropped"] or not ends[-1]["kernels"]:raise RuntimeError("Incomplete or lossy launch trace")
                        state["stop_reason"]="trace_complete";job.stop();stopped=True;break
                save(status,state);time.sleep(.5)
            if mock.errors:raise RuntimeError("Mock protocol failed: "+str(mock.errors))
            if a.mode=="counter" and (state.get("child_exit_code")!=0 or not (a.output/"counter.ncu-rep").exists()):raise RuntimeError("Counter profile did not finish")
            state["status"]="complete"
        except BaseException as exc:state.update(status="failed",error=str(exc),traceback=traceback.format_exc())
        finally:
            try:
                if job:job.stop();stopped=True;job.close()
                else:stopped=True
                if mock:mock.close();state["mock_methods"]=mock.methods;state["mock_errors"]=mock.errors
                if changed and stopped:
                    current=gpu.read()["PowerLimit"]
                    if abs(current-220)<=2:gpu.power(original)
                    elif abs(current-original)>2:state["external_power_change_preserved"]=current
                state["final_power_watts"]=gpu.read()["PowerLimit"];state["power_restored"]=abs(state["final_power_watts"]-original)<=2
            except BaseException as exc:state.update(status="cleanup_failed",cleanup_error=str(exc))
            state["ended_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat();save(status,state)
    if a.mode=="counter" and state["status"]=="complete":
        with (a.output/"metrics.csv").open("wb") as f:r=subprocess.run([str(ncu),"--import",str(a.output/"counter.ncu-rep"),"--page","raw","--csv"],stdout=f,stderr=subprocess.STDOUT,timeout=30)
        state["counter_export_exit_code"]=r.returncode
        if r.returncode:state.update(status="failed",error="Counter export failed")
        save(status,state)
    print(json.dumps(state))
    return 0 if state["status"]=="complete" and state["power_restored"] else 1
if __name__=="__main__":raise SystemExit(main())
