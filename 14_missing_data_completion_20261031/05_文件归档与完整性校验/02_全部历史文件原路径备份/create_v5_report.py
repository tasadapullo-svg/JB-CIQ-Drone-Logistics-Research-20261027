from pathlib import Path
import json,csv,hashlib,shutil,zipfile,pandas as pd
out=Path('/mnt/data/CIQ_V5_Freeze_Audit_20261030')
src=Path('/mnt/data/CIQ_ABC_QGIS322_V5_ONE_WMP228_68_NODES_FULL_PROJECT(1).zip')
shutil.copy2('/mnt/data/ciq_v5_baseline_audit.py',out/'reproduce_independent_v5_audit.py')
audit=json.loads((out/'V5_INDEPENDENT_AUDIT.json').read_text())
freeze={
 'frozen_baseline_id':'CIQ_ABC_QGIS322_V5_ONE_WMP228_68_NODES_20261030',
 'frozen_source_zip_filename':src.name,
 'frozen_source_zip_sha256':audit['source_zip_sha256'],
 'frozen_active_geopackage_filename':'data/CIQ_ABC_V5_ACTIVE.gpkg',
 'frozen_active_geopackage_sha256':audit['source_gpkg_sha256'],
 'archived_v4_geopackage_sha256':audit['source_gpkg_v4_sha256'],
 'active_nodes':68,'source_qa_IDs_match':True,
 'zones':audit['zones'],
 'candidate_UAV_geometric_links':116,'ground_straight_reference_links':5,
 'additional_ground_HOLD_lines':4,'WMP228_reference_circles':1,
 'coordinate_edits':'NONE', 'source_changes':'NONE',
 'CAVEAT_A09_A10':'A09 and A10 have zone=C in source; do not infer zone from ID prefix',
 'CAVEAT_ARCHIVED_68_ROW_CSV':'archive/ALL_68_STUDY_NODES_LONG_LAT.csv contains A_N10 and omits G_CIQ; use active GPKG',
 'scope':'CONDITIONAL_SCI_GEOGRAPHIC_REFERENCE_NOT_AUTHORIZED_FLIGHTS',
 'S06_state':'STATIC_GIS_PASS_REBASELINE_REQUIRED',
 'S07_state':'HOLD_UNTIL_FIVE_MONTH_WEATHER_ROADS_AND_FROZEN_ORDERS_VERIFIED',
 'historical_repo':'https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027',
 'historical_repo_commit_reviewed':'4569817b8145efe2ae06f4b21addc1986f971c12',
 'freeze_instruction':'Do not modify V5 archive or coordinates. Build derived versioned S06/S07 inputs and report discrepancies separately.'
}
(out/'V5_FROZEN_BASELINE_RECORD.json').write_text(json.dumps(freeze,ensure_ascii=False,indent=2),encoding='utf8')

steps=[
('S06-V5','基线转换','重建68节点主表、116条候选UAV线、5条地面交接及4条HOLD线并冻结SHA','旧69点中间文件不得再用于主实验'),
('S06-V5','基线转换','重新计算点线关联、分区角色、历史19点ID与位置冲突','A09/A10属于C区；存档CSV不能作为活动点表'),
('S06-V5','基线转换','冻结S07输入合同及候选可用性标志','只能声明几何参考通过，不允许写飞行许可通过'),
('S07','五个月数据耦合','逐文件恢复并校验2026年5–9月气象和历史交通源','原始字节SHA、变量单位、起止时刻、数据版本'),
('S07','五个月数据耦合','时区及小时区间统一，生成3672小时天气查询库','雨累计区间、阵风、风向、缺失与实际可用性'),
('S07','五个月数据耦合','关联68节点至天气源格网，审核空间代表性','ERA5为历史粗格网代理，不得写成68个独立实测站'),
('S07','五个月数据耦合','构建覆盖A/B/C的有向OSM道路网络','老A/B路网不能替代新增C区；不将直线当道路'),
('S07','五个月数据耦合','节点出入口与双向OD求路，逐项处理37条旧异常','未验证不得自动修复，保留错误状态'),
('S07','五个月数据耦合','在V5坐标上生成同一批冻结合成任务，保留历史回放组','不得按同名旧ID替换实际空间位置'),
('S07','五个月数据耦合','天气—道路—任务联合QA和数据冻结','全需求分母、时间日期、随机种子、场景定义和SHA'),
('S08','汽油车M0','选定汽油车辆车型/载荷/油耗与同口径燃油碳因子','区分有依据的参数、情景假设与敏感性'),
('S08','汽油车M0','开发公平强基线M0多订单路线/车队优化','不可用逐单往返故意弱化汽油车'),
('S08','汽油车M0','按时段交通计算道路行驶时间、怠速、空驶和实际油耗','历史FCD是代理，不是每个路段实时车辆轨迹'),
('S08','汽油车M0','订单级与车次级燃油、成本、完成率守恒审计','M0先形成可独立验收基线'),
('S09','两款无人机','分离DJI FlyCart30和Wingcopter198 Cargo载重/航程/速率约束','不能直接使用历史470W泛化功率'),
('S09','两款无人机','建立载荷-风-距离-往返-保底电量与充电损耗模型','任务级能耗未校准处保持区间情景'),
('S09','两款无人机','按实际仿真发航、返航时刻查询天气','释放小时天气不直接固定整次飞行'),
('S09','两款无人机','航段与站点的条件可用性及灵敏度QA','空域参考圆不是监管批准边界'),
('S10','五模式配对仿真','冻结相同任务集和统一服务/成本约束','五种情况：M0+两个M1+两个M2'),
('S10','五模式配对仿真','实现固定站点M1地面接驳/等待/充电/返程','实际车次共享成本不能订单级重复分配'),
('S10','五模式配对仿真','实现M2车机同步、会合、补能与回退','严格记录物理车辆及无人机资源占用'),
('S10','五模式配对仿真','执行按月-时段-风雨-拥堵的多种子仿真','不把5个固定日当作5个月全覆盖'),
('S10','五模式配对仿真','核验订单配对、结果守恒及失败分类','未评价订单不能视作完成或自然丢弃'),
('S11','低碳优化','确立相同TTW和WTW运营能源排放范围','不能混淆尾气、购电和全生命周期'),
('S11','低碳优化','计算ΔCO2e、汽油替代里程和充电碳强度','从同一车次/任务事件账本计算'),
('S11','低碳优化','联合服务率、准时率、成本上限形成Pareto方案','不存在可行低碳方案也需报告'),
('S11','低碳优化','绘制排放盈亏平衡临界面和双机型差异','天气、交通、需求密度三维条件'),
('S12','统计SCI成稿','区分种子随机性和天气日期/道路/机型参数不确定性','输出置信区间与异质性检验'),
('S12','统计SCI成稿','强M0基线及天气/道路/空域不利情景反证','不能只报告有利场景'),
('S12','统计SCI成稿','重跑输入-输出复现和全流程科学审计','图表数据必须来自可冻结数值实验'),
('S12','统计SCI成稿','完成SCI Fig/Tables、Results、Discussion证据边界','RQs 1–3均可对应具体结果')]
with (out/'V5_31_BLOCKS_EXPERIMENT_BACKLOG.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['block_id','stage','workstream','action','gate']);
 for i,row in enumerate(steps,1):w.writerow([f'{i:02d}',*row])

md=f'''# CIQ 无人机物流 SCI — V5 冻结基准、数据状态与剩余实验正式核验

**核验日：2026-10-30**  
**唯一冻结空间原件：** `{src.name}`  
**原始 ZIP SHA-256：** `{audit['source_zip_sha256']}`  
**活动 GeoPackage SHA-256：** `{audit['source_gpkg_sha256']}`  
**独立核验：** 24/24 项静态测试 PASS；**不等于**运营、法规和完整动态仿真通过。

## 1. 空间基准最终决定

- V5 活动节点 **68**：A区29（22主研究节点、6港区补充参考点、1 G_CIQ地面关口），B区10，C区29。`A09`、`A10` 实际属性是 `zone=C`，不能由前缀推算区域。
- 基础候选连接 **121**：111条原有几何连接 + 10条港区连接；港区10条分为 5 条 UAV 几何候选和 5 条地面交接直线，因此 **UAV几何候选116条、地面交接直线5条**。此外还有 **4条额外地面专用HOLD线**，不纳入121条。
- V5 相比包内 V4，**仅将 A_N10 移出活动节点**；68个保留节点的坐标、121条候选线几何均独立核验为不变。
- 12个节点与116条UAV候选几何没有直接连接；保留为需求、地面或参考节点，不能自动删除。
- 单一 WMP228 **CAAS_2026、半径3704米参考圆**；活动候选线与圆的直线几何不相交。但圆是**制图参考**，不是已证实法律禁飞边界；也不等于航路已获许可。
- 活动主节点61/61的 `uav_operational_admission=NO`、`road_entry_verified=False`，港区6点也没有许可起降证据。故**静态图层PASS，运营准入HOLD**。
- QGS 与 QGZ XML一致；QGIS工程含本地有效图层19项与一个在线OSM瓦片图层，原包全部28项SHA匹配；**尚未在QGIS Desktop 3.22.4 GUI实机验证**。OSM瓦片联网显示不等于附带OSM可求路图。

## 2. 必须隔离的旧文件与历史数据

**严重的成员清单差异：** 原包 `archive/ALL_68_STUDY_NODES_LONG_LAT.csv` 含已删除的 `A_N10`，却缺当前活动 `G_CIQ`，虽也是68行但不是V5活动68节点。`qa/V5_ALL_68_NODE_IDS.csv` 则与活动GeoPackage完整匹配。正式计算一律从活动GPKG或本包导出的 `V5_FROZEN_68_NODE_MASTER.csv` 获取活动节点。

- V3旧版S06/S07 的69节点CSV、节点连接、13个UAV零度节点等需按V5重算，禁止将旧CSV直接并入新仿真。
- 旧 Stage 6 **29,842条合成订单**（30种子×5抽样日）来自**旧 A/B 参考网络**，不能按同名ID接入新 A/B/C；其历史汽油车M0并不存在（使用电动面包车代理），不能作为新汽油基线。
- 历史工程另存在 **918,000行重复抽样工程fixture**，其原冻结源和生成器不完整，不能当作918,000独立观测订单。
- 历史天气 2026-05—09 五个月元数据存在，但**尚未以V5的68点建立可审核逐小时天气值**；历史ERA5仅两个返回网格，空间代表性需标记。
- 旧A/B有向OSM图文件可在GitHub找到，但未通过新版V5全三分区节点入口、转向与C区覆盖验证；37条旧OD异常仍然需要处理。

GitHub历史数据固定参考提交 `4569817b8145efe2ae06f4b21addc1986f971c12`（2026-10-28 06:55 UTC）；历史文件**保留且不可覆盖**。

## 3. 后续还剩多少实验

**总计6个正式实验阶段：V2-S07、S08、S09、S10、S11、S12。** 
另外先完成一个非新实验的 **S06→V5迁移验收**。把每阶段细化为**28项实验执行工作块 + 3项迁移验收 = 31项待办工作块**（详见CSV）。这不是31套独立模拟，也无需另起31个研究项目。

| 环节 | 工作块 | 当前状态 | 对应核心成果 |
|---|---:|---|---|
| S06→V5接口迁移 | 3 | 可立即执行 | 更新69→68；冻结116/5/4；迁移旧新坐标命名空间 |
| **S07** 数据融合 | **7** | 部分可做；真实联合输入HOLD | 3672小时天气、A/B/C有向路由、V5冻结合成订单 |
| **S08** 汽油车M0 | **4** | 可以开发测试，正式仿真HOLD | 最优多站路径、油耗、成本、尾气排放 |
| **S09** 双无人机 | **4** | 可以开发测试，参数标定HOLD | DJI与Wingcopter负载、风、返程、充电能耗 |
| **S10** 配对五模式 | **5** | HOLD | 同任务M0、两机型M1、两机型M2事件级结果 |
| **S11** 减排优化 | **4** | HOLD | 同边界排放、盈亏平衡、服务/成本可行帕累托 |
| **S12** 科学统计和图表 | **4** | HOLD | 不确定性、鲁棒性、SCI图表和论文三问题证据 |

## 4. 硬放行次序

1. 先做 S06→V5 迁移，不触碰现有V5源工程；静态空间输入可以冻结，运营许可状态必须保留NO/HOLD。
2. **S07放行**必须同时取得：①有依据的5个月小时气象值及时间区间；②可重现的A/B/C有向OSM路网、节点出入口和37条异常分类；③在V5点位上生成的唯一任务清单，五模式使用相同订单分母。
3. S08、S09可同步开发，但没有S07实物输入不得提前发布“汽油车/无人机真实模拟CO2减排率”。
4. S10要逐车次+逐任务记录物理时间、距离、燃油、耗电、回退和成本，分开交付M0/M1/M2五种情况。
5. S11用相同能耗边界计算运营CO2e，明示TTW/WTW，不把运营减排等同完整LCA；S12须检验强汽油车基线是否仍有优势。

## 5. 科研边界与冻结规则

**冻结不等于删HOLD。** 你已经确认V5布局最终不再修改，本次仅建立派生数据与接口，不变更源点坐标、不增删原有121条线。某条线即便直线达到航程要求，也不得标为已获批准的空中通道；5条地面交接线和4条额外HOLD线不能被当作已求出的汽车道路。

**最终裁定：V5静态研究底图/几何基准PASS；V5有效运营路网HOLD；6个正式实验阶段仍待完成。**
'''
(out/'V5_FORMAL_FREEZE_AND_REMAINING_EXPERIMENTS_CN.md').write_text(md,encoding='utf8')
(out/'README_CN.md').write_text('''# V5 独立空间基准冻结与剩余实验工程\n\n**源数据不修改。** 输入ZIP位于 `input/`；正式冻结以其中 `data/CIQ_ABC_V5_ACTIVE.gpkg` 为准。\n\n打开 `V5_FORMAL_FREEZE_AND_REMAINING_EXPERIMENTS_CN.md` 查看结论；`V5_INDEPENDENT_AUDIT.json` 为机器验收报告。\n\n重新运行：`python reproduce_independent_v5_audit.py input/CIQ_ABC_QGIS322_V5_ONE_WMP228_68_NODES_FULL_PROJECT(1).zip audit_rerun`。需 geopandas、pandas、pyproj、shapely。\n\n本包的 `SOURCE_28_SHA256_CHECKS.csv`、节点/连接输出、V4对照、`V5_31_BLOCKS_EXPERIMENT_BACKLOG.csv` 和签名表是重新执行的可审核证据。旧 Stage 3–8 文件没有被写入或更改。\n''',encoding='utf8')
inputdir=out/'input';inputdir.mkdir(exist_ok=True); shutil.copy2(src,inputdir/src.name)
# package-level hashes excluding manifest itself
lst=[]
for f in sorted(out.iterdir()):
 if f.is_file() and f.name!='DELIVERY_SHA256_MANIFEST.csv':
  lst.append({'path':f.name,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
for f in sorted(inputdir.iterdir()):
 lst.append({'path':'input/'+f.name,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
with (out/'DELIVERY_SHA256_MANIFEST.csv').open('w',newline='',encoding='utf8') as fh:
 w=csv.DictWriter(fh,fieldnames=['path','bytes','sha256']);w.writeheader();w.writerows(lst)
path=Path('/mnt/data/CIQ_V5_Frozen_Baseline_Independent_Audit_and_6_Stage_Roadmap_20261030.zip')
with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
 for f in sorted(out.glob('*')):
  if f.is_file():z.write(f,f.name)
  elif f.name=='input':
   for v in f.iterdir():z.write(v,'input/'+v.name)
with zipfile.ZipFile(path) as z: assert z.testzip() is None
print('ZIP',path,path.stat().st_size,'FILES',len(z.namelist()),'CSV',len(steps))
