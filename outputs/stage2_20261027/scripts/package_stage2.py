import csv
import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "stage2_20261027"
MANIFEST = OUT / "file_sha256_manifest.csv"
ZIP_PATH = ROOT / "outputs" / "CIQ_stage2_repair_calibrate_gates_20261027.zip"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


files = sorted(path for path in OUT.rglob("*") if path.is_file() and "__pycache__" not in path.parts and path != MANIFEST)
with MANIFEST.open("w", newline="", encoding="utf-8-sig") as stream:
    writer = csv.DictWriter(stream, fieldnames=["relative_path", "bytes", "sha256"])
    writer.writeheader()
    for path in files:
        writer.writerow({"relative_path": path.relative_to(OUT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})

with ZipFile(ZIP_PATH, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
    for path in [*files, MANIFEST]:
        archive.write(path, arcname=(Path("stage2_20261027") / path.relative_to(OUT)).as_posix())

zip_hash = sha256(ZIP_PATH)
ZIP_PATH.with_suffix(ZIP_PATH.suffix + ".sha256").write_text(f"{zip_hash}  {ZIP_PATH.name}\n", encoding="utf-8")
print("FILES", len(files) + 1)
print("ZIP_BYTES", ZIP_PATH.stat().st_size)
print("ZIP_SHA256", zip_hash)
