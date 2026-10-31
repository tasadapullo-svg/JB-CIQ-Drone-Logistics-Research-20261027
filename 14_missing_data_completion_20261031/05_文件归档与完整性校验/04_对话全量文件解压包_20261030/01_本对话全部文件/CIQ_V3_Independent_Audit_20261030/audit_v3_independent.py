"""Read-only independent check of the user-supplied QGIS V3 ZIP; does not run its Python scripts."""
from pathlib import Path
from collections import Counter, defaultdict
import csv, json, hashlib, zipfile, sqlite3, re, ast, math, os, xml.etree.ElementTree as ET
import geopandas as gpd
from pyproj import Geod
import pandas as pd

ROOT=Path('/mnt/data/CIQ_V3_inspection_raw/CIQ_ABC_QGIS322_NEW_COMPLETE_PROJECT')
OUT=Path('/mnt/data/CIQ_V3_Independent_Audit_20261030')
Z=Path('/mnt/data/CIQ_ABC_QGIS322_NEW_COMPLETE_PROJECT_ALL_FILES_V3.zip')
GPKG=ROOT/'data/CIQ_ABC_FINAL_EDITABLE.gpkg'
OUT.mkdir(parents=True,exist_ok=True)

def norm(s): return '' if s is None else str(s).strip()
def records(path):
 with open(path,encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def savecsv(name,rows,fields=None):
 p=OUT/name
 if fields is None: fields=list(dict.fromkeys(k for r in rows for k in r))
 with open(p,'w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

r={'package':{'path':str(Z),'sha256':hashlib.sha256(Z.read_bytes()).hexdigest()},'checks':{},'warnings':[],'blockers':[]}
with zipfile.ZipFile(Z) as z:
 r['package']['zip_file_count']=len(z.infolist());r['package']['zip_testzip']=z.testzip()
 r['package']['zip_unique_paths']=len({i.filename for i in z.infolist()})==len(z.infolist())
manifest=records if False else {}
lines=(ROOT/'SHA256_MANIFEST.txt').read_text().splitlines()
for s in lines:
 if not s.strip():continue
 m=re.match(r'^([0-9a-f]{64})\s{2}(.+)$',s)
 if not m:r['warnings'].append('Invalid SHA manifest line '+s[:50]);continue
 manifest[m[2]]=m[1]
sha_rows=[]
for path in sorted(p for p in ROOT.rglob('*') if p.is_file()):
 rel=path.relative_to(ROOT).as_posix()
 sha=hashlib.sha256(path.read_bytes()).hexdigest()
 sha_rows.append({'file':rel,'bytes':path.stat().st_size,'sha256':sha,'manifest_sha256':manifest.get(rel,''),'matches_manifest':sha==manifest.get(rel)})
missing_manifest=set(manifest)-{x['file'] for x in sha_rows}
r['checks']['sha256']={'manifest_entries':len(manifest),'actual_files':len(sha_rows),'all_match':all(x['matches_manifest'] for x in sha_rows if x['file']!='SHA256_MANIFEST.txt'),'missing_referenced_files':sorted(missing_manifest)}
savecsv('V3_file_sha256_verified.csv',sha_rows)

# QGIS XML, local datasource references and full-name configuration
qgs=ROOT/'CIQ_ABC_ALL_69_NAMES_PORTABLE.qgs'
xml=ET.parse(qgs).getroot()
with zipfile.ZipFile(ROOT/'CIQ_ABC_ALL_69_NAMES_PORTABLE.qgz') as gz:
 r['checks']['qgz_xml_identical']=len(gz.namelist())==1 and gz.read(gz.namelist()[0])==qgs.read_bytes()
conn=sqlite3.connect(GPKG)
try:
 gpkg_integrity=conn.execute('pragma integrity_check').fetchone()[0]
 contents=conn.execute('select table_name,data_type,srs_id from gpkg_contents').fetchall()
 names={x[0] for x in contents}
 gmeta={x[0]:x for x in conn.execute('select table_name,column_name,geometry_type_name,srs_id from gpkg_geometry_columns').fetchall()}
 layer_rows=[]
 for lyr in xml.findall('.//projectlayers/maplayer'):
  name=lyr.findtext('layername');source=norm(lyr.findtext('datasource'));ft=norm(lyr.findtext('provider'))
  localfile=source.split('|')[0];src_layer=source.split('layername=')[-1] if 'layername=' in source else ''
  resolve=(ROOT/localfile).resolve()
  relative=not Path(localfile).is_absolute() and localfile.startswith('./')
  custom={x.attrib.get('key'):x.attrib.get('value') for x in lyr.findall('./customproperties/property')}
  layer_rows.append({'qgs_layer':name,'data_source':source,'provider':ft,'is_relative':relative,'file_exists':resolve.exists(),
   'table_exists':src_layer in names,'gpkg_table':src_layer,'geometry_type':gmeta.get(src_layer,('','','',''))[2],
   'labels_enabled_attr':lyr.get('labelsEnabled'),'labels_enabled_property':custom.get('labeling/enabled'),
   'label_expression':custom.get('labeling/fieldName'),'labels_display_all':custom.get('labeling/displayAll')})
 r['checks']['qgs']={'version':xml.attrib.get('version'),'crs':xml.findtext('.//projectCrs/spatialrefsys/authid'),
     'layers':len(layer_rows),'referenced_data_files_exist':all(x['file_exists'] for x in layer_rows),
     'referenced_gpkg_tables_exist':all(x['table_exists'] for x in layer_rows),'relative_paths':all(x['is_relative'] for x in layer_rows),
     'three_label_layers':[{k:row[k] for k in ['qgs_layer','label_expression','labels_enabled_attr','labels_display_all']} for row in layer_rows if row['gpkg_table'] in ('V7_ALL_62_RETAINED_ROLES','V8_CIQ_PORT_6_EVIDENCE_POINTS','G_CIQ_ground_gateway')]}
 savecsv('V3_QGIS_layer_references.csv',layer_rows)
 r['checks']['gpkg']={'integrity_check':gpkg_integrity,'data_tables':len(contents),'non4326':[(x[0],x[2]) for x in contents if x[2]!=4326]}
 r['checks']['gpkg']['contents']=[{'table':name,'rows':conn.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0], 'geom_type':gmeta[name][2], 'srs_id':gmeta[name][3]} for name,_,_ in contents]
finally: conn.close()

# WGS84 coordinate checks and source equality
lyr62=gpd.read_file(GPKG,layer='V7_ALL_62_RETAINED_ROLES')
lyr6=gpd.read_file(GPKG,layer='V8_CIQ_PORT_6_EVIDENCE_POINTS')
lyr1=gpd.read_file(GPKG,layer='G_CIQ_ground_gateway')
nodes=[]
for g,k,zone in [(lyr62,'id','STUDY'),(lyr6,'node_id','PORT'),(lyr1,'id','GATEWAY')]:
 for _,x in g.iterrows():
  nid=norm(x[k]);z=norm(x.get('zone',zone));node={'node_id':nid,'zone':z,'name':norm(x['name']),
   'longitude':float(x.geometry.x),'latitude':float(x.geometry.y), 'source_layer':('62_STUDY' if zone=='STUDY' else zone),
   'operational_status':norm(x.get('uav_operational_admission',x.get('operational_uav_site',x.get('status','')))),
   'source_url':norm(x.get('source_url',x.get('source','')))}
  nodes.append(node)
node_map={x['node_id']:x for x in nodes}
assert len(nodes)==69
ids=[x['node_id'] for x in nodes];r['checks']['nodes']={'total':len(nodes),'unique_ids':len(set(ids)),'nonempty_names':sum(bool(n['name']) for n in nodes),
 'zone_count':dict(Counter(n['zone'] for n in nodes)),'lon_range':[min(x['longitude'] for x in nodes),max(x['longitude'] for x in nodes)],
 'lat_range':[min(x['latitude'] for x in nodes),max(x['latitude'] for x in nodes)], 'invalid_point_geometries':int(sum(not g.geometry.is_valid for g in (lyr62,lyr6,lyr1)) if False else sum((not row.geometry.is_valid or row.geometry.is_empty) for g in (lyr62,lyr6,lyr1) for _,row in g.iterrows()))}
for n in nodes:n['has_source_url']=bool(n['source_url'])
savecsv('V3_69_nodes_verified.csv',nodes)

source68=records(ROOT/'data/ALL_68_STUDY_NODES_LONG_LAT.csv')
check68=[]
for src in source68:
 n=node_map.get(src['node_id']); e=''
 if n is None:e='MISSING_IN_GPKG'
 else:
  dlon=abs(n['longitude']-float(src['longitude_E']));dlat=abs(n['latitude']-float(src['latitude_N']));
  if dlon>1e-7 or dlat>1e-7:e='COORDINATE_DIFFERENCE_GT_1e-7deg'
  if norm(src['name'])!=n['name']:e+=';NAME_DIFFERENCE'
 check68.append({'node_id':src['node_id'],'source_name':src['name'],'source_lon':src['longitude_E'],'source_lat':src['latitude_N'],
 'gpkg_name':n['name'] if n else None,'gpkg_lon':n['longitude'] if n else None,'gpkg_lat':n['latitude'] if n else None,'status':e or 'MATCH'})
r['checks']['source_csv_nodes']={'rows':len(source68),'matched':sum(x['status']=='MATCH' for x in check68),'mismatch':sum(x['status']!='MATCH' for x in check68)}
savecsv('V3_CSV_vs_GPKG_68_nodes.csv',check68)

# endpoint & length checks against independent WGS84 Geod
geod=Geod(ellps='WGS84')
links=[]
for name,idfield,u,v,source_len,modefield in [
 ('V7_ALL_111_GEOMETRY_ONLY','edge_id','from_id','to_id','geodesic_one_way_km',''),
 ('V8_CIQ_PORT_10_GROUND_AND_UAV_GEOMETRY','edge_id','from_id','to_id','one_way_km','mode')]:
 g=gpd.read_file(GPKG,layer=name)
 for _,x in g.iterrows():
  pt=x.geometry
  a=norm(x[u]);b=norm(x[v]);
  expected_a=node_map.get(a);expected_b=node_map.get(b)
  actual_start=pt.coords[0];actual_end=pt.coords[-1]
  direct=geod.inv(*actual_start,*actual_end)[2]/1000
  source_value=float(x[source_len]);
  source_status='UNRESOLVED_ENDPOINT' if not expected_a or not expected_b else 'ENDPOINT_MATCH'
  start_offset=geod.inv(actual_start[0],actual_start[1],expected_a['longitude'],expected_a['latitude'])[2] if expected_a else None
  end_offset=geod.inv(actual_end[0],actual_end[1],expected_b['longitude'],expected_b['latitude'])[2] if expected_b else None
  if start_offset is not None and (start_offset>3 or end_offset>3):source_status='ENDPOINT_GEOMETRY_OFFSET_GT3M'
  if pt.geom_type!='LineString' or pt.is_empty or not pt.is_valid:source_status+=';INVALID_GEOMETRY'
  mode='V7_UAV_GEOMETRY' if not modefield else norm(x[modefield]);
  links.append({'edge_id':norm(x[idfield]),'from_id':a,'to_id':b,'source_layer':name,'mode':mode,
   'source_distance_km':source_value,'geodesic_direct_km':round(direct,7),'distance_abs_error_m':round(abs(direct-source_value)*1000,3),
   'n_vertices':len(pt.coords),'start_offset_m':round(start_offset,3) if start_offset is not None else None,'end_offset_m':round(end_offset,3) if end_offset is not None else None,
   'status':source_status,'self_loop':a==b,
   'dji_5p6_flag':str(x.get('dji_scenario_5p6km',x.get('DJI_geom_5p6_km',''))),
   'wing_32p2_flag':str(x.get('wing_scenario_32p2km',x.get('Wing_geom_32p2_km',''))),
   'airspace_status':norm(x.get('valid_aip_and_notam_verified',x.get('airspace_current_verified',''))),
   'approval_status':norm(x.get('uas_flight_approved',x.get('commercial_operation_permission','')))})
# Note geodesic direct independent, not comparison for 3+-vertex polylines.
count=Counter(l['mode'] for l in links)
r['checks']['links']={'total':len(links),'by_mode':dict(count),'source_layer_count':dict(Counter(l['source_layer'] for l in links)),
 'unresolved_or_bad_endpoint':sum(l['status']!='ENDPOINT_MATCH' for l in links),
 'max_endpoint_offset_m':max(max((l['start_offset_m'] or 0),(l['end_offset_m'] or 0)) for l in links),
 'max_distance_error_m':max(l['distance_abs_error_m'] for l in links),'errors_over_150m':sum(l['distance_abs_error_m']>150 for l in links),
 'errors_over_10m':sum(l['distance_abs_error_m']>10 for l in links),'self_loops':sum(l['self_loop'] for l in links),
 'duplicated_edge_ids':dict((k,v) for k,v in Counter(l['edge_id'] for l in links).items() if v>1),
 'duplicate_directed_endpoints':{f'{k[0]}->{k[1]}':v for k,v in Counter((l['from_id'],l['to_id']) for l in links).items() if v>1}}
savecsv('V3_121_links_independent_geometry_audit.csv',links)

# count verified edge categories + model geom flags
r['checks']['links']['v8_modes']=dict(Counter(l['mode'] for l in links if l['source_layer'].startswith('V8_')))
# cross-check CSV vs layer by ID and rough coordinate
csvedges=records(ROOT/'data/V7_ALL_111_EDGE_AUDIT.csv')+records(ROOT/'data/V8_PORT_10_EDGE_AUDIT.csv')
actual={x['edge_id']:x for x in links}
r['checks']['source_csv_links']={'rows':len(csvedges),'match_ids':sum(x['edge_id'] in actual for x in csvedges),
 'unique_ids':len({x['edge_id'] for x in csvedges})}

# label QA sheet alignment
labelrows=records(ROOT/'qa/QA_ALL_69_NODE_LABELS.csv')
r['checks']['label_qa']={'rows':len(labelrows),'unique_ids':len({x.get('node_id',x.get('id','')) for x in labelrows}),'columns':list(labelrows[0]) if labelrows else []}

# compile AST only; do not execute untrusted scripts
pys=[]
for file in (ROOT/'code').glob('*.py'):
 try:
  ast.parse(file.read_text(encoding='utf-8-sig'),filename=file.name);stat='SYNTAX_OK'
 except (SyntaxError,UnicodeError) as e:stat='SYNTAX_ERROR '+str(e)
 pys.append({'file':file.name,'result':stat})
r['checks']['python_syntax']=pys

# Gate status; do not call these approved/legal operational sites
r['release']={'V2_S06_spatial_reference_inventory':'PASS_REFERENCE_ONLY',
             'V2_S06_qgis_3_22_desktop_open_and_layout_export':'HOLD_NOT_RUN_IN_QGIS_RUNTIME',
             'V2_S06_online_osm_basemap_borders_terrain':'HOLD_NEED_EXTERNAL_GIS',
             'V2_S06_drivable_road_access_and_turn_restrictions':'HOLD_NO_ROUTABLE_ROAD_GRAPH',
             'V2_S06_airspace_and_flight_regulatory_feasibility':'HOLD_REFERENCE_ONLY',
             'V2_S06_all_inputs_for_fuel_carbon_main_sim':'HOLD'}
(OUT/'V3_independent_audit.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'checks':{k:v for k,v in r['checks'].items() if k not in ('gpkg','qgs','python_syntax')},'gpkg_count':r['checks']['gpkg']['data_tables'],'qgs_layer_count':r['checks']['qgs']['layers'],'release':r['release']},ensure_ascii=False,indent=2))
