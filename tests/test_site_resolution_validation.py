from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from gba_ops_reanalysis.site_resolution_validation import (
    aggregate_resolved_records,
    classify_coordinates,
    gini,
    identity_crosswalk,
    is_aggregate_99,
    parent_subcode_diagnostic,
    reporting_granularity,
    resolve_component_precedence,
    structural_metrics,
)


def row(site: str, value: int = 0, suppressed: int = 0, code: str = "8-839.88", year: int = 2024):
    return {
        "reporting_year": year, "site_identifier": site, "ik": "1", "OPS_code": code,
        "hospital_name": "Hospital X", "numeric_count": value,
        "current_parser_numeric_count": value, "suppressed_flag": suppressed > 0,
        "source_file": f"{site}.xml", "suppressed_record_count": suppressed,
        "raw_record_count": 1,
    }


class SiteResolutionTest(unittest.TestCase):
    def resolve(self, rows):
        annotated, audit = resolve_component_precedence(pd.DataFrame(rows))
        site, institution = aggregate_resolved_records(annotated)
        return annotated, audit, site, institution

    def test_aggregate_identifier(self):
        self.assertTrue(is_aggregate_99("260-99"))
        self.assertFalse(is_aggregate_99("260-00"))

    def test_exact_equal_components_precede_aggregate(self):
        _, audit, site, institution = self.resolve([row("1-99", 100), row("1-A", 60), row("1-B", 40)])
        self.assertEqual(set(site.site_identifier), {"1-A", "1-B"})
        self.assertEqual(site.visible_activity.sum(), 100)
        self.assertEqual(institution.visible_activity.sum(), 100)
        self.assertEqual(audit.iloc[0].visible_residual_source_aggregate_minus_components, 0)

    def test_residual_is_diagnostic_only(self):
        _, audit, site, _ = self.resolve([row("1-99", 103), row("1-A", 60), row("1-B", 40)])
        self.assertEqual(site.visible_activity.sum(), 100)
        self.assertEqual(audit.iloc[0].visible_residual_source_aggregate_minus_components, 3)
        self.assertEqual(len(site), 2)

    def test_suppressed_component_retained_and_interval(self):
        _, audit, site, _ = self.resolve(
            [row("1-99", 103), row("1-A", 60), row("1-B", 40), row("1-C", 0, 1)]
        )
        self.assertEqual(set(site.site_identifier), {"1-A", "1-B", "1-C"})
        self.assertEqual(tuple(audit.iloc[0][["component_total_lower", "component_total_midpoint", "component_total_upper"]]), (101, 102, 103))
        self.assertTrue(audit.iloc[0].aggregate_within_suppression_interval)

    def test_99_fallback_is_unresolved(self):
        _, _, site, _ = self.resolve([row("1-99", 100)])
        self.assertEqual(len(site), 1)
        self.assertTrue(site.iloc[0].unresolved_institution_provider)

    def test_parent_subcode_is_only_diagnostic(self):
        annotated, _, site, _ = self.resolve([row("1-A", 5, code="8-839.8"), row("1-A", 7, code="8-839.88")])
        diagnostic = parent_subcode_diagnostic(annotated)
        self.assertEqual(len(diagnostic), 1)
        self.assertEqual(site.visible_activity.sum(), 12)

    def test_structural_metrics(self):
        data = pd.DataFrame({
            "reporting_year": [2024] * 4, "visible_activity": [40, 30, 20, 10],
            "suppressed_entries": [0] * 4,
        })
        metric = structural_metrics(data, "site").iloc[0]
        self.assertEqual(metric.top5_share_pct, 100)
        self.assertAlmostEqual(metric.hhi_10000, 3000)
        self.assertAlmostEqual(metric.effective_center_count, 10 / 3, places=3)
        self.assertAlmostEqual(gini(pd.Series([10, 20, 30, 40])), 0.25)

    def test_exact_identity_change_confirmed(self):
        data = pd.DataFrame({
            "reporting_year": [2023, 2024], "site_identifier": ["A", "B"],
            "hospital_name": ["Hôpital X", "Hopital X"],
            "full_address": ["Main Str 1", "Main Str 1"],
            "address_source": ["site-specific address from source data"] * 2,
        })
        cross, review = identity_crosswalk(data, "physical_site", "site_identifier")
        self.assertEqual(cross.iloc[0].match_status, "confirmed")
        self.assertTrue(review.empty)

    def test_site_and_institution_counts_differ(self):
        _, _, site, institution = self.resolve([row("1-A", 60), row("1-B", 40)])
        self.assertEqual(len(site), 2)
        self.assertEqual(len(institution), 1)

    def test_99_to_components_is_reporting_transition(self):
        annotated, _ = resolve_component_precedence(
            pd.DataFrame([
                row("1-99", 10, year=2023),
                row("1-A", 6, year=2024),
                row("1-B", 4, year=2024),
            ])
        )
        _, transitions = reporting_granularity(annotated)
        self.assertEqual(transitions.iloc[0].transition_type, "99_only_to_component_sites")

    def test_address_and_coordinate_source_classification(self):
        _, _, site, _ = self.resolve([row("1-A", 10), row("1-99", 10, code="8-839.81")])
        site["full_address"] = site["site_identifier"].map(
            {"1-A": "Main Str 1", "1-99": "Institution Str 2"}
        )
        site["address_source"] = site["site_identifier"].map({
            "1-A": "site-specific address from source data",
            "1-99": "institution-level address from aggregate report",
        })
        site["site_full_address"] = site["site_identifier"].map({"1-A": "Main Str 1", "1-99": ""})
        site["institution_full_address"] = site["site_identifier"].map(
            {"1-A": "", "1-99": "Institution Str 2"}
        )
        cache = pd.DataFrame({
            "geocode_key": ["1-A", "1-99"], "latitude": [50.0, 51.0], "longitude": [8.0, 9.0],
            "geocode_source": ["test", "test"],
            "geocode_query": ["Main Str 1, Germany", "Institution Str 2, Germany"],
        })
        classified = classify_coordinates(site, cache).set_index("site_identifier")
        self.assertEqual(
            classified.loc["1-A", "coordinate_source_class"],
            "geocoded from a site-specific address",
        )
        self.assertEqual(
            classified.loc["1-99", "coordinate_source_class"],
            "geocoded from an institution-level address",
        )

    def test_repository_legacy_series_reproduces_exactly(self):
        root = Path(__file__).resolve().parents[1]
        code = pd.read_csv(root / "outputs/audit/tips_code_level_audit.csv")
        production = pd.read_csv(
            root / "outputs/indications/tips_8-839-8_updated2024/tables/yearly_summary.csv"
        )
        reproduced = (
            pd.to_numeric(code["current_parser_numeric_count"], errors="coerce").fillna(0)
            .groupby(code["reporting_year"]).sum().astype(int)
        )
        expected = production.set_index("year")["tips_cases_total"].astype(int)
        pd.testing.assert_series_equal(
            reproduced, expected, check_names=False, check_index_type=False
        )


if __name__ == "__main__":
    unittest.main()
