#!/usr/bin/env python3
"""Explicit science release gate: does NOT certify C routing, orders, or UAV activity."""
import argparse,csv,json,pathlib

def audit(root):
    root=pathlib.Path(root)
    def read(rel):
        f=root/rel
        return json.loads(f.read_text('utf-8')) if f.exists() else None
    src=read('qa/actual_source_recovery_status.json') or {}
    files=src.get('files',[])
    weather=read('outputs/weather_workbook_extraction_audit.json') or []
    road=read('outputs/legacy_AB_graph_topology_audit.json') or []
    nodefile=root/'outputs/node_road_access_candidates_NOT_APPROVED.csv'
    nodes=list(csv.DictReader(nodefile.open(encoding='utf-8-sig'))) if nodefile.exists() else []
    checks={
        'pinned_source_bytes_all11':len(files)==11 and all(f.get('status')=='PASS_BYTES_HASH' for f in files),
        'actual_five_weather_workbooks_extracted':len(weather)==5 and all(w.get('status')=='EXTRACTED_RAW_NOT_OPERATIONALLY_RELEASED' for w in weather),
        'legacy_AB_graph_bytes_parsed':len(road)==2 and all(x.get('status')=='HISTORIC_GRAPH_TOPOLOGY_READ_NOT_OPERATIONAL_RELEASE' for x in road),
        'all_69_nodes_preserved':len(nodes)==69 and len(set(n['node_id'] for n in nodes))==69,
        'verified_new_C_graph':False,
        'verified_new_ABC_directed_routes':False,
        'new_ABC_synthetic_orders_frozen':False,
        'historical_37_OD_repair_approved':False,
        'uav_flight_operational_authorization':False,
    }
    x={'research_scope':'JB CIQ carbon-first study; reference-only dataset','stage':'V2-S07-R2',
        'status':'HOLD_NO_FULL_JOIN','technical_substeps_pass':[k for k,v in checks.items() if v],
        'blocked_substeps':[k for k,v in checks.items() if not v],
        'checks':checks,'release_M0_M1_M2':False,'weather_emissions_effect_computed':False,
        'note':'Existing spatial reference is retained. Static reference integrity is not operational route availability.'}
    (root/'qa/S07_R2_release_record.json').write_text(json.dumps(x,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({'status':x['status'],'passed':sum(checks.values()),'total':len(checks)}))
    return x
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args();audit(a.root)
