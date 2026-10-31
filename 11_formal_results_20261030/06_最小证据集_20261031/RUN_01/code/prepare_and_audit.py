from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


HERE=Path(__file__).resolve(); RUN=HERE.parents[1]; ROOT=HERE.parents[3]
OLD=ROOT/"output_SCI_Complete_Experimental_Closure_20261031"/"RUN_20261031_01"
S07=ROOT/"output_S07_S08_Codex_20261030"/"S07"/"data"
GEN=ROOT/"01_全部历史文件原路径"/"CIQ_V5_S06_S07_Rebase_20261030"/"code"/"build_v5_rebase_and_synthetic_tasks.py"
PROTOCOL=ROOT/"01_全部历史文件原路径"/"CIQ_V5_S06_S07_Rebase_20261030"/"qa"/"V5_SYNTHETIC_TASK_DESIGN_PROTOCOL.json"
TASKS=S07/"V5_TASK_TIME_WEATHER_ROAD_INDEX.parquet"

def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
 return h.hexdigest()

inputs=[TASKS,GEN,PROTOCOL,OLD/"S11B_REPAIRS"/"data"/"PARAMS.yaml",OLD/"S11B_REPAIRS"/"code"/"run_s11b.py",OLD/"S11B_REPAIRS"/"data"/"G1_SCENARIO_SUMMARY.csv",OLD/"S11B_REPAIRS"/"data"/"G2_PER_SEED_153DAY.csv",OLD/"S11B_REPAIRS"/"data"/"G1_PARAMETER_EVIDENCE_MATRIX.csv"]
pd.DataFrame([{"absolute_path":str(p.resolve()),"bytes":p.stat().st_size,"sha256":sha(p)} for p in inputs]).to_csv(RUN/"work"/"INPUT_HASHES_BEFORE.csv",index=False)

t=pd.read_parquet(TASKS)
assert len(t)==82620 and t.task_id.nunique()==82620
t["date_local"]=t.date_local.astype(str); t["month"]=t.date_local.str[:7]
t["release_dt"]=pd.to_datetime(t.release_local); t["release_hour"]=t.release_dt.dt.hour

# Objective 30-date selection: within each month, rank daily stress using equal-weight
# standardized gust, rain, and inverse observed speed; take six fixed stress quantiles.
daily=t.groupby("date_local",as_index=False).agg(month=("month","first"),mean_gust=("wind_gusts_10m","mean"),mean_rain=("rain","mean"),mean_speed=("observed_speed_kmh_conditional","mean"))
selected=[]
for month,g in daily.groupby("month",sort=True):
 g=g.copy()
 for c in ["mean_gust","mean_rain","mean_speed"]:
  sd=g[c].std(ddof=0);g[c+"_z"]=(g[c]-g[c].mean())/(sd if sd else 1)
 g["stress_score"]=g.mean_gust_z+g.mean_rain_z-g.mean_speed_z
 g=g.sort_values(["stress_score","date_local"]).reset_index(drop=True)
 raw=np.linspace(0,len(g)-1,6).round().astype(int)
 pick=g.iloc[raw].copy();pick["selection_rank_quantile"]=[0,.2,.4,.6,.8,1.0];selected.append(pick)
dates=pd.concat(selected,ignore_index=True).sort_values("date_local")
assert len(dates)==30 and dates.date_local.nunique()==30 and (dates.groupby("month").size()==6).all()
dates.to_csv(RUN/"work"/"SELECTED_DATES.csv",index=False)
seeds=sorted(t.scenario_seed.unique())
scenarios=pd.MultiIndex.from_product([dates.date_local,seeds],names=["date_local","scenario_seed"]).to_frame(index=False)
scenarios=scenarios.merge(dates[["date_local","month","stress_score","selection_rank_quantile"]],on="date_local",validate="many_to_one")
assert len(scenarios)==900 and not scenarios.duplicated(["date_local","scenario_seed"]).any()
scenarios.to_csv(RUN/"work"/"SELECTED_SCENARIOS.csv",index=False)
scenarios[["date_local","scenario_seed"]].head(1).to_csv(RUN/"work"/"GOLDEN_SCENARIO.csv",index=False)

rows=[]
def add(item,stratum,value,unit,status,note="",source=TASKS): rows.append({"audit_item":item,"stratum":str(stratum),"value":value,"unit":unit,"source_path":str(Path(source).resolve()),"evidence_status":status,"note":note})
add("orders_total","ALL",len(t),"orders","Verified internally")
add("task_id_unique","ALL",t.task_id.nunique(),"IDs","Verified internally")
add("task_id_duplicates","ALL",int(t.task_id.duplicated().sum()),"rows","Verified internally")
g=t.groupby(["date_local","scenario_seed"]).size();add("scenarios","ALL",len(g),"date-seed scenes","Verified internally");add("orders_per_scene_min","ALL",int(g.min()),"orders","Verified internally");add("orders_per_scene_max","ALL",int(g.max()),"orders","Verified internally")
add("seed_count","ALL",t.scenario_seed.nunique(),"seeds","Verified internally");add("date_count","ALL",t.date_local.nunique(),"dates","Verified internally");add("date_min","ALL",t.date_local.min(),"date","Verified internally");add("date_max","ALL",t.date_local.max(),"date","Verified internally")
active=set(t.origin_node_id)|set(t.destination_node_id);add("V5_candidate_nodes","ALL",68,"nodes","Verified internally","Candidate inventory; not all receive orders",S07/"V5_GPKG_68_NODE_CROSSCHECK.csv");add("order_active_nodes","ALL",len(active),"nodes","Verified internally")
for c in ["origin_zone","destination_zone","month","release_hour","parcel_kg","deadline_minutes","demand_stratum","route_status","road_route_status"]:
 for k,v in t[c].value_counts(dropna=False).sort_index().items():add(c,k,int(v),"orders","Verified internally")
for c in ["parcel_kg","deadline_minutes","road_distance_km","freeflow_minutes"]:
 for q,v in t[c].quantile([0,.05,.25,.5,.75,.95,1]).items():add(c+"_quantile",q,float(v),c.split("_")[-1],"Verified internally")
for c in ["origin_node_id","destination_node_id"]:
 for k,v in t[c].value_counts().items():add(c+"_frequency",k,int(v),"orders","Verified internally")
od=t.groupby(["origin_node_id","destination_node_id"]).size();add("unique_directed_OD","ALL",len(od),"OD pairs","Verified internally");add("orders_in_repeated_OD","ALL",int(od[od>1].sum()),"orders","Verified internally");add("cross_zone_orders","ALL",int((t.origin_zone!=t.destination_zone).sum()),"orders","Verified internally")
per_zone=t.groupby(["date_local","scenario_seed","origin_zone"]).size();add("orders_per_scene_origin_zone_min","ALL",int(per_zone.min()),"orders","Verified internally");add("orders_per_scene_origin_zone_max","ALL",int(per_zone.max()),"orders","Verified internally")
pd.DataFrame(rows).to_csv(RUN/"SYNTHETIC_ORDER_AUDIT.csv",index=False)

param=[]
def p(group,name,base,unit,evidence,source,limitation=""):param.append({"parameter_group":group,"parameter":name,"baseline_or_rule":base,"unit":unit,"evidence_level":evidence,"source_path":str(Path(source).resolve()),"limitation":limitation})
p("petrol","distance fuel intensity",0.1,"L/km","SCENARIO_ASSUMPTION",OLD/"S11B_REPAIRS"/"data"/"PARAMS.yaml","Equivalent to 10 L/100 km; not vehicle-specific field measurement")
p("petrol","TTW CO2 factor",2.2410927,"kg CO2/L","FROZEN_INPUT",OLD/"S11B_REPAIRS"/"data"/"PARAMS.yaml","TTW operational factor; not WTW/LCA")
p("electricity","grid operational factor",0.740,"kg CO2e/kWh","FROZEN_INPUT",OLD/"S11B_REPAIRS"/"data"/"PARAMS.yaml","Scenario grid factor")
p("DJI","nominal battery",3.9688,"kWh","OEM_SPEC",OLD/"S11B_REPAIRS"/"data"/"PARAMS.yaml","Project OEM-labelled input; task energy remains modeled")
p("Wing","battery",3.0,"kWh","SCENARIO_ASSUMPTION",OLD/"S11B_REPAIRS"/"data"/"PARAMS.yaml","No verified task-level OEM energy evidence")
p("aircraft","SOC reserve",0.20,"fraction","SCENARIO_ASSUMPTION",OLD/"S11B_REPAIRS"/"data"/"PARAMS.yaml")
p("joint stress test","G petrol multiplier","0.8,1.0,1.2","multiplier","SCENARIO_ASSUMPTION",HERE,"Pre-registered stress range; not a measured physical interval")
p("joint stress test","D DJI mission-energy multiplier","0.8,1.0,1.2","multiplier","SCENARIO_ASSUMPTION",HERE,"Applied before qualification, SOC, dispatch and fallback")
p("joint stress test","W Wing mission-energy multiplier","0.8,1.0,1.2","multiplier","SCENARIO_ASSUMPTION",HERE,"Applied before qualification, SOC, dispatch and fallback")
p("demand","seeds","20261027..20261056","integer seeds","FROZEN_INPUT",PROTOCOL)
p("demand","dates","2026-05-01..2026-09-30","local dates","FROZEN_INPUT",PROTOCOL)
p("demand","orders per zone-day",6,"orders","SCENARIO_ASSUMPTION",GEN,"Balanced controlled design; not observed volume")
p("demand","within/cross-zone slots","5 within + 1 cross","orders per zone-day","SCENARIO_ASSUMPTION",GEN,"Explicit stress stratum")
p("demand","payload set","0.5,1,2.5,4.5,5,8","kg","SCENARIO_ASSUMPTION",PROTOCOL,"Not an observed parcel-weight distribution")
p("demand","deadline set","45,90,150","minutes","SCENARIO_ASSUMPTION",PROTOCOL,"Not observed service promises")
p("demand","destination selection","uniform among non-excluded nodes","rule","SCENARIO_ASSUMPTION",PROTOCOL,"No empirical demand weights")
p("demand","release minute","PRNG {0,15,30,45}","minutes","SCENARIO_ASSUMPTION",PROTOCOL)
pd.DataFrame(param).to_csv(RUN/"PARAMETER_AND_SOURCE_AUDIT.csv",index=False)

qa={"orders":len(t),"unique_task_ids":t.task_id.nunique(),"scenes":len(g),"orders_per_scene_min":int(g.min()),"orders_per_scene_max":int(g.max()),"selected_dates":len(dates),"selected_scenes":len(scenarios),"selected_seeds":scenarios.scenario_seed.nunique(),"months":scenarios.month.value_counts().sort_index().to_dict(),"selection_rule":"Within each month, equal-weight standardized daily mean gust + rain - FCD speed; six fixed stress-score quantiles 0,.2,.4,.6,.8,1; all 30 seeds for each date.","generator_found":GEN.exists(),"protocol_found":PROTOCOL.exists()}
(RUN/"work"/"PRECHECK.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")
print(json.dumps(qa,indent=2))
