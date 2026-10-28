"""Windows-only ownership for a profiler plus every inherited child.
Create suspended, assign to a kill-on-close Job Object, then resume. No breakaway.
References: Microsoft CreateProcessW / AssignProcessToJobObject / nested jobs.
"""
import ctypes as c
from ctypes import wintypes as w
import msvcrt,os,pathlib,subprocess,time
class BasicLimit(c.Structure):
 _fields_=[("processTime",c.c_longlong),("jobTime",c.c_longlong),("flags",w.DWORD),("minWorking",c.c_size_t),("maxWorking",c.c_size_t),("activeLimit",w.DWORD),("affinity",c.c_size_t),("priority",w.DWORD),("scheduling",w.DWORD)]
class Io(c.Structure):_fields_=[(n,c.c_ulonglong) for n in ["readOps","writeOps","otherOps","readBytes","writeBytes","otherBytes"]]
class ExtendedLimit(c.Structure):
 _fields_=[("basic",BasicLimit),("io",Io),("processMemory",c.c_size_t),("jobMemory",c.c_size_t),("peakProcessMemory",c.c_size_t),("peakJobMemory",c.c_size_t)]
class Accounting(c.Structure):
 _fields_=[(n,c.c_longlong) for n in ["user","kernel","periodUser","periodKernel"]]+[(n,w.DWORD) for n in ["faults","total","active","terminated"]]
class Startup(c.Structure):
 _fields_=[("cb",w.DWORD),("reserved",w.LPWSTR),("desktop",w.LPWSTR),("title",w.LPWSTR)]+[(n,w.DWORD) for n in ["x","y","xSize","ySize","xChars","yChars","fill","flags"]]+[("show",w.WORD),("reserved2size",w.WORD),("reserved2",c.POINTER(c.c_byte)),("stdin",w.HANDLE),("stdout",w.HANDLE),("stderr",w.HANDLE)]
class ProcessInfo(c.Structure):_fields_=[("process",w.HANDLE),("thread",w.HANDLE),("pid",w.DWORD),("tid",w.DWORD)]
K=c.WinDLL("kernel32",use_last_error=True)
def api(name,args,ret=w.BOOL):
 f=getattr(K,name);f.argtypes=args;f.restype=ret;return f
CreateJob=api("CreateJobObjectW",[c.c_void_p,w.LPCWSTR],w.HANDLE)
SetJob=api("SetInformationJobObject",[w.HANDLE,c.c_int,c.c_void_p,w.DWORD])
QueryJob=api("QueryInformationJobObject",[w.HANDLE,c.c_int,c.c_void_p,w.DWORD,c.POINTER(w.DWORD)])
Assign=api("AssignProcessToJobObject",[w.HANDLE,w.HANDLE])
TerminateJob=api("TerminateJobObject",[w.HANDLE,w.UINT])
Close=api("CloseHandle",[w.HANDLE]);Resume=api("ResumeThread",[w.HANDLE],w.DWORD)
CreateProcess=api("CreateProcessW",[w.LPCWSTR,w.LPWSTR,c.c_void_p,c.c_void_p,w.BOOL,w.DWORD,c.c_void_p,w.LPCWSTR,c.POINTER(Startup),c.POINTER(ProcessInfo)])
TerminateProcess=api("TerminateProcess",[w.HANDLE,w.UINT]);Wait=api("WaitForSingleObject",[w.HANDLE,w.DWORD],w.DWORD)
ExitCode=api("GetExitCodeProcess",[w.HANDLE,c.POINTER(w.DWORD)])
OpenProcess=api("OpenProcess",[w.DWORD,w.BOOL,w.DWORD],w.HANDLE)
IsInJob=api("IsProcessInJob",[w.HANDLE,w.HANDLE,c.POINTER(w.BOOL)])
def ck(value):
 if not value:raise c.WinError(c.get_last_error())
 return value
class OwnedJob:
 def __init__(self,command,log_path,cwd=None,env=None):
  self.job=None;self.process=None;self.pid=None
  self.job=ck(CreateJob(None,None));limit=ExtendedLimit();limit.basic.flags=0x2000
  try:
   ck(SetJob(self.job,9,c.byref(limit),c.sizeof(limit)))
   with open(log_path,"wb") as out,open(os.devnull,"rb") as inp:
    oh=msvcrt.get_osfhandle(out.fileno());ih=msvcrt.get_osfhandle(inp.fileno())
    os.set_handle_inheritable(oh,True);os.set_handle_inheritable(ih,True)
    startup=Startup();startup.cb=c.sizeof(startup);startup.flags=0x100;startup.stdin=ih;startup.stdout=oh;startup.stderr=oh
    info=ProcessInfo();cmd=c.create_unicode_buffer(subprocess.list2cmdline([str(x) for x in command]));environment=c.create_unicode_buffer("\0".join(k+"="+v for k,v in sorted((env or os.environ).items()))+"\0\0")
    try:ck(CreateProcess(str(command[0]),cmd,None,None,True,0x4|0x4000|0x08000000|0x400,environment,str(cwd) if cwd else None,c.byref(startup),c.byref(info)))
    finally:os.set_handle_inheritable(oh,False);os.set_handle_inheritable(ih,False)
    self.process=info.process;self.pid=int(info.pid)
    try:
     ck(Assign(self.job,self.process))
     if Resume(info.thread)==0xffffffff:raise c.WinError(c.get_last_error())
    except BaseException:TerminateProcess(self.process,1);Wait(self.process,5000);raise
    finally:Close(info.thread)
  except BaseException:self.close();raise
 def active_count(self):
  a=Accounting();ck(QueryJob(self.job,1,c.byref(a),c.sizeof(a),None));return int(a.active)
 def contains(self,pid):
  h=OpenProcess(0x1000,False,int(pid))
  if not h:return False
  try:b=w.BOOL();ck(IsInJob(h,self.job,c.byref(b)));return bool(b.value)
  finally:Close(h)
 def poll(self):
  if Wait(self.process,0)==258:return None
  code=w.DWORD();ck(ExitCode(self.process,c.byref(code)));return int(code.value)
 def stop(self):
  if self.active_count():ck(TerminateJob(self.job,1))
  end=time.monotonic()+10
  while self.active_count() and time.monotonic()<end:time.sleep(.05)
  if self.active_count():raise RuntimeError("Owned job children did not exit")
  if self.process and Wait(self.process,5000)==258:raise RuntimeError("Owned parent process has not finished exit")
 def close(self):
  try:
   if self.job:self.stop()
  finally:
   if self.process:Close(self.process);self.process=None
   if self.job:Close(self.job);self.job=None
 def __enter__(self):return self
 def __exit__(self,*unused):self.close()
