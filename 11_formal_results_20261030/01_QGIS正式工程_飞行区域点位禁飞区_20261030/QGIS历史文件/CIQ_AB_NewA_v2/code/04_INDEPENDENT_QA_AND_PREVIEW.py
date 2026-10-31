# -*- coding: utf-8 -*-
"""Offline QA and vector-only preview (not a replacement for QGIS OSM basemap rendering)."""
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as ET
import json, math, hashlib
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent.parent
pkg=ROOT/'CIQ_AB_NewA_v2.gpkg'
rd=lambda name:gpd.read_file(pkg,layer=name)
A=rd('A_new_11_evidence_nodes');S=rd('A_new_4_site_search');D=rd('A_new_7_demand_references')
B=rd('B_10_frozen_reference_points');L=rd('A_new_12_unapproved_air_lines')
BL=rd('B_33_frozen_unique_geometry');C=rd('WMP228_two_historical_discs')
W=rd('A_user_study_windows_approx');G=rd('A_CIQ_ground_gateway')
assert sorted(A.site_id)==[f'A{i:02}' for i in range(1,12)]
assert sorted(B.site_id)==[f'B{i:02}' for i in range(10)]
assert len(A)==11 and len(S)==4 and len(D)==7 and len(L)==12 and len(B)==10 and len(BL)==33
assert set(L.src).union(set(L.dst)).issubset(set(A.site_id))
assert len(set(A.site_id)&set(B.site_id))==0
assert A.is_valid.all() and B.is_valid.all() and L.is_valid.all() and BL.is_valid.all()
assert all(x=='NOT_VERIFIED' for x in A.site_permission)
# Historical A's reference IDs A00..A08 are reused for NEW nodes except A00, so assess by feature names/sources and not ID alone.
legacy_names={'Johor Bahru City Square','KOMTAR JBCC','KSL City','Pelangi Plaza','Larkin Sentral','R&F Princess Cove residential','Kampung Nong Chik','JB Sentral'}
assert not any(name in legacy_names for name in A.name)
with ZipFile(ROOT/'CIQ_AB_NewA_v2.qgz') as z:
 root=ET.fromstring(z.read('CIQ_AB_NewA_v2.qgs'))
 rsrc=[p.findtext('datasource','') for p in root.xpath('./projectlayers/maplayer')]
 assert not any('Fig1_19_reference_points' in x or 'Fig1_55_unique' in x for x in rsrc)
 assert len(root.xpath('./projectlayers/maplayer'))==17
for i,r in L.iterrows():
 s=A[A.site_id==r.src].iloc[0].geometry;d=A[A.site_id==r.dst].iloc[0].geometry
 ln=r.geometry
 assert s.distance(ln.coords[0] and __import__('shapely').geometry.Point(ln.coords[0]))<2e-6
 assert d.distance(ln.coords[-1] and __import__('shapely').geometry.Point(ln.coords[-1]))<2e-6
# Build three-panel vector QA; no online tiles, no approved routes implied.
fig=plt.figure(figsize=(16,11),dpi=150)
axs=[fig.add_axes([.09,.55,.83,.37]),fig.add_axes([.06,.12,.44,.33]),fig.add_axes([.55,.12,.38,.33])]
for idx,ax in enumerate(axs):
 area=('AB','A','B')[idx]
 if area in ('AB','A'):
  for geom in C.geometry:
   x,y=geom.exterior.xy;ax.plot(x,y,color='#af263c',linewidth=1.0,linestyle='--')
  for geom in W.geometry:
   x,y=geom.exterior.xy;ax.plot(x,y,color='#c0392b',linewidth=1.1)
  for ln in L.geometry:
   x,y=ln.xy;ax.plot(x,y,color='#1497a5',linewidth=.85,linestyle='--',alpha=.60)
  ax.scatter(S.geometry.x,S.geometry.y,c='#007a79',marker='^',s=42,zorder=4,label='New A sites (search only)')
  ax.scatter(D.geometry.x,D.geometry.y,c='#d69329',marker='o',s=21,zorder=3,label='New A demand anchors')
  ax.scatter(G.geometry.x,G.geometry.y,c='#333333',marker='s',s=30,zorder=4)
  for x in A.itertuples():
   ax.annotate(x.site_id,(x.geometry.x,x.geometry.y),xytext=(2,3),textcoords='offset points',fontsize=6)
  ax.annotate('G_CIQ',(G.geometry.iloc[0].x,G.geometry.iloc[0].y),xytext=(3,4),textcoords='offset points',fontsize=6)
 if area in ('AB','B'):
  for ln in BL.geometry:
   x,y=ln.xy;ax.plot(x,y,color='#355e8b',linewidth=.5,alpha=.24)
  ax.scatter(B.geometry.x,B.geometry.y,c='#234a84',s=17)
  for x in B.itertuples():ax.annotate(x.site_id,(x.geometry.x,x.geometry.y),xytext=(2,3),textcoords='offset points',fontsize=6)
 bb={'AB':(103.51,103.855,1.33,1.57),'A':(103.646,103.85,1.43,1.56),'B':(103.52,103.67,1.33,1.47)}[area]
 ax.set_xlim(bb[0],bb[1]);ax.set_ylim(bb[2],bb[3]);ax.grid(alpha=.15)
 ax.set_xlabel('Longitude WGS84');ax.set_ylabel('Latitude WGS84')
 ax.set_title({'AB':'(a) Johor-Singapore: NEW A + frozen B','A':'(b) New A01–A11 and WMP228 references','B':'(c) B00–B09 unchanged'}[area],fontsize=10)
 ax.set_aspect('equal')
fig.suptitle('INDEPENDENT GEOMETRY QA — NO basemap / NO approved flights or UAV pads',fontsize=13)
p=ROOT/'QA'/'NEW_A_B_3panel_VECTOR_ONLY_PREVIEW.png';fig.savefig(p,dpi=180);plt.close(fig)
print('QA PASS, preview:',p)
