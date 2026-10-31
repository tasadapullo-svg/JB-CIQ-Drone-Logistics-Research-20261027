import sys,unittest,csv,datetime as dt,importlib.util,pathlib,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
import build_s07_event_contract as mod
import validate_s07_external_data as val

class S07ScientificChecks(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.r=ROOT
  cls.nodes=mod.read(cls.r/'inputs/S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv')
  cls.tasks=mod.read(cls.r/'inputs/S07_V5_SYNTHETIC_TASKS_CONDITIONAL_DESIGN.csv')
  cls.hours=mod.read(cls.r/'inputs/S07_V5_3672_HOURLY_TIMELINE.csv')
  cls.edges=mod.read(cls.r/'inputs/S06_V5_116_UAV_GEOMETRY_ONLY.csv')
  cls.grids=mod.read(cls.r/'inputs/S07_V5_68_NODE_ERA5_COARSE_GRID_CANDIDATES.csv')
  cls.audit=__import__('json').loads((cls.r/'qa/S07_ACTUAL_EXECUTION_AUDIT.json').read_text())
  cls.actual=mod.read(cls.r/'outputs/S07_V5_82620_TASK_EVENT_WEATHER_ROAD_LOOKUP_KEYS_ONLY.csv')
 def test_01_nodes_count(self):self.assertEqual(len(self.nodes),68)
 def test_02_node_unique(self):self.assertEqual(len({r['node_id'] for r in self.nodes}),68)
 def test_03_locked_input_exists(self):self.assertTrue((self.r/'inputs/V5_FROZEN_SOURCE.zip').is_file())
 def test_04_task_count(self):self.assertEqual(len(self.tasks),82620)
 def test_05_task_id_unique(self):self.assertEqual(len({t['task_id'] for t in self.tasks}),82620)
 def test_06_seed_count(self):self.assertEqual(len({t['scenario_seed'] for t in self.tasks}),30)
 def test_07_day_count(self):self.assertEqual(len({t['date_local'] for t in self.tasks}),153)
 def test_08_hours(self):self.assertEqual(len(self.hours),3672)
 def test_09_grid_member(self):self.assertEqual(set(x['node_id'] for x in self.grids),set(x['node_id'] for x in self.nodes))
 def test_10_edge_count(self):self.assertEqual(len(self.edges),116)
 def test_11_edge_classification(self):self.assertTrue(all(r['input_mode']=='UAV_GEOMETRY_ONLY' for r in self.edges))
 def test_12_no_stale_A_N10(self):self.assertNotIn('A_N10',set(t['origin_node_id'] for t in self.tasks)|set(t['destination_node_id'] for t in self.tasks))
 def test_13_no_null_ids(self):self.assertTrue(all(t['origin_node_id'] and t['destination_node_id'] for t in self.tasks))
 def test_14_event_keys_count(self):self.assertEqual(len(self.actual),82620)
 def test_15_hour_windows(self):
  for x in self.actual[::2000]:
   start=dt.datetime.fromisoformat(x['weather_slot_start_utc']);release=dt.datetime.fromisoformat(x['release_utc'])
   self.assertGreaterEqual(release,start);self.assertLess(release-start,dt.timedelta(hours=1))
 def test_16_all_mode_identical_population(self):self.assertTrue(all(x['paired_modes_reference'].count('|')==4 for x in self.actual))
 def test_17_no_unauthorized_road_or_weather(self):self.assertTrue(all(x['road_directed_route_accepted']=='NO' and x['release_hour_UTC_numerical_weather_accepted']=='NO' for x in self.actual))
 def test_18_edge_direction_partition(self):self.assertEqual(sum(self.audit[z] for z in ['candidate_direct_edge_tasks','candidate_reverse_only_tasks','no_direct_edge_tasks']),82620)
 def test_19_time_strata(self):
  d=mod.read(self.r/'outputs/S07_13770_SEED_DAY_ZONE_STRATA_COUNTS.csv');self.assertEqual(len(d),13770);self.assertTrue(all(int(x['designed_task_count'])==6 for x in d))
 def test_20_no_operational_carbon_claim(self):self.assertFalse(self.audit['operational_CO2e_and_cost_results_approved'])
 def test_21_pinned_missing_source_block(self):self.assertEqual(self.audit['pinned_source_verified_count'],0)
 def test_22_workbook_filename_preserved(self):self.assertEqual(sum(x['name'].endswith('.xlsx') for x in mod.read(self.r/'qa/S07_PINNED_SOURCE_BYTE_GATE.csv')),5)
 def test_23_reject_stale_node(self):
  t=[dict(self.tasks[0])];t[0]['origin_node_id']='A_N10'
  with self.assertRaises(AssertionError):mod.preflight(self.nodes,t,self.hours,self.grids,self.edges)
 def test_24_reject_missing_road_field(self):
  with tempfile.TemporaryDirectory() as p:
   path=pathlib.Path(p)/'road.csv';path.write_text('origin_node_id,destination_node_id\nA01,A02\n')
   self.assertEqual(val.validate_road(path,{'A01','A02'})['status'],'HOLD_ROAD_SCHEMA')
 def test_25_reject_unverified_road_access(self):
  with tempfile.TemporaryDirectory() as p:
   path=pathlib.Path(p)/'road.csv'
   path.write_text(','.join(val.REQUIRED_ROAD)+'\n'+','.join(['A01','A02','4.2','a'*64,'NO','NO','YES'])+'\n')
   self.assertEqual(val.validate_road(path,{'A01','A02'})['status'],'HOLD_ROAD_ACCESS_AND_TURN_QA')
 def test_26_reject_unverified_weather_units(self):
  with tempfile.TemporaryDirectory() as p:
   path=pathlib.Path(p)/'w.csv'
   path.write_text(','.join(val.REQUIRED_WX)+'\n'+','.join(['CW_MY','2026-05-01T00:00:00+00:00','2026-05-01T01:00:00+00:00','5','6','90','0.5','a'*64,'NO'])+'\n')
   self.assertEqual(val.validate_weather(path)['status'],'HOLD_WEATHER_QA')
 def test_27_reject_bad_weather_interval(self):
  with tempfile.TemporaryDirectory() as p:
   path=pathlib.Path(p)/'w.csv'
   path.write_text(','.join(val.REQUIRED_WX)+'\n'+','.join(['CW_MY','2026-05-01T00:00:00+00:00','2026-05-01T02:00:00+00:00','5','6','90','0.5','a'*64,'YES'])+'\n')
   self.assertEqual(val.validate_weather(path)['status'],'HOLD_WEATHER_QA')
 def test_28_no_CIQ_wait_fabrication(self):self.assertTrue(all(t['ciq_crossborder_status']=='MY_INLAND_SCENARIO_CIQ_WAIT_NOT_APPLICABLE' for t in self.tasks))
 def test_29_source_digest(self):self.assertEqual(self.audit['input_registry']['tasks']['sha256'],mod.sha256(self.r/'inputs/S07_V5_SYNTHETIC_TASKS_CONDITIONAL_DESIGN.csv'))
 def test_30_real_grid_distance_not_zero_placeholder(self):self.assertTrue(all(float(x['grid_distance_m'])>0 for x in self.grids))
if __name__=='__main__':unittest.main(verbosity=2)
