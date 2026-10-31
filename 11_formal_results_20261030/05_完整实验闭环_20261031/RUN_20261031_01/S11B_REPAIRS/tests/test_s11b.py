from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pandas as pd


HERE = Path(__file__).resolve()
BASE = HERE.parents[1]
PILOT = BASE / "chunks" / "PILOT2E"
spec = importlib.util.spec_from_file_location("s11b", BASE / "code" / "run_s11b.py")
s11b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s11b)


def load(name):
    return pd.read_parquet(PILOT / name)


def test_01_fixed_station_whitelist_has_11_unique_nodes():
    assert len(s11b.FIXED_STATIONS) == 11 == len(set(s11b.FIXED_STATIONS))


def test_02_m1_never_launches_from_implicit_origin():
    f = load("FLIGHTS.parquet")
    x = f[f["mode"].str.startswith("M1_")]
    assert set(x["launch_node"]).issubset(set(s11b.FIXED_STATIONS))


def test_03_every_used_vehicle_has_mandatory_return():
    l = load("GROUND_LEGS.parquet")
    for keys, g in l.groupby(["mode", "spatial_scenario", "date_local", "scenario_seed"]):
        used = set(g["vehicle_id"])
        returned = set(g.loc[g["target_event"] == "MANDATORY_RETURN_DEPOT", "vehicle_id"])
        assert used == returned, keys


def test_04_all_return_arrivals_within_24h():
    l = load("GROUND_LEGS.parquet")
    x = l[l["target_event"] == "MANDATORY_RETURN_DEPOT"].copy()
    end = pd.to_datetime(x["date_local"]).dt.tz_localize("Asia/Kuala_Lumpur") + pd.Timedelta(hours=24)
    assert (pd.to_datetime(x["arrival_local"]) <= end).all()


def test_05_soc_never_below_reserve():
    x = load("SOC_LEDGER.parquet")
    assert (x["soc_after_kwh"] + 1e-12 >= x["reserve_kwh"]).all()


def test_06_unique_physical_ids():
    l, f = load("GROUND_LEGS.parquet"), load("FLIGHTS.parquet")
    assert not l["physical_leg_id"].duplicated().any()
    assert not f["flight_id"].duplicated().any()


def test_07_order_mode_rows_complete():
    x = load("ORDER_RESULTS.parquet")
    assert len(x) == 2 * 6 * 18
    assert (x.groupby(["mode", "date_local", "scenario_seed"]).size() == 18).all()


def test_08_shared_controls_are_identical():
    x = load("ORDER_RESULTS.parquet")
    a = x[x["mode"] == "M1_NO_UAV"].sort_values(["date_local", "scenario_seed", "task_id"])
    b = x[x["mode"] == "M2_NO_UAV"].sort_values(["date_local", "scenario_seed", "task_id"])
    cols = ["task_id", "status", "delivery_local", "on_time", "service_path", "vehicle_id"]
    pd.testing.assert_frame_equal(a[cols].reset_index(drop=True), b[cols].reset_index(drop=True))


def test_09_four_weather_checks_per_flight():
    f, w = load("FLIGHTS.parquet"), load("WEATHER_LEDGER.parquet")
    assert len(w) == 4 * len(f)
    assert (w.groupby("flight_id").size() == 4).all()
    assert set(w["event"]) == {"LAUNCH", "DELIVERY", "RETURN_LAUNCH", "RECOVERY"}


def test_10_strict_flights_exclude_gt10km_weather_proxy():
    w = load("WEATHER_LEDGER.parquet")
    assert not w["grid_gt10km_warning"].astype(bool).any()


def test_11_roundtrip_event_order_is_monotone():
    f = load("FLIGHTS.parquet")
    assert (pd.to_datetime(f["launch_local"]) < pd.to_datetime(f["delivery_local"])).all()
    assert (pd.to_datetime(f["delivery_local"]) < pd.to_datetime(f["recovery_local"])).all()


def test_12_ground_leg_clock_is_monotone():
    l = load("GROUND_LEGS.parquet")
    assert (pd.to_datetime(l["departure_local"]) <= pd.to_datetime(l["arrival_local"])).all()
    assert (l["road_distance_km"] >= 0).all()


def test_13_event_clock_contains_required_events():
    e = load("EVENT_CLOCK.parquet")
    required = {"RELEASE", "PICKUP_ARRIVAL", "PICKUP_COMPLETE", "DELIVERY", "MANDATORY_RETURN_DEPOT"}
    assert required.issubset(set(e["event"]))
    if len(load("FLIGHTS.parquet")):
        assert {"LAUNCH", "RETURN_LAUNCH", "RECOVERY"}.issubset(set(e["event"]))


def test_14_energy_multiplier_changes_physical_energy():
    sp = s11b.MODELS["DJI"]
    low = s11b.energy(sp, "DJI", 5.0, 4.0, 0.8)
    high = s11b.energy(sp, "DJI", 5.0, 4.0, 1.2)
    assert high > low > 0


def test_15_headwind_symmetry():
    assert abs(s11b.headwind(10, 0, 0) - 10) < 1e-12
    assert abs(s11b.headwind(10, 180, 0) + 10) < 1e-12


def test_16_shared_control_physical_ledger_not_double_counted():
    l = load("GROUND_LEGS.parquet")
    assert set(l.loc[l["mode"].str.contains("NO_UAV"), "mode"]) == {"NO_UAV_SHARED"}


def test_17_return_launch_reloads_cross_hour_weather():
    tz = "Asia/Kuala_Lumpur"
    launch = pd.Timestamp("2026-05-01 00:54:00", tz=tz)
    def wr(gust):
        return SimpleNamespace(wind_speed_10m=0.0, wind_gusts_10m=gust, wind_direction_10m=0.0, rain=0.0, precipitation=0.0, grid_distance_m=1000.0, grid_gt10km_warning=False)
    h0 = launch.tz_convert("UTC").floor("h")
    h1 = (launch + pd.Timedelta(hours=1)).tz_convert("UTC").floor("h")
    wmap = {("A", h0): wr(0.0), ("B", h0): wr(0.0), ("A", h1): wr(0.0), ("B", h1): wr(30.0)}
    task = SimpleNamespace(parcel_kg=1.0)
    mission = {"launch_node":"A", "dest_node":"B", "oneway_km":1.1, "course":90.0, "reverse":False, "wmp":False, "cross_border":False}
    result = s11b.evaluate_flight(task, mission, s11b.MODELS["DJI"], "DJI", launch, "STRICT_EXCLUDE_GT10KM", wmap, 1.0)
    assert result["ok"] is False and result["reason"] == "WEATHER_WIND"

