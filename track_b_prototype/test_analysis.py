"""Checks the analysis against hand-calculated values from the case study tables."""

import unittest

import analysis as a


class TrackBAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = a.run_all()
        cls.lines = {r["line"]: r for r in cls.results["lines"]}
        cls.machines = {m["machine"]: m for m in cls.results["machines"]}
        cls.batches = {b["batch"]: b for b in cls.results["batches"]}

    def test_line_achievement(self):
        self.assertAlmostEqual(self.lines["Line 1"]["achievement"], 0.85)
        self.assertAlmostEqual(self.lines["Line 2"]["achievement"], 0.75)
        self.assertAlmostEqual(self.lines["Line 3"]["achievement"], 0.90)

    def test_line_defect_rate(self):
        self.assertAlmostEqual(self.lines["Line 1"]["defect_rate"], 34 / 850)
        self.assertAlmostEqual(self.lines["Line 2"]["defect_rate"], 81 / 900)

    def test_line_downtime_pct(self):
        self.assertAlmostEqual(self.lines["Line 1"]["downtime_pct"], 1.5 / 16)
        self.assertAlmostEqual(self.lines["Line 2"]["downtime_pct"], 2.5 / 16)

    def test_line2_is_worst_and_has_300_unit_shortfall(self):
        self.assertEqual(self.lines["Line 2"]["shortfall_units"], 300)
        self.assertEqual(min(self.lines.values(), key=lambda r: r["achievement"])["line"], "Line 2")

    def test_downtime_explains_about_331_units(self):
        total = sum(r["downtime_loss_units"] for r in self.lines.values())
        self.assertAlmostEqual(total, 331.25, places=2)

    def test_oee_estimate_is_achievement_times_quality(self):
        self.assertAlmostEqual(self.lines["Line 1"]["oee_estimate"], 0.85 * (816 / 850))

    def test_top_three_machines_are_m004_m006_m002(self):
        ranked = [m["machine"] for m in self.results["machines"]]
        self.assertEqual(ranked[:3], ["M004", "M006", "M002"])

    def test_top_three_machines_are_high_risk(self):
        for mid in ["M004", "M006", "M002"]:
            self.assertEqual(self.machines[mid]["tier"], "High")

    def test_low_machines_are_low_risk(self):
        for mid in ["M001", "M003", "M005"]:
            self.assertEqual(self.machines[mid]["tier"], "Low")

    def test_batch_material_variance_total_is_100kg(self):
        total = sum(b["variance_kg"] for b in self.batches.values())
        self.assertAlmostEqual(total, 100)

    def test_b002_is_worst_batch(self):
        worst = max(self.batches.values(), key=lambda b: b["variance_pct"])
        self.assertEqual(worst["batch"], "B002")
        self.assertAlmostEqual(worst["variance_pct"], 40 / 600)

    def test_data_checks_flag_known_inconsistencies(self):
        text = " ".join(self.results["warnings"])
        self.assertIn("Downtime mismatch", text)
        self.assertIn("Defect mismatch", text)
        self.assertIn("Batch B004", text)
        self.assertIn("30 days", text)

    def test_risk_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(a.RISK_WEIGHTS.values()), 1.0)


if __name__ == "__main__":
    unittest.main()
