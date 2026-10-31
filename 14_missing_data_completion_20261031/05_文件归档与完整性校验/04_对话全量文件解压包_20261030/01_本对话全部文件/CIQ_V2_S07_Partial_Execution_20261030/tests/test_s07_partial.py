"""Tests against ACTUAL S06 V3 static files and run products, not synthetic SCI performance."""
import unittest,pathlib,sys,csv,json,collections,datetime as dt
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
from build_s07_partial import build,readcsv,geod
from recover_pinned_github_sources import E,git_blob
class TestS07(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.out=build(ROOT)
 def test_static_nodes_and_zones(self):
  r=readcsv(ROOT/'outputs/S07_01_node_roles_69.csv');self.assertEqual(len(r),69);self.assertEqual(len({x['node_id'] for x in r}),69)
  self.assertEqual(collections.Counter(x['zone'] for x in r),{'A':23,'B':10,'C':29,'PORT_A':6,'GATEWAY':1})
 def test_no_operational_releases(self):
  r=readcsv(ROOT/'outputs/S07_01_node_roles_69.csv');self.assertTrue(all(x['operational_site_release']=='NO' for x in r))
 def test_zero_degree_counts(self):
  r=readcsv(ROOT/'outputs/S07_01_node_roles_69.csv');self.assertEqual(sum(int(x['uav_candidate_degree'])==0 for x in r),13)
 def test_legacy_id_collisions(self):
  x=readcsv(ROOT/'outputs/S07_02_legacy19_vs_new69_coordinate_crosswalk.csv');self.assertEqual(len(x),19)
  self.assertEqual(sum(r['same_id_status']=='ID_COLLISION' for r in x),8)
  self.assertEqual(sum(r['same_id_status']=='ID_COORDINATE_MATCH' for r in x),10)
  self.assertTrue(all(r['order_id_remapping_authorized']=='NO' for r in x))
 def test_old_a03_new_an10_and_old_a00_gateway(self):
  x={r['legacy_id']:r for r in readcsv(ROOT/'outputs/S07_02_legacy19_vs_new69_coordinate_crosswalk.csv')}
  self.assertEqual(x['A03']['nearest_new_id'],'A_N10');self.assertLess(float(x['A03']['nearest_distance_m']),1)
  self.assertEqual(x['A00']['nearest_new_id'],'G_CIQ');self.assertLess(float(x['A00']['nearest_distance_m']),1)
 def test_time_axis(self):
  x=readcsv(ROOT/'outputs/S07_03_hourly_timeline_3672.csv');self.assertEqual(len(x),3672)
  self.assertEqual(x[0]['interval_start_local'],'2026-05-01T00:00:00+08:00');self.assertEqual(x[-1]['interval_end_exclusive_local'],'2026-10-01T00:00:00+08:00')
  self.assertEqual(len({z['date_local'] for z in x}),153)
  for i in (0,1,743,744,3671):
   a=dt.datetime.fromisoformat(x[i]['interval_start_utc']);b=dt.datetime.fromisoformat(x[i]['interval_end_exclusive_utc']);self.assertEqual((b-a).total_seconds(),3600)
 def test_monthly_coverage_metadata(self):
  x=readcsv(ROOT/'outputs/S07_04_historical_weather_monthly_qc.csv');self.assertEqual(len(x),5)
  self.assertEqual(sum(int(r['expected_four_reference_rows']) for r in x),14688)
  self.assertTrue(all(r['validation']=='GITHUB_HISTORICAL_QC_SUMMARY_NOT_RECOMPUTED_FROM_RAW' for r in x))
 def test_weather_grid_only_two_and_far_dist(self):
  x=readcsv(ROOT/'outputs/S07_05_node_to_weather_grid_69_CANDIDATES_ONLY.csv');self.assertEqual(len(x),69)
  self.assertEqual(len(set((z['era5_nearest_returned_cell_lat'],z['era5_nearest_returned_cell_lon']) for z in x)),2)
  self.assertEqual(sum(z['spatial_proxy_qa']=='HOLD_DIST_GT_10KM' for z in x),31)
 def test_numeric_weather_not_fabricated(self):
  x=readcsv(ROOT/'outputs/S07_06_ERA5_two_grid_hourly_EMPTY_SCHEMATIC_NOT_DATA.csv');self.assertEqual(len(x),7344)
  self.assertTrue(all(z['wind_speed_m_s']=='' and z['rain_mm_in_interval']=='' and z['weather_simulation_release']=='NO' for z in x))
 def test_workbook_version_gate(self):
  x=readcsv(ROOT/'outputs/S07_05b_weather_XLSX_version_discrepancy.csv');self.assertEqual(len(x),5)
  self.assertTrue(all(z['byte_size_equal']=='False' and z['status'].startswith('HOLD_') for z in x))
 def test_37_od_remain_blocked(self):
  x=readcsv(ROOT/'outputs/S07_07b_legacy37_routes_still_blocked.csv')
  self.assertEqual(len(x),37)
  self.assertEqual(collections.Counter(r['legacy_area'] for r in x), {'A':7,'B':30})
  self.assertTrue(all(r['route_frozen']=='NO' and r['legacy_repair_applied']=='NO' for r in x))
  self.assertTrue(all(r['gate'].startswith('HOLD') for r in x))
 def test_no_carbons_or_orders_claimed(self):
  g=json.loads((ROOT/'qa/S07_partial_execution_audit.json').read_text());self.assertFalse(g['operational_simulation_released']);self.assertFalse(g['carbon_savings_released'])
  x=json.loads((ROOT/'outputs/S07_08_task_population_hold.json').read_text());self.assertIsNone(x['joint_order_count'])
 def test_git_blob_hash_function(self):self.assertEqual(git_blob(b'hello'), 'b6fc4c620b67d95f953a5c1c1230aaab5db5a1b0')
 def test_external_inputs_registered(self):self.assertEqual(len(E),11)
if __name__=='__main__':unittest.main()
