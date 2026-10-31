#!/usr/bin/env python3
"""Only stage 05 evidence readiness audit. NEVER executes a logistics or emissions simulation."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def hash_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def audit_evidence(gate, project_root):
    rows=[]
    for item in gate.get('hard_requirements', []):
        issue=[]
        status=item.get('status')
        if status != 'PASS': issue.append('GATE_NOT_PASS')
        path=item.get('evidence_path')
        expected=item.get('sha256')
        if not path: issue.append('EVIDENCE_NOT_IDENTIFIED')
        if not expected or len(str(expected)) != 64: issue.append('EVIDENCE_SHA256_NOT_FROZEN')
        p = (project_root/path).resolve() if path else None
        if p and not p.is_relative_to(project_root.resolve()): issue.append('EVIDENCE_OUTSIDE_PROJECT_ROOT')
        elif p and not p.is_file(): issue.append('EVIDENCE_FILE_MISSING')
        elif p and expected and len(str(expected))==64 and hash_file(p) != expected: issue.append('SHA256_MISMATCH')
        rows.append({'gate_id':item.get('id'), 'status':status, 'evidence_path':path, 'checks':issue, 'pass':not issue})
    return rows


def audit_parameter_table(path):
    with path.open('r',encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    issues=[]
    for row in rows:
        val=row.get('value','').strip()
        decision=row.get('freeze_decision','')
        name=row.get('parameter','')
        if decision=='BLOCKED' and val:
            issues.append({'parameter':name,'error':'BLOCKED_PARAMETER_HAS_VALUE'})
        if decision in ('REFERENCE_FROZEN','METHOD_FROZEN','SCREENING_FROZEN') and not val:
            issues.append({'parameter':name,'error':'FROZEN_REFERENCE_MISSING_VALUE'})
    required=['DJI_FC30_cruise_energy_model','Wingcopter_198_Cargo_mission_energy_model','diesel_van_fuel_consumption','petrol_car_fuel_consumption','Singapore_grid_GEF_2024']
    names={r.get('parameter') for r in rows}
    issues.extend({'parameter':n,'error':'REQUIRED_PARAMETER_NOT_REGISTERED'} for n in required if n not in names)
    return {'count':len(rows),'blocked_count':sum(x['freeze_decision']=='BLOCKED' for x in rows),'issues':issues}


def check(root=ROOT, result_path=None):
    gate=json.loads((root/'records/stage05_strict_run_gate_DENY_ALL.json').read_text(encoding='utf-8'))
    protocol=json.loads((root/'records/stage05_unified_task_protocol.json').read_text(encoding='utf-8'))
    evidence=audit_evidence(gate,root)
    parameters=audit_parameter_table(root/'records/stage05_parameter_registry.csv')
    issues=[]
    if gate.get('auto_run') is not False: issues.append('AUTO_RUN_MUST_BE_DISABLED')
    if protocol.get('run_policy',{}).get('allow_main_simulation') is not False: issues.append('PROTOCOL_WRONG_RUN_POLICY')
    if protocol.get('status')!='PROTOCOL_FROZEN_NO_NUMERICAL_RUN': issues.append('PROTOCOL_NOT_CURRENT')
    if len(evidence)!=10: issues.append('REQUIRED_GATE_COUNT_MISMATCH')
    if parameters['issues']: issues.append('PARAMETER_REGISTER_INVALID')
    all_proof=bool(evidence) and all(x['pass'] for x in evidence)
    # Explicit human sign-off required beyond having proof files.
    manual_approved=gate.get('approval')=='APPROVED_BY_RESEARCHER'
    ready=all_proof and manual_approved and not issues
    decision={
       'stage':'S05','release_status':'READY_FOR_SEPARATE_SMOKE_REVIEW' if ready else 'HOLD_NO_SIMULATION',
       'permission_to_run_main_experiment':False,
       'permission_to_run_unvalidated_comparative_emissions':False,
       'ready_for_independent_smoke_review':ready,
       'gate_status':evidence,'parameter_status':parameters,
       'policy_issues':issues,
       'source':'Offline metadata and hash evidence only; no flight approval, no weather/road/CO2 simulation.'
    }
    out=result_path or root/'results/stage05_release_result.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(decision,indent=2,ensure_ascii=False),encoding='utf-8')
    return decision

if __name__=='__main__':
    report=check()
    print(json.dumps({'stage':report['stage'],'status':report['release_status'],
                      'evidence_pass':sum(g['pass'] for g in report['gate_status']),
                      'evidence_total':len(report['gate_status']),
                      'blocked_parameters':report['parameter_status']['blocked_count'],
                      'permission_to_run_main_experiment':report['permission_to_run_main_experiment']},ensure_ascii=False))
    sys.exit(0 if report['release_status']=='READY_FOR_SEPARATE_SMOKE_REVIEW' else 2)
