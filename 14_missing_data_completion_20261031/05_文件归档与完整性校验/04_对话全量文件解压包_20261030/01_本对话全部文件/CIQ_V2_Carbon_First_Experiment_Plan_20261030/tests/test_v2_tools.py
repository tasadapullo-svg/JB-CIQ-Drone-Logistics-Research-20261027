import tempfile,csv,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from validate_paired_results import check as paired
from audit_trip_ledger import check as trip
from verify_stage import check_one

def csvwrite(p,header,rows):
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(header);w.writerows(rows)

def run():
    ROOT=Path(__file__).resolve().parents[1]
    g=check_one(ROOT,'V2_S06')
    assert g['status']=='HOLD' and any('MISSING_INPUT' in x for x in g['blockers'])
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/'paired.csv'
        fields=['task_id','task_population_id','seed','date_sgt','zone','scenario','mode','uav_model','vehicle_type','completed','on_time','door_to_door_min','cost_myr','fallback_reason']
        modes=['M0_PETROL','M1_DJI','M1_WING','M2_DJI','M2_WING']
        make=lambda m:['SYNTHETIC_TEST_ONLY','P_TEST','1','2026-05-15','A','TEST',m,'UAV_TEST','PETROL','1','1','12','3','']
        csvwrite(p,fields,[make(m) for m in modes]);assert paired(p)['status']=='PASS'
        csvwrite(p,fields,[make(m) for m in modes[:4]]);assert paired(p)['status']=='FAIL'
        csvwrite(p,fields,[make(m) for m in modes]+[make(modes[0])]);assert paired(p)['status']=='FAIL'
        t=Path(d)/'ledger.csv';th=['trip_id','task_population_id','seed','scenario','mode','vehicle_type','distance_km','fuel_l','idle_fuel_l','wall_charge_kwh_my','wall_charge_kwh_sg','trip_owner_id']
        rec=['TESTTRIP','P_TEST','1','TEST','M0_PETROL','PETROL','3','0.3','0','0','0','VEHICLE_A']
        csvwrite(t,th,[rec]);assert trip(t)['status']=='PASS'
        csvwrite(t,th,[rec,rec]);assert trip(t)['status']=='FAIL'
        bad=rec.copy();bad[8]='';csvwrite(t,th,[bad]);assert trip(t)['status']=='FAIL'
    print('PASS: 7 technical tests (synthetic fixture only; no real emissions model run)')
if __name__=='__main__':run()
