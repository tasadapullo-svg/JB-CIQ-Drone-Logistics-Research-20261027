# -*- coding: utf-8 -*-
"""Use inside QGIS Desktop 3.22.4 Python console, AFTER opening
CIQ_ABC_69_SHORT_IDS_PORTABLE.qgz.
Apply only short node IDs directly, without clearing the project.
"""
from qgis.core import (
    QgsProject, QgsPalLayerSettings, QgsVectorLayerSimpleLabeling,
    QgsTextFormat, QgsTextBufferSettings
)
from qgis.PyQt.QtGui import QColor, QFont

project = QgsProject.instance()
REQUIRED = {
    'V7_ALL_62_RETAINED_ROLES': ('id', 62),
    'V8_CIQ_PORT_6_EVIDENCE_POINTS': ('node_id', 6),
    'G_CIQ_ground_gateway': ('id', 1)
}
found = {}
for layer in project.mapLayers().values():
    src = layer.source() if hasattr(layer, 'source') else ''
    if '|layername=' not in src:
        continue
    name = src.split('|layername=')[-1].split('|')[0]
    if name not in REQUIRED:
        continue
    fld, expected = REQUIRED[name]
    if not layer.isValid():
        raise RuntimeError('Invalid layer: ' + name)
    if layer.featureCount() != expected:
        raise RuntimeError('Count mismatch: %s: %s vs %s' % (name, layer.featureCount(), expected))
    actual_fields = [f.name() for f in layer.fields()]
    if not all(f in actual_fields for f in [fld, 'name']):
        raise RuntimeError('Missing ID/name attribute: ' + name)
    config = QgsPalLayerSettings()
    config.fieldName = fld
    config.isExpression = False
    config.placement = QgsPalLayerSettings.OrderedPositionsAroundPoint
    config.dist = 1.2
    config.priority = 10
    config.displayAll = True
    config.scaleVisibility = False
    fmt = QgsTextFormat()
    font = QFont('Arial')
    font.setBold(True)
    fmt.setFont(font)
    fmt.setSize(8.0)
    fmt.setColor(QColor('#111111'))
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(0.75)
    buffer.setColor(QColor('white'))
    fmt.setBuffer(buffer)
    config.setFormat(fmt)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(config))
    layer.setLabelsEnabled(True)
    layer.triggerRepaint()
    found[name] = layer.featureCount()

if set(found) != set(REQUIRED):
    raise RuntimeError('Node layer(s) missing: ' + ', '.join(sorted(set(REQUIRED)-set(found))))
project.setDirty(True)
if not project.write():
    raise RuntimeError('Could not save QGIS project; use Project > Save As')
iface.mapCanvas().refresh()
print('SUCCESS: forced all 69 SHORT ID-only labels; project saved:', project.fileName())
print('Layer QA:', found)
