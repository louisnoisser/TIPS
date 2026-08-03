#!/usr/bin/env python3
"""Build the pending-review official BfArM OPS 8-839.8 mapping package."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gba_ops_reanalysis.official_ops_88398 import (  # noqa: E402
    ANALYSIS_VERSION,
    YEARS,
    build_codebook,
    build_coverage,
    build_cross_year_changes,
    discover_catalogues,
    extract_observed_records,
    generation_timestamp,
    git_commit,
    source_inventory,
    validate_approved_mapping,
)
from gba_ops_reanalysis.site_resolution_validation import resolve_component_precedence  # noqa: E402


DEFAULT_OUTPUT = ROOT / "outputs" / "official_ops_88398_validation_2026-07-28"


def md_escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    rule = "| " + " | ".join("---" for _ in columns) + " |"
    rows = [
        "| " + " | ".join(md_escape(row[column]) for column in columns) + " |"
        for _, row in frame[columns].fillna("").iterrows()
    ]
    return "\n".join([header, rule, *rows])


def add_metadata(frame: pd.DataFrame, timestamp: str, commit: str) -> pd.DataFrame:
    result = frame.copy()
    result["generation_timestamp"] = timestamp
    result["git_commit_hash"] = commit
    result["analysis_version"] = ANALYSIS_VERSION
    result["manual_review_package_status"] = "pending"
    return result


def activity_reconciliation(audit_csv: Path, control_csv: Path) -> pd.DataFrame:
    audit = pd.read_csv(audit_csv, dtype={"ik": str})
    audit = audit[
        pd.to_numeric(audit.reporting_year, errors="coerce").isin(YEARS)
        & audit.OPS_code.astype(str).str.strip().str.lower().str.startswith("8-839.8")
    ].copy()
    annotated, _ = resolve_component_precedence(audit)
    reproduced = (
        annotated[annotated.retained_site_resolution]
        .groupby("reporting_year", as_index=False)
        .visible_count.sum()
        .rename(columns={"visible_count": "reproduced_visible_activity"})
    )
    control = pd.read_csv(control_csv)
    if "provider_definition" in control:
        control = control[control.provider_definition.eq("physical_site")]
    control = control[
        pd.to_numeric(control.reporting_year, errors="coerce").isin(YEARS)
    ][["reporting_year", "visible_national_activity"]]
    result = control.merge(reproduced, on="reporting_year", how="outer", validate="one_to_one")
    result["difference"] = (
        result.reproduced_visible_activity - result.visible_national_activity
    )
    result["exact_match"] = result.difference.eq(0)
    if not result.exact_match.all():
        raise ValueError(
            "Annual visible activity did not reproduce the validated physical-site control"
        )
    value_2024 = int(
        result.loc[result.reporting_year.eq(2024), "reproduced_visible_activity"].iloc[0]
    )
    if value_2024 != 5247:
        raise ValueError(f"2024 visible activity is {value_2024}, expected 5,247")
    return result.sort_values("reporting_year").reset_index(drop=True)


def write_xlsx(
    path: Path, codebook: pd.DataFrame, sources: pd.DataFrame, changes: pd.DataFrame
) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        codebook.to_excel(writer, sheet_name="codebook", index=False)
        sources.to_excel(writer, sheet_name="catalogue_sources", index=False)
        changes.to_excel(writer, sheet_name="cross_year_changes", index=False)
        instructions = pd.DataFrame(
            {
                "instruction": [
                    "Review every year-code row against the cited official XML and PDF.",
                    "Enter both reviewer names, set manual_review_status to approved or rejected, and add comments where needed.",
                    "Set officially_verified to TRUE only after both reviewers approve that exact year-code definition.",
                    "No secondary-only analysis may be considered final while any observed year-code row is unapproved.",
                ]
            }
        )
        instructions.to_excel(writer, sheet_name="review_instructions", index=False)
        workbook = writer.book
        for sheet in workbook.worksheets:
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for column in sheet.columns:
                width = min(max(len(str(cell.value or "")) for cell in column) + 2, 60)
                sheet.column_dimensions[column[0].column_letter].width = width


def codebook_markdown(codebook: pd.DataFrame, timestamp: str, commit: str) -> str:
    columns = [
        "reporting_year", "ops_code_official", "official_full_label",
        "official_notes", "proposed_classification", "classification_reason",
        "source_file", "pdf_reference", "manual_review_status", "officially_verified",
    ]
    return f"""# Official OPS 8-839.8 codebook, 2013–2024

- Generation timestamp: `{timestamp}`
- Git commit: `{commit or "unavailable"}`
- Analysis version: `{ANALYSIS_VERSION}`
- Manual-review status: **pending**

All proposals below are based exclusively on the official year-specific catalogue
wording. They are not author-approved mappings. `officially_verified` remains
false for every row.

{markdown_table(codebook, columns)}
"""


def review_markdown(
    codebook: pd.DataFrame,
    changes: pd.DataFrame,
    coverage: pd.DataFrame,
    timestamp: str,
    commit: str,
) -> str:
    ambiguous = codebook[
        codebook.proposed_classification.isin(["unresolved_parent", "unresolved_other"])
    ]
    changed_codes = changes[
        changes.wording_changed | changes.proposed_classification_changed
    ]
    uncovered = coverage[coverage.codebook_match_count.ne(1)]
    sections = []
    for code, group in codebook.groupby("ops_code_normalised", sort=True):
        sections.append(f"### `{code}`\n")
        sections.append(
            markdown_table(
                group,
                [
                    "reporting_year", "official_full_label", "official_notes",
                    "proposed_classification", "classification_reason",
                    "source_file", "pdf_reference", "manual_reviewer_1",
                    "manual_reviewer_2", "manual_review_status",
                    "manual_review_comment", "officially_verified",
                ],
            )
        )
        sections.append(
            "\n\nReviewer 1: ____________________  Decision: __________\n\n"
            "Reviewer 2: ____________________  Decision: __________\n\n"
            "Comment: ______________________________________________________________\n"
        )
    uncovered_text = (
        markdown_table(
            uncovered,
            [
                "reporting_year", "observed_ops_code", "codebook_match_count",
                "number_of_records", "visible_activity", "number_of_suppressed_entries",
            ],
        )
        if len(uncovered)
        else "None."
    )
    return f"""# Manual review of the official OPS 8-839.8 mapping

- Generation timestamp: `{timestamp}`
- Git commit: `{commit or "unavailable"}`
- Analysis version: `{ANALYSIS_VERSION}`
- Overall approval: **PENDING**

## Mandatory interpretation boundary

This package establishes proposed meanings from official BfArM catalogue wording.
It does not establish an author-approved primary-versus-secondary mapping.
No secondary-only analysis may be considered final until every observed
year-code combination has an approved classification from two reviewers and
`officially_verified` is explicitly set to true.

Reporting years before 2013 are outside the classifiable range because codes
specifically denoting primary TIPS placement were not available across the
earlier period. The years 2008, 2010, and 2012 must never enter a secondary-only
computation. Absence of a primary-placement code before 2013 is not evidence of
secondary-only activity.

## Review summary

- Year-code definitions: {len(codebook)}
- Ambiguous or parent definitions: {len(ambiguous)}
- Codes with wording or proposed-classification changes: {len(changed_codes)}
- Observed year-code combinations without exactly one official match: {len(uncovered)}

## Ambiguous definitions

{markdown_table(ambiguous, ["reporting_year", "ops_code_official", "official_full_label", "proposed_classification", "pdf_reference"])}

## Cross-year changes requiring attention

{markdown_table(changed_codes, ["ops_code_normalised", "first_year_present", "last_year_present", "wording_changed", "proposed_classification_changed", "wording_by_years"])}

## Uncovered or multiply matched observed combinations

{uncovered_text}

## Approval fields

Overall reviewer 1: ____________________  Date: __________  Approved: YES / NO

Overall reviewer 2: ____________________  Date: __________  Approved: YES / NO

Overall comment: ____________________________________________________________

## Code-by-code review

{"".join(sections)}
"""


def validation_report(
    sources: pd.DataFrame,
    codebook: pd.DataFrame,
    changes: pd.DataFrame,
    coverage: pd.DataFrame,
    observed: pd.DataFrame,
    reconciliation: pd.DataFrame,
    timestamp: str,
    commit: str,
) -> str:
    unmatched = coverage[coverage.codebook_match_count.eq(0)]
    duplicates = coverage[coverage.codebook_match_count.gt(1)]
    pending = coverage[classification_status := "classification_status"].eq(
        "pending_manual_review"
    ).sum()
    annual = observed.groupby("reporting_year", as_index=False).agg(
        records=("ops_code_observed", "size"),
        pre_resolution_visible_activity=(
            "visible_numeric_value", lambda s: int(s.fillna(0).sum())
        ),
        suppressed_entries=("suppression_status", "sum"),
    ).merge(reconciliation, on="reporting_year", validate="one_to_one")
    source_lines = "\n".join(
        f"- {row.catalogue_year}: `{row.source_path}`, SHA-256 `{row.source_sha256}`, "
        f"PDF `{row.pdf_reference}`"
        for row in sources.itertuples(index=False)
    )
    gate = "FAIL — manual approval and catalogue coverage resolution required"
    return f"""# Preliminary official OPS 8-839.8 codebook validation report

- Generation timestamp: `{timestamp}`
- Git commit: `{commit or "unavailable"}`
- Analysis version: `{ANALYSIS_VERSION}`
- Manual-review status: **pending**
- Secondary-only analysis release gate: **{gate}**

## Scope and evidence boundary

The mapping proposals were derived exclusively from the official year-specific
ClaML wording. The repository's operational code mapping was not used as
evidence. It may only be compared after official manual approval.

Reporting years before 2013 are outside the classifiable range. In particular,
2008, 2010, and 2012 are excluded from every secondary-only computation and an
absence of a primary-placement code in those years must not be interpreted as
secondary-only activity.

## Catalogue sources

{source_lines}

All {len(sources)} required years were discovered deterministically and passed
the OPS ClaML identity checks.

## Extracted family

- Unique year-code definitions: {len(codebook)}
- Unique normalised codes: {codebook.ops_code_normalised.nunique()}
- Parent definitions: {(codebook.proposed_classification == "unresolved_parent").sum()}
- Residual or otherwise ambiguous definitions: {(codebook.proposed_classification == "unresolved_other").sum()}
- Codes with wording changes: {int(changes.wording_changed.sum())}
- Codes with proposed-classification changes: {int(changes.proposed_classification_changed.sum())}
- Automatically verified definitions: 0

## Observed-code coverage

- Observed 2013–2024 records: {len(observed)}
- Observed year-code combinations: {len(coverage)}
- Exactly one catalogue match: {(coverage.codebook_match_count == 1).sum()}
- Unmatched combinations: {len(unmatched)}
- Duplicate matches: {len(duplicates)}
- Exactly matched combinations still pending manual review: {int(pending)}

### Unmatched combinations

{markdown_table(unmatched, ["reporting_year", "observed_ops_code", "number_of_records", "visible_activity", "number_of_suppressed_entries"])}

## Preliminary activity reconciliation

{markdown_table(annual, ["reporting_year", "records", "pre_resolution_visible_activity", "reproduced_visible_activity", "visible_national_activity", "difference", "exact_match", "suppressed_entries"])}

Component-site precedence reproduces the validated annual physical-site totals
exactly, including 5,247 visible procedure occurrences in 2024. The unmatched
2013 code has five suppressed entries and zero visible activity, but it still
blocks codebook coverage and classification. No
primary-versus-secondary site classification, secondary-only analysis, or
manuscript conclusion was generated.

## Required next action

Two reviewers must approve every observed year-code definition. All unmatched
combinations must be resolved before the approved analysis can run. The reviewed
codebook must retain year-specific definitions and must not set
`officially_verified` to true without explicit author approval.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalogue-root", type=Path, default=ROOT / "ops_bfarm_2013_2024"
    )
    parser.add_argument(
        "--observed-audit",
        type=Path,
        default=ROOT / "outputs" / "audit" / "tips_code_level_audit.csv",
    )
    parser.add_argument(
        "--annual-control",
        type=Path,
        default=(
            ROOT / "outputs" / "final_submission_assets_2026-07-24" / "tables"
            / "TableS1_corrected_annual_site_metrics.csv"
        ),
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--reviewed-codebook",
        type=Path,
        help=(
            "Check a manually reviewed CSV or XLSX against observed coverage. "
            "This gate check does not execute the secondary-only analysis."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    timestamp = generation_timestamp()
    commit = git_commit(ROOT)

    sources_raw = discover_catalogues(args.catalogue_root)
    observed_raw = extract_observed_records(args.observed_audit)
    if args.reviewed_codebook:
        if args.reviewed_codebook.suffix.lower() == ".xlsx":
            reviewed = pd.read_excel(args.reviewed_codebook, sheet_name="codebook")
        else:
            reviewed = pd.read_csv(args.reviewed_codebook)
        coverage = build_coverage(observed_raw, reviewed)
        validate_approved_mapping(reviewed, coverage)
        print("APPROVAL GATE PASSED: every observed mapping is uniquely matched and approved by two reviewers.")
        print("No secondary-only analysis was run by this first-stage validation command.")
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)
    sources = add_metadata(source_inventory(sources_raw, args.catalogue_root), timestamp, commit)
    codebook = add_metadata(build_codebook(sources_raw, args.catalogue_root), timestamp, commit)
    changes = add_metadata(build_cross_year_changes(codebook), timestamp, commit)
    observed = add_metadata(observed_raw, timestamp, commit)
    coverage = add_metadata(build_coverage(observed, codebook), timestamp, commit)
    reconciliation = add_metadata(
        activity_reconciliation(args.observed_audit, args.annual_control),
        timestamp,
        commit,
    )

    sources.to_csv(args.output_dir / "ops_catalogue_sources_2013_2024.csv", index=False)
    codebook.to_csv(args.output_dir / "official_ops_88398_codebook_2013_2024.csv", index=False)
    changes.to_csv(args.output_dir / "ops_88398_cross_year_changes.csv", index=False)
    observed.to_csv(args.output_dir / "observed_ops_88398_records_2013_2024.csv", index=False)
    coverage.to_csv(args.output_dir / "ops_codebook_coverage_report.csv", index=False)
    reconciliation.to_csv(
        args.output_dir / "preliminary_ops_activity_reconciliation.csv", index=False
    )
    write_xlsx(
        args.output_dir / "official_ops_88398_codebook_2013_2024.xlsx",
        codebook,
        sources,
        changes,
    )
    (args.output_dir / "official_ops_88398_codebook_2013_2024.md").write_text(
        codebook_markdown(codebook, timestamp, commit), encoding="utf-8"
    )
    (args.output_dir / "ops_mapping_manual_review.md").write_text(
        review_markdown(codebook, changes, coverage, timestamp, commit), encoding="utf-8"
    )
    (args.output_dir / "ops_codebook_validation_report.md").write_text(
        validation_report(
            sources, codebook, changes, coverage, observed, reconciliation,
            timestamp, commit
        ),
        encoding="utf-8",
    )

    print(f"Output: {args.output_dir}")
    print(f"Catalogues: {len(sources)}")
    print(f"Year-code definitions: {len(codebook)}")
    print(f"Observed combinations: {len(coverage)}")
    print(f"Unmatched combinations: {(coverage.codebook_match_count == 0).sum()}")
    print("STOP: manual review is pending; no secondary-only analysis was run.")


if __name__ == "__main__":
    main()
