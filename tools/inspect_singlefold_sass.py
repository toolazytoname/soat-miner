"""Inspect compiled SM86 code only. This command never loads a GPU workload."""
import argparse,collections,datetime,hashlib,json,os,pathlib,re,subprocess
ROOT=pathlib.Path(__file__).resolve().parent.parent
PREFIX="_ZN2om5pearl12noisyGemmPtxILi2ELi4ELi4ELi2ELi64ELi2ELi8ELi1ELb1E"
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--output",type=pathlib.Path,required=True);args=ap.parse_args();out=args.output
 if out.exists() and any(out.iterdir()):raise ValueError("Use a fresh static-analysis output directory")
 out.mkdir(parents=True,exist_ok=True);receipt=json.loads(pathlib.Path("D:/Apps/CUDAInspectors/13.1.1/install-receipt.json").read_text());cu=receipt["components"][0]["binary"];env=os.environ.copy();env["PATH"]=";".join(str(pathlib.Path(x["binary"]).parent) for x in receipt["components"])+";"+env["PATH"];binary=ROOT/"build/prl3090-fold/soat-miner.exe"
 def command(name,argv):
  result=subprocess.run([cu,*argv,str(binary)],cwd=ROOT,env=env,capture_output=True,text=True,encoding="utf-8",errors="replace",creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS,timeout=30)
  (out/name).write_text(result.stdout+result.stderr,encoding="utf-8")
  if result.returncode:raise RuntimeError("Static inspection failed: "+result.stderr)
  return result.stdout
 resources=command("resources.txt",["--dump-resource-usage"]);names=re.findall(r"Function\s+([^:\s]+):",resources);kernels={}
 for kind,ending in [("generic","Lb0E"),("singlefold","Lb1E")]:
  name=next(x for x in names if x.startswith(PREFIX+ending));text=command(kind+"-sass.txt",["--dump-sass","--function",name]);instances=[]
  for block in re.split(r"\s*Function\s*:\s*[^\n]+\n",text)[1:]:
   ops=re.findall(r"/\*[0-9a-fA-F]+\*/\s*(?:@\S+\s+)?([A-Z][A-Z0-9_.]*)\s",block)
   if ops:instances.append({"static_instructions":len(ops),"opcode_counts":dict(sorted(collections.Counter(x.split('.')[0] for x in ops).items()))})
  if not instances:raise RuntimeError("No matching SASS instruction body")
  kernels[kind]={"mangled_name":name,"instances":instances}
 with binary.open("rb") as f:digest=hashlib.file_digest(f,"sha256").hexdigest()
 result={"time":datetime.datetime.now(datetime.timezone.utc).isoformat(),"scope":"Offline SASS counts, not dynamic instruction counts or performance","binary":str(binary),"binary_sha256":digest,"gpu_work":False,"kernels":kernels}
 (out/"result.json").write_text(json.dumps(result,indent=2),encoding="utf-8");print(json.dumps(result,indent=2))
if __name__=="__main__":main()
