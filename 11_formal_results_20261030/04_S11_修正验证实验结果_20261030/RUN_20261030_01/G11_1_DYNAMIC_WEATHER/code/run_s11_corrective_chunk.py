from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve()
RUN = HERE.parents[2]
ROOT = HERE.parents[4]
OLD = ROOT / "output_S08A_S09_S10_Codex_20261030" / "RUN_20261030_01"
S0708 = ROOT / "output_S07_S08_Codex_20261030"
DEPOTS = ["A01", "B06", "C02"]
PETROL_L_100KM = 10.0
PETROL_CO2_KG_L = 2.2410927
GRID_KG_KWH = 0.740
DRIVER_MYR_H = 15.0
UAV_OPERATOR_MYR_H = 15.0
MAINT_MYR_KM = 0.20
ELEC_MYR_KWH = 0.50
DUTY_HOURS = float(os.environ.get("S11_DUTY_HOURS", "24"))
RAIN_LIMIT = 0.5
SPATIAL_SCENARIOS = ["STRICT_EXCLUDE_GT10KM", "RELAXED_PROXY"]
MODELS = {
    "DJI": {"name": "DJI_FLYCART30", "cruise_mps": 15.0, "wind_limit": 12.0,
            "capacity_kwh": 3.9688, "reserve_fraction": 0.20, "charger_kw": 7.2,
            "capacity_evidence": "OEM_NOMINAL"},
    "WING": {"name": "WINGCOPTER198_CARGO", "cruise_mps": 25.0, "wind_limit": 18.0,
             "capacity_kwh": 3.0, "reserve_fraction": 0.20, "charger_kw": 2.0,
             "capacity_evidence": "SCENARIO_NOT_OEM"},
}


def load_s08():
    path = S0708 / "S08/code/run_s08_petrol_m0.py"
    spec = importlib.util.spec_from_file_location("s08_original", path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


class HourCache:
    def __init__(self, base): self.base, self.cache = base, {}
    def travel(self, a, b, t):
        hour = pd.Timestamp(t).floor("h"); key = (str(a), str(b), hour)
        if key not in self.cache: self.cache[key] = self.base.travel(a, b, hour)
        return self.cache[key]


def bearing(lon1, lat1, lon2, lat2):
    p1, p2 = math.radians(lat1), math.radians(lat2); dl = math.radians(lon2-lon1)
    y = math.sin(dl)*math.cos(p2); x = math.cos(p1)*math.sin(p2)-math.sin(p1)*math.cos(p2)*math.cos(dl)
    return (math.degrees(math.atan2(y, x))+360)%360


def headwind(speed, met_from, course):
    wind_to=(met_from+180)%360
    return -speed*math.cos(math.radians(wind_to-course))


def as_local(value):
    x = pd.Timestamp(value)
    return x.tz_localize("Asia/Kuala_Lumpur") if x.tzinfo is None else x.tz_convert("Asia/Kuala_Lumpur")


def weather_at(wmap, node, local_time):
    utc = pd.Timestamp(local_time).tz_convert("UTC").floor("h")
    return wmap.get((str(node), utc))


def flight_evaluation(task, f, spec, launch, spatial_scenario, wmap):
    distance=float(f.one_way_km); course=bearing(task.origin_lon,task.origin_lat,task.destination_lon,task.destination_lat)
    wo=weather_at(wmap,task.origin_node_id,launch)
    if wo is None: return {"ok":False,"reason":"WEATHER_MISSING","launch":launch}
    go=max(5.0,spec["cruise_mps"]-max(0.0,headwind(float(wo.wind_speed_10m),float(wo.wind_direction_10m),course)))
    out_min=distance*1000/go/60; delivery=launch+pd.Timedelta(minutes=2+out_min+2)
    return_launch=delivery+pd.Timedelta(minutes=5); wd=weather_at(wmap,task.destination_node_id,return_launch)
    if wd is None: return {"ok":False,"reason":"WEATHER_MISSING","launch":launch,"delivery":delivery}
    gb=max(5.0,spec["cruise_mps"]-max(0.0,headwind(float(wd.wind_speed_10m),float(wd.wind_direction_10m),(course+180)%360)))
    back_min=distance*1000/gb/60; recover=return_launch+pd.Timedelta(minutes=2+back_min+2)
    events=[("LAUNCH",task.origin_node_id,launch),("DELIVERY",task.destination_node_id,delivery),
            ("RETURN_LAUNCH",task.destination_node_id,return_launch),("RECOVERY",task.origin_node_id,recover)]
    weather=[]; missing=False
    for event,node,t in events:
        q=weather_at(wmap,node,t)
        if q is None: missing=True; continue
        weather.append({"event":event,"node_id":node,"event_local":t,"weather_hour_utc":pd.Timestamp(t).tz_convert("UTC").floor("h"),
                        "wind_speed_10m":float(q.wind_speed_10m),"wind_direction_10m":float(q.wind_direction_10m),
                        "wind_gusts_10m":float(q.wind_gusts_10m),"precipitation":float(q.precipitation),
                        "grid_distance_m":float(q.grid_distance_m),"grid_gt10km_warning":bool(q.grid_gt10km_warning)})
    maxgust=max((x["wind_gusts_10m"] for x in weather),default=np.nan); maxrain=max((x["precipitation"] for x in weather),default=np.nan)
    spatial_hold=any(x["grid_gt10km_warning"] for x in weather)
    wind_ok=not missing and maxgust<=spec["wind_limit"]; rain_ok=not missing and maxrain<=RAIN_LIMIT
    spatial_ok=(not spatial_hold) if spatial_scenario=="STRICT_EXCLUDE_GT10KM" else True
    base_move=max(0.01,float(f.mission_minutes)-13.0); dynamic_move=out_min+back_min
    battery=float(f.battery_energy_kwh)*dynamic_move/base_move
    ok=wind_ok and rain_ok and spatial_ok and not missing
    reason="PASS" if ok else ("WEATHER_MISSING" if missing else "WEATHER_SPATIAL_HOLD" if not spatial_ok else "WEATHER_WIND" if not wind_ok else "WEATHER_RAIN")
    return {"ok":ok,"reason":reason,"launch":launch,"delivery":delivery,"return_launch":return_launch,"recover":recover,
            "mission_minutes":float((recover-launch).total_seconds()/60),"battery_kwh":battery,"grid_kwh":battery/0.9,
            "max_gust":maxgust,"max_rain":maxrain,"spatial_hold":spatial_hold,"weather":weather}


def direct_ground(tasks, engine, duty_hours=DUTY_HOURS, release_override=None, mode="NO_UAV"):
    release_override=release_override or {}; day=as_local(tasks.iloc[0].release_local).normalize(); end=day+pd.Timedelta(hours=duty_hours)
    scenario_key=f"{tasks.iloc[0].date_local}-{int(tasks.iloc[0].scenario_seed):02d}"
    vs=[{"id":f"V{i+1:02d}","depot":d,"loc":d,"time":day,"start":None,"km":0.0} for i,d in enumerate(DEPOTS)]
    orders=[]; legs=[]
    for t in tasks.sort_values(["release_utc","task_id"]).itertuples(index=False):
        release=max(as_local(t.release_local),release_override.get(t.task_id,day)); deadline=as_local(t.release_local)+pd.Timedelta(minutes=float(t.deadline_minutes))
        cand=[]
        for v in vs:
            depart=max(v["time"],release); tr1=engine.travel(v["loc"],t.origin_node_id,depart); a1=depart+pd.Timedelta(minutes=tr1["minutes"])
            ready=max(a1,release)+pd.Timedelta(minutes=5); tr2=engine.travel(t.origin_node_id,t.destination_node_id,ready)
            delivery=ready+pd.Timedelta(minutes=tr2["minutes"]); finish=delivery+pd.Timedelta(minutes=5)
            cand.append((finish,v,depart,tr1,a1,ready,tr2,delivery))
        finish,v,depart,tr1,a1,ready,tr2,delivery=min(cand,key=lambda x:(x[0],x[1]["id"]))
        if delivery>end:
            orders.append({"task_id":t.task_id,"status":"UNSERVED_DUTY_WINDOW","delivery_local":pd.NaT,"delivery_duration_minutes":np.nan,
                           "on_time":False,"late_minutes":np.nan,"service_path":"GROUND_UNSERVED_DUTY","vehicle_id":""}); continue
        if v["start"] is None: v["start"]=depart
        for a,b,dep,arr,tr,event in [(v["loc"],t.origin_node_id,depart,a1,tr1,"PICKUP"),(t.origin_node_id,t.destination_node_id,ready,delivery,tr2,"DROPOFF")]:
            legs.append({"physical_leg_id":f"{mode}-{scenario_key}-{len(legs)+1}","vehicle_id":v["id"],"from_node":a,"to_node":b,
                         "departure_local":dep,"arrival_local":arr,"road_distance_km":tr["distance_km"],"driving_minutes":tr["minutes"],
                         "target_task_id":t.task_id,"target_event":event})
        v["km"]+=tr1["distance_km"]+tr2["distance_km"]; v["loc"]=t.destination_node_id; v["time"]=finish
        dur=(delivery-as_local(t.release_local)).total_seconds()/60
        orders.append({"task_id":t.task_id,"status":"COMPLETED","delivery_local":delivery,"delivery_duration_minutes":dur,
                       "on_time":delivery<=deadline,"late_minutes":max(0.0,(delivery-deadline).total_seconds()/60),
                       "service_path":"GROUND_DIRECT","vehicle_id":v["id"]})
    for v in vs:
        if v["start"] is None: continue
        tr=engine.travel(v["loc"],v["depot"],v["time"]); arr=v["time"]+pd.Timedelta(minutes=tr["minutes"])
        if arr<=end:
            legs.append({"physical_leg_id":f"{mode}-{scenario_key}-{len(legs)+1}","vehicle_id":v["id"],"from_node":v["loc"],"to_node":v["depot"],
                         "departure_local":v["time"],"arrival_local":arr,"road_distance_km":tr["distance_km"],"driving_minutes":tr["minutes"],
                         "target_task_id":"","target_event":"RETURN_TO_DEPOT"}); v["km"]+=tr["distance_km"]
        v["time"]=min(arr,end)
    driver_h=sum((v["time"]-v["start"]).total_seconds()/3600 for v in vs if v["start"] is not None)
    return pd.DataFrame(orders),pd.DataFrame(legs),{"vehicle_km":sum(v["km"] for v in vs),"driver_hours":driver_h}


def m1(tasks, feas, engine, model_key, spatial, wmap):
    spec=MODELS[model_key]; fx=feas[(feas["model"]==spec["name"])&feas.task_id.isin(tasks.task_id)].set_index("task_id")
    stations={}; uav_orders=[]; flights=[]; weather_rows=[]; soc=[]; fall=[]; overrides={}
    for t in tasks.sort_values(["release_utc","task_id"]).itertuples(index=False):
        if t.task_id not in fx.index: fall.append(t.task_id); continue
        f=fx.loc[t.task_id]
        if not bool(f.technical_feasible) or bool(f.reverse_geometry_proxy) or bool(f.wmp228_reference_circle_intersects): fall.append(t.task_id); continue
        st=stations.setdefault(str(t.origin_node_id),{"available":as_local(t.release_local).normalize(),"soc":spec["capacity_kwh"],"battery_id":f"M1-{model_key}-{t.origin_node_id}-B01"})
        launch=max(as_local(t.release_local),st["available"]); ev=flight_evaluation(t,f,spec,launch,spatial,wmap)
        usable=st["soc"]-spec["capacity_kwh"]*spec["reserve_fraction"]
        if not ev["ok"] or ev.get("battery_kwh",1e9)>usable:
            fall.append(t.task_id); overrides[t.task_id]=launch
            weather_rows.append({"mode":f"M1_{model_key}","task_id":t.task_id,"decision":"GROUND_FALLBACK","reason":ev["reason"],"spatial_scenario":spatial,"actual_launch_local":launch})
            continue
        before=st["soc"]; after=before-ev["battery_kwh"]; charge=spec["capacity_kwh"]-after; charge_min=(charge/0.9)/spec["charger_kw"]*60
        st["available"]=ev["recover"]+pd.Timedelta(minutes=charge_min); st["soc"]=spec["capacity_kwh"]
        fid=f"{spatial}-M1_{model_key}-{t.scenario_seed}-{t.task_id}"; dur=(ev["delivery"]-as_local(t.release_local)).total_seconds()/60; deadline=as_local(t.release_local)+pd.Timedelta(minutes=float(t.deadline_minutes))
        uav_orders.append({"task_id":t.task_id,"status":"COMPLETED","delivery_local":ev["delivery"],"delivery_duration_minutes":dur,"on_time":ev["delivery"]<=deadline,
                           "late_minutes":max(0,(ev["delivery"]-deadline).total_seconds()/60),"service_path":"UAV_FIXED_STATION","vehicle_id":"","flight_id":fid})
        flights.append({"flight_id":fid,"task_id":t.task_id,"launch_local":launch,"delivery_local":ev["delivery"],"recovery_local":ev["recover"],"grid_input_kwh":ev["grid_kwh"],
                        "battery_energy_kwh":ev["battery_kwh"],"roundtrip_km":f.roundtrip_km,"battery_id":st["battery_id"],"operator_minutes":ev["mission_minutes"]})
        soc.append({"battery_id":st["battery_id"],"flight_id":fid,"task_id":t.task_id,"soc_before_kwh":before,"mission_kwh":ev["battery_kwh"],"soc_after_kwh":after,
                    "reserve_kwh":spec["capacity_kwh"]*spec["reserve_fraction"],"charged_kwh":charge,"grid_charge_kwh":charge/0.9,"charge_minutes":charge_min})
        weather_rows.extend({"mode":f"M1_{model_key}","task_id":t.task_id,"decision":"FLY","reason":"PASS","spatial_scenario":spatial,"actual_launch_local":launch,**x} for x in ev["weather"])
    gt=tasks[tasks.task_id.isin(fall)].copy(); go,gl,gs=direct_ground(gt,engine,release_override=overrides,mode=f"M1_{model_key}") if len(gt) else (pd.DataFrame(),pd.DataFrame(),{"vehicle_km":0,"driver_hours":0})
    if len(gl): gl["physical_leg_id"]=spatial+"-"+gl["physical_leg_id"].astype(str)
    orders=pd.concat([go,pd.DataFrame(uav_orders)],ignore_index=True,sort=False); grid=sum(x["grid_input_kwh"] for x in flights); op=sum(x["operator_minutes"] for x in flights)/60
    return orders,gl,pd.DataFrame(flights),pd.DataFrame(weather_rows),pd.DataFrame(soc),{**gs,"grid_kwh":grid,"operator_hours":op}


def m2(tasks, feas, engine, model_key, spatial, wmap):
    spec=MODELS[model_key]; fx=feas[(feas["model"]==spec["name"])&feas.task_id.isin(tasks.task_id)].set_index("task_id")
    day=as_local(tasks.iloc[0].release_local).normalize(); end=day+pd.Timedelta(hours=DUTY_HOURS)
    vs=[]
    for i,d in enumerate(DEPOTS):
        vs.append({"id":f"V{i+1:02d}","depot":d,"loc":d,"time":day,"start":None,"km":0.0,
                   "batteries":[{"id":f"M2-{model_key}-V{i+1:02d}-B01","soc":spec["capacity_kwh"]},{"id":f"M2-{model_key}-V{i+1:02d}-B02","soc":spec["capacity_kwh"]}]})
    orders=[];legs=[];flights=[];weather_rows=[];soc=[]; scenario_key=f"{tasks.iloc[0].date_local}-{int(tasks.iloc[0].scenario_seed):02d}"
    for t in tasks.sort_values(["release_utc","task_id"]).itertuples(index=False):
        release=as_local(t.release_local); deadline=release+pd.Timedelta(minutes=float(t.deadline_minutes)); f=fx.loc[t.task_id] if t.task_id in fx.index else None
        base_eligible=f is not None and bool(f.technical_feasible) and not bool(f.wmp228_reference_circle_intersects)
        cand=[]
        for v in vs:
            depart=max(v["time"],release); tr1=engine.travel(v["loc"],t.origin_node_id,depart); a1=depart+pd.Timedelta(minutes=tr1["minutes"]); ready=max(a1,release)+pd.Timedelta(minutes=5)
            ev=flight_evaluation(t,f,spec,ready,spatial,wmap) if base_eligible else {"ok":False,"reason":"TECHNICAL_OR_GEOMETRY"}
            battery=None
            if ev.get("ok"):
                need=ev["battery_kwh"]+spec["capacity_kwh"]*spec["reserve_fraction"]
                battery=next((b for b in v["batteries"] if b["soc"]>=need),None)
            if ev.get("ok") and battery is not None:
                finish=ev["recover"]+pd.Timedelta(minutes=5); delivery=ev["delivery"]; tr2=None; use_uav=True
            else:
                tr2=engine.travel(t.origin_node_id,t.destination_node_id,ready); delivery=ready+pd.Timedelta(minutes=tr2["minutes"]); finish=delivery+pd.Timedelta(minutes=5); use_uav=False
            cand.append((finish,v,depart,tr1,a1,ready,tr2,delivery,use_uav,ev,battery))
        finish,v,depart,tr1,a1,ready,tr2,delivery,use_uav,ev,battery=min(cand,key=lambda x:(x[0],x[1]["id"]))
        if delivery>end:
            orders.append({"task_id":t.task_id,"status":"UNSERVED_DUTY_WINDOW","delivery_local":pd.NaT,"delivery_duration_minutes":np.nan,"on_time":False,"late_minutes":np.nan,
                           "service_path":"UNSERVED_DUTY","vehicle_id":"","flight_id":""}); continue
        if v["start"] is None:v["start"]=depart
        legs.append({"physical_leg_id":f"{spatial}-M2_{model_key}-{scenario_key}-{len(legs)+1}","vehicle_id":v["id"],"from_node":v["loc"],"to_node":t.origin_node_id,
                     "departure_local":depart,"arrival_local":a1,"road_distance_km":tr1["distance_km"],"driving_minutes":tr1["minutes"],"target_task_id":t.task_id,"target_event":"PICKUP_OR_LAUNCH"})
        v["km"]+=tr1["distance_km"];v["loc"]=t.origin_node_id
        fid=""
        if use_uav:
            fid=f"{spatial}-M2_{model_key}-{t.scenario_seed}-{t.task_id}";before=battery["soc"];battery["soc"]-=ev["battery_kwh"]
            flights.append({"flight_id":fid,"task_id":t.task_id,"vehicle_id":v["id"],"launch_local":ready,"delivery_local":delivery,"recovery_local":ev["recover"],
                            "grid_input_kwh":ev["grid_kwh"],"battery_energy_kwh":ev["battery_kwh"],"roundtrip_km":f.roundtrip_km,"battery_id":battery["id"],"operator_minutes":ev["mission_minutes"]})
            soc.append({"battery_id":battery["id"],"flight_id":fid,"task_id":t.task_id,"soc_before_kwh":before,"mission_kwh":ev["battery_kwh"],"soc_after_kwh":battery["soc"],
                        "reserve_kwh":spec["capacity_kwh"]*spec["reserve_fraction"],"charged_kwh":0.0,"grid_charge_kwh":ev["grid_kwh"],"charge_minutes":0.0})
            weather_rows.extend({"mode":f"M2_{model_key}","task_id":t.task_id,"decision":"FLY","reason":"PASS","spatial_scenario":spatial,"actual_launch_local":ready,**x} for x in ev["weather"])
            v["time"]=finish
        else:
            legs.append({"physical_leg_id":f"{spatial}-M2_{model_key}-{scenario_key}-{len(legs)+1}","vehicle_id":v["id"],"from_node":t.origin_node_id,"to_node":t.destination_node_id,
                         "departure_local":ready,"arrival_local":delivery,"road_distance_km":tr2["distance_km"],"driving_minutes":tr2["minutes"],"target_task_id":t.task_id,"target_event":"GROUND_DROPOFF"})
            v["km"]+=tr2["distance_km"];v["loc"]=t.destination_node_id;v["time"]=finish
            reason="NO_BATTERY_SOC" if ev.get("ok") and battery is None else ev.get("reason","TECHNICAL_OR_GEOMETRY")
            weather_rows.append({"mode":f"M2_{model_key}","task_id":t.task_id,"decision":"GROUND_FALLBACK","reason":reason,"spatial_scenario":spatial,"actual_launch_local":ready})
        dur=(delivery-release).total_seconds()/60;orders.append({"task_id":t.task_id,"status":"COMPLETED","delivery_local":delivery,"delivery_duration_minutes":dur,"on_time":delivery<=deadline,
                                                                 "late_minutes":max(0,(delivery-deadline).total_seconds()/60),"service_path":"UAV_MOBILE_SOC" if use_uav else "GROUND_FALLBACK","vehicle_id":v["id"],"flight_id":fid})
    for v in vs:
        if v["start"] is None:continue
        tr=engine.travel(v["loc"],v["depot"],v["time"]);arr=v["time"]+pd.Timedelta(minutes=tr["minutes"])
        if arr<=end:
            legs.append({"physical_leg_id":f"{spatial}-M2_{model_key}-{scenario_key}-{len(legs)+1}","vehicle_id":v["id"],"from_node":v["loc"],"to_node":v["depot"],"departure_local":v["time"],
                         "arrival_local":arr,"road_distance_km":tr["distance_km"],"driving_minutes":tr["minutes"],"target_task_id":"","target_event":"RETURN_TO_DEPOT"});v["km"]+=tr["distance_km"]
        v["time"]=min(arr,end)
    driver_h=sum((v["time"]-v["start"]).total_seconds()/3600 for v in vs if v["start"] is not None);grid=sum(x["grid_input_kwh"] for x in flights);op=sum(x["operator_minutes"] for x in flights)/60
    return pd.DataFrame(orders),pd.DataFrame(legs),pd.DataFrame(flights),pd.DataFrame(weather_rows),pd.DataFrame(soc),{"vehicle_km":sum(v["km"] for v in vs),"driver_hours":driver_h,"grid_kwh":grid,"operator_hours":op}


def scenario_summary(mode,spatial,date,seed,orders,stats,price):
    km=stats["vehicle_km"];litres=km*.1;ttw=litres*PETROL_CO2_KG_L;grid=stats.get("grid_kwh",0);gridghg=grid*GRID_KG_KWH
    cost=litres*price+km*MAINT_MYR_KM+stats["driver_hours"]*DRIVER_MYR_H+stats.get("operator_hours",0)*UAV_OPERATOR_MYR_H+grid*ELEC_MYR_KWH
    completed=int((orders.status=="COMPLETED").sum());ontime=int(orders.on_time.sum())
    return {"spatial_scenario":spatial,"mode":mode,"date_local":date,"scenario_seed":seed,"orders":len(orders),"completed":completed,"on_time":ontime,
            "completion_rate":completed/len(orders),"on_time_rate_all_orders":ontime/len(orders),"vehicle_km":km,"fuel_litres":litres,"petrol_ttw_co2_kg":ttw,
            "grid_input_kwh":grid,"grid_operation_ghg_kg":gridghg,"combined_mixed_boundary_proxy_kg":ttw+gridghg,"partial_opex_MYR":cost,"driver_hours":stats["driver_hours"],
            "uav_operator_hours":stats.get("operator_hours",0),"uav_flights":int((orders.service_path.str.startswith("UAV")).sum()),"duty_window_hours":DUTY_HOURS}


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--start",type=int,default=0);ap.add_argument("--limit",type=int);ap.add_argument("--chunk-label",required=True);ap.add_argument("--summary-only",action="store_true");args=ap.parse_args()
    out=RUN/"G11_1_DYNAMIC_WEATHER"/"data"/"chunks"/args.chunk_label;out.mkdir(parents=True,exist_ok=True)
    s08=load_s08(); od=pd.read_parquet(S0708/"S07/data/V5_68_DIRECTED_OD_MATRIX_AND_PATHS.parquet");edges=pd.read_parquet(S0708/"S07/data/OSM_ROUTE_EDGES_WITH_FCD_PROXY.parquet");fcd=pd.read_parquet(S0708/"S07/data/fcd_hourly_345node_2026_05_09.parquet")
    engine=HourCache(s08.RouteEngine(od,edges,fcd));tasks=pd.read_parquet(S0708/"S07/data/V5_TASK_TIME_WEATHER_ROAD_INDEX.parquet");feas=pd.read_parquet(OLD/"S09/data/S09_MISSION_FEASIBILITY.parquet")
    weather=pd.read_parquet(S0708/"S07/data/V5_249696_NODE_HOUR_WEATHER.parquet");weather["hour"]=pd.to_datetime(weather.interval_start_utc,utc=True);wmap={(str(r.node_id),r.hour):r for r in weather.itertuples()}
    prices=pd.read_csv(S0708/"S08/data/S08_SCENARIO_SUMMARY.csv").set_index(["date_local","scenario_seed"]).petrol_MYR_per_litre.to_dict()
    groups=list(tasks.groupby(["date_local","scenario_seed"],sort=True));groups=groups[args.start:(args.start+args.limit) if args.limit else None]
    all_o=[];all_s=[];all_l=[];all_f=[];all_w=[];all_soc=[]
    for i,((date,seed),g) in enumerate(groups,1):
        control_o,control_l,control_stats=direct_ground(g,engine,mode="NO_UAV_COMMON")
        if len(control_l) and not args.summary_only:
            control_l["mode"]="NO_UAV_COMMON";control_l["spatial_scenario"]="COMMON";control_l["date_local"]=date;control_l["scenario_seed"]=seed;all_l.append(control_l)
        for spatial in SPATIAL_SCENARIOS:
            for mode in ("M1_NO_UAV","M2_NO_UAV"):
                o=control_o.copy();o["mode"]=mode;o["spatial_scenario"]=spatial;o["date_local"]=date;o["scenario_seed"]=seed
                if not args.summary_only: all_o.append(o)
                all_s.append(scenario_summary(mode,spatial,date,seed,o,control_stats,prices[(date,seed)]))
            for family,func in (("M1",m1),("M2",m2)):
                for model in ("DJI","WING"):
                    mode=f"{family}_{model}";o,l,f,w,soc,stats=func(g,feas,engine,model,spatial,wmap)
                    for frame in (o,l,f,w,soc):
                        if len(frame): frame["mode"]=mode;frame["spatial_scenario"]=spatial;frame["date_local"]=date;frame["scenario_seed"]=seed
                    if not args.summary_only: all_o.append(o)
                    all_s.append(scenario_summary(mode,spatial,date,seed,o,stats,prices[(date,seed)]))
                    if not args.summary_only:
                        if len(l):all_l.append(l)
                        if len(f):all_f.append(f)
                        if len(w):all_w.append(w)
                        if len(soc):all_soc.append(soc)
        if i%100==0 or i==len(groups): print(f"checkpoint {i}/{len(groups)}",flush=True)
    pd.DataFrame(all_s).to_csv(out/"SCENARIO_SUMMARY.csv",index=False)
    if not args.summary_only:
        pd.concat(all_o,ignore_index=True).to_parquet(out/"ORDER_RESULTS.parquet",index=False)
        pd.concat(all_l,ignore_index=True).to_parquet(out/"GROUND_LEGS.parquet",index=False);pd.concat(all_f,ignore_index=True).to_parquet(out/"FLIGHTS.parquet",index=False)
        pd.concat(all_w,ignore_index=True).to_parquet(out/"WEATHER_LEDGER.parquet",index=False);pd.concat(all_soc,ignore_index=True).to_parquet(out/"SOC_LEDGER.parquet",index=False)


if __name__=="__main__":main()
