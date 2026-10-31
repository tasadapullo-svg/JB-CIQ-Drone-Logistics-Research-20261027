"""Candidate M0-Strong shared-vehicle pickup-delivery insertion heuristic.

RESEARCH STATUS: developmental. Not a finalized calibrated Johor Bahru model.
Inputs must be directed road route metrics backed by accepted OSM/FCD,
not V5 straight-line UAV references. Same customer requests will later be
sent to M1 and M2 with identical service and resource rules.

Each task has a pickup and dropoff; pickup occurs after release;
delivery deadline is absolute minutes from local day zero.
A vehicle follows one sequence of physical stops and accounts its mileage once.
"""
from __future__ import annotations
from dataclasses import dataclass,field
from typing import Mapping
import math

@dataclass(frozen=True)
class Demand:
 task_id: str
 pickup: str
 dropoff: str
 release_min: float
 latest_drop_min: float
 mass_kg: float

@dataclass(frozen=True)
class Vehicle:
 vehicle_id: str
 depot: str
 start_min: float
 capacity_kg: float
 shift_end_min: float
 requires_return_to_depot: bool=True

@dataclass(frozen=True)
class Stop:
 task_id: str
 kind: str  # pickup or dropoff
 node: str

@dataclass
class Route:
 vehicle:Vehicle
 stops:list[Stop]=field(default_factory=list)

@dataclass(frozen=True)
class RoadMetric:
 road_distance_km: float
 driving_minutes: float
 evidence_status: str

class RouteDataGap(Exception): pass
class InvalidServiceRule(Exception): pass

def metric_lookup(matrix:Mapping[tuple[str,str],RoadMetric], a:str,b:str)->RoadMetric:
 if a==b:return RoadMetric(0.,0.,'ACCEPTED_DIRECTED_ROAD')
 v=matrix.get((a,b))
 if v is None:raise RouteDataGap(f'NO_DIRECTED_ARC_{a}_{b}')
 if v.evidence_status!='ACCEPTED_DIRECTED_ROAD':raise RouteDataGap(f'NO_ACCEPTED_ARC_{a}_{b}')
 if any(not math.isfinite(x) or x<0 for x in (v.road_distance_km,v.driving_minutes)) or v.driving_minutes==0:
  raise RouteDataGap(f'INVALID_ARC_{a}_{b}')
 return v

def evaluate(route:Route,requests:Mapping[str,Demand],matrix:Mapping[tuple[str,str],RoadMetric],
             service_minutes_per_event:float=0.0)->dict:
 if service_minutes_per_event<0:raise InvalidServiceRule('negative service time')
 v=route.vehicle
 if not 0<v.capacity_kg or v.shift_end_min<v.start_min:raise InvalidServiceRule('invalid vehicle')
 loc=v.depot;t=v.start_min;km=drive=0.;load=0.;picked=set();delivered=set();trace=[]
 for st in route.stops:
  if st.task_id not in requests:raise InvalidServiceRule('task absent')
  d=requests[st.task_id]
  arc=metric_lookup(matrix,loc,st.node)
  km+=arc.road_distance_km;drive+=arc.driving_minutes;t+=arc.driving_minutes
  if st.kind=='pickup':
   if st.task_id in picked:raise InvalidServiceRule('double pickup')
   t=max(t,d.release_min);load+=d.mass_kg;picked.add(st.task_id)
   if load>v.capacity_kg+1e-8:return {'feasible':False,'reason':'VEHICLE_CAPACITY'}
  elif st.kind=='dropoff':
   if st.task_id not in picked or st.task_id in delivered:raise InvalidServiceRule('bad pickup/dropoff order')
   if t>d.latest_drop_min+1e-8:return {'feasible':False,'reason':'DELIVERY_DEADLINE'}
   load-=d.mass_kg;delivered.add(st.task_id)
  else:raise InvalidServiceRule('invalid stop kind')
  t+=service_minutes_per_event
  trace.append({'task_id':st.task_id,'event':st.kind,'node':st.node,'departure_min':t,'vehicle_load_kg':load})
  loc=st.node
 if picked!=delivered:raise InvalidServiceRule('missing delivery')
 if v.requires_return_to_depot:
  last=metric_lookup(matrix,loc,v.depot)
  km+=last.road_distance_km;drive+=last.driving_minutes;t+=last.driving_minutes
 if t>v.shift_end_min+1e-8:return {'feasible':False,'reason':'VEHICLE_SHIFT'}
 return {'feasible':True,'distance_km':km,'drive_min':drive,'end_min':t,
         'served_task_ids':sorted(delivered),'events':trace}

def greedy_pickup_delivery(orders:list[Demand],vehicles:list[Vehicle],matrix:Mapping[tuple[str,str],RoadMetric],
                           service_minutes_per_event:float=0.0)->dict:
 """Deterministic cheapest insertion, conditional on accepted FULL directed arc matrix.

    This is a reproducible heuristic, NOT proof of global optimum.
    No order may be discarded from output. If road arcs are missing, fail the
    entire optimization with RouteDataGap, rather than mislabel no-path as failure.
 """
 ids=[x.task_id for x in orders]
 if len(ids)!=len(set(ids)):raise InvalidServiceRule('duplicate task IDs')
 req={x.task_id:x for x in orders}
 if not vehicles:raise InvalidServiceRule('no vehicle')
 nodes={x.pickup for x in orders}|{x.dropoff for x in orders}|{v.depot for v in vehicles}
 # Require a full matrix for *all* relevant directed pairs. A sparse road graph
 # must be shortest-path-expanded BEFORE insertion; no straight-line fallback.
 for a in nodes:
  for b in nodes:
   metric_lookup(matrix,a,b)
 routes=[Route(v) for v in vehicles]; rejected=[]
 for order in sorted(orders,key=lambda x:(x.latest_drop_min,x.release_min,x.task_id)):
  best=None
  for k,route in enumerate(routes):
   old=evaluate(route,req,matrix,service_minutes_per_event)
   if not old['feasible']:raise InvalidServiceRule('existing route became infeasible')
   size=len(route.stops)
   for i in range(size+1):
    for j in range(i+1,size+2):
     candidate=route.stops.copy();candidate.insert(i,Stop(order.task_id,'pickup',order.pickup));candidate.insert(j,Stop(order.task_id,'dropoff',order.dropoff))
     r=evaluate(Route(route.vehicle,candidate),req,matrix,service_minutes_per_event)
     if not r['feasible']:continue
     extra_km=r['distance_km']-old['distance_km']
     extra_drive=r['drive_min']-old['drive_min']
     score=(round(extra_km,9),round(extra_drive,9),k,i,j)
     if best is None or score<best[0]:best=(score,k,candidate)
  if best is None:rejected.append({'task_id':order.task_id,'status':'NOT_SERVED_BY_HEURISTIC_WITH_GIVEN_RESOURCES','reason':'CAPACITY_DEADLINE_SHIFT_OR_HEURISTIC_LIMIT'})
  else:routes[best[1]].stops=best[2]
 results=[evaluate(r,req,matrix,service_minutes_per_event) for r in routes]
 return {'algorithm':'DETERMINISTIC_CHEAPEST_INSERTION_NOT_GLOBAL_OPTIMUM',
  'routes':results,'accepted_task_ids':sorted({t for r in results for t in r['served_task_ids']}),
  'unserved_tasks':rejected,'all_task_ids':sorted(ids),
  'physical_driving_distance_total_km':sum(r['distance_km'] for r in results),
  'status':'METHOD_ONLY_NEEDS_EMPIRICAL_DIRECTIONAL_ROAD_AND_FLEET_PARAMETERS'}
