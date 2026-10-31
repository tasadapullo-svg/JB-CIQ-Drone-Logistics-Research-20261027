#!/usr/bin/env python3
"""Recover independently pinned research files; read only existing files, never overwrite unverified originals.
Download only with --download. Each source is pinned to immutable git commit; byte SHA256 where supplied.
"""
import argparse, csv, hashlib, json, os, pathlib, shutil, tempfile, urllib.request, zipfile
COMMIT='4569817b8145efe2ae06f4b21addc1986f971c12'
REPO='tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027'

def git_blob_id(path):
    size=path.stat().st_size; h=hashlib.sha1();h.update(b'blob '+str(size).encode()+b'\0')
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''):h.update(b)
    return h.hexdigest()

def run(index_path,folder,out,download=False):
    index=json.loads(pathlib.Path(index_path).read_text('utf-8'))
    folder=pathlib.Path(folder);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);folder.mkdir(parents=True,exist_ok=True)
    result=[]
    for f in index['files']:
        dest=folder/f['name'];record={k:f.get(k,'') for k in ['name','path','size','git_blob','sha256','scope','note']}
        record['immutable_commit']=COMMIT;record['download_attempted']=bool(download)
        record['source_url']=f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/{f["path"]}'
        if not dest.exists() and download:
            tmp=dest.with_suffix(dest.suffix+'.partial')
            try:
                req=urllib.request.Request(record['source_url'],headers={'User-Agent':'CIQ-S07-source-audit'})
                with urllib.request.urlopen(req,timeout=90) as inp,tmp.open('wb') as o:shutil.copyfileobj(inp,o,1024*1024)
                tmp.rename(dest)
            except Exception as exc:
                tmp.unlink(missing_ok=True);record['download_error']=str(exc)[:500]
        if not dest.exists():record['status']='HOLD_MISSING_BYTES';result.append(record);continue
        record['actual_size']=dest.stat().st_size;record['actual_git_blob']=git_blob_id(dest)
        record['actual_sha256']=sha256(dest)
        record['identity_ok']=(record['actual_size']==f['size'] and record['actual_git_blob']==f['git_blob'] and
                    (not f.get('sha256') or record['actual_sha256']==f['sha256']))
        record['xlsx_zip_crc_ok']=None
        if record['identity_ok'] and dest.suffix.lower()=='.xlsx':
            try:
                with zipfile.ZipFile(dest) as z:record['xlsx_zip_crc_ok']=z.testzip() is None
            except Exception:record['xlsx_zip_crc_ok']=False
        record['status']='PASS_BYTES_HASH' if record['identity_ok'] and record['xlsx_zip_crc_ok'] is not False else 'FAIL_VERSION_OR_INTEGRITY'
        result.append(record)
    (out/'actual_source_recovery_status.json').write_text(json.dumps({'git_commit':COMMIT,'files':result},indent=2,ensure_ascii=False),'utf-8')
    cols=['name','scope','status','size','actual_size','git_blob','actual_git_blob','sha256','actual_sha256','xlsx_zip_crc_ok','source_url','download_error','note']
    with (out/'actual_source_recovery_status.csv').open('w',encoding='utf-8-sig',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(result)
    counts={k:sum(r['status']==k for r in result) for k in sorted(set(r['status'] for r in result))}
    print(json.dumps({'source_total':len(result),'counts':counts},ensure_ascii=False))
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--index',required=True);p.add_argument('--sources',required=True);p.add_argument('--out',required=True);p.add_argument('--download',action='store_true');a=p.parse_args()
    run(a.index,a.sources,a.out,a.download)
