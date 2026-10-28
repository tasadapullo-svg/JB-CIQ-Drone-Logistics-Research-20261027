import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "next_stage"


def test_30_seeds_and_918000_rows_are_audited():
    audit = pd.read_csv(OUT / "input_audit.csv")
    total = audit[audit["audit_level"] == "all_30_seeds"].iloc[0]
    assert int(total["row_count"]) == 918000
    assert int(total["seed_value_count_in_file"]) == 30
    assert int(total["duplicate_order_ids_across_prior_files"]) == 0
    assert int(total["unique_order_ids"]) == 918000


def test_order_integrity_fields_have_no_structural_failures():
    audit = pd.read_csv(OUT / "input_audit.csv")
    total = audit[audit["audit_level"] == "all_30_seeds"].iloc[0]
    for column in [
        "missing_release_time",
        "missing_origin",
        "missing_destination",
        "self_od",
        "unknown_site_ids",
        "missing_parcel_kg",
        "nonpositive_parcel_kg",
    ]:
        assert int(total[column]) == 0
    assert bool(total["member_sha256_matches_manifest"])


def test_road_validation_has_128_od_by_24_hours():
    road = pd.read_csv(OUT / "road_model_validation.csv")
    assert len(road) == 128 * 24
    assert set(road["departure_hour"]) == set(range(24))
    assert (pd.to_numeric(road["road_time_min"], errors="coerce").dropna() >= 0).all()


def test_ciq_wait_and_total_time_are_not_fabricated():
    road = pd.read_csv(OUT / "road_model_validation.csv")
    assert road["ciq_wait_min"].isna().all()
    assert road["total_time_min"].isna().all()
    assert road["anomaly_code"].str.contains("CIQ_WAIT_MODEL_MISSING").all()


def test_same_sample_orders_are_reused_across_modes():
    sim = pd.read_parquet(OUT / "simulation_order_results.parquet")
    order_sets = {mode: set(group["order_id"]) for mode, group in sim.groupby("mode")}
    assert set(order_sets) == {"M0", "M1", "M2"}
    assert order_sets["M0"] == order_sets["M1"] == order_sets["M2"]
    assert sim.groupby("order_id")["mode"].nunique().eq(3).all()


def test_unknown_permissions_never_release_uav_modes():
    sim = pd.read_parquet(OUT / "simulation_order_results.parquet")
    uav = sim[sim["mode"].isin(["M1", "M2"])]
    assert set(uav["service_status"]) == {"unserved"}
    assert uav["reason_code"].str.contains("NO_APPROVED_SITE_ROUTE_AIRSPACE").all()


def test_unknown_metrics_remain_null_not_zero():
    sim = pd.read_parquet(OUT / "simulation_order_results.parquet")
    for column in [
        "door_to_door_min",
        "deadline_min",
        "delay_min",
        "vehicle_km",
        "vehicle_energy_kwh",
        "drone_energy_kwh",
        "cost_total",
        "emissions_kgco2e",
    ]:
        assert sim[column].isna().all()


def test_station_unknown_is_not_marked_feasible():
    station = pd.read_csv(OUT / "station_coverage.csv")
    assert station["station_id"].isna().all()
    assert set(station["overall_scenario_eligibility"]) == {"not_released"}
    assert set(station["permit_evidence_status"]) == {"unknown_no_positive_evidence"}


def test_summary_reconciles_to_smoke_results():
    sim = pd.read_parquet(OUT / "simulation_order_results.parquet")
    summary = pd.read_csv(OUT / "simulation_run_summary.csv")
    for row in summary.itertuples(index=False):
        group = sim[(sim["scenario_id"] == row.scenario_id) & (sim["seed"] == row.seed) & (sim["mode"] == row.mode)]
        assert len(group) == row.orders_total
        assert (group["service_status"] == "unserved").sum() == row.orders_unserved
        assert (group["service_status"] == "censored").sum() == row.orders_censored


def test_manifest_records_missing_reproducibility_inputs_and_no_full_run():
    manifest = json.loads((OUT / "experiment_manifest.json").read_text(encoding="utf-8"))
    assert manifest["git_commit"] is None
    assert manifest["v55_source_referenced_by_v56_manifest"]["present"] is False
    assert manifest["full_30_seed_main_experiment_started"] is False
    assert manifest["exact_duplicate_files"][0]["same_sha256"] is True
