from pathlib import Path
import csv, hashlib,sys
root=Path(__file__).resolve().parents[1]/'01_本对话全部文件'
csv_path=Path(__file__).parent/'UPDATED_ALL_FILES_SHA256.csv'
errors=[]
with csv_path.open(encoding='utf-8-sig',newline='') as f:
 for row in csv.DictReader(f):
  p=root/row['relative_path']
  if not p.is_file():errors.append('MISSING '+str(p));continue
  h=hashlib.sha256()
  with p.open('rb') as r:
   for b in iter(lambda:r.read(4*1024*1024),b''):h.update(b)
  if h.hexdigest()!=row['sha256']:errors.append('HASH_FAIL '+str(p))
print('Errors:',len(errors))
for e in errors:print(e)
sys.exit(bool(errors))
