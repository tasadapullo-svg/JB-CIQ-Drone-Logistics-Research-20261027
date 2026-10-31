# Stage 05 — 统一任务协议、燃油汽车基线与双无人机参数冻结（正式源级审计）

- 审计日期：2026-10-30（Asia/Kuala_Lumpur）
- 版本：S05-AUDIT-v1
- 总体裁定：**METHOD/PROTOCOL FROZEN；NUMERICAL PARAMETER HOLD；MAIN EXPERIMENT DENIED**。
- 历史基线：`4569817b8145efe2ae06f4b21addc1986f971c12`（GitHub main 2026-10-28）。本轮未重算气象、道路、运营排放和 M0/M1/M2 仿真。
- 交付：42 项参数登记（27 项仍阻断）、18 项释放门槛、13 条权威/历史证据登记、模型迁移判断、10 个合成自动测试（全部通过）、严格运行门槛（0/10 通过）。

## 1. 三模式的统一实验对象

**功能单位**：一个合成货运任务在冻结的期限内送达，固定 `task_id`、随机种子、起终点与国家、释放时刻、截止时刻、重量、任务群体 ID。M0、M1、M2 必须在同一个不可变任务集合上报告服务率、准时率、门到门时间、运营成本、运营排放；失败、缺失、无道路/气象/许可的任务均保留独立状态，不能仅以成功订单为分母。

**M0**：燃油地面车（汽油小客车与柴油厢式货车作为不同基准情景）；包含回程/空驶、装卸和可适用的 CIQ 等待。**M1**：地面接驳/集货—固定站点转运—UAV 带载与返回—充电/排队/回退。**M2**：货车与 UAV 同步发射、会合回收，车辆公里数与共享干线严格避免重复计量。容量、仓储/转运和服务等级必须同口径。

历史 Stage 2 的 918,000 条有放回重采样、Stage 6 的 29,842 条合成订单不能相加。历史 128 条 OD 的 `cross_border_route` 全部为 `False`，不得用旧结果推断真实跨境节时。

## 2. 参数来源审计

| 参数 | 来源值 | 可采用范围 |
|---|---:|---|
| DJI FlyCart 30 双电池额定载荷 | 30 kg | 厂商技术筛查 |
| DJI FlyCart 30 满载/空载标称距离 | 16/28 km | 受无风和测试工况限制，不是实际每次往返航程 |
| DJI DB2000 名义电池能量 | 1.9844 kWh × 2 | 名义能量；不等于能耗或可用 SOC |
| DJI FlyCart 30 厂商抗风 | 12 m/s | 特定工况，不等于雨量门槛或操作许可 |
| Wingcopter 198 Cargo 载荷 | 4.7 kg | Cargo 型号技术筛查 |
| Wingcopter 198 Cargo 标称最大距离 | up to 92 km | 载荷/气象/安全储备条件未明确 |
| Wingcopter 198 Cargo 抗风 | up to 18 m/s | 有条件上限，非起飞许可 |
| IPCC 汽油 TTW CO₂ 因子 | 69,300 kg CO₂/TJ | CO₂ 燃烧 Tier 1；实际密度和净热值待验证 |
| IPCC 柴油 TTW CO₂ 因子 | 74,100 kg CO₂/TJ | 同上 |
| 马来西亚半岛 2024 GEF（暂定） | 0.740 kg CO₂e/kWh | 历史电网参考，非 2026 现测 |
| 新加坡 2024 GEF | 0.402 kg CO₂/kWh | CO₂-only，不能视同 kg CO₂e/kWh |

厂家最大航程/电池容量**不能推断任务能耗或每订单 CO₂**。因此两款 UAV 的带载/空载/起降/悬停/电池储备/墙端能耗模型尚未冻结；本次不报告飞行 kgCO₂/单或净减排。

## 3. 核算方法冻结

汽柴油燃烧碳排放的量纲一致公式：

`TTW_CO2_kg = distance_km × fuel_L_per_100km/100 × density_kg_per_L × NCV_MJ_per_kg / 1_000_000 × EF_kgCO2_per_TJ`，另外记录与基础油耗**不重叠**的怠速耗油。M0 不是旧 Stage 6 的电动面包车 `0.23 kWh/km`，旧 Generic UAV 功率参数不得迁移。燃油上游（WTT）、车辆生产和电池生产排放不纳入主运营结果，若研究全生命周期，必须另建完整一致的 WTW/LCA 帐。

电池充电应使用发生地电网因子，跨境应单列 MY/SG 墙端 kWh。马来西亚 0.740 是 CO₂e 而新加坡 0.402 是 CO₂：必须先同气体、同年度/方法口径，再给系统 CO₂e 汇总。禁止用一个国家的电网因子套用另一个国家。

## 4. 监管边界与释放条件

候选 QGIS 线段不是获准航线。涉及新加坡境内跨境无人机飞行，需要 CAAS 跨境许可，另外可能涉及运营者和活动许可；马来西亚 CAAM 也需依据作业类型审查。没有批准时，只能将 UAV 跨境情景标为 `NOT_AUTHORIZED` 或明确的**监管允许反事实假设情景**，不可称为真实运营。

Stage 05 形成了 18 项审计门槛和 10 个只读硬门槛。当前 0/10 通过，未经真实 QGIS 三分区原件、完整新道路与气象映射、燃油油耗及机型任务能耗证据、数据哈希及独立 smoke test，不允许正式数值试验。

## 5. 来源清单

完整权威 URL、检查日期、历史 Git blob SHA、参数级来源及禁止迁移原因见：`records/source_registry.csv`、`records/stage05_parameter_registry.csv`、`records/legacy_to_stage05_decision.csv`、`records/stage05_unified_task_protocol.json`。

程序：`python scripts/stage05_release_check.py`（仅检查证据，并写入 `results/stage05_release_result.json`；不会运行任何仿真）。
