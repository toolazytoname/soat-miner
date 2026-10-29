import datetime,json,pathlib,tempfile,unittest
from run_fast_screen import summarize,review
class FastScreenTests(unittest.TestCase):
    def fixture(self,folder,mode="normal"):
        p=pathlib.Path(folder);(p/"guard-status.json").write_text(json.dumps({"stop_reason":"duration-complete","power_restored":mode!="restore"}))
        stats=[{"timestamp_unix_ms":i*1000,"rate":50,"backend":"CUDA","unit":"TH/s" if mode=="unit" else "T MAC/s"} for i in range(0,61) if mode!="stale" or i<=20]
        (p/"child.log").write_text("\n".join(json.dumps(s) for s in stats))
        samples=[{"time":datetime.datetime.fromtimestamp(i,datetime.timezone.utc).isoformat(),"PowerLimit":220,"Power":220,"Temperature":74,"Hotspot":90,"MemoryJunction":80} for i in range(0,61,2)]
        (p/"telemetry.jsonl").write_text("\n".join(json.dumps(s) for s in samples));return p
    def test_rate_is_aligned_to_real_telemetry(self):
        with tempfile.TemporaryDirectory() as folder:
            t=summarize(self.fixture(folder))["tail"];self.assertEqual(t["time_weighted_Tmac_s"],50);self.assertEqual(t["mean_gpu_power_watts"],220)
    def test_stale_or_unknown_statistics_and_unrestored_power_fail(self):
        for mode in ["stale","unit","restore"]:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as folder:
                with self.assertRaises(ValueError):summarize(self.fixture(folder,mode))
    def test_failed_attempt_counter_cannot_be_hidden_by_a_fast_tail(self):
        with tempfile.TemporaryDirectory() as folder:
            p=self.fixture(folder)
            stats=[json.loads(v) for v in (p/"child.log").read_text().splitlines()]
            stats[40]["rejected"]=1
            (p/"child.log").write_text("\n".join(json.dumps(v) for v in stats))
            with self.assertRaisesRegex(ValueError,"failed candidate attempts"):summarize(p)
    def test_host_verification_error_rejects_legacy_zero_counter_logs(self):
        with tempfile.TemporaryDirectory() as folder:
            p=self.fixture(folder)
            with (p/"child.log").open("a") as log:
                log.write("\n"+json.dumps({"event":"error","msg":"candidate failed host verification (fixture) - NOT submitted"}))
            with self.assertRaisesRegex(ValueError,"host verification"):summarize(p)
    def cases(self,rates):return [{"name":name,"tile":name,"tail":{"time_weighted_Tmac_s":rate,"gpu_Tmac_per_joule":rate/220,"steady":True}} for name,rate in zip(["A0","C1","A1","C2","A2"],rates)]
    def test_warming_baseline_cannot_promote_a_candidate(self):
        r=review(self.cases([50,60,55,62,60]));self.assertFalse(r["baseline_controls_stable"]);self.assertIsNone(r["next_candidate"])
    def test_small_gain_and_thermal_instability_require_more_evidence(self):
        cases=self.cases([50,51,50,60,50]);cases[3]["tail"]["steady"]=False
        r=review(cases);self.assertIsNone(r["next_candidate"])
    def test_material_gain_is_only_referred_for_long_confirmation(self):
        r=review(self.cases([50,52,50,49,50]));self.assertEqual(r["next_candidate"],"C1");self.assertFalse(r["production_config_changed"])
    def test_confirmation_requires_steady_bracketing_controls(self):
        cases=self.cases([50,53,50]);cases[0]["name"]="A1";cases[1]["name"]="B";cases[2]["name"]="A2"
        r=review(cases,"confirm");self.assertTrue(r["candidate_confirmed_improvement"]);self.assertAlmostEqual(r["confirmed_rate_gain_percent"],6)
        cases[2]["tail"]["time_weighted_Tmac_s"]=55
        r=review(cases,"confirm");self.assertFalse(r["candidate_confirmed_improvement"]);self.assertIsNone(r["confirmed_rate_gain_percent"])
    def test_confirmation_rejects_a_thermal_excursion(self):
        cases=self.cases([50,60,50]);cases[0]["name"]="A1";cases[1]["name"]="B";cases[2]["name"]="A2";cases[1]["tail"]["steady"]=False
        r=review(cases,"confirm");self.assertFalse(r["comparison_valid"]);self.assertIsNone(r["confirmed_gpu_efficiency_gain_percent"])

from unittest.mock import patch
import run_fast_screen as fs
class PoolAvailabilityTests(unittest.TestCase):
    def test_transient_failure_preserves_last_success_and_continues(self):
        with patch.object(fs,"fetch",side_effect=TimeoutError("fixture")),patch.object(fs.time,"monotonic",return_value=100):
            r=fs.poll_public_pool("public-test",0)
        self.assertEqual(r["last_ok"],0);self.assertIsNone(r["stop_reason"]);self.assertIn("fixture",r["error"])
    def test_continuous_failure_stops_at_original_thirty_minute_limit(self):
        for elapsed,expected in [(1799,None),(1800,"pool_api_unavailable_30_minutes")]:
            with self.subTest(elapsed=elapsed),patch.object(fs,"fetch",side_effect=TimeoutError()),patch.object(fs.time,"monotonic",return_value=elapsed):
                self.assertEqual(fs.poll_public_pool("public-test",0)["stop_reason"],expected)
    def test_success_resets_last_success(self):
        with patch.object(fs,"fetch",return_value={"goal_reached":False}),patch.object(fs.time,"monotonic",return_value=1100):
            r=fs.poll_public_pool("public-test",0)
        self.assertEqual(r["last_ok"],1100);self.assertIsNone(r["error"]);self.assertIsNone(r["stop_reason"])
    def test_success_between_failures_prevents_accumulating_noncontinuous_outages(self):
        with patch.object(fs,"fetch",side_effect=[{"goal_reached":False},TimeoutError()]),patch.object(fs.time,"monotonic",side_effect=[1100,2500]):
            a=fs.poll_public_pool("public-test",0);b=fs.poll_public_pool("public-test",a["last_ok"])
        self.assertIsNone(b["stop_reason"]);self.assertEqual(b["last_ok"],1100)
    def test_threshold_still_stops_immediately(self):
        with patch.object(fs,"fetch",return_value={"goal_reached":True}),patch.object(fs.time,"monotonic",return_value=10):
            self.assertEqual(fs.poll_public_pool("public-test",0)["stop_reason"],"payout_threshold_accumulated")

if __name__=="__main__":unittest.main(verbosity=2)
