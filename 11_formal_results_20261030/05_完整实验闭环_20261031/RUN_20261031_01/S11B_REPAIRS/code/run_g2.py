from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
QA = BASE / "qa"


def mean_ci(x, seed=20261031, reps=20000):
    x = np.asarray(pd.Series(x).dropna(), dtype=float)
    if not len(x):
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    means = rng.choice(x, size=(reps, len(x)), replace=True).mean(axis=1)
    return float(x.mean()), float(np.quantile(means, .025)), float(np.quantile(means, .975))


s = pd.read_csv(DATA / "G1_SCENARIO_SUMMARY.csv")
o = pd.read_parquet(DATA / "G2_ORDER_SERVICE_STATUS.parquet")
l = pd.read_parquet(DATA / "G1_GROUND_LEG_LEDGER.parquet")
f = pd.read_parquet(DATA / "G1_FLIGHT_LEDGER.parquet")
soc = pd.read_parquet(DATA / "G1_SOC_LEDGER.parquet")

agg = s.groupby(["spatial_scenario", "mode", "scenario_seed"], as_index=False).agg(
    days=("date_local", "nunique"),
    orders=("orders", "sum"),
    completed=("completed", "sum"),
    on_time=("on_time", "sum"),
    vehicle_km=("vehicle_km", "sum"),
    fuel_litres=("fuel_litres", "sum"),
    grid_input_kwh=("grid_input_kwh", "sum"),
    mixed_boundary_operational_ghg_proxy_kg=("mixed_boundary_operational_ghg_proxy_kg", "sum"),
    partial_opex_MYR=("partial_opex_MYR", "sum"),
    driver_hours=("driver_hours", "sum"),
    uav_operator_hours=("uav_operator_hours", "sum"),
    uav_flights=("uav_flights", "sum"),
)
agg["completion_rate"] = agg["completed"] / agg["orders"]
agg["on_time_rate_all_orders"] = agg["on_time"] / agg["orders"]
delivery = o.groupby(["spatial_scenario", "mode", "scenario_seed"], as_index=False).agg(mean_delivery_minutes=("delivery_duration_minutes", "mean"), median_delivery_minutes=("delivery_duration_minutes", "median"))
agg = agg.merge(delivery, on=["spatial_scenario", "mode", "scenario_seed"], how="left", validate="one_to_one")
agg.to_csv(DATA / "G2_PER_SEED_153DAY.csv", index=False)

pairs = []
for spatial in sorted(agg["spatial_scenario"].unique()):
    for mode in ["M1_DJI", "M1_WING", "M2_DJI", "M2_WING"]:
        control = mode.split("_")[0] + "_NO_UAV"
        a = agg[(agg.spatial_scenario == spatial) & (agg["mode"] == mode)]
        b = agg[(agg.spatial_scenario == spatial) & (agg["mode"] == control)]
        z = a.merge(b, on=["spatial_scenario", "scenario_seed"], suffixes=("_uav", "_control"), validate="one_to_one")
        for metric in ["completion_rate", "on_time_rate_all_orders", "mean_delivery_minutes", "vehicle_km", "fuel_litres", "grid_input_kwh", "mixed_boundary_operational_ghg_proxy_kg", "partial_opex_MYR", "driver_hours"]:
            delta = z[f"{metric}_uav"] - z[f"{metric}_control"]
            mean, lo, hi = mean_ci(delta)
            denom = z[f"{metric}_control"]
            pct = np.where(np.abs(denom) > 1e-12, delta / denom * 100, np.nan)
            pct_mean, pct_lo, pct_hi = mean_ci(pct)
            pairs.append({"spatial_scenario": spatial, "mode": mode, "control": control, "metric": metric, "n_seeds": len(z), "mean_uav": z[f"{metric}_uav"].mean(), "mean_control": z[f"{metric}_control"].mean(), "paired_delta_mean": mean, "paired_delta_ci95_low": lo, "paired_delta_ci95_high": hi, "paired_pct_mean": pct_mean, "paired_pct_ci95_low": pct_lo, "paired_pct_ci95_high": pct_hi, "inference_unit": "one 153-day replicate/seed"})
pair = pd.DataFrame(pairs)
pair.to_csv(DATA / "G2_MODE_PAIRING.csv", index=False)

be = pair[pair.metric == "partial_opex_MYR"].copy()
be["five_month_allowable_incremental_capex_MYR_mean"] = -be["paired_delta_mean"]
be["five_month_allowable_incremental_capex_MYR_ci95_low"] = -be["paired_delta_ci95_high"]
be["five_month_allowable_incremental_capex_MYR_ci95_high"] = -be["paired_delta_ci95_low"]
be["interpretation"] = "Per-replicate five-month operating-cost difference; seeds are uncertainty replicates and are not summed. Capital recovery/financing excluded."
be.to_csv(DATA / "G2_BREAK_EVEN_CORRECTED.csv", index=False)

fair = pair.copy()
fair["ablation"] = "UAV_ENABLED_VS_SHARED_NO_UAV_SAME_DISPATCH_KERNEL"
fair["causal_scope"] = "model-internal paired switch; not a real-world causal effect"
fair.to_csv(DATA / "G2_FAIRNESS_ABLATION.csv", index=False)

quality = agg.groupby(["spatial_scenario", "mode"], as_index=False).agg(
    seeds=("scenario_seed", "nunique"),
    mean_completion=("completion_rate", "mean"),
    mean_on_time=("on_time_rate_all_orders", "mean"),
    mean_ghg_proxy_kg=("mixed_boundary_operational_ghg_proxy_kg", "mean"),
    mean_partial_opex_MYR=("partial_opex_MYR", "mean"),
    mean_uav_flights=("uav_flights", "mean"),
)
quality["benchmark_scope"] = "full 30-seed corrected heuristic; exact-solver benchmark NOT_RUN"
quality.to_csv(DATA / "G2_MODEL_QUALITY_BENCHMARK.csv", index=False)

recon = {
    "gate": "G2",
    "status": "PASS_CONDITIONAL",
    "counts": {"per_seed_rows": len(agg), "pairing_rows": len(pair), "orders": len(o), "ground_legs": len(l), "flights": len(f), "soc_rows": len(soc)},
    "checks": {
        "30_seeds_per_mode_spatial": bool((agg.groupby(["spatial_scenario", "mode"]).size() == 30).all()),
        "2754_orders_per_seed_mode": bool((agg["orders"] == 2754).all()),
        "flight_soc_one_to_one": len(f) == len(soc) and set(f.flight_id) == set(soc.flight_id),
        "fuel_reconciles_from_km": bool(np.allclose(s.fuel_litres, s.vehicle_km * .1)),
        "ghg_reconciles": bool(np.allclose(s.mixed_boundary_operational_ghg_proxy_kg, s.fuel_litres * 2.2410927 + s.grid_input_kwh * .740)),
    },
    "limitations": ["No independently validated exact-solver benchmark for all 18-task scenes.", "Operational GHG is a mixed-boundary proxy, not lifecycle assessment.", "Break-even excludes capital recovery and financing."],
}
if not all(recon["checks"].values()):
    recon["status"] = "FAIL"
(QA / "G2_LEDGER_RECONCILIATION.json").write_text(json.dumps(recon, indent=2), encoding="utf-8")
print(json.dumps(recon, indent=2))
