# CIQ A / C / B — QGIS 3.22.4 最终整合代码包（空间审核版）

**发布日期：2026-10-29。性质：科研空间设计与几何审计，不是法定飞行许可、航路图或实际可执行无人机物流调度方案。**

## 1. 文件结构

```text
CIQ_ABC_FINAL_QGIS322/
├── data/
│   ├── CIQ_ABC_FINAL_EDITABLE.gpkg          # 所有持久化 GIS 图层，EPSG:4326
│   ├── ALL_68_STUDY_NODES_LONG_LAT.csv     # 68 个研究参考点的经纬度与角色
│   ├── V7_ALL_62_NODE_EVIDENCE.csv
│   ├── V7_ALL_111_EDGE_AUDIT.csv
│   ├── V7_PRIORITY_12_SITE_GATES.csv
│   ├── V8_PORT_6_NODE_EVIDENCE.csv
│   └── V8_PORT_10_EDGE_AUDIT.csv
├── code/
│   ├── 01_BUILD_COMPLETE_QGIS322.py         # 在 QGIS 3.22.4 Python 控制台运行
│   ├── 02_AUDIT_INPUTS_PLAIN_PYTHON.py      # 普通 Python 中可运行的纯数据验收
│   ├── 03_OFFLINE_VECTOR_PREVIEW.py         # 可选：静态几何 QA 制图，需 geopandas/matplotlib
│   └── RUN_ONE_LINE_IN_QGIS_CONSOLE.txt
├── figures/                                # 先行绘制的离线几何 QA 图片
├── qa/                                     # 计数、完整性、独立距离核验报告
└── exports/                                # QGIS 一键脚本执行后导出的布局 PNG
```

**`.qgz` 生成方式**：解压后，在装有 QGIS 3.22.4 的计算机上执行主脚本，自动生成 `CIQ_ABC_FINAL_REVIEW.qgz`。本交付环境没有 QGIS 3.22 的运行库，所以没有伪造尚未实际运行生成的 `.qgz` 文件。

## 2. 一键运行（QGIS Python 控制台，不是 Android QPython）

1. **完整解压** ZIP 至例如 `D:\CIQ_ABC_FINAL_QGIS322`，不要单独移动 `.gpkg` 或 `.py`。
2. 启动 **QGIS Desktop 3.22.4**，先保存手头其他项目。**主脚本将清空当前 QGIS 工程的已载入图层**，但不会修改交付包中的冻结 B 区原始数据。
3. 在 QGIS 菜单 `插件 → Python 控制台` 输入：

```python
p = r"D:\CIQ_ABC_FINAL_QGIS322\code\01_BUILD_COMPLETE_QGIS322.py"
exec(compile(open(p, encoding="utf-8").read(), p, "exec"), {"__file__": p})
```

4. 脚本载入全部图层、设置分类样式与标签、创建六套 QGIS 布局：总览、A/C/B 局部、CIQ–Stulang 放大，以及 A/C/B 三张完整节点名称大图；再尝试导出 `exports/01...png` 等。**打印布局和 OSM 在线瓦片需要在本机检查**。保存后的 `CIQ_ABC_FINAL_REVIEW.qgz` 可再次打开。
5. 可选：在普通 Python 环境运行 `python code/02_AUDIT_INPUTS_PLAIN_PYTHON.py`，仅需标准库，不会修改节点或线路。

新版默认在 QGIS 画布显示所有 69 点的 `编号 | 完整名称`。`06 OVERVIEW ID-ONLY LABEL LAYERS` 为总览布局使用的同源副本，默认关闭，不需要手动启用。`05 UAV REACH` 默认关闭：可自行启用 DJI 与 Wingcopter 的独立情景圈，但不能称为准许飞行的空域。

## 3. 现阶段的准确数据含义

| 研究对象 | 数据量 | 定义 |
|---|---:|---|
| A/C/B V7 保留参考节点 | 62 | A=23、C=29、B=10；B 原始坐标保持不变；A11 不恢复 |
| V8 近 CIQ 港区补充点 | 6 | 1 个停车场候选地块搜索点，5 个地面/需求参考点 |
| 额外 CIQ 关口点 `G_CIQ` | 1 | 仅代表地面通关口岸，不计入 UAV 站点 |
| V7 原几何连接 | 111 | UAV 研究候选几何线，并非航空批准航路 |
| V8 新候选 UAV 连接 | 5 | A_P01 连到 A03/A04/A07/A_C01/A_N01；所有端点仍需验证 |
| V8 地面交接线 | 5 | **直线示意**，非实际 OSM 道路最短路径 |
| V7 港区额外地面示意 | 4 | 单独保留，默认关闭，避免重复展示 |
| 模型航程圆 | 8 | 4 个优先调查位置 × DJI 5.6 km / Wing 32.2 km 的往返几何情景 |

**距离模型**：DJI FlyCart 30 与 Wingcopter 198 Cargo 仅使用前期论文假设的 5.6 km / 32.2 km 单程几何半径，来自各自厂商参考最大航程 × 0.7 ÷ 2。不同机型最大航程测试载荷与工况不匹配，且此模型**不是**实际任务级有效航程或电耗模型。

逐段初筛：在 **116 条 UAV 候选直线**中，DJI 示例 99 条范围内、17 条超出；Wingcopter 示例 116 条范围内。这不是可执行任务覆盖率。

## 4. 禁飞区与 GIS 监管核查

- `WMP228_history_two_discs`：CAAM 2025 / CAAS 2026 **历史完整 2 NM 圆形参考情景**。不能把两圆画成两处独立法定禁飞区，也不能视为 2026-10-29 生效法定空域边界；需核验现行 CAAM AIRAC ENR5.1、海岸线条款、AIP 附加修订和相关 NOTAM。
- `Senai_5NM_aerodrome_ADVISORY`：仅用于进一步识别机场邻近风险，不构成法定飞行许可结论，默认关闭。
- `AC_study_corridors_APPROX` 与 `B_geometric_display_envelope`：仅是科研显示包络，不是来自用户手绘区的精确数字化边界或官方行政界。
- `UAV_4_SITE_SEARCH_REACH_2_MODELS`：模型距离示意圈；未排除障碍、人口暴露或进出航道，也未考虑交接、悬停和补能损耗。

**所有节点均缺少足够的起降资格证据，所有 UAV 路线均缺少正式航空批准。** 保留节点是为了空间规划与未来情景模拟，不等于建站合规。

## 5. 实地和监管验收缺口（不得在地图中隐去）

1. 具体工业/停车场 **地籍宗地边界**及合法场地权属、进入许可、业主同意和实际车辆出入口；其中 A01 Swift Tebrau II 有 PLO137/138 资料线索，但没有实测起降坪坐标。
2. 每条航线的真实 3D 净空、高压线路、树木、建筑物、人口密度、地面风险和应急着陆场调查。
3. 码头和王宫附近的安保及通行约束；`A_P01` 仅为 OSM 现有停车场参考位置；`T_STULANG` 继续作为地面交接终点。
4. 两款 UAV 在同等载荷、风雨、储备电量、悬停、起降与补能条件下的任务级 Wh/km 和可执行飞行时长。
5. CAAM / CAAS 适用空域、运营类别、SUP/BVLOS 等批准及跨境许可（如涉及新加坡）。
6. 使用完整 OSM 可路由道路网络、车辆门口节点和已经核验方向匹配的 FCD 时变速度，才可以替换地面直线为真实交通路径。

本包**不重新生成订单，不重跑配送时间、成本、净碳排放实验，也不改变冻结 B 区原数据**。你在 QGIS 完成选址审批和空间审核后，才能确定哪些节点进入下一版真实约束实验。

## 6. 数据来源可追溯

- 工程底座：V7 `ABC_V7_PRESERVE_ALL_REVIEW.gpkg` + V8 `ABC_V8_ALL_V7_UNCHANGED_PLUS_CIQ_PORT.gpkg`；本交付以 **V8 合并文件作为唯一拷贝来源**，另外新增 1 个地面 CIQ 参考点、1 个 B 研究区几何显示包络和 8 个模型航程圆。
- 所有原始节点来源 URL 和证据等级均保留在 GeoPackage 属性表和 `data/*EVIDENCE.csv`。其中未验证的地理参考坐标不构成场地测绘坐标。
- 项目公开资料仓库：https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027


---

## 7. 2026-10-30 全节点名称修复版

**原问题已定位**：旧 `01_BUILD_COMPLETE_QGIS322.py` 的标注表达式仅对 `RETAIN_PRIORITY_SITE_SEARCH`、`B00`、`B07` 和 `T_STULANG` 返回 ID，其他点返回 `NULL`；同时 `06 OPTIONAL ALL NODE LABELS` 组默认关闭，且 QGIS 默认会自动避让隐藏标签。因此旧地图只有部分节点名称。

**修复范围**（没有修改原始坐标、属性、道路/无人机几何线或禁飞情景图层）：

- 主图层默认对 **V7 62 点 + V8 港区 6 点 + CIQ 地面网关 1 点** 逐点显示 `编号 | 完整名称`；`QgsPalLayerSettings.displayAll=True` 防止标签因碰撞而被自动省略。
- 总览布局 `01` 改为 **全部 69 点编号**（短标签），避免把 69 个长名称硬塞进单张总体图。
- 布局 `02` 的 A/C/B 三面板、布局 `03` 的港区放大图、以及新增的 `04` A 区、`05` C 区、`06` B 区 **单区 A3 大图**，采用完整名称标签；每张单区大图右侧另附 **节点编号—完整名称索引**，用于逐点核查。
- QGIS 图层组 `06 OVERVIEW ID-ONLY LABEL LAYERS` 为总览布局专用的同源副本，默认关闭。无需启用它才能看到全名称：默认画布中的 `01 NODES` 已显示所有 69 点名称。
- `qa/QA_ALL_69_NODE_LABELS.csv` 是可直接检索的 **69 条标签核对表**，其中 `overview_label` 和 `regional_and_canvas_label` 是实际采用的两种标签文本。

**重要的地图可读性限制**：`displayAll=True` 能防止 QGIS 因碰撞丢弃标签，但不能保证在任意缩放级别下完全没有文字重叠、被地图边框截断或被底图文字干扰。总览只显示 ID；请使用 `04–06` 的单区大图核对完整名称，必要时在 QGIS 中进一步放大。右侧索引保证完整名称可查，不代表每个地图标签都已完成视觉验收。

**新版执行方法**：与第 2 节相同，在 QGIS 3.22.4 控制台运行 `code/01_BUILD_COMPLETE_QGIS322.py`，生成 `CIQ_ABC_FINAL_REVIEW.qgz` 和 `exports/01–06*.png`。执行前请保存并关闭正在编辑的其他 QGIS 工程：脚本仍然会清空当前打开的项目。

**独立验收**：普通 Python 可运行 `python code/04_AUDIT_ALL_69_LABELS.py`，校验 69 个唯一编号、69 个非空完整名称、与原始 68 点 CSV 的坐标及名称一致性，并写出 QA CSV/JSON。此检查不能替代用户在 QGIS 3.22.4 中打开布局后的实际视觉检查。

## 8. 本包新增的离线验收图

`figures/LABEL_QA_A_ALL_NAMES_INDEX_OFFLINE.png`、`LABEL_QA_C_ALL_NAMES_INDEX_OFFLINE.png`、`LABEL_QA_B_ALL_NAMES_INDEX_OFFLINE.png` 分别展示 A、C、B 区每个节点的 **ID 地图位置** 与 **完整名称索引**。这些图由 `code/05_MAKE_LABEL_QA_PREVIEWS.py` 使用原始坐标制作，不使用在线 OSM 底图，不是 QGIS 最终导出或航线安全验收图。QGIS 主脚本仍是正式出图入口。
