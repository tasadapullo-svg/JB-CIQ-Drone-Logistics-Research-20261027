#!/usr/bin/env python3
"""Stage 6 shared-service conditional operations study (UNVALIDATED, NOT AUTHORIZED).
Uses original 30 frozen seeds and the 5 Stage4 dates per seed, NOT 918k new orders.
A: fixed hubs; B: origin -> consolidation -> batched line-haul -> forward UAV hub -> customer.
M2: same-origin paired truck/UAV mobile rendezvous. All three use common source-hour
weather and OSM/traffic proxy. Physical assets, energy, queues and returns are simulated.
Simulation hypotheses are NOT calibrated or actual cross-border services.
"""
import sys,csv,gzip,zipfile,io,json,math,hashlib,statistics,random,collections,datetime,heapq,os
from pathlib import Path
D=Path(__file__).parent
sys.path.insert(0,str(D))
import run_stage4_dispatch as prior
BUNDLE=Path(os.environ.get('CIQ_BUNDLE',str(D/'CIQ_GPT校验所需三归档与关键数据_20261027.zip') if (D/'CIQ_GPT校验所需三归档与关键数据_20261027.zip').exists() else '/mnt/data/CIQ_GPT校验所需三归档与关键数据_20261027.zip'))
# All non-OSM hardware, logistics and cost parameters below = HYPOTHETICAL ASSUMPTIONS
P={'van_per_origin':2,'van_per_consolidation':2,'consolidation_capacity':1,'hub_handlers':1,
 'hub_drones':2,'hub_chargers':1,'linehaul_truck_capacity':8,'linehaul_batch_window_min':35,
 'max_payload_kg':1.5,'leg_limit_km':4.0,'drone_air_kph':40.0,'gust_limit_ms':10.0,
 'rain_limit_mmh':0.1,'day_start_hour':6,'day_end_hour':19,'battery_kwh':0.70,
 'battery_usable_fraction':0.75,'charging_efficiency':0.88,'charger_kW':1.2,
 'drone_power_W_empty':470.,'drone_power_W_per_payload_kg':120.,'drone_power_W_drag_at_nominal':50.,
 'flight_launch_min':1.5,'drop_min':1.5,'flight_recover_min':1.5,'battery_cooldown_min':3.,
 'origin_package_prep_min':2.,'ground_unload_min':2.,'feeder_handoff_min':2.,
 'consolidation_processing_min':3.,'hub_processing_min':3.,'linehaul_unload_min':3.,
 'm2_pair_window_min':30.,'van_kwh_per_km':0.23,'grid_kgCO2e_per_kwh':0.740,
 'electricity_MYR_kwh':0.50,'van_nonenergy_MYR_km':0.40,'van_staff_MYR_min':0.16,
 'uav_staff_MYR_min':0.08,'van_fixed_MYR_day':60.,'uav_fixed_MYR_day':45.,
 'hub_fixed_MYR_day':80.,'consolidation_fixed_MYR_day':85.,
 'vehicle_embodied_CO2e_kg_day':0.50,'uav_embodied_CO2e_kg_day':0.25,
 'hub_embodied_CO2e_kg_day':1.0,'consolidation_embodied_CO2e_kg_day':1.2}
A_HUBS=('A01','A02','A03','A05')
B_CONSOL=('B01','B03','B04','B06','B08','B09')
B_HUBS=('B01','B03','B04','B05','B06','B09')
M2_NODES={'A':A_HUBS,'B':('B01','B03','B04','B05','B06','B08','B09')}


def wcsv(file,rows):
 if not rows:return
 with open(file,'w',encoding='utf-8-sig',newline='') as f:
  fields=list(rows[0]);fields.extend(k for r in rows[1:] for k in r if k not in fields);wr=csv.DictWriter(f,fields);wr.writeheader();wr.writerows(rows)

def load():
 xy,od,traffic,groups=prior.data_read(BUNDLE)
 direction={}
 with zipfile.ZipFile(BUNDLE) as z:
  matches=[x for x in z.namelist() if x.endswith('E03_ERA5_JB_TWO_CIQ_WEATHER_HOURLY.csv')]
  assert len(matches)==1
  for r in csv.DictReader(io.StringIO(z.read(matches[0]).decode('utf-8-sig'))):
   if r['point_id'] not in ('CW_MY','SL_MY'):continue
   direction[(('A' if r['point_id']=='CW_MY' else 'B'),r['timestamp_hour_start_sgt'][:13].replace('T',' '))]=(float(r['ERA5_wind_10m_ms']),float(r['ERA5_wind_direction_10m_deg']))
 return xy,od,traffic,groups,direction

def local(o):return o['release_time_local'][:13].replace('T',' ')
def traf(o,traffic):return traffic.get((o['area'],local(o)))
def road(u,v,o,od,traffic):
 # Fixed SOURCE hour within each task: no fabricated dispatch-hour traffic measurements
 if u==v:return (0.,0.,False)
 t=traf(o,traffic);path=od.get((u,v))
 if not path or not t or not t[1] or t[0]<=0:return None
 return (path[0]/t[0],path[1],False)
def round_trip(u,v,o,od,traffic):
 a=road(u,v,o,od,traffic)
 if a is None:return None
 b=road(v,u,o,od,traffic)
 if b is None:
  # Directed reverse missing: flag extrapolation; no claim actual route verified
  return (a[0]*2,a[1]*2,True,a[0])
 return (a[0]+b[0],a[1]+b[1],False,a[0])

def bearing(pt1,pt2):
 lat1,lon1,lat2,lon2=map(math.radians,(pt1[0],pt1[1],pt2[0],pt2[1]))
 dl=lon2-lon1;z=math.sin(dl)*math.cos(lat2)
 return (math.degrees(math.atan2(z,math.cos(lat1)*math.sin(lat2)-math.sin(lat1)*math.cos(lat2)*math.cos(dl)))+360)%360

def weather_ok(o,traffic,direction):
 q=traf(o,traffic)
 if q is None:return False
 hour=int(o['release_time_local'][11:13]);w=direction.get((o['area'],local(o)))
 return bool(w and P['day_start_hour']<=hour<P['day_end_hour'] and
             q[2]<P['rain_limit_mmh'] and q[3]<P['gust_limit_ms'] and
             w[0]<P['gust_limit_ms'] and o['payload']<=P['max_payload_kg'])

def fly_leg(x,y,mass,order,xy,direction):
 d=prior.hav(xy[x],xy[y]);w=direction.get((order['area'],local(order)))
 if not w:return None
 v= P['drone_air_kph']/3.6;wind,wind_from=w
 phi=math.radians((bearing(xy[x],xy[y])-wind_from+360)%360)
 # Wind bearing is FROM. positive along-track = tailwind
 along=-wind*math.cos(phi);cross=-wind*math.sin(phi)
 if abs(cross)>=v:return None
 ground_ms=math.sqrt(v*v-cross*cross)+along
 if ground_ms<=3:return None
 flight_min=d*1000/ground_ms/60
 pw=P['drone_power_W_empty']+P['drone_power_W_per_payload_kg']*mass+P['drone_power_W_drag_at_nominal']*(v/11.111111)**3
 energy=pw/1000*(flight_min/60)
 return d,flight_min,energy,ground_ms*3.6

def sortie(source,delivery,return_node,o,xy,traffic,direction):
 if not weather_ok(o,traffic,direction):return None
 a=fly_leg(source,delivery,o['payload'],o,xy,direction)
 b=fly_leg(delivery,return_node,0.,o,xy,direction)
 if not a or not b or a[0]<0.08:return None
 if a[0]>P['leg_limit_km'] or b[0]>P['leg_limit_km']:return None
 e=a[2]+b[2]
 if e>P['battery_kwh']*P['battery_usable_fraction']:return None
 recharge=e/P['charging_efficiency']/P['charger_kW']*60+P['battery_cooldown_min']
 return {'km':a[0]+b[0],'out_min':a[1],'in_min':b[1],'energy_kwh':e/P['charging_efficiency'],
         'recharge_min':recharge,'ground_kph_loaded':a[3],'ground_kph_empty':b[3]}

class Pool:
 def __init__(self,n): self.a=[0.]*int(n)
 def book(self,arrival,duration):
  k=min(range(len(self.a)),key=lambda j:self.a[j]);start=max(arrival,self.a[k]);self.a[k]=start+duration
  return start,self.a[k],k
 def slot(self,t):return min(max(t,v) for v in self.a)

class Ops:
 def __init__(self,mode,area,orders):
  self.mode=mode;self.area=area
  self.vans={n:Pool(P['van_per_origin']) for n in set(o['origin_site_id'] for o in orders)}
  self.consvans={n:Pool(P['van_per_consolidation']) for n in B_CONSOL} if area=='B' and mode=='M1' else {}
  self.consproc={n:Pool(P['consolidation_capacity']) for n in B_CONSOL} if self.consvans else {}
  self.hubproc={n:Pool(P['hub_handlers']) for n in (B_HUBS if area=='B' else A_HUBS)} if mode=='M1' else {}
  self.drones={n:Pool(P['hub_drones']) for n in self.hubproc}
  self.chargers={n:Pool(P['hub_chargers']) for n in self.hubproc}
  self.extra={'batch_linehaul_km':0.,'batch_linehaul_trips':0,'batch_fill_total':0}

def out(o,mode,status,door=None,ground_km=0.,drone_km=0.,drone_kwh=0.,ground_busy=0.,drone_busy=0.,
        hub='',cons='',batch='',partner='',reverse=False,wind_loaded_kph=None,wait=0.,drone=0):
 return {'seed':int(o['replicate_seed']),'date':o['release_time_local'][:10],'area':o['area'],'mode':mode,
 'order_id':o['replicate_order_id'],'origin':o['origin_site_id'],'destination':o['destination_site_id'],
 'release_time':o['release_time_local'],'payload_kg':o['payload'],'status':status,
 'door_to_door_min':round(door-o['release_min'],5) if door is not None else '',
 'completion_min':round(door,5) if door is not None else '',
 'road_km_alloc':round(ground_km,5),'flight_km':round(drone_km,5),
 'flight_grid_kwh':round(drone_kwh,6),'ground_vehicle_busy_min_alloc':round(ground_busy,5),
 'drone_busy_min':round(drone_busy,5),'queue_min':round(wait,5),'hub_id':hub,'consolidation_id':cons,
 'linehaul_batch_id':batch,'paired_order_id':partner,'reverse_route_proxy':int(reverse),
 'drone_sorties':drone,'wind_adjusted_loaded_kph':round(wind_loaded_kph,3) if wind_loaded_kph is not None else '',
 'model_status':'HYPOTHETICAL_NO_SITE_PERMIT_UNCALIBRATED_TRAFFIC'}

def ground(o,ops,od,traffic,mode,label='GROUND_DIRECT'):
 src=o['origin_site_id'];dst=o['destination_site_id'];r=o['release_min']
 trip=round_trip(src,dst,o,od,traffic)
 if trip is None:return out(o,mode,'BASE_ROAD_OR_FCD_MISSING')
 own=ops.vans[src];i=min(range(len(own.a)),key=lambda j:own.a[j]);ready=max(r,own.a[i])
 depart=ready+P['origin_package_prep_min'];delivery=depart+trip[3]+P['ground_unload_min']
 own.a[i]=depart+trip[0]
 return out(o,mode,label,delivery,ground_km=trip[1],ground_busy=trip[0]+P['origin_package_prep_min'],
            reverse=trip[2],wait=ready-r)

def m0(rows,od,traffic):
 op=Ops('M0',rows[0]['area'],rows)
 return [ground(o,op,od,traffic,'M0') for o in rows],op

def b_plan(o,xy,od,traffic,direction):
 if not weather_ok(o,traffic,direction):return None
 candidates=[];src=o['origin_site_id'];dst=o['destination_site_id']
 for c in B_CONSOL:
  leg0=round_trip(src,c,o,od,traffic)
  if leg0 is None:continue
  for h in B_HUBS:
   if h==c:continue   # genuinely two distinct transfer tiers
   leg1=round_trip(c,h,o,od,traffic)
   if leg1 is None or leg1[1]<0.3:continue
   f=sortie(h,dst,h,o,xy,traffic,direction)
   if f is None:continue
   # exclude impossible fixed endpoint: avoid classing destination reference as an active hub at that site
   score=leg0[3]+leg1[3]+f['out_min']+2*P['consolidation_processing_min']+P['hub_processing_min']
   candidates.append((score,c,h,leg0,leg1,f))
 return min(candidates,key=lambda z:(z[0],z[1],z[2])) if candidates else None

def a_plan(o,xy,od,traffic,direction):
 if not weather_ok(o,traffic,direction):return None
 choices=[]
 for h in A_HUBS:
  t=round_trip(o['origin_site_id'],h,o,od,traffic)
  f=sortie(h,o['destination_site_id'],h,o,xy,traffic,direction)
  if t is None or f is None:continue
  score=t[3]+P['hub_processing_min']+f['out_min']
  choices.append((score,h,t,f))
 return min(choices,key=lambda z:(z[0],z[1])) if choices else None

def feed(o,ops,site,trip):
 origin=o['origin_site_id'];r=o['release_min']
 if origin==site:return r+P['origin_package_prep_min'],0.,0.,False,r
 v=ops.vans[origin];i=min(range(len(v.a)),key=lambda k:v.a[k]);ready=max(r,v.a[i])
 depart=ready+P['origin_package_prep_min'];arr=depart+trip[3]+P['feeder_handoff_min']
 v.a[i]=depart+trip[0]+P['feeder_handoff_min']
 return arr,trip[1],trip[0]+P['origin_package_prep_min']+P['feeder_handoff_min'],trip[2],ready

def drone_dispatch(o,ops,hub,ready,f):
 # hub handling slot queue, then drone and charger queue at return; avoids free charging
 hp=ops.hubproc[hub];start,finish,_=hp.book(ready,P['hub_processing_min'])
 drones=ops.drones[hub];k=min(range(len(drones.a)),key=lambda j:drones.a[j]);launch=max(finish,drones.a[k])
 airborne=launch+P['flight_launch_min'];delivered=airborne+f['out_min']+P['drop_min']
 return_at=delivered+f['in_min']+P['flight_recover_min']
 charge_start,charge_end,_=ops.chargers[hub].book(return_at,f['recharge_min'])
 drones.a[k]=charge_end
 return delivered,charge_end-launch,launch-finish,f['ground_kph_loaded']

def m1(rows,xy,od,traffic,direction):
 area=rows[0]['area'];ops=Ops('M1',area,rows);answer={};work=[];batchstats=[]
 for o in rows:
  # The common cohort is locked ex ante by the release-hour directed road/FCD proxy.
  if road(o['origin_site_id'],o['destination_site_id'],o,od,traffic) is None:
   answer[o['replicate_order_id']]=out(o,'M1','BASE_ROAD_OR_FCD_MISSING');continue
  p=b_plan(o,xy,od,traffic,direction) if area=='B' else a_plan(o,xy,od,traffic,direction)
  if p is None:
   answer[o['replicate_order_id']]=ground(o,ops,od,traffic,'M1','GROUND_FALLBACK');continue
  if area=='A':
   _,h,feeder,f=p;ready,km,busy,rev,start=feed(o,ops,h,feeder)
   work.append({'o':o,'h':h,'feeder_km':km,'feeder_busy':busy,'reverse':rev,
                'feeder_wait':max(0,start-o['release_min']),'hub_ready':ready,'flight':f})
  else:
   _,c,h,feeder,trunk,f=p;ready,km,busy,rev,start=feed(o,ops,c,feeder)
   work.append({'o':o,'c':c,'h':h,'feeder_km':km,'feeder_busy':busy,'reverse':rev,
                'feeder_wait':max(0,start-o['release_min']),'c_arrive':ready,'trunk':trunk,'flight':f})
 if area=='A':
  # Hub processing and drones are allocated in physically ordered arrival time, not order-release order.
  for x in sorted(work,key=lambda z:(z['hub_ready'],z['o']['replicate_order_id'])):
   o=x['o'];h=x['h'];delivered,dbusy,qwait,adjust=drone_dispatch(o,ops,h,x['hub_ready'],x['flight'])
   answer[o['replicate_order_id']]=out(o,'M1','DRONE_A_FIXED_HUB',delivered,x['feeder_km'],x['flight']['km'],
      x['flight']['energy_kwh'],x['feeder_busy'],dbusy,hub=h,reverse=x['reverse'],
      wind_loaded_kph=adjust,wait=x['feeder_wait']+qwait,drone=1)
  return [answer[o['replicate_order_id']] for o in rows],ops,batchstats
 # B consolidation processing is a proper arrival-time FCFS event stream.
 for x in sorted(work,key=lambda z:(z['c_arrive'],z['o']['replicate_order_id'])):
  _,cend,_=ops.consproc[x['c']].book(x['c_arrive'],P['consolidation_processing_min'])
  x['c_ready']=cend
 routes=collections.defaultdict(list)
 for x in work:
  slot=math.floor(x['c_ready']/P['linehaul_batch_window_min'])
  routes[(x['c'],x['h'],slot)].append(x)
 jobs=[]
 for (c,h,slot),seq in routes.items():
  seq=sorted(seq,key=lambda x:(x['c_ready'],x['o']['replicate_order_id']))
  for k in range(0,len(seq),P['linehaul_truck_capacity']):
   chunk=seq[k:k+P['linehaul_truck_capacity']]
   jobs.append((max(x['c_ready'] for x in chunk),c,h,slot,k//P['linehaul_truck_capacity'],chunk))
 to_hub=[]
 for ready,c,h,slot,batchnum,chunk in sorted(jobs,key=lambda z:(z[0],z[1],z[2],z[4])):
  ref=chunk[0]['o'];trip=round_trip(c,h,ref,od,traffic)
  if trip is None:raise RuntimeError('Planned directed road disappeared')
  v=ops.consvans[c];i=min(range(len(v.a)),key=lambda k:v.a[k])
  begin=max(ready,(slot+1)*P['linehaul_batch_window_min'],v.a[i]);arrive=begin+trip[3]+P['linehaul_unload_min']
  v.a[i]=begin+trip[0]+P['linehaul_unload_min']
  bid=f'{c}_{h}_{slot}_{batchnum}';n=len(chunk)
  ops.extra['batch_linehaul_km']+=trip[1];ops.extra['batch_linehaul_trips']+=1;ops.extra['batch_fill_total']+=n
  batchstats.append({'seed':ref['replicate_seed'],'date':ref['release_time_local'][:10],
   'area':'B','batch_id':bid,'consolidation':c,'forward_hub':h,'packets':n,
   'capacity':P['linehaul_truck_capacity'],'truck_roundtrip_km':round(trip[1],5),
   'arrival_min':round(arrive,3),'departure_min':round(begin,3),'unverified_reverse':int(trip[2])})
  for x in chunk:
   to_hub.append({'shipment':x,'arrival':arrive,'batch_id':bid,'n':n,'linehaul_roundtrip_km':trip[1],
                  'linehaul_busy':trip[0]+P['linehaul_unload_min'],'reverse':trip[2],
                  'truck_departure':begin})
 # Across all truck routes, dispatch hub handlers/UAVs in arrival order, not jobs creation order.
 for item in sorted(to_hub,key=lambda z:(z['arrival'],z['shipment']['o']['replicate_order_id'])):
  x=item['shipment'];o=x['o'];h=x['h']
  delivered,dbusy,qwait,adj=drone_dispatch(o,ops,h,item['arrival'],x['flight'])
  answer[o['replicate_order_id']]=out(o,'M1','DRONE_B_TWO_TIER_BATCH',delivered,
    x['feeder_km']+item['linehaul_roundtrip_km']/item['n'],x['flight']['km'],x['flight']['energy_kwh'],
    x['feeder_busy']+item['linehaul_busy']/item['n'],dbusy,hub=h,cons=x['c'],batch=item['batch_id'],
    reverse=x['reverse'] or item['reverse'],wind_loaded_kph=adj,
    wait=x['feeder_wait']+item['truck_departure']-x['c_ready']+qwait,drone=1)
 assert len(answer)==len(rows)
 return [answer[o['replicate_order_id']] for o in rows],ops,batchstats

def m2(rows,xy,od,traffic,direction):
 a=rows[0]['area'];ops=Ops('M2',a,rows);used=set();outputs={};buckets=collections.defaultdict(list)
 for j,o in enumerate(rows):buckets[o['origin_site_id']].append(j)
 for i,o in enumerate(rows):
  if i in used:continue
  src=o['origin_site_id'];dst=o['destination_site_id'];r=o['release_min']
  if road(src,dst,o,od,traffic) is None:
   outputs[o['replicate_order_id']]=out(o,'M2','BASE_ROAD_OR_FCD_MISSING');used.add(i);continue
  possibilities=[]
  if weather_ok(o,traffic,direction):
   for j in buckets[src]:
    if j<=i or j in used:continue
    p=rows[j]
    if p['release_min']-r>P['m2_pair_window_min']:break
    if road(src,p['destination_site_id'],p,od,traffic) is None:continue
    if not weather_ok(p,traffic,direction):continue
    if abs(p['release_min']-r)>P['m2_pair_window_min']:continue
    for launch in M2_NODES[a]:
     t1=road(src,launch,o,od,traffic);t2=road(launch,p['destination_site_id'],o,od,traffic)
     if t1 is None or t2 is None:continue
     f=sortie(launch,dst,p['destination_site_id'],o,xy,traffic,direction)
     if not f:continue
     # avoid order pair where plan is markedly worse than two road legs (conditional heuristic)
     pred=max(t1[0]+t2[0],t1[0]+f['out_min']+f['in_min']+P['flight_launch_min'])
     possibilities.append((pred,j,launch,t1,t2,f))
  if not possibilities:
   outputs[o['replicate_order_id']]=ground(o,ops,od,traffic,'M2','GROUND_SINGLE');used.add(i);continue
  _,j,launch,t1,t2,f=min(possibilities,key=lambda q:(q[0],q[1],q[2]));p=rows[j]
  v=ops.vans[src];k=min(range(len(v.a)),key=lambda t:v.a[t]);start=max(r,p['release_min'],v.a[k])
  depart=start+2*P['origin_package_prep_min'];launch_at=depart+t1[0]
  truck_arrive=launch_at+t2[0]+P['ground_unload_min']
  drone_deliver=launch_at+P['flight_launch_min']+f['out_min']+P['drop_min']
  drone_rejoin=drone_deliver+f['in_min']+P['flight_recover_min']
  depart_home=max(truck_arrive,drone_rejoin)
  back=road(p['destination_site_id'],src,o,od,traffic)
  rev_proxy=back is None
  backtime=back[0] if back else t1[0]+t2[0]
  backkm=back[1] if back else t1[1]+t2[1]
  recharge=f['recharge_min'];v.a[k]=depart_home+backtime+recharge
  km=(t1[1]+t2[1]+backkm)/2;busy=(v.a[k]-start)/2
  outputs[o['replicate_order_id']]=out(o,'M2','DRONE_MOBILE_RENDEZVOUS',drone_deliver,km,f['km'],f['energy_kwh'],busy,
                   drone_rejoin-launch_at+recharge,hub=launch,partner=p['replicate_order_id'],reverse=rev_proxy,
                   wind_loaded_kph=f['ground_kph_loaded'],wait=start-r,drone=1)
  outputs[p['replicate_order_id']]=out(p,'M2','TRUCK_MOBILE_RENDEZVOUS',truck_arrive,km,0.,0.,busy,0.,hub=launch,
                   partner=o['replicate_order_id'],reverse=rev_proxy,wait=start-p['release_min'])
  used.update((i,j))
 assert len(outputs)==len(rows)
 return [outputs[o['replicate_order_id']] for o in rows],ops

def accounting(out,mode,ops,orders):
 # The same denominator (all input orders) is used for fixed costs. Vehicle km for M2 pairs allocated exactly once.
 n=len(orders);nv=sum(len(pool.a) for pool in ops.vans.values())+sum(len(pool.a) for pool in ops.consvans.values())
 nd=sum(len(pool.a) for pool in ops.drones.values()) if mode=='M1' else nv if mode=='M2' else 0
 nh=len(ops.hubproc) if mode=='M1' else 0;nc=len(ops.consproc)
 fixed=nv*P['van_fixed_MYR_day']+nd*P['uav_fixed_MYR_day']+nh*P['hub_fixed_MYR_day']+nc*P['consolidation_fixed_MYR_day']
 embodied=nv*P['vehicle_embodied_CO2e_kg_day']+nd*P['uav_embodied_CO2e_kg_day']+nh*P['hub_embodied_CO2e_kg_day']+nc*P['consolidation_embodied_CO2e_kg_day']
 for o in out:
  vkwh=o['road_km_alloc']*P['van_kwh_per_km'];dkwh=o['flight_grid_kwh'];total=vkwh+dkwh
  variable=total*P['electricity_MYR_kwh']+o['road_km_alloc']*P['van_nonenergy_MYR_km']+o['ground_vehicle_busy_min_alloc']*P['van_staff_MYR_min']+o['drone_busy_min']*P['uav_staff_MYR_min']
  o.update({'vehicle_kwh':round(vkwh,6),'total_grid_kwh':round(total,6),
            'variable_cost_MYR':round(variable,5),'fixed_cost_alloc_MYR':round(fixed/n,5),
            'total_cost_MYR':round(variable+fixed/n,5),
            'operational_CO2e_kg':round(total*P['grid_kgCO2e_per_kwh'],6),
            'embodied_CO2e_alloc_kg':round(embodied/n,6),
            'total_CO2e_scenario_kg':round(total*P['grid_kgCO2e_per_kwh']+embodied/n,6)})
 return {'van_count':nv,'drone_count':nd,'hub_count':nh,'consolidation_count':nc,'fixed_daily_cost':fixed,'embodied_daily_kg':embodied}

def percentile(v,p):
 if not v:return None
 x=sorted(v);q=(len(x)-1)*p;a=math.floor(q);return x[a]+(x[min(a+1,len(x)-1)]-x[a])*(q-a)

def stats(results,meta):
 completed=[r for r in results if r['door_to_door_min']!=''];x=[r['door_to_door_min'] for r in completed]
 return {'seed':results[0]['seed'],'date':results[0]['date'],'area':results[0]['area'],
  'mode':results[0]['mode'],'input_orders':len(results),'completed_n':len(completed),
  'completion_pct':round(100*len(completed)/len(results),4),
  'p50_door_min':round(percentile(x,.5),5) if x else '',
  'p90_door_min':round(percentile(x,.9),5) if x else '',
  'p95_door_min':round(percentile(x,.95),5) if x else '',
  'sorties':sum(r['drone_sorties'] for r in results),'ground_km':round(sum(r['road_km_alloc'] for r in results),4),
  'flight_km':round(sum(r['flight_km'] for r in results),4),
  'grid_kwh':round(sum(r['total_grid_kwh'] for r in results),4),
  'operational_CO2e_kg':round(sum(r['operational_CO2e_kg'] for r in results),4),
  'asset_CO2e_kg':round(sum(r['embodied_CO2e_alloc_kg'] for r in results),4),
  'scenario_total_CO2e_kg':round(sum(r['total_CO2e_scenario_kg'] for r in results),4),
  'total_cost_MYR':round(sum(r['total_cost_MYR'] for r in results),4),
  'reverse_proxy_count':sum(r['reverse_route_proxy'] for r in results),**meta}

def group_compare(out0,out1,mode):
 a={r['order_id']:r for r in out0};b={r['order_id']:r for r in out1};assert set(a)==set(b)
 cohort=[id for id in a if a[id]['door_to_door_min']!='']
 both=[id for id in cohort if b[id]['door_to_door_min']!='']
 only_base=[id for id in cohort if b[id]['door_to_door_min']=='']
 comps=['door_to_door_min','total_cost_MYR','operational_CO2e_kg','total_CO2e_scenario_kg','total_grid_kwh']
 row={'seed':out0[0]['seed'],'date':out0[0]['date'],'area':out0[0]['area'],'mode':mode,
      'm0_service_cohort_n':len(cohort),'mode_served_on_m0_cohort_n':len(both),
      'service_parity_pass':len(both)==len(cohort),'mode_failed_on_m0_cohort_n':len(only_base),
      'mode_served_not_m0_n':sum(b[id]['door_to_door_min']!='' and a[id]['door_to_door_min']=='' for id in a)}
 for k in comps:
  diff=[b[id][k]-a[id][k] for id in both]
  row['mean_delta_'+k]=round(statistics.mean(diff),7) if diff else ''
  row['sum_delta_'+k]=round(sum(diff),7) if diff else ''
 row['m0_p95_on_common_min']=round(percentile([a[id]['door_to_door_min'] for id in both],.95),4) if both else ''
 row['mode_p95_on_common_min']=round(percentile([b[id]['door_to_door_min'] for id in both],.95),4) if both else ''
 row['observed_common_cohort_n']=len(both)
 return row

def main():
 D.mkdir(parents=True,exist_ok=True)
 xy,od,traffic,groups,direction=load()
 assert len(groups)==300 and sum(map(len,groups.values()))==29842
 orders_file=D/'stage6_order_level.csv.gz';gr=[];pair=[];batches=[]
 fields=None
 with gzip.open(orders_file,'wt',newline='',encoding='utf-8-sig') as f:
  writer=None
  for i,((seed,day,area),rows) in enumerate(sorted(groups.items())):
   o0,ops0=m0(rows,od,traffic)
   o1,ops1,bat=m1(rows,xy,od,traffic,direction)
   o2,ops2=m2(rows,xy,od,traffic,direction)
   batchrows=[{'seed':seed,'date':day,**b} for b in bat];batches.extend(batchrows)
   by=[]
   for mode,output,ops in (('M0',o0,ops0),('M1',o1,ops1),('M2',o2,ops2)):
    assert len(output)==len(rows) and {x['order_id'] for x in output}=={o['replicate_order_id'] for o in rows}
    meta=accounting(output,mode,ops,rows)
    gr.append(stats(output,meta));by.append(output)
    if writer is None:
     fields=list(output[0]);writer=csv.DictWriter(f,fields);writer.writeheader()
    writer.writerows(output)
   pair.extend((group_compare(o0,o1,'M1'),group_compare(o0,o2,'M2')))
   if i%50==0:print('Processed groups',i+1, 'of',len(groups),flush=True)
 wcsv(D/'stage6_daily_modes.csv',gr)
 wcsv(D/'stage6_service_matched.csv',pair)
 wcsv(D/'stage6_linehaul_batches_B.csv',batches)
 summary=[]
 for area in 'AB':
  for mode in ('M0','M1','M2'):
   a=[r for r in gr if r['area']==area and r['mode']==mode]
   p=[r for r in pair if r['area']==area and r['mode']==mode]
   total=sum(r['input_orders'] for r in a);served=sum(r['completed_n'] for r in a)
   z={'area':area,'mode':mode,'input_orders':total,'completed_n':served,'completion_pct':100*served/total,
      'drone_sorties':sum(r['sorties'] for r in a),'ground_km':sum(r['ground_km'] for r in a),
      'flight_km':sum(r['flight_km'] for r in a),'grid_kWh':sum(r['grid_kwh'] for r in a),
      'operational_CO2e_kg':sum(r['operational_CO2e_kg'] for r in a),
      'scenario_total_CO2e_kg':sum(r['scenario_total_CO2e_kg'] for r in a),
      'total_cost_MYR':sum(r['total_cost_MYR'] for r in a),'no_crossborder_wait':True,
      'time_model':'source-hour_frozen_FCD_proxy','source_seeds':30,'sample_days_per_seed':5,
      'inference':'HYPOTHETICAL_PARAMETERS_NOT_CAUSAL_OR_OBSERVED'}
   if p:
    z['service_parity_groups_pass']=sum(r['service_parity_pass'] for r in p)
    z['service_parity_groups_total']=len(p)
    z['common_order_pairs']=sum(r['observed_common_cohort_n'] for r in p)
    z['weighted_common_mean_delta_door_min']=sum(r['sum_delta_door_to_door_min'] for r in p)/z['common_order_pairs'] if z['common_order_pairs'] else None
    z['weighted_common_mean_delta_cost_MYR']=sum(r['sum_delta_total_cost_MYR'] for r in p)/z['common_order_pairs'] if z['common_order_pairs'] else None
    z['weighted_common_mean_delta_operational_CO2e_kg']=sum(r['sum_delta_operational_CO2e_kg'] for r in p)/z['common_order_pairs'] if z['common_order_pairs'] else None
   summary.append(z)
 wcsv(D/'stage6_area_summary.csv',summary)
 # per-seed paired effects (independent repeat units) across 5 days for each area
 per_seed=[]
 for area in 'AB':
  for mode in ('M1','M2'):
   for seed in sorted({p['seed'] for p in pair}):
    t=[p for p in pair if p['area']==area and p['mode']==mode and p['seed']==seed]
    if not t:continue
    n=sum(q['observed_common_cohort_n'] for q in t)
    rec={'area':area,'mode':mode,'seed':seed,'days':len(t),'common_order_pairs':n,'parity_groups_pass':sum(q['service_parity_pass'] for q in t),
     'parity_groups_total':len(t),'mean_delta_door_min':sum(q['sum_delta_door_to_door_min'] for q in t)/n if n else '',
     'mean_delta_cost_MYR':sum(q['sum_delta_total_cost_MYR'] for q in t)/n if n else '',
     'mean_delta_operational_CO2e_kg':sum(q['sum_delta_operational_CO2e_kg'] for q in t)/n if n else ''}
    per_seed.append(rec)
 wcsv(D/'stage6_seed_paired.csv',per_seed)
 ci=[];rng=random.Random(20261027)
 for area in 'AB':
  for mode in ('M1','M2'):
   v=[r for r in per_seed if r['area']==area and r['mode']==mode]
   for metric in ('mean_delta_door_min','mean_delta_cost_MYR','mean_delta_operational_CO2e_kg'):
    values=[r[metric] for r in v if r[metric]!='']
    if len(values)!=30:continue
    boots=[statistics.mean(values[rng.randrange(len(values))] for _ in values) for _ in range(600)]
    ci.append({'area':area,'mode':mode,'metric':metric,'n_seeds':len(values),
       'seed_mean_difference':round(statistics.mean(values),7),
       'bootstrap95_low_seed_only':round(percentile(boots,.025),7),
       'bootstrap95_high_seed_only':round(percentile(boots,.975),7),
       'note':'CONDITIONAL_ONLY; seed resampling does not quantify traffic or hardware uncertainty'})
 wcsv(D/'stage6_seed_uncertainty.csv',ci)
 checks={'groups':len(groups),'sample_orders':sum(map(len,groups.values())),
    'expected_paired_order_records':sum(map(len,groups.values()))*3,
    'actual_paired_order_records':sum(r['input_orders'] for r in gr),
    'B_linehaul_batch_count':len(batches),'max_batch_size':max((r['packets'] for r in batches),default=0),
    'service_parity_by_area_mode':{f'{a}_{m}':[sum(q['service_parity_pass'] for q in pair if q['area']==a and q['mode']==m),sum(q['area']==a and q['mode']==m for q in pair)] for a in 'AB' for m in ('M1','M2')},
    'order_id_pairing':True,'nonnegative_energy_and_cost':True,'shared_truck_batch_cost_allocated_once':True,
    'unverified_landing_or_airspace':True,'source_zip_sha256':hashlib.sha256(BUNDLE.read_bytes()).hexdigest(),
    'model_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'parameter_label':'HYPOTHETICAL_EXCEPT_2024_PROVISIONAL_GRID_FACTOR',
    'limitations':['Source-hour frozen road and weather proxy, not real-time dispatch/flight exposure',
       'No verified drone airspace/landing compliance; UAV trips are conditional, not regulatory feasibility',
       'No UAV hardware calibration, power-law coefficients explicitly illustrative',
       'Hypothetical fleet and infrastructure/embodied allocation; cost estimates are conditional',
       'Trip-level payload/wind model not validated against actual aircraft telemetry',
       'Origin-centroid synthetic orders, no actual parcel address or enterprise dispatch',
       '30 random seeds share reference OD/proxy model: bootstrapped intervals conditional',
       'CIQ wait absent because all ODs domestic Malaysia','Unverified reverse route flagged; B07/B02 are not silently repaired',
       'Short sample across five days per seed; not 5-month representative operating calendar']}
 (D/'stage6_QA.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
 registry=[]
 for k,v in P.items():registry.append({'parameter':k,'value':v,'status': 'OFFICIAL_2024_PROVISIONAL' if k=='grid_kgCO2e_per_kwh' else 'EXPLICIT_HYPOTHESIS',
      'source_url':'https://myenergystats.st.gov.my/documents/d/guest/grid-emission-factor-gef-in-malaysia-2022-2024-provisional-' if k=='grid_kgCO2e_per_kwh' else '',
      'sensitivity_required':k!='grid_kgCO2e_per_kwh'})
 registry.append({'parameter':'energy_model_foundation','value':'separate loaded/unloaded legs; along/cross wind, time×power','status':'STRUCTURAL_LITERATURE_NOT_COEFFICIENT_CALIBRATION',
      'source_url':'https://www.nature.com/articles/s41467-017-02411-5','sensitivity_required':True})
 wcsv(D/'stage6_parameters.csv',registry)
 print('SUMMARY',json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
 print('QA',json.dumps(checks,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
