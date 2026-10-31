# CIQ ABC V3 QGIS 工程：V2-S06 独立空间输入验收报告

**审计日期：** 2026-10-30  
**原始输入：** `CIQ_ABC_QGIS322_NEW_COMPLETE_PROJECT_ALL_FILES_V3.zip`  
**原始输入 SHA-256：** `a4e4d05397fa62d4611ea8a9a443445f8c6b9ae95c5ad545e7dea83aecd8ad92`  
**验收性质：** 真实上传文件的离线 GIS 数据级审计；尚未进行 QGIS 3.22.4 桌面运行、法规审批或真实道路验证。

## 1. 明确裁定

- **PASS（可用）**：V3 工程作为**新版三分区空间参考输入**的原始节点、属性和几何数据，可从本次上传的 GeoPackage 和 CSV 读取。旧版“最新 QGIS 工程未上传”的阻断原因已解除。
- **CONDITIONAL GO（可开始）**：V2-S06 节点网络登记、旧新节点映射、地面／UAV 线段分型、地理哈希冻结、模型输入接口和必要质量测试。
- **HOLD（不可冒充通过）**：QGIS 3.22.4 GUI 实际打开与导图，真实路由道路网络、地块与空域合规、实际可飞航路以及正式汽油车 M0 / DJI、Wingcopter M1/M2 仿真。

## 2. 独立核查数值

| 项目 | 独立结果 | 裁定 |
|---|---:|---|
| ZIP 归档条目 | 34 个；ZIP CRC 成功 | PASS |
| SHA-256 清单 | 33 条文件记录全部一致；第 34 个文件是清单本身，按常规未自引用 | PASS |
| QGS/QGZ | XML 内容逐字节相同；XML 解析通过 | PASS，GUI 待测 |
| QGIS 图层引用 | 19/19 GeoPackage 图层和相对路径存在 | PASS |
| GeoPackage SQLite 完整性 | `PRAGMA integrity_check = ok` | PASS |
| 图层 CRS | EPSG:4326；全部 19 个均一致 | PASS |
| 全图层几何 | 19 层均无空几何、无拓扑无效几何 | PASS |
| 全部独立节点 | 69 个，名称/编号全部唯一非空 | PASS |
| A / C / B | 23 / 29 / 10 | PASS |
| 港区参考点／地面网关 | 6 / 1 | PASS |
| `ALL_68_STUDY_NODES_LONG_LAT.csv` 对 GeoPackage | 68/68 ID、名称、坐标一致 | PASS |
| `QA_ALL_69_NODE_LABELS.csv` 对 GeoPackage | 69/69 ID、名称、坐标和表达式正文一致 | PASS |
| V7+V8 两类核心线 | 111+10 = 121 条 | PASS |
| 线端点到 69 节点 | 121/121，偏差 0 m | PASS |
| WGS84 测地线长与属性距离 | 最大差异 0.5 米 | PASS |
| 自环／重复 `edge_id`／重复有向点对 | 0 / 0 / 0 | PASS |
| V7 52+10 节点子图与合并图 | 62/62 几何一致 | PASS |
| V7 78+33 线段子图与合并图 | 111/111 几何一致 | PASS |
| 6 个 PyQGIS／Python 脚本 | 6/6 语法解析通过；未实际执行 QGIS 专属 API | PASS_SYNTAX_ONLY |

**经纬度方向：** WGS84 / EPSG:4326，`longitude (X)` 为东经、`latitude (Y)` 为北纬。本次数据实际经度范围 `103.5468–103.8327`，纬度范围 `1.35327–1.5521`。这些数值证明 GIS/CSV 内部一致；不代表已与政府高精度海岸线、道路和地籍底图完成外部配准验证。

## 3. 需要修复或严格隔离的问题

**P0 — 5 条地面直线具有 UAV 航程标志：** 在 `V8_CIQ_PORT_10_GROUND_AND_UAV_GEOMETRY` 中，5 条 `GROUND_HANDOFF_STRAIGHT_REFERENCE` 地面线的 `DJI_geom_5p6_km` 和 `Wing_geom_32p2_km` 均为 1。它们仍然是地面交接参考线，绝不可仅按航程布尔值筛进 UAV 任务。必须以 `mode == UAV_GEOMETRY_SEARCH` 为优先筛选条件。原始数据保留不动。

**P0 — 尚无真正可行驶的地面路由网络：** 本 ZIP 只有节点和直线几何、研究显示面及筛查圈，没有带通行方向／道路限制／交通速度的可求路图。需要 V2-S07/S08 引入 OSM 道路、路径成本与道路状态；`G_CIQ→A_P01` 的 1.8174 km 为直线，不是汽油车道路里程。

**P0 — 起降/空域仍为搜索参考：** V7 的 62 个节点 `uav_operational_admission=NO`；V8 的 6 点也无已证实的批准起降资格。WMP228 两参考圆及 Senai 邻近圈仅是科研参照情景，不是执行日期的完整法律空域；不能据此认定任何可执行航线。

**P1 — 机型航程仅为旧情景半径：** 在 116 条 UAV 候选直线中，DJI 的 5.6 km 单段几何压力测试为 99 条在内、17 条在外；Wingcopter 32.2 km 情景下为 116 条在内。`99/116` 与 `116/116` 不是天气/电量/合法性/实际运输服务完成率。

**P1 — 桌面 QGIS 渲染尚未验收：** 两种工程文件的 XML、数据源和三个主节点图层的 `ID | name` 标注配置已复核；但本环境没有 QGIS 3.22.4 运行时。ZIP 附的 `figures/` 是离线预览，`exports/` 尚没有主脚本实际导出的六套正式布局；在用户电脑打开 `.qgz` 并运行构建脚本后需复核全名称标签、背景图与图框裁切。总体图用短 ID，区域图可通过名称索引查全名。

**P1 — 未与旧版本跨包逐点比对：** V3 中 `B_10_FROZEN_NOT_PADS` 与 V3 合并图的 10 个 B 点完全一致，这只能证明**V3 内部一致**；若要验证“相对历史 Stage 3–8 的 B 区绝未移动”，仍须读取原始冻结文件按 ID/坐标/哈希逐点对比。

## 4. 后续模型严禁误读

| 数据字段 / 图层 | 可以做 | 不可以做 |
|---|---|---|
| 69 个 WGS84 点及名称 | 构造条件性站点/需求参考网络 | 宣称 69 个已获批准起降坪 |
| 116 条 UAV 直线 | 进行必要的几何长度初筛 | 代替审批航线、风场路线、3D 避障路线 |
| 5 条港区地面直线 | 构造示意接驳拓扑 | 当作 OSM 驾车距离、行驶时间、实际道路 |
| 历史 WMP228 两圆 | 做谨慎的敏感性或对照情景 | 作为当前法定禁飞区完整边界 |
| 5.6 / 32.2 km 情景半径 | 距离压力测试 | 当作两款机型的载重—风—能耗可执行航程 |
| `QGIS 3.22.4` 工程定义 | 在本机打开、生成正式布局 | 仅用 XML 成功宣称图件已通过桌面渲染 |

## 5. 建议立即执行的 V2-S06 子步骤

1. 以本上传 ZIP 的 SHA256 冻结 `spatial_reference_version=QGIS_ABC_V3_20261030`，本文件只读，绝不覆盖历史 Stage 3–8。归档位置建议：`11_v2_carbon_first_experiments/V2-S06/inputs/QGIS_ABC_V3/`。
2. 使用交付的 `V3_69_nodes_verified.csv` 和 `V3_121_links_independent_geometry_audit.csv` 建立新旧 ID 的逐点对照；必须通过 ID/坐标审核才允许历史订单站点映射。
3. 建立 `uav_candidate_edges`（116 条）与 `ground_reference_beelines`（5 条）的严格分表，另加 `node_site_status`、`airspace_status`、`road_access_status` 字段；全程保留 UNKNOWN/HOLD。
4. 在 QGIS Desktop 3.22.4 打开 `.qgz`，验证 19 图层、69 节点全名与实际输出，运行 `code/01_BUILD_COMPLETE_QGIS322.py` 生成布局 PNG 和新工程；不把正式地图质量归因于离线预览图。
5. 使用权威底图和 OSM 道路网络分别验证点与道路出入口，以及候选线路与现行空域图层；不能因为现有参考圆未相交就批准飞行。
6. 通过上述 Gate 后，将 S06 空间输入交付 S07 时间对齐与 S08 汽油车地面基线，之后才能启动五模式实际仿真。

## 6. 已生成的验证输出

- `V3_independent_audit.json`：机器可读的独立核查全表。
- `V3_file_sha256_verified.csv`：文件 SHA256 与随包清单逐项对照。
- `V3_QGIS_layer_references.csv`：19 个图层的相对路径和标签配置。
- `V3_69_nodes_verified.csv`：69 个节点名称、类型、经纬度与证据网址。
- `V3_CSV_vs_GPKG_68_nodes.csv`：68 点独立坐标交叉核对。
- `V3_69_label_coordinates_independently_crosschecked.csv`：69 点标签文本及坐标对照。
- `V3_121_links_independent_geometry_audit.csv`：逐线 ID、端点、长度、类别和不正确混筛风险。
- `V2_S06_RELEASE_GATES.json`：可开始与必须 HOLD 的门槛。
- `audit_v3_independent.py` 和 `check_data_crosswalk.py`：只读复核代码，不调用用户包内可能有副作用的 PyQGIS 绘制程序。

**最终裁定：V3 作为“冻结空间参考网络输入”的数据验收通过；S06 正式 QGIS 桌面图件、道路通达与合法运营许可仍需补做。不能因此提前发布汽油车与无人机排放结果。**
