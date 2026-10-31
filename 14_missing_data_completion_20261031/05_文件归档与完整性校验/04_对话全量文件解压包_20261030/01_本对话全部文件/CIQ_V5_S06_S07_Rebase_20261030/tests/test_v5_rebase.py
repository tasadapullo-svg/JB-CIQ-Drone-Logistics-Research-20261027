import unittest,sys,csv,json,collections,pathlib,datetime as dt,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
from build_v5_rebase_and_synthetic_tasks import sha256,EXPECTED_V5_ZIP_SHA256,EXPECTED_ACTIVE_GPKG_SHA256,task_generator,MODEL_CHOICES
from v5_s07_source_gate import check

def rows(name):
 with (ROOT/'outputs'/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
class TestV5ScienceHandover(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.nodes=rows('S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv');cls.edges=rows('S06_V5_ALL_125_LINKS_BY_FUNCTION.csv')
  cls.old=rows('S07_V5_19_LEGACY_COORDINATE_CROSSWALK_NOT_AUTO_MIGRATED.csv')
  cls.tasks=rows('S07_V5_SYNTHETIC_TASKS_CONDITIONAL_DESIGN.csv');cls.time=rows('S07_V5_3672_HOURLY_TIMELINE.csv')
 def test_01_source_zip_hash(self):self.assertEqual(sha256(ROOT/'inputs/CIQ_ABC_QGIS322_V5_ONE_WMP228_68_NODES_FULL_PROJECT(1).zip'),EXPECTED_V5_ZIP_SHA256)
 def test_02_source_gpkg_hash(self):self.assertEqual(json.load(open(ROOT/'qa/V5_REBASE_EXECUTION_AUDIT.json'))['v5_active_gpkg_sha256'],EXPECTED_ACTIVE_GPKG_SHA256)
 def test_03_node_count_unique(self):self.assertEqual((len(self.nodes),len({x['node_id'] for x in self.nodes})),(68,68))
 def test_04_no_old_node_A_N10(self):self.assertNotIn('A_N10',{x['node_id'] for x in self.nodes})
 def test_05_gateway_present(self):self.assertIn('G_CIQ',{x['node_id'] for x in self.nodes})
 def test_06_A09_A10_are_zone_C(self):
  ix={x['node_id']:x for x in self.nodes};self.assertEqual(ix['A09']['zone'],'C');self.assertEqual(ix['A10']['zone'],'C')
 def test_07_zone_counts(self):self.assertEqual(dict(collections.Counter(x['zone'] for x in self.nodes)),{'A':29,'B':10,'C':29})
 def test_08_edge_counts(self):self.assertEqual(dict(collections.Counter(x['edge_type'] for x in self.edges)),{'UAV_GEOMETRY_CANDIDATE_ONLY':116,'GROUND_HANDOFF_STRAIGHT_REFERENCE':5,'GROUND_ONLY_HOLD_EXTRA':4})
 def test_09_endpoint_ids(self):
  ids={x['node_id'] for x in self.nodes};self.assertTrue(all(x['from_id'] in ids and x['to_id'] in ids for x in self.edges))
 def test_10_no_road_distance_fabricated(self):self.assertTrue(all(not x['road_distance_km'] for x in self.edges))
 def test_11_no_authorized_flights(self):self.assertTrue(all(x['airspace_authorized']=='NO' and x['counted_as_operational_edge']=='NO' for x in self.edges))
 def test_12_no_pad_approved(self):self.assertTrue(all(x['launch_pad_operationally_approved']=='NO' for x in self.nodes))
 def test_13_legacy19_all_blocked(self):self.assertEqual(len(self.old),19);self.assertTrue(all(x['orders_migration_authorized']=='NO' for x in self.old))
 def test_14_legacy_collisions(self):self.assertEqual(sum(x['mapping_gate']=='ID_COLLISION_DIFFERENT_GEO_HARD_BLOCK' for x in self.old),8)
 def test_15_old_37_no_repair(self):
  od=rows('S07_V5_37_LEGACY_OD_EXCEPTION_NO_AUTO_REPAIR.csv');self.assertEqual(len(od),37);self.assertTrue(all(x['candidate_repair_applied']=='NO' for x in od))
 def test_16_hourly_153days(self):
  self.assertEqual(len(self.time),3672);self.assertEqual(self.time[0]['local_date'],'2026-05-01');self.assertEqual(self.time[-1]['local_date'],'2026-09-30')
 def test_17_timezone_and_interval(self):
  for t in (self.time[0],self.time[2000],self.time[-1]):
   a=dt.datetime.fromisoformat(t['interval_start_local']);b=dt.datetime.fromisoformat(t['interval_end_local_exclusive']);self.assertEqual((b-a).total_seconds(),3600);self.assertEqual(a.utcoffset(),dt.timedelta(hours=8))
 def test_18_all_tasks_unique(self):self.assertEqual(len(self.tasks),len({x['task_id'] for x in self.tasks}))
 def test_19_task_volume(self):self.assertEqual(len(self.tasks),82620)
 def test_20_task_seed_date_counts(self):
  self.assertEqual(len({x['scenario_seed'] for x in self.tasks}),30);self.assertEqual(len({x['date_local'] for x in self.tasks}),153)
  self.assertEqual(dict(collections.Counter(x['origin_zone'] for x in self.tasks)),{'A':27540,'B':27540,'C':27540})
 def test_21_task_hours(self):self.assertEqual({int(x['release_local'][11:13]) for x in self.tasks},set(range(24)))
 def test_22_equal_crosszone_directions(self):
  c=collections.Counter(x['origin_zone']+'->'+x['destination_zone'] for x in self.tasks if x['demand_stratum']=='DESIGNED_CROSS_ZONE_STRESS')
  self.assertEqual(len(c),6);self.assertEqual(set(c.values()),{2295})
 def test_23_eligible_anchors(self):
  ids={x['node_id'] for x in self.nodes};self.assertTrue(all(x['origin_node_id'] in ids and x['destination_node_id'] in ids and x['origin_node_id']!=x['destination_node_id'] for x in self.tasks))
 def test_24_weather_grid_68(self):
  r=rows('S07_V5_68_NODE_ERA5_COARSE_GRID_CANDIDATES.csv');self.assertEqual(len(r),68);self.assertEqual(len(set(x['returned_era5_grid_id'] for x in r)),2)
 def test_25_no_unvalidated_outcomes(self):
  self.assertTrue(all(x['service_and_carbon_result_status']=='NOT_COMPUTED' and x['road_route_status']=='NOT_ROUTED_HOLD' and x['empirical_demand_evidence']=='NONE_CONDITIONAL_SCENARIO' for x in self.tasks))
 def test_26_one_order_identity_for_five_modes(self):self.assertEqual(len(MODEL_CHOICES),5);self.assertFalse('mode' in self.tasks[0]);self.assertTrue(all(x.startswith(('M0_','M1_','M2_')) for x in MODEL_CHOICES))
 def test_27_deterministic_sample_replay(self):
  one=task_generator(self.nodes,seeds=1,tasks_per_day_zone=6);self.assertEqual(one[0]['task_id'],self.tasks[0]['task_id']);self.assertEqual(str(one[0]['origin_node_id']),self.tasks[0]['origin_node_id']);self.assertEqual(str(one[0]['destination_node_id']),self.tasks[0]['destination_node_id']);self.assertEqual(one[0]['release_local'],self.tasks[0]['release_local'])
 def test_28_offline_source_gate_truthful(self):
  gate=json.loads((ROOT/'qa/S07_V5_SOURCE_RELEASE_GATE.json').read_text());self.assertEqual(gate['V5_SOURCE_ABC_ROAD'],'HOLD_NEW_C_ROAD_AND_SITE_ACCESS_UNVERIFIED')
 def test_29_no_wmp_clearance_inferred(self):self.assertTrue(all(x['feasible_flight']=='UNVERIFIED' for x in self.edges if x['edge_type']=='UAV_GEOMETRY_CANDIDATE_ONLY'))
 def test_30_legacy_history_not_blended(self):self.assertTrue(all(x['task_id'].startswith('V5S07-') for x in self.tasks))
if __name__=='__main__':unittest.main()
