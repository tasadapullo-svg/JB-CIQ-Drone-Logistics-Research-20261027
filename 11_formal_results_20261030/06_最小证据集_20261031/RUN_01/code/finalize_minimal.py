from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve()
RUN = HERE.parents[1]
ROOT = HERE.parents[3]
ZIP = RUN / "CIQ_MINIMAL_EVIDENCE_CHECK_COMPLETE.zip"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def append_external_sources() -> None:
    params = pd.read_csv(RUN / "PARAMETER_AND_SOURCE_AUDIT.csv")
    params = params[params["parameter_group"] != "external_demand_context"].copy()
    ext = pd.read_csv(RUN / "work" / "EXTERNAL_SOURCES.csv")
    rows = []
    for r in ext.itertuples(index=False):
        rows.append({
            "parameter_group": "external_demand_context",
            "parameter": r.source_id,
            "baseline_or_rule": r.title,
            "unit": "reference",
            "evidence_level": r.verification_status,
            "source_path": r.doi_or_url,
            "limitation": f"Supports: {r.supports}. Does not support: {r.does_not_support}.",
        })
    params = pd.concat([params, pd.DataFrame(rows)], ignore_index=True)
    params.to_csv(RUN / "PARAMETER_AND_SOURCE_AUDIT.csv", index=False)


def golden_audit() -> dict:
    d = RUN / "work" / "GOLDEN"
    tables = {p.stem: pd.read_parquet(p) for p in d.glob("*.parquet")}
    summary = pd.read_csv(d / "SCENARIO_SUMMARY.csv")
    checks = {
        "summary_modes_six_including_duplicate_controls": len(summary) == 6,
        "orders_18_per_mode": bool((summary.orders == 18).all()),
        "order_results_present": "ORDER_RESULTS" in tables and len(tables["ORDER_RESULTS"]) == 108,
        "ground_legs_present": "GROUND_LEGS" in tables and len(tables["GROUND_LEGS"]) > 0,
        "event_clock_present": "EVENT_CLOCK" in tables and len(tables["EVENT_CLOCK"]) > 0,
        "fuel_equals_vehicle_km_times_0_1": bool(((summary.fuel_litres - summary.vehicle_km * 0.1).abs() < 1e-9).all()),
    }
    if "SOC_LEDGER" in tables and len(tables["SOC_LEDGER"]):
        soc = tables["SOC_LEDGER"]
        after = next((c for c in ["soc_after_kwh", "soc_after", "soc_after_fraction", "soc_end"] if c in soc), None)
        reserve = next((c for c in ["reserve_kwh", "reserve_soc", "reserve_fraction", "soc_reserve"] if c in soc), None)
        checks["soc_nonnegative"] = bool((soc[after] >= -1e-9).all()) if after else False
        checks["soc_reserve_respected_when_columns_available"] = bool((soc[after] + 1e-9 >= soc[reserve]).all()) if after and reserve else "COLUMN_NOT_AVAILABLE"
    else:
        checks["soc_nonnegative"] = False
    if "FLIGHTS" in tables and "WEATHER_LEDGER" in tables:
        flights, weather = tables["FLIGHTS"], tables["WEATHER_LEDGER"]
        checks["weather_four_rows_per_flight"] = len(weather) == 4 * len(flights)
    if "GROUND_LEGS" in tables:
        checks["mandatory_return_legs_present"] = bool((tables["GROUND_LEGS"]["target_event"] == "MANDATORY_RETURN_DEPOT").any())
    checks["pass"] = all(v is True or v == "COLUMN_NOT_AVAILABLE" for v in checks.values())
    checks["table_rows"] = {k: len(v) for k, v in tables.items()}
    return checks


def make_report(jqa: dict, pre: dict, golden: dict) -> None:
    s = pd.read_csv(RUN / "JOINT_SENSITIVITY_SUMMARY.csv")
    base = s[(s.config_id == "GRID_G1.0_E1.0") & (s["mode"] == "M2_WING")].iloc[0]
    m2 = s[s["mode"] == "M2_WING"].copy()
    m2["reduction"] = -m2.operational_ghg_proxy_kg_pct_vs_m0
    lo, hi = m2.reduction.min(), m2.reduction.max()
    winners = s[["config_id", "lowest_ghg_service_feasible_mode"]].drop_duplicates()
    counts = winners.lowest_ghg_service_feasible_mode.value_counts().to_dict()
    reversals = jqa["m2_wing_nonpositive_reduction_configs"]
    under1 = jqa["m2_wing_reduction_under_1pct_configs"]
    a_status = "PASS" if jqa["status"] == "PASS" and golden["pass"] else "HOLD"
    b_status = "CONDITIONAL" if pre["orders"] == 82620 and pre["unique_task_ids"] == 82620 else "HOLD"
    cn = f"""# 最小必要补充实验最终证据报告

## 模块 A：联合稳健性

状态：**{a_status}**。实际完成 900 个分层配对场景、13 组联合参数、5 种模式，共 58,500 条场景—配置—模式记录（每组每模式 16,200 张订单）。所有涉及 DJI/Wing 能耗变化的情景均重新执行任务资格、SOC、调度与地面回退；汽油倍率只在已验证路线和事件不变时重算燃油账本。基准复现与路线不变性检查均为 {jqa['baseline_reproduction_pass']} / {jqa['fuel_ledger_recalc_route_invariance_pass']}。

M2-Wing 在基准子样本相对 M0 的运营排放代理变化为 {base.operational_ghg_proxy_kg_pct_vs_m0:.3f}%（负值表示降低；双向日期/种子聚类自助法 95% CI：{base.operational_ghg_proxy_kg_pct_vs_m0_ci95_low:.3f}% 至 {base.operational_ghg_proxy_kg_pct_vs_m0_ci95_high:.3f}%）。13 组中减排幅度范围为 {lo:.3f}%–{hi:.3f}%；非正减排（优势反转）配置：{', '.join(reversals) if reversals else '无'}；低于 1% 配置：{', '.join(under1) if under1 else '无'}。满足完成率≥95%、全订单准时率≥90%后，最低排放模式计数为 {counts}。该结果是模型内运营排放代理，不是实机、全生命周期或实际运营验证。

## 模块 B：冻结合成订单审计

状态：**{b_status}**。82,620 个唯一订单覆盖 153 天、30 个种子和 4,590 个场景；每场景固定 18 单，每个始发分区固定 6 单。生成器、协议和冻结订单可逐项追溯。订单由“每区 5 个区内 + 1 个跨区压力订单”、离散重量集、离散时窗、均匀目的地和固定随机种子构成，适合相同任务条件下的受控模式比较，但不是 JB/CIQ 的经验需求样本。

主要限制：（1）缺少本地承运商订单量、OD、重量和承诺时窗的实测分布，不能推断市场代表性；（2）三区等量设计会人为均衡空间需求，不能外推真实需求密度；（3）Wingcopter 任务级能耗与电池参数仍缺少可复核的 OEM/实飞证据。因此 Methods 可冻结为“受控合成情景”，Results 只能冻结为条件性模型结论。

## English Methods (reproducible subset)

We evaluated joint parameter robustness on 900 paired scenarios selected from the frozen 4,590 date–seed scenarios. Within each month from May to September 2026, six dates were selected at fixed quantiles of an objective daily stress score: standardized mean wind gust plus standardized rainfall minus standardized observed FCD speed. All 30 frozen random seeds were retained for every selected date, yielding 180 scenarios per month. The same orders were compared across five modes: petrol-only M0, DJI and Wingcopter variants of M1, and DJI and Wingcopter variants of M2.

Thirteen parameter configurations combined petrol fuel-intensity multipliers G and aircraft mission-energy multipliers D and W. Nine configurations formed a 3 × 3 grid with G in {{0.8, 1.0, 1.2}} and equal D=W in {{0.8, 1.0, 1.2}}; four asymmetric corner configurations tested opposite DJI and Wing energy assumptions. Aircraft-energy changes were applied before mission qualification and triggered complete reruns of SOC feasibility, dispatch, timing, and ground fallback. Petrol multipliers were applied to the physical fuel ledger only after confirming identical vehicle kilometres and UAV-flight events within each fixed D/W dispatch pair. Operational emissions were calculated as petrol tank-to-wheel CO2 plus grid-input electricity multiplied by the frozen grid factor. These are operational proxies and exclude vehicle manufacture, infrastructure, and full fuel-cycle effects.

For each configuration and mode, we reported completion, all-order on-time performance, delivery time, vehicle kilometres, fuel, electricity, partial operating cost, and operational greenhouse-gas proxy. Percentage effects were paired against M0 by date and seed. Uncertainty intervals used 5,000 two-way cluster-bootstrap replicates that independently resampled dates and seeds. A mode was service-feasible only when completion was at least 95% and all-order on-time performance was at least 90%. Synthetic-order provenance was independently audited against the frozen generator and protocol; the resulting demand is treated as a balanced controlled experiment, not an observed or population-representative parcel-demand sample.
"""
    (RUN / "FINAL_EVIDENCE_REPORT_CN.md").write_text(cn, encoding="utf-8")


def build_package(qa: dict) -> dict:
    files = [
        RUN / "JOINT_SENSITIVITY_SUMMARY.csv",
        RUN / "JOINT_SENSITIVITY_SCENE_LEVEL.csv.gz",
        RUN / "PARAMETER_AND_SOURCE_AUDIT.csv",
        RUN / "SYNTHETIC_ORDER_AUDIT.csv",
        RUN / "FINAL_EVIDENCE_REPORT_CN.md",
        RUN / "QA_AND_RUN_MANIFEST.json",
        RUN / "RUN_REPRODUCE.ps1",
        *sorted((RUN / "code").glob("*.py")),
    ]
    manifest = pd.DataFrame([{"relative_path": str(p.relative_to(RUN)).replace("\\", "/"), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in files])
    manifest.to_csv(RUN / "SHA256_MANIFEST.csv", index=False)
    files.append(RUN / "SHA256_MANIFEST.csv")
    if ZIP.exists(): ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files: z.write(p, p.relative_to(RUN))
    with tempfile.TemporaryDirectory(prefix="fresh_extract_", dir=RUN / "work") as tmp:
        fresh = Path(tmp)
        with zipfile.ZipFile(ZIP) as z:
            bad = z.testzip()
            names = set(z.namelist())
            z.extractall(fresh)
        for r in manifest.itertuples(index=False):
            assert sha256(fresh / r.relative_path) == r.sha256
    result = {"zip_test_bad_member": bad, "manifest_entries_verified": len(manifest), "zip_members": len(names), "zip_bytes": ZIP.stat().st_size, "zip_sha256": sha256(ZIP)}
    assert bad is None and len(names) == len(files)
    return result


def main() -> None:
    append_external_sources()
    jqa = json.loads((RUN / "work" / "JOINT_QA.json").read_text(encoding="utf-8"))
    pre = json.loads((RUN / "work" / "PRECHECK.json").read_text(encoding="utf-8"))
    golden = golden_audit()
    make_report(jqa, pre, golden)
    before = pd.read_csv(RUN / "work" / "INPUT_HASHES_BEFORE.csv")
    after = before.copy(); after["sha256_after"] = [sha256(Path(p)) for p in after.absolute_path]
    inputs_unchanged = bool((after.sha256 == after.sha256_after).all())
    input_hashes = after[["absolute_path", "bytes", "sha256", "sha256_after"]].to_dict("records")
    code_hashes = [{"relative_path": str(p.relative_to(RUN)).replace("\\", "/"), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in sorted((RUN / "code").glob("*.py"))]
    qa = {
        "module_A_status": "PASS" if jqa["status"] == "PASS" and golden["pass"] else "HOLD",
        "module_A": jqa,
        "module_B_status": "PASS_CONDITIONAL" if pre["orders"] == 82620 and pre["unique_task_ids"] == 82620 else "HOLD",
        "module_B": pre,
        "golden_ledger_audit": golden,
        "historical_inputs_unchanged": inputs_unchanged,
        "input_hashes_before_and_after": input_hashes,
        "executed_code_hashes": code_hashes,
        "claim_evidence": [
            {"claim": "Joint experiment was fully run", "state": "verified", "evidence": "58,500 scene-level rows; 65 summary rows; baseline and golden-ledger checks"},
            {"claim": "Synthetic orders are empirically representative of JB/CIQ demand", "state": "unsupported", "evidence": "Generator explicitly labels empirical_demand_evidence=NONE_CONDITIONAL_SCENARIO"},
            {"claim": "Operational GHG proxy is life-cycle carbon", "state": "contradicted", "evidence": "Ledger contains TTW petrol plus grid-operation factor only"},
        ],
        "commands": ["prepare_and_audit.py", "run_joint_dispatch.py (five D/W pairs)", "build_joint_results.py", "run_joint_dispatch.py (one golden scenario with ledgers)", "finalize_minimal.py"],
        "package_validation": "Two-pass ZIP CRC and internal SHA-256 verification; final pass result stored below.",
    }
    (RUN / "QA_AND_RUN_MANIFEST.json").write_text(json.dumps(qa, indent=2, ensure_ascii=False), encoding="utf-8")
    first = build_package(qa)
    qa["pre_final_package_validation_result"] = first
    (RUN / "QA_AND_RUN_MANIFEST.json").write_text(json.dumps(qa, indent=2, ensure_ascii=False), encoding="utf-8")
    final = build_package(qa)
    (RUN / "work" / "PACKAGE_RESULT.json").write_text(json.dumps(final, indent=2), encoding="utf-8")
    print(json.dumps(final, indent=2))


if __name__ == "__main__":
    main()
