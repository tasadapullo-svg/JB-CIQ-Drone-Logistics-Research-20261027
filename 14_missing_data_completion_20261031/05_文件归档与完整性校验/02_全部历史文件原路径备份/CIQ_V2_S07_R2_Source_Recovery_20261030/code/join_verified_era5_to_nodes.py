#!/usr/bin/env python3
"""Join real ERA5 hourly CSV to 69 GIS reference nodes using frozen *candidate* grid assignment.
This is a meteorological spatial proxy table, not four independent station observations,
not UAV operational eligibility, and not a genuine ERA5 interpolation over the new C zone.
"""
import argparse,csv,datetime,json,pathlib,collections

def rows(p):
    with pathlib.Path(p).open(encoding='utf-8-sig',newline='') as f:yield from csv.DictReader(f)

def pick(keys,aliases):
    norm={x.strip().lower():x for x in keys}
    for a in aliases:
        if a.lower() in norm:return norm[a.lower()]
    return None

def process(source,assignment,timeline,out):
    out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
    result={'status':'HOLD','input_era5':str(source),'input_assignment':str(assignment)}
    if not pathlib.Path(source).is_file():result['reason']='HOLD_ERA5_CSV_NOT_PRESENT';return save(out,result)
    ass=list(rows(assignment));times=list(rows(timeline))
    source_rows=list(rows(source))
    if not source_rows:result['reason']='HOLD_ERA5_EMPTY';return save(out,result)
    fields=source_rows[0].keys()
    mapping={
        'point_id':pick(fields,['point_id','station_id']),
        'hour':pick(fields,['timestamp_hour_start_sgt','timestamp_sgt','datetime_sgt','timestamp_local']),
        'wind_speed_ms':pick(fields,['ERA5_wind_10m_ms','wind_speed_10m_ms','wind_speed_ms']),
        'wind_direction_deg':pick(fields,['ERA5_wind_direction_10m_deg','wind_direction_10m_deg','wind_direction_deg']),
        'rainfall_mm_h':pick(fields,['ERA5_precipitation_mm_h','ERA5_precipitation_mm','ERA5_total_precipitation_mm_h','precipitation_mm_h','rainfall_mm_h']),
        'gust_ms':pick(fields,['ERA5_wind_gusts_10m_ms','ERA5_gust_10m_ms','wind_gusts_10m_ms'])}
    result['detected_columns']=mapping
    if not all(mapping[k] for k in ['point_id','hour','wind_speed_ms','wind_direction_deg']):
        result['reason']='HOLD_REQUIRED_WIND_COLUMNS_UNRESOLVED';result['source_columns']=list(fields);return save(out,result)
    by_point=collections.defaultdict(dict)
    def normtime(x):return x[:13].replace(' ','T')
    for r in source_rows:
        point=r[mapping['point_id']];h=normtime(r[mapping['hour']])
        if h in by_point[point]:result['reason']='HOLD_DUPLICATE_POINT_HOUR';result['dup']=[point,h];return save(out,result)
        by_point[point][h]=r
    reference_point={(1.5,103.75):'CW_MY',(1.5,103.5):'SL_MY'}
    wanted=set()
    for r in times:
        t=r.get('interval_start_local') or r.get('hour_start_local') or r.get('timestamp_hour_start_sgt') or r.get('hour_start_sgt')
        if t:wanted.add(normtime(t))
    if not wanted:result['reason']='HOLD_TIMELINE_SCHEMA';result['timeline_columns']=list(times[0]) if times else [];return save(out,result)
    for p in set(reference_point.values()):
        missing=wanted-set(by_point[p]);
        if missing:result['reason']='HOLD_MISSING_REAL_ERA5_HOURS';result['point']=p;result['missing_count']=len(missing);return save(out,result)
    dest=out/'S07_ERA5_69node_3672hour_spatial_proxy_NOT_OPERATIONAL_RELEASE.csv'
    header=['node_id','zone','timestamp_hour_start_sgt','reference_point_id','assigned_era5_cell_lat','assigned_era5_cell_lon',
            'wind_speed_10m_ms','wind_direction_10m_deg','precipitation_source_raw','gust_source_raw','spatial_proxy_distance_km','provenance_gate']
    count=0
    with dest.open('w',encoding='utf-8-sig',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=header);wr.writeheader()
        for a in ass:
            grid=(float(a['era5_nearest_returned_cell_lat']),float(a['era5_nearest_returned_cell_lon']))
            if grid not in reference_point:
                result['reason']='HOLD_UNRECOGNIZED_HISTORICAL_ERA5_GRID';result['grid']=grid;return save(out,result)
            p=reference_point[grid]
            for h in sorted(wanted):
                r=by_point[p][h]
                wr.writerow({'node_id':a['node_id'],'zone':a['zone'],'timestamp_hour_start_sgt':h,
                   'reference_point_id':p,'assigned_era5_cell_lat':grid[0],'assigned_era5_cell_lon':grid[1],
                   'wind_speed_10m_ms':r[mapping['wind_speed_ms']],
                   'wind_direction_10m_deg':r[mapping['wind_direction_deg']],
                   'precipitation_source_raw':r[mapping['rainfall_mm_h']] if mapping['rainfall_mm_h'] else '',
                   'gust_source_raw':r[mapping['gust_ms']] if mapping['gust_ms'] else '',
                   'spatial_proxy_distance_km':a.get('era5_grid_candidate_distance_km',''),
                   'provenance_gate':'PROXY_WEATHER_NOT_SITE_OBSERVATION_OR_FLIGHT_CLEARANCE'})
                count+=1
    result.update({'status':'GENERATED_SPATIAL_PROXY_ONLY','row_count':count,'source_reference_count':len(by_point),
          'used_cells':2,'rain_unit_release':'HOLD_CONFIRM_SOURCE_TIME_INTERVAL_AND_UNITS',
          'flight_weather_release':'HOLD_REAL_TAKEOFF_INTERVAL_NOT_EVALUATED','output':str(dest)})
    return save(out,result)

def save(out,r):
    (out/'S07_ERA5_node_join_audit.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(r,ensure_ascii=False)[:1400]);return r
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--assignment',required=True);p.add_argument('--timeline',required=True);p.add_argument('--out',required=True);a=p.parse_args();process(a.source,a.assignment,a.timeline,a.out)
