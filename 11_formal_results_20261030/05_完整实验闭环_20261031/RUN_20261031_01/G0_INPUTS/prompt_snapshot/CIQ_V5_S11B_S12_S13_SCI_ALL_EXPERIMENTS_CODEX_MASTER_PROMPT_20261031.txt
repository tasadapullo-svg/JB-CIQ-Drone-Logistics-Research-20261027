# CIQ V5 无人机物流 SCI —— S11B → S12 → S13 全实验、全结果与投稿证据闭环
# CODEX MASTER PROMPT | 2026-10-31 | 中文正式执行版本

你现在充当本研究的“计算交通与无人机物流模型开发者 + GIS/气象数据工程师 + 科研统计审计员 + SCI 结果制作者”。你具有在本地 Windows 工程目录中读写文件和执行 Python/QGIS（若已安装）的权限。本任务不是撰写计划，也不是单纯生成表格和好看的图片：要逐文件读取、审计、修改新版本代码、实际运行、复算、做反例测试、出图、生成论文用数字和交付 ZIP；只有真实运行的结果才可标 PASS。缺少必要证据时必须标 HOLD，不能臆造任何观测、许可、参数或论文结果。

====================
A. 固定研究目的与最重要的边界
====================
1. 研究场景：Johor Bahru 的 Causeway 与 Second Link 周边 CIQ 影响区，现有 V5 A/B/C 三区共 68 个冻结候选节点（A29/B10/C29），新旧 WMP228 图层的准确来源必须明确。研究的是马来西亚一侧的“口岸周边合成配送”，不等同于实际获准跨境无人机物流。
2. 研究目标依次为：① 哪里在地理/道路/天气/情景空域条件下具有技术适用性？② 在什么时段、什么需求与资源条件下，UAV 能替代地面车辆并满足服务门槛？③ 在同等服务约束和可比运营/能源/成本边界下，什么固定站或移动协同配置是最低运营碳排放代理的可行方案？明确回答何时没有实际优势。
3. 冻结输入：2026-05-01 至 2026-09-30 的 153 天、30 随机种子、4,590 日期×种子基础场景、18 单/场景、82,620 冻结合成订单；V5 68 节点、天气、FCD、OSM 图以及旧 Stage 3–8 均不得修改。检查原始资料实际覆盖时区及首末时间戳，不能仅按报告中的日期概括。
4. 参考无人机：DJI FlyCart 30 与 Wingcopter 198 Cargo。OEM 标称信息 ≠ 任务级实测能耗。Wing 电池/任务能耗未经证实时必须用明示且有来源/理由的情景范围表示。
5. 主研究模式：M0（汽油车纯地面）、M1（固定站地空混合，按机型区分）、M2（车辆—无人机协同，按机型区分）。另建同一调度器内的 NO_UAV 控制。如果 M1_NO_UAV/M2_NO_UAV 是同一份结果，明言 SHARED_CONTROL；若架构有不同残余约束，须分别真正运行。S08 原 M0 30h 基线仅作历史参照，不得直接与 S11 24h 主实验当作同口径因果比较。
6. 预先确定论文主实验：STRICT_EXCLUDE_GT10KM、24h 运营窗口、相同订单/车辆数/调度资源与相同种子；保留 RELAXED_PROXY 作为敏感性情景。10km 是空间代表性审计阈值而非法律/物理禁飞界限，不得挑选有利于 UAV 的阈值充当主方案。
7. 严守边界：汽油燃烧 TTW CO2 + 电网运营 GHG 的指标仅可称 MIXED_BOUNDARY_OPERATIONAL_GHG_PROXY；它不是对称 WTW、全温室气体 LCA 或验证过的碳减排。Partial OPEX 不是 Total Cost。站点、BVLOS、CAAM SUP/ATF、NOTAM、CIQ 与跨境许可不存在完整证据时必须 HOLD。
8. 科学诚实：旧 S10 的约 30% M2 改善在 S11 严格试验中不再保留；绝不以恢复旧优势为优化目标。不准重抽“更好”的种子、不准删除坏天气订单、不准人为移动 V5 节点、放松约束、改写旧结果、隐藏失败。

====================
B. 目录、自动发现与只读保护
====================
主项目根目录：
C:\Users\DELL\Desktop\CIQ 无人机物流 SCI 研_20261026
候选历史 GitHub 工程：
C:\Users\DELL\Desktop\CIQ_Drone_Logistics_SCI_GitHub_20261028
请递归查找以下历史只读工程（以真实路径为准）：
- output_S07_S08_Codex_20261030（S07、S08）
- output_S08A_S09_S10_Codex_20261030\RUN_20261030_01
- output_S11_Corrective_Validation_20261030\RUN_20261030_01
- CIQ_V5_S11_CORRECTIVE_VALIDATION_COMPLETE.zip（最终版本预期 SHA-256：637aa153807b162b76a3add029e72063ada8d38a3403b67a14164b28571e7c4f；若本机有另一版本，必须查明版本链）
- CIQ_S11_INDEPENDENT_DEEP_AUDIT_20261031.md
- CIQ_V5_S11B_CODEX_MASTER_PROMPT_20261031.txt（早期 S11B 修复建议，仅供比对；以本总控指令为准）
- V5 活动 GPKG、QGIS 项目、旧 Stage 3–8、冻结订单、道路 GraphML、天气/ERA5、FCD 以及所有 SHA 清单。
请先扫描盘上存在的路径，不要因路径略有变化就停止，不要假定本机绝对路径等于上传者描述。保存 FILE_FOUND/MISSING/HOLD 与文件大小、SHA-256、版本来源、引用者、使用范围。

只在以下新目录写入：
C:\Users\DELL\Desktop\CIQ 无人机物流 SCI 研_20261026\output_SCI_Complete_Experimental_Closure_20261031\RUN_YYYYMMDD_NN\
需要创建 INPUT_AUDIT、S11B_REPAIRS、S12_EXPERIMENTS、S13_PAPER_RESULTS、FINAL_HANDOFF、packages。若 RUN 已存在，递增编号，禁止覆盖。所有旧目录只读；执行前后核对旧关键文件哈希是否变化。

安装环境要求：检查 Python 版本、GIS/QGIS 3.22.4、pandas/numpy/scipy/networkx/geopandas/shapely/pyarrow/matplotlib 等；记录冻结依赖和 pip freeze。无依赖就先尝试在新环境安装，无法安装则标环境 HOLD。对小规模 CSV/Parquet 可生成对应的可核验互换版本，不能声称一个未读取的 Parquet 已逐行复算。对于远程资料，记录原始 URL、出版者、适用日期、下载/检索时间、许可证和哈希；禁止冒充未成功获取的官方数据。

====================
C. 总体执行控制（必须执行、禁止空报告）
====================
阶段顺序固定：
G0 预检/独立复现/论文实验清单
G1 S11B-P0 模型硬缺陷修复
G2 S11B 公平控制/统计口径/复现封装
G3 S12-A 交通×天气×空间×任务证据补充
G4 S12-B 动态能耗/班次/资源/运营成本与碳边界敏感性
G5 S12-C 全量稳健性、消融、控制组、非支配 Pareto
G6 S13 GIS图件、Fig.1–7、论文表格与结果逐数追溯
G7 S13 SCI Results/Discussion/Limitations/结论与最终独立验收

每一关有真实脚本、原始输入哈希、输出账本、测试、审计日志与状态。状态仅 PASS / PASS_CONDITIONAL / HOLD / FAIL / NOT_RUN。发现 P0 失败，应优先修复；未修好不得以旧结果开展依赖该关的“论文主结果”推断。可以执行不依赖该 P0 的资料审查、绘图布局预检与代码准备，但不能伪造完成。若运行计算量过大，采用 2–3 个独立金标准案例→按区/种子分片→全量，保留进度/块校验/重试和汇总一致性；不能用小样本推断冒充全量结果。

====================
G0：输入审计、旧结果复现与完整实验表
====================
1. 解包 S11 与旧阶段 ZIP 到新只读快照，核对 ZIP CRC、清单 SHA、大小、行数、schema、主键及可读性；特殊核查旧联合 ZIP 曾出现的 3 个 __pycache__/*.pyc 列表缺项。新的归档规则应统一排除 __pycache__、*.pyc、临时文件，重建清单而不是偷偷把缺失标 PASS。
2. 复现既有 S11 STRICT 24h 的重要数字和单位：4,590 基础场景、82,620 订单；主运行 991,440 条模式订单/55,080 模式场景（旧设计为 2天气×6模式×4,590）；56,342 飞行与 1,487,220 地面路段的口径要区分全情景还是 strict；旧结果只作为回归基准而非修订后预计数。
3. 每个种子为一个完整 153 天重复；每种子 2,754 张订单。禁止把 30 个种子的累计运营成本/排放当成实际单次五个月运营数据。所有表格同时提供 TOTAL_ACROSS_REPEATS_AUDIT_ONLY、MEAN_PER_153DAY_REPLICATE 和 CI。
4. 建立论文实验矩阵：实验 ID、所回答 RQ、运行数据、数据来源、代码入口、参数来源、种子、时间范围、主次情景、输出主键、预计必要结果、验收门槛和论文 Fig/Table 映射。未经核验的“官方”源、未存在的 CSV、未实际运行的实验均打 HOLD/NOT_RUN。
5. 至少两个旧数据 golden-case 重放，手算/独立最短路与事件时钟对照；旧模型差异登记（S08→S10→S11），不得将 S10/S11 不同调度器的差值作单因素归因。
输出 G0_INPUT_REGISTRY.csv、G0_ARTIFACT_LINEAGE.csv、G0_EXPERIMENT_CATALOG.csv、G0_FREEZE_HASH_AUDIT.csv、G0_REPRO_DIFFERENCE_REPORT.md。

====================
G1：S11B 模型结构硬缺陷（必修，必须真实重跑）
====================
G1.1 M1 11固定站点约束：
- 从冻结 V5 与站点清单读取经过原工程定义的 11 个 M1 固定发射点 ID、位置、容量与可用性；禁止 `stations.setdefault(origin_node_id, ...)` 或动态为所有任务起点创建满电发射站。
- 任务必须有清晰的包裹到站地面路径、起降与回收站点、站点—需求匹配及库存/操作员/电池资源。没有合规站点—订单接驳路径的任务不可“原地凭空发射”，必须走地面回退并记账。
- 统计修复前动态创建站点数量、站点外任务、受影响飞行和成本；若 11 点清单缺失则 M1 正式结论 HOLD，不得造点。

G1.2 任务时钟和截止窗口：
- 统一每张订单 release、pickup、dispatch、vehicle arrive、UAV launch、delivery、return launch、recovery、ground return depot、driver relief、completion 事件；所有事件 UTC 存储，展示使用 Asia/Kuala_Lumpur 及明确小时边界。
- 服务准时以订单 deadline 计算；业务完成、飞行/回收/车辆返仓是否超过窗口单独判定，主情景不允许 M1 自由超时而地面受限；8/12/24/30h 均实际重新调度，不是后裁切。
- M2 若配送已到、无人机未回收，不能将设备当场释放使用；车辆等待与同点回收、回仓/可驻外的差异必须成对情景表示且计入时间、里程、成本。
- 防止跨日随机种子或场景车辆状态偷渡；如果跨日可用必须显式日际连续运营和司机换班账本。

G1.3 一致的航路/几何/气象筛查：
- M1/M2 使用相同的技术筛选内核：载荷、航程、有效往返距离、reverse_geometry_proxy、WMP228参考风险层、天气缺测/空间距离、沿程/起降事件风雨；调度架构不同只能改变车辆/发射位置/时间和资源，不能偷偷改变飞行安全门槛。
- 必须核对行政国界、岸线与候选直线是否穿越未经验证的禁飞/边境区域；参考圆不能当权威 CAAM 边界。地理无法核证的航线 HOLD，不可擅自移点。

G1.4 连续资源：
- 每架 UAV、每块电池、车辆、司机、操作员、充电器、站点分别有唯一 ID 与时序状态。建立能量守恒（kWh/SOC）、安全余量、充电功率/效率、换电时间、站点队列、车辆等待、任务唯一执行和返航占用检查。
- 不可在飞行中充电、不可一块电池同时分配两机、不可由车载充电产生未入账能量。M2 可单独采用已明确的有限预充电备用电池场景；若要增加车载充电须给出电源、功率和时间依据。

G1.5 能耗扰动真正重新优化：
- 0.5×、1×、2×以及载荷/逆风/航程/储备 SOC 为仿真输入，而非对飞行结果乘系数。每一情景都重新评估资格、起飞时刻、排队、SOC、电网能量、车辆回退、准时率、运营排放和成本。
- 报告在哪些订单上任务选择改变、改变前后原因；Wing 能耗若无 OEM 必须保留情景边界。

G1.6 代码和守恒反例测试：
- 至少 12 类真实可运行单元/集成测试：非法新站点、站点库存、M1 超过运行窗口的送达/回收、M2 无法返仓、反向几何代理、航路穿越风险层、跨小时天气、SOC不足、电池双占用、充电时间、车辆装载、司机换班/成本、重复服务和未服务订单记账。
- 至少 3 个小规模 golden cases 以独立求解器/人工演算验证时序与成本；实际全量订单中抽取极端天气/远距离/临界 SOC 场景回放。

主24h严格情景全量重跑，8/12/30h 及 relaxed 情景至少在 G1 PASS 后按阶段矩阵执行，必须标明哪些组合已完成。G1 FAIL/HOLD 时立即阻断相关 S12 主结果。
输出 G1_DEFECT_LEDGER.csv、G1_FIXED_STATIONS.csv、G1_EVENT_CLOCK_LEDGER.parquet、G1_SOC_LEDGER.parquet、G1_BEFORE_AFTER_SCENE_DIFF.csv、G1_QA_RESULTS.json、G1_CORRECTED_MODEL_VERSION.json。

====================
G2：公平的实验对照、复算口径与统计基础
====================
1. 先固定同一订单、时段、FCD、车辆/司机工作量、能耗、能源价格、求解算法、运行预算和窗口。对控制组建立真正可关闭无人机功能的同调度器开关。必须清楚写明纯地面 M0_COMMON_24H、NO_UAV_SHARED 或架构专属 NO_UAV 的含义；不得从 S08 M0_30H 直接借用不能比的数据。
2. 每一模式必须为全部冻结订单生成一行，包括未服务、未起飞、地面回退、准时/迟到，不能过滤无效订单改变分母。按 (date, seed, order, mode, weather_scenario, work_window, param_scenario) 建立稳定复合主键。
3. 拆分地面调度改善、UAV 增量效应、天气/资源约束与交互作用。禁止把不同调度器的整体差称作 UAV 净效应；若使用准因果/消融措辞，严格限定为模型内开关实验。
4. 按每个 seed 的153天重复归一，审计成本/排放/航程的单位：km、L、kWh、kg、MYR、minutes、kgCO2/kgCO2e；成本精确到分，累计和浮点误差分别记录。
5. 修复 BREAK_EVEN：将 30 seed 总节省转成每次五个月重复的均值、分位和可信阈值，注明是五个月还是年化；当部分 OPEX 差额为负时报告“无正可覆盖固定成本”，不能机械给出正阈值。
6. 检验算法质量：公平设置相同时间/迭代/初始解预算，给小规模 MILP/精确搜索对照、随机多启动比较、解质量差异；数据量较大时针对代表场景而非声称全局最优。
7. 独立读取地面路段、UAV 任务、SOC账本，确认每条物理路段和每次飞行仅记账一次，车辆/货物载荷/人员/能源守恒，并核对结果表到明细的可追溯性。
输出 G2_MODE_PAIRING.csv、G2_PER_SEED_153DAY.csv、G2_ORDER_SERVICE_STATUS.csv、G2_BREAK_EVEN_CORRECTED.csv、G2_FAIRNESS_ABLATION.csv、G2_MODEL_QUALITY_BENCHMARK.csv、G2_LEDGER_RECONCILIATION.json。

====================
G3：S12-A GIS/需求/交通/天气证据与分层实验
====================
A. V5空间：验证68冻结节点A29/B10/C29的ID、坐标系、点位与边界、主路、岸线、国界及 CIQ 区域关系；记录 21 个 >100m 接入候选、OSM不是研究期历史快照、节点功能（发射/交接/需求）、可实际靠近CIQ的合法情景场地。保持所有原数据只读，无法证据闭合则 HOLD。输出 QGIS 3.22.4 可打开的修订展示工程，而不是把图像替代 GIS 工程。
B. 冻结合成订单：追溯采样框、起终点、日期时段、距离、载荷、deadline、需求权重、随机过程、A/B/C 分布与口岸区位关系。检查是否有不可能 OD、跨境路径、异常大/小重量、重复；不得为了提升 UAV 表现重生成订单。必要时以单独 EXTERNAL_VALIDITY_SCENARIO 运行需求扰动，不替代主订单。
C. FCD 与路网：验证研究日期3,672小时及345节点代理覆盖、缺失与非正速度处理、地理匹配、方向缺失、OBD/OSM不同时代的边界。对高峰、低峰、雨天和跨小时出发时刻，进行分区分时逐边精确路由对照；不能用缓存误差0.228%宣称真实速度准确度已验证。缺方向观测则留方向情景敏感性。
D. 天气：验证 ERA5/历史天气实际变量、单位、质量标识和 5个月小时序列；研究节点距天气网格距离、缺测、雨风分布与极端时段。按实际飞行轨迹穿越的空间、起降/返航/跨小时事件做时空筛查。5/10/15/20/25km气象空间距离作为一组预声明敏感性，而非事实上的安全禁飞半径；如能取得本地官方/独立观测则先做数据与时间点校验，并报告 MAE/Bias/coverage，再决定是否作为替代输入。
E. 必须输出 GIS/道路/天气/订单分层的核验与明确控制变量的对照：A/B/C、Causeway与Second Link附近、月份、工作日/周末（节假日若无经过核验的日历则不要标假日效应）、小/大订单、雨风等级、道路拥堵等级。样本少的分层标 n 与高不确定性，不以单点差异写因果结论。
输出 S12_SPATIAL_NODE_AUDIT.csv、S12_ORDER_GENERATION_EVIDENCE.csv、S12_FCD_WEATHER_QC.csv、S12_WEATHER_DISTANCE_SWEEP.csv、S12_MONTH_ZONE_STRATA.csv 和 GIS版本/源数据登记。

====================
G4：S12-B 参数与运营假设的动态敏感性
====================
在 G1/G2通过的修订模型上执行下列主线；所有影响技术资格/SOC/车辆回退的参数都必须进入调度输入并真正重算，不得只乘汇总比例：
1. 电池与UAV：DJI / Wing 的名义/低/高耗电、载荷、飞行速度、风雨、技术航程、可用能量、保留SOC、备用电池数、充电功率、充电效率、换电时间、操作员并发与 UAV 台数（0/1/2/3）。若机型电池无实证，仍为 SCENARIO。
2. 地面与运营：8/12/24/30h、司机轮班/车辆连续运营（严格区分“每日零点后有多少小时”和“人员每班工作时长”）、司机工资、车辆油耗与燃油价、订单时窗、车队容量、站点能力、车辆到发射点等候与返仓约束。避免完全笛卡儿积造成不可用计算；预先筛选单因素和科学合理的小规模正交/拉丁超立方组合，再对论文关键情景进行完整4,590基础场景重跑，分清 PILOT 与 FULL。
3. 天气压力试验：严格10km主方案、5/15/20/25km的空间敏感性与缺测规则；风/雨极端时的等待、取消、回退；当独立气象不可得，不能将空间阈值放松视为真实可飞。
4. 能源排放：燃油TTW CO2、上游燃油因子若有独立数据可作为独立WTW情景、电网排放因子地域年份、电网电耗/充电损失；所有边界分别列、禁止混称。应给出达到不低于控制组排放的 breakeven grid factor/energy-per-mission，但仅对可追溯方程与明确任务集合有效。
5. 成本：PARTIAL_OPEX 与 SCENARIO_FULL_COST 分开，折旧期、资本（机体、固定站、充电设施、电池、车辆）、人工/保险/许可证/维护、资产使用率、运营天数、年化方式、汇率/价格基年登记。如果缺可靠报价可计算 LOW/BASE/HIGH 灵敏度，不可凭空冒充市场采购价；无法核验则 HOLD。建立公平分摊规则且不允许一项费用双计。
6. 每个参数情景输出订单级服务、飞行、电耗、路段、排放和成本；每个聚合结果必须可追溯至 PARAMS.yaml + VERSION_ID + 原始 ledger；计算量过大时完整主情景与关键敏感性全量运行，其余可明确标 SUBSET，绝不能宣称 FULL。
输出 S12_SCENARIO_REGISTRY.csv、S12_DYNAMIC_SENSITIVITY.csv、S12_COMPLETION_AND_ONTIME.csv、S12_EMISSION_BOUNDARY_MATRIX.csv、S12_FULL_COST_SCENARIOS.csv、S12_BREAK_EVEN_AND_THRESHOLD.csv。

====================
G5：S12-C 验证、统计、消融、Pareto与论文研究问题
====================
1. 评价主模式与公平控制的样本单位为30次153天随机重复，配对同日/同订单，另以周/月块与日期-种子双向依赖做稳健统计；不能把82,620个模拟订单当独立真实实测样本，也不能只用 p值代表实际价值。输出效应大小、95%CI、实际服务约束可行性、结构参数变化的结论反转频率和分层 n。
2. 消融实验至少有：NO_UAV、放宽vs严格天气、动态事件vs订单发布时间天气、连续SOC开关（仅诊断）、算法同预算vs旧算法、M1站点固定开关（非法情景只用于解释旧结果，不能视作主配置）、M2回仓约束开关、能耗低基高。每一项需单独控制其余因素，明确 ONE_FACTOR vs MULTI_FACTOR；不允许把S10与S11的多处同时变化归咎于某单因素。
3. 服务门槛以已有预注册完成率≥95%、准时率≥90%为主约束；只分析符合门槛的配置作为服务可行集。非支配 Pareto 要在同一情景、相同服务/资源口径的真实候选上用时间、成本、运营排放代理计算 dominance；允许有约束可行但被支配的方案。必须输出逐对 dominance 证据、非支配集及可能的低碳选择；“非支配”不等于已证明全局数学最优。需要时加足量不同配置（站点容量、车/UAV数、电池/充电）以形成有意义的 Pareto，而不是只有四个 UAV 模式。
4. 以最低碳为目标，在达到服务门槛和合理成本限制后选择条件性配置；如果 NO_UAV 优于所有机型或不存在经济可行混合方案，应直接报告“无 UAV 最优/没有证据支持低碳混合模式”，不得强行保留无人机为胜者。
5. 进行近似/精确小实例对照，或可复现的启发式上界下界质量检验；不同调度架构的比较在等计算预算、同车辆数、司机工时和截止要求下进行。
6. 明确哪些结果仅模型内统计显著，哪些是工程效果大小，哪些因参数证据不足而 HOLD；对 Wing 与 DJI 机型排序不做过度确信判断。
输出 S12_PAIRED_ESTIMATES.csv、S12_CLUSTERED_CI.csv、S12_ABLATION_EFFECTS.csv、S12_ALGORITHM_BENCHMARK.csv、S12_PARETO_CANDIDATES.csv、S12_PARETO_NONDOMINATED.csv、S12_DOMINANCE_AUDIT.json、S12_MAIN_FINDINGS_CLAIM_MATRIX.csv。

====================
G6：S13 完成论文所有图表（严格基于真实数据）
====================
先建立 MANUSCRIPT_FIG_TABLE_SPEC.csv，逐项列明画图目的、所回答RQ、来自哪些 CSV/Parquet/GPKG、关键列、样本/统计口径、单位、文字证据和是否已通过审计。优先 SCI 简洁排版、矢量 PDF/SVG + 600dpi PNG/TIFF，保持文字与图形不遮挡、黑色文字、单位明确、色盲友好、所有地图/照片标注真实来源和许可。若无数据，保留 FIG_HOLD 及原因，不画虚假的地图/图表。所有 figure 的 panel 编号、缩写、颜色与数字必须跨图一致。

Fig.1 研究区及真实空间网络：总览 JB/两 CIQ 廊道与 A/B/C 三区，冻结68节点、11个真正固定站（通过G1才展示）、V5研究路网、岸线、国界及新版可核验 WMP228 风险边界；可增加三个分区 inset 以避免拥挤；标坐标系、比例尺、指南针和数据来源。不要沿用地理错配旧图，不要使用未经验证的真实空域多边形，也不能以网络示意充当地理精准图。输出可打开的 QGIS 3.22.4 工程与GIS图层及独立高分辨率导出。
Fig.2 研究方法/数据与门槛流程：简洁展示“空间与合成需求→历史天气/FCD→候选航段筛查→M0/M1/M2→动态天气/SOC/调度→时间/能源/成本→公平对照→稳健性/Pareto”，不堆叠大段文本；所有框与真正代码/输入节点对应。
Fig.3 研究对象与无人机配置：在真实GIS底图中标注发射/交接场地及技术航程场景，另一子图对两机型载重/航程/风限制及情景能耗画可核对示意；OEM 与假设的参数分栏，提供来源；需要机型图片时只能用作者自制示意或授权许可的图片，不得臆造制造商性能。
Fig.4 2026年5–9月天气与道路交通：真实历史天气/风雨窗口、FCD交通状态与空间节点/路网位置的多面板图，展示每小时或适度聚合的风雨/速度分布与 strict/relaxed 的分歧；天气测点位置不得画成“实测站”若实际是ERA5网格。
Fig.5 可行飞行、任务分配与配送表现：严格主方案和关键敏感性下，按机型、M1/M2、三区/月份显示 UAV 资格→实际调度→回退→迟到/未服务的任务流与准时表现；展示配对公平控制和效应区间，禁止只展示已飞任务成功率。
Fig.6 运营排放与成本：保留用户已确定的两面板 (a)(b)（不增加(c)），a 按统一边界展示汽油TTW/网电排放代理分解、相对控制组及不确定性，b 展示部分OPEX、合理的资本敏感性/break-even；不要用累计30种子冒充单次五个月值，也不得标题称LCA净减排。
Fig.7 鲁棒性、最低碳可行配置及 Pareto：天气空间阈值、能耗、站点/UAV电池资源、班次或不同区域的关键结果；真正的服务约束 Pareto 前沿并标识 NONDOMINATED、被支配及 HOLD 方案，突出模型不确定性和零/负收益区域，而不是人为突出UAV。

论文表格至少：T1 数据源/时间范围/空间精度与证据等级；T2 研究配置和机型能源/资源参数（OEM vs scenario）；T3 模式/基线与同口径主结果；T4 订单分区/月份及天气可飞性；T5 配对统计/CI；T6 成本与排放边界及break-even；T7 稳健性/Pareto；可按目标期刊篇幅分主文与补充。每张图表出“原数据切片 CSV、绘图 Python/QGIS脚本、caption EN、图中数字审计 JSON、脚注/来源、PNG/PDF/SVG（可提供则全部）”。

结果和图件三轮审查：①数据主键/单位/公式；②图形空间地理及标签、可读性/版式/许可；③与正文/表格/CI/HOLD一致。不通过不得标 FINAL_FIGURE。

====================
G7：S13 论文证据冻结与 SCI 交付
====================
1. 基于**真实通过的 G1–G6 输出**撰写英文论文可用的 Methods、Results、Discussion、Conclusions、Limitations、Abstract 数值提要。明确区分条件性仿真、实际观测和未来数据需求；不得用历史 S10 大幅优越数值代替修订数据。非稳健的结论也要如实报告。
2. 建立论文完整可追溯矩阵：研究问题→实验ID→原始冻结文件SHA→代码commit/version→参数YAML→结果CSV/Parquet行键→Fig/Table→论文段落→证据等级→可能HOLD。所有百分比、样本量、统计区间和货币值都要自动从最终 CSV 生成并核对。
3. 若用户上传了目标期刊模板/实际文献库，按原模板和真实参考文献编写；没有则按中性交通物流 SCI IMRaD 栏目输出，不臆造文献、DOI、IF/Q分区及作者数据。
4. 规范研究创新点与定位：CIQ 周边交通—天气—三分区地理与 UAV 动态资源耦合、等调度器控制、对约束敏感性的反转证据以及可行最低碳配置，而不是简单“无人机优于车辆”。评估哪些结果足以回答三大研究问题；如某问题回答不完整，以证据缺口列出。
5. 完整交付运行数据和可审计复现：源代码（不要只放日志）、README、环境锁定、参数 YAML、运行入口、数据字典、输入 SHA、实验设计、测试、结果汇总、论文图表及 LaTeX/Markdown 草稿（DOCX 若具备工具可生成）。保留所有旧实验不覆盖。
6. 真实数据与敏感数据处理：公开仓库只发布有授权的公开/合成数据，不上传 API 密钥、隐私地址、未经许可的商业原始FCD、受限航图或厂商资料；GitHub 文件要有可公开许可核查。
7. 每个阶段 ZIP 和联合 ZIP 都要 ZIP CRC、新目录解压、逐成员 SHA、数据清单内部SHA匹配。报告所有排除项，例如 __pycache__/pyc，避免之前清单含而 ZIP 不含。外部源数据不包含在 ZIP 时，必须有明确 READONLY_EXTERNAL_INPUTS 清单并说明独立复现需另取哪些文件，不能声称真正离线一键复现。

====================
D. 状态准则、失败停止线与验收指标
====================
- 订单、场景、飞行、路段、SOC事件复合键重复数必须0；每模式每情景的冻结订单全部有结果（包括未服务）。任何漏单/双服务 FAIL。
- 车辆载重、无人机载荷、SOC/充电功率、司机资源、站点库存、任务时间/位置守恒必须无重大违规；若数值浮点残差存在，报告数值大小与单位。对不可考证的实际驾驶合法工时/空域必须区分模型合规与现实合规。
- FCD/天气出现异常或不可获取数据时，不得默认为晴天畅通，必须按预定义回退或 HOLD；所有处理能审计。
- 关键主比较使用相同种子、订单、服务时间门槛、资源和求解预算，并报告控制组、模型效果大小、30种子区间与时间自相关敏感性。
- 主研究严格24h阈值（>=95%完成、>=90%准时）不随结果调整；若不满足则如实报告不可行，不得删除未服务订单以提高准时率。
- 敏感性标签分为 FULL_RERUN / SUBSET_RERUN / ANALYTIC_BOUND_ONLY / NOT_RUN / HOLD；不能将解析上界误报完整仿真。不得制造现实世界因果或许可证明。
- 缺Wing任务级实测、全生命周期清单、批准航线、固定成本正式报价时，可以提交 CONDITIONAL SCI 论文，但结果用 SCENARIO；正式部署、LCA、真实机型优劣等主张维持 HOLD。
- 每关 gate 完成必须输出 pass/conditional/hold/fail、失败原因、实际跑过的命令、时间与日志、数据条目数、异常数、是否全量、文件 SHA和下一关 GO/NO_GO。不得自动把未运行的关卡置为 PASS。

====================
E. 必须交付的结果清单与项目结构
====================
在新工作目录下固定生成：
00_PROJECT_EXECUTION_INDEX.md
G0_INPUTS/G0_EXPERIMENT_CATALOG.csv
G0_INPUTS/G0_INPUT_REGISTRY.csv
G0_INPUTS/G0_REPRO_GATE.json
S11B_REPAIRS/S11B_BUG_FIX_AND_LINEAGE.csv
S11B_REPAIRS/S11B_CORRECTED_STRICT_24H_MODE_SUMMARY.csv
S11B_REPAIRS/S11B_OLD_NEW_ORDER_PAIRED.csv
S11B_REPAIRS/S11B_TEST_AND_AUDIT_REPORT_CN.md
S12_EXPERIMENTS/S12_SCENARIO_REGISTRY.csv
S12_EXPERIMENTS/S12_MASTER_MODE_SUMMARY.csv
S12_EXPERIMENTS/S12_PER_SEED_153DAY_RESULTS.csv
S12_EXPERIMENTS/S12_ORDER_LEVEL_RESULTS.parquet
S12_EXPERIMENTS/S12_GROUND_EDGE_LEDGER.parquet
S12_EXPERIMENTS/S12_UAV_FLIGHT_SOC_LEDGER.parquet
S12_EXPERIMENTS/S12_SENSITIVITY_RESULTS.csv
S12_EXPERIMENTS/S12_PAIRED_STATISTICS_AND_CI.csv
S12_EXPERIMENTS/S12_BREAK_EVEN_AND_FULL_COST_SCENARIOS.csv
S12_EXPERIMENTS/S12_PARETO_CANDIDATES.csv
S12_EXPERIMENTS/S12_PARETO_NONDOMINATED.csv
S12_EXPERIMENTS/S12_ABLATION_AND_CAUSAL_BOUNDS.csv
S12_EXPERIMENTS/S12_SCI_EVIDENCE_AND_HOLD_MATRIX.csv
S13_PAPER_RESULTS/figures/Fig1...Fig7及绘图代码、图注和源数据
S13_PAPER_RESULTS/tables/T1...T7及对应源数据
S13_PAPER_RESULTS/S13_SCI_METHODS_EN.md
S13_PAPER_RESULTS/S13_SCI_RESULTS_EN.md
S13_PAPER_RESULTS/S13_SCI_DISCUSSION_EN.md
S13_PAPER_RESULTS/S13_SCI_CONCLUSIONS_LIMITATIONS_EN.md
S13_PAPER_RESULTS/S13_ABSTRACT_NUMERIC_SUMMARY_EN.md
S13_PAPER_RESULTS/S13_FIG_TABLE_CLAIM_TRACEABILITY.csv
S13_PAPER_RESULTS/S13_MANUSCRIPT_CLAIM_AUDIT.csv
FINAL_HANDOFF/FINAL_STAGE_GATE_MATRIX.json
FINAL_HANDOFF/FINAL_SCI_ACCEPTANCE_REPORT_CN.md
FINAL_HANDOFF/FINAL_UNRESOLVED_EVIDENCE_GAPS.csv
FINAL_HANDOFF/FINAL_REPRODUCTION_GUIDE.md
FINAL_HANDOFF/FINAL_FILE_SHA256_MANIFEST.csv
FINAL_HANDOFF/ZIP_FRESH_EXTRACTION_TEST.json
packages/CIQ_S11B_CORRECTIVE_COMPLETE.zip
packages/CIQ_S12_EXPERIMENTS_COMPLETE.zip
packages/CIQ_S13_PAPER_RESULTS_COMPLETE.zip
packages/CIQ_FULL_SCI_EXPERIMENTAL_EVIDENCE_COMPLETE.zip

文件清单如与实际合理实验命名不同，可建立字段映射，但不允许以空文件代替成果。不能得出的图、表或统计要生成 <name>.HOLD.md 并列入 FINAL_UNRESOLVED_EVIDENCE_GAPS.csv。完整项目包如因授权、体量或上游数据依赖而不包含全部源文件，必须明确分为：SELF_CONTAINED / REPRODUCIBLE_WITH_EXTERNAL_INPUTS / NOT_REPRODUCIBLE，并输出详细输入取得步骤。各阶段含真正源代码、数据、QA、日志、版本和 manifest，而不只是文档。

====================
F. 最终回答格式与立即执行命令
====================
开始即先打印并保存：
1. 真实探测到的项目/数据目录及源哈希检查结果；
2. 冻结研究实验矩阵与已完成/缺失实验列表；
3. S11B P0 前置缺陷定位清单（站点、时钟、几何、SOC、能耗、成本）；
4. 下一条将执行的实际 Python/命令行命令。
随后**实际执行** G0→G7，运行本机代码、写入新输出目录和分阶段 ZIP。不要只输出计划、提示词、占位 CSV 或预测数字。未完成任务写 NOT_RUN/HOLD，失败写 FAIL，给出证据和可执行修复路径。
最终答复必须依次列出：研究主线回答、最终主实验真实数值和CI（如有）、最有说服力的消融/稳健性结论、每个 Fig/Table 的真实路径与审计状态、全部阶段真实运行状态、未闭合证据的影响、可投稿的与禁止的表述、阶段ZIP绝对路径/大小/SHA-256/CRC/新目录解压结果。

现在不要再向我索要当前对话里已经给过的路径和文件清单；自动搜索。只在确实缺失会阻断全部后续的本地关键数据或外部凭证时，清楚列出缺项及下一步，而不是编造。进入 G0，开始执行。
