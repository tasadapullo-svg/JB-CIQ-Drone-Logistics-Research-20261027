#!/usr/bin/env python3
"""V5 S07 strict source-byte gate, weather/FCD/OSM read-only QA; NO emissions.
Usage:
  python code/s07_recover_and_gate.py --local-source C:\\your\\GitHub-repo
  python code/s07_recover_and_gate.py --local-source D:\\staged-data-folder
  python code/s07_recover_and_gate.py --download
  python code/s07_recover_and_gate.py --check-only
Results to qa/, recovered source bytes to recovered_sources/.
"""
import argparse,csv,gzip,hashlib,json,math,shutil,sys,urllib.request,zipfile,collections,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GITHUB='tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027'
REGISTRY=ROOT/'inputs/SOURCE_FILES_PINNED_14.json'
EXPECTED_ROWS=[2976,2880,2976,2976,2880]

def digest(path,kind):
    h=hashlib.new(kind);size=path.stat().st_size
    if kind=='sha1':h.update(f'blob {size}\0'.encode('ascii'))
    with path.open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
    return h.hexdigest()

def identity_check(file,meta):
    if not file.is_file():return {'status':'HOLD_FILE_MISSING','bytes':0,'sha256':None,'blob':None}
    size=file.stat().st_size;blob=digest(file,'sha1');sha=digest(file,'sha256')
    ok=(size==int(meta['size']) and blob==meta['git_blob'] and (not meta.get('sha256') or sha==meta['sha256']))
    if ok and file.suffix.lower() in {'.xlsx','.zip'}:
        try:
            with zipfile.ZipFile(file) as z:ok=z.testzip() is None
        except Exception:ok=False
    return {'status':'PASS_BYTES_HASH' if ok else 'HOLD_INTEGRITY_OR_VERSION','bytes':size,'sha256':sha,'blob':blob}

def retrieve(meta,repo_root,dest,download,commit):
    if dest.exists():return ''
    if repo_root:
        root=Path(repo_root)
        candidates=[root/meta['path'],root/meta['name']]
        found=[q for q in candidates if q.is_file()]
        if len(found)==1:
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(found[0],dest)
            return ''
        if len(found)>1:
            if found[0].resolve()==found[1].resolve():
                dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(found[0],dest);return ''
            return 'AMBIGUOUS_LOCAL_DUPLICATES'
    if not download:return 'NOT_FOUND_LOCALLY'
    url=f'https://raw.githubusercontent.com/{GITHUB}/{commit}/{meta["path"]}'
    tmp=dest.with_name(dest.name+'.partial');dest.parent.mkdir(parents=True,exist_ok=True)
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CIQ-V5-S07-recovery-v2'}),timeout=35) as response, tmp.open('wb') as f:
            shutil.copyfileobj(response,f,1024*1024)
        tmp.replace(dest)
        return ''
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        return 'DOWNLOAD_FAILED:'+str(exc)[:180]

def raw_weather_audit(file,month,verified):
    result={'month':month,'source_verified':verified,'status':'HOLD_SOURCE_BYTES','raw_weather_rows':None,'fields':None}
    if not verified:return result
    # Extract the actual hour rows; never infer rainfall units, wind levels or site representativeness.
    try:
        from read_weather_workbooks import extract_one
        out=ROOT/'raw_weather_hourly'/(file.stem+'_Weather_Hourly_RAW.csv')
        verified_sha=digest(file,'sha256')
        extraction=extract_one(file,out,'Weather_Hourly',verified_sha)
        result.update(raw_weather_rows=extraction.get('rows'),fields=extraction.get('columns'),source_sheet='Weather_Hourly',extract_status=extraction['status'])
        result['status']='RAW_HOURLY_EXTRACTED_NOT_SEMANTICALLY_APPROVED' if extraction['status']=='EXTRACTED_RAW_NOT_OPERATIONALLY_RELEASED' else 'HOLD_WEATHER_SHEET_EXTRACTION'
        yearmonth=int(month)
        expected={5:2976,6:2880,7:2976,8:2976,9:2880}[yearmonth]
        result['expected_rows_4_reference_points']=expected
        if result['raw_weather_rows']!=expected:result['status']='HOLD_MONTHLY_WEATHER_ROW_COUNT'
    except Exception as e:result.update(status='HOLD_XLSX_PARSE',error=str(e)[:160])
    return result

def csv_source_audit(file,kind,verified):
    result={'kind':kind,'status':'HOLD_SOURCE_BYTES','rows':None,'fields':None}
    if not verified:return result
    is_gz=file.suffix.lower()=='.gz';open_fn=gzip.open if is_gz else open
    try:
        with open_fn(file,'rt',encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f);header=reader.fieldnames
            if not header:raise ValueError('EMPTY_HEADER')
            n=0;missing=collections.Counter();min_length=float('inf');neg=0
            for r in reader:
                n+=1
                if kind.endswith('_EDGES'):
                    val=r.get('length_m','')
                    if val=='':missing['length_m']+=1
                    else:
                        try:
                            km=float(val)
                            if not math.isfinite(km) or km<0:neg+=1
                            else:min_length=min(min_length,km)
                        except ValueError:neg+=1
            result.update(status='LEGACY_SOURCE_ROW_COUNTED_NOT_V5_APPROVED',rows=n,fields=header,blank_length=missing['length_m'],invalid_length=neg,min_length_m=(min_length if min_length!=float('inf') else None))
            if kind=='FCD_5_MONTH' and n!=1266840:result['status']='HOLD_FCD_ROW_COUNT_DIFFERENT_HISTORICAL_QA'
            if kind=='A_EDGES' and n!=178098:result['status']='HOLD_A_EDGE_COUNT_DIFFERENT_HISTORICAL_QA'
            if kind=='B_EDGES' and n!=104317:result['status']='HOLD_B_EDGE_COUNT_DIFFERENT_HISTORICAL_QA'
    except Exception as e:result.update(status='HOLD_CSV_DECODE_OR_SCHEMA',error=str(e)[:170])
    return result

def run(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--local-source',help='Local GitHub checkout or flat directory with source files')
    parser.add_argument('--download',action='store_true',help='Download pinned commit when local source is absent')
    parser.add_argument('--check-only',action='store_true',help='Only check files already recovered')
    parser.add_argument('--output',default=str(ROOT/'recovered_sources'))
    a=parser.parse_args(argv)
    idx=json.loads(REGISTRY.read_text(encoding='utf-8'));data_root=Path(a.output)
    reports=[];raw=[]
    for rec in idx['files']:
        dest=data_root/rec['path']
        err='' if a.check_only else retrieve(rec,a.local_source,dest,a.download,idx['git_commit'])
        audit=identity_check(dest,rec)
        reports.append({'name':rec['name'],'path':rec['path'],'expected_bytes':rec['size'],'expected_blob':rec['git_blob'],'expected_sha256':rec.get('sha256'),'restore_message':err,**audit})
        if rec['name'].startswith('JB_SG_Weather_') and rec['name'].endswith('.xlsx'):
            raw.append(raw_weather_audit(dest,rec['name'][-7:-5],audit['status']=='PASS_BYTES_HASH'))
        elif rec['name']=='JB_CIQ_E01_corrected_five_month_traffic_data_345nodes_2026-05_09.csv.gz':raw.append(csv_source_audit(dest,'FCD_5_MONTH',audit['status']=='PASS_BYTES_HASH'))
        elif rec['name']=='E02_A_directed_edges_OSM.csv':raw.append(csv_source_audit(dest,'A_EDGES',audit['status']=='PASS_BYTES_HASH'))
        elif rec['name']=='E02_B_directed_edges_OSM.csv':raw.append(csv_source_audit(dest,'B_EDGES',audit['status']=='PASS_BYTES_HASH'))
    assert len(reports)==14
    qa=ROOT/'qa';qa.mkdir(parents=True,exist_ok=True)
    (qa/'source_byte_gate.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (qa/'source_byte_gate.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(reports[0]));writer.writeheader();writer.writerows(reports)
    (qa/'source_basic_numeric_audit.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    passed=sum(x['status']=='PASS_BYTES_HASH' for x in reports)
    overall={'frozen_spatial_version':'V5_68_NODES','frozen_task_population':82620,'frozen_paired_scenarios':4590,'git_commit':idx['git_commit'],'source_files':14,'files_with_verified_full_bytes':passed,'weather_fcd_osm_numeric_release':'HOLD_PENDING_FULL_QA','v5_c_directed_road':'HOLD_NOT_IN_14_HISTORICAL_FILES','S08_petrol_operational_result':'HOLD','S09_aircraft_mission_operational_energy':'HOLD','S10_S11_S12_results':'NOT_RUN'}
    (qa/'S07_RELEASE_GATE.json').write_text(json.dumps(overall,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(overall,ensure_ascii=False))
    return 0 if passed==14 else 2
if __name__=='__main__':sys.exit(run())
