#!/usr/bin/env python3
"""Independent audit for matched task outcomes. Does not compute performance effects."""
import argparse,csv,json,collections
from pathlib import Path
MODES=('M0_PETROL','M1_DJI','M1_WING','M2_DJI','M2_WING')
REQUIRED={'task_id','task_population_id','seed','date_sgt','zone','scenario','mode','uav_model','vehicle_type','completed','on_time','door_to_door_min','cost_myr','fallback_reason'}

def check(path:Path):
    errors=[];groups=collections.defaultdict(dict);n=0
    with path.open(encoding='utf-8-sig',newline='') as f:
        rdr=csv.DictReader(f);miss=REQUIRED-set(rdr.fieldnames or [])
        if miss:return {'status':'FAIL','errors':['MISSING_COLUMNS:'+','.join(sorted(miss))], 'rows':0}
        for row in rdr:
            n+=1
            key=tuple(row[x] for x in ('task_population_id','seed','date_sgt','zone','scenario','task_id'))
            mode=row['mode'];b=groups[key]
            if not row['task_id'] or not row['task_population_id']:errors.append(f'EMPTY_TASK_ID:line{n}')
            if mode in b:errors.append(f'DUPLICATE_TASK_MODE:line{n}')
            b[mode]=row
            if mode not in MODES:errors.append(f'UNKNOWN_MODE:{mode}')
            if row['completed'] not in ('0','1') or row['on_time'] not in ('0','1'):
                errors.append(f'BAD_BINARY_STATUS:line{n}')
            if row['completed']=='0' and row['on_time']=='1':errors.append(f'ONTIME_WHEN_UNSERVED:line{n}')
            for metric in ('door_to_door_min','cost_myr'):
                if row[metric].strip():
                    try:
                        if float(row[metric])<0:errors.append(f'NEGATIVE_{metric}:line{n}')
                    except ValueError:errors.append(f'BAD_{metric}:line{n}')
    for k,by in groups.items():
        missing=set(MODES)-set(by)
        if missing:errors.append('MISSING_MODE_FOR_TASK:'+repr(k)+':'+','.join(sorted(missing)))
    return {'status':'PASS' if not errors and groups else 'FAIL','rows':n,'unique_tasks':len(groups),
            'expected_mode_records':len(groups)*len(MODES),'error_count':len(errors),'errors':errors[:100],
            'note':'PASS is structural parity only, not calibrated simulation.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('input_csv');p.add_argument('--out',default='')
    a=p.parse_args();r=check(Path(a.input_csv));v=json.dumps(r,ensure_ascii=False,indent=2);print(v)
    if a.out:Path(a.out).write_text(v+'\n',encoding='utf-8')
    if r['status']=='FAIL':raise SystemExit(2)
if __name__=='__main__':main()
