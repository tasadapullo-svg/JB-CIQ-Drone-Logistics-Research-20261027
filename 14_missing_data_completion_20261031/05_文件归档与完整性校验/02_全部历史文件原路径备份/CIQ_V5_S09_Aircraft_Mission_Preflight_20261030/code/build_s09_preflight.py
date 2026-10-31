#!/usr/bin/env python3
"""Audit all frozen V5 tasks against exact V5 candidate geometry and OEM payload bounds.

Outputs are exact geometric membership and upper-bound-range tests ONLY.
No real aerial operations, mission energy, petrol driving distance or emissions are computed.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from pathlib import Path
import csv,json,argparse,hashlib,math


def read_csv(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def put_csv(p,rows,fields):
    with Path(p).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for a in iter(lambda:f.read(1<<20),b''):h.update(a)
    return h.hexdigest()


def build(root):
    root=Path(root); inp=root/'inputs';out=root/'outputs';qa=root/'qa';out.mkdir(exist_ok=True);qa.mkdir(exist_ok=True)
    nodes=read_csv(inp/'S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv')
    edges=read_csv(inp/'S06_V5_116_UAV_GEOMETRY_ONLY.csv')
    taskfile=inp/'S07_V5_SYNTHETIC_TASKS_CONDITIONAL_DESIGN.csv'
    oem=json.loads((inp/'S09_OEM_SPEC_REGISTRY.json').read_text('utf-8'))['aircraft']
    if len(nodes)!=68 or len(edges)!=116:raise AssertionError('FROZEN_V5_CHANGED')
    ids={x['node_id'] for x in nodes}
    if len(ids)!=68:raise AssertionError('DUPLICATE_NODES')
    nmap={x['node_id']:x for x in nodes}
    directed=defaultdict(list);undirected=defaultdict(list)
    for e in edges:
        if not {e['from_id'],e['to_id']}<=ids:raise AssertionError('ORPHAN_EDGE')
        if e['input_mode']!='UAV_GEOMETRY_ONLY':raise AssertionError('GROUND_LINE_LEAKED_INTO_UAV')
        d=float(e['one_way_geodesic_km'])
        if d<=0 or not math.isfinite(d):raise AssertionError('BAD_GEOMETRY')
        directed[e['from_id'],e['to_id']].append(e)
        undirected[frozenset((e['from_id'],e['to_id']))].append(e)
    edge_rows=[];cnt=Counter()
    with taskfile.open(encoding='utf-8-sig',newline='') as f, (out/'S09_V5_ALL_TASKS_OEM_PAYLOAD_AND_DIRECT_EDGE_SCREEN.csv').open('w',encoding='utf-8-sig',newline='') as outf:
        rd=csv.DictReader(f)
        fields=['task_id','scenario_seed','release_utc','origin_node_id','destination_node_id','origin_zone','destination_zone','parcel_kg','directed_edge_count','reverse_only_edge_count','direct_candidate_status','direct_edge_id','direct_edge_oneway_km',
                'DJI_payload_screen','Wingcopter_payload_screen','DJI_geometric_roundtrip_public_range_proxy','Wingcopter_92km_UPPER_BOUND_only','real_flight_eligibility','mission_energy_kwh','event_weather_status','road_and_M0_status','S10_five_modes']
        wr=csv.DictWriter(outf,fieldnames=fields);wr.writeheader()
        n=0
        for t in rd:
            n+=1;oid=t['origin_node_id'];did=t['destination_node_id']
            if oid not in ids or did not in ids or oid==did: raise AssertionError('BAD_TASK_NODE')
            payload=float(t['parcel_kg']);same=directed.get((oid,did),());rev=directed.get((did,oid),())
            e=same[0] if same else (rev[0] if rev else None)
            dist=float(e['one_way_geodesic_km']) if e is not None else None
            if same:etype='DIRECTED_CANDIDATE_MATCH_NOT_AIR_ROUTE'
            elif rev:etype='REVERSE_CANDIDATE_ONLY_DIRECTION_UNVERIFIED'
            else:etype='NO_DIRECT_CANDIDATE_GEOMETRY'
            dj='WEIGHT_ONLY_PASS' if payload<=oem['DJI_FLYCART_30_DUAL']['payload_capacity_kg'] else 'WEIGHT_FAIL'
            wc='WEIGHT_ONLY_PASS' if payload<=oem['WINGCOPTER_198_CARGO']['payload_capacity_kg'] else 'WEIGHT_FAIL'
            # Public DJI max-distance tests: these are scenario geometry proxies, not flight approvals.
            # 1/16 loaded + 1/28 empty fractions are not a physically calibrated blended mission model.
            dji='HOLD_NO_DIRECT_GEOMETRY'
            wco='HOLD_NO_DIRECT_GEOMETRY'
            if dist is not None:
                dji='PASS_GEOMETRY_TEST_PROXY_NOT_ENERGY' if dist/16+dist/28<=1 else 'EXCEEDS_PUBLIC_TEST_EQUIVALENT_PROXY'
                wco='WITHIN_92KM_UPPER_BOUND_ONLY_NOT_LOADED_RANGE' if 2*dist<=92 else 'EXCEEDS_92KM_UPPER_BOUND'
            row={
                'task_id':t['task_id'],'scenario_seed':t['scenario_seed'],'release_utc':t['release_utc'],
                'origin_node_id':oid,'destination_node_id':did,'origin_zone':t['origin_zone'],
                'destination_zone':t['destination_zone'],'parcel_kg':str(payload),
                'directed_edge_count':len(same),'reverse_only_edge_count':len(rev) if not same else 0,
                'direct_candidate_status':etype,'direct_edge_id':e['edge_id'] if e else '',
                'direct_edge_oneway_km':f'{dist:.7f}' if dist is not None else '',
                'DJI_payload_screen':dj,'Wingcopter_payload_screen':wc,
                'DJI_geometric_roundtrip_public_range_proxy':dji,'Wingcopter_92km_UPPER_BOUND_only':wco,
                'real_flight_eligibility':'HOLD_WEATHER_AIRSPACE_STATION_AND_ENERGY',
                'mission_energy_kwh':'','event_weather_status':'HOLD_EVENT_TIME_WEATHER_NOT_VERIFIED',
                'road_and_M0_status':'HOLD_V5_ABC_DIRECTED_ROAD_AND_PETROL_CALIBRATION',
                'S10_five_modes':'UNCOMPUTED_SHARED_DEMAND_DENOMINATOR'}
            wr.writerow(row)
            cnt['tasks']+=1;cnt['mode_'+etype]+=1;cnt['dji_'+dj]+=1;cnt['wing_'+wc]+=1
            cnt['dji_geom_'+dji]+=1;cnt['wing_geom_'+wco]+=1
            if t['origin_zone']!=t['destination_zone']:cnt['cross_zone_designed']+=1
            if t['population_release']!='CONDITIONAL_SYNTHETIC_NOT_EMPIRICAL':raise AssertionError('NOT_CONDITIONAL_SCENARIO')
    if n!=82620:raise AssertionError(f'FROZEN_DEMAND_COUNT_CHANGED: {n}')
    for e in edges:
        d=float(e['one_way_geodesic_km'])
        edge_rows.append({'edge_id':e['edge_id'],'from_id':e['from_id'],'to_id':e['to_id'],
            'one_way_geodesic_km':d,'geodesic_fixed_hub_roundtrip_km':2*d,
            'dji_public_range_fraction_proxy_assumed_loaded_out_empty_back':round(d/16+d/28,6),
            'dji_public_test_proxy_25pct_reserve_assumption': 'WITHIN_TEST_PROXY' if d/16+d/28<=0.75 else 'EXCEEDS_TEST_PROXY',
            'wing_92km_public_max_only_screen':'BELOW_MAX_UPPER_BOUND_NOT_LOAD_VALIDATED' if 2*d<=92 else 'EXCEEDS_MAX_UPPER_BOUND',
            'regulatory_permission':'NOT_VERIFIED','vehicle_routing_km':'','calibrated_mission_energy_kwh':'',
            'status':'CONDITIONAL_GEOMETRY_ONLY_NOT_OPS'})
    put_csv(out/'S09_V5_116_EDGE_OEM_DISTANCE_BOUNDARY_SCREEN.csv',edge_rows,list(edge_rows[0]))
    cnt['edge_count']=len(edge_rows)
    cnt['edge_DJI_assumed_25pct_reserve_pass']=sum(x['dji_public_test_proxy_25pct_reserve_assumption']=='WITHIN_TEST_PROXY' for x in edge_rows)
    cnt['edge_DJI_test_proxy_energy_fraction_only_pass']=sum(x['dji_public_range_fraction_proxy_assumed_loaded_out_empty_back']<=1 for x in edge_rows)
    cnt['edge_Wingcopter_92km_max_geometric_roundtrip_below_upper_bound']=sum(x['wing_92km_public_max_only_screen']=='BELOW_MAX_UPPER_BOUND_NOT_LOAD_VALIDATED' for x in edge_rows)
    cnt['task_five_mode_fully_simulated']=0
    result={'status':'GEOMETRY_AND_PAYLOAD_SCREEN_PASS__MISSION_ENERGY_AND_CARBON_HOLD',
            'fixed_population':n,'nodes':len(ids),'edges':len(edges),'counts':dict(cnt),
            'provenance':{p.name:sha(p) for p in [taskfile,inp/'S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv',inp/'S06_V5_116_UAV_GEOMETRY_ONLY.csv',inp/'V5_FROZEN_SOURCE.zip']},
            'claims_not_supported':['aircraft operational flight feasibility','valid actual wind and rain windows','task kWh or CO2','petrol road-km','carbon reduction or optimization'],
            'v5_source_status':'FROZEN_UNCHANGED'}
    (qa/'S09_ACTUAL_V5_SCREEN_AUDIT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['status','fixed_population','nodes','edges']},ensure_ascii=False))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default=str(Path(__file__).resolve().parents[1]));args=p.parse_args();build(args.root)
