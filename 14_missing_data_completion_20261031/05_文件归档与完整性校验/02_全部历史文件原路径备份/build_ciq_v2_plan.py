from pathlib import Path
import json,csv,hashlib,zipfile,shutil,datetime,textwrap,os
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path('/mnt/data/CIQ_V2_Carbon_First_Experiment_Plan_20261030')
if ROOT.exists():shutil.rmtree(ROOT)
ROOT.mkdir(parents=True)
D='2026-10-30'
COMMIT='4569817b8145efe2ae06f4b21addc1986f971c12'
REPO='https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027'

def put(path,txt):
    f=ROOT/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(txt.strip()+"\n",encoding='utf-8');return f

def write_json(path,obj):return put(path,json.dumps(obj,ensure_ascii=False,indent=2))
def write_csv(path,header,rows):
    f=ROOT/path;f.parent.mkdir(parents=True,exist_ok=True)
    with f.open('w',encoding='utf-8-sig',newline='') as fd:
        w=csv.writer(fd);w.writerow(header);w.writerows(rows)
    return f

def blank_csv(path,header):write_csv(path,header,[])

stages=[
('V2_S06','三分区空间网络冻结','Spatial network acceptance', 'RQ1',
 ['以最新三分区 QGIS 工程为唯一新版空间源；不得用旧19点替换新版坐标','导出所有点/线/区及原始图层 CRS、稳定 ID、所属国家、证据状态','检查重复 ID、空几何、坐标精度、孤立点、起终点引用和道路接入','叠加 CAAM/CAAS 适用空域、禁飞/待审批分层与边界；不得把直线候选当合法航线','完成历史19点→新点 ID 对照（保留 deleted/new/modified）；冻结源文件哈希'],
 [('qgis_project_bundle.zip','ZIP','最新 QGIS QGZ/QGS 与全部本地依赖；不得只提交地图图片'),('nodes.csv','CSV','完整新版节点清单'),('edges.csv','CSV','完整新版候选连接与类别'),('spatial_screen.csv','CSV','道路接入及空域/场地证据分类'),('legacy_crosswalk.csv','CSV','历史节点与新版节点关系')],
 [('nodes_checked.csv','可核验节点及空间证据'),('edges_checked.csv','可核验连接及端点'),('spatial_exclusions.csv','硬排除/待审批/情景适用分别编码'),('spatial_freeze.json','CRS/输入 SHA/统计/人工验收签核')],
 ['每条 node_id 唯一且坐标有效','每条 edge 的起终点存在','CRS 与跨国边界口径明确','所有未知审批保留 UNKNOWN，不自动通过','空间输入哈希+版本冻结、人工认可'],
 '未取得新版 QGIS 原件。'),
('V2_S07','任务—气象—交通同口径冻结','Paired tasks & time-aligned weather/road','RQ1,RQ2',
 ['只选一种冻结合成需求总体（可优先沿用 Stage6 的29,842订单，经新空间映射后重新审定）','为所有 M0/M1/M2 保留同一 task_id、seed、载重、时间戳、目的地与期限','用有向 OSM OD 路径匹配交通小时；37 条旧异常仅作为候选、未经复核不得自动修复','天气按计划起飞/飞行小时读取；验证降雨变量、单位、时区、ERA5 网格重复和 NEA 缺口','跨境 OD 另建任务群；无真实等待数据时显式给出情景区间而非实测值'],
 [('frozen_tasks.csv','CSV','不可变任务样本与任务总体ID'),('road_od_hourly.csv','CSV','方向级道路 OD/小时代理与证据状态'),('weather_hourly.csv','CSV','降雨、风向/风速、时区、站点或网格来源'),('cross_border_wait.csv','CSV','国境等候实测/情景分离')],
 [('paired_task_manifest.csv','任务总体与种子/日期哈希'),('time_join_QA.csv','天气道路时间戳覆盖及缺测'),('road_access_repair_log.csv','可达性候选/实际修复逐条追踪'),('demand_freeze.json','可评价分母及排除理由')],
 ['同一 task_id 在各模式只定义一次','无跨日期或不同订单总体混合','未验证 37 OD 不视为 PASS','无法计算的数值为缺失而非 0','每条跨境任务有实际国家对及排队证据类型'],
 '有历史天气/订单资料，但新空间任务映射及跨境 OD 未冻结。'),
('V2_S08','汽油车纯道路 M0 基线','Gasoline-car M0 benchmark','RQ2,RQ3',
 ['以汽油配送车辆为主基线；柴油可作敏感性，不以旧电动车 M0 替代','冻结车型、车辆质量/容量、载荷、城市/高速油耗、燃油排放因子、价格及来源版本','统一包括去程、返程、整车共享里程、怠速、排队、站点作业及运营人员时长','路网和车速驱动里程/时间，独立于机型；缺油耗实测时设置文献校准区间并标注情景','核验车辆/旅行单位: L/100km、L/h、MYR/L、kg CO2/L，按燃油体积和类型分项'],
 [('vehicle_registry.csv','CSV','汽油车型/容量/服务配置及证据'),('fuel_parameters.csv','CSV','油耗/怠速/油品密度/热值/因子可追溯参数'),('road_trips_m0.csv','CSV','基线去返程、共享路程、车次事件及证据'),('fuel_costs.csv','CSV','燃油价格和非燃油成本数据源')],
 [('m0_trip_ledger.csv','车次级油耗及 TTW CO2 台账'),('m0_order_results.csv','逐任务时间/完成/按时/费用与分摊'),('m0_QA.json','单位、路程、队列和误差检查'),('m0_baseline_freeze.json','M0 定义及哈希')],
 ['以汽油车为 M0 且车辆类型明确','油耗、怠速、燃油 CO2 因子具有出处/不确定性','所有去返程和共享路程不重复计数','M0 与后续 M1/M2 使用同一任务与车队公平性协议','不能把旧电动车 kgCO2e 当汽油 CO2'],
 '燃油车具体车型及油耗校准仍待冻结。'),
('V2_S09','双无人机能耗—天气—航路审计','DJI and Wingcopter energy & eligibility','RQ1,RQ2,RQ3',
 ['明确两机型: DJI FlyCart 30 双电池货箱和 Wingcopter 198 Cargo，型号版本不得混用','区分官方标称载重/航程与实际任务可用能量；禁止用最大航程反推 kWh/km','建载荷—飞行阶段（起降/巡航/悬停/返航）—风场—备用电量—充电效率模型','分别审查雨量/阵风/高度/禁航条件、空域时效、航线长度与合法性；不将许可未知说成获批','必须冻结可信任务能耗区间及来源；不足时仅输出几何上界和敏感性，阻止碳效益排名'],
 [('uav_models.csv','CSV','型号、官方规格、证据与适用工况'),('uav_energy_parameters.csv','CSV','功耗/能量/储备/充电参数和区间来源'),('uav_candidate_missions.csv','CSV','载荷/路径/航时/天气与空间筛查'),('regulatory_scenarios.csv','CSV','批准/禁飞/待审批/仅模拟四类情景')],
 [('uav_mission_energy.csv','两机型逐航次电耗范围'),('uav_weather_restrictions.csv','可飞性和天气回退原因'),('airspace_scenario_QA.csv','限制与科研情景分开'),('uav_energy_freeze.json','任务模型与假设的版本锁定')],
 ['两机型分别识别且不能用470 W旧泛化模型','任务能耗包含带载/空载/起降/返航/充电损失','每条任务天气基于实际起飞/返航时刻','空域状态明确标记、未授权不能称可部署','能耗缺口未闭合则阻止定量减排排序'],
 '官方规格已核实，但完整任务能耗参数尚未冻结。'),
('V2_S10','M1/M2 混合物流统一仿真','Road–air multimodal dispatch','RQ2,RQ3',
 ['运行 M0、M1 固定站点/转运、M2 车辆—无人机同步会合；两机型各独立情景','同订单总体、同车辆类型/资源配置规则、天气样本与道路基线；固定随机数种子','精确追踪转运、排队、充电、更换电池、往返、车辆回收与无人机失败后的地面回退','按物理行程 ID 计车次；共享批量运输只记一次总行程再分摊；任务不因无人机失败而从分母删除','先同日小样本逐事件审计，再运行冻结的30种子×5日期；跨境另设可溯源分层'],
 [('dispatch_config.json','JSON','车辆/无人机/服务资源及策略'),('paired_tasks.csv','CSV','完全相同的任务输入和样本标识'),('road_trip_library.csv','CSV','可用道路行程与小时条件'),('uav_mission_library.csv','CSV','可用航次与机型能耗证据')],
 [('event_log.csv','逐事件日志：等待、装卸、起飞、回收、兜底'),('trip_ledger.csv','唯一物理车辆/航次/共享干线行程'),('order_mode_results.csv','M0/M1/M2逐任务完成、按时、费用分项'),('dispatch_QA.json','同订单/容量/时间/服务公平性检查')],
 ['每个 task × scenario × mode 一条最终结局','物理车次/航次 ID 唯一且共享里程只计一次','天气禁飞回退时仍保留任务且有真实耗时','同等需求及明确车队资源约束','小样本已验收且30种子运行可复现'],
 '依赖 V2-S06~09 数据及标定；不允许提前运行。'),
('V2_S11','运营碳排放—成本与最小碳优化','Carbon-cost-service optimization','RQ3',
 ['定义主口径：燃油车辆 TTW CO2 + 充电电力 location-based CO2，单位一致；CO2e 仅在覆盖 CH4/N2O/口径统一后计算','按充电地分别应用 MY/SG 电网因子；车队燃油、怠速、无人机充电、转运及共享行程均纳入','统一输出按总输入订单、完成订单、共同服务队列、真实车次四种分母，禁止只挑 UAV 成功订单','设定服务不能下降、按时率与成本上限为约束；成本容忍度设为显式情景且不强行推出有减排方案','逐种子寻找满足约束的最低碳 M1/M2/混合配比，若不存在则如实输出 infeasible'],
 [('trip_ledger.csv','CSV','唯一燃油车/无人机/充电车次原始活动量'),('order_mode_results.csv','CSV','可评价的同订单模式结果'),('emission_factor_register.csv','CSV','燃料及电力因子、气体、国家、年份和不确定性'),('cost_parameter_register.csv','CSV','成本参数 MYR、证据和区间'),('optimization_constraints.json','JSON','服务/准时/成本约束和情景')],
 [('operational_carbon_ledger.csv','燃油与电力独立碳账本'),('matched_comparison.csv','服务匹配时间/成本/碳变化'),('pareto_feasible.csv','可行 Pareto 情景/不可行原因'),('emission_QA.json','单位和跨模式共享车次复算')],
 ['CO2 与 CO2e 口径不可混用','MY/SG 供电按真实地点分账','排放相同物理车次不重复计','低碳结论必须满足已冻结的服务与成本约束','成本/能耗/排放因子缺失禁止输出净减排'],
 '依赖 V2-S08~10 已批准的原始车辆/航次账本。'),
('V2_S12','统计、敏感性与 SCI 图表定稿','Uncertainty, figures & independent replication','RQ1,RQ2,RQ3',
 ['以30个独立随机种子为主要重采样单位，不把89,526模式记录当独立样本','按区域、车型、时段、天气、成本约束分层报告平均差异及区间，分母解释透明','进行油耗、任务功率、返航备用、天气限制、地面拥堵、充电国别及跨境排队的联合敏感性','绘制 Fig.3 模型/空间、Fig.4 道路气象、Fig.5 服务、Fig.6 碳成本、Fig.7 Pareto/不确定性，全部从机器可读结果直接产生','独立复跑、代码和所有输入 SHA256、原始/生成数据版本冻结，整理 Results、Discussion、Limitations'],
 [('paired_run_results.csv','CSV','按seed/date/zone/vehicle/uav/mode的完整账本汇总'),('uncertainty_draws.csv','CSV','有来源的联合参数不确定性抽样'),('release_qa.json','JSON','所有前序阶段签核和版本'),('figure_data.csv','CSV','每个子图真实数据源表')],
 [('rq1_rq2_rq3_summary.csv','论文三问逐条量化结果'),('sensitivity_summary.csv','风雨/拥堵/油耗/能耗/成本边界'),('figures/','Fig.3–Fig.7正式科研图'),('replication_report.md','可重复执行日志和引用/限制')],
 ['不将订单行数当独立样本数','不发表未授权飞行/实际净减排的断言','所有图表数值与输出CSV一致','最后一个seed每项计算可重放','公开汇总无密钥、无隐私、来源许可检查通过'],
 '等待前序阶段正式数值结果；当前只可冻结统计方案。')
]

out_index=[]
for code,cn,en,rq,steps,inputs,outputs,gates,note in stages:
    base=Path('STAGES')/code
    input_rows=[]
    for fn,typ,desc in inputs: input_rows.append([fn,typ,desc,'', 'MISSING','', ''])
    write_csv(base/'INPUT_REGISTER.csv',['filename','format','purpose','sha256','status','provenance_url','reviewer'],input_rows)
    gate_rows=[[f'{code}-G{i:02d}',g,'BLOCKED','',''] for i,g in enumerate(gates,1)]
    write_csv(base/'QA_GATES.csv',['gate_id','acceptance_criterion','status','evidence_path','reviewer'],gate_rows)
    out_rows=[[n,desc,'NOT_PRODUCED',''] for n,desc in outputs]
    write_csv(base/'OUTPUT_REGISTER.csv',['filename','definition','status','sha256'],out_rows)
    write_json(base/'STAGE_CONTRACT.json',{
        'stage':code,'stage_name_cn':cn,'purpose_en':en,'research_questions':rq,
        'inputs':[{'filename':fn,'type':typ,'purpose':desc} for fn,typ,desc in inputs],
        'outputs':[{'filename':x,'purpose':desc} for x,desc in outputs],
        'release_gates':gates,
        'expected_status':'BLOCKED_UNTIL_REAL_INPUTS_ACCEPTED',
        'historical_git_commit':COMMIT,
        'review_rule':'Automatic schema gate is not scientific approval; release requires human evidence review plus frozen source hashes.'})
    readme=f'''# {code} — {cn} / {en}

- 状态：**HOLD / PLANNED**。本阶段未运行任何正式数值实验。
- 论文对应：{rq}。
- 历史来源只读提交：`{COMMIT}`，绝不覆盖旧 Stage 3–8。
- 目前阻断：{note}

## 1. 执行步骤（不得跳过）
'''+"\n".join(f'{i}. {x}' for i,x in enumerate(steps,1))+f'''

## 2. 输入数据和证据

| 输入文件 | 格式 | 要求 |
|---|---|---|
'''+"\n".join(f'| `{n}` | {t} | {d} |' for n,t,d in inputs)+'''

填写 `INPUT_REGISTER.csv` 的实际源路径/校验信息，放入本阶段 `inputs/`。数据模板仅含列名，不得当实际数据使用。

## 3. 预期产物
'''+"\n".join(f'- `{n}`：{d}' for n,d in outputs)+f'''

## 4. 放行检查
'''+"\n".join(f'- [ ] {x}' for x in gates)+f'''

## 5. 独立验收方法

项目根目录执行：

```bash
python tools/verify_stage.py --root . --stage {code}
python tools/generate_sha256_manifest.py --directory STAGES/{code} --output STAGES/{code}/SHA256_MANIFEST.csv
```

自动检查仅代表输入文件**结构有效**。`QA_GATES.csv` 里的 BLOCKED 不会被自动变成真实科学验收 PASS。

## 6. 上传 GitHub

将本阶段目录连同 `tools/`、`protocol/`、`references/` 上传至：`11_v2_carbon_first_experiments/{code}/`（建议新目录）；**不要覆盖**旧 `10_experiment_results/` 归档。

**论文声明边界：** {note}
'''
    put(base/'README_CN.md',readme)
    write_json(base/'release_record.json',{'stage':code,'scientific_approval':'HOLD','reviewer':'','approval_date':'','reviewed_source_sha256_manifest':'','notes':'No scientific release has been granted.'})
    (ROOT/base/'inputs').mkdir(parents=True,exist_ok=True)
    put(base/'inputs'/'README.txt','Place verified real input files here. Header-only templates are under template_inputs and must not be treated as data.')
    (ROOT/base/'template_inputs').mkdir(parents=True,exist_ok=True)
    # data templates with named expected schemas; built separately below
    out_index.append([code,cn,rq,'HOLD',str(base/'README_CN.md'),'',''])

# detailed template schemas
schemas={
'V2_S06':{
'nodes.csv':'node_id zone country longitude latitude node_type site_status land_access_status source_layer source_feature_id'.split(),
'edges.csv':'edge_id origin_node_id destination_node_id edge_type country_pair distance_km geometry_status regulatory_status source_layer'.split(),
'spatial_screen.csv':'edge_id authority airspace_status site_status obstacle_status evidence_date source_url'.split(),
'legacy_crosswalk.csv':'legacy_node_id v2_node_id mapping_status decision_reason source_sha'.split()},
'V2_S07':{
'frozen_tasks.csv':'task_id task_population_id seed date_sgt release_time_sgt deadline_time_sgt origin_node_id destination_node_id origin_country destination_country zone payload_kg parcel_count'.split(),
'road_od_hourly.csv':'od_id origin_node_id destination_node_id time_sgt distance_km travel_time_min connectivity_status traffic_source traffic_status'.split(),
'weather_hourly.csv':'weather_id grid_cell_id time_sgt latitude longitude rain_mm_hour wind_10m_ms wind_dir_deg gust_ms source qc_status'.split(),
'cross_border_wait.csv':'corridor country_from country_to time_sgt wait_min evidence_class source_url'.split()},
'V2_S08':{
'vehicle_registry.csv':'vehicle_id vehicle_class fuel_type capacity_kg country source_url status'.split(),
'fuel_parameters.csv':'vehicle_id parameter value unit lower upper source_url evidence_class status'.split(),
'road_trips_m0.csv':'trip_id task_population_id mode seed time_sgt vehicle_id distance_km drive_min idle_min shared_allocation_key evidence_status'.split(),
'fuel_costs.csv':'country time_period price_myr_per_liter labor_myr_per_min other_cost_myr source_url evidence_class'.split()},
'V2_S09':{
'uav_models.csv':'uav_model configuration payload_max_kg nominal_range_km battery_nominal_kwh max_wind_resistance_ms source_url reference_conditions status'.split(),
'uav_energy_parameters.csv':'uav_model parameter value unit lower upper source_url evidence_class status'.split(),
'uav_candidate_missions.csv':'mission_id task_id uav_model launch_node_id delivery_node_id recovery_node_id takeoff_time_sgt payload_kg distance_km weather_id scenario_status'.split(),
'regulatory_scenarios.csv':'scenario_id country authority corridor_status legal_status data_valid_date source_url'.split()},
'V2_S10':{
'paired_tasks.csv':'task_id task_population_id seed release_time_sgt deadline_time_sgt origin_node_id destination_node_id payload_kg'.split(),
'road_trip_library.csv':'trip_id mode task_population_id origin_node_id destination_node_id depart_time_sgt distance_km travel_min fuel_l source_status'.split(),
'uav_mission_library.csv':'mission_id uav_model task_population_id takeoff_time_sgt duration_min wall_kwh energy_quality scenario_status'.split()},
'V2_S11':{
'trip_ledger.csv':'trip_id task_population_id seed scenario mode vehicle_type uav_model distance_km fuel_l idle_fuel_l wall_charge_kwh_my wall_charge_kwh_sg trip_owner_id evidence_quality'.split(),
'order_mode_results.csv':'task_id task_population_id seed date_sgt zone scenario mode uav_model vehicle_type completed on_time door_to_door_min cost_myr fallback_reason'.split(),
'emission_factor_register.csv':'factor_id factor_name country fuel gas unit value year uncertainty source_url evidence_class status'.split(),
'cost_parameter_register.csv':'parameter_id parameter unit value lower upper currency_year source_url evidence_class status'.split()},
'V2_S12':{
'paired_run_results.csv':'task_population_id seed date_sgt zone scenario mode uav_model vehicle_type demand_n completed_n ontime_n cost_myr operating_co2_kg evidence_quality'.split(),
'uncertainty_draws.csv':'draw_id factor_id seed value source_dist uncertainty_class'.split(),
'figure_data.csv':'figure_panel source_file metric unit seed zone mode evidence_hash'.split()}}
for stage,rows in schemas.items():
    for name,cols in rows.items():blank_csv(Path('STAGES')/stage/'template_inputs'/name,cols)

# JSON input templates with deliberately-null uncalibrated settings
write_json('STAGES/V2_S10/template_inputs/dispatch_config.json',{
    'status':'NOT_CALIBRATED','random_seeds':30,'sample_dates':['2026-05-15','2026-06-15','2026-07-15','2026-08-15','2026-09-15'],
    'task_population_id':None,'vehicle_capacity_kg':None,'uav_count':None,'charger_count':None,
    'transfer_time_min':None,'fallback_policy':'GROUND_WITH_ACTUAL_DELAY_NOT_ASSUMED_ZERO',
    'dispatch_strategy':'TO_BE_FROZEN_FROM_EXPERIMENT_PROPOSAL',
    'note':'Historical five dates are candidate reference only, not equivalent to five complete months.'})
write_json('STAGES/V2_S11/template_inputs/optimization_constraints.json',{
    'status':'PRE_REGISTER_BEFORE_MAIN_RUN',
    'service_min_relative_to_M0':None,
    'on_time_min_relative_to_M0':None,
    'max_cost_ratio':None,
    'cost_ratio_sensitivity_proposals':[1.0,1.05,1.10,1.20],
    'grid_country_split_required':True,
    'if_no_feasible_solution':'REPORT_INFEASIBLE_NO_OPTIMALITY_CLAIM'})
write_json('STAGES/V2_S12/template_inputs/release_qa.json',{
    'status':'BLOCKED','all_upstream_scientific_approvals':'HOLD','historical_commit':COMMIT})

write_json('protocol/MASTER_PROTOCOL_V2.json',{
    'project':'CIQ Johor-Singapore Road-Air Low Carbon Logistics SCI','version':'V2_20261030_PLAN',
    'scope':'conditional scenario simulation; not proven deployment',
    'historical_baseline_git_commit':COMMIT,
    'spatial_source':'latest three-zone QGIS project, hash and exact boundary pending',
    'research_questions':{
        'RQ1':'Where can candidate road-air logistics nodes and corridors be screened given geography, technology and regulation?',
        'RQ2':'When, under weather and traffic, is multimodal delivery more reliable or timely than a paired petrol-road baseline?',
        'RQ3':'Can carbon-minimizing feasible multimodal combinations reduce operational CO2 without losing service and within explicit cost constraints?'},
    'modes':{
        'M0_PETROL':'road-only gasoline delivery vehicle (primary baseline)',
        'M1_DJI':'fixed-hub gasoline feeder + DJI FlyCart 30',
        'M1_WING':'fixed-hub gasoline feeder + Wingcopter 198 Cargo',
        'M2_DJI':'gasoline vehicle + synchronized DJI FlyCart 30 rendezvous',
        'M2_WING':'gasoline vehicle + synchronized Wingcopter 198 Cargo'},
    'sensitivity':'diesel road-only baseline only separately; energy and weather intervals for each UAV',
    'task_population_policy':'same frozen task IDs; do not concatenate Stage2 918000 with Stage6 29842; remap and hash any revised demand',
    'historical_demand_candidate':'Stage6 29842 synthetic order population across 30 seeds, five dates; no claims of real orders or 5-month coverage',
    'mode_fairness':'road vehicle assumptions, capacity, infrastructure and task cohort matched where physically meaningful; mixed modes must count feeder trucks, transfer and fallback',
    'primary_carbon_metric':'operational kg CO2 = petrol road exhaust CO2 (TTW) + location-based purchased charging electricity CO2, if gas consistent; otherwise separate ledgers only',
    'CO2e_policy':'only calculate with documented coverage of other gases and harmonized MY/SG factor scope',
    'system_boundary':['road loaded/empty/reposition/return','fuel idle and queues','consolidation/transfer ground vehicle','UAV loaded outbound and return/rendezvous','charging wall electricity','fallback road service'],
    'exclude_primary':['embodied carbon','electricity upstream unless explicitly same accounting scope','fuel well-to-tank upstream unless separately reported'],
    'eligibility':'Regulatory not authorized != legal route. A simulation scenario may be conditional only with clearly identified restrictions, no claim of deployment.',
    'missing_data':'NaN/blank and explicit reason, never 0',
    'optimization':'minimize matched operational CO2 subject to same task cohort, service and on-time constraints plus declared cost budget; no feasible solution -> infeasible',
    'status':'METHOD_PLAN_NOT_NUMERICALLY_RELEASED'
})

write_json('protocol/VERIFIED_HISTORICAL_EVIDENCE.json',{
    'github_repo':REPO,'commit':COMMIT,'readme_gitblob':'42ac492b46b837e53a54490ed6637121f39ff687',
    'stage6_readme_gitblob':'924698cbda91196f08f8fa543d8128fe657756e6',
    'stage6_run_py_gitblob':'1bbf7864ee9546b781f048d515c5d756da8752',
    'stage8_f0_f1_report_gitblob':'d333b04bcc9e231064105c10dcab2e28bbb8974b',
    'historical_stage6':{'synthetic_orders':29842,'modes':3,'rows':89526,'seeds':30,'dates_per_seed':5},
    'historical_stage2':{'resampled_fixture_rows':918000,'known_road_OD':128,'road_model_paths':91,'exceptions_unapproved':37},
    'reason_no_old_carbon':'Stage6 electric van 0.23kWh/km and generic UAV 470W plus hypothetical asset parameters are not gasoline car or real FlyCart/Wingcopter mission calibration.',
    'purpose':'historical evidence freeze only, not V2 input confirmation'
})

source_rows=[
['SRC01','DJI FlyCart 30','manufacturer specifications','dual battery 30kg full-load 16km; 28km empty; 1,984.4Wh per battery; conditions matter','https://www.dji.com/flycart-30/specs','2026-10-30','OFFICIAL_SPEC_NOT_MISSION_ENERGY'],
['SRC02','Wingcopter 198 Cargo','manufacturer specifications','4.7kg and up to 92km; battery and 4.7kg mission energy not established','https://wsd.wingcopter.com/w198-cargo','2026-10-30','OFFICIAL_MAX_NOT_MISSION_ENERGY'],
['SRC03','IPCC 2006 Vol 2 Energy Ch3','methodology','mobile combustion fuel-based emissions method; fuel type density NCV EF need consistent units','https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol2','2026-10-30','GUIDELINE_NOT_VEHICLE_CONSUMPTION'],
['SRC04','Malaysia GEF 2022-24 provisional','official grid factor','2024 Peninsular 0.740 kg CO2e/kWh, provisional, not a 2026 observation','https://myenergystats.st.gov.my/documents/d/guest/grid-emission-factor-gef-in-malaysia-2022-2024-provisional-','2026-10-30','PROVISIONAL_CO2E_SCOPE'],
['SRC05','CAAM UAS','regulatory','SUP category may cover item carriage, BVLOS, and R&D','https://www.caam.gov.my/public/unmanned-aircraft-system-uas/','2026-10-30','REGULATORY_NOT_PERMIT'],
['SRC06','CAAS UA','regulatory','cross-border UAV permit guidance and BVLOS documents listed','https://www.caas.gov.sg/resources/regulatory-requirements-and-guidelines/unmanned-aircraft/','2026-10-30','REGULATORY_NOT_PERMIT'],
['SRC07','Singapore EMA','grid factor pending freeze','use matched year and gas scope; Stage05 prior 2024 CO2 value requires source reconciliation','https://www.ema.gov.sg/resources/singapore-energy-statistics','2026-10-30','NOT_FROZEN'],
['SRC08','Stage6 source and acceptance','research baseline','29,842 synthetic tasks, generic UAV+EV, conditional only',f'{REPO}/blob/{COMMIT}/10_experiment_results/stage6_dual_region_multilevel_feeder/README_STAGE6_CN.md','2026-10-30','HISTORICAL_BASELINE'],
['SRC09','Stage8 airspace and 2 aircraft audit','research baseline','19 reference anchors and 76 geometric candidate links; NOT_AUTHORIZED','https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027/blob/main/10_experiment_results/stage8_f0_f1_airspace_and_energy_evidence/reports/CIQ_Stage8_F0_F1_formal_experiment_audit_report_20261028.md','2026-10-30','HISTORICAL_BASELINE']]
write_csv('references/SOURCE_REGISTER.csv',['source_id','source','type','supports','url','review_date','evidence_status'],source_rows)

# experimental matrix: principal 5 modes + contextual scenarios
matrix=[
['EXP00','M0_PETROL','NONE','BASELINE','historical weather and traffic on frozen task hours','PETROL_ROAD_ONLY','30 seeds x 5 frozen dates after mapping','M0 benchmark','RQ2,RQ3','BLOCKED'],
['EXP01','M1_DJI','DJI_FC30','FIXED_HUB','same weather / traffic / tasks','PETROL_FEEDER','30 x 5','fixed feeder comparison','RQ2,RQ3','BLOCKED'],
['EXP02','M1_WING','W198_CARGO','FIXED_HUB','same weather / traffic / tasks','PETROL_FEEDER','30 x 5','fixed feeder comparison','RQ2,RQ3','BLOCKED'],
['EXP03','M2_DJI','DJI_FC30','RENDEZVOUS','same weather / traffic / tasks','PETROL_COORDINATED','30 x 5','vehicle drone coordination','RQ2,RQ3','BLOCKED'],
['EXP04','M2_WING','W198_CARGO','RENDEZVOUS','same weather / traffic / tasks','PETROL_COORDINATED','30 x 5','vehicle drone coordination','RQ2,RQ3','BLOCKED'],
['EXP05','M0_DIESEL','NONE','SENSITIVITY','identical cohort','DIESEL_ROAD_ONLY','paired 30 x 5','vehicle-fuel sensitivity only','RQ3','BLOCKED'],
['EXP06','M1_M2_ALL','BOTH','WEATHER_STRESS','dry/wet/high-wind sourced intervals','PETROL','paired 30 x 5','weather/flight sensitivity','RQ2,RQ3','BLOCKED'],
['EXP07','M1_M2_ALL','BOTH','ROAD_STRESS','FCD speed ratios or validated ranges','PETROL','paired 30 x 5','traffic stress','RQ2,RQ3','BLOCKED'],
['EXP08','M1_M2_ALL','BOTH','COST_CAP_STRESS','same input','PETROL','paired 30 x 5','cost cap 1.00/1.05/1.10/1.20 as proposed scenarios','RQ3','BLOCKED'],
['EXP09','M1_M2_ALL','BOTH','JOINT_UNCERTAINTY','weather/fuel/UAV energy/queue joint draws','PETROL','30-seed clustered uncertainty','robust min carbon feasible set','RQ3','BLOCKED'],
['EXP10','M1_M2_ALL','BOTH','CROSS_BORDER','ONLY if verified new OD / travel wait / airspace scenarios','PETROL','separate population and analysis','crossborder conditional sensitivity','RQ1,RQ2,RQ3','BLOCKED']]
write_csv('control/EXPERIMENT_MATRIX.csv',['experiment_id','mode','uav','operation','weather_traffic','ground_vehicle','sample','primary_comparison','RQ','status'],matrix)

figs=[
['Fig1','A/B/C QGIS geographically registered maps','V2_S06','RQ1','verified_nodes/edges/airspace', 'QGIS PNG/TIFF + shapefile context','Do not export prototype as final'],
['Fig3(a)','dual UAV manufacturer spec and candidate locations','V2_S06,V2_S09','RQ1','spec_registry + GIS freeze','PNG/PDF','spec ranges ≠ task energy'],
['Fig3(b,c)','mission geometry and operational constraints','V2_S09','RQ1','mission candidate / weather reg states','SVG/PNG','no approved route implication'],
['Fig4','2026 May–Sep weather + road time proxy','V2_S07','RQ2','weather_qc + road_od_hourly','PNG','not independent 4 ERA5 grid points'],
['Fig5','paired delivery & SLA, fallback / weather','V2_S10','RQ2','order_mode_results / event_log','PNG','same task IDs denominator'],
['Fig6(a)','cost ratio vs paired on-time service delta (2 UAVs)','V2_S11','RQ3','matched comparison','PNG','Do not mix unmatched service'],
['Fig6(b)','petrol vs hybrid operational CO2 & cost','V2_S11','RQ3','carbon ledger / matched comparison','PNG','CO2/CO2e scope harmonized'],
['Fig7','feasible Pareto + 30-seed uncertainty','V2_S12','RQ3','pareto / bootstraps','PNG','report infeasible cases']]
write_csv('control/SCI_FIGURE_LINKAGE.csv',['figure','subject','stage','RQ','data','deliverable','warning'],figs)

critical=[
['G01','V2_S06','new QGIS vector dependency & exact CRS locked','BLOCKED','no new project original'],
['G02','V2_S06','new A/B/C nodes mapped, airspace classification present','BLOCKED','new project missing'],
['G03','V2_S07','single immutable demand ID set and version','BLOCKED','QGIS mapping missing'],
['G04','V2_S07','time-zone, rainfall and wind quality checks','BLOCKED','real full hourly raw refit not rerun'],
['G05','V2_S07','directed road repaired/validated and border waiting declared','BLOCKED','37 old OD not applied'],
['G06','V2_S08','petrol vehicle and observed/literature evidence class for L/100km and L/h','BLOCKED','fuel economy missing'],
['G07','V2_S08','fuel emission factor and boundary single gas','BLOCKED','vehicle TTW full factor sheet missing'],
['G08','V2_S09','DJI mission energy interval credible & sourced','BLOCKED','not calibrated'],
['G09','V2_S09','Wingcopter mission energy interval credible & sourced','BLOCKED','not calibrated'],
['G10','V2_S09','regulatory screen scenario status and route geometry','BLOCKED','new airspace/route missing'],
['G11','V2_S10','paired M0/M1/M2 state machine smoke tests','BLOCKED','run forbidden'],
['G12','V2_S10','full demand + failed/fallback preserved','BLOCKED','run forbidden'],
['G13','V2_S11','MY/SG electricity consistent CO2 gas scope or separate ledger','BLOCKED','not harmonized'],
['G14','V2_S11','carbon & cost & service comparable denominator and tested physical trip ledger','BLOCKED','no ledgers'],
['G15','V2_S11','Pareto service/time/cost constraints pre-registered','BLOCKED','parameters not locked'],
['G16','V2_S12','30 seeds clusters + uncertainty & independent reproduction','BLOCKED','no outputs'],
['G17','V2_S12','SCI figures derived from reproducible CSV not manually edited','BLOCKED','no outputs']]
write_csv('control/MASTER_RELEASE_GATES.csv',['gate_id','stage','criterion','status','blocker'],critical)

readme=f'''# CIQ V2 低碳地空物流 SCI 后续实验总控（2026-10-30）

## 核心决定

**只围绕：汽油车 M0 对比；M1 固定接驳与 M2 车辆—无人机协同；天气/交通/成本约束下的运营 CO₂ 最小化。** 旧 Stage3–8 只读；V2 工作目录单独建立。不宣称当前已有新数值实验结果。

- 最新 GitHub 主分支版本：`{COMMIT}`（2026-10-28 上传的历史版本）。
- 现有 Stage05 仅冻结方法；实际燃油油耗、两机型任务能耗、三分区 QGIS 原件仍缺。
- 主要订单候选：旧 Stage6 29,842 条合成订单、30个seed、5个日期，前提是新 GIS 可以逐笔映射；旧 Stage2 918,000 是不同的重采样夹具，**绝不合并**。
- 不把五个固定日混称为整个 5 月到 9 月运行结果。
- 研究对象以马来西亚—新加坡 CIQ 物流 **条件性研究** 呈现；旧128条OD全部非跨境，不得捏造跨境物流的已测结果。

## 执行顺序与研究问题

| 次序 | 阶段 | 研究工作 | 主要 RQ |
|---|---|---|---|
'''+"\n".join(f'| {i} | `{s[0]}` | {s[1]} | {s[3]} |' for i,s in enumerate(stages,1))+'''

## 核心对照（最小实验矩阵）

同一任务样本，分别对 M0 汽油车、M1-DJI、M1-Wingcopter、M2-DJI、M2-Wingcopter。柴油 M0 仅作敏感性，不能顶替汽油车。风险/天气/道路/能源的扩展只作解释因子，不扩大主研究问题。

## 最终 SCI 结论允许的类型

1. RQ1：已证实几何候选及条件性可达网络；不可直接称政府批准的部署位置。
2. RQ2：按同批任务量化时间、准时率、天气和拥堵条件下适用性；不将三模式不同任务分母相除。
3. RQ3：在服务/准时/成本约束下找运营 CO2 最低的方案；若不存在成本和服务均不劣的方案，则如实报告“没有可行净减排方案”。

## SCI 统计与样本边界

30 seed 为历史试验统计重复单位。任务数量和 mode 级记录不能伪装为独立实测样本。时间窗口固定5日期不是5个月每天实验。先做审计小样本，再做30-seed成对主试验，最后多因素联合不确定性。

## GitHub 上传目录建议

`11_v2_carbon_first_experiments/`。每个节点目录含 README、合同、输入模板、QA 门槛、输出注册和状态记录；每节点另附 ZIP。无需覆盖旧 `10_experiment_results/`。

## 如何执行检查

```bash
python tools/verify_stage.py --root . --stage V2_S06
python tools/verify_stage.py --root . --stage V2_S07
python tools/verify_stage.py --root . --stage V2_S08
python tools/verify_stage.py --root . --stage V2_S09
python tools/verify_stage.py --root . --stage V2_S10
python tools/verify_stage.py --root . --stage V2_S11
python tools/verify_stage.py --root . --stage V2_S12
```

**当前预期为 HOLD，不是脚本失败。** 缺原始数据时，工具应返回阻断明细，严禁虚构结果。

## 主要文件

- `protocol/MASTER_PROTOCOL_V2.json`：全局科学边界
- `control/EXPERIMENT_MATRIX.csv`：五模式+敏感性 11 组实验设计
- `control/MASTER_RELEASE_GATES.csv`：17 项跨阶段放行门槛
- `control/SCI_FIGURE_LINKAGE.csv`：与 Fig1/3/4/5/6/7 一一对应
- `references/SOURCE_REGISTER.csv`：官方来源及证据类型
- `tools/verify_stage.py`：输入结构和文件哈希检查（不自动给科学签字）
- `tools/validate_paired_results.py`：成对任务与 mode 分母审计
- `tools/generate_sha256_manifest.py`：上传前生成逐文件哈希
- `STAGES/V2_Sxx`：每个里程碑步骤、输入/输出模板和验收登记

**注意**：模板 CSV 只有列名，没有真实实验值；任何 0/空字段不代表实际零消耗或零成本。
'''
put('README_CN.md',readme)

put('GITHUB_UPLOAD_INSTRUCTIONS.md',f'''# GitHub 更新方法 — 不覆盖历史工程

原仓库：{REPO}
固定历史 commit：`{COMMIT}`

建议新增根目录 `11_v2_carbon_first_experiments/` 并把本包内容移入，不删除原有任何历史文件。

```bash
# 在克隆后的项目根目录下：
mkdir -p 11_v2_carbon_first_experiments
# 将本包解压文件复制进入上述新文件夹（不覆盖旧 Stage3–8）
git add 11_v2_carbon_first_experiments
git commit -m "Plan V2 petrol-road vs hybrid UAV carbon-first experiments"
git push origin main
```

**上传每次节点结果前必做**：
1. 检查是否含私人 API key、证书、token、许可敏感材料、不可再分发源数据。
2. 运行 `verify_stage.py` 记录输入存在性与字段检查。
3. 运行 SHA256 manifest 记录输入输出、脚本版本、随机种子和时区。
4. 将实验输出与审计报告放回对应 `STAGES/V2_Sxx/outputs/`；不把原始源数据替换为改写版。
5. 对大文件遵守既有仓库的 20 MiB split 约定。

在真实三分区 QGIS 工程、燃油 M0 和两款无人机任务能耗证据未冻结前，任何阶段保持 HOLD，不要运行正式碳结果。
''')

# Source boundary and role ownership
write_csv('control/DELIVERABLE_MAP.csv',['stage','source_inputs','script_or_check','mandatory_outputs','paper_use','status'],[
 [code,'; '.join(i[0] for i in ins),'tools/verify_stage.py; stage input QA','; '.join(o[0] for o in outs),rq,'HOLD'] for code,cn,en,rq,steps,ins,outs,gates,note in stages])

print('created root',ROOT,'stage count',len(stages))
