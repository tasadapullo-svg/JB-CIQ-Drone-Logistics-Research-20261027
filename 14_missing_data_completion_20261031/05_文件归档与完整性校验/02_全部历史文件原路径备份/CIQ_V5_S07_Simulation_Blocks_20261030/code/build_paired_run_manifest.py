#!/usr/bin/env python3
"""Freeze paired S10 runs from V5 S07 tasks without claiming routing or emissions.
All modes consume the identical task membership per (seed, local day).
This code never replaces missing weather / road data with assumptions.
"""
import argparse, csv, hashlib, json, collections, datetime as dt, pathlib
from zoneinfo import ZoneInfo

MODES=[('M0','PETROL_ONLY'),('M1_DJI','DJI_FLYCART_30'),('M1_WING','WINGCOPTER_198_CARGO'),('M2_DJI','DJI_FLYCART_30'),('M2_WING','WINGCOPTER_198_CARGO')]


def hfile(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()


def read_csv(path):
 with open(path,encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))


def write_csv(path,rows,fields):
 with open(path,'w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)


def run(nodes_path,tasks_path,out,strict=True):
 out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
 nodes=read_csv(nodes_path);tasks=read_csv(tasks_path)
 if len(nodes)!=68 or len({n['node_id'] for n in nodes})!=68:raise ValueError('INVALID_V5_68_NODE_MASTER')
 byid={n['node_id']:n for n in nodes}
 if 'A_N10' in byid:raise ValueError('ARCHIVED_NODE_A_N10_IS_NOT_ACTIVE')
 if strict and len(tasks)!=82620:raise ValueError('EXPECTED_FROZEN_82620_TASKS')
 groups=collections.defaultdict(list);seen=set();dates=set();seeds=set();bad=[]
 for t in tasks:
  tid=t['task_id'];seed=t['scenario_seed'];date=t['date_local'];key=(seed,date)
  if tid in seen: raise ValueError(f'DUPLICATE_TASK_ID:{tid}')
  seen.add(tid);groups[key].append(t);dates.add(date);seeds.add(seed)
  for which,zname,lname,latname in [('origin','origin_zone','origin_lon','origin_lat'),('destination','destination_zone','destination_lon','destination_lat')]:
   n=byid.get(t[f'{which}_node_id'])
   if n is None:raise ValueError(f'UNKNOWN_V5_NODE_IN_ORDER:{tid}:{which}')
   if t[zname]!=n['zone']:raise ValueError(f'ZONE_MISMATCH:{tid}:{which}')
   if abs(float(t[lname])-float(n['longitude_E']))>1e-7 or abs(float(t[latname])-float(n['latitude_N']))>1e-7:raise ValueError(f'COORD_MISMATCH:{tid}:{which}')
  if t['ciq_crossborder_status']!='MY_INLAND_SCENARIO_CIQ_WAIT_NOT_APPLICABLE': raise ValueError('CROSS_BORDER_SCENARIO_CHANGED')
  local=dt.datetime.fromisoformat(t['release_local']);utc=dt.datetime.fromisoformat(t['release_utc'])
  if local.tzinfo is None or utc.tzinfo is None or local.utcoffset()!=dt.timedelta(hours=8) or local.astimezone(dt.timezone.utc)!=utc.astimezone(dt.timezone.utc):raise ValueError(f'TIMEZONE_ERROR:{tid}')
  if local.date().isoformat()!=date:raise ValueError(f'RELEASE_LOCAL_DATE_CHANGED:{tid}')
  if float(t['parcel_kg'])<=0 or float(t['deadline_minutes'])<=0:raise ValueError('INVALID_ORDER_PARAMS')
  if t['service_and_carbon_result_status']!='NOT_COMPUTED':raise ValueError('UNEXPECTED_PRECOMPUTED_RESULT')
 if strict:
  expected_dates={ (dt.date(2026,5,1)+dt.timedelta(days=d)).isoformat() for d in range(153)}
  if dates!=expected_dates or len(seeds)!=30 or len(groups)!=4590:raise ValueError('FROZEN_SAMPLE_SCOPE_MISMATCH')
 summary=[];mode_runs=[];flat_task_index=[]
 for (seed,date),rr in sorted(groups.items(),key=lambda x:(x[0][1],x[0][0])):
  zone_counts=collections.Counter(x['origin_zone'] for x in rr)
  if strict and (len(rr)!=18 or dict(zone_counts)!={'A':6,'B':6,'C':6}):raise ValueError(f'UNBALANCED_SEED_DAY:{seed}:{date}:{zone_counts}')
  ids=sorted(x['task_id'] for x in rr)
  digest=hashlib.sha256(('\n'.join(ids)+'\n').encode()).hexdigest()
  rid=f'V5-D{date.replace("-","")}-S{seed}'
  base=dict(run_id=rid,scenario_seed=seed,date_local=date,task_count=len(ids),zone_A=zone_counts.get('A',0),zone_B=zone_counts.get('B',0),zone_C=zone_counts.get('C',0),task_set_sha256=digest,reference_space='V5_FROZEN_68_NODES',orders_population='CONDITIONAL_SYNTHETIC_82620',routing_status='HOLD_UNVERIFIED_DIRECTED_ROAD',weather_status='HOLD_UNVERIFIED_HOURLY_WEATHER',operation_emission_status='NOT_COMPUTED')
  summary.append(base)
  for mode,vehicle in MODES:
   mode_runs.append(dict(**base,mode=mode,aircraft=vehicle,mode_input_status='PAIRED_TASK_SET_READY_OPERATIONS_HOLD'))
  for t in sorted(rr,key=lambda a:a['task_id']):flat_task_index.append(dict(run_id=rid,task_id=t['task_id'],scenario_seed=seed,date_local=date))
 write_csv(out/'S07_V5_4590_SEED_DAY_RUN_MANIFEST.csv',summary,list(summary[0]))
 write_csv(out/'S10_V5_22950_MODE_RUN_KEYS_NO_SIM_RESULTS.csv',mode_runs,list(mode_runs[0]))
 write_csv(out/'S07_V5_82620_RUN_TASK_MEMBERSHIP.csv',flat_task_index,list(flat_task_index[0]))
 report={'phase':'V5_S07_TO_S10_BLOCKWISE_SIMULATION_ADMISSION','source_v5_node_csv_sha256':hfile(nodes_path),'frozen_synthetic_tasks_sha256':hfile(tasks_path),
  'v5_nodes':68,'task_rows':len(tasks),'unique_task_ids':len(seen),'unique_seeds':len(seeds),'dates':len(dates),'independent_seed_day_scenarios':len(summary),'mode_run_keys':len(mode_runs),'modes':list(x[0] for x in MODES),
  'tasks_per_seed_day_histogram':dict(collections.Counter(len(v) for v in groups.values())),'status':'PASS_PAIRED_INPUT_STRUCTURE_ONLY','hold':['REAL_WEATHER_VALUES_NOT_VERIFIED','ABC_DIRECTED_ROAD_UNAVAILABLE','VEHICLE_FUEL_AND_UAV_ENERGY_NOT_VERIFIED','M0_M1_M2_NOT_EXECUTED'],
  'scientific_warning':'Seed/day replicate scenarios are not 82620 independent empirical orders; all five modes must consume the identical per-run task hash. Do not pool orders from different seeds or days in one physical vehicle route.'}
 (out/'S07_S10_REAL_INPUT_AUDIT.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--nodes',required=True);p.add_argument('--tasks',required=True);p.add_argument('--out',required=True);p.add_argument('--non-strict',action='store_true');a=p.parse_args()
 print(json.dumps(run(a.nodes,a.tasks,a.out,not a.non_strict),ensure_ascii=False,indent=2))
