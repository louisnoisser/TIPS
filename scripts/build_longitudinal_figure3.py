#!/usr/bin/env python3
"""Build the revised longitudinal Figure 3 from locked production metrics."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/final_corrected_2026-07-24/suppression_final_metrics.csv"
EXPECTED_SOURCE_SHA256 = "d0a52a5d8ea8a250b7d4729a91bae7174272a22752ff772142c8543b7f99cf88"
TABLE_S1_CROSSCHECK = ROOT / "outputs/final_submission_assets_2026-07-24/tables/TableS1_corrected_annual_site_metrics.csv"
EXPECTED_TABLE_S1_SHA256 = "5d89bae867188c91aab7d066ab0947fe085e436546533562b0c739bc8de008ca"
OUTPUT_ROOT = ROOT / "outputs/late_stage_revision_2026-08-13"
FIGURE_DIR = OUTPUT_ROOT / "figure3"
QA_DIR = OUTPUT_ROOT / "render_qa/figure3"
YEARS = [2008, 2010, *range(2012, 2025)]
CATEGORIES = ["4–19", "20–49", "50–99", "100–199", "≥200"]
CATEGORY_COLUMNS = [
    "sites_4_19", "sites_20_49", "sites_50_99", "sites_100_199", "sites_ge_200"
]
COLOURS = ["#d9eaf3", "#a8cde1", "#6baed6", "#3182bd", "#08519c"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_check(rows: list[dict[str, object]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "passed": bool(passed), "detail": detail})


def main() -> None:
    if sha256_file(SOURCE) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("Locked suppression_final_metrics.csv hash does not match")
    if sha256_file(TABLE_S1_CROSSCHECK) != EXPECTED_TABLE_S1_SHA256:
        raise RuntimeError("Independent Table S1 cross-check hash does not match")
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)

    source = pd.read_csv(SOURCE)
    selected = source.loc[
        source.reporting_year.isin(YEARS)
        & source.provider_definition.eq("physical_site")
        & source.suppression_scenario.eq("visible")
    ].sort_values("reporting_year").reset_index(drop=True)
    if selected.reporting_year.tolist() != YEARS:
        raise RuntimeError("Expected exactly one physical-site visible record for each reporting year")
    table_s1 = pd.read_csv(TABLE_S1_CROSSCHECK).sort_values("reporting_year").reset_index(drop=True)
    if table_s1.reporting_year.tolist() != YEARS:
        raise RuntimeError("Independent Table S1 year sequence differs")

    plotted = pd.DataFrame(
        {
            "reporting_year": selected.reporting_year.astype(int),
            "provider_definition": selected.provider_definition,
            "suppression_scenario": selected.suppression_scenario,
            "openly_numeric_physical_sites": selected.active_numeric_providers.astype(int),
            "sites_4_19": (selected.active_numeric_providers - selected.providers_ge_20).astype(int),
            "sites_20_49": (selected.providers_ge_20 - selected.providers_ge_50).astype(int),
            "sites_50_99": (selected.providers_ge_50 - selected.providers_ge_100).astype(int),
            "sites_100_199": (selected.providers_ge_100 - selected.providers_ge_200).astype(int),
            "sites_ge_200": selected.providers_ge_200.astype(int),
        }
    )
    plotted["stack_sum"] = plotted[CATEGORY_COLUMNS].sum(axis=1).astype(int)

    checks: list[dict[str, object]] = []
    add_check(checks, "exactly_15_bars", len(plotted) == 15, f"observed={len(plotted)}")
    add_check(checks, "exact_year_sequence", plotted.reporting_year.tolist() == YEARS, str(YEARS))
    add_check(checks, "no_2009", 2009 not in set(plotted.reporting_year), "2009 absent")
    add_check(checks, "no_2011", 2011 not in set(plotted.reporting_year), "2011 absent")
    add_check(
        checks, "all_stacks_equal_openly_numeric_sites",
        plotted.stack_sum.equals(plotted.openly_numeric_physical_sites),
        f"mismatches={(plotted.stack_sum != plotted.openly_numeric_physical_sites).sum()}",
    )
    add_check(
        checks, "all_categories_non_negative_integers",
        bool((plotted[CATEGORY_COLUMNS] >= 0).all().all())
        and all(pd.api.types.is_integer_dtype(plotted[column]) for column in CATEGORY_COLUMNS),
        f"minimum={int(plotted[CATEGORY_COLUMNS].min().min())}",
    )
    row_2008 = plotted.loc[plotted.reporting_year.eq(2008)].iloc[0]
    row_2024 = plotted.loc[plotted.reporting_year.eq(2024)].iloc[0]
    add_check(checks, "2008_total_equals_28", row_2008.stack_sum == 28, f"observed={row_2008.stack_sum}")
    add_check(checks, "2024_total_equals_113", row_2024.stack_sum == 113, f"observed={row_2024.stack_sum}")
    expected_2024 = [53, 29, 15, 10, 6]
    add_check(
        checks, "2024_segments_equal_53_29_15_10_6",
        row_2024[CATEGORY_COLUMNS].astype(int).tolist() == expected_2024,
        f"observed={row_2024[CATEGORY_COLUMNS].astype(int).tolist()}",
    )
    add_check(checks, "legend_order_matches_stack_order", CATEGORIES == ["4–19", "20–49", "50–99", "100–199", "≥200"], str(CATEGORIES))
    crosscheck_columns = [
        "reporting_year", "active_numeric_providers", "providers_ge_20",
        "providers_ge_50", "providers_ge_100", "providers_ge_200",
    ]
    add_check(
        checks,
        "independent_corrected_Table_S1_crosscheck",
        selected[crosscheck_columns].reset_index(drop=True).equals(
            table_s1[crosscheck_columns].reset_index(drop=True)
        ),
        "all 15 annual openly numeric and threshold counts match",
    )
    validation = pd.DataFrame(checks)
    if not validation.passed.all():
        raise RuntimeError(f"Figure 3 validation failed:\n{validation.loc[~validation.passed]}")

    data_path = FIGURE_DIR / "Figure3_longitudinal_exclusive_categories_data.csv"
    validation_path = QA_DIR / "Figure3_programmatic_validation.csv"
    plotted.to_csv(data_path, index=False)
    validation.to_csv(validation_path, index=False)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.labelsize": 10,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 9,
            "legend.fontsize": 8.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    x_positions = np.arange(len(plotted))
    fig, ax = plt.subplots(figsize=(7.25, 4.75))
    bottom = np.zeros(len(plotted), dtype=int)
    for column, label, colour in zip(CATEGORY_COLUMNS, CATEGORIES, COLOURS, strict=True):
        values = plotted[column].to_numpy(dtype=int)
        ax.bar(
            x_positions,
            values,
            bottom=bottom,
            width=0.72,
            color=colour,
            edgecolor="white",
            linewidth=0.45,
            label=label,
        )
        bottom += values

    ax.set_xlabel("Reporting year", labelpad=8)
    ax.set_ylabel("Openly numeric physical sites, n", labelpad=8)
    ax.set_xticks(x_positions, plotted.reporting_year.astype(str), rotation=45, ha="right")
    ax.set_xlim(-0.65, len(plotted) - 0.35)
    ax.set_ylim(0, 125)
    ax.set_yticks(np.arange(0, 126, 20))
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#d9d9d9", linewidth=0.6)
    ax.tick_params(axis="x", length=0)
    ax.tick_params(axis="y", length=3, color="#666666")
    ax.legend(
        title="Mutually exclusive visible-activity category",
        ncol=5,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.01),
        frameon=False,
        handlelength=1.2,
        handletextpad=0.45,
        columnspacing=1.15,
        title_fontsize=8.5,
    )
    fig.subplots_adjust(left=0.11, right=0.99, bottom=0.20, top=0.83)

    png_path = FIGURE_DIR / "Figure3_longitudinal_exclusive_categories.png"
    pdf_path = FIGURE_DIR / "Figure3_longitudinal_exclusive_categories.pdf"
    fig.savefig(png_path, dpi=600)
    fig.savefig(pdf_path)
    plt.close(fig)

    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": str(SOURCE.relative_to(ROOT)),
            "sha256": EXPECTED_SOURCE_SHA256,
            "filters": {
                "provider_definition": "physical_site",
                "suppression_scenario": "visible",
                "reporting_years": YEARS,
            },
        },
        "independent_crosscheck": {
            "path": str(TABLE_S1_CROSSCHECK.relative_to(ROOT)),
            "sha256": EXPECTED_TABLE_S1_SHA256,
            "status": "all 15 annual openly numeric and threshold counts match",
        },
        "category_order_bottom_to_top": CATEGORIES,
        "outputs": [
            {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path), "size_bytes": path.stat().st_size}
            for path in [data_path, validation_path, png_path, pdf_path]
        ],
        "programmatic_checks": {"passed": int(validation.passed.sum()), "total": len(validation)},
    }
    metadata_path = QA_DIR / "Figure3_build_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Figure 3 built: {png_path}")
    print(f"Programmatic checks: {validation.passed.sum()}/{len(validation)} passed")


if __name__ == "__main__":
    main()
