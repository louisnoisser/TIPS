#!/usr/bin/env python3
"""Run TIPS 8-839.8* codeset sensitivity reports and comparison outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gba_ops_reanalysis import config
from gba_ops_reanalysis.indication_report import build_indication_report
from gba_ops_reanalysis.indication_supplement import build_indication_supplement

from verify_primary_vs_secondary import build_verification

CODESET_RUNS: list[tuple[str, str, str]] = [
    ("A_PRIMARY_ONLY", "codeset_A_primary", "A"),
    ("B_LOOSEN", "codeset_B_loosen", "B"),
    ("C_INCLUSIVE", "codeset_C_inclusive", "C"),
]


def _build_concentration(hospital_year: pd.DataFrame, case_col: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for year, group in hospital_year.groupby("year", dropna=False):
        active = group.loc[pd.to_numeric(group[case_col], errors="coerce").fillna(0) > 0].copy()
        active[case_col] = pd.to_numeric(active[case_col], errors="coerce").fillna(0)
        total = float(active[case_col].sum())
        if total <= 0:
            rows.append(
                {
                    "year": int(year),
                    "total_cases": 0,
                    "active_centers": 0,
                    "HHI": 0.0,
                    "top10_share": 0.0,
                }
            )
            continue
        shares = active[case_col] / total
        top10_share = float(100 * active.sort_values(case_col, ascending=False)[case_col].head(10).sum() / total)
        rows.append(
            {
                "year": int(year),
                "total_cases": int(total),
                "active_centers": int(len(active)),
                "HHI": float(np.square(shares).sum() * 10000),
                "top10_share": top10_share,
            }
        )
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def _merge_comparison(results_dir: Path, report_dirs: dict[str, Path]) -> pd.DataFrame:
    per_set: list[pd.DataFrame] = []
    for _, _, suffix in CODESET_RUNS:
        report_dir = report_dirs[suffix]
        hospital_year = pd.read_csv(report_dir / "tables" / "hospital_year.csv")
        summary = json.loads((report_dir / "report_summary.json").read_text(encoding="utf-8"))
        case_col = str(summary["case_col"])
        stats = _build_concentration(hospital_year, case_col)
        rename = {
            "total_cases": f"total_cases_{suffix}",
            "active_centers": f"active_centers_{suffix}",
            "HHI": f"HHI_{suffix}",
            "top10_share": f"top10_share_{suffix}",
        }
        per_set.append(stats.rename(columns=rename))

    merged = per_set[0]
    for frame in per_set[1:]:
        merged = merged.merge(frame, on="year", how="outer")
    merged = merged.sort_values("year").reset_index(drop=True)
    merged.to_csv(results_dir / "codeset_comparison.csv", index=False)
    return merged


def _plot_comparison(comparison: pd.DataFrame, figure_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), dpi=160)
    styles = {"A": "#1f77b4", "B": "#ff7f0e", "C": "#2ca02c"}
    labels = {"A": "A Primary-only", "B": "B Loosen", "C": "C Inclusive"}

    for suffix in ("A", "B", "C"):
        axes[0].plot(
            comparison["year"],
            comparison[f"total_cases_{suffix}"],
            color=styles[suffix],
            linewidth=2.2,
            label=labels[suffix],
        )
        axes[1].plot(
            comparison["year"],
            comparison[f"active_centers_{suffix}"],
            color=styles[suffix],
            linewidth=2.2,
            label=labels[suffix],
        )

    axes[0].set_title("Yearly TIPS volume by code set")
    axes[0].set_xlabel("Year")
    axes[0].set_ylabel("Cases")
    axes[0].grid(alpha=0.25, linestyle=":")
    axes[1].set_title("Yearly active centers by code set")
    axes[1].set_xlabel("Year")
    axes[1].set_ylabel("Active centers")
    axes[1].grid(alpha=0.25, linestyle=":")
    axes[1].legend(loc="best", frameon=False)
    fig.tight_layout()
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(figure_path, bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-xml-dir", type=Path, default=config.XML_DIR)
    parser.add_argument("--latest-year", type=int, default=2024)
    parser.add_argument("--threshold", action="append", type=int, default=None)
    parser.add_argument("--main-threshold", type=int, default=50)
    parser.add_argument("--strict-threshold", type=int, default=100)
    parser.add_argument("--time-bin", action="append", type=int, default=None)
    parser.add_argument("--grid-resolution", type=float, default=0.05)
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--skip-supplement", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    thresholds = sorted(set(args.threshold or [20, 50, 100, 200]))
    time_bins = sorted(set(args.time_bin or [30, 60]))
    results_dir = args.results_dir.resolve()
    results_dir.mkdir(parents=True, exist_ok=True)

    report_dirs: dict[str, Path] = {}
    for codeset_key, subdir_name, suffix in CODESET_RUNS:
        selector = config.codeset_to_selector(config.TIPS_CODESETS[codeset_key])
        report_dir = results_dir / subdir_name
        report_dirs[suffix] = report_dir
        cache_tag = f"tips_8-839-8_{codeset_key.lower()}"

        print(f"[{codeset_key}] building report -> {report_dir}")
        build_indication_report(
            indication_name="TIPS",
            ops_selector=selector,
            label="tips",
            base_xml_dir=args.base_xml_dir,
            report_dir=report_dir,
            codeset=codeset_key,
            cache_tag=cache_tag,
            geocode_cache_tag="8-839.8",
            latest_year=args.latest_year,
            thresholds=thresholds,
            main_threshold=args.main_threshold,
            strict_threshold=args.strict_threshold,
            time_bins=time_bins,
            grid_resolution=args.grid_resolution,
        )

        if not args.skip_supplement:
            print(f"[{codeset_key}] building supplement")
            try:
                build_indication_supplement(report_dir)
            except FileNotFoundError as exc:
                print(f"[{codeset_key}] supplement skipped due to missing prerequisite table: {exc}")

    comparison = _merge_comparison(results_dir, report_dirs)
    figure_path = results_dir / "figures" / "codeset_comparison.png"
    _plot_comparison(comparison, figure_path)

    verification_dir = results_dir / "verification_primary_vs_secondary"
    verification = build_verification(args.base_xml_dir, verification_dir)

    print(f"Comparison table: {results_dir / 'codeset_comparison.csv'}")
    print(f"Comparison figure: {figure_path}")
    print(f"Verification report: {verification_dir / 'verification_report.md'}")
    print(verification["headline"])


if __name__ == "__main__":
    main()
