import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE=Path(__file__).resolve().parents[1]/"scripts"/"stage04_evidence_gate.py"
spec=importlib.util.spec_from_file_location("audit",MODULE)
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

class AuditTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.d=Path(self.t.name)
    def tearDown(self):self.t.cleanup()
    def write_csv(self,name,fields,rows):
        path=self.d/name
        with path.open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
        return path
    def fixtures(self):
        od=self.write_csv("od.csv",audit.OD_REQUIRED,[
          dict(od_id="A01_A02",area="A",cross_border_route="False",original_route_exists="True",diagnostic_category="NONE_EXISTING_ROUTE",original_status="MODEL_ROUTE_REQUIRES_QA",candidate_route_found="False"),
          dict(od_id="B02_B01",area="B",cross_border_route="False",original_route_exists="False",diagnostic_category="DATA_GAP",original_status="SNAP_REVIEW_REQUIRED",candidate_route_found="True")])
        repair=self.write_csv("repair.csv",audit.REPAIR_REQUIRED,[dict(od_id="B02_B01",area="B",diagnostic_category="DATA_GAP",candidate_route_found="True",repair_applied="False",residual_exception="UNVERIFIED")])
        return od,repair
    def test_unapproved_candidate_does_not_become_path(self):
        o,r=self.fixtures();d=audit.audit_od(audit.read_csv(o,audit.OD_REQUIRED),audit.read_csv(r,audit.REPAIR_REQUIRED))
        self.assertEqual(d["counts"]["routable_original"],1)
        self.assertEqual(d["counts"]["repairs_applied"],0)
        self.assertIn("UNAPPROVED_OD_REPAIRS_REMAIN",d["issues"])
    def test_no_crossborder_is_detected(self):
        o,r=self.fixtures();d=audit.audit_od(audit.read_csv(o,audit.OD_REQUIRED),audit.read_csv(r,audit.REPAIR_REQUIRED))
        self.assertIn("NO_CROSS_BORDER_OD_IN_HISTORY",d["issues"])
    def test_duplicate_od_is_blocked(self):
        o,r=self.fixtures();rows=audit.read_csv(o,audit.OD_REQUIRED);rows.append(rows[0]);d=audit.audit_od(rows,audit.read_csv(r,audit.REPAIR_REQUIRED))
        self.assertIn("DUPLICATE_OD_ID",d["issues"])
    def test_fabricated_repair_release_is_blocked(self):
        o,r=self.fixtures();rows=audit.read_csv(r,audit.REPAIR_REQUIRED);rows[0]["repair_applied"]="True"
        d=audit.audit_od(audit.read_csv(o,audit.OD_REQUIRED),rows)
        self.assertIn("APPLIED_REPAIR_MISSING_EXPLICIT_REVIEWER_APPROVAL",d["issues"])
    def test_weather_repeated_grids(self):
        weather={"months":{"05":{"anomaly_total":0,"weather_hourly_rows":100,
          "era5_grid_by_point":[{"latitude_returned":1.5,"longitude_returned":103.75},{"latitude_returned":1.5,"longitude_returned":103.75}],
          "coverage":[{"source":"NEA","variable":"rainfall","status":"PARTIAL"}],
          "era5_nasa_rain":{"correlation":0.03}}}}
        d=audit.audit_weather_qc(weather)
        self.assertIn("MONTH_05_REPEATED_ERA5_GRID",d["issues"])
        self.assertIn("MONTH_05_NEA_NOT_FULLY_VALIDATED",d["issues"])
    def test_does_not_issue_authorization(self):
        o,r=self.fixtures()
        g=self.d/"spatial.json";g.write_text('{"scientific_spatial_input_frozen":true,"status":"PASS"}')
        out=audit.run(o,r,None,g)
        self.assertFalse(out["recalculation_authorized"])
        self.assertEqual(out["status"],"HOLD_RECALC_BLOCKED")
    def test_row_repair_mismatch(self):
        o,r=self.fixtures();rows=audit.read_csv(r,audit.REPAIR_REQUIRED);rows[0]["area"]="C"
        d=audit.audit_od(audit.read_csv(o,audit.OD_REQUIRED),rows)
        self.assertTrue(any("MISMATCH" in x for x in d["issues"]))

if __name__=="__main__":unittest.main()
