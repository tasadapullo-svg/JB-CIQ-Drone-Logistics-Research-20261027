#!/usr/bin/env python3
"""Strict READ-ONLY S07 source-byte, numerical and scenario checks.

This does NOT authorize route travel times, site access or UAV flight.
Three distinctions are deliberately separate:
  a. GitHub object metadata and historical reports (not raw verification)
  b. Full downloaded source bytes (Git SHA-1 blob and monthly SHA-256)
  c. Actual numerical/schema, spatial, time, directional and operational acceptance.
No inferred values or placeholders are inserted into weather/road/FCD data.
"""
import argparse,csv,datetime as dt,gzip,hashlib,json,math,sys,zipfile
from pathlib import Path
from collections import Counter
from read_weather_workbooks import extract_one

HERE=Path(__file__).resolve().parents[1]
MONTH_HOURS={5:744,6:720,7:744,8:744,9:720}
EXPECTED_POINTS={'CW_MY','CW_SG','SL_MY','SL_SG'}
SOURCE_INDEX=HERE/'inputs/SOURCE_FILES_PINNED_14.json'
FCD_NAME='JB_CIQ_E01_corrected_five_month_traffic_data_345nodes_2026-05_09.csv.gz'

def sha256(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()

def blob_sha(path):
 path=Path(path);h=hashlib.sha1();h.update(('blob '+str(path.stat().st_size)+'\x00').encode('ascii'))
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()

def source_identity(meta,source_root):
 candidates=[source_root/meta['path'],source_root/meta['name']]
 present=[p for p in candidates if p.is_file()]
 if not present:return {'name':meta['name'],'status':'HOLD_NOT_LOCAL','verified':False,'reason':'FULL_BYTES_NOT_PRESENT'}
 if len(present)>1 and present[0].resolve()!=present[1].resolve():
  return {'name':meta['name'],'status':'HOLD_AMBIGUOUS_FILES','verified':False}
 p=present[0];size=p.stat().st_size;blob=blob_sha(p);sha=sha256(p)
 good=size==meta['size'] and blob==meta['git_blob'] and (not meta.get('sha256') or sha==meta['sha256'])
 if good and p.suffix.lower() in ('.zip','.xlsx'):
  try:
   with zipfile.ZipFile(p) as z:good=z.testzip() is None
  except Exception:good=False
 return {'name':meta['name'],'path':str(p),'size':size,'blob':blob,'sha256':sha,'status':'PASS_SOURCE_BYTES' if good else 'HOLD_HASH_OR_ZIP_BAD','verified':good}

def get_col(columns,aliases,contains=()):
 lowered={k.lower().strip():k for k in columns}
 for a in aliases:
  if a.lower() in lowered:return lowered[a.lower()]
 if contains:
  c=[k for k in columns if all(piece in k.lower() for piece in contains)]
  if len(c)==1:return c[0]
 return None

def excel_or_text_hour(s):
 s=str(s).strip()
 if not s:return None
 if s.replace('.','',1).isdigit() and 30000<float(s)<60000:
  d=dt.datetime(1899,12,30)+dt.timedelta(days=float(s))
  return d.replace(minute=0,second=0,microsecond=0)
 v=s.replace('Z','+00:00')
 try:r=dt.datetime.fromisoformat(v)
 except ValueError:
  for fmt in ('%Y/%m/%d %H:%M:%S','%d/%m/%Y %H:%M:%S','%Y-%m-%d %H:%M','%Y/%m/%d %H:%M','%Y-%m-%d %H:%M:%S'):
   try:r=dt.datetime.strptime(s,fmt);break
   except ValueError:continue
  else:return None
 if r.tzinfo is not None:r=r.astimezone(dt.timezone(dt.timedelta(hours=8))).replace(tzinfo=None)
 return r

def weather_hourly_validate(csv_path,month):
 with open(csv_path,'rt',encoding='utf-8-sig',newline='') as f:
  reader=csv.DictReader(f);columns=reader.fieldnames or []
  pcol=get_col(columns,['point_id','location_id','site_id','reference_point_id'])
  tcol=get_col(columns,['time_sgt','timestamp_sgt','datetime_sgt','hour_sgt','local_time','datetime_local','time_local','timestamp_local','time_my','time'],contains=('time',))
  counter=Counter();keys=set();bad_times=0;bad_points=0;duplicates=0;parsed=0;out_window=0
  for row in reader:
   parsed+=1
   if pcol and tcol:
    p=(row.get(pcol) or '').strip();t=excel_or_text_hour(row.get(tcol,''))
    if p not in EXPECTED_POINTS:bad_points+=1
    if t is None:bad_times+=1
    else:
     if t.month!=month or t.year!=2026:out_window+=1
     key=(p,t)
     if key in keys:duplicates+=1
     keys.add(key);counter[p]+=1
 expect=4*MONTH_HOURS[month]
 ok=(pcol is not None and tcol is not None and parsed==expect and
     not(bad_times or bad_points or duplicates or out_window) and
     set(counter)==EXPECTED_POINTS and all(counter[p]==MONTH_HOURS[month] for p in EXPECTED_POINTS))
 return {'month':month,'source_rows':parsed,'expected_rows':expect,'fields':columns,'point_col':pcol,'time_col':tcol,
  'observed_points':dict(counter),'bad_times':bad_times,'bad_points':bad_points,'duplicate_point_hour_keys':duplicates,
  'out_of_month_keys':out_window,'status':'PASS_WEATHER_TIME_POINT_SCHEMA_ONLY' if ok else 'HOLD_WEATHER_TIME_POINT_SCHEMA',
  'weather_units_approved':False,'precipitation_window_approved':False,'event_weather_approved':False}

def _speed_col(fields):
 return get_col(fields,['speed_kmh','avg_speed_kmh','speed_mean_kmh','speed_hour_kmh','observed_speed_kmh','fcd_speed_kmh',
  'speed_value_kmh','travel_speed_kmh'],contains=('speed','kmh'))

def fcd_validate(path):
 report={'source':path.name,'status':'HOLD_SCHEMA','row_count':0,'nodes':None,'hours':None,'duplicate_node_hour_keys':None}
 seen=set();nodes=set();hours=set();state=Counter();count=0;dup=0
 with gzip.open(path,'rt',encoding='utf-8-sig',newline='') as f:
  r=csv.DictReader(f);fields=r.fieldnames or []
  node_col=get_col(fields,['node_id','fcd_node_id','station_id','site_id','monitoring_node_id'])
  time_col=get_col(fields,['hour_sgt','datetime_sgt','timestamp_sgt','local_hour','time_sgt','timestamp_local','time_local',
     'hour_start_sgt','time','timestamp'],contains=('time',))
  speed_col=_speed_col(fields)
  report.update(fields=fields,node_col=node_col,time_col=time_col,speed_col=speed_col)
  for row in r:
   count+=1
   if speed_col:
    s=(row.get(speed_col) or '').strip()
    if not s:state['MISSING']+=1
    else:
     try:
      x=float(s)
      if not math.isfinite(x):state['MISSING']+=1
      elif x>0:state['POSITIVE']+=1
      else:state['NONPOSITIVE']+=1
     except ValueError:state['INVALID_STRING']+=1
   if node_col and time_col:
    node=(row.get(node_col) or '').strip();hour=(row.get(time_col) or '').strip()
    if not node or not hour:state['MISSING_KEY']+=1
    key=(node,hour)
    if key in seen:dup+=1
    seen.add(key);nodes.add(node);hours.add(hour)
  report.update(row_count=count,nodes=len(nodes) if node_col else None,hours=len(hours) if time_col else None,
   speed_states=dict(state),duplicate_node_hour_keys=dup if node_col and time_col else None)
  report['status']='PASS_HISTORICAL_FCD_STRUCTURE_ONLY' if (count==1266840 and len(nodes)==345 and len(hours)==3672 and
   dup==0 and speed_col is not None and state['MISSING_KEY']==0) else 'HOLD_FCD_STRUCTURAL_QA'
  report['FCD_DIRECTION_VERIFIED']=False;report['V5_GROUND_ROUTING_APPROVED']=False
  return report

def roads_validate(path,area):
 count=0;bad_length=0;bad_speed=0;fields=[]
 with open(path,'rt',encoding='utf-8-sig',newline='') as f:
  reader=csv.DictReader(f);fields=reader.fieldnames or []
  for row in reader:
   count+=1
   try:
    val=float(row.get('length_m','nan'))
    if not math.isfinite(val) or val<=0:bad_length+=1
   except ValueError:bad_length+=1
   speed=row.get('speed_kmh','')
   if speed:
    try:
     value=float(speed)
     if not math.isfinite(value) or value<=0:bad_speed+=1
    except ValueError:bad_speed+=1
 expected={'A':178098,'B':104317}[area]
 good=count==expected and not bad_length and all(x in fields for x in ('source','target','length_m'))
 return {'area':area,'rows':count,'historic_expected_rows':expected,'fields':fields,'invalid_length':bad_length,'invalid_speed':bad_speed,
  'status':'PASS_HISTORICAL_EDGE_STRUCTURE_ONLY' if good else 'HOLD_LEGACY_EDGE_STRUCTURE',
  'V5_ABC_NETWORK_APPROVED':False,'turn_restrictions_encoded':False,'entrances_approved':False}

def scenario_check():
 with open(HERE/'inputs/S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv',encoding='utf-8-sig') as f:nodes=list(csv.DictReader(f))
 with open(HERE/'inputs/S07_V5_4590_SEED_DAY_RUN_MANIFEST.csv',encoding='utf-8-sig') as f:runs=list(csv.DictReader(f))
 with open(HERE/'inputs/S10_V5_22950_MODE_RUN_KEYS_NO_SIM_RESULTS.csv',encoding='utf-8-sig') as f: modes=list(csv.DictReader(f))
 counts=Counter(x['run_id'] for x in modes)
 ok=(len(nodes)==68 and len({x['node_id'] for x in nodes})==68 and len(runs)==4590 and len(modes)==22950 and
    all(v==5 for v in counts.values()) and set(counts)=={x['run_id'] for x in runs} and
    all(x['operation_emission_status']=='NOT_COMPUTED' for x in modes))
 return {'V5_nodes':len(nodes),'paired_scenarios':len(runs),'mode_keys':len(modes),
  'scenarios_each_with_five_modes':sum(x==5 for x in counts.values()),'status':'PASS_V5_FROZEN_PAIRS' if ok else 'HOLD_V5_PAIRING'}

def run(args):
 root=Path(args.sources);out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
 ix=json.loads(SOURCE_INDEX.read_text('utf-8'))
 ident=[];reports=[];name_to_source={}
 for meta in ix['files']:
  item=source_identity(meta,root);ident.append(item)
  if item['verified']:name_to_source[item['name']]=Path(item['path'])
 for m in MONTH_HOURS:
  name=f'JB_SG_Weather_2026_{m:02d}.xlsx'
  if name not in name_to_source:
   reports.append({'section':'WEATHER','month':m,'status':'HOLD_SOURCE_BYTES_NOT_AVAILABLE'});continue
  src=name_to_source[name];target=out/f'WEATHER_{m:02d}_RAW.csv'
  res=extract_one(src,target,'Weather_Hourly',next(x.get('sha256') for x in ix['files'] if x['name']==name))
  if res.get('status')!='EXTRACTED_RAW_NOT_OPERATIONALLY_RELEASED':
   reports.append({'section':'WEATHER','month':m,'status':'HOLD_XLSX_EXTRACTION','detail':res});continue
  x=weather_hourly_validate(target,m);x['section']='WEATHER';x['original_filename']=name;reports.append(x)
  # Count unfiltered ERA5 worksheet too, detecting the documented +4 boundary records.
  e=extract_one(src,out/f'ERA5_{m:02d}_RAW.csv','ERA5_Hourly',next(x.get('sha256') for x in ix['files'] if x['name']==name))
  if e.get('status')=='EXTRACTED_RAW_NOT_OPERATIONALLY_RELEASED':
   reports.append({'section':'ERA5_RAW','month':m,'source_rows':e['rows'],'expected_historic_rows':4*MONTH_HOURS[m]+4,
    'status':'HOLD_VERIFY_ERA5_BOUNDARY_ROWS' if e['rows']==4*MONTH_HOURS[m]+4 else 'HOLD_ERA5_HISTORICAL_ROW_DIFFERENCE'})
 for name,kind in [(FCD_NAME,'FCD'),('E02_A_directed_edges_OSM.csv','ROAD_A'),('E02_B_directed_edges_OSM.csv','ROAD_B')]:
  if name not in name_to_source:
   reports.append({'section':kind,'status':'HOLD_SOURCE_BYTES_NOT_AVAILABLE'});continue
  try:
   v=fcd_validate(name_to_source[name]) if kind=='FCD' else roads_validate(name_to_source[name],kind[-1]);v['section']=kind;reports.append(v)
  except Exception as e:reports.append({'section':kind,'status':'HOLD_PARSE_OR_SCHEMA_ERROR','error':repr(e)[:240]})
 scenario=scenario_check()
 digest={'study':'CIQ_V5_FROZEN_68_NODES','orders':82620,'source_commit':ix['git_commit'],
  'source_files_expected':len(ident),'source_files_verified_actual':sum(x['verified'] for x in ident),
  'scenario_gate':scenario,'weather_fcd_road_results':reports,
  'S07_NUMERIC_ACCEPTANCE':'HOLD' if (len(name_to_source)<14 or any(x['status'].startswith('HOLD') for x in reports)) else 'STILL_REQUIRES_WEATHER_UNITS_FCD_DIRECTION_AND_V5_ROAD_ACCESS',
  'S08_S09_S10_S11_S12_EMISSIONS':'NOT_COMPUTED',
  'caution':'HISTORICAL_GITHUB_JSON_STATS_ARE_NOT_THIS_RUN_RAW_NUMERIC_RESULTS'}
 (out/'S07_SOURCE_BYTE_IDENTITIES.json').write_text(json.dumps(ident,indent=2,ensure_ascii=False)+'\n','utf-8')
 (out/'S07_CURRENT_NUMERIC_GATE.json').write_text(json.dumps(digest,indent=2,ensure_ascii=False)+'\n','utf-8')
 with open(out/'S07_SOURCE_BYTE_IDENTITIES.csv','w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['name','status','verified','size','sha256','blob','path','reason']);w.writeheader();w.writerows(ident)
 print(json.dumps({'verified':digest['source_files_verified_actual'],'out_of':len(ident),'S07':digest['S07_NUMERIC_ACCEPTANCE'],'scenario':scenario['status']},ensure_ascii=False))
 return digest

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--sources',default=str(HERE/'recovered_sources'))
 p.add_argument('--output',default=str(HERE/'outputs'));args=p.parse_args()
 run(args)
