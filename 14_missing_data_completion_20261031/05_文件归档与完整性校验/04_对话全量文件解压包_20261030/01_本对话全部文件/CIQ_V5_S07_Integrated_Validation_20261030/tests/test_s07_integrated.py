import csv,datetime as dt,gzip,hashlib,importlib.util,sys,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
import build_s07_integrated as v

class S07ActualTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.nodes=v.readcsv(ROOT/'inputs/S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv')
  cls.orders=v.readcsv(ROOT/'inputs/S07_V5_SYNTHETIC_TASKS_CONDITIONAL_DESIGN.csv')
  cls.audit=v.audit_frozen(cls.nodes,cls.orders)
  cls.out=ROOT/'outputs'

 def test_01_real_frozen_node_count(self): self.assertEqual(self.audit['node_count'],68)
 def test_02_real_frozen_order_count(self):self.assertEqual(self.audit['task_count'],82620)
 def test_03_real_scenario_count(self):self.assertEqual(self.audit['scenario_count'],4590)
 def test_04_zone_totals(self):self.assertEqual(self.audit['node_zones'],{'A':29,'B':10,'C':29})
 def test_05_a09_a10_zone_is_source_c(self):
  d={x['node_id']:x['zone'] for x in self.nodes}
  self.assertEqual(d['A09'],'C');self.assertEqual(d['A10'],'C')
 def test_06_no_legacy_a_n10(self):self.assertNotIn('A_N10',{z['node_id'] for z in self.nodes})
 def test_07_no_frozen_error(self):self.assertEqual(self.audit['status'],'PASS')
 def test_08_v5_source_zip_sha_lock(self):
  p=ROOT/'inputs/CIQ_ABC_QGIS322_V5_ONE_WMP228_68_NODES_FULL_PROJECT(1).zip'
  self.assertEqual(v.sha(p),'0d19633630b6f12525ad9bd776bbf966ec1e8a46520bd8bc3d904013b02dce74')
 def test_09_zip_crc(self):
  with zipfile.ZipFile(ROOT/'inputs/CIQ_ABC_QGIS322_V5_ONE_WMP228_68_NODES_FULL_PROJECT(1).zip') as z:self.assertIsNone(z.testzip())
 def test_10_timezone_utc(self):self.assertEqual(v.parse_hour('2026-04-30T16:00:00Z'),dt.datetime(2026,5,1,0))
 def test_11_timezone_local(self):self.assertEqual(v.parse_hour('2026-05-01T00:00:00+08:00'),dt.datetime(2026,5,1,0))
 def test_12_reject_partial_hours(self):self.assertIsNone(v.parse_hour('2026-05-01T00:15:00+08:00'))
 def test_13_all_nodes_have_grid(self):self.assertEqual(len(v.node_grids(self.nodes)),68)
 def test_14_coarse_grid_warning(self):self.assertEqual(sum(x['grid_gt10km_warning'] for x in v.node_grids(self.nodes)),31)
 def test_15_task_weather_warning(self):
  gg={x['node_id']:x['grid_gt10km_warning'] for x in v.node_grids(self.nodes)}
  self.assertEqual(sum(gg[x['origin_node_id']] for x in self.orders),55080)
 def test_16_actual_hour_keys(self):
  with gzip.open(self.out/'S07_V5_249696_NODE_HOUR_LOOKUP_KEYS_ONLY.csv.gz','rt') as f:
   rr=csv.DictReader(f);self.assertEqual(sum(1 for _ in rr),249696)
 def test_17_no_invented_weather(self):
  with gzip.open(self.out/'S07_V5_249696_NODE_HOUR_LOOKUP_KEYS_ONLY.csv.gz','rt') as f:
   z=next(csv.DictReader(f));self.assertEqual(z['wind_m_s'],'');self.assertEqual(z['precip_mm'],'')
 def test_18_all_task_keys(self):
  with gzip.open(self.out/'S07_V5_82620_TASK_EVENT_KEYS_ONLY.csv.gz','rt') as f:
   rr=csv.DictReader(f);self.assertEqual(sum(1 for _ in rr),82620)
 def test_19_no_false_emissions(self):
  import json
  j=json.loads((self.out/'S07_FORMAL_RELEASE_DECISION.json').read_text('utf-8'))
  self.assertIn('HOLD',j['S07_FORMAL_RELEASE']);self.assertEqual(j['S10_S11_OPERATIONAL_CARBON'],'NOT_RUN')
 def test_20_source_lock_pinned(self):
  import json
  r=json.loads((ROOT/'inputs/source_index.json').read_text('utf-8'))
  self.assertEqual(r['git_commit'],v.PIN)
 def test_21_missing_files_are_not_released(self):
  import json
  r=json.loads((ROOT/'inputs/source_index.json').read_text('utf-8'))
  with tempfile.TemporaryDirectory() as tmp:
   r0=v.locked_source(Path(tmp),r)
   self.assertEqual(sum(x['status']=='PASS_BYTES' for x in r0),0)
 def test_22_source_sha_does_not_match_lookalike(self):
  import json
  r=json.loads((ROOT/'inputs/source_index.json').read_text('utf-8'))
  with tempfile.TemporaryDirectory() as tmp:
   file=Path(tmp)/r['files'][0]['path'];file.parent.mkdir(parents=True);file.write_bytes(b'fake data')
   r0=v.locked_source(Path(tmp),r)
   self.assertEqual(r0[0]['status'],'HOLD_VERSION_OR_CRC')
 def test_23_fcd_missing_cannot_be_zero_speed(self):
  with tempfile.TemporaryDirectory() as tmp:
   d=Path(tmp);c='node_id,timestamp_sgt,speed_kmh\n1,2026-05-01T00:00:00+08:00,\n2,2026-05-01T00:00:00+08:00,0\n3,2026-05-01T00:00:00+08:00,25\n'
   p=d/'a.gz'
   with gzip.open(p,'wt') as f:f.write(c)
   reg={'files':[{'name':'JB_CIQ_E01_corrected_five_month_traffic_data_345nodes_2026-05_09.csv.gz','path':'a.gz'}]}
   out=v.audit_fcd(d,reg,{reg['files'][0]['name']})
   self.assertEqual(out['speed_states'],{'MISSING':1,'NONPOSITIVE':1,'POSITIVE':1})
   self.assertEqual(out['status'],'HOLD_FCD_STRUCTURE')
 def test_24_era5_month_744_hours(self):self.assertEqual(sum(v.HOURS.values()),3672)
 def test_25_weather_sheet_with_real_xlsx_engine(self):
  import openpyxl
  with tempfile.TemporaryDirectory() as tmp:
   d=Path(tmp);b=openpyxl.Workbook();w=b.active;w.title='Weather_Hourly';w.append(['point_id','time_sgt','ERA5_wind_speed_10m','ERA5_precipitation'])
   for k in ['CW_MY','CW_SG','SL_MY','SL_SG']:
    for j in range(744):w.append([k,(dt.datetime(2026,5,1)+dt.timedelta(hours=j)).isoformat(),4.1,0.0])
   e=b.create_sheet('ERA5_Hourly');e.append(['point_id','time_sgt']);b.save(d/'sample.xlsx')
   reg={'files':[{'name':'JB_SG_Weather_2026_05.xlsx','path':'sample.xlsx'}]}
   outs=v.audit_weather(d,reg,{'JB_SG_Weather_2026_05.xlsx'},d)
   may=outs[0];self.assertEqual(may['status'],'PASS_WEATHER_TIME_AND_VALUES_WITH_UNIT_REVIEW');self.assertEqual(may['actual_rows'],2976)
 def test_26_timing_unique(self):
  self.assertEqual(len({(t['scenario_seed'],t['date_local']) for t in self.orders}),4590)

if __name__=='__main__':unittest.main(verbosity=2)
