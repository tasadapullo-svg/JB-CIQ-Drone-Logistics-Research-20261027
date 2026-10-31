import json
import unittest
from pathlib import Path

import pandas as pd


RUN = Path(__file__).resolve().parents[1]


class FullOutputTests(unittest.TestCase):
    def test_s08a_full_ledger_and_conditional_gate(self):
        audit = json.loads((RUN / "S08A/qa/S08A_FULL_RECONCILIATION.json").read_text(encoding="utf-8"))
        gates = json.loads((RUN / "S08A/qa/S08A_GATES.json").read_text(encoding="utf-8"))
        self.assertEqual(audit["orders"]["result_rows"], 82620)
        self.assertEqual(audit["physical_ledger"]["rows"], 179010)
        self.assertEqual(audit["physical_ledger"]["duplicate_composite_keys"], 0)
        self.assertEqual(audit["events"]["rows"], 165240)
        self.assertEqual(audit["events"]["drop_before_pickup"], 0)
        self.assertEqual(gates["COMPUTATION_STATUS"], "PASS")
        self.assertEqual(gates["SCI_EVIDENCE_STATUS"], "CONDITIONAL")

    def test_s09_two_model_population_and_hold_labels(self):
        d = pd.read_parquet(RUN / "S09/data/S09_MISSION_FEASIBILITY.parquet")
        gates = json.loads((RUN / "S09/qa/S09_GATES.json").read_text(encoding="utf-8"))
        self.assertEqual(len(d), 165240)
        self.assertEqual(d.task_id.nunique(), 82620)
        self.assertEqual(set(d.model), {"DJI_FLYCART30", "WINGCOPTER198_CARGO"})
        self.assertTrue((d.groupby("model").size() == 82620).all())
        self.assertTrue((d.airspace_evidence == "UNVERIFIED_CONDITIONAL_SCENARIO").all())
        self.assertEqual(gates["VALIDATED_AIRCRAFT_ENERGY"], "HOLD")
        self.assertEqual(gates["AIRSPACE_AND_LANDING_PERMISSION"], "HOLD")

    def test_s10_complete_keys_and_physical_ledgers(self):
        q = json.loads((RUN / "S10/qa/S10_INVARIANTS.json").read_text(encoding="utf-8"))
        self.assertEqual(q["mode_order_rows"], 413100)
        self.assertEqual(q["unique_mode_order_keys"], 413100)
        self.assertEqual(q["mode_scenario_rows"], 22950)
        self.assertEqual(q["duplicate_mode_order_keys"], 0)
        self.assertEqual(q["ground_leg_duplicate_keys"], 0)
        self.assertEqual(q["flight_duplicate_ids"], 0)
        self.assertTrue(q["all_tasks_preserved"])
        self.assertTrue(q["physical_accounting_pass"])

    def test_s10_claim_boundaries(self):
        gates = json.loads((RUN / "S10/qa/S10_GATES.json").read_text(encoding="utf-8"))
        summary = pd.read_csv(RUN / "S10/data/S10_MODE_SUMMARY.csv")
        self.assertEqual(gates["S10_FULL_RUN"], "PASS_CONDITIONAL")
        self.assertEqual(gates["S10_SCI_CARBON_CLAIM"], "HOLD")
        self.assertEqual(set(summary["mode"]), {"M0_PETROL", "M1_DJI", "M1_WING", "M2_DJI", "M2_WING"})
        self.assertTrue((summary["orders"] == 82620).all())
        self.assertTrue((summary["completion_rate"] == 1.0).all())


if __name__ == "__main__":
    unittest.main(verbosity=2)
