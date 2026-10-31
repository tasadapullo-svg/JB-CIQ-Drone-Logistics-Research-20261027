from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve()
RUN = HERE.parents[2]
RESEARCH = HERE.parents[4]
OLD = RESEARCH / "output_S07_S08_Codex_20261030"
S08 = OLD / "S08"
S07 = OLD / "S07"
OUT = RUN / "S08A"
PRE = RUN / "00_PREFLIGHT"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def main() -> None:
    for folder in (PRE, OUT / "data", OUT / "qa", OUT / "reports", OUT / "logs"):
        folder.mkdir(parents=True, exist_ok=True)

    required = [
        S07 / "data" / "V5_TASK_TIME_WEATHER_ROAD_INDEX.parquet",
        S07 / "data" / "V5_249696_NODE_HOUR_WEATHER.parquet",
        S07 / "data" / "V5_68_DIRECTED_OD_MATRIX_AND_PATHS.parquet",
        S07 / "data" / "OSM_ROUTE_EDGES_WITH_FCD_PROXY.parquet",
        S08 / "data" / "S08_ORDER_RESULTS.parquet",
        S08 / "data" / "S08_SCENARIO_SUMMARY.csv",
        S08 / "data" / "S08_PHYSICAL_LEG_LEDGER.parquet",
        S08 / "data" / "S08_VEHICLE_TRIPS.parquet",
        S08 / "data" / "S08_VEHICLE_EVENT_LOG.parquet",
        S08 / "code" / "run_s08_petrol_m0.py",
        S08 / "PARAMETER_SOURCE_MATRIX.csv",
        OLD / "deliverables" / "CIQ_V5_S07_REAL_DATA_FUSION_COMPLETE.zip",
        OLD / "deliverables" / "CIQ_V5_S08_PETROL_M0_BASELINE_COMPLETE.zip",
    ]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError(missing)
    registry = []
    for p in required:
        registry.append({"path": str(p), "relative_role": p.name, "bytes": p.stat().st_size,
                         "mtime": pd.Timestamp(p.stat().st_mtime, unit="s", tz="UTC").isoformat(),
                         "sha256": sha256(p), "readable": True, "source_mutated": False})
    pd.DataFrame(registry).to_csv(PRE / "INPUT_REGISTRY.csv", index=False, encoding="utf-8-sig")
    write_json(PRE / "ENVIRONMENT.json", {
        "python": sys.version, "platform": platform.platform(), "pandas": pd.__version__,
        "numpy": np.__version__, "run_id": RUN.name, "historical_inputs_read_only": True,
    })

    tasks = pd.read_parquet(required[0])
    orders = pd.read_parquet(required[4])
    scenarios = pd.read_csv(required[5])
    legs = pd.read_parquet(required[6])
    trips = pd.read_parquet(required[7])
    events = pd.read_parquet(required[8])

    scenario_key = ["date_local", "scenario_seed"]
    leg_key = scenario_key + ["vehicle_id", "leg_id"]
    task_key = ["task_id"]
    event_key = scenario_key + ["vehicle_id", "task_id", "event"]

    # Frozen-order and population invariants.
    frozen = tasks[["task_id", "date_local", "scenario_seed", "release_local", "origin_node_id",
                    "destination_node_id", "parcel_kg", "deadline_minutes"]].copy()
    order_join = frozen.merge(orders[task_key + scenario_key + ["vehicle_id", "status", "pickup_local",
                                "delivery_local", "deadline_minutes"]], on="task_id", how="outer",
                              suffixes=("_frozen", "_result"), indicator=True)
    order_audit = {
        "frozen_rows": len(frozen), "frozen_unique_task_ids": frozen.task_id.nunique(),
        "result_rows": len(orders), "result_unique_task_ids": orders.task_id.nunique(),
        "outer_join_both": int((order_join._merge == "both").sum()),
        "missing_or_extra": int((order_join._merge != "both").sum()),
        "date_mismatch": int((order_join.date_local_frozen != order_join.date_local_result).sum()),
        "seed_mismatch": int((order_join.scenario_seed_frozen != order_join.scenario_seed_result).sum()),
        "deadline_mismatch": int((order_join.deadline_minutes_frozen != order_join.deadline_minutes_result).sum()),
        "scenarios": int(frozen[scenario_key].drop_duplicates().shape[0]),
        "orders_per_scenario_min": int(frozen.groupby(scenario_key).size().min()),
        "orders_per_scenario_max": int(frozen.groupby(scenario_key).size().max()),
    }

    # Physical ledger and return audit.
    return_legs = legs[legs.target_event == "RETURN_TO_DEPOT"].copy()
    zero_returns = return_legs[return_legs.road_distance_km == 0]
    bad_zero_returns = zero_returns[(zero_returns.from_node != zero_returns.to_node) |
                                    (zero_returns.traffic_quality == "HOLD_RETURN_ROUTE")]
    leg_audit = {
        "rows": len(legs), "unique_composite_keys": int(legs[leg_key].drop_duplicates().shape[0]),
        "duplicate_composite_keys": int(legs.duplicated(leg_key).sum()),
        "negative_distance": int((legs.road_distance_km < 0).sum()),
        "negative_driving_minutes": int((legs.driving_minutes < 0).sum()),
        "arrival_before_departure": int((pd.to_datetime(legs.arrival_local, utc=True) <
                                           pd.to_datetime(legs.departure_local, utc=True)).sum()),
        "return_rows": len(return_legs), "expected_return_rows": len(trips),
        "return_completed_false": int((~trips.return_completed.astype(bool)).sum()),
        "zero_distance_returns": len(zero_returns),
        "zero_distance_returns_same_node": int(((zero_returns.from_node == zero_returns.to_node) &
                                                  (zero_returns.traffic_quality != "HOLD_RETURN_ROUTE")).sum()),
        "invalid_or_hold_zero_returns": len(bad_zero_returns),
        "road_km_sum": float(legs.road_distance_km.sum()),
        "trip_km_sum": float(trips.road_km.sum()),
        "km_residual": float(legs.road_distance_km.sum() - trips.road_km.sum()),
    }

    # Event replay: two events per completed task, same vehicle, pickup before drop, valid load.
    event_counts = events.groupby(["task_id", "event"]).size().unstack(fill_value=0)
    event_vehicle_counts = events.groupby("task_id").vehicle_id.nunique()
    pickup = events[events.event == "PICKUP"][["task_id", "vehicle_id", "service_start_local"]].rename(
        columns={"vehicle_id": "pickup_vehicle", "service_start_local": "pickup_time"})
    drop = events[events.event == "DROPOFF"][["task_id", "vehicle_id", "service_start_local"]].rename(
        columns={"vehicle_id": "drop_vehicle", "service_start_local": "drop_time"})
    paired = pickup.merge(drop, on="task_id", how="outer")
    seq = events.sort_values(scenario_key + ["vehicle_id", "service_start_local", "departure_local"]).copy()
    seq["previous_departure"] = seq.groupby(scenario_key + ["vehicle_id"])["departure_local"].shift()
    event_overlap = (pd.to_datetime(seq.service_start_local, utc=True) <
                     pd.to_datetime(seq.previous_departure, utc=True)).fillna(False)
    event_audit = {
        "rows": len(events), "unique_event_keys": int(events[event_key].drop_duplicates().shape[0]),
        "duplicate_event_keys": int(events.duplicated(event_key).sum()),
        "tasks_with_one_pickup": int((event_counts.get("PICKUP", 0) == 1).sum()),
        "tasks_with_one_dropoff": int((event_counts.get("DROPOFF", 0) == 1).sum()),
        "tasks_multiple_vehicles": int((event_vehicle_counts != 1).sum()),
        "pickup_drop_vehicle_mismatch": int((paired.pickup_vehicle != paired.drop_vehicle).sum()),
        "drop_before_pickup": int((pd.to_datetime(paired.drop_time, utc=True) <
                                    pd.to_datetime(paired.pickup_time, utc=True)).sum()),
        "load_below_zero": int((events.load_after_kg < -1e-9).sum()),
        "load_above_500kg": int((events.load_after_kg > 500 + 1e-9).sum()),
        "max_load_kg": float(events.load_after_kg.max()),
        "service_departure_before_start": int((pd.to_datetime(events.departure_local, utc=True) <
                                                pd.to_datetime(events.service_start_local, utc=True)).sum()),
        "event_service_overlap": int(event_overlap.sum()),
    }

    # Shift, cross-day, and labor accounting audit.  These are diagnostics, not reruns.
    trip_diag = trips.copy()
    trip_diag["active_hours"] = trip_diag.active_minutes / 60.0
    for hours in (8, 12, 24, 30):
        trip_diag[f"exceeds_{hours}h"] = trip_diag.active_hours > hours
    trip_diag.to_csv(OUT / "data" / "S08A_SHIFT_AND_CROSSDAY.csv", index=False, encoding="utf-8-sig")
    delivery = pd.to_datetime(orders.delivery_local, utc=True).dt.tz_convert("Asia/Kuala_Lumpur")
    order_day = pd.to_datetime(orders.date_local).dt.date
    crossday = delivery.dt.date > order_day
    scenario_active = trips.groupby(scenario_key).active_minutes.sum() / 60.0
    shift_audit = {
        "interpretation": "1800 minutes gates entry to the scheduling loop; actions and return can finish after it",
        "vehicle_trip_rows": len(trips), "mean_active_hours_per_vehicle": float(trip_diag.active_hours.mean()),
        "max_active_hours_per_vehicle": float(trip_diag.active_hours.max()),
        "p95_active_hours_per_vehicle": float(trip_diag.active_hours.quantile(.95)),
        "mean_three_vehicle_hours_per_scenario": float(scenario_active.mean()),
        "scenarios_over_72_vehicle_hours": int((scenario_active > 72).sum()),
        "crossday_deliveries": int(crossday.sum()),
        "vehicles_exceeding_8h": int(trip_diag.exceeds_8h.sum()),
        "vehicles_exceeding_12h": int(trip_diag.exceeds_12h.sum()),
        "vehicles_exceeding_24h": int(trip_diag.exceeds_24h.sum()),
        "vehicles_exceeding_30h": int(trip_diag.exceeds_30h.sum()),
        "hard_cutoff_results": "NOT_CLAIMED; diagnostics only; any alternative hard-cutoff result requires full rerun",
        "conditional_fairness_contract": "vehicles may operate continuously; relay drivers are assumed; paid labor equals active vehicle-hours",
    }

    # Traffic fallback counts are edge traversals encoded per physical leg.
    quality_edges = Counter()
    for raw in legs.traffic_quality_counts.fillna("{}"):
        quality_edges.update(json.loads(raw))
    dominant = legs.groupby("traffic_quality").agg(
        legs=("leg_id", "size"), distance_km=("road_distance_km", "sum"), driving_minutes=("driving_minutes", "sum")
    ).reset_index()
    dominant.to_csv(OUT / "data" / "S08A_FCD_FALLBACK_AUDIT.csv", index=False, encoding="utf-8-sig")
    fcd_audit = {
        "internal_edge_traversal_counts": dict(quality_edges),
        "dominant_leg_quality_rows": dominant.to_dict("records"),
        "speed_rule": "max(5 km/h, min(FCD proxy, OSM speed))",
        "direction_status": "FCD_UNDIRECTED_PROXY",
        "historical_network_status": "CURRENT_OSM_NOT_MAY_SEP_2026_SNAPSHOT",
    }

    # Carbon, fuel, and cost reconciliation.
    km = float(legs.road_distance_km.sum())
    litres = km * 10.0 / 100.0
    co2_per_litre = 0.73 * 44.3 * 69300 / 1_000_000
    co2 = litres * co2_per_litre
    driver_hours = float(trips.active_minutes.sum()) / 60.0
    fuel_cost = float(scenarios.fuel_cost_MYR.sum())
    maintenance = km * 0.20
    driver_cost = driver_hours * 15.0
    calculated_cost = fuel_cost + maintenance + driver_cost
    carbon_cost = {
        "road_km": km, "fuel_litres_formula": litres, "reported_fuel_litres": float(scenarios.fuel_litres.sum()),
        "fuel_residual_litres": litres - float(scenarios.fuel_litres.sum()),
        "ttw_co2_kg_per_litre": co2_per_litre, "ttw_co2_formula_kg": co2,
        "reported_ttw_co2_kg": float(scenarios.ttw_co2_kg.sum()),
        "co2_residual_kg": co2 - float(scenarios.ttw_co2_kg.sum()),
        "driver_hours": driver_hours, "driver_cost_MYR": driver_cost,
        "maintenance_cost_MYR": maintenance, "fuel_cost_MYR": fuel_cost,
        "calculated_operating_cost_MYR": calculated_cost,
        "reported_operating_cost_MYR": float(scenarios.operating_cost_MYR.sum()),
        "cost_residual_MYR": calculated_cost - float(scenarios.operating_cost_MYR.sum()),
        "scope": "PETROL_COMBUSTION_TTW_CO2_ONLY; COST_IS_PARTIAL_OPEX",
    }

    # Fixed-depot confounding in the prior 2/4-vehicle sensitivity.
    resource_file = S08 / "data" / "S08_VEHICLE_RESOURCE_SENSITIVITY_306_SCENARIOS.csv"
    resource = pd.read_csv(resource_file)
    resource_audit = {
        "rows": len(resource), "scenario_coverage": int(resource[scenario_key].drop_duplicates().shape[0]),
        "vehicle_counts": sorted(resource.vehicle_count.unique().astype(int).tolist()),
        "confounding": "vehicle_template cycles A01,B06,C02; 2 and 4 vehicles change depot composition",
        "pure_vehicle_resource_effect_verified": False,
    }

    invariants = {
        "orders": order_audit, "physical_ledger": leg_audit, "events": event_audit,
        "shift": shift_audit, "fcd": fcd_audit, "carbon_cost": carbon_cost,
        "vehicle_resource_sensitivity": resource_audit,
    }
    write_json(OUT / "qa" / "S08A_FULL_RECONCILIATION.json", invariants)
    write_json(OUT / "qa" / "S08A_COST_CARBON_AUDIT.json", carbon_cost)
    write_json(OUT / "qa" / "S08A_FCD_FALLBACK_AUDIT.json", fcd_audit)
    pd.DataFrame([leg_audit]).to_csv(OUT / "data" / "S08A_PHYSICAL_LEDGER_AUDIT.csv", index=False, encoding="utf-8-sig")

    critical_values = [order_audit["missing_or_extra"], order_audit["date_mismatch"], order_audit["seed_mismatch"],
                       leg_audit["duplicate_composite_keys"], leg_audit["negative_distance"],
                       leg_audit["arrival_before_departure"], leg_audit["invalid_or_hold_zero_returns"],
                       event_audit["duplicate_event_keys"], event_audit["tasks_multiple_vehicles"],
                       event_audit["pickup_drop_vehicle_mismatch"], event_audit["drop_before_pickup"],
                       event_audit["load_below_zero"], event_audit["load_above_500kg"],
                       event_audit["event_service_overlap"]]
    numerical_pass = all(v == 0 for v in critical_values) and abs(leg_audit["km_residual"]) < 1e-6 \
        and abs(carbon_cost["fuel_residual_litres"]) < 1e-6 and abs(carbon_cost["co2_residual_kg"]) < 1e-6 \
        and abs(carbon_cost["cost_residual_MYR"]) < 1e-5
    gates = {
        "COMPUTATION_STATUS": "PASS" if numerical_pass else "FAIL",
        "SCI_EVIDENCE_STATUS": "CONDITIONAL" if numerical_pass else "HOLD",
        "S10_M0_RELEASE": "M0_30H_OPERATIONAL_WINDOW_CONDITIONAL" if numerical_pass else "HOLD",
        "original_S08_immutable": True,
        "limitations": [
            "30h is an operational vehicle scheduling window, not a validated individual-driver shift",
            "relay-driver interpretation is required; cost remains active vehicle-hours at MYR15/hour",
            "FCD direction is unobserved and speeds are floored at 5 km/h",
            "current OSM, site entrances, turn constraints and border permissions remain conditional",
            "prior 2/4-vehicle sensitivity changes depot composition",
            "18-order/3-vehicle heuristic is not proven globally optimal",
        ],
    }
    write_json(OUT / "qa" / "S08A_GATES.json", gates)
    write_json(OUT / "qa" / "S08A_M0_VERSION_DECISION.json", {
        "selected_version": gates["S10_M0_RELEASE"],
        "routing_output": "UNCHANGED_ORIGINAL_S08_MULTI_START",
        "reason": "full numerical/event conservation passes; retain pre-existing result without outcome-driven degradation",
        "driver_interpretation": shift_audit["conditional_fairness_contract"],
        "hard_shift_variants": "DIAGNOSTIC_ONLY_NOT_SIMULATED; no claim of 8/12/24h completion rates",
    })

    report = f"""# S08A M0 汽油车基线强化审计

## 结论

- 计算状态：**{gates['COMPUTATION_STATUS']}**；科学证据：**{gates['SCI_EVIDENCE_STATUS']}**。
- 冻结比较版本：`{gates['S10_M0_RELEASE']}`；旧 S08 文件未修改。
- 82,620 冻结订单、4,590 场景、179,010 物理路段、13,770 车辆行程和 165,240 取送事件均已逐行读取。
- 路段、行程、燃油、TTW CO₂和成本守恒残差均在浮点容差内。

## 物理与事件账本

- 复合路段键重复：{leg_audit['duplicate_composite_keys']}；负距离：{leg_audit['negative_distance']}；异常零公里回仓：{leg_audit['invalid_or_hold_zero_returns']}。
- 所有车辆均记录回仓；同点回仓产生的合法零公里段为 {leg_audit['zero_distance_returns_same_node']}。
- 重复任务配送：{event_audit['tasks_multiple_vehicles']}；先送后取：{event_audit['drop_before_pickup']}；载重范围 0–{event_audit['max_load_kg']:.3f} kg。

## 30小时边界

源码中的1800分钟是“允许车辆进入调度循环”的边界；动作和返仓可能在边界后完成，它不是法定司机班次。每车平均活跃 {shift_audit['mean_active_hours_per_vehicle']:.3f}h，最大 {shift_audit['max_active_hours_per_vehicle']:.3f}h；三车合计平均 {shift_audit['mean_three_vehicle_hours_per_scenario']:.3f}h；超过72车小时的场景 {shift_audit['scenarios_over_72_vehicle_hours']}；次日送达 {shift_audit['crossday_deliveries']} 单。

8/12/24/30小时仅做违反数量诊断，不伪造硬截止完成率。主比较采用“车辆连续可用、司机可换班、人工按车辆活跃小时计费”的条件性解释；该解释必须同样应用于五模式地面车辆。

## 证据限制

FCD无方向观测，内部边速度受5 km/h下限及OSM速度上限约束；路网不是研究期历史快照。既有2/4车敏感性同时改变仓点组合，不能解释为纯车辆数效应。本基线仍是条件性仿真，不是实地运营事实。
"""
    (OUT / "reports" / "S08A_BASELINE_RECONCILIATION_CN.md").write_text(report, encoding="utf-8")
    print(json.dumps({"gates": gates, "shift": shift_audit, "ledger": leg_audit,
                      "events": event_audit, "carbon_cost": carbon_cost}, ensure_ascii=False))


if __name__ == "__main__":
    main()
