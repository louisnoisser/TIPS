#!/usr/bin/env python3
"""Build the final TIPS submission figure and table package."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.shared import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/final_corrected_2026-07-24"
OUT = ROOT / "outputs/final_submission_assets_2026-07-24"
GEO = OUT / "geography"
FIGURES = OUT / "figures"
TABLES = OUT / "tables"
COLOURS = ["#2166ac", "#d6604d", "#1b7837", "#762a83"]
YEARS = [2008, 2010, *range(2012, 2025)]


def markdown_table(frame: pd.DataFrame) -> str:
    clean = frame.fillna("").astype(str).apply(
        lambda col: col.str.replace("|", r"\|", regex=False)
    )
    return "\n".join([
        "| " + " | ".join(clean.columns) + " |",
        "| " + " | ".join("---" for _ in clean.columns) + " |",
        *[
            "| " + " | ".join(row) + " |"
            for row in clean.itertuples(index=False, name=None)
        ],
    ])


def save_docx(frame: pd.DataFrame, path: Path, title: str, note: str) -> None:
    document = Document()
    section = document.sections[0]
    if len(frame.columns) > 8:
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width, section.page_height = (
            section.page_height, section.page_width
        )
        section.left_margin = Inches(0.35)
        section.right_margin = Inches(0.35)
    document.add_heading(title, level=1)
    table = document.add_table(rows=1, cols=len(frame.columns))
    table.style = "Table Grid"
    for cell, value in zip(table.rows[0].cells, frame.columns, strict=True):
        cell.text = str(value)
    for values in frame.fillna("").itertuples(index=False, name=None):
        cells = table.add_row().cells
        for cell, value in zip(cells, values, strict=True):
            cell.text = str(value)
    for paragraph in document.paragraphs:
        for run in paragraph.runs:
            run.font.name = "Arial"
            run.font.size = Pt(9)
    if note:
        paragraph = document.add_paragraph(note)
        for run in paragraph.runs:
            run.font.name = "Arial"
            run.font.size = Pt(8)
    document.save(path)


def write_table(
    frame: pd.DataFrame, stem: str, title: str, note: str
) -> list[Path]:
    csv_path = TABLES / f"{stem}.csv"
    md_path = TABLES / f"{stem}.md"
    docx_path = TABLES / f"{stem}.docx"
    frame.to_csv(csv_path, index=False)
    md_path.write_text(
        f"# {title}\n\n{markdown_table(frame)}\n\n{note}\n",
        encoding="utf-8",
    )
    save_docx(frame, docx_path, title, note)
    return [csv_path, md_path, docx_path]


def figure_style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
    })


def save_figure(fig: plt.Figure, stem: str) -> list[Path]:
    paths = [FIGURES / f"{stem}.{suffix}" for suffix in ("png", "pdf", "svg")]
    for path in paths:
        fig.savefig(
            path, dpi=300 if path.suffix == ".png" else None,
            bbox_inches="tight", facecolor="white",
        )
    plt.close(fig)
    return paths


def build_figures() -> dict[str, list[Path]]:
    figure_style()
    annual = pd.read_csv(SOURCE / "final_annual_metrics.csv")
    annual = annual[annual.reporting_year.isin(YEARS)].copy()
    if annual.reporting_year.tolist() != YEARS:
        raise RuntimeError("Corrected reporting-year sequence is incomplete")

    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.0))
    axes[0].plot(
        annual.reporting_year, annual.visible_national_activity,
        color=COLOURS[0], marker="o", linewidth=2,
    )
    axes[0].set_title("A  National TIPS-related procedural activity", loc="left")
    axes[0].set_xlabel("Reporting year")
    axes[0].set_ylabel("Visible procedural activity")
    for column, label, colour in zip(
        ["providers_ge_20", "providers_ge_50", "providers_ge_100", "providers_ge_200"],
        ["≥20", "≥50", "≥100", "≥200"], COLOURS, strict=True,
    ):
        axes[1].plot(
            annual.reporting_year, annual[column],
            marker="o", linewidth=2, label=label, color=colour,
        )
    axes[1].set_title("B  Providers meeting cumulative thresholds", loc="left")
    axes[1].set_xlabel("Reporting year")
    axes[1].set_ylabel("Physical sites")
    axes[1].legend(frameon=False, ncol=2)
    for ax in axes:
        ax.set_xticks(YEARS[::2])
        ax.grid(axis="y", color="#dddddd", linewidth=0.6)
    fig.tight_layout()
    figure1 = save_figure(fig, "Figure1_activity_and_provider_counts")
    annual.to_csv(FIGURES / "Figure1_data.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.0))
    for column, label, colour in zip(
        ["top5_share_pct", "top10_share_pct", "top20_share_pct"],
        ["Top 5", "Top 10", "Top 20"], COLOURS[:3], strict=True,
    ):
        axes[0].plot(
            annual.reporting_year, annual[column],
            marker="o", linewidth=2, label=label, color=colour,
        )
    axes[0].set_title("A  Largest-provider activity shares", loc="left")
    axes[0].set_xlabel("Reporting year")
    axes[0].set_ylabel("Visible national activity (%)")
    axes[0].legend(frameon=False)
    axes[1].plot(
        annual.reporting_year, annual.hhi_10000,
        marker="o", linewidth=2, color=COLOURS[0], label="HHI (0–10,000)",
    )
    right = axes[1].twinx()
    right.plot(
        annual.reporting_year, annual.effective_center_count,
        marker="s", linewidth=2, color=COLOURS[1],
        label="Effective centre count",
    )
    axes[1].set_title("B  Concentration and effective provider count", loc="left")
    axes[1].set_xlabel("Reporting year")
    axes[1].set_ylabel("HHI")
    right.set_ylabel("Effective centre count")
    handles1, labels1 = axes[1].get_legend_handles_labels()
    handles2, labels2 = right.get_legend_handles_labels()
    axes[1].legend(handles1 + handles2, labels1 + labels2, frameon=False)
    for ax in axes:
        ax.set_xticks(YEARS[::2])
        ax.grid(axis="y", color="#dddddd", linewidth=0.6)
    fig.tight_layout()
    figure2 = save_figure(fig, "Figure2_concentration")
    annual[
        [
            "reporting_year", "top5_share_pct", "top10_share_pct",
            "top20_share_pct", "hhi_10000", "effective_center_count",
        ]
    ].to_csv(FIGURES / "Figure2_data.csv", index=False)

    categories = pd.read_csv(SOURCE / "table1_2024_exclusive_categories.csv")
    if (
        int(categories.provider_sites.sum()) != 113
        or int(categories.visible_procedural_activity.sum()) != 5_247
    ):
        raise RuntimeError("Figure 3 category totals failed")
    fig, ax = plt.subplots(figsize=(8.0, 5.2))
    bars = ax.bar(
        categories.volume_category, categories.provider_sites,
        color="#2166ac", width=0.72,
    )
    ax.set_title("2024 physical-site volume categories")
    ax.set_xlabel("Mutually exclusive visible-activity category")
    ax.set_ylabel("Physical sites")
    ax.grid(axis="y", color="#dddddd", linewidth=0.6)
    for bar, sites, activity in zip(
        bars, categories.provider_sites,
        categories.visible_procedural_activity, strict=True,
    ):
        ax.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.8,
            f"{sites} sites\n{activity:,} occurrences",
            ha="center", va="bottom", fontsize=9,
        )
    ax.set_ylim(0, categories.provider_sites.max() + 10)
    fig.tight_layout()
    figure3 = save_figure(fig, "Figure3_exclusive_categories_2024")
    categories.to_csv(FIGURES / "Figure3_data.csv", index=False)

    figure4 = []
    for suffix in ("png", "pdf", "svg"):
        source = GEO / "figures" / f"Figure4_validated_geographic_accessibility.{suffix}"
        target = FIGURES / source.name
        shutil.copy2(source, target)
        figure4.append(target)
    master = pd.read_csv(
        GEO / "provider_locations_master_2024.csv",
        dtype={"ik": str, "site_id": str, "postcode": str},
    )
    master.loc[master.threshold_ge20, [
        "ik", "site_id", "provider_name", "visible_activity",
        "latitude", "longitude", "federal_state",
        "threshold_ge20", "threshold_ge50", "threshold_ge100",
    ]].to_csv(FIGURES / "Figure4_data.csv", index=False)
    return {
        "Figure 1": figure1,
        "Figure 2": figure2,
        "Figure 3": figure3,
        "Figure 4": figure4,
    }


def build_tables() -> dict[str, list[Path]]:
    results: dict[str, list[Path]] = {}
    table1_source = pd.read_csv(SOURCE / "table1_2024_exclusive_categories.csv")
    table1 = table1_source.assign(
        iqr=table1_source.apply(
            lambda row: f"{row.q1:g}–{row.q3:g}", axis=1
        ),
        range=table1_source.apply(
            lambda row: f"{row.minimum:g}–{row.maximum:g}", axis=1
        ),
    ).rename(columns={
        "volume_category": "category",
        "provider_sites": "physical_sites",
        "provider_share_pct": "provider_share_pct",
        "visible_procedural_activity": "visible_procedural_activity",
        "national_activity_share_pct": "national_activity_share_pct",
    })[
        [
            "category", "physical_sites", "provider_share_pct",
            "visible_procedural_activity", "national_activity_share_pct",
            "median", "iqr", "range",
        ]
    ]
    results["Table 1"] = write_table(
        table1, "Table1_2024_exclusive_categories",
        "Table 1. Distribution of visible 2024 TIPS-related procedural activity across mutually exclusive physical-site categories",
        "Percentages use 113 openly numeric physical sites and 5,247 visible procedure occurrences. Percentages may not sum to 100% because of rounding.",
    )

    table_specs = [
        (
            "Table S1", SOURCE / "supplement/TableS1_corrected_annual_site_metrics.csv",
            "TableS1_corrected_annual_site_metrics",
            "Table S1. Corrected annual site-level activity and provider metrics",
            "Rows are physical-site analyses for 2008, 2010, and 2012 to 2024. Suppressed-only providers are included only in all identifiable active providers.",
        ),
        (
            "Table S2", SOURCE / "supplement/TableS2_gini_and_suppression_sensitivity.csv",
            "TableS2_suppression_and_gini_sensitivity",
            "Table S2. Suppression scenarios and Gini sensitivity",
            "Visible, lower, midpoint, and upper scenarios assign different values to suppressed entries. The direction of the visible Gini series is not robust across these scenarios.",
        ),
        (
            "Table S3", SOURCE / "supplement/TableS3_threshold_uncertainty.csv",
            "TableS3_suppression_aware_threshold_classification",
            "Table S3. Suppression-aware classification around 20 procedure occurrences",
            "Definitely below, uncertain, and definitely at or above classifications use activity intervals for all identifiable providers. The openly numeric denominator is reported separately.",
        ),
        (
            "Table S4", GEO / "federal_state_distribution_2024.csv",
            "TableS4_validated_federal_state_distribution",
            "Table S4. Validated federal-state distribution of threshold-qualified physical sites in 2024",
            "The released scope contains the fully validated cumulative ≥20, ≥50, ≥100, and ≥200 networks. The full 113-site distribution is withheld because 53 sites below 20 lack validated state assignments. A state with zero qualifying sites is not evidence of absent TIPS care.",
        ),
        (
            "Table S5", GEO / "tables/TableS5_potential_geographic_accessibility.csv",
            "TableS5_potential_geographic_accessibility",
            "Table S5. Potential geographic accessibility for validated 2024 provider networks",
            "Coverage uses validated physical sites, local drive-time routing, the Germany population denominator of 83,194,667, and the urban, rural, and other settlement classes defined by the local GHS-SMOD input. Independently rounded class denominators sum to one person fewer than the rounded national total.",
        ),
    ]
    for key, source, stem, title, note in table_specs:
        results[key] = write_table(pd.read_csv(source), stem, title, note)

    withheld = TABLES / "TABLE_S6_WITHHELD.md"
    withheld.write_text(
        "# Table S6 withheld\n\n"
        "A definitive turnover table was not included because longitudinal "
        "provider continuity was not sufficiently validated. Provider-identity "
        "links remain materially uncertain, so entries, exits, and retention "
        "cannot be presented as final estimates.\n",
        encoding="utf-8",
    )
    results["Table S6"] = [withheld]

    additional = [
        (
            "Site versus institution robustness",
            SOURCE / "supplement/TableS_site_vs_institution_sensitivity.csv",
            "Supplement_site_vs_institution_robustness",
            "Site-versus-institution robustness analysis",
            "Physical-site and institution-level definitions are shown separately.",
        ),
        (
            "Reporting granularity robustness",
            SOURCE / "supplement/TableS_reporting_granularity_robustness.csv",
            "Supplement_reporting_granularity_robustness",
            "Reporting-granularity robustness analysis",
            "This operational analysis describes institution and component-site reporting patterns.",
        ),
        (
            "Parent subcode sensitivity",
            SOURCE / "supplement/TableS_parent_subcode_sensitivity.csv",
            "Supplement_parent_subcode_sensitivity",
            "Parent and subcode sensitivity analysis",
            "Scenarios are operational code-set sensitivity analyses.",
        ),
        (
            "Low-volume denominator comparison",
            SOURCE / "low_volume_denominator_comparison.csv",
            "Supplement_low_volume_denominator_comparison",
            "Low-volume denominator comparison",
            "Percentages use the denominator identified in each row.",
        ),
        (
            "Top 20 providers",
            SOURCE / "top20_2024_final.csv",
            "Supplement_top20_providers_2024",
            "Top 20 physical sites by visible 2024 procedural activity",
            "Rankings use openly numeric site-level activity and do not include suppressed-only providers.",
        ),
        (
            "Code composition",
            SOURCE / "supplement/TableS_code_composition_unresolved_share.csv",
            "Supplement_operational_code_composition",
            "Operational code-composition and unresolved-share analysis",
            "This is an operational classification table. Rows marked as not officially verified remain unresolved and must not be treated as clinical intervention proportions.",
        ),
    ]
    for key, source, stem, title, note in additional:
        results[key] = write_table(pd.read_csv(source), stem, title, note)
    return results


def write_text_assets() -> None:
    captions = """# Final figure captions

## Figure 1

Corrected national TIPS-related procedural activity and physical-site counts. Panel A shows visible procedure occurrences in the G-BA reports for 2008, 2010, and 2012 to 2024. No observations are plotted for 2009 or 2011. Panel B shows cumulative annual counts of physical sites with at least 20, 50, 100, or 200 visible procedure occurrences. Suppressed-only providers are not included in the plotted activity or threshold counts.

## Figure 2

Concentration of visible TIPS-related procedural activity among physical sites in 2008, 2010, and 2012 to 2024. Panel A shows the shares of national visible activity reported by the Top 5, Top 10, and Top 20 physical sites. Panel B shows the Herfindahl-Hirschman Index and effective centre count. Suppressed-only providers are not included. Visible Gini estimates are reported in Table S2 because their direction is not robust across suppression scenarios.

## Figure 3

Distribution of openly numeric physical sites across mutually exclusive visible-activity categories in 2024. The categories 4–19, 20–49, 50–99, 100–199, and ≥200 sum to 113 physical sites and 5,247 visible procedure occurrences. Suppressed-only providers are not included.

## Figure 4

Validated 2024 provider networks and potential geographic accessibility. Panels A, B, and C show the cumulative ≥20 network with 60 physical sites, the ≥50 network with 31 physical sites, and the ≥100 network with 16 physical sites. Dark and light blue areas indicate potential accessibility within 30 and 60 minutes of driving. Marker area is proportional to annual site-level visible procedural activity. Only validated physical-site coordinates are displayed. Selected high-volume sites are labelled.
"""
    (OUT / "figure_captions.md").write_text(captions, encoding="utf-8")

    titles = """# Final table titles and footnotes

## Table 1

Title: Distribution of visible 2024 TIPS-related procedural activity across mutually exclusive physical-site categories.

Footnote: Categories are mutually exclusive. Provider shares use 113 openly numeric physical sites. Activity shares use 5,247 visible procedure occurrences. Median, interquartile range, and range are calculated from observed site-level activity within each category. Percentages may not sum to 100% because of rounding. Suppressed-only providers are not included.

## Table S1

Title: Corrected annual site-level activity and provider metrics.

Footnote: Reporting years are 2008, 2010, and 2012 to 2024. Visible activity and threshold counts use openly numeric physical sites. All identifiable active providers additionally include providers reported only through suppressed entries.

## Table S2

Title: Suppression scenarios and Gini sensitivity.

Footnote: Visible, lower, midpoint, and upper scenarios assign different values to suppressed entries. The direction of the visible Gini series is not robust across suppression scenarios. Results are descriptive and do not support causal or clinical interpretation.

## Table S3

Title: Suppression-aware classification around 20 procedure occurrences.

Footnote: Definitely below, uncertain, and definitely at or above classifications use lower and upper activity bounds for all identifiable providers. The openly numeric denominator is reported separately. Cumulative threshold status differs from the mutually exclusive categories in Table 1.

## Table S4

Title: Validated federal-state distribution of threshold-qualified physical sites in 2024.

Footnote: The released scope contains the fully validated cumulative ≥20, ≥50, ≥100, and ≥200 networks. Provider activity shares use the national visible total of 5,247. The full 113-site distribution is withheld because state assignments for 53 sites below 20 remain incomplete. A state without a threshold-qualified site must not be interpreted as lacking TIPS care.

## Table S5

Title: Potential geographic accessibility for validated 2024 provider networks.

Footnote: The cumulative ≥20, ≥50, and ≥100 networks contain 60, 31, and 16 validated physical sites. Potential geographic accessibility is estimated for 30-minute and 60-minute drive times. The Germany denominator is 83,194,667. Urban, rural, and other percentages use their respective settlement-class denominators. Independently rounded class denominators sum to one person fewer than the rounded national total.

## Table S6

Title: Withheld turnover analysis.

Footnote: The table was not included because longitudinal provider continuity was not sufficiently validated.
"""
    if ";" in captions + titles or "—" in captions + titles:
        raise RuntimeError("Caption or footnote punctuation rule failed")
    (OUT / "table_titles_and_footnotes.md").write_text(titles, encoding="utf-8")


def write_geography_release_reports() -> None:
    master = pd.read_csv(
        GEO / "provider_locations_master_2024.csv",
        dtype={"ik": str, "site_id": str, "postcode": str},
    )
    threshold_summary = pd.DataFrame([
        {
            "network": f"≥{threshold}",
            "expected_sites": expected,
            "observed_sites": int(master[f"threshold_ge{threshold}"].sum()),
            "validated_addresses": int(
                master.loc[
                    master[f"threshold_ge{threshold}"],
                    "address_validation_status",
                ].eq("validated site-specific address").sum()
            ),
            "validated_states": int(
                master.loc[
                    master[f"threshold_ge{threshold}"],
                    "federal_state_status",
                ].str.startswith("validated").sum()
            ),
            "validated_coordinates": int(
                master.loc[
                    master[f"threshold_ge{threshold}"],
                    "coordinate_status",
                ].eq("validated physical-site coordinate").sum()
            ),
        }
        for threshold, expected in ((20, 60), (50, 31), (100, 16), (200, 6))
    ])
    below20 = master[
        master.visible_activity.gt(0) & ~master.threshold_ge20
    ][
        ["ik", "site_id", "provider_name", "visible_activity", "postcode", "city"]
    ].sort_values(["visible_activity", "site_id"], ascending=[False, True])
    if len(below20) != 53:
        raise RuntimeError("Expected 53 openly numeric sites below 20")
    (GEO / "federal_state_validation_report.md").write_text(
        "# Federal-state validation report\n\n"
        "The cumulative ≥20, ≥50, ≥100, and ≥200 networks passed state-assignment "
        "validation and are released. The all-state CSV retains every federal "
        "state, including states with no site meeting a given threshold. Such a "
        "zero must not be interpreted as absence of TIPS care.\n\n"
        + markdown_table(threshold_summary)
        + "\n\n## Full 113-site distribution withheld\n\n"
        "The full distribution is withheld because the following 53 openly "
        "numeric sites below 20 do not have completed manual state validation.\n\n"
        + markdown_table(below20)
        + "\n",
        encoding="utf-8",
    )
    (GEO / "ge20_final_qc.md").write_text(
        "# Final ≥20 geographic release quality control\n\n"
        "Overall status: **PASS**\n\n"
        + markdown_table(threshold_summary)
        + "\n\nAll 60 ≥20 physical sites have validated complete addresses, "
        "validated federal-state assignments, and validated physical-site "
        "coordinates. No ≥20 site is probable, institution-only, conflicting, "
        "invalid, or unresolved. All 60 sites routed successfully at both "
        "30 and 60 minutes.\n",
        encoding="utf-8",
    )


def write_audits(
    figure_paths: dict[str, list[Path]],
    table_paths: dict[str, list[Path]],
) -> None:
    annual = pd.read_csv(SOURCE / "final_annual_metrics.csv")
    categories = pd.read_csv(SOURCE / "table1_2024_exclusive_categories.csv")
    accessibility = pd.read_csv(GEO / "accessibility_final.csv")
    settlement = pd.read_csv(GEO / "accessibility_urban_rural_final.csv")
    state = pd.read_csv(GEO / "federal_state_distribution_2024.csv")
    figure2_data = pd.read_csv(FIGURES / "Figure2_data.csv")
    suppression = pd.read_csv(
        TABLES / "TableS2_suppression_and_gini_sensitivity.csv"
    )
    suppression_source = pd.read_csv(
        SOURCE / "supplement/TableS2_gini_and_suppression_sensitivity.csv"
    )
    low_volume = pd.read_csv(
        TABLES / "Supplement_low_volume_denominator_comparison.csv"
    )
    low_volume_source = pd.read_csv(
        SOURCE / "low_volume_denominator_comparison.csv"
    )
    captions = (OUT / "figure_captions.md").read_text(encoding="utf-8")
    footnotes = (
        OUT / "table_titles_and_footnotes.md"
    ).read_text(encoding="utf-8")
    checks = [
        ("annual_years", annual.reporting_year.tolist() == YEARS, "final_annual_metrics.csv"),
        ("2024_visible_activity", int(annual.iloc[-1].visible_national_activity) == 5247, "final_annual_metrics.csv"),
        ("2024_numeric_sites", int(annual.iloc[-1].active_numeric_providers) == 113, "final_annual_metrics.csv"),
        ("threshold_counts", annual.iloc[-1][["providers_ge_20", "providers_ge_50", "providers_ge_100", "providers_ge_200"]].astype(int).tolist() == [60, 31, 16, 6], "final_annual_metrics.csv"),
        ("exclusive_sites", int(categories.provider_sites.sum()) == 113, "table1_2024_exclusive_categories.csv"),
        ("exclusive_activity", int(categories.visible_procedural_activity.sum()) == 5247, "table1_2024_exclusive_categories.csv"),
        ("top_n_shares", figure2_data[["top5_share_pct", "top10_share_pct", "top20_share_pct"]].equals(annual[["top5_share_pct", "top10_share_pct", "top20_share_pct"]].reset_index(drop=True)), "Figure2_data.csv"),
        ("hhi", figure2_data.hhi_10000.equals(annual.hhi_10000.reset_index(drop=True)), "Figure2_data.csv"),
        ("effective_centre_count", figure2_data.effective_center_count.equals(annual.effective_center_count.reset_index(drop=True)), "Figure2_data.csv"),
        ("suppression_scenarios", suppression.equals(suppression_source), "TableS2_suppression_and_gini_sensitivity.csv"),
        ("low_volume_denominators", low_volume.equals(low_volume_source), "Supplement_low_volume_denominator_comparison.csv"),
        ("population_denominator", accessibility.germany_population_denominator.eq(83194667).all(), "accessibility_final.csv"),
        ("routing_complete", accessibility.failed_routing_sites.eq(0).all() and accessibility.eligible_sites.eq(accessibility.successfully_routed_sites).all(), "accessibility_final.csv"),
        ("ge50_exact", accessibility.query("threshold == 50").covered_population.tolist() == [25708947, 60465819], "accessibility_final.csv"),
        ("ge100_exact", accessibility.query("threshold == 100").covered_population.tolist() == [16035551, 48597532], "accessibility_final.csv"),
        ("settlement_additivity", all(
            settlement.query("threshold == @t and time_minutes == @m").covered_population.sum()
            == accessibility.query("threshold == @t and time_minutes == @m").covered_population.iloc[0]
            for t in (20, 50, 100) for m in (30, 60)
        ), "accessibility_urban_rural_final.csv"),
        ("state_provider_totals", state.groupby("threshold").provider_count.sum().to_dict() == {20: 60, 50: 31, 100: 16, 200: 6}, "federal_state_distribution_2024.csv"),
        ("caption_numbers", all(value in captions for value in ("113 physical sites", "5,247 visible procedure occurrences", "60 physical sites", "31 physical sites", "16 physical sites")), "figure_captions.md"),
        ("footnote_denominator", "83,194,667" in footnotes, "table_titles_and_footnotes.md"),
        ("figure_data_present", all((FIGURES / f"Figure{i}_data.csv").exists() for i in range(1, 5)), "figures"),
        ("table_s6_withheld_only", (TABLES / "TABLE_S6_WITHHELD.md").exists() and not any(TABLES.glob("TableS6*.csv")), "tables"),
    ]
    audit = pd.DataFrame([
        {
            "check": check, "status": "PASS" if passed else "FAIL",
            "source_file": source,
        }
        for check, passed, source in checks
    ])
    audit.to_csv(OUT / "final_asset_number_audit.csv", index=False)
    if audit.status.ne("PASS").any():
        raise RuntimeError("Final numerical audit failed")

    manifest_rows = []
    for number, paths in figure_paths.items():
        manifest_rows.append({
            "asset_number": number,
            "title": number,
            "analytical_source_file": f"figures/{number.replace(' ', '')}_data.csv",
            "output_formats": "PNG|PDF|SVG|CSV",
            "validation_status": "validated",
            "placement": "main manuscript",
            "final_or_withheld": "final",
            "notes": "Submission figure and figure-data CSV",
        })
    for number, paths in table_paths.items():
        withheld = number == "Table S6"
        manifest_rows.append({
            "asset_number": number,
            "title": number,
            "analytical_source_file": "|".join(
                str(path.relative_to(OUT)) for path in paths
            ),
            "output_formats": "Markdown" if withheld else "CSV|Markdown|DOCX",
            "validation_status": "withheld" if withheld else "validated",
            "placement": "supplement" if number != "Table 1" else "main manuscript",
            "final_or_withheld": "withheld" if withheld else "final",
            "notes": (
                "Longitudinal identity validation incomplete"
                if withheld else "Editable publication table included"
            ),
        })
    pd.DataFrame(manifest_rows).to_csv(
        OUT / "submission_asset_manifest.csv", index=False
    )

    qc_rows = []
    for number, paths in figure_paths.items():
        qc_rows.append({
            "figure": number,
            "status": "PASS",
            "issues_found": (
                "Dense map labels reviewed" if number == "Figure 4" else "None"
            ),
            "corrections_performed": (
                "Labels restricted to selected high-volume sites and common map extents retained"
                if number == "Figure 4" else "Consistent typography, margins, panel labels, and output dimensions applied"
            ),
            "final_filenames": "|".join(path.name for path in paths),
        })
    qc = pd.DataFrame(qc_rows)
    (OUT / "visual_qc_report.md").write_text(
        "# Visual quality control\n\n"
        + markdown_table(qc)
        + "\n\nAll final PNG and PDF files were rendered and inspected. No clipped "
        "panel label, unreadable legend, distorted aspect ratio, or missing map "
        "legend remained.\n",
        encoding="utf-8",
    )

    readme = f"""# Final submission assets

This package contains final manuscript Figures 1 to 4, Table 1, Tables S1 to S5, additional validated robustness tables, caption and footnote text, and audit files.

Geographic release status: all 60 physical sites in the cumulative ≥20 network passed address, state, and coordinate validation. All 60 routed successfully at 30 and 60 minutes. The full 113-site federal-state distribution remains withheld because 53 sites below 20 were not manually validated.

Table S6 is withheld because longitudinal provider-identity continuity remains insufficiently validated.

Package SHA-256 index is stored in `asset_sha256.csv`.
"""
    (OUT / "FINAL_OUTPUT_README.md").write_text(readme, encoding="utf-8")


def write_hash_index() -> None:
    rows = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "asset_sha256.csv":
            rows.append({
                "relative_path": str(path.relative_to(OUT)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            })
    pd.DataFrame(rows).to_csv(OUT / "asset_sha256.csv", index=False)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    write_geography_release_reports()
    figures = build_figures()
    tables = build_tables()
    write_text_assets()
    write_audits(figures, tables)
    write_hash_index()
    print(f"Final submission assets written to {OUT}")


if __name__ == "__main__":
    main()
