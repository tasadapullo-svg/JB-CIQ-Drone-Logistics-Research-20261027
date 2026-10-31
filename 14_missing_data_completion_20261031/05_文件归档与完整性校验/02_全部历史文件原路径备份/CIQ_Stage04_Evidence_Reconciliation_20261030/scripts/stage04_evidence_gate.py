#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage04: read-only historical OD & weather evidence reconciliation.

No routing, weather interpolation, dispatch simulation, or emissions calculations.
The program always returns HOLD until externally reviewed spatial and experiment releases.
"""
import argparse
import collections
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

OD_REQUIRED = (
    "od_id", "area", "cross_border_route", "original_route_exists",
    "diagnostic_category", "original_status", "candidate_route_found"
)
REPAIR_REQUIRED = (
    "od_id", "area", "diagnostic_category", "candidate_route_found",
    "repair_applied", "residual_exception"
)


def read_csv(path: Path, required):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        missing = sorted(set(required) - set(fields))
        if missing:
            raise ValueError("Missing columns in %s: %s" % (path.name, ", ".join(missing)))
        rows = list(reader)
    return rows


def digest(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def flag(v):
    value = str(v).strip().lower()
    if value in ("true", "1", "yes"): return True
    if value in ("false", "0", "no"): return False
    return None


def audit_od(ods, repairs):
    issues = []
    keys = [x["od_id"].strip() for x in ods]
    if len(set(keys)) != len(keys): issues.append("DUPLICATE_OD_ID")
    if not ods: issues.append("EMPTY_OD")
    index = {x["od_id"].strip(): x for x in ods}
    exceptions = [x for x in ods if flag(x["original_route_exists"]) is False]
    other = [x for x in ods if flag(x["original_route_exists"]) is None]
    if other: issues.append("UNKNOWN_ORIGINAL_ROUTE_EXISTS")
    if any(not x["area"].strip() for x in ods): issues.append("MISSING_AREA")
    repair_ids = [x["od_id"].strip() for x in repairs]
    if len(set(repair_ids)) != len(repair_ids): issues.append("DUPLICATE_REPAIR_OD_ID")
    unmatched = set(repair_ids) - set(keys)
    if unmatched: issues.append("REPAIR_NOT_IN_OD: " + ",".join(sorted(unmatched)))
    missing_repairs = set(x["od_id"].strip() for x in exceptions) - set(repair_ids)
    if missing_repairs: issues.append("EXCEPTION_MISSING_REPAIR_LOG: " + ",".join(sorted(missing_repairs)))
    contradictory = []
    for r in repairs:
        src = index.get(r["od_id"].strip())
        if src and (src["area"].strip() != r["area"].strip() or src["diagnostic_category"].strip() != r["diagnostic_category"].strip()):
            contradictory.append(r["od_id"])
    if contradictory: issues.append("REPAIR_CATEGORY_OR_ZONE_MISMATCH: " + ",".join(sorted(contradictory)))
    applied = [x for x in repairs if flag(x["repair_applied"]) is True]
    if applied and any(not x.get("reviewer_approval_id", "").strip() for x in applied):
        issues.append("APPLIED_REPAIR_MISSING_EXPLICIT_REVIEWER_APPROVAL")
    if any(flag(x["repair_applied"]) is None for x in repairs): issues.append("UNKNOWN_REPAIR_APPLIED")
    area_counts = collections.Counter(x["area"] for x in ods)
    exception_by_area = collections.Counter(x["area"] for x in exceptions)
    cross_border_n = sum(flag(x["cross_border_route"]) is True for x in ods)
    if cross_border_n == 0: issues.append("NO_CROSS_BORDER_OD_IN_HISTORY")
    if exceptions and len(applied) != len(exceptions): issues.append("UNAPPROVED_OD_REPAIRS_REMAIN")
    return {
        "counts": {
            "od_rows": len(ods), "areas": dict(sorted(area_counts.items())),
            "routable_original": sum(flag(x["original_route_exists"]) is True for x in ods),
            "unroutable_original": len(exceptions),
            "exceptions_by_area": dict(sorted(exception_by_area.items())),
            "cross_border_od": cross_border_n,
            "candidate_found_in_repair_log": sum(flag(x["candidate_route_found"]) is True for x in repairs),
            "repair_rows": len(repairs), "repairs_applied": len(applied),
            "repaired_without_approval": sum(not x.get("reviewer_approval_id", "").strip() for x in applied),
        },
        "original_status": dict(sorted(collections.Counter(x["original_status"] for x in ods).items())),
        "diagnostic_category": dict(sorted(collections.Counter(x["diagnostic_category"] for x in ods).items())),
        "issues": issues,
    }


def audit_weather_qc(summary):
    issues=[]; months=[]
    for month, d in sorted(summary.get("months", {}).items()):
        era=d.get("era5_grid_by_point", [])
        nasa=d.get("nasa_grid_by_point", [])
        ekeys = [(v.get("latitude_returned"),v.get("longitude_returned")) for v in era]
        nkeys = [(v.get("latitude_returned"),v.get("longitude_returned")) for v in nasa]
        nea=[c for c in d.get("coverage",[]) if c.get("source")=="NEA" and c.get("variable") in ("rainfall","wind-speed","wind-direction")]
        nea_status = sorted(set(c.get("status", "UNKNOWN") for c in nea))
        row={"month":month,"weather_hourly_rows":d.get("weather_hourly_rows"),
             "era5_returned_grid_count":len(era), "era5_unique_grid_count":len(set(ekeys)),
             "nasa_returned_grid_count":len(nasa), "nasa_unique_grid_count":len(set(nkeys)),
             "rain_correlation_reported":d.get("era5_nasa_rain",{}).get("correlation"),
             "wind_correlation_reported":d.get("era5_nasa_wind",{}).get("correlation"),
             "nea_statuses":nea_status,"nea_core_coverage_rows":len(nea)}
        months.append(row)
        if len(set(ekeys)) < len(ekeys):issues.append("MONTH_%s_REPEATED_ERA5_GRID"%month)
        if "NOT_REQUESTED" in nea_status or "PARTIAL" in nea_status:issues.append("MONTH_%s_NEA_NOT_FULLY_VALIDATED"%month)
        if d.get("anomaly_total",None)!=0:issues.append("MONTH_%s_PIPELINE_ANOMALIES_OR_UNKNOWNS"%month)
        if row["rain_correlation_reported"] is None:issues.append("MONTH_%s_RAIN_CORRELATION_NOT_AVAILABLE"%month)
    if not months:issues.append("NO_MONTHLY_WEATHER_QC")
    return {"months":months,"issues":issues,"note":"Historic reported QC only, not independent hourly weather recalculation"}


def run(od=None, repairs=None, qc=None, spatial_gate=None):
    inputs={"od":od,"repair_log":repairs,"weather_qc":qc,"stage02_gate":spatial_gate}
    out={"audit_id":"CIQ_S04_20261030","status":"HOLD_RECALC_BLOCKED",
         "recalculation_authorized":False,
         "source_files":{},"checks":{},"blocking_reasons":[],
         "notice":"Read-only audit, never authorizes traffic, weather, dispatch or emissions recalculation"}
    for key,path in inputs.items():
        if path is not None and path.exists():
            out["source_files"][key]={"path":str(path),"size_bytes":path.stat().st_size,"sha256":digest(path)}
        else:
            out["source_files"][key]={"path":str(path) if path else None,"status":"NOT_PROVIDED_OR_MISSING"}
            out["blocking_reasons"].append("MISSING_"+key.upper())
    if od and repairs and od.is_file() and repairs.is_file():
        try:
            od_result=audit_od(read_csv(od,OD_REQUIRED),read_csv(repairs,REPAIR_REQUIRED))
            out["checks"]["historical_road_diagnostics"]=od_result
            out["blocking_reasons"]+=od_result["issues"]
        except Exception as e:
            out["blocking_reasons"].append("OD_READ_ERROR:"+str(e))
    if qc and qc.is_file():
        try:
            weather_result=audit_weather_qc(json.loads(qc.read_text(encoding="utf-8-sig")))
            out["checks"]["historical_weather_qc"]=weather_result
            out["blocking_reasons"]+=weather_result["issues"]
        except Exception as e:
            out["blocking_reasons"].append("WEATHER_READ_ERROR:"+str(e))
    if spatial_gate and spatial_gate.is_file():
        try:
            s=json.loads(spatial_gate.read_text(encoding="utf-8-sig"))
            out["checks"]["stage02"]={"scientific_spatial_input_frozen":s.get("scientific_spatial_input_frozen",False),"status":s.get("status","UNKNOWN")}
            if s.get("scientific_spatial_input_frozen") is not True:out["blocking_reasons"].append("STAGE02_NOT_FROZEN")
        except Exception as e:
            out["blocking_reasons"].append("SPATIAL_GATE_READ_ERROR:"+str(e))
    out["blocking_reasons"] = sorted(set(out["blocking_reasons"]))
    # Deliberate hard lock: a read-only audit cannot grant regulatory/scientific release.
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--od",type=Path)
    p.add_argument("--repairs",type=Path)
    p.add_argument("--weather-qc",type=Path)
    p.add_argument("--stage02-gate",type=Path)
    p.add_argument("--output",type=Path,default=Path("stage04_road_weather_evidence_gate.json"))
    a=p.parse_args()
    r=run(a.od,a.repairs,a.weather_qc,a.stage02_gate)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":r["status"],"issues":len(r["blocking_reasons"]),"output":str(a.output)},ensure_ascii=False))
    return 2

if __name__=="__main__":sys.exit(main())
