# -*- coding: utf-8 -*-
"""Rebuild edit-ready New Area A + original Area B GeoPackage and QGIS project.
Run from any Python 3 environment with geopandas, pandas, pyproj, fiona, lxml, matplotlib.
Input files are bundled in ../inputs/; no network request. WMP228 references are screening geometry only.
The old A00..A08 operational network is EXCLUDED; the physical CIQ is an independent gateway context point.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from copy import deepcopy
import csv, json, uuid, hashlib
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, box
from lxml import etree as ET
from pyproj import Transformer

ROOT=Path(__file__).resolve().parent.parent
IN=ROOT/'inputs'; QA=ROOT/'QA';QA.mkdir(exist_ok=True)
GPKG=ROOT/'CIQ_AB_NewA_v2.gpkg'; QGZ=ROOT/'CIQ_AB_NewA_v2.qgz'
# 1-to-1 migration from previous experimental labels; these are NOT the old frozen A nodes.
ID_MAP={**{f'E{i:02d}':f'A{i:02d}' for i in range(1,9)},
        'W01':'A09','W02':'A10','W03':'A11'}
NAME_OVERRIDE={'A01':'Swift Tebrau II | priority facility search',
 'A02':'Tebrau II | alternative in SAME industrial cluster',
 'A03':'Bakar Batu | conditional ground feeder search',
 'A04':'Mid Valley Southkey | demand reference',
 'A05':'Taman Molek | mixed demand reference',
 'A06':'Permas Jaya | residential/commercial demand',
 'A07':'Kampung Tengah | demand reference (land caution)',
 'A08':'Pandan wholesale market | demand reference',
 'A09':'Bukit Indah industrial reference | west comparison',
 'A10':'Bukit Indah courier reference | west demand',
 'A11':'Perling residential reference | west demand'}

def source(n):
 df=gpd.read_file(IN/n)
 if df.crs is None: raise ValueError('Missing CRS '+n)
 return df.to_crs('EPSG:4326')

A=source('New_A_11_evidence_anchors_PRE_RENAME.geojson')
assert set(A.id)==set(ID_MAP)
A['source_prior_code']=A['id']; A['id']=A['id'].map(ID_MAP)
A['site_id']=A['id'];A['name']=A['id'].map(NAME_OVERRIDE)
A['operational_status']='CANDIDATE_OR_DEMAND_ONLY_NOT_APPROVED'
A['approved_pad']=False; A['site_permission']='NOT_VERIFIED'
A['site_safety']='NOT_VERIFIED';A['flight_permission']='NOT_VERIFIED'
A['research_area']='A_NEW'; A['review_revision']='V2_2026_10_29'
assert len(A)==11 and len(A.id.unique())==11
A_sites=A[A['id'].isin(['A01','A02','A03','A09'])].copy()
A_demand=A[~A['id'].isin(['A01','A02','A03','A09'])].copy()
A_lines=source('New_A_12_screen_lines_PRE_RENAME.geojson')
for field in ('src','dst'):
 A_lines[field]=A_lines[field].map(ID_MAP)
assert A_lines[['src','dst']].notna().all().all()
A_lines['id']=A_lines['src']+'__'+A_lines['dst']
A_lines['area']='A_NEW'
A_lines['line_type']='STRAIGHT_GEOMETRY_ONLY_UNAPPROVED'
A_lines['landing_end']='NOT_VERIFIED'
A_lines['approved_route']=False
assert len(A_lines)==12

B=source('B_10_frozen_points.geojson'); B_lines=source('B_33_frozen_geometries.geojson')
assert len(B)==10 and set(B['site_id'])=={f'B{i:02d}' for i in range(10)}
assert len(B_lines)==33 and set(B_lines['area'])=={'B'}
B['status']='FROZEN_REFERENCE_ONLY_NOT_APPROVED'
B_lines['approved_route']=False

# Location still shown, but NOT the old A00 operational node.
G=gpd.GeoDataFrame([{
 'id':'G_CIQ','name':'Sultan Iskandar CIQ / Causeway',
 'role':'GROUND_GATEWAY_CONTEXT_NOT_UAV_PAD','area':'A_NEW',
 'permission':'NOT_APPROVED_FOR_UAV_LAUNCH','source':'Original map reference at 103.76663E,1.46502N',
 'geometry':Point(103.76663,1.46502)}],crs='EPSG:4326')
C=source('WMP228_2_reference_discs.geojson')
# Preserve the DMS strings as descriptive text; not a parsed time field.
W=source('User_area_windows_APPROX.geojson')
W['is_legal_boundary']=False
FCD=source('A_FCD_sample_points.geojson')
# Two visual extent envelopes; they are NOT operational candidate land boundaries.
CTX=gpd.GeoDataFrame([
 {'id':'A_MAP_CONTEXT','meaning':'DISPLAY_ONLY','geometry':box(103.64,1.435,103.85,1.555)},
 {'id':'B_MAP_CONTEXT','meaning':'DISPLAY_ONLY','geometry':box(103.535,1.34,103.67,1.465)}],crs='EPSG:4326')

layers=[('A_new_11_evidence_nodes',A),('A_new_4_site_search',A_sites),
 ('A_new_7_demand_references',A_demand),('A_new_12_unapproved_air_lines',A_lines),
 ('A_CIQ_ground_gateway',G),('B_10_frozen_reference_points',B),
 ('B_33_frozen_unique_geometry',B_lines),('WMP228_two_historical_discs',C),
 ('A_user_study_windows_approx',W),('AB_display_bounds_only',CTX),
 ('A_9_FCD_examples_uncalibrated',FCD)]
if GPKG.exists():GPKG.unlink()
for name,df in layers:
 df.to_file(GPKG,layer=name,driver='GPKG',encoding='UTF-8',index=False)
A.drop(columns='geometry').to_csv(ROOT/'A_new_site_evidence_review.csv',index=False,encoding='utf-8-sig')
A_lines.drop(columns='geometry').to_csv(ROOT/'A_new_air_geometry_screen.csv',index=False,encoding='utf-8-sig')
B.drop(columns='geometry').to_csv(ROOT/'B_frozen_site_list.csv',index=False,encoding='utf-8-sig')
with open(ROOT/'ID_E_W_to_NEW_A_crosswalk.csv','w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['previous_review_id','NEW_A_id','purpose'])
 for old,new in ID_MAP.items():w.writerow([old,new,NAME_OVERRIDE[new]])
# Request list: every geographic route must be solved on a real connected graph.
request=[('A_NEW','G_CIQ',x) for x in ['A01','A02','A03','A04','A09']]+[
 ('B','B00',x) for x in ['B01','B02','B06','B07']]
with open(ROOT/'Ground_OD_requests_NOT_ROUTES.csv','w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['area','origin_id','destination_id','status'])
 for area,o,d in request:w.writerow([area,o,d,'PENDING_VERIFIED_OSM_ROAD_GRAPH_AND_GATE_QA'])

# Portable QGIS skeleton is copied only from original B and shared airspace, never old A.
root=ET.parse(str(IN/'clean_B_airspace_basemap_template.qgs')).getroot()
project_layers=root.find('projectlayers');tree=root.find('layer-tree-group')
p_old=next(m for m in root.xpath('./projectlayers/maplayer') if m.findtext('layername')=='FIG1 | Area B reference anchors')
l_old=next(m for m in root.xpath('./projectlayers/maplayer') if m.findtext('layername')=='FIG1 | Area B candidate straight links')
poly_old=next(m for m in root.xpath('./projectlayers/maplayer') if m.findtext('layername')=='FIG3A V2 | WMP228 CAAM main reference 2NM')
# Keep only raster OSM + airspace sources. All site layers below point at the NEW gpkg.
for m in list(root.xpath('./projectlayers/maplayer')):
 if m.findtext('layername').startswith('FIG1 |'):project_layers.remove(m)
for el in list(tree):tree.remove(el)
root.set('projectname','CIQ_AB_NEW_A_V2_REPLACED')
root.find('title').text='New A01-A11 and frozen B00-B09 | prior A removed | site search only'

def group(name):
 g=ET.Element('layer-tree-group',attrib={'expanded':'1','name':name,'checked':'Qt::Checked'})
 ET.SubElement(g,'customproperties').append(ET.Element('Option'))
 tree.append(g)
 return g

def recolor(m,kind,color,shape=None,field=None):
 r=m.find('renderer-v2');syms=r.find('symbols') if r is not None else None
 if syms is not None:
  first=syms.find('symbol')
  if first is not None:
   first=deepcopy(first)
   for c in list(r):r.remove(c)
   r.set('type','singleSymbol')
   el=ET.SubElement(r,'symbols');el.append(first)
   first.set('name','0')
   for opt in first.xpath('.//Option[@name]'):
    n=opt.get('name')
    if kind=='point':
     if n=='color':opt.set('value',color)
     if n=='outline_color':opt.set('value','255,255,255,255')
     if n=='size':opt.set('value','3.1')
     if n=='name' and shape:opt.set('value',shape)
    if kind=='line':
     if n=='line_color':opt.set('value',color)
     if n=='line_width':opt.set('value','0.45')
     if n=='line_style':opt.set('value','dash' if shape=='dash' else 'solid')
    if kind=='polygon':
     if n=='outline_color':opt.set('value',color)
     if n=='color':opt.set('value','255,255,255,0')
     if n=='outline_width':opt.set('value','0.5')
     if n=='outline_style':opt.set('value','dash')
 m.set('labelsEnabled','1' if kind=='point' and field else '0')
 if kind=='point' and field:
  for ts in m.xpath('./labeling/settings/text-style'):
   ts.set('fieldName',field);ts.set('isExpression','0');ts.set('fontSize','8');ts.set('textColor','0,0,0,255')

def register(layer_name,kind,display,color,group_,visible=True,field=None,shape=None):
 template={'point':p_old,'line':l_old,'polygon':poly_old}[kind]
 m=deepcopy(template);name='CIQ_'+uuid.uuid5(uuid.NAMESPACE_DNS,layer_name).hex[:20]
 ds='./CIQ_AB_NewA_v2.gpkg|layername='+layer_name
 m.find('id').text=name;m.find('layername').text=display;m.find('datasource').text=ds
 m.set('wkbType',{'point':'Point','line':'LineString','polygon':'Polygon'}[kind]);m.set('geometry',{'point':'Point','line':'Line','polygon':'Polygon'}[kind])
 data=dict(layers)[layer_name];bounds=data.total_bounds
 for e in (m.find('extent'),m.find('wgs84extent')):
  if e is not None:
   for nm,val in zip(['xmin','ymin','xmax','ymax'],bounds):
    v=e.find(nm)
    if v is not None:v.text=str(val)
 recolor(m,kind,color,shape=shape,field=field)
 project_layers.append(m)
 node=ET.SubElement(group_,'layer-tree-layer',attrib={'expanded':'0','source':ds,'legend_exp':'','name':display,'providerKey':'ogr','id':name,'legend_split_behavior':'0','patch_size':'-1,-1','checked':'Qt::Checked' if visible else 'Qt::Unchecked'})
 ET.SubElement(node,'customproperties').append(ET.Element('Option'))
 return name

def inherit(name,grp,visible=False):
 original=next(m for m in root.xpath('./projectlayers/maplayer') if m.findtext('layername')==name)
 ds=original.findtext('datasource')
 layerid=original.findtext('id')
 node=ET.SubElement(grp,'layer-tree-layer',attrib={'expanded':'0','source':ds,'legend_exp':'','name':name,'providerKey':'ogr','id':layerid,'legend_split_behavior':'0','patch_size':'-1,-1','checked':'Qt::Checked' if visible else 'Qt::Unchecked'})
 ET.SubElement(node,'customproperties').append(ET.Element('Option'))

pgroup=group('01 | NEW A01–A11 + B00–B09 | search/demand only')
register('A_new_4_site_search','point','A NEW | A01 A02 A03 A09 site SEARCH (not pads)','13,114,115,255',pgroup,True,'site_id','triangle')
register('A_new_7_demand_references','point','A NEW | A04–A08 A10–A11 demand (not pads)','228,140,30,255',pgroup,True,'site_id','circle')
register('B_10_frozen_reference_points','point','B | B00–B09 frozen references','35,75,132,255',pgroup,True,'site_id','circle')
register('A_CIQ_ground_gateway','point','Causeway CIQ | ground gateway ONLY','75,75,75,255',pgroup,True,'id','square')
register('A_new_11_evidence_nodes','point','A NEW | complete attribute master (toggle for editing)','20,132,130,255',pgroup,False,'site_id')
register('A_9_FCD_examples_uncalibrated','point','A NEW | FCD sample points (NOT speed-matched)','100,100,100,255',pgroup,False,'id')
lgroup=group('02 | Geometry links, NOT approved flights or audited roads')
register('A_new_12_unapproved_air_lines','line','A NEW | 12 straight flight geometry tests','25,138,157,255',lgroup,True,shape='dash')
register('B_33_frozen_unique_geometry','line','B | 33 unique historic geometry segments','64,86,130,255',lgroup,True,shape='dash')
reg=group('03 | Regulatory sources: historical refs ONLY')
register('WMP228_two_historical_discs','polygon','WMP228 | two historical 2-NM screening discs','176,38,51,255',reg,True)
for name in ['FIG3A V2 | Published centre locations (2 WMP + airports)','FIG3A V2 | WMKJ Senai ARP 5NM screen','FIG3A V2 | SG airport 5km screens (OneMap pending)']:
 inherit(name,reg,False)
# Original CAAM/CAAS layer definitions retained only as source-backed toggles; avoid double-render with vector disks.
for name in ['FIG3A V2 | WMP228 CAAM main reference 2NM','FIG3A V2 | WMP228 CAAS alternate 2NM']:
 inherit(name,reg,False)
wg=group('04 | Display/search windows are not legal polygons')
register('A_user_study_windows_approx','polygon','A NEW | east user rectangle + west comparison (APPROX)','205,45,55,255',wg,True)
register('AB_display_bounds_only','polygon','A/B overview frame bounds (display only)','80,80,80,255',wg,False)
inher=group('05 | Live basemap')
inherit('OpenStreetMap',inher,True)
# Remove old custom drawing order information that could refer to deleted map layer IDs.
for n in list(root.xpath('.//custom-order')):
 n.getparent().remove(n)
can=root.find('mapcanvas')
if can is not None:
 extent=can.find('extent')
 if extent is not None:
  tr=Transformer.from_crs(4326,3857,always_xy=True)
  x1,y1=tr.transform(103.52,1.33);x2,y2=tr.transform(103.855,1.565)
  for k,v in zip(['xmin','ymin','xmax','ymax'],[x1,y1,x2,y2]):
   e=extent.find(k)
   if e is not None:e.text=str(v)
qgs=ET.tostring(root,encoding='UTF-8',xml_declaration=True,pretty_print=True)
with ZipFile(QGZ,'w',compression=ZIP_DEFLATED) as z:z.writestr('CIQ_AB_NewA_v2.qgs',qgs)

# independent structural QA; ensure NO old Area A objects or route refs leak into operational package
from fiona import listlayers
assert set(listlayers(str(GPKG)))==set(n for n,_ in layers)
assert all(not s.startswith('E') and not s.startswith('W') for s in A.id)
assert not any(x.startswith('A') for x in B.site_id)
with ZipFile(QGZ) as z:qroot=ET.fromstring(z.read('CIQ_AB_NewA_v2.qgs'))
maplayers=qroot.xpath('./projectlayers/maplayer')
assert not any('FIG1 | Area A ' in m.findtext('layername','') for m in maplayers)
assert not any('Aprime_' in m.findtext('datasource','') for m in maplayers)
assert not any('Fig1_19_reference_points' in m.findtext('datasource','') for m in maplayers)
refs=[]
for m in maplayers:
 ds=m.findtext('datasource') or ''
 if ds.startswith('./'):
  ff=ROOT/ds.split('|')[0]
  assert ff.exists(),(m.findtext('layername'),str(ff))
  refs.append(str(ff.relative_to(ROOT)))
counts={'NEW_A_nodes':len(A),'NEW_A_site_search':len(A_sites),'NEW_A_demand':len(A_demand),'NEW_A_straight_test_lines':len(A_lines),
 'B_frozen_nodes':len(B),'B_unique_geometry_segments':len(B_lines),'Old_A_nodes_in_new_project':0,'Old_A_edges_in_new_project':0,
 'WMP_reference_discs':len(C),'verified_UAV_pads':0,'roads_calibrated':False,'project_internal_refs_checked':len(refs),
 'airspace_legal_boundary_verified':False, 'source_road_routes_computed':False}
(QA/'QA_counts_and_gates.json').write_text(json.dumps(counts,indent=2,ensure_ascii=False),encoding='utf-8')
allfiles=[x for x in ROOT.rglob('*') if x.is_file() and 'sha256_manifest' not in x.name]
with (QA/'sha256_manifest.txt').open('w',encoding='utf-8') as f:
 for p in sorted(allfiles):f.write(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(ROOT))+'\n')
print(json.dumps(counts,ensure_ascii=False,indent=2))
