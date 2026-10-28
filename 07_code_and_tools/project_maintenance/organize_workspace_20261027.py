from __future__ import annotations

import csv
import hashlib
import re
import urllib.parse
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_ROOT = Path(r"C:\Users\DELL\Desktop\CIQ 无人机物流 SCI 研_20261026").resolve()
if ROOT != EXPECTED_ROOT:
    raise RuntimeError(f"Refusing to organize unexpected root: {ROOT}")

LOG_DIR = ROOT / "00_项目说明" / "整理记录"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_CSV = LOG_DIR / "文件整理日志_20261027.csv"
SUMMARY_MD = LOG_DIR / "文件整理说明_20261027.md"
SELF = Path(__file__).resolve()
events: list[dict] = []


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def record(action: str, source: str, destination: str = "", sha256: str = "", note: str = ""):
    events.append({"action": action, "source": source, "destination": destination, "sha256": sha256, "note": note})


def canonical_score(path: Path) -> tuple:
    name = path.name
    text = rel(path)
    score = 0
    score += 1000 if "99_重复文件" not in path.parts else 0
    score += 300 if not re.search(r"\s\(\d+\)(?=\.[^.]+$)", name) else 0
    score += 300 if "重复副本" not in name and "副本" not in name else 0
    score += 100 if not re.search(r"%[0-9A-Fa-f]{2}", name) else 0
    score += 30 if len(path.parts) > 1 else 0
    return score, -len(text), text


# Phase 1: delete only byte-identical duplicates, retaining the best canonical path.
files = [path for path in ROOT.rglob("*") if path.is_file() and path.resolve() != SELF]
groups: dict[tuple[int, str], list[Path]] = defaultdict(list)
for path in files:
    groups[(path.stat().st_size, digest(path))].append(path)

duplicate_groups = 0
deleted_duplicate_bytes = 0
for (size, file_hash), members in groups.items():
    if len(members) < 2:
        continue
    duplicate_groups += 1
    canonical = max(members, key=canonical_score)
    for path in members:
        if path == canonical:
            continue
        source = rel(path)
        path.unlink()
        deleted_duplicate_bytes += size
        record("DELETE_EXACT_DUPLICATE", source, rel(canonical), file_hash, "byte-identical SHA256 duplicate")

# Phase 2: remove generated Python cache files/directories.
for path in sorted(ROOT.rglob("*.pyc")):
    if path.is_file():
        source = rel(path)
        path.unlink()
        record("DELETE_CACHE", source, "", "", "generated Python bytecode")
for directory in sorted((p for p in ROOT.rglob("__pycache__") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
    if not any(directory.iterdir()):
        directory.rmdir()

# Phase 3: decode percent-encoded filenames; do not overwrite different content.
for path in sorted((p for p in ROOT.rglob("*") if p.is_file()), key=lambda p: len(p.parts), reverse=True):
    decoded = urllib.parse.unquote(path.name).strip()
    if decoded == path.name:
        continue
    target = path.with_name(decoded)
    if target.exists():
        if target.is_file() and digest(target) == digest(path):
            source = rel(path)
            file_hash = digest(path)
            path.unlink()
            record("DELETE_DECODE_COLLISION_DUPLICATE", source, rel(target), file_hash, "decoded target already contains identical bytes")
            continue
        stem = target.stem + "_名称冲突"
        target = target.with_name(stem + target.suffix)
        counter = 2
        while target.exists():
            target = target.with_name(f"{stem}_{counter}{target.suffix}")
            counter += 1
    source = rel(path)
    path.rename(target)
    record("RENAME_URL_DECODE", source, rel(target), digest(target), "percent-encoded filename converted to readable Unicode")


def destination_for(name: str) -> Path | None:
    suffix = Path(name).suffix.lower()
    if name.startswith("CIQ_Codex_") or name == "README_先读.md":
        return ROOT / "00_项目说明" / "Codex说明" / name
    if name.startswith("A10_"):
        return ROOT / "09_其他资料" / "A10_文献审查" / name
    if name.startswith("CIQ_RQ1_M0_stage3") or name.startswith("CIQ_Stage3_"):
        return ROOT / "10_阶段实验成果" / "Stage3_RQ1_M0" / name
    if name.startswith("CIQ_RQ1_M0_B区") or name.startswith("CIQ_Stage4_") or name == "stage4_paired_orders.csv.gz":
        return ROOT / "10_阶段实验成果" / "Stage4_B区域_M1M2情景" / name
    if name.startswith("CIQ_Stage5_"):
        return ROOT / "10_阶段实验成果" / "Stage5_运营敏感性_成本碳排放" / name
    if name.startswith("CIQ_Stage6_") or name in {"README_STAGE6_CN.md", "run_stage6.py", "stage6_order_level.csv.gz"}:
        return ROOT / "10_阶段实验成果" / "Stage6_双区域多级接驳" / name
    if name in {
        "01_AB_24h_hourly_joint.csv",
        "01_AB_24h_weather_traffic_operation_gates.csv",
        "03_hourly_91_reference_OD_MODEL_PROXY_NOT_REAL.csv.gz",
        "04_seed_distribution_DESCRIPTIVE_NOT_EFFECT_CI.csv",
        "05_integrity_repeat_QA.csv",
        "E04_G1_CIQ_Traffic_ERA5_PILOT_2026_05_09.csv.gz",
    }:
        return ROOT / "02_基础与交通数据" / "联合与派生数据" / name
    if name == "E03_ERA5_JB_TWO_CIQ_WEATHER_HOURLY.csv":
        return ROOT / "04_天气数据" / "汇总数据" / name
    if name.endswith(".xlsx") and (name.startswith("E04_") or name.startswith("E05_") or name.startswith("JB_CIQ_24h_") or name.startswith("JB_CIQ_E03_E04_")):
        return ROOT / "05_审查与验收" / "实验与气象" / name
    if name.startswith("FIG_") and suffix == ".png":
        return ROOT / "06_图表与可视化" / "交通气象图" / name
    if name.startswith("ScreenShot_") and suffix == ".png":
        return ROOT / "06_图表与可视化" / "截图" / name
    if name.startswith("JB_CIQ_") and suffix == ".zip":
        return ROOT / "08_归档包" / "实验归档" / name
    return None


# Phase 4: move loose root files into the existing research hierarchy.
for path in sorted(p for p in ROOT.iterdir() if p.is_file() and p.resolve() != SELF):
    target = destination_for(path.name)
    if target is None:
        continue
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if digest(target) == digest(path):
            source = rel(path)
            file_hash = digest(path)
            path.unlink()
            record("DELETE_MOVE_COLLISION_DUPLICATE", source, rel(target), file_hash, "canonical destination already contains identical bytes")
            continue
        raise FileExistsError(f"Refusing to overwrite non-identical destination: {target}")
    source = rel(path)
    path.rename(target)
    record("MOVE_TO_CATEGORY", source, rel(target), digest(target), "organized root-level file")

# The organizer itself belongs with tooling after execution.
tool_target = ROOT / "07_代码与工具" / "项目维护" / SELF.name
tool_target.parent.mkdir(parents=True, exist_ok=True)
if tool_target.exists() and tool_target.resolve() != SELF:
    raise FileExistsError(tool_target)
if SELF != tool_target.resolve():
    source_self = rel(SELF)
    SELF.rename(tool_target)
    record("MOVE_TO_CATEGORY", source_self, rel(tool_target), digest(tool_target), "workspace maintenance script")

# Remove the duplicate-only hierarchy after verified duplicate deletion.
duplicate_root = ROOT / "99_重复文件"
if duplicate_root.exists():
    for directory in sorted((p for p in duplicate_root.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()
    if not any(duplicate_root.iterdir()):
        duplicate_root.rmdir()
        record("REMOVE_EMPTY_DIRECTORY", "99_重复文件", "", "", "all contained files were verified exact duplicates")

with LOG_CSV.open("w", newline="", encoding="utf-8-sig") as stream:
    writer = csv.DictWriter(stream, fieldnames=["action", "source", "destination", "sha256", "note"])
    writer.writeheader()
    writer.writerows(events)

counts = defaultdict(int)
for event in events:
    counts[event["action"]] += 1

SUMMARY_MD.write_text(
    f"""# 文件整理说明

执行日期：2026-10-27

## 处理原则

- 仅删除SHA256完全相同的重复文件；名称相似但内容不同的文件不删除。
- 优先保留无 `(1)/(2)` 后缀、非 `99_重复文件`、名称可读且路径正式的版本。
- URL百分号编码文件名转换为可读中文。
- 根目录散落文件按项目说明、基础数据、天气、验收、图表、归档、其他资料和阶段成果归位。
- 原始天气响应目录 `data/`、正式工程目录和 `outputs/` 内研究结果结构保持不变。

## 执行统计

- 重复内容组：{duplicate_groups}
- 删除的字节级重复文件：{counts['DELETE_EXACT_DUPLICATE'] + counts['DELETE_DECODE_COLLISION_DUPLICATE'] + counts['DELETE_MOVE_COLLISION_DUPLICATE']}
- 释放重复空间：{deleted_duplicate_bytes:,} bytes
- 删除Python缓存文件：{counts['DELETE_CACHE']}
- URL编码名称修正：{counts['RENAME_URL_DECODE']}
- 根目录文件归位：{counts['MOVE_TO_CATEGORY']}
- 详细路径、保留版本和SHA256见 `文件整理日志_20261027.csv`。
""",
    encoding="utf-8",
)

print("EVENTS", len(events))
print("DUPLICATE_GROUPS", duplicate_groups)
print("DELETED_DUPLICATE_BYTES", deleted_duplicate_bytes)
print("LOG", LOG_CSV)
