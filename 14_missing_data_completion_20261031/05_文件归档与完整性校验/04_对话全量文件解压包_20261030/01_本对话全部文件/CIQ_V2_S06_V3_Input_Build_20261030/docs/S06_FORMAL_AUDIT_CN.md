# V2-S06｜V3 三分区正式空间输入构建与科学验收

**执行日期**：2026-10-30；**主线**：汽油车 M0 ↔ DJI/Wingcopter M1/M2，服务与成本约束下的运营碳排放比较。  
**性质**：对已上传真实 GeoPackage、CSV 和 QGIS 源工程进行只读建模输入构建；不是批准后的航空物流或已标定道路模型。  
**主输入**：`CIQ_ABC_QGIS322_NEW_COMPLETE_PROJECT_ALL_FILES_V3.zip`，SHA256：`a4e4d05397fa62d4611ea8a9a443445f8c6b9ae95c5ad545e7dea83aecd8ad92`。

## I. 本阶段已做的实际处理

1. 实际解压用户 V3 原包，独立核对核心 CSV、GeoPackage 19 个 EPSG:4326 图层、原始点坐标与线几何。
2. 在 `V7_ALL_62_RETAINED_ROLES`、`V8_CIQ_PORT_6_EVIDENCE_POINTS` 和 `G_CIQ_ground_gateway` 中保留 69 个独立点：A 23、C 29、B 10、港区补充 6、地面关口 1。
3. 对 V7 的 111 条几何线及 V8 的 10 条新增连接分别读取原 GPKG 线几何，检查源点、端点、测地距离。全部 121 条源线均能构建；属性长度与独立测地长度最大差 0.5 m。
4. 严格依据源类型与 `mode` 生成：116 条 UAV 候选几何关系（V7 111 + V8 5）以及 5 条地面交接直线参考。两个模式均**不得视为批准的运营线路**。
5. 为全部节点生成道路接入证据登记和空域/场地证据登记。保持原 V3 标注的“不具备批准运营资料”状态，**不擅自移点、删点或批准场地**。
6. 以历史 Stage 8 报告给出的 A9+B10 共 19 个旧参考点数量，生成 19 个基于同名 ID 的**候选**迁移关系；未取得旧 19 点坐标原件，因此未宣称跨版本位置一致。
7. 将前阶段独立核查的 37 条尚未应用的历史 OD 修复候选按节点编号关联，供后续道路网络修正参考，但不将其计入有效新路由。
8. 输出 3 个 GeoJSON、7 张真实输入 CSV、审计 JSON、来源 SHA256、运行日志和 14 项实际测试。

## II. 量化结果与结论

| 审查项 | 实际结果 | 判定 |
|---|---:|---|
| 69 个节点、编号、源坐标与几何 | 69 / 69 | PASS_REFERENCE |
| A/C/B/港区/关口 | 23 / 29 / 10 / 6 / 1 | PASS_REFERENCE |
| V7 几何候选与 V8 新增 UAV 候选 | 111 + 5 = 116 | PASS_CLASSIFICATION |
| V8 地面交接直线 | 5 | PASS_CLASSIFICATION |
| GeoJSON 输入产生 | 3 份 | PASS |
| 历史 Stage 8 相同 ID 候选 | 19 | HOLD_COORDINATES |
| V3 的 A10 `legacy_id` 情况 | A10 被 V3 标注旧别名，但 Stage8 记述 A 旧点 9 个 | HOLD_REVIEW |
| 原 37 条历史异常 OD | 37 条已关联；0 条被视为修复 | PASS_SAFE_QUARANTINE |
| 实际道路网络/节点合法道路接入 | 0 条独立验证记录 | HOLD |
| 当前生效的 CAAM/CAAS 空域法定边界 | 0 个可机读证据文件 | HOLD |
| 正式批准起降站点 | 0 个获批证据 | HOLD |
| 真实道路／飞行混合调度所需数据 | 未闭合 | HOLD |

**裁定**：`REFERENCE_INPUT_CONSTRUCTION = PASS`；`S07_SPATIAL_NODE_MAPPING = CONDITIONAL_GO`；`REAL_ROAD_AND_UAS_OPERATIONS = HOLD`。允许后续开展**假设性的情景仿真**，前提是显式标注适用性边界并取得其余道路、气象、能耗输入；不得宣称任何已批准航路或真实低碳收益。

## III. 两个必须长期保留的风险

**原 V8 中的五条地面交接线 `DJI_geom_5p6_km = 1`、`Wing_geom_32p2_km = 1`。** 这是可以触发错误筛选的混杂字段。本版仅在 `mode = UAV_GEOMETRY_SEARCH` 时输出 UAV 候选，地面交接关系绝不作为飞行任务，也不作为汽油车的道路距离。

**原 V3 中的 `WMP228_history_two_discs`、`V8_WMP228_TWO_REFERENCE_DISCS` 与 `Senai_5NM_aerodrome_ADVISORY` 为研究参考/告警几何。** 尽管源文件记录所有 116 条 UAV 几何线与指定的历史 WMP 参考圈均不相交，也**不能**推断当前时段的法律空域已允许飞行；不同司法管辖区还需考虑实际运行日期、空域高度、NOTAM/临时限制及跨境许可。

## IV. 需补充的道路接入核查（不可用直线代替）

本 V3 压缩包只有 QGIS 站点、示意连接、缓冲与历史告警圈，不含足够的可行驶路网数据。下阶段要求取得：

- 有版本号与来源的本区 OpenStreetMap 道路边、节点、道路类别、单行线和必要的转向限制（若缺转向限制，要明确部分路由是近似值）。
- 69 点的场地可接入道路/出入口是否存在、最近可行驶边/入口、缓冲距离、单行可达性、道路网络连通分量。
- 两区道路 OD 的有向去程、回程、实际路由距离及随时间变化的 FCD 道路速度；对原 37 条失败 OD 逐项记录已修复、仍 HOLD 或新证据替代。
- **所有燃油车行程与费用、CO₂e 核算必须使用有来源的有向道路距离，而非直线**。

## V. 空域与运营准入核查（官方来源与研究几何严格区分）

本轮公开官方来源审查已确认：CAAM 的 UAS 页面提出商业/BVLOS 等高风险作业审批要求；其 AIS 页面列示 AIP、AIP SUP、NOTAM 类型。CAAS 的官方 OneMap 指南指出禁飞区、许可区域、临时限制会随地点与日期变化；另有跨境无人机许可指引 AC 101-2-3。**这些是法规材料，不等于已下载生效期 GIS 边界**。

- CAAM UAS：<https://www.caam.gov.my/public/unmanned-aircraft-system-uas/>
- CAAM AIS/AIP/NOTAM：<https://www.caam.gov.my/public/ais/>
- CAAS 无人机地理限制/OneMap：<https://www.caas.gov.sg/unmanned-aircraft/no-fly-zones-and-ua-flying-areas/>
- CAAS 无人机法规清单与跨境许可通告：<https://www.caas.gov.sg/resources/regulatory-requirements-and-guidelines/unmanned-aircraft/>
- CAAS 运营许可：<https://www.caas.gov.sg/unmanned-aircraft/operator-and-activity-permits/>

后续需独立核对试验**每一个实际日期**的官方生效边界、空域高度、NOTAM 和司法权，按 `EXCLUDED / NEEDS_APPROVAL / NOT_ASSESSED` 分类，且不得把 `UNKNOWN` 自动写成 `ALLOWED`。没有生效官方图层时，给出情景约束和政策不确定性分析即可，不能推出实地获批飞行。

## VI. 与 S07–S12 的数据接口

- S07 可用：69 个参考 `node_id, lon, lat, zone`、116 UAV 研究几何与 5 地面关系的**模式区分**。需将 2026-05 至 09 的天气与道路按 `zone × time` 映射并记录气象格网代表性与缺测。
- S08 使用新 OSM 有向道路图构建 **汽油车 M0**。未完成道路接入前不得以 GeoJSON 飞行线替代地面行车路线。
- S09 仅可对两款机型进行几何/载荷的压力测试；任务级可用电量、任务起降与风负荷未标定前不得给出确定的绝对排放排名。
- S10/S11 将模型运行限定为有注明的场景，严格设置任务级回退、车辆实际里程、充电、成本和统一能耗边界；不能无证据将模拟线路描述为可获批商业线路。
- S12 统计和论文结果必须区分（a）参考网络输入通过，（b）条件性仿真得到结果，（c）场地与监管批准未核实。

### 下一个实际操作门槛

1. 先将本包内 `outputs/data/` 和 `outputs/geojson/` 作为 **V2-S06 基础版本**冻结。
2. 对照原 Stage 8 的 `19_site_reference_anchors_NOT_LAUNCH_PADS.csv` 做真实旧新点坐标差异检查；无法取得旧源则保留同名映射待检，不阻碍全新任务生成。
3. 取得有向 OSM 道路图和官方法规空间资料；在这些缺失时可开发仿真程序、做明确场景假设，但禁止发布“已验证真实部署”的时间/碳排放数据。
4. 将交通与气象资料按冻结的节点 ID 关联，开始 V2-S07 数据接入。

**完整复现指令**见根目录 `README_CN.md`，包括 Python 程序、运行结果及实际测试日志。不得直接覆盖历史 Stage 3–8。
