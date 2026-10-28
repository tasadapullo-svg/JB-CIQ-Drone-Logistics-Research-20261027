#!/usr/bin/env python3
"""E02 auditable OSM directed road network and conditional OD estimator.

Source: OpenStreetMap Overpass JSON elements. Only geometric/network proof is claimed.
No commercial FCD is redistributed, no unknown direction is assumed to be observed.
"""
from __future__ import annotations
import argparse, collections, csv, datetime as dt, hashlib, json, math, os, pathlib, time
import networkx as nx
from pyproj import Geod, Transformer
import numpy as np
import pandas as pd
import requests
from scipy.spatial import cKDTree
from shapely.geometry import Point, LineString
from shapely.strtree import STRtree

GEOD=Geod(ellps='WGS84')
T=Transformer.from_crs('EPSG:4326','EPSG:32648',always_xy=True)
BBOX={
 'A':(1.435,103.710,1.550,103.850),
 'B':(1.320,103.515,1.485,103.690),
}
HIGHWAYS=('motorway','trunk','primary','secondary','tertiary','unclassified','residential','living_street','service','motorway_link','trunk_link','primary_link','secondary_link','tertiary_link')
DEFAULTS={
 'motorway':90,'trunk':75,'primary':55,'secondary':50,'tertiary':40,
 'unclassified':30,'residential':25,'living_street':10,'service':15,
 'motorway_link':45,'trunk_link':40,'primary_link':35,'secondary_link':30,'tertiary_link':25
}

def mkdir(x): pathlib.Path(x).mkdir(parents=True,exist_ok=True)
def hashfile(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for part in iter(lambda:f.read(2**20),b''):h.update(part)
 return h.hexdigest()
def writecsv(p,rows,fields):
 with open(p,'w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def preflight(args):
 reg=pd.read_csv(args.registry,dtype={'node_id':str});sites=pd.read_csv(args.sites,dtype={'site_id':str})
 assert reg.node_id.nunique()==345 and len(reg)==345,'Expected 345 unique FCD nodes'
 assert set(reg.group_id)==set('G1 G2 G3 G4 G5'.split())
 assert sites.site_id.nunique()==19 and set(sites.area)=={'A','B'}
 print('PRECHECK nodes',len(reg),'sites',len(sites))
 mkdir(args.out)
 site_rows=[]
 for _,r in sites.iterrows():
  a=r['area'];lat=float(r.latitude);lon=float(r.longitude);b=BBOX[a]
  site_rows.append({'site_id':r.site_id,'area':a,'place_name':r.place_name,'latitude':lat,'longitude':lon,'within_acquisition_bbox':b[0]<=lat<=b[2] and b[1]<=lon<=b[3],
                    'role':'GATEWAY_REFERENCE_NOT_AN_OD' if str(r.place_type)=='CIQ_reference' else 'REFERENCE_ANCHOR_NOT_CONFIRMED_SITE',
                    'site_operational_approval':'UNKNOWN','FCD_sample_node':'NO'})
 writecsv(os.path.join(args.out,'01_site_scope_audit.csv'),site_rows,list(site_rows[0]))
 fcd_rows=[]
 for _,r in reg.iterrows():
  memberships=';'.join([k for k,b in BBOX.items() if b[0]<=r.latitude<=b[2] and b[1]<=r.longitude<=b[3]])
  fcd_rows.append({'node_id':r.node_id,'group_id':r.group_id,'latitude':r.latitude,'longitude':r.longitude,'acquisition_areas':memberships or 'OUTSIDE_BOTH',
                   'road_name_evidence':r.name_evidence_status,'direction_verified':'NO'})
 writecsv(os.path.join(args.out,'02_345node_scope_audit.csv'),fcd_rows,list(fcd_rows[0]))
 # OD pairs are geographic reference anchors, not parcel orders.
 od=[]
 for a in 'AB':
  z=sites[(sites.area==a)&(sites.place_type!='CIQ_reference')]
  for _,s in z.iterrows():
   for _,t in z.iterrows():
    if s.site_id==t.site_id:continue
    _,_,dist=GEOD.inv(float(s.longitude),float(s.latitude),float(t.longitude),float(t.latitude))
    od.append({'area':a,'origin_id':s.site_id,'destination_id':t.site_id,'origin_name':s.place_name,'destination_name':t.place_name,
               'beeline_km':round(dist/1000,3),'order_status':'REFERENCE_ONLY_NO_REAL_DEMAND','site_status':'UNVERIFIED'})
 writecsv(os.path.join(args.out,'03_reference_OD_pairs_NOT_ORDERS.csv'),od,list(od[0]))
 print('OD_REFERENCE pairs',len(od),'by area',dict(collections.Counter(x['area'] for x in od)))


def fetch(args):
 mkdir(args.out)
 out=pathlib.Path(args.out)/f'OSM_{args.area}_overpass_response.json'
 if out.exists() and not args.force:
  print('CACHED',out,hashfile(out));return
 bbox=BBOX[args.area]
 b=','.join(f'{x:.6f}' for x in bbox)
 tags='|'.join(HIGHWAYS)
 query=f'[out:json][timeout:240];way["highway"~"^({tags})$"]({b});(._;>;);out body;'
 servers=['https://overpass.kumi.systems/api/interpreter','https://overpass-api.de/api/interpreter','https://overpass.nchc.org.tw/api/interpreter']
 last=None
 for i in range(args.retries):
  for srv in servers:
   try:
    res=requests.post(srv,data={'data':query},timeout=320,headers={'User-Agent':'JB-CIQ-Research-E02/1.0 research reproducibility'})
    if res.status_code in (429,502,503,504):raise RuntimeError('rate limited/status '+str(res.status_code))
    res.raise_for_status();obj=res.json()
    if not obj.get('elements'):raise RuntimeError('Overpass returned zero elements')
    out.write_text(json.dumps(obj,ensure_ascii=False),encoding='utf-8')
    (pathlib.Path(args.out)/f'OSM_{args.area}_download_metadata.json').write_text(json.dumps({'endpoint':srv,'bbox_S_W_N_E':bbox,'downloaded_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'sha256':hashfile(out),'elements':len(obj['elements'])},indent=2),encoding='utf-8')
    print('DOWNLOADED',out,len(obj['elements']),hashfile(out));return
   except Exception as e:
    last=str(e);print('DOWNLOAD RETRY',srv,last,flush=True)
  time.sleep(min(30*(i+1),120))
 raise RuntimeError('OSM download unavailable; no GIS network created. Last error: '+str(last))


def eligible(tags):
 hw=tags.get('highway');
 if hw not in HIGHWAYS:return False
 if tags.get('area')=='yes':return False
 if tags.get('access') in ('no','private') or tags.get('motor_vehicle') in ('no','private') or tags.get('motorcar') in ('no','private') or tags.get('vehicle')=='no':return False
 if tags.get('construction') or tags.get('proposed')=='yes':return False
 return True

def oneway(tags):
 ow=str(tags.get('oneway','')).lower();
 if ow in ('yes','true','1'):return 1
 if ow in ('-1','reverse'):return -1
 if ow in ('no','false','0'):return 0
 if tags.get('junction') in ('roundabout','circular'):return 1
 if tags.get('highway') in ('motorway','motorway_link'):return 1
 return 0

def maxspeed(tags):
 val=str(tags.get('maxspeed','')).strip().lower()
 import re
 m=re.search(r'\d+(?:\.\d+)?',val)
 if m:
  v=float(m.group());v=v*1.609344 if 'mph' in val else v
  if 5<=v<=135:return (v,'OSM_TAG')
 return DEFAULTS.get(tags.get('highway'),25),'CLASS_ASSUMPTION'

def construct_graph(obj):
 coords={int(e['id']):(e['lat'],e['lon']) for e in obj['elements'] if e.get('type')=='node' and 'lat'in e}
 G=nx.MultiDiGraph();way_count=0
 for w in obj['elements']:
  if w.get('type')!='way':continue
  tags=w.get('tags',{})
  if not eligible(tags):continue
  nd=[int(x) for x in w['nodes']];direction=oneway(tags);speed,sourcespeed=maxspeed(tags)
  way_count+=1
  for u,v in zip(nd[:-1],nd[1:]):
   if u not in coords or v not in coords:continue
   la1,lo1=coords[u];la2,lo2=coords[v];_,_,d=GEOD.inv(lo1,la1,lo2,la2)
   if d<=0:continue
   base=dict(way_id=int(w['id']),highway=tags.get('highway'),name=tags.get('name',''),ref=tags.get('ref',''),length_m=round(d,3),osm_maxspeed_kmh=speed,
             speed_source=sourcespeed,oneway=direction,bridge=tags.get('bridge',''),tunnel=tags.get('tunnel',''),access=tags.get('access',''),time_reference='MODEL_NOT_MEASURED',
             valid_turns='UNKNOWN_NOT_PARSED')
   for k in (u,v):
    if k not in G:
     la,lo=coords[k];G.add_node(k,lat=la,lon=lo)
   if direction>=0:G.add_edge(u,v,**base,kmh=speed,minutes=d/1000/speed*60,direction='FORWARD')
   if direction<=0:G.add_edge(v,u,**base,kmh=speed,minutes=d/1000/speed*60,direction='BACKWARD')
 return G,way_count

def kdtree_for_graph(G):
 nd=list(G.nodes);xy=np.asarray([T.transform(G.nodes[n]['lon'],G.nodes[n]['lat']) for n in nd],dtype=float)
 return nd,cKDTree(xy)

def nearest_points(df,ids,tree,G,kind='FCD',area=''):
 rows=[]
 for _,r in df.iterrows():
  lat=float(r['latitude']);lon=float(r['longitude']);xy=T.transform(lon,lat)
  d,i=tree.query(xy,k=1);n=ids[int(i)]
  rows.append({'area':area,'point_kind':kind,'point_id':r.get('node_id',r.get('site_id','')), 'reference_latitude':lat,'reference_longitude':lon,
               'nearest_osm_node_id':int(n),'nearest_node_distance_m':round(float(d),2),
               'snap_status':'NEAR_NODE_REVIEW' if d<=100 else 'TOO_FAR_TO_SNAP',
               'FCD_direction_evidence':'NOT_VERIFIED' if kind=='FCD' else '', 'review_note':'Nearest graph node, not nearest directed way; manual directional road match required'})
 return rows

def edge_candidates(G,df,area):
    """Spatial-only nearest road-edge candidates: no inferred FCD travel direction."""
    unique={}
    for u,v,k,tag in G.edges(keys=True,data=True):
        key=(min(u,v),max(u,v),tag['way_id'])
        if key not in unique: unique[key]=(u,v,tag)
    triples=list(unique.values())
    shapes=[]
    for u,v,tag in triples:
        la1=G.nodes[u]['lat'];lo1=G.nodes[u]['lon']
        la2=G.nodes[v]['lat'];lo2=G.nodes[v]['lon']
        shapes.append(LineString([T.transform(lo1,la1),T.transform(lo2,la2)]))
    tree=STRtree(shapes)
    rows=[]
    for _,r in df.iterrows():
        p=Point(*T.transform(float(r.longitude),float(r.latitude)))
        i=int(tree.nearest(p));u,v,t=triples[i]
        dist=round(p.distance(shapes[i]),2)
        rows.append({'area':area,'node_id':r.node_id,'group_id':r.group_id,'fcd_latitude':r.latitude,'fcd_longitude':r.longitude,
                     'nearest_osm_way_id':t['way_id'],'nearest_osm_road_name':t['name'],'nearest_osm_road_class':t['highway'],
                     'match_distance_m':dist,'frozen_road_name_evidence':r.name_evidence_status,
                     'possible_directed_osm_edges':'UNKNOWN_FCD_DIRECTION',
                     'candidate_status':'NEEDS_EXTERNAL_DIRECTION_PROOF' if dist<=30 else ('DISTANCE_REVIEW_30_80M' if dist<=80 else 'REJECT_GT_80M'),
                     'match_approved':'FALSE', 'observation_assigned_to_road_speed':'FALSE'})
    return rows

def route(G,s,t):
 path=nx.shortest_path(G,s,t,weight='minutes',method='dijkstra')
 trip=[]
 for u,v in zip(path[:-1],path[1:]):
  edges=G[u][v]
  best=min(edges.items(),key=lambda kv:kv[1]['minutes'])[1]
  trip.append(best)
 return path,trip

def build(args):
 mkdir(args.out)
 data=json.loads(pathlib.Path(args.input).read_text(encoding='utf-8'))
 G,n_ways=construct_graph(data)
 if G.number_of_edges()==0:raise RuntimeError('No graph edges from OSM JSON')
 nodes,tree=kdtree_for_graph(G)
 reg=pd.read_csv(args.registry,dtype={'node_id':str});sites=pd.read_csv(args.sites,dtype={'site_id':str})
 b=BBOX[args.area]
 reg=reg[(reg.latitude.between(b[0],b[2]))&(reg.longitude.between(b[1],b[3]))]
 sites=sites[(sites.area==args.area)&(sites.place_type!='CIQ_reference')]
 fm=nearest_points(reg,nodes,tree,G,'FCD',args.area)
 ec=edge_candidates(G,reg,args.area)
 writecsv(os.path.join(args.out,f'E02_{args.area}_FCD_to_OSM_edge_CANDIDATES_NOT_APPROVED.csv'),ec,list(ec[0]))
 sm=nearest_points(sites,nodes,tree,G,'SITE',args.area)
 writecsv(os.path.join(args.out,f'E02_{args.area}_FCD_nearest_road_nodes_UNVERIFIED.csv'),fm,list(fm[0]))
 writecsv(os.path.join(args.out,f'E02_{args.area}_site_nearest_road_nodes_UNVERIFIED.csv'),sm,list(sm[0]))
 sidx={r['point_id']:r for r in sm}
 od=[]
 for origin in sites.itertuples(index=False):
  for dest in sites.itertuples(index=False):
   if origin.site_id==dest.site_id:continue
   a=sidx[origin.site_id];b=sidx[dest.site_id]
   _,_,beeline=GEOD.inv(float(origin.longitude),float(origin.latitude),float(dest.longitude),float(dest.latitude))
   rec={'area':args.area,'origin_id':origin.site_id,'destination_id':dest.site_id,'beeline_km':round(beeline/1000,4),'snap_origin_m':a['nearest_node_distance_m'], 'snap_destination_m':b['nearest_node_distance_m'],
        'OSM_graph_snapshot_sha256':hashfile(args.input),'route_length_km':'','OSM_only_minutes_MODEL':'','circuity_ratio':'','path_edge_count':'','fcd_observed_length_share':0,
        'turn_restrictions':'NOT_MODELED','country_boundary':'NOT_VERIFIED','access_leg':'SNAP_DISTANCE_ONLY',
        'time_output_claim':'OSM_ASSUMPTION_NOT_REAL_TRAFFIC_TIME','status':'NO_ROUTE'}
   if a['snap_status']=='TOO_FAR_TO_SNAP' or b['snap_status']=='TOO_FAR_TO_SNAP':rec['status']='SNAP_REVIEW_REQUIRED'
   else:
    try:
     _,edges=route(G,a['nearest_osm_node_id'],b['nearest_osm_node_id'])
     le=sum(e['length_m'] for e in edges);m=sum(e['minutes'] for e in edges)
     rec.update(route_length_km=round(le/1000,4),OSM_only_minutes_MODEL=round(m,4),circuity_ratio=round(le/beeline,4) if beeline>0 else '',path_edge_count=len(edges),status='MODEL_ROUTE_REQUIRES_QA')
    except nx.NetworkXNoPath:rec['status']='DISCONNECTED_IN_OSM'
   od.append(rec)
 writecsv(os.path.join(args.out,f'E02_{args.area}_OD_OSM_MODEL_NOT_OBSERVED.csv'),od,list(od[0]))
 # Geographic geometry shows the highway ways actually received, do not draw phantom roads.
 edges=[]
 for u,v,k,d in G.edges(keys=True,data=True):
  edges.append({'source':int(u),'target':int(v),'osm_way_id':d['way_id'],'direction':d['direction'], 'length_m':d['length_m'],
                'speed_kmh':d['kmh'],'speed_source':d['speed_source'],'highway':d['highway'], 'osm_name':d['name']})
 writecsv(os.path.join(args.out,f'E02_{args.area}_directed_edges_OSM.csv'),edges,list(edges[0]))
 node_rows=[{'osm_node_id':int(n),'latitude':d['lat'],'longitude':d['lon']} for n,d in G.nodes(data=True)]
 writecsv(os.path.join(args.out,f'E02_{args.area}_road_graph_nodes.csv'),node_rows,list(node_rows[0]))
 # Native QGIS-consumable directed geometry, generated from actual OSM node coordinates.
 geo=pathlib.Path(args.out)/f'E02_{args.area}_road_graph_directed_OSM.geojson'
 with geo.open('w',encoding='utf-8') as h:
     h.write('{"type":"FeatureCollection","features":[')
     for j,(u,v,k,d) in enumerate(G.edges(keys=True,data=True)):
         if j:h.write(',')
         h.write(json.dumps({'type':'Feature','properties':{'osm_way_id':d['way_id'],'source_node':u,'target_node':v,'direction':d['direction'],'highway':d['highway'],'length_m':d['length_m']},'geometry':{'type':'LineString','coordinates':[[G.nodes[u]['lon'],G.nodes[u]['lat']],[G.nodes[v]['lon'],G.nodes[v]['lat']]]}},ensure_ascii=False,separators=(',',':')))
     h.write(']}')
 stats={'area':args.area,'input_file':str(args.input),'input_sha256':hashfile(args.input),'OSM_ways_pass_filter':n_ways,
     'graph_nodes':G.number_of_nodes(),'directed_edges':G.number_of_edges(),'weak_components':nx.number_weakly_connected_components(G),
     'OSM_edge_length_km':round(sum(d['length_m'] for _,_,d in G.edges(data=True))/1000,2),
     'fcd_nearest_review_100m':sum(r['snap_status']=='NEAR_NODE_REVIEW' for r in fm),'fcd_nodes_examined':len(fm),'FCD_edge_candidates_within_30m':sum(x['match_distance_m']<=30 for x in ec),'FCD_edge_candidates_rejected_gt80m':sum(x['match_distance_m']>80 for x in ec),
     'sites_nearest_review_100m':sum(r['snap_status']=='NEAR_NODE_REVIEW' for r in sm),'sites_examined':len(sm),
     'OD_pairs':len(od),'OD_model_route_count':sum(r['status']=='MODEL_ROUTE_REQUIRES_QA' for r in od),
     'OD_confirmed_traffic_travel_time_count':0,
     'oneway_encoded':True,'turn_relations_encoded':False,'MY_SG_boundary_verified':False,'FCD_direction_verified':False,
     'routing_readiness':'GEOMETRY_ONLY_NOT_RESEARCH_OD','study_area_bbox_not_legal_boundary':BBOX[args.area]}
 pathlib.Path(args.out,f'E02_{args.area}_logic_QA.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
 print(json.dumps(stats,ensure_ascii=False,indent=2))

def main():
 p=argparse.ArgumentParser()
 sub=p.add_subparsers(dest='cmd',required=True)
 a=sub.add_parser('preflight');a.add_argument('--registry',required=True);a.add_argument('--sites',required=True);a.add_argument('--out',required=True)
 a=sub.add_parser('fetch');a.add_argument('--area',choices=['A','B'],required=True);a.add_argument('--out',required=True);a.add_argument('--force',action='store_true');a.add_argument('--retries',type=int,default=3)
 a=sub.add_parser('build');a.add_argument('--area',choices=['A','B'],required=True);a.add_argument('--input',required=True);a.add_argument('--registry',required=True);a.add_argument('--sites',required=True);a.add_argument('--out',required=True)
 args=p.parse_args()
 {'preflight':preflight,'fetch':fetch,'build':build}[args.cmd](args)
if __name__=='__main__':main()
