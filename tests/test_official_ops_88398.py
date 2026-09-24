from pathlib import Path

import pandas as pd
import pytest

from gba_ops_reanalysis.official_ops_88398 import (
    YEARS,
    build_approved_analysis_mapping,
    build_codebook,
    build_coverage,
    build_cross_year_changes,
    classify_site_year_records,
    classify_sites_longitudinal,
    discover_catalogues,
    extract_observed_records,
    propose_classification,
    validate_approved_mapping,
)


ROOT = Path(__file__).resolve().parents[1]
CATALOGUES = ROOT / "ops_bfarm_2013_2024"
AUDIT = ROOT / "outputs" / "audit" / "tips_code_level_audit.csv"
APPROVED_OUTPUT = (
    ROOT / "outputs" / "official_ops_88398_validation_2026-07-28"
)


@pytest.fixture(scope="module")
def sources():
    return discover_catalogues(CATALOGUES)


@pytest.fixture(scope="module")
def codebook(sources):
    return build_codebook(sources, CATALOGUES)


@pytest.fixture(scope="module")
def observed():
    return extract_observed_records(AUDIT)


def test_exactly_one_official_claml_and_pdf_per_year(sources):
    assert [source.year for source in sources] == list(YEARS)
    assert all(source.xml_sha256 and source.pdf_path for source in sources)
    assert all(source.version == str(source.year) for source in sources)


def test_parent_and_ambiguous_codes_remain_unresolved(codebook):
    parent = codebook[codebook.ops_code_normalised.eq("8-839.8")]
    residual = codebook[codebook.ops_code_normalised.eq("8-839.8x")]
    assert parent.proposed_classification.eq("unresolved_parent").all()
    assert residual.proposed_classification.eq("unresolved_other").all()
    assert not codebook.officially_verified.any()


def test_official_wording_drives_conservative_proposals():
    assert propose_classification(
        "8-839.87", "Perkutanes Anlegen eines Stents", "", ""
    )[0] == "primary_placement"
    assert propose_classification(
        "8-839.84", "Einlegen in einen bestehenden Shunt", "", ""
    )[0] == "secondary_intervention"
    assert propose_classification("8-839.8x", "Sonstige", "", "")[0] == "unresolved_other"


def test_year_specific_validity_and_coverage(codebook, observed):
    coverage = build_coverage(observed, codebook)
    missing = coverage[coverage.codebook_match_count.eq(0)]
    assert len(missing) == 1
    assert missing.iloc[0].reporting_year == 2013
    assert missing.iloc[0].ops_code_normalised == "8-839.80"
    assert not codebook[
        codebook.reporting_year.eq(2013)
    ].ops_code_normalised.eq("8-839.80").any()
    assert not coverage.codebook_match_count.gt(1).any()


def test_pre_2013_records_are_excluded(observed):
    assert observed.reporting_year.min() == 2013
    assert observed.reporting_year.max() == 2024
    assert not observed.reporting_year.isin([2008, 2010, 2012]).any()


def test_visible_and_suppressed_records_remain_distinct(observed):
    assert observed.visible_numeric_value.notna().any()
    assert observed.suppression_status.any()
    unmatched = observed[
        observed.reporting_year.eq(2013)
        & observed.ops_code_normalised.eq("8-839.80")
    ]
    assert len(unmatched) == 5
    assert unmatched.suppression_status.all()
    assert unmatched.suppressed_entry_count.sum() == 7
    assert unmatched.visible_numeric_value.fillna(0).sum() == 0


def test_cross_year_wording_changes_are_flagged(codebook):
    changes = build_cross_year_changes(codebook).set_index("ops_code_normalised")
    for code in ("8-839.8", "8-839.81", "8-839.84", "8-839.86", "8-839.87",
                 "8-839.88", "8-839.89", "8-839.8a"):
        assert bool(changes.loc[code, "wording_changed"])
    assert not changes.proposed_classification_changed.any()
    assert changes.loc["8-839.89", "first_year_present"] == 2016


def approved_joined_records() -> pd.DataFrame:
    return pd.DataFrame(
        [
            [2013, "A", "1", "primary_placement", True, True, pd.NA],
            [2013, "B", "2", "secondary_intervention", True, False, 7],
            [2013, "C", "3", "primary_placement", True, True, pd.NA],
            [2013, "C", "3", "secondary_intervention", True, False, 9],
            [2013, "D", "4", "unresolved_other", True, False, 4],
            [2013, "E", "5", "unresolved_parent", True, True, pd.NA],
        ],
        columns=[
            "reporting_year", "physical_site_identifier", "ik",
            "proposed_classification", "officially_verified",
            "suppression_status", "visible_numeric_value",
        ],
    )


def test_suppressed_primary_prevents_secondary_only_and_categories_exhaustive():
    result = classify_site_year_records(approved_joined_records()).set_index(
        "physical_site_identifier"
    )
    assert result.loc["A", "site_year_classification"] == "primary_or_mixed"
    assert result.loc["C", "site_year_classification"] == "primary_or_mixed"
    assert result.loc["B", "site_year_classification"] == "definitely_secondary_only"
    assert result.loc["D", "site_year_classification"] == "unresolved"
    assert result.loc["E", "site_year_classification"] == "suppressed_only_unclassifiable"
    assert len(result) == 5


def test_site_year_rejects_pre_2013():
    records = approved_joined_records()
    records.loc[0, "reporting_year"] = 2012
    with pytest.raises(ValueError, match="before 2013"):
        classify_site_year_records(records)


def test_longitudinal_categories_are_exhaustive():
    records = approved_joined_records()
    site_years = classify_site_year_records(records)
    result = classify_sites_longitudinal(records, site_years)
    assert len(result) == records.physical_site_identifier.nunique()
    assert set(result.longitudinal_classification) == {
        "ever_primary",
        "never_primary_visible_secondary_only",
        "never_primary_unresolved",
    }


def test_pending_mapping_cannot_pass_approval_gate(codebook, observed):
    coverage = build_coverage(observed, codebook)
    with pytest.raises(ValueError):
        validate_approved_mapping(codebook, coverage)


def test_approved_mapping_is_exact_and_retains_2013_legacy_exception(
    codebook, observed
):
    mapping = build_approved_analysis_mapping(codebook)
    coverage = build_coverage(observed, mapping)
    validate_approved_mapping(mapping, coverage)

    assert len(mapping) == len(codebook) + 1
    assert not mapping.duplicated(
        ["reporting_year", "ops_code_normalised"]
    ).any()
    assert coverage.codebook_match_count.eq(1).all()

    expected = {
        **{f"8-839.8{suffix}": "secondary_intervention"
           for suffix in ("1", "2", "3", "4", "5", "6")},
        **{f"8-839.8{suffix}": "primary_placement"
           for suffix in ("7", "8", "9", "a")},
        "8-839.8": "unresolved_parent",
        "8-839.8x": "unresolved_other",
    }
    official = mapping[mapping.officially_verified.astype(bool)]
    for code, classification in expected.items():
        rows = official[official.ops_code_normalised.eq(code)]
        if len(rows):
            assert rows.analysis_classification.eq(classification).all()

    legacy = mapping[
        mapping.reporting_year.eq(2013)
        & mapping.ops_code_normalised.eq("8-839.80")
    ].iloc[0]
    assert legacy.analysis_classification == (
        "invalid_hospital_reported_legacy_code"
    )
    assert not bool(legacy.officially_verified)
    assert not bool(legacy.valid_in_reporting_year_catalogue)
    assert "Do not remap" in legacy.legacy_handling_rule


def test_invalid_legacy_cannot_independently_establish_primary_placement():
    records = pd.DataFrame(
        [
            {
                "reporting_year": 2013,
                "physical_site_identifier": "legacy-only",
                "ik": "1",
                "analysis_classification": (
                    "invalid_hospital_reported_legacy_code"
                ),
                "officially_verified": False,
                "suppression_status": True,
                "suppressed_entry_count": 2,
                "visible_numeric_value": pd.NA,
            },
            {
                "reporting_year": 2013,
                "physical_site_identifier": "legacy-plus-valid-primary",
                "ik": "2",
                "analysis_classification": (
                    "invalid_hospital_reported_legacy_code"
                ),
                "officially_verified": False,
                "suppression_status": True,
                "suppressed_entry_count": 1,
                "visible_numeric_value": pd.NA,
            },
            {
                "reporting_year": 2013,
                "physical_site_identifier": "legacy-plus-valid-primary",
                "ik": "2",
                "analysis_classification": "primary_placement",
                "officially_verified": True,
                "suppression_status": True,
                "suppressed_entry_count": 1,
                "visible_numeric_value": pd.NA,
            },
        ]
    )
    classified = classify_site_year_records(records).set_index(
        "physical_site_identifier"
    )
    assert classified.loc[
        "legacy-only", "site_year_classification"
    ] == "suppressed_only_unclassifiable"
    assert classified.loc[
        "legacy-plus-valid-primary", "site_year_classification"
    ] == "primary_or_mixed"
    assert not bool(classified.loc["legacy-only", "primary_code_present"])
    assert classified.loc[
        "legacy-only", "invalid_legacy_suppressed_entries"
    ] == 2


def test_generated_secondary_only_outputs_are_exhaustive_and_reconciled():
    site_years = pd.read_csv(
        APPROVED_OUTPUT / "secondary_only_site_years_2013_2024.csv"
    )
    sites = pd.read_csv(
        APPROVED_OUTPUT / "secondary_only_sites_longitudinal_2013_2024.csv"
    )
    reconciliation = pd.read_csv(
        APPROVED_OUTPUT / "ops_activity_reconciliation.csv"
    )
    observed = pd.read_csv(
        APPROVED_OUTPUT / "observed_ops_88398_records_2013_2024.csv"
    )

    assert site_years.reporting_year.between(2013, 2024).all()
    assert set(site_years.site_year_classification) <= {
        "primary_or_mixed",
        "definitely_secondary_only",
        "unresolved",
        "suppressed_only_unclassifiable",
    }
    assert len(site_years) == len(
        site_years.drop_duplicates(
            ["reporting_year", "physical_site_identifier", "ik"]
        )
    )
    assert sites.longitudinal_classification.notna().all()
    assert reconciliation.exact_reconciliation.astype(bool).all()
    assert int(
        reconciliation.loc[
            reconciliation.reporting_year.eq(2024),
            "post_resolution_visible_activity",
        ].iloc[0]
    ) == 5247

    definite = site_years[
        site_years.site_year_classification.eq("definitely_secondary_only")
    ]
    assert int(definite.visible_activity.max()) == 8
    assert not definite.visible_activity.ge(20).any()

    legacy = observed[
        observed.reporting_year.eq(2013)
        & observed.ops_code_normalised.eq("8-839.80")
    ]
    assert len(legacy) == 5
    assert legacy.suppression_status.astype(bool).all()
    assert int(legacy.suppressed_entry_count.sum()) == 7
    assert int(legacy.visible_numeric_value.fillna(0).sum()) == 0
    assert legacy.analysis_classification.eq(
        "invalid_hospital_reported_legacy_code"
    ).all()
    affected = site_years[
        site_years.invalid_legacy_code_present.astype(bool)
    ]
    assert len(affected) == 5
    assert affected.site_year_classification.eq("primary_or_mixed").all()
    assert affected.primary_placement_codes.str.contains(
        r"8-839\.8[78]", regex=True
    ).all()


def test_annual_visible_activity_reconciles_and_2024_is_5247():
    from gba_ops_reanalysis.site_resolution_validation import resolve_component_precedence

    audit = pd.read_csv(AUDIT, dtype={"ik": str})
    audit = audit[
        pd.to_numeric(audit.reporting_year, errors="coerce").isin(YEARS)
        & audit.OPS_code.astype(str).str.lower().str.startswith("8-839.8")
    ]
    annotated, _ = resolve_component_precedence(audit)
    actual = (
        annotated[annotated.retained_site_resolution]
        .groupby("reporting_year").visible_count.sum()
    )
    control = pd.read_csv(
        ROOT / "outputs" / "final_submission_assets_2026-07-24" / "tables"
        / "TableS1_corrected_annual_site_metrics.csv"
    )
    expected = control[
        control.provider_definition.eq("physical_site")
        & control.reporting_year.isin(YEARS)
    ].set_index("reporting_year").visible_national_activity
    pd.testing.assert_series_equal(
        actual.astype(int), expected.astype(int), check_names=False
    )
    assert int(actual.loc[2024]) == 5247
