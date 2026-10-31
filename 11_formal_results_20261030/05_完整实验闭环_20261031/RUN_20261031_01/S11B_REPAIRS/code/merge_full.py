from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
CHUNKS = [
    BASE / "chunks" / "FULL_0000_1147",
    BASE / "chunks" / "FULL_1148_2295",
    BASE / "chunks" / "FULL_2296_3443",
    BASE / "chunks" / "FULL_3444_4589",
]
DATA = BASE / "data"
QA = BASE / "qa"
DATA.mkdir(exist_ok=True)
QA.mkdir(exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def merge_csv(name: str) -> pd.DataFrame:
    return pd.concat([pd.read_csv(p / name) for p in CHUNKS], ignore_index=True)


def merge_parquet(name: str) -> pd.DataFrame:
    return pd.concat([pd.read_parquet(p / name) for p in CHUNKS], ignore_index=True)


summary = merge_csv("SCENARIO_SUMMARY.csv")
orders = merge_parquet("ORDER_RESULTS.parquet")
legs = merge_parquet("GROUND_LEGS.parquet")
flights = merge_parquet("FLIGHTS.parquet")
weather = merge_parquet("WEATHER_LEDGER.parquet")
soc = merge_parquet("SOC_LEDGER.parquet")
events = merge_parquet("EVENT_CLOCK.parquet")

outputs = {
    "G1_SCENARIO_SUMMARY.csv": summary,
    "G2_ORDER_SERVICE_STATUS.parquet": orders,
    "G1_GROUND_LEG_LEDGER.parquet": legs,
    "G1_FLIGHT_LEDGER.parquet": flights,
    "G1_WEATHER_EVENT_LEDGER.parquet": weather,
    "G1_SOC_LEDGER.parquet": soc,
    "G1_EVENT_CLOCK_LEDGER.parquet": events,
}
for name, frame in outputs.items():
    path = DATA / name
    if name.endswith(".csv"):
        frame.to_csv(path, index=False)
    else:
        frame.to_parquet(path, index=False)

strict = summary[summary["spatial_scenario"] == "STRICT_EXCLUDE_GT10KM"]
returns = legs[legs["target_event"] == "MANDATORY_RETURN_DEPOT"].copy()
return_arrival = pd.to_datetime(returns["arrival_local"])
return_end = pd.to_datetime(returns["date_local"]).dt.tz_localize("Asia/Kuala_Lumpur") + pd.Timedelta(hours=24)
tests = {
    "scenario_summary_rows_55080": len(summary) == 55080,
    "strict_scenario_mode_rows_27540": len(strict) == 27540,
    "order_mode_rows_991440": len(orders) == 991440,
    "strict_order_mode_rows_495720": len(orders[orders["spatial_scenario"] == "STRICT_EXCLUDE_GT10KM"]) == 495720,
    "all_4590_scenarios": summary[["date_local", "scenario_seed"]].drop_duplicates().shape[0] == 4590,
    "all_82620_tasks": orders["task_id"].nunique() == 82620,
    "all_30_seeds": summary["scenario_seed"].nunique() == 30,
    "order_composite_unique": not orders.duplicated(["spatial_scenario", "mode", "date_local", "scenario_seed", "task_id"]).any(),
    "physical_leg_id_unique": not legs["physical_leg_id"].duplicated().any(),
    "flight_id_unique": not flights["flight_id"].duplicated().any(),
    "soc_reserve_respected": bool((soc["soc_after_kwh"] + 1e-12 >= soc["reserve_kwh"]).all()),
    "strict_weather_gt10_excluded": not weather.loc[weather["spatial_scenario"] == "STRICT_EXCLUDE_GT10KM", "grid_gt10km_warning"].astype(bool).any(),
    "four_weather_events_per_flight": len(weather) == 4 * len(flights),
    "all_return_arrivals_within_window": bool((return_arrival <= return_end).all()),
    "controls_orderwise_identical": True,
}
a = orders[orders["mode"] == "M1_NO_UAV"].sort_values(["spatial_scenario", "date_local", "scenario_seed", "task_id"])
b = orders[orders["mode"] == "M2_NO_UAV"].sort_values(["spatial_scenario", "date_local", "scenario_seed", "task_id"])
cols = ["task_id", "status", "delivery_local", "on_time", "service_path", "vehicle_id"]
try:
    pd.testing.assert_frame_equal(a[cols].reset_index(drop=True), b[cols].reset_index(drop=True))
except AssertionError:
    tests["controls_orderwise_identical"] = False

report = {
    "gate": "G1",
    "status": "PASS" if all(tests.values()) else "FAIL",
    "tests": tests,
    "counts": {"summary": len(summary), "orders": len(orders), "legs": len(legs), "flights": len(flights), "weather": len(weather), "soc": len(soc), "events": len(events)},
}
(QA / "G1_QA_RESULTS.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

manifest = []
for p in sorted(DATA.iterdir()):
    manifest.append({"file": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)})
pd.DataFrame(manifest).to_csv(QA / "G1_OUTPUT_MANIFEST.csv", index=False)
print(json.dumps(report, indent=2))
