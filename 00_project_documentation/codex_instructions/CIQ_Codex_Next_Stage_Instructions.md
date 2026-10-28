# CIQ 无人机物流研究 — Codex 下一阶段工程执行指令

## 角色与任务
你是研究复现工程师、运输仿真工程师和 Python 测试工程师。你正在用户**已经存在的本地工程根目录**内工作。不要向用户索要工程 ZIP，不要要求重新提供数据。首先自动扫描当前工作区，并根据真实文件和代码建立工程清单。严禁把历史对话所述的数据量当成已经验证的事实。

研究对象：Johor Bahru–Singapore Causeway 与 Second Link CIQ 走廊；使用合成订单、24 小时交通、气象、OSM OD，比较三种配送模式：M0 纯地面；M1 固定多节点地空；M2 货车–无人机协同。历史记录称已有 30 个随机种子与 918,000 条合成订单记录；此数字必须通过真实输入审计确认，不要生成新的订单来补齐，也不允许默认成功。

## 强制约束
1. 默认只读原始数据，禁止覆盖原始文件、重新采样订单、重设种子或悄悄替换模型。新文件保存于 `outputs/next_stage/` 或符合现有目录约定的独立版本目录。
2. 必须先审计，再修改模型，随后小样本端到端验证，最后才允许全量运行。全量仿真不得因本指令而自动开始，除非所有门槛通过且项目已有适当的运行开关。
3. 采用真实文件发现而非假定路径；支持 `.csv`, `.parquet`, `.json`, `.jsonl`, `.geojson`, `.gpkg`, `.xlsx`, `.zip`, `.py`, `.yaml`, `.toml`。ZIP 先查看目录与内容摘要，禁止对未知大文件盲目解压覆盖。
4. 依赖环境应优先使用现有 `pyproject.toml`, `requirements*.txt`, `environment.yml` 或 lockfiles；不任意升级环境。
5. 所有未校准参数标为 `assumed`；文献参数标 `literature`；官方参数标 `official`；实际校准参数仅在有真实校准证据时标 `calibrated`。不允许编造值、来源 URL、许可、路线或实测数据。
6. 马来西亚 CAAM、新加坡 CAAS 的空域/跨境飞行权限与货物通关是不同约束。缺少批准证据的跨境航段不得标记为实际授权运营；允许独立记录 `conditional_permission_scenario`，与基线分开。
7. 3 km/4 km 必须记录量纲及含义（单程半径、路径长度或往返任务总航程），无人机能耗必须考虑载荷、天气、安全储备和回收位置。不得把直线距离当做可飞航线验证。
8. 严格保证订单×种子×模式的一致性。未服务与失败订单必须保留；无法计算的数值使用空值及 `reason_code`，绝不填零假装无排放、无成本或零延误。
9. 所有结果包含 `run_id`, `scenario_id`, `input_version`, `model_version`, `parameter_version`, `seed`, `mode`, `order_id`（适用处）。时间字段明确时区 Asia/Kuala_Lumpur 或 Asia/Singapore，以及原始时间源和单位。
10. 逐步修改、运行测试、汇报差异。避免无关的重构和删除旧成果。

## 第 1 步：真实工程盘点
列出工程树（排除 `.git`, `venv`, 缓存、体积极大的逐行输出）；定位：订单生成代码/随机种子输出、OSM 图与 OD 参考路由、道路速度/小时交通/CIQ 等待、天气降雨及风、场站坐标与候选集、无人机性能、模拟主入口、分析图表与单位测试。

自动生成 `outputs/next_stage/project_inventory.csv`：`relative_path, file_type, size_bytes, sha256, likely_role, evidence_status, notes`。生成 `outputs/next_stage/engineering_gap_report.md`，分别标记 `verified_existing`, `partially_implemented`, `missing`, `unverified`，每项引用路径、函数或字段作为证据。不要因为没有找到而直接断言文件不存在：先搜索压缩包成员及配置映射。

## 第 2 步：冻结与输入审计
在不改动输入的前提下，用流式/分块方法检查订单记录数量、种子取值及数量、`(seed, order_id)` 唯一性、起终点坐标、订单释放时间、货重、OD 引用、两通道分类、缺失值、重复和明显异常。若数据为多文件分片，确认各片无重复或漏片。输出 `input_audit.csv`，一条统计记录对应每个种子/文件分片或明确的审计层级，并给出最终总计。保存原始输入哈希与代码 Git commit（如果有）至 `experiment_manifest.json`。预期 918,000 与 30 是**待检验断言**。若有差异，报告而不是擅自修复。

## 第 3 步：道路模型验证
识别 OSM 图版本、路段长度、速度/拥堵因子、时间依赖路由逻辑、过境路线、CIQ 等待建模方式和单位。生成 `road_model_validation.csv`，至少包含 `route_id, od_id, corridor, departure_hour, route_distance_km, road_time_min, ciq_wait_min, total_time_min, connectivity_status, anomaly_code, evidence_level, model_version`。批量检查不可达路径、负值、零距离非同点 OD、异常绕路、跨境边界、重复计入 CIQ、24 小时索引和时区。区分内部一致性验证与外部观测校准；缺乏实测数据不得写 `validated against observations`。

## 第 4 步：站点与航段可行性
载入现有冻结场站候选，如不存在则标记缺失，不得自动创造坐标。对每个候选订单、站点、3 km/4 km 情景拆分技术可行、气象可飞、法规规则初筛、实际获批四种状态，未知写 unknown，不得把未知强行当成许可或禁飞。输出 `station_coverage.csv`，建议字段 `seed,order_id,station_id,corridor,range_scenario_km,range_interpretation,distance_km,energy_wh,weather_status,technical_status,regulatory_screen_status,permit_evidence_status,overall_scenario_eligibility,reason_code`。站点需求需要明确容量、周转、补货及服务范围。

## 第 5 步：统一三模式模型与小样本验证
使用同一批有代表性的订单样本（含 Causeway/Second Link、高低峰、可飞/不可飞/未知、短长 OD），**不新造订单**。如已有 M0/M1/M2 模块，做最少必要修复；如缺失，设计清楚的接口与可运行实现，但不得使用未声明的假设补足核心参数。
- M0：地面路径、车辆载重与容量、等待、配送、CIQ 队列。
- M1：地面补货到站点、站点库存/交接/分拣/队列/充电、无人机飞行、末端交付、无法飞行转地面兜底。
- M2：货车携机、发射/回收、货车与无人机同步、会合地点、排队/容量/电量、异常兜底。
同一订单均用相同释放时间、目的地、货重、服务完成定义、气象与道路情景；模型含明确状态机，如 `completed_on_time`, `completed_late`, `fallback_completed`, `unserved`, `censored`, `failed`。分别保留交接和运输时间，不得只计算无人机空中时间。

## 第 6 步：能源、排放与成本
定义从订单释放至交付完成的门到门指标和统一功能单位；运行排放与生命周期分摊明确分列。对于马来西亚与新加坡的电耗，依据充电发生地应用有来源且年份标注的电网排放因子。包括车辆燃油/电力、无人机电耗及充电损失、站点用电、设备与站点分摊、再配送与地面兜底。订单分摊之和与运行总值应守恒。每个参数记录 `parameter_name,value,unit,source_type,source_url,source_year,evidence_level,uncertainty_low,uncertainty_high,scenario_id,notes` 至 `parameter_registry.csv`；空缺不可自作主张。

## 第 7 步：规范输出
输出且验证以下文件：
1. `input_audit.csv`
2. `road_model_validation.csv`
3. `station_coverage.csv`
4. `simulation_order_results.parquet`：每一 `(scenario_id,seed,order_id,mode)` 一行，包含 `release_time,completion_time,service_status,reason_code,door_to_door_min,deadline_min,delay_min,vehicle_km,vehicle_energy_kwh,drone_energy_kwh,cost_total,emissions_kgco2e` 及拆分项；缺失/失败订单仍保留。
5. `simulation_run_summary.csv`：按 `(scenario_id,seed,mode)` 聚合，记录订单总数、服务数、未服务数、准时率、兜底率、门到门分位数、延误 P50/P90/P95、车辆里程、能耗、成本和排放；分位数样本集合与缺失处理明确记录。
6. `parameter_registry.csv`
7. `rq_results.xlsx`：RQ1 覆盖与站点需求、RQ2 时间与服务、RQ3 成本排放、paired differences、95% CI、敏感性情景、definitions/provenance 工作表。
8. `experiment_manifest.json`, `validation_report.json`, `engineering_gap_report.md`, `project_inventory.csv`。
注意：XLSX 使用工程现有 Python 库生成；每个表格有单位/数据字典，图表不能只留截图。

## 第 8 步：统计原则
种子内 M1-M0、M2-M0 配对；不得将全部订单行视为相互独立的 918,000 次实验。至少给出种子级配对差及跨 30 种子的 95% CI（在重抽样方案与随机种子固定的情况下），并分别报告结构性/参数不确定性。重复仿真中的非独立订单、24 小时交通共享效应应有清楚说明。显著性不等于政策/实用效益。RQ3 净减排 `E_M0 - E_M1` 与 `E_M0 - E_M2`，负值不隐藏。

## 第 9 步：自动验收
编写并运行 pytest，至少覆盖：(a) 种子与订单复用及哈希不变；(b) 路由与时区；(c) 交通时间与 CIQ 分离；(d) 站点补货、排队、充电；(e) 风雨/许可未知条件不能直接通过；(f) 三模式计时和系统边界相同；(g) 订单数守恒且重复主键为 0；(h) 成本与排放分项加总一致；(i) 汇总数可由 Parquet 重算；(j) paired 统计可重现。
对小样本进行端到端测试，输出测试命令、pass/fail、样本规模、报错及修复说明。不达到条件时停在小样本，不运行正式 30 种子全量仿真。

## 交付格式
先给出真实文件目录、已有模块清单、阻断问题和工程修改计划。随后执行审计与小样本验证。最终回报：新增/修改文件路径、关键数据结果、测试输出、未通过项、未取得证据项、正式主实验启动条件。不得宣称已完成任何没有实际运行和检查的步骤。先确保完整可复算，然后再考虑优化性能。
