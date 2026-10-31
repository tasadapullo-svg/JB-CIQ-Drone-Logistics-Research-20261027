#!/usr/bin/env python3
"""Actual V5 frozen spatial weather-grid proxy audit, no meteorological observations."""
import csv,json,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def rows(name):
 with (ROOT/'inputs'/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def run():
 nodes=rows('S07_V5_68_NODE_ERA5_COARSE_GRID_CANDIDATES.csv')
 tasks=rows('S07_V5_SYNTHETIC_TASKS_CONDITIONAL_DESIGN.csv')
 lk=rows('S07_V5_82620_TASK_EVENT_WEATHER_ROAD_LOOKUP_KEYS_ONLY.csv')
 master=rows('S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv')
 nmap={r['node_id']:r for r in nodes}
 assert len(master)==len(nodes)==68 and set(x['node_id'] for x in master)==set(nmap)
 assert len(tasks)==len(lk)==82620
 assert {x['task_id'] for x in tasks}=={x['task_id'] for x in lk}
 tmap={x['task_id']:x for x in tasks};assert len(tmap)==82620
 byzone=collections.defaultdict(lambda:{'nodes':0,'far_gt10km':0,'mean_km_sum':0,'max_km':0})
 for x in nodes:
  z=x['zone'];km=float(x['grid_distance_m'])/1000;q=byzone[z];q['nodes']+=1;q['far_gt10km']+=int(km>10);q['mean_km_sum']+=km;q['max_km']=max(q['max_km'],km)
 for z,q in byzone.items():q['mean_km']=round(q.pop('mean_km_sum')/q['nodes'],3);q['max_km']=round(q['max_km'],3)
 counts=collections.Counter();zone=collections.defaultdict(collections.Counter);bad_node_ids=0;invalid_grid_lookup=0
 for row in lk:
  task=tmap[row['task_id']];origin=task['origin_node_id'];dest=task['destination_node_id']
  if origin not in nmap or dest not in nmap:bad_node_ids+=1;continue
  far1=float(nmap[origin]['grid_distance_m'])>10000
  far2=float(nmap[dest]['grid_distance_m'])>10000
  if row['origin_grid_farther_than_10km'] != ('TRUE' if far1 else 'FALSE'):invalid_grid_lookup+=1
  if row['destination_grid_farther_than_10km'] != ('TRUE' if far2 else 'FALSE'):invalid_grid_lookup+=1
  counts['origin_far_gt10km']+=int(far1);counts['destination_far_gt10km']+=int(far2)
  counts['both_far_gt10km']+=int(far1 and far2)
  zone[task['origin_zone']]['total']+=1;zone[task['origin_zone']]['origin_far_gt10km']+=int(far1)
  counts['relation_'+row['candidate_edge_relation']]+=1
 assert bad_node_ids==invalid_grid_lookup==0,(bad_node_ids,invalid_grid_lookup)
 out={'input':'V5_68_NODES_AND_FROZEN_82620_TASKS','source_type':'SPATIAL_DISTANCE_PROXY_ONLY_NOT_HOURLY_WEATHER','node_total':len(nodes),
  'zone_node_audit':byzone,'task_total':len(tasks),'task_origin_weather_grid_distance_counts':dict(counts),'origin_zone_task_counts':dict(zone),
  'node_ID_join_failures':bad_node_ids,'precomputed_10km_flags_discrepancies':invalid_grid_lookup,
  'actual_hourly_weather_values_verified':False,'V5_weather_operational_release':'HOLD'}
 (ROOT/'outputs/S07_V5_WEATHER_GRID_ACTUAL_GEOMETRIC_QA.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n','utf-8')
 with (ROOT/'outputs/S07_V5_ZONE_WEATHER_GRID_DISTANCE_QA.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['zone','node_count','nodes_farther_10km','mean_distance_km','max_distance_km','task_origins','task_origins_farther_10km']);
  for z in sorted(byzone):
   q=byzone[z];w.writerow([z,q['nodes'],q['far_gt10km'],q['mean_km'],q['max_km'],zone[z]['total'],zone[z]['origin_far_gt10km']])
 print(json.dumps({'node_count':68,'task_count':82620,'origin_far_gt10km':counts['origin_far_gt10km'],'zone_far':{z:q['far_gt10km'] for z,q in byzone.items()},'status':'GEOMETRY_QA_PASS_WEATHER_HOLD'},ensure_ascii=False))
 return out
if __name__=='__main__':run()
