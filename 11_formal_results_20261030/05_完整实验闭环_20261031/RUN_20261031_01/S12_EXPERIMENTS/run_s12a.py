from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


RUN = Path(__file__).resolve().parents[1]
ROOT = RUN.parents[1]
S07 = ROOT / "output_S07_S08_Codex_20261030" / "S07" / "data"
G1 = RUN / "S11B_REPAIRS" / "data"
OUT = RUN / "S12_EXPERIMENTS" / "S12_A"
OUT.mkdir(parents=True, exist_ok=True)

tasks = pd.read_parquet(S07 / "V5_TASK_TIME_WEATHER_ROAD_INDEX.parquet")
weather = pd.read_parquet(S07 / "V5_249696_NODE_HOUR_WEATHER.parquet")
fcd = pd.read_parquet(S07 / "fcd_hourly_345node_2026_05_09.parquet")
orders = pd.read_parquet(G1 / "G2_ORDER_SERVICE_STATUS.parquet")
strict = orders[orders["spatial_scenario"] == "STRICT_EXCLUDE_GT10KM"].copy()

audit = {
    "frozen_tasks": len(tasks),
    "task_ids_unique": tasks.task_id.nunique(),
    "seeds": tasks.scenario_seed.nunique(),
    "days": tasks.date_local.nunique(),
    "task_active_nodes": len(set(tasks.origin_node_id) | set(tasks.destination_node_id)),
    "zones_origin": tasks.origin_zone.value_counts().to_dict(),
    "weather_node_hours": len(weather),
    "weather_nodes": weather.node_id.nunique(),
    "weather_hours": pd.to_datetime(weather.interval_start_utc, utc=True).nunique(),
    "weather_gt10km_rows": int(weather.grid_gt10km_warning.sum()),
    "weather_gt10km_nodes": int(weather.loc[weather.grid_gt10km_warning, "node_id"].nunique()),
    "fcd_rows": len(fcd),
    "fcd_nodes": fcd.node_id.nunique() if "node_id" in fcd else fcd.iloc[:, 0].nunique(),
    "fcd_hours": pd.to_datetime(fcd.timestamp_utc, utc=True).nunique() if "timestamp_utc" in fcd else None,
    "missing_observed_speed": int(tasks.observed_speed_kmh_conditional.isna().sum()),
    "nonpositive_observed_speed": int((tasks.observed_speed_kmh_conditional.fillna(np.inf) <= 0).sum()),
    "road_route_status": tasks.road_route_status.value_counts(dropna=False).to_dict(),
    "weather_event_status": tasks.weather_event_status.value_counts(dropna=False).to_dict(),
    "evidence_limits": [
        "Orders are frozen synthetic tasks and do not validate observed demand volumes.",
        "FCD direction is unobserved; speed is a directional-road proxy.",
        "The 10 km weather flag is an audit threshold, not a legal or physical flight boundary.",
        "WMP228 is retained as a reference-risk screen, not verified operational clearance.",
    ],
}
(OUT / "S12_A_DATA_AUDIT.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

meta = tasks[["task_id", "origin_zone", "destination_zone", "parcel_kg", "deadline_minutes", "release_local", "rain", "wind_gusts_10m", "observed_speed_kmh_conditional", "grid_distance_m"]].copy()
meta["release_local"] = pd.to_datetime(meta.release_local)
meta["month"] = meta.release_local.dt.month
meta["day_type"] = np.where(meta.release_local.dt.dayofweek < 5, "WEEKDAY", "WEEKEND")
meta["parcel_class"] = pd.cut(meta.parcel_kg, [-np.inf, 4.7, 30, np.inf], labels=["LE4.7KG", "4.7_TO_30KG", "GT30KG"])
meta["rain_class"] = pd.cut(meta.rain, [-np.inf, 0, .5, np.inf], labels=["DRY", "RAIN_LE0.5", "RAIN_GT0.5"])
meta["gust_class"] = pd.cut(meta.wind_gusts_10m, [-np.inf, 12, 18, np.inf], labels=["LE12MPS", "12_TO_18MPS", "GT18MPS"])
meta["traffic_class"] = pd.qcut(meta.observed_speed_kmh_conditional.rank(method="first"), 3, labels=["LOW_SPEED", "MID_SPEED", "HIGH_SPEED"])
joined = strict.merge(meta, on="task_id", how="left", validate="many_to_one")

frames = []
for dimension in ["origin_zone", "destination_zone", "month", "day_type", "parcel_class", "rain_class", "gust_class", "traffic_class"]:
    z = joined.groupby(["mode", dimension], observed=True, dropna=False).agg(
        n=("task_id", "size"), completed=("status", lambda x: int((x == "COMPLETED").sum())), on_time=("on_time", "sum"), mean_delivery_minutes=("delivery_duration_minutes", "mean")
    ).reset_index().rename(columns={dimension: "stratum"})
    z["dimension"] = dimension
    z["completion_rate"] = z.completed / z.n
    z["on_time_rate_all_orders"] = z.on_time / z.n
    frames.append(z)
pd.concat(frames, ignore_index=True).to_csv(OUT / "S12_A_STRATIFIED_SERVICE.csv", index=False)

node = pd.read_csv(S07 / "V5_GPKG_68_NODE_CROSSCHECK.csv")[["node_id","zone","longitude_E","latitude_N","analysis_role","launch_pad_operationally_approved","ground_gate_approved"]].rename(columns={"longitude_E":"lon","latitude_N":"lat"}).sort_values("node_id")
active=set(tasks.origin_node_id) | set(tasks.destination_node_id)
node["used_by_frozen_orders"] = node.node_id.isin(active)
node.to_csv(OUT / "S12_A_V5_68_NODE_REGISTRY.csv", index=False)

gate = {
    "gate": "G3_S12_A",
    "status": "PASS_CONDITIONAL",
    "checks": {
        "82620_frozen_tasks": len(tasks) == 82620,
        "30_seeds": tasks.scenario_seed.nunique() == 30,
        "153_days": tasks.date_local.nunique() == 153,
        "68_nodes": len(node) == 68,
        "249696_weather_links": len(weather) == 249696,
        "345_fcd_nodes": audit["fcd_nodes"] == 345,
        "3672_fcd_hours": audit["fcd_hours"] == 3672,
    },
    "hold": ["FCD direction not observed.", "Synthetic demand cannot establish real demand prevalence.", "No independent local weather-station validation.", "Station/landing permissions and WMP228 operational clearance not verified."],
}
if not all(gate["checks"].values()):
    gate["status"] = "FAIL"
(OUT / "G3_GATE.json").write_text(json.dumps(gate, indent=2), encoding="utf-8")
print(json.dumps(gate, indent=2))
