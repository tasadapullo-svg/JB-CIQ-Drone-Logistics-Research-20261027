import unittest,sys,tempfile,hashlib,zipfile,json,csv,gzip,datetime as dt
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'tools/ciq_s07'))
import qa_real as qa


def build_weather_xlsx(path,duplicate=False):
    """Actual OOXML ZIP with two worksheets; test values are clearly synthetic."""
    from xml.sax.saxutils import escape
    def sheet(era=False):
        rows=[('<row r="1"><c r="A1" t="inlineStr"><is><t>point_id</t></is></c><c r="B1" t="inlineStr"><is><t>time_sgt</t></is></c></row>')]
        idx=1
        for pt in sorted(qa.REF_POINTS):
            for h in range(744):
                idx+=1;ts=dt.datetime(2026,5,1)+dt.timedelta(hours=h)
                if duplicate and pt=='CW_MY' and h==1: ts=dt.datetime(2026,5,1)
                rows.append(f'<row r="{idx}"><c r="A{idx}" t="inlineStr"><is><t>{pt}</t></is></c><c r="B{idx}" t="inlineStr"><is><t>{ts.isoformat(sep=" ")}</t></is></c></row>')
            if era:
                idx+=1;rows.append(f'<row r="{idx}"><c r="A{idx}" t="inlineStr"><is><t>{pt}</t></is></c><c r="B{idx}" t="inlineStr"><is><t>2026-06-01 00:00:00</t></is></c></row>')
        return '<?xml version="1.0" encoding="utf-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+''.join(rows)+'</sheetData></worksheet>'
    book='<?xml version="1.0" encoding="utf-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Weather_Hourly" sheetId="1" r:id="rId1"/><sheet name="ERA5_Hourly" sheetId="2" r:id="rId2"/></sheets></workbook>'
    rel='<?xml version="1.0" encoding="utf-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/></Relationships>'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('xl/workbook.xml',book);z.writestr('xl/_rels/workbook.xml.rels',rel)
        z.writestr('xl/worksheets/sheet1.xml',sheet(False))
        z.writestr('xl/worksheets/sheet2.xml',sheet(True))

class RealS07QA(unittest.TestCase):
    def test_frozen_has_unchanged_68_82620_4590_22950(self):
        r=qa.zip_frozen_check(BASE/'tools/ciq_s07/frozen_v5_inputs.zip',BASE/'tools/ciq_s07/frozen_lock.json')
        self.assertEqual(r['status'],'PASS');self.assertEqual((r['nodes'],r['tasks'],r['runs'],r['modes']),(68,82620,4590,22950))
        self.assertEqual(r['zone_counts'],{'A':29,'B':10,'C':29})
    def test_pinned_git_commit(self):
        self.assertEqual(json.loads((BASE/'tools/ciq_s07/source_index.json').read_text())['git_commit'],qa.PIN)
    def test_local_time_with_offset(self):
        self.assertEqual(qa.local_hour('2026-05-01T00:00:00+08:00'),dt.datetime(2026,5,1))
    def test_utc_to_malaysia(self):
        self.assertEqual(qa.local_hour('2026-04-30T16:00:00Z'),dt.datetime(2026,5,1))
    def test_non_hour_timestamp_rejected(self):
        self.assertIsNone(qa.local_hour('2026-05-01 00:45:00'))
    def test_invalid_timestamp_rejected(self):
        self.assertIsNone(qa.local_hour('wrong'))
    def test_byte_identity_pass_and_fail(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=root/'test.dat';p.write_bytes(b'actual source bytes')
            meta={'path':'test.dat','name':'test.dat','size':p.stat().st_size,'git_blob':qa.digest(p,'sha1'),'sha256':qa.digest(p),'scope':'TEST'}
            self.assertEqual(qa.source_status(meta,root)['status'],'PASS_BYTES')
            meta['size']+=1;self.assertEqual(qa.source_status(meta,root)['status'],'HOLD_VERSION_OR_INTEGRITY')
            p.unlink();self.assertEqual(qa.source_status(meta,root)['status'],'MISSING')
    def test_monthly_weather_fixture_good_with_four_boundary_rows(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'May_fixture.xlsx';build_weather_xlsx(p)
            r=qa.weather_check(p,5,Path(td)/'extract')
            self.assertEqual(r['status'],'PASS_TIME_POINTS_ONLY')
            self.assertEqual(r['rows'],{'Weather_Hourly':2976,'ERA5_Hourly':2980})
            self.assertEqual(r['ERA5_out_of_month_per_point'],{x:1 for x in qa.REF_POINTS})
            self.assertEqual(r['weather_units_release'],'HOLD_NEEDS_METADATA')
    def test_duplicate_hour_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad_fixture.xlsx';build_weather_xlsx(p,duplicate=True)
            r=qa.weather_check(p,5,Path(td)/'extract')
            self.assertEqual(r['status'],'HOLD_WEATHER_TIME_QA')
            self.assertGreater(r['duplicate_keys'],0)
    def test_bad_fcd_not_released(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'fcd.csv.gz'
            with gzip.open(p,'wt',encoding='utf-8',newline='') as f:
                w=csv.writer(f);w.writerow(['node_id','time_sgt','speed_kmh']);w.writerow(['n1','2026-05-01 00:00:00','']);w.writerow(['n1','2026-05-01 00:00:00','0'])
            r=qa.fcd_check(p);self.assertEqual(r['status'],'HOLD_STRUCTURE')
            self.assertEqual(r['duplicate_node_hour'],1)
            self.assertEqual(r['speed_states']['MISSING'],1)
            self.assertEqual(r['speed_states']['NONPOSITIVE'],1)
    def test_no_unauthorized_emission(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'qa';r=qa.main(Path(td)/'no_repo',BASE/'tools/ciq_s07',out)
            self.assertEqual(r['source_core_byte_pass'],0)
            self.assertEqual(r['frozen_V5']['status'],'PASS')
            self.assertEqual(r['M0_M1_M2_real_operation_result'],'NOT_COMPUTED')
            self.assertTrue((out/'S07_GITHUB_ACTUAL_NUMERIC_QA.json').is_file())

if __name__=='__main__':unittest.main(verbosity=2)
