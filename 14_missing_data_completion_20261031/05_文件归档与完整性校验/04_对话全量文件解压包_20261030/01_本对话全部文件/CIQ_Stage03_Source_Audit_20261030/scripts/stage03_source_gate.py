#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only CIQ Stage03 historical-source preflight.

This tool audits historical METADATA/LEGACY SCRIPT and a Stage02 sign-off,
not raw meteorological time-series, not new flight weather, and not carbon.
No model run or automatic numerical release is possible.

Example:
 python stage03_source_gate.py --weather-summary PATH/to/final_verification_summary.json \
   --legacy-code PATH/to/run_stage6.py --stage02-gate PATH/to/07_stage02_spatial_gate.json \
   --out D:/CIQ_AUDITS/Stage03
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

REPO_URL = 'https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027'
HISTORICAL_COMMIT = '4569817b8145efe2ae06f4b21addc1986f971c12'
EXPECTED_BLOBS = {
    'weather_summary': '85845782a5f5cdbb4fa49737bb6e63aaa6dc06c7',
    'legacy_stage6': '1bbf7864ee9546b781f048d515c5c5d756da8752',
}
EXPECTED_MAIN_ROWS = {'05':2976,'06':2880,'07':2976,'08':2976,'09':2880}
EXPECTED_HOURS_PER_POINT = {'05':744,'06':720,'07':744,'08':744,'09':720}
CHECK_TOKENS = {
    'RELEASE_HOUR_WEATHER': "o['release_time_local']",
    'FIXED_SOURCE_HOUR_FCD': 'Fixed SOURCE hour',
    'REVERSE_ROUTE_FALLBACK': 'return (a[0]*2,a[1]*2,True,a[0])',
    'EV_ENERGY_PER_KM': "P['van_kwh_per_km']",
    'GRID_ELECTRICITY_EMISSIONS': "P['grid_kgCO2e_per_kwh']",
    'LEGACY_GENERIC_UAV_POWER': "P['drone_power_W_empty']",
    'OLD_INPUT_DEPENDENCY': 'import run_stage4_dispatch as prior',
}


def git_blob_id(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\x00' + raw).hexdigest()


def check_local_blob(path, expected):
    if not path:
        return {'status':'MISSING','path':None,'expected_git_blob_sha1':expected,
                'git_blob_sha1':None,'sha256':None}
    p=Path(path)
    if not p.is_file():
        return {'status':'MISSING','path':str(p),'expected_git_blob_sha1':expected,
                'git_blob_sha1':None,'sha256':None}
    raw=p.read_bytes()
    gitid=git_blob_id(raw)
    return {'status':'MATCH' if gitid==expected else 'MISMATCH',
            'path':str(p.resolve()),'bytes':len(raw),'expected_git_blob_sha1':expected,
            'git_blob_sha1':gitid,'sha256':hashlib.sha256(raw).hexdigest()}


def review_weather(data):
    checks=[]; monthly=[]
    ms=data.get('months',{}) if isinstance(data,dict) else {}
    if not isinstance(ms,dict):ms={}
    for month,expect in EXPECTED_MAIN_ROWS.items():
        x=ms.get(month)
        if not isinstance(x,dict):
            checks.append({'gate':'WX_MONTH_'+month,'status':'FAIL','detail':'Month missing or nonobject'})
            continue
        n=x.get('weather_hourly_rows')
        nm=x.get('anomaly_total')
        manifest=x.get('manifest_sha_match')
        corr_r=(x.get('era5_nasa_rain') or {}).get('correlation')
        corr_w=(x.get('era5_nasa_wind') or {}).get('correlation')
        cc=x.get('coverage') or []
        nea=[r for r in cc if r.get('source')=='NEA' and r.get('variable') in {'rainfall','wind-speed','wind-direction'}]
        statuses=sorted(set(str(r.get('status','')) for r in nea))
        nea_max=max([float(r.get('coverage_pct',0)) for r in nea],default=None)
        if n!=expect or manifest is not True:
            s='FAIL';detail='Unexpected main rows or monthly manifest flag mismatch'
        else:
            s='PASS_METADATA_ONLY';detail='Main row count / workbook manifest field match; not raw-source validation'
        checks.append({'gate':'WX_MONTH_'+month,'status':s,'detail':detail})
        if nea and (month!='05' and all(r.get('status')=='NOT_REQUESTED' for r in nea)):
            checks.append({'gate':'NEA_'+month,'status':'NOT_REQUESTED','detail':'NEA is not a five-month observation-completeness proof'})
        elif nea_max is not None and nea_max < 5:
            checks.append({'gate':'NEA_'+month,'status':'LOW_COVERAGE','detail':'NEA monthly coverage under 5% for represented metrics'})
        elif not nea:
            checks.append({'gate':'NEA_'+month,'status':'UNAVAILABLE','detail':'No relevant NEA coverage entries'})
        else:
            checks.append({'gate':'NEA_'+month,'status':'REVIEW','detail':'Review station and variable level coverage'})
        if corr_r is None or abs(float(corr_r))<0.2:
            checks.append({'gate':'RAIN_CROSS_SOURCE_'+month,'status':'REVIEW','detail':f'Rain correlation {corr_r}; investigate temporal/spatial/variable comparability'})
        monthly.append({'month':'2026-'+month,'main_hourly_rows':n,'expected_hours_per_point':EXPECTED_HOURS_PER_POINT[month],
                        'era5_rows':x.get('era5_rows'),'nasa_rows':x.get('nasa_rows'),
                        'zero_structural_anomalies_reported':nm==0,'workbook_manifest_sha_flag':manifest,
                        'era5_nasa_rain_correlation':corr_r,'era5_nasa_wind_correlation':corr_w,
                        'NEA_core_metric_rows':len(nea),'NEA_coverage_pct_max':nea_max,
                        'NEA_statuses':';'.join(statuses)})
    return checks,monthly


def review_code(src):
    found=[]
    for key,needle in CHECK_TOKENS.items():
        loc=[i for i,line in enumerate(src.splitlines(),1) if needle in line]
        found.append({'gate':key,'status':'FOUND_LEGACY_PATTERN' if loc else 'PATTERN_NOT_FOUND',
                      'line_numbers':','.join(map(str,loc[:10])),
                      'interpretation':('Historical assumption only; may not be reused directly' if loc else
                                        'Absence in this file does not prove corrected elsewhere')})
    return found


def review_spatial(path):
    if not path or not Path(path).is_file():
        return {'status':'HOLD','explanation':'Stage02 real spatial audit JSON not supplied'}
    try:
        d=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except Exception as exc:
        return {'status':'HOLD','explanation':'Unreadable Stage02 gate: '+repr(exc)}
    return {'status':'READY_FOR_MANUAL_REVIEW' if (d.get('scientific_spatial_input_frozen') is True
                and d.get('counts',{}).get('critical_issues')==0 and d.get('project_file_sha256')) else 'HOLD',
            'project_file_sha256':d.get('project_file_sha256'),'project_file':d.get('project_file'),
            'critical_issue_count':d.get('counts',{}).get('critical_issues'),
            'reported_spatial_frozen':d.get('scientific_spatial_input_frozen',False),
            'explanation':'Spatial signed gate may require independent sign-off and source hashes; this script never grants computational release'}


def write_csv(path,rows,fields):
    with Path(path).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)


def audit(weather_summary=None,legacy_code=None,stage02_gate=None):
    source_checks={'weather_summary':check_local_blob(weather_summary,EXPECTED_BLOBS['weather_summary']),
                   'legacy_stage6':check_local_blob(legacy_code,EXPECTED_BLOBS['legacy_stage6'])}
    weather_checks=[];monthly=[];code_checks=[]
    if source_checks['weather_summary']['status']=='MATCH':
        try:
            x=json.loads(Path(weather_summary).read_text(encoding='utf-8-sig'))
            weather_checks,monthly=review_weather(x)
        except Exception as exc:
            weather_checks=[{'gate':'PARSE_WEATHER_JSON','status':'FAIL','detail':repr(exc)}]
    if source_checks['legacy_stage6']['status']=='MATCH':
        code_checks=review_code(Path(legacy_code).read_text(encoding='utf-8'))
    spatial=review_spatial(stage02_gate)
    blockers=[]
    if source_checks['weather_summary']['status']!='MATCH':blockers.append('HISTORICAL_WEATHER_SUMMARY_BLOB_NOT_VERIFIED')
    if source_checks['legacy_stage6']['status']!='MATCH':blockers.append('HISTORICAL_STAGE6_BLOB_NOT_VERIFIED')
    if spatial['status']!='READY_FOR_MANUAL_REVIEW':blockers.append('LATEST_QGIS_SPATIAL_GATE_NOT_SIGNED')
    if any(c['status']=='FAIL' for c in weather_checks):blockers.append('HISTORICAL_WEATHER_METADATA_MISMATCH')
    # Even matching metadata/code/spatial proof is NOT sufficient for an approved numerical run.
    blockers.extend(['NEW_WEATHER_POINT_TAKEOFF_TIME_MAPPING_NOT_VALIDATED',
                     'NEW_ROAD_OD_AND_CIQ_BOUNDARY_NOT_VALIDATED',
                     'NEW_FUEL_AND_AIRCRAFT_ENERGY_CALIBRATION_NOT_VALIDATED',
                     'RESEARCHER_SCI_RUN_PROTOCOL_NOT_SIGNED'])
    return {
        'schema_version':'ciq-stage03-source-audit-v1','audit_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'historical_commit':HISTORICAL_COMMIT,'evidence_scope':'Historical summary and source code verification, not raw hourly measurements',
        'source_checks':source_checks,'weather_checks':weather_checks,'monthly_metadata':monthly,
        'code_patterns':code_checks,'spatial_gate':spatial,'blocking_codes':blockers,
        'stage03_status':'HOLD_RECALC_BLOCKED','numerical_recalculation_released':False}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--weather-summary',help='Exact repo file data/weather_2026/processed/final_verification_summary.json')
    p.add_argument('--legacy-code',help='Exact repo Stage 6 run_stage6.py')
    p.add_argument('--stage02-gate',help='Stage 02 QGIS export 07_stage02_spatial_gate.json')
    p.add_argument('--out',default='stage03_source_audit_output')
    a=p.parse_args(argv)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    result=audit(a.weather_summary,a.legacy_code,a.stage02_gate)
    (out/'stage03_source_gate.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    write_csv(out/'weather_monthly_metadata_audit.csv',result['monthly_metadata'],
              ['month','main_hourly_rows','expected_hours_per_point','era5_rows','nasa_rows',
               'zero_structural_anomalies_reported','workbook_manifest_sha_flag','era5_nasa_rain_correlation',
               'era5_nasa_wind_correlation','NEA_core_metric_rows','NEA_coverage_pct_max','NEA_statuses'])
    write_csv(out/'historical_legacy_model_patterns.csv',result['code_patterns'],
              ['gate','status','line_numbers','interpretation'])
    print(json.dumps({'status':result['stage03_status'],'blockers':result['blocking_codes'],
                      'weather_summary':result['source_checks']['weather_summary']['status'],
                      'legacy_stage6':result['source_checks']['legacy_stage6']['status'],
                      'out':str(out.resolve())},ensure_ascii=False,indent=2))
    return 2 if result['blocking_codes'] else 0

if __name__=='__main__':raise SystemExit(main())
