#!/usr/bin/env python3
"""Read a separately retrieved V5 A/B/C directed GraphML; candidate road OD only.
OSM topology never substitutes for an approved site entrance, legal border or observed travel time.
"""
import argparse,csv,hashlib,json,math,sys
from collections import Counter
from pathlib import Path

import networkx as nx


def load_csv(path):
 with open(path,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def edge_length(k):
 try:
  val=float(k.get('length',k.get('length_m',float('nan'))))
  return val if math.isfinite(val) and val>0 else None
 except (ValueError,TypeError):return None


def graph_validity(G):
 errors=Counter();edge_count=0
 for u,v,d in G.edges(data=True):
  edge_count+=1
  if edge_length(d) is None:errors['edge_length_nonpositive_or_missing']+=1
  if u==v:errors['self_loop_review']+=1
 for k,d in G.nodes(data=True):
  try:
   lat=float(d['y']);lon=float(d['x'])
   if not(-90<=lat<=90 and -180<=lon<=180):errors['invalid_coordinate']+=1
  except (KeyError,ValueError,TypeError):errors['invalid_coordinate']+=1
 return {'node_count':G.number_of_nodes(),'directed_edge_count':edge_count,'is_directed':G.is_directed(),
   'invalid_coordinate':errors['invalid_coordinate'],'invalid_length':errors['edge_length_nonpositive_or_missing'],
   'self_loops_for_review':errors['self_loop_review'],'weak_component_count':nx.number_weakly_connected_components(G) if G.is_directed() else None}


def nearest_candidate_snaps(G,nodes,threshold_m=100):
 import numpy as np
 from scipy.spatial import cKDTree
 from pyproj import Transformer
 tr=Transformer.from_crs('EPSG:4326','EPSG:32648',always_xy=True)
 ids=[];loc=[]
 for id,x in G.nodes(data=True):
  try:
   xx,yy=tr.transform(float(x['x']),float(x['y']))
   if math.isfinite(xx) and math.isfinite(yy):loc.append([xx,yy]);ids.append(id)
  except (KeyError,ValueError,TypeError):pass
 if not loc:raise ValueError('EMPTY_GRAPH_COORDS')
 tree=cKDTree(np.asarray(loc));snaps=[]
 for n in nodes:
  x,y=tr.transform(float(n['longitude_E']),float(n['latitude_N']))
  dist,index=tree.query([x,y]);d=float(dist)
  snaps.append({'node_id':n['node_id'],'zone':n['zone'],'osm_node_id':str(ids[index]),'snap_distance_m':round(d,2),
    'candidate_gate_status':'CANDIDATE_WITHIN_100M_NOT_LEGAL_ENTRANCE' if d<=threshold_m else 'HOLD_GT_100M',
    'actual_facility_entrance_verified':'NO','turn_restrictions_verified':'NO','border_crossing_approved':'NO'})
 return snaps


def build_simple_length_graph(G):
 """Min-length parallel directed edges, as conditional *road-distance* proxy only."""
 D=nx.DiGraph()
 for u,v,d in G.edges(data=True):
  length=edge_length(d)
  if length is None:continue
  if not D.has_edge(u,v) or length<D[u][v]['length_m']:D.add_edge(u,v,length_m=length)
 return D


def route_candidate_matrix(G,snaps,orders):
 mapping={s['node_id']:s for s in snaps};D=build_simple_length_graph(G)
 pairs=sorted({(o['origin_node_id'],o['destination_node_id']) for o in orders})
 by_origin={}
 for a,b in pairs:by_origin.setdefault(a,[]).append(b)
 outputs=[]
 for origin,dests in by_origin.items():
  snap=mapping[origin]
  if not snap['candidate_gate_status'].startswith('CANDIDATE'):
   for dest in dests:outputs.append({'origin_node_id':origin,'destination_node_id':dest,'route_length_m':'','status':'HOLD_ORIGIN_ACCESS'})
   continue
  start=snap['osm_node_id'];lengths=nx.single_source_dijkstra_path_length(D,start,weight='length_m') if start in D else {}
  for dest in dests:
   target=mapping[dest]
   if not target['candidate_gate_status'].startswith('CANDIDATE'):state='HOLD_DEST_ACCESS';distance=None
   elif target['osm_node_id'] not in lengths:state='HOLD_DIRECTED_DISCONNECTED';distance=None
   else:state='OSM_DIRECTED_DISTANCE_CANDIDATE_ONLY';distance=lengths[target['osm_node_id']]
   outputs.append({'origin_node_id':origin,'destination_node_id':dest,'route_length_m':round(distance,2) if distance is not None else '',
     'status':state,'observed_travel_time':'NO','FCD_direction_calibrated':'NO','Malaysia_only_legal_route_verified':'NO'})
 return outputs


def run(graphml,nodes_csv,orders_csv,out):
 out.mkdir(parents=True,exist_ok=True)
 nodes=load_csv(nodes_csv);orders=load_csv(orders_csv)
 assert len(nodes)==68 and len(orders)==82620
 G=nx.read_graphml(graphml)
 stats=graph_validity(G)
 if not stats['is_directed'] or stats['invalid_coordinate'] or stats['invalid_length']:
  audit={'status':'HOLD_INVALID_GRAPH','stats':stats}
 else:
  snaps=nearest_candidate_snaps(G,nodes)
  with (out/'S07_V5_68_OSM_DIRECTED_NEAREST_CANDIDATES.csv').open('w',newline='',encoding='utf-8-sig') as f:
   w=csv.DictWriter(f,fieldnames=list(snaps[0]));w.writeheader();w.writerows(snaps)
  matrix=route_candidate_matrix(G,snaps,orders)
  with (out/'S07_V5_DIRECTIONAL_OD_OSM_LENGTH_CANDIDATES.csv').open('w',newline='',encoding='utf-8-sig') as f:
   w=csv.DictWriter(f,fieldnames=list(matrix[0]));w.writeheader();w.writerows(matrix)
  audit={'status':'CONDITIONAL_OSM_MODEL_ONLY_NO_LEGAL_OR_FCD_CALIBRATION','graph_stats':stats,
   'all_68_nodes_preserved':len(snaps),'nodes_within_100m_candidates':sum(s['candidate_gate_status'].startswith('CANDIDATE') for s in snaps),
   'directed_unique_OD':len(matrix),'candidate_routes':sum(x['status']=='OSM_DIRECTED_DISTANCE_CANDIDATE_ONLY' for x in matrix),
   'source_graphml_sha256':hashlib.sha256(graphml.read_bytes()).hexdigest(),
   'S07_FORMAL_ROAD_GATE':'HOLD_MANUAL_ENTRANCES_CROSS_BORDER_TURNS_AND_FCD_DIRECTION',
   'note':'Graph retrieved at execution time, not necessarily historic May-Sep 2026 snapshot'}
 (out/'S07_V5_ABC_ROAD_CANDIDATE_AUDIT.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(audit,ensure_ascii=False)[:1000]);return audit

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--graphml',type=Path,required=True);p.add_argument('--nodes',type=Path,required=True);p.add_argument('--orders',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 run(a.graphml,a.nodes,a.orders,a.out)
