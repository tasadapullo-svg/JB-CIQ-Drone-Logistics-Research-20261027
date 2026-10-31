# -*- coding: utf-8 -*-
"""QGIS Desktop 3.22.4 Python Console.
- Open/create review-ready QGIS project from V3 GPKG; no legacy A11.
- Separate small labels and different line/area styles by geometry type.
- A3 overall / Area A east with west inset / Area B and second aircraft comparison layout.
- UAV polygons = nominal distance scenarios, NOT legal airspace permissions.
Run:
 f = r'D:\\CIQ_AB_NewA_v3\\code\\02_QGIS322_BUILD_STYLES_LAYOUTS.py'
 exec(compile(open(f,'rb').read(),f,'exec'))
"""
from pathlib import Path
from qgis.core import (
 QgsProject, QgsVectorLayer, QgsRasterLayer, QgsCoordinateReferenceSystem,
 QgsCoordinateTransform, QgsRectangle, QgsPrintLayout, QgsLayoutSize,
 QgsLayoutItemMap, QgsLayoutItemLabel, QgsLayoutItemScaleBar, QgsLayoutPoint,
 QgsLayoutExporter, QgsMarkerSymbol, QgsFillSymbol, QgsLineSymbol,
 QgsSingleSymbolRenderer, QgsPalLayerSettings, QgsTextFormat,
 QgsTextBufferSettings, QgsVectorLayerSimpleLabeling, QgsUnitTypes)
from qgis.PyQt.QtGui import QColor, QFont
try:
    ROOT=Path(__file__).resolve().parent.parent
    if not (ROOT/'CIQ_AB_NewA_v3.gpkg').exists(): raise RuntimeError()
except Exception:
    ROOT=Path(globals().get('f',r'D:\CIQ_AB_NewA_v3\code\02_QGIS322_BUILD_STYLES_LAYOUTS.py')).resolve().parent.parent
GPKG=ROOT/'CIQ_AB_NewA_v3.gpkg'
if not GPKG.is_file():
    raise RuntimeError('Missing V3 data: '+str(GPKG)+'; run code/01_REBUILD_V3_GPKG.py first.')
P=QgsProject.instance(); P.clear();P.setCrs(QgsCoordinateReferenceSystem('EPSG:3857'))
tree=P.layerTreeRoot()

def add_group(name): return tree.addGroup(name)

def L(layer,title,grp,kind,color,visible=True,label_field=None,marker='circle',size='2.6',width='0.35',line_style='solid',outline_color=None,fill_color=None):
    ly=QgsVectorLayer(str(GPKG)+'|layername='+layer,title,'ogr')
    if not ly.isValid(): raise RuntimeError('Layer invalid '+layer)
    P.addMapLayer(ly,False);grp.addLayer(ly).setItemVisibilityChecked(visible)
    if kind=='point':
        sym=QgsMarkerSymbol.createSimple({'name':marker,'size':size,'color':color,
             'outline_color':'255,255,255,255','outline_width':'0.25'})
    elif kind=='line':
        sym=QgsLineSymbol.createSimple({'line_color':color,'line_width':width,'line_style':line_style})
    else:
        if fill_color is None: fill_color='255,255,255,0'
        sym=QgsFillSymbol.createSimple({'color':fill_color,'outline_color':outline_color or color,
               'outline_width':width,'outline_style':line_style,
               'style':('solid' if fill_color!='255,255,255,0' else 'no')})
    ly.setRenderer(QgsSingleSymbolRenderer(sym))
    if label_field:
        st=QgsPalLayerSettings();st.fieldName=label_field;st.isExpression=False
        st.placement=QgsPalLayerSettings.OrderedPositionsAroundPoint
        st.priority=7;st.displayAll=False
        fmt=QgsTextFormat();font=QFont('Noto Sans',7);font.setBold(False)
        fmt.setFont(font);fmt.setSize(7);fmt.setColor(QColor('#111111'))
        buff=QgsTextBufferSettings();buff.setEnabled(True);buff.setSize(0.7)
        buff.setColor(QColor('#ffffff'));fmt.setBuffer(buff)
        st.setFormat(fmt);ly.setLabeling(QgsVectorLayerSimpleLabeling(st));ly.setLabelsEnabled(True)
    return ly

POINT=add_group('01 | Area A01-A10 / B00-B09 | NO A11')
a_h=L('A_new_4_site_search','A01 A02 A03 A09 | possible parcel/transfer search — NOT pads',POINT,'point','11,119,120,255',label_field='site_id',marker='triangle',size='2.9')
a_d=L('A_new_6_demand_references','A04–A08 A10 | demand/ground transfer ONLY',POINT,'point','223,143,46,255',label_field='site_id',size='2.6')
b_p=L('B_10_frozen_reference_points','B00–B09 | frozen research reference nodes',POINT,'point','42,85,150,255',label_field='site_id',size='2.9')
ciq=L('A_CIQ_ground_gateway','G_CIQ | ground port (not UAV launch)',POINT,'point','56,56,56,255',label_field='id',marker='square',size='3.0')
master=L('A_new_10_evidence_nodes','A01–A10 | complete editable attributes (normally hidden)',POINT,'point','11,119,120,255',visible=False)
fcd=L('A_9_FCD_examples_uncalibrated','A | FCD samples (unmatched road direction; hidden)',POINT,'point','111,111,111,255',visible=False)

LINES=add_group('02 | NOT authorized flight corridors / baseline B geometries')
a_line=L('A_new_11_unapproved_air_lines','A | 11 distance-screened straight candidates, NOT authorized',LINES,'line','24,146,166,255',width='0.42',line_style='dash')
b_line=L('B_33_frozen_unique_geometry','B | 33 original unique geometric links, NOT authorized',LINES,'line','74,88,145,255',width='0.3',line_style='dash')

FLIGHT=add_group('03 | UAV NOMINAL REACH | round-trip geometry only')
A_dji=L('reach_DJI_A_WMP_screen','A | DJI nominal 5.6km radius OUTSIDE TWO WMP refs only',FLIGHT,'polygon','30,150,154,255',
     outline_color='36,158,160,160',fill_color='49,188,183,55',width='0.16')
B_dji=L('reach_DJI_B_WMP_screen','B | DJI nominal 5.6km radius WMP reference scenario',FLIGHT,'polygon','36,150,160,255',
     outline_color='55,145,169,160',fill_color='49,188,183,55',width='0.16')
A_dji_nom=L('reach_DJI_A_nominal','A | DJI UNMASKED nominal reach (off)',FLIGHT,'polygon','28,152,177,180',visible=False,
     outline_color='28,152,177,180',width='0.35',line_style='dot')
B_dji_nom=L('reach_DJI_B_nominal','B | DJI UNMASKED nominal reach (off)',FLIGHT,'polygon','28,152,177,180',visible=False,
     outline_color='28,152,177,180',width='0.35',line_style='dot')
A_wing=L('reach_WING_A_WMP_screen','A | Wingcopter nominal 32.2km radius outside reference WMP (off)',FLIGHT,'polygon','140,99,183,170',visible=False,
     outline_color='137,90,176,200',fill_color='183,137,215,35',width='0.35',line_style='dash')
B_wing=L('reach_WING_B_WMP_screen','B | Wingcopter nominal 32.2km radius in B study bounds (off)',FLIGHT,'polygon','140,99,183,170',visible=False,
     outline_color='137,90,176,200',fill_color='183,137,215,35',width='0.35',line_style='dash')
A_wing_nom=L('reach_WING_A_nominal','A | Wingcopter UNMASKED nominal (off)',FLIGHT,'polygon','140,99,183,170',visible=False,
     outline_color='137,90,176,180',width='0.3',line_style='dot')
B_wing_nom=L('reach_WING_B_nominal','B | Wingcopter UNMASKED nominal (off)',FLIGHT,'polygon','140,99,183,170',visible=False,
     outline_color='137,90,176,180',width='0.3',line_style='dot')

AIRSPACE=add_group('04 | WMP228 TWO HISTORIC geometry REFS | NOT legal prohibition polygons')
wmp=L('WMP228_two_historical_discs','WMP228 | CAAM 2025 + CAAS 2026 2 NM reference outlines',AIRSPACE,'polygon','177,35,48,255',
    outline_color='185,35,51,215',width='0.48',line_style='dash')

AREA=add_group('05 | Research bounds (approximation; west excludes A11 Perling)')
window=L('A_user_study_windows_approx','A | east screenshot box / west A09 A10 only',AREA,'polygon','206,56,56,255',
     outline_color='218,66,72,255',width='0.44',line_style='dash')
context=L('AB_display_bounds_only','A/B display extent only (off)',AREA,'polygon','133,133,133,255',visible=False)

BASE=add_group('06 | OpenStreetMap live background (online)')
xyz=QgsRasterLayer('type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png&zmin=0&zmax=18','OpenStreetMap / OpenStreetMap contributors','wms')
if xyz.isValid(): P.addMapLayer(xyz,False);BASE.addLayer(xyz)
else: print('WARNING: OSM XYZ unavailable; all GIS vectors still work.')

# Two independent presentation styles: detail labels vs simplified overview labels.
# Duplicates are data-source VIEWS, not duplicated nodes; their legend tree group is switched off.
OV=add_group('07 | Layout-only reduced-label styles (hidden on canvas)')
def clone_unlabeled(src,title,subset=None,marker=None):
    # explicitly reuse public source path to avoid provider-specific sublayer representation
    uri=src.source().split('|subset=')[0]
    obj=QgsVectorLayer(uri,title,'ogr')
    if not obj.isValid():raise RuntimeError('Invalid clone '+uri)
    if subset: obj.setSubsetString(subset)
    obj.setRenderer(src.renderer().clone());obj.setLabelsEnabled(False)
    P.addMapLayer(obj,False);OV.addLayer(obj).setItemVisibilityChecked(False)
    return obj

a_h_o=clone_unlabeled(a_h,'Overview style: A candidates (unlabeled)')
a_d_o=clone_unlabeled(a_d,'Overview style: A demand (unlabeled)')
b_p_o=clone_unlabeled(b_p,'Overview style: B points (unlabeled)')
ciq_o=clone_unlabeled(ciq,'Overview style: CIQ (unlabeled)')

P.setFileName(str(ROOT/'CIQ_AB_NewA_v3.qgz'))
CRS=QgsCoordinateReferenceSystem('EPSG:3857')
T=QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'),CRS,P)
def rect(left,bottom,right,top): return T.transformBoundingBox(QgsRectangle(left,bottom,right,top))

def title_label(layout,text,x,y,w,h,pt=8,bold=False):
    o=QgsLayoutItemLabel(layout);o.setText(text)
    font=QFont('Noto Sans',pt);font.setBold(bold);o.setFont(font);o.setFontColor(QColor('#151515'))
    layout.addLayoutItem(o);o.attemptMove(QgsLayoutPoint(x,y));o.attemptResize(QgsLayoutSize(w,h));return o

def create_layout(name,heading,subheading):
    for old in list(P.layoutManager().printLayouts()):
        if old.name()==name:P.layoutManager().removeLayout(old)
    l=QgsPrintLayout(P);l.initializeDefaults();l.setName(name)
    l.pageCollection().pages()[0].setPageSize(QgsLayoutSize(420,297))
    title_label(l,heading,12,3,390,11,14,True)
    title_label(l,subheading,12,16,395,8,8,False)
    return l

def draw_map(l,x,y,w,h,extent,layers,scale_units_per_segment=2000):
    m=QgsLayoutItemMap(l);l.addLayoutItem(m);m.attemptMove(QgsLayoutPoint(x,y));m.attemptResize(QgsLayoutSize(w,h))
    m.setCrs(CRS);m.setLayers(layers);m.setKeepLayerSet(True);m.zoomToExtent(rect(*extent))
    m.setFrameEnabled(True);m.setFrameStrokeColor(QColor('#555555'))
    return m

def add_scale(l,m,x,y,seg=2000):
    b=QgsLayoutItemScaleBar(l);b.setStyle('Single Box');b.setLinkedMap(m)
    b.setNumberOfSegments(2);b.setNumberOfSegmentsLeft(0)
    b.setUnits(QgsUnitTypes.DistanceMeters);b.setUnitsPerSegment(seg);b.setUnitLabel('m')
    b.setFont(QFont('Noto Sans',7));b.setFontColor(QColor('#111111'))
    b.setFillColor(QColor('black'));b.setFillColor2(QColor('white'))
    l.addLayoutItem(b);b.attemptMove(QgsLayoutPoint(x,y))

osm=[xyz] if xyz.isValid() else []
# Layers supplied top->bottom. Fill polygons behind lines and markers.
over_layers=[a_h_o,a_d_o,b_p_o,ciq_o,a_line,b_line,wmp,window,A_dji,B_dji]+osm
A_layers=[a_h,a_d,ciq,a_line,wmp,window,A_dji]+osm
B_layers=[b_p,b_line,B_dji]+osm
west_layers=[a_h,a_d,window,A_dji]+osm

main=create_layout('SCI_V3_AB_Main_3Panel_A3',
'Johor–Singapore CIQ | NEW Area A (A01–A10) and frozen Area B',
'GIS planning REVIEW only | No approved UAV launch sites, routes, or FCD-calibrated travel times')
title_label(main,'(a) Area A/B overview: node types, historical WMP228, nominal DJI reach',12,26,390,8,10,True)
mm=draw_map(main,12,34,396,91,(103.515,1.323,103.858,1.562),over_layers)
add_scale(main,mm,353,41,5000);title_label(main,'N ↑',395,48,13,7,9,True)
title_label(main,'(b) Area A | east study box (west A09–A10 shown as an inset)',12,134,200,8,10,True)
title_label(main,'(c) Area B | Second Link original research network',215,134,193,8,10,True)
am=draw_map(main,12,143,192,115,(103.753,1.468,103.848,1.545),A_layers)
bm=draw_map(main,215,143,193,115,(103.530,1.338,103.680,1.468),B_layers)
add_scale(main,am,143,148,2000);add_scale(main,bm,347,148,2000)
title_label(main,'N ↑',192,154,10,7,8,True);title_label(main,'N ↑',396,154,10,7,8,True)
# Short separate inset. Right/west boundary east <=103.675, excludes Perling A11 at 103.68381.
inset=draw_map(main,15,206,62,47,(103.643,1.474,103.679,1.52),west_layers)
title_label(main,'West: A09–A10',16,207,55,6,8,True)
title_label(main,'Legend: △ site search  ● commercial/residential demand  ■ G_CIQ ground gate  ● B reference nodes',12,263,395,8,8,False)
title_label(main,'Teal shaded = DJI nominal 5.6 km return-radius OUTSIDE two historical WMP228 circles (screening only)',12,272,395,8,8)
title_label(main,'Red dashed = WMP228 historical alternatives (not two independent prohibited zones); dashed blue/teal = UNAPPROVED straight links',12,281,395,8,7)
P.layoutManager().addLayout(main)

comparison=create_layout('SCI_V3_UAV_NominalReach_4Panel_A3',
'Nominal return-distance geometry by aircraft | A/B comparison',
'Not an operational flight area: no verified pads, obstacle survey, route permission or weather validation')
def cpanel(text,x,y,w,h,extent,layers,seg=2000):
    title_label(comparison,text,x,y-7,w,7,9,True)
    m=draw_map(comparison,x,y,w,h,extent,layers)
    add_scale(comparison,m,x+w-64,y+4,seg)
    return m
Aa=[a_h,a_d,ciq,a_line,wmp,window,A_dji]+osm
Aw=[a_h,a_d,ciq,a_line,wmp,window,A_wing]+osm
Bb=[b_p,b_line,B_dji]+osm
Bw=[b_p,b_line,B_wing]+osm
cpanel('(a) Area A | DJI FlyCart 30 (5.6 km illustrative)',12,40,191,105,(103.753,1.466,103.848,1.545),Aa)
cpanel('(b) Area A | Wingcopter 198 (32.2 km illustrative)',216,40,191,105,(103.753,1.466,103.848,1.545),Aw)
cpanel('(c) Area B | DJI FlyCart 30 (5.6 km illustrative)',12,169,191,105,(103.530,1.338,103.68,1.466),Bb)
cpanel('(d) Area B | Wingcopter 198 (32.2 km illustrative)',216,169,191,105,(103.530,1.338,103.68,1.466),Bw)
title_label(comparison,'Radius = published maximum range × 0.70 / 2; polygon clipped to research window, with historical WMP228-reference union removed in A.',12,278,395,7,7)
title_label(comparison,'Wingcopter 92 km and DJI 16 km correspond to different maximum-range test conditions; geometry is NOT a validated mission range.',12,286,395,7,7)
P.layoutManager().addLayout(comparison)

iface.mapCanvas().setExtent(rect(103.512,1.320,103.862,1.565));iface.mapCanvas().refresh()
if not P.write():raise RuntimeError('Could not save project '+str(P.fileName()))
print('SAVED:',P.fileName())
for l,name in [(main,'SCI_V3_AB_Main_3Panel_A3.png'),(comparison,'SCI_V3_UAV_NominalReach_4Panel_A3.png')]:
    settings=QgsLayoutExporter.ImageExportSettings();settings.dpi=300
    path=ROOT/'QA'/name
    result=QgsLayoutExporter(l).exportToImage(str(path),settings)
    print('LAYOUT EXPORT:',name,'result=',result)
print('PASS: A11 and A09--A11 excluded in editable V3 data; technical reach not legal flight rights.')
