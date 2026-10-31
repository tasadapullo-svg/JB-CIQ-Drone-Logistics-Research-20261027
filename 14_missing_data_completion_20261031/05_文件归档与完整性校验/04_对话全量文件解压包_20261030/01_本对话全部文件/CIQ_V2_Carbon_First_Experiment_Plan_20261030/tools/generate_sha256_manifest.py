#!/usr/bin/env python3
"""Create immutable SHA-256 file inventory for staged GitHub upload. Never reads credentials."""
import argparse,csv,hashlib
from pathlib import Path
BAD_SUFFIX={'.pem','.key','.p12','.pfx'}
BAD_EXACT={'.env','.env.local','credentials.json','secrets.json'}
def manifest(directory,output):
    directory=Path(directory).resolve();output=Path(output).resolve()
    rows=[]
    for p in sorted(directory.rglob('*')):
        if not p.is_file() or p.resolve()==output or '__pycache__' in p.parts:continue
        if p.name in BAD_EXACT or p.suffix.lower() in BAD_SUFFIX or p.name.startswith('.env'):
            print('SKIP sensitive:',p.relative_to(directory));continue
        h=hashlib.sha256()
        with p.open('rb') as f:
            for b in iter(lambda:f.read(1<<20),b''):h.update(b)
        rows.append([p.relative_to(directory).as_posix(),p.stat().st_size,h.hexdigest()])
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['relative_path','size_bytes','sha256']);w.writerows(rows)
    print(f'{len(rows)} files registered: {output}')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',required=True);ap.add_argument('--output',required=True)
    a=ap.parse_args();manifest(a.directory,a.output)
if __name__=='__main__':main()
