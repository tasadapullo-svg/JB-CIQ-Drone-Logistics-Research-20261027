#!/usr/bin/env python3
"""Conditional petrol M0 simulation on S07 accepted proxy inputs.

The model counts each physical road leg exactly once. It does not allocate the
same shared leg repeatedly to every order. Results remain conditional because
site entrances, FCD direction, and fleet parameters are not empirically verified.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import warnings
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=DeprecationWarning, message="The 'generic' unit for NumPy timedelta")


BASE = {
    "vehicle_definition": "LIGHT_GASOLINE_DELIVERY_VAN_SCENARIO",
    "vehicle_count": 3,
    "vehicle_capacity_kg": 500.0,
    "depots": ["A01", "B06", "C02"],
    "service_minutes_per_event": 5.0,
    "litres_per_100km": 10.0,
    "density_kg_per_litre": 0.73,
    "net_calorific_value_MJ_per_kg": 44.3,
    "ttw_co2_kg_per_TJ": 69300.0,
    "driver_MYR_per_hour": 15.0,
    "maintenance_MYR_per_km": 0.20,
    "waiting_engine_off": True,
    "idling_litres_per_hour": 0.0,
    "shift_end_minutes": 1800.0,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


class RouteEngine:
    def __init__(self, od: pd.DataFrame, edges: pd.DataFrame, fcd: pd.DataFrame):
        self.paths = {(r.origin_node_id, r.destination_node_id): json.loads(r.path_edge_ids_json)
                      for r in od.itertuples() if r.route_status == "CONDITIONAL_OSM_ROUTE"}
        self.edge = edges.set_index("edge_id").to_dict("index")
        pos = fcd[fcd["observed_speed_kmh_conditional"] > 0].copy()
        pos["hour"] = pos["timestamp_utc"].dt.hour
        self.exact = {(str(r.node_id), pd.Timestamp(r.timestamp_utc)): float(r.observed_speed_kmh_conditional)
                      for r in pos.itertuples()}
        self.node_hod = pos.groupby(["node_id", "hour"])["observed_speed_kmh_conditional"].median().to_dict()
        self.global_exact = pos.groupby("timestamp_utc")["observed_speed_kmh_conditional"].median().to_dict()
        self.global_hod = pos.groupby("hour")["observed_speed_kmh_conditional"].median().to_dict()
        self.cache = {}

    def travel(self, a: str, b: str, start_local: pd.Timestamp):
        if a == b:
            return {"distance_km": 0.0, "minutes": 0.0, "quality": "SAME_NODE", "quality_counts": {}}
        minute_key = pd.Timestamp(start_local).floor("min")
        key = (a, b, minute_key)
        if key in self.cache:
            return self.cache[key]
        path = self.paths.get((a, b))
        if path is None:
            raise KeyError(f"NO_DIRECTED_ROUTE:{a}->{b}")
        current = pd.Timestamp(start_local).tz_convert("UTC")
        distance_m = 0.0
        qualities = Counter()
        for edge_id in path:
            e = self.edge[edge_id]
            hour = current.floor("h")
            fcd_id = str(e["fcd_node_id"])
            raw = self.exact.get((fcd_id, hour))
            if raw is not None and raw > 0:
                proxy = raw; quality = "FCD_POSITIVE_UNDIRECTED_PROXY"
            else:
                proxy = self.node_hod.get((fcd_id, int(current.hour)))
                quality = "FALLBACK_FCD_NODE_HOUR_MEDIAN"
                if proxy is None or not math.isfinite(proxy) or proxy <= 0:
                    proxy = self.global_exact.get(hour)
                    quality = "FALLBACK_FCD_GLOBAL_EXACT_HOUR"
                if proxy is None or not math.isfinite(proxy) or proxy <= 0:
                    proxy = self.global_hod.get(int(current.hour), float(e["osm_speed_kmh"]))
                    quality = "FALLBACK_FCD_GLOBAL_HOUR_OF_DAY"
            speed = max(5.0, min(float(proxy), float(e["osm_speed_kmh"])))
            minutes = float(e["length_m"]) / 1000.0 / speed * 60.0
            current += pd.Timedelta(minutes=minutes)
            distance_m += float(e["length_m"])
            qualities[quality] += 1
        result = {"distance_km": distance_m / 1000.0,
                  "minutes": (current - pd.Timestamp(start_local).tz_convert("UTC")).total_seconds() / 60.0,
                  "quality": qualities.most_common(1)[0][0] if qualities else "NO_EDGES",
                  "quality_counts": dict(qualities)}
        self.cache[key] = result
        return result


def vehicle_template(day: pd.Timestamp, count: int):
    depots = [BASE["depots"][i % len(BASE["depots"])] for i in range(count)]
    return [{"vehicle_id": f"V{i+1:02d}", "depot": d, "loc": d, "time": day,
             "load": 0.0, "onboard": set(), "active_start": None, "km": 0.0,
             "drive_min": 0.0, "wait_min": 0.0, "service_min": 0.0, "events": 0}
            for i, d in enumerate(depots)]


def _simulate_strategy(tasks: pd.DataFrame, engine: RouteEngine, vehicle_count: int, strategy: str):
    tasks = tasks.copy()
    tasks["release"] = pd.to_datetime(tasks["release_local"], format="mixed", utc=True).dt.tz_convert("Asia/Kuala_Lumpur")
    tasks["deadline"] = tasks["release"] + pd.to_timedelta(tasks["deadline_minutes"], unit="m")
    day = tasks["release"].min().normalize()
    orders = {r.task_id: {"row": r, "state": "UNASSIGNED", "vehicle": None,
                          "pickup": None, "delivery": None, "pickup_wait_min": 0.0}
              for r in tasks.itertuples()}
    vehicles = vehicle_template(day, vehicle_count)
    legs, events = [], []
    guard = 0
    while any(o["state"] != "DELIVERED" for o in orders.values()):
        guard += 1
        if guard > 10000:
            break
        candidates_v = [v for v in vehicles if v["time"] <= day + pd.Timedelta(minutes=BASE["shift_end_minutes"])]
        if not candidates_v:
            break
        v = min(candidates_v, key=lambda x: (x["time"], x["vehicle_id"]))
        available = [k for k, o in orders.items() if o["state"] == "UNASSIGNED" and o["row"].release <= v["time"]]
        drops = list(v["onboard"])
        if not available and not drops:
            future = [o["row"].release for o in orders.values() if o["state"] == "UNASSIGNED"]
            if not future:
                # Other vehicles own all remaining tasks; move this one out of the scheduling queue.
                v["time"] = day + pd.Timedelta(minutes=BASE["shift_end_minutes"] + 1)
                continue
            nxt = min(future)
            v["wait_min"] += max(0.0, (nxt - v["time"]).total_seconds() / 60.0)
            v["time"] = max(v["time"], nxt)
            continue

        choices = []
        for task_id in drops:
            o = orders[task_id]; target = o["row"].destination_node_id
            try: tr = engine.travel(v["loc"], target, v["time"])
            except KeyError: continue
            arrival = v["time"] + pd.Timedelta(minutes=tr["minutes"])
            lateness = max(0.0, (arrival - o["row"].deadline).total_seconds() / 60.0)
            slack = (o["row"].deadline - arrival).total_seconds() / 60.0
            if strategy == "DISTANCE_FIRST":
                score = (lateness, tr["distance_km"], slack, 0, task_id)
            elif strategy == "BATCH_PICKUPS":
                batch_bias = 1 if available and len(v["onboard"]) < 3 else 0
                score = (lateness, batch_bias, tr["distance_km"], slack, task_id)
            else:
                score = (lateness, slack, tr["distance_km"], 0, task_id)
            choices.append((score, "DROPOFF", task_id, target, tr, arrival))
        for task_id in available:
            o = orders[task_id]
            if v["load"] + float(o["row"].parcel_kg) > BASE["vehicle_capacity_kg"]:
                continue
            target = o["row"].origin_node_id
            try:
                tr = engine.travel(v["loc"], target, v["time"])
                direct = engine.travel(target, o["row"].destination_node_id,
                                       v["time"] + pd.Timedelta(minutes=tr["minutes"] + BASE["service_minutes_per_event"]))
            except KeyError:
                continue
            arrival = v["time"] + pd.Timedelta(minutes=tr["minutes"])
            projected = arrival + pd.Timedelta(minutes=BASE["service_minutes_per_event"] + direct["minutes"])
            lateness = max(0.0, (projected - o["row"].deadline).total_seconds() / 60.0)
            slack = (o["row"].deadline - projected).total_seconds() / 60.0
            if strategy == "DISTANCE_FIRST":
                score = (lateness, tr["distance_km"], slack, 1, task_id)
            elif strategy == "BATCH_PICKUPS":
                pickup_bias = 0 if len(v["onboard"]) < 3 else 1
                score = (lateness, pickup_bias, tr["distance_km"], slack, task_id)
            else:
                score = (lateness, slack, tr["distance_km"], 1, task_id)
            choices.append((score, "PICKUP", task_id, target, tr, arrival))
        if not choices:
            # Mark a currently available unreachable task and continue.
            if available:
                orders[available[0]]["state"] = "UNSERVED_ROUTE_GAP"
            else:
                v["time"] = day + pd.Timedelta(minutes=BASE["shift_end_minutes"] + 1)
            continue
        _, kind, task_id, target, tr, arrival = min(choices, key=lambda x: x[0])
        o = orders[task_id]
        depart = v["time"]
        if v["active_start"] is None:
            v["active_start"] = depart
        leg_id = f"{v['vehicle_id']}-{len(legs)+1:05d}"
        legs.append({"leg_id": leg_id, "vehicle_id": v["vehicle_id"], "from_node": v["loc"], "to_node": target,
                     "departure_local": depart, "arrival_local": arrival, "road_distance_km": tr["distance_km"],
                     "driving_minutes": tr["minutes"], "traffic_quality": tr["quality"],
                     "traffic_quality_counts": json.dumps(tr["quality_counts"]), "target_task_id": task_id,
                     "target_event": kind, "physical_leg_count_rule": "COUNT_ONCE_NOT_PER_ORDER"})
        v["km"] += tr["distance_km"]; v["drive_min"] += tr["minutes"]; v["loc"] = target; v["time"] = arrival
        if kind == "PICKUP":
            start = max(v["time"], o["row"].release)
            wait = max(0.0, (start - v["time"]).total_seconds() / 60.0)
            v["wait_min"] += wait; o["pickup_wait_min"] += wait
            v["load"] += float(o["row"].parcel_kg); v["onboard"].add(task_id)
            o["state"] = "ONBOARD"; o["vehicle"] = v["vehicle_id"]; o["pickup"] = start
        else:
            start = v["time"]
            v["load"] -= float(o["row"].parcel_kg); v["onboard"].remove(task_id)
            o["state"] = "DELIVERED"; o["delivery"] = start
        v["time"] = start + pd.Timedelta(minutes=BASE["service_minutes_per_event"])
        v["service_min"] += BASE["service_minutes_per_event"]; v["events"] += 1
        events.append({"vehicle_id": v["vehicle_id"], "task_id": task_id, "event": kind,
                       "node_id": target, "service_start_local": start, "departure_local": v["time"],
                       "load_after_kg": v["load"]})

    # Return every used vehicle to its scenario depot.
    for v in vehicles:
        if v["active_start"] is None:
            continue
        try: tr = engine.travel(v["loc"], v["depot"], v["time"])
        except KeyError: tr = {"distance_km": 0.0, "minutes": 0.0, "quality": "HOLD_RETURN_ROUTE", "quality_counts": {}}
        arrival = v["time"] + pd.Timedelta(minutes=tr["minutes"])
        legs.append({"leg_id": f"{v['vehicle_id']}-{len(legs)+1:05d}", "vehicle_id": v["vehicle_id"],
                     "from_node": v["loc"], "to_node": v["depot"], "departure_local": v["time"],
                     "arrival_local": arrival, "road_distance_km": tr["distance_km"], "driving_minutes": tr["minutes"],
                     "traffic_quality": tr["quality"], "traffic_quality_counts": json.dumps(tr["quality_counts"]),
                     "target_task_id": "", "target_event": "RETURN_TO_DEPOT",
                     "physical_leg_count_rule": "COUNT_ONCE_NOT_PER_ORDER"})
        v["km"] += tr["distance_km"]; v["drive_min"] += tr["minutes"]; v["time"] = arrival; v["loc"] = v["depot"]

    order_rows = []
    for task_id, o in orders.items():
        delivered = o["state"] == "DELIVERED"
        duration = (o["delivery"] - o["row"].release).total_seconds() / 60.0 if delivered else np.nan
        order_rows.append({"task_id": task_id, "vehicle_id": o["vehicle"] or "", "status": "COMPLETED" if delivered else o["state"],
                           "pickup_local": o["pickup"], "delivery_local": o["delivery"],
                           "delivery_duration_minutes": duration, "deadline_minutes": float(o["row"].deadline_minutes),
                           "on_time": bool(delivered and o["delivery"] <= o["row"].deadline),
                           "late_minutes": max(0.0, duration - float(o["row"].deadline_minutes)) if delivered else np.nan,
                           "fuel_allocation": "NOT_ALLOCATED_ORDER_LEVEL_SHARED_LEGS_COUNTED_ONCE"})
    vehicle_rows = []
    for v in vehicles:
        active = (v["time"] - v["active_start"]).total_seconds() / 60.0 if v["active_start"] is not None else 0.0
        vehicle_rows.append({"vehicle_id": v["vehicle_id"], "depot": v["depot"], "road_km": v["km"],
                             "driving_minutes": v["drive_min"], "waiting_minutes": v["wait_min"],
                             "service_minutes": v["service_min"], "active_minutes": active,
                             "events": v["events"], "return_completed": v["loc"] == v["depot"]})
    return pd.DataFrame(order_rows), pd.DataFrame(legs), pd.DataFrame(events), pd.DataFrame(vehicle_rows)


def simulate(tasks: pd.DataFrame, engine: RouteEngine, vehicle_count: int = 3, strategy: str | None = None):
    """Multi-start deterministic heuristic; retain the best fair petrol result.

    Objective order is: minimize unserved orders, total late minutes, then physical
    vehicle-km. This prevents selecting a route merely because it makes M0 look poor.
    """
    strategies = [strategy] if strategy else ["DEADLINE_SLACK", "DISTANCE_FIRST", "BATCH_PICKUPS"]
    candidates = []
    for name in strategies:
        result = _simulate_strategy(tasks, engine, vehicle_count, name)
        orders, legs, events, vehicles = result
        score = (int((orders["status"] != "COMPLETED").sum()), float(orders["late_minutes"].fillna(1e9).sum()),
                 float(legs["road_distance_km"].sum()))
        candidates.append((score, name, result))
    score, chosen, result = min(candidates, key=lambda x: (x[0], x[1]))
    for frame in result:
        frame["chosen_strategy"] = chosen
    return result


def fuel_price_table(path: Path):
    p = pd.read_csv(path)
    p = p[p["series_type"] == "level"].copy()
    p["date"] = pd.to_datetime(p["date"])
    return p.sort_values("date")


def price_for_date(prices: pd.DataFrame, date: str, col: str = "ron95") -> float:
    d = pd.Timestamp(date)
    eligible = prices[prices["date"] <= d]
    if eligible.empty:
        eligible = prices[prices["date"] >= d]
    return float(eligible.iloc[-1 if prices[prices["date"] <= d].shape[0] else 0][col])


def co2_per_litre() -> float:
    return BASE["density_kg_per_litre"] * BASE["net_calorific_value_MJ_per_kg"] * BASE["ttw_co2_kg_per_TJ"] / 1_000_000.0


def scenario_summary(date, seed, order_rows, legs, vehicles, prices):
    km = float(legs["road_distance_km"].sum()) if len(legs) else 0.0
    litres = km * BASE["litres_per_100km"] / 100.0
    active_h = float(vehicles["active_minutes"].sum()) / 60.0
    price = price_for_date(prices, date, "ron95")
    completed = int((order_rows["status"] == "COMPLETED").sum())
    ontime = int(order_rows["on_time"].sum())
    return {"date_local": date, "scenario_seed": seed, "orders": int(len(order_rows)), "completed": completed,
            "on_time": ontime, "completion_rate": completed / len(order_rows), "on_time_rate_all_orders": ontime / len(order_rows),
            "mean_delivery_minutes": float(order_rows["delivery_duration_minutes"].mean()),
            "p95_delivery_minutes": float(order_rows["delivery_duration_minutes"].quantile(.95)),
            "late_orders": int(((order_rows["status"] == "COMPLETED") & (~order_rows["on_time"])).sum()),
            "vehicle_km": km, "fuel_litres": litres, "ttw_co2_kg": litres * co2_per_litre(),
            "petrol_MYR_per_litre": price, "fuel_cost_MYR": litres * price,
            "driver_hours": active_h, "driver_cost_MYR": active_h * BASE["driver_MYR_per_hour"],
            "maintenance_cost_MYR": km * BASE["maintenance_MYR_per_km"],
            "operating_cost_MYR": litres * price + active_h * BASE["driver_MYR_per_hour"] + km * BASE["maintenance_MYR_per_km"],
            "co2_boundary": "TTW_CO2_ONLY_NOT_FULL_LIFECYCLE_CO2E", "model_evidence": "CONDITIONAL_SCENARIO"}


def run_all(tasks, engine, prices, out: Path, limit: int | None, vehicle_count: int, checkpoint_every: int = 250):
    keys = tasks[["date_local", "scenario_seed"]].drop_duplicates().sort_values(["date_local", "scenario_seed"])
    if limit is not None:
        keys = keys.head(limit)
    all_orders, all_legs, all_events, all_vehicles, summaries = [], [], [], [], []
    for n, key in enumerate(keys.itertuples(index=False), 1):
        group = tasks[(tasks["date_local"] == key.date_local) & (tasks["scenario_seed"] == key.scenario_seed)]
        orders, legs, events, vehicles = simulate(group, engine, vehicle_count=vehicle_count)
        for d in (orders, legs, events, vehicles):
            d.insert(0, "scenario_seed", key.scenario_seed); d.insert(0, "date_local", key.date_local)
        all_orders.append(orders); all_legs.append(legs); all_events.append(events); all_vehicles.append(vehicles)
        summaries.append(scenario_summary(key.date_local, key.scenario_seed, orders, legs, vehicles, prices))
        if n % checkpoint_every == 0 or n == len(keys):
            write_json(out / "checkpoint.json", {"completed_scenarios": n, "total_scenarios": len(keys),
                                                  "last_date": key.date_local, "last_seed": key.scenario_seed,
                                                  "updated_utc": datetime.now(timezone.utc).isoformat()})
            print(json.dumps({"progress": n, "total": len(keys), "date": key.date_local}, ensure_ascii=False), flush=True)
    return (pd.concat(all_orders, ignore_index=True), pd.concat(all_legs, ignore_index=True),
            pd.concat(all_events, ignore_index=True), pd.concat(all_vehicles, ignore_index=True), pd.DataFrame(summaries))


def parameter_sensitivity(summary: pd.DataFrame, prices: pd.DataFrame):
    total_km = float(summary["vehicle_km"].sum()); total_driver_h = float(summary["driver_hours"].sum())
    rows = []
    for rate in (8.0, 10.0, 12.0):
        for price_mode, price in (("UNSUBSIDISED_STUDY_WEEK_MEAN", float(prices[(prices.date >= "2026-05-01") & (prices.date < "2026-10-01")].ron95.mean())),
                                  ("BUDI95_ELIGIBILITY_NOT_ASSUMED", 1.99), ("SKPS_ELIGIBILITY_NOT_ASSUMED", 2.05)):
            for wage in (8.72, 15.0, 25.0):
                litres = total_km * rate / 100.0
                rows.append({"litres_per_100km": rate, "fuel_price_case": price_mode, "fuel_MYR_per_litre": price,
                             "driver_MYR_per_hour": wage, "fuel_litres": litres, "ttw_co2_kg": litres * co2_per_litre(),
                             "fuel_cost_MYR": litres * price, "driver_cost_MYR": total_driver_h * wage,
                             "maintenance_cost_MYR": total_km * BASE["maintenance_MYR_per_km"],
                             "operating_cost_MYR": litres * price + total_driver_h * wage + total_km * BASE["maintenance_MYR_per_km"]})
    return pd.DataFrame(rows)


def brute_force_validation(group: pd.DataFrame, engine: RouteEngine):
    sample = group.sort_values("release_local").head(3).copy()
    sample["release"] = pd.to_datetime(sample["release_local"], format="mixed", utc=True).dt.tz_convert("Asia/Kuala_Lumpur")
    sample["deadline"] = sample["release"] + pd.to_timedelta(sample["deadline_minutes"], unit="m")
    rec = {r.task_id: r for r in sample.itertuples()}
    events = [(t, k) for t in rec for k in ("P", "D")]
    best = None
    day = sample["release"].min().normalize()
    for seq in itertools.permutations(events):
        pos = {x: i for i, x in enumerate(seq)}
        if any(pos[(t, "P")] > pos[(t, "D")] for t in rec):
            continue
        loc = "A01"; now = day; km = 0.0; late = 0.0; feasible = True
        for task_id, kind in seq:
            r = rec[task_id]; target = r.origin_node_id if kind == "P" else r.destination_node_id
            try: tr = engine.travel(loc, target, now)
            except KeyError: feasible = False; break
            now += pd.Timedelta(minutes=tr["minutes"]); km += tr["distance_km"]
            if kind == "P": now = max(now, r.release)
            else: late += max(0.0, (now - r.deadline).total_seconds() / 60.0)
            now += pd.Timedelta(minutes=BASE["service_minutes_per_event"]); loc = target
        if feasible:
            tr = engine.travel(loc, "A01", now); km += tr["distance_km"]
            score = (late, km)
            if best is None or score < best: best = score
    heuristic_orders, heuristic_legs, _, _ = simulate(sample, engine, vehicle_count=1)
    return {"date_local": str(sample.iloc[0].date_local), "scenario_seed": int(sample.iloc[0].scenario_seed),
            "orders_compared": 3, "exact_late_minutes": best[0] if best else np.nan,
            "exact_km": best[1] if best else np.nan, "heuristic_late_minutes": float(heuristic_orders["late_minutes"].sum()),
            "heuristic_km": float(heuristic_legs["road_distance_km"].sum()),
            "validation_scope": "THREE_ORDER_ONE_VEHICLE_EXACT_PRECEDENCE_ENUMERATION"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--s07", type=Path, required=True)
    ap.add_argument("--tasks", type=Path, required=True)
    ap.add_argument("--prices", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--vehicle-count", type=int, default=3)
    args = ap.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    data = args.s07 / "data"
    od = pd.read_parquet(data / "V5_68_DIRECTED_OD_MATRIX_AND_PATHS.parquet")
    edges = pd.read_parquet(data / "OSM_ROUTE_EDGES_WITH_FCD_PROXY.parquet")
    fcd = pd.read_parquet(data / "fcd_hourly_345node_2026_05_09.parquet")
    tasks = pd.read_csv(args.tasks, low_memory=False)
    prices = fuel_price_table(args.prices)
    engine = RouteEngine(od, edges, fcd)
    orders, legs, events, vehicles, summary = run_all(tasks, engine, prices, args.out, args.limit, args.vehicle_count)

    orders.to_parquet(args.out / "S08_ORDER_RESULTS.parquet", index=False)
    orders.to_csv(args.out / "S08_ORDER_RESULTS.csv.gz", index=False, compression="gzip", encoding="utf-8")
    legs.to_parquet(args.out / "S08_PHYSICAL_LEG_LEDGER.parquet", index=False)
    events.to_parquet(args.out / "S08_VEHICLE_EVENT_LOG.parquet", index=False)
    vehicles.to_parquet(args.out / "S08_VEHICLE_TRIPS.parquet", index=False)
    summary.to_csv(args.out / "S08_SCENARIO_SUMMARY.csv", index=False, encoding="utf-8-sig")
    parameter_sensitivity(summary, prices).to_csv(args.out / "S08_PARAMETER_SENSITIVITY.csv", index=False, encoding="utf-8-sig")

    if args.limit is None:
        selected = tasks[tasks["scenario_seed"] == tasks["scenario_seed"].min()].groupby("date_local", as_index=False).head(18)
        resource_rows = []
        for count in (2, 4):
            _, _, _, _, rs = run_all(selected, engine, prices, args.out / f"resource_{count}", None, count, checkpoint_every=153)
            rs["vehicle_count"] = count; resource_rows.append(rs)
        pd.concat(resource_rows, ignore_index=True).to_csv(args.out / "S08_VEHICLE_RESOURCE_SENSITIVITY_306_SCENARIOS.csv", index=False, encoding="utf-8-sig")
        validation = []
        for _, g in tasks.groupby(["date_local", "scenario_seed"], sort=True):
            validation.append(brute_force_validation(g, engine))
            if len(validation) == 10: break
        pd.DataFrame(validation).to_csv(args.out / "S08_SMALL_EXACT_ALGORITHM_VALIDATION.csv", index=False, encoding="utf-8-sig")

    completed = int((orders["status"] == "COMPLETED").sum()); ontime = int(orders["on_time"].sum())
    total = len(orders); litres = float(summary["fuel_litres"].sum()); co2 = float(summary["ttw_co2_kg"].sum())
    result = {"status": "CONDITIONAL", "scenarios": int(len(summary)), "orders": int(total), "completed": completed,
              "completion_rate": completed / total, "on_time": ontime, "on_time_rate_all_orders": ontime / total,
              "vehicle_km": float(summary["vehicle_km"].sum()), "fuel_litres": litres, "ttw_co2_kg": co2,
              "operating_cost_MYR": float(summary["operating_cost_MYR"].sum()),
              "physical_legs": int(len(legs)), "vehicle_trip_rows": int(len(vehicles)),
              "model_evidence": "CONDITIONAL_SCENARIO_CURRENT_OSM_UNDIRECTED_FCD_PROXY_UNVERIFIED_ENTRANCES",
              "accounting": "PHYSICAL_LEGS_COUNTED_ONCE; NO PER_ORDER_FUEL_DUPLICATION",
              "co2_scope": "TTW_CO2_ONLY; NOT WTW OR FULL CO2E", "parameters": BASE,
              "input_hashes": {"tasks": sha256(args.tasks), "fuel_prices": sha256(args.prices),
                               "od_matrix": sha256(data / "V5_68_DIRECTED_OD_MATRIX_AND_PATHS.parquet"),
                               "edge_fcd_map": sha256(data / "OSM_ROUTE_EDGES_WITH_FCD_PROXY.parquet")}}
    write_json(args.out / "S08_SUMMARY.json", result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
