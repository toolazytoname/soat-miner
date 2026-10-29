"""Locale-independent GPU PID/name inspection; no GPU work or Windows API calls."""
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import run_guarded as module

class GpuProcessEncodingTests(unittest.TestCase):
    def scan(self, output, names, returncode=0):
        with patch.object(module.subprocess,"run",return_value=SimpleNamespace(returncode=returncode,stdout=output)) as run, patch.object(module,"process_names",return_value=names) as snapshot:
            result=module.gpu_processes()
            self.assertIn("--query-compute-apps=pid",run.call_args.args[0])
            self.assertFalse(run.call_args.kwargs.get("text",False))
            return result,snapshot
    def test_unicode_names_come_from_windows_snapshot(self):
        result,_=self.scan(b"101\r\n202\r\n",{101:"dwm.exe",202:"工具.exe"})
        self.assertEqual(result,{101:"dwm.exe",202:"工具.exe"})
        self.assertNotIn(result[202],module.DESKTOP_PROCESSES)
    def test_missing_pid_remains_an_unknown_client(self):
        result,_=self.scan(b"303\r\n",{})
        self.assertEqual(set(result),{303});self.assertNotIn(result[303],module.DESKTOP_PROCESSES)
    def test_empty_list_does_not_need_process_snapshot(self):
        result,snapshot=self.scan(b"\r\n",{})
        self.assertEqual(result,{});snapshot.assert_not_called()
    def test_malformed_pid_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError,"GPU process PID"):self.scan(b"bad\r\n",{})
    def test_non_ascii_pid_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError,"GPU process PID"):self.scan(b"\xff123\r\n",{})
    def test_query_error_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError,"Cannot inspect"):self.scan(b"",{},1)

if __name__=="__main__":unittest.main()
