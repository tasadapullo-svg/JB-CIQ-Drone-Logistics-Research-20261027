from __future__ import annotations

import importlib.util
import traceback
from pathlib import Path


test_file = Path(__file__).with_name("test_s11b.py")
spec = importlib.util.spec_from_file_location("test_s11b", test_file)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

tests = sorted((name, fn) for name, fn in vars(module).items() if name.startswith("test_") and callable(fn))
failed = []
for name, fn in tests:
    try:
        fn()
        print(f"PASS {name}")
    except Exception:
        failed.append(name)
        print(f"FAIL {name}")
        traceback.print_exc()

print(f"TOTAL={len(tests)} PASS={len(tests)-len(failed)} FAIL={len(failed)}")
raise SystemExit(1 if failed else 0)
