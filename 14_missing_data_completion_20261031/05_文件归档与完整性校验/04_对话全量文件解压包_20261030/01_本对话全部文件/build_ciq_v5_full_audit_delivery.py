from __future__ import annotations
import os,csv,json,hashlib,shutil,subprocess,sys,zipfile,datetime as dt,collections
from pathlib import Path

ROOT=Path('/mnt/data')
OUT=ROOT/'CIQ_V5_ALL_STAGES_SOURCE_DATA_AUDIT_20261030'
OUT.mkdir(exist_ok=True)
def mk(p):
 p=OUT/p;p.mkdir(parents=True,exist_ok=True);return p
def hashfile(path):
 h=hashlib.sha256();
 with open(path,'rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def csvrows(p):
 with open(p,newline='',encoding='utf-8-sig') as f:
  for r in csv.DictReader(f):yield r
def writecsv(p,rows,fields):
 p.parent.mkdir(parents=True,exist_ok=True)
 with open(p,'w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

active=mk('01_ACTIVE_V5_FROZEN')
arch=mk('02_STAGE_PACKAGES_CURRENT_V5')
historical=mk('03_HISTORICAL_PRE_V5_READ_ONLY')
sources=mk('04_SOURCE_RECOVERY_AND_GITHUB_INVENTORY')
reports=mk('05_AUDIT_REPORTS_AND_TEST_LOGS')
code=mk('06_RUNNABLE_TOOLS')

copied=[]
def cp(src,dest):
 if not src.is_file():raise FileNotFoundError(src)
 dest.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(src,dest)
 copied.append({'path':str(dest.relative_to(OUT)).replace('\\','/'),'size_bytes':dest.stat().st_size,'sha256':hashfile(dest),'from_path':str(src.relative_to(ROOT))})

# Direct, unambiguous frozen V5 project and current stage outputs.
activefiles=[
 ('CIQ_ABC_QGIS322_V5_ONE_WMP228_68_NODES_FULL_PROJECT(1).zip','V5_SPATIAL_AUTHORITATIVE_PROJECT.zip'),
 ('CIQ_V5_S06_S07_Rebase_20261030/outputs/S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv','S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv'),
 ('CIQ_V5_S06_S07_Rebase_20261030/outputs/S06_V5_116_UAV_GEOMETRY_ONLY.csv','S06_V5_116_UAV_GEOMETRY_ONLY.csv'),
 ('CIQ_V5_S06_S07_Rebase_20261030/outputs/S07_V5_SYNTHETIC_TASKS_CONDITIONAL_DESIGN.csv','S07_V5_SYNTHETIC_TASKS_CONDITIONAL_DESIGN.csv'),
 ('CIQ_V5_S07_Simulation_Blocks_20261030/outputs/S07_V5_4590_SEED_DAY_RUN_MANIFEST.csv','S07_V5_4590_SEED_DAY_RUN_MANIFEST.csv'),
 ('CIQ_V5_S07_Simulation_Blocks_20261030/outputs/S07_V5_82620_RUN_TASK_MEMBERSHIP.csv','S07_V5_82620_RUN_TASK_MEMBERSHIP.csv'),
 ('CIQ_V5_S07_Simulation_Blocks_20261030/outputs/S10_V5_22950_MODE_RUN_KEYS_NO_SIM_RESULTS.csv','S10_V5_22950_MODE_RUN_KEYS_NO_SIM_RESULTS.csv'),
 ('CIQ_V5_S09_Aircraft_Mission_Preflight_20261030/outputs/S09_V5_ALL_TASKS_OEM_PAYLOAD_AND_DIRECT_EDGE_SCREEN.csv','S09_V5_ALL_TASKS_OEM_PAYLOAD_AND_DIRECT_EDGE_SCREEN.csv'),
 ('CIQ_V5_S09_Aircraft_Mission_Preflight_20261030/outputs/S09_V5_116_EDGE_OEM_DISTANCE_BOUNDARY_SCREEN.csv','S09_V5_116_EDGE_OEM_DISTANCE_BOUNDARY_SCREEN.csv'),
 ('CIQ_V5_Freeze_Audit_20261030/V5_ALL_125_LINK_RECORDS_BY_TYPE.csv','S06_V5_125_ALL_LINKS_MODE_CLASSIFIED.csv'),
 ('CIQ_V5_Freeze_Audit_20261030/V5_5_GROUND_HANDOFF_STRAIGHT_NOT_ROAD.csv','S06_V5_5_GROUND_HANDOFF_NOT_ROAD.csv'),
 ('CIQ_V5_Freeze_Audit_20261030/V5_4_EXTRA_GROUND_ONLY_HOLD.csv','S06_V5_4_GROUND_ONLY_HOLD.csv'),
 ('CIQ_V5_Freeze_Audit_20261030/V5_ARCHIVE_CSV_MEMBERSHIP_HAZARD.csv','S06_V5_ARCHIVE_STALE_ID_WARNING.csv'),
]
for src,dest in activefiles:cp(ROOT/src,active/dest)

# Group stage archives: these packages preserve all code/input/result/test files from each phase.
current_stage_pkgs=[
 ('CIQ_V5_Frozen_Baseline_Independent_Audit_and_6_Stage_Roadmap_20261030.zip','S06_V5_frozen_GIS_audit.zip'),
 ('CIQ_V5_S06_S07_Rebase_And_Synthetic_Orders_20261030.zip','S06_S07_V5_rebase_and_orders.zip'),
 ('CIQ_V5_S07_Stage01_Event_Alignment_and_Source_Gates_20261030.zip','S07_01_event_timeline_source_gates.zip'),
 ('CIQ_V5_S07_4590_Paired_Scenarios_and_Source_Gate_20261030.zip','S07_02_4590_paired_runs.zip'),
 ('CIQ_V5_S08_Petrol_Baseline_And_Dual_UAV_Payload_Executed_20261030.zip','S08_petrol_model_and_payload_audit.zip'),
 ('CIQ_V5_S07_S09_Real_Task_Screen_and_Energy_Model_20261030.zip','S09_aircraft_energy_and_screen.zip'),
]
for src,dest in current_stage_pkgs:cp(ROOT/src,arch/dest)

# All other generated stage-package ZIP files retained, but NEVER used as latest science input.
exclude={x[0] for x in current_stage_pkgs}|{activefiles[0][0]}
for p in sorted(ROOT.glob('*.zip')):
 if p.name not in exclude:
  cp(p,historical/p.name)

# Freeze source-data versions; source bytes absent locally must not be marked verified.
pinned=json.loads((ROOT/'CIQ_V5_S07_Simulation_Blocks_20261030/inputs/PINNED_SOURCE_INDEX.json').read_text('utf-8'))
repo='tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027'
commit=pinned['git_commit']
extras=[
 {'name':'JB_CIQ_E01_corrected_five_month_traffic_data_345nodes_2026-05_09.csv.gz','path':'02_base_and_traffic_data/traffic_data/JB_CIQ_E01_corrected_five_month_traffic_data_345nodes_2026-05_09.csv.gz','size':17898780,'git_blob':'7615e1e124be99fc450c5ea4c7c592627793fbef','sha256':'','scope':'FCD_MAY_SEP_2026','note':'five-month 345-node FCD; actual hourly speed and direction QA required'},
 {'name':'JB_FCD_345nodes_G1-G5_Grouped_2026-05_09.zip','path':'02_base_and_traffic_data/traffic_data/JB_FCD_345nodes_G1-G5_Grouped_2026-05_09.zip','size':7691136,'git_blob':'7caa522a8be469cd1bf6f5639aa435e72ddfc0ab','sha256':'','scope':'FCD_GROUPED','note':'frozen grouped FCD supporting archive; match to same version as E01'},
 {'name':'JB_FCD_345nodes_G1-G5_grouped_statistics_and_node_master.xlsx','path':'02_base_and_traffic_data/traffic_data/JB_FCD_345nodes_G1-G5_grouped_statistics_and_node_master.xlsx','size':147690,'git_blob':'918f4bcde9b31e9f3513306d32ee07b4e9bacd34','sha256':'','scope':'FCD_NODE_METADATA','note':'metadata/node master; not direct per-hour speed measurement'},
]
known={x['path'] for x in pinned['files']}
for x in extras:
 if x['path'] not in known:pinned['files'].append(x)
pinned['schema']='S07_PINNED_SOURCE_INDEX_V5_INCLUDES_FCD_v3'
pinned['original_authoritative_sources']='GitHub at commit '+commit
pinned['caution']='Metadata and Git blob hashes are retrieved; raw data bytes unavailable in this runtime; no numerical S07 release.'
idx=sources/'SOURCE_FILES_PINNED_14.json'
idx.write_text(json.dumps(pinned,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
registry=[]
for f in pinned['files']:
 registry.append({
  'filename':f['name'],'group':f.get('scope',''),'repo_path':f['path'],'git_blob_sha1':f.get('git_blob',''),
  'repo_bytes':f.get('size',0),'manifest_sha256':f.get('sha256',''),'local_verified_bytes':'NO',
  'file_gate':'GITHUB_FILE_CONFIRMED_NOT_LOCAL_BYTES_VERIFIED',
  'pinned_url':f'https://raw.githubusercontent.com/{repo}/{commit}/{f["path"]}',
  'downstream_use':'HOLD_UNTIL_BYTES_AND_SCIENCE_QA',
 })
writecsv(sources/'14_GITHUB_SOURCES_STATUS_AND_DIRECT_LINKS.csv',registry,list(registry[0]))

# Independent read-only QA on actual mounted data (do not change inputs).
nodes=list(csvrows(active/'S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv'))
tasks=list(csvrows(active/'S07_V5_SYNTHETIC_TASKS_CONDITIONAL_DESIGN.csv'))
runs=list(csvrows(active/'S07_V5_4590_SEED_DAY_RUN_MANIFEST.csv'))
mode_runs=list(csvrows(active/'S10_V5_22950_MODE_RUN_KEYS_NO_SIM_RESULTS.csv'))
screens=list(csvrows(active/'S09_V5_ALL_TASKS_OEM_PAYLOAD_AND_DIRECT_EDGE_SCREEN.csv'))
nodeids={n['node_id'] for n in nodes};taskids={x['task_id'] for x in tasks}
modegroups=collections.defaultdict(lambda:{'modes':set(),'hashes':set(),'task_counts':set()})
for r in mode_runs:
 x=modegroups[r['run_id']];x['modes'].add((r['mode'],r['aircraft']));x['hashes'].add(r['task_set_sha256']);x['task_counts'].add(r['task_count'])
counters={
 'node_count':len(nodes), 'node_ids_unique':len(nodeids),
 'zone_counts':dict(collections.Counter(n['zone'] for n in nodes)),
 'task_count':len(tasks),'task_ids_unique':len(taskids),
 'unmapped_tasks':sum(1 for t in tasks if t['origin_node_id'] not in nodeids or t['destination_node_id'] not in nodeids),
 'seed_count':len({t['scenario_seed'] for t in tasks}),
 'date_count':len({t['date_local'] for t in tasks}),
 'seed_day_scenarios':len(runs),'all_runs_18_tasks':all(r['task_count']=='18' for r in runs),
 'five_mode_run_keys':len(mode_runs),
 'per_run_five_modes_and_one_hash':sum(len(g['modes'])==5 and len(g['hashes'])==1 and g['task_counts']=={'18'} for g in modegroups.values()),
 'task_screen_rows':len(screens),
 'task_screen_unique':len({r['task_id'] for r in screens}),
 'direct_edge_classes':dict(collections.Counter(r['direct_candidate_status'] for r in screens)),
 'all_s09_energy_empty':all(not r['mission_energy_kwh'] for r in screens),
 'all_s07_no_operational_result':all(t['service_and_carbon_result_status']=='NOT_COMPUTED' for t in tasks),
 'all_s10_no_operational_result':all(r['operation_emission_status']=='NOT_COMPUTED' for r in mode_runs),
 'V5_archive_zip_sha256':hashfile(active/'V5_SPATIAL_AUTHORITATIVE_PROJECT.zip'),
 'GitHub_binary_source_files_in_index':len(registry),
 'locally_available_verified_GitHub_binary_sources':0,
}
assert len(nodes)==68 and len(nodeids)==68
assert len(tasks)==len(taskids)==82620 and counters['unmapped_tasks']==0
assert len(runs)==4590 and len(mode_runs)==22950
assert counters['per_run_five_modes_and_one_hash']==4590
assert len(screens)==len(tasks)
assert counters['all_s09_energy_empty'] and counters['all_s10_no_operational_result']

# Run previously created model QA again, store actual reproducibility logs.
checks=[
 ('S07_time_weather',ROOT/'CIQ_V5_S07_03_Fair_Pairing_And_Real_Data_Intake_20261030'),
 ('S07_pairing',ROOT/'CIQ_V5_S07_Simulation_Blocks_20261030'),
 ('S08_petrol',ROOT/'CIQ_V5_Next_Stage_S08_Petrol_And_Payload_20261030'),
 ('S09_drone',ROOT/'CIQ_V5_S09_Aircraft_Mission_Preflight_20261030'),
]
test_records=[]
for label,folder in checks:
 p=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=folder,capture_output=True,text=True,timeout=90)
 (reports/f'{label}_ACTUAL_RECHECK.txt').write_text(p.stdout+'\n'+p.stderr,encoding='utf8')
 import re
 match=re.search(r'Ran\s+(\d+)\s+tests?',p.stderr)
 n=int(match.group(1)) if match else None
 test_records.append({'test_suite':label,'test_count':n,'returncode':p.returncode,'result':'PASS' if p.returncode==0 else 'FAIL'})
writecsv(reports/'TESTS_ACTUAL_RECHECK.csv',test_records,['test_suite','test_count','returncode','result'])
counters['reexecuted_tests_total']=sum(v['test_count'] or 0 for v in test_records)
counters['reexecuted_suites_all_pass']=all(v['returncode']==0 for v in test_records)

status=[
 ('S06','V5 point/edge spatial freeze','PASS_STATIC','68 nodes and V5 125 edge records; no operational site authorization','Frozen V5 GIS + node master','Do not modify V5 or infer legal flight clearance'),
 ('S07','Five-month weather + V5 directed road + FCD + orders','PARTIAL_HOLD','82,620 tasks and paired scenarios passed; weather/FCD/road source bytes missing from current runtime','5-month raw weather, FCD 345 nodes, directed road for A/B/C','Full raw-byte hash, interval, topology, travel-time and missingness QA'),
 ('S08','Strong petrol M0 multi-stop route + emissions','CODE_TESTED_HOLD','19 algebraic unit tests passed, not an observed road operation','validated directed road, fuel, idle, cost and vehicle schedule','Do not compute route/km/fuel/CO2 from straight lines'),
 ('S09','DJI and Wingcopter mission energy','SCREEN_TESTED_HOLD','18 unit tests passed; load/edge screening; no validated mission-energy result','weather at event time, aircraft power/load/return/reserve and charging data','Prevent max-range assumptions from becoming measured kWh'),
 ('S10','5-mode matched dispatch experiment','NOT_RUN','22,950 five-mode run keys ready; no dispatch results','S07, S08, S09 release + calibrated station capacities','Real completed task and physical trip/flight ledger'),
 ('S11','WTW/TTW emissions, cost, min-carbon feasibility','NOT_RUN','no operational kgCO2e or real Pareto results','S10 physical ledger, harmonized petrol/electric scope and factors','Must compare all modes on same demand and service/cost constraints'),
 ('S12','Robustness, statistical inference, SCI outputs','NOT_RUN','no final effect distributions/plots','S10 S11 results, independent seed/day scenario units','Check selection bias, demand uncertainty, geography/weather mismatch'),
]
writecsv(reports/'V5_STAGE_STATUS_AND_REMAINING_WORK.csv',
 [{'stage':x[0],'scope':x[1],'state':x[2],'verified_output':x[3],'missing_inputs':x[4],'release_requirement':x[5]} for x in status],
 ['stage','scope','state','verified_output','missing_inputs','release_requirement'])
(reports/'V5_AUDIT_SUMMARY.json').write_text(json.dumps({'date':'2026-10-30','space':'V5_FROZEN_68','source_git_commit':commit,'realized_counts':counters,'suites':test_records,'stages':[{'stage':r[0],'state':r[2]} for r in status]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Add tools from latest stages in usable form; no rewriting historical code.
for s,d in [
 ('CIQ_V5_S07_Simulation_Blocks_20261030/code/recover_pinned_sources.py','recover_pinned_sources_original.py'),
 ('CIQ_V5_S07_Simulation_Blocks_20261030/code/read_weather_workbooks.py','read_weather_workbooks.py'),
 ('CIQ_V5_S07_Simulation_Blocks_20261030/code/acquire_v5_abc_directed_osm.py','acquire_v5_abc_directed_osm.py'),
 ('CIQ_V5_S07_Simulation_Blocks_20261030/code/validate_s07_external_data.py','validate_s07_external_data.py'),
 ('CIQ_V5_Next_Stage_S08_Petrol_And_Payload_20261030/code/m0_petrol_core.py','m0_petrol_core.py'),
 ('CIQ_V5_Next_Stage_S08_Petrol_And_Payload_20261030/code/m0_multi_order_dispatch.py','m0_multi_order_dispatch.py'),
 ('CIQ_V5_S09_Aircraft_Mission_Preflight_20261030/code/mission_energy_core.py','mission_energy_core.py'),
 ('CIQ_V5_S09_Aircraft_Mission_Preflight_20261030/code/weather_event_contract.py','weather_event_contract.py'),
 ]:
 cp(ROOT/s,code/d)

# Print a structured and scientifically strict project audit.
md=f'''# CIQ V5 空间—天气—交通—合成订单—运营减排：全工程独立复核

**审查日期：** 2026-10-30  
**唯一活动空间基准：** V5 ONE WMP228，68 个节点。不得改用 V3 的 69 点及其中的 A_N10。  
**冻结任务：** 82,620 条条件性合成订单；30 种子 × 153 天 = 4,590 个独立种子—日期场景，每场景 18 条任务；5 种模式共 22,950 个待运行键。

## 核查结论

**GitHub 确实已经包含五个月天气工作簿、五个月 345 点交通数据以及 A/B 有向 OSM 道路文件。** 不是“未上传”。本环境目前只访问到了文件列表、可读取的小型元数据及已挂载的 V5 模型文件，未取得大型原始字节；直接访问 raw.githubusercontent.com 提示 DNS 无法解析。**因此只能确认资料位置和历史审计，不能冒充已独立重新计算天气与交通原始数值。**

## 本轮真实复算结果

- V5 实际节点：**{counters['node_count']}**，各区分布：`{counters['zone_counts']}`；ID 唯一。
- 冻结任务：**{counters['task_count']:,}**；任务 ID 无重复，端点均属于活动 V5 节点（孤立节点仍保留）。
- 场景：**{counters['seed_day_scenarios']:,}** 个种子—日期组，全部 18 条订单。
- 五模式任务配对键：**{counters['five_mode_run_keys']:,}**；全部 **{counters['per_run_five_modes_and_one_hash']:,}** 个场景均具有 5 个模式及同一 task-set SHA-256。
- S09 技术筛查：**{counters['task_screen_rows']:,}** 条逐单记录；`direct_candidate_status` 计数 `{counters['direct_edge_classes']}`；无任何已实证任务耗电值。
- 当前正式配送结果：S07 任务 `NOT_COMPUTED`，S10 模式结果 `NOT_COMPUTED`，**未产生可投稿的节时率、燃油量、成本或减排率**。
- 本次**实际重新运行** 4 组模型/输入测试，共 **{counters['reexecuted_tests_total']}** 项；全部 {'通过' if counters['reexecuted_suites_all_pass'] else '存在失败'}。这些是模型逻辑与输入守恒测试，不是外部交通或能耗校准。

## 已确认的源数据在 GitHub

- 五个月天气 `data/weather_2026/processed/JB_SG_Weather_2026_05.xlsx` 至 `09.xlsx`；有独立月度 `manifest.json`。
- 五个月 FCD `02_base_and_traffic_data/traffic_data/JB_CIQ_E01_corrected_five_month_traffic_data_345nodes_2026-05_09.csv.gz`，以及配套 G1–G5 分组 ZIP、统计与节点主表。
- 历史 A/B OSM 有向路网位于 `03_gis_and_road_network/road_network_project/JB_CIQ_E02_roadnet_V4_6/outputs/`，分为 directed edges 与 road graph nodes。
- 历史 Stage6 的 89,526 条模式级记录（29,842 个合成订单×3模式）不等于 V5 的 82,620 个订单。

## 道路与气象的关键质量边界

历史 E02 审计报告的数字为 **345 个 FCD 节点 × 3,672 小时 = 1,266,840 条源数据记录**，其中 `speed_missing=125,230`、`NONPOSITIVE=55`；这些是**历史审计报告记录的数字**，不是本轮重新读取大型原件后得到的测量结果。历史 A/B OSM 共有约 28.2 万条有向边，但 37/128 条参考 OD 存在不可直接采用的路径异常；转向限制、方向对齐与导航时效未通过最终验收。现在也没有覆盖 V5 C 区并验证接入的全区道路图。

五个月天气历史质量汇总显示：ERA5 的四参考点实际只有两种返回网格坐标，ERA5–NASA 的月降雨相关性非常低；需要逐小时原表、时间戳、降水区间及站点级空间误差审查。任何自动映射或重采样都不能当作四处独立气象观测。

## 剩余研究实验

详见 `V5_STAGE_STATUS_AND_REMAINING_WORK.csv`：

1. **S07（尚未释放）**：14 个 GitHub 关键文件按固定提交恢复、完整字节核验，验证 153 天降水风场与交通时序；建立 V5 全 A/B/C 有向交通路径与车辆入场模型。
2. **S08（模型通过测试但实证未运行）**：以同一场景需求完成可行的多站点汽油车 M0 路由，收集油耗怠速与成本参数，生成物理车次账本。
3. **S09（技术筛查已完成但能耗未标定）**：DJI 与 Wingcopter 在不同载重、风雨、起降/返航、备用电量与充电效率下的任务耗电区间。
4. **S10（未运行）**：4,590 个场景 × 5 模式配对调度，包含地面接驳、共享车次、起降天气查询、排队与失败回退，生成同分母的逐订单及物理行程结果。
5. **S11（未运行）**：统一运营能源碳核算边界、服务/成本阈值，构建减少汽车里程与增加 UAV 充电量的减排临界面及可行 Pareto 集。
6. **S12（未运行）**：跨种子/日期/需求假设、天气网格、汽油参数、机型功率等联合稳健性检验，形成可追溯 SCI Results 和图表。

## 文件范围与执行方式

`01_ACTIVE_V5_FROZEN/` 内为**唯一允许进入新实验的空间与订单数据**；`02_STAGE_PACKAGES_CURRENT_V5/` 保留最新阶段的完整代码、输入、输出与测试 ZIP；`03_HISTORICAL_PRE_V5_READ_ONLY/` 为全量可用历史审计文件，**不得用来替换最新数据**。

**本交付包含当前会话可实际读取的全部阶段 ZIP、V5 冻结源工程、各阶段核心 CSV 与代码。GitHub 上的大型天气、交通和 OSM 原件未包含在此 ZIP，因为当前环境未取得其文件字节；路径与版本信息收录在 `04_SOURCE_RECOVERY_AND_GITHUB_INVENTORY/`。**

所有缺失资料保持 HOLD；本文件不是 S07–S12 的最终科学验收或实际减排结果。
'''
(reports/'FULL_PROJECT_AUDIT_CN.md').write_text(md,encoding='utf8')

readme='''# CIQ V5 SCI 全项目归档包（2026-10-30）\n\n请先阅读 `05_AUDIT_REPORTS_AND_TEST_LOGS/FULL_PROJECT_AUDIT_CN.md`。\n\n- 01_ACTIVE_V5_FROZEN：最新版 V5 原始 QGIS ZIP 和已实际生成的冻结节点、订单、配对清单、无人机筛查 CSV。\n- 02_STAGE_PACKAGES_CURRENT_V5：当前有效的 S06、S07、S08、S09 完整阶段 ZIP（内含代码、测试、审计）。\n- 03_HISTORICAL_PRE_V5_READ_ONLY：本工作区全部历史阶段 ZIP，仅供审计追溯，禁止当作 V5 现行输入。\n- 04_SOURCE_RECOVERY_AND_GITHUB_INVENTORY：GitHub 14 份天气/道路/交通/旧订单关键原件路径、提交版本、预期大小、Git blob 和可能存在的 SHA256。**不是已下载原件**。\n- 05_AUDIT_REPORTS_AND_TEST_LOGS：本次独立实际复核输出和四组测试日志。\n- 06_RUNNABLE_TOOLS：原有 S07–S09 模型/恢复/验收工具及新版本固定校验工具。\n\n正式减排数据仍 HOLD；不得使用历史电动汽车 Stage6 的电力排放模拟作为汽油车 M0 结果。\n'''
(OUT/'README_FIRST_CN.md').write_text(readme,encoding='utf8')

# New recovery tool also accepts a local repository directory (e.g. user's Windows checkout),
# avoiding unnecessary repeated downloading; both modes enforce pinned blob and size.
recover='''#!/usr/bin/env python3
"""Recover pinned GitHub sources from a local GitHub checkout or GitHub raw; no fabricated output.
Windows examples:
 python 06_RUNNABLE_TOOLS/recover_all_14_sources.py --repo-root "C:/Users/DELL/source/JB-CIQ-Drone-Logistics-Research-20261027"
 python 06_RUNNABLE_TOOLS/recover_all_14_sources.py --download
"""
from pathlib import Path
import argparse,json,csv,hashlib,urllib.request,shutil
ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'04_SOURCE_RECOVERY_AND_GITHUB_INVENTORY/SOURCE_FILES_PINNED_14.json'
REPO='tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027'
def digest(path,alg):
 h=hashlib.new(alg); size=path.stat().st_size
 if alg=='sha1':h.update(f'blob {size}\\0'.encode())
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root');ap.add_argument('--download',action='store_true');ap.add_argument('--out',default=str(ROOT/'RECOVERED_GITHUB_DATA'));a=ap.parse_args()
 idx=json.loads(INDEX.read_text('utf-8'));base=Path(a.out);base.mkdir(parents=True,exist_ok=True)
 logs=[]
 for x in idx['files']:
  dest=base/x['path'];dest.parent.mkdir(parents=True,exist_ok=True)
  status='HOLD_NOT_PRESENT';error=''
  if a.repo_root:
   src=Path(a.repo_root)/x['path']
   if src.exists() and not dest.exists():shutil.copy2(src,dest)
  elif a.download and not dest.exists():
   url=f'https://raw.githubusercontent.com/{REPO}/{idx["git_commit"]}/{x["path"]}'
   try:
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CIQ-v5-S07-audit'}),timeout=90) as rd, dest.with_suffix(dest.suffix+'.tmp').open('wb') as w:shutil.copyfileobj(rd,w)
    dest.with_suffix(dest.suffix+'.tmp').replace(dest)
   except Exception as e:
    error=str(e);dest.with_suffix(dest.suffix+'.tmp').unlink(missing_ok=True)
  actual='';sha256=''
  if dest.exists():
   try:
    actual=digest(dest,'sha1');sha256=digest(dest,'sha256')
    good=(dest.stat().st_size==x['size'] and actual==x['git_blob'] and (not x.get('sha256') or sha256==x['sha256']))
    if good and dest.suffix.lower() in {'.xlsx','.zip'}:
     import zipfile
     try:
      with zipfile.ZipFile(dest) as z:good=z.testzip() is None
     except Exception:good=False
    status='PASS_BYTES_HASH' if good else 'FAIL_VERSION_OR_INTEGRITY'
   except Exception as e:status='FAIL_READ';error=str(e)
  logs.append({'file':x['name'],'status':status,'expected_blob':x['git_blob'],'actual_blob':actual,'actual_sha256':sha256,'error':error})
 logdir=ROOT/'05_AUDIT_REPORTS_AND_TEST_LOGS';logdir.mkdir(exist_ok=True)
 (logdir/'SOURCE_RECOVERY_LATEST.json').write_text(json.dumps(logs,indent=2,ensure_ascii=False),'utf-8')
 with (logdir/'SOURCE_RECOVERY_LATEST.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(logs[0]));w.writeheader();w.writerows(logs)
 print(json.dumps({'source_files':len(logs),'PASS_BYTES_HASH':sum(x['status']=='PASS_BYTES_HASH' for x in logs),'HOLD':sum(x['status']!='PASS_BYTES_HASH' for x in logs)},ensure_ascii=False))
 return 0 if all(x['status']=='PASS_BYTES_HASH' for x in logs) else 2
if __name__=='__main__':raise SystemExit(main())
'''
(code/'recover_all_14_sources.py').write_text(recover,encoding='utf8')
launcher='''@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: RUN_WINDOWS_RECOVER_ALL.cmd "C:\\path\\to\\JB-CIQ-GitHub-Repo"
  echo Or run: python 06_RUNNABLE_TOOLS\\recover_all_14_sources.py --download
  exit /b 2
)
python 06_RUNNABLE_TOOLS\\recover_all_14_sources.py --repo-root "%~1"
if errorlevel 1 (
  echo Some source files are MISSING or FAILED verification. See 05_AUDIT_REPORTS_AND_TEST_LOGS.
  exit /b 2
)
echo Source bytes verified; scientific weather and V5 road QA must still be performed.
'''
(OUT/'RUN_WINDOWS_RECOVER_ALL.cmd').write_text(launcher,encoding='utf8')

# Scientific task counts QA record and SHA256, excluding own manifest to avoid self hash cycle.
allfiles=[p for p in OUT.rglob('*') if p.is_file() and p.name!='FULL_PACKAGE_SHA256_MANIFEST.csv']
manifest=[]
for f in sorted(allfiles):
 manifest.append({'path':str(f.relative_to(OUT)).replace('\\','/'),'size_bytes':f.stat().st_size,'sha256':hashfile(f)})
writecsv(OUT/'FULL_PACKAGE_SHA256_MANIFEST.csv',manifest,['path','size_bytes','sha256'])
summary={'output_dir':str(OUT),'files':len(allfiles)+1,'stage_zip_files':len(list(arch.glob('*.zip'))),'historical_zip_files':len(list(historical.glob('*.zip'))),'raw_main_rows':counters,'tests':test_records,'original_v5_sha256':counters['V5_archive_zip_sha256']}
(ROOT/'CIQ_V5_FULL_DELIVERY_AUDIT_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2)[:5600])
