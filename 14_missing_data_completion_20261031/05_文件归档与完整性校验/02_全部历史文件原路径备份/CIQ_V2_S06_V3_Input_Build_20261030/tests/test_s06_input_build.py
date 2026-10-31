#!/usr/bin/env python3
"""Independent validations of ACTUAL V3-derived S06 outputs (not only toy tests)."""
import csv, hashlib, json, pathlib, sqlite3, sys, unittest, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
D=ROOT/'outputs/data'; GEO=ROOT/'outputs/geojson';QA=ROOT/'outputs/qa'
SRC=ROOT/'inputs/CIQ_ABC_QGIS322_NEW_COMPLETE_PROJECT_ALL_FILES_V3.zip'

def csvrows(s):
 with (D/s).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

class SourceAndModeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.nodes=csvrows('S06_69_node_master.csv')
  cls.u=csvrows('S06_116_uav_geometry_candidates_ONLY.csv')
  cls.g=csvrows('S06_5_ground_handoff_straight_references_NOT_ROUTES.csv')
  cls.cross=csvrows('S06_crosswalk_legacy19_vs_V3_69_NOT_VERIFIED.csv')
  cls.road=csvrows('S06_69_road_access_evidence_HOLD.csv')
  cls.air=csvrows('S06_69_airspace_and_site_evidence_HOLD.csv')
  cls.audit=json.loads((QA/'S06_formal_rebuild_audit.json').read_text(encoding='utf-8'))
 def test_01_original_uploaded_sha256(self):
  h=hashlib.sha256(SRC.read_bytes()).hexdigest()
  self.assertEqual(h,'a4e4d05397fa62d4611ea8a9a443445f8c6b9ae95c5ad545e7dea83aecd8ad92')
  self.assertEqual(self.audit['source_v3_sha256'],h)
 def test_02_zip_crc_and_referenced_parts(self):
  with zipfile.ZipFile(SRC) as z:
   self.assertIsNone(z.testzip());names=z.namelist()
   self.assertEqual(len(names),34)
   self.assertEqual(len(set(names)),34)
 def test_03_geopackage_source_reading(self):
  with zipfile.ZipFile(SRC) as z:
   p=next(n for n in z.namelist() if n.endswith('CIQ_ABC_FINAL_EDITABLE.gpkg'))
   import tempfile
   with tempfile.TemporaryDirectory() as tmp:
    f=pathlib.Path(tmp)/'g.gpkg';f.write_bytes(z.read(p))
    con=sqlite3.connect(str(f));self.assertEqual(con.execute('pragma integrity_check').fetchone()[0],'ok')
    self.assertEqual(con.execute('select count(*) from V7_ALL_62_RETAINED_ROLES').fetchone()[0],62)
    con.close()
 def test_04_node_unique_complete_and_zone_partition(self):
  self.assertEqual(len(self.nodes),69)
  self.assertEqual(len({r['node_id'] for r in self.nodes}),69)
  self.assertEqual({z:sum(r['zone']==z for r in self.nodes) for z in ['A','B','C','PORT_A','GATEWAY']},
   {'A':23,'B':10,'C':29,'PORT_A':6,'GATEWAY':1})
  self.assertTrue(all(r['name'].strip() for r in self.nodes))
 def test_05_source_label_name_and_coordinates(self):
  source={}
  with zipfile.ZipFile(SRC) as z:
   p=next(n for n in z.namelist() if n.endswith('QA_ALL_69_NODE_LABELS.csv'))
   reader=csv.DictReader(z.read(p).decode('utf-8-sig').splitlines())
   source={r['node_id']:r for r in reader}
  self.assertEqual(len(source),69)
  for r in self.nodes:
   s=source[r['node_id']];self.assertEqual(r['name'],s['full_name'])
   self.assertLess(abs(float(r['longitude'])-float(s['longitude_E'])),1e-8)
   self.assertLess(abs(float(r['latitude'])-float(s['latitude_N'])),1e-8)
 def test_06_unambiguous_edge_mode_split(self):
  self.assertEqual(len(self.u),116);self.assertEqual(len(self.g),5)
  self.assertEqual(sum(r['source_series']=='V7_111' for r in self.u),111)
  self.assertEqual(sum(r['source_series']=='V8_10' for r in self.u),5)
  self.assertTrue(all(r['line_mode']=='UAV_GEOMETRY_SEARCH' for r in self.u))
  self.assertTrue(all(r['line_mode']=='GROUND_HANDOFF_STRAIGHT_REFERENCE' for r in self.g))
  self.assertFalse(set(r['edge_id'] for r in self.u)&set(r['edge_id'] for r in self.g))
 def test_07_known_bad_mode_flags_cannot_dispatch(self):
  self.assertTrue(all(r['original_dji_flag_must_be_ignored']=='1' for r in self.g))
  self.assertTrue(all(r['original_wing_flag_must_be_ignored']=='1' for r in self.g))
  self.assertTrue(all(r['road_simulation_released']=='NO' and r['road_distance_km']=='' for r in self.g))
  self.assertTrue(all(r['drone_dispatch_released']=='NO' for r in self.u))
 def test_08_geometry_endpoint_and_length_audit(self):
  ids={r['node_id'] for r in self.nodes}
  for r in self.u+self.g:
   self.assertIn(r['from_id'],ids);self.assertIn(r['to_id'],ids)
   self.assertLessEqual(float(r['distance_attribute_delta_m']),1.1)
   self.assertGreater(float(r['line_distance_geodesic_km']),0)
  self.assertLessEqual(self.audit['max_line_geodesic_attribute_delta_m'],1.1)
 def test_09_crosswalk_not_wrongly_certified(self):
  self.assertEqual(len(self.cross),69)
  self.assertEqual(sum(bool(r['legacy_node_id_candidate']) for r in self.cross),19)
  self.assertTrue(all(r['old_source_sha256']=='' and r['old_longitude']=='' for r in self.cross))
  self.assertFalse(self.audit['old_stage8_crosspackage_coords_verified'])
  a10=next(r for r in self.cross if r['new_node_id']=='A10')
  self.assertIn('REVIEW',a10['crosswalk_status'])
 def test_10_road_access_and_airspace_not_claimed(self):
  self.assertEqual(len(self.road),69);self.assertEqual(len(self.air),69)
  self.assertTrue(all(r['road_access_verified']=='NO' for r in self.road))
  self.assertTrue(all(r['official_caam_current_date_AIP_boundary_loaded']=='NO' for r in self.air))
  self.assertTrue(all(r['actual_takeoff_approval']=='NO' for r in self.air))
 def test_11_geojson_matches_counts(self):
  for name,num in [('S06_69_reference_nodes.geojson',69),('S06_116_UAV_GEOMETRY_ONLY.geojson',116),('S06_5_ground_handoff_NOT_ROADS.geojson',5)]:
   data=json.loads((GEO/name).read_text(encoding='utf-8'))
   self.assertEqual(data['type'],'FeatureCollection');self.assertEqual(len(data['features']),num)
 def test_12_legacy_road_exception_not_repaired(self):
  exceptions=csvrows('S06_legacy37_road_OD_exceptions_NOT_REPAIRED.csv')
  self.assertEqual(len(exceptions),37)
  self.assertTrue(all(r['endpoint_ids_in_new_v3']=='True' for r in exceptions))
  self.assertTrue(all(r['old_repair_applied'] in ('False','NO','0','') for r in exceptions))
  self.assertTrue(all(r['status'].startswith('HOLD') for r in exceptions))
 def test_13_release_gates_stop_simulation(self):
  self.assertEqual(self.audit['gates']['spatial_reference_lock'],'PASS_FOR_REFERENCE_AND_S06_INPUT_BUILD')
  self.assertTrue(self.audit['gates']['M0_M1_M2_real_experiment'].startswith('HOLD'))
  self.assertEqual(self.audit['approved_UAV_sites'],0)
 def test_14_qgs_qgz_xml_same_source(self):
  import xml.etree.ElementTree as ET
  with zipfile.ZipFile(SRC) as z:
   qgs=next(z.read(n) for n in z.namelist() if n.endswith('CIQ_ABC_ALL_69_NAMES_PORTABLE.qgs'))
   qgz_bytes=next(z.read(n) for n in z.namelist() if n.endswith('CIQ_ABC_ALL_69_NAMES_PORTABLE.qgz'))
   with zipfile.ZipFile(__import__('io').BytesIO(qgz_bytes)) as z2:
    qgs2=z2.read(next(n for n in z2.namelist() if n.endswith('.qgs')))
   self.assertEqual(qgs,qgs2)
   self.assertEqual(ET.fromstring(qgs).tag,'qgis')

if __name__=='__main__':unittest.main(verbosity=2)
