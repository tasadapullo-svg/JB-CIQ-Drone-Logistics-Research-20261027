#!/usr/bin/env python3
"""Stream selected worksheet from frozen monthly XLSX without inventing data.
Outputs raw Weather_Hourly rows and reports schema; NEVER assumes generic meteorological units.
Excel dates are converted only for columns whose name denotes time/date.
"""
import argparse,csv,datetime,hashlib,json,pathlib,re,xml.etree.ElementTree as ET,zipfile
S='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P='http://schemas.openxmlformats.org/package/2006/relationships'

def local(tag):return tag.rsplit('}',1)[-1]

def shared_strings(z):
    try:f=z.open('xl/sharedStrings.xml')
    except KeyError:return []
    arr=[]
    with f:
        for _,e in ET.iterparse(f,events=('end',)):
            if local(e.tag)=='si':
                arr.append(''.join(x.text or '' for x in e.iter() if local(x.tag)=='t'))
                e.clear()
    return arr

def sheet_location(z,name):
    root=ET.fromstring(z.read('xl/workbook.xml'))
    rid=None
    for e in root.iter():
        if local(e.tag)=='sheet' and e.get('name')==name:rid=e.get('{'+R+'}id');break
    if not rid:raise KeyError('MISSING_SHEET:'+name)
    rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    for e in rels:
        if e.get('Id')==rid:
            target=e.get('Target');return target.lstrip('/') if target.startswith('/') else 'xl/'+target.lstrip('./')
    raise KeyError('MISSING_RELATIONSHIP:'+name)

def col_idx(ref):
    col=''.join(x for x in ref if x.isalpha()).upper();idx=0
    for c in col:idx=idx*26+ord(c)-64
    return idx-1

def sheet_rows(z,name):
    loc=sheet_location(z,name);ss=shared_strings(z)
    with z.open(loc) as f:
        for _,elem in ET.iterparse(f,events=('end',)):
            if local(elem.tag)!='row':continue
            arr=[]
            for cell in elem:
                if local(cell.tag)!='c':continue
                i=col_idx(cell.get('r','A'))
                while len(arr)<=i:arr.append('')
                kind=cell.get('t','')
                if kind=='inlineStr':val=''.join(x.text or '' for x in cell.iter() if local(x.tag)=='t')
                else:
                    v=next((x.text for x in cell if local(x.tag)=='v'),None)
                    if v is None:val=''
                    elif kind=='s':val=ss[int(v)]
                    else:val=v
                arr[i]=val
            elem.clear()
            if any(x.strip() for x in arr):yield arr

def extract_one(path,output,sheet,expected_sha):
    path=pathlib.Path(path);output=pathlib.Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():return dict(file=path.name,status='HOLD_FILE_MISSING')
    h=hashlib.sha256(path.read_bytes()).hexdigest()
    if expected_sha and h!=expected_sha:return dict(file=path.name,status='HOLD_SHA256_MISMATCH',sha256_actual=h)
    try:
        with zipfile.ZipFile(path) as z:
            if z.testzip():return dict(file=path.name,status='HOLD_XLSX_CRC')
            it=iter(sheet_rows(z,sheet));header=[s.strip().replace('\ufeff','') for s in next(it)]
            if not header or len(set(header))!=len(header):return dict(file=path.name,status='HOLD_HEADER',headers=header)
            count=0
            with output.open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.writer(f);w.writerow(header)
                for row in it:
                    count+=1;w.writerow(row[:len(header)]+['']*max(0,len(header)-len(row)))
        return dict(file=path.name,status='EXTRACTED_RAW_NOT_OPERATIONALLY_RELEASED',sheet=sheet,rows=count,columns=header,sha256_actual=h)
    except Exception as exc:return dict(file=path.name,status='HOLD_PARSE_ERROR',error=str(exc)[:400])

def main(folder,index_path,out,sheet):
    folder=pathlib.Path(folder);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
    idx=json.loads(pathlib.Path(index_path).read_text('utf-8'))
    log=[]
    for d in idx['files']:
        if not d['name'].endswith('.xlsx'):continue
        res=extract_one(folder/d['name'],out/(d['name'].replace('.xlsx','')+'_'+sheet+'_RAW.csv'),sheet,d.get('sha256'))
        res['expected_bytes']=d['size'];log.append(res)
    (out/'weather_workbook_extraction_audit.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({'extracted':sum(x['status'].startswith('EXTRACTED') for x in log),'total':len(log)}))
    return log
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--sources',required=True);p.add_argument('--index',required=True);p.add_argument('--out',required=True);p.add_argument('--sheet',default='Weather_Hourly');a=p.parse_args();main(a.sources,a.index,a.out,a.sheet)
