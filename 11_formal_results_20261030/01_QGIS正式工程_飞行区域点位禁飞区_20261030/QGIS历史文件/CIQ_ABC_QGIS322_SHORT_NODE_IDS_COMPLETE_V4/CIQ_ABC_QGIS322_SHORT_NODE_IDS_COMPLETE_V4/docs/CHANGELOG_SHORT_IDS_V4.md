# V4 — 69 node SHORT IDs only

## Requested visual change
- Labels on the main map, regional maps, and ports are **only the node code** (B00, C01, A_N05, etc.).
- The source GIS `name` attribute is retained, but no longer concatenated to the visible map label.
- QGIS portable `.qgs` and `.qgz` each specify `labeling/fieldName=id` or `node_id`, with `labeling/isExpression=false`, and force `labeling/displayAll=true` for the three node layers.
- Build script and recovery script now use ID-only labels, and regional layout sidebars no longer enumerate full names.
- Offline QA pictures regenerated with ID-only map symbols and no full-name legend.
- Original nodes and links are byte-for-byte unchanged in the GeoPackage.

## Validation boundary
Static XML/ZIP integrity, node uniqueness and source-data checks performed. Rendering via QGIS 3.22.4 and its online OSM tiles is not available in the build runtime. Dense points may still require manual label offsets for optimal presentation at final print scale.
