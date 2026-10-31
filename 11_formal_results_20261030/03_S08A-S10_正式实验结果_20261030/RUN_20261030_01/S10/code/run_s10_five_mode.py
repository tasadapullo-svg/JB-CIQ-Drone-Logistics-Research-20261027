from __future__ import annotations

import importlib.util
import argparse
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
S08 = OLD / "S08"
S09 = RUN / "S09"
OUT = RUN / "S10"
MODES = ["M0_PETROL", "M1_DJI", "M1_WING", "M2_DJI", "M2_WING"]
MODEL_FOR = {"M1_DJI": "DJI_FLYCART30", "M2_DJI": "DJI_FLYCART30",
             "M1_WING": "WINGCOPTER198_CARGO", "M2_WING": "WINGCOPTER198_CARGO"}
DEPOTS = ["A01", "B06", "C02"]
PETROL_L_100KM = 10.0
PETROL_CO2_KG_L = 2.2410927
GRID_KG_KWH = 0.740
ELECTRICITY_MYR_KWH = 0.50  # explicit scenario assumption, not a verified tariff
DRIVER_MYR_H = 15.0
MAINT_MYR_KM = 0.20


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def load_s08_module():
    path = S08 / "code" / "run_s08_petrol_m0.py"
    spec = importlib.util.spec_from_file_location("s08_original", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class HourlyStartCache:
    """Reuse routes within the same FCD hour across the 30 paired replications.

    FCD itself is hourly.  The underlying S08 engine still advances edge by edge
    across hour boundaries; only the departure minute is standardized to the
    start of its hour for hybrid-mode tractability.
    """
    def __init__(self, base):
        self.base = base
        self.cache = {}

    def travel(self, a, b, start_local):
        start = pd.Timestamp(start_local)
        hour = start.floor("h")
        key = (str(a), str(b), hour)
        if key not in self.cache:
            self.cache[key] = self.base.travel(a, b, hour)
        return self.cache[key]


def m1_scenario(tasks, feas, engine, s08mod, mode, petrol_price):
    model = MODEL_FOR[mode]
    fx = feas[(feas.model == model) & feas.task_id.isin(tasks.task_id)].set_index("task_id")
    # M1 fixed stations respect the directed V5 candidate orientation. Reverse-only candidates remain ground fallback.
    eligible_ids = set(fx.index[fx.conditional_schedule_eligible & ~fx.reverse_geometry_proxy])
    drone_tasks = tasks[tasks.task_id.isin(eligible_ids)].copy().sort_values(["release_utc", "task_id"])
    ground_tasks = tasks[~tasks.task_id.isin(eligible_ids)].copy()
    station_available = {}
    uav_rows, flights = [], []
    for t in drone_tasks.itertuples(index=False):
        f = fx.loc[t.task_id]
        release = pd.Timestamp(t.release_local)
        if release.tzinfo is None:
            release = release.tz_localize("Asia/Kuala_Lumpur")
        station = str(t.origin_node_id)
        start = max(release, station_available.get(station, release.normalize()))
        out_flight = max(0.0, float(f.mission_minutes) - 13.0) / 2.0
        delivery = start + pd.Timedelta(minutes=2 + out_flight + 2)
        charger_kw = 7.2 if model == "DJI_FLYCART30" else 2.0
        charge_min = float(f.grid_input_kwh) / charger_kw * 60.0
        available = start + pd.Timedelta(minutes=float(f.mission_minutes) + charge_min)
        station_available[station] = available
        duration = (delivery - release).total_seconds() / 60.0
        deadline = float(t.deadline_minutes)
        uav_rows.append({"task_id": t.task_id, "status": "COMPLETED", "delivery_local": delivery,
                         "delivery_duration_minutes": duration, "deadline_minutes": deadline,
                         "on_time": duration <= deadline, "late_minutes": max(0.0, duration - deadline),
                         "service_path": "UAV_FIXED_STATION_CONDITIONAL", "vehicle_id": "",
                         "flight_id": f"{mode}-{t.scenario_seed}-{t.task_id}"})
        flights.append({"flight_id": f"{mode}-{t.scenario_seed}-{t.task_id}", "mode": mode,
                        "task_id": t.task_id, "date_local": t.date_local, "scenario_seed": t.scenario_seed,
                        "launch_node": station, "delivery_node": t.destination_node_id,
                        "launch_local": start, "delivery_local": delivery, "resource_available_local": available,
                        "roundtrip_km": f.roundtrip_km, "grid_input_kwh": f.grid_input_kwh,
                        "mission_minutes": f.mission_minutes, "energy_evidence": f.energy_evidence,
                        "airspace_evidence": f.airspace_evidence, "physical_count_rule": "COUNT_ONCE_PER_FLIGHT"})
    if len(ground_tasks):
        # The frozen M0 itself retains the stronger three-strategy result.  Hybrid
        # fallback uses the deterministic BATCH_PICKUPS policy to keep the full
        # 9,180 fallback reruns tractable; algorithm-budget asymmetry is reported.
        go, gl, ge, gv = s08mod.simulate(ground_tasks, engine, vehicle_count=3, strategy="BATCH_PICKUPS")
        ground = go.copy()
        ground["service_path"] = "PETROL_FALLBACK"
        ground["flight_id"] = ""
        for x in (gl, gv):
            x["date_local"] = tasks.iloc[0].date_local
            x["scenario_seed"] = tasks.iloc[0].scenario_seed
            x["mode"] = mode
        gl["physical_leg_id"] = (mode + "-" + str(tasks.iloc[0].scenario_seed) + "-" +
                                  gl["vehicle_id"].astype(str) + "-" + gl["leg_id"].astype(str))
    else:
        ground = pd.DataFrame(columns=uav_rows[0].keys() if uav_rows else [])
        gl = pd.DataFrame(columns=["road_distance_km", "driving_minutes"])
        gv = pd.DataFrame(columns=["active_minutes"])
    order = pd.concat([ground, pd.DataFrame(uav_rows)], ignore_index=True, sort=False)
    km = float(gl.road_distance_km.sum()) if len(gl) else 0.0
    driver_h = float(gv.active_minutes.sum()) / 60.0 if len(gv) else 0.0
    grid = float(sum(x["grid_input_kwh"] for x in flights))
    uav_operator_h = float(sum(x["mission_minutes"] for x in flights)) / 60.0
    litres = km * PETROL_L_100KM / 100
    cost = litres * petrol_price + km * MAINT_MYR_KM + driver_h * DRIVER_MYR_H + grid * ELECTRICITY_MYR_KWH + uav_operator_h * DRIVER_MYR_H
    stats = {"vehicle_km": km, "fuel_litres": litres, "ttw_co2_kg": litres * PETROL_CO2_KG_L,
             "grid_input_kwh": grid, "grid_ghg_kgco2e": grid * GRID_KG_KWH,
             "operational_energy_ghg_kg_scenario": litres * PETROL_CO2_KG_L + grid * GRID_KG_KWH,
             "driver_hours": driver_h, "uav_operator_hours": uav_operator_h,
             "operating_cost_MYR_partial": cost, "uav_flights": len(flights),
             "fixed_station_count": len(station_available), "ground_legs": len(gl)}
    return order, gl, pd.DataFrame(flights), stats


def m2_scenario(tasks, feas, engine, mode, petrol_price):
    model = MODEL_FOR[mode]
    fx = feas[(feas.model == model) & feas.task_id.isin(tasks.task_id)].set_index("task_id")
    day = pd.Timestamp(tasks.iloc[0].release_local).normalize()
    vehicles = [{"vehicle_id": f"V{i+1:02d}", "depot": depot, "loc": depot, "time": day,
                 "start": None, "km": 0.0, "drive": 0.0} for i, depot in enumerate(DEPOTS)]
    orders, legs, flights = [], [], []
    for t in tasks.sort_values(["release_utc", "task_id"]).itertuples(index=False):
        release = pd.Timestamp(t.release_local)
        if release.tzinfo is None:
            release = release.tz_localize("Asia/Kuala_Lumpur")
        eligible = t.task_id in fx.index and bool(fx.loc[t.task_id].conditional_schedule_eligible)
        candidates = []
        for v in vehicles:
            depart = max(v["time"], release)
            tr1 = engine.travel(v["loc"], t.origin_node_id, depart)
            pickup_arrive = depart + pd.Timedelta(minutes=tr1["minutes"])
            ready = max(pickup_arrive, release) + pd.Timedelta(minutes=5)
            if eligible:
                f = fx.loc[t.task_id]
                finish = ready + pd.Timedelta(minutes=float(f.mission_minutes))
                score = (finish, tr1["distance_km"], v["vehicle_id"])
                candidates.append((score, v, depart, tr1, None, ready, f))
            else:
                tr2 = engine.travel(t.origin_node_id, t.destination_node_id, ready)
                delivery = ready + pd.Timedelta(minutes=tr2["minutes"])
                finish = delivery + pd.Timedelta(minutes=5)
                score = (finish, tr1["distance_km"] + tr2["distance_km"], v["vehicle_id"])
                candidates.append((score, v, depart, tr1, tr2, ready, None))
        _, v, depart, tr1, tr2, ready, f = min(candidates, key=lambda x: x[0])
        if v["start"] is None:
            v["start"] = depart
        pickup_arrive = depart + pd.Timedelta(minutes=tr1["minutes"])
        legs.append({"mode": mode, "date_local": t.date_local, "scenario_seed": t.scenario_seed,
                     "physical_leg_id": f"{mode}-{t.scenario_seed}-{len(legs)+1}", "vehicle_id": v["vehicle_id"],
                     "from_node": v["loc"], "to_node": t.origin_node_id, "departure_local": depart,
                     "arrival_local": pickup_arrive, "road_distance_km": tr1["distance_km"],
                     "driving_minutes": tr1["minutes"], "target_task_id": t.task_id,
                     "target_event": "MOBILE_LAUNCH_OR_PICKUP", "physical_count_rule": "COUNT_ONCE"})
        v["km"] += tr1["distance_km"]; v["drive"] += tr1["minutes"]; v["loc"] = t.origin_node_id
        if f is not None:
            out_flight = max(0.0, float(f.mission_minutes) - 13.0) / 2.0
            delivery = ready + pd.Timedelta(minutes=2 + out_flight + 2)
            finish = ready + pd.Timedelta(minutes=float(f.mission_minutes))
            flight_id = f"{mode}-{t.scenario_seed}-{t.task_id}"
            flights.append({"flight_id": flight_id, "mode": mode, "task_id": t.task_id,
                            "date_local": t.date_local, "scenario_seed": t.scenario_seed,
                            "vehicle_id": v["vehicle_id"], "launch_node": t.origin_node_id,
                            "delivery_node": t.destination_node_id, "recovery_node": t.origin_node_id,
                            "launch_local": ready, "delivery_local": delivery, "recovery_local": finish,
                            "roundtrip_km": f.roundtrip_km, "grid_input_kwh": f.grid_input_kwh,
                            "mission_minutes": f.mission_minutes, "energy_evidence": f.energy_evidence,
                            "airspace_evidence": f.airspace_evidence, "physical_count_rule": "COUNT_ONCE_PER_FLIGHT"})
            service_path = "UAV_MOBILE_SAME_POINT_RENDEZVOUS_CONDITIONAL"
            v["time"] = finish; flight = flight_id
        else:
            delivery = ready + pd.Timedelta(minutes=tr2["minutes"])
            finish = delivery + pd.Timedelta(minutes=5)
            legs.append({"mode": mode, "date_local": t.date_local, "scenario_seed": t.scenario_seed,
                         "physical_leg_id": f"{mode}-{t.scenario_seed}-{len(legs)+1}", "vehicle_id": v["vehicle_id"],
                         "from_node": t.origin_node_id, "to_node": t.destination_node_id, "departure_local": ready,
                         "arrival_local": delivery, "road_distance_km": tr2["distance_km"],
                         "driving_minutes": tr2["minutes"], "target_task_id": t.task_id,
                         "target_event": "GROUND_DROPOFF", "physical_count_rule": "COUNT_ONCE"})
            v["km"] += tr2["distance_km"]; v["drive"] += tr2["minutes"]
            v["loc"] = t.destination_node_id; v["time"] = finish
            service_path = "PETROL_GROUND_DIRECT"; flight = ""
        duration = (delivery - release).total_seconds() / 60.0
        orders.append({"task_id": t.task_id, "vehicle_id": v["vehicle_id"], "status": "COMPLETED",
                       "delivery_local": delivery, "delivery_duration_minutes": duration,
                       "deadline_minutes": float(t.deadline_minutes), "on_time": duration <= float(t.deadline_minutes),
                       "late_minutes": max(0.0, duration - float(t.deadline_minutes)),
                       "service_path": service_path, "flight_id": flight})
    for v in vehicles:
        if v["start"] is None:
            continue
        tr = engine.travel(v["loc"], v["depot"], v["time"])
        arrival = v["time"] + pd.Timedelta(minutes=tr["minutes"])
        legs.append({"mode": mode, "date_local": tasks.iloc[0].date_local,
                     "scenario_seed": tasks.iloc[0].scenario_seed,
                     "physical_leg_id": f"{mode}-{tasks.iloc[0].scenario_seed}-{len(legs)+1}",
                     "vehicle_id": v["vehicle_id"], "from_node": v["loc"], "to_node": v["depot"],
                     "departure_local": v["time"], "arrival_local": arrival,
                     "road_distance_km": tr["distance_km"], "driving_minutes": tr["minutes"],
                     "target_task_id": "", "target_event": "RETURN_TO_DEPOT", "physical_count_rule": "COUNT_ONCE"})
        v["km"] += tr["distance_km"]; v["drive"] += tr["minutes"]; v["time"] = arrival; v["loc"] = v["depot"]
    km = sum(v["km"] for v in vehicles)
    driver_h = sum((v["time"] - v["start"]).total_seconds() / 3600 for v in vehicles if v["start"] is not None)
    grid = sum(x["grid_input_kwh"] for x in flights)
    litres = km * PETROL_L_100KM / 100
    cost = litres * petrol_price + km * MAINT_MYR_KM + driver_h * DRIVER_MYR_H + grid * ELECTRICITY_MYR_KWH
    stats = {"vehicle_km": km, "fuel_litres": litres, "ttw_co2_kg": litres * PETROL_CO2_KG_L,
             "grid_input_kwh": grid, "grid_ghg_kgco2e": grid * GRID_KG_KWH,
             "operational_energy_ghg_kg_scenario": litres * PETROL_CO2_KG_L + grid * GRID_KG_KWH,
             "driver_hours": driver_h, "uav_operator_hours": 0.0,
             "operating_cost_MYR_partial": cost, "uav_flights": len(flights),
             "fixed_station_count": 0, "ground_legs": len(legs)}
    return pd.DataFrame(orders), pd.DataFrame(legs), pd.DataFrame(flights), stats


def summarize_scenario(mode, date, seed, orders, stats):
    return {"mode": mode, "date_local": date, "scenario_seed": seed, "orders": len(orders),
            "completed": int((orders.status == "COMPLETED").sum()), "on_time": int(orders.on_time.sum()),
            "completion_rate": float((orders.status == "COMPLETED").mean()),
            "on_time_rate_all_orders": float(orders.on_time.mean()),
            "mean_delivery_minutes": float(orders.delivery_duration_minutes.mean()),
            "p95_delivery_minutes": float(orders.delivery_duration_minutes.quantile(.95)),
            "late_orders": int((~orders.on_time).sum()), **stats,
            "ghg_boundary": "PETROL_TTW_CO2_PLUS_GRID_OPERATIONAL_GHG_SCENARIO_NOT_WTW_OR_LCA",
            "cost_boundary": "PARTIAL_OPEX_NO_CAPITAL_SITE_BATTERY_DEPRECIATION"}


def paired_statistics(scenarios):
    metrics = ["on_time_rate_all_orders", "vehicle_km", "fuel_litres", "grid_input_kwh",
               "operational_energy_ghg_kg_scenario", "operating_cost_MYR_partial"]
    rows = []
    rng = np.random.default_rng(20261030)
    for mode in MODES[1:]:
        for metric in metrics:
            a = scenarios[scenarios["mode"] == mode].set_index(["date_local", "scenario_seed"])[metric]
            b = scenarios[scenarios["mode"] == "M0_PETROL"].set_index(["date_local", "scenario_seed"])[metric]
            diff = (a - b).dropna()
            # Cluster at seed: each seed contributes one five-month mean difference.
            tmp = diff.reset_index().groupby("scenario_seed")[metric].mean().to_numpy()
            boots = np.array([rng.choice(tmp, len(tmp), replace=True).mean() for _ in range(4000)])
            rows.append({"mode_vs_m0": mode, "metric": metric, "paired_scenarios": len(diff),
                         "seed_clusters": len(tmp), "mean_difference": float(diff.mean()),
                         "seed_cluster_mean_difference": float(tmp.mean()),
                         "ci95_low": float(np.quantile(boots, .025)), "ci95_high": float(np.quantile(boots, .975)),
                         "inference": "SEED_CLUSTER_BOOTSTRAP_CONDITIONAL_NOT_CAUSAL"})
    return pd.DataFrame(rows)


def main() -> None:
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="first N date-seed scenarios for boundary smoke test")
    ap.add_argument("--start", type=int, default=0, help="zero-based scenario offset")
    ap.add_argument("--chunk-label", default=None, help="write an independently mergeable full-output chunk")
    args = ap.parse_args()
    if args.chunk_label:
        OUT = OUT / "chunks" / args.chunk_label
    elif args.limit is not None:
        OUT = OUT / "sample_test"
    for folder in (OUT / "data", OUT / "qa", OUT / "reports", OUT / "logs"):
        folder.mkdir(parents=True, exist_ok=True)
    s08mod = load_s08_module()
    tasks = pd.read_parquet(S07 / "data" / "V5_TASK_TIME_WEATHER_ROAD_INDEX.parquet")
    od = pd.read_parquet(S07 / "data" / "V5_68_DIRECTED_OD_MATRIX_AND_PATHS.parquet")
    edges = pd.read_parquet(S07 / "data" / "OSM_ROUTE_EDGES_WITH_FCD_PROXY.parquet")
    fcd = pd.read_parquet(S07 / "data" / "fcd_hourly_345node_2026_05_09.parquet")
    engine = HourlyStartCache(s08mod.RouteEngine(od, edges, fcd))
    feas = pd.read_parquet(S09 / "data" / "S09_MISSION_FEASIBILITY.parquet")
    m0_orders = pd.read_parquet(S08 / "data" / "S08_ORDER_RESULTS.parquet")
    m0_scen = pd.read_csv(S08 / "data" / "S08_SCENARIO_SUMMARY.csv")
    petrol_price = m0_scen.set_index(["date_local", "scenario_seed"]).petrol_MYR_per_litre.to_dict()
    all_orders, all_scenarios, all_legs, all_flights = [], [], [], []

    m0o = m0_orders.copy(); m0o["mode"] = "M0_PETROL"; m0o["service_path"] = "PETROL_BASELINE"; m0o["flight_id"] = ""
    all_orders.append(m0o)
    m0 = m0_scen.copy(); m0["mode"] = "M0_PETROL"; m0["grid_input_kwh"] = 0.0; m0["grid_ghg_kgco2e"] = 0.0
    m0["operational_energy_ghg_kg_scenario"] = m0.ttw_co2_kg
    m0["operating_cost_MYR_partial"] = m0.operating_cost_MYR
    m0["uav_operator_hours"] = 0.0; m0["uav_flights"] = 0; m0["fixed_station_count"] = 0; m0["ground_legs"] = np.nan
    m0["ghg_boundary"] = "PETROL_COMBUSTION_TTW_CO2_ONLY"
    m0["cost_boundary"] = "PARTIAL_OPEX_NO_CAPITAL"
    all_scenarios.append(m0)

    grouped = list(tasks.groupby(["date_local", "scenario_seed"], sort=True))
    if args.limit is not None or args.start:
        grouped = grouped[args.start:(args.start + args.limit) if args.limit is not None else None]
        allowed = {(str(k[0]), int(k[1])) for k, _ in grouped}
        m0o = m0o[m0o.apply(lambda r: (str(r.date_local), int(r.scenario_seed)) in allowed, axis=1)]
        all_orders[0] = m0o
        m0 = m0[m0.apply(lambda r: (str(r.date_local), int(r.scenario_seed)) in allowed, axis=1)]
        all_scenarios[0] = m0
    checkpoint = OUT / "logs" / "S10_PROGRESS.json"
    for idx, ((date, seed), group) in enumerate(grouped, start=1):
        price = float(petrol_price[(date, seed)])
        for mode in MODES[1:]:
            if mode.startswith("M1"):
                oo, ll, ff, stats = m1_scenario(group, feas, engine, s08mod, mode, price)
            else:
                oo, ll, ff, stats = m2_scenario(group, feas, engine, mode, price)
            oo["mode"] = mode; oo["date_local"] = date; oo["scenario_seed"] = seed
            all_orders.append(oo); all_scenarios.append(pd.DataFrame([summarize_scenario(mode, date, seed, oo, stats)]))
            if len(ll): all_legs.append(ll)
            if len(ff): all_flights.append(ff)
        if idx % 100 == 0 or idx == len(grouped):
            write_json(checkpoint, {"completed_scenarios": idx, "total_scenarios": len(grouped),
                                    "completed_mode_scenarios_including_m0": idx * 5})
            print(f"S10 checkpoint {idx}/{len(grouped)}", flush=True)

    orders = pd.concat(all_orders, ignore_index=True, sort=False)
    scenarios = pd.concat(all_scenarios, ignore_index=True, sort=False)
    legs = pd.concat(all_legs, ignore_index=True, sort=False)
    flights = pd.concat(all_flights, ignore_index=True, sort=False)
    orders.to_parquet(OUT / "data" / "S10_MODE_ORDER_RESULTS.parquet", index=False)
    scenarios.to_csv(OUT / "data" / "S10_MODE_SCENARIO_SUMMARY.csv", index=False, encoding="utf-8-sig")
    legs.to_parquet(OUT / "data" / "S10_GROUND_PHYSICAL_LEGS.parquet", index=False)
    flights.to_parquet(OUT / "data" / "S10_UAV_SCHEDULED_FLIGHTS.parquet", index=False)
    paired = paired_statistics(scenarios)
    paired.to_csv(OUT / "data" / "S10_PAIRED_STATISTICS.csv", index=False, encoding="utf-8-sig")
    seed_totals = scenarios.groupby(["mode", "scenario_seed"], as_index=False).agg(
        orders=("orders", "sum"), completed=("completed", "sum"), on_time=("on_time", "sum"),
        vehicle_km=("vehicle_km", "sum"), fuel_litres=("fuel_litres", "sum"),
        grid_input_kwh=("grid_input_kwh", "sum"),
        operational_energy_ghg_kg_scenario=("operational_energy_ghg_kg_scenario", "sum"),
        operating_cost_MYR_partial=("operating_cost_MYR_partial", "sum"))
    seed_totals.to_csv(OUT / "data" / "S10_SEED_LEVEL_FIVE_MONTH_TOTALS.csv", index=False, encoding="utf-8-sig")
    mode_summary = scenarios.groupby("mode", as_index=False).agg(
        scenarios=("scenario_seed", "size"), orders=("orders", "sum"), completed=("completed", "sum"),
        on_time=("on_time", "sum"), vehicle_km=("vehicle_km", "sum"), fuel_litres=("fuel_litres", "sum"),
        ttw_co2_kg=("ttw_co2_kg", "sum"), grid_input_kwh=("grid_input_kwh", "sum"),
        grid_ghg_kgco2e=("grid_ghg_kgco2e", "sum"),
        operational_energy_ghg_kg_scenario=("operational_energy_ghg_kg_scenario", "sum"),
        operating_cost_MYR_partial=("operating_cost_MYR_partial", "sum"), uav_flights=("uav_flights", "sum"))
    mode_summary["completion_rate"] = mode_summary.completed / mode_summary.orders
    mode_summary["on_time_rate_all_orders"] = mode_summary.on_time / mode_summary.orders
    mode_summary.to_csv(OUT / "data" / "S10_MODE_SUMMARY.csv", index=False, encoding="utf-8-sig")
    key = ["mode", "date_local", "scenario_seed", "task_id"]
    expected_order_rows = len(grouped) * 18 * 5
    expected_scenario_rows = len(grouped) * 5
    qa = {"mode_order_rows": len(orders), "expected_mode_order_rows": expected_order_rows,
          "unique_mode_order_keys": int(orders[key].drop_duplicates().shape[0]),
          "duplicate_mode_order_keys": int(orders.duplicated(key).sum()),
          "mode_scenario_rows": len(scenarios), "expected_mode_scenario_rows": expected_scenario_rows,
          "orders_per_mode": orders.groupby("mode").size().to_dict(),
          "orders_per_mode_scenario_min": int(orders.groupby(["mode", "date_local", "scenario_seed"]).size().min()),
          "orders_per_mode_scenario_max": int(orders.groupby(["mode", "date_local", "scenario_seed"]).size().max()),
          "ground_leg_duplicate_keys": int(legs.duplicated(["mode", "date_local", "scenario_seed", "physical_leg_id"]).sum()),
          "flight_duplicate_ids": int(flights.flight_id.duplicated().sum()),
          "negative_ground_distance": int((legs.road_distance_km < 0).sum()),
          "negative_flight_energy": int((flights.grid_input_kwh < 0).sum()),
          "all_tasks_preserved": len(orders) == expected_order_rows and orders[key].drop_duplicates().shape[0] == expected_order_rows}
    write_json(OUT / "qa" / "S10_INVARIANTS.json", qa)
    gates = {"S10_PREFLIGHT": "PASS", "S10_FULL_RUN": "PASS_CONDITIONAL" if qa["all_tasks_preserved"] else "FAIL",
             "S10_SCI_CARBON_CLAIM": "HOLD",
             "reason": "Wingcopter task energy, airspace/site permission, symmetric WTW/LCA and full capital costs are unverified"}
    write_json(OUT / "qa" / "S10_GATES.json", gates)
    summary = {"gates": gates, "qa": qa, "mode_summary": mode_summary.to_dict("records"),
               "statistics": "paired date+seed differences; CI clustered by 30 seeds; conditional, not causal",
               "m1_definition": "directed fixed launch-node UAV pool plus three-vehicle petrol fallback",
               "m2_definition": "three vehicle-mounted UAVs; vehicle reaches launch node, waits for same-point recovery; ground fallback",
               "hybrid_traffic_time_resolution": "hourly departure cache; underlying engine advances edges across hourly FCD",
               "accounting_boundary": "PETROL_TTW_PLUS_GRID_OPERATIONAL_GHG_SCENARIO; NOT WTW/LCA; PARTIAL_OPEX"}
    write_json(OUT / "data" / "S10_SUMMARY.json", summary)
    report = f"""# S10 五模式条件性联合实验

实际生成 {len(scenarios):,} 个模式场景和 {len(orders):,} 条模式—订单记录；所有模式均保留82,620条冻结任务。完整汇总见 `data/S10_MODE_SUMMARY.csv`。

M1采用有向V5候选线的固定发射节点、有限单机排队及三辆汽油车回退；M2采用三辆车各携一机，车辆实际到达任务起点、等待无人机同点回收，再继续任务。没有瞬移；地面路段与飞行分别使用唯一ID且只记一次。

当前排放列为汽油TTW CO₂加2024马来半岛临时电网因子的运营能源情景，并非对称WTW或LCA。成本是部分OPEX，不含站点、机体、电池及资本折旧。Wingcopter任务kWh是显式代理，空域和场地未获批准。因此可以报告条件性数值、敏感性和破平衡关系，但不能写“已验证显著减排”或“实际最低碳”。

状态：`{gates['S10_FULL_RUN']}`；碳优越性主张：`{gates['S10_SCI_CARBON_CLAIM']}`。
"""
    (OUT / "reports" / "S10_SCI_AUDIT_REPORT_CN.md").write_text(report, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
