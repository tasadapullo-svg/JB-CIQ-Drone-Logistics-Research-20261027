from pathlib import Path
import sys, json, hashlib, tempfile, unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from stage03_source_gate import audit,git_blob_id,review_weather,review_code,review_spatial

class TestStage03(unittest.TestCase):
    def test_git_blob(self):
        self.assertEqual(git_blob_id(b'hello\n'),'ce013625030ba8dba906f756967f9e9ca394464a')
    def test_monthly_logic(self):
        d={'months':{k:{'weather_hourly_rows':n,'manifest_sha_match':True,'anomaly_total':0,
            'coverage':[{'source':'NEA','variable':'rainfall','coverage_pct':0,'status':'NOT_REQUESTED'}],
            'era5_nasa_rain':{'correlation':0.1},'era5_nasa_wind':{'correlation':0.6}}
            for k,n in {'05':2976,'06':2880,'07':2976,'08':2976,'09':2880}.items()}}
        c,m=review_weather(d)
        self.assertEqual(len(m),5)
        self.assertTrue(any(x['gate']=='NEA_08' and x['status']=='NOT_REQUESTED' for x in c))
        self.assertTrue(any(x['gate']=='RAIN_CROSS_SOURCE_06' and x['status']=='REVIEW' for x in c))
    def test_legacy_patterns(self):
        x=review_code("q=o['release_time_local']\n")
        self.assertEqual(x[0]['status'],'FOUND_LEGACY_PATTERN')
    def test_gate_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s02.json'
            p.write_text(json.dumps({'scientific_spatial_input_frozen':False,
                   'project_file_sha256':'abc','counts':{'critical_issues':0}}))
            self.assertEqual(review_spatial(p)['status'],'HOLD')
            self.assertFalse(audit(stage02_gate=p)['numerical_recalculation_released'])
    def test_no_inputs_still_outputs_hold(self):
        x=audit()
        self.assertEqual(x['stage03_status'],'HOLD_RECALC_BLOCKED')
        self.assertTrue('HISTORICAL_WEATHER_SUMMARY_BLOB_NOT_VERIFIED' in x['blocking_codes'])

if __name__=='__main__':unittest.main()
