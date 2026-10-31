# SCI 核心数学定义和防止错算规则

## 1. 同任务与三模式公平比较

令固定任务总体为 T，订单 i 对于 m 模式的完成状态为 s_i,m∈{0,1}，准时为 a_i,m∈{0,1}。

- 总服务率 = sum_i(s_i,m)/|T|；分母必须为完整固定任务总体，包括失败、禁飞与兜底。
- 总准时率 = sum_i(a_i,m)/|T|；可另报告已完成订单中的准时率，但不能替代完整需求口径。
- 任务级门到门时间只对实际完成任务有值；禁止将缺失视为 0 秒或把不可达任务删除后声称总体改善。
- 在 M0 与其他模式同时完成任务的 matched cohort 上报告配对时间差，但同时汇报全任务服务率与失败状态分布。

## 2. 汽油车 TTW CO2

- 实际油耗：fuel_L = (loaded+empty+return+reposition distance_km)*validated L_per_100km/100 + nonoverlapping_idle_hours*validated L_per_hour。
- 如油耗模型已在总段油耗中包含怠速，不再单独加怠速。
- 如果燃油因子来自 IPCC kg CO2/TJ，需由来源匹配燃料密度 kg/L、NCV MJ/kg：kg CO2/L = kg/L * MJ/kg * (TJ/10^6 MJ) * kg CO2/TJ。
- 千万不要把 69,300 kg/TJ 当 69.3 kg/L；不要把电动车历史 0.23 kWh/km 当汽油车油耗。

## 3. 无人机与电网

- kWh_wall = mission discharge kWh / verified charge efficiency + verified charger auxiliary kWh; battery usable kWh and reserve are technical constraints, **not** estimated from max range alone。
- kg CO2 of charging = sum_{country=MY,SG} kWh_wall,country * published kg CO2/kWh of compatible gas scope and year。若只有 kg CO2e/kWh 则独立输出 CO2e 电力账，不直接加 CO2 汽油尾气。
- 飞行耗电包含载荷去程、空载返航/会合、起降/悬停、风场、等待/充电损耗；必须存来源和参数区间。

## 4. 共同碳账本与最低碳可行解

主比较仅在排放因子气体口径一致时执行：

E_operational,m = E_petrol_TTW_CO2,m + E_charging_CO2,m

优化目标为在冻结样本下最小化 E_operational,m，约束：
- completed_m ≥ completed_M0 或明确预注册的服务容忍度；
- on_time_m ≥ on_time_M0 或预注册时效容忍度；
- cost_m/cost_M0 ≤ 预注册的上限；
- UAV 任务不能违反模型内明确排除的空域、天气、任务能耗与载荷情景；
- 不存在可行模式则写 INFEASIBLE，而非篡改阈值再宣称低碳。

## 5. 独立性及置信区间

- Stage6 的 29,842 个订单来自30个seed与5个日期；默认独立重采样层以 seed 为单位，避免将任务行或89,526条 mode记录当独立研究单元。
- 采用配对 seed 差和整群重采样；5个固定日不能推断整个五月至九月的季节性均值。
- 另做有来源的联合参数敏感性，不把种子 bootstrap 当模型结构不确定性。

## 6. 空域与跨境

空间上可达 ≠ 获准无人机运营。无许可站点可在明确标记 CONDITIONAL_SCREEN 的研究情景里分析“若满足许可”的假设，不得发布实地可部署声明。旧128条OD全为非跨境参考；新增跨境 OD 需独立证据、关口排队和合法性分层。
