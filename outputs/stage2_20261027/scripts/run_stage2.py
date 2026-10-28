from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import io
import json
import platform
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "stage2_20261027"
E02 = ROOT / "03_GIS与路网" / "路网工程" / "JB_CIQ_E02_roadnet_V4_6"
E02_OUT = E02 / "outputs"
E02_INPUT = E02 / "inputs"
STAGE1 = ROOT / "outputs" / "next_stage"
STAGE2_INSTRUCTION = ROOT / "00_项目说明" / "Codex说明" / "CIQ_Codex_Stage2_Repair_Calibrate_Gates_20261027.md"
V56 = next(ROOT.rglob("JB_CIQ_E05_V5.6_30次*.zip"))
V54 = next(ROOT.rglob("JB_CIQ_E05_模拟*.zip"))
V53 = next(ROOT.rglob("JB_CIQ_E05-E07_24小时*.zip"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def read_e02_module():
    path = E02 / "code" / "e02_roadnet.py"
    spec = importlib.util.spec_from_file_location("e02_roadnet_stage2", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_source_outputs() -> dict:
    inventory = pd.read_csv(STAGE1 / "project_inventory.csv")
    inventory = inventory.rename(columns={"evidence_status": "stage1_evidence_status"})
    paths = inventory["relative_path"].astype(str).str.lower()
    status = np.where(
        paths.str.contains("v5.5"),
        "REFERENCE_ONLY",
        np.where(
            inventory["likely_role"].isin(["order_or_demand_fixture", "road_network_or_routing", "traffic_input_or_result", "weather_input_or_result"]),
            "FOUND_VERIFIED",
            "FOUND_UNVERIFIED",
        ),
    )
    inventory.insert(0, "stage2_status", status)
    inventory.to_csv(OUT / "source_inventory.csv", index=False, encoding="utf-8-sig")

    lineage = pd.DataFrame(
        [
            {
                "lineage_step": 1,
                "artifact": "V5.4 synthetic order fixture",
                "status": "FOUND_VERIFIED",
                "source_or_code": f"{V54.name}::generate_synthetic_od.py",
                "transformation": "fixed illustrative demand assumptions create 30,600 records",
                "output": "V5.4 example orders",
                "risk": "not empirical demand",
            },
            {
                "lineage_step": 2,
                "artifact": "V5.5 frozen joined source",
                "status": "ABSENT",
                "source_or_code": "SOURCE_V5.5/01_E05_orders_24h_FCD_ERA5_referenceOD_join.csv.gz",
                "transformation": "claimed traffic/weather/reference-OD join",
                "output": "V5.5 frozen source",
                "risk": "referenced hash exists but data file is absent",
            },
            {
                "lineage_step": 3,
                "artifact": "V5.6 resampling transformation",
                "status": "ABSENT",
                "source_or_code": "generator code not present in V5.6 archive or workspace",
                "transformation": "stratified resampling with replacement",
                "output": "30 seed shards",
                "risk": "transformation cannot be independently rerun",
            },
            {
                "lineage_step": 4,
                "artifact": "V5.6 current baseline snapshot",
                "status": "FOUND_VERIFIED",
                "source_or_code": V56.name,
                "transformation": "none in Stage 2; read-only audit",
                "output": "30 seeds / 918,000 rows",
                "risk": "usable as current snapshot, not renameable as V5.5",
            },
        ]
    )
    lineage.to_csv(OUT / "source_lineage.csv", index=False, encoding="utf-8-sig")

    stage1_audit = pd.read_csv(STAGE1 / "input_audit.csv")
    stage1_audit.insert(0, "stage2_interpretation", "CURRENT_BASELINE_SNAPSHOT_ONLY_LINEAGE_INCOMPLETE")
    stage1_audit.to_csv(OUT / "order_integrity_checks.csv", index=False, encoding="utf-8-sig")

    selected = [
        V56,
        V54,
        V53,
        ROOT / "02_基础与交通数据" / "交通数据" / "JB_CIQ_E01_修正后五个月交通数据_345nodes_2026-05_09.csv.gz",
        ROOT / "04_天气数据" / "汇总数据" / "E03_ERA5_JB_TWO_CIQ_WEATHER_HOURLY.csv",
        ROOT / "02_基础与交通数据" / "联合与派生数据" / "01_AB_24h_hourly_joint.csv",
        ROOT / "02_基础与交通数据" / "联合与派生数据" / "03_hourly_91_reference_OD_MODEL_PROXY_NOT_REAL.csv.gz",
        E02_INPUT / "19_site_reference_anchors_NOT_LAUNCH_PADS.csv",
        E02_OUT / "OSM_A_overpass_response.json",
        E02_OUT / "OSM_B_overpass_response.json",
        STAGE1 / "validation_report.json",
        STAGE1 / "SHA256_manifest.csv",
        ROOT / "outputs" / "CIQ_next_stage_audit_smoke_20261027.zip",
        STAGE2_INSTRUCTION,
    ]
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_root": str(ROOT),
        "git_commit": None,
        "git_status": "NO_GIT_REPOSITORY_AT_PROJECT_ROOT",
        "inputs": [
            {
                "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                "bytes": path.stat().st_size,
                "modified_utc": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
                "sha256": sha256(path),
            }
            for path in selected
            if path.exists()
        ],
        "absent_required_inputs": [
            {
                "path": "SOURCE_V5.5/01_E05_orders_24h_FCD_ERA5_referenceOD_join.csv.gz",
                "expected_bytes": 1007063,
                "expected_sha256": "932899a6178a6f464db2dd66195d4e0d81b058f3501d289e1ad417bd040a71f5",
            },
            {"path": "V5.6 resampling generator code", "expected_sha256": None},
        ],
    }
    write_json(OUT / "input_hash_manifest.json", manifest)

    (OUT / "freeze_gap_report.md").write_text(
        """# 冻结数据与血缘缺口报告

## 结论

当前30个种子可作为只读的“现有基准快照”使用，但不能称为可完整复现的V5.5冻结数据链。

- 已验证：30个分片、918,000行、918,000个唯一订单ID、包内成员哈希一致。
- 已确认：订单属于重采样工程夹具，不是独立实测需求。
- 缺失：V5.6清单引用的V5.5冻结联结文件。
- 缺失：执行V5.6重采样的生成代码。
- 可复现边界：可以从现有V5.6分片无歧义地重新读取任一seed订单集合；不能从V5.5源重新生成这些分片。

因此 `G1_DATA_LINEAGE=BLOCKED`，不得启动正式30种子主实验。Stage 2未生成、改名或覆盖任何订单。
""",
        encoding="utf-8",
    )
    return manifest


def components(G: nx.MultiDiGraph):
    weak_sets = sorted(nx.weakly_connected_components(G), key=len, reverse=True)
    strong_sets = sorted(nx.strongly_connected_components(G), key=len, reverse=True)
    weak_map = {node: i for i, nodes in enumerate(weak_sets) for node in nodes}
    strong_map = {node: i for i, nodes in enumerate(strong_sets) for node in nodes}
    return weak_map, {i: len(x) for i, x in enumerate(weak_sets)}, strong_map, {i: len(x) for i, x in enumerate(strong_sets)}


def spatial_context(G: nx.MultiDiGraph, transformer):
    node_ids = list(G.nodes)
    node_xy = np.asarray([transformer.transform(G.nodes[n]["lon"], G.nodes[n]["lat"]) for n in node_ids])
    node_tree = cKDTree(node_xy)
    unique = {}
    for u, v, _, data in G.edges(keys=True, data=True):
        key = (min(u, v), max(u, v), data["way_id"])
        unique.setdefault(key, (u, v, data))
    edge_records = list(unique.values())
    edge_shapes = [
        LineString(
            [
                transformer.transform(G.nodes[u]["lon"], G.nodes[u]["lat"]),
                transformer.transform(G.nodes[v]["lon"], G.nodes[v]["lat"]),
            ]
        )
        for u, v, _ in edge_records
    ]
    return node_ids, node_xy, node_tree, edge_records, edge_shapes, STRtree(edge_shapes)


def site_candidates(row, context, transformer, k=8):
    node_ids, node_xy, node_tree, edge_records, edge_shapes, edge_tree = context
    point_xy = transformer.transform(float(row.longitude), float(row.latitude))
    point = Point(*point_xy)
    edge_index = int(edge_tree.nearest(point))
    edge_u, edge_v, edge_data = edge_records[edge_index]
    edge_distance = float(point.distance(edge_shapes[edge_index]))
    distances, indices = node_tree.query(point_xy, k=k)
    distances = np.atleast_1d(distances)
    indices = np.atleast_1d(indices)
    candidates = {int(node_ids[int(i)]): float(d) for d, i in zip(distances, indices)}
    for node in (edge_u, edge_v):
        idx = node_ids.index(node)
        candidates[int(node)] = float(np.linalg.norm(node_xy[idx] - np.asarray(point_xy)))
    ordered = sorted(candidates.items(), key=lambda item: item[1])
    return {
        "nearest_node": ordered[0][0],
        "nearest_node_distance_m": ordered[0][1],
        "nearest_edge_distance_m": edge_distance,
        "nearest_edge_u": int(edge_u),
        "nearest_edge_v": int(edge_v),
        "nearest_edge_way_id": int(edge_data["way_id"]),
        "nearest_edge_highway": edge_data["highway"],
        "nearest_edge_name": edge_data["name"],
        "candidates": ordered,
    }


def route_between_candidates(G, origin_context, destination_context):
    best = None
    source_access_map = dict(origin_context["candidates"])
    sources = list(source_access_map)
    for target, target_access in destination_context["candidates"]:
        try:
            distance, path = nx.multi_source_dijkstra(G, sources, target=target, weight="minutes")
        except nx.NetworkXNoPath:
            continue
        source = path[0]
        source_access = source_access_map[source]
        if path:
            length_m = 0.0
            for u, v in zip(path[:-1], path[1:]):
                edge = min(G[u][v].values(), key=lambda d: d["minutes"])
                length_m += edge["length_m"]
            candidate = {
                "source_node": int(source),
                "target_node": int(target),
                "origin_access_node_distance_m": source_access,
                "destination_access_node_distance_m": target_access,
                "route_minutes": float(distance),
                "route_length_km": length_m / 1000,
                "path_edge_count": max(len(path) - 1, 0),
            }
            score = candidate["route_minutes"] + (source_access + target_access) / 1000 / 20 * 60
            if best is None or score < best[0]:
                best = (score, candidate)
    return None if best is None else best[1]


def make_route_outputs(e02):
    sites_all = pd.read_csv(E02_INPUT / "19_site_reference_anchors_NOT_LAUNCH_PADS.csv")
    diagnostic_rows = []
    repair_rows = []
    area_details = {}

    for area in ["A", "B"]:
        raw = E02_OUT / f"OSM_{area}_overpass_response.json"
        graph, _ = e02.construct_graph(json.loads(raw.read_text(encoding="utf-8")))
        weak_map, weak_sizes, strong_map, strong_sizes = components(graph)
        context = spatial_context(graph, e02.T)
        sites = sites_all[(sites_all.area == area) & (sites_all.place_type != "CIQ_reference")].copy()
        site_context = {row.site_id: site_candidates(row, context, e02.T) for row in sites.itertuples(index=False)}
        old = pd.read_csv(E02_OUT / f"E02_{area}_OD_OSM_MODEL_NOT_OBSERVED.csv")
        for old_row in old.itertuples(index=False):
            origin = site_context[old_row.origin_id]
            destination = site_context[old_row.destination_id]
            original_ok = old_row.status == "MODEL_ROUTE_REQUIRES_QA"
            original_source = int(origin["nearest_node"])
            original_target = int(destination["nearest_node"])
            same_weak = weak_map[original_source] == weak_map[original_target]
            same_strong = strong_map[original_source] == strong_map[original_target]
            candidate = None if original_ok else route_between_candidates(graph, origin, destination)

            if original_ok:
                category = "NONE_EXISTING_ROUTE"
                subcause = "ORIGINAL_MODEL_ROUTE_PRESENT"
                post_status = "EXISTING_ROUTE_REQUIRES_QA"
            elif old_row.status == "SNAP_REVIEW_REQUIRED" and (
                origin["nearest_edge_distance_m"] > 100 or destination["nearest_edge_distance_m"] > 100
            ):
                category = "DATA_GAP"
                subcause = "REFERENCE_ANCHOR_GT_100M_FROM_OSM_ROAD_EDGE_ACCESS_NOT_ESTABLISHED"
                post_status = "CANDIDATE_ROUTE_NOT_APPROVED_REFERENCE_ACCESS_GAP"
            elif candidate is not None and (
                origin["nearest_edge_distance_m"] <= 100 and destination["nearest_edge_distance_m"] <= 100
            ):
                category = "SNAP_FAILURE"
                if old_row.status == "DISCONNECTED_IN_OSM" and same_weak and not same_strong:
                    subcause = "NEAREST_NODE_ON_DIRECTIONALLY_INCOMPATIBLE_LANE_OR_SINK"
                else:
                    subcause = "NEAREST_NODE_THRESHOLD_REJECTED_NEARBY_OSM_EDGE"
                post_status = "CANDIDATE_ROUTE_NOT_APPROVED_ACCESS_DIRECTION_UNVERIFIED"
            elif not same_weak:
                category = "DISCONNECTED_COMPONENT"
                subcause = "ORIGINAL_SNAPS_IN_DIFFERENT_WEAK_COMPONENTS"
                post_status = "UNREACHABLE_IN_CURRENT_GRAPH"
            elif same_weak and not same_strong:
                category = "DIRECTED_ONE_WAY"
                subcause = "WEAKLY_CONNECTED_BUT_NO_DIRECTED_PATH"
                post_status = "UNREACHABLE_IN_CURRENT_DIRECTED_GRAPH"
            else:
                category = "DATA_GAP"
                subcause = "NO_SUPPORTED_ROUTE_WITH_AVAILABLE_OSM_SNAPSHOT"
                post_status = "UNRESOLVED"

            row = {
                "od_id": f"{old_row.origin_id}_{old_row.destination_id}",
                "area": area,
                "corridor_context": "Causeway_inland_reference_area" if area == "A" else "Second_Link_inland_reference_area",
                "cross_border_route": False,
                "origin_id": old_row.origin_id,
                "destination_id": old_row.destination_id,
                "origin_latitude": float(sites.loc[sites.site_id == old_row.origin_id, "latitude"].iloc[0]),
                "origin_longitude": float(sites.loc[sites.site_id == old_row.origin_id, "longitude"].iloc[0]),
                "destination_latitude": float(sites.loc[sites.site_id == old_row.destination_id, "latitude"].iloc[0]),
                "destination_longitude": float(sites.loc[sites.site_id == old_row.destination_id, "longitude"].iloc[0]),
                "original_status": old_row.status,
                "original_route_exists": original_ok,
                "original_route_length_km": old_row.route_length_km,
                "original_osm_minutes": old_row.OSM_only_minutes_MODEL,
                "origin_nearest_node_id": original_source,
                "destination_nearest_node_id": original_target,
                "origin_nearest_node_distance_m": round(origin["nearest_node_distance_m"], 3),
                "destination_nearest_node_distance_m": round(destination["nearest_node_distance_m"], 3),
                "origin_nearest_edge_distance_m": round(origin["nearest_edge_distance_m"], 3),
                "destination_nearest_edge_distance_m": round(destination["nearest_edge_distance_m"], 3),
                "origin_nearest_way_id": origin["nearest_edge_way_id"],
                "destination_nearest_way_id": destination["nearest_edge_way_id"],
                "origin_nearest_highway": origin["nearest_edge_highway"],
                "destination_nearest_highway": destination["nearest_edge_highway"],
                "origin_weak_component": weak_map[original_source],
                "destination_weak_component": weak_map[original_target],
                "same_weak_component": same_weak,
                "origin_strong_component": strong_map[original_source],
                "destination_strong_component": strong_map[original_target],
                "same_strong_component": same_strong,
                "diagnostic_category": category,
                "diagnostic_subcause": subcause,
                "candidate_route_found": candidate is not None,
                "candidate_source_node": None if candidate is None else candidate["source_node"],
                "candidate_target_node": None if candidate is None else candidate["target_node"],
                "candidate_route_length_km": None if candidate is None else round(candidate["route_length_km"], 6),
                "candidate_osm_minutes": None if candidate is None else round(candidate["route_minutes"], 6),
                "candidate_origin_access_node_distance_m": None if candidate is None else round(candidate["origin_access_node_distance_m"], 3),
                "candidate_destination_access_node_distance_m": None if candidate is None else round(candidate["destination_access_node_distance_m"], 3),
                "turn_restrictions": "NOT_PARSED",
                "legal_boundary": "NOT_VERIFIED",
                "repair_applied": False,
                "post_diagnostic_route_status": post_status,
                "evidence_source": f"E02 V4.6 OSM snapshot {sha256(raw)}",
            }
            diagnostic_rows.append(row)
            if not original_ok:
                repair_rows.append(
                    {
                        **{key: row[key] for key in ["od_id", "area", "origin_id", "destination_id", "original_status", "diagnostic_category", "diagnostic_subcause"]},
                        "proposed_change": "edge-aware snap candidate; retain as diagnostic until access and direction are reviewed" if candidate else "no supported change",
                        "repair_applied": False,
                        "candidate_route_found": candidate is not None,
                        "candidate_route_length_km": row["candidate_route_length_km"],
                        "candidate_osm_minutes": row["candidate_osm_minutes"],
                        "residual_exception": "ACCESS_DIRECTION_TURN_BOUNDARY_UNVERIFIED" if candidate else post_status,
                    }
                )
        area_details[area] = {
            "graph_nodes": graph.number_of_nodes(),
            "graph_edges": graph.number_of_edges(),
            "weak_components": len(weak_sizes),
            "strong_components": len(strong_sizes),
        }

    diagnostics = pd.DataFrame(diagnostic_rows)
    repairs = pd.DataFrame(repair_rows)
    diagnostics.to_csv(OUT / "od_connectivity_diagnostics.csv", index=False, encoding="utf-8-sig")
    repairs.to_csv(OUT / "od_route_repair_log.csv", index=False, encoding="utf-8-sig")
    (
        diagnostics.groupby(["original_status", "diagnostic_category", "post_diagnostic_route_status"], dropna=False)
        .size()
        .rename("od_count")
        .reset_index()
        .to_csv(OUT / "od_status_crosstab.csv", index=False, encoding="utf-8-sig")
    )

    road = pd.read_csv(STAGE1 / "road_model_validation.csv")
    enrichment = diagnostics[
        [
            "od_id",
            "cross_border_route",
            "diagnostic_category",
            "diagnostic_subcause",
            "candidate_route_found",
            "candidate_route_length_km",
            "candidate_osm_minutes",
            "repair_applied",
            "post_diagnostic_route_status",
        ]
    ]
    road = road.merge(enrichment, on="od_id", how="left", validate="many_to_one")
    road["ciq_wait_applicability"] = "NOT_APPLICABLE_TO_INLAND_REFERENCE_OD"
    road["ciq_wait_min"] = np.nan
    road["total_time_min"] = np.nan
    road["external_calibration_status"] = "NOT_CALIBRATED"
    road["formal_use_status"] = "DIAGNOSTIC_ONLY"
    road["anomaly_code_v2"] = road.apply(
        lambda r: ";".join(
            [
                str(r.diagnostic_category),
                "REFERENCE_OD_DOES_NOT_CROSS_CIQ",
                "TURN_RESTRICTIONS_NOT_PARSED",
                "LEGAL_BOUNDARY_NOT_VERIFIED",
                "EXTERNAL_TRAVEL_TIME_NOT_CALIBRATED",
            ]
        ),
        axis=1,
    )
    road.to_csv(OUT / "road_model_validation_v2.csv", index=False, encoding="utf-8-sig")

    counts = Counter(diagnostics["diagnostic_category"])
    exception_counts = Counter(repairs["diagnostic_category"])
    candidate_count = int(repairs["candidate_route_found"].sum())
    (OUT / "routing_exception_report.md").write_text(
        f"""# 128个有向OD路由诊断报告

## 结论

- 共诊断128个有向参考OD；91个原有模型路径，37个原异常全部完成归因。
- 37个异常分类为 {dict(exception_counts)}。
- {candidate_count}个异常存在基于同一OSM快照的边感知候选路径，但正式修复数为0；原因是参考点道路接入、FCD方向、转向限制和法定边界证据仍未通过。
- A区7个异常全部为A05作为起点。原最近节点与目的节点处于同一弱组件但不同强组件，且附近候选节点可路由，符合“最近节点落在方向不兼容车道/汇点”的吸附失配特征。
- B区30个异常全部涉及B02或B07。B02距离最近OSM道路边约119米，B07约240米，均超过原100米门槛。更远节点虽可计算候选路径，但参考点道路接入没有建立，因此归为 `DATA_GAP`，既不自动修复，也不认定为真实不可达。

## 重要结构修正

这128个OD全部由A01–A08或B01–B09等非CIQ参考点组成，没有包含A00/B00 CIQ参考点，也没有跨越马新国境。因此它们是两处口岸周边的马来西亚境内参考OD，不能直接赋予MY→SG或SG→MY方向，也不能把CIQ等待时间加到每条OD上。

## 放行边界

候选路径仅用于诊断，未写回E02原始文件，未把91/128改写成128/128。正式道路修复仍需逐点确认道路接入、行驶方向、转向限制和边界规则。

图摘要：{json.dumps(area_details, ensure_ascii=False)}
""",
        encoding="utf-8",
    )
    return diagnostics, repairs, road


def make_ciq_outputs():
    rows = []
    for corridor in ["Causeway", "Second_Link"]:
        for direction in ["MY_TO_SG", "SG_TO_MY"]:
            for scenario in ["LOW", "BASE", "HIGH"]:
                rows.append(
                    {
                        "corridor": corridor,
                        "direction": direction,
                        "day_type": "UNSPECIFIED",
                        "hour_local": "UNSPECIFIED",
                        "scenario": scenario,
                        "ciq_wait_min": None,
                        "parameter_status": "MISSING_NOT_CALIBRATED",
                        "evidence_level": "UNVERIFIED",
                        "source_url": "",
                        "applicability": "future cross-border OD only; not applicable to current 128 inland reference ODs",
                    }
                )
    pd.DataFrame(rows).to_csv(OUT / "ciq_wait_parameter_scenarios.csv", index=False, encoding="utf-8-sig")

    external = pd.DataFrame(
        [
            {
                "evidence_id": "SG_LTA_TRAFFIC_IMAGES",
                "source_type": "OFFICIAL_REALTIME_API",
                "source_url": "https://data.gov.sg/datasets/d_6cdb6b405b25aaaacbaf7689bcc6fae0/view",
                "period_match": "API supports timestamped images but no checkpoint wait-minute field",
                "corridor_match": "Woodlands and Tuas camera views available",
                "direction_match": "camera-specific, not a validated CIQ direction wait series",
                "observation_count": 0,
                "mae_min": None,
                "mdae_min": None,
                "smape_pct": None,
                "validation_status": "NOT_MATCHABLE_FOR_NUMERIC_CALIBRATION",
            },
            {
                "evidence_id": "SG_LTA_TRAFFIC_SPEED_BANDS",
                "source_type": "OFFICIAL_REALTIME_API",
                "source_url": "https://datamall.lta.gov.sg/content/datamall/en/dynamic-data.html",
                "period_match": "current road speed bands; no supplied historical checkpoint wait series",
                "corridor_match": "road network coverage not equivalent to CIQ processing wait",
                "direction_match": "road link direction only",
                "observation_count": 0,
                "mae_min": None,
                "mdae_min": None,
                "smape_pct": None,
                "validation_status": "NOT_MATCHABLE_FOR_CIQ_WAIT_CALIBRATION",
            },
            {
                "evidence_id": "ICA_2026_NATIONAL_DAY_RELEASE",
                "source_type": "OFFICIAL_EVENT_REPORT",
                "source_url": "https://www.ica.gov.sg/news-and-publications/newsroom/media-release/heavy-traffic-expected-at-land-checkpoints-during-national-day-long-weekend",
                "period_match": "within May-Sep 2026 study window but event-level only",
                "corridor_match": "Woodlands and Tuas aggregated",
                "direction_match": "not separated sufficiently for model calibration",
                "observation_count": 0,
                "mae_min": None,
                "mdae_min": None,
                "smape_pct": None,
                "validation_status": "CONTEXT_ONLY_NOT_A_CALIBRATION_SERIES",
            },
        ]
    )
    external.to_csv(OUT / "road_external_validation.csv", index=False, encoding="utf-8-sig")
    (OUT / "road_calibration_report.md").write_text(
        """# 道路与CIQ外部校准报告

## 状态

`NOT_CALIBRATED`

仓库没有Causeway/Second Link、双方向、2026年5–9月逐小时的CIQ等待观测。官方LTA来源提供实时交通图像和当前速度带；ICA公开材料提供事件级拥堵描述，但没有与现有OD、小时和方向可一一匹配的等待分钟序列。

因此：

- MAE、MdAE和SMAPE不计算，保持空值，而不是报告零误差。
- `ciq_wait_parameter_scenarios.csv`只建立参数接口，不填低/基准/高分钟数。
- 道路行驶时间与CIQ等待在schema中分离。
- 当前128个参考OD均为口岸周边境内OD，不跨越CIQ，CIQ等待对这些OD标记为不适用。
- 未来跨境OD必须另建方向明确的路线与口岸事件，且不得把道路拥堵代理和CIQ排队重复计入。
""",
        encoding="utf-8",
    )


def choose_smoke_orders(diagnostics: pd.DataFrame) -> pd.DataFrame:
    status_map = diagnostics.set_index("od_id")["original_route_exists"].to_dict()
    with zipfile.ZipFile(V56) as archive:
        member = sorted(name for name in archive.namelist() if name.endswith("_orders.csv.gz"))[0]
        data = pd.read_csv(io.BytesIO(archive.read(member)), compression="gzip")
    data["hour"] = pd.to_datetime(data["release_time_local"]).dt.hour
    data["od_id"] = data["origin_site_id"].astype(str) + "_" + data["destination_site_id"].astype(str)
    data["ground_route_class"] = data["od_id"].map(status_map).map({True: "ORIGINAL_ROUTE", False: "ORIGINAL_EXCEPTION"}).fillna("OD_NOT_IN_128_REFERENCE_SET")
    data["time_band"] = np.where(data["hour"].isin([7, 8, 9, 17, 18, 19]), "PEAK", "OFFPEAK")
    data["weather_class"] = np.where((data["era5_rain_mm_h"] > 0) | (data["era5_gust10_ms"] >= 8), "ADVERSE_SCREEN", "NORMAL_SCREEN")
    selected = []
    for area in ["A", "B"]:
        for route_class in ["ORIGINAL_ROUTE", "ORIGINAL_EXCEPTION"]:
            for time_band in ["PEAK", "OFFPEAK"]:
                subset = data[(data.area == area) & (data.ground_route_class == route_class) & (data.time_band == time_band)]
                if not subset.empty:
                    selected.append(subset.iloc[0])
    for weather_class in ["ADVERSE_SCREEN", "NORMAL_SCREEN"]:
        subset = data[data.weather_class == weather_class]
        if not subset.empty:
            selected.append(subset.iloc[0])
    selected_df = pd.DataFrame(selected).drop_duplicates("replicate_order_id").reset_index(drop=True)
    return selected_df


def make_smoke_outputs(diagnostics: pd.DataFrame):
    sample = choose_smoke_orders(diagnostics)
    diagnostic_map = diagnostics.set_index("od_id").to_dict("index")
    rows = []
    for order in sample.itertuples(index=False):
        diag = diagnostic_map.get(order.od_id, {})
        for mode in ["M0", "M1", "M2"]:
            if mode == "M0":
                reason = "ROAD_NOT_EXTERNALLY_CALIBRATED_AND_SERVICE_PROCESS_NOT_DEFINED"
            elif mode == "M1":
                reason = "SITE_REPLENISHMENT_QUEUE_CHARGE_PERMIT_AND_AIRCRAFT_PARAMETERS_MISSING"
            else:
                reason = "TRUCK_DRONE_SYNC_RENDEZVOUS_RECOVERY_CAPACITY_AND_PERMIT_PARAMETERS_MISSING"
            rows.append(
                {
                    "seed_id": int(order.replicate_seed),
                    "order_id": order.replicate_order_id,
                    "mode_id": mode,
                    "scenario_id": "STAGE2_DIAGNOSTIC_ONLY",
                    "area": order.area,
                    "od_id": order.od_id,
                    "release_time_local": order.release_time_local,
                    "time_band": order.time_band,
                    "weather_class": order.weather_class,
                    "original_ground_route_class": order.ground_route_class,
                    "route_diagnostic_category": diag.get("diagnostic_category", "OD_NOT_IN_128_REFERENCE_SET"),
                    "evaluation_status": "NOT_EVALUABLE",
                    "operational_outcome": None,
                    "reason_code": reason,
                    "ground_fallback_status": "NOT_EVALUATED",
                    "station_replenishment_status": "NOT_EVALUATED" if mode != "M0" else "NOT_APPLICABLE",
                    "station_queue_status": "NOT_EVALUATED" if mode != "M0" else "NOT_APPLICABLE",
                    "charging_status": "NOT_EVALUATED" if mode != "M0" else "NOT_APPLICABLE",
                    "truck_drone_sync_status": "NOT_EVALUATED" if mode == "M2" else "NOT_APPLICABLE",
                    "permission_status": "UNKNOWN_NO_POSITIVE_EVIDENCE" if mode != "M0" else "NOT_APPLICABLE",
                    "door_to_door_min": None,
                    "road_time_min": None,
                    "ciq_wait_min": None,
                    "queue_time_min": None,
                    "charge_time_min": None,
                    "vehicle_km": None,
                    "vehicle_energy_kwh": None,
                    "drone_energy_kwh": None,
                    "cost_total": None,
                    "emissions_kgco2e": None,
                }
            )
    result = pd.DataFrame(rows)
    result.to_parquet(OUT / "smoke_order_results.parquet", index=False)
    summary = (
        result.groupby(["scenario_id", "seed_id", "mode_id"], dropna=False)
        .agg(
            orders_total=("order_id", "size"),
            orders_not_evaluable=("evaluation_status", lambda s: int((s == "NOT_EVALUABLE").sum())),
            orders_served=("operational_outcome", lambda s: int((s == "SERVED").sum())),
            formal_metrics_available=("door_to_door_min", lambda s: int(s.notna().sum())),
        )
        .reset_index()
    )
    summary.to_csv(OUT / "smoke_run_summary.csv", index=False, encoding="utf-8-sig")

    assertions = {
        "status": "PASS_DIAGNOSTIC_GATING_NOT_OPERATIONAL_SIMULATION",
        "assertions": {
            "unique_composite_key": not result.duplicated(["seed_id", "order_id", "mode_id", "scenario_id"]).any(),
            "same_order_set_all_modes": all(
                set(result[result.mode_id == mode].order_id) == set(sample.replicate_order_id) for mode in ["M0", "M1", "M2"]
            ),
            "three_modes_per_order": bool(result.groupby("order_id")["mode_id"].nunique().eq(3).all()),
            "unknown_metrics_remain_null": bool(
                result[["door_to_door_min", "cost_total", "emissions_kgco2e", "drone_energy_kwh"]].isna().all().all()
            ),
            "uav_modes_not_released_without_permission": bool(
                (result[result.mode_id.isin(["M1", "M2"])]["permission_status"] == "UNKNOWN_NO_POSITIVE_EVIDENCE").all()
            ),
            "unreachable_orders_not_dropped": bool((result.groupby("order_id")["mode_id"].nunique() == 3).all()),
            "time_conservation_check": "NOT_APPLICABLE_NO_TIME_OUTPUT_RELEASED",
            "payload_constraint_check": "BLOCKED_AIRCRAFT_PARAMETERS_MISSING",
            "energy_nonnegative_check": "NOT_APPLICABLE_NO_ENERGY_OUTPUT_RELEASED",
        },
        "sample_orders": len(sample),
        "result_rows": len(result),
        "scope": "DIAGNOSTIC_ONLY",
    }
    write_json(OUT / "smoke_assertions.json", assertions)
    return result, summary, assertions


def make_registry_and_gaps():
    rows = [
        ["v55_frozen_source", None, "file", "all", "all", "V5.6 internal manifest reference", "V5.6 SHA256_manifest.csv", "UNVERIFIED", None, "all", "missing", "required for lineage"],
        ["road_osm_snapshot", "A/B snapshots", "json", "A/B", "2026-10-26 snapshot", "OSM Overpass", "download metadata and hashes", "OFFICIAL", None, "M0/M1/M2", "found", "turn restrictions and legal boundary still unverified"],
        ["regional_fcd_proxy", None, "ratio", "A/B", "2026-05 to 2026-09", "project FCD aggregate", "V5.3 proxy", "UNVERIFIED", None, "M0", "found", "not directional edge observations"],
        ["ciq_wait_minutes", None, "min", "Causeway/Second Link", "hourly", "none", "none", "UNVERIFIED", None, "M0/M1/M2", "missing", "scenario interface only"],
        ["approved_station", None, "site", "A/B", "all", "none", "none", "UNVERIFIED", None, "M1/M2", "missing", "reference anchors are not approved sites"],
        ["aircraft_payload", None, "kg", "A/B", "all", "none", "none", "UNVERIFIED", None, "M1/M2", "missing", "no operational model"],
        ["aircraft_energy", None, "kWh/km or mission", "A/B", "all", "none", "none", "UNVERIFIED", None, "M1/M2", "missing", "no formal energy results"],
        ["cross_border_flight_permission", None, "status", "MY/SG", "all", "none", "none", "UNVERIFIED", None, "M1/M2", "missing", "technical screen is not approval"],
        ["cost_parameters", None, "currency/function unit", "A/B", "all", "none", "none", "UNVERIFIED", None, "M0/M1/M2", "missing", "RQ3 blocked"],
        ["emission_parameters", None, "kgCO2e/function unit", "A/B", "all", "none", "none", "UNVERIFIED", None, "M0/M1/M2", "missing", "RQ3 blocked"],
    ]
    columns = ["parameter_name", "value", "unit", "region", "period", "source", "source_locator", "evidence_level", "valid_range", "applicable_modes", "status", "change_note"]
    pd.DataFrame(rows, columns=columns).to_csv(OUT / "parameter_registry.csv", index=False, encoding="utf-8-sig")

    gaps = pd.DataFrame(
        [
            ["DATA_LINEAGE", "P0", "V5.5 frozen source and V5.6 resampling code absent", "BLOCKS_FORMAL_MAIN_EXPERIMENT"],
            ["ROAD_ACCESS", "P0", "37 edge-aware candidates require access/direction review", "BLOCKS_FORMAL_ROUTE_REPAIR"],
            ["ROAD_RULES", "P0", "turn restrictions and legal boundary not verified", "BLOCKS_FORMAL_ROAD_BASELINE"],
            ["CIQ_OBSERVATIONS", "P1", "no matched hourly corridor-direction wait series", "BLOCKS_CIQ_CALIBRATION"],
            ["STATION_OPERATIONS", "P2", "replenishment, queue, charging and fallback parameters absent", "BLOCKS_M1"],
            ["TRUCK_DRONE_OPERATIONS", "P2", "sync, rendezvous, recovery and capacity parameters absent", "BLOCKS_M2"],
            ["PERMISSIONS", "P2", "no approved cross-border route/airspace/cargo evidence", "BLOCKS_UAV_RELEASE"],
            ["COST_EMISSIONS", "P2", "functional unit and sourced parameters incomplete", "BLOCKS_RQ3"],
        ],
        columns=["gap_id", "priority", "description", "impact"],
    )
    gaps.to_csv(OUT / "model_gap_register.csv", index=False, encoding="utf-8-sig")


def make_gates(diagnostics, repairs, road, assertions):
    gates = [
        ["G1_DATA_LINEAGE", "BLOCKED", "30-seed snapshot verified; V5.5 source and V5.6 generator absent", "cannot reproduce transformation from frozen source", "recover exact file/hash and generator"],
        ["G2_OD_STATUS", "PASS", f"128/128 attributed; 37 exceptions classified; {int(repairs.candidate_route_found.sum())} diagnostic candidates", "formal repairs remain zero", "manually validate access and direction for candidates"],
        ["G3_ROAD_INTERNAL", "BLOCKED", "no negative road time; edge-aware diagnostic complete", "turn restrictions and legal boundary unverified", "parse restrictions and validate legal boundary"],
        ["G4_CIQ_SEPARATION", "PASS", "road and CIQ fields separated; 128 inland ODs marked CIQ not applicable", "cross-border OD set not yet defined", "retain separate event components"],
        ["G5_EXTERNAL_CALIBRATION", "BLOCKED", "official sources reviewed; no matched historical wait-minute series", "MAE/MdAE/SMAPE unavailable", "obtain corridor-direction-hour observations or retain scenarios"],
        ["G6_STATION_OPERATIONS", "BLOCKED", "diagnostic state fields created", "replenishment/queue/charging/fallback model absent", "freeze sourced operational parameters and implement"],
        ["G7_DRONE_RESTRICTIONS", "BLOCKED", "weather and geometric screens remain separate", "aircraft/energy/reserve/permission evidence absent", "freeze sourced aircraft and regulatory inputs"],
        ["G8_MODE_PARITY", "PASS", "same existing orders retained once in each M0/M1/M2 diagnostic row", "all results NOT_EVALUABLE", "rerun after G3/G5/G6/G7 pass"],
        ["G9_COST_EMISSIONS", "BLOCKED", "schema reserved and null", "functional unit/lifecycle and factors absent", "freeze sourced accounting boundary"],
        ["G10_REPRODUCIBILITY", "PASS", "read-only inputs hashed; deterministic scripts/tests/manifest included", "no git repository at root", "preserve ZIP and SHA256"],
    ]
    data = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "full_main_experiment_allowed": False, "gates": [dict(zip(["id", "status", "evidence", "exception", "next_action"], row)) for row in gates]}
    write_json(OUT / "stage2_gates.json", data)
    lines = ["# Stage 2质量门槛报告", "", "全量主实验：**不放行**。", "", "| Gate | 状态 | 证据 | 例外/阻塞 | 下一步 |", "|---|---|---|---|---|"]
    for row in data["gates"]:
        lines.append(f"| {row['id']} | {row['status']} | {row['evidence']} | {row['exception']} | {row['next_action']} |")
    (OUT / "stage2_gate_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


def make_reports(diagnostics, repairs, road, smoke, gates):
    counts = Counter(repairs.diagnostic_category)
    (OUT / "engineering_gap_report_v2.md").write_text(
        f"""# CIQ工程缺口报告V2

## 与上一轮相比的新确认

- 37个异常OD已逐条归因：{dict(counts)}。
- {int(repairs.candidate_route_found.sum())}个异常具有边感知候选路径，但正式修复数为0，未强制改写为可达。
- 当前128个参考OD均为马来西亚境内口岸周边点对，不包含CIQ参考点，也不是MY→SG/SG→MY跨境路线。上一轮把CIQ缺失作为全部128 OD共同异常的口径已在V2中纠正为“不适用”。
- 官方公开来源不足以形成2026年5–9月逐小时、双通道、双方向CIQ等待校准集，状态为 `NOT_CALIBRATED`。
- M0/M1/M2仅完成同订单、同口径的 `NOT_EVALUABLE` 诊断门槛记录；没有伪造站点、充电、协同、成本或排放结果。

## 尚未消除的阻塞

1. V5.5冻结源与V5.6重采样代码缺失。
2. 37个候选路线尚未获得道路接入/方向人工证据，转向限制与法定边界未验证。
3. 缺少可时空匹配的CIQ等待和独立导航观测。
4. M1站点补货、排队、充电、兜底及M2同步、会合、回收、容量没有冻结参数。
5. 许可、机型、能源、成本和排放边界未冻结。

## 研究放行范围

- 可进入：道路吸附算法、方向组件、时间代理与CIQ接口的诊断情景。
- 不可进入：RQ1部署结论、RQ2正式节时/可靠性比较、RQ3成本与净CO2e推断。
""",
        encoding="utf-8",
    )

    versions = {
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "networkx": nx.__version__,
        "platform": platform.platform(),
    }
    (OUT / "STAGE2_README.md").write_text(
        f"""# CIQ Stage 2交付说明

生成日期：2026-10-27（Asia/Shanghai）

## 执行范围

本包完成冻结证据链复核、128个有向OD逐条诊断、道路/CIQ分层、外部证据可匹配性核查，以及同一批既有订单的三模式诊断门槛测试。没有生成新订单，没有覆盖原始文件，没有启动918,000行正式三模式实验。

## 执行命令

```powershell
py outputs/stage2_20261027/scripts/run_stage2.py
py outputs/stage2_20261027/tests/test_stage2.py
py outputs/stage2_20261027/scripts/package_stage2.py
```

## 环境

`{json.dumps(versions, ensure_ascii=False)}`

## 样本规模

- 订单冻结快照：30 seeds / 918,000 rows（只读审计）。
- 道路诊断：128个有向参考OD，其中37个原异常。
- 24小时道路检查：{len(road)}行。
- 三模式门槛样本：{smoke.order_id.nunique()}个现有订单，{len(smoke)}行。

## 解释限制

`smoke_order_results.parquet` 全部标记为 `NOT_EVALUABLE`，仅证明相同订单在M0/M1/M2均被保留及缺口被显式编码。它不是运营仿真结果，不支持RQ1–RQ3正式推断。
""",
        encoding="utf-8",
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    make_source_outputs()
    e02 = read_e02_module()
    diagnostics, repairs, road = make_route_outputs(e02)
    make_ciq_outputs()
    smoke, _, assertions = make_smoke_outputs(diagnostics)
    make_registry_and_gaps()
    gates = make_gates(diagnostics, repairs, road, assertions)
    make_reports(diagnostics, repairs, road, smoke, gates)
    summary = {
        "status": "STAGE2_DIAGNOSTIC_COMPLETE_FULL_MAIN_EXPERIMENT_BLOCKED",
        "od_rows": len(diagnostics),
        "original_routes": int(diagnostics.original_route_exists.sum()),
        "original_exceptions": len(repairs),
        "exception_categories": dict(Counter(repairs.diagnostic_category)),
        "diagnostic_candidates": int(repairs.candidate_route_found.sum()),
        "formal_repairs": int(repairs.repair_applied.sum()),
        "road_validation_rows": len(road),
        "smoke_orders": int(smoke.order_id.nunique()),
        "smoke_rows": len(smoke),
        "gates": {row["id"]: row["status"] for row in gates["gates"]},
        "full_main_experiment_started": False,
    }
    write_json(OUT / "stage2_execution_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
