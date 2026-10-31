import json
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
S08 = ROOT / "S08" / "data"


class TestS08Outputs(unittest.TestCase):
    def test_full_denominators_and_single_result(self):
        orders = pd.read_parquet(S08 / "S08_ORDER_RESULTS.parquet")
        scenarios = pd.read_csv(S08 / "S08_SCENARIO_SUMMARY.csv")
        self.assertEqual(len(orders), 82620)
        self.assertEqual(orders["task_id"].nunique(), 82620)
        self.assertEqual(len(scenarios), 4590)

    def test_physical_leg_accounting(self):
        legs = pd.read_parquet(S08 / "S08_PHYSICAL_LEG_LEDGER.parquet")
        self.assertEqual(legs["physical_leg_count_rule"].unique().tolist(), ["COUNT_ONCE_NOT_PER_ORDER"])
        self.assertFalse(legs.duplicated(["date_local", "scenario_seed", "leg_id"]).any())
        self.assertTrue((legs["road_distance_km"] >= 0).all())

    def test_summary_is_conditional_and_co2_scope_is_explicit(self):
        summary = json.loads((S08 / "S08_SUMMARY.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["status"], "CONDITIONAL")
        self.assertEqual(summary["orders"], 82620)
        self.assertIn("TTW_CO2_ONLY", summary["co2_scope"])
        self.assertIn("COUNTED_ONCE", summary["accounting"])


if __name__ == "__main__":
    unittest.main()
