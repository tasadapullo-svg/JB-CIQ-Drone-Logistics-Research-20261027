import csv
import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "next_stage"
MANIFEST = OUT / "SHA256_manifest.csv"
ZIP_PATH = ROOT / "outputs" / "CIQ_next_stage_audit_smoke_20261027.zip"
ZIP_HASH_PATH = ZIP_PATH.with_suffix(ZIP_PATH.suffix + ".sha256")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def delivery_files() -> list[Path]:
    return sorted(
        path
        for path in OUT.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path != MANIFEST
    )


files = delivery_files()
with MANIFEST.open("w", newline="", encoding="utf-8-sig") as stream:
    writer = csv.DictWriter(stream, fieldnames=["relative_path", "bytes", "sha256"])
    writer.writeheader()
    for path in files:
        writer.writerow(
            {
                "relative_path": path.relative_to(OUT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )

with ZipFile(ZIP_PATH, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
    for path in [*files, MANIFEST]:
        archive.write(path, arcname=(Path("next_stage") / path.relative_to(OUT)).as_posix())

zip_hash = sha256(ZIP_PATH)
ZIP_HASH_PATH.write_text(f"{zip_hash}  {ZIP_PATH.name}\n", encoding="utf-8")
print(f"MANIFEST_ROWS {len(files)}")
print(f"ZIP_BYTES {ZIP_PATH.stat().st_size}")
print(f"ZIP_SHA256 {zip_hash}")
