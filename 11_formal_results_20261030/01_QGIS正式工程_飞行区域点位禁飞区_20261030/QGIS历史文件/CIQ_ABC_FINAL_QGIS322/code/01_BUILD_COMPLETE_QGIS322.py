# -*- coding: utf-8 -*-
r"""
CIQ A/C/B complete and reproducible GIS review project for QGIS Desktop 3.22.4.
Run INSIDE the QGIS Python Console (NOT Android's QPython):
    p = r'D:\CIQ_ABC_FINAL_QGIS322\code\01_BUILD_COMPLETE_QGIS322.py'
    exec(compile(open(p, encoding='utf-8').read(), p, 'exec'), {'__file__': p})

IMPORTANT: Clears the currently open QGIS project. Save other work first.
Output: CIQ_ABC_FINAL_REVIEW.qgz + 6 A3/A4 layouts & PNG files (when rendered).
All UAV lines are geometric candidates only. NOT approved or terrain-safe routes.
All nodes are references or property searches, not verified/approved landing pads.
"""
from pathlib import Path
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer, QgsCoordinateReferenceSystem,
    QgsCoordinateTransform, QgsRectangle, QgsSingleSymbolRenderer,
    QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsMarkerSymbol,
    QgsLineSymbol, QgsFillSymbol, QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling, QgsTextFormat, QgsTextBufferSettings,
    QgsPrintLayout, QgsLayoutItemLabel, QgsLayoutItemMap,
    QgsLayoutItemScaleBar, QgsLayoutSize, QgsLayoutPoint, QgsLayoutExporter
)
from qgis.PyQt.QtGui import QColor, QFont

ROOT = Path(__file__).resolve().parent.parent
GPKG = ROOT / 'data' / 'CIQ_ABC_FINAL_EDITABLE.gpkg'
QGZ = ROOT / 'CIQ_ABC_FINAL_REVIEW.qgz'
EXPORTS = ROOT / 'exports'
EXPORTS.mkdir(parents=True, exist_ok=True)
assert GPKG.is_file(), 'Missing GIS source: ' + str(GPKG)

# Stable scientific assertions, checked before touching the open project.
def checked_layer(table):
    layer = QgsVectorLayer(str(GPKG) + '|layername=' + table, table, 'ogr')
    if not layer.isValid():
        raise RuntimeError('Unable to open GeoPackage table ' + table)
    return layer
expected = {
    'V7_ALL_62_RETAINED_ROLES':62, 'V7_ALL_111_GEOMETRY_ONLY':111,
    'B_10_FROZEN_NOT_PADS':10, 'B_33_FROZEN_reaudited':33,
    'V8_CIQ_PORT_6_EVIDENCE_POINTS':6,
    'V8_CIQ_PORT_10_GROUND_AND_UAV_GEOMETRY':10,
    'WMP228_history_two_discs':2,
    'UAV_4_SITE_SEARCH_REACH_2_MODELS':8,
}
for name, count in expected.items():
    v = checked_layer(name)
    if v.featureCount() != count:
        raise RuntimeError('Unexpected feature count in %s: %s != %s' % (name, v.featureCount(), count))
# This is a non-destructive copy of source files, but QgsProject.clear clears the UI.
prj = QgsProject.instance()
prj.clear()
CRS4326 = QgsCoordinateReferenceSystem('EPSG:4326')
CRS3857 = QgsCoordinateReferenceSystem('EPSG:3857')
prj.setCrs(CRS3857)
prj.setTitle('CIQ A/C/B | all nodes retained | geometry only | QGIS 3.22.4')
root = prj.layerTreeRoot()

# Group order is display order, from top (nodes) to bottom (basemap).
g_nodes = root.addGroup('01  NODES | survey candidates + demand + ground')
g_links = root.addGroup('02  LINKS | geometric candidates, NOT approved routes')
g_air = root.addGroup('03  AIRSPACE | historical scenarios NOT legal boundaries')
g_bounds = root.addGroup('04  STUDY WINDOWS | approximations')
g_reach = root.addGroup('05  UAV REACH | 70-percent nominal example ONLY / off')
g_labels = root.addGroup('06  OVERVIEW ID-ONLY LABEL LAYERS / layout only / off')
g_raw = root.addGroup('90  FROZEN SOURCE / inspection only / off')
g_base = root.addGroup('99  OSM ONLINE BASEMAP')
layers = {}

def add(table, name, group, show=True):
    v = QgsVectorLayer(str(GPKG) + '|layername=' + table, name, 'ogr')
    if not v.isValid():
        raise RuntimeError('Cannot load '+table)
    prj.addMapLayer(v, False)
    node = group.addLayer(v)
    node.setItemVisibilityChecked(show)
    layers[table] = v
    return v

# Bottom layer is XYZ online tiles; other layers work offline.
osm = QgsRasterLayer('type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png&zmax=19',
                     'OpenStreetMap contributors (online tiles)', 'wms')
if osm.isValid():
    prj.addMapLayer(osm, False)
    g_base.addLayer(osm)
else:
    print('Note: OSM online layer unavailable; vector mapping remains usable.')

# Add all exact sources as independently editable GeoPackage tables.
pts = add('V7_ALL_62_RETAINED_ROLES','V7 all A/C/B 62 nodes (NOT approved pads)',g_nodes)
port = add('V8_CIQ_PORT_6_EVIDENCE_POINTS','Six CIQ/Stulang land-side evidence nodes',g_nodes)
ciq = add('G_CIQ_ground_gateway','Causeway CIQ ground gateway only',g_nodes)
links = add('V7_ALL_111_GEOMETRY_ONLY','V7 111 straight-line candidates',g_links)
portlinks = add('V8_CIQ_PORT_10_GROUND_AND_UAV_GEOMETRY','V8 five UAV candidates + five GROUND beelines',g_links)
ground = add('HOLD_ground_only_harbours','V7 ground-only harbour references (beelines)',g_links,False)
wmp = add('WMP228_history_two_discs','WMP228 two historical 2 NM reference circles',g_air)
senai = add('Senai_5NM_aerodrome_ADVISORY','Senai aerodrome advisory circle (not legal)',g_air,False)
ac = add('AC_study_corridors_APPROX','A/C approximate study windows (not hand-traced)',g_bounds)
barea = add('B_geometric_display_envelope','B visual envelope: convex hull + 1.7 km (not official)',g_bounds)
reach = add('UAV_4_SITE_SEARCH_REACH_2_MODELS','DJI/Wing 70% nominal geometry only (optional)',g_reach,False)
v8reach=add('V8_DJI_GEOMETRIC_REACH_ONLY','V8 port DJI geometry-only reference',g_reach,False)
rawb = add('B_10_FROZEN_NOT_PADS','Frozen B00–B09 source (do not edit)',g_raw,False)
rawbline = add('B_33_FROZEN_reaudited','Frozen B 33 base geometries (do not edit)',g_raw,False)
rawac = add('AC_52_nodes_NOT_PADS','A/C 52 original source reference nodes',g_raw,False)
rawacline = add('AC_78_geometric_links','A/C 78 original source candidate links',g_raw,False)

# Study-window polygons: softly transparent, but all symbols are non-authoritative.
ac.setRenderer(QgsCategorizedSymbolRenderer('zone',[
    QgsRendererCategory('A',QgsFillSymbol.createSimple({'color':'34,177,185,15','outline_color':'0,135,148,215','outline_style':'dash','outline_width':'0.65'}),'A east / approximation'),
    QgsRendererCategory('C',QgsFillSymbol.createSimple({'color':'237,111,68,15','outline_color':'214,92,72,220','outline_style':'dash','outline_width':'0.65'}),'C west / approximation')
]))
barea.renderer().setSymbol(QgsFillSymbol.createSimple({
    'color':'77,115,204,10','outline_color':'71,93,158,165','outline_style':'dash','outline_width':'0.45'}))

wmp.setRenderer(QgsCategorizedSymbolRenderer('scenario',[
    QgsRendererCategory('CAAM_2025',QgsFillSymbol.createSimple({
        'color':'203,50,61,12','outline_color':'176,33,48,235','outline_style':'dash','outline_width':'0.9'}),'CAAM 2025 historical disc'),
    QgsRendererCategory('CAAS_2026',QgsFillSymbol.createSimple({
        'color':'245,150,49,5','outline_color':'210,124,30,210','outline_style':'dash','outline_width':'0.75'}),'CAAS 2026 historical disc')
]))
senai.renderer().setSymbol(QgsFillSymbol.createSimple({
    'color':'245,200,45,0','outline_color':'160,113,46,175','outline_style':'dot','outline_width':'0.5'}))

# Never style geometric candidates as approved airways: all dashed.
links.setRenderer(QgsCategorizedSymbolRenderer('dji_distance_class',[
    QgsRendererCategory('GEOMETRY_WITHIN_5P6_KM',QgsLineSymbol.createSimple({
        'line_color':'24,115,151,195','line_width':'0.42','line_style':'dash'}),
        'Within DJI 5.6 km model geometry; NOT approved'),
    QgsRendererCategory('GEOMETRY_EXCEEDS_5P6_KM',QgsLineSymbol.createSimple({
        'line_color':'193,97,44,220','line_width':'0.52','line_style':'dash'}),
        'Beyond DJI 5.6 km model; Wing geometrically within')
]))
portlinks.setRenderer(QgsCategorizedSymbolRenderer('mode',[
    QgsRendererCategory('UAV_GEOMETRY_SEARCH',QgsLineSymbol.createSimple({
        'line_color':'0,139,119,255','line_width':'0.8','line_style':'dash'}),'Port-area UAV GEOMETRY candidates'),
    QgsRendererCategory('GROUND_HANDOFF_STRAIGHT_REFERENCE',QgsLineSymbol.createSimple({
        'line_color':'88,94,104,215','line_width':'0.6','line_style':'dot'}),'GROUND beelines; NOT road routes')
]))
ground.renderer().setSymbol(QgsLineSymbol.createSimple({
    'line_color':'95,105,112,190','line_width':'0.3','line_style':'dot'}))

pts.setRenderer(QgsCategorizedSymbolRenderer('retention_class',[
    QgsRendererCategory('RETAIN_PRIORITY_SITE_SEARCH',QgsMarkerSymbol.createSimple({
        'name':'triangle','color':'15,132,112,255','size':'2.5','outline_color':'255,255,255,255','outline_width':'0.3'}),'12 survey-priority candidate properties / NOT pads'),
    QgsRendererCategory('RETAIN_DEMAND_AND_ALTERNATE_SEARCH',QgsMarkerSymbol.createSimple({
        'name':'circle','color':'205,146,81,255','size':'1.8','outline_color':'255,255,255,255','outline_width':'0.2'}),'Demand or alternate study nodes'),
    QgsRendererCategory('RETAIN_GROUND_DEMAND_ONLY',QgsMarkerSymbol.createSimple({
        'name':'square','color':'140,96,76,255','size':'1.9','outline_color':'255,255,255,255','outline_width':'0.2'}),'Ground only / demand reference'),
    QgsRendererCategory('RETAIN_B_FROZEN_NOT_PAD',QgsMarkerSymbol.createSimple({
        'name':'circle','color':'58,94,160,255','size':'2.0','outline_color':'255,255,255,255','outline_width':'0.2'}),'Frozen B reference nodes, NOT pads')
]))
port.setRenderer(QgsCategorizedSymbolRenderer('node_role',[
    QgsRendererCategory('UAV_PARCEL_SEARCH_ONLY',QgsMarkerSymbol.createSimple({
        'name':'triangle','color':'14,139,89,255','size':'4.2','outline_color':'255,255,255,255','outline_width':'0.38'}),'A_P01 ground parking parcel search'),
    QgsRendererCategory('GROUND_TRANSFER_REFERENCE',QgsMarkerSymbol.createSimple({
        'name':'square','color':'76,95,107,255','size':'2.2','outline_color':'255,255,255,255','outline_width':'0.2'}),'Ground transfer'),
    QgsRendererCategory('PORT_STRUCTURE_GROUND_TERMINAL',QgsMarkerSymbol.createSimple({
        'name':'diamond','color':'178,92,36,255','size':'3.3','outline_color':'255,255,255,255','outline_width':'0.22'}),'Ferry terminal building; ground only'),
    *[QgsRendererCategory(label,QgsMarkerSymbol.createSimple({
        'name':'circle','color':'154,115,93,255','size':'2.0','outline_color':'255,255,255,255','outline_width':'0.2'}),label.replace('_',' ').title()) for label in (
        'COMMERCIAL_DEMAND_GROUND_ONLY','COMMERCIAL_GROUND_EXCHANGE_ONLY','LOCAL_RETAIL_DEMAND_ONLY')]
]))
ciq.renderer().setSymbol(QgsMarkerSymbol.createSimple({
    'name':'diamond','color':'34,41,53,255','size':'3.6','outline_color':'255,255,255,255','outline_width':'0.3'}))

# Both model coverage layers invisible by default; selecting large Wing buffers can dominate map.
reach.setRenderer(QgsCategorizedSymbolRenderer('scenario',[
    QgsRendererCategory('DJI_FLYCART30_5P6KM',QgsFillSymbol.createSimple({
        'color':'31,141,175,11','outline_color':'22,123,164,120','outline_style':'dot','outline_width':'0.45'}),'DJI 5.6 km model'),
    QgsRendererCategory('WINGCOPTER198_32P2KM',QgsFillSymbol.createSimple({
        'color':'151,126,195,5','outline_color':'129,91,161,125','outline_style':'dash','outline_width':'0.35'}),'Wing 32.2 km model')
]))
v8reach.renderer().setSymbol(QgsFillSymbol.createSimple({
    'color':'10,159,108,12','outline_color':'10,159,108,130','outline_style':'dot','outline_width':'0.5'}))

# LABEL REPAIR (2026-10-30): the previous project suppressed all but priority IDs.
# The three source point layers now label EVERY feature, by ID + complete name.
# QGIS PAL's default collision filtering is disabled for these labels; at overview
# scale some labels can overlap, so dedicated region maps + printed name indexes
# are provided below. This changes NO geometry or source attributes.
def set_labels(v, expr, is_expression=True, size=7.5, priority=9, distance_mm=1.2):
    pal=QgsPalLayerSettings()
    pal.fieldName=expr
    pal.isExpression=is_expression
    pal.placement=QgsPalLayerSettings.OrderedPositionsAroundPoint
    pal.priority=priority
    pal.dist=distance_mm
    pal.displayAll=True  # critical: do NOT silently drop nodes due to collision
    tf=QgsTextFormat()
    font=QFont('Arial')
    font.setBold(True)
    tf.setFont(font)
    tf.setSize(size)
    tf.setColor(QColor('#111111'))
    b=QgsTextBufferSettings()
    b.setEnabled(True)
    b.setSize(0.7)
    b.setColor(QColor('white'))
    tf.setBuffer(b)
    pal.setFormat(tf)
    v.setLabeling(QgsVectorLayerSimpleLabeling(pal))
    v.setLabelsEnabled(True)

set_labels(pts, '"id" || '  |  ' || "name"',True,7.5,9)
set_labels(port, '"node_id" || '  |  ' || "name"',True,7.5,10)
set_labels(ciq, '"id" || '  |  ' || "name"',True,7.5,10)

# For the single overview, use separate copies of the SAME point data,
# labelled by ID only. Copies are render-only; original geometries unchanged.
# The overview layout explicitly uses these instead of the full-name layers.
ids_pts=add('V7_ALL_62_RETAINED_ROLES','OVERVIEW IDs | all 62',g_labels,False)
ids_port=add('V8_CIQ_PORT_6_EVIDENCE_POINTS','OVERVIEW IDs | all 6 port',g_labels,False)
ids_ciq=add('G_CIQ_ground_gateway','OVERVIEW IDs | CIQ gateway',g_labels,False)
for source, target, field in ((pts,ids_pts,'id'),(port,ids_port,'node_id'),(ciq,ids_ciq,'id')):
    target.setRenderer(source.renderer().clone())
    set_labels(target,field,False,7.0,10,0.8)

# Raw/audit layers and range circles are hidden in the default canvas.
g_reach.setItemVisibilityChecked(False)
g_labels.setItemVisibilityChecked(False)
g_raw.setItemVisibilityChecked(False)

# Layout layer lists are locked and independent from the canvas view.
background=[portlinks,ground,links,wmp,senai,ac,barea]
if osm.isValid(): background.append(osm)
display=[port,ciq,pts]+background
id_display=[ids_port,ids_ciq,ids_pts]+background

# Complete node index used for sidebars and standalone index pages.
# Feature attributes are read from the delivered GPKG, not hard-coded.
node_index={'A':[], 'C':[], 'B':[], 'A_PORT':[], 'CIQ_GROUND':[]}
for f in pts.getFeatures():
    zone=str(f['zone'])
    if zone not in node_index: raise RuntimeError('Unknown node zone: '+zone)
    node_index[zone].append((str(f['id']),str(f['name'])))
for f in port.getFeatures():
    node_index['A_PORT'].append((str(f['node_id']),str(f['name'])))
for f in ciq.getFeatures():
    node_index['CIQ_GROUND'].append((str(f['id']),str(f['name'])))
for zone in node_index:
    node_index[zone].sort(key=lambda item:item[0])
assert [len(node_index[z]) for z in ('A','C','B','A_PORT','CIQ_GROUND')]==[23,29,10,6,1]
assert all(k.strip() and name.strip() for values in node_index.values() for k,name in values)
assert len(set(k for values in node_index.values() for k,name in values))==69

# Page helpers.
def new_layout(name, width=420, height=297):
    l=QgsPrintLayout(prj);l.initializeDefaults();l.setName(name)
    l.pageCollection().page(0).setPageSize(QgsLayoutSize(width,height))
    return l

def label(l,s,x,y,w,h,size=9,bold=False):
    t=QgsLayoutItemLabel(l);t.setText(s);t.setFont(QFont('Arial',size,QFont.Bold if bold else QFont.Normal))
    t.setFontColor(QColor('#111827'))
    l.addLayoutItem(t);t.attemptMove(QgsLayoutPoint(x,y));t.attemptResize(QgsLayoutSize(w,h))
    return t

def make_map(l,x,y,w,h,extent,title=None,layerset=None,scale=True):
    if title: label(l,title,x,y-10,w,9,10,True)
    m=QgsLayoutItemMap(l);l.addLayoutItem(m)
    m.attemptMove(QgsLayoutPoint(x,y));m.attemptResize(QgsLayoutSize(w,h))
    m.setCrs(CRS4326)
    m.setLayers(layerset or display);m.setKeepLayerSet(True)
    m.zoomToExtent(QgsRectangle(*extent))
    m.setFrameEnabled(True);m.setFrameStrokeColor(QColor('#c5cbd2'))
    # North is at the top of WGS84 maps in these non-rotated layouts.
    label(l,'N  \u2191',x+w-17,y+3,15,8,8,True)
    if scale:
        sb=QgsLayoutItemScaleBar(l)
        sb.setStyle('Single Box');sb.setLinkedMap(m);sb.applyDefaultSize()
        sb.setNumberOfSegments(2);sb.setNumberOfSegmentsLeft(0)
        l.addLayoutItem(sb);sb.attemptMove(QgsLayoutPoint(x+5,y+h-14))
    return m

def publish(layout, basename, dpi=300):
    prj.layoutManager().addLayout(layout)
    exp=QgsLayoutExporter(layout)
    st=QgsLayoutExporter.ImageExportSettings();st.dpi=dpi
    # Export may have online OSM tile errors offline; vector .qgz is still fully usable.
    try:
        code=exp.exportToImage(str(EXPORTS/(basename+'.png')),st)
        print('PNG export result:',basename,code)
    except Exception as ex:
        print('PNG export failed (project saved anyway):',basename,str(ex))

# Overview: ALL 69 IDs, using ID-only layout layers (not priority-only).
l1=new_layout('01  OVERVIEW A C B | ALL 69 IDs')
label(l1,'Causeway / Second Link  |  A–C–B candidate logistics network',10,5,400,13,16,True)
label(l1,'68 evidence-reference nodes + 1 ground gateway  |  116 UAV geometry candidates / 5 ground beelines  |  0 authorized UAV sites',10,19,400,8,9)
make_map(l1,10,35,400,215,(103.510,1.319,103.864,1.574),layerset=id_display,scale=True)
label(l1,'A = east/coastal search  |  C = west residential/industrial linkage  |  B = frozen Second Link core',10,255,400,8,9,True)
label(l1,'Red / orange dashed circles: historical WMP228 sensitivity references, NOT verified current legal boundaries.',10,267,400,8,8)
label(l1,'Dashed connections: straight-line geometry, NOT cleared air routes. Grey dotted connections: ground BEELINES, NOT road routes.',10,278,400,8,8)
publish(l1,'01_AB_C_overview_300dpi')

# Dedicated A/C/B maps with ALL ID + full-name labels (collision forced).
l2=new_layout('02  A C B | ALL FULL NODE NAMES')
label(l2,'Area A / C / B  |  ALL node names and screening-only straight lines',10,5,400,12,15,True)
label(l2,'Editable QGIS source in data/  •  A11 not reinstated  •  B00–B09 frozen',10,19,400,8,9)
make_map(l2,10,42,130,204,(103.739,1.441,103.853,1.562),'A  /  East–coastal')
make_map(l2,145,42,130,204,(103.577,1.382,103.766,1.569),'C  /  West–B connector')
make_map(l2,280,42,130,204,(103.525,1.323,103.696,1.474),'B  /  Frozen core')
label(l2,'Green triangles: parcel survey candidates (NOT approved landing pads). Brown circles/squares: demands or ground refs.',10,256,400,8,8)
label(l2,'Blue dashed: DJI nominal geometry within 5.6 km; orange dashed: exceeds 5.6 km; Wing geometry only.',10,268,400,8,8)
label(l2,'Any operational use requires current AIP/NOTAM, obstacle, ground risk, task energy, property access and CAAM authorization.',10,279,400,8,8)
publish(l2,'02_A_C_B_regions_300dpi')

# Enlarged CIQ and ferry-site review, geometry-only + separate ground-transfer depiction.
l3=new_layout('03  CAUSEWAY CIQ / STULANG PORT DETAIL',297,210)
label(l3,'Causeway CIQ – Stulang ferry terminal  |  property-search review',8,5,281,12,14,True)
label(l3,'A_P01 = existing mapped parking area; NOT a pad or approved launch location.',8,19,281,8,9)
make_map(l3,8,37,281,131,(103.756,1.457,103.802,1.492),scale=True)
label(l3,'5 dashed green lines: hypothetical UAV geometry to A nodes; 5 grey dotted lines: GROUND handoff beelines.',8,171,281,9,8)
label(l3,'WMP228 circles = historical geometric stress tests, NOT final legal coast-trimmed boundaries.',8,181,281,9,8)
label(l3,'Port, palace vicinity and population exposure: site and route acceptance are pending. Do not infer operational safety.',8,191,281,9,8)
publish(l3,'03_CIQ_STULANG_PORT_300dpi')

# Dedicated A3 map + complete text index for each region. This is the
# guaranteed readable fallback if some forced map labels overlap at overview.
def region_detail(zone, map_extent, region_title, basename):
    layout=new_layout('04  FULL LABELS / '+zone+' | MAP + INDEX')
    label(layout,region_title+'  |  ALL node IDs and complete names',10,5,400,13,15,True)
    label(layout,'Research references / parcel searches only. Label collision forcing is ON; inspect dense clusters at local zoom.',10,20,400,8,8)
    make_map(layout,10,41,296,228,map_extent,layerset=display,scale=True)
    label(layout,'NODE NAME INDEX  |  '+zone,312,37,98,10,10,True)
    index_rows=node_index[zone]
    if zone=='A': index_rows=index_rows+node_index['A_PORT']+node_index['CIQ_GROUND']
    # Side index uses two lines per record for readability and to preserve full names.
    line_height=7.25 if len(index_rows)>25 else 9.3
    y=49
    for code,name in index_rows:
        label(layout,code+'  '+name,312,y,98,line_height,7,False)
        y+=line_height
    label(layout,'Dashed lines = geometry only; NOT approved UAV routes. Historical WMP228 circles are sensitivity references.',10,274,400,9,8)
    publish(layout,basename)

region_detail('A',(103.733,1.442,103.861,1.565),
              'A / Causeway East and CIQ port','04_A_ALL_NODE_NAMES_300dpi')
region_detail('C',(103.572,1.385,103.772,1.574),
              'C / Western connector','05_C_ALL_NODE_NAMES_300dpi')
region_detail('B',(103.521,1.326,103.700,1.476),
              'B / Second Link frozen core','06_B_ALL_NODE_NAMES_300dpi')

# A compact plain-text audit layout that remains readable without map tiles.
# Every one of the 69 node names is present in either the A/C/B index pages.
# Save last, after all layout items and styles are already registered.
prj.setFileName(str(QGZ))
if not prj.write(): raise RuntimeError('QGIS project save failed: '+str(QGZ))
print('QGIS saved:',QGZ)
print('LABEL QA: 62 V7 + 6 V8 + 1 gateway = 69 unique ID + full-name labels.')
print('Loaded 68 evidence nodes + 1 G_CIQ ground gateway; V7 111 + V8 10 geometries.')
print('Approved UAV pads/routes = ZERO. Turn on the optional reach group only for technical scenarios.')
try:
    ext=QgsRectangle(103.515,1.322,103.858,1.57)
    trans=QgsCoordinateTransform(CRS4326, CRS3857, prj)
    iface.mapCanvas().setExtent(trans.transformBoundingBox(ext))
    iface.mapCanvas().refresh()
except Exception as ex:
    print('Canvas could not be repositioned:',str(ex))
