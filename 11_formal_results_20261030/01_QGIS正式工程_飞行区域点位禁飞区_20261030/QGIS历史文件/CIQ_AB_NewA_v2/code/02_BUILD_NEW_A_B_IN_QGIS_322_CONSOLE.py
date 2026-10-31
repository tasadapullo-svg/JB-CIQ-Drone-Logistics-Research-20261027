# -*- coding: utf-8 -*-
"""QGIS Desktop 3.22.4, Python Console, stand-alone map & editable A3 layout builder.
This script replaces (does not merge) the open project with NEW A + original B.
No legacy A anchors or legs are loaded. Run after extracting the entire ZIP:
  f = r'D:\\CIQ_AB_NewA_v2\\code\\02_BUILD_NEW_A_B_IN_QGIS_322_CONSOLE.py'
  exec(compile(open(f, 'rb').read(), f, 'exec'))
No regulatory approval or physical landing-pad verification is implied by line layers.
"""
from pathlib import Path
from qgis.core import (
 QgsProject,QgsVectorLayer,QgsRasterLayer,QgsCoordinateReferenceSystem,QgsCoordinateTransform,
 QgsRectangle,QgsPrintLayout,QgsLayoutItemMap,QgsLayoutItemLabel,QgsLayoutItemScaleBar,
 QgsLayoutExporter,QgsLayoutPoint,QgsLayoutSize,QgsMarkerSymbol,QgsFillSymbol,QgsLineSymbol,
 QgsSingleSymbolRenderer,QgsPalLayerSettings,QgsTextFormat,QgsTextBufferSettings,
 QgsVectorLayerSimpleLabeling,QgsUnitTypes)
from qgis.PyQt.QtGui import QColor,QFont

# Resolve ROOT from the on-disk script filename, not from the current QGIS project.
# Python console exec(compile(..., f, 'exec')) does not always set __file__.
try:
    ROOT = Path(__file__).resolve().parent.parent
    if not (ROOT / 'CIQ_AB_NewA_v2.gpkg').exists(): raise ValueError('Wrong __file__')
except Exception:
    # Update this single directory only if running by pasting the script text (instead of exec).
    ROOT = Path(globals().get('f', r'D:\CIQ_AB_NewA_v2\code\02_BUILD_NEW_A_B_IN_QGIS_322_CONSOLE.py')).resolve().parent.parent
GPKG = ROOT / 'CIQ_AB_NewA_v2.gpkg'
OUTPUT = ROOT / 'CIQ_AB_NewA_v2.qgz'
if not GPKG.is_file():
    raise RuntimeError('Cannot locate GeoPackage: '+str(GPKG)+'\nUse exec(compile(open(f,"rb").read(), f, "exec")) with f pointing at this .py file.')

p=QgsProject.instance()
p.clear()
p.setCrs(QgsCoordinateReferenceSystem('EPSG:3857'))
root=p.layerTreeRoot()

def group(name): return root.addGroup(name)

def add_vector(layerid,label,groupobj,rgb,kind='point',marker='circle',visible=True,label_field=None,style='solid'):
    lyr=QgsVectorLayer(str(GPKG)+'|layername='+layerid,label,'ogr')
    if not lyr.isValid(): raise RuntimeError('Invalid GPKG layer '+layerid)
    p.addMapLayer(lyr,False)
    tn=groupobj.addLayer(lyr)
    tn.setItemVisibilityChecked(visible)
    if kind=='point':
        sym=QgsMarkerSymbol.createSimple({'name':marker,'color':rgb,'outline_color':'255,255,255,255','outline_width':'0.35','size':'3.0'})
    elif kind=='line':
        sym=QgsLineSymbol.createSimple({'line_color':rgb,'line_style':style,'line_width':'0.45'})
    else:
        sym=QgsFillSymbol.createSimple({'color':'255,255,255,0','outline_color':rgb,'outline_width':'0.48','outline_style':'dash','style':'no'})
    lyr.setRenderer(QgsSingleSymbolRenderer(sym))
    if kind=='point' and label_field:
        settings=QgsPalLayerSettings()
        settings.fieldName=label_field
        settings.isExpression=False
        fmt=QgsTextFormat()
        fmt.setFont(QFont('Arial',8))
        fmt.setSize(8)
        fmt.setColor(QColor('0,0,0'))
        buffer=QgsTextBufferSettings();buffer.setEnabled(True);buffer.setSize(0.8);buffer.setColor(QColor('255,255,255'))
        fmt.setBuffer(buffer)
        settings.setFormat(fmt)
        lyr.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        lyr.setLabelsEnabled(True)
    return lyr

G1=group('01 | NEW A01-A11 and B00-B09 | site SEARCH and demand')
A_S=add_vector('A_new_4_site_search','NEW A | A01 A02 A03 A09 site SEARCH - not approved',G1,'15,111,114,255',marker='triangle',label_field='site_id')
A_D=add_vector('A_new_7_demand_references','NEW A | A04-A08 A10-A11 demand - not landing pads',G1,'224,138,32,255',label_field='site_id')
B_S=add_vector('B_10_frozen_reference_points','B | B00-B09 original frozen references',G1,'32,78,139,255',label_field='site_id')
CIQ=add_vector('A_CIQ_ground_gateway','Causeway CIQ | G_CIQ ground context only',G1,'73,73,73,255',marker='square',label_field='id')
add_vector('A_new_11_evidence_nodes','NEW A | full editable node attributes (off)',G1,'10,110,115,255',visible=False,label_field='site_id')
add_vector('A_9_FCD_examples_uncalibrated','A | 9 FCD road sample positions (off)',G1,'105,105,105,255',visible=False,label_field='id')
G2=group('02 | Geometry lines only - no certified flights/road times')
AIR=add_vector('A_new_12_unapproved_air_lines','NEW A | 12 UAV straight candidates (not approved)',G2,'15,135,155,255',kind='line',style='dash')
B_L=add_vector('B_33_frozen_unique_geometry','B | 33 frozen undirected reference geometries',G2,'78,88,126,255',kind='line',style='dash')

# Graph route geometry is optional and does NOT yet imply directional/traffic calibration.
ROAD=None
road_path=ROOT/'route_outputs'/'OSM_road_routes_A_B_BASELINE_ONLY.geojson'
if road_path.is_file():
    test=QgsVectorLayer(str(road_path),'Ground OSM candidate roads | NOT FCD calibrated','ogr')
    if test.isValid() and test.featureCount()>0:
        p.addMapLayer(test,False)
        G2.addLayer(test)
        test.setRenderer(QgsSingleSymbolRenderer(QgsLineSymbol.createSimple({'line_color':'32,103,181,255','line_width':'0.65','line_style':'solid'})))
        ROAD=test

G3=group('03 | WMP228 historical references - NOT verified legal polygons')
REG=add_vector('WMP228_two_historical_discs','WMP228 CAAM/CAAS | conflicting full 2-NM reference discs',G3,'181,39,53,255',kind='polygon')
# Keep secondary regulatory references available to inspect, but off by default.
regpath=ROOT/'regulatory_source'/'regulatory_screening_circles_WGS84.geojson'
if regpath.is_file():
    for nm,sub in [('WMKJ Senai area reference | preliminary','MY_ATZ'),('Singapore airport 5-km screen | preliminary','SG_5KM')]:
        obj=QgsVectorLayer(str(regpath)+'|subset="group" = \'%s\''%sub,nm,'ogr')
        if obj.isValid():
            p.addMapLayer(obj,False)
            G3.addLayer(obj).setItemVisibilityChecked(False)
            obj.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({'style':'no','outline_color':'134,105,74,255','outline_width':'0.3','outline_style':'dash'})))

G4=group('04 | Search windows: approximate, not verified boundaries')
WINDOW=add_vector('A_user_study_windows_approx','NEW A | east screenshot box + west comparison (approx)',G4,'203,39,60,255',kind='polygon')
add_vector('AB_display_bounds_only','A/B display boundaries (off)',G4,'83,83,83,255',kind='polygon',visible=False)

G5=group('05 | OSM basemap (requires internet)')
url='type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png&zmin=0&zmax=18'
base=QgsRasterLayer(url,'OpenStreetMap','wms')
if base.isValid():
    p.addMapLayer(base,False)
    G5.addLayer(base)
else:
    print('WARN: XYZ basemap unavailable. Vectors and layout remain available.')

layname='SCI_New_A_and_B_3panel_A3_review'
for item in list(p.layoutManager().printLayouts()):
    if item.name()==layname:p.layoutManager().removeLayout(item)
layout=QgsPrintLayout(p);layout.initializeDefaults();layout.setName(layname)
layout.pageCollection().pages()[0].setPageSize(QgsLayoutSize(420,297))

def label(text,x,y,w,h,pt=8,bold=False):
    item=QgsLayoutItemLabel(layout);item.setText(text)
    ff=QFont('Arial',pt);ff.setBold(bold);item.setFont(ff);item.setFontColor(QColor('0,0,0'))
    layout.addLayoutItem(item);item.attemptMove(QgsLayoutPoint(x,y));item.attemptResize(QgsLayoutSize(w,h))
    return item

label('Johor–Singapore CIQ corridors | NEW Area A and unchanged Area B',11,3,390,10,15,True)
label('SITE SEARCH / STRAIGHT-LINE SCREENING ONLY — no approved landing sites, flight routes or FCD-calibrated ground paths',11,14,394,7,8)
lay_order=[A_S,A_D,B_S,CIQ,AIR,B_L,REG,WINDOW]
if ROAD is not None:lay_order.insert(6,ROAD)
if base.isValid():lay_order.append(base)
CRS=QgsCoordinateReferenceSystem('EPSG:3857')
transform=QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'),CRS,p)

def bbox(b): return transform.transformBoundingBox(QgsRectangle(*b))
frames=[
 ('(a) Causeway and Second Link — overview',11,31,398,107,(103.515,1.326,103.86,1.570)),
 ('(b) NEW Area A | east site search and west comparison',11,158,193,113,(103.646,1.43,103.852,1.553)),
 ('(c) Area B | unchanged Second Link reference network',216,158,193,113,(103.520,1.333,103.674,1.472))]
for title,x,y,w,h,extent in frames:
    label(title,x,y-8,w,8,10,True)
    m=QgsLayoutItemMap(layout);layout.addLayoutItem(m)
    m.attemptMove(QgsLayoutPoint(x,y));m.attemptResize(QgsLayoutSize(w,h))
    m.setCrs(CRS);m.setLayers(lay_order);m.setKeepLayerSet(True)
    m.zoomToExtent(bbox(extent));m.setFrameEnabled(True);m.setFrameStrokeColor(QColor('70,70,70'))
    bar=QgsLayoutItemScaleBar(layout);bar.setStyle('Single Box');bar.setLinkedMap(m)
    bar.setNumberOfSegments(2);bar.setNumberOfSegmentsLeft(0)
    bar.setUnits(QgsUnitTypes.DistanceMeters);bar.setUnitsPerSegment(5000 if w>300 else 2000)
    bar.setUnitLabel('m');bar.setFont(QFont('Arial',7));bar.setFontColor(QColor('0,0,0'))
    bar.setFillColor(QColor('0,0,0'));bar.setFillColor2(QColor('255,255,255'))
    layout.addLayoutItem(bar);bar.attemptMove(QgsLayoutPoint(x+w-46,y+4))
    label('N ↑',x+w-13,y+15,12,7,9,True)
label('Legend: teal ▲ site SEARCH | ochre ● demand | blue ● B references | blue/teal dashed = unapproved geometric links.',11,275,398,6,8)
label('WMP228: two historical full-circle alternatives; coastal legal boundary / NOTAM pending. East/west rectangles are approximate.',11,282,398,6,8)
p.layoutManager().addLayout(layout)
# Open view to both corridors and record clean project.
iface.mapCanvas().setExtent(bbox((103.51,1.32,103.855,1.57)))
iface.mapCanvas().refresh()
p.setFileName(str(OUTPUT))
if not p.write():raise RuntimeError('Failed writing '+str(OUTPUT))
print('Saved NEW A + B project:',OUTPUT)
print('Available layout:',layname)
# Export review PNG; set this to 600 if a 600 dpi image is desired.
EXPORT_DPI=300
img=ROOT/'QA'/'NEW_A_B_3panel_QGIS_LOCAL_300dpi.png'
settings=QgsLayoutExporter.ImageExportSettings();settings.dpi=EXPORT_DPI
status=QgsLayoutExporter(layout).exportToImage(str(img),settings)
print('Layout PNG code/status:',status,'path:',img)
print('IMPORTANT: technical map only. 0 approved pads; 0 approved air routes; no calibrated travel time.')
