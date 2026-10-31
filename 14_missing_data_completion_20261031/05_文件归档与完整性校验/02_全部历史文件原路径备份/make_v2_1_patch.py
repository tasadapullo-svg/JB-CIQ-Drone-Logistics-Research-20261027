from pathlib import Path
import json,hashlib,zipfile,csv
root=Path('/mnt/data/CIQ_V2_1_SCI_Method_Review_20261030')
items=[
('P0-01','V2_S06','最新三分区GIS原件真实性、节点与空域', 'QGZ/QGS+全部本地依赖，实际层ID、CRS、图层哈希、19旧点映射、A/B/C点线索引','逐层source存在；有向连线端点匹配；显式未知/受限；坐标不擅自移动','HOLD_EXTERNAL'),
('P0-02','V2_S07','五个月联合天气交通暴露与代表性时段','153天日历 × 原始可用小时grid/FCD × strata × 来源/日期哈希；不以缺测填0','按日期/月/小时检测missing; 原ERA5两格点去伪独立; 原数据单位/时间戳换算正确','HOLD_SOURCE'),
('P0-03','V2_S07','同订单样本与需求生成器', '按国家/走廊/日期/seed冻结唯一任务集合，需求假设文献和ID签名','所有模式含相同task_id；不得合并918000和29842；新增分层任务不可伪称真实','HOLD_SOURCE'),
('P0-04','V2_S08','强汽油车基线和可解释的燃油车参数','汽油多站点路径、转弯、服务窗、资源/车载重量、怠速和车辆负荷区间','与M1/M2调度质量和资源相当，整日车辆trip一次计账','HOLD_CALIBRATION'),
('P0-05','V2_S09','两机型分级证据能耗区间和天气时刻','E1/E2/E3证据等级、起降航段、可用SOC、风场、充电/备用、航路绕飞','如无实测只出条件性区间及阈值；不许由名义航程推每公里kWh','HOLD_CALIBRATION'),
('P0-06','V2_S11','统一能源排放边界 TTW+grid/WTT/WTW','燃油 TTW & WTT 和供电电力完整范围、MY/SG、气体和年份分账','相同边界WTW能比较方可宣称净减排；不齐只报细账和假设情景','HOLD_EF'),
('P0-07','V2_S10','事件驱动调度、车次账本和回退','物理 vehicle_trip_id / drone_sortie_id / task_id 映射，容量资源、装卸等待、充电、无效发飞、回退','有真实数值求解器与端到端集成测试；每订单唯一结局；每物理车次只计一次','HOLD_IMPLEMENTATION'),
('P0-08','V2_S10','双边研究范围与跨境样本隔离','MY国内、SG国内、CROSS_BORDER 3类任务；真实/条件性交通及监管数据分别标注','历史全部非跨境OD不能导出跨境证据；没有数据只报告空间情景','HOLD_EXTERNAL'),
('P1-01','V2_S11','减排临界面BE-01','汽油总里程节约、额外接驳/怠速、两机型墙端充电电量分项','同边界0差值曲线及低中高参数区间；关键阈值可复算','PLANNED'),
('P1-02','V2_S10','强M0竞争基线BAS-01','匹配车辆调度预算和车队，优化M0路线','混合方案对M0公平基线及更强M0对照均报告','PLANNED'),
('P1-03','V2_S11','优化决策变量与不可行证据','模式/机型/站点/任务/车资源/会合时刻、成本、服务、准时约束','标清启发式/最优界，返回Pareto含INFEASIBLE原因','PLANNED'),
('P1-04','V2_S12','种子与日期双层不确定性','30seed需求随机性+独立日期块+车型/UAV参数区间','不能把5天*30seed当150独立天气日；置信区间分不同不确定源','PLANNED'),
('P1-05','V2_S12','科学验证VAL-01','物理守恒/恶劣条件/服务反例/跨境等待开关/单位换算','真运行和逐事件QA，而非只有表头/哈希脚本','PLANNED'),
('P2-01','V2_S12','SCI图形证据映射及声明质量','Figure2流程、Figure4月日小时天气路网、Figure6临界面、Figure7可行Pareto','所有图从冻结输出生成，字数与气体口径一致，失败和HOLD可见','PLANNED'),
]
register=[dict(id=i,priority=i.split('-')[0],stage=s,issue=issue,required_artifacts=artifact,acceptance=gate,current_status=status) for i,s,issue,artifact,gate,status in items]
(root/'control'/'amendment_register.json').write_text(json.dumps({'version':'V2.1_REVIEW_20261030','status':'SCIENTIFIC_METHOD_AMENDMENT_NOT_EXECUTED','items':register},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for num in range(6,13):
 stage=f'V2_S{num:02d}'; files=[x for x in register if x['stage']==stage]
 lines=[f'# {stage} — V2.1 需要补充/修订的审查项目','','**定位：**针对原 V2 阶段合同的增补，不改写历史报告，不代表已经通过。','']
 for x in files:
  lines.extend([f"## {x['id']} {x['issue']}",f"- 优先级：{x['priority']}",f"- 应交付：{x['required_artifacts']}",f"- 放行条件：{x['acceptance']}",f"- 现状：`{x['current_status']}`",''])
 lines += ['## 必须随阶段上传 GitHub 的证据文件', '- `README.md`（写明本轮输入、变更、复现命令与结果的证据等级）','- `input_manifest.json`（路径、来源、版本、时间戳、哈希、允许使用范围）','- `code/`（真实实现+依赖锁定）','- `tests/`（合成/真实小样本及失败场景）','- `results/`（实际输出、日志；无原件不能填假数据）','- `qa_report.json` 与 `release_record.json`（所有阻断项、实际审查者）','- `SHA256SUMS` 和该阶段独立 ZIP','']
 (root/'stages'/f'{stage}_PATCH.md').write_text('\n'.join(lines),encoding='utf-8')
# concise machine-readable updated release rule
root_gates={
 'status':'V2.1_PLANNED_HOLD',
 'no_numeric_results_until':['V2_S06_SPATIAL_FROZEN','V2_S07_TASK_AND_EXPOSURE_FROZEN','V2_S08_PETROL_MODEL_EVIDENCED','V2_S09_UAV_MODEL_BOUNDED','V2_S10_ENGINE_REAL_INTEGRATION_QA'],
 'scientific_truth_rules':{
  'net_reduction_requires':'Comparable documented operational energy-boundary WTW CO2e OR explicitly conditional transparent source-specific accounting, not claimed actual net reduction',
  'time_and_service':'same all-task denominator for completion/ontime; matched time paired with full denominator status',
  'mode':'only 5 primary modes; EXP05~10 diagnostics and scenarios',
  'sample':'distinct seed uncertainty and independent day/weather blocks',
  'airspace':'simulation conditional screening != regulatory flight authorisation',
  'data':'raw source provenance and hashes; never invent GIS, orders, fuel, wind, grid EF'
 },
 'required_packages':'one independent ZIP per V2-S06 through S12 containing source/inputs/code/results/tests/hashes/README; nonexisting real inputs reported HOLD',
 'manual_approval_required':True
}
(root/'control'/'V2_1_release_policy.json').write_text(json.dumps(root_gates,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Manifest excluding self
manifest=[]
for p in sorted(root.rglob('*')):
 if p.is_file() and p.name not in {'FILE_SHA256.json'}:
  manifest.append({'path':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size})
(root/'control'/'FILE_SHA256.json').write_text(json.dumps({'algorithm':'sha256','files':manifest},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
zip_path=Path('/mnt/data/CIQ_V2_1_SCI_Method_Review_and_Work_Handoff_20261030.zip')
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
 for p in sorted(root.rglob('*')):
  if p.is_file():z.write(p,arcname=root.name+'/'+p.relative_to(root).as_posix())
with zipfile.ZipFile(zip_path) as z:
 assert z.testzip() is None
 assert len(z.namelist())==len(manifest)+1
print('zip',zip_path,'files',len(manifest)+1,'bytes',zip_path.stat().st_size)
print('issues',len(register),'P0',sum(x['priority']=='P0' for x in register),'P1',sum(x['priority']=='P1' for x in register),'P2',sum(x['priority']=='P2' for x in register))
