# -*- coding: utf-8 -*-
"""Independent baseline-road-geometry routing for CIQ A/B (not traffic-calibrated).

Python 3 standard library only. Uses the frozen E02 Oct 26 2026 OSM JSON
snapshots from the project GitHub rather than today's changing OSM.
Outputs line geometries only for successfully matched nodes in the same graph.
DO NOT interpret as approved vehicle access, verified observed times or drone routes.
"""
from pathlib import Path
from urllib.request import urlretrieve
from hashlib import sha256
from math import radians, sin, cos, asin, sqrt
import json, csv, heapq, datetime

HERE=Path(__file__).resolve().parent.parent
CACHE=HERE/'route_outputs'/'road_data_cache'
OUT=HERE/'route_outputs'
CACHE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
REPO='https://raw.githubusercontent.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027/main/03_gis_and_road_network/road_network_project/JB_CIQ_E02_roadnet_V4_6/outputs/'
META={
'A':('OSM_A_overpass_response.json','7686c2eec13aee3ad9181542b5b2d0723ef780dcb6b8070b4b5e1876d99da667',(1.435,103.71,1.55,103.85)),
'B':('OSM_B_overpass_response.json','29c1c7b6203efdf8b40cb443f8132f88a646bd01b2e90a19729a782c95b9a56f',(1.32,103.515,1.485,103.69))}
# NEW A IDs replace prior E/W labels; old Area A sites are not used.
# Attributes are read from the accompanying CSVs; no hidden station changes.
POINTS={
'G_CIQ':(103.76663,1.46502),'A01':(103.7743763,1.5311284),'A02':(103.77658,1.53356),
'A03':(103.783,1.4985),'A04':(103.777987,1.500802), 'A09':(103.65939,1.49927),
'B00':(103.59894,1.37765),'B01':(103.598,1.392),'B02':(103.62,1.39),
'B06':(103.62725,1.41221),'B07':(103.6205,1.4487)}
JOBS={'A':[('G_CIQ','A01'),('G_CIQ','A02'),('G_CIQ','A03'),('G_CIQ','A04'),('G_CIQ','A09')],
      'B':[('B00','B01'),('B00','B02'),('B00','B06'),('B00','B07')]}
# B06/B07: test only; B road network includes parts of broader corridor and may not be connected via legal access.
DRIVE_CLASSES={'motorway','trunk','primary','secondary','tertiary','unclassified','residential',
               'service','living_street','motorway_link','trunk_link','primary_link','secondary_link','tertiary_link'}

def haversine(a,b,c,d):
 r=6371008.8; la,lo,lb,lc=map(radians,(b,a,d,c))
 aa=sin((lb-la)/2)**2 + cos(la)*cos(lb)*sin((lc-lo)/2)**2
 return 2*r*asin(min(1,sqrt(aa)))

def get_snapshot(area):
 filename,expected,_=META[area];p=CACHE/filename
 if not p.exists():
  print('Downloading source snapshot',area,'~15MB via GitHub...',flush=True)
  try:urlretrieve(REPO+filename,str(p))
  except Exception as exc: raise RuntimeError('No cached snapshot and download failed: '+str(exc))
 digest=sha256(p.read_bytes()).hexdigest()
 if digest!=expected:
  raise RuntimeError('%s snapshot SHA256 mismatch; expected %s got %s. Do NOT route with changed source'%(area,expected,digest))
 return json.loads(p.read_text(encoding='utf-8'))

def create_graph(data):
 elements=data['elements']
 coords={int(e['id']):(float(e['lon']),float(e['lat'])) for e in elements if e['type']=='node' and 'lat'in e and 'lon'in e}
 graph={};edges=0
 for item in elements:
  if item['type']!='way':continue
  tag=item.get('tags',{});hwy=tag.get('highway')
  if hwy not in DRIVE_CLASSES:continue
  if tag.get('access') in ('no','private') or tag.get('motor_vehicle') in ('no','private') or tag.get('motorcar') in ('no','private'):continue
  if tag.get('service')=='emergency_access':continue
  waynodes=item.get('nodes',[])
  isone=str(tag.get('oneway','')).lower()
  rev=isone=='-1'
  if rev:waynodes=list(reversed(waynodes))
  forward_only=rev or isone in ('yes','true','1') or tag.get('junction')=='roundabout' or hwy=='motorway'
  for u,v in zip(waynodes,waynodes[1:]):
   if u not in coords or v not in coords:continue
   a,b=coords[u],coords[v]
   w=haversine(*a,*b)
   if w<0.5:continue
   graph.setdefault(u,[]).append((v,w));edges+=1
   if not forward_only:graph.setdefault(v,[]).append((u,w));edges+=1
 return coords,graph,edges

def snap(p,coords,graph,max_m=300):
 lon,lat=p;_,_,latmax,lonmax=(0,0,0,0)  # explicit WGS84 lon/lat
 best=(float('inf'),None)
 for node in graph:
  x,y=coords[node]
  # cheap bounding check: ~0.008 deg < 1 km
  if abs(x-lon)>0.012 or abs(y-lat)>0.012:continue
  d=haversine(lon,lat,x,y)
  if d<best[0]:best=(d,node)
 if best[0]>max_m:return None,best[0]
 return best[1],best[0]

def dijkstra(graph,origin,target):
 heap=[(0.,origin)];best={origin:0.};pre={}
 while heap:
  cur,u=heapq.heappop(heap)
  if cur!=best[u]:continue
  if u==target:
   rev=[u]
   while u!=origin:u=pre[u];rev.append(u)
   return cur,list(reversed(rev))
  for v,d in graph.get(u,()):
   new=cur+d
   if new<best.get(v,float('inf')):
    best[v]=new;pre[v]=u;heapq.heappush(heap,(new,v))
 return None,None

def route_area(area):
 data=get_snapshot(area);coords,graph,edges=create_graph(data)
 print(area,'OSM nodes',len(coords),'driveable directed edges',edges)
 records=[];feats=[]
 for frm,to in JOBS[area]:
  src,sm=snap(POINTS[frm],coords,graph);dst,dm=snap(POINTS[to],coords,graph)
  if src is None or dst is None:
   state='NO_VALID_ENDPOINT_SNAP_WITHIN_300M';dist=None;sequence=None
  else:
   dist,sequence=dijkstra(graph,src,dst)
   state='OSM_GEOMETRIC_ROUTE_ONLY' if sequence else 'NO_CONNECTED_DIRECTED_PATH'
  rec=dict(area=area,from_id=frm,to_id=to,status=state,
   osm_origin_snap_m=round(sm,1),osm_destination_snap_m=round(dm,1),
   route_km=round(dist/1000,3) if dist is not None else '',
   link_count=len(sequence)-1 if sequence else 0,
   frozen_osm_sha256=META[area][1],traffic_travel_time='NOT_ESTIMATED',
   site_gate_verified='NO',turn_restrictions='NOT_MODELED',country_boundary_check='NOT_VERIFIED',
   road_access='HIGHWAY_ONLY_NO_PARCEL_ACCESS_PROOF')
  records.append(rec)
  if sequence:
   feats.append({'type':'Feature','properties':rec,
       'geometry':{'type':'LineString','coordinates':[list(coords[n]) for n in sequence]}})
  print(frm,'->',to, state,rec['route_km'],'km, snap',rec['osm_origin_snap_m'],rec['osm_destination_snap_m'])
 return records,feats

all_records=[];all_feats=[]
for area in ['A','B']:
 try:
  rr,ff=route_area(area)
 except Exception as exc:
  print('FAILED area',area,exc)
  rr=[{'area':area,'status':'NO_ROUTE_SOURCE_AVAILABLE_OR_HASH_MISMATCH','reason':str(exc)}]
  ff=[]
 all_records+=rr;all_feats+=ff
with (OUT/'OSM_road_routes_A_B_BASELINE_ONLY.geojson').open('w',encoding='utf-8') as f:
 json.dump({'type':'FeatureCollection','features':all_feats},f,ensure_ascii=False)
cols=list(dict.fromkeys(k for record in all_records for k in record))
with (OUT/'OSM_road_route_A_B_QA.csv').open('w',encoding='utf-8-sig',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader();writer.writerows(all_records)
(OUT/'ROUTE_STATUS.txt').write_text('Generated: '+datetime.datetime.now(datetime.timezone.utc).isoformat()+'\nRoad route geometries are model paths derived from a frozen OSM snapshot. No parcel gate, turn restrictions, road closures, FCD speed calibration, traffic-dependent travel time, or air permissions validated.\n',encoding='utf8')
print('Saved',len(all_feats),'OSM baseline route geometries. Failure cases retained in QA.csv')
