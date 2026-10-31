#!/usr/bin/env python3
"""Read-only pre-start inventory and code gate for CIQ V2/V2.1.
Do not use results as scientific approvals. Run on a local folder with planning ZIPs;
no network and no modification of original stage projects.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path

ZIPS=['CIQ_V2_Carbon_First_Experiments_Full_Roadmap_20261030.zip',
      'CIQ_V2_1_SCI_Method_Review_and_Work_Handoff_20261030.zip'] + [f'CIQ_V2_V2_S{i:02d}_Step_by_Step_20261030.zip' for i in range(6,13)]
GIS_SUFFIXES={'.qgz','.qgs','.gpkg','.shp','.geojson','.fgb','.gdb'}


def hashfile(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):h.update(chunk)
    return h.hexdigest()


def zipcheck(path):
    r={'filename':path.name,'present':path.is_file()}
    if not r['present']:return r
    r.update(size_bytes=path.stat().st_size, sha256=hashfile(path))
    try:
        with zipfile.ZipFile(path) as z:
            files=[x for x in z.infolist() if not x.is_dir()]
            bad=z.testzip()
            r.update(zip_crc='PASS' if bad is None else 'FAIL', bad_member=bad,
                     member_files=len(files), member_uncompressed_bytes=sum(x.file_size for x in files),
                     gis_member_files=[x.filename for x in files if Path(x.filename).suffix.lower() in GIS_SUFFIXES],
                     source_data_member_files=sum(1 for x in files if '/inputs/' in x.filename.lower() and not x.filename.endswith('/README.txt')))
    except Exception as e:r.update(zip_crc='FAIL',error=str(e))
    return r


def read_csv(path):
    with path.open('r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def check_stage(root,number):
    d=root/'STAGES'/f'V2_S{number:02d}'
    reg=d/'INPUT_REGISTER.csv'
    if not reg.is_file():return {'stage':number,'available':False,'reason':'NO_STAGE_CONTRACT'}
    rows=read_csv(reg)
    found=[];missing=[]
    for row in rows:
        p=d/'inputs'/row['filename']
        (found if p.is_file() else missing).append(row['filename'])
    return {'stage':f'V2-S{number:02d}','contract_present':True,'mandatory_input_count':len(rows),
            'local_input_present':found,'missing_input':missing,
            'all_inputs_version_frozen':bool(rows) and all((row.get('sha256') and row.get('provenance_url') and row.get('status')=='APPROVED') for row in rows),
            'local_preflight':json.loads((d/'outputs/PRECHECK_RESULT.json').read_text()).get('status') if (d/'outputs/PRECHECK_RESULT.json').exists() else None}


def check_register(root):
    p=root/'control/FILE_SHA256.json'
    if not p.is_file():return {'present':False}
    o=json.loads(p.read_text());bad=[]
    for x in o['files']:
        f=root/x['path']
        if not f.is_file() or hashfile(f)!=x['sha256'] or f.stat().st_size!=x['size']:bad.append(x['path'])
    return {'present':True,'checked_entries':len(o['files']),'mismatches':bad,'status':'PASS' if not bad else 'FAIL'}


def check_v2_register(root):
    p=root/'control/PACKAGE_SHA256_MANIFEST.csv'
    if not p.is_file():return {'present':False}
    o=read_csv(p);bad=[]
    for x in o:
        f=root/x['path']
        if not f.is_file() or hashfile(f)!=x['sha256'] or f.stat().st_size!=int(x['bytes']):bad.append(x['path'])
    return {'present':True,'checked_entries':len(o),'mismatches':bad,'status':'PASS' if not bad else 'FAIL'}


def run_tests(root):
    test=root/'tests/test_v2_tools.py'
    if not test.is_file():return {'status':'NOT_RUN','reason':'SCRIPT_NOT_FOUND'}
    proc=subprocess.run([sys.executable,str(test)],cwd=root,text=True,capture_output=True,timeout=45)
    return {'status':'PASS' if proc.returncode==0 else 'FAIL', 'exit_code':proc.returncode,'stdout':proc.stdout.strip(),'stderr':proc.stderr.strip(), 'note':'synthetic fixtures only; no real simulation'}


def fresh_gate_check(root):
    if not (root/'tools/verify_stage.py').is_file():return {'status':'NOT_RUN'}
    with tempfile.TemporaryDirectory(prefix='ciq_v2_fresh_gate_') as d:
        copied=Path(d)/'v2'
        shutil.copytree(root,copied)
        cmd=[sys.executable,str(copied/'tools/verify_stage.py'),'--root',str(copied),'--stage','ALL','--strict']
        proc=subprocess.run(cmd,cwd=copied,text=True,capture_output=True,timeout=45)
    return {'exit_code':proc.returncode, 'strict_hold_observed':proc.returncode==2, 'stdout':proc.stdout.strip(), 'stderr':proc.stderr.strip(),
            'note':'run on temporary copy of prior project; does not touch original data'}


def main():
    a=argparse.ArgumentParser();a.add_argument('--base',default='/mnt/data');a.add_argument('--out',required=True);a.add_argument('--qgis',default='');args=a.parse_args()
    base=Path(args.base).resolve();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    zips=[zipcheck(base/x) for x in ZIPS]
    qgis_paths=[]
    if args.qgis:
        p=Path(args.qgis).resolve()
        if p.is_file():qgis_paths=[str(p)]
        elif p.is_dir():qgis_paths=[str(x) for x in p.rglob('*') if x.is_file() and x.suffix.lower() in GIS_SUFFIXES]
    else:
        for p in base.rglob('*'):
            if out in p.parents or not p.is_file():continue
            if p.suffix.lower() in GIS_SUFFIXES:qgis_paths.append(str(p))
    root=base/'CIQ_V2_Carbon_First_Experiment_Plan_20261030'
    v21=base/'CIQ_V2_1_SCI_Method_Review_20261030'
    stages=[check_stage(root,i) for i in range(6,13)] if root.is_dir() else []
    audit={'audit_kind':'LOCAL_FILE_AND_GATE_READINESS_NOT_NUMERIC_SIMULATION','version':'2026-10-30',
           'zip_packages':zips,'gis_files_found':qgis_paths,'stage_inputs':stages,
           'v2_manifest':check_v2_register(root) if root.is_dir() else {'present':False},
           'v2_1_manifest':check_register(v21) if v21.is_dir() else {'present':False},
           'tests':run_tests(root) if root.is_dir() else {'status':'NOT_RUN'},
           'strict_stage_gate':fresh_gate_check(root) if root.is_dir() else {'status':'NOT_RUN'},
           'summary':{'planning_packages_integrity':'PASS' if all(x.get('zip_crc')=='PASS' for x in zips) else 'FAIL',
                      'expected_stage_inputs':sum(x.get('mandatory_input_count',0) for x in stages),
                      'actual_stage_input_files_present':sum(len(x.get('local_input_present',[])) for x in stages),
                      'real_qgis_source_present':bool(qgis_paths),
                      'research_implementation':'MISSING_OR_NOT_VALIDATED',
                      'release_decision':'CONDITIONAL_GO_ENGINEERING_ONLY__HOLD_FORMAL_EXPERIMENT'}}
    (out/'local_prestart_evidence.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return audit
if __name__=='__main__':
    a=main();print(json.dumps(a['summary'],ensure_ascii=False,indent=2));print(a['tests']);print('strict_exit',a['strict_stage_gate'].get('exit_code'))
