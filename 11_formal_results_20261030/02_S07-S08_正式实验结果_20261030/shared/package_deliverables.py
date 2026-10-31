#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DELIV = ROOT / "deliverables"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def stage_manifest(stage: Path):
    target = stage / "SHA256_MANIFEST.csv"
    rows = []
    for p in sorted(stage.rglob("*")):
        if p.is_file() and p != target and "__pycache__" not in p.parts:
            rows.append({"relative_path": p.relative_to(stage).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)})
    with target.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["relative_path", "bytes", "sha256"]); w.writeheader(); w.writerows(rows)
    return rows


def make_zip(stage: Path, name: str):
    target = DELIV / name
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for p in sorted(stage.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                z.write(p, arcname=f"{stage.name}/{p.relative_to(stage).as_posix()}")
    with zipfile.ZipFile(target) as z:
        bad = z.testzip(); members = len(z.infolist())
    if bad:
        raise RuntimeError(f"bad zip member {bad}")
    return target, members


def main():
    DELIV.mkdir(parents=True, exist_ok=True)
    s07 = json.loads((ROOT / "S07" / "qa" / "S07_SUMMARY.json").read_text(encoding="utf-8"))
    s08 = json.loads((ROOT / "S08" / "data" / "S08_SUMMARY.json").read_text(encoding="utf-8"))
    scenarios = pd.read_csv(ROOT / "S08" / "data" / "S08_SCENARIO_SUMMARY.csv")
    weather = pd.read_csv(ROOT / "S07" / "data" / "QA_WEATHER_MONTHLY.csv")
    validation = pd.read_csv(ROOT / "S08" / "data" / "S08_SMALL_EXACT_ALGORITHM_VALIDATION.csv")
    km_gap = float((validation["heuristic_km"] / validation["exact_km"] - 1).mean())
    late_gap = float((validation["heuristic_late_minutes"] - validation["exact_late_minutes"]).mean())

    s08_report = f"""# S08 汽油车 M0 条件性基线审计报告

- 裁定：**{s08['status']}**，不是已验证的实际车队运营结果。
- 场景：{s08['scenarios']:,}；订单：{s08['orders']:,}；完成：{s08['completed']:,}（{s08['completion_rate']:.4%}）。
- 准时：{s08['on_time']:,}（以全部订单为分母 {s08['on_time_rate_all_orders']:.4%}）。
- 车辆公里：{s08['vehicle_km']:,.3f} km；汽油：{s08['fuel_litres']:,.3f} L。
- TTW CO₂：{s08['ttw_co2_kg']:,.3f} kg；该值不是 WTW/LCA，也不冒充完整非 CO₂ 温室气体 CO₂e。
- 条件性运营成本：MYR {s08['operating_cost_MYR']:,.2f}。
- 物理行程段：{s08['physical_legs']:,}；每段只核算一次，不按共享订单重复乘算油耗。
- 小规模精确对照：10个三订单/单车算例；多起点启发式平均车公里高于精确解 {km_gap:.2%}，平均多迟到 {late_gap:.2f} 分钟。该差距作为算法局限保留，不宣称全局最优。

## 参数与证据

参数、单位、官方来源和 `SCENARIO_ASSUMPTION` 标签见 `PARAMETER_SOURCE_MATRIX.csv`。主情景采用 IPCC 代表性 10 km/L（10 L/100 km），不是柔佛实测车队油耗。油价按马来西亚 data.gov.my 周度 RON95 非补贴价格；BUDI95/SKPS 仅作资格未验证的成本敏感性。

## 科学限制

- 当前 OSM 提取不是2026年5—9月逐时历史路网快照。
- 21/68节点距主强连通道路候选超过100 m；全部场站道路入口与许可均未验证。
- FCD无方向，速度单位也仅依据 TomTom 默认作条件性 km/h 解释；缺失/非正速度使用明确记录的中位数回退。
- 车种、容量、3辆车、A01/B06/C02仓点、服务时间、人工和维护费含显著情景假设。
- 多起点启发式明显优于被弃用的单策略结果，但小规模精确对照仍显示最优性差距。
- 因此结果只可用于后续同边界的条件性 M0/M1/M2 比较，不可表述为实际企业运营或已证明无人机减排。
"""
    (ROOT / "S08" / "S08_SCI_AUDIT_REPORT_CN.md").write_text(s08_report, encoding="utf-8")

    combined = f"""# CIQ V5 S07→S08 联合交接（2026-10-30）

## S07

- G07-W：{s07['gates']['G07-W']}；五个月 Weather_Hourly {s07['weather_rows']:,}行，ERA5边界行 {s07['era5_boundary_rows']:,}。
- FCD：{s07['fcd']['rows']:,}行；正速度 {s07['fcd']['positive_speed']:,}、缺失 {s07['fcd']['missing_speed']:,}、非正 {s07['fcd']['nonpositive_speed']:,}。
- V5：68节点（A=29、B=10、C=29），节点—小时 {s07['weather_node_hour_rows']:,}；距天气网格>10 km节点 {s07['weather_nodes_gt10km']}。
- 道路：当前 OSM {s07['road']['graph_nodes']:,}节点/{s07['road']['graph_directed_arcs']:,}有向弧；68节点均保留，其中>100 m接入候选 {s07['road']['nodes_over_100m']}。
- G07-R：{s07['gates']['G07-R']}；G07-INTEGRATION：{s07['gates']['G07-INTEGRATION']}；82,620订单、4,590场景全部保留。
- S07总裁定：**{s07['gates']['S07']}**。

## S08

- 裁定：**{s08['status']}**；证据等级：`{s08['model_evidence']}`。
- {s08['scenarios']:,}场景、{s08['orders']:,}订单；完成率 {s08['completion_rate']:.4%}，全部订单准时率 {s08['on_time_rate_all_orders']:.4%}。
- 车辆公里 {s08['vehicle_km']:,.3f} km；汽油 {s08['fuel_litres']:,.3f} L；TTW CO₂ {s08['ttw_co2_kg']:,.3f} kg。
- 条件性运营成本 MYR {s08['operating_cost_MYR']:,.2f}。
- 排放边界是汽油燃烧 CO₂，不是完整 WTW/LCA CO₂e。

## 下一阶段门槛

本次没有运行 S09/S10。只有在后续接受上述条件性道路/天气代理，或补齐场站入口、方向交通、历史路网和本地车队参数后，才可决定是否运行历史天气驱动的 S09 与五模式 S10。不能依据本次汽油车结果单独宣称无人机必然减排。
"""
    handoff = DELIV / "S07_S08_COMBINED_HANDOFF_CN.md"
    handoff.write_text(combined, encoding="utf-8")

    stage_manifest(ROOT / "S07"); stage_manifest(ROOT / "S08")
    z07, n07 = make_zip(ROOT / "S07", "CIQ_V5_S07_REAL_DATA_FUSION_COMPLETE.zip")
    z08, n08 = make_zip(ROOT / "S08", "CIQ_V5_S08_PETROL_M0_BASELINE_COMPLETE.zip")
    rows = [
        {"file": z07.name, "bytes": z07.stat().st_size, "sha256": sha(z07), "zip_members": n07, "zip_test": "PASS"},
        {"file": z08.name, "bytes": z08.stat().st_size, "sha256": sha(z08), "zip_members": n08, "zip_test": "PASS"},
        {"file": handoff.name, "bytes": handoff.stat().st_size, "sha256": sha(handoff), "zip_members": "", "zip_test": "N/A"},
    ]
    with (DELIV / "SHA256_MANIFEST.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

    # Extract each archive into a fresh temporary directory and verify every
    # packaged file listed by its embedded manifest.
    extraction = []
    with tempfile.TemporaryDirectory(prefix="ciq_zip_verify_") as temp:
        for zpath in (z07, z08):
            target = Path(temp) / zpath.stem
            with zipfile.ZipFile(zpath) as z: z.extractall(target)
            manifests = list(target.rglob("SHA256_MANIFEST.csv"))
            if len(manifests) != 1:
                raise RuntimeError(f"{zpath.name}: expected one embedded manifest, found {len(manifests)}")
            manifest_path = manifests[0]
            stage_root = manifest_path.parent
            manifest_rows = pd.read_csv(manifest_path)
            mismatches = []
            for row in manifest_rows.itertuples(index=False):
                packaged = stage_root / str(row.relative_path)
                if (not packaged.is_file() or packaged.stat().st_size != int(row.bytes)
                        or sha(packaged).lower() != str(row.sha256).lower()):
                    mismatches.append(str(row.relative_path))
            if mismatches:
                raise RuntimeError(f"{zpath.name}: extracted manifest mismatches: {mismatches[:5]}")
            extraction.append({"zip": zpath.name, "fresh_extract": "PASS",
                               "embedded_manifest_count": 1,
                               "manifest_files_verified": len(manifest_rows),
                               "manifest_mismatches": 0,
                               "extracted_files": sum(p.is_file() for p in target.rglob("*"))})
    (DELIV / "ZIP_FRESH_EXTRACTION_TEST.json").write_text(json.dumps(extraction, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"S07_zip": str(z07), "S08_zip": str(z08), "manifest": rows, "fresh_extract": extraction}, ensure_ascii=False))


if __name__ == "__main__":
    main()
