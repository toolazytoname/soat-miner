# Copyright (c) 2026 toolazytoname. MIT; see ../LICENSE.
"""Read GPU telemetry through the installed NVIDIA driver; no extra drivers.
Thermal ABI/RTX30 indices: LibreHardwareMonitorLib/Interop/NvApi.cs and
Hardware/Gpu/NvidiaGpu.cs in https://github.com/LibreHardwareMonitor/LibreHardwareMonitor.
Only NVAPI Initialize, EnumPhysicalGPUs, GetThermalSensors are called (read-only).
Power changes use NVIDIA's documented nvidia-smi interface.
"""
import ctypes as c, subprocess, json, time
SMI='C:/Windows/System32/nvidia-smi.exe'
class Thermal(c.Structure):
 _pack_=8
 _fields_=[('version',c.c_uint32),('mask',c.c_uint32),('reserved',c.c_int32*8),('temperatures',c.c_int32*32)]
class Gpu:
 def __init__(self):
  self.lib=c.WinDLL('C:/Windows/System32/nvapi64.dll');self.query=self.lib.nvapi_QueryInterface
  self.query.argtypes=[c.c_uint32];self.query.restype=c.c_void_p
  if self.fn(0x0150E828,[])()!=0:raise RuntimeError('NVAPI initialization failed')
  handles=(c.c_void_p*64)();n=c.c_int()
  if self.fn(0xE5AC921F,[c.POINTER(c.c_void_p),c.POINTER(c.c_int)])(handles,c.byref(n))!=0 or n.value!=1:raise RuntimeError('Expected one NVIDIA GPU')
  self.handle=handles[0];self.thermal=self.fn(0x65FE3AAD,[c.c_void_p,c.POINTER(Thermal)]);self.mask=0
  for b in range(32):
   t=Thermal();t.version=c.sizeof(Thermal)|(2<<16);t.mask=1<<b
   if self.thermal(self.handle,c.byref(t))!=0:break
   self.mask|=1<<b
  if not self.mask&512:raise RuntimeError('Memory junction sensor is not supported')
 def fn(self,ident,args):
  p=self.query(ident)
  if not p:raise RuntimeError('NVAPI interface not available')
  return c.CFUNCTYPE(c.c_int,*args)(p)
 def read(self):
  fields='power.limit,temperature.gpu,power.draw,utilization.gpu,memory.used,fan.speed,clocks.gr,clocks.mem'
  r=subprocess.run([SMI,'--query-gpu='+fields,'--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=8,creationflags=subprocess.CREATE_NO_WINDOW)
  if r.returncode:raise RuntimeError('NVIDIA telemetry unavailable')
  v=[x.strip() for x in r.stdout.strip().split(',')]
  if len(v)!=8:raise RuntimeError('Unexpected GPU telemetry layout')
  t=Thermal();t.version=c.sizeof(Thermal)|(2<<16);t.mask=self.mask
  if self.thermal(self.handle,c.byref(t))!=0:raise RuntimeError('NVAPI temperature read failed')
  values=[x/256 for x in t.temperatures]
  for i in [0,1,9]:
   if not 5<values[i]<140:raise RuntimeError('Invalid temperature sensor value')
  if abs(values[0]-float(v[1]))>10:raise RuntimeError('GPU temperature cross-check failed')
  return {'PowerLimit':float(v[0]),'Temperature':float(v[1]),'Power':float(v[2]),'Utilization':float(v[3]),'MemoryMiB':float(v[4]),'FanPercent':float(v[5]) if v[5]!='[N/A]' else None,'CoreClockMHz':float(v[6]),'MemoryClockMHz':float(v[7]),'Hotspot':round(values[1],2),'MemoryJunction':round(values[9],2),'NvapiCore':round(values[0],2)}
 def power(self,watts):
  r=subprocess.run([SMI,'-i','0','-pl',str(watts)],capture_output=True,text=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
  if r.returncode:raise RuntimeError('GPU power change failed: '+r.stdout+r.stderr)
  got=self.read()['PowerLimit']
  if abs(got-watts)>1:raise RuntimeError('GPU power read-back mismatch')
if __name__=='__main__':print(json.dumps(Gpu().read()))
