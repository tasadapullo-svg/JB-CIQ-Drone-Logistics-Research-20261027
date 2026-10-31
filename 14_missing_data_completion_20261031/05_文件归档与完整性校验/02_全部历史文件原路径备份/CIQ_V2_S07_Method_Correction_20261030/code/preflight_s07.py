#!/usr/bin/env python3
"""Read-only V2-S07 input preflight; no simulation and no approval inference.
Usage: python code/preflight_s07.py --s06 /path/to/S06 --s07-input /optional/dir --output /new/qa/dir
"""
import argparse,csv,hashlib,json,pathlib,collections,datetime

def read_csv(path):
    with path.open('r',encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while True:
            chunk=f.read(1<<20)
            if not chunk: break
            h.update(chunk)
    return h.hexdigest()

def gate(ok,reason):return {'status':'PASS' if ok else 'HOLD','reason':reason}

def audit(s06,s07_inputs):
    s06=pathlib.Path(s06); data=s06/'outputs'/'data'; s07_inputs=pathlib.Path(s07_inputs) if s07_inputs else None
    fn={'nodes':'S06_69_node_master.csv','uav':'S06_116_uav_geometry_candidates_ONLY.csv',
        'ground':'S06_5_ground_handoff_straight_references_NOT_ROUTES.csv',
        'road':'S06_69_road_access_evidence_HOLD.csv','airspace':'S06_69_airspace_and_site_evidence_HOLD.csv',
        'crosswalk':'S06_crosswalk_legacy19_vs_V3_69_NOT_VERIFIED.csv',
        'exceptions':'S06_legacy37_road_OD_exceptions_NOT_REPAIRED.csv'}
    report={'protocol':'V2-S07-CORRECTION-v1','audit_type':'ACTUAL_S06_PRECHECK_NO_NUMERIC_SIMULATION',
            'source_paths':{},'facts':{},'gates':{},'missing_inputs':[], 'warnings':[]}
    datasets={}
    for key,name in fn.items():
        path=data/name
        report['source_paths'][key]={'path':str(path),'exists':path.is_file()}
        if path.is_file():
            report['source_paths'][key]['sha256']=sha256(path)
            datasets[key]=read_csv(path)
        else:report['missing_inputs'].append(str(path))
    if len(datasets)!=len(fn):
        report['gates']['s06_files']=gate(False,'missing S06 source tables')
        report['overall']='HOLD'
        return report
    nodes=datasets['nodes'];uav=datasets['uav'];ground=datasets['ground'];road=datasets['road'];air=datasets['airspace'];xc=datasets['crosswalk'];exc=datasets['exceptions']
    ids=[r['node_id'] for r in nodes];idset=set(ids)
    d=collections.Counter()
    for e in uav:d[e['from_id']]+=1;d[e['to_id']]+=1
    isolated=[r['node_id'] for r in nodes if d[r['node_id']]==0]
    role=collections.Counter((r['zone'],r['node_type']) for r in nodes)
    report['facts']={'node_rows':len(nodes),'zone_counts':dict(collections.Counter(x['zone'] for x in nodes)),
        'uav_candidate_edges':len(uav),'ground_reference_edges':len(ground),
        'uav_zero_degree_node_count':len(isolated),'uav_zero_degree_node_ids':isolated,
        'legacy37_exception_rows':len(exc),
        'ground_route_distance_populated_count':sum(bool(e.get('road_distance_km','').strip()) for e in ground),
        'verified_road_access_node_count':sum(x.get('road_access_verified')=='YES' for x in road),
        'actual_takeoff_approval_node_count':sum(x.get('actual_takeoff_approval')=='YES' for x in air),
        'legacy_crosswalk_coordinate_verified_count':sum(x.get('crosswalk_status')=='VERIFIED_COORDINATES_MATCH' for x in xc),
        'node_roles_by_zone_type':{f'{k[0]}/{k[1]}':v for k,v in role.items()}}
    report['gates']['s06_integrity']=gate(len(nodes)==69 and len(idset)==69 and len(uav)==116 and len(ground)==5 and len(exc)==37 and all(x['from_id'] in idset and x['to_id'] in idset for x in uav+ground),'expected 69 unique nodes/116 UAV/5 ground/37 historical exceptions with valid endpoints')
    report['gates']['mode_isolation']=gate(all(x.get('line_mode')=='UAV_GEOMETRY_SEARCH' for x in uav) and all(x.get('line_mode')=='GROUND_HANDOFF_STRAIGHT_REFERENCE' for x in ground), 'UAV and ground geometry classified distinctly')
    report['gates']['verified_road_graph']=gate(False,'no independently validated directed OSM road graph, entrance snaps, turns, and directed OD routes supplied')
    report['gates']['old_to_new_task_coordinates']=gate(False,'legacy original 19-point source coordinates and order remapping not verified')
    report['gates']['uav_operational_geometry']=gate(False,'unapproved straight geometry; not flight routes; nodes with zero degree exist')
    report['gates']['legal_airspace_site']=gate(False,'no date-valid machine-readable CAAM/CAAS boundaries, pad permission/ground-risk evidence; scenario-only analysis possible')
    required={
        'weather_hourly_normalized.csv':'actual hourly meteorology with interval semantics, source, grid and QC',
        'weather_node_grid_join.csv':'69 nodes matched to actual weather grid cells with resolution/error',
        'directed_osm_road_network.gpkg':'routable OSM source geometry with one-way/restrictions and snapshot hash',
        'road_node_access.csv':'verified node-to-road vehicle entry, direction and component',
        'road_od_hourly.csv':'directed road routes + time-varying speeds + source/evidence; never straight lines',
        'frozen_tasks.csv':'one frozen and sourced task population with new-space assignment',
        'task_population_manifest.json':'generation/provenance/seed selection, dates and immutable cohort digest',
    }
    for name,meaning in required.items():
        present=bool(s07_inputs and (s07_inputs/name).is_file() and (s07_inputs/name).stat().st_size>0)
        report['gates']['source_'+name]=gate(present,("source present; schema, coverage and scientific provenance still require separate validation" if present else 'missing '+meaning))
        if not present:report['missing_inputs'].append(name)
        else:report['source_paths']['s07_'+name]={'path':str(s07_inputs/name),'sha256':sha256(s07_inputs/name)}
    # Preserve distinctions between verified physical operations, exploratory scenarios, and actual flight approval.
    report['gates']['real_numeric_modes']=gate(False,'S07 does not certify M0/M1/M2 routing, UAV energy, emissions or real flight permission')
    report['overall']='HOLD_NOT_RELEASED_TO_FORMAL_M0_M1_M2'
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--s06',required=True);p.add_argument('--s07-input');p.add_argument('--output',required=True)
    a=p.parse_args(); out=pathlib.Path(a.output);out.mkdir(parents=True,exist_ok=True)
    r=audit(a.s06,a.s07_input)
    (out/'actual_s07_preflight.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    with (out/'uav_zero_degree_nodes.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['node_id','status','interpretation'])
        for x in r.get('facts',{}).get('uav_zero_degree_node_ids',[]):w.writerow([x,'NO_UAV_CANDIDATE_EDGE','Not a verified ground-only node; role and accessibility review needed'])
    print(json.dumps({'overall':r['overall'],'facts':{k:v for k,v in r.get('facts',{}).items() if k!='node_roles_by_zone_type'},'gates_pass':sum(1 for x in r['gates'].values() if x['status']=='PASS'),'gates_total':len(r['gates'])},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
