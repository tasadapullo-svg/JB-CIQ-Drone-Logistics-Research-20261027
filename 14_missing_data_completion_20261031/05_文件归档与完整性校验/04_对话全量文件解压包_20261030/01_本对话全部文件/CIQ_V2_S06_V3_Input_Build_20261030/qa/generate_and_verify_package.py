from pathlib import Path
import csv,hashlib,io,json,zipfile
root=Path(__file__).resolve().parents[1]
final=Path('/mnt/data/CIQ_V2_S06_V3_Frozen_Reference_Inputs_and_Audit_20261030.zip')
files=sorted([p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ('S06_PACKAGE_SHA256_MANIFEST.csv','package_integrity_check.json')])
manifest=root/'qa/S06_PACKAGE_SHA256_MANIFEST.csv'
with manifest.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['file','sha256','bytes'])
 for p in files:w.writerow([p.relative_to(root).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_size])
with zipfile.ZipFile(final,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
 for p in sorted(root.rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and p.name!='package_integrity_check.json':z.write(p,p.relative_to(root).as_posix())
with zipfile.ZipFile(final) as z:
 assert z.testzip() is None
 assert len(set(z.namelist()))==len(z.namelist())
 rows=list(csv.DictReader(io.StringIO(z.read('qa/S06_PACKAGE_SHA256_MANIFEST.csv').decode('utf-8-sig'))))
 for r in rows:
  b=z.read(r['file']);assert hashlib.sha256(b).hexdigest()==r['sha256'];assert len(b)==int(r['bytes'])
 d={'zip_name':final.name,'zip_size_bytes':final.stat().st_size,'zip_sha256':hashlib.sha256(final.read_bytes()).hexdigest(),'zip_file_count':len(z.namelist()),'manifest_hash_matches':len(rows),'zip_crc':'PASS','all_sha256':'PASS','contains_original_uploaded_V3': 'inputs/CIQ_ABC_QGIS322_NEW_COMPLETE_PROJECT_ALL_FILES_V3.zip' in z.namelist()}
Path('/mnt/data/CIQ_V2_S06_V3_package_integrity_check_20261030.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(d,indent=2))
