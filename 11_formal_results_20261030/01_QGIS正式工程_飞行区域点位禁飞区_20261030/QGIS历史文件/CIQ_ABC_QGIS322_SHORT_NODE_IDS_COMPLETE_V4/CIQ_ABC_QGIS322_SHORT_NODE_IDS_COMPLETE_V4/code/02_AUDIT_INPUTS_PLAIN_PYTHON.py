# -*- coding: utf-8 -*-
"""Independent QGIS-free check of the delivered editable GeoPackage.
Run with system Python: python code/02_AUDIT_INPUTS_PLAIN_PYTHON.py
Requires only Python's standard library. DOES NOT alter spatial inputs.
"""
from pathlib import Path
from math import sin,cos,asin,sqrt,radians
from collections import Counter
import csv,sqlite3,json,hashlib,sys
ROOT=Path(__file__).resolve().parent.parent
GPKG=ROOT/'data'/'CIQ_ABC_FINAL_EDITABLE.gpkg'
OUT=ROOT/'qa';OUT.mkdir(exist_ok=True)
con=sqlite3.connect(str(GPKG));con.row_factory=sqlite3.Row

def count(t):return con.execute('SELECT COUNT(*) FROM "'+t+'"').fetchone()[0]
expected={'V7_ALL_62_RETAINED_ROLES':62,'V7_ALL_111_GEOMETRY_ONLY':111,
          'V8_CIQ_PORT_6_EVIDENCE_POINTS':6,'V8_CIQ_PORT_10_GROUND_AND_UAV_GEOMETRY':10,
          'B_10_FROZEN_NOT_PADS':10,'B_33_FROZEN_reaudited':33,
          'G_CIQ_ground_gateway':1,'UAV_4_SITE_SEARCH_REACH_2_MODELS':8}
for t,n in expected.items():
 assert count(t)==n, (t,count(t),n)
assert con.execute('select count(*) from V7_ALL_62_RETAINED_ROLES where id="A11"').fetchone()[0]==0
assert con.execute("select count(*) from V7_ALL_111_GEOMETRY_ONLY where dji_distance_class='GEOMETRY_EXCEEDS_5P6_KM'").fetchone()[0]==17
assert con.execute("select count(*) from V8_CIQ_PORT_10_GROUND_AND_UAV_GEOMETRY where mode='UAV_GEOMETRY_SEARCH'").fetchone()[0]==5

nodes={}
for row in con.execute('select id,lat,lon,zone from V7_ALL_62_RETAINED_ROLES'):
 assert row['id'] not in nodes
 nodes[row['id']]=(float(row['lat']),float(row['lon']),row['zone'])
for row in con.execute('select node_id,lat,lon from V8_CIQ_PORT_6_EVIDENCE_POINTS'):
 assert row['node_id'] not in nodes
 nodes[row['node_id']]=(float(row['lat']),float(row['lon']),'A_PORT')
for row in con.execute('select id,lat,lon from G_CIQ_ground_gateway'):
 nodes[row['id']]=(float(row['lat']),float(row['lon']),'CIQ_GROUND')
assert len(nodes)==69

def haversine(a,b):
    la1,lo1,_=a;la2,lo2,_=b
    phi1,phi2=radians(la1),radians(la2)
    dphi=radians(la2-la1);dlambda=radians(lo2-lo1)
    z=sin(dphi/2)**2+cos(phi1)*cos(phi2)*sin(dlambda/2)**2
    return 2*6371.0088*asin(min(1,sqrt(z)))

records=[]
for t,distcol in [('V7_ALL_111_GEOMETRY_ONLY','geodesic_one_way_km'),
                  ('V8_CIQ_PORT_10_GROUND_AND_UAV_GEOMETRY','one_way_km')]:
    for r in con.execute('select * from "'+t+'"'):
        ori=r['from_id'];dst=r['to_id']
        assert ori in nodes and dst in nodes, (t,ori,dst)
        km=haversine(nodes[ori],nodes[dst]);filekm=float(r[distcol])
        delta=abs(km-filekm)
        # Haversine is a spherical approximation vs WGS84 elliptic distances; 0.15 km tolerance.
        assert delta < 0.150, ('Distance discrepancy',t,r['edge_id'],delta)
        geomtype='GROUND_BEELINE' if t.startswith('V8') and r['mode'].startswith('GROUND') else 'UAV_CANDIDATE'
        records.append({'source_table':t,'edge_id':r['edge_id'],'from_id':ori,'to_id':dst,
           'mode':geomtype,'stored_WGS84_km':round(filekm,4),'spherical_QA_km':round(km,4),
           'distance_abs_difference_km':round(delta,4),
           'DJI_5p6_geom_filter':('YES' if filekm<=5.6 else 'NO') if geomtype=='UAV_CANDIDATE' else 'N/A',
           'Wing_32p2_geom_filter':('YES' if filekm<=32.2 else 'NO') if geomtype=='UAV_CANDIDATE' else 'N/A',
           'operational_approved':'NO'})
assert len(records)==121
assert sum(r['mode']=='UAV_CANDIDATE' for r in records)==116
assert sum(r['mode']=='GROUND_BEELINE' for r in records)==5
# The 94 + 5 distance-feasible UAV geometries are purely a scenario count.
assert sum(r['mode']=='UAV_CANDIDATE' and r['DJI_5p6_geom_filter']=='YES' for r in records)==99
with (OUT/'QA_121_LINKS_GEOMETRY_ONLY.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=records[0].keys());w.writeheader();w.writerows(records)

stats={'passed':True,'study_nodes':68,'gateway_ground_reference':1,'all_geometries':121,
       'candidate_UAV_geometries':116,'ground_reference_beelines':5,
       'DJI_geometric_candidates_within_5p6km':99,
       'DJI_geometric_candidates_beyond_5p6km':17,
       'Wing_geometric_candidates_within_32p2km':116,
       'approved_UAV_routes':0,'approved_UAV_pads':0,
       'all_B_source_points_retained':count('B_10_FROZEN_NOT_PADS')==10,
       'A11_not_reintroduced':True,
       'distance_checks':'Haversine independent approximation compared with source WGS84 geodesic distances; 150 m QA tolerance',
       'note':'Geometry-only filters; not weather, load, power, airspace legal status, risk or flight approval'}
(OUT/'QA_STANDALONE_RESULTS.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(stats,ensure_ascii=False,indent=2))
con.close()
