import sys,unittest,csv,hashlib,json,zipfile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
from s07_recover_and_gate import digest,identity_check,csv_source_audit,raw_weather_audit
from read_weather_workbooks import extract_one
class S07RecoveryTests(unittest.TestCase):
 def test_source_count(self):
  x=json.loads((ROOT/'inputs/SOURCE_FILES_PINNED_14.json').read_text('utf-8'))
  self.assertEqual(len(x['files']),14)
  self.assertEqual(x['git_commit'],'4569817b8145efe2ae06f4b21addc1986f971c12')
 def test_unique_source_paths(self):
  a=json.loads((ROOT/'inputs/SOURCE_FILES_PINNED_14.json').read_text('utf-8'))['files']
  self.assertEqual(len({x['path'] for x in a}),14)
 def test_missing_file_fails_closed(self):
  self.assertEqual(identity_check(ROOT/'UNKNOWN.NONEXISTENT',{'size':1,'git_blob':'abcd'})['status'],'HOLD_FILE_MISSING')
 def test_blob_sha1_git_formula(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'a';p.write_bytes(b'hello\n');expected=hashlib.sha1(b'blob 6\0hello\n').hexdigest()
   self.assertEqual(digest(p,'sha1'),expected)
 def test_source_bytes_pass(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'a';p.write_bytes(b'hi')
   m={'size':2,'git_blob':hashlib.sha1(b'blob 2\0hi').hexdigest(),'sha256':hashlib.sha256(b'hi').hexdigest()}
   self.assertEqual(identity_check(p,m)['status'],'PASS_BYTES_HASH')
 def test_corrupted_source_blocks(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'a';p.write_bytes(b'hi')
   m={'size':99,'git_blob':'aa'}
   self.assertEqual(identity_check(p,m)['status'],'HOLD_INTEGRITY_OR_VERSION')
 def test_csv_missing_blocks(self):
  a=csv_source_audit(ROOT/'DOES_NOT_EXIST.csv','A_EDGES',False)
  self.assertEqual(a['status'],'HOLD_SOURCE_BYTES')
 def test_road_rows_a_gate(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'e.csv';p.write_text('source,target,length_m\n1,2,10\n',encoding='utf-8')
   a=csv_source_audit(p,'A_EDGES',True)
   self.assertEqual(a['status'],'HOLD_A_EDGE_COUNT_DIFFERENT_HISTORICAL_QA')
 def test_weather_missing_blocks(self):
  a=raw_weather_audit(ROOT/'DOES_NOT_EXIST.xlsx','05',False)
  self.assertEqual(a['status'],'HOLD_SOURCE_BYTES')
 def test_v5_node_count(self):
  p=ROOT/'inputs/S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv'
  with p.open(encoding='utf-8-sig',newline='') as f:rr=list(csv.DictReader(f))
  self.assertEqual(len(rr),68)
  self.assertEqual(len({r['node_id'] for r in rr}),68)
  self.assertFalse(any(x['node_id']=='A_N10' for x in rr))
 def test_tasks_unchanged_structure(self):
  p=ROOT/'inputs/S07_V5_SYNTHETIC_TASKS_CONDITIONAL_DESIGN.csv';count=0;seen=set()
  with p.open(encoding='utf-8-sig',newline='') as f:
   for r in csv.DictReader(f):
    count+=1;seen.add(r['task_id'])
    self.assertEqual(r['service_and_carbon_result_status'],'NOT_COMPUTED')
  self.assertEqual((count,len(seen)),(82620,82620))
 def test_scenarios_4590(self):
  with (ROOT/'inputs/S07_V5_4590_SEED_DAY_RUN_MANIFEST.csv').open(encoding='utf-8-sig',newline='') as f:rr=list(csv.DictReader(f))
  self.assertEqual(len(rr),4590)
 def test_source_holds_are_not_missing_orders(self):
  a=json.loads((ROOT/'qa/S07_RELEASE_GATE.json').read_text('utf-8'))
  self.assertEqual(a['frozen_task_population'],82620)
  self.assertEqual(a['S08_petrol_operational_result'],'HOLD')
 def test_minimal_xlsx_raw_sheet(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'x.xlsx'
   with zipfile.ZipFile(p,'w') as z:
    z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Weather_Hourly" sheetId="1" r:id="rId1"/></sheets></workbook>')
    z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="x" Target="worksheets/sheet1.xml"/></Relationships>')
    z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>time</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>2026-05-01</t></is></c></row></sheetData></worksheet>')
   a=extract_one(p,Path(tmp)/'raw.csv','Weather_Hourly',digest(p,'sha256'))
   self.assertEqual(a['rows'],1)
 def test_no_fabricated_emissions(self):
  p=ROOT/'qa/S07_RELEASE_GATE.json';d=json.loads(p.read_text('utf-8'))
  self.assertEqual(d['S10_S11_S12_results'],'NOT_RUN')
if __name__=='__main__':unittest.main(verbosity=2)
