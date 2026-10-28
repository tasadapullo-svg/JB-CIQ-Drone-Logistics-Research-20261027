# Stage 8 F0–F1 第三轮：WMP228 官方坐标冲突、海岸线近似裁切、A 区探索性重新选址与两机型能耗证据升级

**日期：2026-10-28；性质：实际复算 + 官方来源交叉审计；结论等级：F0、F1 仍为部分完成。**

## 1. 最重要的审计修正

过去的“9/9 个 A 区参考点落入 WMP228 风险包络、28/28 条直线连接受影响”只对应 **2025-12-02 CAAM eAIP ENR 5.1 报告的中心经度 103°44′33″E**。进一步检索到另一组官方资料：**马来西亚 CAAM 早期 ENR 5.1 PDF 和新加坡 CAAS 2026 AIP ENR 5.1** 采用 **103°43′34″E**。二者同为 01°28′45″N、2 海里半径，地面至 5,000 英尺 ALT，差异约 1,823.8 米。

**目前未取得 2026-10-28 当日适用的马来西亚完整 ENR 5.1 正式文本及关联修订/NOTAM 的可审计快照，故不擅自判定某个坐标为当前唯一有效坐标。** CAAM eAIP 目录显示 2026-10-29 下一 AIRAC 即将生效；不能把未来修订误用于 10 月 28 日。

资料出处：

- 2025-12-02 Malaysia CAAM eAIP ENR 5.1：https://aip.caam.gov.my/aip/eAIP/2025-12-02/html/eAIP/WM-ENR-5.1-en-MS.html
- CAAM 较早版本 ENR 5.1 PDF：https://aip.caam.gov.my/aip%20pdf/ENR/ENR%205/ENR%205.1/Prohibited%2C%20Restricted%20And%20Dangerous%20Areas.pdf
- CAAS 2026-01-22 AIP ENR 5.1：https://aim-sg.caas.gov.sg/aim-content/uploads/aip/22-JAN-2026/AIP-2/2026-01-22-000000/html/eAIP/SG-ENR-5.1-en-GB.html
- Malaysia CAAM eAIP 发行目录：https://aip.caam.gov.my/aip/eAIP/history-en-MS.html
- CAAM AIS 与 NOTAM 来源说明：https://www.caam.gov.my/public/ais/

## 2. 本轮 A/B 空间复算结果

输入继续固定 Stage 6 的 **19 个地理参考点**（A 9 / B 10）与原 **76 条候选站—目的地直线连接**（A 28 / B 48），无新增真实订单/场地/获批航段。WGS84 坐标变换为 EPSG:32648，并以 2×1852 m 的圆形包络与点、直线段相交，两个官方中心分别计算。

| 指标 | CAAM eAIP 2025: 103°44′33″E | CAAM 早期/CAAS 2026: 103°43′34″E |
|---|---:|---:|
| A 区落入完整圆包络的参考点 | **9/9** | **2/9** |
| A 区与圆包络相交的候选直线 | **28/28** | **13/28** |
| A 区采用 GSHHS 中分辨率近似陆地裁剪后点暴露 | **6/9** | **1/9** |
| A 区采用 GSHHS 中分辨率近似陆地裁剪后直线暴露 | **27/28** | **13/28** |
| B 区全部 10 地点 / 48 连接 | **0/10、0/48** | **0/10、0/48** |

**7 个 A 区点、15 条 A 区直线连接的风险标签取决于采用哪组官方坐标。** 采用两个圆的并集作审慎风险剔除，保守地保留原 A 网络的 0 个不相交直线连接，但它不是正式禁止空域法定矢量边界，也不能证明整个 A 区无法建设无人机系统。B 区避开 *此特定 WMP228 包络* 不代表通过其他空域、城市障碍和场地审核。

**海岸线近似裁剪的限制**：采用运行环境随 Basemap 提供的 GSHHS intermediate resolution 近岸面状代理，非 CAAM 发布的法律边界，也不是最新高精度航测海岸线。原始 A 区若干岸边参考点被该地理数据判为海面，足以表明其定位不能用于地籍/起降坪批准。因此应优先将 **完整圆包络的双情景复算**作为主审计量；陆地裁剪只作敏感性材料，不作法律结论。

## 3. A 区替代位置搜索——本轮产生 41 个探索性网格中心，不是站点

在原 A 区参考地点包围框外扩 5 km 的搜索窗口内，构建约 1 km 间距网格；只保留 GSHHS 中分辨率模型近似的柔佛大陆、距离近似海岸 >600 m、距离**两组** WMP228 圆包络并集 >1,000 m 的单元中心，并按距原 A 区 9 个参考锚点的平均欧氏距离排列。结果：**41 个探索性研究网格中心**，最前 10 个示于图形和 CSV。

这是一项 **搜索空间生成实验**：没有核实格网内是否存在厂房/停车场/地面电力/地产进入权，不代表已经发现 41 个安全或合法站点。它也没有改变原冻结订单、未加入新道路路由和无人机可达性，因此**不能把 41 当作建站可行数量，更不能计算覆盖率改进**。后续必须获得土地用途、物业权限、建筑高度、人口密度和空域运营申请证据，并用独立道路网络重新求解这些搜索区域的接驳任务。

## 4. 双机型 F0 数据证据补强

### 4.1 DJI FlyCart 30（双 DB2000）

官方电池名义能量 2×1.9844 = **3.9688 kWh**；空载 28 km 和双电池 30 kg 16 km 是受控环境 *最大距离参考测试值*。3.9688/28 = **0.14174 kWh/km** 与 3.9688/16 = **0.24805 kWh/km** 都只是“电池名义总容量÷官方最大距离”的算术当量，**不是飞行日志的 Wh/km，不是上下界，也不能作为有效载荷 0.2–2.0 kg 的能耗曲线**。仍需实际任务 SOC/Wh、风、起降悬停、返航储备和充电效率。

https://www.dji.com/uk/flycart-30/specs

### 4.2 Wingcopter 198：新找到较早技术版本的电池资料

日本经济产业省公开研究报告及 2023 年同行评议论文引用 Wingcopter **2021 年技术规格版本**：**两块各 814 Wh，总名义电池 1.628 kWh**，老版本载荷 5 kg、最大标称单程 75 km，公开引用的旧版航程设置包含 20% 电池预留。该旧版资料可构造 `1.628/75≈0.02171 kWh/km` 的**名义总容量当量**，或扣除假定预留后的 `1.628×0.8/75≈0.01736 kWh/km` **名义可用能量当量**；二者均不是真实任务电耗。

**现行 Wingcopter 198 Cargo 官网**公布最大 4.7 kg、最多 92 km，但未对本次检索展示相应电池容量、任务载荷或每航段 Wh。旧版 1.628 kWh 不能无说明地接到现行 92 km 进行碳排放计算。旧版计算与现行规格必须分开保存、注明证据等级。

证据源：

- 日本 METI 2022FY 研究报告，Wingcopter 198 表 4-21：https://www.meti.go.jp/meti_lib/report/2022FY/000295.pdf （检索文本可见；本轮外部 PDF 全文下载受 403 限制，未能本地完整复核）
- 2023 *Sustainability* 15(2),1137，文献引用旧版 Wingcopter spec：https://www.mdpi.com/2071-1050/15/2/1137
- Wingcopter 官方目前在售 Cargo 网页：https://wsd.wingcopter.com/w198-cargo
- 旧版厂商技术规格 PDF（本轮在线读取受限）：https://wingcopter.com/wp-content/uploads/2022/06/Specsheet-Wingcopter-198.pdf

### 4.3 更低碳的必要条件筛查，而不是伪精确结果

沿用原 G11 假设的燃油基线（125cc 摩托 2.0L/100km、1.6L 汽油车 6.6L/100km、1.8L 汽油车 6.3L/100km），汽油直接排放系数 2.06916 kgCO₂e/L，电网 0.740 kgCO₂e/kWh，如果一次无人机决策 **确实避免 1 km 地面燃油车辆行驶**，单从燃油替代角度形成的额外电力名义预算分别仅约：

| 替代车辆 | 每真正避免 1 km 燃油行驶最多相抵的新增购电 |
|---|---:|
| 125cc 摩托 | 55.92 Wh |
| 1.6L 汽油汽车 | 184.55 Wh |
| 1.8L 汽油汽车 | 176.16 Wh |

`Wh_budget = (fuel_L_per_100km / 100) × petrol_kgCO₂e_per_L / grid_kgCO₂e_per_kWh × 1000`。**此仅为一阶临界参考值，不是无人机任务可比耗电，也不是净减排结论。** B 区柴油干线、集货接驳、地面等待、车辆怠速、充电与设施能耗均会消耗或改变整个碳预算；每架无人机可替代的地面实际里程也不是飞行直线公里数。

## 5. 审计门槛与下一轮实验指令

| Gate | 检验要求 | 结果 |
|---|---|---|
| AIP-1 | 当日实际有效 CAAM ENR5.1 WMP228 中心经度官方权威确认，并核对补充资料和 NOTAM | **BLOCKED** |
| COAST-1 | 官方或高精度海岸线/国界几何与起飞点定位、障碍与土地权限 | **BLOCKED** |
| SITE-1 | 从 41 个网格搜索单元里核实 2–5 个实体候选地块、道路接驳和场地进入权 | **BLOCKED** |
| DJI-E1 | DJI 实际轻载任务 SOC/Wh—速度—风速—悬停曲线 | **BLOCKED** |
| WING-E1 | 最新 198 Cargo 与 2021 规格的版本对应及任务 Wh / 电池资料 | **BLOCKED** |
| FEAS-1 | 已确认候选航线 + 天气 + 机型约束的可服务订单新覆盖率 | **BLOCKED** |
| F2-F4 | LC-M1 模式真实机型最低排放排名、合法可部署地图 | **不得宣称已完成** |

本轮实质完成的工作是**发现并量化决定性官方坐标冲突、近岸空间敏感性、探索性替代搜索区域，以及补到旧版 Wingcopter 的可追溯电池规格**。F0/F1 尚不具备结题条件；不能靠扩大随机种子绕过上述阻断。

## 6. 可复现文件说明

- `outputs/F1_19_sites_dual_AIP_coordinate_audit.csv`：双中心 19 点及陆地代理分类
- `outputs/F1_76_legs_dual_AIP_coordinate_audit.csv`：双中心 76 直线连接相交
- `outputs/F1_A_alternative_1km_search_cells_NOT_SITES.csv`：41 个纯研究网格中心
- `outputs/F0_two_model_versioned_energy_evidence.csv`：产品版本区分的 5 条任务能量来源
- `outputs/F1_A_discrepant_WMP228_and_candidate_research_cells.geojson`：GeoJSON 示意，非批准航路
- `outputs/F0F1_boundary_energy_reaudit_QA.json`、`outputs/independent_QA.json`：结果和独立测地线 QA
- `figures/F1_WMP228_two_conflicting_official_centers_and_search_cells.png`：直观展示两组官方圆形示意
- `code/run_boundary_and_energy.py`, `code/independent_qa.py`：可运行 Python
- `F0_F1_空域坐标冲突_机型能耗证据_空间搜索.xlsx`：六表 Excel；包括燃油车碳预算公式

**重跑依赖：** Python、pandas、numpy、shapely、pyproj、matplotlib、mpl_toolkits.basemap (GSHHS intermediate)。`python code/run_boundary_and_energy.py && python code/independent_qa.py && python code/draw_map.py`。使用项目自带 `inputs/`，无需联网；不同 Basemap 海岸线版本可能造成海岸裁剪与网格中心变动，必须报告数据版本。研究代码与工程复现不能替代法定航空批准。
