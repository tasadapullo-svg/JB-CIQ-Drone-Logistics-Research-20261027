# Complete portable QGIS project V3 — packaging audit

- `CIQ_ABC_ALL_69_NAMES_PORTABLE.qgz` and `.qgs`: portable preassembled QGIS project with **relative** GeoPackage paths and all 19 tables; 69 full-name labels configured.
- `data/CIQ_ABC_FINAL_EDITABLE.gpkg`: original (unchanged) SQLite GeoPackage.
- `code/01_BUILD_COMPLETE_QGIS322.py`: authoritative PyQGIS build for the fully styled review project and six print layouts; run in QGIS desktop, not normal Python.
- `code/RUN_ONE_LINE_IN_QGIS_CONSOLE.txt`: console one-line launcher.
- `figures/`: offline QA index and previous map previews.
- `qa/`: all label checks and existing geometry QA tables; no simulation results were modified.

**Caveat:** Preassembled QGZ XML was generated outside the QGIS runtime and passed XML validation, but has not been opened in QGIS 3.22.4. The rebuild script is the full-fidelity fallback.

**Source safety:** All routes are candidate straight-line geometries only, not legally authorized routes; historical circles are not verified current legal boundaries.
