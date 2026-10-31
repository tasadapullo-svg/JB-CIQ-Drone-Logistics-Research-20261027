from __future__ import annotations
import argparse, importlib.util, json, math
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve();RUN=HERE.parents[1];ROOT=HERE.parents[3]
S0708=ROOT/"output_S07_S08_Codex_20261030";S10RUN=ROOT/"output_S08A_S09_S10_Codex_20261030"/"RUN_20261030_01";OUT=RUN
DEPOTS=["A01","B06","C02"]
FIXED_STATIONS=["A01","A02","A03","A09","A_N05","A_N07","B06","B07","C02","C04","C21"]
PETROL_L_100KM=.1;PETROL_CO2_KG_L=2.2410927;GRID_KG_KWH=.740;DRIVER_MYR_H=15.;OPERATOR_MYR_H=15.;MAINT_MYR_KM=.20;ELEC_MYR_KWH=.50;RAIN_LIMIT=.5
MODELS={"DJI":{"source":"DJI_FLYCART30","payload":30.,"speed":15.,"wind":12.,"cap":3.9688,"reserve":.20,"charger":7.2,"eff":.90,"to_kwh":.10},"WING":{"source":"WINGCOPTER198_CARGO","payload":4.7,"speed":25.,"wind":18.,"cap":3.,"reserve":.20,"charger":2.,"eff":.90,"to_kwh":.05}}

def as_local(x):
 t=pd.Timestamp(x);return t.tz_localize("Asia/Kuala_Lumpur") if t.tzinfo is None else t.tz_convert("Asia/Kuala_Lumpur")
def load_s08():
 p=S0708/"S08/code/run_s08_petrol_m0.py";s=importlib.util.spec_from_file_location("s08",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class HourCache:
 def __init__(self,e):self.e=e;self.c={}
 def travel(self,a,b,t):
  k=(str(a),str(b),pd.Timestamp(t).floor("h"))
  if k not in self.c:self.c[k]=self.e.travel(k[0],k[1],k[2])
  return self.c[k]
def bearing(lon1,lat1,lon2,lat2):
 a,b,c,d=map(math.radians,[lon1,lat1,lon2,lat2]);return (math.degrees(math.atan2(math.sin(c-a)*math.cos(d),math.cos(b)*math.sin(d)-math.sin(b)*math.cos(d)*math.cos(c-a)))+360)%360
def haversine(lon1,lat1,lon2,lat2):
 r=6371.;a,b,c,d=map(math.radians,[lon1,lat1,lon2,lat2]);q=math.sin((d-b)/2)**2+math.cos(b)*math.cos(d)*math.sin((c-a)/2)**2;return 2*r*math.asin(math.sqrt(q))
def headwind(speed,met_from,course):return float(speed)*math.cos(math.radians(((float(met_from)-course+180)%360)-180))
def weather_at(wmap,node,t):return wmap.get((str(node),pd.Timestamp(t).tz_convert("UTC").floor("h")))
def energy(spec,model,payload,km,mult):
 if payload>spec["payload"]:return None
 if model=="DJI":
  maxdist=28.-12.*payload/spec["payload"];b=km*(spec["cap"]/maxdist+spec["cap"]/28.)+spec["to_kwh"]
 else:
  if 2*km>92.*(1-spec["reserve"]):return None
  b=km*.18+spec["to_kwh"]
 return b*mult

def evaluate_flight(task,m,spec,model,launch,spatial,wmap,mult):
 batt=energy(spec,model,float(task.parcel_kg),m["oneway_km"],mult)
 if batt is None or batt>spec["cap"]*(1-spec["reserve"]):return {"ok":False,"reason":"ENERGY_OR_PAYLOAD"}
 if m["reverse"]:return {"ok":False,"reason":"REVERSE_GEOMETRY_PROXY"}
 if m["wmp"]:return {"ok":False,"reason":"WMP228_REFERENCE_RISK"}
 if m["cross_border"]:return {"ok":False,"reason":"CROSS_BORDER_HOLD"}
 wl=weather_at(wmap,m["launch_node"],launch)
 if wl is None:return {"ok":False,"reason":"WEATHER_MISSING"}
 out_speed=max(3.,spec["speed"]-headwind(wl.wind_speed_10m,wl.wind_direction_10m,m["course"]));out_min=m["oneway_km"]*1000/out_speed/60;delivery=launch+pd.Timedelta(minutes=2+out_min+2)
 wd=weather_at(wmap,m["dest_node"],delivery)
 if wd is None:return {"ok":False,"reason":"WEATHER_MISSING"}
 ret=delivery+pd.Timedelta(minutes=2);wret=weather_at(wmap,m["dest_node"],ret)
 if wret is None:return {"ok":False,"reason":"WEATHER_MISSING"}
 back_speed=max(3.,spec["speed"]-headwind(wret.wind_speed_10m,wret.wind_direction_10m,(m["course"]+180)%360));back_min=m["oneway_km"]*1000/back_speed/60;recover=ret+pd.Timedelta(minutes=back_min+2);wr=weather_at(wmap,m["launch_node"],recover)
 events=[("LAUNCH",launch,wl,m["launch_node"]),("DELIVERY",delivery,wd,m["dest_node"]),("RETURN_LAUNCH",ret,wret,m["dest_node"]),("RECOVERY",recover,wr,m["launch_node"])]
 if any(x[2] is None for x in events):return {"ok":False,"reason":"WEATHER_MISSING"}
 rows=[{"event":ev,"event_local":t,"node_id":node,"wind_speed_10m":w.wind_speed_10m,"wind_gusts_10m":w.wind_gusts_10m,"wind_direction_10m":w.wind_direction_10m,"rain":w.rain,"precipitation":w.precipitation,"grid_distance_m":w.grid_distance_m,"grid_gt10km_warning":w.grid_gt10km_warning} for ev,t,w,node in events]
 missing=any(not np.isfinite(float(x[k])) for x in rows for k in ["wind_gusts_10m","rain"]);wind_ok=all(float(x["wind_gusts_10m"])<=spec["wind"] for x in rows if np.isfinite(float(x["wind_gusts_10m"])));rain_ok=all(float(x["rain"])<=RAIN_LIMIT for x in rows if np.isfinite(float(x["rain"])));spatial_ok=spatial=="RELAXED_PROXY" or not any(bool(x["grid_gt10km_warning"]) for x in rows)
 ok=not missing and wind_ok and rain_ok and spatial_ok;reason="PASS" if ok else "WEATHER_MISSING" if missing else "WEATHER_WIND" if not wind_ok else "WEATHER_RAIN" if not rain_ok else "WEATHER_SPATIAL_HOLD"
 return {"ok":ok,"reason":reason,"delivery":delivery,"return_launch":ret,"recover":recover,"battery_kwh":batt,"grid_kwh":batt/spec["eff"],"mission_minutes":float((recover-launch).total_seconds()/60),"weather":rows}

def mission_catalog(feas,coords):
 out={}
 for key,spec in MODELS.items():
  x=feas[feas["model"]==spec["source"]].sort_values("task_id").drop_duplicates(["origin_node_id","destination_node_id"]);cat={}
  for r in x.itertuples(index=False):
   a,b=str(r.origin_node_id),str(r.destination_node_id)
   if a not in coords or b not in coords:continue
   la,xa=coords[a];lb,xb=coords[b];cat[(a,b)]={"launch_node":a,"dest_node":b,"oneway_km":haversine(xa,la,xb,lb),"course":bearing(xa,la,xb,lb),"reverse":bool(r.reverse_geometry_proxy),"wmp":bool(r.wmp228_reference_circle_intersects),"cross_border":bool(getattr(r,"cross_border_hold",False))}
  out[key]=cat
 return out

def simulate(tasks,engine,wmap,catalog,arch,model,uav_on,spatial,duty_h,mult,run_label=None):
 spec=MODELS[model];day=as_local(tasks.iloc[0].release_local).normalize();end=day+pd.Timedelta(hours=duty_h);scenario=f"{tasks.iloc[0].date_local}-{int(tasks.iloc[0].scenario_seed):02d}"
 idtag=run_label or f"{arch}_{model}"
 vs=[{"id":f"V{i+1:02d}","depot":d,"loc":d,"time":day,"start":None,"km":0.,"bats":[{"id":f"M2-{model}-V{i+1:02d}-B{j+1:02d}","soc":spec["cap"]} for j in range(2)]} for i,d in enumerate(DEPOTS)]
 stations={s:{"available":day,"battery_id":f"M1-{model}-{s}-B01","soc":spec["cap"]} for s in FIXED_STATIONS}
 orders=[];legs=[];flights=[];soc=[];weather=[];events=[];counts=Counter()
 def trip(a,b,t):return engine.travel(str(a),str(b),t)
 for t in tasks.sort_values(["release_utc","task_id"]).itertuples(index=False):
  release=as_local(t.release_local);deadline=release+pd.Timedelta(minutes=float(t.deadline_minutes));cands=[]
  for v in vs:
   depart=max(v["time"],release);tr0=trip(v["loc"],t.origin_node_id,depart);pickup=depart+pd.Timedelta(minutes=tr0["minutes"]);ready=pickup+pd.Timedelta(minutes=5)
   trg=trip(t.origin_node_id,t.destination_node_id,ready);delivery=ready+pd.Timedelta(minutes=trg["minutes"]);finish=delivery+pd.Timedelta(minutes=5);back=trip(t.destination_node_id,v["depot"],finish)
   if finish+pd.Timedelta(minutes=back["minutes"])<=end:cands.append({"kind":"GROUND","v":v,"delivery":delivery,"finish":finish,"depart":depart,"tr0":tr0,"pickup":pickup,"tr1":trg,"newloc":str(t.destination_node_id)})
   if not uav_on:continue
   if arch=="M1":
    for st in FIXED_STATIONS:
     m=catalog.get((st,str(t.destination_node_id)))
     if m is None:continue
     trs=trip(t.origin_node_id,st,ready);at=ready+pd.Timedelta(minutes=trs["minutes"]);launch=max(at+pd.Timedelta(minutes=5),stations[st]["available"]);ev=evaluate_flight(t,m,spec,model,launch,spatial,wmap,mult)
     if not ev["ok"]:counts[ev["reason"]]+=1;continue
     veh_finish=at+pd.Timedelta(minutes=5);back=trip(st,v["depot"],veh_finish)
     if ev["recover"]>end or veh_finish+pd.Timedelta(minutes=back["minutes"])>end:counts["DUTY_WINDOW"]+=1;continue
     cands.append({"kind":"UAV_M1","v":v,"station":st,"mission":m,"ev":ev,"delivery":ev["delivery"],"finish":veh_finish,"depart":depart,"tr0":tr0,"pickup":pickup,"tr1":trs,"newloc":st,"launch":launch})
   else:
    base=catalog.get((str(t.origin_node_id),str(t.destination_node_id)))
    if base is None:counts["NO_DIRECTED_CANDIDATE"]+=1;continue
    m={**base,"oneway_km":haversine(t.origin_lon,t.origin_lat,t.destination_lon,t.destination_lat),"course":bearing(t.origin_lon,t.origin_lat,t.destination_lon,t.destination_lat)};launch=ready;ev=evaluate_flight(t,m,spec,model,launch,spatial,wmap,mult);bat=None
    if ev["ok"]:
     need=ev["battery_kwh"]+spec["cap"]*spec["reserve"];bat=next((b for b in v["bats"] if b["soc"]>=need),None)
    if not ev["ok"]:counts[ev["reason"]]+=1;continue
    if bat is None:counts["NO_BATTERY_SOC"]+=1;continue
    finish=ev["recover"]+pd.Timedelta(minutes=5);back=trip(t.origin_node_id,v["depot"],finish)
    if finish+pd.Timedelta(minutes=back["minutes"])>end:counts["DUTY_WINDOW"]+=1;continue
    cands.append({"kind":"UAV_M2","v":v,"battery":bat,"mission":m,"ev":ev,"delivery":ev["delivery"],"finish":finish,"depart":depart,"tr0":tr0,"pickup":pickup,"tr1":None,"newloc":str(t.origin_node_id),"launch":launch})
  if not cands:
   orders.append({"task_id":t.task_id,"status":"UNSERVED_DUTY_OR_ROUTE","delivery_local":pd.NaT,"delivery_duration_minutes":np.nan,"on_time":False,"late_minutes":np.nan,"service_path":"UNSERVED","vehicle_id":"","flight_id":""});continue
  c=min(cands,key=lambda x:(x["delivery"],0 if x["kind"]=="GROUND" else 1,x["v"]["id"]));v=c["v"]
  if v["start"] is None:v["start"]=c["depart"]
  def addleg(a,b,dep,arr,tr,event):
    lid=f"{spatial}-{idtag}-{scenario}-{len(legs)+1}";legs.append({"physical_leg_id":lid,"vehicle_id":v["id"],"from_node":a,"to_node":b,"departure_local":dep,"arrival_local":arr,"road_distance_km":tr["distance_km"],"driving_minutes":tr["minutes"],"target_task_id":t.task_id,"target_event":event});v["km"]+=tr["distance_km"]
  addleg(v["loc"],t.origin_node_id,c["depart"],c["pickup"],c["tr0"],"PICKUP");fid=""
  if c["kind"]=="GROUND":addleg(t.origin_node_id,t.destination_node_id,c["pickup"]+pd.Timedelta(minutes=5),c["delivery"],c["tr1"],"GROUND_DROPOFF")
  else:
   if c["kind"]=="UAV_M1":
    addleg(t.origin_node_id,c["station"],c["pickup"]+pd.Timedelta(minutes=5),c["finish"]-pd.Timedelta(minutes=5),c["tr1"],"PACKAGE_TO_FIXED_STATION");asset=stations[c["station"]];before=asset["soc"];after=before-c["ev"]["battery_kwh"];charge=spec["cap"]-after;charge_min=(charge/spec["eff"])/spec["charger"]*60;asset["available"]=c["ev"]["recover"]+pd.Timedelta(minutes=charge_min);asset["soc"]=spec["cap"];bid=asset["battery_id"]
   else:
    asset=c["battery"];before=asset["soc"];after=before-c["ev"]["battery_kwh"];asset["soc"]=after;charge=0.;charge_min=0.;bid=asset["id"]
   fid=f"{spatial}-{idtag}-{scenario}-{t.task_id}";flights.append({"flight_id":fid,"task_id":t.task_id,"vehicle_id":v["id"] if arch=="M2" else "","launch_node":c["mission"]["launch_node"],"delivery_node":c["mission"]["dest_node"],"launch_local":c["launch"],"delivery_local":c["ev"]["delivery"],"recovery_local":c["ev"]["recover"],"battery_energy_kwh":c["ev"]["battery_kwh"],"grid_input_kwh":c["ev"]["grid_kwh"],"battery_id":bid,"oneway_km":c["mission"]["oneway_km"],"energy_multiplier":mult,"operator_minutes":c["ev"]["mission_minutes"]})
   soc.append({"battery_id":bid,"flight_id":fid,"task_id":t.task_id,"soc_before_kwh":before,"mission_kwh":c["ev"]["battery_kwh"],"soc_after_kwh":after,"reserve_kwh":spec["cap"]*spec["reserve"],"charged_kwh":charge,"charge_minutes":charge_min});weather.extend({"flight_id":fid,"task_id":t.task_id,"decision":"FLY","reason":"PASS",**x} for x in c["ev"]["weather"])
  v["loc"]=c["newloc"];v["time"]=c["finish"];dur=(c["delivery"]-release).total_seconds()/60;orders.append({"task_id":t.task_id,"status":"COMPLETED","delivery_local":c["delivery"],"delivery_duration_minutes":dur,"on_time":c["delivery"]<=deadline,"late_minutes":max(0.,(c["delivery"]-deadline).total_seconds()/60),"service_path":c["kind"],"vehicle_id":v["id"],"flight_id":fid})
  events.extend([{"resource_id":v["id"],"task_id":t.task_id,"event":"RELEASE","event_local":release,"node_id":t.origin_node_id},{"resource_id":v["id"],"task_id":t.task_id,"event":"PICKUP_ARRIVAL","event_local":c["pickup"],"node_id":t.origin_node_id},{"resource_id":v["id"],"task_id":t.task_id,"event":"PICKUP_COMPLETE","event_local":c["pickup"]+pd.Timedelta(minutes=5),"node_id":t.origin_node_id},{"resource_id":v["id"],"task_id":t.task_id,"event":"DELIVERY","event_local":c["delivery"],"node_id":t.destination_node_id}])
  if c["kind"]=="GROUND":events.append({"resource_id":v["id"],"task_id":t.task_id,"event":"DROPOFF_SERVICE_COMPLETE","event_local":c["finish"],"node_id":t.destination_node_id})
  else:
   events.extend({"resource_id":bid,"task_id":t.task_id,"event":x["event"],"event_local":x["event_local"],"node_id":x["node_id"]} for x in c["ev"]["weather"])
   events.append({"resource_id":v["id"],"task_id":t.task_id,"event":"VEHICLE_RELEASED_AFTER_UAV_HANDOFF" if c["kind"]=="UAV_M1" else "UAV_RECOVERY_SERVICE_COMPLETE","event_local":c["finish"],"node_id":c["newloc"]})
 for v in vs:
  if v["start"] is None:continue
  tr=trip(v["loc"],v["depot"],v["time"]);arr=v["time"]+pd.Timedelta(minutes=tr["minutes"])
  if arr>end:raise RuntimeError(f"RETURN_RESERVATION_BROKEN:{scenario}:{v['id']}")
  lid=f"{spatial}-{idtag}-{scenario}-{len(legs)+1}";legs.append({"physical_leg_id":lid,"vehicle_id":v["id"],"from_node":v["loc"],"to_node":v["depot"],"departure_local":v["time"],"arrival_local":arr,"road_distance_km":tr["distance_km"],"driving_minutes":tr["minutes"],"target_task_id":"","target_event":"MANDATORY_RETURN_DEPOT"});events.append({"resource_id":v["id"],"task_id":"","event":"MANDATORY_RETURN_DEPOT","event_local":arr,"node_id":v["depot"]});v["km"]+=tr["distance_km"];v["time"]=arr
 oh=sum(x["operator_minutes"] for x in flights)/60;dh=sum((v["time"]-v["start"]).total_seconds()/3600 for v in vs if v["start"] is not None)
 return [pd.DataFrame(x) for x in [orders,legs,flights,weather,soc,events]],{"vehicle_km":sum(v["km"] for v in vs),"driver_hours":dh,"operator_hours":oh,"grid_kwh":sum(x["grid_input_kwh"] for x in flights),"reject_counts":dict(counts)}

def summary(mode,spatial,date,seed,o,st,price,duty,mult):
 km=st["vehicle_km"];litres=km*PETROL_L_100KM;grid=st["grid_kwh"];completed=int((o.status=="COMPLETED").sum());ontime=int(o.on_time.sum())
 return {"spatial_scenario":spatial,"mode":mode,"date_local":date,"scenario_seed":seed,"orders":len(o),"completed":completed,"on_time":ontime,"completion_rate":completed/len(o),"on_time_rate_all_orders":ontime/len(o),"mean_delivery_minutes":float(o.delivery_duration_minutes.mean()),"vehicle_km":km,"fuel_litres":litres,"petrol_MYR_per_litre":price,"grid_input_kwh":grid,"mixed_boundary_operational_ghg_proxy_kg":litres*PETROL_CO2_KG_L+grid*GRID_KG_KWH,"partial_opex_MYR":litres*price+km*MAINT_MYR_KM+st["driver_hours"]*DRIVER_MYR_H+st["operator_hours"]*OPERATOR_MYR_H+grid*ELEC_MYR_KWH,"driver_hours":st["driver_hours"],"uav_operator_hours":st["operator_hours"],"uav_flights":int(o.service_path.astype(str).str.startswith("UAV").sum()),"ground_completed":completed-int(o.service_path.astype(str).str.startswith("UAV").sum()),"unserved":len(o)-completed,"duty_window_hours":duty,"energy_multiplier":mult}

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--chunk-label",required=True);ap.add_argument("--selected-scenarios",required=True);ap.add_argument("--duty-hours",type=float,default=24);ap.add_argument("--dji-energy-multiplier",type=float,required=True);ap.add_argument("--wing-energy-multiplier",type=float,required=True);ap.add_argument("--spatial",choices=["STRICT_EXCLUDE_GT10KM"],default="STRICT_EXCLUDE_GT10KM");ap.add_argument("--summary-only",action="store_true");a=ap.parse_args();out=OUT/"work"/a.chunk_label;out.mkdir(parents=True,exist_ok=True)
 s08=load_s08();od=pd.read_parquet(S0708/"S07/data/V5_68_DIRECTED_OD_MATRIX_AND_PATHS.parquet");edges=pd.read_parquet(S0708/"S07/data/OSM_ROUTE_EDGES_WITH_FCD_PROXY.parquet");fcd=pd.read_parquet(S0708/"S07/data/fcd_hourly_345node_2026_05_09.parquet");engine=HourCache(s08.RouteEngine(od,edges,fcd))
 tasks=pd.read_parquet(S0708/"S07/data/V5_TASK_TIME_WEATHER_ROAD_INDEX.parquet");feas=pd.read_parquet(S10RUN/"S09/data/S09_MISSION_FEASIBILITY.parquet");weatherdf=pd.read_parquet(S0708/"S07/data/V5_249696_NODE_HOUR_WEATHER.parquet");weatherdf["hour"]=pd.to_datetime(weatherdf.interval_start_utc,utc=True);wmap={(str(r.node_id),r.hour):r for r in weatherdf.itertuples()}
 coords={}
 for r in tasks[["origin_node_id","origin_lat","origin_lon"]].drop_duplicates("origin_node_id").itertuples(index=False):coords[str(r.origin_node_id)]=(float(r.origin_lat),float(r.origin_lon))
 for r in tasks[["destination_node_id","destination_lat","destination_lon"]].drop_duplicates("destination_node_id").itertuples(index=False):coords[str(r.destination_node_id)]=(float(r.destination_lat),float(r.destination_lon))
 cats=mission_catalog(feas,coords);prices=pd.read_csv(S0708/"S08/data/S08_SCENARIO_SUMMARY.csv").set_index(["date_local","scenario_seed"]).petrol_MYR_per_litre.to_dict();selected=pd.read_csv(a.selected_scenarios);selected_keys=set(zip(selected.date_local.astype(str),selected.scenario_seed.astype(int)));groups=[x for x in tasks.groupby(["date_local","scenario_seed"],sort=True) if (str(x[0][0]),int(x[0][1])) in selected_keys];assert len(groups)==len(selected_keys) and len(groups) in (1,900);spatials=[a.spatial]
 ao=[];al=[];af=[];aw=[];aso=[];ae=[];ss=[]
 for i,((date,seed),g) in enumerate(groups,1):
  for spatial in spatials:
   control_frames,control_st=simulate(g,engine,wmap,cats["DJI"],"M1","DJI",False,spatial,a.duty_hours,1.0,"NO_UAV_SHARED")
   if not a.summary_only:
    cl=control_frames[1].copy();cl["mode"]="NO_UAV_SHARED";cl["spatial_scenario"]=spatial;cl["date_local"]=date;cl["scenario_seed"]=seed;al.append(cl)
    ce=control_frames[5].copy();ce["mode"]="NO_UAV_SHARED";ce["spatial_scenario"]=spatial;ce["date_local"]=date;ce["scenario_seed"]=seed;ae.append(ce)
   for arch in ["M1","M2"]:
    mode=f"{arch}_NO_UAV";o=control_frames[0].copy();o["mode"]=mode;o["spatial_scenario"]=spatial;o["date_local"]=date;o["scenario_seed"]=seed;ss.append(summary(mode,spatial,date,seed,o,control_st,prices[(date,seed)],a.duty_hours,1.0))
    if not a.summary_only:ao.append(o)
    for model in ["DJI","WING"]:
     mode=f"{arch}_{model}";emult=a.dji_energy_multiplier if model=="DJI" else a.wing_energy_multiplier;frames,st=simulate(g,engine,wmap,cats[model],arch,model,True,spatial,a.duty_hours,emult,mode);o,l,f,w,so,e=frames
     for x in frames:
      if len(x):x["mode"]=mode;x["spatial_scenario"]=spatial;x["date_local"]=date;x["scenario_seed"]=seed
     ss.append(summary(mode,spatial,date,seed,o,st,prices[(date,seed)],a.duty_hours,emult))
     if not a.summary_only:
      ao.append(o)
      if len(l):al.append(l)
      if len(f):af.append(f)
      if len(w):aw.append(w)
      if len(so):aso.append(so)
      if len(e):ae.append(e)
  if i%50==0 or i==len(groups):print(f"checkpoint {i}/{len(groups)}",flush=True)
 pd.DataFrame(ss).to_csv(out/"SCENARIO_SUMMARY.csv",index=False)
 if not a.summary_only:
  pd.concat(ao,ignore_index=True).to_parquet(out/"ORDER_RESULTS.parquet",index=False)
  for name,arr in [("GROUND_LEGS.parquet",al),("FLIGHTS.parquet",af),("WEATHER_LEDGER.parquet",aw),("SOC_LEDGER.parquet",aso),("EVENT_CLOCK.parquet",ae)]:
   (pd.concat(arr,ignore_index=True) if arr else pd.DataFrame()).to_parquet(out/name,index=False)

if __name__=="__main__":main()
