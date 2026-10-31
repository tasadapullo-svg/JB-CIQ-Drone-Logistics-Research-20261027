#!/usr/bin/env python3
"""Download full V5 study-bbox drive graph using OSMnx 2.1.x, for scenario ROUTE CANDIDATES.
NOT a legal boundary, approved gate, turn restriction audit, historical road snapshot or observed travel speed.
No source project file is modified. Requires online Overpass in the executing environment.
"""
import argparse,csv,datetime as dt,json,pathlib,hashlib,math,collections

def rows(p):
 with open(p,'r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def hash_file(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()

def run(node_csv,out,download=False):
 out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
 nodes=rows(node_csv);assert len(nodes)==68 and len(set(x['node_id'] for x in nodes))==68
 lons=[float(x['longitude_E']) for x in nodes];lats=[float(x['latitude_N']) for x in nodes]
 margin=.025
 bbox=(min(lons)-margin,min(lats)-margin,max(lons)+margin,max(lats)+margin)
 audit={'status':'HOLD_NOT_DOWNLOADED', 'source':'OSM Overpass via OSMnx',
   'bbox_epsg4326_left_bottom_right_top':bbox,'num_v5_nodes':68,
   'snapshot':'CURRENT_OSM_AT_EXECUTION_NOT_HISTORICAL_2026_MAY_TO_SEPT',
   'scope_warning':'bbox includes locations possibly across MY/SG; cross-border access and wait times are NOT inferred',
   'legal_access_warning':'node snap is not proof of vehicle entrance, turn access, legal crossing, road passage or route validation',
   'source_v5_nodes_sha256':hash_file(node_csv)}
 if not download:
  audit['blocker']='RUN_WITH_--download_ONLY_ON_ONLINE_PC'
  (out/'V5_ABC_OSM_DOWNLOAD_AUDIT.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False),'utf-8')
  print(json.dumps(audit,ensure_ascii=False));return audit
 try:
  import osmnx as ox, networkx as nx
  assert ox.__version__.split('.')[0]=='2','ONLY_OSMNX_2_COMPATIBLE'
  ox.settings.use_cache=True;ox.settings.log_console=False
  G=ox.graph.graph_from_bbox(bbox,network_type='drive',simplify=True,retain_all=True,truncate_by_edge=True)
  assert G.is_directed() and len(G)>0
  audit.update(status='GRAPH_OBTAINED_NOT_OPERATIONALLY_ACCEPTED',retrieval_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
    osmnx_version=ox.__version__,nodes_G=G.number_of_nodes(),directed_arcs=G.number_of_edges(),weak_components=nx.number_weakly_connected_components(G))
  save=out/'V5_ABC_DRIVE_DIRECTED_OSM_SNAPSHOT_NOT_HISTORICAL.graphml'
  ox.io.save_graphml(G,filepath=save)
  audit['graphml_sha256']=hash_file(save)
  # Candidate snapping without assuming facility access or validated vehicle route.
  records=[];mapped={}
  for n in nodes:
   try:
    osm_n,dist=ox.distance.nearest_nodes(G,X=float(n['longitude_E']),Y=float(n['latitude_N']),return_dist=True)
    eligible=dist<=100
    mapped[n['node_id']]=int(osm_n) if eligible else None
    records.append({'node_id':n['node_id'],'zone':n['zone'],'nearest_osm_node':osm_n,
      'distance_to_candidate_road_node_m':round(float(dist),1),
      'status':'CANDIDATE_UNVERIFIED_GATE_AND_TURN' if eligible else 'HOLD_NODE_GT_100M',
      'road_access_legally_confirmed':'NO'})
   except Exception as e:
    mapped[n['node_id']]=None
    records.append({'node_id':n['node_id'],'zone':n['zone'],'nearest_osm_node':'',
      'distance_to_candidate_road_node_m':'','status':'HOLD_SNAP_ERROR:'+str(e)[:80],
      'road_access_legally_confirmed':'NO'})
  from csv import DictWriter
  with (out/'V5_68_OSM_NEAREST_NODES_NOT_APPROVED.csv').open('w',newline='',encoding='utf-8-sig') as f:
   wr=DictWriter(f,fieldnames=list(records[0]));wr.writeheader();wr.writerows(records)
  audit.update(nearest_node_candidates_at_100m=sum(r['status']=='CANDIDATE_UNVERIFIED_GATE_AND_TURN' for r in records),
    all_68_nodes_preserved=len(records), full_ABC_road_gate='HOLD_MANUAL_ENTRANCE_TURN_CROSS_BORDER_AND_HISTORICITY_CHECK')
 except Exception as e:
  audit.update(status='HOLD_OSM_DOWNLOAD_OR_PARSE_FAILED',error=repr(e)[:800])
 (out/'V5_ABC_OSM_DOWNLOAD_AUDIT.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False),'utf-8')
 print(json.dumps(audit,ensure_ascii=False));return audit
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--nodes',required=True);p.add_argument('--out',required=True);p.add_argument('--download',action='store_true');a=p.parse_args()
 run(a.nodes,a.out,a.download)
