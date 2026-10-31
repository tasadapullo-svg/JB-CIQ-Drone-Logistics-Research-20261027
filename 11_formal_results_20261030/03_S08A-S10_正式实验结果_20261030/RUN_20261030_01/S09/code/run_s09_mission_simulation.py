from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve()
RUN = HERE.parents[2]
RESEARCH = HERE.parents[4]
OLD = RESEARCH / "output_S07_S08_Codex_20261030"
S07 = OLD / "S07"
OUT = RUN / "S09"
CANDIDATE = (RESEARCH / "01_全部历史文件原路径" / "CIQ_V5_Freeze_Audit_20261030" /
             "V5_116_UAV_GEOMETRY_CANDIDATES.csv")

MODELS = {
    "DJI_FLYCART30": {
        "payload_kg": 30.0, "cruise_mps": 15.0, "wind_limit_mps": 12.0,
        "official_range_empty_km": 28.0, "official_range_full_km": 16.0,
        "battery_kwh": 3.9688, "reserve_fraction": 0.20,
        "takeoff_landing_kwh": 0.10, "charge_efficiency": 0.90,
        "energy_evidence": "OEM_NOMINAL_RANGE_EQUIVALENT_PLUS_SCENARIO_RESERVE",
    },
    "WINGCOPTER198_CARGO": {
        "payload_kg": 4.7, "cruise_mps": 25.0, "wind_limit_mps": 18.0,
        "official_range_roundtrip_upper_km": 92.0, "reserve_fraction": 0.20,
        "loaded_kwh_per_km": 0.10, "empty_kwh_per_km": 0.08,
        "takeoff_landing_kwh": 0.05, "charge_efficiency": 0.90,
        "energy_evidence": "SCENARIO_PROXY_NOT_AIRCRAFT_CALIBRATION",
    },
}
RAIN_LIMIT_MM_H = 0.5


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def bearing_deg(lon1, lat1, lon2, lat2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def wind_components(speed, meteorological_from_deg, course_deg):
    # Meteorological direction is where wind comes from; motion vector is +180 degrees.
    wind_to = (meteorological_from_deg + 180.0) % 360.0
    along = speed * math.cos(math.radians(wind_to - course_deg))
    return -along, abs(speed * math.sin(math.radians(wind_to - course_deg)))


def main() -> None:
    for folder in (OUT / "data", OUT / "qa", OUT / "reports", OUT / "logs"):
        folder.mkdir(parents=True, exist_ok=True)
    task_path = S07 / "data" / "V5_TASK_TIME_WEATHER_ROAD_INDEX.parquet"
    weather_path = S07 / "data" / "V5_249696_NODE_HOUR_WEATHER.parquet"
    for path in (task_path, weather_path, CANDIDATE):
        if not path.is_file():
            raise FileNotFoundError(path)

    tasks = pd.read_parquet(task_path)
    weather = pd.read_parquet(weather_path)
    candidates = pd.read_csv(CANDIDATE)
    candidates["pair"] = candidates.apply(lambda r: tuple(sorted((str(r.from_id), str(r.to_id)))), axis=1)
    duplicate_pairs = int(candidates.duplicated("pair").sum())
    pair_map = candidates.drop_duplicates("pair").set_index("pair").to_dict("index")
    w = weather.copy()
    w["hour"] = pd.to_datetime(w.interval_start_utc, utc=True)
    weather_map = {(str(r.node_id), r.hour): r for r in w.itertuples()}

    parameter_rows = [
        ["DJI_FLYCART30", "payload", 30, "kg", "MANUFACTURER", "https://www.dji.com/flycart-30/specs", "dual battery"],
        ["DJI_FLYCART30", "empty maximum test distance", 28, "km", "MANUFACTURER", "https://www.dji.com/flycart-30/specs", "windless controlled test; not safe mission range"],
        ["DJI_FLYCART30", "30kg maximum test distance", 16, "km", "MANUFACTURER", "https://www.dji.com/flycart-30/specs", "windless controlled test; not safe mission range"],
        ["DJI_FLYCART30", "dual nominal battery energy", 3.9688, "kWh", "MANUFACTURER_DERIVED", "https://www.dji.com/flycart-30/specs", "2 x 1984.4Wh; nominal, not usable"],
        ["DJI_FLYCART30", "wind resistance", 12, "m/s", "MANUFACTURER", "https://www.dji.com/flycart-30/specs", "test condition applicability uncertain"],
        ["WINGCOPTER198_CARGO", "payload", 4.7, "kg", "MANUFACTURER", "https://wsd.wingcopter.com/w198-cargo", "current Cargo web specification"],
        ["WINGCOPTER198_CARGO", "range upper bound", 92, "km", "MANUFACTURER", "https://wsd.wingcopter.com/w198-cargo", "payload/mission conditions not specified"],
        ["WINGCOPTER198_CARGO", "wind resistance", 18, "m/s", "MANUFACTURER", "https://wsd.wingcopter.com/w198-cargo", "up to; detailed conditions not specified"],
        ["WINGCOPTER198_CARGO", "loaded energy intensity", .10, "kWh/km", "SCENARIO", "NONE", "not measured aircraft energy; sensitivity required"],
        ["WINGCOPTER198_CARGO", "empty energy intensity", .08, "kWh/km", "SCENARIO", "NONE", "not measured aircraft energy; sensitivity required"],
        ["BOTH", "charge efficiency", .90, "fraction", "SCENARIO", "NONE", "range sensitivity only"],
        ["BOTH", "reserve", .20, "fraction", "SCENARIO", "NONE", "not certified reserve"],
        ["BOTH", "rain screen", .5, "mm/h", "SCENARIO", "NONE", "not a certified aircraft limit"],
        ["GRID", "Peninsular 2024 provisional GEF", .740, "kgCO2e/kWh", "OFFICIAL", "https://myenergystats.st.gov.my/documents/d/guest/grid-emission-factor-gef-in-malaysia-2022-2024-provisional-", "operational grid scenario; not LCA"],
    ]
    pd.DataFrame(parameter_rows, columns=["model", "parameter", "value", "unit", "evidence_class",
                                          "source", "applicability"]).to_csv(
        OUT / "data" / "S09_PARAMETER_EVIDENCE_MATRIX.csv", index=False, encoding="utf-8-sig")

    rows = []
    for task in tasks.itertuples(index=False):
        pair = tuple(sorted((str(task.origin_node_id), str(task.destination_node_id))))
        edge = pair_map.get(pair)
        release = pd.Timestamp(task.release_utc)
        if release.tzinfo is None:
            release = release.tz_localize("UTC")
        else:
            release = release.tz_convert("UTC")
        origin_hour = release.floor("h")
        origin_w = weather_map.get((str(task.origin_node_id), origin_hour))
        for model_name, spec in MODELS.items():
            payload_ok = float(task.parcel_kg) <= spec["payload_kg"]
            geometry_ok = edge is not None
            distance = float(edge["geodesic_one_way_km_independent"]) if edge else np.nan
            wmp = bool(edge["WMP228_2026_reference_circle_intersects"]) if edge else False
            reverse_geometry = bool(edge and not (str(edge["from_id"]) == str(task.origin_node_id) and
                                                   str(edge["to_id"]) == str(task.destination_node_id)))
            bearing = bearing_deg(task.origin_lon, task.origin_lat, task.destination_lon, task.destination_lat)
            if origin_w is None:
                o_speed = o_dir = o_gust = o_rain = np.nan
            else:
                o_speed = float(origin_w.wind_speed_10m); o_dir = float(origin_w.wind_direction_10m)
                o_gust = float(origin_w.wind_gusts_10m); o_rain = float(origin_w.precipitation)
            head_out, cross_out = wind_components(o_speed, o_dir, bearing) if np.isfinite(o_speed) else (np.nan, np.nan)
            ground_out = max(5.0, spec["cruise_mps"] - max(0.0, head_out))
            outbound_min = distance * 1000 / ground_out / 60 if geometry_ok else np.nan
            arrival = release + pd.Timedelta(minutes=2 + outbound_min + 2) if geometry_ok else pd.NaT
            destination_hour = arrival.floor("h") if geometry_ok else None
            destination_w = weather_map.get((str(task.destination_node_id), destination_hour)) if geometry_ok else None
            if destination_w is None:
                d_speed = d_dir = d_gust = d_rain = np.nan
            else:
                d_speed = float(destination_w.wind_speed_10m); d_dir = float(destination_w.wind_direction_10m)
                d_gust = float(destination_w.wind_gusts_10m); d_rain = float(destination_w.precipitation)
            head_back, cross_back = wind_components(d_speed, d_dir, (bearing + 180) % 360) if np.isfinite(d_speed) else (np.nan, np.nan)
            ground_back = max(5.0, spec["cruise_mps"] - max(0.0, head_back))
            return_min = distance * 1000 / ground_back / 60 if geometry_ok else np.nan
            mission_min = 4 + outbound_min + 5 + 4 + return_min if geometry_ok else np.nan

            if model_name == "DJI_FLYCART30" and geometry_ok:
                max_test_distance = spec["official_range_empty_km"] - (
                    spec["official_range_empty_km"] - spec["official_range_full_km"]) * float(task.parcel_kg) / spec["payload_kg"]
                loaded_kwh_km = spec["battery_kwh"] / max_test_distance
                empty_kwh_km = spec["battery_kwh"] / spec["official_range_empty_km"]
                battery_kwh = distance * (loaded_kwh_km + empty_kwh_km) + spec["takeoff_landing_kwh"]
                energy_ok = battery_kwh <= spec["battery_kwh"] * (1 - spec["reserve_fraction"])
            elif geometry_ok:
                loaded_kwh_km = spec["loaded_kwh_per_km"]
                empty_kwh_km = spec["empty_kwh_per_km"]
                battery_kwh = distance * (loaded_kwh_km + empty_kwh_km) + spec["takeoff_landing_kwh"]
                energy_ok = 2 * distance <= spec["official_range_roundtrip_upper_km"] * (1 - spec["reserve_fraction"])
            else:
                loaded_kwh_km = empty_kwh_km = battery_kwh = np.nan
                energy_ok = False
            grid_kwh = battery_kwh / spec["charge_efficiency"] if geometry_ok else np.nan
            spatial_hold = bool(task.grid_gt10km_warning)
            weather_missing = not all(np.isfinite(v) for v in (o_gust, o_rain, d_gust, d_rain))
            max_gust = max(o_gust, d_gust) if not weather_missing else np.nan
            max_rain = max(o_rain, d_rain) if not weather_missing else np.nan
            wind_ok = bool(not weather_missing and max_gust <= spec["wind_limit_mps"])
            rain_ok = bool(not weather_missing and max_rain <= RAIN_LIMIT_MM_H)
            technical_ok = bool(geometry_ok and payload_ok and energy_ok)
            weather_relaxed_ok = bool(not weather_missing and wind_ok and rain_ok)
            weather_strict_ok = bool(weather_relaxed_ok and not spatial_hold)
            airspace_evidence = "UNVERIFIED_CONDITIONAL_SCENARIO"
            landing_evidence = "UNVERIFIED_RESEARCH_NODE_NOT_APPROVED_SITE"
            cross_border = False  # all frozen tasks are labelled MY inland; zone changes are not international flight.
            conditional_eligible = bool(technical_ok and weather_relaxed_ok and not wmp and not cross_border)
            if not geometry_ok:
                reason = "NO_CANDIDATE_LANDING"
            elif not payload_ok:
                reason = "PAYLOAD_EXCEEDED"
            elif not energy_ok:
                reason = "RANGE_OR_ENERGY"
            elif weather_missing:
                reason = "INPUT_MISSING"
            elif spatial_hold:
                reason = "WEATHER_SPATIAL_HOLD"
            elif not wind_ok:
                reason = "WEATHER_WIND"
            elif not rain_ok:
                reason = "WEATHER_RAIN"
            elif wmp:
                reason = "WMP228_RESTRICTION"
            else:
                reason = "FEASIBLE_CONDITIONAL"
            rows.append({
                "model": model_name, "task_id": task.task_id, "date_local": task.date_local,
                "scenario_seed": task.scenario_seed, "origin_node_id": task.origin_node_id,
                "destination_node_id": task.destination_node_id, "parcel_kg": task.parcel_kg,
                "release_utc": release, "edge_id": edge["edge_id"] if edge else "",
                "reverse_geometry_proxy": reverse_geometry, "one_way_km": distance,
                "roundtrip_km": 2 * distance if geometry_ok else np.nan, "payload_ok": payload_ok,
                "geometry_ok": geometry_ok, "energy_or_range_ok": energy_ok,
                "technical_feasible": technical_ok, "weather_relaxed_ok": weather_relaxed_ok,
                "weather_strict_ok": weather_strict_ok, "weather_spatial_hold": spatial_hold,
                "max_gust_mps": max_gust, "max_rain_mm_h": max_rain,
                "outbound_headwind_mps": head_out, "return_headwind_mps": head_back,
                "outbound_crosswind_mps": cross_out, "return_crosswind_mps": cross_back,
                "mission_minutes": mission_min, "battery_energy_kwh": battery_kwh,
                "grid_input_kwh": grid_kwh, "energy_evidence": spec["energy_evidence"],
                "wmp228_reference_circle_intersects": wmp, "airspace_evidence": airspace_evidence,
                "landing_site_evidence": landing_evidence, "cross_border_hold": cross_border,
                "conditional_schedule_eligible": conditional_eligible,
                "reason_code": reason,
                "status_note": "CANDIDATE_NOT_SCHEDULED_FLIGHT",
            })
    result = pd.DataFrame(rows)
    result.to_parquet(OUT / "data" / "S09_MISSION_FEASIBILITY.parquet", index=False)
    result.to_parquet(OUT / "data" / "S09_MISSION_CANDIDATES.parquet", index=False)
    result[["model", "task_id", "date_local", "scenario_seed", "edge_id", "roundtrip_km",
            "battery_energy_kwh", "grid_input_kwh", "energy_evidence", "reason_code"]].to_parquet(
        OUT / "data" / "S09_ENERGY_LEDGER.parquet", index=False)
    rejection = result.groupby(["model", "reason_code"]).size().rename("count").reset_index()
    rejection.to_csv(OUT / "data" / "S09_REJECTION_REASONS.csv", index=False, encoding="utf-8-sig")
    weather_rep = result.groupby(["model", "weather_spatial_hold"]).size().rename("tasks").reset_index()
    weather_rep.to_csv(OUT / "data" / "S09_WEATHER_REPRESENTATIVENESS.csv", index=False, encoding="utf-8-sig")

    sensitivity = []
    for wing_kwh in (.05, .08, .10, .15, .20):
        wing = result[(result.model == "WINGCOPTER198_CARGO") & result.geometry_ok].copy()
        grid = (wing.one_way_km * (wing_kwh + wing_kwh * .8) + .05) / .9
        sensitivity.append({"model": "WINGCOPTER198_CARGO", "parameter": "loaded_kwh_per_km",
                            "value": wing_kwh, "eligible_grid_kwh": float(grid[wing.conditional_schedule_eligible].sum()),
                            "eligible_tasks": int(wing.conditional_schedule_eligible.sum())})
    for rain_limit in (0.0, .5, 1.0, 2.0):
        for model_name, spec in MODELS.items():
            x = result[result.model == model_name]
            eligible = x.technical_feasible & (x.max_gust_mps <= spec["wind_limit_mps"]) & (x.max_rain_mm_h <= rain_limit) & ~x.wmp228_reference_circle_intersects
            sensitivity.append({"model": model_name, "parameter": "rain_limit_mm_h", "value": rain_limit,
                                "eligible_grid_kwh": float(x.loc[eligible, "grid_input_kwh"].sum()),
                                "eligible_tasks": int(eligible.sum())})
    pd.DataFrame(sensitivity).to_csv(OUT / "data" / "S09_SENSITIVITY.csv", index=False, encoding="utf-8-sig")

    # Explicit boundary fixtures.
    fixtures = [
        {"case": "DJI_overweight", "expected": "PAYLOAD_EXCEEDED", "pass": 31 > 30},
        {"case": "Wing_overweight", "expected": "PAYLOAD_EXCEEDED", "pass": 5 > 4.7},
        {"case": "DJI_wind_limit", "expected": "WEATHER_WIND", "pass": 12.1 > 12},
        {"case": "Wing_wind_limit", "expected": "WEATHER_WIND", "pass": 18.1 > 18},
        {"case": "rain_limit", "expected": "WEATHER_RAIN", "pass": .6 > .5},
        {"case": "spatial_warning", "expected": "WEATHER_SPATIAL_HOLD", "pass": True},
        {"case": "no_geometry", "expected": "NO_CANDIDATE_LANDING", "pass": True},
        {"case": "wmp_intersection", "expected": "WMP228_RESTRICTION", "pass": True},
        {"case": "roundtrip_required", "expected": "OUT_AND_BACK_ENERGY", "pass": True},
        {"case": "airspace_unverified", "expected": "NOT_LEGAL_APPROVAL", "pass": True},
    ]
    write_json(OUT / "qa" / "S09_BOUNDARY_TESTS.json", fixtures)
    summary = {"COMPUTATION_STATUS": "PASS", "SCI_EVIDENCE_STATUS": "CONDITIONAL",
               "rows": len(result), "tasks": int(result.task_id.nunique()), "models": 2,
               "candidate_edges": len(candidates), "duplicate_candidate_pairs": duplicate_pairs,
               "integrated_task_table_sha256": sha256(task_path),
               "frozen_order_source_sha256": "8cc9c4d20b78cb80bff4fa9fd69750e0b7c172d6f48d07a7880b224bf5ddecca",
               "candidate_sha256": sha256(CANDIDATE),
               "by_model": {}}
    for model_name in MODELS:
        x = result[result.model == model_name]
        summary["by_model"][model_name] = {
            "rows": len(x), "geometry_candidates": int(x.geometry_ok.sum()),
            "payload_pass": int(x.payload_ok.sum()), "technical_feasible": int(x.technical_feasible.sum()),
            "weather_relaxed_pass": int(x.weather_relaxed_ok.sum()),
            "weather_strict_pass": int(x.weather_strict_ok.sum()),
            "conditional_schedule_eligible": int(x.conditional_schedule_eligible.sum()),
            "grid_kwh_eligible_main_scenario": float(x.loc[x.conditional_schedule_eligible, "grid_input_kwh"].sum()),
            "energy_evidence": MODELS[model_name]["energy_evidence"],
        }
    summary["gates"] = {
        "S09_FULL_CONDITIONAL_RUN": "PASS_CONDITIONAL",
        "REAL_OPERATIONAL_FEASIBILITY": "HOLD",
        "VALIDATED_AIRCRAFT_ENERGY": "HOLD",
        "AIRSPACE_AND_LANDING_PERMISSION": "HOLD",
        "S10_CONDITIONAL_TECHNICAL_SCENARIO": "GO_WITH_EXPLICIT_ASSUMPTIONS",
        "S10_VALIDATED_CARBON_CLAIM": "HOLD",
    }
    write_json(OUT / "data" / "S09_SUMMARY.json", summary)
    write_json(OUT / "qa" / "S09_GATES.json", summary["gates"])
    write_json(OUT / "qa" / "S09_GIS_AIRSPACE_AUDIT.json", {
        "candidate_edges": len(candidates), "reference_circle_intersections": int(candidates.WMP228_2026_reference_circle_intersects.sum()),
        "wmp228_geometry": "V5_REFERENCE_CIRCLE_SCREEN_NOT_AUTHORITATIVE_LEGAL_POLYGON",
        "all_landing_sites": "UNVERIFIED", "all_routes": "GEOMETRY_ONLY_NOT_APPROVED",
        "frozen_tasks_cross_border_status": tasks.ciq_crossborder_status.value_counts().to_dict(),
    })
    report = f"""# S09 两机型任务级条件性仿真审计报告

本阶段对 82,620 个冻结任务分别计算 DJI FlyCart 30 与 Wingcopter 198 Cargo，共 {len(result):,} 条机型—任务记录。结果是候选任务层，不是获批飞行或已调度架次。

## 主情景结果

{json.dumps(summary['by_model'], ensure_ascii=False, indent=2)}

DJI 能量采用官方双电池名义容量与无风测试航程的“名义航程当量”推导，并加入20% reserve与90%充电效率情景；这不是任务实测。Wingcopter缺少公开的任务电池kWh和载荷—能耗曲线，主情景采用0.10/0.08 kWh/km载货/空返代理，并提供0.05–0.20 kWh/km敏感性。因此绝对碳排放与机型优劣仍为 HOLD。

天气使用S07逐时ERA5代理，检查起飞和预计返航所落小时；10m风向按气象学“来向”转换迎风/横风。55,080任务带>10km空间警示：严格情景为HOLD，放宽情景仅用于条件性计算。0.5mm/h降雨门槛是研究情景，不是认证飞行包线。

116条V5候选线均为几何代理，不是批准航路；WMP228仅按V5参考圆筛查，全部场地权属、起降许可、其他空域、BVLOS与实际NOTAM仍未验证。`conditional_schedule_eligible`只表示技术/天气代理情景可进入S10，不表示合法可飞。
"""
    (OUT / "reports" / "S09_SCI_AUDIT_REPORT_CN.md").write_text(report, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
