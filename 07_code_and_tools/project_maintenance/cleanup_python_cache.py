from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
expected = Path(r"C:\Users\DELL\Desktop\CIQ 无人机物流 SCI 研_20261026").resolve()
if ROOT != expected:
    raise RuntimeError(f"Refusing unexpected root: {ROOT}")

files = list(ROOT.rglob("*.pyc"))
for path in files:
    path.resolve().relative_to(ROOT)
    path.unlink()

directories = sorted((p for p in ROOT.rglob("__pycache__") if p.is_dir()), key=lambda p: len(p.parts), reverse=True)
removed_directories = 0
for directory in directories:
    directory.resolve().relative_to(ROOT)
    if not any(directory.iterdir()):
        directory.rmdir()
        removed_directories += 1

print(f"REMOVED_PYC={len(files)}")
print(f"REMOVED_EMPTY_CACHE_DIRS={removed_directories}")
