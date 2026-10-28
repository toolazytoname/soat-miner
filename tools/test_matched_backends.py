import math,unittest
from analyze_matched_backends import weighted_window,validate_window_units,measurement_start
def row(epoch,rate,core=74):
    return {"Epoch":epoch,"ReportedRate":rate,"Gpu":{"PowerLimit":220,"Power":220 if rate else 8,"Temperature":core,"Hotspot":90,"MemoryJunction":80}}
class WeightedBenchmark(unittest.TestCase):
    def test_uninitialized_startup_units_are_outside_the_tail(self):
        rows=[dict(row(i,60),ReportedRateUnit="T MAC/s") for i in range(0,201,5)]
        rows[0].pop("ReportedRateUnit")
        validate_window_units(rows,"T MAC/s")
    def test_unknown_units_inside_tail_are_rejected(self):
        rows=[dict(row(i,60),ReportedRateUnit="T MAC/s") for i in range(0,201,5)]
        rows[-2].pop("ReportedRateUnit")
        with self.assertRaises(ValueError):validate_window_units(rows,"T MAC/s")
    def test_intentional_cooldown_is_not_counted_as_mining_time(self):
        session={"StartTime":"1970-01-01T00:01:40+00:00"}
        self.assertEqual(measurement_start({"analysis_anchor":"first_selected_profile_epoch"},session,[row(300,0)]),300)
    def test_legacy_round_keeps_its_recorded_anchor(self):
        session={"StartTime":"1970-01-01T00:01:40+00:00"}
        self.assertEqual(measurement_start({},session,[row(300,0)]),100)
    def test_waiting_time_is_included_in_wall_throughput(self):
        rows=[row(i,0 if i<10 else 60) for i in range(0,21,5)]
        result=weighted_window(rows,20)
        self.assertEqual(result["time_weighted_Tmac_s"],30);self.assertEqual(result["active_time_weighted_Tmac_s"],60);self.assertEqual(result["idle_wall_seconds"],10)
    def test_unequal_sampling_is_time_weighted(self):
        result=weighted_window([row(0,40),row(1,60),row(10,60)],10)
        self.assertEqual(result["time_weighted_Tmac_s"],58)
    def test_missing_gap_is_not_filled_with_old_rate(self):
        with self.assertRaises(ValueError):weighted_window([row(0,40),row(16,60),row(20,60)],20)
    def test_nonfinite_or_changed_power_is_rejected(self):
        for key,value in [("ReportedRate",float("nan")),("PowerLimit",370)]:
            rows=[row(0,60),row(10,60),row(20,60)]
            if key=="PowerLimit":rows[1]["Gpu"][key]=value
            else:rows[1][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):weighted_window(rows,20)
    def test_stop_latency_does_not_move_the_planned_measurement_window(self):
        rows=[row(i,60) for i in range(0,31,5)]+[row(35,0,61),row(40,0,60)]
        result=weighted_window(rows,20,end_epoch=30)
        self.assertEqual(result["time_weighted_Tmac_s"],60);self.assertTrue(result["steady"])
    def test_measurement_end_requires_real_coverage(self):
        with self.assertRaises(ValueError):weighted_window([row(0,60),row(10,60),row(20,60)],20,end_epoch=25)
    def test_thermal_drift_does_not_pass_as_steady(self):
        result=weighted_window([row(0,60,70),row(10,60,74),row(20,60,75)],20)
        self.assertFalse(result["steady"])
if __name__=="__main__":unittest.main()
