#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Historical weather downloader for JB-SG CIQ SCI study (2026 May–Sep).

Data classes: ERA5 via Open-Meteo (REANALYSIS), NASA POWER (MODELED/ANALYSIS),
NEA data.gov.sg (IN-SITU STATIONS, Singapore ONLY).

Key quality constraints:
* Download authentic server responses; NEVER invent or interpolate 30-min values.
* Preserve raw JSON, request log and independent sources.
* ERA5 rainfall is preceding-hour accumulation; NASA POWER hour begins at timestamp.
* NEA rainfall is provisionally treated as 5-min amount and summed to 30 min only
  with six distinct five-minute samples; see README before citing precipitation.
* NEA published wind-speed is 10-min mean sampled every minute, NOT gust.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import logging
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

YEAR = 2026
LOCAL_TZ = ZoneInfo("Asia/Singapore")  # Malaysia and Singapore both UTC+08
UTC = timezone.utc
OPENMETEO_URL = "https://archive-api.open-meteo.com/v1/archive"
NASA_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"
NEA_BASE = "https://api-open.data.gov.sg/v2/real-time/api"
OPENMETEO_HOURLY = [
    "precipitation", "rain", "wind_speed_10m", "wind_speed_100m",
    "wind_direction_10m", "wind_direction_100m", "wind_gusts_10m",
    "temperature_2m", "relative_humidity_2m",
]
NASA_PARAMS = ["PRECTOTCORR", "WS10M", "WD10M", "T2M", "RH2M"]
NEA_TYPES = ["rainfall", "wind-speed", "wind-direction"]
NEA_KNOT_M_S = 0.5144444444444445
LOG = logging.getLogger("weather")


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read_points(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"point_id": str})
    required = {"point_id", "corridor", "country", "latitude", "longitude", "description", "coordinate_source"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Points file lacks columns: {sorted(missing)}")
    if df.point_id.duplicated().any() or len(df) < 2:
        raise ValueError("Duplicate point_id or fewer than two points")
    if not df.latitude.between(-90, 90).all() or not df.longitude.between(-180, 180).all():
        raise ValueError("Point coordinates outside WGS84 valid range")
    return df


class Fetcher:
    """GET with disk cache, audit trail, retry/backoff and no synthetic fallback."""

    def __init__(self, root: Path, refresh: bool = False, sleep_seconds: float = 1.8):
        self.root = root
        self.cache = root / "raw"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.refresh = refresh
        self.sleep_seconds = sleep_seconds
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "JB-SG-weather-research/1.0 (academic)", "Accept": "application/json"})
        self.audit: list[dict[str, Any]] = []
        self.last_request = 0.0
        self.audit_path = root / "api_log.csv"

    def _write_audit(self, row: dict[str, Any]):
        self.audit.append(row)
        keys = ["retrieved_at_utc", "source", "cache_file", "url_without_key", "status", "sha256", "bytes", "notes"]
        with self.audit_path.open("a", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            if f.tell() == 0:
                w.writeheader()
            w.writerow({k: row.get(k, "") for k in keys})

    def get_json(self, source: str, relpath: str, url: str, params: dict[str, Any],
                 *, timeout: int = 120, can_be_not_found: bool = False) -> dict[str, Any] | None:
        dest = self.cache / source / relpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        public_url = requests.Request("GET", url, params=params).prepare().url
        if dest.exists() and not self.refresh:
            try:
                with gzip.open(dest, "rt", encoding="utf-8") as f:
                    saved = json.load(f)
                LOG.info("CACHE %s", dest)
                data_bytes = json.dumps(saved, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                self._write_audit({"retrieved_at_utc": utc_now(), "source": source, "cache_file": str(dest),
                                   "url_without_key": public_url, "status": "CACHED_REUSED", "sha256": sha256_bytes(data_bytes),
                                   "bytes": len(data_bytes), "notes": "Originally downloaded earlier; see prior SUCCESS log"})
                return saved
            except (OSError, json.JSONDecodeError):
                LOG.warning("Cache corrupt, downloading again: %s", dest)
        headers = {}
        if source == "nea" and os.getenv("DATAGOVSG_API_KEY"):
            headers["x-api-key"] = os.environ["DATAGOVSG_API_KEY"]
        last_error = ""
        for attempt in range(1, 7):
            elapsed = time.monotonic() - self.last_request
            if elapsed < self.sleep_seconds:
                time.sleep(self.sleep_seconds - elapsed)
            self.last_request = time.monotonic()
            try:
                response = self.session.get(url, params=params, headers=headers, timeout=timeout)
                if response.status_code in [404] and can_be_not_found:
                    last_error = "HTTP 404 (no historical data)"
                    break
                if response.status_code in {429, 500, 502, 503, 504}:
                    retry_after = response.headers.get("Retry-After")
                    try:
                        delay = min(float(retry_after), 120) if retry_after else min(2 ** attempt * 2, 90)
                    except ValueError:
                        delay = min(2 ** attempt * 2, 90)
                    LOG.warning("HTTP %s %s retry in %.1fs", response.status_code, source, delay)
                    time.sleep(delay)
                    last_error = f"HTTP {response.status_code}"
                    continue
                response.raise_for_status()
                obj = response.json()
                if not isinstance(obj, dict):
                    raise ValueError("Unexpected JSON type")
                if obj.get("error") is True or (source == "nea" and obj.get("code") not in (None, 0, 1)):
                    raise ValueError(f"API rejection: {str(obj)[:300]}")
                data_bytes = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                with gzip.open(dest, "wb") as f:
                    f.write(data_bytes)
                self._write_audit({"retrieved_at_utc": utc_now(), "source": source, "cache_file": str(dest),
                                   "url_without_key": public_url, "status": "SUCCESS", "sha256": sha256_bytes(data_bytes),
                                   "bytes": len(data_bytes), "notes": ""})
                return obj
            except (requests.RequestException, ValueError, json.JSONDecodeError) as e:
                last_error = f"{type(e).__name__}: {str(e)[:250]}"
                if attempt < 6:
                    time.sleep(min(2 ** attempt, 45))
        LOG.error("FAILED source=%s path=%s: %s", source, relpath, last_error)
        self._write_audit({"retrieved_at_utc": utc_now(), "source": source, "cache_file": str(dest),
                           "url_without_key": public_url, "status": "FAILED", "sha256": "", "bytes": 0,
                           "notes": last_error})
        return None


def month_bounds_local(year: int, month: int):
    start = pd.Timestamp(year=year, month=month, day=1, tz=LOCAL_TZ)
    end = start + pd.DateOffset(months=1)
    return start, end


def local_window_month(year: int, month: int, frequency: str) -> pd.DatetimeIndex:
    start, end = month_bounds_local(year, month)
    return pd.date_range(start, end, freq=frequency, inclusive="left")


def get_era5(fetcher: Fetcher, month: int, point: pd.Series) -> pd.DataFrame:
    start, end = month_bounds_local(YEAR, month)
    # UTC guard days capture local boundaries and preceding-hour precipitation.
    utc_start = start.tz_convert("UTC") - pd.Timedelta(days=1)
    utc_end = end.tz_convert("UTC") + pd.Timedelta(days=1)
    params = {
        "latitude": float(point.latitude), "longitude": float(point.longitude),
        "start_date": utc_start.date().isoformat(), "end_date": utc_end.date().isoformat(),
        "hourly": ",".join(OPENMETEO_HOURLY), "models": "era5", "timezone": "UTC",
        "wind_speed_unit": "ms", "precipitation_unit": "mm", "temperature_unit": "celsius",
    }
    o = fetcher.get_json("openmeteo", f"{YEAR}-{month:02d}/{point.point_id}.json.gz", OPENMETEO_URL, params)
    if not o or "hourly" not in o or "time" not in o["hourly"]:
        return pd.DataFrame()
    hourly = o["hourly"]
    n = len(hourly["time"])
    for k in OPENMETEO_HOURLY:
        if k not in hourly or len(hourly[k]) != n:
            LOG.warning("Missing/incomplete ERA5 variable %s at %s", k, point.point_id)
    ts_utc = pd.to_datetime(hourly["time"], utc=True, errors="coerce")
    df = pd.DataFrame({"timestamp_utc": ts_utc})
    for k in OPENMETEO_HOURLY:
        df[k] = pd.to_numeric(hourly.get(k, [None] * n), errors="coerce")
    # All hourly fields except precipitation are timestamped at response time;
    # precipitation and rain are sums over [t-1 hour, t).
    df["timestamp_sgt"] = df.timestamp_utc.dt.tz_convert(LOCAL_TZ)
    df["rain_period_start_sgt"] = df.timestamp_sgt - pd.Timedelta(hours=1)
    df["rain_period_end_sgt"] = df.timestamp_sgt
    df = df[(df.timestamp_sgt >= start) & (df.timestamp_sgt < end) |
            (df.rain_period_start_sgt >= start) & (df.rain_period_start_sgt < end)].copy()
    df["point_id"] = point.point_id
    df["corridor"] = point.corridor
    df["source_class"] = "REANALYSIS_ERA5_0.25DEG"
    df["latitude_requested"] = point.latitude
    df["longitude_requested"] = point.longitude
    df["latitude_returned"] = o.get("latitude")
    df["longitude_returned"] = o.get("longitude")
    df["source_url"] = OPENMETEO_URL
    return df


def get_nasa(fetcher: Fetcher, month: int, point: pd.Series) -> pd.DataFrame:
    start, end = month_bounds_local(YEAR, month)
    first_utc = (start.tz_convert("UTC") - pd.Timedelta(days=1)).date()
    last_utc = (end.tz_convert("UTC") + pd.Timedelta(days=1)).date()
    params = {
        "latitude": float(point.latitude), "longitude": float(point.longitude),
        "start": first_utc.strftime("%Y%m%d"), "end": last_utc.strftime("%Y%m%d"),
        "parameters": ",".join(NASA_PARAMS), "community": "RE", "format": "JSON", "time-standard": "UTC",
    }
    o = fetcher.get_json("nasa", f"{YEAR}-{month:02d}/{point.point_id}.json.gz", NASA_URL, params)
    values = (o or {}).get("properties", {}).get("parameter", {})
    if not isinstance(values, dict) or not values:
        return pd.DataFrame()
    keys = set()
    for dic in values.values():
        if isinstance(dic, dict):
            keys.update(dic.keys())
    if not keys:
        return pd.DataFrame()
    df = pd.DataFrame({"utc_compact": sorted(keys)})
    df["timestamp_utc"] = pd.to_datetime(df.utc_compact, format="%Y%m%d%H", utc=True, errors="coerce")
    df = df.drop(columns="utc_compact")
    for key in NASA_PARAMS:
        series = values.get(key, {})
        parsed = pd.to_numeric(pd.Series([series.get(t.strftime("%Y%m%d%H")) if isinstance(series, dict) else None
                                         for t in df.timestamp_utc]), errors="coerce")
        df[key] = parsed.where(parsed > -990, np.nan).values
    df["timestamp_sgt"] = df.timestamp_utc.dt.tz_convert(LOCAL_TZ)
    df = df[(df.timestamp_sgt >= start) & (df.timestamp_sgt < end)].copy()
    # NASA POWER explicitly defines timestamp as the BEGINNING of each hour.
    df["rain_period_start_sgt"] = df.timestamp_sgt
    df["rain_period_end_sgt"] = df.timestamp_sgt + pd.Timedelta(hours=1)
    df["point_id"] = point.point_id
    df["corridor"] = point.corridor
    df["source_class"] = "NASA_POWER_ANALYSIS_ESTIMATE"
    df["latitude_requested"] = point.latitude
    df["longitude_requested"] = point.longitude
    df["source_url"] = NASA_URL
    return df


def nea_reading_rows(payload: dict[str, Any], kind: str):
    """Parse v2 schema including data.readings; tolerate older items variants."""
    data = payload.get("data", {})
    if not isinstance(data, dict):
        return [], {}
    station_meta = {}
    for s in data.get("stations", []) or []:
        if not isinstance(s, dict):
            continue
        loc = s.get("location") or {}
        sid = str(s.get("id") or s.get("stationId") or "").strip()
        if sid:
            station_meta[sid] = {"station_id": sid, "station_name": s.get("name", ""),
                                 "latitude": loc.get("latitude"), "longitude": loc.get("longitude"),
                                 "device_id": s.get("deviceId", "")}
    readings = data.get("readings", []) or []
    if not readings and isinstance(data.get("items"), list):
        # Compatibility: nested items/readings schema in some versions.
        for item in data["items"]:
            if isinstance(item, dict):
                readings.extend(item.get("readings", []) or [])
    rows = []
    for reading in readings:
        if not isinstance(reading, dict):
            continue
        timestamp = reading.get("timestamp")
        for e in reading.get("data", []) or []:
            if not isinstance(e, dict):
                continue
            sid = str(e.get("stationId") or e.get("station_id") or "").strip()
            if not sid or timestamp is None:
                continue
            try:
                numeric = float(e.get("value"))
            except (TypeError, ValueError):
                continue
            if not math.isfinite(numeric):
                continue
            rows.append({"kind": kind, "station_id": sid, "timestamp_raw": timestamp,
                         "value_raw": numeric, "reading_type": data.get("readingType", ""),
                         "reading_unit": data.get("readingUnit", "")})
    return rows, station_meta


def get_nea_day(fetcher: Fetcher, kind: str, day: str, probe: bool = False):
    all_rows = []
    meta = {}
    token = None
    visited = set()
    max_pages = 1 if probe else 1000
    complete = False
    for page in range(max_pages):
        params = {"date": day}
        if token:
            params["paginationToken"] = token
        obj = fetcher.get_json("nea", f"{day[:7]}/{kind}/{day}/page{page:04d}.json.gz",
                               f"{NEA_BASE}/{kind}", params, can_be_not_found=True)
        if obj is None:
            return all_rows, meta, False
        rows, stations = nea_reading_rows(obj, kind)
        all_rows.extend(rows)
        meta.update(stations)
        data = obj.get("data") or {}
        if not isinstance(data, dict):
            return all_rows, meta, False
        token = data.get("paginationToken") or data.get("pagination_token") or None
        if not token:
            complete = True
            break
        if token in visited:
            LOG.error("Repeating NEA pagination token %s %s", kind, day)
            return all_rows, meta, False
        visited.add(token)
    return all_rows, meta, complete


def haversine_km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    lat1, lat2 = math.radians(a_lat), math.radians(b_lat)
    dlat, dlon = lat2-lat1, math.radians(b_lon-a_lon)
    x = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371.0088 * 2 * math.atan2(math.sqrt(x), math.sqrt(1-x))


def select_nearest(known_stations: dict[str, Any], sg_points: pd.DataFrame, kind: str,
                   max_station_km: float) -> list[dict[str, Any]]:
    selected = []
    for _, p in sg_points.iterrows():
        candidates = []
        for sid, st in known_stations.items():
            try:
                km = haversine_km(float(p.latitude), float(p.longitude), float(st["latitude"]), float(st["longitude"]))
            except (ValueError, TypeError, KeyError):
                continue
            candidates.append((km, sid, st))
        if not candidates:
            continue
        km, sid, st = min(candidates, key=lambda x: x[0])
        if km <= max_station_km:
            selected.append({"point_id": p.point_id, "corridor": p.corridor, "kind": kind,
                             "station_id": sid, "station_name": st.get("station_name", ""),
                             "distance_km": round(km, 3), "station_lat": st.get("latitude"),
                             "station_lon": st.get("longitude"), "selection": "nearest_station_proxy"})
        else:
            LOG.warning("No NEA station within %.1f km of %s: nearest=%.1f km", max_station_km, p.point_id, km)
    return selected


def normalize_nea_rows(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["timestamp_utc"] = pd.to_datetime(df.timestamp_raw, utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp_utc"])
    df["timestamp_sgt"] = df.timestamp_utc.dt.tz_convert(LOCAL_TZ)
    df["value_converted"] = pd.to_numeric(df.value_raw, errors="coerce")
    mask = df.kind.eq("wind-speed")
    df.loc[mask, "value_converted"] = df.loc[mask, "value_raw"] * NEA_KNOT_M_S
    df["unit_converted"] = np.where(mask, "m/s", np.where(df.kind.eq("rainfall"), "mm", "degree"))
    return df.drop_duplicates(subset=["kind", "station_id", "timestamp_utc"], keep="last")


def build_nea_30min(raw: pd.DataFrame, selected: pd.DataFrame, year: int, month: int):
    windows = local_window_month(year, month, "30min")
    all_rows = []
    if selected.empty:
        return pd.DataFrame(), pd.DataFrame()
    matched_obs = []
    for s in selected.to_dict("records"):
        d = raw[(raw.kind == s["kind"]) & (raw.station_id == s["station_id"])].copy() if not raw.empty else pd.DataFrame()
        if not d.empty:
            d["point_id"] = s["point_id"]
            d["distance_km"] = s["distance_km"]
            matched_obs.append(d)
        if d.empty:
            agg = pd.DataFrame(index=windows)
        else:
            # Reading at exactly hh:30 is the END of the previous 5-minute rainfall interval.
            adjusted = d.timestamp_sgt - (pd.Timedelta(nanoseconds=1) if s["kind"] == "rainfall" else pd.Timedelta(0))
            d["bin"] = adjusted.dt.floor("30min")
            series = d.groupby("bin").value_converted
            agg = pd.DataFrame(index=windows)
            agg["sample_n"] = series.count()
            if s["kind"] == "rainfall":
                # Six distinct 5-min rainfall readings required for valid 30m total.
                agg["rain_30min_mm"] = series.sum(min_count=1)
                agg.loc[agg.sample_n != 6, "rain_30min_mm"] = np.nan
            elif s["kind"] == "wind-speed":
                agg["wind_10min_mean_samples_avg_ms"] = series.mean()
                agg["wind_10min_mean_samples_max_ms"] = series.max()
            else:
                angle = d.groupby("bin").value_converted.apply(lambda x: float((math.degrees(math.atan2(
                    np.sin(np.deg2rad(x)).mean(), np.cos(np.deg2rad(x)).mean())) + 360) % 360))
                agg["wind_dir_circular_mean_deg"] = angle
        agg = agg.reindex(windows)
        agg["timestamp_sgt"] = agg.index
        agg["point_id"] = s["point_id"]
        agg["kind"] = s["kind"]
        agg["station_id"] = s["station_id"]
        agg["distance_km"] = s["distance_km"]
        agg["source_class"] = "NEA_INSITU_STATION_PROXY"
        agg["quality_note"] = "rain valid only if 6 samples" if s["kind"] == "rainfall" else "10min mean wind observations; NOT gust"
        all_rows.append(agg.reset_index(drop=True))
    return pd.concat(all_rows, ignore_index=True), (pd.concat(matched_obs, ignore_index=True) if matched_obs else pd.DataFrame())


def get_nea_month(fetcher: Fetcher, month: int, points: pd.DataFrame, max_station_km: float,
                  probe: bool = False):
    start, end = month_bounds_local(YEAR, month)
    sg = points[points.country.astype(str).str.upper().eq("SG")]
    if sg.empty:
        return tuple(pd.DataFrame() for _ in range(5))
    raw_rows = []
    all_station_meta = {}
    first_seen_stations: dict[str, dict[str, Any]] = {}
    selected = []
    statuses = []
    # Include next month's first day to capture the 00:00 rainfall sample that
    # may close the preceding 23:55–00:00 five-minute interval.
    days = pd.date_range(start, end + pd.Timedelta(days=1), freq="D", inclusive="left")
    if probe:
        days = days[:1]
    for day in days:
        day_s = day.strftime("%Y-%m-%d")
        for kind in NEA_TYPES:
            rows, station_meta, complete = get_nea_day(fetcher, kind, day_s, probe=probe)
            all_station_meta.update({(kind, sid): dict(x, kind=kind) for sid, x in station_meta.items()})
            if kind not in first_seen_stations and station_meta:
                first_seen_stations[kind] = station_meta
                selected.extend(select_nearest(station_meta, sg, kind, max_station_km))
            chosen = {x["station_id"] for x in selected if x["kind"] == kind}
            filtered = [x for x in rows if x["station_id"] in chosen]
            raw_rows.extend(filtered)
            statuses.append({"day": day_s, "kind": kind,
                             "is_next_month_boundary_guard": day >= end,
                             "api_rows_all_stations": len(rows),
                             "selected_station_rows": len(filtered), "pagination_complete": complete,
                             "source_class": "NEA_INSITU"})
            LOG.info("NEA %s %s all=%d selected=%d paginated=%s", day_s, kind, len(rows), len(filtered), complete)
    raw = normalize_nea_rows(raw_rows)
    selected_df = pd.DataFrame(selected)
    data30, selected_raw = build_nea_30min(raw, selected_df, YEAR, month)
    stations = pd.DataFrame(list(all_station_meta.values()))
    return data30, selected_raw, selected_df, pd.DataFrame(statuses), stations


def build_hourly_master(points: pd.DataFrame, month: int, era: pd.DataFrame,
                        nasa: pd.DataFrame) -> pd.DataFrame:
    """Uniform LOCAL hourly time index; NULLs remain NULLs; original source tables preserved."""
    hours = local_window_month(YEAR, month, "h")
    master = pd.concat([pd.DataFrame({
        "point_id": p.point_id, "corridor": p.corridor, "country": p.country,
        "timestamp_hour_start_sgt": hours,
        "latitude_requested": p.latitude, "longitude_requested": p.longitude,
    }) for _, p in points.iterrows()], ignore_index=True)
    if not era.empty:
        # Reanalysis instantaneous wind at t and preceding-hour rainfall ending at t+1.
        wind = era[["point_id", "timestamp_sgt", "wind_speed_10m", "wind_speed_100m",
                    "wind_direction_10m", "wind_direction_100m", "wind_gusts_10m",
                    "temperature_2m", "relative_humidity_2m"]].rename(columns={
                        "timestamp_sgt": "timestamp_hour_start_sgt", "wind_speed_10m": "era5_wind10_ms",
                        "wind_speed_100m": "era5_wind100_ms", "wind_direction_10m": "era5_dir10_deg",
                        "wind_direction_100m": "era5_dir100_deg", "wind_gusts_10m": "era5_gust10_ms",
                        "temperature_2m": "era5_temp_c", "relative_humidity_2m": "era5_rh_pct"})
        rain = era[["point_id", "rain_period_start_sgt", "precipitation", "rain"]].rename(columns={
            "rain_period_start_sgt": "timestamp_hour_start_sgt", "precipitation": "era5_precip_1h_mm",
            "rain": "era5_rain_1h_mm"})
        master = master.merge(wind.drop_duplicates(["point_id", "timestamp_hour_start_sgt"]),
                              on=["point_id", "timestamp_hour_start_sgt"], how="left")
        master = master.merge(rain.drop_duplicates(["point_id", "timestamp_hour_start_sgt"]),
                              on=["point_id", "timestamp_hour_start_sgt"], how="left")
    if not nasa.empty:
        ns = nasa[["point_id", "timestamp_sgt", "PRECTOTCORR", "WS10M", "WD10M", "T2M", "RH2M"]].rename(columns={
            "timestamp_sgt": "timestamp_hour_start_sgt", "PRECTOTCORR": "nasa_precip_mm_per_hour",
            "WS10M": "nasa_wind10_ms", "WD10M": "nasa_dir10_deg",
            "T2M": "nasa_temp_c", "RH2M": "nasa_rh_pct"})
        master = master.merge(ns.drop_duplicates(["point_id", "timestamp_hour_start_sgt"]),
                              on=["point_id", "timestamp_hour_start_sgt"], how="left")
    master["precip_interval"] = "[timestamp_hour_start_sgt, timestamp+1hour)"
    master["era5_source_class"] = "REANALYSIS_ERA5" if not era.empty else "NOT_FETCHED"
    master["nasa_source_class"] = "ANALYSIS_ESTIMATE" if not nasa.empty else "NOT_FETCHED"
    master["caution"] = "ERA5 wind at hour start; ERA5 rain covers the following hour, via end timestamp"
    return master


def build_nea_wide(month: int, points: pd.DataFrame, nea30: pd.DataFrame) -> pd.DataFrame:
    sg = points[points.country.astype(str).str.upper().eq("SG")]
    windows = local_window_month(YEAR, month, "30min")
    base = pd.concat([pd.DataFrame({"point_id": p.point_id, "corridor": p.corridor,
                                   "timestamp_sgt": windows}) for _, p in sg.iterrows()], ignore_index=True) if len(sg) else pd.DataFrame()
    if base.empty or nea30.empty:
        return base
    kinds = {"rainfall": ["rain_30min_mm", "sample_n", "station_id"],
             "wind-speed": ["wind_10min_mean_samples_avg_ms", "wind_10min_mean_samples_max_ms", "sample_n", "station_id"],
             "wind-direction": ["wind_dir_circular_mean_deg", "sample_n", "station_id"]}
    for kind, cols in kinds.items():
        # Some NEA kinds may be absent: retain columns with NA, never invent weather.
        for c in cols:
            if c not in nea30.columns:
                nea30 = nea30.assign(**{c: np.nan})
        d = nea30[nea30.kind.eq(kind)][["point_id", "timestamp_sgt"]+cols].copy()
        d = d.rename(columns={"sample_n": f"{kind.replace('-', '_')}_samples", "station_id": f"{kind.replace('-', '_')}_station"})
        base = base.merge(d, on=["point_id", "timestamp_sgt"], how="left")
    base["rain_class"] = "IN_SITU_NEAREST_STATION; requires 6 five-minute samples"
    base["wind_class"] = "IN_SITU_NEAREST_STATION; 10-min mean samples NOT gust"
    return base


def make_hourly_comparison(era: pd.DataFrame, nasa: pd.DataFrame) -> pd.DataFrame:
    if era.empty or nasa.empty:
        return pd.DataFrame()
    er = era[["point_id", "rain_period_start_sgt", "precipitation", "wind_speed_10m"]].rename(columns={
        "rain_period_start_sgt": "period_start_sgt", "precipitation": "era5_rain_mm",
        "wind_speed_10m": "era5_wind_ms"})
    na = nasa[["point_id", "rain_period_start_sgt", "PRECTOTCORR", "WS10M"]].rename(columns={
        "rain_period_start_sgt": "period_start_sgt", "PRECTOTCORR": "nasa_rain_mm_per_hour",
        "WS10M": "nasa_wind_ms"})
    # ERA5 wind speed is timestamped at end of precipitation period; keep label warning.
    combined = pd.merge(er, na, on=["point_id", "period_start_sgt"], how="inner")
    combined["rain_difference_mm"] = combined.era5_rain_mm - combined.nasa_rain_mm_per_hour
    combined["wind_difference_ms_not_identical_temporal_definition"] = combined.era5_wind_ms - combined.nasa_wind_ms
    combined["interpretation"] = "rain period aligned; wind definitions/timestamps may differ"
    return combined


def make_nea_era5_comparison(master: pd.DataFrame, nea_wide: pd.DataFrame) -> pd.DataFrame:
    """NEA station vs ERA5 grid comparison; no fill/interpolation of missing observations."""
    if nea_wide.empty or not {"rain_30min_mm", "wind_10min_mean_samples_avg_ms"}.issubset(nea_wide.columns):
        return pd.DataFrame()
    d = nea_wide.copy()
    d["timestamp_hour_start_sgt"] = d.timestamp_sgt.dt.floor("h")
    def two_half_hours_or_missing(x):
        return x.sum() if len(x) == 2 and x.notna().all() else np.nan
    agg = d.groupby(["point_id", "timestamp_hour_start_sgt"], as_index=False).agg(
        nea_station_precip_1h_mm=("rain_30min_mm", two_half_hours_or_missing),
        nea_station_wind10_mean_ms=("wind_10min_mean_samples_avg_ms", lambda x: x.mean() if len(x) == 2 and x.notna().all() else np.nan))
    cols = ["point_id", "timestamp_hour_start_sgt"]
    for col in ["era5_precip_1h_mm", "era5_wind10_ms"]:
        if col in master.columns:
            cols.append(col)
    if len(cols) < 4:
        return pd.DataFrame()
    out = agg.merge(master[cols], on=["point_id", "timestamp_hour_start_sgt"], how="left")
    out["rain_error_nea_minus_era5_mm"] = out.nea_station_precip_1h_mm - out.era5_precip_1h_mm
    out["wind_error_nea_minus_era5_ms"] = out.nea_station_wind10_mean_ms - out.era5_wind10_ms
    out["warning"] = "NEA station vs ERA5 grid; different sampling height, location and wind averaging"
    return out


def make_qc(month: int, points: pd.DataFrame, era: pd.DataFrame, nasa: pd.DataFrame,
            data30: pd.DataFrame, nea_status: pd.DataFrame, sources: set[str]) -> pd.DataFrame:
    hours = len(local_window_month(YEAR, month, "h"))
    slots30 = len(local_window_month(YEAR, month, "30min"))
    rows = []
    start, end = month_bounds_local(YEAR, month)
    for _, p in points.iterrows():
        for source, data, columns, requested in [
            ("ERA5", era, ["wind_speed_10m", "wind_gusts_10m", "precipitation"], "openmeteo" in sources),
            ("NASA_POWER", nasa, ["WS10M", "PRECTOTCORR"], "nasa" in sources)]:
            subset = data[data.point_id == p.point_id] if not data.empty else pd.DataFrame()
            for col in columns:
                if not subset.empty:
                    time_col = "rain_period_start_sgt" if col in ["precipitation", "PRECTOTCORR"] else "timestamp_sgt"
                    d = subset[(subset[time_col] >= start) & (subset[time_col] < end)]
                else:
                    d = pd.DataFrame()
                valid = int(d[col].notna().sum()) if not d.empty and col in d.columns else 0
                rows.append({"point_id": p.point_id, "source": source, "variable": col,
                             "expected_slots": hours, "observed_valid_slots": valid,
                             "coverage_pct": round(100 * valid / hours, 2),
                             "status": ("NOT_REQUESTED" if not requested else ("DATA" if valid else "NOT_FETCHED_OR_EMPTY"))})
    for _, p in points[points.country.astype(str).str.upper().eq("SG")].iterrows():
        for kind, col in [("rainfall", "rain_30min_mm"),
                          ("wind-speed", "wind_10min_mean_samples_avg_ms"),
                          ("wind-direction", "wind_dir_circular_mean_deg")]:
            d = data30[(data30.point_id == p.point_id) & data30.kind.eq(kind)] if not data30.empty else pd.DataFrame()
            valid = int(d[col].notna().sum()) if not d.empty and col in d.columns else 0
            rows.append({"point_id": p.point_id, "source": "NEA", "variable": kind,
                         "expected_slots": slots30, "observed_valid_slots": valid,
                         "coverage_pct": round(100 * valid / slots30, 2),
                         "status": "NOT_REQUESTED" if "nea" not in sources else ("DATA" if valid else "NOT_FETCHED_OR_EMPTY")})
    if not nea_status.empty:
        for kind, group in nea_status.groupby("kind"):
            rows.append({"point_id": "SG_STATIONS", "source": "NEA", "variable": kind+"_daily_pagination",
                         "expected_slots": len(group), "observed_valid_slots": int(group.pagination_complete.sum()),
                         "coverage_pct": round(100 * group.pagination_complete.mean(), 2),
                         "status": "PAGINATION_AUDIT"})
    return pd.DataFrame(rows)


def to_excel_safe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    a = df.copy()
    for col in a.columns:
        if isinstance(a[col].dtype, pd.DatetimeTZDtype):
            a[col] = a[col].dt.strftime("%Y-%m-%d %H:%M:%S%z")
    return a.replace({np.nan: None})


def write_xlsx(path: Path, tables: dict[str, pd.DataFrame]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="xlsxwriter", datetime_format="yyyy-mm-dd hh:mm:ss") as writer:
        for name, df in tables.items():
            # Excel has 1,048,576 rows per sheet, enforce to avoid silent truncation.
            if len(df) > 1_048_575:
                raise ValueError(f"Excel max rows exceeded: {name}: {len(df)}")
            if df.empty and not len(df.columns):
                df = pd.DataFrame(columns=["NO_DATA_AVAILABLE"])
            a = to_excel_safe(df)
            a.to_excel(writer, sheet_name=name[:31], index=False, na_rep="")
            ws = writer.sheets[name[:31]]
            ws.freeze_panes(1, 0)
            ws.autofilter(0, 0, max(1, len(a)), max(0, len(a.columns)-1))
            hdr = writer.book.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#17365D", "text_wrap": True})
            ws.set_row(0, 29, hdr)
            for i, c in enumerate(a.columns):
                ws.set_column(i, i, min(34, max(13, len(str(c)) + 2)))


def run_month(fetcher: Fetcher, month: int, points: pd.DataFrame, sources: set[str], station_km: float):
    LOG.info("========== %s-%02d =========", YEAR, month)
    era_frames, nasa_frames = [], []
    for _, p in points.iterrows():
        if "openmeteo" in sources:
            er = get_era5(fetcher, month, p)
            if not er.empty:
                era_frames.append(er)
            LOG.info("ERA5 %s %d rows", p.point_id, len(er))
        if "nasa" in sources:
            na = get_nasa(fetcher, month, p)
            if not na.empty:
                nasa_frames.append(na)
            LOG.info("NASA %s %d rows", p.point_id, len(na))
    era = pd.concat(era_frames, ignore_index=True) if era_frames else pd.DataFrame()
    nasa = pd.concat(nasa_frames, ignore_index=True) if nasa_frames else pd.DataFrame()
    nea30, nea_raw, nea_selection, nea_status, nea_stations = (pd.DataFrame() for _ in range(5))
    if "nea" in sources:
        nea30, nea_raw, nea_selection, nea_status, nea_stations = get_nea_month(fetcher, month, points, station_km)
    cmp = make_hourly_comparison(era, nasa)
    master = build_hourly_master(points, month, era, nasa)
    nea_wide = build_nea_wide(month, points, nea30)
    cmp_nea = make_nea_era5_comparison(master, nea_wide)
    qc = make_qc(month, points, era, nasa, nea30, nea_status, sources)
    source_rows = [
        {"source": "ERA5", "class": "REANALYSIS", "url": OPENMETEO_URL,
         "documentation": "https://open-meteo.com/en/docs/historical-weather-api",
         "time_resolution": "hourly", "rain_interval_semantics": "preceding hour [t-1h,t)",
         "wind_semantics": "10m/100m and modelled 10m gust"},
        {"source": "NASA_POWER", "class": "ANALYSIS_ESTIMATE", "url": NASA_URL,
         "documentation": "https://power.larc.nasa.gov/docs/services/api/temporal/hourly/",
         "time_resolution": "hourly", "rain_interval_semantics": "hour beginning at t, mm/hour",
         "wind_semantics": "WS10M hourly; no gust variable included"},
        {"source": "NEA", "class": "IN_SITU_SG_ONLY", "url": NEA_BASE,
         "documentation": "https://data.gov.sg/datasets/d_6580738cdd7db79374ed3152159fbd69/view",
         "time_resolution": "5min rain; 1min wind readings", "rain_interval_semantics": "5-min mm; validate alignment before publication",
         "wind_semantics": "10-min average wind (knots); not gust"},
    ]
    notes = [
        {"key": "CAUTION", "value": "No weather measurements may be invented. Blank means unavailable, not 0."},
        {"key": "GEO", "value": "These are checkpoint reference points, NOT approved UAV routes. Edit points.csv to match GIS."},
        {"key": "SG", "value": "NEA represents actual station values, not measurements at the checkpoint itself."},
        {"key": "ERA5_RAIN", "value": "Precipitation t is previous hour cumulative, explicitly marked period start/end."},
        {"key": "NASA_TIME", "value": "Request time-standard=UTC; NASA hourly time is hour START."},
        {"key": "30MIN", "value": "30min only from station observations, not interpolated hourly ERA5/NASA."},
        {"key": "GUST", "value": "NEA 10min mean wind cannot be represented as gust. Gusts via ERA5 model only."},
        {"key": "VERIFICATION", "value": "API returned values must be audited and verified with official station metadata."},
        {"key": "REANALYSIS", "value": "ERA5 is not in-situ measured data. NASA POWER is not independent station observation."},
        {"key": "STATUS", "value": "PARTIAL if any source/variable has zero coverage or incomplete NEA pagination."},
    ]
    current_audit = pd.DataFrame(fetcher.audit)
    out = fetcher.root / "processed" / f"JB_SG_Weather_{YEAR}_{month:02d}.xlsx"
    tables = {"README": pd.DataFrame(notes), "Point_Metadata": points,
              "Weather_Hourly": master, "ERA5_Hourly": era, "NASA_Hourly": nasa,
              "NEA_30min_Wide": nea_wide, "NEA_30min": nea30,
              "NEA_SelectedRaw": nea_raw, "NEA_Station_Selection": nea_selection,
              "NEA_Station_Metadata": nea_stations, "NEA_Day_Status": nea_status,
              "CrossVal_NASA": cmp, "CrossVal_NEA": cmp_nea, "QC_Coverage": qc,
              "Source_Registry": pd.DataFrame(source_rows), "API_Log": current_audit}
    write_xlsx(out, tables)
    qc_csv = out.with_suffix(".qc.csv")
    qc.to_csv(qc_csv, index=False, encoding="utf-8-sig")
    manifest = {"year": YEAR, "month": month, "run_time_utc": utc_now(), "requested_sources": sorted(sources),
                "xlsx": str(out), "bytes": out.stat().st_size,
                "era5_actual_rows": int(len(era)), "nasa_actual_rows": int(len(nasa)),
                "nea_selected_raw_rows": int(len(nea_raw)),
                "qc": qc.to_dict("records"),
                "model_and_station_data_are_not_interchangeable": True}
    out.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    LOG.info("EXPORTED %s (%.1f MB)", out, out.stat().st_size / 1048576)
    LOG.info("QC summary:\n%s", qc.to_string(index=False))
    genuine_count = (0 if era.empty else int(era["wind_speed_10m"].notna().sum())) + (0 if nasa.empty else int(nasa["WS10M"].notna().sum())) + (0 if nea_raw.empty else len(nea_raw))
    if genuine_count == 0:
        LOG.error("ZERO_REAL_OBSERVATIONS_OR_REANALYSIS: workbook contains indexes only; NOT suitable as real weather dataset")
    return out


def probe(fetcher: Fetcher, month: int, points: pd.DataFrame, sources: set[str]):
    p = points.iloc[0]
    probe_report = []
    if "openmeteo" in sources:
        df = get_era5(fetcher, month, p)
        probe_report.append({"source": "ERA5", "records": len(df), "sample": df.head(1).to_json(date_format="iso")})
    if "nasa" in sources:
        df = get_nasa(fetcher, month, p)
        probe_report.append({"source": "NASA", "records": len(df), "sample": df.head(1).to_json(date_format="iso")})
    if "nea" in sources:
        day = f"{YEAR}-{month:02d}-01"
        for kind in NEA_TYPES:
            rows, st, complete = get_nea_day(fetcher, kind, day, probe=True)
            probe_report.append({"source": f"NEA_{kind}", "first_page_rows": len(rows),
                                 "station_count": len(st), "first_page_is_complete": complete,
                                 "sample": rows[:1]})
    path = fetcher.root / f"probe_{YEAR}_{month:02d}.json"
    path.write_text(json.dumps(probe_report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(probe_report, ensure_ascii=False, indent=2, default=str))
    LOG.info("Probe report: %s", path)


def main():
    ap = argparse.ArgumentParser(description="Download real JB–SG weather for May–Sep 2026, as monthly XLSX")
    ap.add_argument("--months", type=int, nargs="+", default=[5, 6, 7, 8, 9])
    ap.add_argument("--sources", default="openmeteo,nasa,nea", help="CSV: openmeteo,nasa,nea")
    ap.add_argument("--probe", action="store_true", help="Test API response; NEA only first page of first day")
    ap.add_argument("--refresh", action="store_true", help="Redownload cached successful JSON files")
    ap.add_argument("--points", default=None, help="CSV of actual GIS checkpoints; defaults to bundled points.csv")
    ap.add_argument("--out", default=None, help="Output directory; default <project>/data/weather_2026")
    ap.add_argument("--max-station-km", type=float, default=15.0)
    ap.add_argument("--sleep", type=float, default=1.8, help="Minimum delay between API requests in seconds")
    args = ap.parse_args()
    if not set(args.months).issubset(set(range(5, 10))):
        ap.error("Only 2026 months 5,6,7,8,9 are approved in this study")
    sources = {x.strip().lower() for x in args.sources.split(",") if x.strip()}
    if not sources.issubset({"openmeteo", "nasa", "nea"}) or not sources:
        ap.error("--sources must be a nonempty subset of openmeteo,nasa,nea")
    base = Path(__file__).resolve().parents[1]
    output_root = Path(args.out).resolve() if args.out else base / "data" / "weather_2026"
    output_root.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(output_root / "download.log", encoding="utf-8")])
    points = read_points(Path(args.points).resolve() if args.points else base / "weather_pipeline" / "points.csv")
    fetcher = Fetcher(output_root, refresh=args.refresh, sleep_seconds=args.sleep)
    for month in sorted(set(args.months)):
        try:
            if args.probe:
                probe(fetcher, month, points, sources)
            else:
                run_month(fetcher, month, points, sources, args.max_station_km)
        except Exception:
            LOG.exception("MONTH_FAILED %d - continuing next month", month)
    LOG.info("All requested months attempted; check QC_Coverage and download.log before scientific use")


if __name__ == "__main__":
    main()
