"""Static syntax/safety checks only; does not execute PyQGIS."""
import ast
from pathlib import Path
p=Path(__file__).parents[1]/'scripts'/'stage02_qgis_console.py'
s=p.read_text(encoding='utf-8')
ast.parse(s)
assert "numerical_recalculation_released':False" in s
assert 'OLD_19_SITE_DATA_NOT_GROUNDED' in s
assert 'EDGE_ENDPOINT_GAP_GT_50M' in s
assert 'NODE_NAME_BLANK' in s
assert 'ZONE_NOT_EVIDENCED' in s
assert 'AIRSPACE_WMP228_CTR_CAAM_CAAS' in s
assert 'CIQ_STAGE02_OUT' in s
assert '.save(' not in s
print('PyQGIS script AST/safety checks passed; not a real QGIS execution')
