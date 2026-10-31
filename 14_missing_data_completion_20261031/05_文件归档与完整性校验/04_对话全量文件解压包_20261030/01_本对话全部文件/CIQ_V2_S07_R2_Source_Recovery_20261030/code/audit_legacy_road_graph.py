#!/usr/bin/env python3
"""Independent OSM A/B graph topology QA and node snap CANDIDATES only.
Does not infer access rights, turn restrictions, actual traffic speeds or C network coverage.
"""
import argparse,csv,heapq,json,math,pathlib,collections

def readcsv(p):
    with pathlib.Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def distance_m(lat1,lon1,lat2,lon2):
    la1,la2=map(math.radians,(lat1,lat2));dlat=la2-la1;dlon=math.radians(lon2-lon1)
    x=math.sin(dlat/2)**2+math.cos(la1)*math.cos(la2)*math.sin(dlon/2)**2
    return 6371008.8*2*math.asin(min(1,math.sqrt(x)))

def snap(nodes,lat,lon):
    # latitude-longitude buckets improve search without introducing snap-to-road fabrication
    step=.008;key=(int(math.floor(lat/step)),int(math.floor(lon/step)))
    hits=[]
    for stepnum in range(1,7):
        for i in range(key[0]-stepnum,key[0]+stepnum+1):
            for j in range(key[1]-stepnum,key[1]+stepnum+1):hits.extend(nodes.get((i,j),[]))
        if hits:break
    if not hits:return None
    return min(((distance_m(lat,lon,a,b),n) for n,a,b in hits),default=None)

def qa(folder,site_csv,out):
    folder=pathlib.Path(folder);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
    rows=readcsv(site_csv);aud=[];site=[]
    for area in ['A','B']:
        ep=folder/f'E02_{area}_directed_edges_OSM.csv';np=folder/f'E02_{area}_road_graph_nodes.csv'
        if not ep.exists() or not np.exists():
            aud.append({'area':area,'status':'HOLD_OSM_FILES_MISSING','nodes':0,'arcs':0})
            for r in rows:
                if r['zone']==area:site.append({'node_id':r['node_id'],'zone':area,'candidate_osm_node_id':'','nearest_node_distance_m':'','status':'HOLD_OSM_GRAPH_MISSING','road_vehicle_access_approved':'NO','source':'LEGACY_GRAPH_NOT_RETRIEVED'})
            continue
        graph=collections.defaultdict(list);seen=set();edge_n=0;rejected=0
        with ep.open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                try:
                    u=int(row['source']);v=int(row['target']);length=float(row['length_m'])
                    if not math.isfinite(length) or length<=0:raise ValueError('bad length')
                    graph[u].append((v,length));seen.add(u);seen.add(v);edge_n+=1
                except Exception:rejected+=1
        bins=collections.defaultdict(list)
        with np.open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                try:
                    lat=float(row['latitude']);lon=float(row['longitude']);n=int(row['osm_node_id'])
                    bins[(int(math.floor(lat/.008)),int(math.floor(lon/.008)))].append((n,lat,lon))
                except Exception:rejected+=1
        audited=0
        for r in rows:
            if r['zone']!=area:continue
            match=snap(bins,float(r['latitude']),float(r['longitude']))
            site.append({'node_id':r['node_id'],'zone':area,'candidate_osm_node_id':match[1] if match else '',
                         'nearest_node_distance_m':round(match[0],2) if match else '',
                         'status':'CANDIDATE_NEEDS_EDGE_ACCESS_AND_TURN_QA' if match and match[0]<=100 else 'HOLD_NEAREST_NODE_GT100M_OR_MISSING',
                         'road_vehicle_access_approved':'NO','source':'LEGACY_AB_OSM_TOPOLOGY_ONLY'})
            audited+=1
        aud.append({'area':area,'status':'HISTORIC_GRAPH_TOPOLOGY_READ_NOT_OPERATIONAL_RELEASE','nodes_in_arcs':len(seen),'arcs':edge_n,'malformed_rows':rejected,'nodes_checked':audited,'edge_direction_retained':True})
    for r in rows:
        if r['zone'] not in ('A','B'):site.append({'node_id':r['node_id'],'zone':r['zone'],'candidate_osm_node_id':'','nearest_node_distance_m':'','status':'HOLD_NO_VERIFIED_GRAPH_FOR_ZONE_'+r['zone'],'road_vehicle_access_approved':'NO','source':'LEGACY_GRAPH_NOT_EXTENDABLE'})
    fields=['node_id','zone','candidate_osm_node_id','nearest_node_distance_m','status','road_vehicle_access_approved','source']
    with (out/'node_road_access_candidates_NOT_APPROVED.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(sorted(site,key=lambda x:x['node_id']))
    (out/'legacy_AB_graph_topology_audit.json').write_text(json.dumps(aud,indent=2),'utf-8')
    print(json.dumps({'graphs':aud,'site_rows':len(site),'release':'HOLD'}));return aud
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--sources',required=True);p.add_argument('--nodes',required=True);p.add_argument('--out',required=True);a=p.parse_args();qa(a.sources,a.nodes,a.out)
