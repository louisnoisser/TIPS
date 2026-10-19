from __future__ import annotations

from pathlib import Path
import unittest
import os

import pandas as pd

from gba_ops_reanalysis.final_corrected import (
    exclusive_landscape_2024,
    low_volume_denominators,
    validate_expected_totals,
)


class FinalCorrectedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.site = pd.read_csv(Path(os.environ.get("GBA_OPS_SITE_DATA", str(root / "outputs/site_resolution_validation/resolved_site_level_data.csv"))))

    def test_corrected_totals(self):
        result = validate_expected_totals(self.site)
        self.assertTrue(result["exact_match"].all())
        self.assertNotIn(2009, set(result.reporting_year))
        self.assertNotIn(2011, set(result.reporting_year))

    def test_2024_categories(self):
        table = exclusive_landscape_2024(self.site)
        self.assertEqual(table.provider_sites.sum(), 113)
        self.assertEqual(table.visible_procedural_activity.sum(), 5247)
        self.assertEqual(table.provider_sites.tolist(), [53, 29, 15, 10, 6])
        self.assertEqual(table.visible_procedural_activity.tolist(), [568, 962, 1044, 1251, 1422])

    def test_low_volume_denominators_are_separate(self):
        table = low_volume_denominators(self.site)
        self.assertEqual(set(table.reporting_year), {2008, 2024})
        self.assertEqual(
            set(table.denominator_type),
            {"openly_reported_numeric_activity", "all_identifiable_active_providers"},
        )


if __name__ == "__main__":
    unittest.main()
