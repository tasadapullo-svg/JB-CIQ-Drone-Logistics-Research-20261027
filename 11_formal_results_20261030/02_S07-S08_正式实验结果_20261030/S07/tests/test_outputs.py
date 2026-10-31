import json
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
S07 = ROOT / "S07"


class TestS07Outputs(unittest.TestCase):
    def test_weather_and_boundaries(self):
        weather = pd.read_parquet(S07 / "data" / "weather_hourly_2026_05_09.parquet")
        grid = pd.read_parquet(S07 / "data" / "era5_grid_hourly_2026_05_09.parquet")
        boundary = pd.read_csv(S07 / "data" / "QA_ERA5_BOUNDARY_ROWS.csv")
        self.assertEqual(len(weather), 14688)
        self.assertEqual(weather[["point_id", "timestamp_utc"]].drop_duplicates().shape[0], 14688)
        self.assertEqual(len(grid), 7344)
        self.assertEqual(len(boundary), 20)

    def test_fcd_full_counts_and_missing_preserved(self):
        fcd = pd.read_parquet(S07 / "data" / "fcd_hourly_345node_2026_05_09.parquet")
        self.assertEqual(len(fcd), 1266840)
        self.assertEqual(fcd["node_id"].nunique(), 345)
        self.assertEqual(fcd["timestamp_utc"].nunique(), 3672)
        counts = fcd["speed_state_recomputed"].value_counts().to_dict()
        self.assertEqual(counts, {"POSITIVE": 1141555, "MISSING": 125230, "NONPOSITIVE": 55})
        self.assertTrue(fcd.loc[fcd.speed_state_recomputed == "MISSING", "observed_speed_kmh_conditional"].isna().all())

    def test_v5_weather_road_and_orders(self):
        node_hour = pd.read_parquet(S07 / "data" / "V5_249696_NODE_HOUR_WEATHER.parquet")
        od = pd.read_parquet(S07 / "data" / "V5_68_DIRECTED_OD_MATRIX_AND_PATHS.parquet")
        orders = pd.read_parquet(S07 / "data" / "V5_TASK_TIME_WEATHER_ROAD_INDEX.parquet")
        self.assertEqual(len(node_hour), 249696)
        self.assertEqual(node_hour["node_id"].nunique(), 68)
        self.assertEqual(len(od), 68 * 68)
        self.assertEqual(len(orders), 82620)
        self.assertEqual(orders["task_id"].nunique(), 82620)
        self.assertEqual(orders[["date_local", "scenario_seed"]].drop_duplicates().shape[0], 4590)

    def test_gate_is_not_overclaimed(self):
        gates = json.loads((S07 / "qa" / "S07_GATES.json").read_text(encoding="utf-8"))
        self.assertIn(gates["S07"], {"CONDITIONAL", "HOLD"})
        self.assertNotEqual(gates["S07"], "PASS")


if __name__ == "__main__":
    unittest.main()
