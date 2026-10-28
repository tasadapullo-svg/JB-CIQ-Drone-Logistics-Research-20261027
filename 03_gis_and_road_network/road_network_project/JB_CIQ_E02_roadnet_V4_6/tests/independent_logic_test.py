import json, pathlib, sys, csv
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'code'))
from e02_roadnet import construct_graph, route, BBOX
root=pathlib.Path(__file__).parent
obj=json.loads((root/'synthetic_OSM_ONEWAY_not_real_roads.json').read_text())
G,ways=construct_graph(obj)
a=route(G,1001,1002);back=route(G,1002,1001)
assert ways==2
assert G.has_edge(1001,1002) and not G.has_edge(1002,1001), 'oneway restriction failed'
assert a[0]==[1001,1002],a[0]
assert back[0]==[1002,1003,1004,1001],back[0]
a_m=sum(e['minutes'] for e in a[1]);b_m=sum(e['minutes'] for e in back[1])
assert b_m>a_m, (a_m,b_m)
import pandas as pd
reg=pd.read_csv(root.parent/'inputs'/'FCD_345_frozen_registry.csv')
poi=pd.read_csv(root.parent/'inputs'/'19_site_reference_anchors_NOT_LAUNCH_PADS.csv')
assert len(reg)==345 and reg.node_id.nunique()==345
assert len(poi)==19 and poi.site_id.nunique()==19
for area in ['A','B']:
 site=poi[(poi.area==area)&(poi.place_type!='CIQ_reference')]
 od=list(csv.DictReader(open(root.parent/'outputs'/'03_reference_OD_pairs_NOT_ORDERS.csv',encoding='utf-8-sig')))
 assert sum(r['area']==area for r in od)==len(site)*(len(site)-1)
print(json.dumps({'PASS':True,'test':'synthetic directional routing and roster integrity','forward_minutes':round(a_m,5),'reverse_minutes':round(b_m,5),'source':'SYNTHETIC_FIXTURE_NOT_REAL_OSM'},indent=2))
