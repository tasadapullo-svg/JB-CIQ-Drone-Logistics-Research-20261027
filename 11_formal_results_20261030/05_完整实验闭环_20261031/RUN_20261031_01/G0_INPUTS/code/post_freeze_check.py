import hashlib
from pathlib import Path
import pandas as pd

run=Path(__file__).resolve().parents[2]
p=run/"G0_INPUTS"/"G0_FREEZE_HASH_AUDIT.csv"
d=pd.read_csv(p)
def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
 return h.hexdigest()
d["exists_after"]=d.absolute_path.map(lambda x:Path(x).exists())
d["sha256_after"]=d.apply(lambda r:sha(r.absolute_path) if r.exists_after else "",axis=1)
d["unchanged"]=d.sha256==d.sha256_after
d.to_csv(run/"G0_INPUTS"/"G0_FREEZE_HASH_POSTCHECK.csv",index=False)
print({"files":len(d),"unchanged":int(d.unchanged.sum()),"all_unchanged":bool(d.unchanged.all())})
