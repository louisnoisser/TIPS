#!/usr/bin/env python3
"""Build the strict offline 2024 TIPS geographic validation package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gba_ops_reanalysis.geography_validation import (  # noqa: E402
    EXPECTED_NETWORK_COUNTS,
    address_status,
    apply_manual_reviews,
    manual_priority,
    network_masks,
    normalize_address,
    query_matches_address,
    reconstruct_provider_sets,
    validate_provider_sets,
)
from gba_ops_reanalysis.urban_rural import classify_points  # noqa: E402


def md(path: Path, title: str, body: str) -> None:
    path.write_text(f"# {title}\n\n{body.strip()}\n", encoding="utf-8")


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    clean = df.fillna("").astype(str).apply(
        lambda c: c.str.replace("|", r"\|", regex=False).str.replace("\n", " ", regex=False)
    )
    return "\n".join([
        "| " + " | ".join(clean.columns) + " |",
        "| " + " | ".join("---" for _ in clean.columns) + " |",
        *["| " + " | ".join(row) + " |" for row in clean.itertuples(index=False, name=None)],
    ])


def state_from_coordinates(frame: pd.DataFrame) -> pd.Series:
    states = gpd.read_file(ROOT / "spatial/germany-states.geojson").to_crs("EPSG:4326")
    states = states.rename(columns={"NAME_1": "coordinate_state"})
    valid = frame["latitude"].notna() & frame["longitude"].notna()
    result = pd.Series("", index=frame.index, dtype=object)
    if valid.any():
        points = gpd.GeoDataFrame(
            frame.loc[valid, ["site_identifier"]].copy(),
            geometry=gpd.points_from_xy(frame.loc[valid, "longitude"], frame.loc[valid, "latitude"]),
            crs="EPSG:4326",
        )
        joined = gpd.sjoin(points, states[["coordinate_state", "geometry"]], how="left", predicate="within")
        joined_states = joined["coordinate_state"].fillna("")
        unmatched = joined_states.eq("")
        if unmatched.any():
            # The local state polygons generalise coastlines. Retain exact coastal
            # hospital points when they are no more than 2 km from the nearest state.
            projected_points = points.loc[unmatched].to_crs("EPSG:25832")
            projected_states = states[["coordinate_state", "geometry"]].to_crs("EPSG:25832")
            nearest = gpd.sjoin_nearest(
                projected_points, projected_states, how="left", max_distance=2_000,
                distance_col="boundary_distance_m",
            )
            joined_states.loc[unmatched] = nearest["coordinate_state"].fillna("").to_numpy()
        result.loc[valid] = joined_states.to_numpy()
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir", type=Path,
        default=ROOT / "outputs/geography_validation_2026-07-24",
    )
    parser.add_argument(
        "--manual-review", type=Path, default=None,
        help="Optional completed editable review CSV from a prior run",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    out, figures, tables = args.output_dir, args.output_dir / "figures", args.output_dir / "tables"
    for directory in (out, figures, tables):
        directory.mkdir(parents=True, exist_ok=True)

    validation = ROOT / "outputs/site_resolution_validation"
    final = ROOT / "outputs/final_corrected_2026-07-24"
    site = pd.read_csv(validation / "resolved_site_level_data.csv", dtype={"ik": str, "postal_code": str})
    providers = reconstruct_provider_sets(site)
    checks = validate_provider_sets(providers)
    if not all(checks.values()):
        md(out / "provider_set_validation.md", "Provider set validation", markdown_table(
            pd.DataFrame(checks.items(), columns=["check", "passed"])
        ))
        raise SystemExit("Provider set validation failed")
    provider_columns = [
        "reporting_year", "ik", "site_identifier", "hospital_name", "visible_activity",
        "suppressed_only", "exclusive_volume_category", "threshold_ge20",
        "threshold_ge50", "threshold_ge100", "threshold_ge200",
    ]
    providers[provider_columns].to_csv(out / "provider_sets_2024.csv", index=False)
    md(
        out / "provider_set_validation.md", "Final corrected 2024 provider sets",
        markdown_table(pd.DataFrame(checks.items(), columns=["check", "passed"]))
        + "\n\nAll threshold sets are nested; the source is the immutable corrected physical-site dataset.",
    )

    # Address evidence is carried from explicit XML-node provenance extraction.
    addresses = providers.copy()
    addresses["original_address"] = addresses["full_address"].fillna("")
    addresses["normalised_address"] = addresses["original_address"].map(normalize_address)
    addresses["federal_state_directly_stated"] = ""
    addresses["exact_source_field_or_xml_path"] = addresses["address_source"].map({
        "site-specific address from source data": ".//Standortkontaktdaten/Kontakt_Zugang",
        "institution-level address inherited by a site": ".//Krankenhauskontaktdaten/Kontakt_Zugang",
    }).fillna("legacy/generic contact field; exact hierarchy unresolved")
    addresses["source_type"] = addresses["address_source"].map({
        "site-specific address from source data": "original G-BA site-specific XML field",
        "institution-level address inherited by a site": "original G-BA institution-level XML field",
    }).fillna("unresolved local XML contact evidence")
    addresses["address_validation_status"] = addresses.apply(address_status, axis=1)
    address_columns = [
        "ik", "site_identifier", "hospital_name", "original_address", "normalised_address",
        "street", "house_number", "postal_code", "city", "federal_state_directly_stated",
        "address_source_file", "exact_source_field_or_xml_path", "source_type",
        "address_validation_status",
    ]
    addresses[address_columns].to_csv(out / "provider_addresses_2024.csv", index=False)
    address_counts = addresses["address_validation_status"].value_counts()
    md(
        out / "address_source_audit.md", "Physical-site address source audit",
        f"Addresses were reconstructed from the original G-BA XML provenance already retained in the "
        f"corrected site dataset. Explicit site-specific and complete addresses: "
        f"{int(address_counts.get('validated site-specific address', 0))}; probable/incomplete site "
        f"addresses: {int(address_counts.get('probable site-specific address', 0))}; institution-only: "
        f"{int(address_counts.get('institution-level address only', 0))}; missing: "
        f"{int(address_counts.get('no address found', 0))}. Unicode is normalised with NFKC/casefold, "
        "while original text is retained. Institution evidence is never promoted to site evidence.",
    )

    # Coordinate inventory from the only local TIPS cache.
    cache_path = ROOT / "data/cache/geocode/tips_8-839-8_geocode_cache.csv"
    cache = pd.read_csv(cache_path).rename(columns={"geocode_key": "site_identifier"})
    work = addresses.merge(cache, on="site_identifier", how="left")
    work["local_coordinate_source_path"] = str(cache_path.relative_to(ROOT))
    work["query_address_level"] = work["address_validation_status"].map({
        "validated site-specific address": "site-specific candidate",
        "probable site-specific address": "site-specific candidate",
        "institution-level address only": "institution-level",
    }).fillna("unresolved")
    work["query_matches_physical_site_address"] = work.apply(
        lambda r: query_matches_address(r.get("geocode_query"), r.get("original_address")), axis=1
    )
    work["coordinate_key"] = work.apply(
        lambda r: (
            f"{float(r.latitude):.6f},{float(r.longitude):.6f}"
            if pd.notna(r.get("latitude")) and pd.notna(r.get("longitude")) else ""
        ), axis=1
    )
    work["coordinate_reused"] = work["coordinate_key"].ne("") & work.duplicated(
        "coordinate_key", keep=False
    )
    work["coordinate_state"] = state_from_coordinates(work)
    work["within_germany"] = work["coordinate_state"].ne("")
    statuses, reasons = [], []
    for row in work.itertuples():
        has = pd.notna(row.latitude) and pd.notna(row.longitude)
        if not has:
            status, reason = "unresolved coordinate", "no local coordinate linked to site identifier"
        elif not row.within_germany:
            status, reason = "invalid coordinate", "coordinate lies outside local Germany state polygons"
        elif row.coordinate_reused:
            status, reason = "duplicate coordinate requiring review", "coordinate reused by distinct site identifier"
        elif row.address_validation_status == "institution-level address only":
            status, reason = "institution-level coordinate only", "query is based on institution-level address evidence"
        elif not row.query_matches_physical_site_address:
            status, reason = "coordinate/address mismatch", "cached query does not match physical-site address"
        elif row.address_validation_status == "validated site-specific address":
            status = "probable physical-site coordinate"
            reason = (
                "exact site-address query and Germany polygon match, but no local postcode-to-state/"
                "city reference exists for independent consistency validation"
            )
        else:
            status, reason = "unresolved coordinate", "site address or coordinate provenance is incomplete"
        statuses.append(status); reasons.append(reason)
    work["coordinate_validation_status"] = statuses
    work["coordinate_validation_reason"] = reasons

    # Settlement labels are retained only as audit context and never promoted for unvalidated coordinates.
    work["settlement_class"] = ""
    coord_rows = work[work["latitude"].notna() & work["longitude"].notna()].copy()
    if len(coord_rows):
        labelled = classify_points(coord_rows)
        mapping = dict(zip(labelled["site_identifier"], labelled["urban_rural"]))
        work["settlement_class"] = work["site_identifier"].map(mapping).fillna("")

    # State validation is independent: no local postcode-state crosswalk was found, so coordinate-only
    # assignments are not promoted to address-validated state assignments.
    state_status, state_source, final_state = [], [], []
    for row in work.itertuples():
        if row.address_validation_status == "institution-level address only":
            state_status.append("institution-level evidence only")
            state_source.append("institution address / coordinate audit only")
            final_state.append("")
        elif row.address_validation_status in {"validated site-specific address", "probable site-specific address"}:
            state_status.append("unresolved")
            state_source.append("site postcode present but no local postcode-to-state reference")
            final_state.append("")
        else:
            state_status.append("unresolved"); state_source.append("no site-specific address evidence"); final_state.append("")
    work["federal_state"] = final_state
    work["federal_state_source"] = state_source
    work["federal_state_status"] = state_status
    work["postcode_ambiguous"] = False
    state_columns = [
        "ik", "site_identifier", "hospital_name", "visible_activity", "postal_code", "city",
        "address_validation_status", "coordinate_state", "federal_state", "federal_state_source",
        "federal_state_status", "postcode_ambiguous",
    ]
    work[state_columns].to_csv(out / "federal_state_assignment_audit.csv", index=False)

    coord_columns = [
        "ik", "site_identifier", "hospital_name", "visible_activity", "latitude", "longitude",
        "geocode_source", "local_coordinate_source_path", "geocode_query", "query_address_level",
        "query_matches_physical_site_address", "coordinate_reused", "within_germany",
        "coordinate_state", "coordinate_validation_status", "coordinate_validation_reason",
    ]
    work[coord_columns].to_csv(out / "coordinate_inventory_2024.csv", index=False)
    conflict_mask = ~work["coordinate_validation_status"].isin(
        ["validated physical-site coordinate", "probable physical-site coordinate"]
    )
    work.loc[conflict_mask, coord_columns].to_csv(out / "coordinate_conflicts_2024.csv", index=False)
    coord_counts = work["coordinate_validation_status"].value_counts()
    md(
        out / "coordinate_audit_report.md", "Coordinate audit",
        f"The local cache contains coordinates for {int(work.latitude.notna().sum())}/193 providers. "
        f"Strict validation found {int(coord_counts.get('validated physical-site coordinate', 0))} validated, "
        f"{int(coord_counts.get('probable physical-site coordinate', 0))} probable, "
        f"{int(coord_counts.get('institution-level coordinate only', 0))} institution-only, "
        f"{int(coord_counts.get('unresolved coordinate', 0))} unresolved, "
        f"{int(coord_counts.get('invalid coordinate', 0))} invalid, and "
        f"{int(coord_counts.get('duplicate coordinate requiring review', 0))} duplicated coordinates "
        "requiring review. Probable coordinates are not accepted for accessibility.",
    )

    # Master table and editable review files.
    # Optional user-reviewed evidence is ingested only when explicitly supplied.
    for column in (
        "manual_status", "manual_address", "manual_postcode", "manual_federal_state",
        "manual_latitude", "manual_longitude", "manual_source", "manual_notes",
        "address_confirmation", "federal_state_confirmation", "coordinate_confirmation",
        "evidence_source", "review_notes",
    ):
        work[column] = ""
    if args.manual_review is not None:
        reviewed = pd.read_csv(args.manual_review, dtype=str).fillna("")
        work = apply_manual_reviews(work, reviewed)

        # Corrected/confirmed coordinates must be re-audited after import.
        work["coordinate_key"] = work.apply(
            lambda r: (
                f"{float(r.latitude):.6f},{float(r.longitude):.6f}"
                if pd.notna(r.get("latitude")) and pd.notna(r.get("longitude")) else ""
            ), axis=1
        )
        work["coordinate_reused"] = work["coordinate_key"].ne("") & work.duplicated(
            "coordinate_key", keep=False
        )
        work["coordinate_state"] = state_from_coordinates(work)
        work["within_germany"] = work["coordinate_state"].ne("")
        reviewed_coordinate = work["coordinate_validation_status"].eq(
            "validated physical-site coordinate"
        )
        invalid_reviewed = reviewed_coordinate & ~work["within_germany"]
        duplicate_reviewed = reviewed_coordinate & work["coordinate_reused"]
        state_disagreement = (
            reviewed_coordinate
            & work["federal_state"].ne("")
            & work["coordinate_state"].ne(work["federal_state"])
        )
        work.loc[invalid_reviewed, "coordinate_validation_status"] = "invalid coordinate"
        work.loc[invalid_reviewed, "coordinate_validation_reason"] = (
            "manually supplied coordinate lies outside Germany"
        )
        work.loc[duplicate_reviewed, "coordinate_validation_status"] = (
            "duplicate coordinate requiring review"
        )
        work.loc[duplicate_reviewed, "coordinate_validation_reason"] = (
            "manually confirmed coordinate remains duplicated across distinct sites"
        )
        work.loc[state_disagreement, "coordinate_validation_status"] = (
            "coordinate/address mismatch"
        )
        work.loc[state_disagreement, "coordinate_validation_reason"] = (
            "manually confirmed federal state disagrees with coordinate-derived state"
        )
        concordant = (
            work["coordinate_validation_status"].eq("validated physical-site coordinate")
            & work["federal_state_status"].str.startswith("validated")
            & work["coordinate_state"].eq(work["federal_state"])
        )
        work.loc[concordant, "federal_state_status"] = (
            "validated from both address and coordinate"
        )

        work["settlement_class"] = ""
        coord_rows = work[work["latitude"].notna() & work["longitude"].notna()].copy()
        if len(coord_rows):
            labelled = classify_points(coord_rows)
            mapping = dict(zip(labelled["site_identifier"], labelled["urban_rural"]))
            work["settlement_class"] = work["site_identifier"].map(mapping).fillna("")

        # Replace preliminary audit artifacts with the reviewed state.
        work[address_columns].to_csv(out / "provider_addresses_2024.csv", index=False)
        work[state_columns].to_csv(out / "federal_state_assignment_audit.csv", index=False)
        work[coord_columns].to_csv(out / "coordinate_inventory_2024.csv", index=False)
        conflict_mask = ~work["coordinate_validation_status"].isin(
            ["validated physical-site coordinate", "probable physical-site coordinate"]
        )
        work.loc[conflict_mask, coord_columns].to_csv(
            out / "coordinate_conflicts_2024.csv", index=False
        )
        reviewed_address_counts = work["address_validation_status"].value_counts()
        md(
            out / "address_source_audit.md", "Physical-site address source audit",
            "After review import, explicit or officially confirmed complete site-specific "
            f"addresses: {int(reviewed_address_counts.get('validated site-specific address', 0))}; "
            f"probable: {int(reviewed_address_counts.get('probable site-specific address', 0))}; "
            f"institution-only: {int(reviewed_address_counts.get('institution-level address only', 0))}; "
            f"missing: {int(reviewed_address_counts.get('no address found', 0))}. Original source "
            "text is retained unless a documented manual correction is supplied.",
        )
        reviewed_coordinate_counts = work["coordinate_validation_status"].value_counts()
        md(
            out / "coordinate_audit_report.md", "Coordinate audit",
            f"After review import: "
            f"{int(reviewed_coordinate_counts.get('validated physical-site coordinate', 0))} validated, "
            f"{int(reviewed_coordinate_counts.get('probable physical-site coordinate', 0))} probable, "
            f"{int(reviewed_coordinate_counts.get('institution-level coordinate only', 0))} institution-only, "
            f"{int(reviewed_coordinate_counts.get('unresolved coordinate', 0))} unresolved, "
            f"{int(reviewed_coordinate_counts.get('invalid coordinate', 0))} invalid, and "
            f"{int(reviewed_coordinate_counts.get('duplicate coordinate requiring review', 0))} "
            "duplicate coordinates requiring review.",
        )

    work["geographic_validation_status"] = work["coordinate_validation_status"].map({
        "validated physical-site coordinate": "validated",
        "probable physical-site coordinate": "probable, manual confirmation required",
        "invalid coordinate": "invalid",
    }).fillna("unresolved")
    work["validation_reason"] = work["coordinate_validation_reason"]
    work["manual_review_priority"] = work.apply(
        lambda r: manual_priority(r.visible_activity, r.suppressed_only), axis=1
    )
    work["manual_review_required"] = work["geographic_validation_status"].ne("validated")
    work["year"] = 2024
    work["site_id"] = work["site_identifier"]
    work["provider_name"] = work["hospital_name"]
    work["postcode"] = work["postal_code"]
    work["coordinate_source"] = work["geocode_source"]
    work["coordinate_status"] = work["coordinate_validation_status"]
    master_columns = [
        "year", "ik", "site_id", "provider_name", "visible_activity", "suppressed_only",
        "exclusive_volume_category", "threshold_ge20", "threshold_ge50", "threshold_ge100",
        "threshold_ge200", "original_address", "normalised_address", "street", "house_number",
        "postcode", "city", "address_source_file", "address_validation_status", "federal_state",
        "federal_state_source", "federal_state_status", "latitude", "longitude",
        "coordinate_source", "coordinate_status", "settlement_class",
        "geographic_validation_status", "validation_reason", "manual_review_priority",
        "manual_review_required", "manual_status", "manual_address", "manual_postcode",
        "manual_federal_state", "manual_latitude", "manual_longitude", "manual_source", "manual_notes",
    ]
    work[master_columns].to_csv(out / "provider_locations_master_2024.csv", index=False)
    editable_columns = master_columns + [
        "address_confirmation", "federal_state_confirmation", "coordinate_confirmation",
        "evidence_source", "review_notes",
    ]
    for col in editable_columns:
        if col not in work:
            work[col] = ""
    ge20_review = work[work.threshold_ge20 & work.manual_review_required].sort_values(
        ["manual_review_priority", "visible_activity"], ascending=[True, False]
    )
    ge20_review[editable_columns].to_csv(out / "geography_manual_review_ge20_2024.csv", index=False)
    md(
        out / "geography_manual_review_ge20_2024.md", "Priority manual review: ≥20 network",
        markdown_table(ge20_review[[
            "manual_review_priority", "site_id", "provider_name", "visible_activity",
            "original_address", "address_validation_status", "latitude", "longitude",
            "coordinate_status", "validation_reason",
        ]]),
    )
    below_review = work[~work.threshold_ge20 & work.manual_review_required].sort_values(
        ["manual_review_priority", "visible_activity"], ascending=[True, False]
    )
    below_review[editable_columns].to_csv(
        out / "geography_manual_review_below20_2024.csv", index=False
    )

    # Completeness by cumulative network.
    completion_rows = []
    masks = network_masks(work)
    for network, mask in masks.items():
        group = work[mask]
        completion_rows.append({
            "network": network, "expected_sites": EXPECTED_NETWORK_COUNTS[network],
            "observed_sites": len(group),
            "validated_site_specific_addresses": int((group.address_validation_status == "validated site-specific address").sum()),
            "probable_site_specific_addresses": int((group.address_validation_status == "probable site-specific address").sum()),
            "institution_level_addresses_only": int((group.address_validation_status == "institution-level address only").sum()),
            "conflicting_or_missing_addresses": int(group.address_validation_status.isin(["conflicting address evidence", "no address found"]).sum()),
            "validated_state_assignments": int(group.federal_state_status.str.startswith("validated").sum()),
            "unresolved_state_assignments": int((~group.federal_state_status.str.startswith("validated")).sum()),
            "state_validated_without_coordinates": int((group.federal_state_status.str.startswith("validated") & group.latitude.isna()).sum()),
            "ambiguous_postcodes": int(group.postcode_ambiguous.sum()),
            "validated_coordinates": int((group.coordinate_status == "validated physical-site coordinate").sum()),
            "probable_coordinates": int((group.coordinate_status == "probable physical-site coordinate").sum()),
            "institution_level_coordinates_only": int((group.coordinate_status == "institution-level coordinate only").sum()),
            "unresolved_coordinates": int(group.coordinate_status.isin(["unresolved coordinate", "coordinate/address mismatch", "duplicate coordinate requiring review"]).sum()),
            "invalid_coordinates": int((group.coordinate_status == "invalid coordinate").sum()),
            "unresolved_visible_activity": int(group.loc[group.manual_review_required, "visible_activity"].sum()),
            "manual_review_sites": int(group.manual_review_required.sum()),
            "accessibility_release_permitted": bool((group.coordinate_status == "validated physical-site coordinate").all()),
            "federal_state_release_permitted": bool(group.federal_state_status.str.startswith("validated").all()),
        })
    completeness = pd.DataFrame(completion_rows)
    completeness.to_csv(out / "geographic_validation_completeness.csv", index=False)

    state_summary = completeness[[
        "network", "observed_sites", "validated_state_assignments",
        "unresolved_state_assignments", "state_validated_without_coordinates",
        "ambiguous_postcodes", "federal_state_release_permitted",
    ]]
    released_state_networks = state_summary.loc[
        state_summary.federal_state_release_permitted, "network"
    ].tolist()
    md(
        out / "federal_state_assignment_report.md", "Federal-state assignment audit",
        "Reviewed official physical-site evidence is accepted only when explicitly supplied. "
        + (
            "Networks passing the federal-state release gate: "
            + ", ".join(released_state_networks)
            + ".\n\n"
            if released_state_networks
            else "No network currently passes the federal-state release gate.\n\n"
        )
        + markdown_table(state_summary),
    )
    released_accessibility = completeness.loc[
        completeness.accessibility_release_permitted, "network"
    ].tolist()
    if "ge100" in released_accessibility and "ge50" not in released_accessibility:
        decision_text = (
            "Outcome C: all 16 ≥100 sites are validated. ≥100 accessibility is permitted; "
            "≥50 and ≥20 accessibility remain withheld. A dedicated validated ≥100 figure "
            "may be generated, but unsupported ≥20/≥50 panels remain withheld."
        )
    elif "ge50" in released_accessibility and "ge20" not in released_accessibility:
        decision_text = (
            "Outcome B: ≥50 and ≥100 accessibility are permitted; ≥20 remains withheld."
        )
    elif "ge20" in released_accessibility:
        decision_text = "Outcome A: ≥20, ≥50, and ≥100 accessibility are permitted."
    else:
        decision_text = (
            "Outcome D: one or more ≥100 sites remain unresolved. Accessibility at ≥20, "
            "≥50, and ≥100 is withheld."
        )
    md(
        out / "geographic_validation_decision.md", "Geographic validation release decision",
        markdown_table(completeness)
        + "\n\n" + decision_text,
    )
    priority_counts = ge20_review.groupby("manual_review_priority").size().to_dict()
    priority_sections = []
    for priority, label in [
        (1, "Priority 1 (≥100)"),
        (2, "Priority 2 (50–99)"),
        (3, "Priority 3 (20–49)"),
    ]:
        rows = ge20_review[ge20_review.manual_review_priority == priority].sort_values(
            ["visible_activity", "site_id"], ascending=[False, True]
        )
        sites = "\n".join(
            f"- `{row.site_id}` — {row.provider_name} ({int(row.visible_activity)} visible cases)"
            for row in rows.itertuples(index=False)
        )
        priority_sections.append(f"## {label}\n\n{sites}")
    md(
        out / "MANUAL_REVIEW_INSTRUCTIONS.md", "Manual review instructions",
        f"The primary ≥20 workload is {len(ge20_review)} sites: Priority 1 (≥100) "
        f"{priority_counts.get(1, 0)}, Priority 2 (50–99) {priority_counts.get(2, 0)}, and Priority 3 "
        f"(20–49) {priority_counts.get(3, 0)}. Accessibility release status: "
        f"{', '.join(released_accessibility) if released_accessibility else 'none'}; federal-state "
        f"release status: {', '.join(released_state_networks) if released_state_networks else 'none'}."
        "\n\nFor each row in "
        "`geography_manual_review_ge20_2024.csv`, complete `address_confirmation`, "
        "`federal_state_confirmation`, `coordinate_confirmation`, `evidence_source`, and "
        "`review_notes`, plus the separate `manual_*` fields where a correction is needed. Acceptable "
        "evidence is a traceable official hospital/site page, original G-BA site field, or documented "
        "reviewed coordinate tied to that physical site. Do not use an IK headquarters, postcode "
        "centroid, or unsourced map pin.\n\n"
        + "\n\n".join(priority_sections)
        + "\n\n## Applying completed review\n\nAfter editing, rerun "
        "`python scripts/run_tips_geography_validation.py --manual-review "
        "outputs/geography_validation_2026-07-24/geography_manual_review_ge20_2024.csv`. "
        "Only rows with explicit confirmation fields and corresponding manual values are promoted; "
        "blank or incomplete review fields remain unresolved.",
    )

    # Local input inventory and blockers. No network or routing call is made.
    input_rows = [
        ["routing_engine", "OpenRouteService", "software version not pinned", "",
         "ors-docker/config", "", "licence metadata not recorded locally",
         "driving-car graph exists; routing withheld because coordinate completeness gate failed", "blocked"],
        ["road_data", "OpenStreetMap Germany extract / ORS graph", "graph version 4", "OSM timestamp 2026-03-29T20:20:46Z",
         "ors-docker/files/germany-latest.osm.pbf; ors-docker/graphs/driving-car/graph_build_info.yml",
         "graph-native", "licence metadata not recorded alongside local extract",
         "graph built 2026-04-01; exact OSM data timestamp is recorded in graph metadata", "available but unused"],
        ["population", "GHS-POP E2025 GLOBE R2023A 3 arcsec V1.0", "R2023A V1.0", "2025",
         "spatial/GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif", "EPSG:4326",
         "licence metadata not found alongside raster",
         "cached Germany total is 83,194,667; denominator not recomputed in this run because routing was withheld", "available but unused"],
        ["settlement", "GHS-SMOD E2025 GLOBE R2023A 1km V2.0", "R2023A V2.0", "2025",
         "spatial/GHS_SMOD_E2025_GLOBE_R2023A_54009_1000_V2_0.tif", "ESRI:54009",
         "licence metadata not found alongside raster",
         "codes 30/23/22/21 urban; 13/12/11 rural; other otherwise", "available and sampled"],
        ["federal_states", "Germany states GeoJSON", "unknown", "unknown",
         "spatial/germany-states.geojson", "EPSG:4326", "provider/version/licence metadata absent",
         "GADM-style attributes; used only to audit coordinate-derived state", "metadata blocked"],
        ["coordinates", "TIPS geocoding cache", "undated", "2024 cohort",
         "data/cache/geocode/tips_8-839-8_geocode_cache.csv", "EPSG:4326", "not recorded",
         "113 cached rows; no live geocoding used", "available"],
        ["postcode_state_reference", "none found", "", "", "", "", "",
         "required for independent postcode-derived state validation", "missing"],
    ]
    inventory = pd.DataFrame(input_rows, columns=[
        "input_type", "software_or_dataset", "release_or_version", "reference_year",
        "source_path", "crs", "licence_metadata", "configuration_or_notes", "validation_status",
    ])
    inventory.to_csv(out / "geographic_input_inventory.csv", index=False)
    md(
        out / "geographic_input_validation.md", "Local geographic input validation",
        markdown_table(inventory)
        + "\n\nSteps 8 inventory completed offline. Routing and population-denominator reproduction were "
        "not performed because no threshold coordinate network passed the completeness gate.",
    )

    # Explicit placeholders for conditional outputs. A dedicated ≥100 release does
    # not make the unsupported ≥20/≥50 multipanel products releasable.
    if "ge50" in released_accessibility:
        figure4_note = (
            "The full ≥20/≥50/≥100 Figure 4 remains withheld because the ≥20 "
            "network does not have complete validated physical-site coordinates. "
            "A separate ≥50/≥100 figure may be released using only the 31 validated "
            "≥50 sites and their unchanged 16-site ≥100 subset."
        )
        table_s5_note = (
            "The ≥50 and ≥100 networks passed complete physical-site coordinate "
            "validation. The ≥20 result remains withheld, so the full "
            "multithreshold Table S5 is not released; use the dedicated ≥50/≥100 "
            "accessibility table."
        )
    elif "ge100" in released_accessibility:
        figure4_note = (
            "The full multipanel Figure 4 remains withheld because the ≥20 and ≥50 "
            "networks do not have complete validated physical-site coordinates. A "
            "separate ≥100 figure may be released using only the 16 validated sites."
        )
        table_s5_note = (
            "The ≥100 network passed complete physical-site coordinate validation. "
            "Results for ≥20 and ≥50 remain withheld, so the full multithreshold "
            "Table S5 is not released; use the dedicated ≥100 accessibility output."
        )
    else:
        figure4_note = (
            "No threshold network has complete validated physical-site coordinates. "
            "Old coordinates were not reused."
        )
        table_s5_note = (
            "No accessibility threshold passed complete physical-site coordinate validation."
        )
    if "ge50" in released_state_networks:
        table_s4_note = (
            "The ≥50 and ≥100 networks have complete validated site-specific "
            "federal-state assignments. The ≥20 network remains incomplete, so "
            "the full multithreshold Table S4 is withheld; use the dedicated "
            "≥50/≥100 federal-state output."
        )
    elif "ge100" in released_state_networks:
        table_s4_note = (
            "The ≥100 network has complete validated site-specific federal-state "
            "assignments. The ≥20 and ≥50 networks remain incomplete, so the full "
            "multithreshold Table S4 is withheld."
        )
    else:
        table_s4_note = (
            "No provider network has complete independently validated site-specific "
            "federal-state assignments."
        )
    md(figures / "FIGURE4_WITHHELD.md", "Full Figure 4 withheld", figure4_note)
    md(tables / "TABLE_S4_WITHHELD.md", "Full Table S4 withheld", table_s4_note)
    md(tables / "TABLE_S5_WITHHELD.md", "Full Table S5 withheld", table_s5_note)
    if "ge50" in released_accessibility:
        manuscript_input = """This is a technical validation handoff only; the geography runner does not edit a manuscript.

| Result type | Status | Source / next step |
| --- | --- | --- |
| ≥100 validation | released, 16/16 sites | geographic_validation_decision.md |
| ≥50 validation | released, 31/31 sites | geographic_validation_decision.md |
| ≥50 and ≥100 accessibility | permitted after successful routing | generate dedicated validated accessibility outputs |
| ≥50 and ≥100 federal-state distribution | permitted | generate dedicated validated state table |
| ≥20 geographic outputs | withheld pending Priority-3 reviews | MANUAL_REVIEW_INSTRUCTIONS.md |
"""
    elif "ge100" in released_accessibility:
        manuscript_input = """This is a technical validation handoff only; the geography runner does not edit a manuscript.

| Result type | Status | Source / next step |
| --- | --- | --- |
| ≥100 validation | released, 16/16 sites | geographic_validation_decision.md |
| ≥100 accessibility | permitted after successful routing | generate dedicated validated ≥100 output |
| ≥50 and ≥20 geographic outputs | withheld pending review | MANUAL_REVIEW_INSTRUCTIONS.md |
"""
    else:
        manuscript_input = """No geographic numerical claim is currently validated for manuscript release.

| Result type | Status | Source / next step |
| --- | --- | --- |
| Address and coordinate methods | validated wording only | address_source_audit.md; coordinate_audit_report.md |
| Federal states | blocked | federal_state_assignment_report.md |
| Accessibility/urban-rural | blocked | geographic_validation_decision.md |
| Geographic outputs | blocked | MANUAL_REVIEW_INSTRUCTIONS.md |
"""
    md(
        out / "geographic_manuscript_input.md",
        "Focused geographic technical handoff",
        manuscript_input,
    )

    report_checks = {
        **checks,
        "no_institution_coordinate_upgraded": not (
            (work.address_validation_status == "institution-level address only")
            & (work.coordinate_status == "validated physical-site coordinate")
        ).any(),
        "no_duplicate_coordinate_accepted": not (
            work.coordinate_reused & (work.coordinate_status == "validated physical-site coordinate")
        ).any(),
        "figure4_not_generated": not any(figures.glob("Figure4*.png")),
        "table_s4_not_generated": not (tables / "TableS4.csv").exists(),
        "table_s5_not_generated": not (tables / "TableS5.csv").exists(),
        "manual_ge20_only": bool(ge20_review.threshold_ge20.all()),
    }
    check_df = pd.DataFrame(report_checks.items(), columns=["check", "passed"])
    md(
        out / "geographic_validation_report.md", "Geographic validation quality-control report",
        markdown_table(check_df)
        + f"\n\nPassed {int(check_df.passed.sum())}/{len(check_df)} checks. Routing completeness, "
        "population denominator, final state distribution, accessibility, Figure 4, and Tables S4/S5 "
        "were not tested/generated because their validation gates did not pass.",
    )
    print(f"Geographic validation package written to {out}")


if __name__ == "__main__":
    main()
