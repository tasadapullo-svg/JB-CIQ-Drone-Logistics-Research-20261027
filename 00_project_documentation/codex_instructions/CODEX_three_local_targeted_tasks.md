# Codex 专用任务：E02有限证据补齐（仅三项，不新增实验）

研究基线：2026年5月1日至9月30日；马来西亚Johor Bahru，A区Causeway / B区Second Link；345 FCD节点、G1–G5不变；既有128组参考OD不作为真实订单；不重复9月质量审计。

请在我已有本地工作目录内读取 `JB_CIQ_E02_roadnet_V4_6_REAL_OSM_20261026.zip`、`JB_CIQ_E02_FCD动态速度准备与道路方向审查_V4.7.zip` 和本工作包，**不要重新建设OSM图，不修改原始FCD**。

## Task 1：TomTom → OSM有向证据
1. 搜索原TomTom采集工程配置、日志/保存的授权样本，对单次请求的`unit`设置产生SHA256+去密钥证明；若未显式指定，记录代码及调用版本，不将默认值视作直接存档事实。
2. 从确实保留的历史采样相关路段证据恢复geometry、OpenLR或行驶方向信息（按供应商许可仅私有保存）。当前新的实时API响应不得冒充2026年5–9月历史记录。
3. 依据明确的行驶方向、车道、OSM way/from/to节点和几何匹配逐条审核（优先G1中的46个节点）。不得将“最近边”“道路名称匹配”或OSM单行标记当作TomTom采样方向的证明。
4. 输出 `04_manual_FCD_direction_approvals_EMPTY.csv` 的填充副本；保留未证明项为NO，记录proof文件的sha和审核人。不得上传商业原始响应或密钥。

## Task 2：路网通行合法性/三点入口
1. 使用 `06_restriction_relations_overpass_requests.txt` 分A、B区取得OSM `type=restriction` 关系，解析from/to/via（via node及via way），记录取回时间/OSM版本/请求/sha。若道路way与relation快照不一致，登记变更风险，重点对涉及的OD转向核验。
2. 用可追溯的马来西亚边界矢量层裁剪/判定，输出每条选择路线上可能跨境或处于不明确国界附近的边，不依据OSM行政边界直接声称官方法定边界确定。
3. 核实A05、B02、B07真实机动车辆出入口及合法接入方式。参考`11_three_site_nearest_OSM_drivable_edge_candidates.csv`中的10个几何候选，不通过放宽100米吸附阈值伪造路由。将核实的入口坐标、道路边、证明文件写入`03_three_site_vehicle_entrance_audit.csv`，保持原参考坐标不变。

## Task 3：真实OD与独立旅行时间验收
1. **只针对已冻结的真实D1/D2或明确标记的合成订单OD**，筛选原参考OD，不强求128个候选全部成为订单。
2. 在时间依赖有向图上按实际出发时间逐边查询小时速度；不同边如跨小时，更新边进入时间。对有FCD方向核实的路段标注OBSERVED_DIRECTION_VERIFIED，对其余可建模路段标注MODEL_ASSUMED，对UNKNOWN不冒充实测。
3. 对关键OD取得独立的路由/导航时间样本，来源、日期、时刻、模式及车辆类型可追溯，预先冻结误差指标与合格阈值。报告每条路径FCD支撑里程占比、模型填补比例、转向约束、合法边界、车辆OD时间与样本误差。
4. 不计算无人机节省时间和CO₂e；正式门槛未通过时必须保持 `E02_DYNAMIC_OD_UNVALIDATED`。

## 数据文件与验收
每个文件同时保存原始/派生区别、SHA256、处理脚本、日志和来源；严禁泄露API密钥。运行`python validate_e02_evidence.py --folder <证据工作目录>`做**初筛**，随后独立核查其语义，不凭一个json布尔值宣称论文实验合格。

交付：`SOURCE_UNIT_PROOF`、`FCD_EDGE_DIRECTION_EVIDENCE`、`TURN_RESTRICTION_RELATIONS`、`MY_BORDER_CHECK`、`A05_B02_B07_ENTRANCES`、`FROZEN_OD`、`INDEPENDENT_TRAVEL_TIME` 七类证据和一个明确 PASS/BLOCKED/NOT_APPLICABLE状态的验收报告。除修正真正错误，不添加新的物流站点、配送模式或研究时间窗。
