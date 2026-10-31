#!/usr/bin/env python3
"""V5-only spatial rebase + deterministic CONDITIONAL synthetic tasks.
No road route, weather value, pad approval, aircraft energy or emission output is inferred.
Use original, immutable uploaded V5 ZIP. Historical ID collisions are never migrated.
"""
import argparse, csv, hashlib, json, zipfile, math, datetime as dt, pathlib, random, collections, shutil
import fiona
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo

EXPECTED_V5_ZIP_SHA256='0d19633630b6f12525ad9bd776bbf966ec1e8a46520bd8bc3d904013b02dce74'
EXPECTED_ACTIVE_GPKG_SHA256='1edbeeba32257f35dfbb90bf36c0e86474a032038d1783fcfc85bb34ab94311b'
MAY_1=dt.date(2026,5,1); SEPT_30=dt.date(2026,9,30)
LOCAL=dt.timezone(dt.timedelta(hours=8))
ZONE_SEQUENCE=('A','B','C')
SCENARIO_SOURCES={
  'A':('A01','A02','A03','A08','A_N05','A_N07'),
  'B':('B06','B07'),
  'C':('A09','C02','C04','C06','C07','C21'),
}
# Ground-only or gate nodes are not synthetic customer destinations; remain in 68-node inventory.
EXCLUDE_DEST={'T_STULANG','G_CIQ','A_P01','A_P04','A_P06','B00','B01','B02','B08','C23'}
ERA5_RETURNED_GRID={'WX_EAST':(1.5,103.75),'WX_WEST':(1.5,103.5)}
MODEL_CHOICES=('M0_PETROL','M1_DJI_FC30','M1_WINGCOPTER198_CARGO','M2_DJI_FC30','M2_WINGCOPTER198_CARGO')

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for part in iter(lambda:f.read(1048576),b''):h.update(part)
    return h.hexdigest()

def outcsv(path,rows,fields=None):
    path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if fields is None:fields=list(rows[0]) if rows else []
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)

def readcsv(path):
    with open(path,newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def hav_m(lat1,lon1,lat2,lon2):
    r=6371008.8;p1,p2=math.radians(lat1),math.radians(lat2)
    d1=p2-p1;d2=math.radians(lon2-lon1)
    return r*2*math.asin(min(1,math.sqrt(math.sin(d1/2)**2+math.cos(p1)*math.cos(p2)*math.sin(d2/2)**2)))

def classify(node):
    i=node['node_id']; z=node['zone']; role=node['node_role_source']
    if i in ('G_CIQ','B00'): cat='GROUND_GATEWAY_REFERENCE'
    elif i in ('T_STULANG','B08','C23','A_P06'):cat='CONTROLLED_GROUND_ONLY_REFERENCE'
    elif i.startswith('A_P'):cat='PORT_AREA_CONTEXT_OR_DEMAND_PROXY'
    elif role in ('INDUSTRIAL_PARCEL_SEARCH','LOGISTICS_FACILITY_SEARCH','COURIER_COUNTER','RETAIL_AND_GROUND_HUB','SMALL_GROUND_FEEDER_SEARCH'):cat='CONDITIONAL_SOURCE_SEARCH'
    elif i in ('B01','B02'):cat='CONDITIONAL_TRUCK_TRANSFER_SEARCH'
    else:cat='CONDITIONAL_DEMAND_REFERENCE'
    return dict(node,analysis_role=cat,synthetic_origin_proxy='YES' if i in SCENARIO_SOURCES[z] else 'NO',
                synthetic_destination_proxy='YES' if i not in EXCLUDE_DEST else 'NO',
                country_context='MY_REFERENCE_ONLY',
                launch_pad_operationally_approved='NO',ground_gate_approved='NO',
                scenario_use_notice='DESIGN_ONLY_NOT_OBSERVED_DEMAND_OR_APPROVED_SITE')

def original_v5_zip_extract(zip_path,work):
    if sha256(zip_path)!=EXPECTED_V5_ZIP_SHA256:raise AssertionError('V5_SOURCE_ZIP_SHA256_MISMATCH_REFUSE_REBASE')
    extract=work/'source_extracted'
    if extract.exists():shutil.rmtree(extract)
    extract.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as z:
        assert z.testzip() is None,'ZIP_CRC_FAIL'
        for m in z.infolist():
            target=(extract/m.filename).resolve()
            assert target.is_relative_to(extract.resolve()),'UNSAFE_ZIP_PATH'
        z.extractall(extract)
    gp=list(extract.rglob('CIQ_ABC_V5_ACTIVE.gpkg'))
    if len(gp)!=1:raise AssertionError(f'EXPECTED_ONE_ACTIVE_V5_GPKG_GOT_{len(gp)}')
    if sha256(gp[0])!=EXPECTED_ACTIVE_GPKG_SHA256:raise AssertionError('ACTIVE_GPKG_SHA256_MISMATCH')
    return gp[0]

def extract_nodes(gp):
    records=[]
    for layer in ('A_NODES','B_NODES','C_NODES','A_PORT_6_NODES','A_GROUND_GATEWAY'):
        with fiona.open(gp,layer=layer) as f:
            for feature in f:
                a=dict(feature['properties']); geometry=feature['geometry'];lon,lat=map(float,geometry['coordinates'])
                nid=a.get('node_id') or a.get('id'); z=a.get('zone') or 'A'
                assert nid and z in ZONE_SEQUENCE
                field_lon=a.get('lon');field_lat=a.get('lat')
                assert field_lon is not None and field_lat is not None
                dist=hav_m(lat,lon,float(field_lat),float(field_lon))
                assert dist<0.05,(nid,'GEOMETRY_ATTRIBUTE_MISMATCH',dist)
                records.append(dict(node_id=nid,zone=z,name=a['name'],longitude_E=round(lon,9),latitude_N=round(lat,9),
                     node_role_source=a.get('node_type') or a.get('node_role') or a.get('status') or 'GROUND_REFERENCE',
                     original_layer=layer,geo_coordinates_match_m=round(dist,8),
                     original_operational_status=str(a.get('uav_operational_admission') or a.get('operational_uav_site') or 'NO'),
                     original_road_entry_verified=str(a.get('road_entry_verified') or a.get('ground_entry_verified') or 'False')))
    assert len(records)==68 and len(set(n['node_id'] for n in records))==68
    assert collections.Counter(x['zone'] for x in records)=={'A':29,'B':10,'C':29}
    assert {x['node_id'] for x in records}.isdisjoint({'A_N10'}) and 'G_CIQ' in {x['node_id'] for x in records}
    return sorted([classify(n) for n in records],key=lambda x:(x['zone'],x['node_id']))

def extract_edges(gp,ids):
    out=[]
    for layer in ('A_GEOMETRY_LINKS','B_GEOMETRY_LINKS','C_GEOMETRY_LINKS','A_PORT_LINKS','INTER_AREA_LINKS','A_GROUND_ONLY_HOLD'):
        with fiona.open(gp,layer=layer) as f:
            for feature in f:
                a=dict(feature['properties']);u=a['from_id'];v=a['to_id'];eid=a['edge_id']
                assert u in ids and v in ids and u!=v,(eid,u,v)
                if layer=='A_GROUND_ONLY_HOLD':typ='GROUND_ONLY_HOLD_EXTRA'
                elif layer=='A_PORT_LINKS' and a.get('mode')=='GROUND_HANDOFF_STRAIGHT_REFERENCE':typ='GROUND_HANDOFF_STRAIGHT_REFERENCE'
                else:typ='UAV_GEOMETRY_CANDIDATE_ONLY'
                assert feature['geometry']['type']=='LineString';points=feature['geometry']['coordinates']
                assert len(points)>=2
                start=ids[u];end=ids[v]
                assert hav_m(start['latitude_N'],start['longitude_E'],points[0][1],points[0][0])<1
                assert hav_m(end['latitude_N'],end['longitude_E'],points[-1][1],points[-1][0])<1
                out.append(dict(edge_id=eid,from_id=u,to_id=v,from_zone=start['zone'],to_zone=end['zone'],source_layer=layer,edge_type=typ,
                  one_way_geodesic_km=round(hav_m(start['latitude_N'],start['longitude_E'],end['latitude_N'],end['longitude_E'])/1000,7),
                  road_distance_km='',airspace_authorized='NO',feasible_flight='UNVERIFIED',
                  input_mode='UAV_GEOMETRY_ONLY' if typ=='UAV_GEOMETRY_CANDIDATE_ONLY' else 'GROUND_REFERENCE_NOT_ROUTE',
                  ground_route_approved='NO',counted_as_operational_edge='NO',
                  wmp228_geo_intersects_source=str(a.get('wmp_union_full_circle_intersects') or a.get('historical_circle_crossing') or 'UNKNOWN_REFERENCE_ONLY')))
    assert len(out)==125 and len(set((x['edge_id'],x['source_layer']) for x in out))==125
    ct=collections.Counter(x['edge_type'] for x in out)
    assert ct=={'UAV_GEOMETRY_CANDIDATE_ONLY':116,'GROUND_HANDOFF_STRAIGHT_REFERENCE':5,'GROUND_ONLY_HOLD_EXTRA':4},ct
    return sorted(out,key=lambda x:(x['edge_type'],x['edge_id']))

def legacy_map(old_file,nodes):
    old=readcsv(old_file);index={x['node_id']:x for x in nodes};out=[]
    assert len(old)==19
    for r in old:
        lo,la=float(r['legacy_lon']),float(r['legacy_lat']);oldid=r['legacy_id']
        found=index.get(oldid);same=hav_m(la,lo,found['latitude_N'],found['longitude_E']) if found else None
        nearest=min(nodes,key=lambda n:hav_m(la,lo,n['latitude_N'],n['longitude_E']))
        nd=hav_m(la,lo,nearest['latitude_N'],nearest['longitude_E'])
        if found and same<1:status='SAME_COORDINATES_ID_NOT_AUTO_APPROVED'
        elif found:status='ID_COLLISION_DIFFERENT_GEO_HARD_BLOCK'
        elif nd<100:status='OLD_ID_ABSENT_NEAREST_COORDINATE_CANDIDATE'
        else:status='NO_SAME_ID_NO_100M_MATCH_HARD_BLOCK'
        out.append(dict(legacy_id=oldid,legacy_name=r['legacy_name'],legacy_zone=r['legacy_zone'],legacy_lon=lo,legacy_lat=la,
                        v5_same_id_name=found['name'] if found else '',v5_same_id_zone=found['zone'] if found else '',
                        same_id_distance_m=round(same,2) if same is not None else '',
                        nearest_v5_id=nearest['node_id'],nearest_v5_name=nearest['name'],nearest_v5_distance_m=round(nd,2),
                        nearest_name_similarity=round(SequenceMatcher(None,r['legacy_name'].lower(),nearest['name'].lower()).ratio(),3),
                        mapping_gate=status,orders_migration_authorized='NO',geographic_semantics_review_required='YES'))
    return out

def timeline_rows():
    rows=[];n=(SEPT_30-MAY_1).days+1;assert n==153
    for day in range(n):
        date=MAY_1+dt.timedelta(days=day)
        for hour in range(24):
            a=dt.datetime.combine(date,dt.time(hour),tzinfo=LOCAL);b=a+dt.timedelta(hours=1)
            rows.append(dict(interval_id=day*24+hour+1,local_date=date.isoformat(),local_hour=hour,
              interval_start_local=a.isoformat(),interval_end_local_exclusive=b.isoformat(),
              interval_start_utc=a.astimezone(dt.timezone.utc).isoformat(),interval_end_utc_exclusive=b.astimezone(dt.timezone.utc).isoformat(),
              rainfall_valid_end_utc=b.astimezone(dt.timezone.utc).isoformat(),
              weather_numeric_record_status='HOLD_RAW_FILE_NOT_VERIFIED',traffic_numeric_record_status='HOLD_FCD_ROAD_JOIN_NOT_VERIFIED'))
    assert len(rows)==3672
    return rows

def weather_grids(nodes):
    results=[]
    for n in nodes:
        best=min(ERA5_RETURNED_GRID.items(),key=lambda x:hav_m(n['latitude_N'],n['longitude_E'],x[1][0],x[1][1]))
        d=hav_m(n['latitude_N'],n['longitude_E'],best[1][0],best[1][1])
        results.append(dict(node_id=n['node_id'],zone=n['zone'],name=n['name'],returned_era5_grid_id=best[0],
                weather_grid_lat=best[1][0],weather_grid_lon=best[1][1],grid_distance_m=round(d,1),
                weather_quality='SPATIAL_REPRESENTATIVENESS_REVIEW' if d>10000 else 'COARSE_GRID_PROXY_ONLY',
                weather_hourly_values_recovered='NO',not_independent_weather_station='YES'))
    return results

def task_generator(nodes,seeds=30,tasks_per_day_zone=6):
    assert tasks_per_day_zone==6,'TASK_DESIGN_VERSION_IS_6_PER_DAY_ZONE'
    byzone={z:[x for x in nodes if x['zone']==z and x['synthetic_destination_proxy']=='YES'] for z in ZONE_SEQUENCE}
    ix={n['node_id']:n for n in nodes}
    for z in ZONE_SEQUENCE:
        assert len(byzone[z])>=4
        assert len(SCENARIO_SOURCES[z])>=1 and all(ix[i]['zone']==z for i in SCENARIO_SOURCES[z])
    orders=[];payload_categories=(0.5,1.0,2.5,4.5,5.0,8.0)
    deadline_categories=(45,90,150)
    day_count=(SEPT_30-MAY_1).days+1
    # fixed 30 seeds preserved; cross-zone task in slot 5 is explicit designed stress stratum (1/6).
    for sidx in range(seeds):
        seed=20261027+sidx; rng=random.Random(seed)
        for day in range(day_count):
            d=MAY_1+dt.timedelta(days=day)
            for zone in ZONE_SEQUENCE:
                for slot in range(tasks_per_day_zone):
                    cross=slot==tasks_per_day_zone-1
                    dz=ZONE_SEQUENCE[(ZONE_SEQUENCE.index(zone)+(1 if (day+sidx)%2==0 else -1))%3] if cross else zone
                    dest=rng.choice(byzone[dz]); origins=tuple(i for i in SCENARIO_SOURCES[zone] if i!=dest['node_id']); assert origins
                    src=ix[rng.choice(origins)]
                    h=(slot*4+(day+sidx)%4)%24; minute=rng.choice((0,15,30,45))
                    release=dt.datetime.combine(d,dt.time(h,minute),tzinfo=LOCAL)
                    payload=payload_categories[(slot+day+sidx)%len(payload_categories)]
                    deadline=deadline_categories[(slot+sidx)%len(deadline_categories)]
                    orders.append(dict(task_id=f'V5S07-{seed}-{day:03d}-{zone}-{slot:02d}',scenario_seed=seed,date_local=d.isoformat(),
                       release_local=release.isoformat(),release_utc=release.astimezone(dt.timezone.utc).isoformat(),
                       origin_node_id=src['node_id'],origin_zone=src['zone'],origin_name=src['name'],
                       origin_lon=src['longitude_E'],origin_lat=src['latitude_N'],
                       destination_node_id=dest['node_id'],destination_zone=dest['zone'],destination_name=dest['name'],
                       destination_lon=dest['longitude_E'],destination_lat=dest['latitude_N'],
                       parcel_kg=payload,deadline_minutes=deadline,
                       demand_stratum='DESIGNED_CROSS_ZONE_STRESS' if cross else 'DESIGNED_WITHIN_ZONE',
                       empirical_demand_evidence='NONE_CONDITIONAL_SCENARIO',road_route_status='NOT_ROUTED_HOLD',
                       airspace_status='NOT_APPROVED',weather_event_status='NOT_EVALUATED',
                       ciq_crossborder_status='MY_INLAND_SCENARIO_CIQ_WAIT_NOT_APPLICABLE',
                       service_and_carbon_result_status='NOT_COMPUTED',population_release='CONDITIONAL_SYNTHETIC_NOT_EMPIRICAL'))
    assert len(orders)==seeds*day_count*3*tasks_per_day_zone
    return orders

def main(args):
    root=pathlib.Path(args.root).resolve();out=root/'outputs';out.mkdir(exist_ok=True,parents=True)
    source=root/'inputs'/args.v5zip
    gp=original_v5_zip_extract(source,root/'qa')
    nodes=extract_nodes(gp);idx={x['node_id']:x for x in nodes};edges=extract_edges(gp,idx)
    old=legacy_map(root/'inputs'/'legacy19_coordinates_extracted_from_previously_audited_GitHub.csv',nodes)
    timeline=timeline_rows();wg=weather_grids(nodes)
    outcsv(out/'S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv',nodes)
    outcsv(out/'S06_V5_ALL_125_LINKS_BY_FUNCTION.csv',edges)
    outcsv(out/'S06_V5_116_UAV_GEOMETRY_ONLY.csv',[e for e in edges if e['edge_type']=='UAV_GEOMETRY_CANDIDATE_ONLY'])
    outcsv(out/'S06_V5_5_GROUND_STRAIGHT_HANDOFF_NOT_ROADS.csv',[e for e in edges if e['edge_type']=='GROUND_HANDOFF_STRAIGHT_REFERENCE'])
    outcsv(out/'S06_V5_4_EXTRA_GROUND_HOLD.csv',[e for e in edges if e['edge_type']=='GROUND_ONLY_HOLD_EXTRA'])
    outcsv(out/'S07_V5_19_LEGACY_COORDINATE_CROSSWALK_NOT_AUTO_MIGRATED.csv',old)
    outcsv(out/'S07_V5_3672_HOURLY_TIMELINE.csv',timeline)
    outcsv(out/'S07_V5_68_NODE_ERA5_COARSE_GRID_CANDIDATES.csv',wg)
    old_exceptions=readcsv(root/'inputs'/'legacy37_route_exceptions.csv')
    for e in old_exceptions:
        e['v5_origin_same_id_present']='YES' if e['old_origin_id'] in idx else 'NO'
        e['v5_dest_same_id_present']='YES' if e['old_dest_id'] in idx else 'NO'
        e['v5_route_status']='HOLD_NO_RECOMPUTED_DIRECTED_ROUTE'
        e['candidate_repair_applied']='NO'
    assert len(old_exceptions)==37
    outcsv(out/'S07_V5_37_LEGACY_OD_EXCEPTION_NO_AUTO_REPAIR.csv',old_exceptions)
    outcsv(out/'S07_V5_68_ROAD_ACCESS_PENDING.csv',[dict(node_id=n['node_id'],zone=n['zone'],
      graph_source_state='HOLD_FULL_ABC_DIRECTED_OSM_BYTES_NOT_PRESENT',
      road_access_verified='NO',car_route_km='',snap_candidate_id='',
      acceptance='NO_ROUTES_COMPUTED_GROUND_STRAIGHT_REFERENCE_IS_NOT_ROAD') for n in nodes])
    # This is a reproducible, transparent designed population; NOT recovered historic orders.
    orders=task_generator(nodes,args.seeds,args.orders_per_zone_day)
    outcsv(out/'S07_V5_SYNTHETIC_TASKS_CONDITIONAL_DESIGN.csv',orders)
    cnt=collections.Counter(x['origin_zone'] for x in orders)
    monthly=collections.Counter(x['date_local'][:7] for x in orders)
    hours=collections.Counter(int(x['release_local'][11:13]) for x in orders)
    dest=collections.Counter(x['destination_node_id'] for x in orders)
    cross=sum(x['demand_stratum']=='DESIGNED_CROSS_ZONE_STRESS' for x in orders)
    report={
      'status':'S06_V5_SPATIAL_PASS__S07_SYNTHETIC_CONDITIONAL__ROAD_WEATHER_HOLD',
      'v5_zip_sha256':sha256(source),'v5_active_gpkg_sha256':sha256(gp),
      'nodes':len(nodes),'zones':dict(collections.Counter(x['zone'] for x in nodes)),
      'lines_by_type':dict(collections.Counter(x['edge_type'] for x in edges)),
      'legacy19_crosswalk_categories':dict(collections.Counter(x['mapping_gate'] for x in old)),
      'old_order_migrations_approved':0,'old37_od_repair_applied':0,
      'weather_hourly_index':len(timeline),'historical_era5_grid_unique':len(ERA5_RETURNED_GRID),
      'grids_over_10km':sum(x['weather_quality']=='SPATIAL_REPRESENTATIVENESS_REVIEW' for x in wg),
      'synthetic_tasks_total':len(orders),'synthetic_seed_count':args.seeds,
      'synthetic_orders_per_day_per_zone':args.orders_per_zone_day,
      'tasks_by_origin_zone':dict(cnt),'tasks_per_month':dict(monthly),
      'cross_zone_stress_count':cross,'release_hour_coverage':len(hours),'destinations_with_orders':len(dest),
      'same_task_id_for_five_modes':'TO_BE_USED_BY_S10_SHARED_LEDGER_NOT_YET_SIMULATED',
      'actual_fuel_CO2_calculated':False,'actual_weather_values_read':False,
      'directed_road_routes_computed':False,
      'simulation_status':'HOLD_MISSING_REAL_WEATHER_NUMERICS_ABC_DIRECTIONAL_ROAD_GRAPH_AND_ENERGY_EVIDENCE',
      'interpretation':'Synthetic tasks are an explicit scenario design, NOT observed orders nor empirically calibrated market demand.'}
    (root/'qa'/'V5_REBASE_EXECUTION_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    protocol={'protocol':'V5S07_SYNTHETIC_SCENARIO_v1', 'source_v5_hash':report['v5_zip_sha256'],
      'dates_local':'2026-05-01..2026-09-30','timezone':'Asia/Kuala_Lumpur',
      'number_seeds':args.seeds,'seed_values':'20261027..20261056' if args.seeds==30 else f'20261027..{20261026+args.seeds}',
      'tasks_per_origin_zone_per_day':args.orders_per_zone_day,
      'hour_rule':'6 slots/day, h=(slot*4+(day_index+seed_index)%4)%24',
      'minute_rule':'PRNG choice {0,15,30,45}',
      'dest_rule':'slots 0..4 intra origin zone; slot 5 cross zone with direction alternating by (day_index+seed_index)%2',
      'cross_zone_map_even_day_seed':{'A':'B','B':'C','C':'A'},
      'cross_zone_map_odd_day_seed':{'A':'C','B':'A','C':'B'},
      'origin_nodes_by_zone':{k:list(v) for k,v in SCENARIO_SOURCES.items()},
      'excluded_destination_node_ids':sorted(EXCLUDE_DEST),
      'destination_selection':'uniform across non-excluded V5 nodes in selected zone, conditional scenario, not empirical density',
      'weight_set_kg':[0.5,1,2.5,4.5,5,8], 'deadline_set_minutes':[45,90,150],
      'weight_rule':'category index=(slot+day_index+seed_index)%6',
      'deadline_rule':'category index=(slot+seed_index)%3',
      'mode_comparison_set':list(MODEL_CHOICES),'every_mode_uses_same_task_id':True,
      'CIQ_real_cross_border_OD':'NOT_IN_THIS_TASK_POPULATION',
      'historical_stage6_orders':'UNCHANGED_ARCHIVE_NOT_COMBINED',
      'warning':'This is a transparent engineering scenario. Use statistical inference across seeds as simulation sensitivity only, not population demand.'}
    (root/'qa'/'V5_SYNTHETIC_TASK_DESIGN_PROTOCOL.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2),'utf-8')
    release={'S06_V5_REFERENCE_INPUT':'PASS','S07_SYNTHETIC_TASK_DESIGN':'CONDITIONAL_SCENARIO_FREEZE',
      'S07_WEATHER_HOURLY_NUMERIC':'HOLD','S07_ABC_ROAD_NETWORK_ROUTING':'HOLD','S07_FCD_ABC_SPEED_COUPLING':'HOLD',
      'S07_LEGACY_ORDER_MIGRATION':'HOLD_NO_AUTO_MIGRATION','S08_PETROL_BASELINE':'NOT_RUN',
      'S09_TWO_AIRCRAFT_MISSION_ENERGY':'NOT_RUN','S10_FIVE_MODE_DISPATCH':'NOT_RUN',
      'S11_OPERATIONAL_CARBON':'NOT_RUN','S12_SCI_STATISTICS':'NOT_RUN'}
    (root/'qa'/'V5_S07_RELEASE_GATE.json').write_text(json.dumps(release,ensure_ascii=False,indent=2),'utf-8')
    (root/'qa'/'V5_S07_OUTPUT_CHECKSUMS.csv').unlink(missing_ok=True)
    outcsv(root/'qa'/'V5_S07_OUTPUT_CHECKSUMS.csv',[
      dict(file=str(p.relative_to(root)),bytes=p.stat().st_size,sha256=sha256(p)) for p in sorted(out.glob('*.csv'))])
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True)
    parser.add_argument('--v5zip',default='CIQ_ABC_QGIS322_V5_ONE_WMP228_68_NODES_FULL_PROJECT(1).zip')
    parser.add_argument('--seeds',type=int,default=30);parser.add_argument('--orders-per-zone-day',type=int,default=6)
    main(parser.parse_args())
