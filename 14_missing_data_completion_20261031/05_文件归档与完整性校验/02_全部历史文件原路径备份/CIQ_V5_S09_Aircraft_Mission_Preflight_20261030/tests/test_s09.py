import csv,json,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
from mission_energy_core import AircraftScenario, Leg,calculate_scenario_mission
from weather_event_contract import WeatherHour,weather_for_event,along_track_wind_mps

class TestS09(unittest.TestCase):
    def p(self):return AircraftScenario(30.0,3.9688,0.85,0.20,0.85,15.0,10.0,7.0,0.1)
    def test_1_hypothetical_scenario(self):
        r=calculate_scenario_mission([Leg(2,1,0,'TEST_FIXTURE_ONLY','CONDITIONAL_GEOMETRY'),Leg(2,0,0,'TEST_FIXTURE_ONLY','CONDITIONAL_GEOMETRY')],self.p())
        self.assertGreater(r['grid_recharge_kwh_assumed'],r['battery_mission_kwh_assumed']);self.assertFalse(r['has_real_event_time_weather'])
    def test_2_missing_weather_rejected(self):
        with self.assertRaises(ValueError):calculate_scenario_mission([Leg(2,1,None,'TEST_FIXTURE_ONLY','CONDITIONAL_GEOMETRY')],self.p())
    def test_3_payload_rejected(self):
        with self.assertRaises(ValueError):calculate_scenario_mission([Leg(2,31,0,'TEST_FIXTURE_ONLY','CONDITIONAL_GEOMETRY')],self.p())
    def test_4_headwind_stall(self):
        with self.assertRaises(ValueError):calculate_scenario_mission([Leg(2,1,-15,'TEST_FIXTURE_ONLY','CONDITIONAL_GEOMETRY')],self.p())
    def test_5_energy_budget_can_fail(self):
        r=calculate_scenario_mission([Leg(15,5,0,'TEST_FIXTURE_ONLY','CONDITIONAL_GEOMETRY')],self.p())
        self.assertFalse(r['conditional_energy_budget_pass'])
    def test_6_battery_uncertainty_explicit(self):
        with self.assertRaises(ValueError):AircraftScenario(4.7,0,0.9,0.2,0.9,20,2,2,.1).validate()
    def test_7_no_operational_claim(self):
        r=calculate_scenario_mission([Leg(0.5,1,0,'TEST_FIXTURE_ONLY','CONDITIONAL_GEOMETRY')],self.p());self.assertEqual(r['release_status'],'CONDITIONAL_MODEL_UNVALIDATED')
    def test_8_wind_projection(self):
        self.assertAlmostEqual(along_track_wind_mps(5,270,90),5)
        self.assertAlmostEqual(along_track_wind_mps(5,90,90),-5)
    def weather(self,start):return WeatherHour('WX',start,start+timedelta(hours=1),4,270,7,0,'VERIFIED_INPUT_SOURCE_AND_TIME')
    def test_9_single_hour_interval(self):
        d=datetime(2026,5,1,tzinfo=timezone.utc);rr=weather_for_event('WX',d+timedelta(minutes=5),d+timedelta(minutes=30),[self.weather(d)])
        self.assertEqual(sum(z[1] for z in rr),25*60)
    def test_10_crosses_two_hours(self):
        d=datetime(2026,5,1,tzinfo=timezone.utc);r=weather_for_event('WX',d+timedelta(minutes=50),d+timedelta(hours=1,minutes=10),[self.weather(d),self.weather(d+timedelta(hours=1))]);self.assertEqual(len(r),2)
    def test_11_gaps_hold(self):
        d=datetime(2026,5,1,tzinfo=timezone.utc)
        with self.assertRaises(ValueError):weather_for_event('WX',d,d+timedelta(hours=2),[self.weather(d)])
    def test_12_source_hold(self):
        d=datetime(2026,5,1,tzinfo=timezone.utc);x=self.weather(d)
        from dataclasses import replace
        with self.assertRaises(ValueError):weather_for_event('WX',d,d+timedelta(hours=1),[replace(x,evidence='METADATA_ONLY')])
    def test_13_overlaps_hold(self):
        d=datetime(2026,5,1,tzinfo=timezone.utc)
        with self.assertRaises(ValueError):weather_for_event('WX',d,d+timedelta(hours=1),[self.weather(d),self.weather(d)])
    def test_14_v5_population(self):
        with (ROOT/'inputs/S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv').open(encoding='utf-8-sig') as f:ns=list(csv.DictReader(f))
        self.assertEqual(len(ns),68);self.assertNotIn('A_N10',{n['node_id'] for n in ns})
    def test_15_v5_oem_bounds(self):
        a=json.loads((ROOT/'inputs/S09_OEM_SPEC_REGISTRY.json').read_text())['aircraft']
        self.assertEqual(a['DJI_FLYCART_30_DUAL']['payload_capacity_kg'],30)
        self.assertEqual(a['WINGCOPTER_198_CARGO']['payload_capacity_kg'],4.7)
        self.assertIsNone(a['WINGCOPTER_198_CARGO']['battery_usable_kWh'])
    def test_16_screen_rows(self):
        with (ROOT/'outputs/S09_V5_ALL_TASKS_OEM_PAYLOAD_AND_DIRECT_EDGE_SCREEN.csv').open(encoding='utf-8-sig') as f:
            rs=list(csv.DictReader(f))
        self.assertEqual(len(rs),82620)
        self.assertEqual(len({r['task_id'] for r in rs}),82620)
        self.assertEqual(sum(r['Wingcopter_payload_screen']=='WEIGHT_FAIL' for r in rs),27540)
        self.assertEqual(sum(r['real_flight_eligibility']!='HOLD_WEATHER_AIRSPACE_STATION_AND_ENERGY' for r in rs),0)
    def test_17_only_true_v5_edges(self):
        with (ROOT/'outputs/S09_V5_116_EDGE_OEM_DISTANCE_BOUNDARY_SCREEN.csv').open(encoding='utf-8-sig') as f:rs=list(csv.DictReader(f))
        self.assertEqual(len(rs),116)
        self.assertTrue(all(r['calibrated_mission_energy_kwh']=='' for r in rs))
    def test_18_all_no_carbon(self):
        q=json.loads((ROOT/'qa/S09_ACTUAL_V5_SCREEN_AUDIT.json').read_text())
        self.assertEqual(q['counts']['task_five_mode_fully_simulated'],0)

if __name__=='__main__':unittest.main()
