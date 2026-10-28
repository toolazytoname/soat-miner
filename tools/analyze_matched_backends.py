"""Matched real-pool source / KRig / source analysis; never converts counters to earnings."""
import argparse,datetime,json,math,pathlib
def load(path):return json.loads(pathlib.Path(path).read_text(encoding="utf-8-sig"))
def finite(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError("Missing or invalid numeric telemetry")
    return float(value)
def weighted_window(rows,seconds=180):
    if len(rows)<2:raise ValueError("Insufficient telemetry")
    for a,b in zip(rows,rows[1:]):
        if not 0<b["Epoch"]-a["Epoch"]<=15:raise ValueError("Non-monotonic or missing telemetry")
    end=finite(rows[-1]["Epoch"]);start=end-seconds
    if rows[0]["Epoch"]>start:raise ValueError("Tail window is not fully covered")
    pieces=[];thermal=[]
    for a,b in zip(rows,rows[1:]):
        left=max(start,a["Epoch"]);right=min(end,b["Epoch"])
        if right<=left:continue
        duration=right-left;g=a["Gpu"];rate=finite(a["ReportedRate"])
        if rate<0 or abs(finite(g["PowerLimit"])-220)>2:raise ValueError("Rate or board cap changed outside protocol")
        power=finite(g["Power"])
        if power<0:raise ValueError("Invalid board power")
        values=[finite(g[k]) for k in ("Temperature","Hotspot","MemoryJunction")]
        if any(v>=limit for v,limit in zip(values,(80,100,96))):raise ValueError("Thermal protection threshold reached")
        pieces.append((duration,rate,power));thermal.append(values)
    if abs(sum(p[0] for p in pieces)-seconds)>.001:raise ValueError("Incomplete tail coverage")
    thermal.append([finite(rows[-1]["Gpu"][k]) for k in ("Temperature","Hotspot","MemoryJunction")])
    ranges=[max(v[i] for v in thermal)-min(v[i] for v in thermal) for i in range(3)]
    mean=sum(d*r for d,r,w in pieces)/seconds;power=sum(d*w for d,r,w in pieces)/seconds
    active=sum(d for d,r,w in pieces if r>0)
    return {"tail_seconds":seconds,"tail_start_epoch":start,"tail_end_epoch":end,"time_weighted_Tmac_s":mean,"active_time_weighted_Tmac_s":sum(d*r for d,r,w in pieces if r>0)/active if active else 0,"idle_wall_seconds":seconds-active,"mean_gpu_power_watts":power,"gpu_Tmac_per_joule":mean/power if power else None,"thermal_range_c":{"core":ranges[0],"hotspot":ranges[1],"memory":ranges[2]},"steady":all(v<=2 for v in ranges),"points":len(pieces)}
def validate_window_units(rows,expected,seconds=180):
    start=rows[-1]["Epoch"]-seconds
    measured=[a for a,b in zip(rows,rows[1:]) if b["Epoch"]>start]+rows[-1:]
    if any(r.get("ReportedRateUnit")!=expected for r in measured):raise ValueError("Backend units changed inside measured window")
def case(root,name,final):
    start=load(root/(name+"-start.json"));s=start["session"];backend=start["backend"]
    path=pathlib.Path(s["RunDirectory"])/"telemetry.ndjson"
    rows=[json.loads(v) for v in path.read_text(encoding="utf-8-sig").splitlines() if v.strip()]
    rows=[r for r in rows if r.get("Stage")=="selected-profile"]
    expected="T MAC/s" if backend=="soat" else "TH/s"
    validate_window_units(rows,expected)
    for a,b in zip(rows,rows[1:]):
        if any(b.get(k,0)<a.get(k,0) for k in ("AcceptedShares","RejectedShares","StaleShares")):raise ValueError("Share counters went backwards")
    tail=weighted_window(rows)
    last=rows[-1];stop=None
    if final:
        stop=load(root/(name+"-stop.json"))
        after=stop["after"]
        if not stop.get("operator_completed_case") or after.get("Status")!="stopped" or not after.get("PowerRestored") or after.get("StopReason")!="user_stop" or stop["actual_after"].get("OldProcesses"):raise ValueError("Case stop/ownership/power gate failed")
        if after.get("SessionId")!=s["SessionId"]:raise ValueError("Case session changed")
        if after.get("RejectedShares",0) or after.get("StaleShares",0) or not after.get("AcceptedShares",0):raise ValueError("Real-pool share acceptance gate failed")
    return {"case":name,"backend":backend,"session_id":s["SessionId"],"run_directory":s["RunDirectory"],"preview":not final,"duration_observed_seconds":rows[-1]["Epoch"]-rows[0]["Epoch"],"miner_reported_accepted":last.get("AcceptedShares",0),"miner_reported_rejected":last.get("RejectedShares",0),"miner_reported_stale":last.get("StaleShares",0),"native_unit":expected,"normalization_factor":1,"tail":tail,"stop_receipt":str(root/(name+"-stop.json")) if final else None}
def analyze(root,unit_receipt):
    units=load(unit_receipt)
    if units.get("status")!="passed" or units.get("native_KRig_TH_to_Tmac_factor")!=1:raise ValueError("Independent unit calibration is required")
    cases=[case(root,n,True) for n in ("A1","B","A2")];a1,b,a2=[v["tail"] for v in cases]
    source=(a1["time_weighted_Tmac_s"]+a2["time_weighted_Tmac_s"])/2;closed=b["time_weighted_Tmac_s"]
    source_power=(a1["mean_gpu_power_watts"]+a2["mean_gpu_power_watts"])/2;closed_power=b["mean_gpu_power_watts"]
    drift=abs(a2["time_weighted_Tmac_s"]/a1["time_weighted_Tmac_s"]-1)*100
    valid=all(c["tail"]["steady"] for c in cases) and drift<=3
    return {"status":"complete" if valid else "needs_review","comparison_valid":valid,"scope":"One Windows RTX3090, original real pool/wallet/PPS+, 220 W cap, auto clocks/fans. Tail means include zero-rate waiting intervals. No wall-plug measurement or earning claim.","cases":cases,"source_bracketed_Tmac_s":source,"krig_Tmac_s":closed,"source_bracketed_gpu_power_watts":source_power,"krig_gpu_power_watts":closed_power,"source_control_drift_percent":drift,"krig_vs_source_throughput_percent":(closed/source-1)*100 if valid else None,"source_vs_krig_throughput_percent":(source/closed-1)*100 if valid else None,"source_gpu_Tmac_per_joule":source/source_power,"krig_gpu_Tmac_per_joule":closed/closed_power,"theoretical_fee_adjusted_work_not_measured_payout":{"source_fee_percent":0,"krig_localhost_fee_percent":3,"source_Tmac_s":source,"krig_Tmac_s":closed*.97,"krig_vs_source_percent":(closed*.97/source-1)*100 if valid else None},"share_count_limit":"Miner-reported shares are compatibility evidence, not a statistically precise income comparison. KRig API counters are not asserted to distinguish developer-pool shares.","unit_calibration":str(unit_receipt)}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",type=pathlib.Path,required=True);ap.add_argument("--units",type=pathlib.Path);ap.add_argument("--case",choices=["A1","B","A2"]);ap.add_argument("--preview",action="store_true");ap.add_argument("--output",type=pathlib.Path);a=ap.parse_args()
    if a.case:result=case(a.root,a.case,not a.preview)
    else:
        if not a.units:raise ValueError("--units is required for the complete comparison")
        result=analyze(a.root,a.units)
    if a.output:a.output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result))
if __name__=="__main__":main()
