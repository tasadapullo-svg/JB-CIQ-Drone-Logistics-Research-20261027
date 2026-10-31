import tempfile,sys,unittest,json,hashlib,csv
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from stage05_release_check import audit_evidence, audit_parameter_table, check, hash_file
ROOT=Path(__file__).resolve().parents[1]

class Stage05Test(unittest.TestCase):
    def test_real_gate_stays_hold(self):
        d=check(ROOT, ROOT/'results/stage05_release_result_test.json')
        self.assertEqual(d['release_status'],'HOLD_NO_SIMULATION')
        self.assertFalse(d['permission_to_run_main_experiment'])
        self.assertEqual(sum(g['pass'] for g in d['gate_status']),0)
    def test_sources_referenced(self):
        with (ROOT/'records/stage05_parameter_registry.csv').open(encoding='utf-8-sig',newline='') as f:
            x=list(csv.DictReader(f))
        with (ROOT/'records/source_registry.csv').open(encoding='utf-8-sig',newline='') as f:
            src={z['source_id'] for z in csv.DictReader(f)}
        self.assertGreaterEqual(len(x),40)
        self.assertTrue(all((r['source_id'] in src) or (r['source_id']=='') for r in x))
    def test_approved_ref_value_or_blocked_null(self):
        p=audit_parameter_table(ROOT/'records/stage05_parameter_registry.csv')
        self.assertEqual(p['issues'],[])
    def test_missing_proof_rejected(self):
        with tempfile.TemporaryDirectory() as z:
            g={'hard_requirements':[{'id':'ONE','status':'PASS','evidence_path':'does_not_exist.txt','sha256':'1'*64}]}
            v=audit_evidence(g,Path(z))[0]
            self.assertFalse(v['pass']);self.assertIn('EVIDENCE_FILE_MISSING',v['checks'])
    def test_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as z:
            p=Path(z)/'evidence.txt';p.write_text('abc')
            v=audit_evidence({'hard_requirements':[{'id':'ONE','status':'PASS','evidence_path':'evidence.txt','sha256':'b'*64}]},Path(z))[0]
            self.assertFalse(v['pass']);self.assertIn('SHA256_MISMATCH',v['checks'])
    def test_hash_proof_verified(self):
        with tempfile.TemporaryDirectory() as z:
            p=Path(z)/'evidence.txt';p.write_text('abc')
            v=audit_evidence({'hard_requirements':[{'id':'ONE','status':'PASS','evidence_path':'evidence.txt','sha256':hash_file(p)}]},Path(z))[0]
            self.assertTrue(v['pass'])
    def test_directory_escape_rejected(self):
        with tempfile.TemporaryDirectory() as z:
            v=audit_evidence({'hard_requirements':[{'id':'ONE','status':'PASS','evidence_path':'../../x.txt','sha256':'b'*64}]},Path(z))[0]
            self.assertIn('EVIDENCE_OUTSIDE_PROJECT_ROOT',v['checks'])
    def test_gas_mismatch_clear(self):
        p=json.loads((ROOT/'records/stage05_unified_task_protocol.json').read_text(encoding='utf-8'))
        self.assertIn('do not use 0.740 MY kgCO2e and 0.402 SG kgCO2',p['accounting']['grid_CO2_formula'])
    def test_sample_is_unique_concept(self):
        p=json.loads((ROOT/'records/stage05_unified_task_protocol.json').read_text(encoding='utf-8'))
        self.assertTrue(any('never add 918000' in s for s in p['task_constraints']))
    def test_18_release_gates(self):
        with (ROOT/'records/stage05_release_gates.csv').open(encoding='utf-8-sig',newline='') as f: self.assertEqual(len(list(csv.DictReader(f))),18)

if __name__=='__main__':unittest.main(verbosity=2)
