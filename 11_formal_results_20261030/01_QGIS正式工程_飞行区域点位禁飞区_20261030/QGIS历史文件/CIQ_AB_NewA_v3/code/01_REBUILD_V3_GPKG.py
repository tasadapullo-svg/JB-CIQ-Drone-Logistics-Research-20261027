# -*- coding: utf-8 -*-
"""Rebuild V3 independently from a cleaned, frozen V3 input seed, keeping B unchanged.
Run with Python + fiona + shapely + pyproj (standalone; no QGIS dependency).
Flight polygons are range-based *scenario screens*, not authorized flight areas.
V3 removes A11, A09--A11, and excludes Perling from the west search window.
"""
from pathlib import Path
from collections import defaultdict
import json, csv, math, hashlib
import fiona
from fiona.crs import CRS
from shapely.geometry import shape, mapping, Point, box
from shapely.ops import transform as shp_transform, unary_union
from pyproj import Transformer, Geod

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT/'seed'/'CIQ_AB_NewA_v3_CLEAN_INPUTS.gpkg'
OUT = ROOT/'CIQ_AB_NewA_v3.gpkg'
if not SEED.is_file(): raise FileNotFoundError('V2 seed missing: '+str(SEED))
if OUT.exists(): OUT.unlink()

source_layer_names={
 'A_new_10_evidence_nodes': 'A_new_10_evidence_nodes',
 'A_new_4_site_search': 'A_new_4_site_search',
 'A_new_6_demand_references': 'A_new_6_demand_references',
 'A_new_11_unapproved_air_lines': 'A_new_11_unapproved_air_lines',
 'A_CIQ_ground_gateway': 'A_CIQ_ground_gateway',
 'B_10_frozen_reference_points':'B_10_frozen_reference_points',
 'B_33_frozen_unique_geometry':'B_33_frozen_unique_geometry',
 'WMP228_two_historical_discs':'WMP228_two_historical_discs',
 'A_user_study_windows_approx':'A_user_study_windows_approx',
 'AB_display_bounds_only':'AB_display_bounds_only',
 'A_9_FCD_examples_uncalibrated':'A_9_FCD_examples_uncalibrated'
}
all_nodes={}
for dest,src in source_layer_names.items():
 with fiona.open(SEED,layer=src) as layer:
  schema=layer.schema.copy()
  features=[]
  for feat in layer:
   p=dict(feat['properties']); g=shape(feat['geometry'])
   # No old A11 reference anywhere in the deliverable layers
   if p.get('site_id')=='A11' or p.get('id')=='A11' or p.get('src')=='A11' or p.get('dst')=='A11': continue
   if src=='A_new_11_unapproved_air_lines' and 'A11' in str(p.get('id','')): continue
   if dest=='A_user_study_windows_approx' and p.get('id')=='WEST_COMPARISON_WINDOW_ANALYTICAL':
    # strict WEST comparison envelope: Perling A11 at E103.68381 lies outside E103.675
    g=box(103.648,1.477,103.675,1.516)
    p['name']='Bukit Indah west comparison ONLY (A09/A10)'
    p['bounds']='103.648,1.477,103.675,1.516'
    p['basis']='ANALYTICAL_REVISED_V3_EXCLUDES_PERLING_A11'
    p['warning']='Not a legal, cadastral, or georeferenced screenshot boundary; A11 excluded'
   if dest=='A_new_10_evidence_nodes':
    p['review_revision']='V3_EXCLUDE_A11_2026_10_29'
    all_nodes[p['site_id']]=(g.x,g.y,p)
   features.append((g,p))
  if dest=='A_new_10_evidence_nodes': schema['properties']['review_revision']='str'
  with fiona.open(OUT,'w',driver='GPKG',layer=dest,crs=layer.crs,schema=schema,encoding='UTF-8') as out:
   for g,p in features: out.write({'geometry':mapping(g),'properties':p})

# Parameters are assumptions, not validated operating range or flight authorization.
config={
 'project':'CIQ_AB_NewA_v3',
 'frozen_A_ids_removed':['A11'],
 'excluded_west_site':'A11 Perling',
 'A_study_sites':['A01','A02','A03','A04','A05','A06','A07','A08','A09','A10'],
 'A_search_hubs_for_reach':['A01','A03','A09'],
 'A02_note':'Alternative in same Tebrau II industrial cluster as A01; not counted independently',
 'B_reference_hubs_for_reach':['B01','B02','B07'],
 'frozen_B_has_no_verified_uav_pad':True,
 'technical_range_reference_km':{'DJI_FlyCart30_30kg':16.0, 'Wingcopter198_reference':92.0},
 'nominal_mission_budget_fraction':0.70,
 'geometry_mode':'radius_km = published_reference_max_km * fraction / 2 (illustrative return-to-same-base)',
 'screens':['UNMASKED_GEOMETRY','OUTSIDE_UNION_OF_TWO_CONFLICTING_WMP228_REFERENCE_CIRCLES'],
 'flight_rights':'NO_FLIGHT_PERMISSION_VERIFIED',
 'obstacle_weather_payload_landuse':'NOT_VERIFIED',
 'screenshot_windows':'HAND_DRAWN_APPROX_NOT_A_CADASTRAL_OR_LEGAL_BOUNDARY',
 'coordinate_system_distance':'EPSG:32648 projected planar distance for 2–32 km local engineering illustration',
 'data_date':'2026-10-29',
 'caveat':'Wingcopter 92km and FlyCart 16km official maximum range are version/payload-specific; 70% factor is an arbitrary scenario, not an approved flight budget. Neither disk demonstrates operational feasibility.'
}
(ROOT/'flight_scenario_parameters.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')

wgs_to_utm=Transformer.from_crs('EPSG:4326','EPSG:32648',always_xy=True).transform
utm_to_wgs=Transformer.from_crs('EPSG:32648','EPSG:4326',always_xy=True).transform
with fiona.open(OUT,layer='A_user_study_windows_approx') as src:
 win={f['properties']['id']:shp_transform(wgs_to_utm,shape(f['geometry'])) for f in src}
with fiona.open(OUT,layer='AB_display_bounds_only') as src:
 bounds={f['properties']['id']:shp_transform(wgs_to_utm,shape(f['geometry'])) for f in src}
with fiona.open(OUT,layer='WMP228_two_historical_discs') as src:
 wmp=unary_union([shp_transform(wgs_to_utm,shape(f['geometry'])) for f in src])

A_clipper=unary_union(list(win.values()))
B_clipper=bounds['B_MAP_CONTEXT']
B_sites={}
with fiona.open(OUT,layer='B_10_frozen_reference_points') as src:
 for feat in src: B_sites[feat['properties']['site_id']]=shape(feat['geometry'])

flight_schema={'geometry':'MultiPolygon','properties':{'area':'str','aircraft':'str','scenario':'str','technical_km':'float','fraction':'float','radius_km':'float','hubs':'str','scope':'str','pad_approved':'str','legal_screen':'str'}}
count=0
for aircraft,max_km in config['technical_range_reference_km'].items():
 radius_m=max_km*0.7*1000/2
 for area,hubs,clipper in [('A_NEW',config['A_search_hubs_for_reach'],A_clipper),('B',config['B_reference_hubs_for_reach'],B_clipper)]:
  nodes=all_nodes if area=='A_NEW' else {k:(v.x,v.y,None) for k,v in B_sites.items()}
  circles=[shp_transform(wgs_to_utm,Point(nodes[h][0],nodes[h][1])).buffer(radius_m,resolution=128) for h in hubs]
  full=unary_union(circles)
  for scenario,region in [('TECHNICAL_REACH_CLIPPED',full.intersection(clipper)),
                           ('OUTSIDE_WMP228_TWO_REFERENCE_CIRCLES_ONLY',full.difference(wmp).intersection(clipper))]:
   if region.is_empty: continue
   from shapely.geometry import MultiPolygon,Polygon
   if region.geom_type=='Polygon': region=MultiPolygon([region])
   elif region.geom_type=='GeometryCollection': region=MultiPolygon([p for p in region.geoms if p.geom_type=='Polygon'])
   if not region.is_valid: region=region.buffer(0)
   layer_name='reach_'+('DJI' if aircraft.startswith('DJI') else 'WING')+'_'+('A' if area=='A_NEW' else 'B')+'_'+('nominal' if scenario=='TECHNICAL_REACH_CLIPPED' else 'WMP_screen')
   props={'area':area,'aircraft':aircraft,'scenario':scenario,'technical_km':max_km,'fraction':.7,'radius_km':radius_m/1000,
          'hubs':','.join(hubs),'scope':'CLIPPED_TO_ANALYTICAL_STUDY_WINDOWS_NOT_FULL_RADIUS','pad_approved':'NO','legal_screen':'NOT_LEGAL_CLEARANCE'}
   with fiona.open(OUT,'w',driver='GPKG',layer=layer_name,crs=CRS.from_epsg(4326),schema=flight_schema,encoding='UTF-8') as dst:
    dst.write({'geometry':mapping(shp_transform(utm_to_wgs,region)),'properties':props})
   count+=1

# Export clean selected attributes and a concise audit summary.
for layer,outname in [('A_new_10_evidence_nodes','A_new_10_nodes.csv'),('A_new_11_unapproved_air_lines','A_new_11_air_candidates.csv'),('B_10_frozen_reference_points','B_10_frozen_nodes.csv')]:
 with fiona.open(OUT,layer=layer) as data:
  props=list(data.schema['properties'].keys())
  with (ROOT/outname).open('w',newline='',encoding='utf-8-sig') as fh:
   writer=csv.DictWriter(fh,fieldnames=props); writer.writeheader()
   for f in data: writer.writerow(dict(f['properties']))

fcounts={name:len(fiona.open(OUT,layer=name)) for name in fiona.listlayers(OUT)}
assert fcounts['A_new_10_evidence_nodes']==10
assert fcounts['A_new_4_site_search']==4
assert fcounts['A_new_6_demand_references']==6
assert fcounts['A_new_11_unapproved_air_lines']==11
assert fcounts['B_10_frozen_reference_points']==10
assert fcounts['B_33_frozen_unique_geometry']==33
assert len([k for k in fcounts if k.startswith('reach_')])==8
assert 'A11' not in [p['site_id'] for p in [v[2] for v in all_nodes.values()]]
qa={'status':'V3_GPKG_STATIC_OK','counts':fcounts,'reference_circles_are_not_legal_prohibited_area':True,
    'A11_removed':True,'A09_A10_retained':True,'WMP_screen_is_comparison_not_authority':True,
    'has_real_drone_operation_approvals':False,'has_FCD_calibrated_routes':False}
(ROOT/'QA'/'V3_counts_and_scientific_gates.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
print('Created',OUT,'feature groups:',len(fcounts))
print('A 10 sites, A 11 lines, B 10 sites/33 geometric lines, 8 reach / WMP comparison polygons')
