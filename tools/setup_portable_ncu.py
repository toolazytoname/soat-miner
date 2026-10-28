"""Fetch the SHA-256 pinned official CUDA redist Nsight Compute ZIP only.
No MSI, driver installation, registry edits, PATH edits or GPU profiling.
"""
import argparse,datetime,hashlib,json,pathlib,shutil,subprocess,urllib.request,zipfile
MANIFEST="https://developer.download.nvidia.com/compute/cuda/redist/redistrib_13.1.1.json"
BASE="https://developer.download.nvidia.com/compute/cuda/redist/"
def main():
 p=argparse.ArgumentParser();p.add_argument("--downloads",type=pathlib.Path,default=pathlib.Path("D:/Downloads/Installers/NsightCompute"));p.add_argument("--apps",type=pathlib.Path,default=pathlib.Path("D:/Apps/NsightCompute"));a=p.parse_args()
 with urllib.request.urlopen(MANIFEST,timeout=30) as response:manifest=json.load(response)
 component=manifest["nsight_compute"];version=component["version"];item=component["windows-x86_64"];url=BASE+item["relative_path"];dest=a.apps/version;downloads=a.downloads/version;downloads.mkdir(parents=True,exist_ok=True)
 if shutil.disk_usage(downloads).free<int(item["size"])*5:raise RuntimeError("Insufficient disk space")
 archive=downloads/pathlib.Path(item["relative_path"]).name
 if not archive.exists():
  partial=archive.with_suffix(archive.suffix+".part")
  with urllib.request.urlopen(url,timeout=60) as response,partial.open("wb") as out:shutil.copyfileobj(response,out,1024*1024)
  partial.replace(archive)
 with archive.open("rb") as source:digest=hashlib.file_digest(source,"sha256").hexdigest()
 if digest!=item["sha256"]:raise RuntimeError("Official archive SHA-256 mismatch; not extracting")
 if archive.stat().st_size!=int(item["size"]):raise RuntimeError("Official archive size mismatch")
 if dest.exists():raise RuntimeError("Destination already exists; inspect receipt instead of overlaying tools")
 dest.mkdir(parents=True)
 with zipfile.ZipFile(archive) as z:
  members=z.infolist();prefix=members[0].filename.split("/")[0]+"/"
  if not all(m.filename.startswith(prefix) for m in members):raise RuntimeError("Unexpected archive layout")
  for m in members:
   relative=m.filename[len(prefix):]
   if not relative:continue
   target=(dest/relative).resolve()
   if not target.is_relative_to(dest.resolve()) or (m.external_attr>>16)&0o170000==0o120000:raise RuntimeError("Unsafe archive member")
   if m.is_dir():target.mkdir(parents=True,exist_ok=True);continue
   target.parent.mkdir(parents=True,exist_ok=True)
   with z.open(m) as source,target.open("wb") as out:shutil.copyfileobj(source,out)
 ncu=dest/"ncu.exe"
 if not ncu.is_file():
  found=list(dest.glob("**/ncu.exe"))
  if len(found)!=1:raise RuntimeError("Cannot locate unique portable CLI")
  ncu=found[0]
 result=subprocess.run([str(ncu),"--version"],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=30)
 if result.returncode:raise RuntimeError("CLI version check failed: "+result.stderr)
 receipt={"installed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"manifest_url":MANIFEST,"component":"nsight_compute","version":version,"archive_url":url,"archive":str(archive),"sha256":digest,"size":archive.stat().st_size,"directory":str(dest),"ncu":str(ncu),"version_output":result.stdout,"driver_install":False,"registry_change":False,"path_change":False,"profile_started":False,"license":component["license"],"license_url":BASE+component["license_path"]}
 (dest/"install-receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8");(downloads/"official-component.json").write_text(json.dumps(component,indent=2),encoding="utf-8");print(json.dumps(receipt,indent=2))
if __name__=="__main__":main()
