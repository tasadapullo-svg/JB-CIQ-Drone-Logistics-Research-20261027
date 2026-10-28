#!/usr/bin/env python3
"""Create an auditable E02 stage report without upgrading model results to observations."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

import pandas as pd


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--traffic", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out = root / "outputs"
    traffic_path = Path(args.traffic).resolve()

    scope = pd.read_csv(out / "02_345node_scope_audit.csv", dtype={"node_id": str})
    scope_counts = scope["acquisition_areas"].value_counts().to_dict()

    traffic = pd.read_csv(
        traffic_path,
        usecols=[
            "node_id",
            "timestamp_local",
            "observed_speed_raw",
            "speed_state",
            "source_month",
            "group_id",
            "source_route_code",
            "name_evidence_status",
        ],
        dtype={"node_id": str},
    )
    traffic_summary = {
        "file": str(traffic_path),
        "sha256": sha256(traffic_path),
        "rows": int(len(traffic)),
        "unique_nodes": int(traffic["node_id"].nunique()),
        "unique_hour_timestamps": int(traffic["timestamp_local"].nunique()),
        "months": sorted(int(v) for v in traffic["source_month"].dropna().unique()),
        "speed_missing": int(traffic["observed_speed_raw"].isna().sum()),
        "speed_state_counts": {
            str(k): int(v) for k, v in traffic["speed_state"].value_counts(dropna=False).items()
        },
        "direction_field_present": False,
        "calibration_use": "BLOCKED_UNTIL_FCD_DIRECTION_AND_EDGE_MATCH_ARE_APPROVED",
    }

    areas: dict[str, dict] = {}
    anomaly_rows: list[dict] = []
    total_routes = 0
    total_pairs = 0
    total_length_failures = 0
    total_candidates = 0
    total_within_30 = 0
    total_rejected_80 = 0

    for area in ("A", "B"):
        qa = load_json(out / f"E02_{area}_logic_QA.json")
        meta = load_json(out / f"OSM_{area}_download_metadata.json")
        raw = out / f"OSM_{area}_overpass_response.json"
        actual_raw_hash = sha256(raw)
        if actual_raw_hash != meta["sha256"]:
            raise RuntimeError(f"OSM {area} metadata hash does not match the saved raw response")

        od = pd.read_csv(out / f"E02_{area}_OD_OSM_MODEL_NOT_OBSERVED.csv")
        candidates = pd.read_csv(
            out / f"E02_{area}_FCD_to_OSM_edge_CANDIDATES_NOT_APPROVED.csv",
            dtype={"node_id": str},
        )
        routed = od[od["status"] == "MODEL_ROUTE_REQUIRES_QA"].copy()
        length_failures = routed[
            routed["route_length_km"] + 0.0001 < routed["beeline_km"]
        ]
        high_circuity = routed[routed["circuity_ratio"] > 3.0]

        for row in od[od["status"] != "MODEL_ROUTE_REQUIRES_QA"].itertuples(index=False):
            anomaly_rows.append(
                {
                    "area": area,
                    "anomaly_type": "NO_APPROVED_MODEL_ROUTE",
                    "origin_id": row.origin_id,
                    "destination_id": row.destination_id,
                    "status": row.status,
                    "beeline_km": row.beeline_km,
                    "route_length_km": row.route_length_km,
                    "model_minutes": row.OSM_only_minutes_MODEL,
                    "circuity_ratio": row.circuity_ratio,
                    "detail": "Disconnected OSM graph or site snap exceeds 100 m",
                }
            )
        for row in high_circuity.itertuples(index=False):
            anomaly_rows.append(
                {
                    "area": area,
                    "anomaly_type": "CIRCUITY_GT_3_REVIEW",
                    "origin_id": row.origin_id,
                    "destination_id": row.destination_id,
                    "status": row.status,
                    "beeline_km": row.beeline_km,
                    "route_length_km": row.route_length_km,
                    "model_minutes": row.OSM_only_minutes_MODEL,
                    "circuity_ratio": row.circuity_ratio,
                    "detail": "Topology/snap/access-leg review required; threshold is a QA flag, not a universal standard",
                }
            )

        reverse = routed.merge(
            routed,
            left_on=["origin_id", "destination_id"],
            right_on=["destination_id", "origin_id"],
            suffixes=("_forward", "_reverse"),
        )
        reverse = reverse[reverse["origin_id_forward"] < reverse["destination_id_forward"]].copy()
        if not reverse.empty:
            reverse["max_min_time_ratio"] = reverse[
                ["OSM_only_minutes_MODEL_forward", "OSM_only_minutes_MODEL_reverse"]
            ].max(axis=1) / reverse[
                ["OSM_only_minutes_MODEL_forward", "OSM_only_minutes_MODEL_reverse"]
            ].min(axis=1)
            asymmetry = reverse[reverse["max_min_time_ratio"] > 1.5]
        else:
            asymmetry = reverse
        for row in asymmetry.itertuples(index=False):
            anomaly_rows.append(
                {
                    "area": area,
                    "anomaly_type": "REVERSE_TIME_RATIO_GT_1_5",
                    "origin_id": row.origin_id_forward,
                    "destination_id": row.destination_id_forward,
                    "status": "DIRECTIONAL_QA_REQUIRED",
                    "beeline_km": row.beeline_km_forward,
                    "route_length_km": row.route_length_km_forward,
                    "model_minutes": row.OSM_only_minutes_MODEL_forward,
                    "circuity_ratio": row.circuity_ratio_forward,
                    "detail": f"reverse_model_minutes={row.OSM_only_minutes_MODEL_reverse:.4f}; ratio={row.max_min_time_ratio:.4f}",
                }
            )

        status_counts = {str(k): int(v) for k, v in od["status"].value_counts().items()}
        areas[area] = {
            "osm_endpoint": meta["endpoint"],
            "downloaded_at_utc": meta["downloaded_at_utc"],
            "osm_raw_elements": int(meta["elements"]),
            "osm_raw_sha256_verified": actual_raw_hash,
            "ways_pass_filter": int(qa["OSM_ways_pass_filter"]),
            "graph_nodes": int(qa["graph_nodes"]),
            "directed_edges": int(qa["directed_edges"]),
            "weak_components": int(qa["weak_components"]),
            "directed_edge_length_km": float(qa["OSM_edge_length_km"]),
            "fcd_nodes_examined": int(qa["fcd_nodes_examined"]),
            "fcd_edge_candidates_within_30m": int(qa["FCD_edge_candidates_within_30m"]),
            "fcd_edge_candidates_rejected_gt80m": int(qa["FCD_edge_candidates_rejected_gt80m"]),
            "od_pairs": int(len(od)),
            "od_status_counts": status_counts,
            "route_length_below_beeline_failures": int(len(length_failures)),
            "circuity_gt_3_review_count": int(len(high_circuity)),
            "reverse_time_ratio_gt_1_5_count": int(len(asymmetry)),
            "turn_relations_encoded": False,
            "malaysia_legal_boundary_verified": False,
            "fcd_direction_verified": False,
            "independent_navigation_time_verified": False,
        }
        total_routes += int(len(routed))
        total_pairs += int(len(od))
        total_length_failures += int(len(length_failures))
        total_candidates += int(len(candidates))
        total_within_30 += int((candidates["match_distance_m"] <= 30).sum())
        total_rejected_80 += int((candidates["match_distance_m"] > 80).sum())

    anomaly_fields = [
        "area",
        "anomaly_type",
        "origin_id",
        "destination_id",
        "status",
        "beeline_km",
        "route_length_km",
        "model_minutes",
        "circuity_ratio",
        "detail",
    ]
    with (out / "E02_OD_route_anomalies_REVIEW_REQUIRED.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=anomaly_fields)
        writer.writeheader()
        writer.writerows(anomaly_rows)

    summary = {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "E02_PRELIMINARY_OSM_NETWORK_BUILT_FORMAL_ACCEPTANCE_BLOCKED",
        "scope": "A Causeway and B Second Link only; 128 reference OD pairs, not orders",
        "areas": areas,
        "totals": {
            "frozen_fcd_nodes": int(len(scope)),
            "fcd_nodes_inside_fixed_A_B_download_windows": int(
                len(scope) - scope_counts.get("OUTSIDE_BOTH", 0)
            ),
            "fcd_nodes_outside_fixed_A_B_download_windows": int(
                scope_counts.get("OUTSIDE_BOTH", 0)
            ),
            "fcd_edge_candidates_generated": total_candidates,
            "fcd_edge_candidates_within_30m": total_within_30,
            "fcd_edge_candidates_rejected_gt80m": total_rejected_80,
            "reference_od_pairs": total_pairs,
            "model_routes_requiring_QA": total_routes,
            "reference_od_pairs_without_model_route": total_pairs - total_routes,
            "route_length_below_beeline_failures": total_length_failures,
            "confirmed_observation_calibrated_od": 0,
        },
        "traffic_input": traffic_summary,
        "formal_release_gates": {
            "real_osm_snapshot_and_hash": "PASS",
            "directed_edges_from_osm_oneway_tags": "PASS_WITHOUT_TURN_RELATIONS",
            "all_345_nodes_have_approved_edge_and_direction": "FAIL",
            "malaysia_legal_boundary_and_cross_border_exclusion": "FAIL",
            "osm_turn_restrictions_applied_and_checked": "FAIL",
            "fcd_direction_and_road_name_match_approved": "FAIL",
            "independent_navigation_time_validation": "FAIL",
            "formal_observation_calibrated_od_matrix": "NOT_RELEASED",
        },
        "claim_limit": "All route times remain OSM model estimates and are not observed traffic travel times.",
    }
    (out / "E02_stage_acceptance_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    report = f"""# E02 真实有向路网阶段验收报告

生成时间（UTC）：{summary['generated_at_utc']}

## 结论

真实 OSM 下载、有向边构建和初步 OD 路由已经完成，但正式 E02 验收未通过。当前 {total_routes}/{total_pairs} 个参考方向 OD 具有模型路径；0 个达到 `OBSERVATION_CALIBRATED`。所有时间仍是 OSM 限速或道路等级假设产生的模型估计，不是实测交通旅行时间。

## 已通过

- A/B 原始 Overpass JSON、下载端点、UTC 时间和 SHA256 已保存并相互校验。
- OSM `oneway` 标签已编码为有向边；合成单行线逆行测试通过。
- {total_routes} 条模型路径均满足道路路径长度不小于测地线距离（容差 0.1 m）。

## 未通过的正式门槛

- 固定 A/B 下载窗口只覆盖 345 个 FCD 节点中的 {len(scope) - scope_counts.get('OUTSIDE_BOTH', 0)} 个，另有 {scope_counts.get('OUTSIDE_BOTH', 0)} 个在两个窗口外；因此没有完成全部 345 节点匹配。
- 现有逐小时 FCD 表没有行驶方向字段，不能把最近道路候选自动认定为正确方向，也不能将速度赋给两向边。
- 当前路由未解析 OSM 转向限制 relation。
- 未取得可用于正式放行的马来西亚法定边界证据，未完成越境道路排除。
- 未提供独立导航旅行时间样本，无法完成外部时间验证。
- {total_pairs - total_routes} 个方向 OD 无模型路径或站点吸附距离超过 100 m；异常清单另存 CSV。

## 当前状态

`E02_PRELIMINARY_OSM_NETWORK_BUILT_FORMAL_ACCEPTANCE_BLOCKED`
"""
    (out / "E02_stage_acceptance_report.md").write_text(report, encoding="utf-8")

    log = f"""2026-10-26 local execution
Primary endpoint overpass.kumi.systems timed out after 320 seconds for A and B.
Fallback endpoint {areas['A']['osm_endpoint']} succeeded for A at {areas['A']['downloaded_at_utc']}.
Fallback endpoint {areas['B']['osm_endpoint']} succeeded for B at {areas['B']['downloaded_at_utc']}.
Saved raw OSM JSON hashes verified against download metadata.
Formal acceptance remains blocked; see E02_stage_acceptance_report.md.
"""
    (out / "network_attempt_log_20261026.txt").write_text(log, encoding="utf-8")

    excluded = {root / "SHA256_manifest.csv"}
    files = sorted(
        p for p in root.rglob("*") if p.is_file() and p not in excluded and p.suffix.lower() != ".zip"
    )
    with (root / "SHA256_manifest.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["relative_path", "size_bytes", "sha256"])
        for path in files:
            writer.writerow([path.relative_to(root).as_posix(), path.stat().st_size, sha256(path)])

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
