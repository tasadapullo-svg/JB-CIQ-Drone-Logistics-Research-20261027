# V2-S06 数据字典与严格解释约束

## data/S06_69_node_master.csv

- `node_id`, `zone`, `name`, `longitude`, `latitude`: V3 冻结 WGS84 点位与全名，可做节点空间索引。
- `class_source`: `V7_62_RETAINED_REFERENCE`, `V8_6_PORT_REFERENCES`, `GROUND_CIQ_GATEWAY`；源文件血缘，不是批准状态。
- `old_id_in_v3`: V3 自身字段，仅反映旧 ID **声称**，不等于旧版 Stage8 精准坐标验证。
- `road_access_gate`: 无可路由路网证据时保持 HOLD；不得用节点直线生成行车距离。
- `station_gate`, `sim_node_gate`: 候选点和实际合法起降资格必须区分。

## data/S06_crosswalk_legacy19_vs_V3_69_NOT_VERIFIED.csv

- `legacy_node_id_candidate`: 原 Stage8 记载的 A 九点及 B 十点的**同名候选**，`old_source_sha256`、原经纬度与差异值暂为空，禁止声称完成跨版本精确几何一致性验收。
- `A10`: V3 有 `legacy_id=A10`，但 Stage8 旧 A 点总数为 9，因此明确标记 REVIEW。

## data/S06_116_uav_geometry_candidates_ONLY.csv

- `line_mode=UAV_GEOMETRY_SEARCH`；`source_distance_km` 为几何测地线，不是避障/空域授权轨迹。
- `dji_5p6km_scenario_only`, `wing_32p2km_scenario_only`: 旧版压力测试开关，**不是 DJI FlyCart 30/Wingcopter 198 Cargo 厂商有效航程、载重匹配或安全储备**。
- `drone_dispatch_released=NO`: 禁止将几何线作为真实可飞航线。

## data/S06_5_ground_handoff_straight_references_NOT_ROUTES.csv

- `line_mode=GROUND_HANDOFF_STRAIGHT_REFERENCE`；`road_distance_km`, `road_travel_time_min` 保持空白，直到引入经路由验证的 OSM 图。
- `original_dji_flag_must_be_ignored=1` 及 Wing 同列证明源存在易错编码，但**不能**据此派发 UAV。

## data/S06_69_road_access_evidence_HOLD.csv

- 不是现行道路通达性结果，是各节点的道路证据缺口登记；`road_access_verified=NO` 代表本次未能验证，不代表实地无道路。

## data/S06_69_airspace_and_site_evidence_HOLD.csv

- `current_date_AIP_boundary_loaded`, `caam_NOTAM_effective_time_checked`, `caas_OneMap_effective_geo_boundary_loaded` 为本次**实际证据获取状态**，不能依据历史圆缺交就改为 YES。
- `UNKNOWN_NEEDS_AUTHORITATIVE_REVIEW` 不是 `PROHIBITED`，更不是 `ALLOWED`。

## geojson/*.geojson

使用 GeoPackage 原始坐标/线顶点导出，WGS84。所有直线几何都是条件性参考，不表示 3D 可飞路径或可行驶路径。
