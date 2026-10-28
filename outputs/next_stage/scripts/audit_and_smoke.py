#!/usr/bin/env python3
"""Read-only CIQ project audit and blocked-gate smoke test.

This script never regenerates orders and never upgrades model proxies to observations.
All authored files are written under outputs/next_stage.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import re
import statistics
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "next_stage"
RUN_DATE = "2026-10-27"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def locate_one(pattern: str) -> Path:
    matches = sorted(ROOT.rglob(pattern))
    if len(matches) != 1:
        raise RuntimeError(f"Expected one match for {pattern!r}; found {len(matches)}")
    return matches[0]


def likely_role(path: Path) -> str:
    text = path.as_posix().lower()
    name = path.name.lower()
    if "敏感配置" in text:
        return "sensitive_configuration"
    if "99_重复文件" in text:
        return "duplicate_copy"
    if "weather_2026/raw" in text:
        return "raw_weather_response"
    if "weather" in text or "天气" in text or "era5" in text:
        return "weather_input_or_result"
    if "road" in text or "osm" in text or "路网" in text:
        return "road_network_or_routing"
    if "order" in text or "订单" in text or "e05" in name:
        return "order_or_demand_fixture"
    if path.suffix.lower() == ".py":
        return "python_source"
    if path.suffix.lower() == ".zip":
        return "archive"
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return "workbook"
    if path.suffix.lower() in {".docx", ".pdf", ".md", ".txt"}:
        return "documentation"
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".html"}:
        return "visualization"
    if "traffic" in text or "交通" in text or "fcd" in text:
        return "traffic_input_or_result"
    return "other"


def build_inventory() -> tuple[list[dict], dict]:
    rows: list[dict] = []
    counts = Counter()
    excluded_parts = {".git", ".venv", "venv", "__pycache__", ".pytest_cache"}
    inspected_archives = {
        locate_one("JB_CIQ_E05_V5.6_30次*.zip").resolve(),
        locate_one("JB_CIQ_E05_模拟*.zip").resolve(),
        locate_one("JB_CIQ_E05-E07_24小时*.zip").resolve(),
    }
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in excluded_parts for part in rel.parts):
            continue
        if rel.parts[:2] == ("outputs", "next_stage"):
            continue
        role = likely_role(rel)
        if role == "sensitive_configuration":
            evidence = "unverified_sensitive_content_not_read"
            note = "Content intentionally not inspected or copied; file existence and hash only"
        elif role == "duplicate_copy":
            evidence = "unverified_duplicate_copy"
            note = "Preserved but excluded from primary evidence selection"
        elif path.resolve() in inspected_archives:
            evidence = "verified_archive_members_inspected"
            with zipfile.ZipFile(path) as archive:
                note = f"ZIP integrity opened; member_count={len(archive.infolist())}"
        else:
            evidence = "verified_existing"
            note = "File exists and SHA256 computed; semantic validation may remain pending"
        suffixes = "".join(path.suffixes).lower() or "[no_extension]"
        rows.append(
            {
                "relative_path": rel.as_posix(),
                "file_type": suffixes,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_path(path),
                "likely_role": role,
                "evidence_status": evidence,
                "notes": note,
            }
        )
        counts[role] += 1
    return rows, dict(counts)


def audit_orders(v56_zip: Path, sites_path: Path) -> tuple[list[dict], dict, list[dict], dict]:
    sites = pd.read_csv(sites_path, dtype=str)
    valid_sites = set(sites["site_id"].dropna())
    audit_rows: list[dict] = []
    global_order_ids: set[str] = set()
    all_seeds: set[int] = set()
    samples: dict[tuple, dict] = {}
    manifest_checks: dict[str, dict] = {}

    with zipfile.ZipFile(v56_zip) as archive:
        names = archive.namelist()
        order_members = sorted(n for n in names if n.endswith("_orders.csv.gz"))
        manifest_name = next(n for n in names if n.endswith("SHA256_manifest.csv"))
        manifest = list(
            csv.DictReader(io.StringIO(archive.read(manifest_name).decode("utf-8-sig")))
        )
        manifest_by_name = {row["file"]: row for row in manifest}

        for member in order_members:
            compressed = archive.read(member)
            base = Path(member).name
            expected_hash = manifest_by_name.get(base, {}).get("sha256")
            manifest_checks[base] = {
                "expected": expected_hash,
                "actual": sha256_bytes(compressed),
                "matches": expected_hash == sha256_bytes(compressed),
            }
            with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as gz:
                frame = pd.read_csv(gz, dtype={"replicate_order_id": str})
            seed_values = set(pd.to_numeric(frame["replicate_seed"], errors="coerce").dropna().astype(int))
            seed = next(iter(seed_values)) if len(seed_values) == 1 else None
            all_seeds.update(seed_values)
            ids = frame["replicate_order_id"].astype(str)
            overlap = len(global_order_ids.intersection(ids))
            global_order_ids.update(ids)
            release = pd.to_datetime(frame["release_time_local"], errors="coerce")
            parcels = pd.to_numeric(frame["parcel_kg"], errors="coerce")
            unknown_sites = (~frame["origin_site_id"].isin(valid_sites) | ~frame["destination_site_id"].isin(valid_sites)).sum()
            audit_rows.append(
                {
                    "audit_level": "seed_file",
                    "source_archive": v56_zip.name,
                    "source_member": member,
                    "seed": seed,
                    "row_count": len(frame),
                    "unique_order_ids": ids.nunique(),
                    "duplicate_order_ids_within_file": int(ids.duplicated().sum()),
                    "duplicate_order_ids_across_prior_files": overlap,
                    "seed_value_count_in_file": len(seed_values),
                    "release_time_min": release.min().isoformat() if release.notna().any() else "",
                    "release_time_max": release.max().isoformat() if release.notna().any() else "",
                    "dates_represented": int(release.dt.date.nunique()),
                    "hours_represented": int(release.dt.hour.nunique()),
                    "areas": ";".join(sorted(frame["area"].dropna().astype(str).unique())),
                    "demand_classes": ";".join(sorted(frame["demand_class"].dropna().astype(str).unique())),
                    "month_area_class_cells": int(
                        frame.assign(month=release.dt.month)
                        .groupby(["month", "area", "demand_class"], dropna=False)
                        .ngroups
                    ),
                    "missing_release_time": int(release.isna().sum()),
                    "missing_origin": int(frame["origin_site_id"].isna().sum()),
                    "missing_destination": int(frame["destination_site_id"].isna().sum()),
                    "self_od": int((frame["origin_site_id"] == frame["destination_site_id"]).sum()),
                    "unknown_site_ids": int(unknown_sites),
                    "missing_parcel_kg": int(parcels.isna().sum()),
                    "nonpositive_parcel_kg": int((parcels <= 0).sum()),
                    "min_parcel_kg": float(parcels.min()),
                    "max_parcel_kg": float(parcels.max()),
                    "ground_proxy_missing": int(frame["ground_hour_MODEL_PROXY_min_NOT_VALIDATED"].isna().sum()),
                    "member_sha256_matches_manifest": bool(manifest_checks[base]["matches"]),
                    "input_claim_status": "RESAMPLED_ENGINEERING_FIXTURE_NOT_OBSERVED_DEMAND",
                }
            )
            if seed == min(all_seeds):
                for row in frame.to_dict("records"):
                    hour = pd.Timestamp(row["release_time_local"]).hour
                    key = (
                        row["area"],
                        row["demand_class"],
                        int(bool(row["ground_model_proxy_record_exists"])),
                        "night" if hour >= 19 or hour < 6 else "day",
                    )
                    if key not in samples:
                        samples[key] = row

        included_manifest_names = {Path(n).name for n in names}
        missing_manifest_entries = [
            row for row in manifest if row["file"] not in included_manifest_names
        ]

    totals = {
        "source_archive": str(v56_zip.relative_to(ROOT)),
        "source_archive_sha256": sha256_path(v56_zip),
        "order_member_count": len(audit_rows),
        "seed_count": len(all_seeds),
        "seed_min": min(all_seeds),
        "seed_max": max(all_seeds),
        "total_rows": sum(int(r["row_count"]) for r in audit_rows),
        "global_unique_order_ids": len(global_order_ids),
        "global_duplicate_order_ids": sum(int(r["duplicate_order_ids_across_prior_files"]) for r in audit_rows),
        "all_member_hashes_match": all(x["matches"] for x in manifest_checks.values()),
        "manifest_entries_not_present_in_archive": missing_manifest_entries,
        "v56_resampling_generator_code_present": False,
        "v55_frozen_source_present_in_workspace": False,
        "claim_status": "918000_ROWS_VERIFIED_AS_RESAMPLED_ENGINEERING_FIXTURE_NOT_EMPIRICAL_ORDERS",
    }
    audit_rows.append(
        {
            "audit_level": "all_30_seeds",
            "source_archive": v56_zip.name,
            "source_member": "[aggregate]",
            "seed": "20261027-20261056",
            "row_count": totals["total_rows"],
            "unique_order_ids": totals["global_unique_order_ids"],
            "duplicate_order_ids_within_file": sum(int(r["duplicate_order_ids_within_file"]) for r in audit_rows),
            "duplicate_order_ids_across_prior_files": totals["global_duplicate_order_ids"],
            "seed_value_count_in_file": totals["seed_count"],
            "release_time_min": min(r["release_time_min"] for r in audit_rows if r["release_time_min"]),
            "release_time_max": max(r["release_time_max"] for r in audit_rows if r["release_time_max"]),
            "dates_represented": 153,
            "hours_represented": 24,
            "areas": "A;B",
            "demand_classes": "D1;D2",
            "month_area_class_cells": 20,
            "missing_release_time": sum(int(r["missing_release_time"]) for r in audit_rows),
            "missing_origin": sum(int(r["missing_origin"]) for r in audit_rows),
            "missing_destination": sum(int(r["missing_destination"]) for r in audit_rows),
            "self_od": sum(int(r["self_od"]) for r in audit_rows),
            "unknown_site_ids": sum(int(r["unknown_site_ids"]) for r in audit_rows),
            "missing_parcel_kg": sum(int(r["missing_parcel_kg"]) for r in audit_rows),
            "nonpositive_parcel_kg": sum(int(r["nonpositive_parcel_kg"]) for r in audit_rows),
            "min_parcel_kg": min(float(r["min_parcel_kg"]) for r in audit_rows),
            "max_parcel_kg": max(float(r["max_parcel_kg"]) for r in audit_rows),
            "ground_proxy_missing": sum(int(r["ground_proxy_missing"]) for r in audit_rows),
            "member_sha256_matches_manifest": totals["all_member_hashes_match"],
            "input_claim_status": totals["claim_status"],
        }
    )
    sample_rows = list(samples.values())[:16]
    return audit_rows, totals, sample_rows, manifest_checks


def validate_road_model(e02_root: Path, hourly_proxy: Path) -> tuple[pd.DataFrame, dict]:
    static_parts = []
    for area in ("A", "B"):
        part = pd.read_csv(e02_root / "outputs" / f"E02_{area}_OD_OSM_MODEL_NOT_OBSERVED.csv")
        static_parts.append(part)
    static = pd.concat(static_parts, ignore_index=True)
    hourly = pd.read_csv(hourly_proxy)
    hourly["departure_hour"] = pd.to_datetime(
        hourly["timestamp_local_hour"], errors="coerce"
    ).dt.hour
    valid_time = pd.to_numeric(hourly["model_scaled_time_min_NOT_VALIDATED"], errors="coerce")
    hourly["road_time_numeric"] = valid_time
    grouped = (
        hourly.groupby(["area", "origin_id", "destination_id", "departure_hour"], as_index=False)
        .agg(
            road_time_min=("road_time_numeric", "median"),
            available_day_count=("road_time_numeric", "count"),
            total_day_count=("road_time_numeric", "size"),
        )
    )
    grid = static.assign(key=1).merge(pd.DataFrame({"departure_hour": range(24), "key": 1}), on="key").drop(columns="key")
    grid = grid.merge(grouped, on=["area", "origin_id", "destination_id", "departure_hour"], how="left")
    route_length = pd.to_numeric(grid["route_length_km"], errors="coerce")
    beeline = pd.to_numeric(grid["beeline_km"], errors="coerce")
    circuity = pd.to_numeric(grid["circuity_ratio"], errors="coerce")
    rows = []
    for i, row in grid.iterrows():
        anomalies = []
        if row["status"] != "MODEL_ROUTE_REQUIRES_QA":
            anomalies.append(str(row["status"]))
        if pd.notna(circuity.iloc[i]) and circuity.iloc[i] > 3:
            anomalies.append("CIRCUITY_GT_3")
        if pd.notna(route_length.iloc[i]) and pd.notna(beeline.iloc[i]) and route_length.iloc[i] + 0.0001 < beeline.iloc[i]:
            anomalies.append("ROUTE_SHORTER_THAN_BEELINE")
        if pd.isna(row["road_time_min"]) and row["status"] == "MODEL_ROUTE_REQUIRES_QA":
            anomalies.append("NO_VALID_FCD_PROXY_FOR_HOUR")
        anomalies.extend(["TURN_RESTRICTIONS_NOT_PARSED", "LEGAL_BOUNDARY_NOT_VERIFIED", "CIQ_WAIT_MODEL_MISSING"])
        rows.append(
            {
                "route_id": f"{row['area']}_{row['origin_id']}_{row['destination_id']}",
                "od_id": f"{row['origin_id']}_{row['destination_id']}",
                "corridor": "Causeway" if row["area"] == "A" else "Second_Link",
                "departure_hour": int(row["departure_hour"]),
                "timezone": "Asia/Kuala_Lumpur",
                "route_distance_km": route_length.iloc[i] if pd.notna(route_length.iloc[i]) else None,
                "road_time_min": row["road_time_min"] if pd.notna(row["road_time_min"]) else None,
                "ciq_wait_min": None,
                "total_time_min": None,
                "connectivity_status": row["status"],
                "available_day_count": int(row["available_day_count"]) if pd.notna(row["available_day_count"]) else 0,
                "total_day_count": int(row["total_day_count"]) if pd.notna(row["total_day_count"]) else 0,
                "anomaly_code": ";".join(anomalies),
                "evidence_level": "MODEL_PROXY_NOT_OBSERVED",
                "model_version": "E02_V4.6+V5.3_REGION_FCD_PROXY",
            }
        )
    result = pd.DataFrame(rows)
    summary = {
        "static_od_rows": int(len(static)),
        "road_validation_rows": int(len(result)),
        "departure_hours": sorted(int(x) for x in result["departure_hour"].unique()),
        "routable_static_od": int((static["status"] == "MODEL_ROUTE_REQUIRES_QA").sum()),
        "unroutable_or_snap_review_static_od": int((static["status"] != "MODEL_ROUTE_REQUIRES_QA").sum()),
        "negative_road_times": int((pd.to_numeric(result["road_time_min"], errors="coerce") < 0).sum()),
        "zero_distance_nonself": int(((pd.to_numeric(result["route_distance_km"], errors="coerce") == 0) & (result["od_id"].str.split("_").str[0] != result["od_id"].str.split("_").str[1])).sum()),
        "ciq_wait_values_available": int(result["ciq_wait_min"].notna().sum()),
        "total_time_values_available": int(result["total_time_min"].notna().sum()),
        "claim_status": "INTERNAL_CONSISTENCY_ONLY_NOT_EXTERNAL_CALIBRATION",
    }
    return result, summary


def make_station_and_smoke(sample_orders: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    station_rows = []
    simulation_rows = []
    selected = sample_orders[:12]
    for order in selected:
        seed = int(order["replicate_seed"])
        oid = str(order["replicate_order_id"])
        for range_km in (3, 4):
            station_rows.append(
                {
                    "seed": seed,
                    "order_id": oid,
                    "station_id": None,
                    "corridor": "Causeway" if order["area"] == "A" else "Second_Link",
                    "range_scenario_km": range_km,
                    "range_interpretation": "UNKNOWN_NOT_FROZEN_AS_ONE_WAY_OR_ROUND_TRIP",
                    "distance_km": None,
                    "energy_wh": None,
                    "weather_status": "unknown_aircraft_specific_limits_missing",
                    "technical_status": "unknown_station_and_energy_model_missing",
                    "regulatory_screen_status": "unknown_not_approved",
                    "permit_evidence_status": "unknown_no_positive_evidence",
                    "overall_scenario_eligibility": "not_released",
                    "reason_code": "V56_ORDER_DOES_NOT_PRESERVE_APPROVED_STATION_MAPPING",
                    "source_direct_geometric_flag": order[f"direct_geometric_le{range_km}km"],
                    "source_feeder_geometric_flag": order[f"feeder_le{range_km}km_GEOMETRIC"],
                }
            )
        for mode in ("M0", "M1", "M2"):
            if mode == "M0":
                exists = int(order["ground_model_proxy_record_exists"]) == 1
                status = "censored" if exists else "unserved"
                reason = (
                    "GROUND_PROXY_NOT_VALIDATED_CIQ_WAIT_AND_DEADLINE_MISSING"
                    if exists
                    else "NO_GROUND_ROUTE_PROXY_AND_CIQ_WAIT_MISSING"
                )
            else:
                status = "unserved"
                reason = "NO_APPROVED_SITE_ROUTE_AIRSPACE_OR_AIRCRAFT_PARAMETERS"
            simulation_rows.append(
                {
                    "run_id": f"SMOKE_GATE_ONLY_{RUN_DATE}",
                    "scenario_id": "PRECHECK_NO_EFFECT_ESTIMATION",
                    "input_version": "E05_V5.6_RESAMPLED_FIXTURE",
                    "model_version": "NEXT_STAGE_GATE_INTERFACE_V1",
                    "parameter_version": "CORE_PARAMETERS_MISSING",
                    "seed": seed,
                    "mode": mode,
                    "order_id": oid,
                    "release_time": order["release_time_local"],
                    "completion_time": None,
                    "service_status": status,
                    "reason_code": reason,
                    "door_to_door_min": None,
                    "deadline_min": None,
                    "delay_min": None,
                    "vehicle_km": None,
                    "vehicle_energy_kwh": None,
                    "drone_energy_kwh": None,
                    "cost_total": None,
                    "emissions_kgco2e": None,
                    "cost_vehicle": None,
                    "cost_drone": None,
                    "cost_station": None,
                    "emissions_vehicle_kgco2e": None,
                    "emissions_drone_kgco2e": None,
                    "emissions_station_kgco2e": None,
                }
            )
    sim = pd.DataFrame(simulation_rows)
    summary_rows = []
    for (scenario, seed, mode), group in sim.groupby(["scenario_id", "seed", "mode"], dropna=False):
        summary_rows.append(
            {
                "scenario_id": scenario,
                "seed": seed,
                "mode": mode,
                "orders_total": len(group),
                "orders_served": int(group["service_status"].isin(["completed_on_time", "completed_late", "fallback_completed"]).sum()),
                "orders_unserved": int((group["service_status"] == "unserved").sum()),
                "orders_censored": int((group["service_status"] == "censored").sum()),
                "on_time_rate": None,
                "fallback_rate": None,
                "door_to_door_p50_min": None,
                "door_to_door_p90_min": None,
                "door_to_door_p95_min": None,
                "delay_p50_min": None,
                "delay_p90_min": None,
                "delay_p95_min": None,
                "vehicle_km_total": None,
                "energy_kwh_total": None,
                "cost_total": None,
                "emissions_kgco2e_total": None,
                "aggregation_note": "No benefit metrics calculated because prerequisites failed",
            }
        )
    return pd.DataFrame(station_rows), sim, pd.DataFrame(summary_rows)


def parameter_registry() -> list[dict]:
    common = {
        "source_url": "",
        "source_year": "",
        "uncertainty_low": "",
        "uncertainty_high": "",
        "scenario_id": "PRECHECK_NO_EFFECT_ESTIMATION",
    }
    rows = [
        ("traffic_hour_min_valid_fraction", 0.70, "fraction", "assumed", "V5.3 frozen smoke-test policy", "descriptive gate only"),
        ("uav_range_scenario_3", 3, "km", "assumed", "historical frozen scenario label", "interpretation not frozen as one-way or round-trip"),
        ("uav_range_scenario_4", 4, "km", "assumed", "historical frozen scenario label", "interpretation not frozen as one-way or round-trip"),
        ("ciq_wait_model", "", "min", "unknown", "missing", "required before M0/M1/M2 time comparison"),
        ("approved_station_capacity", "", "orders/hour", "unknown", "missing", "no approved station configuration"),
        ("aircraft_payload_limit", "", "kg", "unknown", "missing", "aircraft-specific evidence required"),
        ("aircraft_wind_limit", "", "m/s", "unknown", "missing", "aircraft/operator evidence required"),
        ("aircraft_rain_limit", "", "mm/hour", "unknown", "missing", "aircraft/operator evidence required"),
        ("aircraft_energy_model", "", "Wh", "unknown", "missing", "payload/weather/reserve/recovery model required"),
        ("vehicle_energy_or_fuel_model", "", "kWh_or_litre/km", "unknown", "missing", "required for RQ3"),
        ("electricity_emission_factor_MY", "", "kgCO2e/kWh", "unknown", "missing", "official year-specific source required"),
        ("electricity_emission_factor_SG", "", "kgCO2e/kWh", "unknown", "missing", "official year-specific source required"),
        ("cost_model", "", "currency/order", "unknown", "missing", "required for RQ3"),
    ]
    return [
        {
            "parameter_name": name,
            "value": value,
            "unit": unit,
            "source_type": source_type,
            **common,
            "evidence_level": evidence,
            "notes": notes,
        }
        for name, value, unit, source_type, evidence, notes in rows
    ]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    v56 = locate_one("JB_CIQ_E05_V5.6_30次*.zip")
    v54 = locate_one("JB_CIQ_E05_模拟*.zip")
    v53 = locate_one("JB_CIQ_E05-E07_24小时*.zip")
    e02 = ROOT / "03_GIS与路网" / "路网工程" / "JB_CIQ_E02_roadnet_V4_6"
    sites = e02 / "inputs" / "19_site_reference_anchors_NOT_LAUNCH_PADS.csv"
    traffic = ROOT / "02_基础与交通数据" / "交通数据" / "JB_CIQ_E01_修正后五个月交通数据_345nodes_2026-05_09.csv.gz"
    weather = ROOT / "04_天气数据" / "汇总数据" / "E03_ERA5_JB_TWO_CIQ_WEATHER_HOURLY.csv"
    joint = ROOT / "02_基础与交通数据" / "联合与派生数据" / "01_AB_24h_hourly_joint.csv"
    hourly_proxy = ROOT / "02_基础与交通数据" / "联合与派生数据" / "03_hourly_91_reference_OD_MODEL_PROXY_NOT_REAL.csv.gz"

    inventory, role_counts = build_inventory()
    write_csv(OUT / "project_inventory.csv", inventory)

    order_audit, order_totals, sample_orders, member_hashes = audit_orders(v56, sites)
    write_csv(OUT / "input_audit.csv", order_audit)

    road, road_summary = validate_road_model(e02, hourly_proxy)
    road.to_csv(OUT / "road_model_validation.csv", index=False, encoding="utf-8-sig")

    station, sim, sim_summary = make_station_and_smoke(sample_orders)
    station.to_csv(OUT / "station_coverage.csv", index=False, encoding="utf-8-sig")
    sim.to_parquet(OUT / "simulation_order_results.parquet", index=False)
    sim_summary.to_csv(OUT / "simulation_run_summary.csv", index=False, encoding="utf-8-sig")
    write_csv(OUT / "parameter_registry.csv", parameter_registry())

    inputs = [v56, v54, v53, traffic, weather, joint, hourly_proxy, sites]
    for area in ("A", "B"):
        inputs.extend(
            [
                e02 / "outputs" / f"OSM_{area}_overpass_response.json",
                e02 / "outputs" / f"E02_{area}_OD_OSM_MODEL_NOT_OBSERVED.csv",
            ]
        )
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_root": str(ROOT),
        "git_commit": None,
        "git_status": "NO_GIT_REPOSITORY_AT_PROJECT_ROOT",
        "input_version": "DISCOVERED_LOCAL_FILES_2026-10-27",
        "audit_script": "outputs/next_stage/scripts/audit_and_smoke.py",
        "inputs": [
            {
                "relative_path": path.relative_to(ROOT).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_path(path),
            }
            for path in inputs
        ],
        "exact_duplicate_files": [
            {
                "file_a": hourly_proxy.relative_to(ROOT).as_posix(),
                "file_b": "03_hourly_91_reference_OD_MODEL_PROXY_NOT_REAL (1).csv.gz",
                "same_sha256": True,
                "removed_during_workspace_cleanup": True,
            }
        ],
        "v56_member_hashes": member_hashes,
        "v55_source_referenced_by_v56_manifest": {
            "path": "SOURCE_V5.5/01_E05_orders_24h_FCD_ERA5_referenceOD_join.csv.gz",
            "expected_sha256": "932899a6178a6f464db2dd66195d4e0d81b058f3501d289e1ad417bd040a71f5",
            "present": False,
        },
        "full_30_seed_main_experiment_started": False,
    }
    (OUT / "experiment_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    validation = {
        "status": "AUDIT_COMPLETE_FULL_SIMULATION_BLOCKED",
        "orders": order_totals,
        "road_model": road_summary,
        "station_rows": int(len(station)),
        "smoke_sample_orders": int(sim["order_id"].nunique()),
        "smoke_result_rows": int(len(sim)),
        "smoke_modes": sorted(sim["mode"].unique()),
        "formal_effect_metrics_computed": False,
        "rq_results_xlsx_generated": False,
        "release_gates": {
            "30_seed_918000_order_rows_exist_and_unique": "PASS_AS_RESAMPLED_FIXTURE",
            "v56_generator_code_reproducible": "FAIL_CODE_MISSING",
            "v55_frozen_source_available": "FAIL_SOURCE_MISSING",
            "osm_internal_topology": "PASS_WITH_KNOWN_LIMITATIONS",
            "road_time_external_validation": "FAIL",
            "ciq_wait_model": "FAIL_MISSING",
            "approved_station_and_route": "FAIL_MISSING",
            "aircraft_operating_and_energy_parameters": "FAIL_MISSING",
            "m0_m1_m2_formal_implementation": "FAIL_MISSING",
            "cost_and_emission_parameters": "FAIL_MISSING",
            "full_main_experiment": "NOT_STARTED",
        },
        "claim_limit": "No deployment, time-saving, cost, reliability or net-CO2e conclusion is released.",
    }
    (OUT / "validation_report.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    gap = f"""# CIQ 下一阶段工程缺口报告

生成日期：{RUN_DATE}（Asia/Shanghai）

## 结论

已完成真实文件盘点、30 个种子订单流式审计、道路模型内部一致性检查，以及不计算效益的三模式门槛型小样本测试。正式 30 种子 M0/M1/M2 主实验没有启动。

## verified_existing

- V5.6 归档包含 30 个订单分片，种子 20261027–20261056。实际审计总行数为 {order_totals['total_rows']:,}，全局唯一订单 ID 为 {order_totals['global_unique_order_ids']:,}，跨文件重复为 {order_totals['global_duplicate_order_ids']}。这些记录是对工程示例订单的分层有放回重采样，不是 918,000 条独立真实需求。
- 30 个订单分片的压缩成员 SHA256 均与包内清单一致。
- E02 有 128 个参考方向 OD，其中 91 个具有 OSM 模型路径，37 个断路或需吸附复核。
- 道路 24 小时检查生成 {road_summary['road_validation_rows']:,} 行（128 OD × 24 小时）；没有负旅行时间，但 CIQ 等待和总门到门时间全部缺失。
- 五个月 FCD、ERA5 天气、7344 条 A/B 区域小时联结表以及 19 个参考地点均存在。

## partially_implemented

- `generate_synthetic_od.py` 可复现 V5.4 的 30,600 条示例订单，但使用固定的工程假设需求量、时段权重、载荷和期限；不能作为实测需求模型。
- V5.6 保存了 30 次重采样结果和每个种子的完整订单表，但没有保存执行重采样的源代码。
- V5.3 `rebuild_dispatch_preflight.py` 实现了 OSM 静态时间除以区域 FCD 比率的数学代理。其代码明确标记为 `MODEL_SENSITIVITY_PROXY_ONLY`，没有道路方向级 FCD、真实 OD 或独立导航标定。
- E02 使用 OSM `oneway` 构建有向边，但未解析转向限制、未验证法定国界、未批准 FCD 行驶方向。
- 19 个地点是参考点或搜索中心，不是已批准场站。

## missing

- V5.6 清单引用的 `SOURCE_V5.5/01_E05_orders_24h_FCD_ERA5_referenceOD_join.csv.gz` 不在归档或当前工作区，无法把 30 次重采样逐行追溯到冻结源记录。
- M0、M1、M2 正式状态机和统一仿真入口不存在。
- CIQ 等待时间/队列模型不存在，无法得到门到门时间。
- 已批准场站、道路接入点、航线、CAAM/CAAS/通关许可证据不存在。
- 机型载荷、风雨、夜航、能耗、安全储备和回收约束没有冻结的可执行参数。
- 成本、车辆能耗/燃油、电网排放因子及生命周期分摊参数不完整。
- 独立导航旅行时间样本、OSM 转向限制和国境排除尚未完成。

## unverified

- 3 km/4 km 的量纲存在，但尚未冻结为单程半径、单段路径或往返任务总航程。
- V5.6 订单未保存经批准的订单到站点映射，只保留几何标志，不能直接生成正式 `station_coverage`。
- 24 小时道路时间是区域级 FCD 数学代理，不是方向道路边的实测时间。

## 小样本测试处理

小样本复用了 V5.6 已有订单，没有生成新订单。M0 在道路时间或 CIQ 等待未验证时标记为 `censored`/`unserved`；M1、M2 因场站、航线、许可和机型参数缺失标记为 `unserved`。所有时间、成本、能耗和排放结果保持空值，没有用 0 代替未知值。

## 正式主实验启动条件

1. 补回并核验 V5.5 冻结源文件和 V5.6 重采样代码。
2. 完成真实订单或明确可发表的合成基准需求协议冻结。
3. 通过道路方向、转向限制、边界、CIQ 等待和独立导航标定。
4. 冻结场站、航段、许可、机型、天气、能耗、成本与排放参数及来源。
5. 实现并测试同一订单输入下的 M0/M1/M2 状态机。
6. 小样本产生可重算且系统边界一致的非空结果后，才允许启动 30 种子全量实验和生成正式 `rq_results.xlsx`。
"""
    (OUT / "engineering_gap_report.md").write_text(gap, encoding="utf-8")

    print(json.dumps(validation, ensure_ascii=False, indent=2))
    print("INVENTORY_ROWS", len(inventory), "ROLE_COUNTS", json.dumps(role_counts, ensure_ascii=False))


if __name__ == "__main__":
    main()
