#!/usr/bin/env python3
"""Read-only strict existence and SHA check of S07 physical bytes; no inferred weather."""
import json,hashlib,argparse,pathlib,os

def gitblob(path):
 h=hashlib.sha1();h.update(b'blob '+str(path.stat().st_size).encode()+b'\x00')
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def main(root):
 root=pathlib.Path(root);p=root/'inputs/PINNED_SOURCE_INDEX.json';idx=json.loads(p.read_text())
 dest=root/'recovered_sources';dest.mkdir(exist_ok=True)
 rec=[]
 for x in idx['files']:
  z=dest/x['name'];status='HOLD_BYTES_ABSENT'
  if z.is_file():
   if z.stat().st_size!=x['size']:status='HOLD_BYTES_SIZE'
   elif x.get('sha256') and sha(z)!=x['sha256']:status='HOLD_SHA256'
   elif x.get('sha256'):
    status='PASS_EXACT_BYTES' if gitblob(z)==x.get('git_blob') else 'HOLD_GIT_BLOB_MISMATCH'
   elif gitblob(z)==x.get('git_blob'):
    status='PASS_GIT_BLOB_IDENTITY_ONLY'
   else:status='HOLD_GIT_BLOB_MISMATCH'
  rec.append({'name':x['name'],'git_blob':x.get('git_blob',''),'expected_bytes':x['size'],'raw_bytes_available':z.is_file(), 'status':status})
 road=root/'outputs/V5_ABC_OSM_CONDITIONAL/V5_ABC_DRIVE_DIRECTED_OSM_SNAPSHOT_NOT_HISTORICAL.graphml'
 road_status='HOLD_FULL_ABC_GRAPH_NOT_PRESENT'
 if road.exists():road_status='HOLD_GRAPH_PRESENT_REQUIRES_SITE_ACCESS_DIRECTION_AND_HISTORICITY_QA'
 report={'metadata_source_commit':idx['git_commit'], 'files':rec,
  'physical_files_with_verified_sha256':sum(x['status']=='PASS_EXACT_BYTES' for x in rec),
  'weather_workbooks_accepted':sum(x['name'].endswith('.xlsx') and x['status']=='PASS_EXACT_BYTES' for x in rec),
  'full_ABC_road_graph':road_status,
  'S07_numeric_weather_released':False,
  'S07_driving_route_released':False,
  'S08_fuel_and_S09_mission_carbon_released':False,
  'reason':'Metadata alone is not a numeric data read; GIS straight lines are not driving routes.'}
 (root/'qa/S07_S09_CURRENT_SOURCE_RELEASE_GATE.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps({k:report[k] for k in ['physical_files_with_verified_sha256','weather_workbooks_accepted','full_ABC_road_graph']}))
 return report
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--root',default=str(pathlib.Path(__file__).resolve().parents[1]));v=a.parse_args();main(v.root)
