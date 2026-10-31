"""Read ONLY frozen V5 tasks and compute evidence-limited, payload-only screens.
No road travel, operating energy, flight feasibility or carbon values inferred.
"""
from __future__ import annotations
import csv,collections,datetime,hashlib,json,math,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
INP=ROOT/'inputs'; OUT=ROOT/'outputs'; QA=ROOT/'qa'
CAP_DJI_DUAL_KG=30.0
CAP_WC198_CARGO_KG=4.7
EXPECTED_ZONES={'A','B','C'}
FROZEN_ZIP_SHA='0d19633630b6f12525ad9bd776bbf966ec1e8a46520bd8bc3d904013b02dce74'

def sha256_file(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def geodesic_km(lon1,lat1,lon2,lat2):
 # Spherical Haversine lower bound proxy, not a traversable road/UAV route
 p1,p2=math.radians(lat1),math.radians(lat2)
 a=math.sin((p2-p1)/2)**2+math.cos(p1)*math.cos(p2)*math.sin(math.radians((lon2-lon1)/2))**2
 return 6371.0088*2*math.asin(min(1.0,math.sqrt(a)))

def execute():
 OUT.mkdir(exist_ok=True);QA.mkdir(exist_ok=True)
 zp=next(INP.glob('CIQ_ABC_QGIS322_V5_ONE_WMP228_68_NODES_FULL_PROJECT*.zip'))
 assert sha256_file(zp)==FROZEN_ZIP_SHA,'V5 changed; stop'
 source=INP/'S07_V5_SYNTHETIC_TASKS_CONDITIONAL_DESIGN.csv'
 node_path=INP/'S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv'
 nodes={}
 with node_path.open(encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f):
   assert r['node_id'] not in nodes
   nodes[r['node_id']]=r
 assert len(nodes)==68
 by_month=collections.Counter();by_zone=collections.Counter();by_w=collections.Counter();by_payload=collections.Counter();by_stratum=collections.Counter(); by_deadline=collections.Counter(); ids=set();seeds=set();days=set();distances=[];total=0; bad=[]
 out=OUT/'S08_TASK_PAYLOAD_AND_GEOMETRY_SCREEN_82620_CONDITIONAL.csv'
 cols=['task_id','scenario_seed','release_utc','origin_node_id','destination_node_id','origin_zone','destination_zone','parcel_kg','deadline_minutes','demand_stratum','lower_bound_geodesic_km_NOT_ROAD_OR_FLIGHT_ROUTE','DJI_FC30_DUAL_30KG_PAYLOAD_ONLY','WINGCOPTER198_CARGO_4_7KG_PAYLOAD_ONLY','WINGCOPTER198_PAYLOAD_MARGIN_KG','WINGCOPTER198_MARGIN_LT_0_5KG','M0_PETROL','M1_DJI','M1_WINGCOPTER','M2_DJI','M2_WINGCOPTER','road_route_status','weather_for_flight_status','airspace_status','flight_energy_status','m0_fuel_and_CO2_status','five_mode_result_status']
 with source.open(encoding='utf-8-sig',newline='') as f,out.open('w',encoding='utf-8-sig',newline='') as fw:
  wr=csv.DictWriter(fw,fieldnames=cols);wr.writeheader()
  for r in csv.DictReader(f):
   total+=1;tid=r['task_id']
   if tid in ids:raise AssertionError('Duplicate task_id: '+tid)
   ids.add(tid)
   o,d=r['origin_node_id'],r['destination_node_id']
   if o not in nodes or d not in nodes:raise AssertionError('Task missing V5 node: '+tid)
   if nodes[o]['zone']!=r['origin_zone'] or nodes[d]['zone']!=r['destination_zone']:
    raise AssertionError('Zone mismatch: '+tid)
   if o==d:bad.append(tid)
   for n,prefix in [(o,'origin'),(d,'destination')]:
    for c,nfield in [('longitude_E','lon'),('latitude_N','lat')]:
     if abs(float(r[f'{prefix}_{nfield}'])-float(nodes[n][c]))>1e-7:raise AssertionError('Coordinate changed: '+tid)
   w=float(r['parcel_kg']);assert 0<w<100
   lower=geodesic_km(float(r['origin_lon']),float(r['origin_lat']),float(r['destination_lon']),float(r['destination_lat']))
   dji=w<=CAP_DJI_DUAL_KG;wing=w<=CAP_WC198_CARGO_KG
   by_zone[r['origin_zone']]+=1;by_month[r['date_local'][:7]]+=1
   by_w[w]+=1;by_deadline[r['deadline_minutes']]+=1;by_stratum[r['demand_stratum']]+=1
   by_payload[('DJI_FC30', 'PAYLOAD_ONLY_PASS' if dji else 'PAYLOAD_ONLY_EXCEED')]+=1
   by_payload[('WINGCOPTER198_CARGO','PAYLOAD_ONLY_PASS' if wing else 'PAYLOAD_ONLY_EXCEED')]+=1
   seeds.add(r['scenario_seed']);days.add(r['date_local']);distances.append(lower)
   rr={'task_id':tid,'scenario_seed':r['scenario_seed'],'release_utc':r['release_utc'],'origin_node_id':o,'destination_node_id':d,'origin_zone':r['origin_zone'],'destination_zone':r['destination_zone'],'parcel_kg':w,'deadline_minutes':r['deadline_minutes'],'demand_stratum':r['demand_stratum'],'lower_bound_geodesic_km_NOT_ROAD_OR_FLIGHT_ROUTE':round(lower,6),
   'DJI_FC30_DUAL_30KG_PAYLOAD_ONLY':'PASS_WEIGHT_ONLY' if dji else 'OVERWEIGHT_ROUTE_TO_CAR',
   'WINGCOPTER198_CARGO_4_7KG_PAYLOAD_ONLY':'PASS_WEIGHT_ONLY' if wing else 'OVERWEIGHT_ROUTE_TO_CAR',
   'WINGCOPTER198_PAYLOAD_MARGIN_KG':round(CAP_WC198_CARGO_KG-w,3),
   'WINGCOPTER198_MARGIN_LT_0_5KG':'YES_PACKAGING_AND_HANDLING_UNVERIFIED' if 0<=CAP_WC198_CARGO_KG-w<.5 else 'NO',
   'M0_PETROL':'IN_COMMON_DEMAND_DENOMINATOR',
   'M1_DJI':'IN_COMMON_DEMAND_DENOMINATOR','M1_WINGCOPTER':'IN_COMMON_DEMAND_DENOMINATOR','M2_DJI':'IN_COMMON_DEMAND_DENOMINATOR','M2_WINGCOPTER':'IN_COMMON_DEMAND_DENOMINATOR',
   'road_route_status':'HOLD_DIRECTED_ABC_ROAD_GRAPH',
   'weather_for_flight_status':'HOLD_RAW_WEATHER_HOURLY',
   'airspace_status':'HOLD_AUTHORIZATION_AND_CORRIDOR',
   'flight_energy_status':'HOLD_MISSION_ENERGY_CALIBRATION',
   'm0_fuel_and_CO2_status':'HOLD_PHYSICAL_ROAD_LEGS_AND_PETROL_PARAMS',
   'five_mode_result_status':'NOT_SIMULATED'}
   wr.writerow(rr)
 assert total==82620 and len(seeds)==30 and len(days)==153
 assert by_zone=={'A':27540,'B':27540,'C':27540}
 assert not bad,'self OD present: '+str(bad[:3])
 assert by_payload[('WINGCOPTER198_CARGO','PAYLOAD_ONLY_EXCEED')]==27540
 res={
 'stage':'S08_DEV_PAYLOAD_SCREEN','status':'EXECUTED_PAYLOAD_ONLY__FULL_SIM_HOLD',
 'v5_spatial_basis_sha256':sha256_file(zp),
 'frozen_task_file_sha256':sha256_file(source),
 'task_count':total,'distinct_task_ids':len(ids),'seed_count':len(seeds),'day_count':len(days),
 'by_origin_zone':dict(by_zone),'by_month':dict(sorted(by_month.items())),
 'by_payload_kg':{str(k):v for k,v in sorted(by_w.items())},
 'by_deadline_minutes':dict(by_deadline),'by_demand_stratum':dict(by_stratum),
 'wingcopter198_cargo_within_0_5kg_of_nominal_payload':by_w.get(4.5,0),
 'wingcopter198_near_limit_warning':'4.5 kg tasks have 0.2 kg nominal margin; packaging/winch and other payload mass must be defined, not operationally approved',
 'payload_only':{aircraft:{state:by_payload[(aircraft,state)] for state in ['PAYLOAD_ONLY_PASS','PAYLOAD_ONLY_EXCEED']} for aircraft in ['DJI_FC30','WINGCOPTER198_CARGO']},
 'geodesic_lower_bound_km_statistics_NOT_ROUTE':{'min':min(distances),'mean':sum(distances)/len(distances),'max':max(distances)},
 'no_real_road_mileage_computed':True,'no_operational_flight_eligibility_claimed':True,
 'no_actual_operational_carbon_or_cost_computed':True,'all_five_modes_identical_task_denominator':True,
 'required_next_inputs':['accepted_V5_ABC_directed_road_graph_and_access','actual_2026_May_Sep_weather_hourly_data','sourced_petrol_consumption_and_fuel_chemistry','two_UAV_mission_energy_models','verified_dispatch_policy_and_resource_constraints'],
 'interpretation':'Conditional synthetic tasks only, no observed company orders or real deployment claims'}
 (QA/'S08_REAL_TASK_SCREEN_AUDIT.json').write_text(json.dumps(res,indent=2,ensure_ascii=False),encoding='utf-8')
 return res

if __name__=='__main__':
 print(json.dumps(execute(),ensure_ascii=False,indent=2))
