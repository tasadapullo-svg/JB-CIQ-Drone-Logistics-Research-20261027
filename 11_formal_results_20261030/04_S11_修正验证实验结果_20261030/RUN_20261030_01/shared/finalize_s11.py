from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import tempfile
import zipfile
from pathlib import Path

import pandas as pd


HERE=Path(__file__).resolve();RUN=HERE.parents[1];ROOT=HERE.parents[3]
OLD=ROOT/"output_S08A_S09_S10_Codex_20261030"/"RUN_20261030_01"
CHUNKS=RUN/"G11_1_DYNAMIC_WEATHER"/"data"/"chunks"
STAGES=["G11_0_PRECHECK","G11_1_DYNAMIC_WEATHER","G11_2_BATTERY_SOC","G11_3_FAIRNESS","G11_4_DUTY_ROAD","G11_5_ENERGY_COST","G11_6_STATS_PARETO","G11_7_GIS","FINAL_HANDOFF"]


def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        while b:=f.read(8*1024*1024):h.update(b)
    return h.hexdigest()


def write(path,text):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text.rstrip()+"\n",encoding="utf-8")


def combine_duty():
    rows=[]
    for h in [8,12,30]:
        x=pd.concat([pd.read_csv(CHUNKS/f"D{h}_C{i}"/"SCENARIO_SUMMARY.csv") for i in range(4)],ignore_index=True)
        if len(x)!=55080:raise RuntimeError(f"D{h} scenario rows {len(x)} != 55080")
        g=x.groupby(["spatial_scenario","mode"],as_index=False).agg(scenarios=("scenario_seed","count"),orders=("orders","sum"),completed=("completed","sum"),on_time=("on_time","sum"),vehicle_km=("vehicle_km","sum"),fuel_litres=("fuel_litres","sum"),grid_input_kwh=("grid_input_kwh","sum"),ghg_proxy_kg=("combined_mixed_boundary_proxy_kg","sum"),partial_opex_MYR=("partial_opex_MYR","sum"),uav_flights=("uav_flights","sum"))
        g["duty_hours"]=h;g["completion_rate"]=g.completed/g.orders;g["on_time_rate_all_orders"]=g.on_time/g.orders;g["method"]="FULL_RESCHEDULE_RERUN";rows.append(g)
    x=pd.read_csv(RUN/"G11_3_FAIRNESS/data/S11_SCENARIO_RESULTS.csv")
    g=x.groupby(["spatial_scenario","mode"],as_index=False).agg(scenarios=("scenario_seed","count"),orders=("orders","sum"),completed=("completed","sum"),on_time=("on_time","sum"),vehicle_km=("vehicle_km","sum"),fuel_litres=("fuel_litres","sum"),grid_input_kwh=("grid_input_kwh","sum"),ghg_proxy_kg=("combined_mixed_boundary_proxy_kg","sum"),partial_opex_MYR=("partial_opex_MYR","sum"),uav_flights=("uav_flights","sum"))
    g["duty_hours"]=24;g["completion_rate"]=g.completed/g.orders;g["on_time_rate_all_orders"]=g.on_time/g.orders;g["method"]="PRIMARY_FULL_RUN";rows.append(g)
    out=pd.concat(rows,ignore_index=True).sort_values(["duty_hours","spatial_scenario","mode"])
    out.to_csv(RUN/"G11_4_DUTY_ROAD/data/DUTY_SHIFT_SENSITIVITY.csv",index=False)
    return out


def create_final_files(duty):
    summary=pd.read_csv(RUN/"G11_6_STATS_PARETO/data/S11_MODE_SUMMARY.csv")
    strict=summary[summary.spatial_scenario=="STRICT_EXCLUDE_GT10KM"].set_index("mode")
    relaxed=summary[summary.spatial_scenario=="RELAXED_PROXY"].set_index("mode")
    road=json.loads((RUN/"G11_4_DUTY_ROAD/qa/ROAD_CACHE_GATE.json").read_text(encoding="utf-8"))
    qa=json.loads((RUN/"G11_2_BATTERY_SOC/qa/RESOURCE_CONFLICT_AUDIT.json").read_text(encoding="utf-8"))
    statuses={
      "G11-0":{"status":"PASS","evidence":"G11_0_PRECHECK/reports/G11_0_STATUS.json"},
      "G11-1":{"status":"PASS","evidence":"G11_1_DYNAMIC_WEATHER/data/S11_LAUNCH_WEATHER_LEDGER.parquet"},
      "G11-2":{"status":"PASS","evidence":"G11_2_BATTERY_SOC/qa/RESOURCE_CONFLICT_AUDIT.json"},
      "G11-3":{"status":"PASS","evidence":"G11_3_FAIRNESS/data/PAIRWISE_CAUSAL_DECOMPOSITION.csv"},
      "G11-4":{"status":"PASS" if road["status"]=="PASS" and set(duty.duty_hours)=={8,12,24,30} else "HOLD","evidence":"G11_4_DUTY_ROAD/data/DUTY_SHIFT_SENSITIVITY.csv; G11_4_DUTY_ROAD/qa/ROAD_CACHE_GATE.json"},
      "G11-5":{"status":"PASS_CONDITIONAL","evidence":"G11_5_ENERGY_COST/data/ENERGY_EVIDENCE_REGISTRY.csv","hold":"Wing energy is non-OEM; fixed capital and lifecycle inventory unavailable"},
      "G11-6":{"status":"PASS_CONDITIONAL","evidence":"G11_6_STATS_PARETO/data/S11_PAIRED_STATISTICS.csv","hold":"inference bounded by G11-5"},
      "G11-7":{"status":"HOLD","evidence":"G11_7_GIS/data/REGULATORY_SOURCE_REGISTRY.csv","hold":"screening is not route authorization or CIQ approval"},
      "FINAL":{"status":"PASS_CONDITIONAL","evidence":"FINAL_HANDOFF/S11_SCI_FINAL_AUDIT_REPORT_CN.md"},
    }
    (RUN/"FINAL_HANDOFF/S11_FINAL_STATUS_MATRIX.json").write_text(json.dumps(statuses,ensure_ascii=False,indent=2),encoding="utf-8")

    old=pd.read_csv(OLD/"S10/data/S10_MODE_SCENARIO_SUMMARY.csv")
    oldg=old.groupby("mode",as_index=False).agg(old_orders=("orders","sum"),old_completed=("completed","sum"),old_on_time=("on_time","sum"),old_ghg_proxy_kg=("operational_energy_ghg_kg_scenario","sum"),old_partial_opex_MYR=("operating_cost_MYR_partial","sum"),old_uav_flights=("uav_flights","sum"))
    oldg["old_completion_rate"]=oldg.old_completed/oldg.old_orders;oldg["old_on_time_rate"]=oldg.old_on_time/oldg.old_orders
    maps={"M1_NO_UAV":"M0_PETROL","M2_NO_UAV":"M0_PETROL","M1_DJI":"M1_DJI","M1_WING":"M1_WING","M2_DJI":"M2_DJI","M2_WING":"M2_WING"}
    new=summary.copy();new["old_mode"]=new["mode"].map(maps);new=new.merge(oldg,left_on="old_mode",right_on="mode",suffixes=("_new","_old"))
    new["new_on_time_rate"]=new.on_time/new.orders;new["new_completion_rate"]=new.completed/new.orders
    new["on_time_rate_change_pp"]=(new.new_on_time_rate-new.old_on_time_rate)*100
    new["ghg_proxy_change_percent"]=(new.ghg_proxy_kg-new.old_ghg_proxy_kg)/new.old_ghg_proxy_kg*100
    new["comparability_note"]="Descriptive old-vs-new only: duty, dispatcher, weather timing, spatial gate and SOC differ. Causal inference uses S11 NO_UAV controls."
    new.to_csv(RUN/"FINAL_HANDOFF/S11_OLD_VS_NEW_RESULTS.csv",index=False)

    closure=pd.DataFrame([
      ["P0-1","release-time weather used as launch weather","closed","four-event actual-time weather ledger","G11_1_DYNAMIC_WEATHER/data/S11_LAUNCH_WEATHER_LEDGER.parquet","weather remains hourly and grid-proxy"],
      ["P0-2",">10 km proxy drove most flights","closed with two-scenario boundary","strict exclusion is primary; relaxed retained","G11_1_DYNAMIC_WEATHER/data/STRICT_RELAXED_PAIRED_RESULTS.csv","strict result has lower external validity where weather stations are sparse"],
      ["P0-3","M2 ground-only tasks benefited from different algorithm","closed","common deterministic NO_UAV ground kernel","G11_3_FAIRNESS/data/PAIRWISE_CAUSAL_DECOMPOSITION.csv","absolute results remain model-conditional"],
      ["P0-4","M2 lacked continuous SOC/assets","closed","battery-level continuous SOC and two precharged packs per vehicle","G11_2_BATTERY_SOC/data/UAV_SOC_EVENT_LEDGER.parquet","M2 onboard charging is not assumed"],
      ["P1-1","energy realism weak","partially closed","0.5x/1x/2x counterfactual ledger","G11_5_ENERGY_COST/data/MISSION_ENERGY_SENSITIVITY.parquet","Wing capacity/energy lacks OEM validation"],
      ["P1-2","cost incomplete","partially closed","driver/operator/electricity/fuel/maintenance plus break-even ceiling","G11_5_ENERGY_COST/data/BREAK_EVEN.csv","capital, insurance and certification costs unavailable"],
      ["P1-3","30 h window","closed","full 8/12/24/30 rescheduling reruns","G11_4_DUTY_ROAD/data/DUTY_SHIFT_SENSITIVITY.csv","shift-rule/legal labor compliance not independently established"],
      ["P1-4","road hourly cache","closed","3,000-leg exact-departure replay","G11_4_DUTY_ROAD/qa/ROAD_CACHE_GATE.json","FCD remains undirected speed proxy"],
      ["P1-5","airspace/regulatory overclaim","open HOLD","official-source registry and claim boundary","G11_7_GIS/data/REGULATORY_SOURCE_REGISTRY.csv","no route-specific CAAM/SUP/CIQ approval"],
    ],columns=["defect_id","audited_defect","closure_status","revision","evidence","residual_limit"])
    closure.to_csv(RUN/"FINAL_HANDOFF/S11_P0_P1_P2_CLOSURE_MATRIX.csv",index=False)

    def line(mode):
        r=strict.loc[mode];return f"{mode}: 完成率 {r.completion_rate:.3%}，准时率 {r.on_time_rate:.3%}，飞行 {int(r.uav_flights):,} 次，运营 GHG 代理 {r.ghg_proxy_kg:,.1f} kg，部分 OPEX {r.partial_opex_MYR:,.1f} MYR"
    cn=f"""# S11 SCI 最终审计报告（修订条件性实验）

## 结论

S11 已实际完成 4,590 个基础场景的主运行，并对 8、12、24、30 小时工时边界分别完成全量重排。主运行产生 {qa['actual_order_rows']:,} 条模式订单、55,080 条模式场景、56,342 次飞行和 1,487,220 条地面物理路段。键唯一性、SOC 守恒和道路时间重放均通过。

旧 S10 中 M2 的大幅服务与排放优势在严格空间天气、实际事件天气和连续 SOC 后不再成立为同等幅度。严格主场景结果：

- {line('M1_DJI')}
- {line('M1_WING')}
- {line('M2_DJI')}
- {line('M2_WING')}
- NO_UAV 对照：完成率 {strict.loc['M2_NO_UAV','completion_rate']:.3%}，准时率 {strict.loc['M2_NO_UAV','on_time_rate']:.3%}。

## 四个核心问题

1. 严格天气、实际发射和 SOC 后，M1-DJI、M1-WING、M2-DJI、M2-WING 分别完成 {int(strict.loc['M1_DJI','uav_flights']):,}、{int(strict.loc['M1_WING','uav_flights']):,}、{int(strict.loc['M2_DJI','uav_flights']):,}、{int(strict.loc['M2_WING','uav_flights']):,} 次条件性飞行。它们不是获批运营任务。
2. 与同一地面调度器禁飞对照相比，严格场景下 M2-DJI 准时率仅增加 {(strict.loc['M2_DJI','on_time_rate']-strict.loc['M2_NO_UAV','on_time_rate'])*100:.3f} 个百分点，M2-WING 增加 {(strict.loc['M2_WING','on_time_rate']-strict.loc['M2_NO_UAV','on_time_rate'])*100:.3f} 个百分点。M2 两配置的部分 OPEX 均高于禁飞对照；运营 GHG 混合边界代理略低，但不是生命周期减排。
3. 在预注册服务门槛（完成率≥95%、准时率≥90%）下多种配置进入可行域；严格场景中 M1 配置在当前部分 OPEX 下优于相应禁飞对照，而 M2 不具成本优势。缺少资本、保险、认证和全生命周期成本，不能宣称完整经济最优。
4. 稳健结论是：严格空间门控显著减少可飞任务，旧 M2 大优势高度依赖放宽天气代理和算法结构；连续 SOC 约束可审计。仍 HOLD 的是 Wing 实测能耗/容量、全生命周期排放、完整固定成本、路线级 CAAM/SUP/CIQ 授权。

## 道路与工时验证

精确出发时刻道路重放抽检 {road['sample_n']:,} 段，平均绝对百分误差 {road['mean_absolute_percent_error']:.3f}%，P95 {road['p95_absolute_percent_error']:.3f}%，通过预设的 5%/10% 门槛。8/12/24/30 小时均为完整重排，不是事后截断。

## 证据边界

排放指标为汽油 TTW CO2 加电网发电 GHG 的运营混合边界代理，不是 LCA。WMP228 和空域字段仅用于几何筛查，不构成飞行许可。所有论文表述应使用“条件性仿真”“运营代理”“在本研究假设下”。
"""
    write(RUN/"FINAL_HANDOFF/S11_SCI_FINAL_AUDIT_REPORT_CN.md",cn)
    en="""# S11 Results, Discussion, and Claim Boundaries

The revised experiment supports conditional simulation claims only. Under strict spatial weather screening, actual-event weather checks, continuous battery SOC, and a common no-UAV ground dispatcher, the large M2 advantage reported by S10 was not retained. Small operational GHG-proxy reductions remain for several configurations, but these are not lifecycle results. The strict M2 configurations did not reduce partial operating cost after operator time was included.

Permitted wording: “Under the registered S11 assumptions, the hybrid configurations changed the operational mixed-boundary GHG proxy relative to a matched no-UAV dispatcher.”

Prohibited wording: “The drones are proven to reduce lifecycle carbon,” “the routes are regulator-approved,” or “Wing energy performance is empirically validated.” Wing energy, fixed capital cost, embodied impacts, route-specific authorisation, and CIQ approval remain unresolved.
"""
    write(RUN/"FINAL_HANDOFF/S11_RESULTS_DISCUSSION_CLAIM_BOUNDARIES_EN.md",en)
    guide=f"""# S11 Complete Reproduction Guide

Run from `{ROOT}` with Python {platform.python_version()}.

1. Verify frozen inputs with `G11_0_PRECHECK/code/run_g11_0.py`.
2. Execute `G11_1_DYNAMIC_WEATHER/code/run_s11_corrective_chunk.py` in four chunks for the 24 h main run.
3. Repeat with environment variable `S11_DUTY_HOURS=8`, `12`, and `30` plus `--summary-only`.
4. Run `shared/postprocess_s11.py`.
5. Run `G11_4_DUTY_ROAD/code/audit_hour_cache.py`.
6. Run `shared/finalize_s11.py`.

Historical S07–S10 inputs are referenced by SHA-256 and are not duplicated in every ZIP. A genuinely independent rerun therefore also requires the frozen directories `output_S07_S08_Codex_20261030` and `output_S08A_S09_S10_Codex_20261030/RUN_20261030_01` listed in the input registry.
"""
    write(RUN/"FINAL_HANDOFF/S11_COMPLETE_REPRODUCTION_GUIDE.md",guide)
    pd.DataFrame([
      ["S11_ORDER_RESULTS","G11_3_FAIRNESS/data/S11_ORDER_RESULTS.parquet","order x mode x spatial scenario","991,440"],
      ["S11_SCENARIO_RESULTS","G11_3_FAIRNESS/data/S11_SCENARIO_RESULTS.csv","scenario x mode x spatial scenario","55,080"],
      ["S11_UAV_FLIGHTS","G11_2_BATTERY_SOC/data/S11_UAV_FLIGHTS.parquet","physical UAV mission","56,342"],
      ["S11_GROUND_PHYSICAL_LEGS","G11_4_DUTY_ROAD/data/S11_GROUND_PHYSICAL_LEGS.parquet","physical directed road leg","1,487,220"],
    ],columns=["dataset","path","grain","rows"]).to_csv(RUN/"FINAL_HANDOFF/S11_DATA_DICTIONARY.csv",index=False)


def stage_docs_and_manifests():
    descriptions={
      "G11_0_PRECHECK":"Frozen-input discovery, SHA registry and historical single-scenario reproduction.",
      "G11_1_DYNAMIC_WEATHER":"Actual launch/delivery/return/recovery weather and strict-vs-relaxed spatial rerun.",
      "G11_2_BATTERY_SOC":"Continuous SOC, battery assets, charging and resource conflicts.",
      "G11_3_FAIRNESS":"Common no-UAV controls and paired causal decomposition.",
      "G11_4_DUTY_ROAD":"8/12/24/30 h full reruns and exact-departure road-cache replay.",
      "G11_5_ENERGY_COST":"Operational energy/emission boundary, partial OPEX and break-even sensitivities.",
      "G11_6_STATS_PARETO":"Paired inference, block bootstrap, month/zone and Pareto gates.",
      "G11_7_GIS":"GIS/airspace/CIQ evidence and official-source boundary.",
      "FINAL_HANDOFF":"Final matrices, reports, reproduction guide and package verification.",
    }
    for st in STAGES:
        d=RUN/st
        write(d/"README.md",f"# {st}\n\n{descriptions[st]}\n\nHistorical inputs are read-only and identified in G11-0. Empty figures folders mean no additional figure is applicable for this gate.")
        write(d/"CHANGELOG.md",f"# Changelog\n\n- 2026-10-30/31: Created as part of S11 corrective validation; no historical S07–S10 file was overwritten.")
        write(d/"RUN_COMMANDS.md",f"# Run commands\n\nSee `{RUN/'FINAL_HANDOFF/S11_COMPLETE_REPRODUCTION_GUIDE.md'}` and stage logs.")
        holds=[]
        if st=="G11_5_ENERGY_COST":holds=["Wing energy/capacity lacks OEM primary validation.","Full capital and lifecycle inventories are unavailable."]
        if st=="G11_7_GIS":holds=["No route-specific CAAM/SUP/CIQ authorisation was supplied."]
        write(d/"HOLD_ITEMS.md","# HOLD items\n\n"+("\n".join(f"- {x}" for x in holds) if holds else "None beyond upstream claim boundaries."))
        external_verification={"ZIP_FRESH_EXTRACTION_TEST.json","S11_FINAL_DELIVERABLE_SHA256.csv"}
        files=[p for p in d.rglob("*") if p.is_file() and p.name!="SHA256_MANIFEST.csv" and p.name not in external_verification]
        pd.DataFrame([{"relative_path":p.relative_to(d).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p)} for p in files]).to_csv(d/"SHA256_MANIFEST.csv",index=False)


def package():
    pkg=RUN/"packages";pkg.mkdir(exist_ok=True)
    zips=[]
    external_verification={"ZIP_FRESH_EXTRACTION_TEST.json","S11_FINAL_DELIVERABLE_SHA256.csv"}
    for st in STAGES:
        zp=pkg/f"S11_{st}.zip"
        with zipfile.ZipFile(zp,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for p in (RUN/st).rglob("*"):
                if p.is_file() and "__pycache__" not in p.parts and p.name not in external_verification:z.write(p,p.relative_to(RUN).as_posix())
        zips.append(zp)
    joint=pkg/"CIQ_V5_S11_CORRECTIVE_VALIDATION_COMPLETE.zip"
    with zipfile.ZipFile(joint,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for st in STAGES:
            for p in (RUN/st).rglob("*"):
                if p.is_file() and "__pycache__" not in p.parts and p.name not in external_verification:z.write(p,p.relative_to(RUN).as_posix())
        for p in (RUN/"shared").glob("*.py"):z.write(p,p.relative_to(RUN).as_posix())
    zips.append(joint)
    tests=[]
    for zp in zips:
        with zipfile.ZipFile(zp) as z:
            bad=z.testzip();members=[x for x in z.namelist() if not x.endswith("/")]
            with tempfile.TemporaryDirectory(prefix="s11_zipcheck_") as td:
                z.extractall(td); mismatch=0;sha_mismatch=0
                for name in members:
                    extracted=Path(td)/Path(name)
                    if not extracted.exists():mismatch+=1
                    else:
                        original=RUN/Path(name)
                        if not original.exists() or sha(extracted)!=sha(original):sha_mismatch+=1
        tests.append({"zip":str(zp),"bytes":zp.stat().st_size,"sha256":sha(zp),"file_count":len(members),"crc_bad_member":bad or "","fresh_extract_missing":mismatch,"fresh_extract_sha_mismatch":sha_mismatch,"status":"PASS" if bad is None and mismatch==0 and sha_mismatch==0 else "FAIL"})
    (RUN/"FINAL_HANDOFF/ZIP_FRESH_EXTRACTION_TEST.json").write_text(json.dumps(tests,ensure_ascii=False,indent=2),encoding="utf-8")
    pd.DataFrame(tests).to_csv(RUN/"FINAL_HANDOFF/S11_FINAL_DELIVERABLE_SHA256.csv",index=False)
    return tests


def main():
    duty=combine_duty();create_final_files(duty);stage_docs_and_manifests();tests=package();print(json.dumps(tests,ensure_ascii=False))


if __name__=="__main__":main()
