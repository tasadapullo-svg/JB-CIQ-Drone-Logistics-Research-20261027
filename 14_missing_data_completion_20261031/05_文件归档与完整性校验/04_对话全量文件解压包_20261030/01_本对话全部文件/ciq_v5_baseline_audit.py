#!/usr/bin/env python3
"""Independent audit of CIQ V5 immutable GIS baseline.
Usage: python ciq_v5_baseline_audit.py '/path/source.zip' '/path/output-directory'
Creates derived audit only, never edits the source or frozen GeoPackage.
Deps: geopandas, shapely, pyproj, pandas.
"""
import csv, hashlib, json, pathlib, sqlite3, sys, zipfile, collections, xml.etree.ElementTree as ET
import geopandas as gpd
import pandas as pd
from pyproj import Geod

SOURCE=pathlib.Path(sys.argv[1]); OUT=pathlib.Path(sys.argv[2]); OUT.mkdir(parents=True,exist_ok=True)
DATA=OUT/'source_extract'; DATA.mkdir(exist_ok=True)
with zipfile.ZipFile(SOURCE) as z:
    assert z.testzip() is None, 'Corrupted archive member'
    for inf in z.infolist():
        path=(DATA/inf.filename).resolve()
        assert path==DATA.resolve() or DATA.resolve() in path.parents, 'Unsafe archive path'
    z.extractall(DATA)
roots=[x for x in DATA.iterdir() if x.is_dir()]
assert len(roots)==1,roots
R=roots[0]; gp=R/'data/CIQ_ABC_V5_ACTIVE.gpkg'; old=R/'archive/CIQ_V4_FROZEN_UNMODIFIED.gpkg'
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''): h.update(b)
    return h.hexdigest()
def write(name,records):
    pd.DataFrame(records).to_csv(OUT/name,index=False,encoding='utf-8-sig')

checks=[]
def check(name,condition,detail=''):
    checks.append({'name':name,'status':'PASS' if condition else 'FAIL','detail':detail})

manifest=[]
for ln in (R/'SHA256_MANIFEST.txt').read_text(encoding='utf8').splitlines():
    if not ln.strip():continue
    exp,rel=ln.split(None,1); rel=rel.strip(); path=R/rel
    real=sha(path) if path.is_file() else ''
    manifest.append({'relative_path':rel,'expected_sha256':exp,'actual_sha256':real,'match':real==exp})
check('V5 archival SHA256 manifest',all(v['match'] for v in manifest),f'{len(manifest)}/{len(manifest)}')
write('SOURCE_28_SHA256_CHECKS.csv',manifest)
with sqlite3.connect(gp) as con:
    check('V5 GPKG SQLite integrity',con.execute('pragma integrity_check').fetchone()[0]=='ok')
    tables={row[0] for row in con.execute('select table_name from gpkg_contents')}
with sqlite3.connect(old) as con:
    check('V4 archive GPKG integrity',con.execute('pragma integrity_check').fetchone()[0]=='ok')
qgs=(R/'CIQ_ABC_V5_68_NODES_ONE_WMP228.qgs').read_bytes()
with zipfile.ZipFile(R/'CIQ_ABC_V5_68_NODES_ONE_WMP228.qgz') as q:
    memb=[n for n in q.namelist() if n.endswith('.qgs')]
    check('QGS = QGZ embedded XML',len(memb)==1 and q.read(memb[0])==qgs)
root=ET.fromstring(qgs)
layerrefs=[]
for layer in root.findall('.//projectlayers/maplayer'):
    name=layer.findtext('layername');source=layer.findtext('datasource') or ''
    if '|layername=' in source:
        filepart,ln=source.split('|layername=',1)
        local=(R/filepart).resolve()
        exists=local.exists() and ln in tables
        cat='vector'
    else:
        exists=source.startswith('crs=EPSG:3857&') and 'tile.openstreetmap.org' in source
        ln='online';cat='online_xyz'
    layerrefs.append({'layername':name,'source':source,'dataset_layer':ln,'kind':cat,'source_reference_valid':exists})
check('20 project map layers with valid refs',len(layerrefs)==20 and all(d['source_reference_valid'] for d in layerrefs))
write('V5_QGIS_LAYER_REFERENCES.csv',layerrefs)

node_layers=['A_NODES','B_NODES','C_NODES','A_PORT_6_NODES','A_GROUND_GATEWAY']
source_layers=['V7_ALL_62_RETAINED_ROLES','V8_CIQ_PORT_6_EVIDENCE_POINTS','G_CIQ_ground_gateway']
normalized=[]; N={}; oldN={}
for layer in node_layers:
    a=gpd.read_file(gp,layer=layer)
    for _,r in a.iterrows():
        key=str(r.get('node_id') or r.get('id'))
        area=str(r.get('zone') or ('A' if layer.startswith('A_') else ''))
        role=str(r.get('node_type') or r.get('node_role') or r.get('status') or '')
        desc=str(r.get('name') or '')
        x=float(r.geometry.x);y=float(r.geometry.y)
        diff_m=Geod(ellps='WGS84').inv(x,y,float(r.lon),float(r.lat))[2]
        status=str(r.get('uav_operational_admission') or r.get('operational_uav_site') or ('NO' if key=='G_CIQ' else ''))
        road=str(r.get('road_entry_verified') if 'road_entry_verified' in r else r.get('ground_entry_verified', 'NOT_VERIFIED'))
        rec={'node_id':key,'zone':area,'name':desc,'longitude_E':x,'latitude_N':y,'node_role_source':role,
             'layer':layer,'source_lon_lat_geom_discrepancy_m':round(diff_m,6),
             'operational_UAV_admission_source':status,'road_entry_verified_source':road,
             's07_dataset_status':'FROZEN_SPATIAL_REFERENCE_ONLY'}
        assert key not in N,('duplicate node',key)
        normalized.append(rec);N[key]=rec
for layer in source_layers:
    a=gpd.read_file(old,layer=layer)
    for _,r in a.iterrows():
        key=str(r.get('node_id') or r.get('id'))
        oldN[key]=(r.geometry.x,r.geometry.y)
check('V5 68 unique nonempty nodes',len(N)==68 and all(v['name'] for v in N.values()))
check('V5 coordinates = stored attributes',all(r['source_lon_lat_geom_discrepancy_m']<.01 for r in normalized))
check('V5 V4 unchanged coordinates and sole deletion',len(oldN)==69 and set(oldN)-set(N)=={'A_N10'} and not (set(N)-set(oldN)) and all(max(abs(oldN[k][0]-v['longitude_E']),abs(oldN[k][1]-v['latitude_N']))<1e-10 for k,v in N.items()))
# Important: the archived 68-row coordinate CSV is NOT the V5 active membership list.
arch=pd.read_csv(R/'archive/ALL_68_STUDY_NODES_LONG_LAT.csv',encoding='utf-8-sig',dtype={'node_id':str})
qa_ids=pd.read_csv(R/'qa/V5_ALL_68_NODE_IDS.csv',encoding='utf-8-sig',dtype={'node_id':str})
check('V5 QA 68-ID CSV matches active GPKG',set(qa_ids.node_id)==set(N) and len(qa_ids)==68)
check('Legacy archive CSV intentionally excluded',set(arch.node_id)-set(N)=={'A_N10'} and set(N)-set(arch.node_id)=={'G_CIQ'})
write('V5_ARCHIVE_CSV_MEMBERSHIP_HAZARD.csv',[
 {'node_id':n,'active_v5':n in N,'archive_68_csv':n in set(arch.node_id),'decision':'KEEP_V5_ACTIVE' if n in N else 'ARCHIVE_ONLY_DO_NOT_USE'}
 for n in sorted(set(arch.node_id)|set(N))])
write('V5_FROZEN_68_NODE_MASTER.csv',normalized)
write('V5_V4_COORDINATE_DIFF.csv',[{'node_id':n,'v4_lon':x,'v4_lat':y,'v5_lon':N[n]['longitude_E'] if n in N else '', 'v5_lat':N[n]['latitude_N'] if n in N else '', 'change':'UNCHANGED' if n in N else 'V5_ACTIVE_EXCLUDED_ARCHIVED'} for n,(x,y) in oldN.items()])

geom_layers=['A_GEOMETRY_LINKS','B_GEOMETRY_LINKS','C_GEOMETRY_LINKS','A_PORT_LINKS','INTER_AREA_LINKS','A_GROUND_ONLY_HOLD']
uav=[];ground=[];ground_hold=[]; allgeom=[]; point_counts=collections.Counter(); maxerr=0; missing=[]; invalid=[]; sourcegeom={}
for l in ['V7_ALL_111_GEOMETRY_ONLY','V8_CIQ_PORT_10_GROUND_AND_UAV_GEOMETRY']:
    for _,r in gpd.read_file(old,layer=l).iterrows():sourcegeom[str(r.edge_id)]=r.geometry
wmp=gpd.read_file(gp,layer='WMP228_ONE_2026_REFERENCE').geometry.iloc[0]
geod=Geod(ellps='WGS84')
for layer in geom_layers:
    d=gpd.read_file(gp,layer=layer)
    for _,r in d.iterrows():
        link=str(r.edge_id);s=str(r.from_id);t=str(r.to_id); g=r.geometry
        if layer=='A_GROUND_ONLY_HOLD': typ='GROUND_ONLY_HOLD_EXTRA'
        elif layer=='A_PORT_LINKS' and r['mode']=='GROUND_HANDOFF_STRAIGHT_REFERENCE':typ='GROUND_HANDOFF_STRAIGHT_REFERENCE'
        else:typ='UAV_GEOMETRY_CANDIDATE_ONLY'
        if s not in N or t not in N:missing.append(link)
        if not g.is_valid or g.is_empty:invalid.append(link)
        coords=list(g.coords)
        if s in N and t in N:
            departure=geod.inv(*coords[0],N[s]['longitude_E'],N[s]['latitude_N'])[2]
            arrival=geod.inv(*coords[-1],N[t]['longitude_E'],N[t]['latitude_N'])[2]
        else:departure=arrival=None
        calc_km=geod.line_length(*zip(*coords))/1000
        fld='geodesic_one_way_km' if 'geodesic_one_way_km' in d else 'one_way_km'
        val=r.get(fld)
        distance_err=abs(float(val)-calc_km) if pd.notna(val) else None
        if distance_err is not None:maxerr=max(maxerr,distance_err)
        rec={'edge_id':link,'from_id':s,'to_id':t,'source_layer':layer,'edge_type':typ,
             'geodesic_one_way_km_independent':round(calc_km,6),'stored_km_minus_independent_km':round(float(val)-calc_km,6) if distance_err is not None else '',
             'start_endpoint_error_m':round(departure,5) if departure is not None else '',
             'end_endpoint_error_m':round(arrival,5) if arrival is not None else '',
             'WMP228_2026_reference_circle_intersects':g.intersects(wmp),
             'road_route_distance_km':'','flight_operational_clearance':'NOT_VERIFIED',
             'operation_status':'GEOMETRY_ONLY_NOT_APPROVED'}
        allgeom.append(rec)
        if typ=='UAV_GEOMETRY_CANDIDATE_ONLY':uav.append(rec);point_counts[s]+=1;point_counts[t]+=1
        elif typ=='GROUND_HANDOFF_STRAIGHT_REFERENCE':ground.append(rec)
        else:ground_hold.append(rec)
        if layer!='A_GROUND_ONLY_HOLD':
            if link not in sourcegeom or not g.equals_exact(sourcegeom[link],1e-12): invalid.append(link)
check('121 candidate links = 116 UAV+5 ground',len(uav)==116 and len(ground)==5 and len(allgeom)==125)
check('4 extra ground HOLD lines',len(ground_hold)==4)
check('All link endpoints match 68 nodes',not missing)
check('All 121 V4 links geometry unchanged',not invalid and len(sourcegeom)==121)
check('Geodesic length within 1m source rounding',maxerr<=0.001,f'{maxerr*1000:.3f} m max')
check('No geometric intersection with single WMP reference',not any(r['WMP228_2026_reference_circle_intersects'] for r in allgeom))
write('V5_ALL_125_LINK_RECORDS_BY_TYPE.csv',allgeom)
write('V5_116_UAV_GEOMETRY_CANDIDATES.csv',uav)
write('V5_5_GROUND_HANDOFF_STRAIGHT_NOT_ROAD.csv',ground)
write('V5_4_EXTRA_GROUND_ONLY_HOLD.csv',ground_hold)
write('V5_12_NODES_WITHOUT_UAV_GEOMETRY.csv',[dict(v,reason='NO_INCIDENT_CANDIDATE_UAV_LINE_NOT_AN_ERROR') for k,v in N.items() if not point_counts[k]])
check('12 nodes without UAV geometry (preserved)',sum(point_counts[k]==0 for k in N)==12)
for l in ['A_AREA_OUTLINE','B_AREA_OUTLINE','C_AREA_OUTLINE']:
    g=gpd.read_file(gp,layer=l).geometry.iloc[0]
    check(f'{l} polygon valid and clear of 2026 WMP proxy',g.is_valid and not g.intersects(wmp))
check('Single CAAS_2026 WMP228 reference layer',len(gpd.read_file(gp,layer='WMP228_ONE_2026_REFERENCE'))==1)
check('No verified UAV operating sites in the 3 main zone layers',all((gpd.read_file(gp,layer=l)['uav_operational_admission'].astype(str)=='NO').all() for l in ['A_NODES','B_NODES','C_NODES']))
check('No verified road entry on 61 principal nodes',all((gpd.read_file(gp,layer=l)['road_entry_verified']==False).all() for l in ['A_NODES','B_NODES','C_NODES']))

stages=[
 {'order':0,'stage':'S06-V5 migration','tasks':3,'state':'GO','deliverable':'V5 hash/pinned spatial tables; migrate 69→68; isolate 116/5/4 without editing source'},
 {'order':1,'stage':'V2-S07 source data integration','tasks':7,'state':'PARTIAL / HOLD','deliverable':'153d/3672h weather, A/B/C directed OSM road, OD repair and frozen synthetic task population'},
 {'order':2,'stage':'V2-S08 petrol baseline M0','tasks':4,'state':'CODE GO / MAIN RUN HOLD','deliverable':'optimized multi-stop petrol routing, fuel consumption, idle/empty runs and costs'},
 {'order':3,'stage':'V2-S09 UAV aircraft energy','tasks':4,'state':'CODE GO / CALIBRATION HOLD','deliverable':'DJI FC30 and Wingcopter198 load, wind, return, reserves, charging audit'},
 {'order':4,'stage':'V2-S10 paired M0/M1/M2 simulation','tasks':5,'state':'HOLD','deliverable':'same tasks, dispatch/queue/rendezvous/return/fallback and full event logs'},
 {'order':5,'stage':'V2-S11 carbon and optimization','tasks':4,'state':'HOLD','deliverable':'consistent operational WTW/TTW accounting, delta-carbon, feasibility and Pareto'},
 {'order':6,'stage':'V2-S12 robustness and manuscript figures','tasks':4,'state':'HOLD','deliverable':'uncertainty by day/seed, strong baseline, break-even tests, SCI figure source tables and audit'}]
write('V5_NEXT_STAGE_STATUS.csv',stages)
result={'source_zip_name':SOURCE.name,'source_zip_sha256':sha(SOURCE),'source_gpkg_sha256':sha(gp),'source_gpkg_v4_sha256':sha(old),
        'nodes':len(N),'zones':dict(collections.Counter(v['zone'] for v in N.values())),
        'uav_geometry_links':len(uav),'ground_reference_links':len(ground),'extra_ground_hold_links':len(ground_hold),
        'active_candidate_links':len(uav)+len(ground),'wmp_reference_circles':1,
        'unconnected_to_uav_count':sum(point_counts[k]==0 for k in N),
        'missing_endpoints':missing,'geometry_errors':invalid,'max_length_discrepancy_metres':maxerr*1000,
        'frozen_space_status':'PASS_REFERENCE_ONLY','operational_network_status':'HOLD',
        'remaining_primary_experiment_stages':6,'S06_migration_preflight_required':True,
        'total_remaining_task_blocks_including_migration':sum(int(d['tasks']) for d in stages),
        'independent_checks':checks}
(OUT/'V5_INDEPENDENT_AUDIT.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf8')
check('All independent static tests pass',all(x['status']=='PASS' for x in checks))
(OUT/'V5_INDEPENDENT_AUDIT.json').write_text(json.dumps(result|{'independent_checks':checks},indent=2,ensure_ascii=False),encoding='utf8')
assert all(x['status']=='PASS' for x in checks),[x for x in checks if x['status']!='PASS']
print(json.dumps({k:v for k,v in result.items() if k not in ['independent_checks']},ensure_ascii=False,indent=2))
print('CHECKS',len(checks),'PASS',sum(x['status']=='PASS' for x in checks))
