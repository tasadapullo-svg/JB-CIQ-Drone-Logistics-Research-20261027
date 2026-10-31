# -*- coding: utf-8 -*-
# QGIS 3.22.4. Open V5 project directly; this optional tool adds OSM if absent.
from pathlib import Path
from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer, QgsPalLayerSettings, QgsVectorLayerSimpleLabeling, QgsTextFormat, QgsTextBufferSettings
from qgis.PyQt.QtGui import QFont,QColor

path=Path(__file__).resolve().parent.parent
qgz=path/'CIQ_ABC_V5_68_NODES_ONE_WMP228.qgz'
p=QgsProject.instance()
if not p.read(str(qgz)):
    raise RuntimeError('Failed to open V5 project: '+str(qgz))
# Confirm all selected V5 vector layers resolved correctly.
missing=[x.name() for x in p.mapLayers().values() if isinstance(x,QgsVectorLayer) and not x.isValid()]
if missing:
    raise RuntimeError('Missing or invalid VECTOR layers: '+repr(missing))
# Repair XYZ on installations where a stored WMS/XYZ raster cannot initialize.
for x in list(p.mapLayers().values()):
    if x.name()=='OpenStreetMap (online)' and not x.isValid():
        p.removeMapLayer(x.id())
if not any(x.name()=='OpenStreetMap (online)' for x in p.mapLayers().values()):
    osm=QgsRasterLayer('type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png&zmin=0&zmax=19','OpenStreetMap (online)','wms')
    if osm.isValid():
        p.addMapLayer(osm,False)
        group=p.layerTreeRoot().addGroup('99  BASEMAP | Internet needed')
        group.addLayer(osm)
    else:
        print('WARN: OSM XYZ not available; GIS data is valid without basemap')
# Update label behavior for QGIS 3.22 using its native writer, so no legacy XML ambiguity.
for l in p.mapLayers().values():
    if not isinstance(l,QgsVectorLayer):continue
    table=l.source().split('|layername=')[-1]
    if table.endswith('_NODES') or table in ('A_GROUND_GATEWAY','A_PORT_6_NODES'):
        key='node_id' if table=='A_PORT_6_NODES' else 'id'; font=8
    elif table.endswith('_AREA_LABEL') or table=='WMP228_LABEL':
        key='label';font=15 if table.endswith('_AREA_LABEL') else 12
    else:continue
    s=QgsPalLayerSettings();s.fieldName=key;s.isExpression=False;s.displayAll=True;s.placement=QgsPalLayerSettings.OrderedPositionsAroundPoint;s.dist=0.5 if key=='label' else 1.25
    f=QgsTextFormat();ft=QFont('Arial');ft.setBold(True);f.setFont(ft);f.setSize(font);f.setColor(QColor('#202020'))
    buffer=QgsTextBufferSettings();buffer.setEnabled(True);buffer.setSize(0.8);buffer.setColor(QColor('white'));f.setBuffer(buffer)
    s.setFormat(f);l.setLabeling(QgsVectorLayerSimpleLabeling(s));l.setLabelsEnabled(True)
if not p.write(str(qgz)):
    raise RuntimeError('Could not save V5 project: '+str(qgz))
iface.mapCanvas().refresh()
print('SUCCESS | V5 QGIS project opened and saved: '+str(qgz))
print('A/B/C groups and four text labels can be toggled separately.')
