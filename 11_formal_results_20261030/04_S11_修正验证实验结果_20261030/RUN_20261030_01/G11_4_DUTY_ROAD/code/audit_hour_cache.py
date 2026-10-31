from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


HERE=Path(__file__).resolve(); RUN=HERE.parents[2]; ROOT=HERE.parents[4]
S0708=ROOT/"output_S07_S08_Codex_20261030"


def main():
    spec=importlib.util.spec_from_file_location("s08",S0708/"S08/code/run_s08_petrol_m0.py")
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    od=pd.read_parquet(S0708/"S07/data/V5_68_DIRECTED_OD_MATRIX_AND_PATHS.parquet")
    edges=pd.read_parquet(S0708/"S07/data/OSM_ROUTE_EDGES_WITH_FCD_PROXY.parquet")
    fcd=pd.read_parquet(S0708/"S07/data/fcd_hourly_345node_2026_05_09.parquet")
    engine=mod.RouteEngine(od,edges,fcd)
    legs=pd.read_parquet(RUN/"G11_4_DUTY_ROAD/data/S11_GROUND_PHYSICAL_LEGS.parquet")
    sample=legs[legs.from_node.astype(str)!=legs.to_node.astype(str)].sample(n=min(3000,len(legs)),random_state=20261030)
    rows=[]
    for r in sample.itertuples(index=False):
        exact=engine.travel(str(r.from_node),str(r.to_node),pd.Timestamp(r.departure_local))
        recorded=float(r.driving_minutes); ex=float(exact["minutes"]); den=max(ex,1e-9)
        rows.append({"physical_leg_id":r.physical_leg_id,"from_node":r.from_node,"to_node":r.to_node,"departure_local":r.departure_local,"hour_cached_minutes":recorded,"exact_departure_minutes":ex,"absolute_error_minutes":abs(recorded-ex),"absolute_percent_error":abs(recorded-ex)/den*100})
    out=pd.DataFrame(rows);out.to_csv(RUN/"G11_4_DUTY_ROAD/data/ROAD_TIME_CACHE_ERROR.csv",index=False)
    mean=float(out.absolute_percent_error.mean());p95=float(out.absolute_percent_error.quantile(.95))
    qa={"sample_n":len(out),"seed":20261030,"mean_absolute_percent_error":mean,"p95_absolute_percent_error":p95,"acceptance":"mean<=5% and p95<=10%","status":"PASS" if mean<=5 and p95<=10 else "HOLD_FULL_EXACT_RERUN_REQUIRED"}
    (RUN/"G11_4_DUTY_ROAD/qa/ROAD_CACHE_GATE.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")
    print(json.dumps(qa))


if __name__=="__main__":main()
