#!/usr/bin/env python3
"""Read-only scientific input builder: V3 candidate reference GIS -> S06 datasets.

Requires Python >=3.9; shapely >=2 and pyproj >=3 for independent geometry audit.
Does NOT make real-world access or aviation-authorisation determinations.
"""
import argparse, csv, hashlib, io, json, math, shutil, sqlite3, sys, tempfile, zipfile
from collections import Counter
from pathlib import Path
from shapely import wkb
from pyproj import Geod

GEOD=Geod(ellps='WGS84')
REQUIRED=[
 'data/CIQ_ABC_FINAL_EDITABLE.gpkg','data/V7_ALL_62_NODE_EVIDENCE.csv',
 'data/V8_PORT_6_NODE_EVIDENCE.csv','data/V7_ALL_111_EDGE_AUDIT.csv',
 'data/V8_PORT_10_EDGE_AUDIT.csv','data/ALL_68_STUDY_NODES_LONG_LAT.csv',
 'qa/QA_ALL_69_NODE_LABELS.csv', 'CIQ_ABC_ALL_69_NAMES_PORTABLE.qgs',
 'CIQ_ABC_ALL_69_NAMES_PORTABLE.qgz']
RELEASE_TAG='QGIS_ABC_V3_20261030_S06_SOURCE_LOCK'
CAAM='https://www.caam.gov.my/public/unmanned-aircraft-system-uas/'
CAAM_AIS='https://www.caam.gov.my/public/ais/'
CAAS='https://www.caas.gov.sg/unmanned-aircraft/no-fly-zones-and-ua-flying-areas/'
CAAS_UA='https://www.caas.gov.sg/resources/regulatory-requirements-and-guidelines/unmanned-aircraft/'


def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def die(condition,msg):
 if not condition: raise ValueError(msg)

def parse_csv(p):
 with open(p,encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

def write_csv(path, rows, fields):
 path.parent.mkdir(parents=True,exist_ok=True)
 with open(path,'w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def write_json(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(obj,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')

def geom_gpkg(raw):
 die(raw is not None and raw[:2]==b'GP','Invalid GeoPackage geometry header')
 flags=raw[3]; env=(flags>>1)&7
 esizes={0:0,1:32,2:48,3:48,4:64}
 die(env in esizes,'Unsupported GPKG envelope')
 return wkb.loads(bytes(raw[8+esizes[env]:]))

def _extract(zip_path,where):
 with zipfile.ZipFile(zip_path) as z:
  die(z.testzip() is None,'ZIP failed CRC check')
  for i in z.infolist():
   p=Path(i.filename)
   die(not p.is_absolute() and '..' not in p.parts,'Unsafe archive member')
  z.extractall(where)
 matches=list(where.rglob('CIQ_ABC_FINAL_EDITABLE.gpkg'))
 die(len(matches)==1,'Expected exactly one V3 GPKG')
 return matches[0].parent.parent

def build(input_zip,out,old_exceptions=None):
 input_zip=Path(input_zip).resolve();out=Path(out).resolve()
 die(input_zip.is_file(),'Original uploaded V3 ZIP does not exist')
 out.mkdir(parents=True,exist_ok=True)
 zip_sha=sha(input_zip)
 with tempfile.TemporaryDirectory(prefix='s06_v3_') as temp:
  root=_extract(input_zip,Path(temp))
  for r in REQUIRED:die((root/r).is_file(),'Missing required V3 member: '+r)
  gpkg=root/'data/CIQ_ABC_FINAL_EDITABLE.gpkg'
  c=sqlite3.connect(f'file:{gpkg}?mode=ro',uri=True)
  c.row_factory=sqlite3.Row
  die(c.execute('PRAGMA integrity_check').fetchone()[0]=='ok','GPKG corrupt')
  contents={z['table_name']:z['srs_id'] for z in c.execute('SELECT table_name,srs_id FROM gpkg_contents')}
  die(len(contents)==19 and all(srid==4326 for srid in contents.values()),'Unexpected layer count or CRS')
  v7=parse_csv(root/'data/V7_ALL_62_NODE_EVIDENCE.csv')
  v8=parse_csv(root/'data/V8_PORT_6_NODE_EVIDENCE.csv')
  e7=parse_csv(root/'data/V7_ALL_111_EDGE_AUDIT.csv')
  e8=parse_csv(root/'data/V8_PORT_10_EDGE_AUDIT.csv')
  die((len(v7),len(v8),len(e7),len(e8))==(62,6,111,10),'Unexpected reference record counts')
  base={r['id']:r for r in v7};port={r['node_id']:r for r in v8}
  die(len(base)==62 and len(port)==6 and not(set(base)&set(port)),'Duplicate input IDs')
  gw=c.execute('SELECT * FROM G_CIQ_ground_gateway').fetchall()
  die(len(gw)==1 and gw[0]['id']=='G_CIQ','CIQ gateway not unique')
  g=gw[0]
  nodes=[]
  for r in v7:
   nodes.append(dict(node_id=r['id'],zone=r['zone'],name=r['name'],longitude=float(r['lon']),latitude=float(r['lat']),
    class_source='V7_62_RETAINED_REFERENCE',node_type=r['node_type'],source_url=r['source_url'],
    coordinate_semantics=r.get('coordinate_semantics',''),old_id_in_v3=r['legacy_id'],
    ground_entry_evidence=r.get('road_entry_verified',''),pad_evidence=r.get('pad_verified',''),
    airspace_evidence=r.get('airspace_validated_current',''),operational_evidence=r.get('uav_operational_admission',''),
    road_access_gate='HOLD_NO_ROUTABLE_ROAD_NETWORK',airspace_gate='HOLD_NO_CURRENT_EFFECTIVE_AIP_NOTAM_BOUNDARIES',
    station_gate='HOLD_REFERENCE_SEARCH_SITE_NOT_APPROVED',sim_node_gate='REFERENCE_ONLY'))
  for r in v8:
   nodes.append(dict(node_id=r['node_id'],zone='PORT_A',name=r['name'],longitude=float(r['lon']),latitude=float(r['lat']),
    class_source='V8_6_PORT_REFERENCES',node_type=r['node_role'],source_url=r['source_url'],
    coordinate_semantics=r.get('coordinate_meaning',''),old_id_in_v3='',
    ground_entry_evidence=r.get('ground_entry_verified',''),pad_evidence=r.get('site_owner_permission',''),
    airspace_evidence=r.get('current_aip_notam_verified',''),operational_evidence=r.get('operational_uav_site',''),
    road_access_gate='HOLD_NO_ROUTABLE_ROAD_NETWORK',airspace_gate='HOLD_NO_CURRENT_EFFECTIVE_AIP_NOTAM_BOUNDARIES',
    station_gate='HOLD_REFERENCE_SEARCH_SITE_NOT_APPROVED',sim_node_gate='REFERENCE_ONLY'))
  nodes.append(dict(node_id='G_CIQ',zone='GATEWAY',name=g['name'],longitude=float(g['lon']),latitude=float(g['lat']),
    class_source='GROUND_CIQ_GATEWAY',node_type='GROUND_GATEWAY_ONLY',source_url=g['source'],
    coordinate_semantics='REFERENCE_GATEWAY_NOT_VALIDATED_VEHICLE_ACCESS',old_id_in_v3='',
    ground_entry_evidence='NOT_VALIDATED',pad_evidence='NOT_APPLICABLE',airspace_evidence='NOT_APPLICABLE',
    operational_evidence='GROUND_ONLY',road_access_gate='HOLD_NO_ROUTABLE_ROAD_NETWORK',
    airspace_gate='NOT_APPLICABLE_GROUND_ONLY',station_gate='GROUND_GATEWAY_NOT_A_UAV_PAD',sim_node_gate='REFERENCE_ONLY'))
  ids={r['node_id'] for r in nodes};die(len(nodes)==len(ids)==69,'69 unique nodes not met')
  coords={r['node_id']:(r['longitude'],r['latitude']) for r in nodes}
  # Cross-check every source point against original GPKG geometries; not just CSV columns.
  point_gpk={}
  for layer,id_field in [('V7_ALL_62_RETAINED_ROLES','id'),('V8_CIQ_PORT_6_EVIDENCE_POINTS','node_id'),('G_CIQ_ground_gateway','id')]:
   for r in c.execute(f'SELECT * FROM "{layer}"'):
    gpt=geom_gpkg(r['geom'])
    die(gpt.geom_type=='Point',f'Point expected {layer}')
    point_gpk[r[id_field]]=(gpt.x,gpt.y)
  max_coord_delta=0.0
  for node,xy in coords.items():
   die(node in point_gpk, f'Node missing source GeoPackage {node}')
   d=max(abs(xy[0]-point_gpk[node][0]),abs(xy[1]-point_gpk[node][1]))
   max_coord_delta=max(d,max_coord_delta)
   die(d < 1e-8,f'Source GPKG point coordinate mismatch: {node}')
  # 68 reference CSV excludes the ground gateway; retain that boundary explicit.
  raw68=parse_csv(root/'data/ALL_68_STUDY_NODES_LONG_LAT.csv')
  die(len(raw68)==68,'Expected 68 row reference CSV')
  for r in raw68:
   xy=coords.get(r['node_id']);die(xy is not None,f'Missing source node {r["node_id"]}')
   die(abs(float(r['longitude_E'])-xy[0])<1e-8 and abs(float(r['latitude_N'])-xy[1])<1e-8,'68 CSV coords differ')
  # Old benchmark is 19 A09+B10; note that V3 additionally calls A10 a legacy alias.
  # These are candidate ID matches, not historical Stage 8 coordinate verification.
  old_ids=set(['A%02d'%i for i in range(1,10)]+['B%02d'%i for i in range(0,10)])
  die(len(old_ids)==19 and old_ids<=ids,'Expected old-reference IDs missing')
  crosswalk=[]
  for r in nodes:
   n=r['node_id'];old=n if n in old_ids else ''
   if old:status='SAME_ID_CANDIDATE_COORDINATES_NOT_INDEPENDENTLY_VERIFIED'
   elif n=='A10':status='V3_LEGACY_ALIAS_OUTSIDE_19_STAGE8_REFERENCE_COUNT_REVIEW'
   else:status='NO_CONFIRMED_STAGE8_REFERENCE_ID'
   crosswalk.append(dict(new_node_id=n,legacy_node_id_candidate=old,new_name=r['name'],zone=r['zone'],
    new_longitude=r['longitude'],new_latitude=r['latitude'],crosswalk_status=status,
    old_source_sha256='',old_longitude='',old_latitude='',old_coordinate_delta_m='',
    source='V3 ID and prior Stage8 summary; original 19-reference snapshot still required'))
  # GeoPackage original vector lines; reconstruct GeoJSON with its actual vertices.
  gpkg_edges={}
  for layer in ['V7_ALL_111_GEOMETRY_ONLY','V8_CIQ_PORT_10_GROUND_AND_UAV_GEOMETRY']:
   for r in c.execute(f'SELECT * FROM "{layer}"'):
    geom=geom_gpkg(r['geom']);die(geom.geom_type=='LineString' and not geom.is_empty,'Invalid linestring')
    die(r['edge_id'] not in gpkg_edges,'duplicate edge id')
    gpkg_edges[r['edge_id']]=(geom,layer)
  die(len(gpkg_edges)==121,'Expected 121 GPKG lines')
  uv=[];ground=[]; max_line_delta_m=0; hist_count=Counter()
  for r,src in [(row,'V7_111') for row in e7]+[(row,'V8_10') for row in e8]:
   eid=r['edge_id'];a=r['from_id'];b=r['to_id']
   die(a in ids and b in ids and a!=b,f'Bad edge endpoints: {eid}')
   die(eid in gpkg_edges,'Edge missing in GPKG '+eid)
   geom,source_layer=gpkg_edges[eid]
   die(geom.is_valid,'Invalid source edge geometry '+eid)
   acoord=geom.coords[0];bcoord=geom.coords[-1]
   for expected,actual in [(coords[a],acoord),(coords[b],bcoord)]:
    die(max(abs(expected[0]-actual[0]),abs(expected[1]-actual[1]))<1e-8,'Wrong GPKG edge endpoint '+eid)
   expected_km=float(r.get('geodesic_one_way_km') or r.get('one_way_km'))
   line_length_m=abs(GEOD.line_length(*zip(*geom.coords)))
   delta_m=abs(line_length_m-expected_km*1000);max_line_delta_m=max(max_line_delta_m,delta_m)
   die(delta_m<=1.1,f'Geodesic length mismatch {eid}: {delta_m:.2f}m')
   is_ground=src=='V8_10' and r['mode']=='GROUND_HANDOFF_STRAIGHT_REFERENCE'
   die(src=='V7_111' or r['mode'] in ('UAV_GEOMETRY_SEARCH','GROUND_HANDOFF_STRAIGHT_REFERENCE'), 'Unexpected V8 mode')
   # Topology type ALWAYS dominates range-flag columns.
   common=dict(edge_id=eid,source_series=src,from_id=a,to_id=b,from_zone=next(x['zone'] for x in nodes if x['node_id']==a),
    to_zone=next(x['zone'] for x in nodes if x['node_id']==b),line_distance_geodesic_km=round(line_length_m/1000,6),
    source_distance_km=expected_km,distance_attribute_delta_m=round(delta_m,3),
    geometry_type='STRAIGHT_GEOMETRIC_REFERENCE_NOT_APPROVED_ROUTE',
    current_legal_airspace='HOLD',ground_access='HOLD',endpoint_pad_approval='HOLD',
    computational_release='DENY_NOT_A_ROUTED_OR_APPROVED_OPERATION')
   if not is_ground:
    common.update(line_mode='UAV_GEOMETRY_SEARCH',classification='RESEARCH_GEOMETRY_ONLY',
      dji_5p6km_scenario_only=r.get('dji_scenario_5p6km',r.get('DJI_geom_5p6_km','')),
      wing_32p2km_scenario_only=r.get('wing_scenario_32p2km',r.get('Wing_geom_32p2_km','')),
      historical_wmp_circle_intersection=r.get('wmp_union_full_circle_intersects',r.get('historical_circle_crossing','')),
      historical_wmp_semantics='HISTORICAL_NON_AUTHORITATIVE_SCREEN_NOT_PERMISSION',
      route_altitude_m='',route_clearance_3d='HOLD',flight_energy_kwh='',
      drone_dispatch_released='NO')
    uv.append((common,geom))
   else:
    common.update(line_mode='GROUND_HANDOFF_STRAIGHT_REFERENCE',classification='GROUND_RELATION_NOT_ROAD_ROUTE',
     original_dji_flag_must_be_ignored=r.get('DJI_geom_5p6_km',''),
     original_wing_flag_must_be_ignored=r.get('Wing_geom_32p2_km',''),
     road_distance_km='',road_travel_time_min='',road_directed_route_id='',road_route_validation='HOLD_NO_OSM_ROAD_GRAPH',
     road_simulation_released='NO')
    ground.append((common,geom))
  die((len(uv),len(ground))==(116,5),'Edge isolation failed')
  die(all(row['line_mode']=='UAV_GEOMETRY_SEARCH' for row,_ in uv),'UAV mode mismatch')
  die(all(row['line_mode']=='GROUND_HANDOFF_STRAIGHT_REFERENCE' for row,_ in ground),'Ground mode mismatch')
  # Every source point remains in the output, even when operational approval is unavailable.
  byid={r['node_id']:r for r in nodes}
  road=[];air=[]
  for r in nodes:
   typ=r['node_type'];is_ground=(r['node_id']=='G_CIQ')
   road.append(dict(node_id=r['node_id'],zone=r['zone'],name=r['name'],lon=r['longitude'],lat=r['latitude'],
    legacy_v3_ground_entry_evidence=r['ground_entry_evidence'],road_graph_present='NO',
    road_snap_osm_node_id='',road_snap_distance_m='',connected_component='',access_road_direction_check='',
    nearest_legal_vehicle_entry='',road_access_verified='NO',gate='HOLD_NO_ROUTABLE_ROAD_GRAPH',
    next_evidence='OSM routable line geometry + legal access + directional routing + independent verification'))
   air.append(dict(node_id=r['node_id'],zone=r['zone'],reference_type=r['class_source'],
    historical_WMP228_circle_geometry='IN_V3_REFERENCE_ONLY_NOT_AIRSPACE_LAW',
    senai_aerodrome_advisory='IN_V3_REFERENCE_ONLY_NOT_CURRENT_AUTHORIZATION',
    official_caam_current_date_AIP_boundary_loaded='NO',caam_NOTAM_effective_time_checked='NO',
    caas_OneMap_effective_geo_boundary_loaded='NO',cross_border_UA_permit_evidence='NO',
    parcel_owner_permission='NO',actual_takeoff_approval='NO',
    regulatory_status=('GROUND_GATEWAY_NOT_UAV_PAD' if is_ground else 'UNKNOWN_NEEDS_AUTHORITATIVE_REVIEW'),
    scenario_screen_gate=('NOT_APPLICABLE_GROUND' if is_ground else 'HOLD_AIRSPACE_AND_SITE_EVIDENCE'),
    caam_url=CAAM,caam_ais_url=CAAM_AIS,caas_url=CAAS))
  outdata=out/'data';outdata.mkdir(exist_ok=True)
  node_fields=list(nodes[0]);write_csv(outdata/'S06_69_node_master.csv',nodes,node_fields)
  write_csv(outdata/'S06_crosswalk_legacy19_vs_V3_69_NOT_VERIFIED.csv',crosswalk,list(crosswalk[0]))
  write_csv(outdata/'S06_116_uav_geometry_candidates_ONLY.csv',[r for r,g in uv],list(uv[0][0]))
  write_csv(outdata/'S06_5_ground_handoff_straight_references_NOT_ROUTES.csv',[r for r,g in ground],list(ground[0][0]))
  write_csv(outdata/'S06_69_road_access_evidence_HOLD.csv',road,list(road[0]))
  write_csv(outdata/'S06_69_airspace_and_site_evidence_HOLD.csv',air,list(air[0]))
  geo=out/'geojson';geo.mkdir(exist_ok=True)
  def geowrite(path,pairs):
   features=[{'type':'Feature','geometry':{'type':g.geom_type,'coordinates':list(g.coords)},'properties':r} for r,g in pairs]
   write_json(path,{'type':'FeatureCollection','name':path.stem,'features':features})
  from shapely.geometry import Point
  geowrite(geo/'S06_69_reference_nodes.geojson',[(r,Point(r['longitude'],r['latitude'])) for r in nodes])
  geowrite(geo/'S06_116_UAV_GEOMETRY_ONLY.geojson',uv)
  geowrite(geo/'S06_5_ground_handoff_NOT_ROADS.geojson',ground)
  legacy_map=[]
  if old_exceptions:
   p=Path(old_exceptions)
   if p.exists():
    for r in parse_csv(p):
     od=r.get('od_id','');from_id=r.get('origin_id',od.split('_')[0]);to_id=r.get('destination_id',od.split('_')[-1])
     legacy_map.append(dict(original_od_id=od,from_id=from_id,to_id=to_id,
       old_source_status=r.get('original_status',''),old_diagnostic=r.get('diagnostic_category',''),
       old_repair_applied=r.get('repair_applied',''),endpoint_ids_in_new_v3=(from_id in ids and to_id in ids),
       status='HOLD_NOT_A_CURRENT_ROUTED_OD',note='Legacy candidate repair was not applied; new road graph required'))
  if legacy_map:write_csv(outdata/'S06_legacy37_road_OD_exceptions_NOT_REPAIRED.csv',legacy_map,list(legacy_map[0]))
  source_files=[root/x for x in REQUIRED]+[input_zip]
  if old_exceptions and Path(old_exceptions).exists():source_files.append(Path(old_exceptions).resolve())
  source_register=[dict(original_rel_path=(str(p.relative_to(root)) if p.is_relative_to(root) else ('UPLOADED_V3_SOURCE_ARCHIVE' if p==input_zip else 'STAGE04_37_OD_SOURCE')),
    sha256=sha(p),bytes=p.stat().st_size,read_permission='READ_ONLY',source_release='V3_SOURCE_LOCK') for p in source_files]
  write_csv(out/'qa/S06_input_hash_register.csv',source_register,list(source_register[0]))
  official=[{'authority':'CAAM','source_type':'UAS requirements','url':CAAM,'evidence_scope':'requirements_only','geospatial_artifact_loaded':False,'permit_validated':False},
   {'authority':'CAAM AIS','source_type':'AIP AIP SUP NOTAM service','url':CAAM_AIS,'evidence_scope':'portal_reference_only','geospatial_artifact_loaded':False,'permit_validated':False},
   {'authority':'CAAS','source_type':'OneMap no-fly and UA areas','url':CAAS,'evidence_scope':'guidance_reference_only','geospatial_artifact_loaded':False,'permit_validated':False},
   {'authority':'CAAS','source_type':'Cross-border UA permit circular AC101-2-3','url':CAAS_UA,'evidence_scope':'regulatory_document_index_only','geospatial_artifact_loaded':False,'permit_validated':False}]
  write_json(out/'qa/S06_official_regulatory_evidence_register.json',official)
  gate={'spatial_reference_lock':'PASS_FOR_REFERENCE_AND_S06_INPUT_BUILD',
        'node_identity_consistency':'PASS','geometry_category_separation':'PASS',
        'legacy_19_old_new_coordinates':'HOLD_SOURCE_OLD19_NOT_RETRIEVED',
        'actual_routable_road_graph':'HOLD_NOT_IN_V3_ARCHIVE',
        'road_entry_legal_access':'HOLD_NOT_VERIFIED',
        'effective_time_official_airspace':'HOLD_NOT_VERIFIED',
        'operator_site_pad_approval':'HOLD_NOT_VERIFIED',
        'QGIS_3_22_GUI_render':'HOLD_NOT_TESTED',
        'S07_node_reference_handoff':'CONDITIONAL_GO_MAPPING_ONLY',
        'M0_M1_M2_real_experiment':'HOLD_NO_ROUTING_ENERGY_COMPLIANCE'}
  summary={'source_v3_sha256':zip_sha,'release_tag':RELEASE_TAG,'gis_crs':'EPSG:4326',
           'nodes_total':len(nodes),'nodes_by_zone':dict(Counter(r['zone'] for r in nodes)),
           'uav_geometry_candidates':len(uv),'ground_reference_beelines':len(ground),
           'old_stage8_19_candidate_ids':len(old_ids),
           'old_stage8_crosspackage_coords_verified':False,
           'legacy_a10_claims_alias_but_stage8_A_count_9':'HOLD_REVIEW',
           'road_access_independently_verified':0,'official_airspace_boundaries_loaded':0,
           'approved_UAV_sites':0,'max_node_geom_coordinate_delta_deg':max_coord_delta,
           'max_line_geodesic_attribute_delta_m':round(max_line_delta_m,3),
           'old_road_exceptions_linked':len(legacy_map),
           'gates':gate,'source_note':'V3 GIS polygons are reference constructs. No road travel or flight permissions inferred.'}
  write_json(out/'qa/S06_formal_rebuild_audit.json',summary)
  write_json(out/'qa/S06_release_gates.json',gate)
  c.close()
  return summary

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--v3',required=True,help='Original V3 ZIP')
 p.add_argument('--out',required=True,help='Separate output folder (never source archive)')
 p.add_argument('--legacy-37',default='',help='Optional old stage 04 exception CSV')
 args=p.parse_args()
 result=build(args.v3,args.out,args.legacy_37 or None)
 print(json.dumps(result,indent=2,ensure_ascii=False))
