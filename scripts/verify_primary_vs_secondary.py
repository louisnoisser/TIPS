#!/usr/bin/env python3
"""Methodological verification for primary vs. secondary TIPS OPS activity."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gba_ops_reanalysis import config
from gba_ops_reanalysis.longitudinal import run_longitudinal_pipeline
from gba_ops_reanalysis.ops_icd import parse_target_specs, target_case_column

PRIMARY_CODES = config.CODESET_A_PRIMARY_ONLY
SECONDARY_CODES = [
    "8-839.81",
    "8-839.82",
    "8-839.83",
    "8-839.84",
    "8-839.85",
    "8-839.86",
]
AMBIGUOUS_CODES = ["8-839.8x", "8-839.8X"]


def _first_non_empty(series: pd.Series) -> str:
    for value in series:
        if pd.notna(value):
            text = str(value).strip()
            if text and text.lower() != "nan":
                return text
    return ""


def _iqr(values: pd.Series) -> tuple[float, float]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return 0.0, 0.0
    return float(clean.quantile(0.25)), float(clean.quantile(0.75))


def build_verification(base_xml_dir: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = output_dir / "tmp_longitudinal"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    ops_targets = parse_target_specs(
        [
            f"primary={','.join(PRIMARY_CODES)}",
            f"secondary={','.join(SECONDARY_CODES)}",
            f"ambiguous={','.join(AMBIGUOUS_CODES)}",
        ]
    )
    hospital_year, _, _ = run_longitudinal_pipeline(
        base_dir=base_xml_dir,
        out_dir=tmp_dir,
        ops_targets=ops_targets,
        icd_targets={},
        denominator_label=None,
    )

    primary_col = target_case_column("primary")
    secondary_col = target_case_column("secondary")
    ambiguous_col = target_case_column("ambiguous")

    grouped = (
        hospital_year.groupby(["year", "ik"], dropna=False)
        .agg(
            hospital_name=("hospital_name", _first_non_empty),
            city=("city", _first_non_empty),
            postal_code=("postal_code", _first_non_empty),
            street=("street", _first_non_empty),
            house_number=("house_number", _first_non_empty),
            phone=("phone", _first_non_empty),
            email=("email", _first_non_empty),
            primary_count=(primary_col, "sum"),
            secondary_count=(secondary_col, "sum"),
            ambiguous_count=(ambiguous_col, "sum"),
        )
        .reset_index()
        .rename(columns={"ik": "hospital_id"})
    )
    grouped["primary_count"] = pd.to_numeric(grouped["primary_count"], errors="coerce").fillna(0).astype(int)
    grouped["secondary_count"] = pd.to_numeric(grouped["secondary_count"], errors="coerce").fillna(0).astype(int)
    grouped["ambiguous_count"] = pd.to_numeric(grouped["ambiguous_count"], errors="coerce").fillna(0).astype(int)
    grouped["total_count"] = grouped["primary_count"] + grouped["secondary_count"] + grouped["ambiguous_count"]
    grouped["primary_share"] = np.where(grouped["total_count"] > 0, grouped["primary_count"] / grouped["total_count"], 0.0)
    grouped["secondary_share"] = np.where(grouped["total_count"] > 0, grouped["secondary_count"] / grouped["total_count"], 0.0)

    panel = grouped.loc[grouped["total_count"] > 0].copy()
    panel = panel.sort_values(["year", "hospital_id"]).reset_index(drop=True)
    panel_out = panel[
        [
            "year",
            "hospital_id",
            "hospital_name",
            "primary_count",
            "secondary_count",
            "ambiguous_count",
            "total_count",
            "primary_share",
            "secondary_share",
        ]
    ].copy()
    panel_out.to_csv(output_dir / "hospital_year_panel.csv", index=False)

    yearly_rows: list[dict[str, Any]] = []
    for year, year_df in panel.groupby("year", dropna=False):
        primary_only = (year_df["primary_count"] > 0) & (year_df["secondary_count"] == 0)
        secondary_only = (year_df["primary_count"] == 0) & (year_df["secondary_count"] > 0)
        mixed = (year_df["primary_count"] > 0) & (year_df["secondary_count"] > 0)
        n_total = int(len(year_df))
        n_secondary_only = int(secondary_only.sum())
        yearly_rows.append(
            {
                "year": int(year),
                "n_hospitals_total": n_total,
                "n_hospitals_primary_only": int(primary_only.sum()),
                "n_hospitals_secondary_only": n_secondary_only,
                "n_hospitals_mixed": int(mixed.sum()),
                "pct_hospitals_secondary_only": round(100 * n_secondary_only / n_total, 2) if n_total else 0.0,
                "total_primary_cases": int(year_df["primary_count"].sum()),
                "total_secondary_cases": int(year_df["secondary_count"].sum()),
            }
        )
    yearly_summary = pd.DataFrame(yearly_rows).sort_values("year").reset_index(drop=True)
    yearly_summary.to_csv(output_dir / "yearly_summary.csv", index=False)

    flagged = panel.loc[(panel["primary_count"] == 0) & (panel["secondary_count"] > 0)].copy()
    flagged = flagged.sort_values(["year", "secondary_count"], ascending=[True, False]).reset_index(drop=True)
    flagged_cols = [
        "year",
        "hospital_id",
        "hospital_name",
        "city",
        "postal_code",
        "street",
        "house_number",
        "phone",
        "email",
        "primary_count",
        "secondary_count",
        "ambiguous_count",
        "total_count",
        "primary_share",
        "secondary_share",
    ]
    flagged[flagged_cols].to_csv(output_dir / "flagged_secondary_only_hospital_years.csv", index=False)

    persistent = (
        flagged.groupby("hospital_id", dropna=False)
        .agg(
            years_flagged=("year", "nunique"),
            total_secondary=("secondary_count", "sum"),
            hospital_name=("hospital_name", _first_non_empty),
            city=("city", _first_non_empty),
        )
        .reset_index()
    )
    persistent = persistent.loc[persistent["years_flagged"] >= 2].sort_values(
        ["years_flagged", "total_secondary"], ascending=[False, False]
    )
    persistent.to_csv(output_dir / "persistent_secondary_only_hospitals.csv", index=False)

    primary_share = panel["primary_share"]
    p25, p75 = _iqr(primary_share)
    median_share = float(pd.to_numeric(primary_share, errors="coerce").median()) if not panel.empty else 0.0
    pct_below_50 = float((primary_share < 0.5).mean() * 100) if not panel.empty else 0.0
    pct_below_25 = float((primary_share < 0.25).mean() * 100) if not panel.empty else 0.0

    all_hospital_years = (
        hospital_year.groupby(["year", "ik"], dropna=False)
        .size()
        .reset_index(name="rows")
    )
    active_hospital_years = int(len(panel))
    total_hospital_years = int(len(all_hospital_years))
    active_pct = (100 * active_hospital_years / total_hospital_years) if total_hospital_years else 0.0
    secondary_only_pct = (100 * len(flagged) / active_hospital_years) if active_hospital_years else 0.0

    top5 = flagged.head(5).copy()
    top5_lines = []
    for _, row in top5.iterrows():
        top5_lines.append(
            f"- {int(row['year'])}: {row['hospital_name']} ({row['hospital_id']}), "
            f"secondary={int(row['secondary_count'])}, ambiguous={int(row['ambiguous_count'])}"
        )
    if not top5_lines:
        top5_lines.append("- none")

    persistent_phrase = (
        f"{len(persistent)} hospitals with >=2 secondary-only years"
        if not persistent.empty
        else "none"
    )
    headline = (
        f"{active_pct:.2f}% of hospital-years had any TIPS-coded activity, "
        f"of which {secondary_only_pct:.2f}% were secondary-only; "
        f"{persistent_phrase} showed a persistent secondary-only pattern."
    )

    report_lines = [
        "# Primary vs Secondary TIPS Verification Report",
        "",
        f"**Headline:** {headline}",
        "",
        "## Core findings",
        f"- Total hospital-years with any TIPS-coded activity: {active_hospital_years} / {total_hospital_years} ({active_pct:.2f}%)",
        f"- Secondary-only hospital-years (primary_count = 0, secondary_count > 0): {len(flagged)} ({secondary_only_pct:.2f}% of active hospital-years)",
        f"- Persistently secondary-only hospitals (>=2 years): {len(persistent)}",
        "",
        "## Primary share distribution (all active hospital-years)",
        f"- Median primary share: {median_share:.3f}",
        f"- IQR primary share: {p25:.3f} to {p75:.3f}",
        f"- Hospital-years with primary share < 50%: {pct_below_50:.2f}%",
        f"- Hospital-years with primary share < 25%: {pct_below_25:.2f}%",
        "",
        "## Top 5 secondary-only hospital-years by secondary count",
        *top5_lines,
    ]
    (output_dir / "verification_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    return {
        "output_dir": str(output_dir),
        "headline": headline,
        "active_hospital_years": active_hospital_years,
        "secondary_only_hospital_years": int(len(flagged)),
        "persistent_secondary_only_hospitals": int(len(persistent)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-xml-dir", type=Path, default=config.XML_DIR)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results" / "verification_primary_vs_secondary")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_verification(args.base_xml_dir, args.output_dir)
    print(f"Verification output: {result['output_dir']}")
    print(result["headline"])


if __name__ == "__main__":
    main()

