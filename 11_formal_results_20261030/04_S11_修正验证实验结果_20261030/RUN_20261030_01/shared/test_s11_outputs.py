import json
import unittest
from pathlib import Path

import pandas as pd


RUN=Path(__file__).resolve().parents[1]


class TestS11Outputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orders=pd.read_parquet(RUN/"G11_3_FAIRNESS/data/S11_ORDER_RESULTS.parquet")
        cls.scen=pd.read_csv(RUN/"G11_3_FAIRNESS/data/S11_SCENARIO_RESULTS.csv")
        cls.soc=pd.read_parquet(RUN/"G11_2_BATTERY_SOC/data/UAV_SOC_EVENT_LEDGER.parquet")
        cls.legs=pd.read_parquet(RUN/"G11_4_DUTY_ROAD/data/S11_GROUND_PHYSICAL_LEGS.parquet")

    def test_full_counts(self):
        self.assertEqual(len(self.orders),991440)
        self.assertEqual(len(self.scen),55080)

    def test_unique_keys(self):
        self.assertEqual(self.orders.duplicated(["spatial_scenario","mode","date_local","scenario_seed","task_id"]).sum(),0)
        self.assertEqual(self.legs.physical_leg_id.duplicated().sum(),0)

    def test_soc_conservation_and_reserve(self):
        self.assertLessEqual((self.soc.soc_before_kwh-self.soc.mission_kwh-self.soc.soc_after_kwh).abs().max(),1e-9)
        self.assertTrue((self.soc.soc_after_kwh+1e-9>=self.soc.reserve_kwh).all())

    def test_four_duty_reruns(self):
        d=pd.read_csv(RUN/"G11_4_DUTY_ROAD/data/DUTY_SHIFT_SENSITIVITY.csv")
        self.assertEqual(set(d.duty_hours),{8,12,24,30})
        self.assertEqual(len(d),48)

    def test_road_cache_gate(self):
        q=json.loads((RUN/"G11_4_DUTY_ROAD/qa/ROAD_CACHE_GATE.json").read_text())
        self.assertEqual(q["status"],"PASS")


if __name__=="__main__":unittest.main(verbosity=2)
