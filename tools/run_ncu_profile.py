"""Bounded counter profiling; an owned Windows Job contains ncu and its GPU child.
Clock control is always none. No pool, wallet, driver or security changes.
"""
import argparse,datetime,hashlib,json,math,os,pathlib,signal,subprocess,sys,time,traceback
from gpu_telemetry import Gpu
from run_guarded import MiningLease,gpu_processes,DESKTOP_PROCESSES,gpu_busy_before_start
from owned_job import OwnedJob
ROOT=pathlib.Path(__file__).resolve().parent.parent
NCU_RECEIPT=pathlib.Path("D:/Apps/NsightCompute/2025.4.1.2/install-receipt.json")
def save(path,value):
 t=path.with_suffix(".tmp");t.write_text(json.dumps(value,indent=2),encoding="utf-8");t.replace(path)
def sha(path):
 with pathlib.Path(path).open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--output",type=pathlib.Path,required=True);ap.add_argument("--build",choices=["prl3090-baseline","prl3090-ampere","prl3090-fixed","prl3090-fold","prl3090-large","prl3090-warpwide","prl3090-prefetch"],default="prl3090-fixed");ap.add_argument("--tile",default="=ampere fixed s2 g8 k64");ap.add_argument("--seconds",type=int,default=120);ap.add_argument("--check-only",action="store_true");a=ap.parse_args()
 if not 15<=a.seconds<=180:raise ValueError("Profile limit must be 15..180 seconds")
 receipt=json.loads(NCU_RECEIPT.read_text(encoding="utf-8-sig"));ncu=pathlib.Path(receipt["ncu"]);miner=ROOT/"build"/a.build/"soat-miner.exe"
 if not ncu.is_file() or not miner.is_file():raise ValueError("Required profiler or miner binary is missing")
 cmd=[str(ncu),"--clock-control","none","--cache-control","none","--target-processes","application-only","--replay-mode","kernel","--kernel-name-base","demangled","--kernel-name","regex:.*noisyGemmPtx.*","--launch-skip","64","--launch-count","1","--kill","yes","--section","SpeedOfLight","--section","ComputeWorkloadAnalysis","--section","MemoryWorkloadAnalysis","--section","MemoryWorkloadAnalysis_Tables","--section","Occupancy","--section","SchedulerStats","--section","WarpStateStats","--section","InstructionStats","--export",str(a.output/"report"),str(miner),"--algo","pearl-pow","--device","0","--bench","--plain","--interval","5"]
 if a.check_only:print(json.dumps({"ncu":str(ncu),"miner":str(miner),"clock_control":"none","power":220,"max_seconds":a.seconds,"gpu_started":False}));return 0
 a.output.mkdir(parents=True,exist_ok=True);status=a.output/"profile-status.json"
 if status.exists():raise ValueError("Refusing to overwrite profile receipt")
 state={"status":"starting","started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"command":cmd,"ncu_sha256":sha(ncu),"miner_sha256":sha(miner),"clock_control":"none","cache_control":"none","gpu_power_limit_watts":220,"maximum_seconds":a.seconds,"ownership":"Windows Job Object: suspended -> assign -> resume; inherited children; kill on close","scope":"synthetic kernel counters, not paid hashrate","power_restored":False};save(status,state)
 cancel=pathlib.Path("D:/Apps/KRig/Runtime/cancel.request");initial_cancel=cancel.stat().st_mtime_ns if cancel.exists() else None;interrupted=[False]
 for sig in [signal.SIGINT,signal.SIGTERM,signal.SIGBREAK]:signal.signal(sig,lambda *_:interrupted.__setitem__(0,True))
 with MiningLease():
  gpu=Gpu();initial=gpu.read();original=initial["PowerLimit"];state["original_power_watts"]=original;job=None;changed=False;stopped=False
  try:
   if interrupted[0] or (a.output/"stop.request").exists() or (cancel.exists() and cancel.stat().st_mtime_ns!=initial_cancel):raise RuntimeError("manual_stop_before_profile")
   if not all(math.isfinite(initial[k]) for k in ["PowerLimit","Temperature","Hotspot","MemoryJunction"]):raise RuntimeError("invalid_gpu_telemetry")
   if gpu_busy_before_start(initial,utilization_limit=10,memory_limit=2048):raise RuntimeError("GPU busy before profile")
   if any(pid!=os.getpid() and name not in DESKTOP_PROCESSES for pid,name in gpu_processes().items()):raise RuntimeError("Another GPU application is present")
   if initial["Temperature"]>=80 or initial["Hotspot"]>=100 or initial["MemoryJunction"]>=96:raise RuntimeError("GPU too warm before profile")
   env=os.environ.copy();env.update(SOAT_PEARL_SHAPE="4096x65536",SOAT_PEARL_TILE=a.tile);env.pop("SOAT_PEARL_PROFILE",None)
   changed=True;gpu.power(220);job=OwnedJob(cmd,a.output/"ncu.log",cwd=ROOT,env=env);state.update(status="running",profiler_pid=job.pid);save(status,state);start=time.monotonic()
   while True:
    if not job.active_count():
     job.stop();stopped=True;state.update(stop_reason="owned_job_exited",child_exit_code=job.poll());break
    reason=None
    if interrupted[0] or (a.output/"stop.request").exists() or (cancel.exists() and cancel.stat().st_mtime_ns!=initial_cancel):reason="manual_stop"
    if time.monotonic()-start>=a.seconds:reason="duration_limit"
    g=gpu.read()
    if not all(math.isfinite(g[k]) for k in ["PowerLimit","Temperature","Hotspot","MemoryJunction"]):raise RuntimeError("invalid_gpu_telemetry")
    with (a.output/"telemetry.jsonl").open("a",encoding="utf-8") as out:out.write(json.dumps({"time":datetime.datetime.now(datetime.timezone.utc).isoformat(),**g})+"\n")
    state["last_telemetry"]=g
    if g["Temperature"]>=80 or g["Hotspot"]>=100 or g["MemoryJunction"]>=96:reason="thermal_guard"
    if abs(g["PowerLimit"]-220)>2:reason="external_power_change"
    for pid,name in gpu_processes().items():
     if pid!=os.getpid() and name not in DESKTOP_PROCESSES and not job.contains(pid):reason="other_gpu_application";break
    if reason:job.stop();stopped=True;state.update(stop_reason=reason,child_exit_code=job.poll());break
    save(status,state);time.sleep(1)
  except BaseException as exc:state.update(status="failed",error=str(exc),traceback=traceback.format_exc())
  finally:
   try:
    if job:job.stop();stopped=True;job.close()
    else:stopped=True
    if changed and stopped:
     current=gpu.read()["PowerLimit"]
     if abs(current-220)<=2:gpu.power(original)
     elif abs(current-original)>2:state["external_power_change_preserved"]=current
    state["actual_final_power_watts"]=gpu.read()["PowerLimit"];state["power_restored"]=abs(state["actual_final_power_watts"]-original)<=2
   except BaseException as exc:state.update(status="cleanup_failed",cleanup_error=str(exc))
   state["ended_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat();save(status,state)
 report=a.output/"report.ncu-rep"
 if state.get("status") not in ["failed","cleanup_failed"]:
  state["status"]="complete" if state.get("child_exit_code")==0 and report.is_file() and state["power_restored"] else "stopped";save(status,state)
 if state["status"]=="complete":
  with (a.output/"metrics.csv").open("wb") as out:result=subprocess.run([str(ncu),"--import",str(report),"--page","raw","--csv"],stdout=out,stderr=subprocess.STDOUT,timeout=30)
  state["metric_export_exit_code"]=result.returncode
  if result.returncode:state.update(status="failed",error="counter CSV export failed")
  save(status,state)
 return 0 if state["status"]=="complete" else 1
if __name__=="__main__":raise SystemExit(main())
