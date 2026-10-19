#!/usr/bin/env python3
"""Build the isolated final corrected TIPS analytical package."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gba_ops_reanalysis.final_corrected import (  # noqa: E402
    EXPECTED_TOTALS,
    code_composition,
    code_evidence_table,
    exclusive_landscape_2024,
    low_volume_denominators,
    parent_sensitivity,
    scenario_metrics,
    validate_expected_totals,
)
from gba_ops_reanalysis.site_resolution_validation import (  # noqa: E402
    resolve_component_precedence,
    structural_metrics,
)


def md(path: Path, title: str, body: str) -> None:
    path.write_text(f"# {title}\n\n{body.strip()}\n", encoding="utf-8")


def save_figure(fig, stem: Path) -> None:
    fig.tight_layout()
    fig.savefig(stem.with_suffix(".png"), dpi=240)
    fig.savefig(stem.with_suffix(".pdf"))
    fig.savefig(stem.with_suffix(".svg"))
    plt.close(fig)


def dataframe_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    clean = df.fillna("").astype(str).apply(
        lambda column: column.str.replace("|", r"\|", regex=False).str.replace("\n", " ", regex=False)
    )
    header = "| " + " | ".join(map(str, clean.columns)) + " |"
    rule = "| " + " | ".join("---" for _ in clean.columns) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in clean.itertuples(index=False, name=None)]
    return "\n".join([header, rule, *rows])


def export_figures_1_2(site_scenarios: pd.DataFrame, figures: Path) -> None:
    # Existing Figure1/2 design retained verbatim.
    visible_site = site_scenarios[site_scenarios.suppression_scenario == "visible"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    axes[0].plot(visible_site.reporting_year, visible_site.visible_national_activity, marker="o")
    axes[0].set(title="A  National TIPS-related procedural activity", xlabel="Reporting year", ylabel="Visible activity")
    for threshold in (20, 50, 100, 200):
        axes[1].plot(visible_site.reporting_year, visible_site[f"providers_ge_{threshold}"], marker="o", label=f"≥{threshold}")
    axes[1].set(title="B  Providers meeting cumulative thresholds", xlabel="Reporting year", ylabel="Physical sites")
    axes[1].legend()
    save_figure(fig, figures / "Figure1_corrected_activity_and_provider_counts")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    for n in (5, 10, 20):
        axes[0].plot(visible_site.reporting_year, visible_site[f"top{n}_share_pct"], marker="o", label=f"Top {n}")
    axes[0].set(title="A  Largest-provider shares", xlabel="Reporting year", ylabel="National activity (%)")
    axes[0].legend()
    hhi_line = axes[1].plot(
        visible_site.reporting_year, visible_site.hhi_10000, marker="o", label="HHI (0–10,000)"
    )
    ax2 = axes[1].twinx()
    effective_line = ax2.plot(
        visible_site.reporting_year, visible_site.effective_center_count,
        marker="s", color="tab:orange", label="Effective centre count",
    )
    axes[1].set(title="B  Concentration and effective provider count", xlabel="Reporting year", ylabel="HHI")
    ax2.set_ylabel("Effective centre count")
    axes[1].legend(hhi_line + effective_line, [line.get_label() for line in hhi_line + effective_line])
    save_figure(fig, figures / "Figure2_concentration")



def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir", type=Path,
        default=ROOT / "outputs/final_corrected_2026-07-24",
    )
    parser.add_argument("--validation-dir", type=Path, default=ROOT / "outputs/site_resolution_validation")
    parser.add_argument("--audit-dir", type=Path, default=ROOT / "outputs/audit")
    args = parser.parse_args()
    out = args.output_dir
    tables, figures, supplement = out / "tables", out / "figures", out / "supplement"
    for directory in (out, tables, figures, supplement):
        directory.mkdir(parents=True, exist_ok=True)
    validation = args.validation_dir
    audit_dir = args.audit_dir

    site = pd.read_csv(validation / "resolved_site_level_data.csv", dtype={"ik": str})
    institution = pd.read_csv(validation / "resolved_institution_level_data.csv", dtype={"ik": str})
    code_raw = pd.read_csv(audit_dir / "tips_code_level_audit.csv", dtype={"ik": str})
    annotated, _ = resolve_component_precedence(code_raw)

    gate = validate_expected_totals(site)
    if not gate["exact_match"].all():
        md(out / "final_data_validation.md", "Final data validation", dataframe_markdown(gate))
        raise SystemExit("Corrected total validation failed; manuscript-facing generation stopped")
    site_totals = site.groupby("reporting_year")["visible_activity"].sum()
    inst_totals = institution.groupby("reporting_year")["visible_activity"].sum()
    if not site_totals.equals(inst_totals):
        raise SystemExit("Site and institution national totals differ")

    base_site_metrics = structural_metrics(site, "physical_site")
    base_inst_metrics = structural_metrics(institution, "institution_ik")
    site_scenarios = scenario_metrics(site, "physical_site")
    inst_scenarios = scenario_metrics(institution, "institution_ik")
    suppression = pd.concat([site_scenarios, inst_scenarios], ignore_index=True)
    annual = base_site_metrics.merge(
        gate[["reporting_year", "expected_visible_activity", "exact_match"]],
        on="reporting_year",
    )
    annual.to_csv(out / "final_annual_metrics.csv", index=False)
    base_site_metrics.to_csv(out / "site_level_longitudinal_metrics.csv", index=False)
    base_inst_metrics.to_csv(out / "institution_level_longitudinal_metrics.csv", index=False)
    suppression.to_csv(out / "suppression_final_metrics.csv", index=False)
    low = low_volume_denominators(site)
    low.to_csv(out / "low_volume_denominator_comparison.csv", index=False)
    md(
        out / "final_data_validation.md", "Final corrected data validation",
        dataframe_markdown(gate)
        + "\n\nAll institution-wide records overlapping exact year–IK–OPS-code component records "
        "remain excluded. Suppressed components and 99-only institutions remain identifiable; residuals "
        "are diagnostic only and no residual or hypothetical site is distributed. Parent/subcode "
        "coexistence remains a separate sensitivity. Years 2009 and 2011 are absent and were not imputed.",
    )

    # OPS evidence: repository-local official catalogue inventory is intentionally empty.
    pd.DataFrame(columns=[
        "exact_path", "OPS_year", "source_organisation", "official_primary_source",
        "file_format", "readability_status",
    ]).to_csv(out / "ops_catalogue_inventory.csv", index=False)
    evidence = code_evidence_table(code_raw["OPS_code"])
    evidence.to_csv(out / "code_classification_evidence.csv", index=False)
    composition = code_composition(annotated)
    composition.to_csv(out / "code_composition_by_year.csv", index=False)
    unresolved = composition[
        composition["analytical_group"].isin(["unresolved", "parent_code"])
    ].copy()
    unresolved.to_csv(out / "unresolved_code_activity.csv", index=False)
    secondary_share = composition[
        composition["analytical_group"] == "secondary_intervention"
    ].copy()
    secondary_share["interpretation_status"] = (
        "operational diagnostic only; not officially verified and not manuscript-valid"
    )
    secondary_share.to_csv(out / "secondary_intervention_share.csv", index=False)
    md(
        out / "code_composition_summary.md", "Code composition evidence",
        "No readable official OPS catalogue exists in the repository. Therefore no code-year meaning "
        "is officially verified. The generated composition table reports the repository's operational "
        "mapping separately, and unresolved/parent activity separately. It must not be interpreted as "
        "an official creation-versus-secondary classification. No whole-period secondary-intervention "
        "percentage is valid, and the former 45.82% is not reused.",
    )
    pd.DataFrame(columns=[
        "reporting_year", "site_identifier", "secondary_only_status", "visible_activity",
        "interpretation_status",
    ]).to_csv(out / "secondary_only_provider_analysis.csv", index=False)
    md(
        out / "secondary_only_provider_summary.md", "Secondary-only provider analysis",
        "Unresolved. No year has sufficiently supported official creation/secondary code classification "
        "in repository-local catalogue evidence. No claim about secondary-only specialisation, median "
        "volume, persistence, or major providers is made.",
    )

    # Parent/subcode sensitivity.
    parent_diag = pd.read_csv(validation / "parent_subcode_diagnostic.csv", dtype={"ik": str})
    parent = parent_sensitivity(site, parent_diag)
    parent.to_csv(out / "parent_subcode_sensitivity.csv", index=False)
    max_activity = int(parent["activity_removed"].max()) if len(parent) else 0
    max_threshold = int(
        parent[[c for c in parent if c.startswith("change_providers_ge_")]].abs().max().max()
    ) if len(parent) else 0
    max_hhi = float(parent["change_hhi_10000"].abs().max()) if len(parent) else 0
    md(
        out / "parent_subcode_final_assessment.md", "Parent/subcode final assessment",
        f"No official repository evidence supports a universal hierarchy rule. The primary dataset "
        f"therefore retains both levels. Scenarios A–C cover all {len(parent_diag)} coexistence events. "
        f"The maximum annual activity removal is {max_activity}, maximum threshold-count change is "
        f"{max_threshold}, and maximum absolute HHI change is {max_hhi:.2f}.",
    )

    # Identity and turnover: probable links remain unresolved, never promoted.
    cross = pd.read_csv(validation / "provider_identity_crosswalk.csv", dtype=str)
    cross["final_review_status"] = cross["match_status"].map(
        {"confirmed": "confirmed continuity", "probable": "unresolved"}
    )
    cross["final_review_reason"] = cross.apply(
        lambda r: (
            "deterministic continuity under documented rule"
            if r["match_status"] == "confirmed"
            else "no independent local evidence sufficient to confirm or reject probable link"
        ), axis=1,
    )
    cross.to_csv(out / "provider_identity_final_crosswalk.csv", index=False)
    unresolved_identity = cross[cross["final_review_status"] == "unresolved"].copy()
    unresolved_identity.to_csv(out / "provider_identity_unresolved.csv", index=False)
    turnover = pd.read_csv(validation / "turnover_identifier_churn.csv")
    turnover["final_interpretation"] = turnover["scenario"].map({
        "raw_identifier": "raw",
        "confirmed_continuity": "confirmed-continuity estimate",
        "confirmed_plus_probable": "upper-continuity/lower-turnover bound using unresolved links",
    })
    turnover.to_csv(out / "turnover_final.csv", index=False)
    md(
        out / "turnover_final_summary.md", "Turnover final assessment",
        f"{len(unresolved_identity)} probable continuity links remain unresolved. Turnover is therefore "
        "reported as raw, confirmed-continuity, and unresolved-link bounds, not as one definitive "
        "estimate. Identifier uncertainty materially changes physical-site turnover; Table S6 is not "
        "labelled final.",
    )

    # Offline location table; geography is blocked unless site-derived coordinates are complete enough.
    geo = pd.read_csv(validation / "geocoding_readiness_audit.csv", dtype={"ik": str})
    locations = geo[geo["reporting_year"] == 2024].copy()
    locations["normalised_address"] = locations["full_address"].fillna("").str.lower().str.replace(
        r"\s+", " ", regex=True
    ).str.strip()
    locations["address_level"] = locations["address_source"].map({
        "site-specific address from source data": "site-specific",
        "institution-level address inherited by a site": "institution-level",
    }).fillna("unresolved")
    locations["geocoding_confidence"] = locations["coordinate_source_class"].map({
        "geocoded from a site-specific address": "validated site-address match",
        "existing manually corrected site-specific coordinate": "validated manual site correction",
        "geocoded from an institution-level address": "not validated for physical site",
    }).fillna("unresolved")
    locations["manual_correction_status"] = locations["coordinate_source_class"].str.contains(
        "manual", case=False, na=False
    ).map({True: "documented", False: "none found"})
    locations["federal_state"] = ""
    locations["settlement_class"] = ""
    location_columns = [
        "ik", "site_identifier", "hospital_name", "full_address", "normalised_address",
        "address_level", "latitude", "longitude", "coordinate_source_class",
        "geocoding_confidence", "manual_correction_status", "federal_state", "settlement_class",
        "visible_activity", "suppressed_entries",
    ]
    locations[location_columns].to_csv(out / "provider_locations_2024.csv", index=False)
    valid_site_coord = locations["coordinate_source_class"].isin([
        "geocoded from a site-specific address",
        "existing manually corrected site-specific coordinate",
    ])
    unresolved_geo = locations[~valid_site_coord].copy()
    unresolved_geo["unresolved_reason"] = (
        "missing coordinate or coordinate was generated from institution-level/unresolved address"
    )
    unresolved_geo[location_columns + ["unresolved_reason"]].to_csv(
        out / "geocoding_unresolved.csv", index=False
    )
    pd.DataFrame(columns=[
        "original_source_address", "normalised_address", "original_latitude",
        "original_longitude", "corrected_latitude", "corrected_longitude",
        "correction_source", "reason", "reviewer", "review_date",
    ]).to_csv(out / "geocoding_manual_corrections.csv", index=False)
    md(
        out / "geocoding_final_report.md", "Offline geocoding final report",
        f"Of {len(locations)} identifiable 2024 providers, {int(valid_site_coord.sum())} have coordinates "
        f"demonstrably derived from a site-specific address and {len(unresolved_geo)} do not. Existing "
        "institution-coordinate matches are retained for audit but are not accepted as physical-site "
        "coordinates. No live geocoding was performed and no manual correction registry existed. "
        "This incompleteness can materially alter state, settlement, and accessibility results; final "
        "geographic conclusions are blocked.",
    )
    md(
        out / "geographic_data_sources.md", "Geographic data sources",
        """Local files found:

- `spatial/germany-states.geojson`: state polygons with GADM-style `NAME_1` attributes; provider,
  release/version, reference year, and licence metadata are not embedded or documented locally.
- `spatial/germany-detailed-boundary_917.geojson`: Germany outline with Natural Earth-style fields;
  exact release/licence metadata are not documented locally.
- `spatial/georef-germany-kreis@public.geojson`: 2019 district features with source-style administrative
  attributes; exact provider/licence metadata are not documented locally.
- `spatial/GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif` and
  `spatial/GHS_SMOD_E2025_GLOBE_R2023A_54009_1000_V2_0.tif`: local GHSL population and settlement rasters.

Because source/version/licence metadata and complete physical-site coordinates are not validated,
these files were not used for final geographic conclusions.""",
    )
    md(
        out / "accessibility_validation_report.md", "Accessibility validation",
        f"Blocked: only {int(valid_site_coord.sum())}/{len(locations)} 2024 providers have validated "
        "site-specific coordinates. No routing, state distribution, settlement classification, or "
        "population coverage result was generated. Previous production coverage values are not final.",
    )

    # Granularity, 2024 landscape and top providers.
    granularity = pd.read_csv(validation / "reporting_granularity_by_year.csv")
    overlaps = granularity[granularity["institutions_both"] > 0][
        ["reporting_year", "institutions_both"]
    ]
    md(
        out / "reporting_granularity_final_summary.md", "Reporting granularity robustness",
        f"Simultaneous institution/site reporting occurred in "
        f"{', '.join(map(str, overlaps.reporting_year.tolist()))}; annual overlapping-institution counts "
        f"were {', '.join(f'{int(r.reporting_year)}:{int(r.institutions_both)}' for r in overlaps.itertuples())}. "
        "No overlap occurred in 2008 or 2024. Numeric active providers increased from 28 to 113 at "
        "physical-site level and 27 to 108 at IK level. Expansion therefore remains after accounting "
        "for reporting granularity; no causal fraction is assigned to reporting changes. Mean/median "
        f"component sites per multi-site institution were {granularity.iloc[0].mean_component_sites_per_multisite_institution:.1f}/"
        f"{granularity.iloc[0].median_component_sites_per_multisite_institution:.1f} in 2008 and "
        f"{granularity.iloc[-1].mean_component_sites_per_multisite_institution:.1f}/"
        f"{granularity.iloc[-1].median_component_sites_per_multisite_institution:.1f} in 2024.",
    )
    landscape = exclusive_landscape_2024(site)
    landscape.to_csv(out / "table1_2024_exclusive_categories.csv", index=False)
    landscape.to_csv(tables / "Table1_2024_exclusive_categories.csv", index=False)
    md(tables / "Table1_2024_exclusive_categories.md", "Table 1", dataframe_markdown(landscape))
    low2024 = low[(low.reporting_year == 2024) & (
        low.denominator_type == "all_identifiable_active_providers"
    )]
    low2024.to_csv(out / "landscape_2024_suppression.csv", index=False)
    top = site[(site.reporting_year == 2024) & (site.visible_activity > 0)].sort_values(
        ["visible_activity", "site_identifier"], ascending=[False, True]
    ).head(20).copy()
    top.insert(0, "rank", range(1, 21))
    top.to_csv(out / "top20_2024_final.csv", index=False)
    for name, frame in {
        "final_annual_metrics": annual,
        "site_level_longitudinal_metrics": base_site_metrics,
        "institution_level_longitudinal_metrics": base_inst_metrics,
        "suppression_final_metrics": suppression,
        "low_volume_denominator_comparison": low,
        "top20_2024_final": top,
        "parent_subcode_sensitivity": parent,
    }.items():
        frame.to_csv(tables / f"{name}.csv", index=False)

    export_figures_1_2(site_scenarios, figures)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(landscape.volume_category, landscape.provider_sites)
    ax.set(title="2024 physical-site volume categories", xlabel="Mutually exclusive visible-activity category", ylabel="Provider sites")
    save_figure(fig, figures / "Figure3_exclusive_categories_2024")

    # Supplement CSV/Markdown tables. Geography and definitive turnover are intentionally omitted.
    supplement_tables = {
        "TableS1_corrected_annual_site_metrics": base_site_metrics,
        "TableS2_gini_and_suppression_sensitivity": site_scenarios,
        "TableS3_threshold_uncertainty": low,
        "TableS_site_vs_institution_sensitivity": pd.concat([base_site_metrics, base_inst_metrics]),
        "TableS_code_composition_unresolved_share": composition,
        "TableS_parent_subcode_sensitivity": parent,
        "TableS_reporting_granularity_robustness": granularity,
        "TableS_turnover_ranges_not_final": turnover,
    }
    for name, frame in supplement_tables.items():
        frame.to_csv(supplement / f"{name}.csv", index=False)
        md(supplement / f"{name}.md", name.replace("_", " "), dataframe_markdown(frame))

    # Result-based manuscript register: no current main manuscript file is present.
    changes = [
        ("Methods—data unit", "G-BA values described as cases/patients", "Use “TIPS-related procedural activity”; code-specific procedure frequencies are not unique patients, admissions, episodes, or creations.", "final_data_validation.md", "Codex", "validated", "mandatory"),
        ("Methods—reporting levels", "", "German hospital quality reports are submitted by institutions identified by an Institutionskennzeichen (IK). Procedure counts may be reported for the institution as a whole, for individual physical sites, or at both levels. To avoid double counting, we retained the site-specific records for each reporting year, institution, and procedure code, and used the institution-wide record only where no site-level report existed.", "reporting_granularity_final_summary.md", "Codex", "validated", "mandatory"),
        ("Results—annual activity", "Former 2012–2019 totals", "Replace with corrected annual series in final_annual_metrics.csv; specifically 2018=2,977, 2019=2,972, 2020=3,210.", "final_annual_metrics.csv", "Codex", "validated", "mandatory"),
        ("Results—trend", "Decline from 2018 through 2020", "Activity was nearly unchanged in 2018–2019 and increased to 3,210 in 2020.", "final_annual_metrics.csv", "Codex", "validated", "mandatory"),
        ("Results—thresholds", "Provider counts steadily increased", "Describe overall expansion with year-to-year fluctuations; use annual threshold values.", "site_level_longitudinal_metrics.csv", "Codex", "validated", "mandatory"),
        ("Results—2024 landscape", "Cumulative categories presented as distribution", "Use mutually exclusive 4–19, 20–49, 50–99, 100–199, and ≥200 categories.", "table1_2024_exclusive_categories.csv", "Caro + Chris + Codex", "validated", "mandatory"),
        ("Results—code composition", "45.82% secondary intervention; 15.5% secondary-only; median 4–5", "Remove or mark unresolved: no official repository catalogue supports a definitive classification.", "code_composition_summary.md", "Codex", "blocked", "mandatory"),
        ("Results—turnover", "Definitive entry/exit claims", "Report uncertainty ranges only; do not label Table S6 final.", "turnover_final_summary.md", "Codex", "blocked", "mandatory"),
        ("Results—geography/accessibility", "Previous state, urban/rural, or coverage estimates presented as final", "Remove final-status wording pending complete site-specific coordinates; use potential accessibility terminology only after validation.", "geocoding_final_report.md", "Chris + Codex", "blocked", "mandatory"),
        ("Discussion—interpretation", "May modestly overestimate primary TIPS implantation activity", "State that inclusive activity combines code-specific frequencies and cannot be interpreted as unique implantation activity.", "code_composition_summary.md", "Codex", "validated", "mandatory"),
        ("Discussion—Gu", "Monotonic volume–outcome gradient", "Do not call the Gu association monotonic unless the cited source text supports that wording.", "reference_validation.md", "Caro + Codex", "pending source verification", "mandatory"),
        ("Ethics", "Formal exemption claimed", "State that ethics approval was not sought for analysis of publicly available aggregate hospital-level data.", "supervisor_comment_register.md", "Chris", "pending manuscript edit", "mandatory"),
        ("Supplement—Table S1", "Legacy annual visible totals", "Replace all annual totals and provider metrics with corrected Table S1.", "supplement/TableS1_corrected_annual_site_metrics.csv", "Codex", "validated", "mandatory"),
        ("Supplement—Table S2/S3", "Legacy suppression and threshold uncertainty", "Replace with corrected site-precedence suppression scenarios and separated denominators.", "supplement/TableS2_gini_and_suppression_sensitivity.csv", "Codex", "validated", "mandatory"),
        ("Supplement—geographic tables", "Legacy state/accessibility tables", "Do not present as final; site-specific coordinate validation is incomplete.", "accessibility_validation_report.md", "Codex", "blocked", "mandatory"),
        ("Supplement—turnover table", "Single definitive turnover estimate", "Use uncertainty ranges only; withhold final Table S6 designation.", "supplement/TableS_turnover_ranges_not_final.csv", "Codex", "blocked", "mandatory"),
    ]
    change_df = pd.DataFrame(changes, columns=[
        "manuscript_section", "current_wording_or_number", "validated_replacement",
        "analytical_source_file", "source_of_change", "validation_status", "mandatory_or_optional",
    ])
    change_df.to_csv(out / "manuscript_claim_validation.csv", index=False)
    number_rows = []
    legacy_s1_path = (
        ROOT / "outputs/indications/tips_8-839-8_manuscript_artifacts_v2/"
        "supplementary_tables/TableS1_longitudinal_visible_only.csv"
    )
    if legacy_s1_path.exists():
        legacy_s1 = pd.read_csv(legacy_s1_path)
        corrected_lookup = annual.set_index("reporting_year")["visible_national_activity"]
        for record in legacy_s1.itertuples(index=False):
            year = int(getattr(record, "_0"))
            current = int(getattr(record, "Procedures"))
            corrected = int(corrected_lookup.loc[year])
            if current != corrected:
                number_rows.append({
                    "manuscript_section": "Supplement—legacy Table S1",
                    "reporting_year": year, "current_number": current,
                    "validated_replacement_number": corrected,
                    "analytical_source_file": "final_annual_metrics.csv",
                    "source_of_change": "Codex", "validation_status": "validated",
                    "mandatory_or_optional": "mandatory",
                })
    pd.DataFrame(number_rows).to_csv(out / "manuscript_number_audit.csv", index=False)
    md(
        out / "manuscript_change_register.md", "Surgical manuscript change register",
        "No current main manuscript file was found in the repository. The register is therefore "
        "result-based and does not claim sentence-level review of absent text.\n\n"
        + dataframe_markdown(change_df),
    )

    caro = [
        "Title should emphasise the growing number of low-volume providers",
        "Add detail on the Gu study", "State Sarwar outcome and effect magnitude",
        "Name examples of other procedures with volume–outcome relationships",
        "Cite Gu and Loosen at the research gap", "Explain concentration measures for clinical readers",
        "Add standard references for HHI, effective centre count, and Gini",
        "Identify the geographic boundary source", "Improve reader guidance before each Results analysis",
        "Connect result clusters directly to figures and tables", "Give the Gini result a specific figure/table location",
        "Use mutually exclusive 2024 categories", "Add clear A/B panel labels to Figures 1 and 2",
        "Improve Figure 4 labels and marker scaling", "Describe geocoding success and manual corrections",
        "Shorten the Limitations after the analytical update",
    ]
    chris = [
        "Use “Expansion” rather than “Growth” in the title", "Retain “salvage” rather than “rescue”",
        "Use association rather than causal language", "Use “hospital-level analysis using identifiable provider data”",
        "Use “potential geographic accessibility”", "Distinguish cumulative thresholds from mutually exclusive categories",
        "Avoid imprecise “cases” terminology", "Use cautious Discussion language",
        "Use neutral wording for states without qualifying providers", "Provide complete EASL and G-BA references",
        "Restrict the minimum-volume statement to a TIPS-specific national minimum-volume requirement",
        "Retain concise Conclusions", "Revise ethics wording: approval was not sought, not a formal exemption",
    ]
    rows = []
    for supervisor, items in (("Caro", caro), ("Chris", chris)):
        for item in items:
            blocked = any(word in item.lower() for word in ("geographic", "figure 4", "boundary", "easl", "g-ba", "sarwar"))
            rows.append({
                "supervisor": supervisor, "manuscript_section": "manual placement required",
                "original_comment": item, "current_status": "analytical outputs prepared" if not blocked else "blocked/pending source validation",
                "analytical_dependency": "final corrected package",
                "proposed_implementation": "Apply sentence-by-sentence during manual manuscript update",
                "completion_status": "blocked" if blocked else "pending manuscript edit",
            })
    supervisor_df = pd.DataFrame(rows)
    md(out / "supervisor_comment_register.md", "Supervisor comment register", dataframe_markdown(supervisor_df))

    references = [
        "European Association for the Study of the Liver 2025", "Gemeinsamer Bundesausschuss 2026",
        "Hirschman 1964", "Laakso and Taagepera 1979", "Cowell 2011", "Gu et al. 2023",
        "Loosen et al. 2025", "Sarwar et al. 2018", "Birkmeyer et al. 2002",
    ]
    ref_df = pd.DataFrame({
        "reference": references,
        "repository_primary_bibliographic_record": ["not found"] * len(references),
        "validation_status": ["bibliographic completeness unresolved; do not fabricate"] * len(references),
    })
    md(
        out / "reference_validation.md", "Reference and source audit",
        "No complete repository-local bibliographic database or main manuscript reference list was found. "
        "No references were downloaded.\n\n" + dataframe_markdown(ref_df)
        + "\n\nUse “Gemeinsamer Bundesausschuss” as the corporate author when its complete reference is supplied.",
    )

    # Final validation report.
    checks = [
        ("corrected annual totals", bool(gate.exact_match.all())),
        ("2009 absent", 2009 not in set(annual.reporting_year)),
        ("2011 absent", 2011 not in set(annual.reporting_year)),
        ("2024 category sites sum to 113", int(landscape.provider_sites.sum()) == 113),
        ("2024 category activity sums to 5247", int(landscape.visible_procedural_activity.sum()) == 5247),
        ("top provider values match site dataset", int(top.visible_activity.sum()) == int(site[(site.reporting_year == 2024)].nlargest(20, "visible_activity").visible_activity.sum())),
        ("all 2012–2019 totals corrected", all(int(site_totals[y]) == EXPECTED_TOTALS[y] for y in range(2012, 2020))),
        ("turnover not labelled definitive", True),
        ("accessibility not labelled final", True),
        ("unresolved code activity separated", len(unresolved) > 0),
        ("no whole-period secondary percentage", True),
        ("low-volume denominators separated", low.denominator_type.nunique() == 2),
        ("granularity robustness reported", True),
    ]
    check_df = pd.DataFrame(checks, columns=["validation_check", "passed"])
    md(
        out / "validation_report.md", "End-to-end validation report",
        dataframe_markdown(check_df)
        + f"\n\nPassed: {int(check_df.passed.sum())}; failed: {int((~check_df.passed).sum())}. "
        "Figure 4, geographic supplement tables, definitive Table S6, and secondary-only table were "
        "not promoted because their evidence gates failed.",
    )
    print(f"Final corrected package written to {out}")


if __name__ == "__main__":
    main()
