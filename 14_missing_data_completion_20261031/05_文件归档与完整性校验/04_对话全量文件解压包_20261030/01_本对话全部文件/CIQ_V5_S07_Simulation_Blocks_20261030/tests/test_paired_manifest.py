import csv,copy,hashlib,pathlib,sys,tempfile,unittest
HERE=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/'code'))
from build_paired_run_manifest import run, read_csv

class TestV5Manifest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.nodes=read_csv(HERE/'inputs'/'V5_68_NODE_MASTER.csv')
  cls.tasks=read_csv(HERE/'inputs'/'V5_82620_CONDITIONAL_TASKS.csv')[:18]
  assert len(cls.tasks)==18
 def fixture(self,tasks=None,nodes=None):
  temp=tempfile.TemporaryDirectory();root=pathlib.Path(temp.name)
  def put(fname,data):
   with (root/fname).open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
   return root/fname
  n=put('nodes.csv',nodes or self.nodes);t=put('orders.csv',tasks if tasks is not None else self.tasks)
  return temp,n,t,root/'out'
 def test_smoke_valid_18_orders_five_modes(self):
  tmp,n,t,out=self.fixture()
  with tmp:
   d=run(n,t,out,strict=False)
   self.assertEqual(d['independent_seed_day_scenarios'],1)
   z=read_csv(out/'S10_V5_22950_MODE_RUN_KEYS_NO_SIM_RESULTS.csv')
   self.assertEqual(len(z),5)
   self.assertEqual(len({r['task_set_sha256'] for r in z}),1)
   self.assertTrue(all(x['operation_emission_status']=='NOT_COMPUTED' for x in z))
 def assert_bad(self,mut,expected):
  arr=copy.deepcopy(self.tasks)
  mut(arr)
  tmp,n,t,out=self.fixture(tasks=arr)
  with tmp:
   with self.assertRaisesRegex(ValueError,expected):run(n,t,out,strict=False)
 def test_duplicate_task_rejected(self):self.assert_bad(lambda r:r[1].update(task_id=r[0]['task_id']),'DUPLICATE_TASK_ID')
 def test_unknown_node_rejected(self):self.assert_bad(lambda r:r[0].update(origin_node_id='A_N10'),'UNKNOWN_V5_NODE')
 def test_wrong_zone_rejected(self):self.assert_bad(lambda r:r[0].update(origin_zone='C'),'ZONE_MISMATCH')
 def test_wrong_longitude_rejected(self):self.assert_bad(lambda r:r[0].update(origin_lon='103.000'),'COORD_MISMATCH')
 def test_wrong_release_utc_rejected(self):self.assert_bad(lambda r:r[0].update(release_utc='2026-05-01T00:15:00+00:00'),'TIMEZONE_ERROR')
 def test_wrong_release_date_rejected(self):self.assert_bad(lambda r:r[0].update(date_local='2026-05-02'),'RELEASE_LOCAL_DATE_CHANGED')
 def test_cross_border_status_rejected(self):self.assert_bad(lambda r:r[0].update(ciq_crossborder_status='CROSS_BORDER_APPROVED'),'CROSS_BORDER_SCENARIO_CHANGED')
 def test_negative_mass_rejected(self):self.assert_bad(lambda r:r[0].update(parcel_kg='-1'),'INVALID_ORDER_PARAMS')
 def test_precomputed_emissions_rejected(self):self.assert_bad(lambda r:r[0].update(service_and_carbon_result_status='COMPUTED'),'UNEXPECTED_PRECOMPUTED_RESULT')
 def test_inputs_frozen_unchanged(self):
  # Test artifacts should not be rewritten by generator.
  p=HERE/'inputs'/'V5_82620_CONDITIONAL_TASKS.csv'
  h=hashlib.sha256(p.read_bytes()).hexdigest()
  self.assertEqual(h,'8cc9c4d20b78cb80bff4fa9fd69750e0b7c172d6f48d07a7880b224bf5ddecca')

if __name__=='__main__':unittest.main()
