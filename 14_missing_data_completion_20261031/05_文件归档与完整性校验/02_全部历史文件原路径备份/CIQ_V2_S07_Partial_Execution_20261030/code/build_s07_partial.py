#!/usr/bin/env python3
"""V2-S07 real-data partial build. Read-only input; never fabricates weather, routes or orders.

Examples:
 python code/build_s07_partial.py --root .
 python -m unittest discover -s tests -v
Only releases spatial/time/metadata. Operations and carbon computations are HARD HOLD.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json,math,pathlib,collections
from zoneinfo import ZoneInfo

UTC=dt.timezone.utc
MYT=ZoneInfo('Asia/Kuala_Lumpur')
REPO='tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027'
GIT='4569817b8145efe2ae06f4b21addc1986f971c12'

def readcsv(path):
    with open(path, encoding='utf-8-sig', newline='') as fh: return list(csv.DictReader(fh))
def savecsv(path, rows, keys):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(keys),extrasaction='ignore');w.writeheader();w.writerows(rows)
def writejson(p,x):p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def geod(lon1,lat1,lon2,lat2):
    a1,p1,a2,p2=map(math.radians,(lon1,lat1,lon2,lat2))
    h=math.sin((p2-p1)/2)**2+math.cos(p1)*math.cos(p2)*math.sin((a2-a1)/2)**2
    return 6371008.8*2*math.asin(min(1.,math.sqrt(h)))
def namesim(a,b):
    import re
    a=set(re.findall(r'[a-z0-9]+',a.lower()));b=set(re.findall(r'[a-z0-9]+',b.lower()))
    common=a&b
    return len(common)/len(a|b) if a|b else 0

def build(root:pathlib.Path):
    I=root/'inputs';O=root/'outputs';Q=root/'qa';O.mkdir(exist_ok=True,parents=True);Q.mkdir(exist_ok=True,parents=True)
    nodes=readcsv(I/'S06_69_node_master.csv');uav=readcsv(I/'S06_116_uav_geometry_candidates_ONLY.csv')
    ground=readcsv(I/'S06_5_ground_handoff_straight_references_NOT_ROUTES.csv')
    legacy=readcsv(I/'legacy19_COORDINATE_EXTRACT_FROM_GITHUB.csv')
    weather=json.loads((I/'WEATHER_MONTHLY_GITHUB_QC_EXTRACT.json').read_text(encoding='utf-8'))
    assert len(nodes)==69 and len({n['node_id'] for n in nodes})==69
    assert len(uav)==116 and len(ground)==5 and len(legacy)==19
    assert all(r['line_mode']=='UAV_GEOMETRY_SEARCH' for r in uav)
    assert all(r['line_mode']=='GROUND_HANDOFF_STRAIGHT_REFERENCE' for r in ground)
    ids={n['node_id']:n for n in nodes}
    degree=collections.Counter()
    for e in uav:
        assert e['from_id'] in ids and e['to_id'] in ids
        degree[e['from_id']]+=1;degree[e['to_id']]+=1
    roles=[]
    for n in nodes:
        typ=n['node_type'];name=n['name'];nid=n['node_id']
        # These are descriptive RESEARCH FUNCTION HYPOTHESES, not permission to operate.
        if typ in {'GROUND_GATEWAY_ONLY','PORT_STRUCTURE_GROUND_TERMINAL','GROUND_TRANSFER_REFERENCE','CONTROLLED_SEAPORT_GROUND_ONLY'}:
            role='GROUND_GATEWAY_OR_TRANSFER_REFERENCE'
        elif typ in {'LOGISTICS_FACILITY_SEARCH','INDUSTRIAL_PARCEL_SEARCH','UAV_PARCEL_SEARCH_ONLY','SMALL_GROUND_FEEDER_SEARCH'} or (nid in {'B01','B02'} and 'Truck transfer' in name):
            role='HUB_OR_TRANSFER_SITE_SEARCH_ONLY'
        elif 'COURIER' in typ or typ=='RETAIL_AND_GROUND_HUB' or 'GROUND_EXCHANGE' in typ:
            role='MIXED_COURIER_RETAIL_OR_TRANSFER_REFERENCE'
        elif any(s in typ for s in ('RESIDENTIAL','RETAIL','DEMAND','COMMERCIAL','NEIGHBOURHOOD','TOWNSHIP')):
            role='DEMAND_ZONE_REFERENCE_ONLY'
        else:role='UNCLASSIFIED_REFERENCE_ONLY'
        roles.append({'node_id':nid,'zone':n['zone'],'label':name,'longitude':n['longitude'],'latitude':n['latitude'],
        'original_node_type':typ,'provisional_function':role,'uav_candidate_degree':degree[nid],
        'has_uav_geometry_candidate':str(degree[nid]>0),'ground_road_access':'HOLD_NOT_VERIFIED',
        'uav_pad_status':'HOLD_NOT_APPROVED','operational_site_release':'NO','demand_count_observed':'NO',
        'evidence_semantics':'STATIC_REFERENCE_ONLY_FROM_V3'})
    savecsv(O/'S07_01_node_roles_69.csv',roles,roles[0].keys())
    # Historical ID collision and physical-location candidate reconciliation.
    cross=[]
    for l in legacy:
        lid=l['legacy_id'];lo=float(l['legacy_lon']);la=float(l['legacy_lat'])
        same=ids.get(lid)
        same_d=geod(lo,la,float(same['longitude']),float(same['latitude'])) if same else None
        ranked=sorted(((geod(lo,la,float(n['longitude']),float(n['latitude'])),n) for n in nodes),key=lambda v:v[0])
        nearest_d,nearest=ranked[0]
        similar=namesim(l['legacy_place_name'],nearest['name'])
        col_status=('SAME_ID_SAME_COORDINATE_REFERENCE_ONLY' if same_d is not None and same_d<10 else
                   'SAME_ID_DIFFERENT_PLACE_HARD_BLOCK' if same else 'OLD_ID_NOT_IN_NEW_NETWORK')
        id_status=('ID_COORDINATE_MATCH' if same_d is not None and same_d<10 else 'ID_COLLISION' if same else 'NOT_PRESENT')
        cross.append({'legacy_id':lid,'legacy_name':l['legacy_place_name'],'legacy_zone':l['legacy_zone'],
        'legacy_lon':lo,'legacy_lat':la,'new_same_id_name':same['name'] if same else '',
        'same_id_distance_m':round(same_d,2) if same_d is not None else '',
        'same_id_status':id_status,'nearest_new_id':nearest['node_id'],'nearest_name':nearest['name'],
        'nearest_distance_m':round(nearest_d,2),'nearest_name_token_similarity':round(similar,3),
        'coordinate_candidate_under_100m':'YES' if nearest_d<100 else 'NO',
        'crosswalk_status':col_status,'order_id_remapping_authorized':'NO',
        'review_reason':'Coordinates AND delivery semantics must be independently verified; no automatic order migration'})
    savecsv(O/'S07_02_legacy19_vs_new69_coordinate_crosswalk.csv',cross,cross[0].keys())
    # All 153 days, 3672 physical one-hour intervals. Preserve UTC and local with end-exclusive.
    now=dt.datetime(2026,5,1,tzinfo=MYT);end=dt.datetime(2026,10,1,tzinfo=MYT)
    time_rows=[]
    while now<end:
        stop=now+dt.timedelta(hours=1)
        time_rows.append({'interval_id':len(time_rows)+1,'date_local':now.date().isoformat(),
        'month_local':now.strftime('%Y-%m'),'hour_local':now.hour,
        'interval_start_local':now.isoformat(timespec='seconds'),
        'interval_end_exclusive_local':stop.isoformat(timespec='seconds'),
        'interval_start_utc':now.astimezone(UTC).isoformat(timespec='seconds'),
        'interval_end_exclusive_utc':stop.astimezone(UTC).isoformat(timespec='seconds'),
        'era5_precip_accumulation_valid_end_utc':stop.astimezone(UTC).isoformat(timespec='seconds'),
        'wind_time_semantics':'VALID_INSTANT_NEEDS_SOURCE_ALIGNMENT',
        'rain_time_semantics':'PRECEDING_ONE_HOUR_ACCUMULATION_NEEDS_SOURCE_VERIFICATION'})
        now=stop
    assert len(time_rows)==3672 and len({r['date_local'] for r in time_rows})==153
    savecsv(O/'S07_03_hourly_timeline_3672.csv',time_rows,time_rows[0].keys())
    # Monthly verification is factual metadata; never claim it contains hourly weather values.
    monthly=[]
    for m in weather['monthly']:
        month=m['month'];n=sum(t['month_local']==month for t in time_rows)
        assert m['hourly_four_ref_rows']==n*4
        monthly.append({**m,'expected_hour_intervals':n,'expected_four_reference_rows':n*4,
        'monthly_reference_count':4,'distinct_ERA5_returned_grid_cells':2,
        'hourly_value_rows_materialized_in_this_package':0,
        'precipitation_time_semantics':'HOLD_SOURCE_UNIT_AND_ACCUMULATION_AUDIT',
        'validation':'GITHUB_HISTORICAL_QC_SUMMARY_NOT_RECOMPUTED_FROM_RAW'})
    savecsv(O/'S07_04_historical_weather_monthly_qc.csv',monthly,monthly[0].keys())
    # Coordinates of returned ERA5 cells; nearest-cell candidate is spatial proxy, not a climate observation.
    cells=sorted({(r['lat'],r['lon']) for r in weather['return_grids']})
    refs=weather['return_grids']
    wg=[]
    for n in nodes:
        lon=float(n['longitude']);lat=float(n['latitude'])
        cell_dist=sorted(((geod(lon,lat,x[1],x[0]),x) for x in cells),key=lambda z:z[0])
        nasa_ref=sorted(((geod(lon,lat,x['nasa_lon'],x['nasa_lat']),x) for x in refs),key=lambda z:z[0])[0]
        dist,cell=cell_dist[0]
        wg.append({'node_id':n['node_id'],'zone':n['zone'],'lon':lon,'lat':lat,
        'era5_nearest_returned_cell_lat':cell[0],'era5_nearest_returned_cell_lon':cell[1],
        'era5_grid_candidate_distance_km':round(dist/1000,3),
        'era5_second_returned_grid_distance_km':round(cell_dist[1][0]/1000,3),
        'nasa_nearest_OLD_reference_id':nasa_ref[1]['point_id'],
        'nasa_ref_distance_km':round(nasa_ref[0]/1000,3),
        'assignment_method':'NEAREST_OF_TWO_HISTORICAL_RETURNED_ERA5_CELLS_NOT_RETRIEVED_GRID',
        'weather_numeric_record_present':'NO', 'node_weather_operational_release':'HOLD_NO_HOURLY_SOURCE',
        'weather_source_note':'No weather measured at any S06 node; nearest historic grid assignment is proxy-only',
        'spatial_proxy_qa':'HOLD_DIST_GT_10KM' if dist>10000 else 'DIST_LE_10KM_STILL_NOT_CALIBRATED'})
    savecsv(O/'S07_05_node_to_weather_grid_69_CANDIDATES_ONLY.csv',wg,wg[0].keys())
    # Historical verified workbook byte sizes differ from current GitHub files; do not mix these versions.
    vb=json.loads((I/'GITHUB_WEATHER_XLSX_VERSION_METADATA.json').read_text(encoding='utf-8'))
    version_rows=[]
    for v in vb['files']:
        version_rows.append({'month':v['month'],'github_file_bytes':v['github_size'],
        'historically_verified_file_bytes':v['historic_verified_size'],
        'byte_size_equal':v['github_size']==v['historic_verified_size'],
        'historic_verified_sha256':v['historic_sha256'],
        'github_blob_sha1_NOT_SHA256':v['github_git_blob_sha1'],
        'status':'HOLD_VERSION_MISMATCH_NEEDS_BYTE_REVIEW' if v['github_size']!=v['historic_verified_size'] else 'HOLD_NEEDS_FILE_SHA256'})
    assert len(version_rows)==5 and all(not v['byte_size_equal'] for v in version_rows)
    savecsv(O/'S07_05b_weather_XLSX_version_discrepancy.csv',version_rows,version_rows[0].keys())
    # Historic 37 route anomalies must NOT become new routed tasks merely because IDs exist.
    anomalies=readcsv(I/'S06_legacy37_road_OD_exceptions_NOT_REPAIRED.csv')
    assert len(anomalies)==37
    blocked=[]
    legacy_id={r['legacy_id']:r for r in cross}
    for item in anomalies:
        a=item['from_id'];b=item['to_id']
        a_ok=(a in legacy_id and legacy_id[a]['same_id_status']=='ID_COORDINATE_MATCH')
        b_ok=(b in legacy_id and legacy_id[b]['same_id_status']=='ID_COORDINATE_MATCH')
        blocked.append({'original_od_id':item['original_od_id'],'legacy_area':item['original_od_id'][:1],
        'old_origin_id':a,'old_dest_id':b,'old_origin_id_coordinate_match':str(a_ok),
        'old_dest_id_coordinate_match':str(b_ok),
        'old_route_diagnostic':item['old_diagnostic'],
        'new_ABC_route_exists':'UNKNOWN_NOT_COMPUTED',
        'route_frozen':'NO','legacy_repair_applied':'NO',
        'gate':'HOLD_ID_COORDINATE_COLLISION_AND_NEW_ROAD_GRAPH' if not(a_ok and b_ok) else 'HOLD_FRESH_DIRECTED_ROUTE_AND_SNAP_VALIDATION'})
    savecsv(O/'S07_07b_legacy37_routes_still_blocked.csv',blocked,blocked[0].keys())
    # Missing numeric weather explicitly null, independent of time validity.
    slots=[]
    for c in cells:
        for t in time_rows:
            slots.append({'weather_cell_id':f'ERA5_{c[0]:.2f}_{c[1]:.2f}',
            'grid_lat':c[0],'grid_lon':c[1],
            'interval_start_local':t['interval_start_local'],
            'interval_end_exclusive_local':t['interval_end_exclusive_local'],
            'wind_speed_m_s':'','wind_direction_from_deg':'','rain_mm_in_interval':'',
            'air_temperature_K':'','numeric_data_status':'MISSING_RAW_WEATHER_NO_IMPUTATION',
            'weather_simulation_release':'NO'})
    assert len(slots)==7344
    savecsv(O/'S07_06_ERA5_two_grid_hourly_EMPTY_SCHEMATIC_NOT_DATA.csv',slots,slots[0].keys())
    inventory=[
        {'dataset':'s06_69_nodes','path':'inputs/S06_69_node_master.csv','status':'PASS_REAL_SPATIAL_REFERENCE','readiness':'SPATIAL_ONLY'},
        {'dataset':'s06_uav_candidates','path':'inputs/S06_116_uav_geometry_candidates_ONLY.csv','status':'PASS_GEOMETRY_ONLY','readiness':'NOT_AIRSPACE_APPROVED'},
        {'dataset':'s06_ground_handoff','path':'inputs/S06_5_ground_handoff_straight_references_NOT_ROUTES.csv','status':'PASS_RELATIONS_ONLY','readiness':'NOT_DRIVABLE_ROUTE'},
        {'dataset':'historic_legacy_19_coordinate_extract','path':'inputs/legacy19_COORDINATE_EXTRACT_FROM_GITHUB.csv','status':'PASS_EXTRACT_FOR_COMPARISON','readiness':'FULL_SOURCE_HASH_NOT_REVERIFIED'},
        {'dataset':'monthly_weather_qc','path':'inputs/WEATHER_MONTHLY_GITHUB_QC_EXTRACT.json','status':'PASS_HISTORICAL_METADATA','readiness':'NOT_NUMERIC_WEATHER'},
        {'dataset':'weather_hourly_2026_05_to_09','path':'GITHUB data/weather_2026/processed/JB_SG_Weather_2026_*.xlsx','status':'HOLD_BINARY_NOT_RETRIEVED','readiness':'NOT_MATERIALIZED'},
        {'dataset':'historic_osm_directed_A','path':'GITHUB 03_gis_and_road_network/road_network_project/JB_CIQ_E02_roadnet_V4_6/outputs/E02_A_directed_edges_OSM.csv','status':'HOLD_NOT_LOCAL_OR_V3_ROUTED','readiness':'HISTORICAL_SCOPE_ONLY'},
        {'dataset':'historic_osm_directed_B','path':'GITHUB 03_gis_and_road_network/road_network_project/JB_CIQ_E02_roadnet_V4_6/outputs/E02_B_directed_edges_OSM.csv','status':'HOLD_NOT_LOCAL_OR_V3_ROUTED','readiness':'HISTORICAL_SCOPE_ONLY'},
        {'dataset':'new_osm_directed_ABC','path':'inputs/new_directed_OSM_ABC.gpkg OR .graphml','status':'HOLD_NOT_PROVIDED','readiness':'NO_NETWORK_COMPUTATION'},
        {'dataset':'old_37_routing_anomalies','path':'inputs/S06_legacy37_road_OD_exceptions_NOT_REPAIRED.csv','status':'HOLD_37_NOT_REPAIRED','readiness':'NO_LEGACY_ROUTE_RELEASE'},
        {'dataset':'historic_29842_orders','path':'GITHUB 10_experiment_results/stage6_dual_region_multilevel_feeder/stage6_order_level.csv.gz','status':'HOLD_BINARY_NOT_RETRIEVED','readiness':'OLD_AB_DIFFERENT_COORDINATE_CONTRACT'},
        {'dataset':'historic_918000_orders','path':'GITHUB old V5.6 30-seed orders','status':'HOLD_SOURCE_GENERATOR_INCOMPLETE','readiness':'SEPARATE_FIXTURE'},
        {'dataset':'new_ABC_orders','path':'inputs/NEW_ABC_frozen_tasks.csv','status':'HOLD_NOT_GENERATED','readiness':'NO_INVENTED_DEMAND'},
        {'dataset':'current_CAAM_CAAS_geo_constraints','path':'inputs/current_authoritative_airspace.*','status':'HOLD_NO_VALID_TIME_FILE','readiness':'SCENARIO_ONLY'}
    ]
    savecsv(O/'S07_07_source_readiness.csv',inventory,inventory[0].keys())
    order_summary={'status':'HOLD_NO_TASK_POPULATION','legacy_stage6':{'task_count':29842,'regions':'OLD_A_B_ONLY','source':'historic Stage 6 README and gz file in GitHub','not_independently_loaded':True,'can_migrate_by_same_id':False},'legacy_v56':{'rows':918000,'resampled_engineering_fixture':True,'generator_missing':True,'must_not_combine_with_stage6':True},'new_ABC':{'task_count':None,'generator_code':None,'frozen_manifest':None,'state':'NOT_STARTED'},'comparison_modes':['M0_PETROL','M1_DJI','M1_WING','M2_DJI','M2_WING'],'joint_order_count':None,'carbon_results_allowed':False}
    writejson(O/'S07_08_task_population_hold.json',order_summary)
    counts={z:sum(n['zone']==z for n in nodes) for z in ('A','B','C','PORT_A','GATEWAY')}
    gates={
      'source_commit':GIT,'stage':'V2-S07','status':'PARTIAL_EXECUTION_HOLD_MAIN_EXPERIMENT',
      'passed':{'S06_node_identity':True,'S06_edge_modes':True,'S07_roles_index':True,'S07_historical_ID_collision_screen':True,'S07_153day_hourly_axis':True,'S07_historic_weather_QC_metadata':True,'S07_grid_candidate_metadata':True},
      'blocked':{'WEATHER_HOURLY_REAL_VALUES':'HOLD_NO_ORIGINAL_XLSX_OR_CSV_BYTES_AND_5_VERSION_SIZE_DISCREPANCIES','DIRECTED_OSM_NEW_ABC':'HOLD_NO_ACCESSIBLE_NEW_GRAPH','OLD_TO_NEW_ORDER_MIGRATION':'HOLD_ID_COLLISION_A','FROZEN_TASK_POPULATION':'HOLD_OLD_ORDER_BINARY_AND_NEW_GENERATOR','ACTUAL_FLIGHT_TIME_WEATHER':'HOLD_DISPATCH_NOT_RUN','CURRENT_AIRSPACE_AND_LAND_ACCESS':'HOLD','M0_M1_M2_RESULTS':'NOT_STARTED'},
      'real_data_metrics':{'weather_nodes_gt_10km_from_nearest_historic_ERA5_cell':sum(float(x['era5_grid_candidate_distance_km'])>10 for x in wg),'weather_workbook_size_mismatch_months':len(version_rows),'nodes':len(nodes),'node_zone_counts':counts,'uav_reference_edges':len(uav),'ground_reference_edges':len(ground),'uav_zero_degree_nodes':sum(degree[n['node_id']]==0 for n in nodes),'historic_legacy_ids':len(legacy),'historic_road_OD_anomalies_preserved':len(anomalies),'legacy_same_id_collisions':sum(x['same_id_status']=='ID_COLLISION' for x in cross),'legacy_same_id_coordinate_matches':sum(x['same_id_status']=='ID_COORDINATE_MATCH' for x in cross),'hours':len(time_rows),'days':153,'ERA5_distinct_historic_returned_cells':2,'missing_hourly_values':len(slots)},
      'no_fake_data':True,'release_for':'METADATA_AND_TIME_AXES_ONLY',
      'operational_simulation_released':False,'carbon_savings_released':False}
    writejson(Q/'S07_partial_execution_audit.json',gates)
    manifest=[]
    for p in sorted([*I.rglob('*'),*O.rglob('*'),*(Q.glob('*.json'))]):
        if p.is_file():manifest.append({'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
    savecsv(Q/'S07_INPUT_OUTPUT_SHA256.csv',manifest,manifest[0].keys())
    print(json.dumps(gates['real_data_metrics'],ensure_ascii=False,indent=2))
    print('S07 STATUS:',gates['status'])
    return gates

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--root',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1]);args=a.parse_args()
    build(args.root)
