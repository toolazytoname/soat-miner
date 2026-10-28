"""Pure accounting/deadline checks; no real wallet or network access."""
import json,os,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from payout_policy import interpret,remaining_seconds
class PolicyTests(unittest.TestCase):
    def balance(self,total='0.9',confirmed='0',pending=None,threshold='1'):
        return dict(total=total,confirmed=confirmed,unconfirmed=pending if pending is not None else total,threshold=threshold)
    def test_below_exact_and_above_pending_threshold(self):
        for total,want in [('0.99999999',False),('1',True),('1.1',True)]:
            self.assertEqual(interpret(self.balance(total),{'count':0})['goal_reached'],want)
    def test_recorded_payout_stops_even_after_balance_resets(self):
        self.assertTrue(interpret(self.balance('0'),{'count':1})['goal_reached'])
    def test_custom_threshold_is_used(self):
        self.assertFalse(interpret(self.balance('1',threshold='2'),{'count':0})['goal_reached'])
    def test_bad_accounting_never_enables_work(self):
        for balance in [self.balance('NaN'),self.balance('-1'),self.balance('1',pending='0'),self.balance('0',threshold='0')]:
            with self.assertRaises(ValueError):interpret(balance,{'count':0})
        with self.assertRaises(ValueError):interpret(self.balance(),{'count':True})
    def test_resume_keeps_original_deadline_and_expiry(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('PEARL_GUARD_TEST_ROOT')) as d:
            p=Path(d)/'previous.json';p.write_text(json.dumps({'MiningDeadline':'2026-10-30T06:52:36+08:00'}))
            self.assertEqual(remaining_seconds(p,datetime(2026,10,29,22,51,36,tzinfo=timezone.utc)),60)
            self.assertEqual(remaining_seconds(p,datetime(2026,10,29,22,53,tzinfo=timezone.utc)),0)
    def test_naive_deadline_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('PEARL_GUARD_TEST_ROOT')) as d:
            p=Path(d)/'previous.json';p.write_text(json.dumps({'MiningDeadline':'2026-10-30T06:52:36'}))
            with self.assertRaises(ValueError):remaining_seconds(p)
if __name__=='__main__':unittest.main(verbosity=2)
