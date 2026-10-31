import csv, hashlib, importlib.util, json, pathlib, tempfile, unittest, zipfile
HERE=pathlib.Path(__file__).resolve().parents[1]
def module(name):
    sp=importlib.util.spec_from_file_location(name,HERE/'code'/f'{name}.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
R=module('recover_pinned_sources');W=module('read_weather_workbooks');G=module('audit_legacy_road_graph')
class TestPipeline(unittest.TestCase):
    def test_real_pinned_index(self):
        i=json.loads((HERE/'inputs/PINNED_SOURCE_INDEX.json').read_text());self.assertEqual(len(i['files']),11)
        self.assertEqual(len([f for f in i['files'] if f['sha256']]),5)
        self.assertTrue(all(len(f['git_blob'])==40 for f in i['files']))
    def test_missing_sources_not_pass(self):
        with tempfile.TemporaryDirectory() as d:
            base=pathlib.Path(d);res=R.run(HERE/'inputs/PINNED_SOURCE_INDEX.json',base/'src',base/'qa')
            self.assertEqual(len(res),11);self.assertTrue(all(x['status']=='HOLD_MISSING_BYTES' for x in res))
    def test_blob_hash_reproducible(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'a';p.write_bytes(b'testing');want=hashlib.sha1(b'blob 7\0testing').hexdigest();self.assertEqual(R.git_blob_id(p),want)
    def test_bad_version_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            b=pathlib.Path(d);p=b/'a';p.write_bytes(b'bad');idx={'files':[{'name':'a','path':'a','size':3,'git_blob':'0'*40,'sha256':'','scope':'test'}]}
            (b/'idx.json').write_text(json.dumps(idx));r=R.run(b/'idx.json',b,b/'qa');self.assertEqual(r[0]['status'],'FAIL_VERSION_OR_INTEGRITY')
    def test_raw_workbook_reading(self):
        # Independent synthetic OOXML fixture; NOT real weather data.
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'weather.xlsx';raw=pathlib.Path(d)/'raw.csv'
            wb='<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Weather_Hourly" sheetId="1" r:id="rId1"/></sheets></workbook>'
            rels='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
            sheet='<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>point_id</t></is></c><c r="B1" t="inlineStr"><is><t>wind</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>CW_MY</t></is></c><c r="B2"><v>3.2</v></c></row></sheetData></worksheet>'
            with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
                z.writestr('xl/workbook.xml',wb);z.writestr('xl/_rels/workbook.xml.rels',rels);z.writestr('xl/worksheets/sheet1.xml',sheet)
            x=W.extract_one(p,raw,'Weather_Hourly',hashlib.sha256(p.read_bytes()).hexdigest());self.assertEqual(x['rows'],1)
            with raw.open(encoding='utf-8-sig') as f:
                self.assertEqual(list(csv.DictReader(f))[0]['wind'],'3.2')
    def test_missing_weather_holds(self):
        with tempfile.TemporaryDirectory() as d:
            x=W.extract_one(pathlib.Path(d)/'missing.xlsx',pathlib.Path(d)/'out.csv','Weather_Hourly','');self.assertEqual(x['status'],'HOLD_FILE_MISSING')
    def test_road_coverage_all_zones_on_missing(self):
        with tempfile.TemporaryDirectory() as d:
            b=pathlib.Path(d);nodes=b/'nodes.csv'
            with nodes.open('w',newline='') as f:
                w=csv.DictWriter(f,['node_id','zone','latitude','longitude']);w.writeheader()
                for z,i in [('A','A01'),('B','B01'),('C','C01'),('PORT_A','A_P01'),('GATEWAY','G_CIQ')]:w.writerow(dict(node_id=i,zone=z,latitude=1.5,longitude=103.7))
            G.qa(b,nodes,b/'out')
            with (b/'out/node_road_access_candidates_NOT_APPROVED.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),5);self.assertTrue(all(x['status'].startswith('HOLD') for x in rows))
    def test_directed_road_graph_read_not_approval(self):
        with tempfile.TemporaryDirectory() as d:
            b=pathlib.Path(d);nodes=b/'sites.csv'
            with nodes.open('w',newline='') as f:
                w=csv.DictWriter(f,['node_id','zone','latitude','longitude']);w.writeheader();w.writerow(dict(node_id='A01',zone='A',latitude=1.5000,longitude=103.7500))
            ep=b/'E02_A_directed_edges_OSM.csv';np=b/'E02_A_road_graph_nodes.csv'
            with ep.open('w',newline='') as f:
                w=csv.DictWriter(f,['source','target','length_m']);w.writeheader();w.writerow(dict(source=1,target=2,length_m=500))
            with np.open('w',newline='') as f:
                w=csv.DictWriter(f,['osm_node_id','latitude','longitude']);w.writeheader();w.writerow(dict(osm_node_id=1,latitude=1.5,longitude=103.75));w.writerow(dict(osm_node_id=2,latitude=1.5,longitude=103.752))
            G.qa(b,nodes,b/'out')
            with (b/'out/node_road_access_candidates_NOT_APPROVED.csv').open(encoding='utf-8-sig') as f:r=list(csv.DictReader(f))
            self.assertEqual(r[0]['candidate_osm_node_id'],'1');self.assertEqual(r[0]['road_vehicle_access_approved'],'NO')
if __name__=='__main__':unittest.main()

class TestWeatherJoin(unittest.TestCase):
    def test_absent_era5_does_not_generate_rows(self):
        with tempfile.TemporaryDirectory() as d:
            b=pathlib.Path(d)
            assignment=b/'a.csv';timeline=b/'t.csv'
            assignment.write_text('node_id,zone,era5_nearest_returned_cell_lat,era5_nearest_returned_cell_lon,era5_grid_candidate_distance_km\nA01,A,1.5,103.75,2\n')
            timeline.write_text('interval_start_local\n2026-05-01T00:00:00+08:00\n')
            mod=module('join_verified_era5_to_nodes');r=mod.process(b/'bad.csv',assignment,timeline,b/'out')
            self.assertEqual(r['reason'],'HOLD_ERA5_CSV_NOT_PRESENT')
    def test_real_join_logic_synthetic_fixture_only(self):
        with tempfile.TemporaryDirectory() as d:
            b=pathlib.Path(d);src=b/'a.csv';ass=b/'ass.csv';tl=b/'tl.csv'
            src.write_text('point_id,timestamp_hour_start_sgt,ERA5_wind_10m_ms,ERA5_wind_direction_10m_deg,ERA5_precipitation_mm_h\nCW_MY,2026-05-01T00:00:00+08:00,4,80,0.0\nSL_MY,2026-05-01T00:00:00+08:00,2,230,0.2\n')
            ass.write_text('node_id,zone,era5_nearest_returned_cell_lat,era5_nearest_returned_cell_lon,era5_grid_candidate_distance_km\nA01,A,1.5,103.75,3.7\nB01,B,1.5,103.5,13.7\n')
            tl.write_text('interval_start_local\n2026-05-01T00:00:00+08:00\n')
            mod=module('join_verified_era5_to_nodes');r=mod.process(src,ass,tl,b/'out')
            self.assertEqual(r['row_count'],2);self.assertEqual(r['status'],'GENERATED_SPATIAL_PROXY_ONLY')
            with (b/'out/S07_ERA5_69node_3672hour_spatial_proxy_NOT_OPERATIONAL_RELEASE.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
            self.assertEqual(rows[0]['reference_point_id'],'CW_MY')
            self.assertEqual(rows[1]['reference_point_id'],'SL_MY')
