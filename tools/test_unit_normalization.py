"""Fail-closed parser and physical-work normalization checks; no GPU."""
import json,pathlib,tempfile,unittest
from analyze_unit_calibration import geometry,operations,krig_equations,capture
class UnitNormalization(unittest.TestCase):
    def test_exact_large_integer_counter(self):
        self.assertEqual(operations("2,199,023,255,552"),2*4096*65536*4096)
    def test_invalid_counter_is_not_silently_zero(self):
        for value in ["N/A","NaN","Infinity","0","-1","1.5"]:
            with self.subTest(value=value),self.assertRaises((ValueError,ArithmeticError)):operations(value)
    def test_geometry_requires_all_three_positive_axes(self):
        self.assertEqual(geometry("(32, 512, 1)"),(32,512,1))
        for value in ["32,512","(0,512,1)","(-1,512,1)","abc(32,512,1)",""]:
            with self.subTest(value=value),self.assertRaises(ValueError):geometry(value)
    def test_native_equation_uses_declared_matrix_work(self):
        line="iters/s=59.69 iter_ms=16.8 tmads/s=65.63 hashes/s=65.63 TH/s"
        rows=krig_equations("\n".join([line]*3),(4096,65536,4096,128))
        self.assertAlmostEqual(rows[0]["matrix_implied_Tmac_s"],65.62984906194944)
    def fixture_capture(self,folder,conflict_in_window=False):
        run=pathlib.Path(folder)
        (run/"status.json").write_text(json.dumps({"status":"complete","power_restored":True,"owned_root_pid":17}))
        events=[{"event":"trace_start","cupti_ns":100_000_000_000,"pid":17},
                {"event":"kernel","name":"gemm","start_ns":102_000_000_000 if not conflict_in_window else 110_000_000_000,"end_ns":102_001_000_000 if not conflict_in_window else 110_001_000_000,"grid":[2,1,1],"block":[128,1,1]},
                {"event":"kernel","name":"gemm","start_ns":120_000_000_000,"end_ns":120_001_000_000,"grid":[32,512,1],"block":[128,1,1]},
                {"event":"trace_end","cupti_ns":130_000_000_000,"kernels":2,"errors":0,"dropped":0}]
        (run/"launches.jsonl").write_text("\n".join(json.dumps(e) for e in events))
        return run,{"kernel":"gemm","grid":[32,512,1],"block":[128,1,1],"macs_per_launch":4096*65536*4096}
    def test_tiny_initial_selfcheck_is_outside_measurement_window(self):
        with tempfile.TemporaryDirectory() as folder:
            run,profile=self.fixture_capture(folder)
            self.assertEqual(capture(run,profile)["complete_gemm_launches"],1)
    def test_geometry_change_inside_window_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            run,profile=self.fixture_capture(folder,True)
            with self.assertRaises(ValueError):capture(run,profile)
    def test_falsely_doubled_native_unit_is_rejected(self):
        line="iters/s=59.69 tmads/s=131.26 hashes/s=131.26 TH/s"
        with self.assertRaises(ValueError):krig_equations("\n".join([line]*3),(4096,65536,4096,128))
if __name__=="__main__":unittest.main()
