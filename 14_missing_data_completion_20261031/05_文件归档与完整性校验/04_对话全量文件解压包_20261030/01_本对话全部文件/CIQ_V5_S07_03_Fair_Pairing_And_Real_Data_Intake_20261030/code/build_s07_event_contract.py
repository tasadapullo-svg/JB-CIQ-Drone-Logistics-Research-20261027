#!/usr/bin/env python3
"""V5 locked study: actual frozen-demand and weather-query-key construction.

Outputs NO observed/reanalysed weather values and NO vehicle route metrics unless
verified input bytes and separate operational QA are available. This program never
modifies V5 original GIS or task files.
"""
from __future__ import annotations
import argparse,collections,csv,datetime as dt,hashlib,json,pathlib,zipfile
from zoneinfo import ZoneInfo
from collections import Counter

Z=ZoneInfo('Asia/Kuala_Lumpur'); UTC=dt.timezone.utc
MODES=['M0_PETROL','M1_DJI_FLYCART30','M1_WINGCOPTER198_CARGO','M2_DJI_FLYCART30','M2_WINGCOPTER198_CARGO']

def read(p):
 with open(p,'r',encoding='utf-8-sig',newline='') as h:return list(csv.DictReader(h))

def write(p,rows,fields):
 p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with open(p,'w',newline='',encoding='utf-8-sig') as h:
  w=csv.DictWriter(h,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def sha256(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()

def git_blob(path):
 p=pathlib.Path(path);h=hashlib.sha1();h.update(f'blob {p.stat().st_size}\0'.encode())
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def preflight(nodes,tasks,hours,grids,edges):
 assert len(nodes)==68 and len({x['node_id'] for x in nodes})==68,'V5_ACTIVE_NODES_MUST_BE_68'
 assert len(edges)==116 and all(x['input_mode']=='UAV_GEOMETRY_ONLY' for x in edges),'MIXED_EDGE_TYPES'
 ids={x['node_id'] for x in nodes}
 assert set(x['node_id'] for x in grids)==ids,'GRID_CANDIDATES_MISSING_NODES'
 assert len(hours)==3672 and len({x['interval_start_utc'] for x in hours})==3672,'FIVE_MONTH_TIMELINE_INVALID'
 assert len(tasks)==82620 and len({x['task_id'] for x in tasks})==82620,'FROZEN_TASK_POPULATION_CHANGED'
 assert len({x['scenario_seed'] for x in tasks})==30,'SEEDS_CHANGED'
 assert len({x['date_local'] for x in tasks})==153,'DATES_CHANGED'
 assert all(x['origin_node_id'] in ids and x['destination_node_id'] in ids for x in tasks),'STALE_NODE_ID'
 assert all(x['origin_zone']==next(n['zone'] for n in nodes if n['node_id']==x['origin_node_id']) for x in tasks),'ORIGIN_ZONE_MISMATCH'
 assert all(x['destination_zone']==next(n['zone'] for n in nodes if n['node_id']==x['destination_node_id']) for x in tasks),'DESTINATION_ZONE_MISMATCH'
 assert all(x['road_route_status']=='NOT_ROUTED_HOLD' for x in tasks),'UNVERIFIED_ROAD_CALCULATIONS_IN_SOURCE'
 assert all(x['service_and_carbon_result_status']=='NOT_COMPUTED' for x in tasks),'UNVERIFIED_RESULT_IN_SOURCE'
 assert all(x['ciq_crossborder_status']=='MY_INLAND_SCENARIO_CIQ_WAIT_NOT_APPLICABLE' for x in tasks),'FALSE_CROSSBORDER'
 assert all(x['source_layer']!='GROUND_HANDOFF_STRAIGHT_REFERENCE' for x in edges),'GROUND_IN_UAV'
 return ids

def build(root):
 root=pathlib.Path(root);src=root/'inputs';out=root/'outputs';qa=root/'qa';qa.mkdir(exist_ok=True)
 paths={k:src/v for k,v in {
  'nodes':'S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv',
  'tasks':'S07_V5_SYNTHETIC_TASKS_CONDITIONAL_DESIGN.csv',
  'hours':'S07_V5_3672_HOURLY_TIMELINE.csv',
  'grids':'S07_V5_68_NODE_ERA5_COARSE_GRID_CANDIDATES.csv',
  'edges':'S06_V5_116_UAV_GEOMETRY_ONLY.csv',
  'v5':'V5_FROZEN_SOURCE.zip'}.items()}
 nodes=read(paths['nodes']);tasks=read(paths['tasks']);hours=read(paths['hours']);grids=read(paths['grids']);edges=read(paths['edges'])
 ids=preflight(nodes,tasks,hours,grids,edges)
 gridmap={r['node_id']:r for r in grids};hourmap={x['interval_start_utc']:x for x in hours}
 target_pairs={(r['from_id'],r['to_id']) for r in edges}
 release_rows=[];seed_day_zone=Counter();period_counter=Counter();month_zone=Counter();weight_counter=Counter();direction=Counter();deadline=Counter();access=Counter();weather_counter=Counter();direct_count=0
 for t in tasks:
  when=dt.datetime.fromisoformat(t['release_utc']);assert when.tzinfo is not None,'NAIVE_UTC'
  when_utc=when.astimezone(UTC);local=when_utc.astimezone(Z)
  assert local.date().isoformat()==t['date_local'],'RELEASE_DATE_MISMATCH'
  key=when_utc.replace(minute=0,second=0,microsecond=0).isoformat()
  assert key in hourmap,'WEATHER_SLOT_OUTSIDE_STUDY'
  ori=gridmap[t['origin_node_id']];dst=gridmap[t['destination_node_id']]
  one_way=(t['origin_node_id'],t['destination_node_id']) in target_pairs
  reverse=(t['destination_node_id'],t['origin_node_id']) in target_pairs
  direct='RECORDED_DIRECT_GEOMETRY' if one_way else ('REVERSE_ONLY_NOT_ASSUMED_VALID' if reverse else 'NO_DIRECT_GEOMETRY')
  direct_count+=int(one_way)
  seed_day_zone[t['scenario_seed'],t['date_local'],t['origin_zone']]+=1
  period_counter[local.hour]+=1;month_zone[local.month,t['origin_zone']]+=1
  weight_counter[t['parcel_kg']]+=1;direction[t['origin_zone'],t['destination_zone']]+=1;deadline[t['deadline_minutes']]+=1
  access[direct]+=1
  wd=local.weekday();weather_counter[ori['returned_era5_grid_id'],dst['returned_era5_grid_id']]+=1
  release_rows.append({'task_id':t['task_id'],'scenario_seed':t['scenario_seed'],'date_local':t['date_local'],
    'release_utc':t['release_utc'],'weather_slot_start_utc':key,'rainfall_accumulation_interval_end_utc':hourmap[key]['rainfall_valid_end_utc'],
    'origin_node_id':t['origin_node_id'],'origin_zone':t['origin_zone'],
    'destination_node_id':t['destination_node_id'],'destination_zone':t['destination_zone'],
    'origin_era5_grid_id':ori['returned_era5_grid_id'],'origin_grid_distance_m':ori['grid_distance_m'],
    'destination_era5_grid_id':dst['returned_era5_grid_id'],'destination_grid_distance_m':dst['grid_distance_m'],
    'origin_grid_farther_than_10km':str(float(ori['grid_distance_m'])>10000).upper(),
    'destination_grid_farther_than_10km':str(float(dst['grid_distance_m'])>10000).upper(),
    'release_hour_UTC_numerical_weather_accepted':'NO','uav_departure_and_return_weather_accepted':'NO',
    'road_directed_route_accepted':'NO','candidate_edge_relation':direct,
    'paired_modes_reference':'|'.join(MODES),
    'current_validation':'REFERENCE_ONLY_HOLD_WEATHER_ROAD_AND_OPERATIONS'})
 assert len(release_rows)==len(tasks)
 field=list(release_rows[0]);write(out/'S07_V5_82620_TASK_EVENT_WEATHER_ROAD_LOOKUP_KEYS_ONLY.csv',release_rows,field)
 daily=[{'scenario_seed':k[0],'date_local':k[1],'origin_zone':k[2],'designed_task_count':v} for k,v in sorted(seed_day_zone.items())]
 write(out/'S07_13770_SEED_DAY_ZONE_STRATA_COUNTS.csv',daily,list(daily[0]))
 assert len(daily)==30*153*3 and all(x['designed_task_count']==6 for x in daily)
 hist=[{'variable':'task_origin_hour_local','group':str(k),'count':v} for k,v in sorted(period_counter.items())]
 hist +=[{'variable':'parcel_kg','group':str(k),'count':v} for k,v in sorted(weight_counter.items(),key=lambda z:float(z[0]))]
 hist +=[{'variable':'deadline_minutes','group':str(k),'count':v} for k,v in sorted(deadline.items(),key=lambda z:int(z[0]))]
 hist +=[{'variable':'origin_zone_to_destination_zone','group':f'{k[0]}>{k[1]}','count':v} for k,v in sorted(direction.items())]
 hist +=[{'variable':'edge_relation','group':str(k),'count':v} for k,v in sorted(access.items())]
 hist +=[{'variable':'origin_era5_grid_to_destination_era5_grid','group':f'{k[0]}>{k[1]}','count':v} for k,v in sorted(weather_counter.items())]
 write(out/'S07_SYNTHETIC_TASK_DESIGN_DIAGNOSTICS.csv',hist,['variable','group','count'])
 monthly=[{'month_2026':m,'origin_zone':z,'task_count':month_zone[(m,z)],'design_not_empirical':'YES'} for m in range(5,10) for z in ['A','B','C']]
 write(out/'S07_MONTH_BY_ZONE_TASK_COUNTS.csv',monthly,list(monthly[0]))
 # Record source acceptance status. Metadata alone is not actual file content.
 idx=json.loads((src/'PINNED_SOURCE_INDEX.json').read_text());repo_idx=[]
 for s in idx['files']:
  q=root/'recovered_sources'/s['name'];identity='HOLD_MISSING_SOURCE_BYTES'
  if q.exists():
   if q.stat().st_size!=s['size'] or git_blob(q)!=s['git_blob'] or (s.get('sha256') and sha256(q)!=s['sha256']):identity='HOLD_HASH_OR_SIZE_MISMATCH'
   else:identity='PASS_EXACT_SOURCE_BYTES'
  repo_idx.append({'name':s['name'],'expected_bytes':s['size'],'expected_git_blob_sha1':s['git_blob'], 'expected_sha256':s.get('sha256',''), 'actual_file_present':q.exists(),'source_identity':identity})
 write(qa/'S07_PINNED_SOURCE_BYTE_GATE.csv',repo_idx,list(repo_idx[0]))
 registry={k:{'filename':p.name,'bytes':p.stat().st_size,'sha256':sha256(p)} for k,p in paths.items()}
 checks={'source_v5_immutable_zip_sha256':registry['v5']['sha256'],
 'frozen_nodes':len(nodes),'frozen_tasks':len(tasks),'hours':len(hours),'distinct_seeds':30,'distinct_days':153,
 'seed_day_zone_blocks':len(daily),'every_seed_day_zone_has_six_tasks':all(x['designed_task_count']==6 for x in daily),
 'candidate_direct_edge_tasks':access['RECORDED_DIRECT_GEOMETRY'],
 'candidate_reverse_only_tasks':access['REVERSE_ONLY_NOT_ASSUMED_VALID'],
 'no_direct_edge_tasks':access['NO_DIRECT_GEOMETRY'],
 'origin_weather_geographic_proxies_farther_10km':sum(float(gridmap[t['origin_node_id']]['grid_distance_m'])>10000 for t in tasks),
 'origin_context_grid_counts':dict(Counter(x['origin_era5_grid_id'] for x in release_rows)),
 'cross_zone_synthetic_tasks':sum(v for (a,b),v in direction.items() if a!=b),
 'monthly_task_count':{f'{m:02}':sum(month_zone[(m,z)] for z in ['A','B','C']) for m in range(5,10)},
 'mode_reference_count':len(MODES),'all_tasks_are_synthetic':True,
 'weather_point_values_accepted':False,'valid_ABC_directed_road_routes_accepted':False,'official_operational_flight_approved':False,
 'petrol_M0_results_approved':False,'operational_CO2e_and_cost_results_approved':False,
 'pinned_source_verified_count':sum(r['source_identity']=='PASS_EXACT_SOURCE_BYTES' for r in repo_idx),
 'source_files_expected':len(repo_idx),'version_pinning':idx['git_commit'],
 'input_registry':registry}
 (qa/'S07_ACTUAL_EXECUTION_AUDIT.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 assert sum(access.values())==82620 and sum(month_zone.values())==82620
 print(json.dumps({k:checks[k] for k in ['frozen_tasks','candidate_direct_edge_tasks','candidate_reverse_only_tasks','no_direct_edge_tasks','origin_weather_geographic_proxies_farther_10km','pinned_source_verified_count']},ensure_ascii=False))
 return checks
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',default=str(pathlib.Path(__file__).resolve().parents[1]));a=p.parse_args();build(a.root)
