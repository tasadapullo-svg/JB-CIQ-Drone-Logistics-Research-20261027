#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only Stage 00/01 file-level integrity and QGIS project preflight.

No simulation, weather recomputation, travel-time estimation, or CO2 calculation.
Python 3.10+ stdlib. Outputs are written ONLY to --out, outside input tree.

Example:
  python stage00_01_local_auditor.py \
    --repo D:/CIQ/JB-CIQ-Drone-Logistics-Research-20261027 \
    --qgis D:/CIQ/QGIS_latest/JB_CIQ_3zones.qgz \
    --out D:/CIQ/AUDIT_STAGE00_01

Audit scope: hash and inventory every regular file in the checkout; classify old
experiment outputs as excluded; inspect a selected QGS/QGZ project and local
GeoPackage attributes/feature counts. This is NOT an independent flight-permission,
GIS topological, scientific calibration, or numerical model reproduction audit.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict

EXPECTED_BASELINE_COMMIT = "4569817b8145efe2ae06f4b21addc1986f971c12"
STAGE_DIRS = [
    "Stage3_RQ1_M0", "stage4_area_b_m1_m2_scenarios",
    "stage5_operational_sensitivity_cost_carbon",
    "stage6_dual_region_multilevel_feeder",
    "stage7_1_audit_and_experiment_matrix",
    "stage7_2_main_experiments_and_statistics",
    "stage7_3_independent_audit_and_remaining_experiments",
    "stage7_g06_g08_fuel_economy_and_operational_emissions",
    "stage7_g09_g10_run_level_validation",
    "stage7_g11_g12_joint_uncertainty",
    "stage8_f0_f1_airspace_and_energy_evidence",
    "stage8_supplementary_experiment_preregistration_and_execution",
    "stage8_integrated_supplementary_experiments_and_conclusion_updates",
]
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "reassembled_large_files"}
REQ = [
    "README.md", "GITHUB_VALIDATION_REPORT.md", "github_upload_manifest.csv",
    "path_mapping.csv", "tools/reassemble_large_files.py",
    "outputs/next_stage/validation_report.json",
    "10_experiment_results/stage6_dual_region_multilevel_feeder/README_STAGE6_CN.md",
    "10_experiment_results/stage6_dual_region_multilevel_feeder/run_stage6.py",
    "10_experiment_results/stage6_dual_region_multilevel_feeder/RUN_INSTRUCTIONS.md",
    "10_experiment_results/stage8_f0_f1_airspace_and_energy_evidence/reports/CIQ_Stage8_F0_F1_formal_experiment_audit_report_20261028.md",
]
DOC_REFERENCES = [
    "10_experiment_results/stage6_dual_region_multilevel_feeder/run_stage4_dispatch.py",
    "10_experiment_results/stage6_dual_region_multilevel_feeder/run_stage6_sensitivity.py",
    "10_experiment_results/stage6_dual_region_multilevel_feeder/qa_and_report.py",
    "10_experiment_results/stage6_dual_region_multilevel_feeder/stage6_QA.json",
    "10_experiment_results/stage6_dual_region_multilevel_feeder/stage6_area_summary.csv",
    "10_experiment_results/stage7_2_main_experiments_and_statistics/Stage7_2_validation_report_20261027.md",
]

def write_csv(p: Path, rows, fields):
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def walk(root):
    if not root.is_dir(): return
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for fn in sorted(files):
            p = Path(base, fn)
            if p.is_file() and not p.is_symlink():
                yield p

def policy(rel):
    r = rel.replace("\\", "/")
    if r.startswith("10_experiment_results/"):
        s = r.split("/")[1]
        return "HISTORICAL_BASELINE_EXCLUDED" if s in STAGE_DIRS else "UNREGISTERED_EXCLUDED"
    if r.startswith(("03_gis_and_road_network/", "06_figures_and_visualizations/")):
        return "LEGACY_GIS_REFERENCE_EXCLUDED"
    if r.startswith(("data/weather_2026/", "02_base_and_traffic_data/", "04_weather_data/")):
        return "OLD_INPUT_REFERENCE_EXCLUDED"
    return "ARCHIVE_OR_DOCUMENTATION_EXCLUDED"

def get_git_head(repo):
    if not (repo / ".git").exists(): return "NOT_A_GIT_CHECKOUT"
    try:
        r = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True,
                           text=True, timeout=10, check=True)
        return r.stdout.strip()
    except Exception: return "GIT_HEAD_UNAVAILABLE"

def inventory(root, base_label):
    rows = []; problems = []
    for p in walk(root):
        rel = p.relative_to(root).as_posix()
        try:
            rows.append(dict(source=base_label, relative_path=rel, byte_size=p.stat().st_size,
                             sha256=sha256(p), inclusion_policy=policy(rel) if base_label == "GitHub_history" else "NEW_QGIS_CANDIDATE_NOT_APPROVED",
                             audit_status="HASHED_NOT_SEMANTICALLY_VERIFIED"))
        except Exception as e:
            problems.append(f"Read/hash failed: {base_label}/{rel}: {type(e).__name__}: {e}")
    return rows, problems

def project_content(path):
    if path.suffix.lower() == ".qgs": return path.read_bytes()
    if path.suffix.lower() == ".qgz":
        with zipfile.ZipFile(path) as z:
            files = [x for x in z.namelist() if x.lower().endswith(".qgs")]
            if len(files) != 1: raise ValueError(f"Expected one .qgs member, got {len(files)}")
            return z.read(files[0])
    raise ValueError("QGIS project must be .qgs or .qgz")

def interpret_source(raw, project_dir):
    """Only conservative local path resolution. Remote/service layers require QGIS inspection."""
    s = (raw or "").strip()
    if not s: return "EMPTY_DATASOURCE", ""
    if s.lower().startswith(("http:", "https:", "wms:", "wfs:", "xyz:", "postgres:", "memory:", "virtual:", "geopackage:")):
        return "REMOTE_OR_VIRTUAL_VERIFY_IN_QGIS", ""
    quoted = re.search(r"\bdbname=['\"]([^'\"]+)['\"]", s)
    if quoted: loc = quoted.group(1)
    else: loc = s.split("|")[0].split("?type=")[0]
    loc = re.sub(r"^file:///?", "/", loc)
    if "://" in loc: return "REMOTE_OR_VIRTUAL_VERIFY_IN_QGIS", ""
    p = Path(loc)
    if not p.is_absolute(): p = project_dir / p
    exists = p.exists()
    return ("LOCAL_SOURCE_FOUND" if exists else "LOCAL_SOURCE_NOT_FOUND"), str(p)

def inspect_project(p):
    root = ET.fromstring(project_content(p))
    crs = root.find(".//projectCrs/spatialrefsys/authid")
    res = dict(project=str(p), format=p.suffix.lower(), project_crs=crs.text if crs is not None else "NOT_DECLARED",
               project_sha256=sha256(p), layers=[], local_sources_missing=[], parse_ok=True)
    for l in root.findall(".//projectlayers/maplayer"):
        name = l.findtext("layername", ""); lid = l.findtext("id", ""); prov = l.findtext("provider", "")
        src = l.findtext("datasource", "")
        status, resolved = interpret_source(src, p.parent)
        row = dict(layer_id=lid, layer_name=name, provider=prov, source_locator=src,
                   source_status=status, resolved_local=resolved)
        res["layers"].append(row)
        if status == "LOCAL_SOURCE_NOT_FOUND": res["local_sources_missing"].append(row)
    res["layer_count"] = len(res["layers"])
    return res

def inspect_gpkg(p):
    report = dict(path=str(p), sha256=sha256(p), tables=[], warnings=[])
    con = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True, timeout=15)
    try:
        rows = con.execute("SELECT table_name, data_type, srs_id FROM gpkg_contents ORDER BY table_name").fetchall()
        for table, typ, srs in rows:
            t = table.replace('"', '""')
            fields = [c[1] for c in con.execute(f'PRAGMA table_info("{t}")').fetchall()]
            n = con.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
            entry = dict(table=table, data_type=typ, srs_id=srs, row_count=n, fields=fields)
            id_candidates = [x for x in fields if x.lower() in ("site_id", "node_id", "station_id", "point_id", "link_id")]
            if id_candidates:
                f = id_candidates[0].replace('"', '""')
                blank, distinct = con.execute(f'SELECT count(*)-count("{f}"),count(DISTINCT "{f}") FROM "{t}"').fetchone()
                entry.update(id_field=id_candidates[0], id_null_count=blank, id_duplicate_count=n - blank - distinct)
                if blank or (n - blank - distinct): report["warnings"].append(f"{table}: null/duplicate {id_candidates[0]}")
            report["tables"].append(entry)
    finally:
        con.close()
    return report

def main():
    ap=argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--repo", type=Path, required=True, help="Existing locally cloned 2026-10-28 GitHub repository")
    ap.add_argument("--qgis", type=Path, required=True, help="Explicitly selected latest .qgz/.qgs file OR folder containing exactly one project")
    ap.add_argument("--out", type=Path, required=True, help="Output directory outside the source tree")
    a=ap.parse_args(); repo=a.repo.resolve(); qgis=a.qgis.resolve(); out=a.out.resolve()
    if repo == out or out.is_relative_to(repo) or (qgis.is_dir() and out.is_relative_to(qgis)):
        ap.error("--out must be outside --repo and --qgis folder (read-only input rule)")
    out.mkdir(parents=True, exist_ok=True)
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    problems=[]; rows=[]; qreports=[]; gpkg=[]
    if not repo.is_dir(): problems.append("BLOCKER: Historical repository directory not available")
    else:
        r, errs=inventory(repo,"GitHub_history"); rows.extend(r); problems += errs
    selected=None
    if qgis.is_file() and qgis.suffix.lower() in (".qgs", ".qgz"): selected=qgis
    elif qgis.is_dir():
        candidates=sorted([p for p in walk(qgis) if p.suffix.lower() in (".qgz", ".qgs") and not p.name.endswith(".qgs~")])
        if len(candidates)==1: selected=candidates[0]
        else: problems.append(f"BLOCKER: Expected exactly one selected QGIS project; found {len(candidates)}")
    else: problems.append("BLOCKER: --qgis path not found or is not a QGIS project")
    if selected:
        try:
            pr=inspect_project(selected); qreports.append(pr)
            if pr["layer_count"]==0: problems.append("BLOCKER: QGIS project has zero parsed layers")
            if pr["local_sources_missing"]: problems.append(f"BLOCKER: {len(pr['local_sources_missing'])} missing QGIS local layer source(s)")
            if any(x["source_status"]=="REMOTE_OR_VIRTUAL_VERIFY_IN_QGIS" for x in pr["layers"]):
                problems.append("MANUAL_GATE: Some QGIS remote/virtual layer sources need live QGIS verification")
        except Exception as e: problems.append(f"BLOCKER: QGIS project parse failed: {type(e).__name__}: {e}")
        # Include only explicitly selected project and referenced vector data in new snapshot.
        r, errs=inventory(selected.parent,"New_QGIS_workspace"); rows.extend(r); problems += errs
        gpkg_paths={Path(x['resolved_local']) for pr in qreports for x in pr['layers'] if x['source_status']=='LOCAL_SOURCE_FOUND' and x['resolved_local'].lower().endswith('.gpkg')}
        for p in sorted(gpkg_paths):
            try: gpkg.append(inspect_gpkg(p))
            except Exception as e: problems.append(f"MANUAL_GATE: GeoPackage {p.name} introspection failed: {e}")
    if repo.is_dir():
        head=get_git_head(repo)
        if head != EXPECTED_BASELINE_COMMIT:
            problems.append(f"BLOCKER: Historical HEAD is {head}; expected frozen {EXPECTED_BASELINE_COMMIT}. Check out exact baseline for comparison")
        try:
            status=subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True, timeout=20, check=True)
            if status.stdout.strip(): problems.append("BLOCKER: Historical checkout has working-tree changes; audit a clean exact baseline")
        except Exception:
            problems.append("MANUAL_GATE: Cannot confirm historical checkout has clean Git working tree")
        present={r["relative_path"] for r in rows if r["source"]=="GitHub_history"}
        for p in REQ:
            if p not in present: problems.append(f"BLOCKER: Key historical file not found at documented path: {p}")
        for p in DOC_REFERENCES:
            if p not in present: problems.append(f"REPRO_GATE: README/source reference not found at documented path: {p}")
        # Snapshot sanity: no quiet mixing of stage outputs with the active input manifest.
        stages=Counter()
        for r in rows:
            if r['source']=='GitHub_history' and r['relative_path'].startswith('10_experiment_results/'):
                fields=r['relative_path'].split('/')
                if len(fields)>2: stages[fields[1]]+=1
    else: stages=Counter()
    groups=defaultdict(list)
    for r in rows: groups[r['sha256']].append(f"{r['source']}:{r['relative_path']}")
    duplicates=[dict(sha256=h, files=v) for h,v in groups.items() if len(v)>1]
    write_csv(out/'file_level_sha256_inventory.csv', rows,
              ['source','relative_path','byte_size','sha256','inclusion_policy','audit_status'])
    layerrows=[dict(project=p['project'],**l) for p in qreports for l in p['layers']]
    write_csv(out/'qgis_layers.csv', layerrows,
              ['project','layer_id','layer_name','provider','source_locator','source_status','resolved_local'])
    blocking=[x for x in problems if x.startswith(('BLOCKER:', 'REPRO_GATE:'))]
    doc={
      'audit_id':'CIQ-STAGE00-01-20261030', 'generated_utc':now,
      'audit_status':'HOLD_NOT_APPROVED' if blocking or not qreports else 'PRELIMINARY_CHECKS_ONLY_MANUAL_APPROVAL_REQUIRED',
      'approval_for_weather_traffic_carbon_recalculation':False,
      'historical_repo':str(repo), 'historical_git_head':get_git_head(repo) if repo.is_dir() else 'NOT_AVAILABLE',
      'qgis_selected':str(selected) if selected else None,
      'counts':{'historical_files_hashed':sum(x['source']=='GitHub_history' for x in rows),
                'new_qgis_workspace_files_hashed':sum(x['source']=='New_QGIS_workspace' for x in rows),
                'historical_stage_files_by_directory':dict(stages),'duplicate_sha256_groups':len(duplicates)},
      'problems':problems,'qgis_projects':qreports,'geopackages':gpkg,
      'identical_hash_groups':duplicates[:100],
      'policy':{
        'historical_stage3_to_8':'READ_ONLY_REFERENCE_NEVER_ACTIVE_BY_DEFAULT',
        'old_spatial_network':'EXCLUDED',
        'selected_new_qgis':'CANDIDATE_PENDING_SEMANTIC_AND_REGULATORY_REVIEW',
        'legacy_weather_traffic_cost':'NOT_ACTIVE_UNTIL_OWN_SOURCE_AND_METHOD_GATES_PASS',
        'numeric_recalculation':'NOT_EXECUTED'
      },
      'manual_gates':[
        'Confirm authoritative version/date of the latest 3-zone QGIS file; compare node/edge/zone IDs',
        'Verify CRS, datum, geometry validity, topology, connectivity and cross-border classification in QGIS',
        'Check candidate locations, A_C03, A_N05, A_N07 and C21 independently if present',
        'Validate effective-date CAAM/CAAS airspace sources, WMP228, CTR and no-go/approval classes',
        'Freeze synthetic demand protocol and correct denominator for matched M0/M1/M2 tasks',
        'Freeze matched road vehicle fuel/electric baselines and wind/rain UAV feasibility by aircraft',
        'Approve emissions system boundary, source factors, and uncertainty scenarios',
        'Review this audit and issue a signed approval before Stage02 numeric computation'
      ]
    }
    (out/'audit_summary.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest={
      'name':'CIQ_new_SCInetwork_active_inputs', 'version':'DRAFT_ONLY',
      'approved_for_numerical_experiments':False,
      'historical_baseline_commit':doc['historical_git_head'],
      'active_spatial_project':{'path':str(selected) if selected else None,
                                'sha256':sha256(selected) if selected else None,
                                'approval':'NOT_APPROVED'},
      'active_input_files':[],
      'deny_input_prefixes':['10_experiment_results/','03_gis_and_road_network/','06_figures_and_visualizations/'],
      'rules':['Historical results can support comparison only; they cannot enter the new computation as source data',
               'Stage 00/01 cannot release any weather/traffic/carbon recalculation',
               'No missing factor is treated as zero', 'Unknown flight/airspace permission stays unverified']}
    (out/'active_inputs_DRAFT_DENY_ALL.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=[
      '# Stage 00 + Stage 01 本地逐文件复核结果', '',
      f'- 运行时间（UTC）：{now}', f'- 总体状态：**{doc["audit_status"]}**',
      '- 天气、道路、运营碳排放重算：**未启动 / 不允许**',
      f'- Git HEAD：`{doc["historical_git_head"]}`',
      f'- 历史文件已哈希：{doc["counts"]["historical_files_hashed"]}',
      f'- 新版 QGIS 工作区文件已哈希：{doc["counts"]["new_qgis_workspace_files_hashed"]}',
      f'- QGIS 已解析图层数：{sum(p["layer_count"] for p in qreports)}', '',
      '## 缺口与阻断项', *[f'- {v}' for v in problems], '',
      '## 数据使用边界',
      '旧 Stage 3–8 一律历史只读；旧 GIS、旧交通、旧天气及旧排放模型不自动进入新版输入。',
      '本工具核实文件存在性、指纹及部分 QGIS 数据引用，并不等于模型可复现性、空域获批或地理精度通过。',
      '', '## 交付', '`file_level_sha256_inventory.csv`（逐文件）、`qgis_layers.csv`（图层引用）、',
      '`audit_summary.json`（机器可读）、`active_inputs_DRAFT_DENY_ALL.json`（计算隔离）。', '',
      '## 待人工验收', *[f'- {v}' for v in doc['manual_gates']]
    ]
    (out/'local_audit_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':doc['audit_status'],'output':str(out),'files':doc['counts'],'problems':len(problems)},ensure_ascii=False,indent=2))
    return 2 if doc['audit_status']=='HOLD_NOT_APPROVED' else 0

if __name__=='__main__': sys.exit(main())
