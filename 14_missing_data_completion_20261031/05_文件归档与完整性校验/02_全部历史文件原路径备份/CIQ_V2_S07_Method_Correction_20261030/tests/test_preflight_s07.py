import pathlib,sys,unittest,os
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'code'))
from preflight_s07 import audit
S06=pathlib.Path(os.environ.get('CIQ_S06_ROOT','/mnt/data/CIQ_V2_S06_V3_Input_Build_20261030'))
class TestActualS06Audit(unittest.TestCase):
 def setUp(self):
  if not S06.exists():self.skipTest("S06 source not present; set CIQ_S06_ROOT")
  self.r=audit(S06,None)
 def test_counts_actual(self):self.assertEqual((self.r['facts']['node_rows'],self.r['facts']['uav_candidate_edges'],self.r['facts']['ground_reference_edges']),(69,116,5))
 def test_isolation_actual(self):self.assertEqual(len(self.r['facts']['uav_zero_degree_node_ids']),13)
 def test_legacy_exception(self):self.assertEqual(self.r['facts']['legacy37_exception_rows'],37)
 def test_hard_hold(self):self.assertEqual(self.r['overall'],'HOLD_NOT_RELEASED_TO_FORMAL_M0_M1_M2')
 def test_geometry_separation(self):self.assertEqual(self.r['gates']['mode_isolation']['status'],'PASS')
 def test_no_fake_road(self):self.assertEqual(self.r['facts']['ground_route_distance_populated_count'],0)
if __name__=='__main__':unittest.main(verbosity=2)
