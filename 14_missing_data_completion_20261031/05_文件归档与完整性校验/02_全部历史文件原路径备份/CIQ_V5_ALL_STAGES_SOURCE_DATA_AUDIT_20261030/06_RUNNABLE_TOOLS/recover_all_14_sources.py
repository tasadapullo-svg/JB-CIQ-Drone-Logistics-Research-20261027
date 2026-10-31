#!/usr/bin/env python3
"""Recover pinned GitHub sources from a local GitHub checkout or GitHub raw; no fabricated output.
Windows examples:
 python 06_RUNNABLE_TOOLS/recover_all_14_sources.py --repo-root "C:/Users/DELL/source/JB-CIQ-Drone-Logistics-Research-20261027"
 python 06_RUNNABLE_TOOLS/recover_all_14_sources.py --download
"""
from pathlib import Path
import argparse,json,csv,hashlib,urllib.request,shutil
ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'04_SOURCE_RECOVERY_AND_GITHUB_INVENTORY/SOURCE_FILES_PINNED_14.json'
REPO='tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027'
def digest(path,alg):
 h=hashlib.new(alg); size=path.stat().st_size
 if alg=='sha1':h.update(f'blob {size}\0'.encode())
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root');ap.add_argument('--download',action='store_true');ap.add_argument('--out',default=str(ROOT/'RECOVERED_GITHUB_DATA'));a=ap.parse_args()
 idx=json.loads(INDEX.read_text('utf-8'));base=Path(a.out);base.mkdir(parents=True,exist_ok=True)
 logs=[]
 for x in idx['files']:
  dest=base/x['path'];dest.parent.mkdir(parents=True,exist_ok=True)
  status='HOLD_NOT_PRESENT';error=''
  if a.repo_root:
   src=Path(a.repo_root)/x['path']
   if src.exists() and not dest.exists():shutil.copy2(src,dest)
  elif a.download and not dest.exists():
   url=f'https://raw.githubusercontent.com/{REPO}/{idx["git_commit"]}/{x["path"]}'
   try:
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CIQ-v5-S07-audit'}),timeout=90) as rd, dest.with_suffix(dest.suffix+'.tmp').open('wb') as w:shutil.copyfileobj(rd,w)
    dest.with_suffix(dest.suffix+'.tmp').replace(dest)
   except Exception as e:
    error=str(e);dest.with_suffix(dest.suffix+'.tmp').unlink(missing_ok=True)
  actual='';sha256=''
  if dest.exists():
   try:
    actual=digest(dest,'sha1');sha256=digest(dest,'sha256')
    good=(dest.stat().st_size==x['size'] and actual==x['git_blob'] and (not x.get('sha256') or sha256==x['sha256']))
    if good and dest.suffix.lower() in {'.xlsx','.zip'}:
     import zipfile
     try:
      with zipfile.ZipFile(dest) as z:good=z.testzip() is None
     except Exception:good=False
    status='PASS_BYTES_HASH' if good else 'FAIL_VERSION_OR_INTEGRITY'
   except Exception as e:status='FAIL_READ';error=str(e)
  logs.append({'file':x['name'],'status':status,'expected_blob':x['git_blob'],'actual_blob':actual,'actual_sha256':sha256,'error':error})
 logdir=ROOT/'05_AUDIT_REPORTS_AND_TEST_LOGS';logdir.mkdir(exist_ok=True)
 (logdir/'SOURCE_RECOVERY_LATEST.json').write_text(json.dumps(logs,indent=2,ensure_ascii=False),'utf-8')
 with (logdir/'SOURCE_RECOVERY_LATEST.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(logs[0]));w.writeheader();w.writerows(logs)
 print(json.dumps({'source_files':len(logs),'PASS_BYTES_HASH':sum(x['status']=='PASS_BYTES_HASH' for x in logs),'HOLD':sum(x['status']!='PASS_BYTES_HASH' for x in logs)},ensure_ascii=False))
 return 0 if all(x['status']=='PASS_BYTES_HASH' for x in logs) else 2
if __name__=='__main__':raise SystemExit(main())
