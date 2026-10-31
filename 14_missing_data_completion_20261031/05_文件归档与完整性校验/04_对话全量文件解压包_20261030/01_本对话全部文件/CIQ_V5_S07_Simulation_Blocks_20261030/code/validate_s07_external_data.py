#!/usr/bin/env python3
"""Validate S07 weather/route records WITHOUT guessing units, timestamps or approvals.
This validator is intentionally strict: it checks a normalized adapter output only;
raw XLSX/OSM is not promoted to science-ready data without documented mapping.
"""
import argparse,csv,datetime as dt,json,pathlib,collections,math

REQUIRED_WX=['source_point_id','interval_start_utc','interval_end_utc_exclusive','wind_speed_10m_ms','wind_gust_10m_ms','wind_direction_deg','rain_mm_per_hour','source_file_sha256','units_verified']
REQUIRED_ROAD=['origin_node_id','destination_node_id','directed_drive_distance_km','road_graph_sha256','entrance_access_verified','turn_constraints_verified','modelled_route_only']

def rows(p):
 with open(p,encoding='utf-8-sig',newline='') as h:
  r=csv.DictReader(h)
  if r.fieldnames is None:raise ValueError('MISSING_CSV_HEADER')
  return list(r),r.fieldnames

def validate_weather(path):
 rr,cols=rows(path)
 if any(x not in cols for x in REQUIRED_WX):return {'status':'HOLD_WEATHER_SCHEMA','missing_columns':sorted(set(REQUIRED_WX)-set(cols))}
 fails=collections.Counter();keys=set()
 if not rr:fails['ZERO_ROWS']+=1
 for r in rr:
  try:
   a=dt.datetime.fromisoformat(r['interval_start_utc']);b=dt.datetime.fromisoformat(r['interval_end_utc_exclusive'])
   if not a.tzinfo or not b.tzinfo or (b-a).total_seconds()!=3600:fails['NOT_A_TZ_AWARE_ONE_HOUR_INTERVAL']+=1
   k=(r['source_point_id'],a.isoformat())
   if k in keys:fails['DUPLICATE_GRID_HOUR']+=1
   keys.add(k)
   ws=float(r['wind_speed_10m_ms']);gust=float(r['wind_gust_10m_ms']);ang=float(r['wind_direction_deg']);rain=float(r['rain_mm_per_hour'])
   if not all(math.isfinite(z) for z in [ws,gust,ang,rain]):fails['NAN_OR_INF_WEATHER']+=1
   if not (0<=ws<=100 and 0<=gust<=150 and 0<=ang<=360 and 0<=rain<=500):fails['OUT_OF_BOUNDS_WEATHER']+=1
   if r['units_verified']!='YES':fails['UNITS_NOT_EXPLICITLY_VERIFIED']+=1
   if len(r['source_file_sha256'])!=64:fails['NO_SOURCE_IDENTITY']+=1
  except (ValueError,TypeError):fails['FORMAT_OR_NUMERIC_PARSE_ERROR']+=1
 return {'status':'NORMALIZED_WEATHER_SCHEMA_QA_ONLY' if not fails else 'HOLD_WEATHER_QA', 'rows':len(rr), 'distinct_grid_hours':len(keys), 'errors':dict(fails), 'warning':'Even valid normalized data is not a source-hash check or mission launch-time forecast.'}

def validate_road(path,known_node_ids):
 rr,cols=rows(path)
 if any(x not in cols for x in REQUIRED_ROAD):return {'status':'HOLD_ROAD_SCHEMA','missing_columns':sorted(set(REQUIRED_ROAD)-set(cols))}
 fails=collections.Counter();keys=set()
 if not rr:fails['ZERO_ROWS']+=1
 for r in rr:
  key=(r['origin_node_id'],r['destination_node_id'])
  if key in keys:fails['DUPLICATE_DIRECTIONAL_OD']+=1
  keys.add(key)
  if key[0] not in known_node_ids or key[1] not in known_node_ids:fails['UNKNOWN_V5_ID']+=1
  try:
   km=float(r['directed_drive_distance_km'])
   if not math.isfinite(km) or km<0:fails['INVALID_KM']+=1
   if key[0]!=key[1] and km==0:fails['NONSELF_ZERO_KM']+=1
  except (ValueError,TypeError):fails['INVALID_KM']+=1
  if len(r['road_graph_sha256'])!=64:fails['ROAD_GRAPH_HASH_MISSING']+=1
  if r['entrance_access_verified']!='YES':fails['ENTRANCE_UNVERIFIED']+=1
  if r['turn_constraints_verified']!='YES':fails['TURN_CONSTRAINTS_UNVERIFIED']+=1
  if r['modelled_route_only']!='YES':fails['UNMARKED_AS_MODELLED']+=1
 return {'status':'ROAD_ACCESS_AND_TURN_QA_PASS' if not fails else 'HOLD_ROAD_ACCESS_AND_TURN_QA', 'rows':len(rr), 'unique_directed_od':len(keys),'errors':dict(fails)}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--weather');p.add_argument('--road');p.add_argument('--node-master',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 nodes,_=rows(a.node_master);ids={r['node_id'] for r in nodes};v={'nodes':len(nodes)}
 v['weather']=validate_weather(a.weather) if a.weather else {'status':'HOLD_WEATHER_BYTES_MISSING'}
 v['road']=validate_road(a.road,ids) if a.road else {'status':'HOLD_ROAD_BYTES_MISSING'}
 pathlib.Path(a.out).parent.mkdir(parents=True,exist_ok=True);pathlib.Path(a.out).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(v,ensure_ascii=False))
