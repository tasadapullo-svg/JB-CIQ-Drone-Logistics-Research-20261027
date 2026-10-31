"""Additional read-only independent label QA, sublayer consistency and scenario pollution checks."""
from pathlib import Path
import geopandas as gpd
import pandas as pd
import json,csv,hashlib,collections
ROOT=Path('/mnt/data/CIQ_V3_inspection_raw/CIQ_ABC_QGIS322_NEW_COMPLETE_PROJECT')
O=Path('/mnt/data/CIQ_V3_Independent_Audit_20261030')
G=ROOT/'data/CIQ_ABC_FINAL_EDITABLE.gpkg'
audit=json.loads((O/'V3_independent_audit.json').read_text())
labels=pd.read_csv(ROOT/'qa/QA_ALL_69_NODE_LABELS.csv').fillna('')
nodes=pd.read_csv(O/'V3_69_nodes_verified.csv',encoding='utf-8-sig').fillna('')
nodes['node_id']=nodes.node_id.astype(str);labels['node_id']=labels.node_id.astype(str)
combined=labels.merge(nodes,on='node_id',how='outer',suffixes=('_source','_gpkg'),indicator=True)
combined['coords_equal']=(combined.longitude_E.astype(float)-combined.longitude.astype(float)).abs().lt(1e-7)&(combined.latitude_N.astype(float)-combined.latitude.astype(float)).abs().lt(1e-7)
combined['names_equal']=combined.full_name==combined.name
combined['label_has_name']=combined.apply(lambda x:x['full_name'] in x['regional_and_canvas_label'],axis=1)
combined['label_has_id']=combined.apply(lambda x:x['node_id'] in x['regional_and_canvas_label'],axis=1)
labels_audit=combined[['node_id','full_name','name','zone_source','zone_gpkg','longitude_E','latitude_N','longitude','latitude','_merge','coords_equal','names_equal','label_has_name','label_has_id']]
labels_audit.to_csv(O/'V3_69_label_coordinates_independently_crosschecked.csv',index=False,encoding='utf-8-sig')
audit['checks']['label_crosswalk']={'rows':len(combined),'all_complete':bool((combined._merge=='both').all()),'all_coords_equal':bool(combined.coords_equal.all()),'all_names_equal':bool(combined.names_equal.all()),'all_labels_have_full_name_and_id':bool((combined.label_has_name&combined.label_has_id).all())}
# duplicate archived sublayers vs aggregated main features
ac=gpd.read_file(G,layer='AC_52_nodes_NOT_PADS')
b=gpd.read_file(G,layer='B_10_FROZEN_NOT_PADS')
joined=gpd.read_file(G,layer='V7_ALL_62_RETAINED_ROLES')
node_subsets=[]
for name,g in [('AC_52_nodes_NOT_PADS',ac),('B_10_FROZEN_NOT_PADS',b)]:
 for _,row in g.iterrows():
  ident=str(row.get('id',row.get('site_id')))
  x=joined[joined.id==ident]
  node_subsets.append({'node_id':ident,'sub_layer':name,'present_in_combined':len(x)==1,
    'same_point_geometry':len(x)==1 and row.geometry.equals_exact(x.iloc[0].geometry,1e-9)})
audit['checks']['source_sublayer_nodes']={'rows':len(node_subsets),'all_joined':all(x['present_in_combined'] for x in node_subsets),'all_same_geom':all(x['same_point_geometry'] for x in node_subsets)}
# 78+33 exactly reproduce 111 geometries
main=gpd.read_file(G,layer='V7_ALL_111_GEOMETRY_ONLY')
edge_sub=[]
for name in ['AC_78_geometric_links','B_33_FROZEN_reaudited']:
 g=gpd.read_file(G,layer=name)
 for _,row in g.iterrows():
  key=row.edge_id
  x=main[main.edge_id==key]
  edge_sub.append({'edge_id':key,'sub_layer':name,'present_in_combined':len(x)==1,'same_geom':len(x)==1 and row.geometry.equals_exact(x.iloc[0].geometry,1e-9)})
audit['checks']['source_sublayer_links']={'rows':len(edge_sub),'all_joined':all(x['present_in_combined'] for x in edge_sub),'all_same_geom':all(x['same_geom'] for x in edge_sub)}
# UAV status and ground flag checks
v8=gpd.read_file(G,layer='V8_CIQ_PORT_10_GROUND_AND_UAV_GEOMETRY')
ground=v8[v8['mode']=='GROUND_HANDOFF_STRAIGHT_REFERENCE']
uav=v8[v8['mode']=='UAV_GEOMETRY_SEARCH']
audit['checks']['v8_mode_flag_separation']={
  'uav_candidate_lines':len(uav),'ground_handoff_beelines':len(ground),
  'ground_lines_with_DJI_geom_flag_1':int((ground['DJI_geom_5p6_km'].astype(str).isin(['1','True','1.0'])).sum()),
  'ground_lines_with_Wing_geom_flag_1':int((ground['Wing_geom_32p2_km'].astype(str).isin(['1','True','1.0'])).sum()),
  'risk':'DO_NOT infer UAV eligibility solely from drone geometric flag; filter mode==UAV_GEOMETRY_SEARCH and regulatory/ops gates.'}
pre=gpd.read_file(G,layer='V7_ALL_62_RETAINED_ROLES')
audit['checks']['site_admission']={'v7_uav_operational_admission_NO':int((pre.uav_operational_admission=='NO').sum()),
 'v7_site_count':len(pre),'v8_operational_uav_site_true':int((gpd.read_file(G,layer='V8_CIQ_PORT_6_EVIDENCE_POINTS').operational_uav_site.astype(str).isin(['True','1','YES']).sum()))}
geomg=gpd.read_file(G,layer='V7_ALL_111_GEOMETRY_ONLY')
audit['checks']['range_scenarios']={'V7_DJI_within5p6':int(geomg.dji_scenario_5p6km.astype(str).isin(['True','1','1.0']).sum()),
  'V7_Wing_within32p2':int(geomg.wing_scenario_32p2km.astype(str).isin(['True','1','1.0']).sum()),
  'V8_UAV_DJI_within5p6':int(uav['DJI_geom_5p6_km'].astype(str).isin(['1','True','1.0']).sum()),
  'V8_UAV_Wing_within32p2':int(uav['Wing_geom_32p2_km'].astype(str).isin(['1','True','1.0']).sum())}
# Reminder that the detached QGS is only a XML project, not verification of desktop working export
(O/'V3_independent_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:audit['checks'][k] for k in ['sha256','label_crosswalk','source_sublayer_nodes','source_sublayer_links','v8_mode_flag_separation','site_admission','range_scenarios']},ensure_ascii=False,indent=2))
