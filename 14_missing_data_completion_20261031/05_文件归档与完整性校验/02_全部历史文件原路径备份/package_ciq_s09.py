import csv,hashlib,json,zipfile
from pathlib import Path
root=Path('/mnt/data/CIQ_V5_S09_Aircraft_Mission_Preflight_20261030')
filename=Path('/mnt/data/CIQ_V5_S07_S09_Real_Task_Screen_and_Energy_Model_20261030.zip')
files=sorted(x for x in root.rglob('*') if x.is_file() and '__pycache__' not in x.parts and not x.name.endswith('.pyc') and x.name!='SHA256_MANIFEST.csv')
manifest=root/'SHA256_MANIFEST.csv'
with manifest.open('w',encoding='utf-8-sig',newline='') as o:
 w=csv.writer(o);w.writerow(['relative_path','size_bytes','sha256'])
 for f in files:
  w.writerow([f.relative_to(root).as_posix(),f.stat().st_size,hashlib.sha256(f.read_bytes()).hexdigest()])
with zipfile.ZipFile(filename,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
 for f in files+[manifest]:z.write(f,arcname=f'{root.name}/{f.relative_to(root).as_posix()}')
with zipfile.ZipFile(filename) as z:
 assert z.testzip() is None
 assert len(z.namelist())==len(files)+1
 for f in files:
  actual=hashlib.sha256(z.read(f'{root.name}/{f.relative_to(root).as_posix()}')).hexdigest()
  assert actual==hashlib.sha256(f.read_bytes()).hexdigest()
print(json.dumps({'zip':str(filename),'size_bytes':filename.stat().st_size,'content_files':len(files)+1,'zip_sha256':hashlib.sha256(filename.read_bytes()).hexdigest()},indent=2))
