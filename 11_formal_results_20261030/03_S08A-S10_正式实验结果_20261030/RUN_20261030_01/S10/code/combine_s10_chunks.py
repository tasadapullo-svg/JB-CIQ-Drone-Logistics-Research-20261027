from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve()
OUT = HERE.parents[1]
CHUNKS = [OUT / "chunks" / f"C{i}" / "data" for i in range(4)]


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def paired_statistics(scenarios):
    modes = ["M1_DJI", "M1_WING", "M2_DJI", "M2_WING"]
    metrics = ["on_time_rate_all_orders", "vehicle_km", "fuel_litres", "grid_input_kwh",
               "operational_energy_ghg_kg_scenario", "operating_cost_MYR_partial"]
    rows, rng = [], np.random.default_rng(20261030)
    for mode in modes:
        for metric in metrics:
            a = scenarios[scenarios["mode"] == mode].set_index(["date_local", "scenario_seed"])[metric]
            b = scenarios[scenarios["mode"] == "M0_PETROL"].set_index(["date_local", "scenario_seed"])[metric]
            diff = (a - b).dropna()
            seed = diff.reset_index().groupby("scenario_seed")[metric].mean().to_numpy()
            boots = np.array([rng.choice(seed, len(seed), replace=True).mean() for _ in range(10000)])
            # Sign-flip randomization p-value on 30 seed-cluster means; deterministic Monte Carlo.
            signs = rng.choice([-1, 1], size=(20000, len(seed)))
            exceed = int((np.abs((signs * seed).mean(axis=1)) >= abs(seed.mean())).sum())
            p = float((exceed + 1) / (len(signs) + 1))
            rows.append({"mode_vs_m0": mode, "metric": metric, "paired_scenarios": len(diff),
                         "seed_clusters": len(seed), "mean_difference_per_scenario": float(diff.mean()),
                         "mean_difference_per_seed_cluster": float(seed.mean()),
                         "ci95_low": float(np.quantile(boots, .025)), "ci95_high": float(np.quantile(boots, .975)),
                         "randomization_p_unadjusted": p,
                         "inference": "SEED_CLUSTER_BOOTSTRAP_AND_SIGN_FLIP_CONDITIONAL_NOT_CAUSAL"})
    result = pd.DataFrame(rows)
    # Holm within each metric across the four mode-vs-M0 comparisons.
    result["holm_p"] = np.nan
    for metric, idx in result.groupby("metric").groups.items():
        indices = list(idx)
        ordered = sorted(indices, key=lambda i: result.loc[i, "randomization_p_unadjusted"])
        adjusted, running = {}, 0.0
        m = len(ordered)
        for rank, i in enumerate(ordered):
            value = min(1.0, (m - rank) * result.loc[i, "randomization_p_unadjusted"])
            running = max(running, value)
            adjusted[i] = running
        for i, value in adjusted.items():
            result.loc[i, "holm_p"] = value
    return result


def main():
    for folder in CHUNKS:
        if not folder.is_dir():
            raise FileNotFoundError(folder)
    orders = pd.concat([pd.read_parquet(p / "S10_MODE_ORDER_RESULTS.parquet") for p in CHUNKS], ignore_index=True)
    scenarios = pd.concat([pd.read_csv(p / "S10_MODE_SCENARIO_SUMMARY.csv") for p in CHUNKS], ignore_index=True)
    legs = pd.concat([pd.read_parquet(p / "S10_GROUND_PHYSICAL_LEGS.parquet") for p in CHUNKS], ignore_index=True)
    flights = pd.concat([pd.read_parquet(p / "S10_UAV_SCHEDULED_FLIGHTS.parquet") for p in CHUNKS], ignore_index=True)
    key = ["mode", "date_local", "scenario_seed", "task_id"]
    scenario_key = ["mode", "date_local", "scenario_seed"]
    qa = {
        "mode_order_rows": len(orders), "expected_mode_order_rows": 413100,
        "unique_mode_order_keys": int(orders[key].drop_duplicates().shape[0]),
        "duplicate_mode_order_keys": int(orders.duplicated(key).sum()),
        "mode_scenario_rows": len(scenarios), "expected_mode_scenario_rows": 22950,
        "unique_mode_scenario_keys": int(scenarios[scenario_key].drop_duplicates().shape[0]),
        "duplicate_mode_scenario_keys": int(scenarios.duplicated(scenario_key).sum()),
        "orders_per_mode": orders.groupby("mode").size().to_dict(),
        "orders_per_mode_scenario_min": int(orders.groupby(scenario_key).size().min()),
        "orders_per_mode_scenario_max": int(orders.groupby(scenario_key).size().max()),
        "completed_per_mode": orders.groupby("mode").status.apply(lambda x: int((x == "COMPLETED").sum())).to_dict(),
        "ground_physical_legs": len(legs),
        "ground_leg_duplicate_keys": int(legs.duplicated(["mode", "date_local", "scenario_seed", "physical_leg_id"]).sum()),
        "uav_scheduled_flights": len(flights), "flight_duplicate_ids": int(flights.flight_id.duplicated().sum()),
        "negative_ground_distance": int((legs.road_distance_km < 0).sum()),
        "negative_flight_energy": int((flights.grid_input_kwh < 0).sum()),
    }
    qa["all_tasks_preserved"] = (qa["mode_order_rows"] == 413100 and qa["unique_mode_order_keys"] == 413100
                                  and qa["mode_scenario_rows"] == 22950 and qa["unique_mode_scenario_keys"] == 22950
                                  and qa["orders_per_mode_scenario_min"] == 18 and qa["orders_per_mode_scenario_max"] == 18)
    qa["physical_accounting_pass"] = (qa["ground_leg_duplicate_keys"] == 0 and qa["flight_duplicate_ids"] == 0
                                       and qa["negative_ground_distance"] == 0 and qa["negative_flight_energy"] == 0)
    if not qa["all_tasks_preserved"] or not qa["physical_accounting_pass"]:
        raise RuntimeError(qa)

    orders.to_parquet(OUT / "data" / "S10_MODE_ORDER_RESULTS.parquet", index=False)
    orders.to_csv(OUT / "data" / "S10_MODE_ORDER_RESULTS.csv.gz", index=False, compression="gzip")
    scenarios.to_csv(OUT / "data" / "S10_MODE_SCENARIO_SUMMARY.csv", index=False, encoding="utf-8-sig")
    legs.to_parquet(OUT / "data" / "S10_GROUND_PHYSICAL_LEGS.parquet", index=False)
    flights.to_parquet(OUT / "data" / "S10_UAV_SCHEDULED_FLIGHTS.parquet", index=False)
    paired = paired_statistics(scenarios)
    paired.to_csv(OUT / "data" / "S10_PAIRED_STATISTICS.csv", index=False, encoding="utf-8-sig")
    seed = scenarios.groupby(["mode", "scenario_seed"], as_index=False).agg(
        orders=("orders", "sum"), completed=("completed", "sum"), on_time=("on_time", "sum"),
        vehicle_km=("vehicle_km", "sum"), fuel_litres=("fuel_litres", "sum"),
        grid_input_kwh=("grid_input_kwh", "sum"),
        operational_energy_ghg_kg_scenario=("operational_energy_ghg_kg_scenario", "sum"),
        operating_cost_MYR_partial=("operating_cost_MYR_partial", "sum"))
    seed.to_csv(OUT / "data" / "S10_SEED_LEVEL_FIVE_MONTH_TOTALS.csv", index=False, encoding="utf-8-sig")
    summary = scenarios.groupby("mode", as_index=False).agg(
        scenarios=("scenario_seed", "size"), orders=("orders", "sum"), completed=("completed", "sum"),
        on_time=("on_time", "sum"), vehicle_km=("vehicle_km", "sum"), fuel_litres=("fuel_litres", "sum"),
        ttw_co2_kg=("ttw_co2_kg", "sum"), grid_input_kwh=("grid_input_kwh", "sum"),
        grid_ghg_kgco2e=("grid_ghg_kgco2e", "sum"),
        operational_energy_ghg_kg_scenario=("operational_energy_ghg_kg_scenario", "sum"),
        operating_cost_MYR_partial=("operating_cost_MYR_partial", "sum"), uav_flights=("uav_flights", "sum"))
    summary["completion_rate"] = summary.completed / summary.orders
    summary["on_time_rate_all_orders"] = summary.on_time / summary.orders
    summary.to_csv(OUT / "data" / "S10_MODE_SUMMARY.csv", index=False, encoding="utf-8-sig")
    gates = {"S10_PREFLIGHT": "PASS", "S10_FULL_RUN": "PASS_CONDITIONAL",
             "S10_SCI_CARBON_CLAIM": "HOLD",
             "reason": "airspace/site approval, Wingcopter task energy, symmetric WTW/LCA and complete costs are unverified"}
    write_json(OUT / "qa" / "S10_INVARIANTS.json", qa)
    write_json(OUT / "qa" / "S10_GATES.json", gates)
    full = {"gates": gates, "qa": qa, "mode_summary": summary.to_dict("records"),
            "statistics": "date+seed paired; bootstrap and sign-flip clustered by 30 seeds; Holm within metric",
            "m1_definition": "directed fixed launch-node, one UAV queue per conditional station, three-vehicle fallback",
            "m2_definition": "three vehicle-mounted UAVs; physical vehicle launch access and same-point recovery wait",
            "boundaries": "petrol TTW + provisional grid operational GHG; not WTW/LCA; partial OPEX"}
    write_json(OUT / "data" / "S10_SUMMARY.json", full)
    report = "# S10 五模式条件性联合实验（全量）\n\n```text\n" + summary.to_string(index=False) + "\n```\n" + \
        "\n\n共22,950个模式场景、413,100条模式订单，分母与唯一键全部通过。" \
        "M1/M2结果属于条件性技术情景；排放为汽油TTW与临时电网运营因子的组合，不是WTW/LCA。" \
        "Wingcopter任务能耗、空域/场地许可、资本与电池折旧未验证，因此显著低碳主张保持HOLD。\n"
    (OUT / "reports" / "S10_SCI_AUDIT_REPORT_CN.md").write_text(report, encoding="utf-8")
    print(json.dumps(full, ensure_ascii=False))


if __name__ == "__main__":
    main()
