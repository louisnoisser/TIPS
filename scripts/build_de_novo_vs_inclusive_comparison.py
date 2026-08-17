#!/usr/bin/env python3
"""Build and audit the de-novo versus inclusive comparison only.

This script reads established aggregate outputs. It does not read the selected-
code-only site-year file and does not rerun either established analysis.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs/de_novo_sensitivity_2013_2024"
DE_NOVO_SOURCE = OUTPUT_DIR / "de_novo_annual_metrics_2013_2024.csv"
INCLUSIVE_SOURCE = ROOT / "outputs/final_corrected_2026-07-24/suppression_final_metrics.csv"
REPORT_SOURCE = OUTPUT_DIR / "de_novo_sensitivity_2013_2024.md"
COMPARISON_OUTPUT = OUTPUT_DIR / "de_novo_vs_inclusive_concentration_by_year.csv"
VERIFICATION_OUTPUT = OUTPUT_DIR / "de_novo_vs_inclusive_verification.csv"

EXPECTED_HASHES = {
    DE_NOVO_SOURCE: "b5dddd1107e8653396c9c5c4b369f33ecfb3ad26e5a71530fe37f5fbf3ee2d67",
    INCLUSIVE_SOURCE: "d0a52a5d8ea8a250b7d4729a91bae7174272a22752ff772142c8543b7f99cf88",
    REPORT_SOURCE: "8a2b226c90f06eea97d2fda44c8c71f8d99e65527fe351fff6a7f82594271921",
}
YEARS = list(range(2013, 2025))
PROVIDER_DEFINITION = "physical_site"
SUPPRESSION_SCENARIO = "visible"
DE_NOVO_ENDPOINT = "activity coded with specific de novo TIPS creation subcodes"
INCLUSIVE_ENDPOINT = "inclusive TIPS-family coded activity"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_input_hashes() -> None:
    for path, expected in EXPECTED_HASHES.items():
        if not path.is_file():
            raise RuntimeError(f"Required established input is missing: {path}")
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"Established input hash mismatch for {path}: {actual} != {expected}")


def parse_report_comparison() -> list[dict[str, str]]:
    text = REPORT_SOURCE.read_text(encoding="utf-8")
    section = text.split("## Comparison with inclusive concentration", 1)[1]
    section = section.split("## Plausibility gates", 1)[0]
    header: list[str] | None = None
    records: list[dict[str, str]] = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == "reporting_year":
            header = cells
        elif header and cells and cells[0].isdigit():
            records.append(dict(zip(header, cells, strict=True)))
    if len(records) != 12:
        raise RuntimeError(f"Expected 12 report comparison rows, found {len(records)}")
    return records


def displayed_decimal_places(value: str) -> int:
    return len(value.partition(".")[2]) if "." in value else 0


def report_value_matches(written: object, displayed: str) -> bool:
    places = displayed_decimal_places(displayed)
    quantum = Decimal(1).scaleb(-places)
    return Decimal(str(written)).quantize(quantum) == Decimal(displayed)


def main() -> None:
    verify_input_hashes()
    de_novo = pd.read_csv(DE_NOVO_SOURCE).sort_values("reporting_year").reset_index(drop=True)
    inclusive_all = pd.read_csv(INCLUSIVE_SOURCE)
    inclusive = inclusive_all.loc[
        inclusive_all.reporting_year.isin(YEARS)
        & inclusive_all.provider_definition.eq(PROVIDER_DEFINITION)
        & inclusive_all.suppression_scenario.eq(SUPPRESSION_SCENARIO)
    ].sort_values("reporting_year").reset_index(drop=True)

    if de_novo.reporting_year.tolist() != YEARS or inclusive.reporting_year.tolist() != YEARS:
        raise RuntimeError("Established inputs do not contain exactly one selected row for every year")
    if not inclusive.provider_definition.eq(PROVIDER_DEFINITION).all():
        raise RuntimeError("Inclusive provider definition is not uniformly physical_site")
    if not inclusive.suppression_scenario.eq(SUPPRESSION_SCENARIO).all():
        raise RuntimeError("Inclusive suppression scenario is not uniformly visible")

    comparison = pd.DataFrame(
        {
            "reporting_year": YEARS,
            "de_novo_visible_activity": de_novo.openly_visible_national_de_novo_activity,
            "inclusive_visible_activity": inclusive.visible_national_activity,
            "activity_difference_de_novo_minus_inclusive": (
                de_novo.openly_visible_national_de_novo_activity - inclusive.visible_national_activity
            ),
            "de_novo_to_inclusive_activity_ratio": de_novo.de_novo_to_inclusive_visible_activity_ratio,
            "de_novo_openly_numeric_sites": de_novo.openly_numeric_de_novo_sites,
            "inclusive_openly_numeric_sites": inclusive.active_numeric_providers,
            "openly_numeric_site_difference_de_novo_minus_inclusive": (
                de_novo.openly_numeric_de_novo_sites - inclusive.active_numeric_providers
            ),
            "de_novo_top5_share_pct": de_novo.top5_share_pct,
            "inclusive_top5_share_pct": inclusive.top5_share_pct,
            "top5_difference_percentage_points_de_novo_minus_inclusive": (
                de_novo.top5_share_pct - inclusive.top5_share_pct
            ).round(4),
            "de_novo_top10_share_pct": de_novo.top10_share_pct,
            "inclusive_top10_share_pct": inclusive.top10_share_pct,
            "top10_difference_percentage_points_de_novo_minus_inclusive": (
                de_novo.top10_share_pct - inclusive.top10_share_pct
            ).round(4),
            "de_novo_top20_share_pct": de_novo.top20_share_pct,
            "inclusive_top20_share_pct": inclusive.top20_share_pct,
            "top20_difference_percentage_points_de_novo_minus_inclusive": (
                de_novo.top20_share_pct - inclusive.top20_share_pct
            ).round(4),
            "de_novo_hhi_10000": de_novo.hhi_10000,
            "inclusive_hhi_10000": inclusive.hhi_10000,
            "hhi_difference_de_novo_minus_inclusive": (
                de_novo.hhi_10000 - inclusive.hhi_10000
            ).round(4),
            "relative_hhi_difference_pct_de_novo_minus_inclusive": (
                (de_novo.hhi_10000 - inclusive.hhi_10000) / inclusive.hhi_10000 * 100
            ).round(6),
            "de_novo_effective_number_of_centres": de_novo.effective_number_of_centres,
            "inclusive_effective_number_of_centres": inclusive.effective_center_count,
            "effective_centre_difference_de_novo_minus_inclusive": (
                de_novo.effective_number_of_centres - inclusive.effective_center_count
            ).round(4),
            "relative_effective_centre_difference_pct_de_novo_minus_inclusive": (
                (de_novo.effective_number_of_centres - inclusive.effective_center_count)
                / inclusive.effective_center_count
                * 100
            ).round(6),
            "de_novo_gini": de_novo.gini,
            "inclusive_gini": inclusive.gini,
            "gini_difference_de_novo_minus_inclusive": (de_novo.gini - inclusive.gini).round(6),
        }
    )

    de_novo_columns = {
        "de_novo_visible_activity": "openly_visible_national_de_novo_activity",
        "de_novo_to_inclusive_activity_ratio": "de_novo_to_inclusive_visible_activity_ratio",
        "de_novo_openly_numeric_sites": "openly_numeric_de_novo_sites",
        "de_novo_top5_share_pct": "top5_share_pct",
        "de_novo_top10_share_pct": "top10_share_pct",
        "de_novo_top20_share_pct": "top20_share_pct",
        "de_novo_hhi_10000": "hhi_10000",
        "de_novo_effective_number_of_centres": "effective_number_of_centres",
        "de_novo_gini": "gini",
    }
    inclusive_columns = {
        "inclusive_visible_activity": "visible_national_activity",
        "inclusive_openly_numeric_sites": "active_numeric_providers",
        "inclusive_top5_share_pct": "top5_share_pct",
        "inclusive_top10_share_pct": "top10_share_pct",
        "inclusive_top20_share_pct": "top20_share_pct",
        "inclusive_hhi_10000": "hhi_10000",
        "inclusive_effective_number_of_centres": "effective_center_count",
        "inclusive_gini": "gini",
    }
    verification: list[dict[str, object]] = []
    for index, year in enumerate(YEARS):
        for written_column, source_column in de_novo_columns.items():
            source_value = de_novo.at[index, source_column]
            written_value = comparison.at[index, written_column]
            verification.append(
                {
                    "reporting_year": year,
                    "provider_definition": PROVIDER_DEFINITION,
                    "suppression_scenario": SUPPRESSION_SCENARIO,
                    "endpoint": DE_NOVO_ENDPOINT,
                    "metric": written_column,
                    "source_file": str(DE_NOVO_SOURCE.relative_to(ROOT)),
                    "source_column": source_column,
                    "source_filters": f"reporting_year={year}; established physical-site visible summary",
                    "source_sha256": EXPECTED_HASHES[DE_NOVO_SOURCE],
                    "source_value": str(source_value),
                    "written_value": str(written_value),
                    "comparison_precision": "exact CSV numeric value before presentation rounding",
                    "match": bool(source_value == written_value),
                }
            )
        for written_column, source_column in inclusive_columns.items():
            source_value = inclusive.at[index, source_column]
            written_value = comparison.at[index, written_column]
            verification.append(
                {
                    "reporting_year": year,
                    "provider_definition": PROVIDER_DEFINITION,
                    "suppression_scenario": SUPPRESSION_SCENARIO,
                    "endpoint": INCLUSIVE_ENDPOINT,
                    "metric": written_column,
                    "source_file": str(INCLUSIVE_SOURCE.relative_to(ROOT)),
                    "source_column": source_column,
                    "source_filters": (
                        f"reporting_year={year}; provider_definition=physical_site; "
                        "suppression_scenario=visible"
                    ),
                    "source_sha256": EXPECTED_HASHES[INCLUSIVE_SOURCE],
                    "source_value": str(source_value),
                    "written_value": str(written_value),
                    "comparison_precision": "exact CSV numeric value before presentation rounding",
                    "match": bool(source_value == written_value),
                }
            )

    report_columns = {
        "selected_subcode_hhi_10000": "de_novo_hhi_10000",
        "selected_subcode_effective_center_count": "de_novo_effective_number_of_centres",
        "selected_subcode_gini": "de_novo_gini",
        "inclusive_hhi_10000": "inclusive_hhi_10000",
        "inclusive_effective_center_count": "inclusive_effective_number_of_centres",
        "inclusive_gini": "inclusive_gini",
    }
    for record in parse_report_comparison():
        year = int(record["reporting_year"])
        row = comparison.loc[comparison.reporting_year.eq(year)].iloc[0]
        for report_column, written_column in report_columns.items():
            displayed = record[report_column]
            written_value = row[written_column]
            verification.append(
                {
                    "reporting_year": year,
                    "provider_definition": PROVIDER_DEFINITION,
                    "suppression_scenario": SUPPRESSION_SCENARIO,
                    "endpoint": "report cross-check",
                    "metric": written_column,
                    "source_file": str(REPORT_SOURCE.relative_to(ROOT)),
                    "source_column": f"Comparison with inclusive concentration::{report_column}",
                    "source_filters": f"reporting_year={year}; displayed Markdown value",
                    "source_sha256": EXPECTED_HASHES[REPORT_SOURCE],
                    "source_value": displayed,
                    "written_value": str(written_value),
                    "comparison_precision": (
                        f"report-displayed precision ({displayed_decimal_places(displayed)} decimal places)"
                    ),
                    "match": report_value_matches(written_value, displayed),
                }
            )

    verification_frame = pd.DataFrame(verification)
    if not verification_frame.match.all():
        failures = verification_frame.loc[~verification_frame.match]
        raise RuntimeError(f"Verification failed:\n{failures.to_string(index=False)}")

    # Explicit formula assertions: all differences are signed de novo minus inclusive.
    np.testing.assert_array_equal(
        comparison.activity_difference_de_novo_minus_inclusive,
        comparison.de_novo_visible_activity - comparison.inclusive_visible_activity,
    )
    np.testing.assert_array_equal(
        comparison.openly_numeric_site_difference_de_novo_minus_inclusive,
        comparison.de_novo_openly_numeric_sites - comparison.inclusive_openly_numeric_sites,
    )
    signed_difference_specs = [
        ("top5_difference_percentage_points_de_novo_minus_inclusive", "de_novo_top5_share_pct", "inclusive_top5_share_pct", 4),
        ("top10_difference_percentage_points_de_novo_minus_inclusive", "de_novo_top10_share_pct", "inclusive_top10_share_pct", 4),
        ("top20_difference_percentage_points_de_novo_minus_inclusive", "de_novo_top20_share_pct", "inclusive_top20_share_pct", 4),
        ("hhi_difference_de_novo_minus_inclusive", "de_novo_hhi_10000", "inclusive_hhi_10000", 4),
        ("effective_centre_difference_de_novo_minus_inclusive", "de_novo_effective_number_of_centres", "inclusive_effective_number_of_centres", 4),
        ("gini_difference_de_novo_minus_inclusive", "de_novo_gini", "inclusive_gini", 6),
    ]
    for difference, de_novo_column, inclusive_column, decimals in signed_difference_specs:
        np.testing.assert_array_equal(
            comparison[difference],
            (comparison[de_novo_column] - comparison[inclusive_column]).round(decimals),
        )
    np.testing.assert_array_equal(
        comparison.relative_hhi_difference_pct_de_novo_minus_inclusive,
        (
            comparison.hhi_difference_de_novo_minus_inclusive
            / comparison.inclusive_hhi_10000
            * 100
        ).round(6),
    )
    np.testing.assert_array_equal(
        comparison.relative_effective_centre_difference_pct_de_novo_minus_inclusive,
        (
            comparison.effective_centre_difference_de_novo_minus_inclusive
            / comparison.inclusive_effective_number_of_centres
            * 100
        ).round(6),
    )

    comparison.to_csv(COMPARISON_OUTPUT, index=False)
    verification_frame.to_csv(VERIFICATION_OUTPUT, index=False)
    print(f"Created {COMPARISON_OUTPUT} ({len(comparison)} rows)")
    print(f"Created {VERIFICATION_OUTPUT} ({len(verification_frame)} rows; all checks passed)")


if __name__ == "__main__":
    main()
