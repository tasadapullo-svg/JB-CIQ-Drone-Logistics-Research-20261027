from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


RUN = Path(__file__).resolve().parents[1]
G2 = RUN / "S11B_REPAIRS" / "data"
OUT = RUN / "S12_EXPERIMENTS"

seed = pd.read_csv(G2 / "G2_PER_SEED_153DAY.csv")
pair = pd.read_csv(G2 / "G2_MODE_PAIRING.csv")
base_scene = pd.read_csv(G2 / "G1_SCENARIO_SUMMARY.csv")

strict = seed[seed.spatial_scenario == "STRICT_EXCLUDE_GT10KM"].copy()
config = strict.groupby("mode", as_index=False).agg(
    n_seeds=("scenario_seed", "nunique"),
    completion_rate=("completion_rate", "mean"),
    on_time_rate=("on_time_rate_all_orders", "mean"),
    mean_delivery_minutes=("mean_delivery_minutes", "mean"),
    operational_ghg_proxy_kg=("mixed_boundary_operational_ghg_proxy_kg", "mean"),
    partial_opex_MYR=("partial_opex_MYR", "mean"),
    vehicle_km=("vehicle_km", "mean"),
    grid_input_kwh=("grid_input_kwh", "mean"),
    uav_flights=("uav_flights", "mean"),
)
config = config[config["mode"] != "M2_NO_UAV"].copy()
config["mode"] = config["mode"].replace({"M1_NO_UAV":"M0_SHARED_NO_UAV"})
config["service_feasible"] = (config.completion_rate >= .95) & (config.on_time_rate >= .90)

objectives = ["mean_delivery_minutes", "operational_ghg_proxy_kg", "partial_opex_MYR"]
dominance = []
for a in config.itertuples(index=False):
    for b in config.itertuples(index=False):
        if a.mode == b.mode:
            continue
        av = np.array([getattr(a, x) for x in objectives])
        bv = np.array([getattr(b, x) for x in objectives])
        dom = bool(a.service_feasible and b.service_feasible and np.all(av <= bv) and np.any(av < bv))
        dominance.append({"candidate_a": a.mode, "candidate_b": b.mode, "a_dominates_b": dom, "a_service_feasible": a.service_feasible, "b_service_feasible": b.service_feasible, **{f"delta_a_minus_b_{x}": getattr(a, x)-getattr(b, x) for x in objectives}})
dom = pd.DataFrame(dominance)
dom.to_csv(OUT / "S12_C_PARETO_PAIRWISE_DOMINANCE.csv", index=False)
dominated = set(dom.loc[dom.a_dominates_b, "candidate_b"])
config["pareto_status"] = np.where(~config.service_feasible, "SERVICE_INFEASIBLE", np.where(config["mode"].isin(dominated), "DOMINATED", "NONDOMINATED_WITHIN_TESTED_SET"))
config["scope_note"] = "Nondominance applies only to the tested corrected configurations; it is not a global optimum proof."
config.to_csv(OUT / "S12_C_SERVICE_CONSTRAINED_PARETO.csv", index=False)

spatial = seed.pivot_table(index=["mode", "scenario_seed"], columns="spatial_scenario", values=["completion_rate", "on_time_rate_all_orders", "mixed_boundary_operational_ghg_proxy_kg", "partial_opex_MYR", "uav_flights"]).reset_index()
spatial.columns = ["_".join([str(y) for y in x if str(y)]) if isinstance(x, tuple) else x for x in spatial.columns]
spatial.to_csv(OUT / "S12_B_SPATIAL_STRICT_VS_RELAXED_PER_SEED.csv", index=False)

catalog = [
    {"experiment_id": "MAIN_STRICT_10KM_24H", "factor": "weather spatial audit", "level": "10km strict", "status": "FULL_RERUN", "scenarios": 4590, "note": "Primary preregistered analysis."},
    {"experiment_id": "RELAXED_PROXY_24H", "factor": "weather spatial audit", "level": "relaxed proxy", "status": "FULL_RERUN", "scenarios": 4590, "note": "Sensitivity only; not evidence of real-world flyability."},
    {"experiment_id": "ENERGY_LOW_0P8", "factor": "UAV mission energy", "level": "0.8x", "status": "PENDING_DISCOVERY", "scenarios": 0, "note": "Must be dynamically rerun."},
    {"experiment_id": "ENERGY_HIGH_1P2", "factor": "UAV mission energy", "level": "1.2x", "status": "PENDING_DISCOVERY", "scenarios": 0, "note": "Must be dynamically rerun."},
    {"experiment_id": "DUTY_8H", "factor": "duty window", "level": "8h", "status": "PENDING_DISCOVERY", "scenarios": 0, "note": "Dynamic rerun."},
    {"experiment_id": "DUTY_12H", "factor": "duty window", "level": "12h", "status": "PENDING_DISCOVERY", "scenarios": 0, "note": "Dynamic rerun."},
    {"experiment_id": "DUTY_30H", "factor": "duty window", "level": "30h", "status": "PENDING_DISCOVERY", "scenarios": 0, "note": "Diagnostic boundary; not primary."},
    {"experiment_id": "WEATHER_5_15_20_25KM", "factor": "weather distance thresholds", "level": "5/15/20/25km", "status": "NOT_RUN", "scenarios": 0, "note": "10km strict and unrestricted proxy completed; intermediate thresholds not computed."},
    {"experiment_id": "RESOURCE_GRID", "factor": "vehicles/UAVs/batteries/chargers", "level": "factorial", "status": "NOT_RUN", "scenarios": 0, "note": "Only the preregistered 3 vehicles, 11 M1 station assets, and 2 M2 batteries/vehicle were tested."},
    {"experiment_id": "EXACT_SOLVER_BENCHMARK", "factor": "algorithm", "level": "exact vs heuristic", "status": "NOT_RUN", "scenarios": 0, "note": "No independently validated exact solver was available."},
]
sens_dir = OUT / "sensitivity"
sensitivity_results=[]
for row in catalog:
    p = sens_dir / row["experiment_id"] / "SCENARIO_SUMMARY.csv"
    if p.exists():
        d = pd.read_csv(p)
        row["status"] = "FULL_RERUN" if d[["date_local", "scenario_seed"]].drop_duplicates().shape[0] == 4590 else "SUBSET_RERUN"
        row["scenarios"] = d[["date_local", "scenario_seed"]].drop_duplicates().shape[0]
        b=base_scene[base_scene.spatial_scenario=="STRICT_EXCLUDE_GT10KM"]
        z=d.merge(b,on=["spatial_scenario","mode","date_local","scenario_seed"],suffixes=("_sensitivity","_base"),validate="one_to_one")
        for mode,g in z.groupby("mode"):
            for metric in ["completion_rate","on_time_rate_all_orders","vehicle_km","grid_input_kwh","mixed_boundary_operational_ghg_proxy_kg","partial_opex_MYR","uav_flights"]:
                delta=g[f"{metric}_sensitivity"]-g[f"{metric}_base"]
                sensitivity_results.append({"experiment_id":row["experiment_id"],"status":row["status"],"scenarios":row["scenarios"],"mode":mode,"metric":metric,"sensitivity_mean":g[f"{metric}_sensitivity"].mean(),"matched_base_mean":g[f"{metric}_base"].mean(),"paired_scene_delta_mean":delta.mean(),"paired_scene_delta_p05":delta.quantile(.05),"paired_scene_delta_p95":delta.quantile(.95)})
pd.DataFrame(catalog).to_csv(OUT / "S12_B_SENSITIVITY_CATALOG.csv", index=False)
pd.DataFrame(sensitivity_results).to_csv(OUT / "S12_B_DYNAMIC_SENSITIVITY_RESULTS.csv", index=False)

ablation = pair.copy()
ablation["ablation_type"] = "ONE_FACTOR_UAV_ENABLED_VS_SHARED_CONTROL"
ablation["status"] = "FULL_RERUN"
ablation.to_csv(OUT / "S12_C_ABLATION_RESULTS.csv", index=False)

g4 = {
    "gate": "G4_S12_B",
    "status": "PASS_CONDITIONAL",
    "completed": [x["experiment_id"] for x in catalog if x["status"] in {"FULL_RERUN", "SUBSET_RERUN"}],
    "not_run_or_pending": [x["experiment_id"] for x in catalog if x["status"] not in {"FULL_RERUN", "SUBSET_RERUN"}],
    "claim_limit": "Only completed dynamic reruns may support sensitivity claims; relaxed weather proxy is not validation of flyability.",
}
(OUT / "G4_GATE.json").write_text(json.dumps(g4, indent=2), encoding="utf-8")
g5 = {
    "gate": "G5_S12_C",
    "status": "PASS_CONDITIONAL",
    "tested_configurations": len(config),
    "service_feasible": int(config.service_feasible.sum()),
    "nondominated": config.loc[config.pareto_status == "NONDOMINATED_WITHIN_TESTED_SET", "mode"].tolist(),
    "limitations": ["Pareto set is conditional on the small tested configuration set.", "No exact-solver benchmark.", "Paired uncertainty uses 30 seed-level 153-day replicates; it does not establish external validity."],
}
(OUT / "G5_GATE.json").write_text(json.dumps(g5, indent=2), encoding="utf-8")
print(json.dumps({"G4": g4, "G5": g5}, indent=2))
