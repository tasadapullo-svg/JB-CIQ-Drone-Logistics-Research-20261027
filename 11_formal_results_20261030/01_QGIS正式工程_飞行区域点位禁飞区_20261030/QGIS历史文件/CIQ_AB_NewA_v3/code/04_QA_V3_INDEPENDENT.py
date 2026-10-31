# -*- coding: utf-8 -*-
"""Independent file/geometry QA, not a substitute for a QGIS 3.22 runtime test."""
from pathlib import Path
import json,zipfile,re,hashlib
import fiona
from shapely.geometry import shape,Point
from shapely.ops import transform,unary_union
from pyproj import Transformer
from lxml import etree as ET
ROOT=Path(__file__).resolve().parents[1]
gpkg=ROOT/'CIQ_AB_NewA_v3.gpkg'
ls=fiona.listlayers(gpkg);count={name:len(fiona.open(gpkg,layer=name)) for name in ls}
with fiona.open(gpkg,layer='A_new_10_evidence_nodes') as s: site_ids=[f['properties']['site_id'] for f in s]
with fiona.open(gpkg,layer='A_new_11_unapproved_air_lines') as s:legs=[(f['properties']['src'],f['properties']['dst'],shape(f['geometry'])) for f in s]
with fiona.open(gpkg,layer='A_user_study_windows_approx') as s:wins={f['properties']['id']:shape(f['geometry']) for f in s}
with fiona.open(gpkg,layer='WMP228_two_historical_discs') as s:wmp=unary_union([shape(f['geometry']) for f in s])
assert len(site_ids)==10 and len(set(site_ids))==10
assert set(site_ids)=={'A%02d'%i for i in range(1,11)}
assert all(a in site_ids and b in site_ids for a,b,_ in legs)
assert len(legs)==11 and all('A11' not in [a,b] for a,b,_ in legs)
assert not wins['WEST_COMPARISON_WINDOW_ANALYTICAL'].covers(Point(103.68381,1.48061))
assert wins['WEST_COMPARISON_WINDOW_ANALYTICAL'].covers(Point(103.65939,1.49927))
assert wins['WEST_COMPARISON_WINDOW_ANALYTICAL'].covers(Point(103.6633132,1.4868072))
assert count['B_10_frozen_reference_points']==10 and count['B_33_frozen_unique_geometry']==33
assert len([k for k in count if k.startswith('reach_')])==8
with zipfile.ZipFile(ROOT/'CIQ_AB_NewA_v3.qgz') as z:
    qgsname=next(n for n in z.namelist() if n.endswith('.qgs'))
    project=ET.fromstring(z.read(qgsname))
refs=[];missing=[]
for ml in project.xpath('./projectlayers/maplayer'):
    ds=ml.findtext('datasource') or ''
    if ds.startswith('./'):
        path=ds.split('|')[0]
        if not (ROOT/path).exists():missing.append(path)
    if 'layername=' in ds:
        ln=ds.split('layername=')[1].split('|')[0]
        if ln not in ls and not ds.endswith('.geojson'): # sources can also be external legal/airport .geojson
            missing.append('layer:'+ln)
    refs.append(ds)
assert not missing,missing
assert all('A_new_11_evidence_nodes' not in ds and 'A_new_12_unapproved_air_lines' not in ds for ds in refs)
assert all('A_new_7_demand_references' not in ds for ds in refs)
# WMP crossing via EPSG:32648, robust for local distances
xf=Transformer.from_crs(4326,32648,always_xy=True).transform
wmputm=transform(xf,wmp)
line_in_wmp=sum(1 for _,_,ln in legs if transform(xf,ln).intersects(wmputm))
reach={}
for key in sorted(k for k in ls if k.startswith('reach_')):
  with fiona.open(gpkg,layer=key) as layer:
    g=unary_union([transform(xf,shape(x['geometry'])) for x in layer])
    reach[key]=round(g.area/1e6,3)
assert reach['reach_DJI_A_WMP_screen']<=reach['reach_DJI_A_nominal']+1e-8
manifest={
 'data_status':'PASS_STATIC_GEOMETRY_XML_AND_REFERENCES',
 'qgis_desktop_3_22_runtime_test':'NOT_AVAILABLE_IN_THIS_CONTAINER',
 'feature_counts':count,'no_A11':True,'west_scope_excludes_perling':True,
 'A_new_leg_intersection_with_two_WMP_reference_discs':line_in_wmp,
 'reach_window_clipped_area_sqkm':reach,
 'node_count_approved_landing_sites':0,
 'leg_count_approved_flight_paths':0,
 'traffic_path_calibration_complete':False,
 'critical_regulatory_note':'CAAM_2025_CAAS_2026_centres_are_conflicting_historical_geometry_references_NOT_VERIFIED_CURRENT_LAW',
 'render_labels':'QGIS-native labels auto-place but manual end-user cartographic inspection still required',
 'files_missing':missing,
 'source':'V3 cleaned seed, base V2 provenance from user-submitted QGIS and GitHub data'
}
(ROOT/'QA'/'V3_independent_QA.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
print('PASS INDEPENDENT QA',json.dumps({'A_points':len(site_ids),'A_lines':len(legs),'B_points':count['B_10_frozen_reference_points'],'B_lines':count['B_33_frozen_unique_geometry'],'bad_refs':missing,'intersect':line_in_wmp}))
