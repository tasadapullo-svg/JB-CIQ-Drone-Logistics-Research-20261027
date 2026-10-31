# -*- coding: utf-8 -*-
"""Offline geometry-only preview for review, no QGIS or online basemap needed.
Requires geopandas and matplotlib. Never makes legal/safety claims.
"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import geopandas as gpd

ROOT=Path(__file__).resolve().parent.parent
p=ROOT/'data'/'CIQ_ABC_FINAL_EDITABLE.gpkg'
OUT=ROOT/'figures'; OUT.mkdir(exist_ok=True)
L=lambda name:gpd.read_file(p,layer=name)
pts=L('V7_ALL_62_RETAINED_ROLES');port=L('V8_CIQ_PORT_6_EVIDENCE_POINTS');ciq=L('G_CIQ_ground_gateway')
links=L('V7_ALL_111_GEOMETRY_ONLY');plink=L('V8_CIQ_PORT_10_GROUND_AND_UAV_GEOMETRY')
wmp=L('WMP228_history_two_discs');ac=L('AC_study_corridors_APPROX');bnd=L('B_geometric_display_envelope')

fig=plt.figure(figsize=(17,13),dpi=220)
gs=fig.add_gridspec(2,3,height_ratios=[1.0,1],hspace=.22,wspace=.14)
axes=[fig.add_subplot(gs[0,:]),fig.add_subplot(gs[1,0]),fig.add_subplot(gs[1,1]),fig.add_subplot(gs[1,2])]
windows=[(103.525,103.86,1.318,1.572),(103.735,103.854,1.439,1.560),(103.561,103.786,1.379,1.566),(103.515,103.704,1.317,1.486)]
titles=['FULL A / C / B CANDIDATE NETWORK','A: EAST & COASTAL SITE SEARCH','C: WEST–B NETWORK LINKAGE','B: FROZEN SECOND LINK NETWORK']
for idx,(ax,win,title) in enumerate(zip(axes,windows,titles)):
 ax.set_title(title,fontsize=10,weight='bold',loc='left',pad=6)
 ax.set_facecolor('#f8fafc')
 try:ac.boundary.plot(ax=ax,color='#849ca8',linewidth=1.3,linestyle=':')
 except:pass
 bnd.boundary.plot(ax=ax,color='#627ca1',linewidth=.8,linestyle=':')
 over=links[links['dji_distance_class']=='GEOMETRY_EXCEEDS_5P6_KM']
 inside=links[links['dji_distance_class']=='GEOMETRY_WITHIN_5P6_KM']
 inside.plot(ax=ax,color='#398ba5',linewidth=.7,linestyle='--',alpha=.65)
 over.plot(ax=ax,color='#bd6c36',linewidth=.9,linestyle='--',alpha=.78)
 plink[plink['mode']=='GROUND_HANDOFF_STRAIGHT_REFERENCE'].plot(ax=ax,color='#687382',linewidth=.8,linestyle=':',alpha=.9)
 plink[plink['mode']=='UAV_GEOMETRY_SEARCH'].plot(ax=ax,color='#15977e',linewidth=1.3,linestyle='--',alpha=.95)
 # Draw historical reference discs only as outlines
 for rid,row in wmp.iterrows():
  gpd.GeoSeries([row.geometry],crs=4326).boundary.plot(ax=ax,color=('#b6404c' if rid==0 else '#e4a04b'),linewidth=1.1,linestyle='--')
 p1=pts[pts['retention_class']=='RETAIN_PRIORITY_SITE_SEARCH'];
 base=pts[pts['retention_class']!='RETAIN_PRIORITY_SITE_SEARCH']
 base.plot(ax=ax,markersize=(16 if idx==0 else 23),color='#bd9863',edgecolor='white',linewidth=.6,zorder=4)
 p1.plot(ax=ax,markersize=(36 if idx==0 else 47),marker='^',color='#0c7d6f',edgecolor='white',linewidth=.8,zorder=5)
 port.plot(ax=ax,markersize=(26 if idx==0 else 45),marker='s',color='#a56e45',edgecolor='white',linewidth=.5,zorder=6)
 ciq.plot(ax=ax,markersize=(47 if idx==0 else 70),marker='D',color='#252b37',edgecolor='white',linewidth=.5,zorder=6)
 ax.set_xlim(win[0],win[1]);ax.set_ylim(win[2],win[3]);ax.set_aspect('equal',adjustable='box')
 ax.grid(color='#ccd4db',linewidth=.35,alpha=.55)
 ax.tick_params(labelsize=7)
 # only key audit identifiers; no wall of overlapping text
 chosen=['A01','A09','C21','B00','B07','T_STULANG','A_P01']
 if idx==1:chosen=['A01','A_N05','A_N07','A_P01','T_STULANG','A03','A04']
 if idx==2:chosen=['A09','C21','B07','C01','C05','C08']
 if idx==3:chosen=['B00','B07','B09','B06','B04']
 for data,idcol in ((pts,'id'),(port,'node_id'),(ciq,'id')):
  for _,r in data[data[idcol].isin(chosen)].iterrows():
   x,y=r.geometry.x,r.geometry.y
   if win[0]<x<win[1] and win[2]<y<win[3]:
    ax.annotate(r[idcol],(x,y),xytext=(4,3),textcoords='offset points',fontsize=7,fontweight='bold',color='#151d24',bbox={'facecolor':'white','edgecolor':'none','alpha':.76,'pad':.4})
fig.suptitle('CIQ A/C/B | Complete integrated spatial review | GEOMETRY ONLY — NOT APPROVED AIR ROUTES', fontsize=14,fontweight='bold',y=.991)
fig.text(.5,.02,'68 evidence points + one CIQ ground gateway | V7: 111 lines + V8: 5 UAV candidate lines + 5 ground beelines | Historical WMP228 circles (not legal geometry)',fontsize=9,ha='center')
fig.savefig(OUT/'ABC_FINAL_OVERVIEW_3_REGIONS_QA.png',bbox_inches='tight')
plt.close(fig)

fig,ax=plt.subplots(figsize=(11,7),dpi=220)
ax.set_facecolor('#f8fafc')
plink[plink['mode']=='UAV_GEOMETRY_SEARCH'].plot(ax=ax,color='#168c7b',linewidth=1.6,linestyle='--')
plink[plink['mode']=='GROUND_HANDOFF_STRAIGHT_REFERENCE'].plot(ax=ax,color='#737b84',linewidth=1.3,linestyle=':')
for rid,row in wmp.iterrows():gpd.GeoSeries([row.geometry],crs=4326).boundary.plot(ax=ax,color=('#bb4052' if rid==0 else '#e3a047'),linewidth=1.25,linestyle='--')
for layer,col,size,marker in [(pts,'#437f9c',25,'o'),(port,'#bf8055',45,'s'),(ciq,'#1f2937',70,'D')]:
 layer.plot(ax=ax,color=col,markersize=size,marker=marker,edgecolor='white',linewidth=.7)
for dat,field,selected in ((pts,'id',{'A03','A04','A07','A_C01','A_N01','T_STULANG'}),(port,'node_id',{'A_P01'}),(ciq,'id',{'G_CIQ'})):
 for _,r in dat[dat[field].isin(selected)].iterrows():
  if 103.755<r.geometry.x<103.809 and 1.455<r.geometry.y<1.51:
   ax.annotate(r[field],(r.geometry.x,r.geometry.y),xytext=((-40,12) if r[field]=='A_P01' else (9,-12) if r[field]=='T_STULANG' else (4,4)),textcoords='offset points',fontsize=8,color='#101827',bbox={'facecolor':'white','edgecolor':'none','alpha':.78,'pad':1})
ax.set_xlim(103.754,103.810);ax.set_ylim(1.454,1.51);ax.set_aspect('equal');ax.grid(alpha=.2)
ax.set_title('Causeway–Stulang ferry / near-CIQ landing-property search | NOT APPROVED',loc='left',fontweight='bold')
ax.set_xlabel('Longitude (WGS84)');ax.set_ylabel('Latitude (WGS84)')
fig.text(.5,.02,'Turquoise = UAV geometry candidates; grey dotted = ground transfer beelines (NOT roads); historical WMP228 circles = reference ONLY.',fontsize=9,ha='center')
fig.savefig(OUT/'ABC_FINAL_CIQ_PORT_CLOSEUP_QA.png',bbox_inches='tight');plt.close(fig)
print('Wrote two QA figures under', OUT)
