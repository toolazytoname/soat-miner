"""Sequential owned-job profiles. Stop on any failed case or new manual cancel."""
import argparse,datetime,json,os,pathlib,re,subprocess,sys,time,traceback
ROOT=pathlib.Path(__file__).resolve().parent.parent
CANCEL=pathlib.Path("D:/Apps/KRig/Runtime/cancel.request")
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--plan",type=pathlib.Path,required=True);ap.add_argument("--output",type=pathlib.Path,required=True);a=ap.parse_args();plan=json.loads(a.plan.read_text())
 if not 1<=len(plan["cases"])<=5:raise ValueError("Expected 1..5 bounded cases")
 if json.loads(pathlib.Path(plan["correctness_result"]).read_text()).get("phase")!="passed":raise ValueError("Correctness gate is not passed")
 for case in plan["cases"]:
  if not re.fullmatch("[a-z0-9-]{1,64}",case["name"]):raise ValueError("Unsafe case name")
 a.output.mkdir(parents=True,exist_ok=True);target=a.output/"result.json"
 if target.exists():raise ValueError("Do not overwrite a profile plan result")
 state={"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"phase":"starting","cases":[],"scope":"instrumented diagnostic counters, not normal mining throughput"};initial=CANCEL.stat().st_mtime_ns if CANCEL.exists() else None
 def save():
  temp=target.with_suffix(".tmp");temp.write_text(json.dumps(state,indent=2),encoding="utf-8");temp.replace(target)
 try:
  for case in plan["cases"]:
   if (a.output/"stop.request").exists() or (CANCEL.exists() and CANCEL.stat().st_mtime_ns!=initial):raise RuntimeError("manual_stop")
   time.sleep(5);out=a.output/case["name"];state.update(phase=case["name"],active_output=str(out));save()
   cmd=[sys.executable,"-u",str(ROOT/"tools/run_ncu_profile.py"),"--output",str(out),"--build",case["build"],"--tile",case["tile"],"--seconds","120"]
   with (a.output/(case["name"]+"-runner.log")).open("w",encoding="utf-8") as log:run=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=log)
   f=out/"profile-status.json";receipt=json.loads(f.read_text()) if f.exists() else {};state["cases"].append({"name":case["name"],"exit_code":run.returncode,"receipt":receipt,"output":str(out)});save()
   if run.returncode or receipt.get("status")!="complete" or not receipt.get("power_restored"):raise RuntimeError("Profiling did not complete safely: "+case["name"])
  state["phase"]="complete"
 except BaseException as exc:state.update(phase="failed",error=str(exc),traceback=traceback.format_exc())
 finally:state["ended_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
 return 0 if state["phase"]=="complete" else 1
if __name__=="__main__":raise SystemExit(main())
