"""Reproducible transcript gate: direct GPU verifier children, each guarded."""
import argparse,datetime,hashlib,json,os,pathlib,subprocess,sys,threading,time,traceback
ROOT=pathlib.Path(__file__).resolve().parent.parent
VARIANTS=["sm86-singlefold-s2-g8-k64","sm86-singlefold-m64n128-b3-k64","sm86-fixed-s2-g8-k64","sm86-fixed-m64n128-b3-k64","ampere-s2-g8","ampere-s2-g4","ampere-s3-g4"]
CANCEL=pathlib.Path("D:/Apps/KRig/Runtime/cancel.request")
def save(path,obj):
 t=path.with_suffix(".tmp");t.write_text(json.dumps(obj,indent=2),encoding="utf-8");t.replace(path)
def cancelled(out,initial):return (out/"stop.request").exists() or (CANCEL.exists() and CANCEL.stat().st_mtime_ns!=initial)
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--output",type=pathlib.Path,required=True);ap.add_argument("--build",choices=["prl3090-fold","prl3090-fixed","prl3090-occupancy"],default="prl3090-fold");ap.add_argument("--variants",nargs="+",choices=VARIANTS,default=VARIANTS[:2]);ap.add_argument("--check-only",action="store_true");a=ap.parse_args();build=ROOT/"build"/a.build
 for exe in ["test-pearl-kernel-resources.exe","test-pearl-mining-shape.exe"]:
  if not (build/exe).is_file():raise ValueError("Missing GPU test target: "+exe)
 cases=[("resources","test-pearl-kernel-resources.exe",[])]
 for m,n in [(256,768),(1024,1024),(4096,65536)]:
  for variant in a.variants:cases.append((str(m)+"x"+str(n)+"-"+variant,"test-pearl-mining-shape.exe",[str(m),str(n),"2048","128",variant]))
 if a.check_only:print(json.dumps({"cases":len(cases),"build":str(build),"variants":a.variants,"gpu_started":False}));return 0
 a.output.mkdir(parents=True,exist_ok=True);status=a.output/"result.json"
 if status.exists():raise ValueError("Refusing to overwrite correctness result")
 state={"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"phase":"starting","build":str(build),"cases":[],"scope":"Full transcript-buffer comparison against independent synchronous oracle; no pool"};initial=CANCEL.stat().st_mtime_ns if CANCEL.exists() else None
 try:
  for name,exe,arguments in cases:
   if cancelled(a.output,initial):raise RuntimeError("manual_stop")
   time.sleep(5);dest=a.output/name;state["phase"]=name;state["active_output"]=str(dest);save(status,state);env=os.environ.copy()
   for key in ["SOAT_PEARL_PROFILE","SOAT_PEARL_SHAPE","SOAT_PEARL_TILE"]:env.pop(key,None)
   cmd=[sys.executable,"-u",str(ROOT/"tools/run_guarded.py"),"--output",str(dest),"--seconds","120","--power","220","--",str(build/exe),*arguments]
   done=threading.Event()
   def watch():
    while not done.wait(1):
     if cancelled(a.output,initial):dest.mkdir(parents=True,exist_ok=True);(dest/"stop.request").touch();return
   thread=threading.Thread(target=watch,daemon=True);thread.start()
   try:
    with (a.output/(name+"-runner.log")).open("w",encoding="utf-8") as log:run=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=log)
   finally:done.set();thread.join(timeout=2)
   gp=dest/"guard-status.json";g=json.loads(gp.read_text()) if gp.exists() else {};log=(dest/"child.log").read_text(encoding="utf-8",errors="replace") if (dest/"child.log").exists() else "missing log"
   with (build/exe).open("rb") as binary:digest=hashlib.file_digest(binary,"sha256").hexdigest()
   result={"name":name,"command":cmd,"binary_sha256":digest,"runner_exit_code":run.returncode,"guard":g,"log":log};state["cases"].append(result);save(status,state)
   if run.returncode or g.get("child_exit_code")!=0 or g.get("stop_reason")!="child-exited" or not g.get("power_restored"):raise RuntimeError("Verifier or guard failed: "+name)
   if arguments:
    expected=arguments[4]+" "+arguments[0]+"x"+arguments[1]+" k=2048 rank=128: ok (0/"
    if expected not in log or "tiles, 0 words differ)" not in log:raise RuntimeError("Missing complete-buffer success report: "+name)
   else:
    rows=[json.loads(l) for l in log.splitlines()]
    if not rows or "gpu" not in rows[0] or not any("configuration" in x for x in rows[1:]):raise RuntimeError("Missing resource inspection report")
  state["phase"]="passed"
 except BaseException as exc:state.update(phase="failed",error=str(exc),traceback=traceback.format_exc())
 finally:state["ended_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat();save(status,state)
 return 0 if state["phase"]=="passed" else 1
if __name__=="__main__":raise SystemExit(main())
