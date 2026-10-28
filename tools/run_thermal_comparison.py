"""Bounded synthetic A/B/A through run_guarded; no pool, clock or fan changes."""
import argparse,datetime,hashlib,json,math,os,pathlib,statistics,subprocess,sys,threading,time,traceback
from gpu_telemetry import Gpu
from run_guarded import gpu_processes,DESKTOP_PROCESSES
ROOT=pathlib.Path(__file__).resolve().parent.parent
UTC=datetime.timezone.utc

def read(path):return json.loads(pathlib.Path(path).read_text(encoding="utf-8-sig"))
def save(path,data):
 t=path.with_suffix(".tmp");t.write_text(json.dumps(data,indent=2),encoding="utf-8");t.replace(path)
def validate(plan):
 if plan.get("power_watts")!=220:raise ValueError("This experiment is limited to 220 W")
 if [x["role"] for x in plan["cases"]]!=["A1","B","A2"]:raise ValueError("Expected bounded A/B/A")
 for c in plan["cases"]:
  if not 600<=c["seconds"]<=900:raise ValueError("Each case needs 600..900 seconds")
  if not pathlib.Path(c["executable"]).is_file():raise ValueError("Missing case binary")
  if c["tile"].startswith("=") and not c.get("exact_filter_supported"):raise ValueError("Binary does not declare exact-filter support")
 if plan["cases"][0]["executable"]!=plan["cases"][2]["executable"] or plan["cases"][0]["tile"]!=plan["cases"][2]["tile"]:raise ValueError("A controls must use the same executable and tile")
 for f in plan["required_correctness"]:
  if read(f).get("phase")!="passed":raise ValueError("Correctness gate not passed")

def new_stop(output,initial_cancel):
 f=pathlib.Path("D:/Apps/KRig/Runtime/cancel.request")
 return (output/"stop.request").exists() or (f.exists() and f.stat().st_mtime_ns!=initial_cancel)

def cooldown(output,gpu,initial_cancel):
 start=time.monotonic();rows=[]
 while time.monotonic()-start<900:
  if new_stop(output,initial_cancel):raise RuntimeError("manual_stop")
  g=gpu.read();rows.append({"time":time.monotonic(),**g})
  if any(pid!=os.getpid() and name not in DESKTOP_PROCESSES for pid,name in gpu_processes().items()):raise RuntimeError("other_gpu_application_during_cooldown")
  if g["MemoryMiB"]>2048 or g["Utilization"]>15:raise RuntimeError("gpu_busy_during_cooldown")
  tail=[x for x in rows if rows[-1]["time"]-x["time"]<=60]
  ready=g["Temperature"]<=50 and g["Hotspot"]<=65 and g["MemoryJunction"]<=65
  stable=len(tail)>=10 and all(max(x[k] for x in tail)-min(x[k] for x in tail)<=2 for k in ["Temperature","MemoryJunction"])
  if time.monotonic()-start>=180 and ready and stable:return {"seconds":round(time.monotonic()-start),"end":g}
  time.sleep(5)
 raise RuntimeError("cooldown_timeout_15_minutes")

def summarize(dest,seconds):
 g=read(dest/"guard-status.json");text=(dest/"child.log").read_text(encoding="utf-8",errors="replace");rates=[]
 for line in text.splitlines():
  try:x=json.loads(line)
  except ValueError:continue
  if "rate" in x and x.get("uptime_s",0)>=seconds-180:rates.append(x["rate"])
 rows=[json.loads(l) for l in (dest/"telemetry.jsonl").read_text().splitlines()]
 end=datetime.datetime.fromisoformat(g["ended_at"]);tail=[x for x in rows if 0<=(end-datetime.datetime.fromisoformat(x["time"])).total_seconds()<=180]
 if len(rates)<25 or len(tail)<30:raise RuntimeError("Insufficient steady-window samples")
 third=max(1,len(tail)//3)
 drift={k:statistics.mean(x[k] for x in tail[-third:])-statistics.mean(x[k] for x in tail[:third]) for k in ["Temperature","Hotspot","MemoryJunction"]}
 return {"guard":g,"selected":[l for l in text.splitlines() if l.startswith("[pearl-pow]") and " with " in l],"rate_samples":len(rates),"mean_tmacs":statistics.mean(rates),"median_tmacs":statistics.median(rates),"temperature_drift_c":drift,"steady":all(abs(v)<=1.5 for v in drift.values()),"telemetry":{k:{"mean":statistics.mean(x[k] for x in tail),"min":min(x[k] for x in tail),"max":max(x[k] for x in tail)} for k in ["Temperature","Hotspot","MemoryJunction","Power","CoreClockMHz"]}}

def main():
 a=argparse.ArgumentParser();a.add_argument("--plan",type=pathlib.Path,required=True);a.add_argument("--output",type=pathlib.Path,required=True);a.add_argument("--check-only",action="store_true");args=a.parse_args();plan=read(args.plan);validate(plan)
 if args.check_only:print("PLAN_CHECK_OK (no GPU work)");return 0
 out=args.output;out.mkdir(parents=True,exist_ok=True)
 if (out/"result.json").exists():raise ValueError("Refusing to overwrite experiment result")
 save(out/"plan.json",plan);state={"started_at":datetime.datetime.now(UTC).isoformat(),"phase":"starting","scope":"synthetic; no shares or mining income","cases":[]};gpu=Gpu();cancel=pathlib.Path("D:/Apps/KRig/Runtime/cancel.request");initial_cancel=cancel.stat().st_mtime_ns if cancel.exists() else None
 try:
  for c in plan["cases"]:
   name=c["role"];state["phase"]="cooldown-"+name;save(out/"result.json",state);cool=cooldown(out,gpu,initial_cancel)
   dest=out/name;state["phase"]=name;state["active_output"]=str(dest);save(out/"result.json",state)
   env=os.environ.copy();env.update(SOAT_PEARL_SHAPE="4096x65536",SOAT_PEARL_TILE=c["tile"]);env.pop("SOAT_PEARL_PROFILE",None)
   cmd=[sys.executable,"-u",str(ROOT/"tools/run_guarded.py"),"--output",str(dest),"--seconds",str(c["seconds"]),"--power","220","--",c["executable"],"--algo","pearl-pow","--device","0","--bench","--plain","--interval","5"]
   done=threading.Event()
   def watch():
    while not done.wait(1):
     if new_stop(out,initial_cancel):
      dest.mkdir(parents=True,exist_ok=True);(dest/"stop.request").touch();return
   t=threading.Thread(target=watch,daemon=True);t.start()
   try:
    with (out/(name+"-runner.log")).open("w",encoding="utf-8") as log:result=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=log)
   finally:done.set();t.join(timeout=2)
   if result.returncode:raise RuntimeError("Guard stopped case "+name+"; see its receipt")
   s=summarize(dest,c["seconds"]);s.update(role=name,cooldown=cool,executable_sha256=hashlib.file_digest(pathlib.Path(c["executable"]).open("rb"),"sha256").hexdigest());state["cases"].append(s);save(out/"result.json",state)
   if s["guard"].get("stop_reason")!="duration-complete" or not s["guard"].get("power_restored"):raise RuntimeError("Guard did not complete and restore "+name)
  a1,b,a2=state["cases"];base=(a1["mean_tmacs"]+a2["mean_tmacs"])/2;drift=100*abs(a2["mean_tmacs"]-a1["mean_tmacs"])/base
  state.update(phase="complete",a_control_drift_percent=drift,b_vs_bracketed_a_percent=100*(b["mean_tmacs"]/base-1),comparison_valid=drift<=2 and all(x["steady"] for x in state["cases"]),not_paid_hashrate=True)
 except BaseException as exc:state.update(phase="stopped",error=str(exc),traceback=traceback.format_exc())
 finally:state["ended_at"]=datetime.datetime.now(UTC).isoformat();save(out/"result.json",state)
 return 0 if state["phase"]=="complete" else 1
if __name__=="__main__":raise SystemExit(main())
