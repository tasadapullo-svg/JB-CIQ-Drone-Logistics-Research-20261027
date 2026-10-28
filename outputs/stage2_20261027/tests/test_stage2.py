import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "stage2_20261027"


def run():
    checks = {}
    diagnostics = pd.read_csv(OUT / "od_connectivity_diagnostics.csv")
    repairs = pd.read_csv(OUT / "od_route_repair_log.csv")
    road = pd.read_csv(OUT / "road_model_validation_v2.csv")
    smoke = pd.read_parquet(OUT / "smoke_order_results.parquet")
    order_audit = pd.read_csv(OUT / "order_integrity_checks.csv")
    gates = json.loads((OUT / "stage2_gates.json").read_text(encoding="utf-8"))

    checks["orders_unchanged_30_seeds_918000"] = bool(
        ((order_audit.audit_level == "all_30_seeds") & (order_audit.row_count == 918000) & (order_audit.unique_order_ids == 918000)).any()
    )
    checks["all_128_od_attributed"] = len(diagnostics) == 128 and diagnostics.od_id.nunique() == 128 and diagnostics.diagnostic_category.notna().all()
    checks["exactly_37_original_exceptions"] = len(repairs) == 37
    checks["no_formal_route_repairs_without_evidence"] = not repairs.repair_applied.astype(bool).any()
    checks["road_grid_128_x_24"] = len(road) == 3072 and set(road.departure_hour) == set(range(24))
    checks["no_negative_road_times"] = bool((pd.to_numeric(road.road_time_min, errors="coerce").dropna() >= 0).all())
    checks["ciq_not_double_counted_in_inland_od"] = road.ciq_wait_min.isna().all() and set(road.ciq_wait_applicability) == {"NOT_APPLICABLE_TO_INLAND_REFERENCE_OD"}
    checks["same_orders_all_modes"] = all(set(smoke[smoke.mode_id == mode].order_id) == set(smoke.order_id) for mode in ["M0", "M1", "M2"])
    checks["unique_smoke_primary_key"] = not smoke.duplicated(["seed_id", "order_id", "mode_id", "scenario_id"]).any()
    checks["unknown_metrics_not_fabricated"] = bool(smoke[["door_to_door_min", "cost_total", "emissions_kgco2e"]].isna().all().all())
    checks["uav_not_released_without_permission"] = bool((smoke[smoke.mode_id.isin(["M1", "M2"])].permission_status == "UNKNOWN_NO_POSITIVE_EVIDENCE").all())
    checks["full_main_experiment_not_allowed"] = gates["full_main_experiment_allowed"] is False

    checks = {name: bool(value) for name, value in checks.items()}
    failed = [name for name, value in checks.items() if not value]
    result = {"status": "PASS" if not failed else "FAIL", "passed": int(sum(checks.values())), "total": int(len(checks)), "failed": failed, "checks": checks}
    (OUT / "test_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    run()
