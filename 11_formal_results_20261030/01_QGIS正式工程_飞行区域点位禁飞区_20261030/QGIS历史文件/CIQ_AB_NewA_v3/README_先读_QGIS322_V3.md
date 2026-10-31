# CIQ A/B 双走廊 GIS V3 — QGIS Desktop 3.22.4 审核工程

日期：2026-10-29。**本次不更新原合成订单、交通校准、碳排放和 SCI 实验结论。**

## 1. 当前研究节点调整

- 新 A 区：**A01–A10，10 个参考/搜索点**，其中 A01/A02/A03/A09 是*场地搜索点*，并不具备正式批准的无人机起降条件；A04–A08/A10 为*需求/地面交接参考点*。
- **A11（Perling）正式退出本次研究范围**。`A09–A11` 几何候选线同步删除；新 A 区 11 条直线候选关系，不是合法飞行路线。
- 西部搜索窗口缩小为经度 103.648–103.675、纬度 1.477–1.516，仅用于 A09/A10 对照研究。A11 原参考位置为 E103.68381、N1.48061，落在新窗口外；窗口为研究用近似形状，并非法定或地籍边界。
- B 区保留冻结的 10 个参考点和 33 条*去重几何连接*，未擅自更改。研究逻辑中原有 48 条有向候选任务不能简单等同于 33 条几何线。
- CIQ (G_CIQ) 保留为地面通关物流参照，不作为 UAV 起降点。

## 2. 无人机名义覆盖区的表达

研究图层分别包含：

| 图层 | 含义 | 默认可见 |
|---|---|---|
| `reach_DJI_A_WMP_screen`、`reach_DJI_B_WMP_screen` | DJI 假定最大参考航程 16 km，名义任务比例 70%，往返半径 5.6 km，再裁剪到研究窗口并排除两套历史 WMP228 完整圆形参考范围 | 是 |
| `reach_WING_A_WMP_screen`、`reach_WING_B_WMP_screen` | Wingcopter 假定最大参考航程 92 km，名义任务比例 70%，往返半径 32.2 km，按相同窗口和几何筛查处理 | 否，可切换 |
| `reach_*_nominal` | 未扣除 WMP228 两套参考圆的原始几何可达情景（仍裁剪至研究窗口） | 否，可切换 |
| `WMP228_two_historical_discs` | CAAM 2025 / CAAS 2026 两套坐标中心+2 NM 几何参考圆 | 是 |

**这些图层均不得标成 “可合法飞行区域 / Approved Flight Zone”。** 它们只对应假设参数的几何筛查。70% 并非官方安全储备要求或任务级能耗校准；FlyCart 16 km、Wingcopter 92 km 是不同试验和机型条件下的最大参考值，不能据此推导轻载/风雨/悬停/返航工况的安全半径。

WMP228 的圆参考资料存在坐标冲突，海岸线裁切、2026-10-29 生效版本及 NOTAM 未完成权威验收。将两个圆作并集排除仅是研究中的**几何保守情景**，不能替代正式空域限制边界。B 区不交叠 WMP228 也不意味着通过其他空域法规审查。

## 3. 怎样用 QGIS Desktop 3.22.4 打开

**推荐操作：** 将整个 ZIP 解压到英文路径（例如 `D:\CIQ_AB_NewA_v3\`），然后：

1. 双击 `CIQ_AB_NewA_v3.qgz`。此文件是无需运行代码的 *map-only 初始审核工程*，OSM 底图联网后显示，GPKG 节点、技术覆盖范围等均可编辑。
2. 打开 **插件 > Python 控制台**，运行以下两行代码（修改成你的实际目录）：

```python
f = r'D:\CIQ_AB_NewA_v3\code\02_QGIS322_BUILD_STYLES_LAYOUTS.py'
exec(compile(open(f, 'rb').read(), f, 'exec'))
```

3. 脚本将**清空当前 QGIS 项目**，从 V3 GeoPackage 重建图层、缩小标签、设置透明覆盖区，并生成两个 A3 横向布局：
   - `SCI_V3_AB_Main_3Panel_A3`：上方 A/B 总览、下方东部 A 主图和 B 主图，A09/A10 西部小插图；
   - `SCI_V3_UAV_NominalReach_4Panel_A3`：按 DJI/Wingcopter 和 A/B 区分别对比技术航程假设。
4. 自动保存 `.qgz`，并尝试导出 `QA/*.png`（300 dpi）。运行后请打开 **项目 > 布局管理器** 检查字体、瓦片、标签、比例尺和图层顺序。系统没有在此容器里提供 QGIS 3.22 的 Python API，因此本机打开渲染和打印布局仍需审核。

**注意**：代码不会创建航线批准，不会引入真实道路时变行程，更不会擅自修改 GitHub 订单和已冻结仿真结果。

## 4. 文件与代码

| 文件 | 用途 |
|---|---|
| `CIQ_AB_NewA_v3.qgz` | 可直接打开的 QGIS 审核地图，包含名义飞行覆盖图层 |
| `CIQ_AB_NewA_v3.gpkg` | **主要可编辑 GIS 数据库**：10 个 A 参考点、11 条新 A 候选线、B 冻结网络、研究窗口、空域参考及 8 个 UAV 技术覆盖图层 |
| `code/02_QGIS322_BUILD_STYLES_LAYOUTS.py` | QGIS 3.22.4 Python 控制台重建图层样式与布局（主代码） |
| `code/01_REBUILD_V3_GPKG.py` | 离线复建 GeoPackage（Python + fiona + shapely + pyproj） |
| `code/03_CREATE_STARTER_QGZ_NO_QGIS.py` | 从模板重建 map-only `.qgz`（Python + lxml + fiona） |
| `code/04_QA_V3_INDEPENDENT.py` | 无 QGIS 环境下的独立静态 QA |
| `code/05_DRAW_VECTOR_QA_PREVIEW.py` | 仅基于矢量的 QA 预览，不是 OSM 正式底图 |
| `flight_scenario_parameters.json` | UAV 最大航程、70% 名义比例、候选中心与有效性边界 |
| `A_new_10_nodes.csv`, `A_new_11_air_candidates.csv` | 点/候选航段属性表 |
| `seed/CIQ_AB_NewA_v3_CLEAN_INPUTS.gpkg` | 已剔除 A11 的冻结数据重建输入，不含研究用 A11 点或连线 |

## 5. 需要你特别核验的地理问题

- 新 A 区截图东部矩形是**人工近似**：A01 接近左边线，A08（Pandan）位于框左侧；不应简单把所有标记为 A 的点宣称都在手画的红框里。后续应用你在 QGIS 中真正数字化的研究区矢量替换该近似范围。
- A01 Swift 仓储位置有设施地址依据，但实际起降坪、土地/物业许可、车辆入口和障碍仍未核验；A02 是同一 Tebrau II 工业片区的备选搜索中心，不应与 A01 重复计作两个已建站点。
- A03 Bakar Batu 距 CIQ 较近，但需要注意河流、低洼区与地块安全；A09/A10 西部是对照研究，不代表经交通验证的最优线路。
- 当前新 A 仅保留 11 条*直线几何筛查*，不是沿真实可飞航道的曲线，更不是道路线路。道路接驳和 FCD 到有向路段的匹配尚未验收。

**本版本的验收目标：图层与编号正确、位置可在 OSM 底图下审核、文字清晰、无人机覆盖假设可编辑，之后再决定是否重新跑实验。**
