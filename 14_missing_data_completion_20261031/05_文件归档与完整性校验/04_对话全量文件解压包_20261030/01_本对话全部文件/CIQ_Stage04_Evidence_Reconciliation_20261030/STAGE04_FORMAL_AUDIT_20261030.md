# CIQ Stage 04 — 历史道路与气象结构复核（正式审计报告）

**审计日：** 2026-10-30（Asia/Kuala_Lumpur）  
**审计编号：** CIQ-S04-ROAD-WEATHER-20261030  
**历史基线：** GitHub `main` commit `4569817b8145efe2ae06f4b21addc1986f971c12`  
**总体裁定：** `HOLD_RECALC_BLOCKED`。此轮已重数历史道路诊断记录，未开展新版 M0/M1/M2 实验。

## 1. 核查对象和证据等级

1. `outputs/stage2_20261027/od_connectivity_diagnostics.csv`，Git blob `c144da04db6fed8df228accb776b07d5493972d9`：GitHub 连接分段取回 **128** 条诊断记录并重新分类统计。
2. `outputs/stage2_20261027/od_route_repair_log.csv`，Git blob `6f1cee1b994959e327eaeecf1708fb7efada1b0d`：取回 **37** 条未落实修复记录，逐 ID 建立登记。
3. `outputs/stage2_20261027/stage2_gates.json`，Git blob `63a6fb3a1ea21b85306e0a2b1a06869810515140`：读取 10 项历史释放门槛。
4. `data/weather_2026/processed/final_verification_summary.json`，Git blob `85845782a5f5cdbb4fa49737bb6e63aaa6dc06c7`：复核历史预先计算的月度 QC 元数据与网格位置；**没有逐小时气象独立重算**。

Git blob 是 Git 对象 SHA-1，不是文件字节 SHA-256。全库源文件 SHA256 检查仍需本地完整原件。

## 2. 道路连通与修复复核结果

| 指标 | Causeway A | Second Link B | 总计 |
|---|---:|---:|---:|
| 原始有向 OD | 56 | 72 | 128 |
| 模型路径存在（原始） | 49 | 42 | 91 |
| 原始异常/需复核 | 7 | 30 | 37 |
| 找到替代诊断路径 | 7 | 30 | 37 |
| **正式修复应用** | **0** | **0** | **0** |

A 区 7 条属于 `SNAP_FAILURE`，涉及方向不兼容的近邻道路/尽端道路节点。B 区 30 条属于 `DATA_GAP`，主要指 B02/B07 类参考锚点与 OSM 道路边距离超过 100 米，真实接入尚未确立。所有 37 条的剩余异常代码都是 `ACCESS_DIRECTION_TURN_BOUNDARY_UNVERIFIED`。

**严禁将 37 个 `candidate_route_found=True` 当成 37 条已恢复 OD。** 修复日志的 `repair_applied` 37 条全部为 `False`。

## 3. 旧跨境研究范围的重大局限

128 条旧 OD 的 `cross_border_route` 全部为 `False`。Stage 2 的 `G4_CIQ_SEPARATION=PASS` 仅说明旧境内 OD 未混写 CIQ 等待；**并不能证明跨境通关模型已经校准**。如果新版论文需要横跨马来西亚—新加坡的配送任务，必须另行定义合法研究边界、是否跨境、口岸等待、监管和车辆运营条件。若新版只比较口岸两侧的本地配送，也须明确两侧范围与不跨境的解释限制。

## 4. 气象格点重复性和源级 QC

| 月份 | 历史 4 点小时主表 | ERA5 独立返回格点数 | NASA 返回格点数 | ERA5–NASA 降雨相关 | NEA 记录状态 |
|---|---:|---:|---:|---:|---|
| 2026-05 | 2,976 | 2 | 4 | 0.0277 | PARTIAL |
| 2026-06 | 2,880 | 2 | 4 | 0.0319 | NOT_REQUESTED |
| 2026-07 | 2,976 | 2 | 4 | 0.0256 | NOT_REQUESTED |
| 2026-08 | 2,976 | 2 | 4 | 0.0875 | NOT_REQUESTED |
| 2026-09 | 2,880 | 2 | 4 | 0.1324 | NOT_REQUESTED |

所有月份，ERA5 的 CW_MY、CW_SG 和 SL_SG 返回坐标均为 `(latitude=1.5, longitude=103.75)`，SL_MY 返回 `(1.5, 103.5)`。**四个参考位置并非四个独立的 ERA5 格点。** 但这也不能简单断言四点气象值绝对相同；须根据原始 API 返回序列和插值设置核验，不能仅凭元数据判定。

NASA POWER 官方小时 API 说明降雨单位为 `mm/hour`；ECMWF 官方原生 ERA5 降雨累计量采用 `m` 并以时段结束时间标记。不过本项目历史数据经 Open-Meteo 处理，不能不检查**实际 API 响应单位**就自动乘以 1000。须先比对请求参数、时区、积算窗口、降雨定义、网格和 0 雨小时比例，再进行降雨一致性检验。原历史雨量相关系数虽很低，但不能仅凭它推断某个数据源错误。

外部定义参考：
- [NASA POWER — Hourly API](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/)
- [ECMWF — Accumulated precipitation conversions](https://confluence.ecmwf.int/pages/viewpage.action?pageId=272324919)

## 5. Stage 3–8 与新版主实验的隔离裁定

| 历史材料 | 可复用内容 | 不得直接复用的内容 |
|---|---|---|
| Stage 2 道路诊断 | 128 OD 分类、37 异常定位与审计代码 | 将 37 候选默认为已修复，直接跨境外推 |
| Stage 3–6 订单/调度 | 配对比较思想、历史种子与样本协议、M0/M1/M2 定义 | 旧节点映射、旧实绩数值、旧 generic UAV 参数 |
| Stage 6 气象模型 | 风矢量分解的建模框架 | 释放小时替代实际起飞小时、单格点多点独立性假设 |
| Stage 6 排放 | 操作活动拆账结构、运营与资产分摊分开 | 0.23 kWh/km 电动车假设当燃油车排放、470 W 泛机型功率 |
| Stage 7–8 | 统计复现思想、敏感性与飞行筛查证据 | 旧候选直线当获准航路、低信息量航程上界当任务能耗 |

## 6. 自动执行验证

新增 `scripts/stage04_evidence_gate.py` 可使用完整本地源文件检查 OD/修复日志的唯一性、异常—修复对账、是否有显式审批、跨境 OD 是否存在、NEA 元数据缺口和 ERA5 格点重复性。工具不修改源文件。七项**合成单元测试**已实际执行通过。

当前工作区运行 `output/actual_workspace_audit.json` 返回 `HOLD_RECALC_BLOCKED`（退出码 2），因为没有完整历史 CSV/天气 QC 原件作为本地输入，也没有 QGIS 三分区冻结文件；这**不是**对真实数据执行通过。

## 7. Stage 04 裁定与可推进的动作

**当前通过：** 历史 OD 分类、修复日志事实、格点数与月度 QC 来源标记的可追溯结构复核。

**尚未通过：** 原始逐小时气象复算、完整道路拓扑和国界/转向核验、新版 A/B/C 空间输入冻结、跨境 OD 建立、独立交通校准、燃油车辆及两款无人机可审查能耗模型。

**最终释放结论：** Stage 04 `PARTIAL/HOLD`；历史 37 条未修复异常不纳入新版可达道路集合；现有 ERA5 只能被视为两格点的气象参考；原始历史主实验数值只保留审计/对照用途。**不批准新版天气、道路、运营碳排放及配送绩效重算。**
