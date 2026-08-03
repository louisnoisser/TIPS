from __future__ import annotations

from pathlib import Path
import importlib.util
import json
import unicodedata
import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

from gba_ops_reanalysis.geography_validation import (
    apply_manual_reviews,
    confirmation_is_accepted,
    normalize_address,
    query_matches_address,
    reconstruct_provider_sets,
    validate_provider_sets,
)


class GeographyValidationTest(unittest.TestCase):
    def test_output_directory_argument_is_isolated_and_default_is_preserved(self):
        root = Path(__file__).resolve().parents[1]
        runner_path = root / "scripts/run_tips_geography_validation.py"
        spec = importlib.util.spec_from_file_location("run_tips_geography_validation", runner_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)

        default_args = runner.parse_args([])
        custom = root / "outputs/geography_validation_test_isolated"
        isolated_args = runner.parse_args(["--output-dir", str(custom)])
        self.assertEqual(
            default_args.output_dir,
            root / "outputs/geography_validation_2026-07-24",
        )
        self.assertEqual(isolated_args.output_dir, custom)
        self.assertNotEqual(isolated_args.output_dir, default_args.output_dir)

    def test_unicode_and_format_normalisation(self):
        nfc = "Moorenstraße 5, 40225 Düsseldorf"
        nfd = unicodedata.normalize("NFD", "MOORENSTR. 5 40225 Düsseldorf, Germany")
        self.assertEqual(normalize_address(nfc), normalize_address(nfd))
        self.assertTrue(query_matches_address(nfd, nfc))

    def test_provider_sets_and_nesting(self):
        root = Path(__file__).resolve().parents[1]
        site = pd.read_csv(root / "outputs/site_resolution_validation/resolved_site_level_data.csv")
        providers = reconstruct_provider_sets(site)
        self.assertTrue(all(validate_provider_sets(providers).values()))

    def test_manual_review_confirms_unchanged_values_with_evidence(self):
        work = pd.DataFrame([{
            "site_identifier": "site-1", "original_address": "Moorenstraße 5, 40225 Düsseldorf",
            "normalised_address": "", "street": "Moorenstraße", "house_number": "5",
            "postal_code": "40225", "city": "Düsseldorf",
            "address_validation_status": "institution-level address only",
            "address_source_file": "source.xml", "exact_source_field_or_xml_path": "",
            "source_type": "", "latitude": 51.1959679, "longitude": 6.7898208,
            "geocode_source": "cache", "geocode_query": "Moorenstraße 5, 40225 Düsseldorf",
            "coordinate_validation_status": "institution-level coordinate only",
            "coordinate_validation_reason": "", "federal_state": "",
            "federal_state_source": "", "federal_state_status": "unresolved",
        }])
        review = pd.DataFrame([{
            "site_id": "site-1", "address_confirmation": "confirmed",
            "federal_state_confirmation": "yes", "coordinate_confirmation": "validated",
            "manual_federal_state": "Nordrhein-Westfalen",
            "evidence_source": "https://official.example/site",
        }])
        result = apply_manual_reviews(work, review).iloc[0]
        self.assertEqual(result.address_validation_status, "validated site-specific address")
        self.assertEqual(result.coordinate_validation_status, "validated physical-site coordinate")
        self.assertEqual(result.federal_state, "Nordrhein-Westfalen")
        self.assertEqual(result.latitude, 51.1959679)

    def test_manual_review_requires_evidence_and_complete_coordinate_pair(self):
        work = pd.DataFrame([{
            "site_identifier": "site-1", "original_address": "Teststraße 1, 12345 Test",
            "normalised_address": "", "street": "Teststraße", "house_number": "1",
            "postal_code": "12345", "city": "Test",
            "address_validation_status": "institution-level address only",
            "address_source_file": "", "exact_source_field_or_xml_path": "", "source_type": "",
            "latitude": 1.0, "longitude": 2.0, "geocode_source": "", "geocode_query": "",
            "coordinate_validation_status": "institution-level coordinate only",
            "coordinate_validation_reason": "", "federal_state": "",
            "federal_state_source": "", "federal_state_status": "unresolved",
        }])
        review = pd.DataFrame([{
            "site_id": "site-1", "address_confirmation": "yes",
            "coordinate_confirmation": "yes", "manual_latitude": "50.0",
        }])
        result = apply_manual_reviews(work, review).iloc[0]
        self.assertEqual(result.address_validation_status, "institution-level address only")
        self.assertEqual(result.coordinate_validation_status, "institution-level coordinate only")
        self.assertTrue(confirmation_is_accepted(" Confirmed "))


class Ge100ReleasePackageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.old = cls.root / "outputs/geography_validation_2026-07-24"
        cls.out = cls.root / "outputs/geography_validation_ge100_2026-07-24"
        cls.completed = pd.read_csv(
            cls.out / "geography_manual_review_ge20_2024_ge100_completed.csv",
            dtype={"ik": str, "site_id": str},
            keep_default_na=False,
        )
        cls.master = pd.read_csv(
            cls.out / "provider_locations_master_2024.csv",
            dtype={"ik": str, "site_id": str, "postcode": str},
        )

    def test_only_priority_one_review_rows_changed(self):
        original = pd.read_csv(
            self.old / "geography_manual_review_ge20_2024_original.csv",
            dtype={"ik": str, "site_id": str},
            keep_default_na=False,
        )
        self.assertEqual(len(original), 60)
        self.assertEqual(len(self.completed), 60)
        unchanged_ids = original.loc[
            original.manual_review_priority.ne(1), "site_id"
        ].tolist()
        self.assertEqual(len(unchanged_ids), 44)
        assert_frame_equal(
            original[original.site_id.isin(unchanged_ids)].reset_index(drop=True),
            self.completed[self.completed.site_id.isin(unchanged_ids)].reset_index(drop=True),
            check_dtype=False,
        )

    def test_ge100_membership_and_validation_are_complete(self):
        sites = self.master[self.master.threshold_ge100].copy()
        self.assertEqual(len(sites), 16)
        self.assertEqual(sites.site_id.nunique(), 16)
        self.assertTrue(
            sites.address_validation_status.eq("validated site-specific address").all()
        )
        self.assertTrue(sites.federal_state_status.str.startswith("validated").all())
        self.assertTrue(
            sites.coordinate_status.eq("validated physical-site coordinate").all()
        )
        self.assertTrue(sites.postcode.astype(str).str.fullmatch(r"\d{5}").all())
        self.assertTrue(sites.city.fillna("").str.strip().ne("").all())
        self.assertFalse(sites[["latitude", "longitude"]].duplicated().any())

    def test_routing_and_figure_data_include_every_site(self):
        audit = pd.read_csv(
            self.out / "accessibility_ge100_routing_audit.csv",
            dtype={"site_id": str},
            keep_default_na=False,
        )
        self.assertEqual(len(audit), 16)
        self.assertEqual(audit.site_id.nunique(), 16)
        self.assertTrue(audit.routed_30m.all())
        self.assertTrue(audit.routed_60m.all())
        self.assertTrue(audit.routing_error.eq("").all())

        features = json.loads(
            (self.out / "accessibility_ge100_site_isochrones.geojson").read_text(
                encoding="utf-8"
            )
        )["features"]
        self.assertEqual(len(features), 32)
        self.assertEqual(
            {feature["properties"]["site_id"] for feature in features},
            set(audit.site_id),
        )
        self.assertEqual(
            {feature["properties"]["time_minutes"] for feature in features},
            {30, 60},
        )
        for suffix in ("png", "pdf", "svg"):
            figure = self.out / "figures" / f"ge100_validated_accessibility.{suffix}"
            self.assertTrue(figure.is_file())
            self.assertGreater(figure.stat().st_size, 0)


class Ge50ReleasePackageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.ge100 = cls.root / "outputs/geography_validation_ge100_2026-07-24"
        cls.out = cls.root / "outputs/geography_validation_ge50_2026-07-24"
        cls.baseline = pd.read_csv(
            cls.ge100 / "geography_manual_review_ge20_2024_ge100_completed.csv",
            dtype=str,
            keep_default_na=False,
        )
        cls.completed = pd.read_csv(
            cls.out / "geography_manual_review_ge20_2024_ge50_completed.csv",
            dtype=str,
            keep_default_na=False,
        )
        cls.master = pd.read_csv(
            cls.out / "provider_locations_master_2024.csv",
            dtype={"ik": str, "site_id": str, "postcode": str},
        )

    def test_priority_one_and_three_rows_remain_unchanged(self):
        self.assertEqual(len(self.baseline), 60)
        self.assertEqual(len(self.completed), 60)
        for priority, expected in (("1", 16), ("3", 29)):
            before = self.baseline[self.baseline.manual_review_priority == priority]
            after = self.completed[self.completed.manual_review_priority == priority]
            self.assertEqual(len(before), expected)
            assert_frame_equal(
                before.reset_index(drop=True),
                after.reset_index(drop=True),
                check_dtype=False,
            )
        self.assertTrue(self.baseline.site_id.equals(self.completed.site_id))
        self.assertTrue(
            self.baseline.visible_activity.equals(self.completed.visible_activity)
        )

    def test_priority_two_evidence_and_corrections_are_exact(self):
        evidence = pd.read_csv(
            self.out / "ge50_manual_validation_evidence.csv",
            dtype={"ik": str, "site_id": str, "verified_postcode": str},
        )
        reviewed = self.completed[self.completed.manual_review_priority == "2"]
        self.assertEqual(len(reviewed), 15)
        self.assertEqual(len(evidence), 15)
        self.assertTrue(
            reviewed[
                [
                    "address_confirmation",
                    "federal_state_confirmation",
                    "coordinate_confirmation",
                ]
            ].eq("validated").all().all()
        )
        self.assertTrue(reviewed.evidence_source.str.strip().ne("").all())
        self.assertEqual(int(evidence.address_changed.sum()), 1)
        self.assertEqual(int(evidence.coordinate_changed.sum()), 0)
        magdeburg = evidence[evidence.site_id == "261500289-773667000"].iloc[0]
        self.assertEqual(
            magdeburg.verified_address,
            "Leipziger Straße 44, 39120 Magdeburg",
        )

    def test_ge50_and_ge100_release_gates_are_complete(self):
        for threshold, expected in ((50, 31), (100, 16)):
            sites = self.master[self.master[f"threshold_ge{threshold}"]]
            self.assertEqual(len(sites), expected)
            self.assertEqual(sites.site_id.nunique(), expected)
            self.assertTrue(
                sites.address_validation_status.eq(
                    "validated site-specific address"
                ).all()
            )
            self.assertTrue(
                sites.federal_state_status.str.startswith("validated").all()
            )
            self.assertTrue(
                sites.coordinate_status.eq(
                    "validated physical-site coordinate"
                ).all()
            )
            self.assertFalse(sites[["latitude", "longitude"]].duplicated().any())

    def test_routing_population_and_accessibility_are_consistent(self):
        audit = pd.read_csv(
            self.out / "accessibility_ge50_ge100_routing_audit.csv",
            dtype={"site_id": str},
            keep_default_na=False,
        )
        final = pd.read_csv(
            self.out / "accessibility_ge50_ge100_final.csv"
        )
        self.assertEqual(len(audit), 31)
        self.assertEqual(audit.site_id.nunique(), 31)
        self.assertEqual(int(audit.member_ge100.sum()), 16)
        self.assertTrue(audit.routed_30m.all())
        self.assertTrue(audit.routed_60m.all())
        self.assertTrue(audit.routing_error.eq("").all())
        self.assertEqual(set(final.threshold), {50, 100})
        self.assertTrue(final.failed_routing_sites.eq(0).all())
        self.assertTrue(
            final.germany_population_denominator.eq(83_194_667).all()
        )
        ge100 = final[final.threshold == 100].set_index("time_minutes")
        self.assertEqual(int(ge100.at[30, "covered_population"]), 16_035_551)
        self.assertEqual(int(ge100.at[60, "covered_population"]), 48_597_532)
        for minutes in (30, 60):
            ge50_population = int(
                final[
                    (final.threshold == 50) & (final.time_minutes == minutes)
                ].covered_population.iloc[0]
            )
            self.assertGreater(
                ge50_population,
                int(ge100.at[minutes, "covered_population"]),
            )

    def test_state_table_figure_data_and_table_s5_are_consistent(self):
        state = pd.read_csv(
            self.out / "federal_state_distribution_ge50_ge100_2024.csv",
            dtype={"provider_identifiers": str},
        )
        self.assertEqual(len(state), 32)
        for threshold, expected in ((50, 31), (100, 16)):
            rows = state[state.threshold == threshold]
            sites = self.master[self.master[f"threshold_ge{threshold}"]]
            self.assertEqual(int(rows.provider_count.sum()), expected)
            self.assertEqual(
                int(rows.visible_activity.sum()),
                int(sites.visible_activity.sum()),
            )
            self.assertTrue(rows.national_visible_activity.eq(5_247).all())
            self.assertAlmostEqual(
                rows.share_of_network_visible_activity_pct.sum(),
                100.0,
                places=1,
            )
        zero_rows = state[state.provider_count == 0]
        self.assertTrue(
            zero_rows.interpretation.str.contains(
                "does not imply absence", regex=False
            ).all()
        )

        features = json.loads(
            (
                self.out
                / "accessibility_ge50_ge100_site_isochrones.geojson"
            ).read_text(encoding="utf-8")
        )["features"]
        self.assertEqual(len(features), 62)
        self.assertEqual(
            {feature["properties"]["time_minutes"] for feature in features},
            {30, 60},
        )
        self.assertEqual(
            sum(
                feature["properties"]["member_ge100"]
                for feature in features
                if feature["properties"]["time_minutes"] == 30
            ),
            16,
        )
        for suffix in ("png", "pdf", "svg"):
            figure = (
                self.out
                / "figures"
                / f"ge50_ge100_validated_accessibility.{suffix}"
            )
            self.assertTrue(figure.is_file())
            self.assertGreater(figure.stat().st_size, 0)
        table_s5 = pd.read_csv(
            self.out / "tables/table_s5_ge50_ge100.csv"
        )
        self.assertEqual(len(table_s5), 4)
        self.assertEqual(set(table_s5.threshold), {50, 100})
        self.assertTrue(table_s5.final_validation_status.eq("released").all())


if __name__ == "__main__":
    unittest.main()
