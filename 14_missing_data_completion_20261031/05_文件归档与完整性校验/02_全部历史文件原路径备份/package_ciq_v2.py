from pathlib import Path
import csv,hashlib,json,zipfile,os
root=Path('/mnt/data/CIQ_V2_Carbon_First_Experiment_Plan_20261030')
output=Path('/mnt/data')
# stage manifests created once, then full manifests
for p in sorted((root/'STAGES').glob('V2_S*')):
    fp=p/'SHA256_MANIFEST.csv'
    rows=[]
    for f in sorted(p.rglob('*')):
        if not f.is_file() or f==fp or '__pycache__' in f.parts:continue
        rows.append([f.relative_to(p).as_posix(),f.stat().st_size,hashlib.sha256(f.read_bytes()).hexdigest()])
    with fp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['relative_path','size_bytes','sha256']);w.writerows(rows)
# verify all docs in zip excluding transient pycache
all_files=sorted(f for f in root.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
full_manifest=root/'control'/'PACKAGE_SHA256_MANIFEST.csv'
with full_manifest.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['path','bytes','sha256'])
    for p in all_files:
        if p==full_manifest:continue
        w.writerow([p.relative_to(root).as_posix(),p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest()])
manifest_verified=0
for stage in sorted((root/'STAGES').glob('V2_S*')):
    with (stage/'SHA256_MANIFEST.csv').open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            a=stage/row['relative_path'];assert a.exists();assert a.stat().st_size==int(row['size_bytes'])
            assert hashlib.sha256(a.read_bytes()).hexdigest()==row['sha256'];manifest_verified+=1
stage_zips=[]
for stage in sorted((root/'STAGES').glob('V2_S*')):
    zp=output/f'CIQ_V2_{stage.name}_Step_by_Step_20261030.zip'
    use=[f for f in root.rglob('*') if f.is_file() and '__pycache__' not in f.parts and (
        f.relative_to(root).parts[0] in ['tools','protocol','references'] or
        f.relative_to(root).parts[0] == 'control' or
        f.relative_to(root).as_posix() in ['README_CN.md','GITHUB_UPLOAD_INSTRUCTIONS.md'] or
        f.is_relative_to(stage))]
    with zipfile.ZipFile(zp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for f in sorted(use):z.write(f,arcname=f.relative_to(root))
    with zipfile.ZipFile(zp) as z:
        assert z.testzip() is None
        assert f'STAGES/{stage.name}/README_CN.md' in z.namelist()
        assert 'tools/verify_stage.py' in z.namelist()
    stage_zips.append((stage.name,str(zp),len(use),zp.stat().st_size))
master=output/'CIQ_V2_Carbon_First_Experiments_Full_Roadmap_20261030.zip'
with zipfile.ZipFile(master,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
    for f in sorted(root.rglob('*')):
        if f.is_file() and '__pycache__' not in f.parts:z.write(f,arcname=f.relative_to(root))
with zipfile.ZipFile(master) as z:
    assert z.testzip() is None
    assert len([n for n in z.namelist() if n.startswith('STAGES/')]) >= 70
status={'package_version':'V2_20261030','status':'PLANNING_HOLD','historical_git_commit':'4569817b8145efe2ae06f4b21addc1986f971c12',
 'stage_count':7,'primary_modes':5,'planned_experiment_variations':11,
 'validation':'7 isolated synthetic technical tests PASS; 7 real stage gates HOLD due to absent real inputs',
 'sha256_rows_verified':manifest_verified,'stage_packages':stage_zips,'master_zip':str(master),'master_zip_bytes':master.stat().st_size}
(output/'CIQ_V2_PACKAGE_VERIFICATION.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(status,ensure_ascii=False,indent=2))
