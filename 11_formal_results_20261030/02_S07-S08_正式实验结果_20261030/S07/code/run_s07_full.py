#!/usr/bin/env python3
"""CIQ V5 S07 real-data acceptance and conditional fusion.

All source files are read-only. Derived files are written only below the supplied
output directory. Current OSM and directionless FCD are explicitly retained as
conditional proxies rather than represented as observed directional traffic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import openpyxl
import osmnx as ox
import pandas as pd
import pyproj
import scipy
from pyproj import Transformer
from scipy.spatial import cKDTree


HOURS = {5: 744, 6: 720, 7: 744, 8: 744, 9: 720}
STUDY_START = pd.Timestamp("2026-05-01T00:00:00+08:00")
STUDY_END = pd.Timestamp("2026-10-01T00:00:00+08:00")
FCD_UNIT_STATUS = "KMH_CONDITIONAL_TOMTOM_DEFAULT_NOT_SAVED_IN_RAW_REQUEST"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def sheet_df(workbook, name: str) -> pd.DataFrame:
    rows = workbook[name].iter_rows(values_only=True)
    header = [str(x).strip() if x is not None else "" for x in next(rows)]
    return pd.DataFrame(rows, columns=header).dropna(how="all")


def parse_tz(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="mixed", utc=True, errors="coerce")


def scalar(v):
    if isinstance(v, (list, tuple)):
        return v[0] if v else None
    return v


def speed_default(highway) -> float:
    h = str(scalar(highway) or "").lower()
    return {
        "motorway": 90.0, "motorway_link": 60.0, "trunk": 70.0,
        "trunk_link": 50.0, "primary": 60.0, "primary_link": 45.0,
        "secondary": 50.0, "secondary_link": 40.0, "tertiary": 40.0,
        "tertiary_link": 35.0, "residential": 30.0, "unclassified": 30.0,
        "living_street": 15.0, "service": 20.0,
    }.get(h, 30.0)


def edge_speed(data: dict) -> tuple[float, str]:
    for field in ("speed_kph", "maxspeed"):
        raw = scalar(data.get(field))
        if raw is None:
            continue
        try:
            text = str(raw).lower().replace("km/h", "").strip()
            if "mph" in text:
                val = float(text.replace("mph", "").strip()) * 1.609344
            else:
                val = float(text.split(";")[0])
            if math.isfinite(val) and val > 0:
                return val, f"OSM_{field.upper()}"
        except (ValueError, TypeError):
            pass
    return speed_default(data.get("highway")), "HIGHWAY_CLASS_ASSUMPTION"


def audit_weather(weather_dir: Path, out: Path):
    weather_frames, grid_frames, qa, boundary_rows, source_rows = [], [], [], [], []
    for month, hours in HOURS.items():
        path = weather_dir / f"JB_SG_Weather_2026_{month:02d}.xlsx"
        manifest = path.with_suffix(".manifest.json")
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        wh = sheet_df(wb, "Weather_Hourly")
        era = sheet_df(wb, "ERA5_Hourly")
        registry = sheet_df(wb, "Source_Registry")
        wb.close()

        wh["timestamp_utc"] = parse_tz(wh["timestamp_hour_start_utc"])
        wh["timestamp_local"] = wh["timestamp_utc"].dt.tz_convert("Asia/Kuala_Lumpur")
        era["timestamp_end_utc"] = parse_tz(era["timestamp_utc"])
        era["interval_start_utc"] = parse_tz(era["rain_period_start_sgt"])
        era["interval_end_utc"] = parse_tz(era["rain_period_end_sgt"])
        era["timestamp_local"] = era["interval_start_utc"].dt.tz_convert("Asia/Kuala_Lumpur")

        in_month = (wh["timestamp_local"].dt.year == 2026) & (wh["timestamp_local"].dt.month == month)
        dup = int(wh.duplicated(["point_id", "timestamp_utc"]).sum())
        numeric = [
            "era5_wind10_ms", "era5_wind100_ms", "era5_dir10_deg", "era5_dir100_deg",
            "era5_gust10_ms", "era5_temp_c", "era5_rh_pct", "era5_precip_1h_mm",
            "era5_rain_1h_mm", "nasa_precip_mm_per_hour", "nasa_wind10_ms",
            "nasa_dir10_deg", "nasa_temp_c", "nasa_rh_pct",
        ]
        missing = {c: int(pd.to_numeric(wh[c], errors="coerce").isna().sum()) for c in numeric}
        physical = {
            "negative_wind": int((pd.to_numeric(wh["era5_wind10_ms"], errors="coerce") < 0).sum()),
            "negative_rain": int((pd.to_numeric(wh["era5_precip_1h_mm"], errors="coerce") < 0).sum()),
            "direction_outside_0_360": int((~pd.to_numeric(wh["era5_dir10_deg"], errors="coerce").between(0, 360)).sum()),
            "rh_outside_0_100": int((~pd.to_numeric(wh["era5_rh_pct"], errors="coerce").between(0, 100)).sum()),
        }

        # Weather_Hourly t represents [t,t+1h); match it to the raw ERA5 accumulated interval.
        m = wh[["point_id", "timestamp_utc", "era5_precip_1h_mm", "era5_rain_1h_mm"]].merge(
            era[["point_id", "interval_start_utc", "interval_end_utc", "precipitation", "rain"]],
            left_on=["point_id", "timestamp_utc"], right_on=["point_id", "interval_start_utc"], how="left",
        )
        precip_match = np.isclose(pd.to_numeric(m["era5_precip_1h_mm"], errors="coerce"),
                                  pd.to_numeric(m["precipitation"], errors="coerce"), equal_nan=False)
        rain_match = np.isclose(pd.to_numeric(m["era5_rain_1h_mm"], errors="coerce"),
                                pd.to_numeric(m["rain"], errors="coerce"), equal_nan=False)

        used = set(zip(wh["point_id"].astype(str), wh["timestamp_utc"].astype(str)))
        extra = era[["point_id", "timestamp_end_utc", "interval_start_utc", "interval_end_utc",
                     "latitude_returned", "longitude_returned", "precipitation", "rain"]].copy()
        extra["used_weather_key"] = [
            (str(p), str(t)) in used for p, t in zip(extra["point_id"], extra["interval_start_utc"])
        ]
        extra = extra[~extra["used_weather_key"]]
        extra["month_file"] = month
        boundary_rows.append(extra)

        grid = era[(era["interval_start_utc"] >= STUDY_START.tz_convert("UTC")) &
                   (era["interval_start_utc"] < STUDY_END.tz_convert("UTC"))].copy()
        grid["grid_id"] = grid.apply(
            lambda r: f"ERA5_{float(r['latitude_returned']):.2f}_{float(r['longitude_returned']):.2f}", axis=1)
        grid_numeric = ["wind_speed_10m", "wind_speed_100m", "wind_direction_10m", "wind_direction_100m",
                        "wind_gusts_10m", "temperature_2m", "relative_humidity_2m", "precipitation", "rain"]
        spread = grid.groupby(["grid_id", "interval_start_utc"])[grid_numeric].agg(lambda x: float(pd.to_numeric(x, errors="coerce").max() - pd.to_numeric(x, errors="coerce").min()))
        max_grid_spread = float(np.nanmax(spread.to_numpy(dtype=float))) if len(spread) else float("nan")
        grouped = grid.groupby(["grid_id", "interval_start_utc", "latitude_returned", "longitude_returned"], as_index=False)[grid_numeric].mean(numeric_only=True)
        grouped["source_class"] = "ERA5_REANALYSIS_SHARED_GRID_PROXY"
        grid_frames.append(grouped)

        expected = 4 * hours
        status = "PASS" if (
            len(wh) == expected and in_month.all() and dup == 0 and wh["timestamp_utc"].notna().all()
            and all(v == 0 for v in physical.values()) and precip_match.all() and rain_match.all()
        ) else "HOLD"
        qa.append({
            "month": month, "xlsx_path": str(path), "xlsx_bytes": path.stat().st_size,
            "xlsx_sha256": sha256(path), "manifest_path": str(manifest),
            "manifest_sha256": sha256(manifest), "weather_rows": int(len(wh)),
            "expected_weather_rows": expected, "era5_raw_rows": int(len(era)),
            "era5_extra_boundary_rows": int(len(extra)), "point_count": int(wh["point_id"].nunique()),
            "unique_hours": int(wh["timestamp_utc"].nunique()), "duplicate_point_hours": dup,
            "outside_target_month": int((~in_month).sum()), "missing_by_field": json.dumps(missing),
            "physical_qa": json.dumps(physical), "precip_interval_matches": int(precip_match.sum()),
            "rain_interval_matches": int(rain_match.sum()), "max_same_grid_value_spread": max_grid_spread,
            "status": status,
        })
        wh["source_file"] = path.name
        weather_frames.append(wh)
        registry["month_file"] = month
        source_rows.append(registry)

    weather = pd.concat(weather_frames, ignore_index=True)
    grid_hour = pd.concat(grid_frames, ignore_index=True).drop_duplicates(["grid_id", "interval_start_utc"])
    boundary = pd.concat(boundary_rows, ignore_index=True)
    sources = pd.concat(source_rows, ignore_index=True)
    weather.to_parquet(out / "weather_hourly_2026_05_09.parquet", index=False)
    grid_hour.to_parquet(out / "era5_grid_hourly_2026_05_09.parquet", index=False)
    pd.DataFrame(qa).to_csv(out / "QA_WEATHER_MONTHLY.csv", index=False, encoding="utf-8-sig")
    boundary.to_csv(out / "QA_ERA5_BOUNDARY_ROWS.csv", index=False, encoding="utf-8-sig")
    sources.to_csv(out / "WEATHER_SOURCE_REGISTRY.csv", index=False, encoding="utf-8-sig")
    return weather, grid_hour, pd.DataFrame(qa), boundary


def audit_fcd(path: Path, out: Path):
    fcd = pd.read_csv(path, compression="gzip", low_memory=False)
    fcd["timestamp_utc"] = parse_tz(fcd["timestamp_local"])
    speed = pd.to_numeric(fcd["observed_speed_raw"], errors="coerce")
    fcd["observed_speed_kmh_conditional"] = speed
    fcd["speed_unit_status"] = FCD_UNIT_STATUS
    derived = np.where(speed.isna(), "MISSING", np.where(speed > 0, "POSITIVE", "NONPOSITIVE"))
    fcd["speed_state_recomputed"] = derived
    fcd["direction_status"] = "UNDIRECTED_SPEED_PROXY"
    dup = int(fcd.duplicated(["node_id", "timestamp_utc"]).sum())
    per_month = fcd.groupby("source_month")["speed_state_recomputed"].value_counts().unstack(fill_value=0)
    qa = {
        "path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path),
        "rows": int(len(fcd)), "expected_rows": 345 * 3672, "unique_nodes": int(fcd["node_id"].nunique()),
        "unique_hours": int(fcd["timestamp_utc"].nunique()), "duplicate_node_hours": dup,
        "invalid_timestamps": int(fcd["timestamp_utc"].isna().sum()),
        "positive_speed": int((derived == "POSITIVE").sum()), "missing_speed": int((derived == "MISSING").sum()),
        "nonpositive_speed": int((derived == "NONPOSITIVE").sum()), "unit_status": FCD_UNIT_STATUS,
        "direction_status": "UNDIRECTED_SPEED_PROXY",
    }
    qa["status"] = "PASS_STRUCTURE_CONDITIONAL_PROXY" if (
        qa["rows"] == qa["expected_rows"] and qa["unique_nodes"] == 345 and qa["unique_hours"] == 3672
        and dup == 0 and qa["invalid_timestamps"] == 0
    ) else "HOLD"
    fcd.to_parquet(out / "fcd_hourly_345node_2026_05_09.parquet", index=False)
    pd.DataFrame([qa]).to_csv(out / "QA_FCD_FULL.csv", index=False, encoding="utf-8-sig")
    per_month.to_csv(out / "QA_FCD_MONTHLY_SPEED_STATES.csv", encoding="utf-8-sig")
    return fcd, qa


def audit_v5(gpkg: Path, master: pd.DataFrame, out: Path):
    layers = ["A_NODES", "B_NODES", "C_NODES", "A_PORT_6_NODES", "A_GROUND_GATEWAY"]
    frames = []
    for layer in layers:
        d = gpd.read_file(gpkg, layer=layer)
        id_col = "id" if "id" in d.columns else "node_id"
        zone_values = d["zone"].astype(str) if "zone" in d.columns else pd.Series(["A"] * len(d), index=d.index)
        frames.append(pd.DataFrame({"node_id": d[id_col].astype(str), "zone": zone_values,
                                    "gpkg_lon": d.geometry.x, "gpkg_lat": d.geometry.y, "layer": layer}))
    actual = pd.concat(frames, ignore_index=True)
    merged = master.merge(actual, on=["node_id", "zone"], how="outer", indicator=True)
    tr = Transformer.from_crs("EPSG:4326", "EPSG:32648", always_xy=True)
    good = merged["_merge"].eq("both")
    x1, y1 = tr.transform(merged.loc[good, "longitude_E"].to_numpy(), merged.loc[good, "latitude_N"].to_numpy())
    x2, y2 = tr.transform(merged.loc[good, "gpkg_lon"].to_numpy(), merged.loc[good, "gpkg_lat"].to_numpy())
    merged.loc[good, "coordinate_difference_m"] = np.hypot(np.asarray(x1)-np.asarray(x2), np.asarray(y1)-np.asarray(y2))
    merged.to_csv(out / "V5_GPKG_68_NODE_CROSSCHECK.csv", index=False, encoding="utf-8-sig")
    qa = {"gpkg": str(gpkg), "gpkg_sha256": sha256(gpkg), "active_points": int(len(actual)),
          "zones": actual["zone"].value_counts().to_dict(), "missing_or_extra": int((merged["_merge"] != "both").sum()),
          "max_coordinate_difference_m": float(merged["coordinate_difference_m"].max()),
          "status": "PASS" if len(actual) == 68 and (merged["_merge"] == "both").all() and merged["coordinate_difference_m"].max() < 0.05 else "HOLD"}
    write_json(out / "QA_V5_GPKG.json", qa)
    return qa


def weather_to_nodes(master: pd.DataFrame, grid_hour: pd.DataFrame, out: Path):
    grids = grid_hour[["grid_id", "latitude_returned", "longitude_returned"]].drop_duplicates().copy()
    tr = Transformer.from_crs("EPSG:4326", "EPSG:32648", always_xy=True)
    gx, gy = tr.transform(grids["longitude_returned"].to_numpy(), grids["latitude_returned"].to_numpy())
    tree = cKDTree(np.c_[gx, gy])
    nx_, ny_ = tr.transform(master["longitude_E"].to_numpy(), master["latitude_N"].to_numpy())
    dist, idx = tree.query(np.c_[nx_, ny_])
    assign = master[["node_id", "zone", "longitude_E", "latitude_N"]].copy()
    assign["grid_id"] = grids.iloc[idx]["grid_id"].to_numpy()
    assign["grid_lat"] = grids.iloc[idx]["latitude_returned"].to_numpy()
    assign["grid_lon"] = grids.iloc[idx]["longitude_returned"].to_numpy()
    assign["grid_distance_m"] = dist
    assign["grid_gt10km_warning"] = dist > 10000
    assign["spatial_status"] = np.where(dist > 10000, "WARNING_GT10KM_PROXY", "PROXY_WITHIN_10KM")
    assign.to_csv(out / "V5_68_NODE_WEATHER_GRID_ASSIGNMENT.csv", index=False, encoding="utf-8-sig")
    node_hour = assign.merge(grid_hour, on="grid_id", how="left")
    node_hour["weather_evidence"] = "ERA5_REANALYSIS_TWO_SHARED_GRIDS_NOT_STATIONS"
    node_hour.to_parquet(out / "V5_249696_NODE_HOUR_WEATHER.parquet", index=False)
    zone = assign.groupby("zone").agg(nodes=("node_id", "size"), nodes_gt10km=("grid_gt10km_warning", "sum"),
                                       max_distance_m=("grid_distance_m", "max"), mean_distance_m=("grid_distance_m", "mean")).reset_index()
    zone.to_csv(out / "QA_WEATHER_SPATIAL_BY_ZONE.csv", index=False, encoding="utf-8-sig")
    return assign, node_hour, zone


def largest_scc(G):
    component = max(nx.strongly_connected_components(G), key=len)
    return G.subgraph(component).copy()


def snap_points_to_graph(G, points: pd.DataFrame, id_col: str, lon_col: str, lat_col: str):
    tr = Transformer.from_crs("EPSG:4326", "EPSG:32648", always_xy=True)
    graph_ids = np.array(list(G.nodes), dtype=object)
    glon = np.array([float(G.nodes[n]["x"]) for n in graph_ids])
    glat = np.array([float(G.nodes[n]["y"]) for n in graph_ids])
    gx, gy = tr.transform(glon, glat)
    tree = cKDTree(np.c_[gx, gy])
    px, py = tr.transform(points[lon_col].to_numpy(), points[lat_col].to_numpy())
    dist, idx = tree.query(np.c_[px, py])
    result = points[[id_col]].copy()
    result["osm_node_id"] = graph_ids[idx]
    result["snap_distance_m"] = dist
    return result


def select_edge(G, u, v):
    values = G.get_edge_data(u, v)
    if not values:
        raise KeyError((u, v))
    key, data = min(values.items(), key=lambda kv: float(kv[1].get("length", float("inf"))))
    return key, data


def audit_road(graphml: Path, master: pd.DataFrame, fcd: pd.DataFrame, out: Path):
    G = ox.load_graphml(graphml)
    Gs = largest_scc(G)
    snaps = snap_points_to_graph(Gs, master, "node_id", "longitude_E", "latitude_N")
    access = master[["node_id", "zone", "name", "longitude_E", "latitude_N", "ground_gate_approved"]].merge(snaps, on="node_id")
    access["candidate_status"] = np.where(access["snap_distance_m"] <= 100, "CONDITIONAL_ACCESS_WITHIN_100M",
                                           "HOLD_ACCESS_GT100M")
    access["legal_access_verified"] = "NO"
    access["turn_restrictions_verified"] = "NO"
    access.to_csv(out / "V5_68_NODE_ROAD_ACCESS_CANDIDATES.csv", index=False, encoding="utf-8-sig")

    fcd_nodes = fcd[["node_id", "latitude", "longitude", "group_id", "source_route_code"]].drop_duplicates("node_id")
    fcd_snap = snap_points_to_graph(Gs, fcd_nodes, "node_id", "longitude", "latitude")
    fcd_map = fcd_nodes.merge(fcd_snap, on="node_id")
    fcd_map["direction_status"] = "UNDIRECTED_SPEED_PROXY"
    fcd_map.to_csv(out / "FCD_345_TO_OSM_NODE_MAP.csv", index=False, encoding="utf-8-sig")

    node_to_osm = dict(zip(access["node_id"], access["osm_node_id"]))
    relevant = sorted(set(master["node_id"]))
    od_rows, edge_rows = [], {}
    for origin in relevant:
        source = node_to_osm[origin]
        lengths, paths = nx.single_source_dijkstra(Gs, source=source, weight="length")
        for destination in relevant:
            if origin == destination:
                od_rows.append({"origin_node_id": origin, "destination_node_id": destination,
                                "road_distance_km": 0.0, "freeflow_minutes": 0.0,
                                "path_edge_ids_json": "[]", "route_status": "CONDITIONAL_OSM_ROUTE"})
                continue
            target = node_to_osm[destination]
            if target not in paths:
                od_rows.append({"origin_node_id": origin, "destination_node_id": destination,
                                "road_distance_km": np.nan, "freeflow_minutes": np.nan,
                                "path_edge_ids_json": "[]", "route_status": "HOLD_DIRECTED_DISCONNECTED"})
                continue
            path = paths[target]
            ids, total_m, total_min = [], 0.0, 0.0
            for u, v in zip(path[:-1], path[1:]):
                k, data = select_edge(Gs, u, v)
                edge_id = f"{u}|{v}|{k}"
                length = float(data.get("length", 0.0))
                speed, speed_source = edge_speed(data)
                total_m += length
                total_min += length / 1000.0 / speed * 60.0
                ids.append(edge_id)
                if edge_id not in edge_rows:
                    edge_rows[edge_id] = {"edge_id": edge_id, "u": str(u), "v": str(v), "key": str(k),
                        "length_m": length, "osm_speed_kmh": speed, "speed_source": speed_source,
                        "highway": str(data.get("highway", "")), "osmid": str(data.get("osmid", "")),
                        "oneway": str(data.get("oneway", "")),
                        "mid_lon": (float(Gs.nodes[u]["x"]) + float(Gs.nodes[v]["x"])) / 2,
                        "mid_lat": (float(Gs.nodes[u]["y"]) + float(Gs.nodes[v]["y"])) / 2}
            od_rows.append({"origin_node_id": origin, "destination_node_id": destination,
                            "road_distance_km": total_m / 1000.0, "freeflow_minutes": total_min,
                            "path_edge_ids_json": json.dumps(ids), "route_status": "CONDITIONAL_OSM_ROUTE"})
    od = pd.DataFrame(od_rows)
    edges = pd.DataFrame(edge_rows.values())

    tr = Transformer.from_crs("EPSG:4326", "EPSG:32648", always_xy=True)
    fx, fy = tr.transform(fcd_nodes["longitude"].to_numpy(), fcd_nodes["latitude"].to_numpy())
    ex, ey = tr.transform(edges["mid_lon"].to_numpy(), edges["mid_lat"].to_numpy())
    dist, idx = cKDTree(np.c_[fx, fy]).query(np.c_[ex, ey])
    edges["fcd_node_id"] = fcd_nodes.iloc[idx]["node_id"].to_numpy()
    edges["fcd_group_id"] = fcd_nodes.iloc[idx]["group_id"].to_numpy()
    edges["fcd_distance_m"] = dist
    edges["fcd_direction_status"] = "UNDIRECTED_SPEED_PROXY_APPLIED_BOTH_DIRECTIONS"
    edges.to_parquet(out / "OSM_ROUTE_EDGES_WITH_FCD_PROXY.parquet", index=False)
    od.to_parquet(out / "V5_68_DIRECTED_OD_MATRIX_AND_PATHS.parquet", index=False)

    road_qa = {
        "graphml": str(graphml), "graphml_sha256": sha256(graphml), "retrieval_basis": "CURRENT_OSM_OVERPASS_ODBL",
        "graph_nodes": G.number_of_nodes(), "graph_directed_arcs": G.number_of_edges(),
        "weak_components": nx.number_weakly_connected_components(G), "largest_scc_nodes": Gs.number_of_nodes(),
        "largest_scc_arcs": Gs.number_of_edges(), "v5_nodes": int(len(access)),
        "nodes_within_100m": int((access["snap_distance_m"] <= 100).sum()),
        "nodes_over_100m": int((access["snap_distance_m"] > 100).sum()),
        "max_snap_distance_m": float(access["snap_distance_m"].max()),
        "directed_od_rows": int(len(od)), "routable_directed_od": int(od["road_distance_km"].notna().sum()),
        "route_edges_with_fcd_proxy": int(len(edges)), "fcd_nodes_mapped": int(len(fcd_map)),
        "FCD_direction": "UNOBSERVED_UNDIRECTED_PROXY", "turn_restrictions": "UNVERIFIED",
        "site_entrances": "CONDITIONAL_NOT_LEGALLY_VERIFIED", "cross_border": "NO_WAIT_OR_PERMISSION_INFERRED",
    }
    road_qa["status"] = "CONDITIONAL" if road_qa["routable_directed_od"] == len(od) else "HOLD"
    write_json(out / "QA_ROAD_FCD.json", road_qa)
    return access, fcd_map, od, edges, road_qa


def integrate_orders(tasks: pd.DataFrame, assignment: pd.DataFrame, node_hour: pd.DataFrame,
                     fcd: pd.DataFrame, fcd_map: pd.DataFrame, od: pd.DataFrame, out: Path):
    orders = tasks.copy()
    orders["release_hour_utc"] = parse_tz(orders["release_utc"]).dt.floor("h")
    weather_cols = ["node_id", "interval_start_utc", "grid_id", "grid_distance_m", "grid_gt10km_warning",
                    "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m", "precipitation", "rain"]
    nw = node_hour[weather_cols].rename(columns={"node_id": "origin_node_id", "interval_start_utc": "release_hour_utc"})
    orders = orders.merge(nw, on=["origin_node_id", "release_hour_utc"], how="left")
    orders = orders.merge(od[["origin_node_id", "destination_node_id", "road_distance_km", "freeflow_minutes", "route_status"]],
                          on=["origin_node_id", "destination_node_id"], how="left")

    # Associate each V5 node with the nearest FCD reference coordinate.
    tr = Transformer.from_crs("EPSG:4326", "EPSG:32648", always_xy=True)
    unique_fcd = fcd[["node_id", "latitude", "longitude"]].drop_duplicates("node_id")
    fx, fy = tr.transform(unique_fcd["longitude"].to_numpy(), unique_fcd["latitude"].to_numpy())
    nx_, ny_ = tr.transform(assignment["longitude_E"].to_numpy(), assignment["latitude_N"].to_numpy())
    dist, idx = cKDTree(np.c_[fx, fy]).query(np.c_[nx_, ny_])
    node_fcd = assignment[["node_id", "zone"]].copy()
    node_fcd["nearest_fcd_node_id"] = unique_fcd.iloc[idx]["node_id"].to_numpy()
    node_fcd["nearest_fcd_distance_m"] = dist
    node_fcd["direction_status"] = "UNDIRECTED_SPEED_PROXY"
    node_fcd.to_csv(out / "V5_68_NODE_NEAREST_FCD_PROXY.csv", index=False, encoding="utf-8-sig")
    orders = orders.merge(node_fcd[["node_id", "nearest_fcd_node_id", "nearest_fcd_distance_m"]].rename(columns={"node_id": "origin_node_id"}), on="origin_node_id", how="left")
    speed = fcd[["node_id", "timestamp_utc", "observed_speed_kmh_conditional", "speed_state_recomputed"]].rename(
        columns={"node_id": "nearest_fcd_node_id", "timestamp_utc": "release_hour_utc"})
    orders = orders.merge(speed, on=["nearest_fcd_node_id", "release_hour_utc"], how="left")
    orders["weather_status"] = np.where(orders["wind_speed_10m"].notna(), "MATCHED_ERA5_PROXY", "HOLD_MISSING_WEATHER")
    orders["traffic_status"] = np.where(orders["speed_state_recomputed"].eq("POSITIVE"), "MATCHED_UNDIRECTED_POSITIVE_PROXY", "FALLBACK_REQUIRED")
    orders["integration_status"] = np.where(orders["road_distance_km"].notna() & orders["wind_speed_10m"].notna(),
                                             "CONDITIONAL_MATCHED", "HOLD_INPUT_GAP")
    orders.to_parquet(out / "V5_TASK_TIME_WEATHER_ROAD_INDEX.parquet", index=False)
    orders.to_csv(out / "V5_TASK_TIME_WEATHER_ROAD_INDEX.csv.gz", index=False, compression="gzip", encoding="utf-8")
    qa = {"rows": int(len(orders)), "unique_task_ids": int(orders["task_id"].nunique()),
          "scenarios": int(orders[["scenario_seed", "date_local"]].drop_duplicates().shape[0]),
          "weather_matched": int(orders["wind_speed_10m"].notna().sum()),
          "road_route_matched": int(orders["road_distance_km"].notna().sum()),
          "positive_fcd_at_release": int(orders["speed_state_recomputed"].eq("POSITIVE").sum()),
          "fcd_fallback_required": int((~orders["speed_state_recomputed"].eq("POSITIVE")).sum()),
          "orders_gt10km_weather_grid": int(orders["grid_gt10km_warning"].fillna(False).sum()),
          "orders_preserved": len(orders) == 82620 and orders["task_id"].nunique() == 82620}
    qa["status"] = "CONDITIONAL" if qa["orders_preserved"] and qa["weather_matched"] == 82620 and qa["road_route_matched"] == 82620 else "HOLD"
    write_json(out / "QA_INTEGRATION.json", qa)
    return orders, qa


def build_registry(paths: list[tuple[Path, str, str]], out: Path):
    rows = []
    for path, stage, role in paths:
        rows.append({"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": sha256(path),
                     "stage": stage, "role": role, "used": True, "read_only": True})
    reg = pd.DataFrame(rows)
    reg.to_csv(out / "INPUT_REGISTRY.csv", index=False, encoding="utf-8-sig")
    (out / "READONLY_INPUTS.sha256").write_text("".join(f"{r.sha256}  {r.path}\n" for r in reg.itertuples()), encoding="utf-8")
    return reg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--github", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--graphml", type=Path, required=True)
    args = ap.parse_args()
    out = args.out
    data = out / "data"; qa_dir = out / "qa"
    data.mkdir(parents=True, exist_ok=True); qa_dir.mkdir(parents=True, exist_ok=True)

    frozen = args.root / "下载CIQ无人机物流SCI--本对话全部文件更新总ZIP" / "01_本对话全部文件" / "CIQ_V5_S07_Actual_QA_Gates_20261030" / "inputs"
    master_path = frozen / "S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv"
    tasks_path = frozen / "S07_V5_SYNTHETIC_TASKS_CONDITIONAL_DESIGN.csv"
    manifest_path = frozen / "S07_V5_4590_SEED_DAY_RUN_MANIFEST.csv"
    v5_zip = args.root / "CIQ_ABC_QGIS322_V5_ONE_WMP228_68_NODES_FULL_PROJECT.zip"
    gpkg = args.root / "output_S07_S08_Codex_20261030" / "shared" / "v5_extracted" / "CIQ_ABC_QGIS322_V5_ONE_WMP228_68_NODES_FULL_PROJECT" / "data" / "CIQ_ABC_V5_ACTIVE.gpkg"
    weather_dir = args.root / "data" / "weather_2026" / "processed"
    fcd_path = args.github / "02_base_and_traffic_data" / "traffic_data" / "JB_CIQ_E01_corrected_five_month_traffic_data_345nodes_2026-05_09.csv.gz"
    road_dir = args.github / "03_gis_and_road_network" / "road_network_project" / "JB_CIQ_E02_roadnet_V4_6" / "outputs"
    ab = [road_dir / f"E02_{z}_{name}.csv" for z in "AB" for name in ("directed_edges_OSM", "road_graph_nodes")]

    master = pd.read_csv(master_path)
    tasks = pd.read_csv(tasks_path, low_memory=False)
    weather, grid_hour, weather_qa, boundary = audit_weather(weather_dir, data)
    fcd, fcd_qa = audit_fcd(fcd_path, data)
    v5_qa = audit_v5(gpkg, master, data)
    assignment, node_hour, spatial_qa = weather_to_nodes(master, grid_hour, data)
    access, fcd_map, od, edges, road_qa = audit_road(args.graphml, master, fcd, data)
    orders, integration_qa = integrate_orders(tasks, assignment, node_hour, fcd, fcd_map, od, data)

    input_paths = [(v5_zip, "S07", "AUTHORITATIVE_V5_ZIP"), (gpkg, "S07", "ACTIVE_GPKG"),
                   (master_path, "S07", "AUTHORITATIVE_68_NODE_MASTER"), (tasks_path, "S07", "FROZEN_82620_ORDERS"),
                   (manifest_path, "S07", "FROZEN_4590_SCENARIOS"), (fcd_path, "S07", "FCD_345_NODE"),
                   (args.graphml, "S07", "CURRENT_OSM_ABC_CONDITIONAL")]
    for m in HOURS:
        x = weather_dir / f"JB_SG_Weather_2026_{m:02d}.xlsx"
        input_paths += [(x, "S07", "WEATHER_XLSX"), (x.with_suffix(".manifest.json"), "S07", "WEATHER_MANIFEST")]
    input_paths += [(p, "S07", "HISTORICAL_AB_ROAD_REFERENCE") for p in ab]
    build_registry(input_paths, args.root / "output_S07_S08_Codex_20261030" / "shared")

    env = {"run_started_or_completed_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version,
           "platform": platform.platform(), "pandas": pd.__version__, "numpy": np.__version__,
           "geopandas": gpd.__version__, "networkx": nx.__version__, "osmnx": ox.__version__,
           "pyproj": pyproj.__version__, "scipy": scipy.__version__}
    write_json(args.root / "output_S07_S08_Codex_20261030" / "shared" / "ENVIRONMENT.json", env)

    g_w = "CONDITIONAL" if (weather_qa["status"] == "PASS").all() and len(node_hour) == 249696 else "HOLD"
    g_r = road_qa["status"] if fcd_qa["status"].startswith("PASS") else "HOLD"
    g_i = integration_qa["status"]
    overall = "CONDITIONAL" if g_w != "HOLD" and g_r != "HOLD" and g_i != "HOLD" else "HOLD"
    gates = {"G07-W": g_w, "G07-R": g_r, "G07-INTEGRATION": g_i, "S07": overall,
             "S08_release": "CONDITIONAL_SCENARIO" if overall == "CONDITIONAL" else "HOLD",
             "limitations": ["ERA5 is reanalysis and only two returned grid cells represent 68 nodes",
                "31 nodes exceed the 10 km weather-proxy warning threshold",
                "FCD has no observed direction and its km/h unit is conditional on TomTom default",
                "current OSM is not a May-Sep 2026 historical snapshot",
                "road entrance legality, turn restrictions and cross-border permissions are unverified"]}
    write_json(qa_dir / "S07_GATES.json", gates)
    summary = {
        "gates": gates, "weather_rows": int(len(weather)), "era5_grid_hour_rows": int(len(grid_hour)),
        "era5_boundary_rows": int(len(boundary)), "fcd": fcd_qa, "v5": v5_qa,
        "weather_node_hour_rows": int(len(node_hour)), "weather_nodes_gt10km": int(assignment["grid_gt10km_warning"].sum()),
        "road": road_qa, "integration": integration_qa,
    }
    write_json(qa_dir / "S07_SUMMARY.json", summary)
    report = "# S07 真实数据验收报告\n\n"
    report += f"- G07-W：**{g_w}**；五个月 Weather_Hourly 共 {len(weather):,} 行，ERA5 有效 grid-hour {len(grid_hour):,} 行，边界记录 {len(boundary):,} 行。\n"
    report += f"- G07-R：**{g_r}**；FCD {len(fcd):,} 行，正速度 {fcd_qa['positive_speed']:,}，缺失 {fcd_qa['missing_speed']:,}，非正 {fcd_qa['nonpositive_speed']:,}。\n"
    report += f"- G07-INTEGRATION：**{g_i}**；保留订单 {len(orders):,}，场景 {integration_qa['scenarios']:,}。\n"
    report += f"- S07 总裁定：**{overall}**。仅允许 S08 以条件性情景运行，不代表实际道路、入口或方向交通已经验证。\n\n"
    report += "## 科学限制\n\n" + "\n".join(f"- {x}" for x in gates["limitations"]) + "\n"
    (out / "S07_ACCEPTANCE_REPORT_CN.md").write_text(report, encoding="utf-8")
    write_json(data / "SCHEMA.json", {p.name: list(pd.read_parquet(p).columns) for p in data.glob("*.parquet")})
    print(json.dumps(summary, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
