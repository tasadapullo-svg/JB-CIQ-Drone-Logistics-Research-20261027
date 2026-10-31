import unittest,sys,io,csv,gzip,tempfile,json,hashlib,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from s07_structural_numeric_check import (sha256,blob_sha,source_identity,get_col,excel_or_text_hour,weather_hourly_validate,fcd_validate,roads_validate,scenario_check)
class QAGates(unittest.TestCase):
 def test_01_current_frozen_scenarios(self):self.assertEqual(scenario_check()['status'],'PASS_V5_FROZEN_PAIRS')
 def test_02_time_zone(self):self.assertEqual(excel_or_text_hour('2026-05-01T00:00:00+08:00').hour,0)
 def test_03_utc_conversion(self):self.assertEqual(excel_or_text_hour('2026-04-30T16:00:00Z').day,1)
 def test_04_invalid_time(self):self.assertIsNone(excel_or_text_hour('BAD'))
 def test_05_excel_serial(self):self.assertEqual(excel_or_text_hour('46143').year,2026)
 def test_06_column_resolution(self):self.assertEqual(get_col(['node_id','speed_kmh'],['speed_kmh']),'speed_kmh')
 def test_07_missing_source(self):
  with tempfile.TemporaryDirectory() as t:
   self.assertEqual(source_identity({'path':'x.csv','name':'x.csv'},Path(t))['status'],'HOLD_NOT_LOCAL')
 def test_08_actual_git_blob_hash(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'a';p.write_bytes(b'abc');self.assertEqual(blob_sha(p),hashlib.sha1(b'blob 3\x00abc').hexdigest())
 def test_09_gzip_speed_missing_not_zero(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'f.csv.gz'
   with gzip.open(p,'wt',newline='') as f:
    w=csv.writer(f);w.writerow(['node_id','timestamp_sgt','speed_kmh']);w.writerows([['n1','2026-05-01 00:00:00','20'],['n1','2026-05-01 01:00:00',''],['n1','2026-05-01 02:00:00','0']])
   z=fcd_validate(p);self.assertEqual(z['speed_states'],{'POSITIVE':1,'MISSING':1,'NONPOSITIVE':1});self.assertEqual(z['status'],'HOLD_FCD_STRUCTURAL_QA')
 def test_10_duplicate_FCD_key(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'f.csv.gz'
   with gzip.open(p,'wt',newline='') as f:
    w=csv.writer(f);w.writerow(['node_id','time_sgt','speed_kmh']);w.writerows([['n1','2026-05-01 00:00:00','20'],['n1','2026-05-01 00:00:00','20']])
   self.assertEqual(fcd_validate(p)['duplicate_node_hour_keys'],1)
 def test_11_weather_schema_two_points_incomplete(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'f.csv'
   with open(p,'w',encoding='utf-8',newline='') as f:
    w=csv.writer(f);w.writerow(['point_id','datetime_sgt','precip_mm']);w.writerow(['CW_MY','2026-05-01 00:00:00','5'])
   self.assertEqual(weather_hourly_validate(p,5)['status'],'HOLD_WEATHER_TIME_POINT_SCHEMA')
 def test_12_weather_duplicate_key(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'f.csv'
   with open(p,'w',encoding='utf-8',newline='') as f:
    w=csv.writer(f);w.writerow(['point_id','datetime_sgt']);w.writerow(['CW_MY','2026-05-01 00:00:00']);w.writerow(['CW_MY','2026-05-01 00:00:00'])
   self.assertEqual(weather_hourly_validate(p,5)['duplicate_point_hour_keys'],1)
 def test_13_road_length_bad(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'r.csv'
   with open(p,'w',encoding='utf-8',newline='') as f:
    w=csv.writer(f);w.writerow(['source','target','length_m','speed_kmh']);w.writerow(['1','2','0','30'])
   self.assertEqual(roads_validate(p,'A')['invalid_length'],1)
 def test_14_hash_failure_fails_closed(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'a.csv';p.write_bytes(b'abc')
   m={'path':'a.csv','name':'a.csv','size':3,'git_blob':'bad','sha256':hashlib.sha256(b'abc').hexdigest()}
   self.assertEqual(source_identity(m,Path(t))['status'],'HOLD_HASH_OR_ZIP_BAD')
 def test_15_valid_byte_hash(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'a.csv';p.write_bytes(b'abc')
   m={'path':'a.csv','name':'a.csv','size':3,'git_blob':blob_sha(p),'sha256':sha256(p)}
   self.assertEqual(source_identity(m,Path(t))['status'],'PASS_SOURCE_BYTES')
if __name__=='__main__':unittest.main(verbosity=2)
