from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


HERE=Path(__file__).resolve();RUN=HERE.parents[1];ROOT=HERE.parents[3]
OLD=ROOT/"output_SCI_Complete_Experimental_Closure_20261031"/"RUN_20261031_01"
FACTOR_FUEL=2.2410927;FACTOR_GRID=.740
configs=[]
for g in [.8,1.0,1.2]:
 for e in [.8,1.0,1.2]:configs.append((f"GRID_G{g:.1f}_E{e:.1f}",g,e,e))
configs += [("CORNER_G1.0_D0.8_W1.2",1,.8,1.2),("CORNER_G1.0_D1.2_W0.8",1,1.2,.8),("CORNER_G0.8_D0.8_W1.2",.8,.8,1.2),("CORNER_G1.2_D1.2_W0.8",1.2,1.2,.8)]
assert len(configs)==13 and len(set(configs))==13
pair_label={(0.8,0.8):"E08_E08",(1.,1.):"E10_E10",(1.2,1.2):"E12_E12",(.8,1.2):"D08_W12",(1.2,.8):"D12_W08"}
frames=[]
for cid,g,d,w in configs:
 x=pd.read_csv(RUN/"work"/pair_label[(d,w)]/"SCENARIO_SUMMARY.csv")
 x=x[x["mode"]!="M2_NO_UAV"].copy();x["mode"]=x["mode"].replace({"M1_NO_UAV":"M0"})
 assert len(x)==4500 and not x.duplicated(["date_local","scenario_seed","mode"]).any()
 x["config_id"]=cid;x["G"]=g;x["D"]=d;x["W"]=w;x["dispatch_pair_id"]=pair_label[(d,w)]
 oldfuel=x.fuel_litres.copy();x["fuel_litres"]=oldfuel*g;x["petrol_ttw_co2_kg"]=x.fuel_litres*FACTOR_FUEL;x["grid_operation_ghg_kg"]=x.grid_input_kwh*FACTOR_GRID;x["operational_ghg_proxy_kg"]=x.petrol_ttw_co2_kg+x.grid_operation_ghg_kg
 x["partial_opex_MYR"]=x.partial_opex_MYR-oldfuel*x.petrol_MYR_per_litre+x.fuel_litres*x.petrol_MYR_per_litre
 x["service_threshold_pass"]=(x.completion_rate>=.95)&(x.on_time_rate_all_orders>=.90)
 x["calculation_status"]=np.where(g==1,"DYNAMIC_DISPATCH_RERUN","DYNAMIC_ENERGY_RERUN_PLUS_FUEL_LEDGER_RECALC")
 frames.append(x)
scene=pd.concat(frames,ignore_index=True)
cols=["config_id","G","D","W","dispatch_pair_id","calculation_status","date_local","scenario_seed","mode","orders","completed","on_time","completion_rate","on_time_rate_all_orders","mean_delivery_minutes","vehicle_km","fuel_litres","petrol_ttw_co2_kg","grid_input_kwh","grid_operation_ghg_kg","operational_ghg_proxy_kg","partial_opex_MYR","driver_hours","uav_operator_hours","uav_flights","ground_completed","unserved","service_threshold_pass"]
scene=scene[cols].sort_values(["config_id","date_local","scenario_seed","mode"])
scene.to_csv(RUN/"JOINT_SENSITIVITY_SCENE_LEVEL.csv.gz",index=False,compression="gzip")

dates=sorted(scene.date_local.unique());seeds=sorted(scene.scenario_seed.unique());summary=[]
reps=5000;rng=np.random.default_rng(20261031)
date_counts=np.eye(len(dates),dtype=np.int16)[rng.integers(0,len(dates),(reps,len(dates)))].sum(axis=1)
seed_counts=np.eye(len(seeds),dtype=np.int16)[rng.integers(0,len(seeds),(reps,len(seeds)))].sum(axis=1)
def twoway_ci(z,value,dates,seeds):
 mat=z.pivot(index="date_local",columns="scenario_seed",values=value).reindex(index=dates,columns=seeds).to_numpy(float)
 assert mat.shape==(30,30) and np.isfinite(mat).all()
 vals=np.einsum("ri,ij,rj->r",date_counts,mat,seed_counts,optimize=True)/(len(dates)*len(seeds))
 return float(mat.mean()),float(np.quantile(vals,.025)),float(np.quantile(vals,.975))
for (cid,mode),z in scene.groupby(["config_id","mode"],sort=True):
 cfg=z.iloc[0];m0=scene[(scene.config_id==cid)&(scene["mode"]=="M0")][["date_local","scenario_seed","operational_ghg_proxy_kg","partial_opex_MYR","mean_delivery_minutes","on_time_rate_all_orders"]]
 j=z.merge(m0,on=["date_local","scenario_seed"],suffixes=("","_m0"),validate="one_to_one")
 for metric in ["operational_ghg_proxy_kg","partial_opex_MYR","mean_delivery_minutes"]:j[metric+"_pct_vs_m0"]=(j[metric]-j[metric+"_m0"])/j[metric+"_m0"]*100
 j["on_time_pp_vs_m0"]=(j.on_time_rate_all_orders-j.on_time_rate_all_orders_m0)*100
 effects={}
 for metric in ["operational_ghg_proxy_kg_pct_vs_m0","partial_opex_MYR_pct_vs_m0","mean_delivery_minutes_pct_vs_m0","on_time_pp_vs_m0"]:
  effects[metric]=twoway_ci(j,metric,dates,seeds)
 total_orders=z.orders.sum();completed=z.completed.sum();ontime=z.on_time.sum()
 row={"config_id":cid,"G":cfg.G,"D":cfg.D,"W":cfg.W,"mode":mode,"scenes":len(z),"orders":int(total_orders),"completion_rate":completed/total_orders,"on_time_rate_all_orders":ontime/total_orders,"mean_delivery_minutes":np.average(z.mean_delivery_minutes,weights=z.completed),"vehicle_km":z.vehicle_km.sum(),"fuel_litres":z.fuel_litres.sum(),"petrol_ttw_co2_kg":z.petrol_ttw_co2_kg.sum(),"grid_input_kwh":z.grid_input_kwh.sum(),"grid_operation_ghg_kg":z.grid_operation_ghg_kg.sum(),"operational_ghg_proxy_kg":z.operational_ghg_proxy_kg.sum(),"partial_opex_MYR":z.partial_opex_MYR.sum(),"uav_flights":int(z.uav_flights.sum()),"ground_completed":int(z.ground_completed.sum()),"unserved":int(z.unserved.sum()),"service_threshold_pass":bool((completed/total_orders>=.95)&(ontime/total_orders>=.90))}
 for metric,(mean,lo,hi) in effects.items():row[metric]=mean;row[metric+"_ci95_low"]=lo;row[metric+"_ci95_high"]=hi
 summary.append(row)
summary=pd.DataFrame(summary)
for cid,g in summary.groupby("config_id"):
 feasible=g[g.service_threshold_pass];winner=feasible.sort_values(["operational_ghg_proxy_kg","partial_opex_MYR","mean_delivery_minutes"]).iloc[0]["mode"] if len(feasible) else "NONE"
 summary.loc[summary.config_id==cid,"lowest_ghg_service_feasible_mode"]=winner
summary.to_csv(RUN/"JOINT_SENSITIVITY_SUMMARY.csv",index=False)

# Exact 900-scene baseline reproduction against finalized S11B scenario output.
old=pd.read_csv(OLD/"S11B_REPAIRS"/"data"/"G1_SCENARIO_SUMMARY.csv")
old=old[(old.spatial_scenario=="STRICT_EXCLUDE_GT10KM") & (old["mode"]!="M2_NO_UAV")].copy();old["mode"]=old["mode"].replace({"M1_NO_UAV":"M0"})
base=scene[(scene.config_id=="GRID_G1.0_E1.0")].copy()
check=base.merge(old,on=["date_local","scenario_seed","mode"],suffixes=("_new","_old"),validate="one_to_one")
fields=["orders","completed","on_time","vehicle_km","grid_input_kwh","uav_flights"]
maxdiff={f:float(np.max(np.abs(check[f+"_new"]-check[f+"_old"]))) for f in fields}
baseline_ok=all(v<1e-9 for v in maxdiff.values())

# Fuel multiplier must not change routes/events within a fixed D/W pair.
route_ok=True
for (d,w),grp in scene.groupby(["D","W"]):
 for key,z in grp.groupby(["date_local","scenario_seed","mode"]):
  if z.vehicle_km.max()-z.vehicle_km.min()>1e-9 or z.uav_flights.max()-z.uav_flights.min()>0:route_ok=False

m2=summary[(summary["mode"]=="M2_WING")].copy();m2["ghg_reduction_pct"]=-m2.operational_ghg_proxy_kg_pct_vs_m0
base_reduction=float(m2.loc[m2.config_id=="GRID_G1.0_E1.0","ghg_reduction_pct"].iloc[0])
reversal=m2[m2.ghg_reduction_pct<=0].config_id.tolist();under1=m2[(m2.ghg_reduction_pct>0)&(m2.ghg_reduction_pct<1)].config_id.tolist()
base_winner=summary.loc[summary.config_id=="GRID_G1.0_E1.0","lowest_ghg_service_feasible_mode"].iloc[0]
rank_reversal=sorted(summary.loc[summary.lowest_ghg_service_feasible_mode!=base_winner,"config_id"].unique())
qa={"status":"PASS" if baseline_ok and route_ok and len(scene)==58500 else "FAIL","scene_rows":len(scene),"summary_rows":len(summary),"unique_configs":scene.config_id.nunique(),"unique_modes":scene["mode"].nunique(),"unique_scenes":scene[["date_local","scenario_seed"]].drop_duplicates().shape[0],"expected_orders_per_config_mode":16200,"baseline_reproduction_max_abs_diff":maxdiff,"baseline_reproduction_pass":baseline_ok,"fuel_ledger_recalc_route_invariance_pass":route_ok,"m2_wing_subset_baseline_reduction_pct":base_reduction,"m2_wing_nonpositive_reduction_configs":reversal,"m2_wing_reduction_under_1pct_configs":under1,"baseline_lowest_ghg_feasible_mode":base_winner,"ranking_reversal_configs":rank_reversal,"uncertainty":"two-way date and seed cluster bootstrap, 5000 replicates"}
(RUN/"work"/"JOINT_QA.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")
pd.DataFrame([{"config_id":cid,"G":g,"D":d,"W":w,"dispatch_pair_id":pair_label[(d,w)]} for cid,g,d,w in configs]).to_csv(RUN/"work"/"CONFIG_CATALOG.csv",index=False)
print(json.dumps(qa,indent=2))
