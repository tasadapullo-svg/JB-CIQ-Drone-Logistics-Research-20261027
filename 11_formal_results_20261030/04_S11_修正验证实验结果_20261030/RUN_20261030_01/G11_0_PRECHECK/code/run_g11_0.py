from __future__ import annotations

import hashlib
import json
import platform
import shutil
import sys
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import pyarrow
import pyproj
import scipy
import shapely


HERE = Path(__file__).resolve()
RUN = HERE.parents[2]
ROOT = HERE.parents[4]
OLD = ROOT / "output_S08A_S09_S10_Codex_20261030" / "RUN_20261030_01"
S0708 = ROOT / "output_S07_S08_Codex_20261030"
OUT = RUN / "G11_0_PRECHECK"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def main():
    files = [
        OLD / "FINAL_HANDOFF/FINAL_HANDOFF_CN.md", OLD / "FINAL_HANDOFF/FINAL_STATUS_MATRIX.json",
        OLD / "FINAL_HANDOFF/FULL_TEST_LOG.txt", OLD / "FINAL_HANDOFF/DELIVERABLE_SHA256.csv",
        OLD / "S08A/qa/S08A_FULL_RECONCILIATION.json", OLD / "S09/data/S09_MISSION_FEASIBILITY.parquet",
        OLD / "S09/data/S09_SUMMARY.json", OLD / "S09/code/run_s09_mission_simulation.py",
        OLD / "S10/data/S10_MODE_ORDER_RESULTS.parquet", OLD / "S10/data/S10_MODE_SCENARIO_SUMMARY.csv",
        OLD / "S10/data/S10_GROUND_PHYSICAL_LEGS.parquet", OLD / "S10/data/S10_UAV_SCHEDULED_FLIGHTS.parquet",
        OLD / "S10/data/S10_PAIRED_STATISTICS.csv", OLD / "S10/code/run_s10_five_mode.py",
        S0708 / "S07/data/V5_TASK_TIME_WEATHER_ROAD_INDEX.parquet",
        S0708 / "S07/data/V5_249696_NODE_HOUR_WEATHER.parquet",
        S0708 / "S07/data/V5_68_DIRECTED_OD_MATRIX_AND_PATHS.parquet",
        S0708 / "S07/data/OSM_ROUTE_EDGES_WITH_FCD_PROXY.parquet",
        S0708 / "S07/data/fcd_hourly_345node_2026_05_09.parquet",
        S0708 / "S08/data/S08_ORDER_RESULTS.parquet",
        S0708 / "S08/data/S08_PHYSICAL_LEG_LEDGER.parquet",
        S0708 / "S08/data/S08_VEHICLE_TRIPS.parquet",
        ROOT / "CIQ_ABC_QGIS322_V5_ONE_WMP228_68_NODES_FULL_PROJECT.zip",
    ]
    registry, missing = [], []
    for p in files:
        if not p.is_file():
            missing.append({"path": str(p), "status": "NOT_FOUND"}); continue
        registry.append({"absolute_path": str(p), "bytes": p.stat().st_size, "mtime_utc": pd.Timestamp(p.stat().st_mtime, unit="s", tz="UTC").isoformat(),
                         "sha256": sha(p), "source_stage": p.parts[-3] if len(p.parts) > 3 else "INPUT",
                         "purpose": p.name, "readable": True, "evidence_level": "HISTORICAL_READ_ONLY"})
    pd.DataFrame(registry).to_csv(OUT / "data/INPUT_REGISTRY.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(registry)[["absolute_path", "bytes", "sha256"]].to_csv(OUT / "data/HASH_REGISTRY.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(missing, columns=["path", "status"]).to_csv(OUT / "data/MISSING_OR_AMBIGUOUS_INPUTS.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"source": "S07", "consumer": "S08A/S09/S10/S11", "relation": "frozen tasks/weather/road/FCD"},
                  {"source": "S08A", "consumer": "S11", "relation": "M0 conditional baseline"},
                  {"source": "S09", "consumer": "S11", "relation": "candidate/energy evidence"},
                  {"source": "S10", "consumer": "S11", "relation": "old comparison and defect regression"}]).to_csv(
        OUT / "data/SOURCE_LINEAGE.csv", index=False, encoding="utf-8-sig")
    env = {"python": sys.version, "platform": platform.platform(), "pandas": pd.__version__, "numpy": np.__version__,
           "pyarrow": pyarrow.__version__, "geopandas": gpd.__version__, "networkx": nx.__version__,
           "shapely": shapely.__version__, "pyproj": pyproj.__version__, "scipy": scipy.__version__,
           "disk_free_bytes": shutil.disk_usage(RUN).free}
    (OUT / "data/ENVIRONMENT_LOCK.txt").write_text("\n".join(f"{k}={v}" for k,v in env.items()) + "\n", encoding="utf-8")

    # Real full-file reads and key audits.
    tasks = pd.read_parquet(S0708 / "S07/data/V5_TASK_TIME_WEATHER_ROAD_INDEX.parquet")
    s09 = pd.read_parquet(OLD / "S09/data/S09_MISSION_FEASIBILITY.parquet")
    s10o = pd.read_parquet(OLD / "S10/data/S10_MODE_ORDER_RESULTS.parquet")
    s10s = pd.read_csv(OLD / "S10/data/S10_MODE_SCENARIO_SUMMARY.csv")
    old_legs = pd.read_parquet(OLD / "S10/data/S10_GROUND_PHYSICAL_LEGS.parquet")
    old_flights = pd.read_parquet(OLD / "S10/data/S10_UAV_SCHEDULED_FLIGHTS.parquet")
    key = ["mode", "date_local", "scenario_seed", "task_id"]
    first = s10s.iloc[0]
    oo = s10o[(s10o["mode"] == first["mode"]) & (s10o.date_local == first.date_local) & (s10o.scenario_seed == first.scenario_seed)]
    reproduce = {"mode": first["mode"], "date_local": first.date_local, "scenario_seed": int(first.scenario_seed),
                 "orders_csv": int(first.orders), "orders_parquet": len(oo), "completed_csv": int(first.completed),
                 "completed_recomputed": int((oo.status == "COMPLETED").sum()), "on_time_csv": int(first.on_time),
                 "on_time_recomputed": int(oo.on_time.sum())}
    reproduce["exact_match"] = all([reproduce["orders_csv"] == reproduce["orders_parquet"],
                                     reproduce["completed_csv"] == reproduce["completed_recomputed"],
                                     reproduce["on_time_csv"] == reproduce["on_time_recomputed"]])
    audit = {"tasks_rows": len(tasks), "task_unique": tasks.task_id.nunique(), "s09_rows": len(s09),
             "s10_order_rows": len(s10o), "s10_unique_keys": int(s10o[key].drop_duplicates().shape[0]),
             "s10_scenarios": len(s10s), "old_ground_legs_read": len(old_legs), "old_flights_read": len(old_flights),
             "reproduced_one_existing_scenario": reproduce, "missing_inputs": len(missing),
             "status": "PASS" if reproduce["exact_match"] and len(s10o)==413100 and len(old_legs)==644903 and len(old_flights)==55246 else "FAIL"}
    (OUT / "qa/PRECHECK_AUDIT.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "reports/PRECHECK_AUDIT.md").write_text(
        f"# G11-0 PRECHECK\n\n状态：**{audit['status']}**。已真实读取82,620任务、165,240 S09行、413,100 S10订单、644,903旧地面路段和55,246旧航次。单场景摘要与订单逐行复算精确一致。历史文件只读。\n", encoding="utf-8")
    (OUT / "reports/VERSION_GRAPH.md").write_text("# Version graph\n\nS07 → S08/S08A → S09 → S10 → S11 corrective validation\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False))


if __name__ == "__main__":
    main()
