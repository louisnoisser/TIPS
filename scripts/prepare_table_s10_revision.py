#!/usr/bin/env python3
"""Prepare validated Table S10 data without editing a Supplement DOCX."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "outputs/de_novo_sensitivity_2013_2024"
OUTPUT_DIR = ROOT / "outputs/late_stage_revision_2026-08-13/table_s10_validation"
ANNUAL = SOURCE_DIR / "de_novo_annual_metrics_2013_2024.csv"
COMPARISON = SOURCE_DIR / "de_novo_vs_inclusive_concentration_by_year.csv"
VERIFICATION = SOURCE_DIR / "de_novo_vs_inclusive_verification.csv"
BRIDGE = SOURCE_DIR / "de_novo_2015_2016_bridge.csv"
MANIFEST = SOURCE_DIR / "de_novo_run_manifest.json"
EXPECTED_HASHES = {
    ANNUAL: "b5dddd1107e8653396c9c5c4b369f33ecfb3ad26e5a71530fe37f5fbf3ee2d67",
    COMPARISON: "00ab93eeb744df3cca08d2a4b5f852ca03cfa5f9126bc9ef417f3adaba2ae92c",
    VERIFICATION: "1a38a1d1253e5812da1b3db152a98aef90a5f182366df0ce938f7044e2346144",
    BRIDGE: "d01d7d24999d47b6da7fcda8006ec0d414caa7a034e0690c7788b6bb0e40c1e3",
    MANIFEST: "7a063b7bb90852aa55a76b2b6c2017bb5ea1b6de872c3e93b561315a0a3238f3",
}
YEARS = list(range(2013, 2025))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    for path, expected in EXPECTED_HASHES.items():
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"Locked source hash mismatch for {path}: {actual}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    annual = pd.read_csv(ANNUAL).sort_values("reporting_year").reset_index(drop=True)
    comparison = pd.read_csv(COMPARISON).sort_values("reporting_year").reset_index(drop=True)
    source_verification = pd.read_csv(VERIFICATION)
    bridge = pd.read_csv(BRIDGE).sort_values("reporting_year").reset_index(drop=True)
    if annual.reporting_year.tolist() != YEARS or comparison.reporting_year.tolist() != YEARS:
        raise RuntimeError("Canonical Table S10 source years are not exactly 2013–2024")
    if not source_verification.match.all():
        raise RuntimeError("Canonical de-novo versus inclusive verification contains a failure")

    panel_a = pd.DataFrame(
        {
            "Year": annual.reporting_year.astype(int),
            "Selected-code visible activity": annual.openly_visible_national_de_novo_activity.astype(int),
            "Inclusive visible activity": comparison.inclusive_visible_activity.astype(int),
            "Selected/inclusive, %": (comparison.de_novo_to_inclusive_activity_ratio * 100).round(1),
            "Identifiable sites": annual.identifiable_active_de_novo_sites.astype(int),
            "Openly numeric sites": annual.openly_numeric_de_novo_sites.astype(int),
            "Suppressed-only sites": annual.suppressed_only_de_novo_sites.astype(int),
            "≥20": annual.sites_visible_ge_20.astype(int),
            "≥50": annual.sites_visible_ge_50.astype(int),
            "≥100": annual.sites_visible_ge_100.astype(int),
            "≥200": annual.sites_visible_ge_200.astype(int),
        }
    )
    panel_b = pd.DataFrame(
        {
            "Year": comparison.reporting_year.astype(int),
            "Top-5, %": comparison.de_novo_top5_share_pct.round(1),
            "Top-10, %": comparison.de_novo_top10_share_pct.round(1),
            "Top-20, %": comparison.de_novo_top20_share_pct.round(1),
            "HHI": comparison.de_novo_hhi_10000.round(1),
            "Effective centres": comparison.de_novo_effective_number_of_centres.round(1),
            "Gini": comparison.de_novo_gini.round(3),
        }
    )

    panel_a_sources = {
        "Year": (ANNUAL, "reporting_year", lambda x: int(x), "integer"),
        "Selected-code visible activity": (ANNUAL, "openly_visible_national_de_novo_activity", lambda x: int(x), "integer"),
        "Inclusive visible activity": (COMPARISON, "inclusive_visible_activity", lambda x: int(x), "integer"),
        "Selected/inclusive, %": (COMPARISON, "de_novo_to_inclusive_activity_ratio", lambda x: round(float(x) * 100, 1), "percentage, 1 decimal"),
        "Identifiable sites": (ANNUAL, "identifiable_active_de_novo_sites", lambda x: int(x), "integer"),
        "Openly numeric sites": (ANNUAL, "openly_numeric_de_novo_sites", lambda x: int(x), "integer"),
        "Suppressed-only sites": (ANNUAL, "suppressed_only_de_novo_sites", lambda x: int(x), "integer"),
        "≥20": (ANNUAL, "sites_visible_ge_20", lambda x: int(x), "integer"),
        "≥50": (ANNUAL, "sites_visible_ge_50", lambda x: int(x), "integer"),
        "≥100": (ANNUAL, "sites_visible_ge_100", lambda x: int(x), "integer"),
        "≥200": (ANNUAL, "sites_visible_ge_200", lambda x: int(x), "integer"),
    }
    panel_b_sources = {
        "Year": (COMPARISON, "reporting_year", lambda x: int(x), "integer"),
        "Top-5, %": (COMPARISON, "de_novo_top5_share_pct", lambda x: round(float(x), 1), "percentage, 1 decimal"),
        "Top-10, %": (COMPARISON, "de_novo_top10_share_pct", lambda x: round(float(x), 1), "percentage, 1 decimal"),
        "Top-20, %": (COMPARISON, "de_novo_top20_share_pct", lambda x: round(float(x), 1), "percentage, 1 decimal"),
        "HHI": (COMPARISON, "de_novo_hhi_10000", lambda x: round(float(x), 1), "1 decimal"),
        "Effective centres": (COMPARISON, "de_novo_effective_number_of_centres", lambda x: round(float(x), 1), "1 decimal"),
        "Gini": (COMPARISON, "de_novo_gini", lambda x: round(float(x), 3), "3 decimals"),
    }
    source_frames = {ANNUAL: annual, COMPARISON: comparison}
    validation_rows: list[dict[str, object]] = []
    for panel_name, panel, mapping in (
        ("Panel A", panel_a, panel_a_sources),
        ("Panel B", panel_b, panel_b_sources),
    ):
        for row_number, displayed_row in panel.iterrows():
            year = int(displayed_row["Year"])
            for column, (source_path, source_column, transform, precision) in mapping.items():
                source_frame = source_frames[source_path]
                source_value = source_frame.loc[source_frame.reporting_year.eq(year), source_column].iloc[0]
                expected_display = transform(source_value)
                displayed_value = displayed_row[column]
                validation_rows.append(
                    {
                        "record_type": "displayed_cell",
                        "panel": panel_name,
                        "reporting_year": year,
                        "display_column": column,
                        "source_file": str(source_path.relative_to(ROOT)),
                        "source_column": source_column,
                        "source_sha256": EXPECTED_HASHES[source_path],
                        "source_value": source_value,
                        "displayed_value": displayed_value,
                        "comparison_precision": precision,
                        "check": "displayed value equals transformed authoritative source",
                        "passed": bool(displayed_value == expected_display),
                        "detail": "",
                    }
                )

    logical_rows: list[dict[str, object]] = []
    def check(name: str, passed: bool, detail: str = "") -> None:
        logical_rows.append(
            {
                "record_type": "logical_check", "panel": "", "reporting_year": "",
                "display_column": "", "source_file": "", "source_column": "",
                "source_sha256": "", "source_value": "", "displayed_value": "",
                "comparison_precision": "", "check": name, "passed": bool(passed), "detail": detail,
            }
        )

    check("Panel A has exactly 12 annual rows", len(panel_a) == 12, f"observed={len(panel_a)}")
    check("Panel B has exactly 12 annual rows", len(panel_b) == 12, f"observed={len(panel_b)}")
    check("Panel A years are exactly 2013–2024", panel_a.Year.tolist() == YEARS)
    check("Panel B years are exactly 2013–2024", panel_b.Year.tolist() == YEARS)
    check("No pre-2013 selected-code row", panel_a.Year.min() == 2013 and panel_b.Year.min() == 2013)
    for row in panel_a.itertuples(index=False):
        year = int(row[0])
        selected, inclusive = int(row[1]), int(row[2])
        identifiable, numeric, suppressed = int(row[4]), int(row[5]), int(row[6])
        ge20, ge50, ge100, ge200 = map(int, row[7:11])
        check(f"{year}: selected activity ≤ inclusive activity", selected <= inclusive)
        check(f"{year}: suppressed-only = identifiable − openly numeric", suppressed == identifiable - numeric)
        check(f"{year}: provider counts are non-negative", min(identifiable, numeric, suppressed, ge20, ge50, ge100, ge200) >= 0)
        check(f"{year}: cumulative thresholds are nested", ge200 <= ge100 <= ge50 <= ge20 <= numeric)

    a2013 = panel_a.loc[panel_a.Year.eq(2013)].iloc[0]
    b2013 = panel_b.loc[panel_b.Year.eq(2013)].iloc[0]
    for label, observed, expected in [
        ("2013 selected-code activity", a2013["Selected-code visible activity"], 1042),
        ("2013 identifiable sites", a2013["Identifiable sites"], 105),
        ("2013 openly numeric sites", a2013["Openly numeric sites"], 51),
        ("2013 Top-5", b2013["Top-5, %"], 30.1),
        ("2013 HHI", b2013.HHI, 352.3),
        ("2013 effective centres", b2013["Effective centres"], 28.4),
        ("2013 Gini", b2013.Gini, 0.434),
    ]:
        check(label, observed == expected, f"observed={observed}; expected={expected}")
    a2024 = panel_a.loc[panel_a.Year.eq(2024)].iloc[0]
    b2024 = panel_b.loc[panel_b.Year.eq(2024)].iloc[0]
    for label, observed, expected in [
        ("2024 selected-code activity", a2024["Selected-code visible activity"], 2548),
        ("2024 inclusive activity", a2024["Inclusive visible activity"], 5247),
        ("2024 selected/inclusive ratio", a2024["Selected/inclusive, %"], 48.6),
        ("2024 identifiable sites", a2024["Identifiable sites"], 176),
        ("2024 openly numeric sites", a2024["Openly numeric sites"], 106),
        ("2024 suppressed-only sites", a2024["Suppressed-only sites"], 70),
        ("2024 ≥20", a2024["≥20"], 44),
        ("2024 ≥50", a2024["≥50"], 14),
        ("2024 ≥100", a2024["≥100"], 4),
        ("2024 ≥200", a2024["≥200"], 0),
        ("2024 Top-5", b2024["Top-5, %"], 21.9),
        ("2024 HHI", b2024.HHI, 210.9),
        ("2024 effective centres", b2024["Effective centres"], 47.4),
        ("2024 Gini", b2024.Gini, 0.518),
    ]:
        check(label, observed == expected, f"observed={observed}; expected={expected}")
    check("2015 selected-code visible activity = 1,308", panel_a.loc[panel_a.Year.eq(2015), "Selected-code visible activity"].iloc[0] == 1308)
    check("2016 selected-code visible activity = 1,427", panel_a.loc[panel_a.Year.eq(2016), "Selected-code visible activity"].iloc[0] == 1427)
    bridge_2016 = bridge.loc[bridge.reporting_year.eq(2016)].iloc[0]
    check("2016 8-839.89 plus 8-839.8a visible occurrences = 44", bridge_2016.visible_8_839_89_plus_8_839_8a == 44)

    validation = pd.DataFrame(validation_rows + logical_rows)
    if not validation.passed.all():
        raise RuntimeError(f"Table S10 validation failed:\n{validation.loc[~validation.passed].to_string(index=False)}")
    panel_a.to_csv(OUTPUT_DIR / "TableS10_panel_A.csv", index=False)
    panel_b.to_csv(OUTPUT_DIR / "TableS10_panel_B.csv", index=False)
    validation.to_csv(OUTPUT_DIR / "TableS10_validation.csv", index=False)
    displayed = int(validation.record_type.eq("displayed_cell").sum())
    logical = int(validation.record_type.eq("logical_check").sum())
    print(f"Table S10 displayed cells verified: {displayed}/{displayed}")
    print(f"Logical and integrity checks: {logical}/{logical} passed")


if __name__ == "__main__":
    main()
