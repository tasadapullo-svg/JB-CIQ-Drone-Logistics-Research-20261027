# -*- coding: utf-8 -*-
"""Audit complete label coverage without QGIS. Python 3 standard library only.
No modification to original GeoPackage, node coordinates, or line geometry.
"""
from pathlib import Path
from collections import Counter
import csv, json, sqlite3, hashlib

ROOT=Path(__file__).resolve().parent.parent
GPKG=ROOT/'data'/'CIQ_ABC_FINAL_EDITABLE.gpkg'
CSV=ROOT/'data'/'ALL_68_STUDY_NODES_LONG_LAT.csv'
OUT=ROOT/'qa'
OUT.mkdir(exist_ok=True)
conn=sqlite3.connect(str(GPKG))
conn.row_factory=sqlite3.Row
rows=[]
for table, id_col, zone_override in (
    ('V7_ALL_62_RETAINED_ROLES','id',None),
    ('V8_CIQ_PORT_6_EVIDENCE_POINTS','node_id','A_PORT'),
    ('G_CIQ_ground_gateway','id','CIQ_GROUND'),
):
    for r in conn.execute('SELECT * FROM "'+table+'"'):
        code=str(r[id_col] or '').strip()
        name=str(r['name'] or '').strip()
        zone=zone_override or str(r['zone'] or '').strip()
        assert code and name and zone, (table,code,name,zone)
        assert r['geom'] is not None, ('missing point geometry',code)
        rows.append({'node_id':code,'full_name':name,'zone':zone,
                     'longitude_E':r['lon'],'latitude_N':r['lat'],
                     'source_layer':table,'overview_label':code,
                     'regional_and_canvas_label':code+'  |  '+name,
                     'expected_display':'YES'})
conn.close()
ids=[r['node_id'] for r in rows]
assert len(rows)==69 and len(set(ids))==69, 'Not exactly 69 unique nodes'
counts=dict(Counter(r['zone'] for r in rows))
assert counts=={'A':23,'C':29,'B':10,'A_PORT':6,'CIQ_GROUND':1}, counts
with CSV.open(encoding='utf-8-sig',newline='') as f:
    original=list(csv.DictReader(f))
assert len(original)==68
for row in original:
    matches=[r for r in rows if r['node_id']==row['node_id']]
    assert len(matches)==1
    match=matches[0]
    assert match['full_name']==row['name'], row['node_id']
    assert abs(float(match['longitude_E'])-float(row['longitude_E']))<1e-8
    assert abs(float(match['latitude_N'])-float(row['latitude_N']))<1e-8
rows.sort(key=lambda r:(['A','A_PORT','CIQ_GROUND','C','B'].index(r['zone']),r['node_id']))
with (OUT/'QA_ALL_69_NODE_LABELS.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=rows[0].keys())
    writer.writeheader();writer.writerows(rows)
summary={'status':'PASS','unique_node_labels':len(rows),'zones':counts,
         'overview_id_labels':69,'canvas_and_region_full_labels':69,
         'name_fields_missing':0,'coordinate_mismatches_with_68_node_csv':0,
         'gpkg_sha256':hashlib.sha256(GPKG.read_bytes()).hexdigest(),
         'warning':'This is a data and labeling-configuration audit, NOT a QGIS rendering/visual-overlap audit. Inspect exported PNGs in QGIS 3.22.4.'}
(OUT/'QA_ALL_69_LABELS_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
