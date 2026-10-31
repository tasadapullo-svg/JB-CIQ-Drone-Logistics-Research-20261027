#!/usr/bin/env python3
"""V2 preflight: require authentic files, schemas and recorded provenance; never claim scientific approval.
No geospatial/operational calculations. Works with Python 3.10+ standard library.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, zipfile
from pathlib import Path

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def read_csv(path:Path):
    with path.open('r',encoding='utf-8-sig',newline='') as f:
        dr=csv.DictReader(f)
        return dr.fieldnames or [], list(dr)

def check_one(root:Path,stage:str):
    base=root/'STAGES'/stage
    contract=json.loads((base/'STAGE_CONTRACT.json').read_text(encoding='utf-8'))
    reg={x['filename']:x for x in read_csv(base/'INPUT_REGISTER.csv')[1]}
    problems=[]; checks=[]
    for expected in contract['inputs']:
        name=expected['filename'];path=base/'inputs'/name;entry=reg.get(name,{})
        evidence={'file':name,'exists':path.exists(),'size_bytes':None,'sha256':None,'schema_valid':None,'source_recorded':False}
        if not path.is_file():
            problems.append(f'MISSING_INPUT:{name}');checks.append(evidence);continue
        evidence['size_bytes']=path.stat().st_size
        evidence['sha256']=sha256(path)
        if not evidence['size_bytes']:
            problems.append(f'EMPTY_FILE:{name}')
        frozen=(entry.get('sha256') or '').strip().lower()
        if not frozen or frozen!=evidence['sha256']:
            problems.append(f'UNFROZEN_OR_SHA_MISMATCH:{name}')
        if not (entry.get('provenance_url') or '').strip():
            problems.append(f'MISSING_PROVENANCE:{name}')
        else:evidence['source_recorded']=True
        if (entry.get('status') or '').upper()!='APPROVED':
            problems.append(f'INPUT_NOT_APPROVED:{name}')
        if path.suffix.lower()=='.zip':
            try:
                with zipfile.ZipFile(path) as z:
                    valid=z.testzip() is None and bool(z.namelist())
                evidence['schema_valid']=valid
                if not valid:problems.append(f'BAD_ZIP:{name}')
            except Exception as e:
                evidence['schema_valid']=False
                problems.append(f'BAD_ZIP:{name}:{type(e).__name__}')
        elif path.suffix.lower()=='.csv':
            try:
                header,rows=read_csv(path)
                template=base/'template_inputs'/name
                expected_header=read_csv(template)[0] if template.exists() else []
                missing_columns=[c for c in expected_header if c not in header]
                evidence['schema_valid']=not missing_columns and len(rows)>0
                evidence['row_count']=len(rows)
                if missing_columns:problems.append(f'SCHEMA_MISSING_COLUMNS:{name}:{",".join(missing_columns)}')
                if not rows:problems.append(f'HEADER_ONLY_OR_EMPTY:{name}')
            except Exception as e:
                evidence['schema_valid']=False
                problems.append(f'CSV_READ_FAILURE:{name}:{type(e).__name__}')
        elif path.suffix.lower()=='.json':
            try:
                data=json.loads(path.read_text(encoding='utf-8'))
                evidence['schema_valid']=isinstance(data,dict) and data.get('status') not in {'NOT_CALIBRATED','BLOCKED'}
                if not evidence['schema_valid']:problems.append(f'UNFROZEN_CONFIG:{name}')
            except Exception as e:
                problems.append(f'JSON_READ_FAILURE:{name}:{type(e).__name__}')
                evidence['schema_valid']=False
        checks.append(evidence)
    approvals=read_csv(base/'QA_GATES.csv')[1]
    if any(str(g.get('status','')).upper()!='PASS' for g in approvals):
        problems.append('QA_GATES_NOT_ALL_PASS')
    release=json.loads((base/'release_record.json').read_text(encoding='utf-8'))
    if release.get('scientific_approval')!='APPROVED' or not release.get('reviewer'):
        problems.append('SCIENTIFIC_APPROVAL_MISSING')
    # Upstream scientific approval cannot be inferred from input presence.
    prefix=int(stage.rsplit('S',1)[1])
    dependencies={6:[],7:[6],8:[7],9:[7],10:[8,9],11:[10],12:[11]}
    for i in dependencies.get(prefix,[]):
        previous=root/'STAGES'/f'V2_S{i:02d}'/'release_record.json'
        if not previous.exists() or json.loads(previous.read_text(encoding='utf-8')).get('scientific_approval')!='APPROVED':
            problems.append(f'UPSTREAM_NOT_APPROVED:V2_S{i:02d}')
    return {'stage':stage,'status':'HOLD' if problems else 'TECHNICAL_GATE_READY_FOR_INDEPENDENT_REVIEW',
            'input_checks':checks,'blockers':sorted(set(problems)),
            'scientific_note':'This tool does not certify airspace authorization, real deployment, or numerical accuracy.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='.')
    p.add_argument('--stage',required=True,help='V2_S06...V2_S12 or ALL')
    p.add_argument('--strict',action='store_true',help='exit 2 when HOLD')
    args=p.parse_args(); root=Path(args.root).resolve()
    stages=[x.name for x in sorted((root/'STAGES').glob('V2_S*'))] if args.stage=='ALL' else [args.stage]
    anyhold=False
    for stage in stages:
        r=check_one(root,stage);out=root/'STAGES'/stage/'outputs'
        out.mkdir(exist_ok=True);(out/'PRECHECK_RESULT.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(f"{stage}: {r['status']} | {len(r['blockers'])} blockers")
        for b in r['blockers'][:8]:print('  -',b)
        anyhold|=r['status']=='HOLD'
    if anyhold and args.strict:raise SystemExit(2)
if __name__=='__main__':main()
