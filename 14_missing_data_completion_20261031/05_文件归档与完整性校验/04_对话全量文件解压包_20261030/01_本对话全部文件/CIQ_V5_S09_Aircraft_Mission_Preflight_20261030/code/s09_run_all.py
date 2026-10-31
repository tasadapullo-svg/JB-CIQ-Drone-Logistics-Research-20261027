#!/usr/bin/env python3
"""Unambiguous reproducible main entrypoint for the frozen V5-S09 screening."""
from pathlib import Path
from build_s09_preflight import build
from check_s07_sources import main as source_gate
import json,unittest,sys

def run(root):
 a=build(root);b=source_gate(root)
 suite=unittest.defaultTestLoader.discover(str(Path(root)/'tests'))
 result=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
 summary={'status':'S09_STATIC_OEM_SCREENS_PASS_S07_SOURCE_NUMERIC_HOLD','frozen_tasks':a['fixed_population'],
          'full_service_model_released':False,'weather_xlsx_verified':b['weather_workbooks_accepted'],
          'unit_tests_run':result.testsRun,'unit_tests_failures':len(result.failures)+len(result.errors)}
 (Path(root)/'qa'/'RUN_ALL_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 if not result.wasSuccessful():raise SystemExit(1)
 return summary
if __name__=='__main__':print(json.dumps(run(Path(__file__).resolve().parents[1]),ensure_ascii=False))
