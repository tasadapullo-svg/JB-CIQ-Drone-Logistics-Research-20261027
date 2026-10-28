# E02 有向道路网络与OD准备包 V4.6 — 2026-10-26

## 本轮事实结论

- **已经完成**：345个冻结FCD节点与19条GIS参考点读取及检查；两区域统一的道路提取边界；128条双向站点参考OD候选关系（A 56、B 72）；`OSM way` → 有向道路边处理程序；空间匹配候选程序；路网/OD初步QA；合成测试中，单行线禁止逆行的逻辑通过。
- **没有完成**：当前运行环境无法访问OSM服务，未拿到真实OSM道路拓扑；没有真实的有向道路边及其方向验证；没有经核实的法定国界裁剪、转弯限制；不能计算或声称**正式车辆门到门时间矩阵**。
- **不重复处理**：9月交通数据的既有审计结论，本包不重新分析；气象由用户并行下载。

## 下载来源（有网络的本地工程执行）

1. 首选执行程序从Overpass取得两个固定矩形范围内的高速/主干/支路等可供汽车使用的 `highway=*` ways + 相关节点。API限流时程序会退避重试，不会产生空道路图。
2. 可选经日期冻结的 Geofabrik OSM PBF：`https://download.geofabrik.de/asia/malaysia-singapore-brunei.html`；如从PBF开始，需要先以Osmium将研究区裁剪并转换成Overpass兼容JSON输入，本包不假装已进行此转换。
3. 数据必须标明OSM快照时间、来源和哈希；© OpenStreetMap contributors / ODbL。
4. 注意下载矩形**不是**柔佛州、马来西亚国界；两个窗口中可能混入新加坡境内道路。**正式物流结果须先取得国家边界多边形并执行边界验证**。

## Windows Codex执行顺序

在解压后的工程根目录运行（路径无空格时更简单）：

```powershell
py -m pip install -r requirements.txt
py code/e02_roadnet.py preflight --registry inputs/FCD_345_frozen_registry.csv --sites inputs/19_site_reference_anchors_NOT_LAUNCH_PADS.csv --out outputs
py code/e02_roadnet.py fetch --area A --out outputs
py code/e02_roadnet.py fetch --area B --out outputs
py code/e02_roadnet.py build --area A --input outputs/OSM_A_overpass_response.json --registry inputs/FCD_345_frozen_registry.csv --sites inputs/19_site_reference_anchors_NOT_LAUNCH_PADS.csv --out outputs
py code/e02_roadnet.py build --area B --input outputs/OSM_B_overpass_response.json --registry inputs/FCD_345_frozen_registry.csv --sites inputs/19_site_reference_anchors_NOT_LAUNCH_PADS.csv --out outputs
py tests/independent_logic_test.py
```

首次真实OSM运行后必须输出并归档：

- `OSM_{A/B}_overpass_response.json`和`OSM_{A/B}_download_metadata.json`（实际下载成功后才会出现）
- `E02_{A/B}_directed_edges_OSM.csv`：真实OSM有向边及长度/道路类型/单行标签，**OSM参考速度不是实测FCD速度**
- `E02_{A/B}_road_graph_nodes.csv`、`E02_{A/B}_road_graph_directed_OSM.geojson`：QGIS地理图层
- `E02_{A/B}_FCD_to_OSM_edge_CANDIDATES_NOT_APPROVED.csv`：FCD与OSM边的几何匹配候选。需人工/额外证据核实道路和方向，**未经批准不得赋FCD速度**
- `E02_{A/B}_OD_OSM_MODEL_NOT_OBSERVED.csv`：初步网络最短时间OD，采用OSM限速或道路等级假设，**只做拓扑与程序验算，不能作为观察到的旅行时间或无人机节时效果**
- `E02_{A/B}_logic_QA.json`：道路长度、连通性、节点匹配率、可达OD数量、未通过项目

## 交通时间正式放行门槛

以下所有条件是**尚待完成**，不以程序运行成功代替验收：

1. 道路OSM快照入档；A/B的OD均必须在可靠的马来西亚境内路网内，越境道路单独排除；网络方向和转弯限制达到可解释口径。
2. 345节点映射到道路边，包含实际距离、OSM way ID、方向、匹配证据；无法确认的节点保留待核，不把未知方向速度同时赋到道路两向。
3. 有向路径长度不小于相应两点测地线距离（允许微小数值容差）；同一路点到自身的路径长度应为0；查出无法连通的OD，不创建虚构直线连边。
4. 若模型路段速度由OSM等级假设补齐，必须明确 `MODEL_ESTIMATE`。要报告 **实测交通驱动** 的路径耗时，须记录路径上FCD观测覆盖比例及方向匹配，并进行独立旅行时间样本验证。可以在研究前冻结如80%观测长度覆盖率的研究阈值，但这不是交通行业通用标准。
5. 不把19条地理中心点当作已经批准的商业站点或真实订单；D1/D2订单OD是E05另行冻结的数据。

## 结果状态

- 可交付本地Codex立即开始：**是**。
- 可以发表真实OD与配送节时：**否，尚需取得真实道路和独立核验**。
- E01五个月原始速度：本包只引用既有验证；原始商业TomTom大文件不随包再次传播。

## 方法风险

- OSM缺少或不完整的专用道路限制、收费、境内外边境、私人道路、转向限制、具体时刻管制都可能影响最短路径。
- 本程序按单向标签建立有向图，但未解析OSM relation中的转弯限制，**任何路径都必须标明TURN_RESTRICTIONS_NOT_PARSED**。
- 从地点参考坐标吸附至路网节点仅是候选；建筑正门、停车位置和多式联运实际接驳步行距离须额外核查。
- OSM模型参考速度只是车辆通达性模型的初步输入，不得写成原始TomTom观测速度。
