from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA, QA = BASE / "data", BASE / "qa"
qa = json.loads((QA / "G1_QA_RESULTS.json").read_text(encoding="utf-8"))

stations = ["A01","A02","A03","A09","A_N05","A_N07","B06","B07","C02","C04","C21"]
pd.DataFrame({"station_node_id":stations,"constraint":"EXPLICIT_FIXED_WHITELIST","permission_status":"HOLD_NOT_VERIFIED","source":"historical S10 implicit-launch discovery, frozen as conditional project whitelist"}).to_csv(DATA/"G1_FIXED_STATIONS.csv",index=False)

defects = [
    ("P0-01","Dynamic M1 station creation","Replaced by explicit 11-node whitelist","CLOSED"),
    ("P0-02","Asymmetric M1 duty clock","Vehicle, station, flight and operator events use explicit clocks","CLOSED"),
    ("P0-03","Return/recovery omission","Outbound, return launch, recovery and mandatory vehicle depot return enforced","CLOSED"),
    ("P0-04","M1/M2 geometry mismatch","Common directed mission catalog and reverse/WMP/cross-border kernel","CLOSED"),
    ("P0-05","Post-hoc energy sensitivity","Energy multiplier enters mission qualification and SOC before selection","CLOSED_CODE; SENSITIVITY_RUN_SEPARATELY"),
    ("P0-06","Break-even summed across seeds","Per-seed 153-day comparison; seeds not summed","CLOSED"),
]
pd.DataFrame(defects,columns=["defect_id","historical_issue","corrective_action","status"]).to_csv(DATA/"G1_DEFECT_LEDGER.csv",index=False)

src = BASE/"code"/"run_s11b.py"
version = {
    "version_id":"S11B_CORRECTED_20261031_01",
    "source_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
    "primary_scenario":"STRICT_EXCLUDE_GT10KM_24H",
    "qa_status":qa["status"],
    "fixed_station_count":11,
    "duty_window_hours":24,
    "vehicle_count":3,
    "m2_batteries_per_vehicle":2,
    "claim_scope":"conditional simulation",
}
(DATA/"G1_CORRECTED_MODEL_VERSION.json").write_text(json.dumps(version,indent=2),encoding="utf-8")

root = BASE.parents[2]
old_path = root/"output_S11_Corrective_Validation_20261030"/"RUN_20261030_01"/"G11_3_FAIRNESS"/"data"/"S11_SCENARIO_RESULTS.csv"
old = pd.read_csv(old_path)
new = pd.read_csv(DATA/"G1_SCENARIO_SUMMARY.csv")
old = old.rename(columns={"combined_mixed_boundary_proxy_kg":"mixed_boundary_operational_ghg_proxy_kg"})
metrics=["completion_rate","on_time_rate_all_orders","vehicle_km","grid_input_kwh","mixed_boundary_operational_ghg_proxy_kg","partial_opex_MYR","uav_flights"]
oa=old.groupby(["spatial_scenario","mode"])[metrics].mean().add_suffix("_historical").reset_index()
na=new.groupby(["spatial_scenario","mode"])[metrics].mean().add_suffix("_corrected").reset_index()
diff=oa.merge(na,on=["spatial_scenario","mode"],how="outer")
for m in metrics: diff[f"{m}_delta_corrected_minus_historical"]=diff[f"{m}_corrected"]-diff[f"{m}_historical"]
diff["attribution_warning"]="MULTI_FACTOR_CORRECTION; do not attribute the before-after difference to one defect"
diff.to_csv(DATA/"G1_BEFORE_AFTER_SCENE_DIFF.csv",index=False)

gate={"gate":"G1_S11B","status":qa["status"],"tests":qa["tests"],"commands":["run_s11b.py in four complete BOTH-spatial chunks","merge_full.py","run_tests.py (17/17 pilot tests, including cross-hour return-launch weather)"],"full_run":qa["counts"],"next_gate":"GO_G2" if qa["status"]=="PASS" else "NO_GO"}
(QA/"G1_GATE.json").write_text(json.dumps(gate,indent=2),encoding="utf-8")
print(json.dumps(gate,indent=2))
