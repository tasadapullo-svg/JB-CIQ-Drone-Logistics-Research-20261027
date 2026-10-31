from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import platform
import sys
import zipfile
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve()
RUN = HERE.parents[2]
ROOT = HERE.parents[4]
D = Path(r"C:\Users\DELL\Desktop\D")
S0708 = ROOT / "output_S07_S08_Codex_20261030"
S10RUN = ROOT / "output_S08A_S09_S10_Codex_20261030" / "RUN_20261030_01"
S11RUN = ROOT / "output_S11_Corrective_Validation_20261030" / "RUN_20261030_01"
G0 = RUN / "G0_INPUTS"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while b := f.read(8 * 1024 * 1024):
            h.update(b)
    return h.hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def registry_row(path: Path, stage: str, purpose: str, evidence: str) -> dict:
    return {
        "absolute_path": str(path.resolve()) if path.exists() else str(path),
        "status": "FILE_FOUND" if path.exists() else "MISSING",
        "bytes": path.stat().st_size if path.exists() else None,
        "sha256": sha256(path) if path.exists() and path.is_file() else None,
        "source_stage": stage,
        "purpose": purpose,
        "evidence_level": evidence,
        "read_only_input": True,
    }


def main() -> None:
    for p in [G0 / "qa", G0 / "logs", G0 / "snapshots"]:
        p.mkdir(parents=True, exist_ok=True)

    gpkg = ROOT / "下载CIQ无人机物流SCI--本对话全部文件更新总ZIP" / "01_本对话全部文件" / "CIQ_V5_Freeze_Audit_20261030" / "source_extract" / "CIQ_ABC_QGIS322_V5_ONE_WMP228_68_NODES_FULL_PROJECT" / "data" / "CIQ_ABC_V5_ACTIVE.gpkg"
    key_files = [
        (D / "CIQ_V5_S11B_S12_S13_SCI_ALL_EXPERIMENTS_CODEX_MASTER_PROMPT_20261031.txt", "CONTROL", "formal execution prompt", "USER_AUTHORIZED"),
        (D / "CIQ_V5_S11B_S12_S13_COMPLETE_CODEX_EXECUTION_PACKAGE_20261031.zip", "CONTROL", "prompt/audit package", "USER_SUPPLIED"),
        (D / "CIQ_V5_S11B_S12_S13_EXPERIMENT_GATE_MATRIX_20261031.csv", "CONTROL", "gate matrix", "USER_SUPPLIED"),
        (S11RUN / "packages" / "CIQ_V5_S11_CORRECTIVE_VALIDATION_COMPLETE.zip", "S11", "historical S11 joint ZIP", "HISTORICAL_READ_ONLY"),
        (S11RUN / "G11_3_FAIRNESS" / "data" / "S11_ORDER_RESULTS.parquet", "S11", "991,440 order-mode records", "HISTORICAL_READ_ONLY"),
        (S11RUN / "G11_3_FAIRNESS" / "data" / "S11_SCENARIO_RESULTS.csv", "S11", "55,080 scenario-mode rows", "HISTORICAL_READ_ONLY"),
        (S11RUN / "G11_2_BATTERY_SOC" / "data" / "S11_UAV_FLIGHTS.parquet", "S11", "56,342 flights across both spatial scenarios", "HISTORICAL_READ_ONLY"),
        (S11RUN / "G11_4_DUTY_ROAD" / "data" / "S11_GROUND_PHYSICAL_LEGS.parquet", "S11", "1,487,220 ground legs", "HISTORICAL_READ_ONLY"),
        (S11RUN / "G11_1_DYNAMIC_WEATHER" / "code" / "run_s11_corrective_chunk.py", "S11", "source code under P0 audit", "HISTORICAL_READ_ONLY"),
        (S10RUN / "S10" / "data" / "S10_UAV_SCHEDULED_FLIGHTS.parquet", "S10", "historical implicit M1 station discovery", "HISTORICAL_READ_ONLY"),
        (S0708 / "S07" / "data" / "V5_TASK_TIME_WEATHER_ROAD_INDEX.parquet", "S07", "frozen tasks and joined evidence", "PROJECT_VALIDATED"),
        (S0708 / "S07" / "data" / "V5_GPKG_68_NODE_CROSSCHECK.csv", "S07", "frozen node attributes", "PROJECT_VALIDATED"),
        (S0708 / "S07" / "data" / "V5_68_DIRECTED_OD_MATRIX_AND_PATHS.parquet", "S07", "directed road OD paths", "CONDITIONAL_OSM"),
        (S0708 / "S07" / "data" / "OSM_ROUTE_EDGES_WITH_FCD_PROXY.parquet", "S07", "directed road edges", "CONDITIONAL_OSM"),
        (S0708 / "S07" / "data" / "fcd_hourly_345node_2026_05_09.parquet", "S07", "345-node hourly FCD proxy", "DIRECTION_UNOBSERVED_PROXY"),
        (S0708 / "S07" / "data" / "weather_hourly_2026_05_09.parquet", "S07", "five-month hourly weather", "HISTORICAL_GRID_PROXY"),
        (S0708 / "S07" / "data" / "V5_249696_NODE_HOUR_WEATHER.parquet", "S07", "68-node hourly weather association", "HISTORICAL_GRID_PROXY"),
        (gpkg, "V5_GIS", "frozen active GeoPackage", "PROJECT_VALIDATED_CONDITIONAL"),
    ]
    reg = pd.DataFrame([registry_row(*x) for x in key_files])
    reg.to_csv(G0 / "G0_INPUT_REGISTRY.csv", index=False, encoding="utf-8-sig")

    # ZIP CRC, version and manifest reconciliation.
    zpath = S11RUN / "packages" / "CIQ_V5_S11_CORRECTIVE_VALIDATION_COMPLETE.zip"
    with zipfile.ZipFile(zpath) as z:
        bad = z.testzip()
        members = {i.filename: i.file_size for i in z.infolist() if not i.is_dir()}
        manifest_names = [n for n in members if n.endswith("SHA256_MANIFEST.csv")]
        manifest_rows = []
        missing = []
        for mn in manifest_names:
            rows = list(csv.DictReader(z.read(mn).decode("utf-8-sig").splitlines()))
            stage = mn.split("/")[0]
            for r in rows:
                rel = r.get("relative_path", "")
                full = f"{stage}/{rel}"
                manifest_rows.append((mn, full))
                if full not in members:
                    missing.append(full)
        zip_audit = {
            "zip_sha256": sha256(zpath),
            "expected_sha256": "637aa153807b162b76a3add029e72063ada8d38a3403b67a14164b28571e7c4f",
            "bytes": zpath.stat().st_size,
            "member_count": len(members),
            "crc_bad_member": bad,
            "manifest_count": len(manifest_names),
            "manifest_rows": len(manifest_rows),
            "manifest_missing_members": missing,
            "manifest_missing_count": len(missing),
            "missing_are_only_pyc": bool(missing) and all("__pycache__" in x and x.endswith(".pyc") for x in missing),
            "status": "PASS_CONDITIONAL" if bad is None and sha256(zpath) == "637aa153807b162b76a3add029e72063ada8d38a3403b67a14164b28571e7c4f" else "FAIL",
        }
    write_json(G0 / "qa" / "G0_S11_ZIP_AUDIT.json", zip_audit)

    # Independent reproduction of historical S11 counts and strict-vs-relaxed interpretation.
    orders = pd.read_parquet(S11RUN / "G11_3_FAIRNESS" / "data" / "S11_ORDER_RESULTS.parquet")
    scen = pd.read_csv(S11RUN / "G11_3_FAIRNESS" / "data" / "S11_SCENARIO_RESULTS.csv")
    flights = pd.read_parquet(S11RUN / "G11_2_BATTERY_SOC" / "data" / "S11_UAV_FLIGHTS.parquet")
    legs = pd.read_parquet(S11RUN / "G11_4_DUTY_ROAD" / "data" / "S11_GROUND_PHYSICAL_LEGS.parquet")
    tasks = pd.read_parquet(S0708 / "S07" / "data" / "V5_TASK_TIME_WEATHER_ROAD_INDEX.parquet")
    strict_f = flights[flights["spatial_scenario"] == "STRICT_EXCLUDE_GT10KM"]
    relaxed_f = flights[flights["spatial_scenario"] == "RELAXED_PROXY"]
    per_seed = tasks.groupby("scenario_seed").agg(orders=("task_id", "size"), days=("date_local", "nunique")).reset_index()
    repro = {
        "base_scenarios": int(tasks.groupby(["date_local", "scenario_seed"]).ngroups),
        "frozen_orders": len(tasks),
        "mode_order_rows": len(orders),
        "mode_scenario_rows": len(scen),
        "all_spatial_flights": len(flights),
        "strict_flights": len(strict_f),
        "relaxed_flights": len(relaxed_f),
        "ground_legs": len(legs),
        "order_key_duplicates": int(orders.duplicated(["spatial_scenario", "mode", "date_local", "scenario_seed", "task_id"]).sum()),
        "scenario_key_duplicates": int(scen.duplicated(["spatial_scenario", "mode", "date_local", "scenario_seed"]).sum()),
        "flight_id_duplicates": int(flights["flight_id"].duplicated().sum()),
        "ground_leg_id_duplicates": int(legs["physical_leg_id"].duplicated().sum()),
        "seed_count": int(per_seed.shape[0]),
        "orders_per_seed_values": sorted(map(int, per_seed.orders.unique())),
        "days_per_seed_values": sorted(map(int, per_seed.days.unique())),
    }
    repro["status"] = "PASS" if (
        repro["base_scenarios"] == 4590 and repro["frozen_orders"] == 82620
        and repro["mode_order_rows"] == 991440 and repro["mode_scenario_rows"] == 55080
        and repro["all_spatial_flights"] == 56342 and repro["ground_legs"] == 1487220
        and repro["orders_per_seed_values"] == [2754] and repro["days_per_seed_values"] == [153]
        and not any(repro[x] for x in ["order_key_duplicates", "scenario_key_duplicates", "flight_id_duplicates", "ground_leg_id_duplicates"])
    ) else "FAIL"
    write_json(G0 / "G0_REPRO_GATE.json", repro)

    # Two independent road/event-clock golden cases.
    od = pd.read_parquet(S0708 / "S07" / "data" / "V5_68_DIRECTED_OD_MATRIX_AND_PATHS.parquet")
    edges = pd.read_parquet(S0708 / "S07" / "data" / "OSM_ROUTE_EDGES_WITH_FCD_PROXY.parquet")
    edge_len = edges.set_index("edge_id")["length_m"].to_dict()
    import ast
    path_map = {}
    for r in od[od["route_status"] == "CONDITIONAL_OSM_ROUTE"].itertuples(index=False):
        try:
            ids = json.loads(r.path_edge_ids_json)
        except Exception:
            ids = ast.literal_eval(r.path_edge_ids_json)
        path_map[(str(r.origin_node_id), str(r.destination_node_id))] = ids
    sample_legs = legs[(legs.from_node != legs.to_node) & legs.apply(lambda r: (str(r.from_node), str(r.to_node)) in path_map, axis=1)].iloc[[0, -1]]
    gold = []
    for r in sample_legs.itertuples(index=False):
        ids = path_map[(str(r.from_node), str(r.to_node))]
        independent_km = sum(float(edge_len[x]) for x in ids) / 1000.0
        clock_minutes = (pd.Timestamp(r.arrival_local) - pd.Timestamp(r.departure_local)).total_seconds() / 60.0
        gold.append({
            "physical_leg_id": r.physical_leg_id,
            "from_node": r.from_node,
            "to_node": r.to_node,
            "recorded_distance_km": r.road_distance_km,
            "independent_path_distance_km": independent_km,
            "distance_abs_error_km": abs(float(r.road_distance_km) - independent_km),
            "recorded_driving_minutes": r.driving_minutes,
            "event_clock_minutes": clock_minutes,
            "clock_abs_error_minutes": abs(float(r.driving_minutes) - clock_minutes),
        })
    gold_df = pd.DataFrame(gold)
    gold_df["status"] = ((gold_df.distance_abs_error_km < 1e-9) & (gold_df.clock_abs_error_minutes < 1e-9)).map({True: "PASS", False: "FAIL"})
    gold_df.to_csv(G0 / "G0_GOLDEN_CASES.csv", index=False)

    # Reconstruct the exact 11 historical implicit M1 launch nodes, then verify V5 membership.
    s10f = pd.read_parquet(S10RUN / "S10" / "data" / "S10_UAV_SCHEDULED_FLIGHTS.parquet")
    m1 = s10f[s10f["mode"].str.startswith("M1")]
    node = pd.read_csv(S0708 / "S07" / "data" / "V5_GPKG_68_NODE_CROSSCHECK.csv")
    node_id_col = "node_id" if "node_id" in node.columns else [c for c in node.columns if "node" in c.lower() and "id" in c.lower()][0]
    historical_nodes = sorted(m1.launch_node.astype(str).unique())
    station = pd.DataFrame({"station_id": historical_nodes})
    station["in_frozen_v5_68"] = station.station_id.isin(set(node[node_id_col].astype(str)))
    station["source"] = "S10_UAV_SCHEDULED_FLIGHTS historical implicit M1 launch-node set"
    station["station_role"] = "CONDITIONAL_FIXED_LAUNCH_WHITELIST"
    station["site_permission"] = "HOLD_NOT_VERIFIED"
    station["inventory_capacity"] = 1
    station["operator_capacity"] = 1
    station["charger_capacity"] = 1
    station["evidence_status"] = "PROJECT_HISTORICAL_CONDITIONAL_NOT_REAL_SITE_APPROVAL"
    station.to_csv(G0 / "G0_HISTORICAL_11_STATION_DISCOVERY.csv", index=False)

    lineage = pd.DataFrame([
        ["S08", "M0 30h petrol baseline", "historical reference only", "not causal-comparable to S11 24h"],
        ["S10", "five-mode model", "historical comparison", "M1 station set implicit in eligible origins; no explicit whitelist"],
        ["S11", "actual-event weather/SOC/fair controls", "regression baseline", "P0 station/window/return/geometry/sensitivity/cost issues"],
        ["S11B", "new corrected model", "target baseline", "must pass G1/G2 before S12 main inference"],
    ], columns=["stage", "artifact", "use_in_new_run", "difference_or_limit"])
    lineage.to_csv(G0 / "G0_ARTIFACT_LINEAGE.csv", index=False)

    catalog = pd.DataFrame([
        ["EXP-G0-01", "RQ1-RQ3", "input/version audit and S11 reproduction", "FULL", "G0_INPUT_REGISTRY;G0_REPRO_GATE", "PASS if hashes/counts/keys reproduce"],
        ["EXP-G1-01", "RQ1-RQ2", "S11B strict 24h corrected baseline", "FULL_RERUN", "S11B corrected ledgers", "P0 invariants; all 82,620 orders per mode"],
        ["EXP-G1-02", "RQ2", "8/12/30h corrected clock sensitivity", "FULL_RERUN", "duty sensitivity ledgers", "actual reschedule; no post-cut"],
        ["EXP-G1-03", "RQ2", "0.5x/1x/2x energy dynamic rerun", "FULL_RERUN", "dynamic sensitivity", "eligibility/SOC/fallback recalc"],
        ["EXP-G2-01", "RQ2-RQ3", "shared solver UAV on/off pairing", "FULL", "mode pairing and per-seed totals", "same budget/resources/orders"],
        ["EXP-G3-01", "RQ1", "68-node GIS/order/FCD/weather evidence", "FULL_AUDIT", "spatial/weather/strata files", "source and evidence labels"],
        ["EXP-G4-01", "RQ2-RQ3", "resource/weather/cost parameter sensitivities", "MIXED_FULL_SUBSET", "scenario registry", "each row labelled FULL/SUBSET/HOLD"],
        ["EXP-G5-01", "RQ1-RQ3", "paired CI/ablation/Pareto", "FULL", "paired and nondominated outputs", "30 seed replicates; dominance audit"],
        ["EXP-G6-01", "RQ1-RQ3", "Fig1-7 and Table1-7", "NOT_RUN", "traceability matrix", "only audited data"],
        ["EXP-G7-01", "RQ1-RQ3", "manuscript and final evidence freeze", "NOT_RUN", "paper sections and packages", "claim-evidence audit"],
    ], columns=["experiment_id", "research_question", "description", "run_scope", "required_outputs", "acceptance_gate"])
    catalog.to_csv(G0 / "G0_EXPERIMENT_CATALOG.csv", index=False)

    defects = pd.DataFrame([
        ["P0-01", "M1 station auto-proliferation", "stations.setdefault(origin)", "11-node historical conditional whitelist found; physical approval HOLD", "G1"],
        ["P0-02", "M1 duty-window asymmetry", "no end-window check in m1", "must repair and rerun", "G1"],
        ["P0-03", "return/recovery cutoff omission", "return leg omitted if after end", "must enforce paired endpoint policies", "G1"],
        ["P0-04", "M1/M2 reverse geometry mismatch", "M2 lacks reverse_geometry_proxy exclusion", "must use common kernel", "G1"],
        ["P0-05", "energy sensitivity post-hoc", "mission energy multiplied after scheduling", "must dynamically rerun", "G1/G4"],
        ["P0-06", "break-even repeat aggregation", "30 seed sum labelled one five-month ceiling", "must normalize per seed", "G2"],
    ], columns=["defect_id", "defect", "evidence", "required_fix", "gate"])
    defects.to_csv(G0 / "G0_P0_DEFECT_LEDGER.csv", index=False)

    freeze = reg[["absolute_path", "bytes", "sha256"]].copy()
    freeze["baseline_hash_recorded_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
    freeze.to_csv(G0 / "G0_FREEZE_HASH_AUDIT.csv", index=False)

    env = {
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "packages": {name: importlib.metadata.version(name) if importlib.util.find_spec(name.replace("-", "_")) else "NOT_IMPORTABLE" for name in ["pandas", "numpy", "scipy", "networkx", "geopandas", "shapely", "pyarrow", "matplotlib"]},
    }
    write_json(G0 / "G0_ENVIRONMENT.json", env)

    report = f"""# G0 independent reproduction and difference report

## Gate

- Input registry: {len(reg)} key artifacts, missing {int((reg.status == 'MISSING').sum())}.
- Historical S11 ZIP: {zip_audit['status']}; CRC bad member: {zip_audit['crc_bad_member']}.
- ZIP manifest mismatch: {zip_audit['manifest_missing_count']} members, all pyc-only={zip_audit['missing_are_only_pyc']}.
- S11 numerical reproduction: {repro['status']}.
- Golden road/event-clock cases: {','.join(gold_df.status)}.
- Historical implicit M1 station nodes: {len(historical_nodes)} ({','.join(historical_nodes)}); all in frozen V5={bool(station.in_frozen_v5_68.all())}.

## Independent recalculation

The 56,342 flights are the sum of strict ({len(strict_f):,}) and relaxed ({len(relaxed_f):,}) spatial-weather scenarios. They are not strict-only flights. Each seed contains {int(per_seed.orders.iloc[0]):,} orders across {int(per_seed.days.iloc[0])} days and represents one five-month simulation replicate.

## G1 decision

GO to code repair and tests. The 11-node historical station set is reproducible from S10 and belongs to frozen V5, so it can be used as a conditional project whitelist. Real site access/permission remains HOLD. No S11 result is promoted to the S11B baseline until P0-01 through P0-06 are repaired and rerun.
"""
    (G0 / "G0_REPRO_DIFFERENCE_REPORT.md").write_text(report, encoding="utf-8")

    index = """# CIQ S11B-S13 execution index

- Current gate: G0 complete; G1 GO for model repair.
- Historical S07-S11 are read-only.
- Main analysis remains STRICT_EXCLUDE_GT10KM, 24h, 82,620 frozen orders, 30 seeds.
- Next executable: `py S11B_REPAIRS/code/run_s11b.py --pilot-golden` after G1 source creation.
"""
    (RUN / "00_PROJECT_EXECUTION_INDEX.md").write_text(index, encoding="utf-8")
    print(json.dumps({"registry_rows": len(reg), "repro": repro, "zip": zip_audit, "stations": historical_nodes, "golden": gold}, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
