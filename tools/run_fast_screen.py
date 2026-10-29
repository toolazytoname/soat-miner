"""Bounded, warmed candidate screening. Provisional observations; no auto-promotion."""
import argparse,datetime,hashlib,json,math,os,pathlib,threading,time,traceback
from types import SimpleNamespace
import run_guarded as guard
from analyze_matched_backends import weighted_window
from payout_policy import fetch,remaining_seconds
ROOT=pathlib.Path(__file__).resolve().parent.parent
STATUS=pathlib.Path("D:/Apps/KRig/Runtime/payout-experience.json")
CONFIG=pathlib.Path("D:/Apps/KRig/mining-config.json")
def load(path):return json.loads(pathlib.Path(path).read_text(encoding="utf-8-sig"))
def save(path,value):
    temp=path.with_suffix(".tmp");temp.write_text(json.dumps(value,indent=2),encoding="utf-8");temp.replace(path)
def digest(path):
    with pathlib.Path(path).open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def validate(plan):
    if plan.get("power_watts")!=220 or not 180<=plan.get("warmup_seconds",0)<=360:raise ValueError("Expected 220 W and bounded 180..360 second warmup")
    if not 60<=plan.get("case_seconds",0)<=120:raise ValueError("Expected 60..120 seconds per screen case")
    cases=plan["cases"]
    if [c["name"] for c in cases]!=["A0","C1","A1","C2","A2"]:raise ValueError("Expected baseline/candidate/baseline/candidate/baseline")
    binary=pathlib.Path(plan["executable"])
    if not binary.is_absolute() or not binary.resolve().is_relative_to((ROOT/"build").resolve()) or binary.name!="soat-miner.exe":raise ValueError("Expected own built miner")
    if digest(binary)!=plan["executable_sha256"]:raise ValueError("Miner changed after planning")
    proof=load(plan["correctness_result"])
    if proof.get("phase")!="passed" or pathlib.Path(proof["build"]).resolve()!=binary.parent.resolve():raise ValueError("Matching complete-buffer gate required")
    tested={c["name"]:c for c in proof["cases"]}
    for c in cases:
        if not c["tile"].startswith("="):raise ValueError("Exact tile selection is required")
        if c["name"].startswith("C"):
            for m,n in [(256,768),(1024,1024),(4096,65536)]:
                key=f"{m}x{n}-{c['oracle_variant']}"
                if key not in tested or tested[key]["binary_sha256"]!=digest(binary.parent/"test-pearl-mining-shape.exe"):raise ValueError("Current verifier did not check all shapes")
    if len({cases[i]["tile"] for i in [0,2,4]})!=1:raise ValueError("Baseline controls must be identical")
    return cases

def summarize(dest):
    g=load(dest/"guard-status.json")
    if g.get("stop_reason")!="duration-complete" or not g.get("power_restored"):raise ValueError("Guard or power restoration failed")
    stats=[]
    for line in (dest/"child.log").read_text(encoding="utf-8",errors="replace").splitlines():
        try:r=json.loads(line)
        except ValueError:continue
        if "rate" not in r:continue
        if r.get("backend")!="CUDA" or r.get("unit")!="T MAC/s":raise ValueError("Unknown backend rate unit")
        epoch=r.get("timestamp_unix_ms")
        if isinstance(epoch,bool) or not isinstance(epoch,(int,float)) or not math.isfinite(epoch):raise ValueError("Missing current statistics timestamp")
        if stats and epoch<=stats[-1][0]:raise ValueError("Non-monotonic source statistics")
        stats.append((epoch/1000,r["rate"]))
    samples=load_lines(dest/"telemetry.jsonl");rows=[];index=0
    for sample in samples:
        epoch=datetime.datetime.fromisoformat(sample["time"]).timestamp()
        if not stats or epoch<stats[0][0]:continue
        while index+1<len(stats) and stats[index+1][0]<=epoch:index+=1
        if epoch-stats[index][0]>5:raise ValueError("Missing fresh benchmark statistics")
        rows.append({"Epoch":epoch,"ReportedRate":stats[index][1],"Gpu":sample})
    tail=weighted_window(rows,30)
    return {"tail":tail,"guard":g,"measurement":"Final 30 seconds covered by guard telemetry, with latest prior source statistic <=5 seconds old"}
def load_lines(path):return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
def review(cases):
    controls=[cases[i]["tail"]["time_weighted_Tmac_s"] for i in [0,2,4]]
    if min(controls)<=0:raise ValueError("Baseline did not compute")
    drift=100*(max(controls)/min(controls)-1);control_ok=drift<=2 and all(cases[i]["tail"]["steady"] for i in [0,2,4]);candidates=[]
    for i in [1,3]:
        item=cases[i];t=item["tail"];adjacent=[cases[i-1]["tail"],cases[i+1]["tail"]]
        rate=sum(c["time_weighted_Tmac_s"] for c in adjacent)/2;eff=sum(c["gpu_Tmac_per_joule"] for c in adjacent)/2
        gain=100*(t["time_weighted_Tmac_s"]/rate-1);egain=100*(t["gpu_Tmac_per_joule"]/eff-1)
        candidates.append({"name":item["name"],"tile":item["tile"],"observed_rate_gain_percent":gain,"observed_gpu_efficiency_gain_percent":egain,"eligible_for_long_confirmation":control_ok and t["steady"] and gain>=3 and egain>=3})
    eligible=[c for c in candidates if c["eligible_for_long_confirmation"]]
    return {"baseline_range_percent":drift,"baseline_controls_stable":control_ok,"candidates":candidates,"next_candidate":max(eligible,key=lambda c:c["observed_gpu_efficiency_gain_percent"])["name"] if eligible else None,"production_config_changed":False,"scope":"Provisional screen. A candidate needs longer controlled confirmation and real-pool acceptance before deployment."}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--plan",type=pathlib.Path,required=True);ap.add_argument("--output",type=pathlib.Path,required=True);ap.add_argument("--check-only",action="store_true");args=ap.parse_args();plan=load(args.plan);cases=validate(plan)
    if args.check_only:print("FAST_SCREEN_PLAN_OK (no GPU work)");return 0
    out=args.output;out.mkdir(parents=True,exist_ok=True);target=out/"result.json"
    if target.exists():raise ValueError("Do not overwrite a screening run")
    initial=guard.manual_cancel_token();config=load(CONFIG);config_sha=digest(CONFIG)
    state={"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"phase":"preflight","scope":"Synthetic candidate screen; no shares or earnings","cases":[],"plan":plan};save(target,state)
    def limits():
        if (out/"stop.request").exists() or guard.manual_cancel_token()!=initial:return "manual_stop"
        if remaining_seconds(STATUS)<=0:return "original_mining_deadline_reached"
        return None
    try:
        if remaining_seconds(STATUS)<plan["warmup_seconds"]+len(cases)*plan["case_seconds"]+90:raise ValueError("Insufficient original time budget")
        balance=fetch(config["wallet"]);state["preflight_pool"]=balance
        if balance["goal_reached"]:raise ValueError("Original first payout threshold already reached")
        for c in [{"name":"warmup","tile":cases[0]["tile"],"seconds":plan["warmup_seconds"]}]+cases:
            if limits():raise RuntimeError(limits())
            if digest(CONFIG)!=config_sha or digest(plan["executable"])!=plan["executable_sha256"]:raise ValueError("Configuration or executable changed")
            dest=out/c["name"];dest.mkdir();state.update(phase=c["name"],active_output=str(dest));save(target,state)
            done=threading.Event();stop_reason=[]
            def watch():
                next_pool=time.monotonic()+60
                while not done.wait(1):
                    reason=limits()
                    if reason is None and time.monotonic()>=next_pool:
                        try:
                            snapshot=fetch(config["wallet"]);next_pool=time.monotonic()+60
                            if snapshot["goal_reached"]:reason="payout_threshold_accumulated"
                        except Exception as exc:reason="pool_check_failed: "+str(exc)
                    if reason:stop_reason.append(reason);(dest/"stop.request").touch();return
            thread=threading.Thread(target=watch,daemon=True);thread.start();prior={k:os.environ.get(k) for k in ["SOAT_PEARL_TILE","SOAT_PEARL_SHAPE","SOAT_PEARL_PROFILE"]}
            os.environ.update(SOAT_PEARL_TILE=c["tile"],SOAT_PEARL_SHAPE="4096x65536");os.environ.pop("SOAT_PEARL_PROFILE",None)
            try:code=guard.run(SimpleNamespace(output=str(dest),seconds=c.get("seconds",plan["case_seconds"]),power=220,command=[plan["executable"],"--algo","pearl-pow","--device","0","--bench","--plain","--interval","1"],initial_manual_cancel=initial))
            finally:
                done.set();thread.join(timeout=20)
                for k,v in prior.items():
                    if v is None:os.environ.pop(k,None)
                    else:os.environ[k]=v
                if thread.is_alive():raise RuntimeError("Pool monitor did not finish; no next case")
            if code or stop_reason:raise RuntimeError("Screen stopped: "+str(stop_reason or code))
            result=summarize(dest);result.update(name=c["name"],tile=c["tile"])
            if c["name"]=="warmup":state["warmup"]=result
            else:state["cases"].append(result)
            save(target,state);time.sleep(2)
        state.update(phase="complete",review=review(state["cases"]))
    except BaseException as exc:state.update(phase="stopped",error=str(exc),traceback=traceback.format_exc())
    finally:
        state.update(ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),production_config_unchanged=digest(CONFIG)==config_sha);save(target,state)
    return 0 if state["phase"]=="complete" else 1
if __name__=="__main__":raise SystemExit(main())
