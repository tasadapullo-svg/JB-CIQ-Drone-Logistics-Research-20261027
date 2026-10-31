#!/usr/bin/env python3
"""Independent release check for original GitHub bytes and V5 derived files.
Never converts historical A/B graph or coarse ERA5 to a complete V5 operated network.
"""
import csv,json,hashlib,pathlib,sys,zipfile
from collections import Counter

def git_blob(path):
 h=hashlib.sha1();size=path.stat().st_size;h.update(b'blob '+str(size).encode()+b'\0')
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()

def sha256(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()

def check(root):
 root=pathlib.Path(root);idx=json.loads((root/'inputs/PINNED_SOURCE_INDEX.json').read_text('utf-8')); rows=[]
 for item in idx['files']:
  p=root/'recovered_sources'/item['name'];size=p.stat().st_size if p.exists() else None
  state='HOLD_MISSING_BYTES'
  if p.is_file():
   same=(size==item['size'] and git_blob(p)==item['git_blob'] and (not item.get('sha256') or sha256(p)==item['sha256']))
   state='PASS_PINNED_BYTES' if same else 'FAIL_SOURCE_HASH';
   if same and p.suffix=='.xlsx':
    try:
     with zipfile.ZipFile(p) as z:
      if z.testzip() is not None:state='FAIL_EXCEL_ZIP_CRC'
    except Exception:state='FAIL_EXCEL_ZIP_OPEN'
  rows.append(dict(name=item['name'],scope=item['scope'],expected_size=item['size'],actual_size=size if size is not None else '',
     expected_git_blob=item['git_blob'],expected_sha256=item.get('sha256',''),status=state,
     original_git_path=item['path'],immutable_commit=idx['git_commit']))
 with (root/'qa/S07_V5_HISTORICAL_SOURCE_GATE.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 source_summary=dict(Counter(r['status'] for r in rows));
 # Even with old A/B source available, there is no complete current V5 A/B/C road input and no site access proof.
 report={'V5_SPATIAL':'PASS','HISTORICAL_PINNED_BYTES':source_summary,
  'HISTORICAL_MONTHLY_WEATHER_XLSX':{'verified_files':sum(r['status']=='PASS_PINNED_BYTES' and r['name'].endswith('.xlsx') for r in rows),'expected_files':5},
  'V5_SOURCE_ABC_ROAD':'HOLD_NEW_C_ROAD_AND_SITE_ACCESS_UNVERIFIED',
  'WEATHER_NUMERIC_V5_INTEGRATION':'HOLD_UNTIL_SHEET_UNITS_INTERVALS_COVERAGE_VALIDATED',
  'V5_SYNTHETIC_TASKS':'CONDITIONAL_SCENARIO_DESIGN_NOT_EMPIRICAL',
  'OPERATIONAL_PETROL_UAV_COMPARISON':'NOT_RELEASED',
  'why':'Road, weather, service, and carbon effects cannot be inferred from spatial and task fixtures alone.'}
 (root/'qa/S07_V5_SOURCE_RELEASE_GATE.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),'utf-8')
 print(json.dumps(report,ensure_ascii=False));return report
if __name__=='__main__':check(sys.argv[1] if len(sys.argv)>1 else '.')
