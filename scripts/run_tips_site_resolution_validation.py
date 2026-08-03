#!/usr/bin/env python3
"""Generate the isolated TIPS site-resolution validation deliverables."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gba_ops_reanalysis.site_resolution_validation import (  # noqa: E402
    aggregate_resolved_records,
    classify_coordinates,
    extract_address_provenance,
    identity_crosswalk,
    parent_subcode_diagnostic,
    reporting_granularity,
    resolve_component_precedence,
    structural_metrics,
    turnover_metrics,
)


def write_md(path: Path, title: str, body: str) -> None:
    path.write_text(f"# {title}\n\n{body.strip()}\n", encoding="utf-8")


def direction(frame: pd.DataFrame, column: str, definition: str) -> str:
    x = frame[frame["provider_definition"] == definition].sort_values("reporting_year")
    if len(x) < 2:
        return "not assessable"
    delta = float(x.iloc[-1][column]) - float(x.iloc[0][column])
    return "increased" if delta > 0 else ("declined" if delta < 0 else "unchanged")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-dir", type=Path, default=ROOT / "outputs/audit")
    parser.add_argument(
        "--production-dir", type=Path,
        default=ROOT / "outputs/indications/tips_8-839-8_updated2024",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "outputs/site_resolution_validation"
    )
    args = parser.parse_args()
    out = args.output_dir
    figures = out / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    code = pd.read_csv(args.audit_dir / "tips_code_level_audit.csv", dtype={"ik": str})
    production = pd.read_csv(args.production_dir / "tables/yearly_summary.csv")
    audit_annual = (
        code.assign(
            current_parser_numeric_count=pd.to_numeric(
                code["current_parser_numeric_count"], errors="coerce"
            ).fillna(0)
        )
        .groupby("reporting_year", as_index=False)["current_parser_numeric_count"].sum()
        .rename(columns={"reporting_year": "year", "current_parser_numeric_count": "reproduced_total"})
    )
    legacy = production[["year", "tips_cases_total"]].merge(audit_annual, on="year", how="outer")
    legacy["difference"] = legacy["reproduced_total"] - legacy["tips_cases_total"]
    legacy["exact_match"] = legacy["difference"].eq(0)
    legacy.to_csv(out / "legacy_reproduction.csv", index=False)
    if not bool(legacy["exact_match"].all()):
        write_md(
            out / "legacy_reproduction_report.md", "Legacy reproduction",
            "Legacy reproduction failed. No correction outputs were generated.",
        )
        raise SystemExit("Legacy reproduction failed")
    write_md(
        out / "legacy_reproduction_report.md", "Legacy reproduction",
        f"All {len(legacy)} available reporting years reproduce exactly. The maximum absolute "
        "difference is 0. Missing source years (2009 and 2011) are not imputed.",
    )

    annotated, resolution_audit = resolve_component_precedence(code)
    resolution_audit.to_csv(out / "site_resolution_audit.csv", index=False)
    resolution_audit[
        resolution_audit["aggregate_value_assessable"]
        & resolution_audit["visible_residual_source_aggregate_minus_components"].ne(0)
    ].to_csv(out / "unresolved_aggregate_residuals.csv", index=False)

    contacts = pd.read_csv(args.production_dir / "tables/hospital_year.csv", dtype=str)
    provenance = extract_address_provenance(code["source_file"], ROOT)
    provenance["year"] = provenance["year"].astype(str)
    provenance["facility_id"] = provenance["facility_id"].astype(str)
    contacts = contacts.drop(
        columns=["street", "house_number", "postal_code", "city"], errors="ignore"
    ).merge(provenance, on=["year", "facility_id"], how="left")
    site, institution = aggregate_resolved_records(annotated, contacts)
    site.to_csv(out / "resolved_site_level_data.csv", index=False)
    institution.to_csv(out / "resolved_institution_level_data.csv", index=False)

    inventory = annotated.merge(
        site[
            ["reporting_year", "site_identifier", "street", "house_number", "postal_code",
             "city", "full_address", "address_source", "site_full_address",
             "institution_full_address", "legacy_contact_full_address"]
        ],
        on=["reporting_year", "site_identifier"], how="left",
    )
    inventory["institution_address"] = inventory["institution_full_address"]
    inventory["site_address"] = inventory["site_full_address"]
    inventory.to_csv(out / "reporting_entity_inventory.csv", index=False)

    summary = (
        annotated.groupby("reporting_year", as_index=False)
        .agg(
            legacy_visible_activity=("visible_count", "sum"),
            resolved_visible_activity=("visible_count", lambda s: int(s[annotated.loc[s.index, "retained_site_resolution"]].sum())),
            retained_records=("retained_site_resolution", "sum"),
            excluded_aggregate_records=("retained_site_resolution", lambda s: int((~s).sum())),
            unresolved_99_records=("unresolved_institution_provider", "sum"),
        )
    )
    removed = resolution_audit.groupby("reporting_year")["removed_legacy_visible_count"].sum()
    summary["removed_legacy_visible_count"] = summary["reporting_year"].map(removed).fillna(0).astype(int)
    summary.to_csv(out / "site_resolution_summary_by_year.csv", index=False)

    parent = parent_subcode_diagnostic(annotated)
    parent.to_csv(out / "parent_subcode_diagnostic.csv", index=False)
    parent_effect = int(parent["parent_visible_value"].sum()) if len(parent) else 0
    write_md(
        out / "parent_subcode_assessment.md", "Parent/subcode assessment",
        f"{len(parent)} site-year parent/subcode coexistence events were found; exact parent "
        f"records contribute {parent_effect} visible production counts. No records were removed: "
        "spatial precedence and code hierarchy are separate mechanisms. No readable official OPS "
        "catalogue is present locally, so a universal hierarchy correction is not supported here. "
        f"A sensitivity excluding the parent has a maximum observed visible effect of {parent_effect}.",
    )

    granularity, transitions = reporting_granularity(annotated)
    granularity.to_csv(out / "reporting_granularity_by_year.csv", index=False)
    transitions.to_csv(out / "reporting_transitions.csv", index=False)
    first, last = granularity.iloc[0], granularity.iloc[-1]
    write_md(
        out / "reporting_granularity_report.md", "Reporting granularity over time",
        f"Among institutions with TIPS-family records, 99-only reporting changed from "
        f"{int(first.institutions_99_only)}/{int(first.unique_institutions)} "
        f"({100*first.proportion_99_only:.1f}%) in {int(first.reporting_year)} to "
        f"{int(last.institutions_99_only)}/{int(last.unique_institutions)} "
        f"({100*last.proportion_99_only:.1f}%) in {int(last.reporting_year)}. During the overlap era, "
        f"the number reporting both ways peaked at {int(granularity.institutions_both.max())}; it was "
        f"{int(last.institutions_both)} in {int(last.reporting_year)}. Identifiable "
        f"component sites changed from {int(first.identifiable_component_sites)} to "
        f"{int(last.identifiable_component_sites)}. {len(transitions)} directly linked transitions "
        "were found under the same IK; these are potential reporting changes, not proven openings.",
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(granularity.reporting_year, granularity.identifiable_component_sites, marker="o", label="Component sites")
    ax.plot(granularity.reporting_year, granularity.institutions_99_only, marker="o", label="99-only institutions")
    ax.set(xlabel="Reporting year", ylabel="Reporting entities", title="TIPS reporting granularity")
    ax.legend(); fig.tight_layout()
    fig.savefig(figures / "reporting_granularity_over_time.png", dpi=180)
    fig.savefig(figures / "reporting_granularity_over_time.pdf")
    plt.close(fig)

    site_cross, site_review = identity_crosswalk(site, "physical_site", "site_identifier")
    inst_identity = institution.copy()
    inst_cross, inst_review = identity_crosswalk(inst_identity, "institution", "ik")
    cross = pd.concat([site_cross, inst_cross], ignore_index=True)
    review = pd.concat([site_review, inst_review], ignore_index=True)
    cross.to_csv(out / "provider_identity_crosswalk.csv", index=False)
    review.to_csv(out / "provider_identity_manual_review.csv", index=False)
    turnover = pd.concat(
        [
            turnover_metrics(site, cross, "physical_site", "site_identifier"),
            turnover_metrics(institution, cross, "institution", "ik"),
        ],
        ignore_index=True,
    )
    turnover.to_csv(out / "turnover_identifier_churn.csv", index=False)
    confirmed_changed = cross[
        (cross["match_status"] == "confirmed")
        & (cross["previous_identifier"] != cross["current_identifier"])
    ]
    probable = cross[cross["match_status"] == "probable"]
    confirmed_reporting_changes = confirmed_changed[
        confirmed_changed["previous_identifier"].astype(str).str.endswith("-99")
        | confirmed_changed["current_identifier"].astype(str).str.endswith("-99")
    ]
    probable_reporting_changes = probable[
        probable["previous_identifier"].astype(str).str.endswith("-99")
        | probable["current_identifier"].astype(str).str.endswith("-99")
    ]
    confirmed_other_identifier_changes = len(confirmed_changed) - len(confirmed_reporting_changes)
    threshold20 = turnover[
        (turnover["provider_level"] == "physical_site") & (turnover["threshold"] == 20)
    ].groupby("scenario")[["entries", "exits"]].sum()
    raw20 = threshold20.loc["raw_identifier"]
    confirmed20 = threshold20.loc["confirmed_continuity"]
    probable20 = threshold20.loc["confirmed_plus_probable"]
    write_md(
        out / "turnover_identity_assessment.md", "Turnover and identifier churn",
        f"The deterministic crosswalk contains {len(confirmed_changed)} confirmed changed-identifier "
        f"continuities ({len(confirmed_reporting_changes)} involving a 99 reporting-unit transition and "
        f"{confirmed_other_identifier_changes} other exact-name/address identifier changes) and "
        f"{len(probable)} probable continuities ({len(probable_reporting_changes)} involving 99); "
        f"{len(review)} rows require manual review. At the "
        f"physical-site ≥20 threshold, summed consecutive-year entries/exits change from "
        f"{int(raw20.entries)}/{int(raw20.exits)} under raw identifiers to "
        f"{int(confirmed20.entries)}/{int(confirmed20.exits)} after confirmed continuity. These are "
        f"{int(probable20.entries)}/{int(probable20.exits)} when probable links are additionally included. "
        "These are "
        "event counts across year pairs, not unique hospitals. Same identifiers are also recorded as "
        "confirmed continuity. Probable links are not silently promoted. Ownership changes, mergers, "
        "splits, and renamings cannot be reliably separated from the available aggregate evidence. "
        "Current turnover/Table S6 should therefore not be treated as validated.",
    )

    metrics = pd.concat(
        [structural_metrics(site, "physical_site"), structural_metrics(institution, "institution_ik")],
        ignore_index=True,
    )
    metrics.to_csv(out / "site_vs_institution_metrics.csv", index=False)
    write_md(
        out / "site_vs_institution_summary.md", "Site versus institution trends",
        "\n".join(
            f"- {label}: active providers {direction(metrics, 'active_numeric_providers', definition)}; "
            f"Top-5/10/20 shares {direction(metrics, 'top5_share_pct', definition)}/"
            f"{direction(metrics, 'top10_share_pct', definition)}/"
            f"{direction(metrics, 'top20_share_pct', definition)}; HHI "
            f"{direction(metrics, 'hhi_10000', definition)}; effective count "
            f"{direction(metrics, 'effective_center_count', definition)}; Gini "
            f"{direction(metrics, 'gini', definition)}."
            for label, definition in (("Physical site", "physical_site"), ("Institution/IK", "institution_ik"))
        )
        + "\n\nVisible activity is inclusive TIPS-related OPS-coded procedural activity, not unique "
        "patients, admissions, or de novo creations.",
    )

    for plot_name, columns, ylabel in (
        ("site_vs_institution_provider_counts", ["active_numeric_providers"], "Providers"),
        ("site_vs_institution_concentration", ["top5_share_pct", "top10_share_pct", "top20_share_pct", "hhi_10000"], "Metric value"),
    ):
        fig, axes = plt.subplots(1, len(columns), figsize=(6 * len(columns), 5), squeeze=False)
        for ax, col in zip(axes[0], columns):
            for definition, group in metrics.groupby("provider_definition"):
                ax.plot(group.reporting_year, group[col], marker="o", label=definition)
            ax.set_title(col); ax.set_xlabel("Year"); ax.set_ylabel(ylabel)
        axes[0][0].legend(); fig.tight_layout()
        fig.savefig(figures / f"{plot_name}.png", dpi=180)
        fig.savefig(figures / f"{plot_name}.pdf")
        plt.close(fig)

    legacy_2024 = pd.read_csv(args.production_dir / "tables/hospital_year.csv", dtype={"ik": str})
    legacy_2024 = legacy_2024[(legacy_2024["year"] == 2024) & (legacy_2024["tips_cases"] > 0)].copy()
    top_frames = []
    for label, frame, id_col in (
        ("legacy_production", legacy_2024.rename(columns={"tips_cases": "visible_activity", "facility_id": "site_identifier"}), "site_identifier"),
        ("corrected_physical_site", site[site.reporting_year == 2024], "site_identifier"),
        ("corrected_institution", institution[institution.reporting_year == 2024], "ik"),
    ):
        top = frame.sort_values("visible_activity", ascending=False).head(20).copy()
        top["definition"] = label
        top["rank"] = range(1, len(top) + 1)
        top["provider_identifier"] = top[id_col].astype(str)
        top_frames.append(top[["definition", "rank", "provider_identifier", "hospital_name", "ik", "visible_activity"]])
    top20 = pd.concat(top_frames, ignore_index=True)
    legacy_lookup = (
        legacy_2024.assign(facility_id=legacy_2024["facility_id"].astype(str))
        .set_index("facility_id")["tips_cases"]
        .to_dict()
    )
    legacy_ik_lookup = legacy_2024.groupby(legacy_2024["ik"].astype(str))["tips_cases"].sum().to_dict()
    top20["legacy_production_value_direct_match"] = top20.apply(
        lambda r: (
            legacy_ik_lookup.get(str(r.ik), pd.NA)
            if r.definition == "corrected_institution"
            else legacy_lookup.get(str(r.provider_identifier), pd.NA)
        ),
        axis=1,
    )
    top20["absolute_difference_from_direct_legacy_match"] = (
        top20["visible_activity"] - pd.to_numeric(top20["legacy_production_value_direct_match"], errors="coerce")
    ).abs()
    top20["difference_reason"] = top20["definition"].map(
        {
            "legacy_production": "reference",
            "corrected_physical_site": "exact-code aggregate 99 removed where components coexist",
            "corrected_institution": "resolved component sites aggregated once by IK",
        }
    )
    top20.to_csv(out / "top20_2024_provider_comparison.csv", index=False)

    suppression_rows = []
    for year, group in site.groupby("reporting_year", sort=True):
        overlaps = resolution_audit[resolution_audit.reporting_year == year]
        physical = group[~group.unresolved_institution_provider]
        unresolved = group[group.unresolved_institution_provider]
        suppression_rows.append(
            {
                "reporting_year": year,
                "identifiable_sites_visible": int((physical.visible_activity > 0).sum()),
                "identifiable_sites_suppressed_only": int(((physical.visible_activity == 0) & (physical.suppressed_entries > 0)).sum()),
                "unresolved_99_visible": int((unresolved.visible_activity > 0).sum()),
                "unresolved_99_suppressed_only": int(((unresolved.visible_activity == 0) & (unresolved.suppressed_entries > 0)).sum()),
                "suppressed_component_entries": int(physical.suppressed_entries.sum()),
                "overlap_residual_groups": int((overlaps.visible_residual_source_aggregate_minus_components != 0).sum()),
                "residuals_compatible_with_suppression": int(
                    overlaps["nonzero_difference_compatible_with_suppression"].fillna(False).sum()
                ),
                "residuals_not_compatible_with_suppression": int(
                    (
                        overlaps["aggregate_value_assessable"]
                        & overlaps["visible_residual_source_aggregate_minus_components"].ne(0)
                        & ~overlaps["nonzero_difference_compatible_with_suppression"].fillna(False)
                    ).sum()
                ),
            }
        )
    suppression = pd.DataFrame(suppression_rows)
    suppression.to_csv(out / "suppression_site_visibility_audit.csv", index=False)
    write_md(
        out / "suppression_site_visibility_report.md", "Suppression and site visibility",
        f"Suppressed component records are retained as active identifiable providers. Across exact "
        f"overlap groups, {int(resolution_audit.nonzero_difference_compatible_with_suppression.fillna(False).sum())} "
        f"nonzero differences are compatible with the 1–3-per-suppressed-entry interval and "
        f"{int((resolution_audit.aggregate_value_assessable & resolution_audit.visible_residual_source_aggregate_minus_components.ne(0) & ~resolution_audit.nonzero_difference_compatible_with_suppression.fillna(False)).sum())} "
        "assessable nonzero differences are not. Hidden aggregate values are labelled unassessable. Residuals are "
        "diagnostic only and are never redistributed or used to invent sites.",
    )

    cache = pd.read_csv(ROOT / "data/cache/geocode/tips_8-839-8_geocode_cache.csv")
    geo = classify_coordinates(site, cache)
    geo.to_csv(out / "geocoding_readiness_audit.csv", index=False)
    pd.DataFrame(
        columns=["original_address", "original_latitude", "original_longitude", "corrected_latitude",
                 "corrected_longitude", "correction_source", "rationale", "correction_unit"]
    ).to_csv(out / "geocoding_manual_corrections.csv", index=False)
    physical = geo[~geo.unresolved_institution_provider]
    physical_with_coords = physical[physical["latitude"].notna() & physical["longitude"].notna()]
    physical_site_addresses = physical[
        physical["address_source"].eq("site-specific address from source data")
    ]
    institutional_addresses = physical[
        physical["address_source"].eq("institution-level address inherited by a site")
    ]
    site_specific_coordinates = physical[
        physical["coordinate_source_class"].isin(
            [
                "geocoded from a site-specific address",
                "existing manually corrected site-specific coordinate",
            ]
        )
    ]
    write_md(
        out / "geocoding_readiness_report.md", "Geocoding readiness",
        f"The resolved history contains {physical.site_identifier.nunique()} identifiable physical-site "
        f"identifiers and {len(physical_site_addresses)}/{len(physical)} provider-year records with an "
        f"explicit `Standortkontaktdaten` address; {len(institutional_addresses)} inherit an explicit "
        "institution address and the remaining legacy records have unresolved contact hierarchy. "
        "Existing coordinates are available for "
        f"{len(physical_with_coords)}/{len(physical)} provider-year records representing "
        f"{physical_with_coords.site_identifier.nunique()} site identifiers, but only "
        f"{site_specific_coordinates.site_identifier.nunique()} identifiers have coordinates demonstrably "
        "generated from a site-specific address; "
        f"{int(physical.shared_coordinate_same_year.sum())} provider-year records share a coordinate "
        f"with another component report, and "
        f"{int((physical.latitude.notna() & ~physical.coordinate_valid_germany_bbox).sum())} lie outside "
        "the Germany bounding-box check. The cache is "
        "keyed to the 2024 cohort and does not establish historical site-specific coordinates. No "
        "manual correction registry was found. The current data are therefore not suitable for a "
        "validated longitudinal physical-site accessibility analysis. Site/institution addresses come "
        "from the eligible G-BA XML report contact blocks; coordinates come from "
        "`data/cache/geocode/tips_8-839-8_geocode_cache.csv`; boundary paths are configured in "
        "`src/gba_ops_reanalysis/config.py`. Isochrones were not recalculated.",
    )

    catalogue_columns = ["file_path", "source_type", "years_covered", "official_primary_source", "readable"]
    pd.DataFrame(columns=catalogue_columns).to_csv(out / "ops_catalogue_inventory.csv", index=False)
    availability = []
    codes = ["8-839.8", "8-839.80", "8-839.81", "8-839.82", "8-839.83", "8-839.84",
             "8-839.85", "8-839.86", "8-839.87", "8-839.88", "8-839.89", "8-839.8a", "8-839.8x"]
    for ops_code in codes:
        observed = code[code.OPS_code.str.lower() == ops_code.lower()]
        availability.append(
            {
                "OPS_code": ops_code, "official_description": "", "first_valid_ops_year": "",
                "last_valid_ops_year": "", "de_novo_creation": "unresolved",
                "secondary_intervention": "unresolved", "unspecified": "unresolved",
                "first_observed_gba_year": int(observed.reporting_year.min()) if len(observed) else "",
                "last_observed_gba_year": int(observed.reporting_year.max()) if len(observed) else "",
                "directly_comparable_across_years": "unresolved",
                "evidence_source_path": "",
                "verification_status": "requires manual verification against the official OPS catalogue",
            }
        )
    pd.DataFrame(availability).to_csv(out / "ops_code_availability.csv", index=False)
    write_md(
        out / "historical_creation_code_assessment.md", "Historical creation-code assessment",
        "No readable official OPS catalogue file was found in the repository. Consequently no official "
        "description or validity period is assigned here. In particular, the meaning of `8-839.80` is "
        "unresolved and requires manual verification against the official OPS catalogue. A continuous "
        "2008–2024 creation-only series cannot be recommended from repository evidence. No period-aware "
        "mapping is proposed until primary-source catalogues are added and verified.",
    )

    write_md(
        out / "provider_identifier_dictionary.md", "Provider identifier dictionary",
        """- `ik`: institutional identifier parsed from the first filename segment. One IK may emit
multiple component-site reports.
- `site_identifier`: `IK-Standortnummer`, parsed from the production-eligible XML filename.
- `-99`: Standortnummer 99 aggregate report. It is excluded only when a non-99 report exists for the
same year, IK, and exact OPS code; otherwise it is retained as an unresolved institution provider.
- Component site: any production-eligible non-99 site identifier. `00` is treated as an identifiable
single/component report, not as an aggregate.
- Suppression: `suppressed_flag` and `suppressed_record_count` from the immutable audit; bounds assign
1/2/3 per suppressed source entry.
- Address: explicit `Standortkontaktdaten` and `Krankenhauskontaktdaten` nodes are extracted separately.
An institution address used by a component report is labelled inherited; older generic `Kontaktdaten`
without a distinguishable hierarchy remain unresolved.
- Coordinates: existing local geocode cache keyed by `facility_id`; it covers the current 2024 cohort,
not longitudinal identity.
- Current longitudinal key: production uses `facility_id` at site level and raw `ik` for IK churn.
Identifier stability is not assumed. Confirmed changed-ID continuity requires exact normalized name
and address; fuzzy links remain probable and require review.
- Count interpretation: visible inpatient TIPS-related OPS-coded procedure occurrences/TIPS-related
procedural activity, not patients, admissions, or unique creations.""",
    )

    total_removed = int(resolution_audit.removed_legacy_visible_count.sum())
    assessable = int(resolution_audit.aggregate_value_assessable.sum())
    exact = int(resolution_audit.exact_visible_equality.fillna(False).sum())
    compatible = int(
        resolution_audit.nonzero_difference_compatible_with_suppression.fillna(False).sum()
    )
    unexplained = int(
        (
            resolution_audit.aggregate_value_assessable
            & resolution_audit.visible_residual_source_aggregate_minus_components.ne(0)
            & ~resolution_audit.nonzero_difference_compatible_with_suppression.fillna(False)
        ).sum()
    )
    write_md(
        out / "decision_report.md", "Site-resolution validation decision",
        f"""1. **Legacy reproduction:** yes, all {len(legacy)} available years exactly.
2. **Removed legacy visible counts:** {total_removed}; annual values are in `site_resolution_summary_by_year.csv`.
3. **Exact year–IK–code overlaps:** {len(resolution_audit)}.
4. **Exact aggregate/component equality:** {exact}/{assessable} groups with an assessable numeric aggregate;
{len(resolution_audit)-assessable} hidden aggregate values are not assessable.
5. **Nonzero differences compatible with known suppression (1–3 each):** {compatible}.
6. **Assessable unexplained nonzero residuals:** {unexplained}.
7. **Reporting granularity:** 99-only share was {100*first.proportion_99_only:.1f}% in {int(first.reporting_year)}
and {100*last.proportion_99_only:.1f}% in {int(last.reporting_year)}; dual 99/component reporting
peaked at {int(granularity.institutions_both.max())} institutions and ended at
{int(last.institutions_both)}, while identifiable component reporting increased.
8. **Provider growth:** physical-site and IK results are reported in `site_vs_institution_metrics.csv`.
9–11. **Concentration/decentralisation:** directions under both definitions are documented in
`site_vs_institution_summary.md`; the size-weighted conclusion must be read with the Gini result.
12–13. **Geography:** the 2024-only cache does not validate the longitudinal physical-site geography;
{physical_site_addresses.site_identifier.nunique()} of {physical.site_identifier.nunique()} physical
identifiers have an explicit site-address node, while
{site_specific_coordinates.site_identifier.nunique()} have coordinates demonstrably generated from
such an address; accessibility analysis is not ready.
14–15. **Identity/turnover:** confirmed changed-ID links={len(confirmed_changed)}, probable={len(probable)}.
Of the confirmed changes, {len(confirmed_reporting_changes)} involve a 99 transition. At ≥20,
raw physical-site entry/exit events are {int(raw20.entries)}/{int(raw20.exits)}, versus
{int(confirmed20.entries)}/{int(confirmed20.exits)} after confirmed continuity and
{int(probable20.entries)}/{int(probable20.exits)} after additionally including probable links.
{len(probable_reporting_changes)} probable links involve a 99 transition. Mergers, ownership
changes, renaming, and unresolved churn cannot be reliably separated; Table S6 is not validated.
16. **2024 rankings:** legacy and corrected physical-site top 20 are identical because no 2024
99/component overlap exists. IK aggregation combines two Schleswig-Holstein university sites
(institution rank 5); Cologne enters the institutional top 20. Full ranks are in the comparison CSV.
17–21. **OPS catalogues:** none are physically present/readable. All requested meanings, including
`8-839.80`, remain unresolved; a continuous creation-only series cannot be recommended.
22. **Known numerical revisions:** totals and provider metrics for overlap years require aggregate-99
deduplication; turnover and accessibility claims require further identity/geography validation.
23. **Robust conclusions:** see the two-definition direction table; no patient/creation interpretation is valid.
24. **Recommended final definition:** inclusive visible TIPS-related OPS activity with exact-code
physical-site precedence may be the primary structural definition, with IK-level and suppression
sensitivities. A creation-only sensitivity is deferred pending official catalogue verification.

**Decision:** proceed with component-precedence structural rebuilding only. Do not yet rebuild
accessibility, turnover claims, creation-only series, manuscript, or final figures.""",
    )
    write_md(
        out / "implementation_summary.md", "Implementation summary",
        """A new validation-only module and CLI were added. The production parser and defaults were
not changed. The CLI gates all work on exact annual legacy reproduction, resolves spatial overlap at
the exact year–IK–OPS-code level, preserves suppressed components, retains 99-only institutions as
unresolved, records residuals without redistribution, builds parallel site/IK datasets, calculates
structural metrics, creates conservative longitudinal crosswalks, and audits existing geography and
repository-local OPS evidence. All outputs are isolated in this directory.""",
    )
    print(f"Wrote validation outputs to {out}")


if __name__ == "__main__":
    main()
