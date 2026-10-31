# -*- coding: utf-8 -*-
"""CIQ Stage 02 QGIS 3.22+ read-only network QA.

Run INSIDE QGIS Desktop Python Console after opening the FINAL three-zone project:
    exec(compile(open(r'D:\\CIQ\\stage02_qgis_console.py',encoding='utf-8').read(),
                 r'D:\\CIQ\\stage02_qgis_console.py','exec'))

Optional environment variables: CIQ_STAGE02_OUT (output dir), CIQ_LEGACY_19_CSV.
No QGIS project or layer is saved/modified. All outputs are candidate evidence;
no automatic scientific/recalculation PASS is possible.
"""
from __future__ import annotations
import csv, datetime, hashlib, json, math, os, re, collections
from pathlib import Path
from qgis.core import QgsProject, QgsMapLayerType, QgsWkbTypes, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsGeometry

P=QgsProject.instance()
OUT=Path(os.environ.get('CIQ_STAGE02_OUT',str(Path.home()/'Documents'/'CIQ_Stage02_Audit'))).expanduser().resolve()
LEGACY=os.environ.get('CIQ_LEGACY_19_CSV','').strip()
OUT.mkdir(parents=True,exist_ok=True)
ID_KEYS=('site_id','node_id','station_id','point_id','hub_id','location_id','id')
NAME_KEYS=('site_name','node_name','station_name','display_name','name','label')
ZONE_KEYS=('zone','zone_id','area','area_id','region','region_id','study_area','subarea')
ROLE_KEYS=('node_role','site_role','role','facility_type','site_type','node_type','category','type')
FR_KEYS=('from_node','from_node_id','source_id','origin_id','from_id','start_node','u')
TO_KEYS=('to_node','to_node_id','target_id','destination_id','to_id','end_node','v')
LINE_ID_KEYS=('edge_id','line_id','connection_id','route_id','link_id','id')
IMPORTANT_REVIEW={'A_N05','A_N07','C21','A_C03'}
MAX_RECORDS_PER_LAYER=30000

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def cs(rows, name, fields):
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def norm_zone(s):
    s=str(s or '').strip().upper()
    if s in ('A','B','C'):return s
    m=re.match(r'^(?:AREA|ZONE|REGION)[_\s-]*([ABC])$',s)
    if m:return m.group(1)
    m=re.match(r'^([ABC])[_\s-]*(?:AREA|ZONE|REGION)$',s)
    return m.group(1) if m else ''

def zone_by_id(s):
    s=str(s or '').strip().upper()
    m=re.match(r'^([ABC])(?:[_-]?[NC]?\d{1,3})$',s)
    return m.group(1) if m else ''

def pick(fields,aliases):
    lower={x.casefold():x for x in fields}
    for x in aliases:
        if x in lower:return lower[x]
    return None

def attr(f,k):
    if not k:return ''
    try:
        x=f[k]
        return '' if x is None else str(x).strip()
    except Exception:return ''

def point_wgs84(g, xf):
    try:
        if g is None or g.isEmpty():return ('','','EMPTY')
        geom=QgsGeometry(g)
        geom.transform(xf)
        pt=geom.centroid().asPoint()
        lon=float(pt.x());lat=float(pt.y())
        if not math.isfinite(lon) or not math.isfinite(lat):return ('','','NON_FINITE')
        return lon,lat,('WITHIN_MY_SG_BROAD_ENVELOPE' if 1.0<=lat<=2.0 and 103.0<=lon<=104.5 else 'OUTSIDE_BROAD_ENVELOPE_REVIEW')
    except Exception as e:return ('','','TRANSFORM_FAILED:'+str(e)[:80])

def line_ends(g, xf):
    try:
        if g is None or g.isEmpty():return None
        geom=QgsGeometry(g);geom.transform(xf)
        if geom.isMultipart():
            parts=geom.asMultiPolyline()
            pts=[p for row in parts for p in row]
        else:pts=geom.asPolyline()
        if len(pts)<2:return None
        return ((pts[0].x(),pts[0].y()),(pts[-1].x(),pts[-1].y()))
    except Exception:return None

def hdist(a,b):
    lo1,la1=a;lo2,la2=b
    dlat=math.radians(la2-la1);dlon=math.radians(lo2-lo1)
    t=math.sin(dlat/2)**2+math.cos(math.radians(la1))*math.cos(math.radians(la2))*math.sin(dlon/2)**2
    return 12742000*math.asin(min(1,math.sqrt(t)))

def physical_sources(source):
    # QGIS normalizes many datasource URIs. For postgres/http/memory do not assume a local file.
    m=re.search(r"\bdbname=['\"]([^'\"]+)['\"]",source or '')
    core=(m.group(1) if m else (source or '').split('|',1)[0])
    if re.match(r'^(?:http:|https:|wms:|wfs:|xyz:|memory:|postgres:|virtual:)',core,re.I):return []
    try:path=Path(core)
    except Exception:return []
    if not path.is_file():return []
    found=[path]
    if path.suffix.lower()=='.shp':
        found += [path.with_suffix(s) for s in ('.shx','.dbf','.prj','.cpg') if path.with_suffix(s).exists()]
    return found

def legacy_csv_rows(path):
    if not path or not Path(path).is_file():return [],'LEGACY_19_REFERENCE_CSV_NOT_AVAILABLE'
    with open(path,encoding='utf-8-sig',newline='') as f: raw=list(csv.DictReader(f))
    if not raw:return [],'LEGACY_19_REFERENCE_CSV_EMPTY'
    field=list(raw[0]);idc=pick(field,ID_KEYS);zc=pick(field,ZONE_KEYS)
    latc=pick(field,('latitude','lat','y'));lonc=pick(field,('longitude','lon','lng','x'))
    if not idc:return [],'LEGACY_ID_FIELD_MISSING'
    result=[]
    for r in raw:
        i=str(r.get(idc,'')).strip()
        if not i:continue
        z=norm_zone(r.get(zc)) if zc else zone_by_id(i)
        result.append({'old_id':i,'zone':z,'longitude':r.get(lonc,'') if lonc else '',
                       'latitude':r.get(latc,'') if latc else ''})
    return result,'READ'

project_path=Path(P.fileName()) if P.fileName() else None
issues=[];layers=[];nodes=[];edges=[];files={}
if not project_path or not project_path.is_file():issues.append(('CRITICAL','UNSAVED_OR_UNAVAILABLE_PROJECT','QGIS main project is not a saved readable .qgs/.qgz'))
else:
    if OUT==project_path.parent or project_path.parent in OUT.parents:
        issues.append(('CRITICAL','OUTPUT_INSIDE_SOURCE_TREE','Audit directory should be outside QGIS source tree; adjust CIQ_STAGE02_OUT and rerun.'))
    files[str(project_path)]=sha(project_path)
if P.isDirty():issues.append(('CRITICAL','UNSAVED_PROJECT_CHANGES','Project currently has unsaved edits; save/backup under a new version before freeze'))
if not P.crs().isValid():issues.append(('CRITICAL','PROJECT_CRS_INVALID','QGIS project CRS invalid'))

ctx=P.transformContext();wgs=QgsCoordinateReferenceSystem('EPSG:4326')
for layer in sorted(P.mapLayers().values(),key=lambda x:(x.name().lower(),x.id())):
    is_vector=(layer.type()==QgsMapLayerType.VectorLayer)
    valid=layer.isValid()
    name=layer.name();fields=[q.name() for q in layer.fields()] if is_vector and valid else []
    srccrs=layer.crs().authid() if valid else ''
    lr={'layer_id':layer.id(),'name':name,'provider':layer.providerType() if is_vector else 'non_vector',
        'valid':valid,'vector':is_vector,'geometry_family':'','feature_count':'','crs':srccrs,
        'labels_enabled':'','source_uri':layer.source(), 'candidate_role':''}
    if not valid:issues.append(('CRITICAL','INVALID_LAYER',name));layers.append(lr);continue
    for p in physical_sources(layer.source()):
        if str(p) not in files:files[str(p)]=sha(p)
    if not is_vector:
        layers.append(lr);continue
    geomtype=layer.geometryType()
    kind=('point' if geomtype==QgsWkbTypes.PointGeometry else ('line' if geomtype==QgsWkbTypes.LineGeometry else 'other'))
    lr['geometry_family']=kind
    count=layer.featureCount();lr['feature_count']=count
    lr['labels_enabled']=bool(layer.labelsEnabled()) if kind=='point' else ''
    if not layer.crs().isValid():issues.append(('CRITICAL','INVALID_LAYER_CRS',name))
    idcol=pick(fields,ID_KEYS);namecol=pick(fields,NAME_KEYS);zonecol=pick(fields,ZONE_KEYS);rolecol=pick(fields,ROLE_KEYS)
    frcol=pick(fields,FR_KEYS);tocol=pick(fields,TO_KEYS)
    hint=bool(re.search(r'(?i)(ciq|hub|station|site|node|drone|link|feeder|corridor|connection|route|起降|节点|线路|航段)',name))
    take=(kind=='point' and idcol and (zonecol or hint)) or (kind=='line' and ((frcol and tocol) or hint))
    lr['candidate_role']=('CANDIDATE_'+kind.upper()) if take else 'NOT_AUTOMATICALLY_CLASSIFIED'
    if take and not physical_sources(layer.source()):
        issues.append(('CRITICAL','CANDIDATE_SOURCE_NOT_HASHABLE',name+': '+layer.source()[:150]))
    if not take:layers.append(lr);continue
    if count>MAX_RECORDS_PER_LAYER:
        issues.append(('CRITICAL','UNINSPECTED_LARGE_CANDIDATE_LAYER',name+': '+str(count)))
        layers.append(lr);continue
    if not layer.crs().isValid():layers.append(lr);continue
    try:xf=QgsCoordinateTransform(layer.crs(),wgs,ctx)
    except Exception as exc:
        issues.append(('CRITICAL','TRANSFORM_INIT_FAILED',name+': '+str(exc)));layers.append(lr);continue
    if kind=='point':
        if not idcol:issues.append(('CRITICAL','POINT_ID_FIELD_UNRECOGNIZED',name));layers.append(lr);continue
        if not namecol:issues.append(('CRITICAL','POINT_LABEL_FIELD_UNRECOGNIZED',name))
        if not layer.labelsEnabled():issues.append(('REVIEW','QGIS_LABELS_NOT_ENABLED_ON_CANDIDATE_POINT_LAYER',name))
    if kind=='line' and not (frcol and tocol):issues.append(('CRITICAL','LINE_ENDPOINT_FIELDS_MISSING',name))
    for f in layer.getFeatures():
        ident=attr(f,idcol if kind=='point' else pick(fields,LINE_ID_KEYS)) or str(f.id())
        zone_raw=attr(f,zonecol)
        zone=norm_zone(zone_raw) or zone_by_id(ident)
        origin=('ATTRIBUTE' if norm_zone(zone_raw) else ('ID_INFERRED_REVIEW' if zone else 'UNDETERMINED'))
        geom=f.geometry()
        if geom and not geom.isEmpty():
            try:
                if not geom.isGeosValid():issues.append(('CRITICAL','INVALID_FEATURE_GEOMETRY',name+'/'+ident))
            except Exception:issues.append(('REVIEW','FEATURE_GEOMETRY_VALIDITY_NOT_TESTED',name+'/'+ident))
        if kind=='point':
            lon,lat,coordstatus=point_wgs84(geom,xf)
            n={'layer':name,'feature_id':f.id(),'node_id':ident,'node_name':attr(f,namecol),
               'zone':zone,'zone_origin':origin,'role':attr(f,rolecol),'longitude':lon,'latitude':lat,
               'coord_status':coordstatus,'crs_source':srccrs,'label_enabled':bool(layer.labelsEnabled()),
               'audit_status':'REVIEW_ONLY_NOT_APPROVED_SITE'}
            nodes.append(n)
            if not n['node_name']:issues.append(('CRITICAL','NODE_NAME_BLANK',name+'/'+ident))
            if not n['zone']:issues.append(('CRITICAL','ZONE_UNRESOLVED',name+'/'+ident))
            elif n['zone_origin']!='ATTRIBUTE':issues.append(('REVIEW','ZONE_INFERRED_NOT_EXPLICIT',name+'/'+ident))
            if coordstatus!='WITHIN_MY_SG_BROAD_ENVELOPE':issues.append(('CRITICAL','NODE_COORDINATE_REVIEW',name+'/'+ident+': '+coordstatus))
            if ident in IMPORTANT_REVIEW:issues.append(('REVIEW','SPECIAL_SITE_REVIEW_REQUIRED',ident))
        elif kind=='line':
            endpoints=line_ends(geom,xf)
            edges.append({'layer':name,'feature_id':f.id(),'edge_id':ident,'zone':zone,'zone_origin':origin,
                          'from_id':attr(f,frcol),'to_id':attr(f,tocol),
                          'start_lon':endpoints[0][0] if endpoints else '', 'start_lat':endpoints[0][1] if endpoints else '',
                          'end_lon':endpoints[1][0] if endpoints else '', 'end_lat':endpoints[1][1] if endpoints else '',
                          'length_native':geom.length() if geom else '', 'crs_source':srccrs,
                          'referential_status':'NOT_CHECKED','start_endpoint_gap_m':'','end_endpoint_gap_m':'',
                          'audit_status':'CANDIDATE_SCREENING_CONNECTION_NOT_APPROVED_FLIGHT_ROUTE'})
            if endpoints is None:issues.append(('CRITICAL','EDGE_GEOMETRY_UNREADABLE',name+'/'+ident))
    layers.append(lr)

# QGIS project may show the same source as several layers: duplicate keys are not silently deduplicated.
index=collections.defaultdict(list);global_index=collections.defaultdict(list)
for n in nodes:
    index[(n['zone'],n['node_id'])].append(n);global_index[n['node_id']].append(n)
for k,arr in index.items():
    if len(arr)>1:issues.append(('CRITICAL','DUPLICATE_ZONE_NODE_ID',str(k)+' x'+str(len(arr))))
for e in edges:
    f_id=e['from_id'];t_id=e['to_id'];zone=e['zone']
    if not f_id or not t_id:
        e['referential_status']='ENDPOINT_FIELDS_EMPTY_OR_UNAVAILABLE'
        issues.append(('CRITICAL','EDGE_ENDPOINT_NOT_RECORDED',e['layer']+'/'+str(e['edge_id'])))
        continue
    left=index.get((zone,f_id),[]) if zone else global_index.get(f_id,[])
    right=index.get((zone,t_id),[]) if zone else global_index.get(t_id,[])
    if len(left)!=1 or len(right)!=1:
        e['referential_status']='UNRESOLVED_OR_AMBIGUOUS_NODE_ID'
        issues.append(('CRITICAL','EDGE_ENDPOINT_UNRESOLVED',e['layer']+'/'+str(e['edge_id'])))
        continue
    if not all(isinstance(v,(float,int)) for v in (e['start_lon'],e['start_lat'],e['end_lon'],e['end_lat'],left[0]['longitude'],left[0]['latitude'],right[0]['longitude'],right[0]['latitude'])):
        e['referential_status']='NO_VALID_ENDPOINT_COORDS';issues.append(('CRITICAL','EDGE_ENDPOINT_COORDINATES_MISSING',str(e['edge_id'])));continue
    a=hdist((e['start_lon'],e['start_lat']),(left[0]['longitude'],left[0]['latitude']))
    b=hdist((e['end_lon'],e['end_lat']),(right[0]['longitude'],right[0]['latitude']))
    e['start_endpoint_gap_m']=round(a,2);e['end_endpoint_gap_m']=round(b,2)
    if a>50 or b>50:
        e['referential_status']='ENDPOINT_GEOMETRY_GAP_GT_50M_REVIEW'
        issues.append(('CRITICAL','EDGE_ENDPOINT_GAP_GT_50M',str(e['edge_id'])+': '+str(round(a,1))+'/'+str(round(b,1))))
    else:e['referential_status']='ID_AND_GEOMETRY_PLAUSIBLE_REVIEW_REQUIRED'

legacy_rows,legacy_state=legacy_csv_rows(LEGACY)
if legacy_state!='READ':issues.append(('CRITICAL','OLD_19_SITE_DATA_NOT_GROUNDED',legacy_state))
cross=[]
for old in legacy_rows:
    k=(old['zone'],old['old_id']);n=index.get(k,[])
    row={'old_id':old['old_id'],'old_zone':old['zone'],'new_id':'','new_zone':'','distance_m':'',
         'migration_suggestion':'NOT_MATCHED','approved_for_transfer':'NO'}
    if len(n)==1:
        row['new_id']=n[0]['node_id'];row['new_zone']=n[0]['zone']
        row['migration_suggestion']='SAME_ID_COORD_REVIEW_REQUIRED'
        try:
            m=hdist((float(old['longitude']),float(old['latitude'])),(n[0]['longitude'],n[0]['latitude']))
            row['distance_m']=round(m,2)
            if m>20:row['migration_suggestion']='SAME_ID_MOVED_GT_20M_REVIEW'
        except Exception:row['migration_suggestion']='SAME_ID_COORD_UNVERIFIED'
    elif len(n)>1:row['migration_suggestion']='AMBIGUOUS_NODE_ID'
    elif old['old_id'] in global_index:row['migration_suggestion']='ID_FOUND_OTHER_ZONE_REVIEW'
    else:row['migration_suggestion']='OLD_ID_NOT_IN_NEW_CANDIDATES'
    cross.append(row)

zones=collections.Counter(n['zone'] for n in nodes if n['zone'])
for z in ('A','B','C'):
    if not zones.get(z):issues.append(('CRITICAL','ZONE_NOT_EVIDENCED',z))
if not nodes:issues.append(('CRITICAL','NO_CANDIDATE_NODES','No recognized point layer records'))
if not edges:issues.append(('CRITICAL','NO_CANDIDATE_EDGES','No recognized line layer records'))
if not project_path:issues.append(('CRITICAL','PROJECT_NOT_FROZEN','No saved project path'))
issues.extend([
    ('MANUAL_GATE','AIRSPACE_WMP228_CTR_CAAM_CAAS','Screen regulatory geometry, validity period, altitude and jurisdiction independently'),
    ('MANUAL_GATE','SITES_LAND_OBSTACLE_PERMISSIONS','Candidate search sites are not approved pads'),
    ('MANUAL_GATE','MATCHED_TASK_AND_ROAD_EMISSIONS','Never automatically reuse old 19-node OD / Stage6 electrical or generic UAV parameters'),
    ('MANUAL_GATE','RESEARCHER_SIGN_OFF','Freeze only after geometry, provenance, permissions and data dictionary approval'),
])

cs(layers,'01_qgis_layer_inventory.csv',['layer_id','name','provider','valid','vector','geometry_family','feature_count','crs','labels_enabled','source_uri','candidate_role'])
cs(nodes,'02_all_candidate_nodes.csv',['layer','feature_id','node_id','node_name','zone','zone_origin','role','longitude','latitude','coord_status','crs_source','label_enabled','audit_status'])
cs(edges,'03_candidate_connections.csv',['layer','feature_id','edge_id','zone','zone_origin','from_id','to_id','start_lon','start_lat','end_lon','end_lat','length_native','crs_source','referential_status','start_endpoint_gap_m','end_endpoint_gap_m','audit_status'])
cs([{'source_path':path,'sha256':digest} for path,digest in sorted(files.items())],'04_source_SHA256_manifest.csv',['source_path','sha256'])
cs(cross,'05_legacy_new_node_crosswalk_REVIEW.csv',['old_id','old_zone','new_id','new_zone','distance_m','migration_suggestion','approved_for_transfer'])
oldkeys={(o['zone'],o['old_id']) for o in legacy_rows}
added=[{'node_id':n['node_id'],'zone':n['zone'],'node_name':n['node_name'],'migration_suggestion':'NEW_CANDIDATE_NOT_IN_LEGACY','review_required':'YES'} for n in nodes if (n['zone'],n['node_id']) not in oldkeys]
cs(added,'05b_new_node_candidates_NOT_IN_LEGACY.csv',['node_id','zone','node_name','migration_suggestion','review_required'])
cs([{'severity':a,'code':b,'evidence':c} for a,b,c in issues],'06_issue_register.csv',['severity','code','evidence'])
summary={'stage':'02','generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
   'project_file':str(project_path) if project_path else None,'project_file_sha256':files.get(str(project_path)) if project_path else None,
   'project_crs':P.crs().authid(),'project_dirty':bool(P.isDirty()),'qgis_version_compatibility':'Author target QGIS 3.22+; execute within actual QGIS',
   'counts':{'layers':len(layers),'candidate_nodes':len(nodes),'candidate_edges':len(edges),'zones':dict(zones),'legacy_nodes_read':len(legacy_rows),
             'critical_issues':sum(a=='CRITICAL' for a,_,_ in issues)},
   'critical_issue_codes':sorted({b for a,b,_ in issues if a=='CRITICAL'}),
   'manual_gate_codes':sorted({b for a,b,_ in issues if a=='MANUAL_GATE'}),
   'status':'HOLD_PENDING_RESEARCHER_REVIEW','scientific_spatial_input_frozen':False,
   'numerical_recalculation_released':False,
   'interpretation':'QGIS geometry/identity preflight, not aviation approval or traffic/emissions validation'}
(OUT/'07_stage02_spatial_gate.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print('CIQ Stage 02 QA exported to:',OUT)
print(json.dumps(summary,ensure_ascii=False,indent=2))
