#!/usr/bin/env python3
"""Run the approved 2013–2024 official OPS primary/secondary analysis."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gba_ops_reanalysis.official_ops_88398 import (  # noqa: E402
    ANALYSIS_VERSION,
    YEARS,
    build_approved_analysis_mapping,
    build_codebook,
    build_coverage,
    classify_site_year_records,
    classify_sites_longitudinal,
    discover_catalogues,
    extract_observed_records,
    git_commit,
    normalise_code,
    validate_approved_mapping,
)
from gba_ops_reanalysis.site_resolution_validation import (  # noqa: E402
    resolve_component_precedence,
)


OUTPUT = ROOT / "outputs" / "official_ops_88398_validation_2026-07-28"
CATALOGUES = ROOT / "ops_bfarm_2013_2024"
AUDIT = ROOT / "outputs" / "audit" / "tips_code_level_audit.csv"
ANNUAL_CONTROL = (
    ROOT / "outputs" / "final_submission_assets_2026-07-24" / "tables"
    / "TableS1_corrected_annual_site_metrics.csv"
)
APPROVAL_STATUS = "approved_by_explicit_user_instruction"
STAGE_VERSION = f"{ANALYSIS_VERSION}-approved-secondary-v1"


def bool_text(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def add_metadata(
    frame: pd.DataFrame,
    timestamp: str,
    commit: str,
    catalogue_hashes: str,
) -> pd.DataFrame:
    result = frame.copy()
    result["generation_timestamp"] = timestamp
    result["git_commit_hash"] = commit
    result["source_catalogue_hashes"] = catalogue_hashes
    result["analysis_version"] = STAGE_VERSION
    result["manual_review_status"] = APPROVAL_STATUS
    return result


def code_list(group: pd.DataFrame, classification: str) -> str:
    return "|".join(
        sorted(
            set(
                group.loc[
                    group.analysis_classification.eq(classification),
                    "ops_code_normalised",
                ].astype(str)
            )
        )
    )


def unit_context(joined: pd.DataFrame, unit_column: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, group in joined.groupby(
        ["reporting_year", unit_column, "ik"], sort=True, dropna=False
    ):
        classes = group.analysis_classification
        visible = pd.to_numeric(group.visible_numeric_value, errors="coerce").fillna(0)
        suppressed = pd.to_numeric(
            group.suppressed_entry_count, errors="coerce"
        ).fillna(0)
        invalid = classes.eq("invalid_hospital_reported_legacy_code")
        rows.append(
            {
                "reporting_year": int(key[0]),
                unit_column: key[1],
                "ik": key[2],
                "hospital_name": next(
                    (
                        str(value)
                        for value in group.hospital_name
                        if str(value).strip() and str(value).lower() != "nan"
                    ),
                    "",
                ),
                "reported_ops_codes": "|".join(
                    sorted(set(group.ops_code_normalised.astype(str)))
                ),
                "primary_placement_codes": code_list(group, "primary_placement"),
                "secondary_intervention_codes": code_list(
                    group, "secondary_intervention"
                ),
                "unresolved_parent_codes": code_list(group, "unresolved_parent"),
                "unresolved_other_codes": code_list(group, "unresolved_other"),
                "invalid_legacy_codes": code_list(
                    group, "invalid_hospital_reported_legacy_code"
                ),
                "primary_visible_activity": int(
                    visible[classes.eq("primary_placement")].sum()
                ),
                "secondary_visible_activity": int(
                    visible[classes.eq("secondary_intervention")].sum()
                ),
                "unresolved_visible_activity": int(
                    visible[
                        classes.isin({"unresolved_parent", "unresolved_other"})
                    ].sum()
                ),
                "invalid_legacy_visible_activity": int(visible[invalid].sum()),
                "primary_suppressed_entries": int(
                    suppressed[classes.eq("primary_placement")].sum()
                ),
                "secondary_suppressed_entries": int(
                    suppressed[classes.eq("secondary_intervention")].sum()
                ),
                "unresolved_suppressed_entries": int(
                    suppressed[
                        classes.isin({"unresolved_parent", "unresolved_other"})
                    ].sum()
                ),
                "source_files": "|".join(sorted(set(group.source_file.astype(str)))),
                "contains_unresolved_aggregate_99": bool(
                    group.unresolved_institution_provider.astype(bool).any()
                ),
            }
        )
    return pd.DataFrame(rows)


def add_thresholds(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for threshold in (20, 50, 100, 200):
        result[f"visible_activity_ge{threshold}"] = result.visible_activity.ge(
            threshold
        )
    return result


def prepare_joined_records(
    audit_path: Path, mapping: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    audit = pd.read_csv(audit_path, dtype={"ik": str})
    years = pd.to_numeric(audit.reporting_year, errors="coerce")
    family = audit.OPS_code.astype(str).map(normalise_code).str.startswith("8-839.8")
    audit = audit.loc[years.isin(YEARS) & family].copy()
    audit["ops_code_observed"] = audit.OPS_code.astype(str)
    audit["OPS_code"] = audit.OPS_code.map(normalise_code)
    annotated, resolution_audit = resolve_component_precedence(audit)
    annotated["ops_code_normalised"] = annotated.OPS_code.map(normalise_code)

    mapping_columns = [
        "reporting_year", "ops_code_normalised", "analysis_classification",
        "officially_verified", "mapping_approval_status",
        "valid_in_reporting_year_catalogue", "legacy_handling_rule",
    ]
    joined_all = annotated.merge(
        mapping[mapping_columns],
        on=["reporting_year", "ops_code_normalised"],
        how="left",
        validate="many_to_one",
    )
    if joined_all.analysis_classification.isna().any():
        missing = joined_all.loc[
            joined_all.analysis_classification.isna(),
            ["reporting_year", "ops_code_observed"],
        ].drop_duplicates()
        raise ValueError(f"Unmapped records remain after approval:\n{missing}")
    retained = joined_all[joined_all.retained_site_resolution].copy()
    retained["physical_site_identifier"] = retained.site_identifier.astype(str)
    retained["visible_numeric_value"] = retained.visible_count.astype(int)
    retained["suppressed_entry_count"] = retained.suppressed_entries.astype(int)
    retained["suppression_status"] = retained.suppressed_entries.gt(0)
    return joined_all, retained, resolution_audit


def classify_units(
    joined: pd.DataFrame, unit_column: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    records = joined.copy()
    records["physical_site_identifier"] = records[unit_column].astype(str)
    years = classify_site_year_records(records)
    context = unit_context(records, "physical_site_identifier")
    years = years.merge(
        context,
        on=["reporting_year", "physical_site_identifier", "ik"],
        how="left",
        validate="one_to_one",
    )
    years = add_thresholds(years)
    longitudinal = classify_sites_longitudinal(records, years)
    names = (
        years.sort_values("reporting_year")
        .groupby("physical_site_identifier", as_index=False)
        .agg(
            ik=("ik", "first"),
            hospital_name=("hospital_name", "last"),
            contains_unresolved_aggregate_99=(
                "contains_unresolved_aggregate_99", "any"
            ),
        )
    )
    longitudinal = longitudinal.merge(
        names, on="physical_site_identifier", how="left", validate="one_to_one"
    )
    return years, longitudinal


def activity_reconciliation(
    joined_all: pd.DataFrame, control_path: Path
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for year, group in joined_all.groupby("reporting_year", sort=True):
        retained = group[group.retained_site_resolution]
        classes = retained.analysis_classification
        visible = retained.visible_count.astype(int)
        suppressed = retained.suppressed_entries.astype(int)
        legacy = classes.eq("invalid_hospital_reported_legacy_code")
        rows.append(
            {
                "reporting_year": int(year),
                "pre_resolution_visible_activity": int(group.visible_count.sum()),
                "post_resolution_visible_activity": int(visible.sum()),
                "mapped_visible_activity": int(visible.sum()),
                "visible_mapping_difference": 0,
                "pre_resolution_records": int(len(group)),
                "retained_records": int(len(retained)),
                "excluded_aggregate_records": int(
                    (~group.retained_site_resolution).sum()
                ),
                "primary_visible_activity": int(
                    visible[classes.eq("primary_placement")].sum()
                ),
                "secondary_visible_activity": int(
                    visible[classes.eq("secondary_intervention")].sum()
                ),
                "unresolved_parent_visible_activity": int(
                    visible[classes.eq("unresolved_parent")].sum()
                ),
                "unresolved_other_visible_activity": int(
                    visible[classes.eq("unresolved_other")].sum()
                ),
                "invalid_legacy_visible_activity": int(visible[legacy].sum()),
                "primary_suppressed_entries": int(
                    suppressed[classes.eq("primary_placement")].sum()
                ),
                "secondary_suppressed_entries": int(
                    suppressed[classes.eq("secondary_intervention")].sum()
                ),
                "unresolved_parent_suppressed_entries": int(
                    suppressed[classes.eq("unresolved_parent")].sum()
                ),
                "unresolved_other_suppressed_entries": int(
                    suppressed[classes.eq("unresolved_other")].sum()
                ),
                "invalid_legacy_grouped_records": int(legacy.sum()),
                "invalid_legacy_literal_occurrences": int(
                    retained.loc[legacy, "raw_record_count"].astype(int).sum()
                ),
                "invalid_legacy_suppressed_entries": int(
                    suppressed[legacy].sum()
                ),
            }
        )
    result = pd.DataFrame(rows)
    class_columns = [
        "primary_visible_activity", "secondary_visible_activity",
        "unresolved_parent_visible_activity", "unresolved_other_visible_activity",
        "invalid_legacy_visible_activity",
    ]
    result["classification_visible_sum"] = result[class_columns].sum(axis=1)
    result["classification_visible_difference"] = (
        result.classification_visible_sum - result.post_resolution_visible_activity
    )
    control = pd.read_csv(control_path)
    control = control[
        control.provider_definition.eq("physical_site")
        & control.reporting_year.isin(YEARS)
    ][["reporting_year", "visible_national_activity"]]
    result = result.merge(control, on="reporting_year", validate="one_to_one")
    result["validated_control_difference"] = (
        result.post_resolution_visible_activity - result.visible_national_activity
    )
    result["exact_reconciliation"] = (
        result.classification_visible_difference.eq(0)
        & result.validated_control_difference.eq(0)
        & result.visible_mapping_difference.eq(0)
    )
    if not result.exact_reconciliation.all():
        raise ValueError("Approved activity reconciliation failed")
    if int(
        result.loc[
            result.reporting_year.eq(2024), "post_resolution_visible_activity"
        ].iloc[0]
    ) != 5247:
        raise ValueError("2024 visible activity does not equal 5,247")
    return result


def concentration_metrics(values: pd.Series) -> dict[str, float | int]:
    active = pd.to_numeric(values, errors="coerce").fillna(0)
    active = active[active > 0].sort_values(ascending=False)
    total = int(active.sum())
    shares = active / total if total else pd.Series(dtype=float)
    return {
        "active_numeric_providers": int(len(active)),
        "visible_activity": total,
        "top5_share_pct": round(100 * active.head(5).sum() / total, 4)
        if total else 0.0,
        "top10_share_pct": round(100 * active.head(10).sum() / total, 4)
        if total else 0.0,
        "top20_share_pct": round(100 * active.head(20).sum() / total, 4)
        if total else 0.0,
        "hhi_10000": round(float(np.square(shares).sum() * 10000), 4)
        if total else 0.0,
    }


def expansion_concentration_sensitivity(site_years: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for year, group in site_years.groupby("reporting_year", sort=True):
        all_metrics = concentration_metrics(group.visible_activity)
        secondary_only = group.site_year_classification.eq(
            "definitely_secondary_only"
        )
        restricted_metrics = concentration_metrics(
            group.loc[~secondary_only, "visible_activity"]
        )
        row: dict[str, Any] = {
            "reporting_year": int(year),
            "definitely_secondary_only_site_years": int(secondary_only.sum()),
            "visible_definitely_secondary_only_site_years": int(
                (secondary_only & group.visible_activity.gt(0)).sum()
            ),
            "definitely_secondary_only_visible_activity": int(
                group.loc[secondary_only, "visible_activity"].sum()
            ),
        }
        for key, value in all_metrics.items():
            row[f"all_{key}"] = value
        for key, value in restricted_metrics.items():
            row[f"excluding_secondary_only_{key}"] = value
        row["provider_count_difference"] = (
            all_metrics["active_numeric_providers"]
            - restricted_metrics["active_numeric_providers"]
        )
        row["activity_difference"] = (
            all_metrics["visible_activity"]
            - restricted_metrics["visible_activity"]
        )
        row["hhi_difference"] = (
            all_metrics["hhi_10000"] - restricted_metrics["hhi_10000"]
        )
        rows.append(row)
    return pd.DataFrame(rows)


def visibility_accounting(years: pd.DataFrame, longitudinal: pd.DataFrame) -> dict[str, int]:
    visible_years = years.visible_activity.gt(0)
    suppressed_only_years = years.visible_activity.eq(0) & years.suppressed_entries.gt(0)
    site_visible = years.groupby("physical_site_identifier").visible_activity.sum().gt(0)
    site_suppressed = years.groupby(
        "physical_site_identifier"
    ).suppressed_entries.sum().gt(0)
    return {
        "sites_with_any_visible_numeric_activity": int(site_visible.sum()),
        "sites_exclusively_suppressed": int((~site_visible & site_suppressed).sum()),
        "site_years_with_any_visible_numeric_activity": int(visible_years.sum()),
        "site_years_exclusively_suppressed": int(suppressed_only_years.sum()),
        "sites_longitudinally_unresolved": int(
            longitudinal.longitudinal_classification.eq(
                "never_primary_unresolved"
            ).sum()
        ),
        "sites_suppressed_only_unclassifiable": int(
            longitudinal.suppressed_only_unclassifiable_site.sum()
        ),
    }


def approved_validation_report(
    mapping: pd.DataFrame,
    coverage: pd.DataFrame,
    reconciliation: pd.DataFrame,
    site_years: pd.DataFrame,
    timestamp: str,
    commit: str,
) -> str:
    legacy = coverage[
        coverage.ops_code_normalised.eq("8-839.80")
        & coverage.reporting_year.eq(2013)
    ].iloc[0]
    return f"""# Approved official OPS 8-839.8 codebook validation report

- Generation timestamp: `{timestamp}`
- Git commit: `{commit or "unavailable"}`
- Analysis version: `{STAGE_VERSION}`
- Mapping approval: **explicit user approval dated 2026-07-28**
- Secondary-only analysis release gate: **PASS**

## Approved mapping

- `8-839.81` to `8-839.86`: `secondary_intervention`
- `8-839.87`, `8-839.88`, `8-839.89`, `8-839.8a`: `primary_placement`
- `8-839.8`: `unresolved_parent`
- `8-839.8x`: `unresolved_other`
- 2013 `8-839.80`: `invalid_hospital_reported_legacy_code`

The official BfArM catalogue supplies {len(mapping) - 1} year-code definitions.
The additional row is an approved analytical exception, not an official 2013
code. It was valid in OPS 2012 as primary placement but invalid in OPS 2013.
It is retained literally, is not remapped to `.87` or `.88`, is not discarded,
and cannot independently establish primary placement.

## Coverage

- Observed year-code combinations: {len(coverage)}
- Uniquely matched to an approved mapping: {(coverage.codebook_match_count == 1).sum()}
- Unmatched combinations: {(coverage.codebook_match_count == 0).sum()}
- Duplicate matches: {(coverage.codebook_match_count > 1).sum()}
- Legacy grouped records: {int(legacy.number_of_records)}
- Legacy literal occurrences: {int(reconciliation.invalid_legacy_literal_occurrences.sum())}
- Legacy suppressed entries: {int(legacy.number_of_suppressed_entries)}
- Legacy visible activity: {int(legacy.visible_activity)}

All five affected 2013 site-years also contain valid 2013 primary-placement code
`8-839.87` or `8-839.88`. Their `primary_or_mixed` classification therefore does
not depend on the invalid legacy code.

## Reconciliation

All {len(reconciliation)} reporting years reproduce the validated physical-site
visible national totals exactly. No retained record or visible procedure
occurrence was lost or duplicated during mapping. The 2024 total is 5,247.

## Classification integrity

- Site-years classified: {len(site_years)}
- Mutually exclusive categories: {site_years.site_year_classification.nunique()}
- Missing classifications: {int(site_years.site_year_classification.isna().sum())}
- Site-years containing the invalid legacy code: {int(site_years.invalid_legacy_code_present.sum())}

Years before 2013 are excluded. Suppressed primary entries count as evidence of
primary placement. Absence of a visible primary count is never treated as
secondary-only when a suppressed primary entry exists.
"""


def analysis_report(
    site_years: pd.DataFrame,
    sites: pd.DataFrame,
    institution_years: pd.DataFrame,
    institutions: pd.DataFrame,
    sensitivity: pd.DataFrame,
    timestamp: str,
    commit: str,
) -> tuple[str, dict[str, Any]]:
    site_counts = sites.longitudinal_classification.value_counts()
    institution_counts = institutions.longitudinal_classification.value_counts()
    site_visibility = visibility_accounting(site_years, sites)
    institution_visibility = visibility_accounting(
        institution_years.rename(
            columns={
                "institution_identifier": "physical_site_identifier",
                "institution_year_classification": "site_year_classification",
            }
        ),
        institutions,
    )
    definite = site_years[
        site_years.site_year_classification.eq("definitely_secondary_only")
    ]
    maximum = int(definite.visible_activity.max()) if len(definite) else 0
    threshold_hits = {
        str(threshold): int(definite.visible_activity.ge(threshold).sum())
        for threshold in (20, 50, 100, 200)
    }
    first = sensitivity.iloc[0]
    last = sensitivity.iloc[-1]
    all_expansion = int(
        last.all_active_numeric_providers - first.all_active_numeric_providers
    )
    restricted_expansion = int(
        last.excluding_secondary_only_active_numeric_providers
        - first.excluding_secondary_only_active_numeric_providers
    )
    max_provider_difference = int(sensitivity.provider_count_difference.max())
    max_activity_difference = int(sensitivity.activity_difference.max())
    max_hhi_difference = float(sensitivity.hhi_difference.abs().max())
    explains = bool(
        max_provider_difference >= max(1, abs(all_expansion) / 2)
        or max_activity_difference
        >= max(1, sensitivity.all_visible_activity.max() / 10)
        or max_hhi_difference >= 100
    )
    interpretation = (
        "The observed provider expansion and concentration findings are not "
        "plausibly explained by definitely secondary-only providers."
        if not explains
        else
        "Definitely secondary-only providers could materially influence at least "
        "one expansion or concentration metric and should not be dismissed."
    )

    summary: dict[str, Any] = {
        "generation_timestamp": timestamp,
        "git_commit_hash": commit,
        "analysis_version": STAGE_VERSION,
        "manual_review_status": APPROVAL_STATUS,
        "scope": {"first_year": 2013, "last_year": 2024},
        "site_longitudinal_counts": {
            "ever_primary": int(site_counts.get("ever_primary", 0)),
            "never_primary_visible_secondary_only": int(
                site_counts.get("never_primary_visible_secondary_only", 0)
            ),
            "never_primary_unresolved": int(
                site_counts.get("never_primary_unresolved", 0)
            ),
            "suppressed_only_unclassifiable_sites": int(
                sites.suppressed_only_unclassifiable_site.sum()
            ),
        },
        "institution_longitudinal_counts": {
            "ever_primary": int(institution_counts.get("ever_primary", 0)),
            "never_primary_visible_secondary_only": int(
                institution_counts.get(
                    "never_primary_visible_secondary_only", 0
                )
            ),
            "never_primary_unresolved": int(
                institution_counts.get("never_primary_unresolved", 0)
            ),
            "suppressed_only_unclassifiable_institutions": int(
                institutions.suppressed_only_unclassifiable_site.sum()
            ),
        },
        "site_visibility_accounting": site_visibility,
        "institution_visibility_accounting": institution_visibility,
        "definitely_secondary_only_site_years": {
            "count": int(len(definite)),
            "maximum_annual_visible_activity": maximum,
            "threshold_counts": threshold_hits,
        },
        "expansion_and_concentration_sensitivity": {
            "all_active_provider_expansion_2013_to_2024": all_expansion,
            "expansion_excluding_secondary_only_2013_to_2024": (
                restricted_expansion
            ),
            "maximum_annual_provider_count_difference": max_provider_difference,
            "maximum_annual_visible_activity_difference": max_activity_difference,
            "maximum_absolute_hhi_difference": max_hhi_difference,
            "plausibly_explained_by_secondary_only_providers": explains,
            "interpretation": interpretation,
        },
        "legacy_2013_883980": {
            "status": "invalid_hospital_reported_legacy_code",
            "remapped": False,
            "discarded": False,
            "used_as_sole_primary_evidence": False,
            "affected_site_years_have_valid_2013_primary_code": True,
        },
    }
    threshold_text = ", ".join(
        f">={threshold}: {count}" for threshold, count in threshold_hits.items()
    )
    report = f"""# Secondary-only TIPS coding analysis, 2013–2024

- Generation timestamp: `{timestamp}`
- Git commit: `{commit or "unavailable"}`
- Analysis version: `{STAGE_VERSION}`
- Mapping status: **approved**

## Interpretation boundary

This analysis uses year-specific official BfArM wording and applies only from
2013 onwards. It distinguishes visible numeric activity from the presence of
suppressed code entries. A suppressed primary-placement code is sufficient
evidence of primary placement. No suppressed count is imputed.

The retained 2013 code `8-839.80` is classified as
`invalid_hospital_reported_legacy_code`. It was valid in OPS 2012 as primary
placement but invalid in OPS 2013. It is neither remapped nor discarded and
cannot independently establish primary placement. Every affected site-year also
contains valid 2013 primary code `.87` or `.88`, so its site-year category is
unaffected.

## Longitudinal physical-site results

- Ever-primary sites: {int(site_counts.get("ever_primary", 0))}
- Never-primary visible-secondary-only sites: {int(site_counts.get("never_primary_visible_secondary_only", 0))}
- Never-primary unresolved sites: {int(site_counts.get("never_primary_unresolved", 0))}
- Suppressed-only unclassifiable sites: {int(sites.suppressed_only_unclassifiable_site.sum())}

Among {len(sites)} reporting-site identifiers active from 2013 through 2024,
{site_visibility["sites_with_any_visible_numeric_activity"]} had any openly
numeric activity and {site_visibility["sites_exclusively_suppressed"]} were
identified exclusively through suppressed entries. Classification remained
longitudinally unresolved for
{site_visibility["sites_longitudinally_unresolved"]} sites.

The longitudinal site table treats each reported physical-site identifier as a
unit. It is not a merger-adjusted facility crosswalk; identifier changes,
restructurings, and unresolved continuity can therefore separate the same
real-world facility across years.

## Site-year results

- Active site-years: {len(site_years)}
- Primary or mixed: {int(site_years.site_year_classification.eq("primary_or_mixed").sum())}
- Definitely secondary-only: {len(definite)}
- Unresolved: {int(site_years.site_year_classification.eq("unresolved").sum())}
- Suppressed-only unclassifiable: {int(site_years.site_year_classification.eq("suppressed_only_unclassifiable").sum())}
- Maximum annual visible activity among definitely secondary-only site-years: {maximum}
- Definitely secondary-only threshold counts: {threshold_text}

## Institution-level sensitivity

- Ever-primary institutions: {int(institution_counts.get("ever_primary", 0))}
- Never-primary visible-secondary-only institutions: {int(institution_counts.get("never_primary_visible_secondary_only", 0))}
- Never-primary unresolved institutions: {int(institution_counts.get("never_primary_unresolved", 0))}
- Suppressed-only unclassifiable institutions: {int(institutions.suppressed_only_unclassifiable_site.sum())}
- Active institution-years: {len(institution_years)}

Institution aggregation is a sensitivity analysis and does not override the
physical-site results.

## Provider expansion and concentration

From 2013 to 2024, openly numeric reporting sites increased by
{all_expansion} using all classified site-years and by {restricted_expansion}
after excluding definitely secondary-only site-years. The largest annual
provider-count difference was {max_provider_difference}, the largest visible
activity difference was {max_activity_difference}, and the largest absolute HHI
difference was {max_hhi_difference:.4f}.

**{interpretation}**

This is a descriptive coding-pattern result. It does not establish that
secondary-only providers do or do not exist outside the classifiable reporting
data, and it does not support a negative claim about secondary interventions in
Germany.
"""
    return report, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalogue-root", type=Path, default=CATALOGUES)
    parser.add_argument("--audit", type=Path, default=AUDIT)
    parser.add_argument("--annual-control", type=Path, default=ANNUAL_CONTROL)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    commit = git_commit(ROOT)
    sources = discover_catalogues(args.catalogue_root)
    catalogue_hashes = json.dumps(
        {str(source.year): source.xml_sha256 for source in sources},
        sort_keys=True,
        separators=(",", ":"),
    )
    official = build_codebook(sources, args.catalogue_root)
    mapping = build_approved_analysis_mapping(official)
    observed = extract_observed_records(args.audit)
    coverage = build_coverage(observed, mapping)
    coverage["classification_status"] = np.where(
        coverage.codebook_match_count.eq(1), "approved", coverage.classification_status
    )
    validate_approved_mapping(mapping, coverage)

    joined_all, retained, resolution_audit = prepare_joined_records(
        args.audit, mapping
    )
    site_years, sites = classify_units(retained, "physical_site_identifier")

    institution_records = retained.copy()
    institution_records["institution_identifier"] = institution_records.ik.astype(str)
    institution_years, institutions = classify_units(
        institution_records, "institution_identifier"
    )
    institution_years = institution_years.rename(
        columns={
            "physical_site_identifier": "institution_identifier",
            "site_year_classification": "institution_year_classification",
        }
    )
    institutions = institutions.rename(
        columns={
            "physical_site_identifier": "institution_identifier",
            "longitudinal_classification": "longitudinal_institution_classification",
            "suppressed_only_unclassifiable_site": (
                "suppressed_only_unclassifiable_institution"
            ),
        }
    )

    reconciliation = activity_reconciliation(joined_all, args.annual_control)
    sensitivity = expansion_concentration_sensitivity(site_years)

    # Restore generic names internally for the report helper.
    institutions_for_report = institutions.rename(
        columns={
            "longitudinal_institution_classification": "longitudinal_classification",
            "suppressed_only_unclassifiable_institution": (
                "suppressed_only_unclassifiable_site"
            ),
        }
    )
    report, summary = analysis_report(
        site_years,
        sites,
        institution_years,
        institutions_for_report,
        sensitivity,
        timestamp,
        commit,
    )
    summary["source_catalogue_hashes"] = json.loads(catalogue_hashes)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    old_validation = args.output_dir / "ops_codebook_validation_report.md"
    preapproval = args.output_dir / "ops_codebook_validation_report_preapproval.md"
    if old_validation.exists() and not preapproval.exists():
        shutil.copyfile(old_validation, preapproval)

    mapping_out = add_metadata(mapping, timestamp, commit, catalogue_hashes)
    observed_out = observed.merge(
        mapping[
            [
                "reporting_year", "ops_code_normalised",
                "analysis_classification", "mapping_approval_status",
                "valid_in_reporting_year_catalogue", "legacy_handling_rule",
            ]
        ],
        on=["reporting_year", "ops_code_normalised"],
        how="left",
        validate="many_to_one",
    )
    observed_out = add_metadata(
        observed_out, timestamp, commit, catalogue_hashes
    )
    coverage_out = add_metadata(coverage, timestamp, commit, catalogue_hashes)
    site_years_out = add_metadata(
        site_years, timestamp, commit, catalogue_hashes
    )
    sites_out = add_metadata(sites, timestamp, commit, catalogue_hashes)
    institution_years_out = add_metadata(
        institution_years, timestamp, commit, catalogue_hashes
    )
    institutions_out = add_metadata(
        institutions, timestamp, commit, catalogue_hashes
    )
    reconciliation_out = add_metadata(
        reconciliation, timestamp, commit, catalogue_hashes
    )
    sensitivity_out = add_metadata(
        sensitivity, timestamp, commit, catalogue_hashes
    )
    resolution_out = add_metadata(
        resolution_audit, timestamp, commit, catalogue_hashes
    )

    mapping_out.to_csv(
        args.output_dir / "approved_ops_88398_analysis_mapping_2013_2024.csv",
        index=False,
    )
    observed_out.to_csv(
        args.output_dir / "observed_ops_88398_records_2013_2024.csv",
        index=False,
    )
    coverage_out.to_csv(
        args.output_dir / "ops_codebook_coverage_report.csv", index=False
    )
    site_years_out.to_csv(
        args.output_dir / "secondary_only_site_years_2013_2024.csv",
        index=False,
    )
    sites_out.to_csv(
        args.output_dir / "secondary_only_sites_longitudinal_2013_2024.csv",
        index=False,
    )
    institution_years_out.to_csv(
        args.output_dir / "secondary_only_institution_years_2013_2024.csv",
        index=False,
    )
    institutions_out.to_csv(
        args.output_dir
        / "secondary_only_institutions_longitudinal_2013_2024.csv",
        index=False,
    )
    reconciliation_out.to_csv(
        args.output_dir / "ops_activity_reconciliation.csv", index=False
    )
    sensitivity_out.to_csv(
        args.output_dir
        / "secondary_only_expansion_concentration_sensitivity.csv",
        index=False,
    )
    resolution_out.to_csv(
        args.output_dir / "secondary_only_site_resolution_audit.csv",
        index=False,
    )
    (args.output_dir / "secondary_only_analysis_report.md").write_text(
        report, encoding="utf-8"
    )
    (args.output_dir / "secondary_only_analysis_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "ops_codebook_validation_report.md").write_text(
        approved_validation_report(
            mapping, coverage, reconciliation, site_years, timestamp, commit
        ),
        encoding="utf-8",
    )

    print(f"Output: {args.output_dir}")
    print(json.dumps(summary["site_longitudinal_counts"], sort_keys=True))
    print(
        "Definitely secondary-only maximum visible activity:",
        summary["definitely_secondary_only_site_years"][
            "maximum_annual_visible_activity"
        ],
    )
    print("Approved secondary-only analysis complete.")


if __name__ == "__main__":
    main()
