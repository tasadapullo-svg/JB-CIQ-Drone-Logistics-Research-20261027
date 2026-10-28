# 柔佛新山 CIQ 周边低空物流论文 RQ1–RQ3 逻辑与证据完整性审核

审阅日：2026-10-28。结论：RQ1→RQ2→RQ3 的逻辑成立；现有结果可支持条件性仿真比较，但未达到合法场站、真实部署与最低碳部署图的最终证据要求。

## 拟冻结研究问题
- RQ1: Where and under what spatial, technical and regulatory-screening conditions could a drone-assisted delivery network be feasible in Johor Bahru?
- RQ2: When and for which comparable delivery tasks does drone-assisted logistics improve end-to-end delivery performance relative to ground delivery?
- RQ3: Which feasible delivery mode minimizes operational GHG emissions while satisfying service and cost constraints, and what conditional deployment strategy follows for the two JB corridors?

## 因果与决策链
1. 对研究对象（国内 CIQ 邻近配送，不含跨境查验）及需求样本进行限定；RQ1 定义可选场站、航段、技术可行OD和待审批状态，拒绝将锚点认作已批准场站。
2. 对 RQ1 允许进入候选比较的任务，在 RQ2 采用同订单、同日期、可比车队运力/总成本和服务时限，输出端到端均值/P95/准时率/回退占比；区分 coverage、完成率和 SLA。
3. RQ3 在 RQ1 候选集合与 RQ2 服务约束内，分别对 M0、M1、M2 最小化同一任务集合、统一核算边界的运营 kgCO2e，受预算及服务要求约束；若不可行或无可靠差异，保留 M0，不能硬推荐无人机。
4. 仅在有地理坐标及已核验约束后，允许生成条件性部署区划图。建设审批需要 CAAM 审批及土地进入权，不属于仅凭模型可以证实的结论。

## RQ1：证据状况与缺口
**已有：** Stage 6 研究工程、OSM 道路与参考 OD、ERA5 风场、合成订单、19 个坐标参考锚点。文件 `02_关键数据/19_site_reference_anchors_NOT_LAUNCH_PADS.csv` 中 19/19 条均标为 `REFERENCE_ONLY_OR_SEARCH_ZONE`；`site_access`、`landowner_permission`、`uav_airspace_approval`、`building_obstacle_audit`、`parcel_demand_evidence` 均 `NOT_VERIFIED`。原模型自身 `model_status=HYPOTHETICAL_NO_SITE_PERMIT_UNCALIBRATED_TRAFFIC`。
**不能证实：** 合法站点数量、可实际部署航段、实际订单覆盖、获批跨境航线。
**外部约束：** CAAM 无人机载货/BVLOS 涉及 Special UAS Project；AIP/AIP SUP/NOTAM 依生效日期与空域逐段核对。监管筛查不等于已获许可。官网 https://www.caam.gov.my/public/unmanned-aircraft-system-uas/ 和 https://www.caam.gov.my/public/ais/ 。
**最低补强：** 对19坐标进行场站可用性分类、空域风险初筛、障碍/地面风险与路线可行性规则，生成 route_id—站点—OD—天气—法规状态—证据来源全表；把“未知审批”单独列状态，不可与“禁止/可飞”混同。

## RQ2：证据状况与缺口
**已有：** 12资源配置、30配对种子、5个固定日期、1,800配置—日期—种子基线，G09在起飞时刻重查气象及回退，G11按固定车型资源池重仿真与配对 Bootstrap。
**证据限制：** A区输入14943、可评价9245（61.87%）；B区输入14899、可评价6715（45.07%）。这仅是道路/交通数据下的模型可评价覆盖率，非实际送达率或RQ1航路覆盖。时间的分母为可评价订单，成本/排放以全部输入订单分母。G11以日级汇总为主，最新模型逐订单 P95/SLA 未独立复核。
**重要混杂：** B区 G10共享车池 M0约40.00、M2约39.78分钟；G11固定池 M0约54.87、M2约39.78分钟。M0资源池变更带来的延误不能归因于无人机技术。
**最低补强：** 相同车型资源/预算对照，同订单逐单状态与时间戳、同一定义SLA/P95，天气失败后回退对照；按小时/天气/两区分层。5个固定日期不可代表全年/五个月每日效果。

## RQ3：证据状况与缺口
**已有 G11_POOL_BASE 条件性结果：**
- A M0：15.406min、10.1336 MYR/输入订单、0.45982 kgCO2e/输入订单。
- A M1 每站2架：15.375min、16.4553 MYR、0.39110 kgCO2e（与同区 M0 比，排放-14.95%、成本+62.38%）。
- A M1 每站4架：15.028min、20.0716 MYR、0.39031 kgCO2e（排放降幅略大但额外成本高）。
- B M0：54.870min、13.5279 MYR、1.21846 kgCO2e。
- B M1 每站2架/35min：54.502min、36.2069 MYR、1.26605 kgCO2e。
- B M2：39.783min、16.9583 MYR、1.68588 kgCO2e；时间差被资源池混杂。
**排放边界：** 汽油/柴油燃烧加无人机购电，非生命周期。采用 MGTC petrol 2.06916 kgCO2e/L、diesel 2.57082 kgCO2e/L、半岛电网 0.740 kgCO2e/kWh（来源 https://lcosbasic.mgtc.gov.my/ ），必须注意系数的年份和实际边界。车辆燃油与电池功率、JB物流车队组成、干线油耗、车型专属非能源成本仍含假设。
**严谨决策：** min_m E(m|a,t,D) s.t. m可运营且处于条件性筛查/批准范围、完成率≥Smin、P95≤Tmax、C≤Cmax、同一需求集；若所有无人机模式不满足条件或优势不稳健，则返回M0/不作新建建议。正式部署建议要固定预算/SLA，否则“最低排放”和“值得部署”不是同一个问题。
**最低补强：** 基于同队列/同车队运力的模式重新排序；微小排放差识别容差与置信区间；成本可承受阈值/边际减排成本与B区柴油干线零减排临界点；以可核实地理单元输出M0/M1/M2条件性策略，而不是只报告A/B区均值。

## 最小实验验收
- P0 F1 RQ1空间候选：19参考点逐点/航段筛查和证据等级；不把监管待审批误写为合法。
- P0 F2 RQ2公平性：匹配车型资源、相同需求集合、完整逐订单P95/准时率/失败回退。
- P0 F3 RQ2天气：实际发射/返航条件与到站发现禁飞回退情景。
- P0 F4 RQ3部署：复核 125cc、1.6L、1.8L和柴油干线能源+TCO参数，求排放最小模式、碳阈值、成本/SLA约束和稳定性。
- P1：更多交通气象匹配日、具体机型功耗和外部道路速度/站点可进入性，按论文声明是否提高为必做。

## 基础文献
- CAAM UAS SUP (载货及BVLOS): https://www.caam.gov.my/public/unmanned-aircraft-system-uas/
- CAAM AIP/NOTAM: https://www.caam.gov.my/public/ais/
- JPJ 官方登记数据（注册不等于在用配送车队）: https://data.gov.my/dashboard/vehicle-registrations
- MGTC 统一核算口径: https://lcosbasic.mgtc.gov.my/
- MOF/OpenDOSM 周油价: https://open.dosm.gov.my/data-catalogue/fuelprice
- Critical assessment of emissions, costs, and time for last-mile goods delivery by drones versus trucks, Scientific Reports (2023): https://www.nature.com/articles/s41598-023-38922-z
- Facility location decisions for drone delivery: A literature review, European Journal of Operational Research (2024): https://www.sciencedirect.com/science/article/pii/S0377221723008123
- Last mile delivery with drones: A carbon emissions comparison, International Journal of Sustainable Transportation (2024): https://www.tandfonline.com/doi/full/10.1080/15568318.2024.2407150
- Investigating the emissions effect of integrating drones into mixed-mode logistics, International Journal of Sustainable Transportation (2025): https://www.tandfonline.com/doi/full/10.1080/15568318.2025.2564851

## 论文结论允许级别
可写：在研究者定义的固定五日期、合成OD及其空域条件假设下，A区M1可呈现运营排放降低但成本增高，B区M1受柴油干线影响显著，摩托车较多时无人机减排空间可能缩小；严格前沿会随车辆池、成本与天气变化。
不可写：已找到合法起降站、已核实JB真实配送车型占比、普遍无人机最低碳、真实节时27.5%、跨境通关时间减少、已验证生命周期净减排或投产建议。
