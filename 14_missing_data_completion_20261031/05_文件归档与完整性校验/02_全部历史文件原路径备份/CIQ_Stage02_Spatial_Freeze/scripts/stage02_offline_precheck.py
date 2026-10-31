#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only CIQ Stage02 offline project file/source preflight. Python 3.10+.
Does NOT certify routes or trigger numerical experiments.

Examples:
 python stage02_offline_precheck.py --search-dir D:\\CIQ\\latest --out D:\\CIQ_Audit\\Stage02
 python stage02_offline_precheck.py --project D:\\CIQ\\latest\\study.qgz --out D:\\CIQ_Audit\\Stage02
"""
from __future__ import annotations
import argparse, csv, datetime as dt, hashlib, json, re, sys, xml.etree.ElementTree as ET, zipfile
from pathlib import Path
from urllib.parse import unquote

VECTOR_SUFFIXES={'.gpkg','.geojson','.json','.shp','.sqlite','.kml','.gml','.csv'}
SHAPE_COMPONENTS={'.shp','.shx','.dbf','.prj','.cpg'}

def sha256_file(path: Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''):h.update(b)
    return h.hexdigest()

def qgs_xml(project: Path)->bytes:
    if project.suffix.lower()=='.qgs': return project.read_bytes()
    if project.suffix.lower()=='.qgz':
        with zipfile.ZipFile(project) as z:
            matches=[n for n in z.namelist() if n.lower().endswith('.qgs') and not n.startswith('__MACOSX/')]
            if len(matches)!=1: raise ValueError(f'Expected exactly one embedded QGS, found {len(matches)}')
            return z.read(matches[0])
    raise ValueError('Unsupported project extension')

def source_uri(raw: str, base: Path):
    raw=(raw or '').strip()
    if not raw: return 'EMPTY', '', ''
    if re.match(r'^(?:https?:|wms:|wfs:|xyz:|postgres:|memory:|virtual:|arcgis:|delimitedtext:)',raw,re.I):
        return 'REMOTE_OR_VIRTUAL','',raw[:120]
    m=re.search(r'\bdbname=[\'\"]([^\'\"]+)[\'\"]',raw)
    candidate=m.group(1) if m else raw.split('|',1)[0].split('?type=',1)[0]
    if '://' in candidate and not candidate.lower().startswith('file://'):
        return 'REMOTE_OR_VIRTUAL','',candidate[:120]
    if candidate.startswith('file://'):candidate=unquote(candidate[7:])
    if re.match(r'^/[A-Za-z]:/',candidate):candidate=candidate[1:]
    p=Path(candidate)
    if not p.is_absolute():p=base/p
    try:p=p.resolve()
    except OSError:pass
    return ('LOCAL_FOUND' if p.is_file() else 'LOCAL_MISSING'),str(p),''

def sources(project):
    root=ET.fromstring(qgs_xml(project))
    crs=root.findtext('.//projectCrs/spatialrefsys/authid','')
    layers=[]
    for layer in root.findall('.//projectlayers/maplayer'):
        raw=layer.findtext('datasource','') or ''
        typ,filepath,note=source_uri(raw,project.parent)
        layers.append({'layer_id':layer.findtext('id',''),'name':layer.findtext('layername',''),
            'provider':layer.findtext('provider',''),'type':layer.get('type',''),
            'source_status':typ,'local_path':filepath,'source_note':note,
            'source_sha256':sha256_file(Path(filepath)) if typ=='LOCAL_FOUND' else '',
            'raw_data_source':raw})
    return crs,layers

def write_csv(path,rows,cols):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(rows)

def find_projects(root):
    if not root or not root.exists():return []
    return sorted([p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in ('.qgz','.qgs')],key=lambda p:str(p))

def run(project:Path|None, search_dir:Path|None, out:Path):
    out=out.resolve();out.mkdir(parents=True,exist_ok=True)
    blockers=[];notes=[];crs='';layer_rows=[]
    candidates=find_projects(search_dir)
    write_csv(out/'qgis_project_candidates.csv', [{'path':str(p),'bytes':p.stat().st_size,'sha256':sha256_file(p)} for p in candidates],['path','bytes','sha256'])
    if not project:
        blockers.append('PROJECT_NOT_EXPLICITLY_SELECTED')
        if candidates:notes.append('Candidate QGIS projects found; select one explicitly. No auto-selection by mtime.')
    elif not project.is_file():blockers.append('PROJECT_FILE_NOT_FOUND')
    elif project.suffix.lower() not in ('.qgs','.qgz'):blockers.append('INVALID_QGIS_PROJECT_TYPE')
    else:
        try:crs,layer_rows=sources(project)
        except Exception as e:blockers.append('QGIS_XML_OR_ARCHIVE_PARSE_ERROR:'+str(e))
        if not crs:blockers.append('QGIS_PROJECT_CRS_NOT_READ')
        if not layer_rows:blockers.append('QGIS_PROJECT_LAYERS_NOT_READ')
        if any(r['source_status']=='LOCAL_MISSING' for r in layer_rows):blockers.append('MISSING_LOCAL_LAYER_SOURCES')
        if any(r['source_status']=='EMPTY' for r in layer_rows):blockers.append('EMPTY_SOURCE_URI')
        if any(r['source_status']=='REMOTE_OR_VIRTUAL' for r in layer_rows):notes.append('Review remote/memory/virtual layers; online basemaps may be acceptable only as background.')
        shape_paths={Path(r['local_path']) for r in layer_rows if r['source_status']=='LOCAL_FOUND' and Path(r['local_path']).suffix.lower()=='.shp'}
        for shp in shape_paths:
            missing=[str(shp.with_suffix(ext)) for ext in ('.shx','.dbf','.prj') if not shp.with_suffix(ext).exists()]
            if missing:blockers.append('SHAPEFILE_SIDECARS_MISSING:'+shp.name)
            for ext in SHAPE_COMPONENTS:
                comp=shp.with_suffix(ext)
                if comp.is_file() and not any(r['local_path']==str(comp) for r in layer_rows):
                    layer_rows.append({'layer_id':'SIDECAR','name':shp.stem+ext,'provider':'shapefile_component','type':'auxiliary','source_status':'LOCAL_FOUND',
                        'local_path':str(comp),'source_note':'Referenced Shapefile component','source_sha256':sha256_file(comp),'raw_data_source':''})
    cols=['layer_id','name','provider','type','source_status','local_path','source_note','source_sha256','raw_data_source']
    write_csv(out/'layer_source_integrity.csv',layer_rows,cols)
    data={'audit':'STAGE02_OFFLINE_PREFLIGHT','timestamp_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'qgis_project':str(project) if project else None,'qgis_project_sha256':sha256_file(project) if project and project.is_file() else None,
        'project_crs':crs,'qgis_project_candidate_count':len(candidates),'declared_layer_count':len([r for r in layer_rows if r['layer_id']!='SIDECAR']),
        'source_rows_including_shapefile_components':len(layer_rows),
        'local_sources_missing':sum(r['source_status']=='LOCAL_MISSING' for r in layer_rows),
        'blockers':blockers,'notes':notes,'result':'HOLD',
        'scientific_release_allowed':False,'weather_road_carbon_recalculation_allowed':False,
        'reason':'File-level source checks alone never constitute 3-zone geometry, legal airspace, or stage reproducibility approval.'}
    (out/'stage02_offline_gate.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:data[k] for k in ('qgis_project','qgis_project_candidate_count','declared_layer_count','local_sources_missing','result','blockers')},ensure_ascii=False,indent=2))
    return data

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--project',type=Path)
    p.add_argument('--search-dir',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.project and a.out.resolve()==a.project.resolve().parent:
        p.error('Output must not be the QGIS source directory')
    d=run(a.project,a.search_dir,a.out)
    return 2 if d['result']=='HOLD' else 0
if __name__=='__main__':sys.exit(main())
