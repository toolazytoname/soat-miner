"""Install official pinned static CUDA binary inspection tools; no GPU/driver work."""
import datetime,hashlib,json,pathlib,shutil,subprocess,urllib.request,zipfile
BASE="https://developer.download.nvidia.com/compute/cuda/redist/"
MANIFEST=BASE+"redistrib_13.1.1.json"
def main():
 root=pathlib.Path("D:/Apps/CUDAInspectors/13.1.1");downloads=pathlib.Path("D:/Downloads/Installers/CUDA/13.1.1");downloads.mkdir(parents=True,exist_ok=True)
 if root.exists():raise RuntimeError("Inspector install already exists; inspect its receipt instead of overlaying it")
 if shutil.disk_usage(downloads).free<300*1024**2:raise RuntimeError("Insufficient D: space")
 with urllib.request.urlopen(MANIFEST,timeout=30) as r:data=json.load(r)
 receipts=[]
 for name,exe in [("cuda_cuobjdump","cuobjdump.exe"),("cuda_nvdisasm","nvdisasm.exe")]:
  component=data[name];item=component["windows-x86_64"];url=BASE+item["relative_path"];archive=downloads/pathlib.Path(item["relative_path"]).name
  if not archive.exists():
   partial=archive.with_suffix(archive.suffix+".part")
   with urllib.request.urlopen(url,timeout=30) as r,partial.open("wb") as f:shutil.copyfileobj(r,f)
   partial.replace(archive)
  with archive.open("rb") as f:digest=hashlib.file_digest(f,"sha256").hexdigest()
  if digest!=item["sha256"] or archive.stat().st_size!=int(item["size"]):raise RuntimeError("Official archive checksum/size mismatch")
  dest=root/name;dest.mkdir(parents=True)
  with zipfile.ZipFile(archive) as z:
   entries=z.infolist();prefix=entries[0].filename.split("/")[0]+"/"
   for e in entries:
    if not e.filename.startswith(prefix):raise RuntimeError("Unexpected archive structure")
    relative=e.filename[len(prefix):]
    if not relative:continue
    target=(dest/relative).resolve()
    if not target.is_relative_to(dest.resolve()) or (e.external_attr>>16)&0o170000==0o120000:raise RuntimeError("Unsafe archive member")
    if e.is_dir():target.mkdir(parents=True,exist_ok=True);continue
    target.parent.mkdir(parents=True,exist_ok=True)
    with z.open(e) as source,target.open("wb") as out:shutil.copyfileobj(source,out)
  binary=dest/"bin"/exe
  result=subprocess.run([str(binary),"--version"],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=30)
  if result.returncode:raise RuntimeError("Static inspector version check failed")
  receipts.append({"component":name,"version":component["version"],"archive_url":url,"archive":str(archive),"sha256":digest,"binary":str(binary),"version_output":result.stdout,"license":component["license"]})
 receipt={"installed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"manifest_url":MANIFEST,"components":receipts,"driver_change":False,"path_change":False,"gpu_work":False}
 (root/"install-receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8");print(json.dumps(receipt,indent=2))
if __name__=="__main__":main()
