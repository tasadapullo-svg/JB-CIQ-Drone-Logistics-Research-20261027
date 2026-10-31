#!/usr/bin/env python3
"""S07 real byte and numerical QA. Never synthesizes missing historical observations.

Run from a checkout of the pinned historic GitHub commit, with frozen inputs ZIP
and SHA lock supplied by this package. Read-only with respect to all sources.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,gzip,hashlib,io,json,math,sys,zipfile
from collections import Counter,defaultdict
from pathlib import Path
from xlsx_extract import extract_one

HOURS={5:744,6:720,7:744,8:744,9:720}
REF_POINTS={'CW_MY','CW_SG','SL_MY','SL_SG'}
PIN='4569817b8145efe2ae06f4b21addc1986f971c12'


def digest(path, kind='sha256'):
    h=hashlib.new(kind)
    if kind=='sha1': h.update(f'blob {path.stat().st_size}\0'.encode('ascii'))
    with path.open('rb') as f:
        for piece in iter(lambda:f.read(1024*1024),b''): h.update(piece)
    return h.hexdigest()


def col(fields,names):
    norm={f.lower().strip():f for f in fields if f}
    for n in names:
        if n.lower() in norm:return norm[n.lower()]
    return None


def local_hour(value):
    """No rounding of non-hourly data; timestamps in UTC normalized to MYT."""
    if value is None:return None
    s=str(value).strip()
    if not s:return None
    try:
        serial=float(s)
    except ValueError:
        serial=None
    if serial is not None and math.isfinite(serial) and 30000 < serial < 60000:
        d=dt.datetime(1899,12,30)+dt.timedelta(days=serial)
    else:
        try:d=dt.datetime.fromisoformat(s.replace('Z','+00:00'))
        except ValueError:
            d=None
            for fmt in ('%Y-%m-%d %H:%M:%S','%Y/%m/%d %H:%M:%S','%Y-%m-%d %H:%M','%d/%m/%Y %H:%M:%S'):
                try:d=dt.datetime.strptime(s,fmt);break
                except ValueError:pass
    if d is None:return None
    if d.tzinfo is not None:d=d.astimezone(dt.timezone(dt.timedelta(hours=8))).replace(tzinfo=None)
    if d.minute!=0 or d.second!=0 or d.microsecond!=0:return None
    return d


def zip_frozen_check(zpath,lockpath):
    result={'status':'HOLD','members':{}}
    lock=json.loads(lockpath.read_text('utf-8'))
    with zipfile.ZipFile(zpath) as z:
        if z.testzip() is not None:return result
        for n,expected in lock['members_sha256'].items():
            try:
                actual=hashlib.sha256(z.read(n)).hexdigest()
                result['members'][n]={'match':actual==expected,'sha256':actual}
            except KeyError:result['members'][n]={'match':False}
        if not all(x['match'] for x in result['members'].values()):return result
        reader=lambda n:csv.DictReader(io.TextIOWrapper(z.open(n),encoding='utf-8-sig'))
        node=list(reader('S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv'))
        orders=list(reader('S07_V5_SYNTHETIC_TASKS_CONDITIONAL_DESIGN.csv'))
        runs=list(reader('S07_V5_4590_SEED_DAY_RUN_MANIFEST.csv'))
        modes=list(reader('S10_V5_22950_MODE_RUN_KEYS_NO_SIM_RESULTS.csv'))
        ids={r['node_id'] for r in node};order_ids=set()
        origin=col(orders[0].keys(),['origin_node_id','origin_id','from_id','origin_node'])
        dest=col(orders[0].keys(),['destination_node_id','destination_id','to_id','destination_node'])
        oid=col(orders[0].keys(),['order_id','task_id','synthetic_order_id'])
        bad=0
        for r in orders:
            if oid:
                if r[oid] in order_ids:bad+=1
                order_ids.add(r[oid])
            if origin and r[origin] not in ids:bad+=1
            if dest and r[dest] not in ids:bad+=1
        c=Counter(r['run_id'] for r in modes)
        good=(len(node)==68 and len(ids)==68 and len(orders)==82620 and len(runs)==4590 and len(modes)==22950
              and len(c)==4590 and all(k==5 for k in c.values()) and bad==0 and all(r.get('operation_emission_status')=='NOT_COMPUTED' for r in modes))
        result.update(status='PASS' if good else 'HOLD',nodes=len(node),tasks=len(orders),runs=len(runs),modes=len(modes),id_errors=bad,
          zone_counts=dict(Counter(r['zone'] for r in node)),model_result_count=0)
    return result


def source_status(meta,repo):
    p=repo/meta['path']
    if not p.is_file():return {'file':meta['name'],'role':meta['scope'],'status':'MISSING','path':meta['path']}
    b=dig= digest(p,'sha1'); s=digest(p)
    ok=(p.stat().st_size==meta['size'] and b==meta['git_blob'] and (not meta.get('sha256') or s==meta['sha256']))
    if ok and p.suffix in ('.xlsx','.zip'):
        try:
            with zipfile.ZipFile(p) as z:ok=z.testzip() is None
        except Exception:ok=False
    return {'file':meta['name'],'role':meta['scope'],'status':'PASS_BYTES' if ok else 'HOLD_VERSION_OR_INTEGRITY',
      'size':p.stat().st_size,'sha256':s,'git_blob':b,'path':meta['path']}


def weather_check(path,month,out):
    named=path.name
    meta={"month":month,"filename":named,"status":"HOLD"}
    products={}
    for sheet in ('Weather_Hourly','ERA5_Hourly'):
        extracted=extract_one(path,out/f'{month:02d}_{sheet}_RAW.csv',sheet,'')
        products[sheet]=extracted
        if extracted.get('status')!='EXTRACTED_RAW_NOT_OPERATIONALLY_RELEASED':
            meta.update(status='HOLD_SHEET_READ',error=extracted);return meta
    rows={s:products[s]['rows'] for s in products}
    meta['rows']=rows
    out_c=out/f'{month:02d}_Weather_Hourly_RAW.csv'
    with out_c.open('r',encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);fields=reader.fieldnames or []
        pc=col(fields,['point_id','reference_point_id','site_id','location_id'])
        tc=col(fields,['time_sgt','datetime_sgt','timestamp_sgt','time_local','datetime_local','timestamp_local','local_time','time','timestamp'])
        meta['fields']=fields;meta['point_field']=pc;meta['time_field']=tc
        if pc is None or tc is None:
            meta['status']='HOLD_MISSING_POINT_OR_TIME_SCHEMA';return meta
        seen=set();duplicates=0;bad=0;outside=0;counts=Counter()
        for r in reader:
            p=r.get(pc,'').strip();t=local_hour(r.get(tc))
            if p not in REF_POINTS or t is None:bad+=1;continue
            if not (t.year==2026 and t.month==month):outside+=1
            if (p,t) in seen:duplicates+=1
            seen.add((p,t));counts[p]+=1
        meta.update(points=dict(counts),duplicate_keys=duplicates,invalid_keys=bad,out_of_month=outside)
    valid=(rows['Weather_Hourly']==4*HOURS[month] and not (duplicates or bad or outside)
           and set(counts)==REF_POINTS and all(counts[p]==HOURS[month] for p in REF_POINTS))
    if not valid:meta['status']='HOLD_WEATHER_TIME_QA';return meta
    # ERA5 hourly may carry one boundary time per point. Check rather than dropping.
    era_path=out/f'{month:02d}_ERA5_Hourly_RAW.csv'
    with era_path.open('r',encoding='utf-8-sig',newline='') as f:
        rr=csv.DictReader(f);ff=rr.fieldnames or []
        p2=col(ff,['point_id','reference_point_id','site_id','location_id'])
        t2=col(ff,['time_sgt','datetime_sgt','timestamp_sgt','time_local','datetime_local','timestamp_local','local_time','time','timestamp'])
        extra=Counter();sample=[];nontime=0;badpoint=0
        if p2 and t2:
            for r in rr:
                t=local_hour(r.get(t2)); p=(r.get(p2) or '').strip()
                if t is None:nontime+=1;continue
                if p not in REF_POINTS:badpoint+=1
                if not (t.year==2026 and t.month==month):
                    extra[p]+=1
                    if len(sample)<8:sample.append({"point_id":p,"timestamp":t.isoformat()})
            meta['ERA5_out_of_month_per_point']=dict(extra);meta['ERA5_extra_samples']=sample
    meta.update(ERA5_valid_time_field=bool(p2 and t2),ERA5_time_unreadable=nontime,ERA5_bad_point=badpoint)
    meta['status']='PASS_TIME_POINTS_ONLY' if rows['ERA5_Hourly']==4*HOURS[month]+4 else 'HOLD_ERA5_ROW_COUNT'
    meta['weather_units_release']='HOLD_NEEDS_METADATA';meta['precipitation_temporal_semantics_release']='HOLD_NEEDS_BOUNDARY_CONFIRMATION'
    meta['point_specific_weather_release']='HOLD_COARSE_SPATIAL_GRID'
    return meta


def fcd_check(path):
    out={'status':'HOLD','row_count':0,'quality_by_month':{}}
    row_count=0;node_ids=set();hours=set();keys=set();dupes=0;bad_keys=0;speed_state=Counter();permonth=defaultdict(Counter)
    with gzip.open(path,'rt',encoding='utf-8-sig',newline='') as f:
        rr=csv.DictReader(f);fields=rr.fieldnames or []
        pc=col(fields,['node_id','fcd_node_id','station_id','monitoring_node_id'])
        tc=col(fields,['time_sgt','timestamp_sgt','datetime_sgt','hour_start_sgt','hour_sgt','time_local','timestamp','time'])
        sc=col(fields,['speed_kmh','avg_speed_kmh','speed_mean_kmh','speed_hour_kmh','fcd_speed_kmh','speed_value_kmh','travel_speed_kmh'])
        if sc is None:
            guesses=[x for x in fields if 'speed' in x.lower() and 'kmh' in x.lower()]
            if len(guesses)==1:sc=guesses[0]
        out['fields']=fields;out['node_col']=pc;out['time_col']=tc;out['speed_col']=sc
        for r in rr:
            row_count+=1
            node=(r.get(pc) or '').strip() if pc else None
            ts=local_hour(r.get(tc)) if tc else None
            if node and ts:
                if (node,ts) in keys:dupes+=1
                keys.add((node,ts));node_ids.add(node);hours.add(ts)
                mon=str(ts.month)
                if not(ts.year==2026 and 5<=ts.month<=9):permonth['outside']['bad_time']+=1
            else:
                bad_keys+=1;mon='unparsed'
            value=(r.get(sc) or '').strip() if sc else ''
            if not value: state='MISSING'
            else:
                try:
                    v=float(value)
                    state='POSITIVE' if math.isfinite(v) and v>0 else ('NONPOSITIVE' if math.isfinite(v) else 'MISSING')
                except ValueError:state='INVALID_STRING'
            speed_state[state]+=1;permonth[mon][state]+=1
    out.update(row_count=row_count,nodes=len(node_ids),hours=len(hours),duplicate_node_hour=dupes,
      bad_node_hour=bad_keys,speed_states=dict(speed_state),quality_by_month={k:dict(v) for k,v in permonth.items()},
      direction_field_present=any('direction' in x.lower() or 'bearing' in x.lower() for x in fields))
    valid=(row_count==345*3672 and len(node_ids)==345 and len(hours)==3672 and not dupes and not bad_keys and sc and tc and pc)
    out['status']='PASS_STRUCTURE_ONLY' if valid else 'HOLD_STRUCTURE';out['FCD_OBSERVATION_TO_DIRECTED_ROADS']='HOLD_NOT_CALIBRATED'
    return out


def roads_check(repo,metas):
    out={};graphnodes={}
    for area in 'AB':
        name=f'E02_{area}_road_graph_nodes.csv';meta=next(x for x in metas if x['name']==name)
        p=repo/meta['path'];ids=set();bad=0
        with p.open('r',encoding='utf-8-sig',newline='') as f:
            rr=csv.DictReader(f)
            for r in rr:
                ids.add(r['osm_node_id'])
                try:
                    lat=float(r['latitude']);lon=float(r['longitude'])
                    if not(-90<=lat<=90 and -180<=lon<=180):bad+=1
                except (TypeError,ValueError):bad+=1
        graphnodes[area]=ids
        out[area]={'graph_nodes':len(ids),'invalid_coord':bad}
    for area,expected in [('A',178098),('B',104317)]:
        name=f'E02_{area}_directed_edges_OSM.csv';meta=next(x for x in metas if x['name']==name)
        p=repo/meta['path'];badlength=0;missingnode=0;count=0
        with p.open('r',encoding='utf-8-sig',newline='') as f:
            rr=csv.DictReader(f)
            for r in rr:
                count+=1
                try:
                    length=float(r['length_m'])
                    if not math.isfinite(length) or length<=0:badlength+=1
                except (TypeError,ValueError):badlength+=1
                if r.get('source') not in graphnodes[area] or r.get('target') not in graphnodes[area]:missingnode+=1
        out[area].update(directed_edges=count,edge_bad_length=badlength,edge_missing_graph_node=missingnode,
          historic_expected_edges=expected,status='PASS_LEGACY_TOPOLOGY_STRUCTURE_ONLY' if count==expected and not(badlength or missingnode or out[area]['invalid_coord']) else 'HOLD_TOPOLOGY')
    return out


def main(repo:Path,tools_dir:Path,output:Path):
    output.mkdir(parents=True,exist_ok=True)
    index=json.loads((tools_dir/'source_index.json').read_text('utf-8'))
    assert index['git_commit']==PIN,'SOURCE_COMMIT_MISMATCH'
    freeze=zip_frozen_check(tools_dir/'frozen_v5_inputs.zip',tools_dir/'frozen_lock.json')
    sources={m['name']:source_status(m,repo) for m in index['files']}
    mandatory_weather=[f'JB_SG_Weather_2026_{m:02d}.xlsx' for m in HOURS]
    fcd='JB_CIQ_E01_corrected_five_month_traffic_data_345nodes_2026-05_09.csv.gz'
    legacy_roads=[f'E02_{a}_{kind}.csv' for a in 'AB' for kind in ('directed_edges_OSM','road_graph_nodes')]
    core=mandatory_weather+[fcd]
    optional=['stage6_order_level.csv.gz','E03_ERA5_JB_TWO_CIQ_WEATHER_HOURLY.csv','JB_FCD_345nodes_G1-G5_Grouped_2026-05_09.zip','JB_FCD_345nodes_G1-G5_grouped_statistics_and_node_master.xlsx']
    results={'fixed_commit':PIN,'frozen_V5':freeze,'sources':list(sources.values()),'classes':{
      'core_numeric_s07':core,'legacy_road_qa':legacy_roads,'reference_not_required_for_V5_orders':optional},
      'weather_monthly':[],'fcd':None,'roads_legacy_AB':None,'S07_release':'HOLD','M0_M1_M2_real_operation_result':'NOT_COMPUTED'}
    if all(sources[n]['status']=='PASS_BYTES' for n in mandatory_weather):
        for m in HOURS:
            p=repo/next(x['path'] for x in index['files'] if x['name']==f'JB_SG_Weather_2026_{m:02d}.xlsx')
            results['weather_monthly'].append(weather_check(p,m,output/'raw_extract'))
    if sources[fcd]['status']=='PASS_BYTES':
        p=repo/next(x['path'] for x in index['files'] if x['name']==fcd)
        results['fcd']=fcd_check(p)
    if all(sources[n]['status']=='PASS_BYTES' for n in legacy_roads):
        results['roads_legacy_AB']=roads_check(repo,index['files'])
    results['source_core_byte_pass']=sum(sources[n]['status']=='PASS_BYTES' for n in core)
    results['source_core_byte_expected']=len(core)
    results['source_legacy_AB_byte_pass']=sum(sources[n]['status']=='PASS_BYTES' for n in legacy_roads)
    results['source_legacy_AB_byte_expected']=len(legacy_roads)
    results['source_optional_byte_pass']=sum(sources[n]['status']=='PASS_BYTES' for n in optional)
    results['S07_core_structural_gate']='PASS_CORE_STRUCTURE_ONLY' if (
        results['source_core_byte_pass']==len(core) and all(x['status']=='PASS_TIME_POINTS_ONLY' for x in results['weather_monthly'])
        and results['fcd'] and results['fcd']['status']=='PASS_STRUCTURE_ONLY') else 'HOLD'
    results['S07_release']='HOLD_NEEDS_V5_ABC_APPROVED_ROAD_FCD_DIRECTION_WEATHER_UNITS_AND_SPATIAL_QA'
    # This is intentional even if raw bytes and structural checks pass: road access,
    # OSM turn constraints, weather semantics and 68-site coverage are not proved.
    (output/'S07_GITHUB_ACTUAL_NUMERIC_QA.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n','utf-8')
    with (output/'S07_SOURCE_CHECK.csv').open('w',newline='',encoding='utf-8-sig') as f:
        columns=['file','role','status','size','sha256','git_blob','path']
        w=csv.DictWriter(f,columns,extrasaction='ignore');w.writeheader();w.writerows(results['sources'])
    with (output/'S07_WEATHER_MONTHLY_CHECK.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['month','status','Weather_Hourly_rows','ERA5_rows','duplicate_keys','invalid_keys','out_of_month','ERA5_extra_samples'])
        for d in results['weather_monthly']:
            w.writerow([d['month'],d['status'],d.get('rows',{}).get('Weather_Hourly'),d.get('rows',{}).get('ERA5_Hourly'),d.get('duplicate_keys'),d.get('invalid_keys'),d.get('out_of_month'),json.dumps(d.get('ERA5_extra_samples',[]))])
    print(json.dumps({'frozen':freeze['status'],'core_byte_verified':f"{results['source_core_byte_pass']}/{len(core)}",'legacy_AB_byte_verified':f"{results['source_legacy_AB_byte_pass']}/{len(legacy_roads)}",'core_structure':results['S07_core_structural_gate'],'formal_S07':results['S07_release']}))
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo-root',required=True);p.add_argument('--tools-dir',default=str(Path(__file__).resolve().parent));p.add_argument('--output',default='qa/s07_actual_run')
    a=p.parse_args();main(Path(a.repo_root),Path(a.tools_dir),Path(a.output))
