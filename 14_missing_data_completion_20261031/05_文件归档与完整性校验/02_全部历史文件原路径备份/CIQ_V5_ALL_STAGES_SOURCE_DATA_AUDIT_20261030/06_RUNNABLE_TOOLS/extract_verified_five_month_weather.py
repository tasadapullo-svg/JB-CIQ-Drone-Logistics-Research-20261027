#!/usr/bin/env python3
"""After byte verification, extract only the 5 pinned monthly Weather_Hourly sheets.
The result is RAW weather source rows, not approved drone flight weather.
"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from read_weather_workbooks import extract_one

def run(sources,out):
    index=json.loads((ROOT/'04_SOURCE_RECOVERY_AND_GITHUB_INVENTORY/SOURCE_FILES_PINNED_14.json').read_text('utf-8'))
    qa_path=ROOT/'05_AUDIT_REPORTS_AND_TEST_LOGS/SOURCE_RECOVERY_LATEST.json'
    verified={x['file']:x['status']=='PASS_BYTES_HASH' for x in json.loads(qa_path.read_text('utf-8'))} if qa_path.exists() else {}
    sources=Path(sources);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    log=[]
    for record in index['files']:
        if not(record.get('scope')=='MAY_SEP_2026' and record['name'].startswith('JB_SG_Weather_') and record['name'].endswith('.xlsx')):
            continue
        path=sources/record['path']
        if not verified.get(record['name']):
            log.append({'file':record['name'],'status':'HOLD_SOURCE_BYTES_HASH_NOT_RELEASED'})
            continue
        ret=extract_one(path,out/(record['name'][:-5]+'_Weather_Hourly_RAW.csv'),'Weather_Hourly',record.get('sha256'))
        log.append(ret)
    assert len(log)==5,'EXACTLY_FIVE_MONTHLY_WEATHER_FILES_REQUIRED'
    (out/'FIVE_MONTH_WEATHER_EXTRACTION_GATE.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    n=sum(x['status']=='EXTRACTED_RAW_NOT_OPERATIONALLY_RELEASED' for x in log)
    print(json.dumps({'month_files':len(log),'raw_extracted':n,'semantic_and_grid_QA_status':'HOLD_PENDING_INTERVAL_UNITS_AND_SPATIAL_AUDIT'},ensure_ascii=False))
    return 0 if n==5 else 2
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--sources',default=str(ROOT/'RECOVERED_GITHUB_DATA'));p.add_argument('--out',default=str(ROOT/'WEATHER_5_MONTH_RAW_EXTRACTED'));a=p.parse_args()
    raise SystemExit(run(a.sources,a.out))
