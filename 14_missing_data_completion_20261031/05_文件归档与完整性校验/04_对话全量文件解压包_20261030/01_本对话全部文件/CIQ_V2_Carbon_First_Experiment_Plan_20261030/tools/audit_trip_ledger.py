#!/usr/bin/env python3
"""Audit one physical-trip row per scenario/mode; check nonnegativity & split grid energy."""
import argparse,csv,collections,json
from pathlib import Path
FIELDS={'trip_id','task_population_id','seed','scenario','mode','vehicle_type','distance_km','fuel_l','idle_fuel_l','wall_charge_kwh_my','wall_charge_kwh_sg','trip_owner_id'}
METRICS=('distance_km','fuel_l','idle_fuel_l','wall_charge_kwh_my','wall_charge_kwh_sg')
def check(path):
    errors=[];ids=set();n=0
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);miss=FIELDS-set(reader.fieldnames or [])
        if miss:return {'status':'FAIL','errors':['MISSING_COLUMNS:'+','.join(sorted(miss))]}
        for row in reader:
            n+=1;key=tuple(row[k] for k in ['task_population_id','seed','scenario','mode','trip_id'])
            if not row['trip_id'] or key in ids:errors.append(f'DUPLICATE_OR_EMPTY_PHYSICAL_TRIP:{n}')
            ids.add(key)
            if not row['trip_owner_id']:errors.append(f'NO_TRIP_OWNER:{n}')
            for metric in METRICS:
                v=row.get(metric,'').strip()
                if v=='':errors.append(f'MISSING_NOT_ZERO:{metric}:{n}');continue
                try:
                    if float(v)<0:errors.append(f'NEGATIVE:{metric}:{n}')
                except ValueError:errors.append(f'NONNUMERIC:{metric}:{n}')
    return {'status':'PASS' if not errors and n else 'FAIL','rows':n,'error_count':len(errors),'errors':errors[:100],
            'note':'Trip-level duplication check only. Separate scientific audit required for physical plausibility and allocations.'}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('trip_csv');a=ap.parse_args();res=check(a.trip_csv)
    print(json.dumps(res,ensure_ascii=False,indent=2));
    if res['status']!='PASS':raise SystemExit(2)
if __name__=='__main__':main()
