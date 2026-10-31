import unittest,sys,json,tempfile,csv,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'code'))
from m0_petrol_core import PetrolParameters,RoadLeg,co2_kg_per_litre,assess_physical_trip_ledger
from run_actual_task_screen import geodesic_km

# ALL numerical parameters in tests are invented algebraic fixtures, not research settings.
class PetrolLedgerMethodTests(unittest.TestCase):
 def setUp(self):
  self.p=PetrolParameters(litres_per_100km=10,density_kg_per_litre=.74,
      net_calorific_value_MJ_per_kg=44,ttw_co2_kg_per_TJ=69300,
      petrol_MYR_per_litre=2,driver_MYR_per_hour=20)
 def leg(self,**kwargs):
  d=dict(leg_id='L1',trip_id='TR1',vehicle_id='CAR1',road_distance_km=10,
    driving_minutes=20,stationary_minutes=0,evidence_status='ACCEPTED_DIRECTED_ROAD',
    road_graph_sha256='toy_graph_sha_NOT_EVIDENCE',served_task_ids=('ORDER1','ORDER2'))
  d.update(kwargs)
  return RoadLeg(**d)
 def test_unit_conversion_co2(self):
  self.assertAlmostEqual(co2_kg_per_litre(self.p),.74*44*69300/1e6)
 def test_fuel_100km(self):
  self.assertAlmostEqual(assess_physical_trip_ledger([self.leg(road_distance_km=100)],self.p)['fuel_litres_total'],10)
 def test_shared_ride_one_physical_leg(self):
  a=assess_physical_trip_ledger([self.leg()],self.p)
  self.assertEqual(a['tasks_mentioned_on_legs_unique'],2)
  self.assertAlmostEqual(a['fuel_litres_total'],1)
 def test_duplicate_physical_leg_rejected(self):
  with self.assertRaisesRegex(ValueError,'duplicate'):
   assess_physical_trip_ledger([self.leg(),self.leg()],self.p)
 def test_unverified_route_rejected(self):
  with self.assertRaisesRegex(ValueError,'HOLD'):
   assess_physical_trip_ledger([self.leg(evidence_status='NOT_ROUTED_HOLD')],self.p)
 def test_zero_travel_positive_distance_rejected(self):
  with self.assertRaises(ValueError):
   assess_physical_trip_ledger([self.leg(driving_minutes=0)],self.p)
 def test_negative_road_length_rejected(self):
  with self.assertRaises(ValueError):
   assess_physical_trip_ledger([self.leg(road_distance_km=-1)],self.p)
 def test_no_emission_if_missing_fuel_consumption(self):
  import dataclasses
  with self.assertRaises(ValueError):
   assess_physical_trip_ledger([self.leg()],dataclasses.replace(self.p,litres_per_100km=None))
 def test_no_emission_if_missing_fuel_density(self):
  import dataclasses
  with self.assertRaises(ValueError):
   assess_physical_trip_ledger([self.leg()],dataclasses.replace(self.p,density_kg_per_litre=None))
 def test_no_emission_if_missing_fuel_price(self):
  import dataclasses
  with self.assertRaises(ValueError):
   assess_physical_trip_ledger([self.leg()],dataclasses.replace(self.p,petrol_MYR_per_litre=None))
 def test_standstill_separate_idling_case(self):
  import dataclasses
  p=dataclasses.replace(self.p,idling_litres_per_hour=.8,cruising_rate_includes_idling=False)
  a=assess_physical_trip_ledger([self.leg(stationary_minutes=30)],p)
  self.assertAlmostEqual(a['fuel_litres_total'],1.4)
 def test_no_double_counting_idling(self):
  import dataclasses
  p=dataclasses.replace(self.p,idling_litres_per_hour=.8,cruising_rate_includes_idling=True)
  with self.assertRaisesRegex(ValueError,'double count'):
   assess_physical_trip_ledger([self.leg(stationary_minutes=30)],p)
 def test_empty_ledger_hold(self):
  with self.assertRaises(ValueError):
   assess_physical_trip_ledger([],self.p)
 def test_return_leg_counts_once(self):
  a=assess_physical_trip_ledger([self.leg(),self.leg(leg_id='L2',road_distance_km=15)],self.p)
  self.assertAlmostEqual(a['road_km_physical_total'],25)
  self.assertAlmostEqual(a['fuel_litres_total'],2.5)
  self.assertEqual(a['tasks_mentioned_on_legs_unique'],2)
 def test_geodesic_proxy_zero_only_for_same_point(self):
  self.assertAlmostEqual(geodesic_km(103.75,1.5,103.75,1.5),0)
  self.assertGreater(geodesic_km(103.75,1.5,103.76,1.5),0)

if __name__=='__main__':unittest.main()

from m0_multi_order_dispatch import Demand,Vehicle,RoadMetric,RouteDataGap,greedy_pickup_delivery
class PickupDeliveryHeuristicTests(unittest.TestCase):
 def matrix(self):
  # A toy fully connected metric, not local GIS; e.g. D->P1->P2->Q1->Q2->D.
  distances={('D','P'):2,('D','Q'):5,('P','Q'):3,
             ('D','R'):3,('P','R'):3,('Q','R'):2}
  m={}
  for (a,b),d in distances.items():
   m[(a,b)]=RoadMetric(d,2*d,'ACCEPTED_DIRECTED_ROAD')
   m[(b,a)]=RoadMetric(d,2*d,'ACCEPTED_DIRECTED_ROAD')
  return m
 def two(self):
  return [Demand('T1','P','Q',0,50,1),Demand('T2','P','R',0,50,1)]
 def vehicle(self):
  return [Vehicle('CAR','D',0,4,120)]
 def test_two_orders_one_vehicle_route(self):
  r=greedy_pickup_delivery(self.two(),self.vehicle(),self.matrix())
  self.assertEqual(r['accepted_task_ids'],['T1','T2'])
  self.assertEqual(len(r['unserved_tasks']),0)
  self.assertEqual(len(r['routes']),1)
  self.assertLess(r['physical_driving_distance_total_km'],20)
 def test_missing_directed_metric_hard_blocks_not_unsatisfied(self):
  mat=self.matrix();del mat[('P','Q')]
  with self.assertRaises(RouteDataGap):
   greedy_pickup_delivery(self.two(),self.vehicle(),mat)
 def test_capacity_overweight_not_deletion(self):
  orders=[Demand('T1','P','Q',0,100,9)]
  r=greedy_pickup_delivery(orders,self.vehicle(),self.matrix())
  self.assertEqual(r['accepted_task_ids'],[])
  self.assertEqual(len(r['unserved_tasks']),1)
  self.assertEqual(r['all_task_ids'],['T1'])
 def test_strict_deadline_rejected_not_deleted(self):
  r=greedy_pickup_delivery([Demand('T1','P','Q',0,1,1)],self.vehicle(),self.matrix())
  self.assertEqual(len(r['unserved_tasks']),1)
  self.assertEqual(r['all_task_ids'],['T1'])
