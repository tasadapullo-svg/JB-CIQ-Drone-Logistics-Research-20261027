# -*- coding: utf-8 -*-
"""Offline vector-only QA diagram; not a QGIS tile-render and not an SCI final basemap."""
from pathlib import Path
from matplotlib import pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.gridspec import GridSpec
import fiona
from shapely.geometry import shape
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'CIQ_AB_NewA_v3.gpkg'
plt.rcParams['font.family']='DejaVu Sans'
plt.rcParams['font.size']=8

def rd(layer):
 with fiona.open(P,layer=layer) as ss:
  return [(shape(f['geometry']),dict(f['properties'])) for f in ss]

def poly(ax,lname,fill,edge=None,alpha=.28,lw=.8,ls='-'):
 for g,p in rd(lname):
  ps=[g] if g.geom_type=='Polygon' else list(g.geoms)
  for pl in ps:
   if pl.is_empty or not hasattr(pl,'exterior'):continue
   x,y=pl.exterior.xy
   ax.fill(x,y,facecolor=fill,edgecolor=edge or fill,alpha=alpha,linewidth=lw,linestyle=ls,zorder=1)

def draw(ax,scope,labels=True,aircraft='DJI'):
 ax.set_facecolor('#f5f7f6')
 poly(ax,'reach_'+aircraft+'_'+('B' if scope=='B' else 'A')+'_WMP_screen',('#22b5aa' if aircraft=='DJI' else '#ad7ed5'),alpha=.30)
 for geom,p in rd('WMP228_two_historical_discs'):
  x,y=geom.exterior.xy;ax.plot(x,y,color='#b12e45',lw=1.05,ls='--',alpha=.8,zorder=5)
 if scope!='B':
  for geom,p in rd('A_user_study_windows_approx'):
   x,y=geom.exterior.xy;ax.plot(x,y,color='#ce4455',lw=1,ls='--',zorder=4)
 for g,p in rd('B_33_frozen_unique_geometry'):
  x,y=g.xy;ax.plot(x,y,color='#536080',alpha=.55,lw=.75,ls='--',zorder=2)
 for g,p in rd('A_new_11_unapproved_air_lines'):
  x,y=g.xy;ax.plot(x,y,color='#078fa6',alpha=.76,lw=.9,ls='--',zorder=2)
 for layer,c,m in [('A_new_4_site_search','#10777c','^'),('A_new_6_demand_references','#e59d40','o'),('B_10_frozen_reference_points','#31578f','o'),('A_CIQ_ground_gateway','#414141','s')]:
  for g,p in rd(layer):
   ax.scatter([g.x],[g.y],s=35 if m=='^' else 23,marker=m,facecolor=c,edgecolor='white',lw=.45,zorder=10)
   id=p.get('site_id') or p.get('id')
   if labels and id in ['A01','A02','A03','A04','A05','A06','A07','A08','A09','A10','G_CIQ','B00','B01','B02','B03','B04','B05','B06','B07','B08','B09']:
    isA=scope!='B' and (id.startswith('A') or id=='G_CIQ')
    isB=scope=='B' and id.startswith('B')
    if isA or isB or scope=='overview' and id in ['A01','A03','A09','G_CIQ','B00','B01']:
     if scope=='overview' and id not in ['A01','A03','A09','G_CIQ','B00','B01']:continue
     xyoffset={
      'A01':(-40,4),'A02':(8,11),'A03':(8,-12),'A04':(-38,-9),'A05':(9,-3),'A06':(-9,-11),'A07':(8,8),'A08':(-8,8),
      'A09':(-20,10),'A10':(7,-9),'G_CIQ':(-29,-8),'B00':(10,-8),'B01':(-25,6),'B02':(4,10),'B03':(8,-6),'B04':(-20,-5),'B05':(5,-9),'B06':(7,5),'B07':(7,7),'B08':(-20,-7),'B09':(-22,5)}.get(id,(8,7))
     ax.annotate(id,(g.x,g.y),xytext=xyoffset,textcoords='offset points',fontsize=7,color='#111111',weight='normal',zorder=12,
                 bbox=dict(facecolor='white',edgecolor='none',alpha=.89,boxstyle='round,pad=.17'))
 ax.set_aspect('equal',adjustable='box');ax.tick_params(labelsize=7)
 ax.grid(True,lw=.35,ls=':',color='#d6d9db')

fig=plt.figure(figsize=(14.2,10.1),facecolor='white')
gs=GridSpec(2,2,figure=fig,height_ratios=[1.1,1.05],hspace=.3,wspace=.17,left=.05,right=.97,top=.88,bottom=.1)
a=fig.add_subplot(gs[0,:]);b=fig.add_subplot(gs[1,0]);c=fig.add_subplot(gs[1,1])
draw(a,'overview');draw(b,'A');draw(c,'B')
a.set_xlim(103.515,103.858);a.set_ylim(1.322,1.568)
b.set_xlim(103.752,103.852);b.set_ylim(1.471,1.55)
c.set_xlim(103.525,103.681);c.set_ylim(1.336,1.471)
a.set_title('(a) New Area A and frozen Area B | WMP228 and DJI nominal screening',fontsize=12,loc='left',pad=8)
b.set_title('(b) Area A east | A01–A08 (west inset: A09–A10)',fontsize=11,loc='left',pad=8)
c.set_title('(c) Area B original references | B00–B09',fontsize=11,loc='left',pad=8)
# West comparator inset (not A11 Perling)
inset=fig.add_axes([.076,.153,.16,.137]);draw(inset,'overview',labels=False)
inset.set_xlim(103.643,103.679);inset.set_ylim(1.474,1.522);inset.set_title('West: A09 / A10',fontsize=8)
inset.set_xticks([]);inset.set_yticks([])
fig.suptitle('Johor–Singapore CIQ network | A01–A10 and B00–B09 (static geometry QA)',fontsize=16,weight='bold',y=.982)
fig.text(.05,.938,'Teal shading = illustrative DJI round-trip technical reach (70% reference range ÷ 2), clipped to study windows; not legally flyable area.',fontsize=9)
fig.text(.05,.923,'Red dashed = historic WMP228 alternative reference circles / study search windows. Dashed lines = unapproved straight connections.',fontsize=9)
fig.text(.05,.042,'Vector-only QA preview (without OpenStreetMap tiles). Perling A11 and line A09–A11 are excluded. No UAV pad or air route is approved.',fontsize=9)
fig.savefig(ROOT/'QA'/'V3_AB_3panel_VECTOR_ONLY_QA.png',dpi=175,facecolor='white')
plt.close(fig)

fig,axes=plt.subplots(2,2,figsize=(13,9),layout='constrained')
for row,area in enumerate(['A','B']):
 for col,m in enumerate(['DJI','WING']):
  ax=axes[row,col];draw(ax,area,labels=False,aircraft=m)
  if area=='A':ax.set_xlim(103.752,103.852);ax.set_ylim(1.469,1.546)
  else:ax.set_xlim(103.525,103.68);ax.set_ylim(1.336,1.469)
  ax.set_title('%s | %s hypothetical reach (clipped; no flight approval)'%(area,m))
fig.suptitle('DJI vs Wingcopter nominal technical geometry — not approved flight areas',fontsize=14)
fig.savefig(ROOT/'QA'/'V3_A_B_UAV_reach_4panel_VECTOR_ONLY_QA.png',dpi=150,facecolor='white');plt.close(fig)
print('Saved QA previews')
