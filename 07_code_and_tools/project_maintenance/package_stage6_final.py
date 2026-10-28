from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile


ROOT = Path(__file__).resolve().parents[2]
STAGE6 = ROOT / "10_阶段实验成果" / "Stage6_双区域多级接驳"
OLD = next(STAGE6.glob("CIQ_Stage6_GPT_*.zip"))
FINAL = STAGE6 / "CIQ_Stage6_最终完整工程_30种子_20261027.zip"
FINAL_HASH = FINAL.with_suffix(FINAL.suffix + ".sha256")


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


members: dict[str, bytes] = {}
with ZipFile(OLD) as source:
    for info in source.infolist():
        base = Path(info.filename).name
        if base == "stage6_file_sha256_manifest.csv":
            continue
        if base.lower().endswith(".zip"):
            base = "CIQ_GPT校验所需三归档与关键数据_20261027.zip"
        elif base.lower().endswith(".xlsx"):
            base = "CIQ_Stage6_双区域多级接驳_同服务边界_20261027.xlsx"
        elif base == "README_STAGE6_CN.md":
            continue
        members[f"Stage6/{base}"] = source.read(info.filename)

for name in ["README_STAGE6_CN.md", "RUN_INSTRUCTIONS.md", "requirements.txt", "STAGE6_验收报告_20261027.md"]:
    members[f"Stage6/{name}"] = (STAGE6 / name).read_bytes()

buffer = io.StringIO()
writer = csv.DictWriter(buffer, fieldnames=["filename", "sha256", "bytes"], lineterminator="\n")
writer.writeheader()
for archive_name, data in sorted(members.items()):
    writer.writerow({"filename": Path(archive_name).name, "sha256": digest_bytes(data), "bytes": len(data)})
members["Stage6/stage6_file_sha256_manifest.csv"] = ("\ufeff" + buffer.getvalue()).encode("utf-8")

with ZipFile(FINAL, "w", allowZip64=True) as archive:
    for archive_name, data in sorted(members.items()):
        compression = ZIP_STORED if archive_name.lower().endswith(".zip") else ZIP_DEFLATED
        archive.writestr(archive_name, data, compress_type=compression, compresslevel=9 if compression == ZIP_DEFLATED else None)

with ZipFile(FINAL) as check:
    if check.testzip() is not None:
        raise RuntimeError("Final ZIP failed CRC test")
    manifest = list(csv.DictReader(io.StringIO(check.read("Stage6/stage6_file_sha256_manifest.csv").decode("utf-8-sig"))))
    names = set(check.namelist())
    for row in manifest:
        name = f"Stage6/{row['filename']}"
        if name not in names:
            raise RuntimeError(f"Manifest member missing: {name}")
        data = check.read(name)
        if len(data) != int(row["bytes"]) or digest_bytes(data) != row["sha256"]:
            raise RuntimeError(f"Manifest mismatch: {name}")

zip_hash = digest_file(FINAL)
FINAL_HASH.write_text(f"{zip_hash}  {FINAL.name}\n", encoding="utf-8")

if OLD != FINAL and OLD.exists():
    OLD.unlink()

print(f"FINAL={FINAL}")
print(f"MEMBERS={len(members)}")
print(f"BYTES={FINAL.stat().st_size}")
print(f"SHA256={zip_hash}")
