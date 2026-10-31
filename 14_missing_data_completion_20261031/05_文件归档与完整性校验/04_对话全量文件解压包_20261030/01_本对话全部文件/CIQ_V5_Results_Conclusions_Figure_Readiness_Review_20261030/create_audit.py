#!/usr/bin/env python3
"""Audit frozen CIQ V5 evidence and render truthful preliminary (not SCI final) figures."""
from pathlib import Path
import csv, gzip, zipfile, io, json, hashlib, collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path('/mnt/data')
OUT=ROOT/'CIQ_V5_Results_Conclusions_Figure_Readiness_Review_20261030'
S09=ROOT/'CIQ_V5_S09_Complete_Nine_Gate_Acceptance_And_Conditional_Model_20261030.zip'
S07G=ROOT/'CIQ_V5_S07_Actual_QA_Gates_20261030/outputs/S07_CURRENT_NUMERIC_GATE.json'
S08=ROOT/'CIQ_V5_S08_Petrol_Baseline_And_Dual_UAV_Payload_Executed_20261030.zip'
V5=ROOT/'CIQ_ABC_QGIS322_V5_ONE_WMP228_68_NODES_FULL_PROJECT(1).zip'

def sha(b):return hashlib.sha256(b).hexdigest()

with zipfile.ZipFile(S09) as z:
    raw=gzip.decompress(z.read('outputs/S09_82620_TASKS_X_2_AIRCRAFT_STATIC_AND_CONDITIONAL.csv.gz'))
    reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    counts=collections.Counter();ids=collections.defaultdict(set)
    metrics=('real_mission_energy_kwh','real_operational_CO2e_kg')
    for row in reader:
        a=row['aircraft_model'];t=row['task_id']
        counts[(a,'n')]+=1
        assert t not in ids[a],f'duplicate task {a}:{t}'
        ids[a].add(t)
        counts[('status',row['directed_candidate_status'])]+=1 if a=='DJI_FLYCART_30_DUAL' else 0
        if row['static_payload_status']=='WEIGHT_ONLY_PASS':
            counts[(a,'payload_pass')]+=1
            if row['directed_candidate_status']=='DIRECTED_CANDIDATE_NOT_AUTHORIZED':
                counts[(a,'payload_and_direct')]+=1
        for field in metrics:
            if row[field].strip(): counts[(a,field+'_filled')]+=1
        if not row['M1_actual_mission_status'].startswith('HOLD'):counts[(a,'m1_nonhold')]+=1
        if not row['M2_actual_mission_status'].startswith('HOLD'):counts[(a,'m2_nonhold')]+=1
    grid=list(csv.DictReader(io.StringIO(z.read('outputs/S09_V5_68_NODE_WEATHER_SPATIAL_REPRESENTATIVENESS.csv').decode('utf-8-sig'))))
    s09gate=json.loads(z.read('outputs/S09_QA_SCIENTIFIC_RELEASE_GATE.json'))
with zipfile.ZipFile(S08) as z:
    s08gate=json.loads(z.read('CIQ_V5_S08_Petrol_And_Payload/qa/S08_STRICT_PETROL_M0_RELEASE_GATE.json'))
s07gate=json.loads(S07G.read_text(encoding='utf-8'))
assert V5.exists()
assert counts[('DJI_FLYCART_30_DUAL','n')]==82620
assert counts[('WINGCOPTER_198_CARGO_ASSUMED','n')]==82620
assert len(ids['DJI_FLYCART_30_DUAL'])==82620
assert len(ids['WINGCOPTER_198_CARGO_ASSUMED'])==82620
assert ids['DJI_FLYCART_30_DUAL']==ids['WINGCOPTER_198_CARGO_ASSUMED']
assert sum(counts[('status',s)] for s in ['DIRECTED_CANDIDATE_NOT_AUTHORIZED','REVERSE_ONLY_NOT_AUTHORIZED','NO_DIRECT_CANDIDATE__FEEDER_OR_MULTILEG_REQUIRED'])==82620
assert counts[('DJI_FLYCART_30_DUAL','payload_and_direct')]==11060
assert counts[('WINGCOPTER_198_CARGO_ASSUMED','payload_and_direct')]==7377
for a in ('DJI_FLYCART_30_DUAL','WINGCOPTER_198_CARGO_ASSUMED'):
    for field in metrics:
        assert counts[(a,field+'_filled')]==0
    assert counts[(a,'m1_nonhold')]==0 and counts[(a,'m2_nonhold')]==0
assert s07gate['S07_NUMERIC_ACCEPTANCE']=='HOLD' and s08gate['full_main_M0_run']=='HOLD'
assert s09gate['actual_M1_M2_missions_computed']==0

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.linewidth':0.85,'figure.dpi':110})
# Figure: actual static screening, not historical weather or delivery.
geom=['Directed candidate','Reverse-only candidate','No direct candidate']
series=[counts[('status',s)] for s in ['DIRECTED_CANDIDATE_NOT_AUTHORIZED','REVERSE_ONLY_NOT_AUTHORIZED','NO_DIRECT_CANDIDATE__FEEDER_OR_MULTILEG_REQUIRED']]
fig,ax=plt.subplots(figsize=(7.8,4.3),layout='constrained')
xs=list(range(3));rects=ax.bar(xs,series,width=0.56,edgecolor='#333333',linewidth=0.7)
for i,b in enumerate(rects):
    ax.annotate(f'{series[i]:,} ({100*series[i]/82620:.1f}%)',(b.get_x()+b.get_width()/2,b.get_height()),ha='center',va='bottom',fontsize=9,xytext=(0,5),textcoords='offset points')
ax.set_xticks(xs,geom);ax.set_ylabel('Orders (N = 82,620)')
ax.set_ylim(0,63000)
ax.set_title('V5 synthetic orders: direct UAV geometry pre-screen',loc='left',fontweight='bold',fontsize=11)
ax.spines[['top','right']].set_visible(False)
ax.grid(axis='y',alpha=0.14);ax.set_axisbelow(True)
fig.text(0.11,-0.035,'Static candidate geometry only. No approved flight corridors, weather or completed missions.',fontsize=8)
fig.savefig(OUT/'PRELIMINARY_FigS1_STATIC_GEOMETRY_SCREEN_ONLY.png',dpi=300,bbox_inches='tight');fig.savefig(OUT/'PRELIMINARY_FigS1_STATIC_GEOMETRY_SCREEN_ONLY.pdf',bbox_inches='tight');plt.close(fig)

# Supplementary QA figure: spatial weather grid proxy distance
zones=[r['zone'] for r in grid]
mean=[float(r['n_nodes_farther_than_10km'])/float(r['n_nodes'])*100 for r in grid]
maxd=[float(r['max_grid_distance_km']) for r in grid]
fig,ax=plt.subplots(figsize=(7.3,4.3),layout='constrained')
rect=ax.bar(zones,mean,width=0.52,edgecolor='#333333',linewidth=0.7)
for b,p in zip(rect,mean):ax.annotate(f'{p:.1f}%',(b.get_x()+b.get_width()/2,b.get_height()),ha='center',va='bottom',fontsize=10,xytext=(0,4),textcoords='offset points')
ax.set_ylim(0,115);ax.set_ylabel('V5 nodes farther than 10 km from grid (%)')
ax.set_title('Historical ERA5 proxy: node-grid distance QA',loc='left',fontweight='bold',fontsize=11)
ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=0.14);ax.set_axisbelow(True)
fig.text(0.09,-0.035,'10 km is a project QA flag, not a universal meteorological validity threshold.',fontsize=8)
fig.savefig(OUT/'PRELIMINARY_FigS2_ERA5_SPATIAL_QA_ONLY.png',dpi=300,bbox_inches='tight');fig.savefig(OUT/'PRELIMINARY_FigS2_ERA5_SPATIAL_QA_ONLY.pdf',bbox_inches='tight');plt.close(fig)

figure_rows=[
['Fig. 1','V5 spatial overview, A/B/C and CIQ','CAN_PREPARE_MAP__FINAL_CARTOGRAPHIC_QA_PENDING','V5 original QGIS GeoPackage; review basemap license, road/country border georeference, scale and attribution','No operational claim'],
['Fig. 2','Study workflow and five-mode carbon comparison','CAN_DRAW_METHOD_DIAGRAM','Frozen protocol and model interfaces','A methodology diagram is not a simulation result'],
['Fig. 3','Reference UAV aircraft, routes and spatial assumptions','CAN_PREPARE_STATIC_CONDITIONAL','V5 68 nodes, 116 candidate geometries, UAV OEM specs','Do not infer approved flight routes or real aircraft mission kWh'],
['Fig. 4','May-Sep historical weather / FCD / go-no-go','NOT_READY_FOR_FINAL','Historical metadata and coarse-grid QA exist; raw hourly weather/FCD QA pending','No actual go/no-go hourly time series verified'],
['Fig. 5','Dispatch, weather cancellation, task on-time rate','STATIC_PREFLIGHT_ONLY__FINAL_NOT_READY','S09 static 165240 model/task records; no weather-driven dispatch','11,060/7,377 are candidate counts, not delivered orders'],
['Fig. 6','M0 vs M1/M2 time, cost, operational CO2e','NOT_READY_FOR_FINAL','M0 has zero validated trip legs; M1/M2 actual records all HOLD','No measured or validated mode-level carbon savings'],
['Fig. 7','Pareto frontier and carbon break-even thresholds','NOT_READY_FOR_FINAL','No validated S10 comparison, S11 not run','Do not generate fake Pareto or confidence intervals'],
]
with (OUT/'FIGURE_READINESS_MATRIX.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['figure','intended_content','readiness','actual_evidence','strict_claim_limit']);w.writerows(figure_rows)

checks={
 'audit_type':'Direct file content check, not new historical-weather simulation',
 'source_SHA256':{'S09_complete_zip':sha(S09.read_bytes()),'S08_zip':sha(S08.read_bytes()),'V5_source_zip':sha(V5.read_bytes()),'S07_gate_json':sha(S07G.read_bytes())},
 'frozen_orders':82620,'aircraft_pair_records':sum(counts[(a,'n')] for a in ['DJI_FLYCART_30_DUAL','WINGCOPTER_198_CARGO_ASSUMED']),
 'direct_candidate_orders':series[0],'reverse_only_orders':series[1],'no_direct_candidate_orders':series[2],
 'dji_weight_and_direct_candidate':counts[('DJI_FLYCART_30_DUAL','payload_and_direct')],
 'wingcopter_weight_and_direct_candidate':counts[('WINGCOPTER_198_CARGO_ASSUMED','payload_and_direct')],
 'verified_real_energy_records':sum(counts[(a,'real_mission_energy_kwh_filled')] for a in ['DJI_FLYCART_30_DUAL','WINGCOPTER_198_CARGO_ASSUMED']),
 'verified_real_carbon_records':sum(counts[(a,'real_operational_CO2e_kg_filled')] for a in ['DJI_FLYCART_30_DUAL','WINGCOPTER_198_CARGO_ASSUMED']),
 'non_HOLD_M1_status_records':sum(counts[(a,'m1_nonhold')] for a in ['DJI_FLYCART_30_DUAL','WINGCOPTER_198_CARGO_ASSUMED']),
 'non_HOLD_M2_status_records':sum(counts[(a,'m2_nonhold')] for a in ['DJI_FLYCART_30_DUAL','WINGCOPTER_198_CARGO_ASSUMED']),
 'S07_real_numeric_gate':s07gate['S07_NUMERIC_ACCEPTANCE'],
 'S07_large_source_files_verified':s07gate['source_files_verified_actual'],
 'S08_petrol_full_run_gate':s08gate['full_main_M0_run'],
 'S09_mission_gate':s09gate['final_status'],
 'S09_computed_actual_M1_M2_missions':s09gate['actual_M1_M2_missions_computed'],
 'manuscript_conclusions_final_ready':False,
 'Fig1_3_possible':'method/static cartographic drafts',
 'Fig4_7_final_ready':False,
 'weather_grid_zone_counts':grid,
}
(OUT/'INDEPENDENT_AUDIT_RESULTS.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')

body='''# CIQ V5 SCI 结果、论文结论与 Fig. 1–7 科学验收报告\n\n日期：2026-10-30。此次为**已交付数据的独立复查**，不是新完成的历史天气配送仿真。\n\n## 最终裁定\n\n- **论文最终 Conclusions：NOT READY。** 已具备研究范围和条件性静态筛查结论；没有实证/历史气象驱动的五模式完成率、时间、成本和运营 CO2e 结果。\n- **可立即制作的图**：Fig.1 GIS 布局图（仍需制图级审计）、Fig.2 方法流程图、Fig.3 两机型和空间技术设计；可绘制补充静态筛查图（本包提供两个来源可追溯的 PNG/PDF）。\n- **不可标注为最终结果的图**：Fig.4–Fig.7，除 Fig.5 中静态候选部分可先形成补充 QA 图外。不要用设计情景风况替代 2026 历史风雨、用地图直线替代汽车有向道路或用假设耗电替代已核验的运营 CO2e。\n\n## 实际源文件检查\n\nS09 原始 gz 逐行检查：165,240 条机型-任务，两个机型各有 82,620 个不重复任务 ID，任务集合相同；DJI 的载重合格且有记录方向候选几何 11,060 条，Cargo 7,377 条。所有记录的正式任务 kWh 和运营 CO2e 字段均为空，M1/M2 状态均 HOLD。整体任务方向候选：11,060 条正向、17,417 条仅反向、54,143 条无直接候选。\n\nS07 当前数值门：0/14 份大型来源独立核验，HOLD；S08 M0：0 条正式通过的车辆物理行程，HOLD；S09 事件级任务运行：0，HOLD。\n\nB/C 两区共有 55,080 条订单起点的 ERA5 关联格点距离超过项目设定的 10 km 预警线；这是空间代表性 QA，不是天气拒飞统计。\n\n## 可以写入当前稿件的范围\n\n可写：研究采用固定 V5 68 节点、116 条候选 UAV 线、82,620 条受控合成订单，进行双机型的静态载重和几何适配筛查。静态约束揭示两机型适配差异，说明地面回退对后续 M1/M2 有必要性。\n\n**不能写：** 已验证哪几个月可飞、某小时可飞率、天气造成多少任务损失、M1/M2 准时率提高百分比、汽油车/无人机 CO2e 节省百分比、最低碳解或稳健显著性。现有实验没有支撑这些事实。\n\n## 后续最短闭环\n\n1. S07：读入并按 SHA 核验五个月 XLSX + FCD，验证 ERA5 边界 4 行/月、时区和前小时降水语义，补全 A/B/C 有向路网、方向和站点接入。\n2. S09：输出每个节点每小时的双机型天气 go/no-go，带证据等级和雨/风阈值；按事件时刻计算任务能耗区间。\n3. S08：在相同订单场景计算有向道路 M0、多订单汽油、时间与成本；严禁直线替代道路。\n4. S10：在 4,590 个种子×日期场景对五个模式配对运行（22,950 模式场景），输出实际模型内完成/迟到/未完成和资源约束。\n5. S11：完整能源/碳/成本对账，做天气相对清朗反事实和最低碳可行边界；S12：按日期聚类敏感性与区间估计，生成正式 Fig.4–7 后才允许写定稿 Conclusions。\n\n## 图件等级\n\n两个 `PRELIMINARY_FigS*.png/.pdf` 仅为**前期 QA 补充图**：分别使用已实算的候选几何条数和历史格点的静态空间距离。未包括任何历史气象时间序列、配送完成率或碳排放。所有画图原始汇总值和脚本均随附。\n'''
(OUT/'SCI_RESULT_FIGURE_READINESS_AUDIT_CN.md').write_text(body,encoding='utf-8')

with (OUT/'SOURCE_SUMMARY_FOR_CHARTS.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['screen','group','count','denominator','percent','evidence_level'])
 for nm,v in zip(geom,series):w.writerow(['geometry',nm,v,82620,f'{100*v/82620:.5f}','V5_SOURCE_AND_S09_GZ_ACTUAL_QA'])
 for nm,a in [('DJI FlyCart 30','DJI_FLYCART_30_DUAL'),('Wingcopter 198 Cargo','WINGCOPTER_198_CARGO_ASSUMED')]:
  v=counts[(a,'payload_and_direct')];w.writerow(['payload_and_direct',nm,v,82620,f'{100*v/82620:.5f}','STATIC_PREFLIGHT_ONLY'])
 for r in grid:
  w.writerow(['grid_farther_10km',r['zone'],r['n_nodes_farther_than_10km'],r['n_nodes'],f'{100*int(r["n_nodes_farther_than_10km"])/int(r["n_nodes"]):.5f}','SPATIAL_QA_ONLY'])

print(json.dumps({k:v for k,v in checks.items() if k in ['frozen_orders','aircraft_pair_records','direct_candidate_orders','reverse_only_orders','no_direct_candidate_orders','verified_real_energy_records','verified_real_carbon_records','S07_real_numeric_gate','S08_petrol_full_run_gate','S09_computed_actual_M1_M2_missions','manuscript_conclusions_final_ready']},indent=2))
