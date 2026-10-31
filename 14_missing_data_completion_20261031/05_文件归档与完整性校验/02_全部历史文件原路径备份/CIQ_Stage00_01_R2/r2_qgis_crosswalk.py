#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 00/01 R2: READ-ONLY QGIS spatial input and node/edge transition audit.

Not an airspace authorization; does not calculate weather, traffic, costs or CO2.
Run with Python 3.10+ (standard library only).

python r2_qgis_crosswalk.py --qgis "D:\\CIQ\\latest\\project.qgz" \
 --old-nodes "D:\\CIQ\\old_nodes.csv" --out "D:\\CIQ_AUDIT_R2"

The old nodes file is optional; without it crosswalk remains INCOMPLETE.
--qgis may be absent, in which case the script returns a HOLD report rather than inventing nodes.
"""
from __future__ import annotations
import argparse, csv, datetime, hashlib, json, os, re, sqlite3, struct, sys, xml.etree.ElementTree as ET, zipfile
from pathlib import Path
from collections import Counter, defaultdict
from math import radians, sin, cos, asin, sqrt

NODE_ID_KEYS=['site_id','node_id','station_id','point_id','hub_id','location_id','nodeid','id']
NODE_LABEL_KEYS=['site_name','node_name','station_name','name','label','display_name']
ZONE_KEYS=['area','area_id','zone','zone_id','region','region_id','subarea','study_area']
EDGE_FROM_KEYS=['source_id','origin_id','from_id','from_node','from_node_id','start_id','start_node','u']
EDGE_TO_KEYS=['target_id','destination_id','to_id','to_node','to_node_id','end_id','end_node','v']


def digest(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def write_csv(path,items,fields):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore')
        w.writeheader();w.writerows(items)

def choose(fields, options):
    low={s.casefold():s for s in fields}
    for c in options:
        if c in low:return low[c]
    return None

def qgs_bytes(p):
    if p.suffix.lower()=='.qgs':return p.read_bytes()
    if p.suffix.lower()=='.qgz':
        with zipfile.ZipFile(p) as z:
            m=[n for n in z.namelist() if n.lower().endswith('.qgs') and not n.startswith('__MACOSX/')]
            if len(m)!=1:raise ValueError(f'Expected one .qgs member, got {m}')
            return z.read(m[0])
    raise ValueError('QGIS project must be .qgs or .qgz')

def datasource(raw, project):
    s=(raw or '').strip()
    if not s:return ('EMPTY_SOURCE',None,None)
    if re.match(r'^(?:https?:|wms:|wfs:|xyz:|postgres:|memory:|virtual:|arcgis:)',s,re.I):
        return ('REMOTE_OR_VIRTUAL',None,None)
    m=re.search(r"(?:^|\s)dbname=['\"]([^'\"]+)['\"]",s)
    source=m.group(1) if m else s.split('|')[0].split('?type=')[0]
    layer=re.search(r'\|layername=([^|]+)',s,re.I)
    name=layer.group(1) if layer else None
    if '://' in source and not source.startswith('file://'):
        return ('REMOTE_OR_VIRTUAL',None,name)
    if source.startswith('file://'):
        source=source[7:]
    p=Path(source)
    if not p.is_absolute():p=project.parent / p
    p=p.resolve()
    return ('LOCAL_FOUND' if p.is_file() else 'LOCAL_MISSING',p,name)

def gpkg_point(blob):
    """Return GeoPackage Point WKB (x,y), or null for non-Point and unsafe geometry."""
    if not blob or len(blob)<13 or blob[:2]!=b'GP':return (None,None)
    flags=blob[3];endian='<' if flags&1 else '>'
    ev=(flags>>1)&7
    sz={0:0,1:32,2:48,3:48,4:64}.get(ev)
    if sz is None:return (None,None)
    off=8+sz
    if len(blob)<off+21:return (None,None)
    fmt='<' if blob[off]==1 else '>'
    kind=struct.unpack(fmt+'I',blob[off+1:off+5])[0]
    # WKB base geometry type; reject 1000/2000/3000 variants as Point is still first two ordinates
    if kind%1000!=1:return (None,None)
    x,y=struct.unpack(fmt+'dd',blob[off+5:off+21]);return x,y

def project_layers(p):
    root=ET.fromstring(qgs_bytes(p))
    authid=root.findtext('.//projectCrs/spatialrefsys/authid') or ''
    rows=[]
    for l in root.findall('.//projectlayers/maplayer'):
        st,loc,table=datasource(l.findtext('datasource',''),p)
        rows.append({'layer_id':l.findtext('id',''),'layer_name':l.findtext('layername',''),
          'provider':l.findtext('provider',''),'source_type':st,'source_path':str(loc) if loc else '',
          'gpkg_layer_requested':table or '', 'source_sha256':digest(loc) if st=='LOCAL_FOUND' and loc.suffix.lower()=='.gpkg' else ''})
    return authid,rows

def normalize_zone(s):
    s=str(s or '').strip().upper()
    if s in {'A','B','C'}:return s
    for pattern in [r'^(?:AREA|ZONE|REGION)[_\s-]*([ABC])$',r'^([ABC])[_\s-]*(?:AREA|ZONE|REGION)$']:
        m=re.match(pattern,s)
        if m:return m.group(1)
    return s

def read_gpkg(path, req_layer, project, source_layer):
    """Inspect only named selected table or all feature tables when no layer name is given."""
    nodes=[];edges=[];tableinfo=[];issues=[]
    con=sqlite3.connect('file:'+path.as_posix()+'?mode=ro',uri=True)
    try:
        geo={t:(g,typ,s) for t,g,typ,s in con.execute('SELECT table_name,column_name,geometry_type_name,srs_id FROM gpkg_geometry_columns')}
        tables=[req_layer] if req_layer else list(geo)
        for t in tables:
            if t not in geo:
                issues.append(f'GPKG_LAYER_NOT_FOUND:{path.name}:{t}');continue
            gcol,geomtype,srid=geo[t]
            q='"'+t.replace('"','""')+'"'
            info=con.execute(f'PRAGMA table_info({q})').fetchall()
            fields=[c[1] for c in info]
            idcol=choose(fields,NODE_ID_KEYS+['link_id','edge_id','route_id','connection_id','line_id'])
            labelcol=choose(fields,NODE_LABEL_KEYS)
            zonecol=choose(fields,ZONE_KEYS)
            frcol=choose(fields,EDGE_FROM_KEYS);tocol=choose(fields,EDGE_TO_KEYS)
            cnt=con.execute(f'SELECT count(*) FROM {q}').fetchone()[0]
            nullg=con.execute(f'SELECT count(*) FROM {q} WHERE "{gcol}" IS NULL').fetchone()[0]
            tableinfo.append({'source':str(path),'table':t,'layer_name':source_layer,'geometry_type':geomtype,
                'feature_count':cnt,'null_geom_count':nullg,'srs_id':srid,'id_field':idcol or '',
                'name_field':labelcol or '', 'zone_field':zonecol or '',
                'edge_from_field':frcol or '', 'edge_to_field':tocol or ''})
            if nullg:issues.append(f'NULL_GEOMETRY:{t}:{nullg}')
            # Never assume all point layers are logistics nodes: record candidate status.
            if not idcol or cnt>300000:
                if cnt>300000:issues.append(f'TABLE_TOO_LARGE_MANUAL_REVIEW:{t}:{cnt}')
                continue
            cols=[idcol]+[c for c in [labelcol,zonecol,frcol,tocol,gcol] if c and c!=idcol]
            cols=list(dict.fromkeys(cols));sqlcols=','.join('"'+c.replace('"','""')+'"' for c in cols)
            seen=set()
            for r in con.execute(f'SELECT {sqlcols} FROM {q}'):
                o=dict(zip(cols,r));raw_id=o.get(idcol)
                ident=str(raw_id).strip() if raw_id is not None else ''
                zone=normalize_zone(o.get(zonecol)) if zonecol else ''
                if not ident:
                    issues.append(f'BLANK_ID:{t}');continue
                key=(zone,ident)
                if key in seen:issues.append(f'DUPLICATE_ID_IN_TABLE:{t}:{zone}:{ident}')
                seen.add(key)
                if geomtype.upper().startswith('POINT'):
                    x,y=gpkg_point(o.get(gcol))
                    nodes.append({'project':str(project),'layer_name':source_layer,'table':t,'node_id':ident,
                        'node_name':str(o.get(labelcol) or '').strip() if labelcol else '',
                        'zone':zone,'x':x,'y':y,'srs_id':srid,
                        'geometry_status':'POINT_XY_EXTRACTED' if x is not None else 'GEOMETRY_UNREADABLE',
                        'audit_class':'CANDIDATE_NODE_NEEDS_ROLE_CONFIRMATION'})
                elif geomtype.upper().startswith(('LINESTRING','MULTILINESTRING')):
                    edges.append({'layer_name':source_layer,'table':t,'edge_id':ident,'zone':zone,
                        'from_node':str(o.get(frcol) or '') if frcol else '',
                        'to_node':str(o.get(tocol) or '') if tocol else '',
                        'srs_id':srid,'audit_class':'CANDIDATE_EDGE_NOT_AUTHORIZED_FLIGHT_ROUTE'})
    finally:con.close()
    return nodes,edges,tableinfo,issues

def read_old(path):
    if not path or not path.is_file():return [],'LEGACY_NODE_CSV_NOT_PROVIDED'
    with path.open(encoding='utf-8-sig',newline='') as f:
        data=list(csv.DictReader(f))
    if not data:return [],'LEGACY_NODE_CSV_EMPTY'
    cols=data[0].keys();ic=choose(cols,NODE_ID_KEYS);zc=choose(cols,ZONE_KEYS)
    xc=choose(cols,['longitude','lon','lng','x']);yc=choose(cols,['latitude','lat','y'])
    if not ic:return [],'LEGACY_NODE_ID_FIELD_MISSING'
    out=[]
    for r in data:
        if not r.get(ic):continue
        out.append({'node_id':r[ic].strip(),'zone':normalize_zone(r.get(zc,'')) if zc else '',
                    'x':tryfloat(r.get(xc)) if xc else None,'y':tryfloat(r.get(yc)) if yc else None,
                    'srs_id':4326 if xc and xc.lower() in ('longitude','lon','lng') else None})
    return out,'LEGACY_NODES_READ'

def tryfloat(v):
    try:return float(v)
    except (ValueError,TypeError):return None

def haversine_km(lat1,lon1,lat2,lon2):
    dlat=radians(lat2-lat1);dlon=radians(lon2-lon1)
    a=sin(dlat/2)**2+cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 12742*asin(min(1,sqrt(a)))

def crosswalk(old,new):
    newindex=defaultdict(list)
    for n in new:newindex[(n['zone'],n['node_id'])].append(n)
    rows=[]
    for o in old:
        cand=newindex.get((o['zone'],o['node_id']),[])
        if len(cand)==0:
            matches=[v for v in new if v['node_id']==o['node_id']]
            status='ID_FOUND_DIFFERENT_OR_UNKNOWN_ZONE_REVIEW' if matches else 'OLD_NODE_NOT_IN_NEW_NETWORK'
            rows.append({'old_id':o['node_id'],'old_zone':o['zone'],'new_id':'','new_zone':'',
                         'status':status,'distance_m':'','review_required':'YES'})
            continue
        if len(cand)!=1:
            rows.append({'old_id':o['node_id'],'old_zone':o['zone'],'new_id':o['node_id'],'new_zone':o['zone'],
                         'status':'AMBIGUOUS_NEW_ID','distance_m':'','review_required':'YES'})
            continue
        n=cand[0];status='ID_MATCH_COORD_NOT_CHECKED';dist=''
        if (o['srs_id']==n['srs_id']==4326 and all(v is not None for v in [o['x'],o['y'],n['x'],n['y']])):
            dm=haversine_km(o['y'],o['x'],n['y'],n['x'])*1000
            dist=round(dm,2)
            status='ID_MATCH_COORD_WITHIN_20M_REVIEW_STILL_REQUIRED' if dm<=20 else 'ID_MATCH_COORD_MOVED_REVIEW'
        rows.append({'old_id':o['node_id'],'old_zone':o['zone'],'new_id':n['node_id'],
            'new_zone':n['zone'],'status':status,'distance_m':dist,'review_required':'YES'})
    return rows

def run(qgis,old,out):
    out=out.resolve();out.mkdir(parents=True,exist_ok=True)
    if qgis and (out==qgis or (qgis.is_dir() and out.is_relative_to(qgis)) or out.is_relative_to(qgis.parent)):
        raise ValueError('Audit output must be separate from QGIS source directory')
    blockers=[];layers=[];nodes=[];edges=[];tables=[];crs='';qsha=''
    if qgis and qgis.is_file() and qgis.suffix.lower() in {'.qgs','.qgz'}:
        qsha=digest(qgis)
        try:crs,layers=project_layers(qgis)
        except Exception as ex:blockers.append('QGIS_PROJECT_PARSE_FAIL:'+str(ex))
        if not crs:blockers.append('QGIS_PROJECT_CRS_NOT_FOUND')
        if not layers:blockers.append('QGIS_PROJECT_HAS_NO_LAYERS')
        done=set()
        for l in layers:
            if l['source_type']=='LOCAL_MISSING':blockers.append('QGIS_LOCAL_SOURCE_MISSING:'+l['layer_name'])
            if l['source_type']=='REMOTE_OR_VIRTUAL':
                # The presence of web basemaps alone is not a scientific blocker.
                continue
            src=l['source_path']
            if src and src.lower().endswith('.gpkg') and Path(src).exists():
                k=(src,l['gpkg_layer_requested'])
                if k in done:continue
                done.add(k)
                try:
                    n,e,t,p=read_gpkg(Path(src),l['gpkg_layer_requested'],qgis,l['layer_name'])
                    nodes+=n;edges+=e;tables+=t;blockers+=p
                except Exception as ex:blockers.append('GPKG_INSPECTION_FAIL:'+str(ex))
    else:blockers.append('LATEST_THREE_ZONE_QGIS_PROJECT_NOT_SUPPLIED')
    oldrows,oldstate=read_old(old)
    if oldstate!='LEGACY_NODES_READ':blockers.append(oldstate)
    zones={n['zone'] for n in nodes if n['zone']}
    if not {'A','B','C'}.issubset(zones):blockers.append('THREE_ZONE_A_B_C_NOT_EVIDENCED_FROM_NODE_ATTRIBUTES')
    if not nodes:blockers.append('NEW_QGIS_NODE_TABLE_NOT_EVIDENCED')
    keys=Counter((n['zone'],n['node_id']) for n in nodes)
    dup=[k for k,v in keys.items() if v>1]
    if dup:blockers.append('DUPLICATE_ZONE_NODE_IDS_ACROSS_LAYERS:'+str(len(dup)))
    ids={n['node_id'] for n in nodes}
    badedges=[e for e in edges if not e['from_node'] or not e['to_node'] or e['from_node'] not in ids or e['to_node'] not in ids]
    if badedges:blockers.append('EDGES_WITH_MISSING_OR_UNRESOLVED_ENDPOINTS:'+str(len(badedges)))
    if not edges:blockers.append('NEW_QGIS_EDGE_TABLE_NOT_EVIDENCED')
    if not crs:blockers.append('QGIS_CRS_UNVERIFIED')
    mapping=crosswalk(oldrows,nodes)
    if not mapping:blockers.append('OLD_NEW_NODE_CROSSWALK_NOT_CREATED')
    write_csv(out/'new_qgis_layer_registry.csv',layers,['layer_id','layer_name','provider','source_type','source_path','gpkg_layer_requested','source_sha256'])
    write_csv(out/'new_qgis_node_candidates.csv',nodes,['project','layer_name','table','node_id','node_name','zone','x','y','srs_id','geometry_status','audit_class'])
    write_csv(out/'new_qgis_edge_candidates.csv',edges,['layer_name','table','edge_id','zone','from_node','to_node','srs_id','audit_class'])
    write_csv(out/'new_qgis_gpkg_table_registry.csv',tables,['source','table','layer_name','geometry_type','feature_count','null_geom_count','srs_id','id_field','name_field','zone_field','edge_from_field','edge_to_field'])
    write_csv(out/'old_new_node_crosswalk_REVIEW_REQUIRED.csv',mapping,['old_id','old_zone','new_id','new_zone','status','distance_m','review_required'])
    report={'audit_id':'CIQ_STAGE00_01_R2','generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'status':'HOLD_NOT_APPROVED','project':str(qgis) if qgis else None,'project_sha256':qsha,
      'project_crs':crs,'old_nodes_source':str(old) if old else None,
      'counts':{'qgis_layers':len(layers),'qgis_nodes_candidates':len(nodes),'qgis_edges_candidates':len(edges),
                'qgis_gpkg_tables':len(tables),'observed_zone_codes':sorted(zones),'old_nodes_read':len(oldrows),
                'crosswalk_rows':len(mapping),'edges_unresolved':len(badedges)},
      'blockers_and_flags':sorted(set(blockers)),
      'mandatory_manual_review':['verify geometry CRS and accuracy in QGIS','confirm role and license of every node/edge',
         'review A_N05 A_N07 C21 A_C03 only if present','review WMP228, WMKJ CTR, CAAM and CAAS historical effective dates',
         'validate national boundary and cross-border study task scope','approve per-file SHA256 active-input freeze',
         'approve immutable node & edge tables before numerical simulation'],
      'recalculation_allowed':False,'current_numeric_recalculation':'NOT_EXECUTED',
      'caveat':'Point/line extraction is candidate classification only; GPKG-only and no geometry/topological or regulatory approval.'}
    (out/'stage00_01_r2_gate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'STAGE00_01_R2_RESULT.md').write_text('# Stage 00/01 R2 空间接入检查\n\n'
      f'**裁定：HOLD_NOT_APPROVED**；重算：NOT_EXECUTED。\n\n'
      f'QGIS: `{qgis}`；SHA-256: `{qsha or "UNAVAILABLE"}`；CRS: `{crs or "UNVERIFIED"}`。\n\n'
      f'候选节点 {len(nodes)}；候选连线 {len(edges)}；原节点 {len(oldrows)}；已记录旧新 ID 对照 {len(mapping)}。\n\n'
      '## 自动发现的缺口 / 需审查事项\n' + ''.join('- '+s+'\n' for s in sorted(set(blockers)))+
      '\n**注意：即使自动检查没有发现问题，也必须由研究者审定节点角色、空域、国界、路径及输入清单，不得自动发放数值计算许可。**\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'out':str(out),'counts':report['counts'],'blockers':len(report['blockers_and_flags'])},ensure_ascii=False,indent=2))
    return report

def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('--qgis',type=Path,help='Latest 3-zone .qgz/.qgs project (required to release a gate)')
    ap.add_argument('--old-nodes',type=Path,help='Optional historical 19-node CSV with IDs/areas/lat-lon')
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    r=run(a.qgis.resolve() if a.qgis else None,a.old_nodes.resolve() if a.old_nodes else None,a.out)
    return 2 if not r['recalculation_allowed'] else 0

if __name__=='__main__':sys.exit(main())
