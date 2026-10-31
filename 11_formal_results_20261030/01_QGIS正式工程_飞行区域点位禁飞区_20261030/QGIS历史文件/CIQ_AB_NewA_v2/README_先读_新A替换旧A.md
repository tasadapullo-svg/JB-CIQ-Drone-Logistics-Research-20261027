# CIQ 双走廊 GIS V2：新 A 替换旧 A，B 保持不变

**日期：2026-10-29 | 目标 QGIS：3.22.4 | 状态：GIS 科研审核版，不是合法起降场批准文件。**

## 1. 本次正式替换

旧版 A00–A08 **作为物流节点及原有候选连接被从本版本的有效 GeoPackage / QGIS 图层中排除**。原来的 22 条旧 A 去重几何线也被排除。旧 A 不与新 A 混合计算。

- E01 → **A01**，Swift Integrated Logistics Tebrau II，优先核验仓储场地；不是批准起降场。
- E02 → **A02**，Tebrau II 工业片区，A01 同工业簇备选；不是独立已验证起降场。
- E03 → **A03**，Bakar Batu，条件性公路接驳/转运场地搜索中心。
- E04 → **A04**，Mid Valley Southkey，商业需求参考点。
- E05 → **A05**，Taman Molek，混合需求参考点。
- E06 → **A06**，Permas Jaya，住宅商业需求参考点。
- E07 → **A07**，Kampung Tengah，居住需求参考点，地块合规需额外核查。
- E08 → **A08**，Pandan 批发市场，需求参考点。
- W01 → **A09**，Bukit Indah 工业参考建筑，西部对照场地搜索中心。
- W02 → **A10**，Bukit Indah 快递服务需求参考点。
- W03 → **A11**，Perling 居住需求参考点。

**Causeway 关口单独编码 `G_CIQ`，只是地面货流及地理背景参考点**，使用原地理参考坐标（103.76663E，1.46502N），不算旧 A 节点、不算无人机起降站。

B00–B09 保留，不修改坐标；B 区 33 条去重几何连接保留，不能误报为 48 条有向实际飞行线路。新 A 有 11 个位置和 12 条**直线筛查参考段**；在未核验目标落点、完整路径、天气与监管限制前，12 条均不属于批准航段。

## 2. 建议打开方式

1. 完整解压 ZIP，**不要移动单独的 QGZ**，保留 GeoPackage、`inputs/` 和 `regulatory_source/` 等相对路径。
2. QGIS Desktop 3.22.4 → **项目 → 打开** → `CIQ_AB_NewA_v2.qgz`。
3. 需在线地图时允许 OSM XYZ 底图联网，离线时仍能编辑并查看矢量点、线及参考圆。
4. 图层树：`01` 新 A/B 站点和需求、`02` 地空几何连接、`03` WMP228 监管参考、`04` 两个手绘区域、`05` OSM 底图。
5. 想在 QGIS 内重新建立完整样式和上总览/下 A/B 三联 A3 布局，可在 **插件 → Python 控制台**运行：

```python
f = r'D:\CIQ_AB_NewA_v2\code\02_BUILD_NEW_A_B_IN_QGIS_322_CONSOLE.py'
exec(compile(open(f, 'rb').read(), f, 'exec'))
```

把 `D:\CIQ_AB_NewA_v2` 替换为你实际解压后的路径。此脚本会**清空并重建当前 QGIS 工程**，因此请先保存你正在编辑的其他工程。输出 `.qgz` 和 300 dpi PNG，另有可编辑的 QGIS Print Layout。若需要 600 dpi，把代码最后的 `EXPORT_DPI=300` 改为 `600`。

> 此环境不具备 QGIS 3.22 Python 库；已做数据文件、QGZ 项目 XML、文件路径、代码语法、GIS 要素及编号检查，但 **QGIS 本机实际渲染与 PNG 导出尚待你运行验收**。

## 3. 文件与复现流程

- `CIQ_AB_NewA_v2.qgz` — 预生成的可打开 QGIS 工程（本机渲染待验收）。
- `CIQ_AB_NewA_v2.gpkg` — 11 个正式的可编辑空间图层；不包括旧 A 点或旧 A 连线。
- `code/01_REBUILD_NEW_A_B_FILES.py` — 从本包输入数据重建 `.gpkg`、`.qgz`、CSV 与 QA 清单（通用 Python，需 geopandas/fiona/lxml/pyproj）。
- `code/02_BUILD_NEW_A_B_IN_QGIS_322_CONSOLE.py` — 原生 PyQGIS 全工程建图/符号/三联打印布局。
- `code/03_OPTIONAL_OSM_GROUND_ROUTES_NEW_A_B.py` — 可选：严格按 SHA256 核验冻结 OSM 的公路几何路由；不是实时交通速度和合法道路大门证明。
- `code/04_INDEPENDENT_QA_AND_PREVIEW.py` — 离线空间一致性 QA 和不含 OSM 底图的预览图。
- `ID_E_W_to_NEW_A_crosswalk.csv` — **审计专用**旧 E/W 代号与新 A 代号对照；不是旧 A 图层。
- `A_new_site_evidence_review.csv` / `A_new_air_geometry_screen.csv` — 新 A 证据与候选几何航段表。
- `Ground_OD_requests_NOT_ROUTES.csv` — 需要完成的公路 OD 请求；此 CSV 不提供已生成路线。
- `QA/NEW_A_B_3panel_VECTOR_ONLY_PREVIEW.png` — 矢量几何 QA，**不是使用真实道路底图导出的 SCI 正式地图**。

如需用独立 Python 复现全部数据，**在解压文件夹中**运行：

```shell
python code/01_REBUILD_NEW_A_B_FILES.py
python code/04_INDEPENDENT_QA_AND_PREVIEW.py
```

如要计算可选 OSM 图几何路线（可能下载两个约十余 MB 原始快照）：

```shell
python code/03_OPTIONAL_OSM_GROUND_ROUTES_NEW_A_B.py
```

其道路结果未完成实际场地车辆出入口、转向规则、边检通行、FCD 方向匹配与时变路速的科学验收，**不能直接作为论文的交通时间结果**。

## 4. 科学结论与边界

- **已完成**：旧 A 运营节点及候选连接完全排除；新 A 11 个候选/需求锚点重编号；新 A 12 条候选线端点同步重编号；B 10 点和 33 条去重几何线保持；双版本 WMP228 圆及用户红框保留为独立参考；GIS QA 通过。
- **未完成**：新站点地块/大门/物业许可/建筑障碍/人口暴露确认；2026-10-29 适用 WMP228 法定边界、NOTAM 及其他空域审查；无人机完整航段、安全着陆/回收核验；有向道路实地连接和 FCD 速度标定；订单仿真复算。新 A 是**研究审核网络**而非获批运营网络。
- 两套 WMP228 完整 2 NM 圆只是公布坐标差异下的几何敏感性筛查，不能当作两个并存的法定禁飞区；图上手绘区域也只是大致定位，不是行政/法定空域边界。
- 本版 **不重跑原有 29,842 合成订单、不更新 Fig. 5/6/7 结论**，等你验收 GIS 设计和后续道路/场地审计完成后再继续。

### 地理数据来源记录

新 A 位置证据和链接位于 GeoPackage `A_new_11_evidence_nodes` 的 `source`, `geo_source`, `risk` 字段；B 坐标及几何为旧项目中冻结的 B 参考数据。两个 WMP228 来源版本与 CAAM/CAAS 链接位于 `WMP228_two_historical_discs` 图层。OD 路网基准来自项目 GitHub 2026-10-26 冻结的 OSM Overpass 快照，**本包未擅自补造道路路径**。
