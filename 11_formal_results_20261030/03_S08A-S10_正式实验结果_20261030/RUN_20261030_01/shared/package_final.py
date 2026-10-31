from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

import pandas as pd


RUN = Path(__file__).resolve().parents[1]
FINAL = RUN / "FINAL_HANDOFF"
RUN_ID = RUN.name


def sha(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def excluded(path: Path, stage: Path):
    rel = path.relative_to(stage)
    return ("__pycache__" in rel.parts or "deliverables" in rel.parts or
            (stage.name == "S10" and ("chunks" in rel.parts or "sample_test" in rel.parts)))


def manifest(stage: Path):
    target = stage / "SHA256_MANIFEST.csv"
    rows = []
    for p in sorted(stage.rglob("*")):
        if p.is_file() and p != target and not excluded(p, stage):
            rows.append({"relative_path": p.relative_to(stage).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)})
    with target.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    return rows


def zip_stage(stage: Path, name: str):
    target = stage / "deliverables" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for p in sorted(stage.rglob("*")):
            if p.is_file() and not excluded(p, stage):
                z.write(p, f"{stage.name}/{p.relative_to(stage).as_posix()}")
    with zipfile.ZipFile(target) as z:
        bad = z.testzip(); members = len(z.infolist())
    if bad:
        raise RuntimeError(bad)
    return target, members


def verify_extract(zpath: Path):
    with tempfile.TemporaryDirectory(prefix="ciq_s08a_s10_verify_") as tmp:
        root = Path(tmp)
        with zipfile.ZipFile(zpath) as z:
            z.extractall(root)
        manifests = list(root.rglob("SHA256_MANIFEST.csv"))
        if len(manifests) != 1:
            raise RuntimeError(f"{zpath}: manifests={len(manifests)}")
        mp = manifests[0]; base = mp.parent; rows = pd.read_csv(mp); mismatch = []
        for row in rows.itertuples(index=False):
            p = base / str(row.relative_path)
            if not p.is_file() or p.stat().st_size != int(row.bytes) or sha(p).lower() != str(row.sha256).lower():
                mismatch.append(str(row.relative_path))
        return {"zip": zpath.name, "fresh_extract": "PASS" if not mismatch else "FAIL",
                "manifest_files_verified": len(rows) - len(mismatch), "manifest_mismatches": len(mismatch),
                "extracted_files": sum(p.is_file() for p in root.rglob("*"))}


def main():
    FINAL.mkdir(parents=True, exist_ok=True)
    s08g = json.loads((RUN / "S08A/qa/S08A_GATES.json").read_text(encoding="utf-8"))
    s09s = json.loads((RUN / "S09/data/S09_SUMMARY.json").read_text(encoding="utf-8"))
    s10s = json.loads((RUN / "S10/data/S10_SUMMARY.json").read_text(encoding="utf-8"))
    mode = pd.read_csv(RUN / "S10/data/S10_MODE_SUMMARY.csv")
    status = {
        "S08A": f"{s08g['COMPUTATION_STATUS']}/{s08g['SCI_EVIDENCE_STATUS']}",
        "S09_PREFLIGHT": "PASS", "S09_FULL_RUN": s09s["gates"]["S09_FULL_CONDITIONAL_RUN"],
        "S10_PREFLIGHT": s10s["gates"]["S10_PREFLIGHT"],
        "S10_FULL_RUN": s10s["gates"]["S10_FULL_RUN"],
        "S10_SCI_CARBON_CLAIM": s10s["gates"]["S10_SCI_CARBON_CLAIM"],
    }
    (FINAL / "FINAL_STATUS_MATRIX.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    m0 = mode.set_index("mode").loc["M0_PETROL"]
    lines = ["# CIQ V5 S08A→S09→S10 最终交接", "", "## 状态", "",
             *[f"- {k}: `{v}`" for k, v in status.items()], "", "## 五模式全量结果", ""]
    for row in mode.itertuples(index=False):
        ghg_pct = (row.operational_energy_ghg_kg_scenario / m0.operational_energy_ghg_kg_scenario - 1) * 100
        cost_pct = (row.operating_cost_MYR_partial / m0.operating_cost_MYR_partial - 1) * 100
        lines.append(f"- {row.mode}: 完成率 {row.completion_rate:.4%}，准时率 {row.on_time_rate_all_orders:.4%}，"
                     f"车辆 {row.vehicle_km:,.3f} km，燃油 {row.fuel_litres:,.3f} L，电网输入 {row.grid_input_kwh:,.3f} kWh，"
                     f"条件性运营能源GHG {row.operational_energy_ghg_kg_scenario:,.3f} kg（相对M0 {ghg_pct:+.2f}%），"
                     f"部分OPEX MYR {row.operating_cost_MYR_partial:,.2f}（相对M0 {cost_pct:+.2f}%）。")
    lines += ["", "## 可写与不可写", "",
              "可以写：在冻结合成任务、历史天气/交通代理和明确资源情景下，M2条件性模型的服务与运营能源指标优于本M0代理。",
              "不能写：无人机实际获批、实机能耗已标定、已证明WTW/LCA净减排、完整成本最优或可直接部署。",
              "Wingcopter任务kWh、空域/场地、资本/电池折旧和对称生命周期边界仍为HOLD；M1/M2结果高度依赖这些假设。",
              "", "## 主要模型边界", "",
              "M1使用11个条件性固定发射节点和三车地面回退；M2使用三车三机，车辆实际到发射点并等待同点回收。",
              "混合模式道路出发时间按小时FCD缓存；M1地面回退使用单一BATCH_PICKUPS策略，算法预算与冻结M0不完全相同。",
              "排放列是汽油燃烧TTW CO2加2024马来半岛临时电网运营GHG，不是WTW或LCA；成本是部分OPEX。"]
    (FINAL / "FINAL_HANDOFF_CN.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    for stage in (RUN / "S08A", RUN / "S09", RUN / "S10"):
        manifest(stage)
    zips = []
    for stage, name in [
        (RUN / "S08A", f"CIQ_V5_S08A_M0_RECONCILIATION_{RUN_ID}.zip"),
        (RUN / "S09", f"CIQ_V5_S09_UAV_MISSION_SIMULATION_{RUN_ID}.zip"),
        (RUN / "S10", f"CIQ_V5_S10_FIVE_MODE_COMPARISON_{RUN_ID}.zip")]:
        z, members = zip_stage(stage, name); zips.append((z, members))

    package = FINAL / "HANDOFF_PACKAGE"
    if package.exists():
        shutil.rmtree(package)
    package.mkdir()
    selected = [RUN / "README_CN.md", RUN / "requirements.txt", RUN / "STAGE_DEPENDENCIES.json",
                FINAL / "FINAL_STATUS_MATRIX.json", FINAL / "FINAL_HANDOFF_CN.md", FINAL / "FULL_TEST_LOG.txt",
                RUN / "S08A/reports/S08A_BASELINE_RECONCILIATION_CN.md", RUN / "S08A/qa/S08A_GATES.json",
                RUN / "S09/reports/S09_SCI_AUDIT_REPORT_CN.md", RUN / "S09/data/S09_SUMMARY.json",
                RUN / "S09/data/S09_PARAMETER_EVIDENCE_MATRIX.csv", RUN / "S09/qa/S09_GATES.json",
                RUN / "S10/reports/S10_SCI_AUDIT_REPORT_CN.md", RUN / "S10/data/S10_SUMMARY.json",
                RUN / "S10/data/S10_MODE_SUMMARY.csv", RUN / "S10/data/S10_PAIRED_STATISTICS.csv",
                RUN / "S10/qa/S10_GATES.json", RUN / "S10/qa/S10_INVARIANTS.json"]
    for p in selected:
        shutil.copy2(p, package / p.name)
    manifest(package)
    handoff_zip, members = zip_stage(package, f"CIQ_V5_S08A_S09_S10_HANDOFF_{RUN_ID}.zip")
    final_handoff_zip = FINAL / handoff_zip.name
    shutil.copy2(handoff_zip, final_handoff_zip)
    zips.append((final_handoff_zip, members))

    verification = [verify_extract(z) for z, _ in zips]
    rows = [{"file": str(z), "bytes": z.stat().st_size, "sha256": sha(z), "zip_members": members,
             "zip_crc": "PASS", "fresh_extract": verification[i]["fresh_extract"],
             "manifest_verified": verification[i]["manifest_files_verified"],
             "manifest_mismatches": verification[i]["manifest_mismatches"]}
            for i, (z, members) in enumerate(zips)]
    with (FINAL / "DELIVERABLE_SHA256.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    (FINAL / "ZIP_FRESH_EXTRACTION_TEST.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "deliverables": rows, "verification": verification}, ensure_ascii=False))


if __name__ == "__main__":
    main()
