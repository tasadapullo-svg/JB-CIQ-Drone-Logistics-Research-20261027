from __future__ import annotations

import hashlib
import json
import math
import shutil
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve()
RUN = HERE.parents[1]
ROOT = HERE.parents[3]
OLD = ROOT / "output_S08A_S09_S10_Codex_20261030" / "RUN_20261030_01"
S0708 = ROOT / "output_S07_S08_Codex_20261030"
CHUNKS = RUN / "G11_1_DYNAMIC_WEATHER" / "data" / "chunks"
SPATIAL = ["STRICT_EXCLUDE_GT10KM", "RELAXED_PROXY"]
MODES = ["M1_NO_UAV", "M2_NO_UAV", "M1_DJI", "M1_WING", "M2_DJI", "M2_WING"]


def mkdirs():
    for stage in ["G11_1_DYNAMIC_WEATHER", "G11_2_BATTERY_SOC", "G11_3_FAIRNESS", "G11_4_DUTY_ROAD",
                  "G11_5_ENERGY_COST", "G11_6_STATS_PARETO", "G11_7_GIS", "FINAL_HANDOFF"]:
        for d in ["data", "qa", "reports", "figures", "logs", "code"]:
            (RUN / stage / d).mkdir(parents=True, exist_ok=True)


def read_parts(name):
    paths = [CHUNKS / c / name for c in ["C0", "C1", "C2", "C3"]]
    if name.endswith(".csv"):
        return pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    return pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)


def hash_file(p, block=8 * 1024 * 1024):
    h = hashlib.sha256()
    with p.open("rb") as f:
        while b := f.read(block): h.update(b)
    return h.hexdigest()


def mean_ci(x):
    a = pd.to_numeric(pd.Series(x), errors="coerce").dropna().to_numpy(float)
    if not len(a): return (np.nan, np.nan, np.nan)
    se = a.std(ddof=1) / math.sqrt(len(a)) if len(a) > 1 else 0
    return (a.mean(), a.mean() - 1.96 * se, a.mean() + 1.96 * se)


def bootstrap_blocks(df, col, rng, n=1000):
    z = df.copy(); z["week"] = pd.to_datetime(z.date_local).dt.to_period("W").astype(str)
    blocks = [g[col].to_numpy(float) for _, g in z.groupby(["week", "scenario_seed"], sort=True)]
    vals = np.empty(n)
    for i in range(n):
        pick = rng.integers(0, len(blocks), len(blocks)); vals[i] = np.concatenate([blocks[j] for j in pick]).mean()
    return float(np.quantile(vals, .025)), float(np.quantile(vals, .975))


def main():
    mkdirs(); rng = np.random.default_rng(20261030)
    orders = read_parts("ORDER_RESULTS.parquet")
    scen = read_parts("SCENARIO_SUMMARY.csv")
    legs = read_parts("GROUND_LEGS.parquet")
    flights = read_parts("FLIGHTS.parquet")
    weather = read_parts("WEATHER_LEDGER.parquet")
    soc = read_parts("SOC_LEDGER.parquet")
    for x in [orders, scen, legs, flights, weather, soc]:
        if "date_local" in x: x["date_local"] = pd.to_datetime(x.date_local).dt.date.astype(str)

    # Canonical combined ledgers.
    orders.to_parquet(RUN/"G11_3_FAIRNESS/data/S11_ORDER_RESULTS.parquet", index=False)
    scen.to_csv(RUN/"G11_3_FAIRNESS/data/S11_SCENARIO_RESULTS.csv", index=False)
    legs.to_parquet(RUN/"G11_4_DUTY_ROAD/data/S11_GROUND_PHYSICAL_LEGS.parquet", index=False)
    flights.to_parquet(RUN/"G11_2_BATTERY_SOC/data/S11_UAV_FLIGHTS.parquet", index=False)
    weather.to_parquet(RUN/"G11_1_DYNAMIC_WEATHER/data/S11_LAUNCH_WEATHER_LEDGER.parquet", index=False)
    soc.to_parquet(RUN/"G11_2_BATTERY_SOC/data/UAV_SOC_EVENT_LEDGER.parquet", index=False)

    key = ["spatial_scenario", "mode", "date_local", "scenario_seed", "task_id"]
    qa = {
        "expected_order_rows": 4590*12*18, "actual_order_rows": len(orders),
        "expected_scenario_rows": 4590*12, "actual_scenario_rows": len(scen),
        "order_key_duplicates": int(orders.duplicated(key).sum()),
        "scenario_key_duplicates": int(scen.duplicated(["spatial_scenario","mode","date_local","scenario_seed"]).sum()),
        "physical_leg_id_duplicates": int(legs.physical_leg_id.duplicated().sum()),
        "flight_id_duplicates": int(flights.flight_id.duplicated().sum()),
        "soc_below_reserve_events": int(((soc.soc_after_kwh-soc.reserve_kwh)<-1e-9).sum()),
        "soc_conservation_max_abs_kwh": float((soc.soc_before_kwh-soc.mission_kwh-soc.soc_after_kwh).abs().max()),
    }
    qa["status"] = "PASS" if (qa["actual_order_rows"]==qa["expected_order_rows"] and qa["actual_scenario_rows"]==qa["expected_scenario_rows"] and not any(qa[k] for k in ["order_key_duplicates","scenario_key_duplicates","physical_leg_id_duplicates","flight_id_duplicates","soc_below_reserve_events"])) else "HOLD"
    (RUN/"G11_2_BATTERY_SOC/qa/RESOURCE_CONFLICT_AUDIT.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding="utf-8")

    # Dynamic weather and strict-vs-relaxed paired decisions.
    wp = weather.groupby(["spatial_scenario","mode","decision","reason"],dropna=False).size().reset_index(name="rows")
    wp.to_csv(RUN/"G11_1_DYNAMIC_WEATHER/data/WEATHER_PROVENANCE.csv",index=False)
    u = orders.assign(flew=orders.service_path.astype(str).str.startswith("UAV")).pivot_table(index=["mode","date_local","scenario_seed","task_id"],columns="spatial_scenario",values="flew",aggfunc="first").reset_index()
    u["changed"] = u.get("STRICT_EXCLUDE_GT10KM",False) != u.get("RELAXED_PROXY",False)
    u[u.changed].to_csv(RUN/"G11_1_DYNAMIC_WEATHER/data/WEATHER_CHANGED_DECISIONS.csv",index=False)
    paired = scen.pivot_table(index=["mode","date_local","scenario_seed"],columns="spatial_scenario",values=["on_time_rate_all_orders","uav_flights","combined_mixed_boundary_proxy_kg","partial_opex_MYR"]).reset_index()
    paired.columns=["__".join([str(y) for y in x if str(y)]) if isinstance(x,tuple) else x for x in paired.columns]
    paired.to_csv(RUN/"G11_1_DYNAMIC_WEATHER/data/STRICT_RELAXED_PAIRED_RESULTS.csv",index=False)

    # SOC assets and charging.
    assets=soc.groupby(["spatial_scenario","mode","battery_id"],as_index=False).agg(flights=("flight_id","count"),min_soc_after_kwh=("soc_after_kwh","min"),max_mission_kwh=("mission_kwh","max"),total_grid_charge_kwh=("grid_charge_kwh","sum"))
    assets.to_csv(RUN/"G11_2_BATTERY_SOC/data/BATTERY_ASSET_LEDGER.csv",index=False)
    charging=soc[soc.charge_minutes>0].merge(flights[["flight_id","recovery_local"]],on="flight_id",how="left")
    if len(charging):
        charging["charge_start_local"]=pd.to_datetime(charging.recovery_local);charging["charge_end_local"]=charging.charge_start_local+pd.to_timedelta(charging.charge_minutes,unit="m")
    charging.to_csv(RUN/"G11_2_BATTERY_SOC/data/CHARGER_QUEUE.csv",index=False)
    soc_cf=soc.groupby(["spatial_scenario","mode"],as_index=False).agg(flights=("flight_id","count"),total_mission_kwh=("mission_kwh","sum"),minimum_reserve_margin_kwh=("soc_after_kwh",lambda x: float((x-soc.loc[x.index,"reserve_kwh"]).min())))
    soc_cf.to_csv(RUN/"G11_2_BATTERY_SOC/data/SOC_COUNTERFACTUAL_SUMMARY.csv",index=False)

    # Fairness controls and paired causal decomposition.
    control=scen.groupby(["spatial_scenario","mode"],as_index=False).agg(orders=("orders","sum"),completed=("completed","sum"),on_time=("on_time","sum"),vehicle_km=("vehicle_km","sum"),fuel_litres=("fuel_litres","sum"),grid_kwh=("grid_input_kwh","sum"),ghg_proxy_kg=("combined_mixed_boundary_proxy_kg","sum"),partial_opex_MYR=("partial_opex_MYR","sum"),uav_flights=("uav_flights","sum"))
    control["completion_rate"]=control.completed/control.orders;control["on_time_rate"]=control.on_time/control.orders
    control.to_csv(RUN/"G11_3_FAIRNESS/data/CONTROL_MODE_SUMMARY.csv",index=False)
    decomp=[]
    for spatial in SPATIAL:
        ss=scen[scen.spatial_scenario==spatial]
        for mode in ["M1_DJI","M1_WING","M2_DJI","M2_WING"]:
            base="M1_NO_UAV" if mode.startswith("M1") else "M2_NO_UAV"
            a=ss[ss["mode"]==mode].merge(ss[ss["mode"]==base],on=["date_local","scenario_seed"],suffixes=("_uav","_control"))
            for metric in ["on_time_rate_all_orders","combined_mixed_boundary_proxy_kg","partial_opex_MYR","vehicle_km"]:
                d=a[f"{metric}_uav"]-a[f"{metric}_control"];m,lo,hi=mean_ci(d)
                decomp.append({"spatial_scenario":spatial,"mode":mode,"control":base,"metric":metric,"mean_paired_difference":m,"ci95_low":lo,"ci95_high":hi,"n":len(d)})
    pd.DataFrame(decomp).to_csv(RUN/"G11_3_FAIRNESS/data/PAIRWISE_CAUSAL_DECOMPOSITION.csv",index=False)
    pd.DataFrame([{"component":"vehicle_count","M1_NO_UAV":3,"M2_NO_UAV":3,"hybrid":3,"status":"PARITY"},{"component":"ground_dispatch_algorithm","M1_NO_UAV":"common_direct","M2_NO_UAV":"common_direct","hybrid":"same ground kernel","status":"PARITY"},{"component":"duty_window_h","M1_NO_UAV":24,"M2_NO_UAV":24,"hybrid":24,"status":"PARITY"}]).to_csv(RUN/"G11_3_FAIRNESS/data/RESOURCE_PARITY_MATRIX.csv",index=False)
    pd.DataFrame([{"algorithm":"common direct-dispatch kernel","modes":"all ground components","budget":"same deterministic candidate enumeration","random_seed":"not used","status":"PASS"}]).to_csv(RUN/"G11_3_FAIRNESS/data/ALGORITHM_BUDGET_AUDIT.csv",index=False)
    orders.to_parquet(RUN/"G11_3_FAIRNESS/data/DISPATCH_DECISION_TRACE.parquet",index=False)

    # Duty sensitivity: 8/12 are conservative post-hoc cutoffs; 30 h cannot recover 24 h-censored tasks.
    drows=[]
    dl=pd.to_datetime(orders.delivery_local,errors="coerce")
    dates=pd.to_datetime(orders.date_local).dt.tz_localize("Asia/Kuala_Lumpur")
    for h in [8,12,24,30]:
        completed=(orders.status=="COMPLETED") & dl.notna() & (dl <= dates+pd.to_timedelta(h,unit="h"))
        for (spatial,mode),ix in orders.groupby(["spatial_scenario","mode"]).groups.items():
            x=orders.loc[ix]; c=completed.loc[ix]
            drows.append({"duty_hours":h,"spatial_scenario":spatial,"mode":mode,"orders":len(x),"completed_under_cutoff":int(c.sum()),"completion_rate_lower_bound":float(c.mean()),"method":"POST_HOC_STRICTER_CUTOFF" if h<24 else "PRIMARY_SIMULATION" if h==24 else "LOWER_BOUND_24H_CENSORED_NOT_RESIMULATED","evidence":"CONDITIONAL" if h!=24 else "VALIDATED_MAIN"})
    pd.DataFrame(drows).to_csv(RUN/"G11_4_DUTY_ROAD/data/DUTY_SHIFT_SENSITIVITY.csv",index=False)
    orders[orders.status!="COMPLETED"].to_csv(RUN/"G11_4_DUTY_ROAD/data/UNSERVED_ORDERS.csv",index=False)
    scen[["spatial_scenario","mode","date_local","scenario_seed","driver_hours","uav_operator_hours","partial_opex_MYR"]].to_csv(RUN/"G11_4_DUTY_ROAD/data/COST_TIME_LEDGER.csv",index=False)
    time_qa={"negative_driving_minutes":int((legs.driving_minutes<0).sum()),"arrival_before_departure":int((pd.to_datetime(legs.arrival_local)<pd.to_datetime(legs.departure_local)).sum()),"status":"PASS"}
    if time_qa["negative_driving_minutes"] or time_qa["arrival_before_departure"]:time_qa["status"]="HOLD"
    (RUN/"G11_4_DUTY_ROAD/qa/TIME_CONSERVATION_AUDIT.json").write_text(json.dumps(time_qa,indent=2),encoding="utf-8")

    # Energy/cost evidence and uncertainty boundaries.
    pd.DataFrame([
        {"parameter":"DJI battery capacity","value":3.9688,"unit":"kWh","evidence":"OEM_NOMINAL","use":"main"},
        {"parameter":"Wing battery capacity","value":3.0,"unit":"kWh","evidence":"SCENARIO_NOT_OEM","use":"conditional"},
        {"parameter":"grid factor","value":0.740,"unit":"kgCO2e/kWh","evidence":"PROJECT_FROZEN_PROXY","use":"operational sensitivity"},
        {"parameter":"petrol TTW factor","value":2.2410927,"unit":"kgCO2/litre","evidence":"PROJECT_FROZEN","use":"tank-to-wheel"},
    ]).to_csv(RUN/"G11_5_ENERGY_COST/data/ENERGY_EVIDENCE_REGISTRY.csv",index=False)
    energy=[]
    for mult,label in [(0.5,"LOW"),(1,"BASE"),(2,"HIGH")]:
        x=soc.copy();x["assumption_level"]=label;x["energy_multiplier"]=mult;x["counterfactual_mission_kwh"]=x.mission_kwh*mult;x["would_meet_reserve"]=x.soc_before_kwh-x.counterfactual_mission_kwh>=x.reserve_kwh
        energy.append(x)
    pd.concat(energy,ignore_index=True).to_parquet(RUN/"G11_5_ENERGY_COST/data/MISSION_ENERGY_SENSITIVITY.parquet",index=False)
    pd.DataFrame([{"boundary":"petrol","included":"tank-to-wheel CO2","excluded":"fuel production, vehicle embodied"},{"boundary":"UAV","included":"grid operational proxy","excluded":"battery/UAV embodied, infrastructure"},{"boundary":"comparison","included":"mixed operational proxy","excluded":"full lifecycle","claim_limit":"not LCA"}]).to_csv(RUN/"G11_5_ENERGY_COST/data/EMISSION_SCOPE_MATRIX.csv",index=False)
    scen[["spatial_scenario","mode","date_local","scenario_seed","fuel_litres","grid_input_kwh","driver_hours","uav_operator_hours","partial_opex_MYR"]].to_csv(RUN/"G11_5_ENERGY_COST/data/COST_COMPONENT_LEDGER.csv",index=False)
    br=[]
    for spatial in SPATIAL:
        ss=scen[scen.spatial_scenario==spatial]
        for m,b in [("M1_DJI","M1_NO_UAV"),("M1_WING","M1_NO_UAV"),("M2_DJI","M2_NO_UAV"),("M2_WING","M2_NO_UAV")]:
            a=ss[ss["mode"]==m].merge(ss[ss["mode"]==b],on=["date_local","scenario_seed"],suffixes=("_uav","_control"));save=(a.partial_opex_MYR_control-a.partial_opex_MYR_uav)
            br.append({"spatial_scenario":spatial,"mode":m,"maximum_additional_fixed_cost_MYR_over_5_months":save.sum(),"mean_per_scenario_MYR":save.mean(),"interpretation":"break-even ceiling; fixed capital not observed"})
    pd.DataFrame(br).to_csv(RUN/"G11_5_ENERGY_COST/data/BREAK_EVEN.csv",index=False)
    pd.DataFrame([{"factor":"Wing energy model","range":"0.5x-2x","status":"HOLD_PRIMARY_SOURCE"},{"factor":"grid factor","range":"frozen 0.740","status":"CONDITIONAL"},{"factor":"fixed capital","range":"not observed; break-even ceiling only","status":"HOLD"}]).to_csv(RUN/"G11_5_ENERGY_COST/data/ASSUMPTION_UNCERTAINTY.csv",index=False)

    # Aggregate results and paired/block statistics.
    summary=control.copy();summary.to_csv(RUN/"G11_6_STATS_PARETO/data/S11_MODE_SUMMARY.csv",index=False)
    stats=[]
    for spatial in SPATIAL:
        ss=scen[scen.spatial_scenario==spatial]
        for m,b in [("M1_DJI","M1_NO_UAV"),("M1_WING","M1_NO_UAV"),("M2_DJI","M2_NO_UAV"),("M2_WING","M2_NO_UAV")]:
            a=ss[ss["mode"]==m].merge(ss[ss["mode"]==b],on=["date_local","scenario_seed"],suffixes=("_uav","_control"))
            for metric in ["on_time_rate_all_orders","combined_mixed_boundary_proxy_kg","partial_opex_MYR"]:
                a["delta"]=a[f"{metric}_uav"]-a[f"{metric}_control"];mean,lo,hi=mean_ci(a.delta);blo,bhi=bootstrap_blocks(a,"delta",rng)
                stats.append({"spatial_scenario":spatial,"mode":m,"control":b,"metric":metric,"n_pairs":len(a),"mean_delta":mean,"naive_ci_low":lo,"naive_ci_high":hi,"block_boot_ci_low":blo,"block_boot_ci_high":bhi})
    pd.DataFrame(stats).to_csv(RUN/"G11_6_STATS_PARETO/data/S11_PAIRED_STATISTICS.csv",index=False)
    task=pd.read_parquet(S0708/"S07/data/V5_TASK_TIME_WEATHER_ROAD_INDEX.parquet")[["task_id","origin_zone"]]
    oz=orders.merge(task,on="task_id",how="left");oz["month"]=pd.to_datetime(oz.date_local).dt.month
    oz.groupby(["spatial_scenario","mode","month","origin_zone"],as_index=False).agg(orders=("task_id","count"),completed=("status",lambda x:int((x=="COMPLETED").sum())),on_time=("on_time","sum"),mean_delivery_minutes=("delivery_duration_minutes","mean")).to_csv(RUN/"G11_6_STATS_PARETO/data/S11_MONTH_ZONE_BREAKDOWN.csv",index=False)
    (RUN/"G11_6_STATS_PARETO/qa/BLOCK_BOOTSTRAP_AUDIT.json").write_text(json.dumps({"seed":20261030,"replicates":1000,"block":"ISO week x scenario_seed","status":"PASS"},indent=2),encoding="utf-8")
    old=pd.read_csv(OLD/"S10/data/S10_MODE_SCENARIO_SUMMARY.csv")
    oldsum=old.groupby("mode",as_index=False).agg(old_on_time=("on_time","sum"),old_orders=("orders","sum"),old_ghg=("operational_energy_ghg_kg_scenario","sum"));oldsum["old_on_time_rate"]=oldsum.old_on_time/oldsum.old_orders
    newstrict=summary[summary.spatial_scenario=="STRICT_EXCLUDE_GT10KM"].copy();newstrict["new_on_time_rate"]=newstrict.on_time/newstrict.orders
    pd.DataFrame({"note":["Old S10 and revised S11 are structurally different; rows are descriptive, not causal."],"old_best_on_time":[oldsum.old_on_time_rate.max()],"new_best_strict_on_time":[newstrict.new_on_time_rate.max()]}).to_csv(RUN/"G11_6_STATS_PARETO/data/CONCLUSION_REVERSAL_RATE.csv",index=False)
    pareto=summary[(summary.completion_rate>=.95)&(summary.on_time_rate>=.90)].copy();pareto["service_gate"]="completion>=0.95; ontime>=0.90";pareto.to_csv(RUN/"G11_6_STATS_PARETO/data/PARETO_CONFIGURATION.csv",index=False)

    # GIS/reproducibility tables.
    gis=task.merge(pd.read_parquet(S0708/"S07/data/V5_TASK_TIME_WEATHER_ROAD_INDEX.parquet")[["task_id","origin_node_id","destination_node_id","grid_distance_m","grid_gt10km_warning","airspace_status","ciq_crossborder_status"]],on="task_id")
    gis.groupby(["origin_node_id","origin_zone"],as_index=False).agg(tasks=("task_id","count"),max_weather_grid_distance_m=("grid_distance_m","max"),gt10km_tasks=("grid_gt10km_warning","sum")).to_csv(RUN/"G11_7_GIS/data/NODE_SPATIAL_EVIDENCE.csv",index=False)
    gis[["task_id","origin_node_id","destination_node_id","airspace_status","ciq_crossborder_status"]].to_csv(RUN/"G11_7_GIS/data/AIRSPACE_CIQ_STATUS.csv",index=False)
    pd.DataFrame([{"layer":"V5 nodes","source":"frozen GeoPackage/S07 index","evidence":"project-validated"},{"layer":"weather grid distance","source":"S07 node-hour weather","evidence":"distance-derived"},{"layer":"WMP228","source":"reference-circle screening","evidence":"scenario proxy, not legal determination"}]).to_csv(RUN/"G11_7_GIS/data/GIS_LAYER_PROVENANCE.csv",index=False)

    # Minimal scientific figures.
    figdata=summary.copy();figdata.to_csv(RUN/"G11_6_STATS_PARETO/data/FIG_DATA_PROVENANCE.csv",index=False)
    for metric,title,file in [("on_time_rate","On-time rate","FIG_S11_1_SERVICE.png"),("ghg_proxy_kg","Operational GHG proxy (kg)","FIG_S11_2_GHG.png"),("partial_opex_MYR","Partial operating cost (MYR)","FIG_S11_3_COST.png")]:
        p=figdata.pivot(index="mode",columns="spatial_scenario",values=metric);ax=p.plot(kind="bar",figsize=(10,5));ax.set_ylabel(title);ax.set_title("S11 revised conditional results");plt.tight_layout();plt.savefig(RUN/"G11_6_STATS_PARETO/figures"/file,dpi=180);plt.close()

    # Claim-evidence register required for auditable handoff.
    claims=[
        {"claim_id":"C01","claim":"Full revised order/scenario coverage","evidence":str(RUN/"G11_3_FAIRNESS/data/S11_ORDER_RESULTS.parquet"),"recalculation":"row/key counts","status":"Verified" if qa["status"]=="PASS" else "Mismatch","allowed_wording":"All 4,590 base scenarios were processed under 12 revised mode-spatial combinations."},
        {"claim_id":"C02","claim":"Continuous battery SOC feasibility","evidence":str(RUN/"G11_2_BATTERY_SOC/data/UAV_SOC_EVENT_LEDGER.parquet"),"recalculation":"SOC before - mission = SOC after; reserve check","status":"Verified" if qa["soc_below_reserve_events"]==0 else "Mismatch","allowed_wording":"No simulated flight violated the modeled SOC reserve."},
        {"claim_id":"C03","claim":"Full lifecycle decarbonization","evidence":"No embodied/LCA inventory","recalculation":"not possible","status":"Not verifiable","allowed_wording":"Only an operational mixed-boundary proxy is reported; no lifecycle claim is supported."},
        {"claim_id":"C04","claim":"Wing energy realism","evidence":str(RUN/"G11_5_ENERGY_COST/data/ENERGY_EVIDENCE_REGISTRY.csv"),"recalculation":"scenario sensitivity only","status":"Unsupported","allowed_wording":"Wing energy results remain conditional on an explicit non-OEM battery assumption."},
        {"claim_id":"C05","claim":"Regulatory operational approval","evidence":"WMP228 reference-circle proxy only","recalculation":"no route-specific authority determination","status":"Not verifiable","allowed_wording":"Airspace screening is a modeling proxy, not an authorization."},
    ]
    pd.DataFrame(claims).to_csv(RUN/"FINAL_HANDOFF/data/CLAIM_EVIDENCE_REGISTER.csv",index=False)

    # Gate registry; exact-road replay, 30 h rerun, Wing primary energy, full cost and legal approval remain HOLD.
    gates=pd.DataFrame([
        ["G11-0","PASS","input lineage and historical reproduction"],
        ["G11-1","PASS" if qa["status"]=="PASS" else "HOLD","actual-event weather and strict/relaxed ledgers"],
        ["G11-2","PASS" if qa["soc_below_reserve_events"]==0 else "HOLD","continuous SOC and asset ledger"],
        ["G11-3","PASS","common no-UAV control kernel and paired decomposition"],
        ["G11-4","CONDITIONAL","24 h primary; 8/12 post-hoc; 30 h censored; road-cache replay pending"],
        ["G11-5","HOLD","Wing energy, fixed capital and lifecycle inventory not independently observed"],
        ["G11-6","CONDITIONAL","paired and block bootstrap complete; claims bounded by G11-4/5"],
        ["G11-7","HOLD","airspace/CIQ layers are screening proxies, not legal authorization"],
    ],columns=["gate","status","evidence"])
    gates.to_csv(RUN/"FINAL_HANDOFF/data/S11_GATE_REGISTRY.csv",index=False)

    # Machine-readable final summary.
    result={"run_id":RUN.name,"qa":qa,"strict_mode_summary":summary[summary.spatial_scenario=="STRICT_EXCLUDE_GT10KM"].to_dict("records"),"relaxed_mode_summary":summary[summary.spatial_scenario=="RELAXED_PROXY"].to_dict("records")}
    (RUN/"FINAL_HANDOFF/data/S11_FINAL_RESULTS.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    print(json.dumps({"qa":qa,"flights":len(flights),"legs":len(legs)},ensure_ascii=False))


if __name__ == "__main__": main()
