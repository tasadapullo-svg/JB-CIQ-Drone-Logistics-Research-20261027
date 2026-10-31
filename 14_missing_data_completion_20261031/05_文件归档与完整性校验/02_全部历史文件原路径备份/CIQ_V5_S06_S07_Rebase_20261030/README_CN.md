# CIQ V5 → S06/S07 正式实验输入迁移（2026-10-30）

## 唯一固定空间依据

`inputs/CIQ_ABC_QGIS322_V5_ONE_WMP228_68_NODES_FULL_PROJECT(1).zip`：**唯一空间来源**。程序先验证原 ZIP 与 `CIQ_ABC_V5_ACTIVE.gpkg` 的 SHA-256，再从活动 GeoPackage 生成新版衍生表。**不编辑 V5 的点、线或 QGIS 原件**。归档 `archive/ALL_68_STUDY_NODES_LONG_LAT.csv` 存在 A_N10/G_CIQ 成员差异，不可用于模型。

- 68 节点（A29、B10、C29），116 条 UAV 几何候选，5 条地面交接直线，额外 4 条地面 HOLD 线。
- A09、A10 均属于 **C** 区，以 `zone` 字段为准。
- 旧 19 点仅生成坐标对照，不根据相同 `node_id` 强制重用订单；旧 37 条 OD 异常仍为 HOLD。
- WMP228 是 V5 历史参考图层，不代表当日禁飞或合法许可认定。

## 已运行并实际生成

- `outputs/S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv`
- `outputs/S06_V5_ALL_125_LINKS_BY_FUNCTION.csv`（包含隔离用途）
- `outputs/S06_V5_116_UAV_GEOMETRY_ONLY.csv`
- `outputs/S06_V5_5_GROUND_STRAIGHT_HANDOFF_NOT_ROADS.csv`
- `outputs/S06_V5_4_EXTRA_GROUND_HOLD.csv`
- `outputs/S07_V5_19_LEGACY_COORDINATE_CROSSWALK_NOT_AUTO_MIGRATED.csv`
- `outputs/S07_V5_37_LEGACY_OD_EXCEPTION_NO_AUTO_REPAIR.csv`
- `outputs/S07_V5_3672_HOURLY_TIMELINE.csv`
- `outputs/S07_V5_68_NODE_ERA5_COARSE_GRID_CANDIDATES.csv`（纯位置代理，无气象数值）
- `outputs/S07_V5_68_ROAD_ACCESS_PENDING.csv`（所有 68 点原样保留）
- `outputs/S07_V5_SYNTHETIC_TASKS_CONDITIONAL_DESIGN.csv`（82,620 条可复现的**条件性设计样本**，非真实订单）

## 合成订单设计的限制

30 个独立随机种子、2026 年 5–9 月 153 天、每种子每天每区 6 单，共 82,620 单。A/B/C 各 27,540 单。按人为设定的 5 单区内 + 1 单跨区结构，跨区六方向各 2,295 单；服务期限 45/90/150 分钟、包裹重量 0.5/1/2.5/4.5/5/8 kg 都是**实验设计参数，不是实测客单分布**。任务生成规则见 `qa/V5_SYNTHETIC_TASK_DESIGN_PROTOCOL.json`。涉及站点均只是假设使用其地理参考位置，**并非获批准的物流仓库、司机停靠或无人机起降点**。

- 该样本可以作为后续五种模式共同任务输入及算法烟雾测试。
- 其结果只支持条件性仿真，不可推导现实 JB 物流需求总量。根据后续的文献与需求假设校准，可另建新编号的稳健性情景；V5 地图不因此改变。
- 不混合 Stage6 原 29,842 条旧版订单；也不将 918,000 行工程重采样当作实测需求。
- 当前任务记录保留道路不可达/天气未评价等状态，尚未有任何时间、油耗、电耗、成本、排放结果。

## 实际源文件门槛

`qa/S07_V5_SOURCE_RELEASE_GATE.json` 实际检查 11 个锁定 GitHub 原件：本执行环境 11/11 缺少完整字节。**不等于 GitHub 文件不存在**。项目空间输入不缺，所缺的是大型天气数值文件、历史 A/B OSM 原件和 V5 完整 A/B/C 道路图。

以前 V3 的 69 点天气表不能继续复用；此批已按 V5 68 点重新计算历史 ERA5 两格网的**参考距离**，不视为 68 个独立气象观测点。

## 本地运行（Windows）

1. 解压 ZIP；要求 Python 3.11+ 和可访问 GitHub 的网络。
2. 双击 `RUN_WINDOWS.cmd`：重算 V5 68 节点和合成样本，按固定 GitHub SHA 恢复 11 个旧原件，提取天气 `Weather_Hourly` 原表，进行历史 A/B 图网络初检，并运行 30 项自动测试。
3. 双击 `RUN_WINDOWS_OSM_ONLY.cmd`：使用 OSMnx 2.x 在线获取覆盖 **V5 全部 A/B/C** 的有向道路图，输出路口吸附候选和图形版本 SHA；这只是初步图建模，不等于完成出入口、转向、跨境合法通行和历史路况校验。
4. 将执行后的整个目录 ZIP 上传回来复核（保留 `recovered_sources/`），不要覆盖历史 Stage 3–8。

若原始文件无法下载，报告会保持 HOLD；若下载字节与锁定 Git blob/SHA256 不一致，将直接 FAIL，绝不静默替换。

## 后续门槛和剩余阶段

**S06→V5 空间适配：已完成。S07：合成样本与时间索引完成，真实气象—有向道路—FCD 融合仍 HOLD。** S08 汽油车；S09 两款无人机能耗；S10 五模式配对调度；S11 运营减排与成本可行优化；S12 统计及 SCI 图件。共 6 个正式后续阶段（S07–S12），尚未把其中任一阶段包装为全部完成。
