"""NEA 2026-05 historical observational data acquisition (best effort, no imputation).
Usage: python NEA_May2026_Download.py
Dependencies: requests (pip install requests)
Outputs: raw JSON, exact observation CSVs, HTTP acquisition audit.
NOTE: NEA endpoint may not expose full historical 1-minute records via date query.
      This program logs absence/limitation; it never manufactures readings.
"""
import csv,hashlib,json,time
from pathlib import Path
from datetime import datetime,timedelta,date
import requests
OUT=Path('NEA_2026_05_raw');OUT.mkdir(exist_ok=True)
BASE='https://api-open.data.gov.sg/v2/real-time/api'
SERIES=['rainfall','wind-speed','wind-direction']
START=date(2026,5,1);END=date(2026,5,31)
S=requests.Session();S.headers.update({'User-Agent':'Academic-climate-data-research/1.0'})
def dump_csv(p,rows,fields):
 with p.open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def extract(payload,source,requested_date,raw_name):
 data=payload.get('data',{}) if isinstance(payload,dict) else {}
 if not isinstance(data,dict):return [],[]
 stations=data.get('stations',[])
 if not isinstance(stations,list):stations=[]
 readings=data.get('readings',[])
 if not isinstance(readings,list):readings=[]
 rows=[]
 for batch in readings:
  if not isinstance(batch,dict):continue
  stamp=batch.get('timestamp')
  for rec in batch.get('data',[]) if isinstance(batch.get('data',[]),list) else []:
   if isinstance(rec,dict):
    rows.append({'provider':'NEA','variable':source,'query_date':requested_date,'timestamp':stamp,'station_id':rec.get('stationId',rec.get('station_id')),'value_raw':rec.get('value'),'unit_raw':data.get('readingUnit'),'raw_file':raw_name})
 return rows,stations
records=[];station_rows=[];audit=[]
day=START
while day<=END:
 for product in SERIES:
  ds=day.isoformat();name=f'{product}_{ds}.json';path=OUT/name
  url=f'{BASE}/{product}'
  try:
   response=S.get(url,params={'date':ds},timeout=25)
   body=response.content
   path.write_bytes(body)
   digest=hashlib.sha256(body).hexdigest()
   payload=response.json() if response.ok else {}
   parsed,stations=extract(payload,product,ds,name)
   # Reject records outside requested May window (some providers ignore date argument)
   accepted=[x for x in parsed if str(x['timestamp'] or '').startswith('2026-05-')]
   for x in accepted:
    x['sha256_raw']=digest;x['source_url']=response.url
   records+=accepted
   for st in stations:
    if isinstance(st,dict):station_rows.append({'provider':'NEA','product':product,'query_date':ds,'station_metadata_json':json.dumps(st,ensure_ascii=False),'raw_file':name})
   audit.append({'date':ds,'product':product,'url':response.url,'http_status':response.status_code,'sha256':digest,'downloaded_bytes':len(body),'reported_readings':len(parsed),'accepted_may_readings':len(accepted),'error':''})
   print(ds,product,response.status_code,len(parsed),len(accepted))
  except Exception as e:
   audit.append({'date':ds,'product':product,'url':url,'http_status':'ERROR','sha256':'','downloaded_bytes':0,'reported_readings':0,'accepted_may_readings':0,'error':repr(e)})
   print(ds,product,'ERROR',repr(e))
  time.sleep(0.25)
 day+=timedelta(days=1)
dump_csv(OUT/'observations_as_returned.csv',records,['provider','variable','query_date','timestamp','station_id','value_raw','unit_raw','raw_file','sha256_raw','source_url'])
dump_csv(OUT/'station_metadata.csv',station_rows,['provider','product','query_date','station_metadata_json','raw_file'])
dump_csv(OUT/'acquisition_audit.csv',audit,['date','product','url','http_status','sha256','downloaded_bytes','reported_readings','accepted_may_readings','error'])
print('Completed. Raw records:',len(records),'Audit requests:',len(audit))
print('CAUTION: 31 day-based requests DO NOT imply complete 30-minute coverage.')
print('Verify timestamps and station IDs before merging; NEA may return limited historical observations.')
