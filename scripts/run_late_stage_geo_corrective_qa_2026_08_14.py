#!/usr/bin/env python3
"""Narrow corrective QA for the completed 2026-08-14 geographic validation.

This script treats the completed validation directory as immutable input. It
adds one explicit shared-campus adjudication and evaluates the same generic
routing-readiness invariant for all 193 canonical reviewed records.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/late_stage_geo_validation_2026-08-14"
OUT = ROOT / "outputs/late_stage_geo_corrective_qa_2026-08-14"
QA = OUT / "qa"
EVIDENCE = OUT / "evidence"

VALIDATION = SOURCE / "geo_validation/additional_133_site_validation.csv"
ROUTING = SOURCE / "geo_validation/routing_readiness_all_193.csv"
FULL_MASTER = SOURCE / "geo_validation/proposed_full_identifiable_network_review_master.csv"
NUMERIC_MASTER = SOURCE / "geo_validation/proposed_openly_numeric_network_review_master.csv"
ADJUDICATIONS = SOURCE / "geo_validation/evidence/official_source_coordinate_adjudications.csv"
LOCKED_60 = ROOT / "outputs/final_submission_assets_2026-07-24/geography_manual_review_ge20_2024_completed.csv"
SOURCE_MANIFEST = SOURCE / "validation_manifest.json"
FIGURE_PNG = SOURCE / "figure3_finalisation/Figure3B_final_selected_legend_wording.png"
FIGURE_PDF = SOURCE / "figure3_finalisation/Figure3B_final_selected_legend_wording.pdf"

EXPECTED = {
    VALIDATION: "ff00191ec9ea4ff79bcd36b46eebdd6c3def834132b4c914cb5db0f4a0cfaa1a",
    ROUTING: "d3f9fda1257986f384b812dc4f9bcfe4c878cf9f6ea207c8525a5dca60599715",
    FULL_MASTER: "dd26689f63106b8551b325916806b1cede28e9a15a89d47d37593e6dc2b347d4",
    NUMERIC_MASTER: "1df3af1e8f4a8248160ace0472d0ffe3ccdbd211d7d2d11e76994d7eae68c79f",
    ADJUDICATIONS: "cbc4bd1d5c00e9ce94c5eb380f59f400713c4bffe7efd3d7b3d22b5611d5a418",
    LOCKED_60: "803e125939df1ceb6a6f72f9e6577e2726e4e20e83328ba3ae0f46edf3739061",
    SOURCE_MANIFEST: "3bfd848380c0023377c48006f32fcf8c9931a18d0d276a72686e82e5998ccd50",
    FIGURE_PNG: "91dc44063f1302e2101b78e0b72c1bd53b4857537548fd06a81380bbbd7d9aff",
    FIGURE_PDF: "bd3fdde5702047cae35640eeed3baa4f0e20d851d72cb617b2c7887be476a938",
}

WESTERSTEDE_ID = "260341444-772466000"
WESTERSTEDE_NAME = "Ammerland-Klinik Westerstede"
WESTERSTEDE_SOURCES = (
    "https://ammerland-klinik.de/klinikzentrum-westerstede; "
    "https://www.ammerland-klinik.de/_downloads/AMKL-Lageplan-Neubau-Querformat_2025-08-05-131147_oyxb.pdf; "
    "https://www.bundeswehr.de/service/locationSearch/bw-de/5995288/term-search"
)
WESTERSTEDE_RATIONALE = (
    "Official Ammerland-Klinik evidence states that Ammerland-Klinik GmbH and "
    "Bundeswehrkrankenhaus Westerstede jointly form Klinikzentrum Westerstede at "
    "Lange Straße 38 and provide care at one location. The official campus plan "
    "shows the Ammerland buildings and Bundeswehrkrankenhaus on the connected "
    "Klinikzentrum campus between the Lange Straße entrance and Mozartstraße. "
    "The reverse result naming Bundeswehrkrankenhaus/Mozartstraße therefore "
    "identifies the shared clinical campus rather than a wrong hospital location; "
    "reverse_exact_street_address=False does not invalidate the campus coordinate."
)

VIVANTES_IDS = [
    "261101878-773179000", "261101878-773183000", "261101878-773184000",
    "261101878-773186000", "261101878-773181000",
]
KETTELER_ID = "260610360-771398000"
ROMED_ID = "260910637-772849000"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bool_value(value: object) -> bool | None:
    if pd.isna(value) or str(value).strip() == "":
        return None
    return str(value).strip().lower() == "true"


def exact_existing_columns(before: pd.DataFrame, after: pd.DataFrame) -> bool:
    return before.equals(after[before.columns])


def write_csv(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def markdown_table(frame: pd.DataFrame) -> str:
    shown = frame.fillna("").astype(str).apply(lambda c: c.str.replace("|", r"\|", regex=False))
    return "\n".join([
        "| " + " | ".join(shown.columns) + " |",
        "| " + " | ".join("---" for _ in shown.columns) + " |",
        *["| " + " | ".join(row) + " |" for row in shown.itertuples(index=False, name=None)],
    ])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    source_checks = []
    for path, expected in EXPECTED.items():
        actual = sha256(path)
        source_checks.append((f"source_hash_{path.name}", actual == expected, actual, expected))
        if actual != expected:
            raise RuntimeError(f"Immutable source hash mismatch: {path}: {actual}")

    validation = pd.read_csv(VALIDATION, dtype={"site_id": str, "ik": str})
    routing_before = pd.read_csv(ROUTING, dtype={"site_id": str, "ik": str})
    full_before = pd.read_csv(FULL_MASTER, dtype={"site_id": str, "ik": str})
    numeric_before = pd.read_csv(NUMERIC_MASTER, dtype={"site_id": str, "ik": str})
    locked = pd.read_csv(LOCKED_60, dtype={"site_id": str, "ik": str})
    adjudications = pd.read_csv(ADJUDICATIONS, dtype={"site_id": str})

    w = validation.loc[validation.site_id.eq(WESTERSTEDE_ID)].copy()
    if len(w) != 1:
        raise RuntimeError(f"Westerstede site_id matches {len(w)} records, expected exactly one")
    wr = w.iloc[0]
    expected_state = {
        "official_verified_site_name": WESTERSTEDE_NAME,
        "official_verified_clinical_address": "Lange Straße 38, 26655 Westerstede",
        "proposed_coordinate_source": "nominatim_full_address",
        "coordinate_precision_code": "A",
        "coordinate_precision_class": "verified_campus_or_building",
        "routing_ready": "yes",
    }
    for column, expected in expected_state.items():
        if str(wr[column]) != expected:
            raise RuntimeError(f"Unexpected Westerstede {column}: {wr[column]!r}")
    if bool_value(wr.reverse_exact_street_address) is not False:
        raise RuntimeError("Westerstede reverse_exact_street_address is not False")
    if not np.isclose(float(wr.proposed_latitude), 53.2579622, atol=1e-7) or not np.isclose(float(wr.proposed_longitude), 7.9184201, atol=1e-7):
        raise RuntimeError("Unexpected Westerstede coordinate")
    if adjudications.site_id.eq(WESTERSTEDE_ID).any():
        raise RuntimeError("Westerstede already has an explicit adjudication in the immutable source")

    adjudications_updated = adjudications.copy()
    for column, default in [
        ("authoritative_adjudication_present", "yes"), ("secondary_official_source_url", ""),
        ("adjudication_date", "2026-08-14"), ("coordinate_retained", "yes"),
        ("precision_retained", "yes"), ("routing_ready_retained", "yes"),
    ]:
        adjudications_updated[column] = default
    new_adj = {column: "" for column in adjudications_updated.columns}
    new_adj.update({
        "site_id": WESTERSTEDE_ID,
        "coordinate_precision_code": "A",
        "official_source_url": "https://ammerland-klinik.de/klinikzentrum-westerstede",
        "reason": WESTERSTEDE_RATIONALE,
        "corrected_address": "",
        "corrected_latitude": "",
        "corrected_longitude": "",
        "coordinate_source": "existing nominatim_full_address coordinate retained after official shared-campus adjudication",
        "authoritative_adjudication_present": "yes",
        "secondary_official_source_url": (
            "https://www.ammerland-klinik.de/_downloads/AMKL-Lageplan-Neubau-Querformat_2025-08-05-131147_oyxb.pdf; "
            "https://www.bundeswehr.de/service/locationSearch/bw-de/5995288/term-search"
        ),
        "adjudication_date": "2026-08-14",
        "coordinate_retained": "yes", "precision_retained": "yes", "routing_ready_retained": "yes",
    })
    adjudications_updated = pd.concat([adjudications_updated, pd.DataFrame([new_adj])], ignore_index=True)
    if adjudications_updated.site_id.duplicated().any() or len(adjudications_updated) != 11:
        raise RuntimeError("Updated adjudication table is not 11 unique records")

    adj_lookup = adjudications_updated.set_index("site_id")
    val_lookup = validation.set_index("site_id")
    locked_lookup = locked.set_index("site_id")
    full_lookup = full_before.set_index("site_id")
    invariant_rows = []
    for row in routing_before.itertuples(index=False):
        site_id = row.site_id
        reverse_exact = None
        authoritative = False
        source = ""
        rationale = ""
        site_name = str(full_lookup.at[site_id, "provider_name"])
        clinical_address = ""
        if site_id in val_lookup.index:
            source_row = val_lookup.loc[site_id]
            reverse_exact = bool_value(source_row.reverse_exact_street_address)
            clinical_address = str(source_row.official_verified_clinical_address)
        if site_id in adj_lookup.index:
            a = adj_lookup.loc[site_id]
            authoritative = str(a.authoritative_adjudication_present).lower() == "yes"
            source = "; ".join(x for x in [str(a.official_source_url), str(a.secondary_official_source_url)] if x and x != "nan")
            rationale = str(a.reason)
        elif site_id in locked_lookup.index:
            l = locked_lookup.loc[site_id]
            authoritative = (
                str(l.manual_status) == "validated"
                and str(l.address_confirmation) == "validated"
                and str(l.coordinate_confirmation) == "validated"
            )
            source = str(l.evidence_source)
            rationale = str(l.review_notes)
            clinical_address = str(l.manual_address) if pd.notna(l.manual_address) else str(l.original_address)
        antecedent = row.coordinate_precision_code in {"A", "B"} and str(row.routing_ready).lower() == "yes"
        passed = (not antecedent) or reverse_exact is True or authoritative
        if reverse_exact is True and authoritative:
            route = "reverse_exact_and_authoritative_adjudication"
        elif reverse_exact is True:
            route = "reverse_exact_street_address"
        elif authoritative:
            route = "authoritative_adjudication"
        else:
            route = "none"
        auto_coordinate = any(token in str(row.proposed_coordinate_source).lower() for token in ["nominatim", "automatic", "geocode"])
        guardrail_pass = not (auto_coordinate and reverse_exact is False and not authoritative and row.coordinate_precision_code in {"A", "B"} and str(row.routing_ready).lower() == "yes")
        invariant_rows.append({
            "site_id": site_id, "site_name": site_name, "validation_group": row.validation_group,
            "verified_clinical_address": clinical_address,
            "proposed_latitude": row.proposed_latitude, "proposed_longitude": row.proposed_longitude,
            "proposed_coordinate_source": row.proposed_coordinate_source,
            "coordinate_precision_code": row.coordinate_precision_code,
            "coordinate_precision_class": row.coordinate_precision_class, "routing_ready": row.routing_ready,
            "reverse_exact_street_address": reverse_exact,
            "authoritative_adjudication_present": "yes" if authoritative else "no",
            "adjudication_source": source, "adjudication_rationale": rationale,
            "invariant_satisfaction_route": route,
            "generic_invariant_result": "PASS" if passed else "FAIL",
            "automatic_coordinate_guardrail_result": "PASS" if guardrail_pass else "FAIL",
        })
    invariant = pd.DataFrame(invariant_rows).sort_values("site_id").reset_index(drop=True)

    reverse_false = invariant.loc[invariant.reverse_exact_street_address.eq(False)].copy()
    reverse_false["pass_fail"] = np.where(
        reverse_false.generic_invariant_result.eq("PASS") & reverse_false.automatic_coordinate_guardrail_result.eq("PASS"),
        "PASS", "FAIL",
    )

    routing_after = routing_before.copy()
    additions = invariant.set_index("site_id")[[
        "reverse_exact_street_address", "authoritative_adjudication_present", "adjudication_source",
        "adjudication_rationale", "invariant_satisfaction_route", "generic_invariant_result",
        "automatic_coordinate_guardrail_result",
    ]]
    routing_after = routing_after.join(additions, on="site_id")

    full_after = full_before.copy()
    address_map = invariant.set_index("site_id").verified_clinical_address
    full_after["proposed_verified_clinical_address"] = full_after.site_id.map(address_map)
    full_after = full_after.join(additions, on="site_id")

    corrected_w = w.copy()
    corrected_w["authoritative_adjudication_present"] = "yes"
    corrected_w["authoritative_adjudication_source"] = WESTERSTEDE_SOURCES
    corrected_w["authoritative_adjudication_rationale"] = WESTERSTEDE_RATIONALE
    corrected_w["generic_invariant_result"] = "PASS"
    corrected_w["coordinate_changed_in_corrective_qa"] = "no"
    corrected_w["precision_changed_in_corrective_qa"] = "no"
    corrected_w["routing_ready_changed_in_corrective_qa"] = "no"

    preservation_rows = []
    for site_id in VIVANTES_IDS + [KETTELER_ID, ROMED_ID]:
        before = routing_before.loc[routing_before.site_id.eq(site_id)].iloc[0]
        after = routing_after.loc[routing_after.site_id.eq(site_id)].iloc[0]
        label = "Vivantes correction" if site_id in VIVANTES_IDS else "Ketteler correction" if site_id == KETTELER_ID else "RoMed correction"
        address_before = ""
        address_after = ""
        address_pass = True
        if site_id == KETTELER_ID:
            source_row = val_lookup.loc[site_id]
            address_before = str(source_row.official_verified_clinical_address)
            address_after = str(full_after.loc[full_after.site_id.eq(site_id), "proposed_verified_clinical_address"].iloc[0])
            address_pass = address_before == address_after == "Lichtenplattenweg 85, 63071 Offenbach" and "85 85" not in address_after
        preservation_rows.append({
            "check_group": label, "site_id": site_id,
            "coordinate_before": f"{before.proposed_latitude:.7f}, {before.proposed_longitude:.7f}",
            "coordinate_after": f"{after.proposed_latitude:.7f}, {after.proposed_longitude:.7f}",
            "coordinate_unchanged": "yes" if np.isclose(before.proposed_latitude, after.proposed_latitude, atol=0, rtol=0) and np.isclose(before.proposed_longitude, after.proposed_longitude, atol=0, rtol=0) else "no",
            "address_before": address_before, "address_after": address_after,
            "address_preserved": "yes" if address_pass else "no", "result": "PASS" if address_pass and before.proposed_latitude == after.proposed_latitude and before.proposed_longitude == after.proposed_longitude else "FAIL",
        })
    for site_id in sorted(locked.site_id):
        before = routing_before.loc[routing_before.site_id.eq(site_id)].iloc[0]
        after = routing_after.loc[routing_after.site_id.eq(site_id)].iloc[0]
        same = before.proposed_latitude == after.proposed_latitude and before.proposed_longitude == after.proposed_longitude
        preservation_rows.append({
            "check_group": "locked_ge20_coordinate", "site_id": site_id,
            "coordinate_before": f"{before.proposed_latitude:.7f}, {before.proposed_longitude:.7f}",
            "coordinate_after": f"{after.proposed_latitude:.7f}, {after.proposed_longitude:.7f}",
            "coordinate_unchanged": "yes" if same else "no", "address_before": "", "address_after": "",
            "address_preserved": "not_applicable", "result": "PASS" if same else "FAIL",
        })
    preservation = pd.DataFrame(preservation_rows)

    ab_ready = invariant.loc[
        invariant.coordinate_precision_code.isin(["A", "B"]) & invariant.routing_ready.eq("yes")
    ]
    numeric_invariant = invariant.loc[invariant.site_id.isin(set(numeric_before.site_id))]

    qa_checks = [
        *[(name, passed, actual, expected) for name, passed, actual, expected in source_checks],
        ("westerstede_unique", len(w) == 1, len(w), 1),
        ("westerstede_exact_identity", wr.official_verified_site_name == WESTERSTEDE_NAME, wr.official_verified_site_name, WESTERSTEDE_NAME),
        ("westerstede_coordinate_retained", corrected_w.coordinate_changed_in_corrective_qa.eq("no").all(), corrected_w.coordinate_changed_in_corrective_qa.iloc[0], "no"),
        ("westerstede_precision_retained", corrected_w.precision_changed_in_corrective_qa.eq("no").all(), corrected_w.precision_changed_in_corrective_qa.iloc[0], "no"),
        ("westerstede_routing_ready_retained", corrected_w.routing_ready_changed_in_corrective_qa.eq("no").all(), corrected_w.routing_ready_changed_in_corrective_qa.iloc[0], "no"),
        ("updated_adjudications_11", len(adjudications_updated) == 11, len(adjudications_updated), 11),
        ("canonical_records_193", len(invariant) == 193 and invariant.site_id.nunique() == 193, len(invariant), 193),
        ("all_AB_routing_ready_checked", len(ab_ready) == 193, len(ab_ready), 193),
        ("generic_invariant_failures_zero", invariant.generic_invariant_result.eq("FAIL").sum() == 0, int(invariant.generic_invariant_result.eq("FAIL").sum()), 0),
        ("automatic_guardrail_failures_zero", invariant.automatic_coordinate_guardrail_result.eq("FAIL").sum() == 0, int(invariant.automatic_coordinate_guardrail_result.eq("FAIL").sum()), 0),
        ("open_numeric_113_routing_ready", len(numeric_invariant) == 113 and numeric_invariant.routing_ready.eq("yes").all(), int(numeric_invariant.routing_ready.eq("yes").sum()), 113),
        ("open_numeric_113_invariant_pass", numeric_invariant.generic_invariant_result.eq("PASS").all(), int(numeric_invariant.generic_invariant_result.eq("PASS").sum()), 113),
        ("full_193_routing_ready", invariant.routing_ready.eq("yes").all(), int(invariant.routing_ready.eq("yes").sum()), 193),
        ("reverse_false_10", len(reverse_false) == 10, len(reverse_false), 10),
        ("reverse_false_adjudicated_10", reverse_false.authoritative_adjudication_present.eq("yes").sum() == 10, int(reverse_false.authoritative_adjudication_present.eq("yes").sum()), 10),
        ("reverse_false_unexplained_zero", reverse_false.pass_fail.eq("FAIL").sum() == 0, int(reverse_false.pass_fail.eq("FAIL").sum()), 0),
        ("routing_existing_fields_byte_values_unchanged", exact_existing_columns(routing_before, routing_after), exact_existing_columns(routing_before, routing_after), True),
        ("full_master_existing_fields_byte_values_unchanged", exact_existing_columns(full_before, full_after), exact_existing_columns(full_before, full_after), True),
        ("open_numeric_master_source_unchanged", sha256(NUMERIC_MASTER) == EXPECTED[NUMERIC_MASTER], sha256(NUMERIC_MASTER), EXPECTED[NUMERIC_MASTER]),
        ("preservation_all_pass", preservation.result.eq("PASS").all(), int(preservation.result.eq("FAIL").sum()), 0),
        ("vivantes_five_preserved", preservation.loc[preservation.check_group.eq("Vivantes correction"), "result"].eq("PASS").sum() == 5, int(preservation.loc[preservation.check_group.eq("Vivantes correction"), "result"].eq("PASS").sum()), 5),
        ("ketteler_address_85_preserved", preservation.loc[preservation.check_group.eq("Ketteler correction"), "address_preserved"].eq("yes").all(), preservation.loc[preservation.check_group.eq("Ketteler correction"), "address_after"].iloc[0], "Lichtenplattenweg 85, 63071 Offenbach"),
        ("romed_coordinate_preserved", preservation.loc[preservation.check_group.eq("RoMed correction"), "result"].eq("PASS").all(), preservation.loc[preservation.check_group.eq("RoMed correction"), "result"].iloc[0], "PASS"),
        ("locked_60_preserved", preservation.loc[preservation.check_group.eq("locked_ge20_coordinate"), "result"].eq("PASS").sum() == 60, int(preservation.loc[preservation.check_group.eq("locked_ge20_coordinate"), "result"].eq("PASS").sum()), 60),
        ("figure_png_unchanged", sha256(FIGURE_PNG) == EXPECTED[FIGURE_PNG], sha256(FIGURE_PNG), EXPECTED[FIGURE_PNG]),
        ("figure_pdf_unchanged", sha256(FIGURE_PDF) == EXPECTED[FIGURE_PDF], sha256(FIGURE_PDF), EXPECTED[FIGURE_PDF]),
    ]
    qa_frame = pd.DataFrame(qa_checks, columns=["check", "passed", "actual", "expected"])
    if not qa_frame.passed.all():
        raise RuntimeError(f"Corrective QA failed: {qa_frame.loc[~qa_frame.passed, 'check'].tolist()}")

    outputs = [
        write_csv(corrected_w, OUT / "westerstede_corrected_adjudicated_record.csv"),
        write_csv(adjudications_updated, EVIDENCE / "authoritative_coordinate_adjudications_updated.csv"),
        write_csv(invariant, QA / "routing_readiness_invariant_all_193.csv"),
        write_csv(reverse_false, QA / "reverse_false_records_qa.csv"),
        write_csv(routing_after, OUT / "routing_readiness_all_193_corrective_qa.csv"),
        write_csv(full_after, OUT / "proposed_full_identifiable_network_review_master_corrective_qa.csv"),
        write_csv(preservation, QA / "preservation_crosscheck.csv"),
        write_csv(qa_frame, QA / "programmatic_qa.csv"),
    ]

    def item(path: Path) -> str:
        return f"`{path.relative_to(ROOT)}` — SHA-256 `{sha256(path)}`"

    report = f"""# Corrective geographic QA report — 2026-08-14

## A. Record resolution

- Queried site_id: `{WESTERSTEDE_ID}`
- Matches: 1
- Resolved site: `{WESTERSTEDE_NAME}`
- Result: **PASS**

All expected pre-change values matched exactly: Lange Straße 38, coordinate {float(wr.proposed_latitude):.7f}, {float(wr.proposed_longitude):.7f}, `nominatim_full_address`, reverse exact-address false, precision A and routing-ready yes. No prior explicit adjudication existed.

## B. Westerstede adjudication

- Coordinate before/after: `{float(wr.proposed_latitude):.7f}, {float(wr.proposed_longitude):.7f}` / unchanged
- Precision before/after: A / A
- Routing-ready before/after: yes / yes
- Authoritative sources: {WESTERSTEDE_SOURCES}
- Rationale: {WESTERSTEDE_RATIONALE}

## C. Generic invariant

Canonical records checked=193; A/B routing-ready records checked=193; satisfying=193; failing=0. The generic assertion was applied without a Westerstede special case: `A/B AND routing_ready=yes -> reverse_exact_street_address=True OR authoritative_adjudication_present=True`.

## D. Reverse=False audit

Reverse=False records=10; authoritative adjudications among them=10; unexplained A/B routing-ready records=0.

## E. Preservation checks

Five Vivantes coordinates unchanged: PASS. Ketteler coordinate unchanged: PASS. Ketteler verified address remains `Lichtenplattenweg 85, 63071 Offenbach`: PASS. RoMed coordinate unchanged: PASS. All 60 locked ≥20 coordinates unchanged: PASS. Every pre-existing field in the 193 routing table and proposed full-network master is value-identical; only new evidence/QA columns were appended.

The openly numeric master was not regenerated because Westerstede is suppressed-only and no openly numeric evidence/status field changed. Its source SHA-256 remains `{sha256(NUMERIC_MASTER)}`.

## F. Updated outputs

""" + "\n".join(f"- {item(path)}" for path in outputs) + """

## G. Readiness conclusion

Openly numeric network routing-ready: 113/113. Full identifiable network routing-ready: 193/193. Unexplained coordinate-evidence guardrail failures: 0. Technical routing readiness does not itself authorise accessibility analysis.

## H. Integrity statement

No routing, isochrone generation, population coverage, Figure 4 or accessibility analysis was performed. Figure 3 and all Word files were untouched. No canonical production or completed-validation output was overwritten. No Git history, branch or remote was modified. No unrelated validated geographic value changed.
"""
    report_path = OUT / "corrective_qa_report.md"
    report_path.write_text(report, encoding="utf-8")
    outputs.append(report_path)
    outputs.append(ROOT / "scripts/run_late_stage_geo_corrective_qa_2026_08_14.py")

    manifest_payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "immutable_source_manifest": {"path": str(SOURCE_MANIFEST.relative_to(ROOT)), "sha256": sha256(SOURCE_MANIFEST)},
        "outputs": [
            {"path": str(path.relative_to(ROOT)), "size_bytes": path.stat().st_size,
             "timestamp_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(), "sha256": sha256(path)}
            for path in sorted(outputs)
        ],
    }
    manifest_path = OUT / "corrective_qa_manifest.json"
    manifest_path.write_text(json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8")
    print(f"Built corrective QA at {OUT}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
