# V5 S09 两款无人机全部九项任务：正式验收报告

**核验日：**2026-10-30  
**研究范围：**JB-CIQ 无人机物流 V5 固定网络；DJI FlyCart 30（双电池）与 Wingcopter 198 Cargo（冻结的 4.7 kg 保守研究配置）。  
**正式裁定：`S09_FULL_AUDIT_EXECUTED / SCI_FINAL_RELEASE=HOLD`。**

## 1. 研究基准与输入保护

冻结源字节核验 **4/4 SHA-256 匹配**：V5 原始 ZIP、68 节点 CSV、116 条 UAV 候选几何及 82,620 条任务 CSV。每个种子-日期单独一个场景，共 4,590 场景，三分区各 27,540 单；没有删除或新生成订单。

V5 候选图不是经批准的航道，直线几何距离不是真实可飞航迹。5 条地面交接线和 4 条 ground-only HOLD 线没有进入 UAV 候选边。

## 2. 本轮真正运行的计算

- 原始任务 **82,620**；两款机型逐任务静态筛查 **165,240** 行。
- 记录方向上的直接候选几何 **11,060** 单；只有逆向候选 **17,417** 单；无直接候选 **54,143** 单。
- DJI 双电池模式的重量初筛 **82,620 PASS**。
- Wingcopter Cargo 冻结 4.7 kg 阈值：**55,080** 单通过重量，**27,540** 单超过载重。超重任务必须保留在共同服务分母，转向地面/混合模式，不能直接视为订单失败。
- 同时满足“有同方向直接候选几何+仅载重初筛”的任务：DJI **11,060**；Wingcopter **7,377**。
- 本轮新运行明确标记为 **DESIGN ONLY** 的 `3×3` 功率假设与顺/逆风压力测试：合计 **165,933** 行。均为“载重去程+空载几何返程”*假设*，不是已完成的 M1/M2 航次或实测电量。
- 68 节点与历史 ERA5 参考粗网格距离复算：**31/68** 距离超过本研究 10 km 预警阈值；涉及 **55,080** 条订单起点。这只是空间代表性预警，不是无人机天气不可飞证据。
- 完成 37 项单元及集成测试（含 UTC 跨时段、气象缺口、空气航段连续性、充电来源和防重复核碳），全部通过。

## 3. 两款机型技术资料：证据分级与型号差异

**DJI FlyCart 30（双电池）**：DJI 官方技术页给出 30 kg 载重，静风理想情况下 30kg 载重 16 km、空载 28 km，额定双电池能量约 3.9688 kWh；12 m/s 最大抗风测试参数。这不是 30kg 在 16km 实际配送任务的耗电轨迹，也不能把理论最大航程当作可安全运营航程。  
来源：https://www.dji.com/flycart-30/specs

**Wingcopter 198 的重大配置差异**：可查的 **Wingcopter 198 Delivery Variant v04-2021** 技术表写明 **5 kg 最大载重、两块 814 Wh 电池、固定翼默认巡航速度 28 m/s**，并有静风理想场景估算航程。当前研究冻结的对象是 **Wingcopter 198 Cargo 4.7 kg 保守阈值**，两者**不能认定为同一硬件配置**；本轮 1.628 kWh 只用作相关 198 机型的技术假设参考，**没有把它确认为 Cargo 量产机电池**。以前使用的“92 km”也不应与 2021 Delivery Variant 的不同载荷航程直接拼接。  
来源：https://www.sisirl.com/wp-content/uploads/2018/01/Specsheet_Wingcopter-198.pdf

**参数风险**：没有两款研究配置的相同测试条件（载重、风、气压/温度、航程、飞行阶段、充电）的完整任务功率曲线。程序的 3 级功率与 3 种合成风况是透明的**敏感性假设**，不得写成 OEM 测试数据。

## 4. 九项工作包独立验收

请见 `outputs/S09_9_WORKPACKAGES_FINAL_ACCEPTANCE_MATRIX.csv`。静态任务筛查、技术计算器、充电双重计账控制、M1/M2 数据接口及敏感性程序验收已通过。**未通过的实证门槛：**

1. **S09-01（Wingcopter Cargo 配置）**：需要核验实际选定 `Cargo 4.7kg` 配置与有效电池规格，或在论文明确降级为 198 Delivery Variant 的条件性代理。
2. **S09-03（真实天气）**：2026 年 5–9 月逐小时实数值文件未在此运行环境中取得并复算；B/C 粗网格空间外推必须做误差及敏感性评估；无 2026 年真实风雨/阵风窗口输出。
3. **S09-04（型号能耗）**：没有足够证据把假设功率系数解释为实测机器性能，也没有可实证量化的起飞、转场、悬停、降落、返航及载重依赖模型。
4. **S09-05（正式排放）**：真实补电效率、2026 年适用区域/边界的电力排放因子及真实任务耗电尚未一致核验。
5. **S09-06（实际任务）**：没有 S10 的实际起飞时刻、车辆会合坐标与经验证飞行航迹；不能直接把订单释放时刻作为无人机飞行时刻。
6. **空域/站点证据**：V5 线段仅为地理候选，不能声明获得 CAAM/CAAS 飞行许可或真实站点起降可行性。

这些缺口对于“实际运营已验证”是硬阻断；本论文仍可采用**明确标注、参数来源充分论证的条件性仿真**，但必须在真实历史天气和合理能源参数下完成主情景以及敏感性核查才可作正式 SCI 结果。

## 5. 碳边界与服务定义

- `battery_kWh` 为 UAV 实际电池需要补充的任务电能，须计入往返、阶段变化和备用电量要求；储备是**容量约束而非实际消耗**，不可直接加为排放电量。
- `grid_kWh = battery_kWh/η_charge + charging_auxiliary_kWh`，仅限经验证电网充电情景。现有 3 级效率是显式**假设值**。
- 若 M2 由车辆发动机提供充电，则耗能归入汽油/发电机账本，不能同时套用电网因子造成双重计账。
- 不适合 UAV 的订单仍在共同任务分母，由 M0/M1/M2 的车辆继续处理；不能把 UAV 直接候选数作为整体完成订单数。
- `3×3` 压力情景采用恒定正/逆风合成值；气象数据未验证不能报告“真实小时可飞率”“实际电耗”“实际减排率”。

## 6. 交付文件与可复现执行

- `inputs/`：不可修改的 V5 参考包、冻结订单、候选边、历史粗网格、原 S09 配置和新版本来源/假设登记。
- `code/s09_full_validation.py`：全任务载重/定向候选/条件性功率与返程能耗。
- `code/s09_m1_m2_event_contract.py`：严防静态释放时刻冒充实际起飞事件；检查 M1/M2 航段连续性、小时天气覆盖及来源门槛。
- `code/s09_operational_energy_accounting.py`：电网补电、发动机供电、运营 CO₂e 防重复计账。
- `outputs/S09_82620_TASKS_X_2_AIRCRAFT_STATIC_AND_CONDITIONAL.csv.gz`：165,240 行完整任务-机型审计表，**实际 kWh 与 CO₂e 均保持空值**。
- `outputs/S09_DIRECT_GEOMETRY_POWER_WIND_3X3_SENSITIVITY_DESIGN_ONLY.csv.gz`：165,933 行假设压力测试。
- `outputs/S09_BY_AIRCRAFT_SUMMARY.csv`：总体比较。
- `outputs/S09_3X3_SENSITIVITY_SUMMARY_DESIGN_ONLY.csv`：场景统计，禁止当作实证结果。
- `outputs/S09_V5_68_NODE_WEATHER_SPATIAL_REPRESENTATIVENESS.csv`：V5 网格距离复算。
- `outputs/S09_9_WORKPACKAGES_FINAL_ACCEPTANCE_MATRIX.csv`：九项完整验收结论。
- `outputs/S09_M1_M2_FORMAL_MISSION_INTERFACE.json`：S10 对接合同。
- `qa/S09_FULL_37_TEST_LOG.txt`、`qa/S09_FINAL_EVIDENCE_STATUS.json`、`outputs/S09_QA_SCIENTIFIC_RELEASE_GATE.json`：复测与拒绝放行证据。

可执行：`python code/s09_full_validation.py --inputs inputs --outputs outputs`，然后 `python code/s09_build_quality_tables.py`，最后 `python -m unittest discover -s tests -p 'test_*.py' -v`。

## 7. 最终科学裁决

**工程、方法与条件性压力测试：PASS。**  
**S09 真实天气、双机型任务功率标定、正式 M1/M2 实际任务电耗与排放：HOLD。**  
**S09 SCI FINAL PASS：NOT GRANTED。**

不得将当前情景的电耗/飞行分钟写为“实际部署/实测碳减排”；本包没有重新设计 V5、没有重新生成 82,620 条冻结任务、没有越级运行 S10/S11。
