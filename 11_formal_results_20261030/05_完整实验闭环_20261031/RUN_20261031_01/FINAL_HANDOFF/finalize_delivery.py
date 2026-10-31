from __future__ import annotations

import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

import pandas as pd


FINAL = Path(__file__).resolve().parent
RUN = FINAL.parent
PACK = RUN / "packages"
PACK.mkdir(exist_ok=True)


def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
    return h.hexdigest()


def markdown_table(df):
    headers=[str(x).replace("|","\\|") for x in df.columns]
    rows=[]
    for row in df.itertuples(index=False,name=None): rows.append("| "+" | ".join(str(x).replace("|","\\|").replace("\n"," ") for x in row)+" |")
    return "| "+" | ".join(headers)+" |\n| "+" | ".join(["---"]*len(headers))+" |\n"+"\n".join(rows)


def add_tree(z, root, arcroot, exclusions=()):
    for p in sorted(root.rglob("*")):
        if not p.is_file(): continue
        rel=p.relative_to(root)
        if any(str(rel).replace("\\","/").startswith(x) for x in exclusions): continue
        z.write(p, Path(arcroot)/rel)


specs = [
    ("CIQ_S11B_CORRECTED_BASELINE_COMPLETE.zip", [(RUN/"G0_INPUTS","G0_INPUTS",()),(RUN/"S11B_REPAIRS","S11B_REPAIRS",("chunks/PILOT",))]),
    ("CIQ_S12_EXPERIMENTS_COMPLETE.zip", [(RUN/"S12_EXPERIMENTS","S12_EXPERIMENTS",())]),
    ("CIQ_S13_PAPER_RESULTS_COMPLETE.zip", [(RUN/"S13_PAPER_RESULTS","S13_PAPER_RESULTS",())]),
    ("CIQ_S11B_S12_S13_FINAL_HANDOFF_COMPLETE.zip", [(RUN/"G0_INPUTS","G0_INPUTS",()),(RUN/"S11B_REPAIRS","S11B_REPAIRS",("chunks/",)),(RUN/"S12_EXPERIMENTS","S12_EXPERIMENTS",()),(RUN/"S13_PAPER_RESULTS","S13_PAPER_RESULTS",()),(RUN/"FINAL_HANDOFF","FINAL_HANDOFF",())]),
]

records=[]
for name, trees in specs:
    out=PACK/name
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED,allowZip64=True) as z:
        for root,arc,exc in trees: add_tree(z,root,arc,exc)
    with zipfile.ZipFile(out) as z:
        bad=z.testzip(); members=len(z.infolist())
        with tempfile.TemporaryDirectory(dir=FINAL,prefix="zip_extract_check_") as td:
            z.extractall(td)
            extracted=sum(1 for p in Path(td).rglob("*") if p.is_file())
    records.append({"absolute_path":str(out.resolve()),"bytes":out.stat().st_size,"sha256":sha(out),"members":members,"crc_test":"PASS" if bad is None else f"FAIL:{bad}","fresh_extract_file_count":extracted,"fresh_extract_status":"PASS" if extracted==members else "FAIL"})
pd.DataFrame(records).to_csv(FINAL/"FINAL_PACKAGE_MANIFEST.csv",index=False)

gates=[]
for gate,path in [
    ("G0",RUN/"G0_INPUTS"/"G0_REPRO_GATE.json"),("G1",RUN/"S11B_REPAIRS"/"qa"/"G1_GATE.json"),("G2",RUN/"S11B_REPAIRS"/"qa"/"G2_LEDGER_RECONCILIATION.json"),
    ("G3",RUN/"S12_EXPERIMENTS"/"S12_A"/"G3_GATE.json"),("G4",RUN/"S12_EXPERIMENTS"/"G4_GATE.json"),("G5",RUN/"S12_EXPERIMENTS"/"G5_GATE.json"),("G6_G7",RUN/"S13_PAPER_RESULTS"/"G6_G7_GATE.json")]:
    x=json.loads(path.read_text(encoding="utf-8"));gates.append({"gate":gate,"status":x.get("status"),"evidence_path":str(path.resolve())})
pd.DataFrame(gates).to_csv(FINAL/"FINAL_GATE_MATRIX.csv",index=False)

seed=pd.read_csv(RUN/"S11B_REPAIRS"/"data"/"G2_PER_SEED_153DAY.csv")
pair=pd.read_csv(RUN/"S11B_REPAIRS"/"data"/"G2_MODE_PAIRING.csv")
strict=seed[seed.spatial_scenario=="STRICT_EXCLUDE_GT10KM"]
summary=strict.groupby("mode").agg(completion=("completion_rate","mean"),ontime=("on_time_rate_all_orders","mean"),ghg=("mixed_boundary_operational_ghg_proxy_kg","mean"),cost=("partial_opex_MYR","mean"),flights=("uav_flights","mean")).reset_index()

lines=["# S11B–S13 最终独立审核结论","","## 总体结论","","本轮完成了冻结输入的独立复现、S11B P0 模型修复、双空间情景全量重跑、种子级公平配对、S12 分层与服务约束 Pareto 审计，以及 S13 图表和论文英文草稿。结果属于条件性仿真，不构成真实飞行许可、实机能耗验证或生命周期减排证明。","","## 严格主情景真实结果","",markdown_table(summary),"","30 个随机种子分别代表一个 153 天复现；上表为种子均值，禁止将 30 个种子累加为单次五个月运营量。","","## 可用于论文的结论","","- 可报告冻结 82,620 订单、4,590 场景、30 个 153 天复现及严格 10 km 审计情景。","- 可报告同一调度内核下 UAV 开关的配对差异及 95% 种子聚类 bootstrap 区间。","- 可报告运营能耗与混合边界排放代理、部分 OPEX，以及测试配置集合内的服务约束非支配关系。","","## 禁止或必须弱化的表述","","- 不得称为实际运营验证、真实因果效应或完整 LCA 净减排。","- 不得宣称 11 个站点已获许可、WMP228 已获正式放行或 Wingcopter 实机能耗已验证。","- 不得将放宽天气空间代理解释为真实可飞。","- 不得将历史 S11 与 S11B 的多因素变化归因于单一修复。","","## 配对效应证据","",markdown_table(pair[pair.spatial_scenario=="STRICT_EXCLUDE_GT10KM"]),"","## Gate 状态","",markdown_table(pd.DataFrame(gates)),"","## ZIP 交付","",markdown_table(pd.DataFrame(records)),""]
(FINAL/"FINAL_INDEPENDENT_AUDIT_CN.md").write_text("\n".join(lines),encoding="utf-8")

manifest=[]
for root in [RUN/"G0_INPUTS",RUN/"S11B_REPAIRS"/"data",RUN/"S11B_REPAIRS"/"qa",RUN/"S12_EXPERIMENTS",RUN/"S13_PAPER_RESULTS",FINAL]:
    for p in sorted(root.rglob("*")):
        if p.is_file() and not p.name.endswith(".zip"):
            manifest.append({"absolute_path":str(p.resolve()),"bytes":p.stat().st_size,"sha256":sha(p)})
pd.DataFrame(manifest).drop_duplicates("absolute_path").to_csv(FINAL/"FINAL_FILE_SHA256_MANIFEST.csv",index=False)
print(pd.DataFrame(records).to_string(index=False))
