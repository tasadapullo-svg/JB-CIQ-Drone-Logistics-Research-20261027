#!/usr/bin/env python3
"""CIQ V5 S07 reproducible historical data validation. Never fabricates wind, rain or route.
Raw input is read-only. Formal release occurs only after byte, numeric, road and scope gates.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,gzip,hashlib,json,math,os,collections,zipfile,sys
from pathlib import Path
from collections import Counter,defaultdict

HOURS={5:744,6:720,7:744,8:744,9:720}
PIN='4569817b8145efe2ae06f4b21addc1986f971c12'
GRID=[('ERA5_GRID_103_75',1.5,103.75),('ERA5_GRID_103_50',1.5,103.5)]
ROOT=Path(__file__).resolve().parents[1]


def sha(path,algo='sha256'):
 h=hashlib.new(algo)
 if algo=='sha1':h.update(f'blob {path.stat().st_size}\0'.encode())
 with path.open('rb') as f:
  for p in iter(lambda:f.read(1024*1024),b''):h.update(p)
 return h.hexdigest()


def haversine(lat1,lon1,lat2,lon2):
 r=6371.0088;p=math.pi/180
 dlat=(lat2-lat1)*p;dlon=(lon2-lon1)*p
 a=math.sin(dlat/2)**2+math.cos(lat1*p)*math.cos(lat2*p)*math.sin(dlon/2)**2
 return 2*r*math.asin(math.sqrt(min(1,a)))


def parse_hour(value):
 if isinstance(value,dt.datetime):d=value
 elif isinstance(value,dt.date):d=dt.datetime.combine(value,dt.time())
 else:
  if value is None:return None
  s=str(value).strip()
  if not s:return None
  try:
   n=float(s)
   if 30000<=n<60000:d=dt.datetime(1899,12,30)+dt.timedelta(days=n)
   else:raise ValueError()
  except ValueError:
   try:d=dt.datetime.fromisoformat(s.replace('Z','+00:00'))
   except ValueError:
    d=None
    for fmt in ('%Y/%m/%d %H:%M:%S','%d/%m/%Y %H:%M:%S','%Y-%m-%d %H:%M:%S'):
     try:d=dt.datetime.strptime(s,fmt);break
     except ValueError:pass
    if d is None:return None
 if d.tzinfo:d=d.astimezone(dt.timezone(dt.timedelta(hours=8))).replace(tzinfo=None)
 if (d.minute,d.second,d.microsecond)!=(0,0,0):return None
 return d


def getcol(fields,alternates):
 nf={str(f).lower().strip():f for f in fields if f}
 for s in alternates:
  if s.lower() in nf:return nf[s.lower()]
 return None


def readcsv(path):
 with open(path,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def writecsv(path,rows,fields):
 path.parent.mkdir(parents=True,exist_ok=True)
 with open(path,'w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)


def locked_source(repo,registry):
 items=[]
 for x in registry['files']:
  p=repo/x['path'];z={'name':x['name'],'role':x.get('scope'), 'repo_path':x['path'], 'expected_bytes':x['size'], 'expected_blob':x['git_blob'],'expected_sha256':x.get('sha256') or ''}
  if not p.exists():z.update(status='MISSING_BYTES',actual_bytes=0);items.append(z);continue
  z.update(actual_bytes=p.stat().st_size,actual_blob=sha(p,'sha1'),actual_sha256=sha(p))
  good=(p.stat().st_size==int(x['size']) and z['actual_blob']==x['git_blob'] and (not x.get('sha256') or z['actual_sha256']==x['sha256']))
  if good and p.suffix=='.xlsx':
   try:
    with zipfile.ZipFile(p) as v:good=v.testzip() is None
   except Exception:good=False
  z['status']='PASS_BYTES' if good else 'HOLD_VERSION_OR_CRC';items.append(z)
 return items


def audit_frozen(nodes,orders):
 ids=[x['node_id'] for x in nodes]; unique=set(ids); taskids=set();scen=defaultdict(list);errors=Counter();months=Counter()
 for t in orders:
  oid=t['task_id'];date=t['date_local']; seed=t['scenario_seed']
  if oid in taskids:errors['duplicate_task_id']+=1
  taskids.add(oid)
  if t['origin_node_id'] not in unique or t['destination_node_id'] not in unique:errors['invalid_v5_endpoint']+=1
  origin_zone=next((x['zone'] for x in nodes if x['node_id']==t['origin_node_id']),None)
  dest_zone=next((x['zone'] for x in nodes if x['node_id']==t['destination_node_id']),None)
  if origin_zone!=t['origin_zone'] or dest_zone!=t['destination_zone']:errors['wrong_zone_mapping']+=1
  try:
   origin=dt.datetime.fromisoformat(t['release_local']);month=origin.month
   months[month]+=1
   if origin.utcoffset()!=dt.timedelta(hours=8) or origin.date().isoformat()!=date or month not in HOURS:errors['bad_release_time']+=1
  except Exception:errors['bad_release_time']+=1
  scen[(date,seed)].append(t)
 for k,group in scen.items():
  if len(group)!=18:errors['incorrect_scenario_size']+=1
  if Counter(t['origin_zone'] for t in group)!=Counter({'A':6,'B':6,'C':6}):errors['incorrect_scenario_zone_balance']+=1
 good=len(nodes)==68 and len(unique)==68 and len(orders)==82620 and len(scen)==4590 and not errors
 return {'status':'PASS' if good else 'HOLD','node_count':len(nodes),'task_count':len(orders),'scenario_count':len(scen),'errors':dict(errors),'orders_by_month':dict(months),'node_zones':dict(Counter(x['zone'] for x in nodes))}


def node_grids(nodes):
 out=[]
 for x in nodes:
  lat=float(x['latitude_N']);lon=float(x['longitude_E'])
  a=[(haversine(lat,lon,glat,glon),gid) for gid,glat,glon in GRID]
  dist,gid=min(a)
  out.append({'node_id':x['node_id'],'zone':x['zone'],'longitude_E':lon,'latitude_N':lat,'weather_grid_id':gid,
    'distance_to_historic_grid_km':f'{dist:.4f}','grid_gt10km_warning':int(dist>10),
    'source':'TWO_HISTORIC_ERA5_RETURNED_GRID_CENTERS',
    'actual_historical_weather_observed':'NO', 'grid_assignment':'NEAREST_CANDIDATE_NOT_STATION'})
 return out


def audit_weather(repo,registry,goodfiles,out):
 """If files exist, independently inspect real XLSX weather rows, never infer field units."""
 result=[]
 try:import openpyxl
 except ImportError:return [{'status':'HOLD_DEPENDENCY_OPENPYXL'}]
 for month in HOURS:
  name=f'JB_SG_Weather_2026_{month:02d}.xlsx'
  row={'month':month,'file':name,'status':'HOLD_MISSING_BYTES','expected_rows':4*HOURS[month]}
  if name not in goodfiles:result.append(row);continue
  path=repo/next(x['path'] for x in registry['files'] if x['name']==name)
  try:
   wb=openpyxl.load_workbook(path,read_only=True,data_only=True)
   row['sheets']=wb.sheetnames
   if 'Weather_Hourly' not in wb.sheetnames or 'ERA5_Hourly' not in wb.sheetnames:
    row['status']='HOLD_SHEET_MISSING';result.append(row);wb.close();continue
   sh=wb['Weather_Hourly'];it=sh.iter_rows(values_only=True)
   fields=[str(c).strip() if c is not None else '' for c in next(it)]
   p=getcol(fields,['point_id','reference_point_id','site_id','location_id'])
   t=getcol(fields,['time_sgt','datetime_sgt','timestamp_sgt','local_time','time_local','time','timestamp','timestamp_local','datetime_local','date_time_sgt'])
   if not t:
    ls=[f for f in fields if any(z in f.lower() for z in ('time','date'))];t=ls[0] if len(ls)==1 else None
   numeric=[f for f in fields if any(z in f.lower() for z in ('wind','rain','precip','gust'))]
   counts=Counter();keys=set();dup=0;unparsed=0;outside=0;any_numeric=Counter();raw_rows=0;examples=[]
   for cells in it:
    if not any(v is not None for v in cells):continue
    raw_rows+=1;d=dict(zip(fields,cells));v=str(d.get(p) or '').strip() if p else None;ts=parse_hour(d.get(t)) if t else None
    if ts is None or not v:unparsed+=1;continue
    if (v,ts) in keys:dup+=1
    keys.add((v,ts));counts[v]+=1
    if ts.year!=2026 or ts.month!=month:outside+=1
    for col in numeric:
     value=d.get(col)
     try:
      if value is not None and str(value).strip()!='' and math.isfinite(float(value)):any_numeric[col]+=1
     except Exception:pass
    if len(examples)<2:examples.append({p:v,t:ts.isoformat(),**{k:str(d.get(k))[:20] for k in numeric[:4]}})
   row.update(actual_rows=raw_rows,point_col=p,time_col=t,fields=fields,point_counts=dict(counts),duplicate_keys=dup,
              unparseable_keys=unparsed,outside_month=outside,weather_numeric_fields=dict(any_numeric),examples=examples,
              era5_sheet_rows=wb['ERA5_Hourly'].max_row-1)
   four_ref=counts==Counter({k:HOURS[month] for k in ('CW_MY','CW_SG','SL_MY','SL_SG')})
   row['status']='PASS_WEATHER_TIME_AND_VALUES_WITH_UNIT_REVIEW' if (raw_rows==4*HOURS[month] and four_ref and not(dup or unparsed or outside) and any_numeric) else 'HOLD_WEATHER_CONTENT_QA'
   wb.close()
  except Exception as e:row.update(status='HOLD_XLSX_READ',error=repr(e)[:240])
  result.append(row)
 return result


def audit_fcd(repo,registry,goodfiles):
 name='JB_CIQ_E01_corrected_five_month_traffic_data_345nodes_2026-05_09.csv.gz';o={'file':name,'status':'HOLD_MISSING_BYTES'}
 if name not in goodfiles:return o
 p=repo/next(x['path'] for x in registry['files'] if x['name']==name)
 try:
  with gzip.open(p,'rt',encoding='utf-8-sig',newline='') as f:
   r=csv.DictReader(f);fields=r.fieldnames or []
   n=getcol(fields,['node_id','fcd_node_id','station_id','monitoring_node_id'])
   t=getcol(fields,['time_sgt','timestamp_sgt','datetime_sgt','hour_start_sgt','hour_sgt','time_local','timestamp','time'])
   s=getcol(fields,['speed_kmh','avg_speed_kmh','speed_mean_kmh','speed_hour_kmh','fcd_speed_kmh','speed_value_kmh','travel_speed_kmh'])
   if not s:
    candidates=[x for x in fields if 'speed' in x.lower() and 'kmh' in x.lower()]
    if len(candidates)==1:s=candidates[0]
   rows=0;nodes=set();hours=set();keys=set();dup=0;bad=0;stats=Counter();permonth=defaultdict(Counter)
   for z in r:
    rows+=1; node=str(z.get(n) or '').strip() if n else None;tm=parse_hour(z.get(t)) if t else None
    if not node or tm is None:bad+=1;mm='invalid'
    else:
     if (node,tm) in keys:dup+=1
     keys.add((node,tm));nodes.add(node);hours.add(tm);mm=f'{tm.month:02d}' if tm.year==2026 and 5<=tm.month<=9 else 'outside'
    raw=z.get(s) if s else None
    if raw is None or str(raw).strip()=='':st='MISSING'
    else:
     try:
      val=float(raw);st='POSITIVE' if math.isfinite(val) and val>0 else ('NONPOSITIVE' if math.isfinite(val) else 'MISSING')
     except ValueError:st='INVALID'
    stats[st]+=1;permonth[mm][st]+=1
   o.update(rows=rows,unique_nodes=len(nodes),unique_hours=len(hours),duplicate_keys=dup,invalid_keys=bad,speed_states=dict(stats),
    monthly_speed_states={k:dict(v) for k,v in permonth.items()},fields=fields,columns={'node':n,'time':t,'speed':s})
   o['status']='PASS_FCD_STRUCTURE_WITH_MISSINGNESS' if (rows==345*3672 and len(nodes)==345 and len(hours)==3672 and dup==0 and bad==0 and n and t and s) else 'HOLD_FCD_STRUCTURE'
   o['approved_observed_directed_edge_speed']='NO_UNTIL_MAP_MATCH_DIRECTION_CALIBRATION'
 except Exception as e:o.update(status='HOLD_FCD_PARSING',error=repr(e)[:260])
 return o


def audit_legacy_osm(repo,registry,goodfiles,nodes,out):
 files=[f'E02_{z}_{s}.csv' for z in 'AB' for s in ('road_graph_nodes','directed_edges_OSM')]
 o={'status':'HOLD_MISSING_BYTES','paths':files}
 if not all(x in goodfiles for x in files):o['missing']=[x for x in files if x not in goodfiles];return o
 try:
  import numpy as np
  from scipy.spatial import cKDTree
  from pyproj import Transformer
  tr=Transformer.from_crs('EPSG:4326','EPSG:32648',always_xy=True)
  allxy=[];allids=[];edges={};invalid=Counter();node_set=set()
  for area in 'AB':
   path=repo/next(x['path'] for x in registry['files'] if x['name']==f'E02_{area}_road_graph_nodes.csv')
   with path.open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f):
     try:x,y=tr.transform(float(r['longitude']),float(r['latitude']))
     except Exception:invalid['bad_coord']+=1;continue
     osm=r['osm_node_id']; node_set.add(osm);allxy.append((x,y));allids.append(osm)
  for area in 'AB':
   path=repo/next(x['path'] for x in registry['files'] if x['name']==f'E02_{area}_directed_edges_OSM.csv')
   c=0;bad=0
   with path.open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f):
     c+=1
     try:dist=float(r['length_m']);bad+=(not math.isfinite(dist) or dist<=0)
     except (TypeError,ValueError):bad+=1
     if r['source'] not in node_set or r['target'] not in node_set:bad+=1
   edges[area]={'rows':c,'invalid':bad}
  tree=cKDTree(np.asarray(allxy));snaps=[]
  for row in nodes:
   xx,yy=tr.transform(float(row['longitude_E']),float(row['latitude_N']));d,i=tree.query([xx,yy]);snaps.append({'node_id':row['node_id'],'zone':row['zone'],'nearest_historical_osm_node':allids[int(i)],'distance_m':round(float(d),2),
    'candidate_status':'NEAREST_ONLY_NOT_CONFIRMED_ROAD_ENTRANCE' if d<=100 else 'HOLD_GT_100M'})
  writecsv(out/'S07_V5_68_HISTORICAL_AB_OSM_NEAREST_NOT_APPROVED.csv',snaps,list(snaps[0]))
  o.update(status='PASS_LEGACY_GRAPH_STRUCTURE_NOT_FULL_V5',road_nodes=len(node_set),edges=edges,invalid=dict(invalid),snap_under_100m=sum(x['candidate_status'].startswith('NEAREST') for x in snaps),snap_by_zone={z:{'n':sum(x['zone']==z for x in snaps),'under_100m':sum(x['zone']==z and x['candidate_status'].startswith('NEAREST') for x in snaps)} for z in 'ABC'})
  if any(x['invalid'] for x in edges.values()):o['status']='HOLD_LEGACY_GRAPH_INTEGRITY'
 except Exception as e:o.update(status='HOLD_ROAD_READ',error=repr(e)[:250])
 return o


def make_local_keys(nodes,orders,out):
 gr=node_grids(nodes);grids={r['node_id']:r for r in gr}
 writecsv(out/'S07_V5_68_NODE_WEATHER_GRID_CANDIDATES.csv',gr,list(gr[0]))
 keys=out/'S07_V5_249696_NODE_HOUR_LOOKUP_KEYS_ONLY.csv.gz'
 with gzip.open(keys,'wt',encoding='utf-8',newline='') as f:
  wr=csv.writer(f);wr.writerow(['node_id','zone','local_hour_MYT','era5_grid_id','grid_distance_km','wind_m_s','precip_mm','weather_gate'])
  d=dt.datetime(2026,5,1);end=dt.datetime(2026,10,1)
  count=0
  while d<end:
   for g in gr:
    wr.writerow([g['node_id'],g['zone'],d.isoformat(),g['weather_grid_id'],g['distance_to_historic_grid_km'],'','','HOLD_REAL_WEATHER_NOT_LOADED'])
    count+=1
   d+=dt.timedelta(hours=1)
 orderkeys=out/'S07_V5_82620_TASK_EVENT_KEYS_ONLY.csv.gz'
 with gzip.open(orderkeys,'wt',encoding='utf-8',newline='') as f:
  wr=csv.writer(f);wr.writerow(['task_id','scenario_seed','date_local','origin_node_id','destination_node_id','weather_lookup_hour_local','origin_grid_id','origin_grid_distance_km','weather_source_status','road_route_status','service_result_status'])
  for z in orders:
   tm=dt.datetime.fromisoformat(z['release_local']).replace(minute=0,second=0,microsecond=0)
   origin=grids[z['origin_node_id']]
   wr.writerow([z['task_id'],z['scenario_seed'],z['date_local'],z['origin_node_id'],z['destination_node_id'],tm.isoformat(),origin['weather_grid_id'],origin['distance_to_historic_grid_km'],
    'HOLD_WEATHER_MEASUREMENTS','HOLD_V5_DIRECTED_GRAPH','NOT_COMPUTED'])
 return {'node_hour_keys':count,'order_event_keys':len(orders),'weather_nearest_gt10km_nodes':sum(x['grid_gt10km_warning'] for x in gr),
  'weather_nearest_gt10km_task_origins':sum(int(grids[t['origin_node_id']]['grid_gt10km_warning']) for t in orders)}


def run(repo,out,make_keys=True):
 out.mkdir(parents=True,exist_ok=True)
 nodes=readcsv(ROOT/'inputs/S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv')
 orders=readcsv(ROOT/'inputs/S07_V5_SYNTHETIC_TASKS_CONDITIONAL_DESIGN.csv')
 freeze=audit_frozen(nodes,orders)
 reg=json.loads((ROOT/'inputs/source_index.json').read_text('utf-8'))
 assert reg['git_commit']==PIN
 sources=locked_source(repo,reg);good={s['name'] for s in sources if s['status']=='PASS_BYTES'}
 weather=audit_weather(repo,reg,good,out)
 fcd=audit_fcd(repo,reg,good)
 road=audit_legacy_osm(repo,reg,good,nodes,out)
 static=make_local_keys(nodes,orders,out) if make_keys else {'not_generated_in_remote_qa':True}
 core=[f'JB_SG_Weather_2026_{m:02d}.xlsx' for m in HOURS]+['JB_CIQ_E01_corrected_five_month_traffic_data_345nodes_2026-05_09.csv.gz']
 core_verified=len(good.intersection(core));roads_ab_verified=len(good.intersection([f'E02_{a}_{k}.csv' for a in 'AB' for k in ('directed_edges_OSM','road_graph_nodes')]))
 weather_time_pass=len(weather)==5 and all(x['status']=='PASS_WEATHER_TIME_AND_VALUES_WITH_UNIT_REVIEW' for x in weather)
 fcd_pass=fcd.get('status')=='PASS_FCD_STRUCTURE_WITH_MISSINGNESS'
 report={'input_status':freeze,'source_commit':PIN,'sources':sources,'core_numeric_source_files_verified':f'{core_verified}/6','historical_AB_files_verified':f'{roads_ab_verified}/4',
  'weather_monthly':weather,'fcd':fcd,'old_AB_road_candidate_graph':road,'static_V5_recalculation':static,
  'checks':{'weather_time_values':'PASS' if weather_time_pass else 'HOLD','fcd_structure':'PASS' if fcd_pass else 'HOLD',
    'weather_units_rain_accumulation_and_grid_coverage':'HOLD_NOT_INDEPENDENTLY_ACCEPTED','v5_ABC_directed_road_and_site_access':'HOLD_NOT_VERIFIED',
    'FCD_direction_to_road_edge':'HOLD_NOT_VERIFIED'},
  'S07_FORMAL_RELEASE':'HOLD_UNTIL_REAL_BYTES_VALUES_V5_ABC_ROAD_AND_OBSERVATION_MAPPING',
  'S09_HISTORICAL_WEATHER_DRIVEN_UAV':'NOT_RUN','S08_M0_ACTUAL_ROUTES':'NOT_RUN','S10_S11_OPERATIONAL_CARBON':'NOT_RUN',
  'scientific_scope':'conditional synthetic orders and archival weather; NOT observed delivery and not approved UAV flight'}
 (out/'S07_FORMAL_RELEASE_DECISION.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,default=str)+'\n','utf-8')
 writecsv(out/'S07_SOURCE_FILE_GATES.csv',sources,['name','role','repo_path','expected_bytes','expected_blob','expected_sha256','status','actual_bytes','actual_blob','actual_sha256'])
 with (out/'S07_WEATHER_MONTHLY_NUMERIC_QA.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['month','status','expected_rows','actual_rows','era5_sheet_rows','duplicate_keys','unparseable_keys','outside_month','point_counts','fields','numeric_availability'])
  for x in weather:w.writerow([x.get('month'),x.get('status'),x.get('expected_rows'),x.get('actual_rows'),x.get('era5_sheet_rows'),x.get('duplicate_keys'),x.get('unparseable_keys'),x.get('outside_month'),json.dumps(x.get('point_counts'),ensure_ascii=False),json.dumps(x.get('fields')),json.dumps(x.get('weather_numeric_fields'))])
 print(json.dumps({'V5':freeze['status'],'node_hours':static.get('node_hour_keys'), 'task_keys':static.get('order_event_keys'),'real_core':f'{core_verified}/6','old_AB':f'{roads_ab_verified}/4','S07':report['S07_FORMAL_RELEASE']},ensure_ascii=False))
 return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo-root',required=True);p.add_argument('--out',default=str(ROOT/'outputs'));p.add_argument('--skip-keys',action='store_true');a=p.parse_args()
 run(Path(a.repo_root),Path(a.out),not a.skip_keys)
