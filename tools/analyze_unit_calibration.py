"""Analyze this pinned PRL3090 unit-calibration fixture, not mining profitability."""
import argparse,ast,collections,csv,hashlib,json,pathlib,re,statistics
from decimal import Decimal
SOURCE_DIMS=(4096,65536,2048,128)
METRIC="sm__ops_path_tensor_src_int8.sum"
def load(path):return json.loads(pathlib.Path(path).read_text(encoding="utf-8-sig"))
def digest(path):
    with pathlib.Path(path).open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def geometry(text):
    try:values=ast.literal_eval(text.strip())
    except (ValueError,SyntaxError) as exc:raise ValueError("Invalid launch geometry") from exc
    if not isinstance(values,(tuple,list)) or len(values)!=3 or any(type(x) is not int or x<=0 for x in values):raise ValueError("Invalid launch geometry")
    return tuple(values)
def operations(text):
    value=Decimal(text.replace(",",""))
    if not value.is_finite() or value<=0 or value!=value.to_integral_value():raise ValueError("Missing or invalid operation count")
    return int(value)
def counter(run,expected_macs):
    state=load(run/"status.json")
    if state.get("status")!="complete" or not state.get("power_restored") or state.get("child_exit_code")!=0:raise ValueError("Counter run not successfully completed")
    command=state["command"];kernel=command[command.index("--kernel-name")+1]
    rows=[r for r in csv.DictReader((run/"metrics.csv").read_text(encoding="utf-8-sig").splitlines()) if r.get("ID")]
    if len(rows)!=3:raise ValueError("Three independent matching launches are required")
    samples=[(operations(r[METRIC]),geometry(r["Grid Size"]),geometry(r["Block Size"])) for r in rows]
    if len(set(samples))!=1:raise ValueError("Counter work or geometry changed between samples")
    ops,grid,block=samples[0]
    if ops!=2*expected_macs:raise ValueError("Hardware operation count does not match the declared matrix work")
    return {"kernel":kernel,"grid":list(grid),"block":list(block),"independent_samples":3,"operations_per_launch":ops,"macs_per_launch":expected_macs,"operations_per_mac":2,"metrics_sha256":digest(run/"metrics.csv")}
def capture(run,profile):
    state=load(run/"status.json")
    if not state.get("power_restored"):raise ValueError("Capture did not restore power")
    if state.get("status")!="complete":
        review=load(run/"acceptance-review.json")
        if not review.get("raw_capture_valid") or not review.get("original_receipt_retained"):raise ValueError("Failed runner has no explicit valid raw-data review")
    events=[json.loads(line) for line in (run/"launches.jsonl").read_text(encoding="utf-8").splitlines()]
    starts=[e for e in events if e.get("event")=="trace_start"];ends=[e for e in events if e.get("event")=="trace_end"]
    kernels=[e for e in events if e.get("event")=="kernel"]
    if len(starts)!=1 or len(ends)!=1 or ends[0].get("errors") or ends[0].get("dropped") or any(e.get("event") in ["error","dropped"] for e in events):raise ValueError("Lossy or incomplete trace")
    start,end=starts[0],ends[0]
    if end["kernels"]!=len(kernels) or start["pid"]!=state["owned_root_pid"]:raise ValueError("Trace count or owned-process identity mismatch")
    lo=start["cupti_ns"]+5_000_000_000;hi=end["cupti_ns"]-2_000_000_000
    if hi-lo<10_000_000_000:raise ValueError("Trace window too short")
    selected=[e for e in kernels if e["name"]==profile["kernel"]]
    if not selected:raise ValueError("Profiled kernel absent from activity capture")
    inside=[e for e in selected if lo<=e["start_ns"]<=e["end_ns"]<=hi]
    if not inside:raise ValueError("No complete profiled work in the measured window")
    if any(e["grid"]!=profile["grid"] or e["block"]!=profile["block"] for e in inside):raise ValueError("Work geometry changed inside the measured window")
    seconds=(hi-lo)/1e9
    return {"trace_sha256":digest(run/"launches.jsonl"),"runner_status":state["status"],"runner_review_required":state["status"]!="complete","trace_start":start,"trace_end":end,"window_cupti_ns":[lo,hi],"window_seconds":seconds,"complete_gemm_launches":len(inside),"gemm_launches_per_second":len(inside)/seconds,"dense_gemm_Tmac_per_wall_second":len(inside)*profile["macs_per_launch"]/seconds/1e12,"two_boundary_launch_work_Tmac_s":2*profile["macs_per_launch"]/seconds/1e12,"scope":"CUPTI activity calibration only, not a steady mining benchmark or earnings proof"}
def krig_equations(text,dims):
    work=dims[0]*dims[1]*dims[2];rows=[]
    for line in text.splitlines():
        m=re.search(r"iters/s=([0-9.]+).*tmads/s=([0-9.]+).*hashes/s=([0-9.]+) TH/s",line)
        if not m:continue
        iters,tmads,hashes=map(float,m.groups());implied=iters*work/1e12
        if tmads!=hashes or abs(implied-hashes)>.02:raise ValueError("Native KRig TH/s did not match the logged matrix-iteration equation")
        rows.append({"iterations_per_second":iters,"native_TH_s":hashes,"tmads_per_second":tmads,"matrix_implied_Tmac_s":implied})
    if len(rows)<3:raise ValueError("Insufficient native unit equations")
    return rows
def analyze(root):
    krig_log=(root/"krig-trace-01/child.log").read_text(encoding="utf-8")
    dims={tuple(map(int,m)) for m in re.findall(r"buffers allocated M=(\d+) N=(\d+) K=(\d+) R=(\d+)",krig_log)}
    if len(dims)!=1:raise ValueError("KRig did not declare one stable matrix configuration")
    kd=next(iter(dims))
    if kd[3]!=128 or SOURCE_DIMS[3]!=128:raise ValueError("Rank-dependent normalization requires separate analysis")
    source=counter(root/"source-counter-01",SOURCE_DIMS[0]*SOURCE_DIMS[1]*SOURCE_DIMS[2])
    krig=counter(root/"krig-counter-01",kd[0]*kd[1]*kd[2])
    equations=krig_equations(krig_log,kd)
    source["matrix_dimensions_m_n_k_rank"]=list(SOURCE_DIMS);krig["matrix_dimensions_m_n_k_rank"]=list(kd)
    source["activity"]=capture(root/"source-trace-02",source);krig["activity"]=capture(root/"krig-trace-01",krig)
    krig["native_unit_equations"]=equations
    traced=krig["activity"]["dense_gemm_Tmac_per_wall_second"];native=statistics.mean(r["native_TH_s"] for r in equations)
    if abs(traced/native-1)>.03:raise ValueError("Independent launch-count rate did not corroborate native unit scale")
    return {"status":"passed","scope":"Pinned RTX3090 / KRig1.5.12 / source820d7f63; synthetic fixed local job. Unit calibration, not a steady or paid-hashrate benchmark.","native_KRig_TH_to_Tmac_factor":1,"factor_basis":"Native iterations times declared M*N*K equals tmads/s and TH/s; three exact hardware-operation samples per backend; independent kernel launch activity corroborates the scale.","source":source,"krig":krig,"real_pool_comparison_still_required":True,"developer_fee_percent":{"source":0,"krig_localhost_policy":3}}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",type=pathlib.Path,required=True);ap.add_argument("--output",type=pathlib.Path,required=True);a=ap.parse_args()
    result=analyze(a.root);a.output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({"status":result["status"],"native_KRig_TH_to_Tmac_factor":result["native_KRig_TH_to_Tmac_factor"],"source_operations_per_launch":result["source"]["operations_per_launch"],"krig_operations_per_launch":result["krig"]["operations_per_launch"],"source_trace_Tmac_s":result["source"]["activity"]["dense_gemm_Tmac_per_wall_second"],"krig_trace_Tmac_s":result["krig"]["activity"]["dense_gemm_Tmac_per_wall_second"],"scope":"unit calibration only; no performance winner claimed"}))
if __name__=="__main__":main()
