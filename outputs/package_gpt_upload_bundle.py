import csv
import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "CIQ_GPT校验所需三归档与关键数据_20261027.zip"
HASH_FILE = OUTPUT.with_suffix(OUTPUT.suffix + ".sha256")

FILES = [
    (
        next(ROOT.rglob("JB_CIQ_E05_V5.6_30次*.zip")),
        "01_三个归档/JB_CIQ_E05_V5.6_30次重复订单_全天交通天气稳健性_完整归档.zip",
        "必须：30个种子、918000条合成订单",
    ),
    (
        next(ROOT.rglob("JB_CIQ_E05-E07_24小时*.zip")),
        "01_三个归档/JB_CIQ_E05-E07_24小时地空物流联调_V5.3_实验前置归档.zip",
        "必须：交通代理模型、联调数据和代码",
    ),
    (
        ROOT / "outputs" / "CIQ_stage2_repair_calibrate_gates_20261027.zip",
        "01_三个归档/CIQ_stage2_repair_calibrate_gates_20261027.zip",
        "建议：Stage 2异常OD诊断、门槛和候选路径",
    ),
    (
        ROOT / "02_基础与交通数据" / "联合与派生数据" / "01_AB_24h_hourly_joint.csv",
        "02_关键数据/01_AB_24h_hourly_joint.csv",
        "24小时交通—气象联结数据",
    ),
    (
        ROOT / "02_基础与交通数据" / "联合与派生数据" / "03_hourly_91_reference_OD_MODEL_PROXY_NOT_REAL.csv.gz",
        "02_关键数据/03_hourly_91_reference_OD_MODEL_PROXY_NOT_REAL.csv.gz",
        "91个可路由OD的道路时间代理",
    ),
    (
        ROOT / "04_天气数据" / "汇总数据" / "E03_ERA5_JB_TWO_CIQ_WEATHER_HOURLY.csv",
        "02_关键数据/E03_ERA5_JB_TWO_CIQ_WEATHER_HOURLY.csv",
        "气象条件",
    ),
    (
        ROOT / "03_GIS与路网" / "路网工程" / "JB_CIQ_E02_roadnet_V4_6" / "inputs" / "19_site_reference_anchors_NOT_LAUNCH_PADS.csv",
        "02_关键数据/19_site_reference_anchors_NOT_LAUNCH_PADS.csv",
        "19个候选参考地点；不是已批准起降点",
    ),
    (
        ROOT / "03_GIS与路网" / "路网工程" / "JB_CIQ_E02_roadnet_V4_6" / "outputs" / "E02_A_OD_OSM_MODEL_NOT_OBSERVED.csv",
        "02_关键数据/E02_A_OD_OSM_MODEL_NOT_OBSERVED.csv",
        "A区道路OD模型输出；不是实测旅行时间",
    ),
    (
        ROOT / "03_GIS与路网" / "路网工程" / "JB_CIQ_E02_roadnet_V4_6" / "outputs" / "E02_B_OD_OSM_MODEL_NOT_OBSERVED.csv",
        "02_关键数据/E02_B_OD_OSM_MODEL_NOT_OBSERVED.csv",
        "B区道路OD模型输出；不是实测旅行时间",
    ),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


missing = [str(path) for path, _, _ in FILES if not path.is_file()]
if missing:
    raise FileNotFoundError("Missing source files: " + "; ".join(missing))

manifest_rows = [
    {
        "archive_path": archive_path,
        "source_relative_path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "purpose": purpose,
    }
    for path, archive_path, purpose in FILES
]

manifest_lines = []
header = ["archive_path", "source_relative_path", "bytes", "sha256", "purpose"]
from io import StringIO

buffer = StringIO()
writer = csv.DictWriter(buffer, fieldnames=header, lineterminator="\n")
writer.writeheader()
writer.writerows(manifest_rows)
manifest_text = "\ufeff" + buffer.getvalue()

readme = """# CIQ GPT校验上传包

本包汇总了用户指定的三个归档和关键数据文件，便于一次上传给GPT继续校验。

## 文件结构

- `01_三个归档/`：V5.6订单归档、V5.3实验前置归档、Stage 2交付包。
- `02_关键数据/`：交通—气象联结、91个OD时间代理、ERA5天气、19个参考地点、A/B道路OD。
- `FILE_SHA256_MANIFEST.csv`：每个源文件的原始路径、大小、SHA256和用途。

## 解释边界

- 918,000行是30个种子的重采样合成订单，不是独立实测订单。
- `MODEL_PROXY_NOT_REAL`与`MODEL_NOT_OBSERVED`文件不是实测或外部校准旅行时间。
- 19个地点是参考锚点，不是已批准起降点。
- Stage 2结果属于诊断与质量门槛输出，正式30种子三模式主实验尚未放行。
"""

with ZipFile(OUTPUT, "w", allowZip64=True) as archive:
    for path, archive_path, _ in FILES:
        compression = ZIP_STORED if path.suffix.lower() == ".zip" else ZIP_DEFLATED
        archive.write(path, arcname=archive_path, compress_type=compression, compresslevel=9 if compression == ZIP_DEFLATED else None)
    archive.writestr("README_上传与解释说明.md", readme, compress_type=ZIP_DEFLATED, compresslevel=9)
    archive.writestr("FILE_SHA256_MANIFEST.csv", manifest_text, compress_type=ZIP_DEFLATED, compresslevel=9)

output_hash = sha256(OUTPUT)
HASH_FILE.write_text(f"{output_hash}  {OUTPUT.name}\n", encoding="utf-8")
print(f"ZIP={OUTPUT}")
print(f"FILES={len(FILES) + 2}")
print(f"BYTES={OUTPUT.stat().st_size}")
print(f"SHA256={output_hash}")
