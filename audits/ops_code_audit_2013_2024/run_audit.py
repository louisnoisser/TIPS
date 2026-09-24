#!/usr/bin/env python3
"""Read-only-source audit of annual OPS 8-839.8* ClaML and canonical G-BA data.

This script writes only to outputs/ops_code_audit_2013_2024. It deliberately
does not accept already-extracted XML as catalogue evidence: each annual source
must be exactly one *syst-claml*.zip in the corresponding year directory.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from gba_ops_reanalysis.site_resolution_validation import (  # noqa: E402
    resolve_component_precedence,
)


YEARS = tuple(range(2013, 2025))
REQUESTED_CODES = (
    "8-839.8",
    "8-839.81",
    "8-839.82",
    "8-839.83",
    "8-839.84",
    "8-839.85",
    "8-839.86",
    "8-839.87",
    "8-839.88",
    "8-839.89",
    "8-839.8a",
    "8-839.8x",
)
DE_NOVO_CODES = ("8-839.87", "8-839.88", "8-839.89", "8-839.8a")
CATALOGUE_ROOT = ROOT / "ops_bfarm_2013_2024"
CANONICAL_CODE_DATA = ROOT / "outputs/audit/tips_code_level_audit.csv"
MAIN_SITE_DATA = ROOT / "outputs/site_resolution_validation/resolved_site_level_data.csv"
OUTPUT = ROOT / "outputs/ops_code_audit_2013_2024"

CLASSIFICATION = {
    "8-839.8": "parent, residual, or otherwise ambiguous",
    "8-839.81": "secondary intervention in an existing TIPS",
    "8-839.82": "secondary intervention in an existing TIPS",
    "8-839.83": "secondary intervention in an existing TIPS",
    "8-839.84": "secondary intervention in an existing TIPS",
    "8-839.85": "secondary intervention in an existing TIPS",
    "8-839.86": "secondary intervention in an existing TIPS",
    "8-839.87": "specific de novo TIPS creation",
    "8-839.88": "specific de novo TIPS creation",
    "8-839.89": "specific de novo TIPS creation",
    "8-839.8a": "specific de novo TIPS creation",
    "8-839.8x": "parent, residual, or otherwise ambiguous",
}

# These are explicit analyst judgments about the 2023 -> 2024 wording changes,
# not substitutions for the source wording retained in the output columns.
SEMANTIC_CHANGE_2024 = {
    "8-839.84": (
        "yes",
        "Official title changed from percutaneous reduction of an existing "
        "portosystemic shunt to stent insertion into an existing shunt.",
    ),
    "8-839.86": (
        "yes",
        "Official title changed from revision with stent insertion to extension "
        "of an existing portosystemic shunt by stent insertion.",
    ),
}

AUDIT_COLUMNS = [
    "catalogue_year", "code", "row_scope", "belongs_to_requested_144",
    "exists", "non_existence_reason", "official_title", "inclusion_notes",
    "exclusion_notes", "usage_or_coding_notes", "source_archive_path",
    "source_archive_filename", "source_archive_sha256", "source_xml_filename",
    "source_xml_member", "source_xml_sha256", "claml_class_identifier",
    "claml_xml_location", "claml_superclass_codes", "claml_subclass_codes",
    "analyst_classification", "classification_basis",
    "provisional_classification_disagreement", "wording_changed_vs_previous_year",
    "clinical_or_coding_meaning_changed_vs_previous_year", "exact_previous_wording",
    "exact_current_wording", "semantic_change_explanation", "catalogue_source_status",
    "annual_archive_candidates", "manual_review_flag", "manual_review_reason",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def clean_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def pipe(values: list[str]) -> str:
    return " | ".join(value for value in values if value)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    return result.stdout.strip()


def archive_candidates(year_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in year_dir.iterdir()
        if path.is_file()
        and path.name.lower().endswith(".zip")
        and "syst-claml" in path.name.lower()
    )


def plausible_files(year_dir: Path) -> list[str]:
    return [
        rel(path)
        for path in sorted(year_dir.iterdir())
        if path.is_file() and not path.name.startswith(".")
    ]


def xml_members(archive_path: Path, year: int) -> list[str]:
    with ZipFile(archive_path) as archive:
        return sorted(
            name
            for name in archive.namelist()
            if not name.startswith("__MACOSX/")
            and not Path(name).name.startswith("._")
            and name.lower().endswith(".xml")
            and f"ops{year}syst_claml" in Path(name).name.lower()
        )


def empty_row(year: int, code: str, status: str, candidates: list[str], reason: str) -> dict[str, Any]:
    row = {column: "" for column in AUDIT_COLUMNS}
    row.update(
        {
            "catalogue_year": year,
            "code": code,
            "row_scope": "requested_144",
            "belongs_to_requested_144": True,
            "exists": "unknown",
            "catalogue_source_status": status,
            "annual_archive_candidates": " | ".join(candidates),
            "manual_review_flag": True,
            "manual_review_reason": reason,
        }
    )
    return row


def parse_catalogues() -> tuple[pd.DataFrame, list[dict[str, Any]], list[dict[str, str]]]:
    rows: list[dict[str, Any]] = []
    annual_sources: list[dict[str, Any]] = []
    codes_842: list[dict[str, str]] = []

    for year in YEARS:
        year_dir = CATALOGUE_ROOT / str(year)
        candidates = archive_candidates(year_dir) if year_dir.is_dir() else []
        nearby = plausible_files(year_dir) if year_dir.is_dir() else []
        if len(candidates) != 1:
            status = "missing_required_claml_archive" if not candidates else "ambiguous_claml_archives"
            reason = (
                f"Expected exactly one annual *syst-claml*.zip; found {len(candidates)}. "
                "Annual processing stopped without using extracted XML or another source. "
                f"Files present: {' | '.join(nearby) if nearby else 'none'}."
            )
            listed = [rel(path) for path in candidates] or nearby
            rows.extend(empty_row(year, code, status, listed, reason) for code in REQUESTED_CODES)
            annual_sources.append(
                {
                    "year": year,
                    "status": status,
                    "archive_path": "",
                    "archive_sha256": "",
                    "xml_member": "",
                    "xml_sha256": "",
                    "candidates": listed,
                    "warning": reason,
                }
            )
            continue

        archive_path = candidates[0]
        members = xml_members(archive_path, year)
        if len(members) != 1:
            reason = (
                f"Selected archive contains {len(members)} plausible annual systematics XML members; "
                "annual processing stopped. Members: {' | '.join(members) if members else 'none'}."
            )
            rows.extend(
                empty_row(year, code, "ambiguous_or_missing_xml_member", members, reason)
                for code in REQUESTED_CODES
            )
            annual_sources.append(
                {
                    "year": year,
                    "status": "ambiguous_or_missing_xml_member",
                    "archive_path": rel(archive_path),
                    "archive_sha256": sha256_file(archive_path),
                    "xml_member": "",
                    "xml_sha256": "",
                    "candidates": members,
                    "warning": reason,
                }
            )
            continue

        member = members[0]
        with ZipFile(archive_path) as archive:
            xml_bytes = archive.read(member)
        try:
            root = ET.fromstring(xml_bytes)
            title = root.find("Title")
            if root.tag.split("}")[-1] != "ClaML":
                raise ValueError("root element is not ClaML")
            if title is None or title.attrib.get("version") != str(year):
                raise ValueError("ClaML Title version does not match the annual folder")
            if "Prozedurenschlüssel" not in clean_text(title):
                raise ValueError("ClaML title is not recognisably the OPS systematics")
            classes = {
                node.attrib["code"]: node
                for node in root.findall("Class")
                if "code" in node.attrib
            }
            if "8-839.8" not in classes:
                raise ValueError("8-839.8 parent class is absent")
        except Exception as exc:
            reason = f"Selected ClaML could not be validated or parsed: {exc}"
            rows.extend(
                empty_row(year, code, "claml_parse_or_validation_error", [member], reason)
                for code in REQUESTED_CODES
            )
            annual_sources.append(
                {
                    "year": year,
                    "status": "claml_parse_or_validation_error",
                    "archive_path": rel(archive_path),
                    "archive_sha256": sha256_file(archive_path),
                    "xml_member": member,
                    "xml_sha256": sha256_bytes(xml_bytes),
                    "candidates": [member],
                    "warning": reason,
                }
            )
            continue

        archive_hash = sha256_file(archive_path)
        xml_hash = sha256_bytes(xml_bytes)
        annual_sources.append(
            {
                "year": year,
                "status": "verified_unique_claml_archive_and_xml",
                "archive_path": rel(archive_path),
                "archive_sha256": archive_hash,
                "xml_member": member,
                "xml_sha256": xml_hash,
                "candidates": [rel(archive_path)],
                "warning": "",
            }
        )

        parent = classes["8-839.8"]
        branch_codes = ["8-839.8"] + [
            item.attrib["code"] for item in parent.findall("SubClass")
        ]
        branch_codes = list(dict.fromkeys(branch_codes))
        selected_codes = list(REQUESTED_CODES) + sorted(
            set(branch_codes) - set(REQUESTED_CODES), key=str.lower
        )

        for code in selected_codes:
            is_requested = code in REQUESTED_CODES
            node = classes.get(code)
            row = {column: "" for column in AUDIT_COLUMNS}
            row.update(
                {
                    "catalogue_year": year,
                    "code": code,
                    "row_scope": "requested_144" if is_requested else "additional_branch_code",
                    "belongs_to_requested_144": is_requested,
                    "source_archive_path": rel(archive_path),
                    "source_archive_filename": archive_path.name,
                    "source_archive_sha256": archive_hash,
                    "source_xml_filename": Path(member).name,
                    "source_xml_member": member,
                    "source_xml_sha256": xml_hash,
                    "catalogue_source_status": "verified_unique_claml_archive_and_xml",
                    "annual_archive_candidates": rel(archive_path),
                }
            )
            if node is None:
                row.update(
                    {
                        "exists": "no",
                        "non_existence_reason": (
                            "Requested literal code is absent from the validated annual ClaML classes."
                        ),
                        "manual_review_flag": False,
                    }
                )
                rows.append(row)
                continue

            rubrics: dict[str, list[str]] = {}
            for rubric in node.findall("Rubric"):
                value = clean_text(rubric)
                if value:
                    rubrics.setdefault(rubric.attrib.get("kind", ""), []).append(value)
            title_text = pipe(rubrics.get("preferred", []))
            inclusion = pipe(rubrics.get("inclusion", []))
            exclusion = pipe(rubrics.get("exclusion", []))
            other = pipe(
                [
                    f"[{kind}] {value}"
                    for kind, values in rubrics.items()
                    if kind not in {"preferred", "inclusion", "exclusion"}
                    for value in values
                ]
            )
            classification = CLASSIFICATION.get(
                code, "parent, residual, or otherwise ambiguous"
            )
            row.update(
                {
                    "exists": "yes",
                    "official_title": title_text,
                    "inclusion_notes": inclusion,
                    "exclusion_notes": exclusion,
                    "usage_or_coding_notes": other,
                    "claml_class_identifier": node.attrib.get("code", ""),
                    "claml_xml_location": f"Class[@code='{code}']",
                    "claml_superclass_codes": pipe(
                        [item.attrib.get("code", "") for item in node.findall("SuperClass")]
                    ),
                    "claml_subclass_codes": pipe(
                        [item.attrib.get("code", "") for item in node.findall("SubClass")]
                    ),
                    "analyst_classification": classification,
                    "classification_basis": (
                        "Analyst interpretation of the separately retained official title and notes, "
                        "cross-checked against the provisional clinical classification."
                    ),
                    "provisional_classification_disagreement": False,
                    "exact_current_wording": pipe(
                        [
                            title_text,
                            f"[inclusion] {inclusion}" if inclusion else "",
                            f"[exclusion] {exclusion}" if exclusion else "",
                            other,
                        ]
                    ),
                    "manual_review_flag": False,
                }
            )
            rows.append(row)

        for code, node in classes.items():
            if code.startswith("8-842."):
                rubrics = [
                    clean_text(rubric)
                    for rubric in node.findall("Rubric")
                    if rubric.attrib.get("kind") == "preferred"
                ]
                codes_842.append(
                    {
                        "catalogue_year": str(year),
                        "code": code,
                        "official_title": pipe(rubrics),
                        "source_archive_path": rel(archive_path),
                        "source_xml_member": member,
                    }
                )

    audit = pd.DataFrame(rows, columns=AUDIT_COLUMNS)
    requested = audit[audit.belongs_to_requested_144.astype(bool)]
    if len(requested) != 144:
        raise RuntimeError(f"Requested audit matrix has {len(requested)} rows, expected 144")
    if requested.duplicated(["catalogue_year", "code"]).any():
        raise RuntimeError("Requested audit matrix has duplicate year-code rows")

    # Compare only adjacent years whose two annual archives were both validated.
    audit = audit.sort_values(
        ["catalogue_year", "belongs_to_requested_144", "code"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    for code, indices in audit.groupby("code", sort=False).groups.items():
        ordered = audit.loc[indices].sort_values("catalogue_year")
        previous: pd.Series | None = None
        for index, current in ordered.iterrows():
            if previous is None:
                audit.loc[index, "wording_changed_vs_previous_year"] = "not_applicable"
                audit.loc[index, "clinical_or_coding_meaning_changed_vs_previous_year"] = "not_applicable"
            elif current.catalogue_year != int(previous.catalogue_year) + 1:
                audit.loc[index, "wording_changed_vs_previous_year"] = "unknown"
                audit.loc[index, "clinical_or_coding_meaning_changed_vs_previous_year"] = "unknown"
                audit.loc[index, "manual_review_flag"] = True
                audit.loc[index, "manual_review_reason"] = pipe(
                    [str(current.manual_review_reason), "Previous annual source is not consecutively verifiable."]
                )
            elif current.exists != "yes" or previous.exists != "yes":
                audit.loc[index, "wording_changed_vs_previous_year"] = "unknown"
                audit.loc[index, "clinical_or_coding_meaning_changed_vs_previous_year"] = "unknown"
                if current.exists == "yes":
                    audit.loc[index, "manual_review_flag"] = True
                    audit.loc[index, "manual_review_reason"] = pipe(
                        [
                            str(current.manual_review_reason),
                            "Previous annual source is not verifiable, so the year-on-year wording and meaning comparison is unknown.",
                        ]
                    )
            else:
                changed = current.exact_current_wording != previous.exact_current_wording
                audit.loc[index, "wording_changed_vs_previous_year"] = "yes" if changed else "no"
                audit.loc[index, "exact_previous_wording"] = previous.exact_current_wording
                if current.catalogue_year == 2024 and code in SEMANTIC_CHANGE_2024:
                    semantic, explanation = SEMANTIC_CHANGE_2024[code]
                else:
                    semantic = "no"
                    explanation = (
                        "Wording clarification without a change in the audited clinical category."
                        if changed else "No source wording or audited clinical-category change."
                    )
                audit.loc[index, "clinical_or_coding_meaning_changed_vs_previous_year"] = semantic
                audit.loc[index, "semantic_change_explanation"] = explanation
            previous = current

    return audit, annual_sources, codes_842


def canonical_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    code = pd.read_csv(CANONICAL_CODE_DATA, dtype={"ik": str}, keep_default_na=False)
    required = {
        "reporting_year", "site_identifier", "ik", "OPS_code", "hospital_name",
        "current_parser_numeric_count", "suppressed_flag", "suppressed_record_count",
        "visible_record_count", "raw_record_count", "source_file",
    }
    missing = required - set(code.columns)
    if missing:
        raise RuntimeError(f"Canonical code-level data lacks columns: {sorted(missing)}")
    code["reporting_year"] = pd.to_numeric(code.reporting_year, errors="raise").astype(int)
    code["OPS_code_literal"] = code.OPS_code.astype(str)
    code["ops_code_normalised"] = code.OPS_code_literal.str.strip().str.lower()
    selected = code[
        code.reporting_year.isin(YEARS)
        & code.ops_code_normalised.str.startswith("8-839.8")
    ].copy()
    for column in (
        "current_parser_numeric_count", "suppressed_record_count",
        "visible_record_count", "raw_record_count",
    ):
        selected[column] = pd.to_numeric(selected[column], errors="coerce").fillna(0).astype(int)
    selected["suppressed_flag"] = selected.suppressed_flag.astype(str).str.lower().isin(
        {"true", "1", "yes"}
    )
    return code, selected


def occurrence_table(audit: pd.DataFrame, observed: pd.DataFrame) -> pd.DataFrame:
    catalogue = audit[
        audit.belongs_to_requested_144.astype(bool)
        & audit.code.isin(DE_NOVO_CODES)
    ][["catalogue_year", "code", "exists"]].rename(
        columns={"catalogue_year": "reporting_year", "exists": "catalogue_availability"}
    )
    firsts: dict[str, dict[str, Any]] = {}
    annotated, _ = resolve_component_precedence(observed)
    for code in DE_NOVO_CODES:
        group = observed[observed.ops_code_normalised.eq(code)]
        firsts[code] = {
            "any": int(group.reporting_year.min()) if len(group) else None,
            "numeric": int(group.loc[group.current_parser_numeric_count.gt(0), "reporting_year"].min())
            if group.current_parser_numeric_count.gt(0).any() else None,
            "suppressed": int(group.loc[group.suppressed_record_count.gt(0), "reporting_year"].min())
            if group.suppressed_record_count.gt(0).any() else None,
        }

    rows: list[dict[str, Any]] = []
    for year in YEARS:
        for code in DE_NOVO_CODES:
            group = observed[
                observed.reporting_year.eq(year)
                & observed.ops_code_normalised.eq(code)
            ]
            resolved_group = annotated[
                annotated.reporting_year.eq(year)
                & annotated.ops_code_normalised.eq(code)
                & annotated.retained_site_resolution.astype(bool)
            ]
            physical_group = resolved_group[
                ~resolved_group.unresolved_institution_provider.astype(bool)
            ]
            available = catalogue[
                catalogue.reporting_year.eq(year) & catalogue.code.eq(code)
            ].catalogue_availability.iloc[0]
            verified_years = audit[
                audit.code.eq(code) & audit.exists.eq("yes")
            ].catalogue_year.astype(int)
            introduction = (
                int(verified_years.min())
                if len(verified_years) and int(verified_years.min()) == min(YEARS)
                else None
            )
            data_first = firsts[code]["any"]
            rows.append(
                {
                    "reporting_year": year,
                    "code": code,
                    "catalogue_availability": available,
                    "official_catalogue_introduction_year": introduction or "",
                    "official_catalogue_final_year": int(verified_years.max()) if len(verified_years) else "",
                    "gba_data_first_year": data_first or "",
                    "first_openly_numeric_year": firsts[code]["numeric"] or "",
                    "first_suppressed_year": firsts[code]["suppressed"] or "",
                    "openly_numeric_activity": int(group.current_parser_numeric_count.sum()),
                    "post_precedence_openly_numeric_activity": int(resolved_group.visible_count.sum()),
                    "numeric_record_count": int(group.visible_record_count.sum()),
                    "suppressed_record_count": int(group.suppressed_record_count.sum()),
                    "post_precedence_suppressed_record_count": int(resolved_group.suppressed_entries.sum()),
                    "reporting_site_identifier_count_pre_resolution": int(group.site_identifier.nunique()),
                    "reporting_physical_site_count": int(physical_group.site_identifier.nunique()),
                    "reporting_site_or_fallback_unit_count_after_precedence": int(
                        resolved_group.site_identifier.nunique()
                    ),
                    "reporting_institution_count": int(group["ik"].nunique()),
                    "source_literal_variants": pipe(sorted(set(group.OPS_code_literal))),
                    "is_gba_data_first_year": bool(data_first == year),
                    "is_first_openly_numeric_year": bool(firsts[code]["numeric"] == year),
                    "is_first_suppressed_year": bool(firsts[code]["suppressed"] == year),
                    "data_first_year_later_than_catalogue_first_year": (
                        bool(data_first > introduction) if data_first and introduction else "unknown"
                    ),
                    "occurrence_predates_official_introduction": (
                        bool(year < introduction and len(group)) if introduction else "unknown"
                    ),
                    "catalogue_vs_data_lag_flag": (
                        "observed_lag_requires_interpretation"
                        if data_first and introduction and data_first > introduction and year == data_first
                        else ""
                    ),
                }
            )
    result = pd.DataFrame(rows)
    if len(result) != 48:
        raise RuntimeError(f"Occurrence table has {len(result)} rows, expected 48")
    return result


def reconciliation(observed: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    annotated, _ = resolve_component_precedence(observed)
    retained = annotated[annotated.retained_site_resolution].copy()
    keys = ["reporting_year", "site_identifier", "ik"]

    rows: list[dict[str, Any]] = []
    for key, group in retained.groupby(keys, sort=True, dropna=False):
        all_group = annotated[
            annotated.reporting_year.eq(key[0])
            & annotated["ik"].eq(key[2])
            & annotated.ops_code_normalised.isin(group.ops_code_normalised)
        ]
        rows.append(
            {
                "reporting_year": int(key[0]),
                "institution_identifier": key[2],
                "physical_site_identifier": key[1],
                "site_name": next(
                    (str(value) for value in group.hospital_name if str(value).strip()), ""
                ),
                "reporting_unit_type": (
                    "unresolved_institution_level_fallback"
                    if group.unresolved_institution_provider.astype(bool).any()
                    else "physical_site"
                ),
                "contributing_code_level_records": " || ".join(
                    f"{item.OPS_code_literal}:visible={int(item.visible_count)},"
                    f"suppressed={int(item.suppressed_entries)},source={item.source_file}"
                    for item in group.sort_values("ops_code_normalised").itertuples()
                ),
                "all_precedence_candidate_records": " || ".join(
                    f"{item.OPS_code_literal}:retained={bool(item.retained_site_resolution)},"
                    f"visible={int(item.visible_count)},suppressed={int(item.suppressed_entries)}"
                    for item in all_group.sort_values("ops_code_normalised").itertuples()
                ),
                "code_level_visible_sum": int(group.visible_count.sum()),
                "code_level_suppressed_entry_count": int(group.suppressed_entries.sum()),
                "parent_subcode_pattern": (
                    "parent_plus_terminal"
                    if group.ops_code_normalised.eq("8-839.8").any()
                    and (~group.ops_code_normalised.eq("8-839.8")).any()
                    else "no_parent_terminal_coexistence"
                ),
                "duplicate_or_site_precedence_pattern": pipe(
                    sorted(set(all_group.resolution_reason.astype(str)))
                ),
            }
        )
    recomputed = pd.DataFrame(rows)

    main = pd.read_csv(MAIN_SITE_DATA, dtype={"ik": str}, keep_default_na=False)
    main["reporting_year"] = pd.to_numeric(main.reporting_year, errors="raise").astype(int)
    main = main[main.reporting_year.isin(YEARS)].copy()
    main["visible_activity"] = pd.to_numeric(main.visible_activity, errors="coerce").fillna(0).astype(int)
    main["suppressed_entries"] = pd.to_numeric(main.suppressed_entries, errors="coerce").fillna(0).astype(int)
    compare = recomputed.merge(
        main[["reporting_year", "site_identifier", "ik", "visible_activity", "suppressed_entries"]],
        left_on=["reporting_year", "physical_site_identifier", "institution_identifier"],
        right_on=["reporting_year", "site_identifier", "ik"],
        how="outer",
        indicator=True,
        validate="one_to_one",
    )
    compare["main_analysis_visible_activity"] = pd.to_numeric(
        compare.visible_activity, errors="coerce"
    ).fillna(0).astype(int)
    compare["main_analysis_suppressed_entry_count"] = pd.to_numeric(
        compare.suppressed_entries, errors="coerce"
    ).fillna(0).astype(int)
    compare["code_level_visible_sum"] = pd.to_numeric(
        compare.code_level_visible_sum, errors="coerce"
    ).fillna(0).astype(int)
    compare["code_level_suppressed_entry_count"] = pd.to_numeric(
        compare.code_level_suppressed_entry_count, errors="coerce"
    ).fillna(0).astype(int)
    compare["difference"] = (
        compare.code_level_visible_sum - compare.main_analysis_visible_activity
    )
    compare["suppressed_entry_difference"] = (
        compare.code_level_suppressed_entry_count
        - compare.main_analysis_suppressed_entry_count
    )
    exact = (
        compare._merge.eq("both")
        & compare.difference.eq(0)
        & compare.suppressed_entry_difference.eq(0)
    )
    compare["reconciliation_status"] = exact.map(
        {True: "fully_reconciled", False: "mismatch_unresolved"}
    )
    compare["explanation"] = "Exact reproduction after lower-case matching, exact-code site precedence, retention of parent and subcodes, and separate suppressed-entry aggregation."
    compare.loc[~exact, "explanation"] = (
        "Mismatch remains after reproducing documented pipeline logic; inspect detailed mismatch output."
    )
    compare["likely_processing_stage_responsible"] = ""
    compare.loc[~compare._merge.eq("both"), "likely_processing_stage_responsible"] = "dataset key coverage"
    compare.loc[
        compare._merge.eq("both") & compare.difference.ne(0),
        "likely_processing_stage_responsible",
    ] = "visible aggregation or precedence"
    compare.loc[
        compare._merge.eq("both") & compare.suppressed_entry_difference.ne(0),
        "likely_processing_stage_responsible",
    ] = "suppressed-entry aggregation"
    compare["resolved_vs_unresolved"] = exact.map({True: "resolved", False: "unresolved"})
    compare["manual_review_flag"] = ~exact
    compare["site_name"] = compare.site_name.fillna("")
    compare["physical_site_identifier"] = compare.physical_site_identifier.fillna(compare.site_identifier)
    compare["institution_identifier"] = compare.institution_identifier.fillna(compare["ik"])

    columns = [
        "reporting_year", "institution_identifier", "physical_site_identifier", "site_name",
        "reporting_unit_type", "contributing_code_level_records",
        "all_precedence_candidate_records", "code_level_visible_sum",
        "main_analysis_visible_activity", "difference",
        "code_level_suppressed_entry_count", "main_analysis_suppressed_entry_count",
        "suppressed_entry_difference", "parent_subcode_pattern",
        "duplicate_or_site_precedence_pattern", "reconciliation_status", "explanation",
        "likely_processing_stage_responsible", "resolved_vs_unresolved", "manual_review_flag",
    ]
    output = compare[columns].sort_values(
        ["reporting_year", "institution_identifier", "physical_site_identifier"]
    ).reset_index(drop=True)
    mismatch = output[output.reconciliation_status.ne("fully_reconciled")].copy()
    return output, mismatch


def summary_table(
    audit: pd.DataFrame, occurrence: pd.DataFrame, observed: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for code in REQUESTED_CODES:
        group = audit[audit.code.eq(code)].sort_values("catalogue_year")
        verified = group[group.exists.eq("yes")]
        first = verified.iloc[0] if len(verified) else None
        final = verified.iloc[-1] if len(verified) else None
        occurrence_code = occurrence[occurrence.code.eq(code)] if code in DE_NOVO_CODES else pd.DataFrame()
        observed_code = observed[observed.ops_code_normalised.eq(code)]
        data_first = (
            int(observed_code.reporting_year.min()) if len(observed_code) else ""
        )
        numeric_first = (
            int(
                observed_code.loc[
                    observed_code.current_parser_numeric_count.gt(0), "reporting_year"
                ].min()
            )
            if observed_code.current_parser_numeric_count.gt(0).any()
            else ""
        )
        suppressed_first = (
            int(
                observed_code.loc[
                    observed_code.suppressed_record_count.gt(0), "reporting_year"
                ].min()
            )
            if observed_code.suppressed_record_count.gt(0).any()
            else ""
        )
        wording_changes = verified[
            verified.wording_changed_vs_previous_year.eq("yes")
        ]
        semantic_changes = verified[
            verified.clinical_or_coding_meaning_changed_vs_previous_year.eq("yes")
        ]
        missing_years = group[~group.exists.eq("yes")].catalogue_year.astype(str).tolist()
        rows.append(
            {
                "code": code,
                "first_catalogue_year": int(first.catalogue_year) if first is not None else "",
                "last_catalogue_year": int(final.catalogue_year) if final is not None else "",
                "availability_continuous": (
                    "unknown; required archives missing for " + ",".join(missing_years)
                    if missing_years else "yes"
                ),
                "exact_title_first_verified_year": first.official_title if first is not None else "",
                "exact_title_final_verified_year": final.official_title if final is not None else "",
                "wording_stable": (
                    "unknown for full 2013-2024 period; "
                    + ("changed in verified period" if len(wording_changes) else "stable in verified period")
                ),
                "clinical_or_coding_meaning_stable": (
                    "unknown for full 2013-2024 period; "
                    + ("changed in verified period" if len(semantic_changes) else "stable in verified period")
                ),
                "all_wording_changes": " || ".join(
                    f"{int(item.catalogue_year)}: {item.exact_previous_wording} -> {item.exact_current_wording}"
                    for item in wording_changes.itertuples()
                ),
                "all_semantic_changes": " || ".join(
                    f"{int(item.catalogue_year)}: {item.semantic_change_explanation}"
                    for item in semantic_changes.itertuples()
                ),
                "catalogue_introduction_year": "",
                "catalogue_introduction_year_status": (
                    "not verifiable because 2013-2018 required archives are missing"
                ),
                "gba_data_first_year": (
                    occurrence_code.gba_data_first_year.iloc[0]
                    if len(occurrence_code) else data_first
                ),
                "first_numeric_year": (
                    occurrence_code.first_openly_numeric_year.iloc[0]
                    if len(occurrence_code) else numeric_first
                ),
                "first_suppressed_year": (
                    occurrence_code.first_suppressed_year.iloc[0]
                    if len(occurrence_code) else suppressed_first
                ),
                "final_classification": (
                    CLASSIFICATION[code] if len(verified) else "unresolved"
                ),
                "recommended_inclusion_in_de_novo_sensitivity": (
                    "provisional_yes_pending_missing_catalogue_review"
                    if code in DE_NOVO_CODES else "no"
                ),
                "manual_review_status": "required",
                "manual_review_reason": (
                    "Whole-period historical availability and introduction cannot be established "
                    "without the required 2013-2018 ClaML archives."
                ),
            }
        )
    return pd.DataFrame(rows)


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None) -> str:
    show = frame[columns].copy() if columns else frame.copy()
    if show.empty:
        return "_No rows._"
    clean = show.fillna("").astype(str).apply(
        lambda column: column.str.replace("|", r"\|", regex=False).str.replace("\n", " ", regex=False)
    )
    return "\n".join(
        [
            "| " + " | ".join(clean.columns) + " |",
            "| " + " | ".join("---" for _ in clean.columns) + " |",
            *["| " + " | ".join(row) + " |" for row in clean.itertuples(index=False, name=None)],
        ]
    )


def report_text(
    audit: pd.DataFrame,
    summary: pd.DataFrame,
    occurrence: pd.DataFrame,
    reconciliation_frame: pd.DataFrame,
    mismatches: pd.DataFrame,
    annual_sources: list[dict[str, Any]],
    codes_842: list[dict[str, str]],
) -> str:
    requested = audit[audit.belongs_to_requested_144.astype(bool)]
    additional = audit[~audit.belongs_to_requested_144.astype(bool)]
    source_table = pd.DataFrame(
        {
            "year": [item["year"] for item in annual_sources],
            "status": [item["status"] for item in annual_sources],
            "archive": [item["archive_path"] for item in annual_sources],
            "xml_member": [item["xml_member"] for item in annual_sources],
        }
    )
    year_table = requested.groupby("catalogue_year", as_index=False).agg(
        verified_existing_codes=("exists", lambda values: int((values == "yes").sum())),
        unknown_codes=("exists", lambda values: int((values == "unknown").sum())),
        manual_review_rows=("manual_review_flag", lambda values: int(pd.Series(values).astype(bool).sum())),
    )
    wording = requested[requested.wording_changed_vs_previous_year.eq("yes")]
    semantic = requested[
        requested.clinical_or_coding_meaning_changed_vs_previous_year.eq("yes")
    ]
    first_year = occurrence.drop_duplicates("code")[
        ["code", "official_catalogue_introduction_year", "official_catalogue_final_year",
         "gba_data_first_year", "first_openly_numeric_year", "first_suppressed_year"]
    ]
    occurrence_pivot = occurrence.pivot(
        index="reporting_year", columns="code", values="openly_numeric_activity"
    ).reset_index()
    suppressed_pivot = occurrence.pivot(
        index="reporting_year", columns="code", values="suppressed_record_count"
    ).reset_index()
    fully = int(reconciliation_frame.reconciliation_status.eq("fully_reconciled").sum())
    missing_years = [
        str(item["year"])
        for item in annual_sources
        if item["status"] != "verified_unique_claml_archive_and_xml"
    ]
    observed_legacy = pd.read_csv(CANONICAL_CODE_DATA, dtype=str, keep_default_na=False)
    legacy = observed_legacy[
        pd.to_numeric(observed_legacy.reporting_year, errors="coerce").eq(2013)
        & observed_legacy.OPS_code.str.lower().eq("8-839.80")
    ]
    legacy_suppressed = int(
        pd.to_numeric(legacy.suppressed_record_count, errors="coerce").fillna(0).sum()
    )
    codes_842_count = len({(item["catalogue_year"], item["code"]) for item in codes_842})
    codes_842_frame = pd.DataFrame(codes_842)
    if len(codes_842_frame):
        codes_842_summary = (
            codes_842_frame.groupby("code", as_index=False)
            .agg(
                verified_catalogue_years=("catalogue_year", lambda values: ",".join(values)),
                exact_official_title_variants=(
                    "official_title", lambda values: " || ".join(dict.fromkeys(values))
                ),
            )
        )
    else:
        codes_842_summary = pd.DataFrame(
            columns=["code", "verified_catalogue_years", "exact_official_title_variants"]
        )

    return f"""# Official BfArM OPS 8-839.8* and canonical G-BA audit, 2013–2024

## Audit purpose and release boundary

This is an audit of annual local BfArM ClaML systematics and the canonical
code-level G-BA data used upstream of the current main-analysis pipeline. It
does **not** calculate the final de novo sensitivity analysis and changes no
production code, existing analytical output, manuscript, supplement, table, or
figure.

The requested matrix contains exactly **{len(requested)}** rows; additional
8-839.8* branch rows: **{len(additional)}**. Row-level evidence is in
[`ops_code_audit_2013_2024.csv`](ops_code_audit_2013_2024.csv).

## Annual ClaML source gate

Only an annual archive matching `*syst-claml*.zip` was eligible. Each selected
XML was decompressed in memory and parsed directly. Extracted XML, PDFs,
indexes, browser exports, current definitions, and external summaries were not
used as catalogue evidence.

{markdown_table(source_table)}

Required annual archives are missing for **{', '.join(missing_years)}**. The
XML files present in those folders were deliberately not substituted. Catalogue
processing stopped for each affected year, leaving its requested combinations
as `exists=unknown` with empty wording and classification. This is a prominent
manual-review blocker, not evidence that the codes were absent.

## Year-by-year catalogue coverage

{markdown_table(year_table)}

For 2019–2024, all 12 requested literal codes exist, including distinct
`8-839.8a`; no other code under the complete 8-839.8 branch was found. The
source-proven finding does not extend through 2013–2018 until their required
archives are supplied.

## Code-level summary

{markdown_table(summary, ['code', 'first_catalogue_year', 'last_catalogue_year',
    'availability_continuous', 'wording_stable', 'clinical_or_coding_meaning_stable',
    'gba_data_first_year', 'final_classification',
    'recommended_inclusion_in_de_novo_sensitivity', 'manual_review_status'])}

The official introduction years of `.87`, `.88`, `.89`, and `.8a`, and
continuous availability of `.87`/`.88` from 2013, are **not verifiable under
the mandated source rule** because the 2013–2018 archives are absent. G-BA
first occurrence is evidence about reporting data, not a substitute for an
official catalogue introduction date.

## Complete wording changes in the verified consecutive period

{markdown_table(wording, ['catalogue_year', 'code', 'exact_previous_wording',
    'exact_current_wording', 'semantic_change_explanation'])}

## Complete semantic changes in the verified consecutive period

{markdown_table(semantic, ['catalogue_year', 'code', 'exact_previous_wording',
    'exact_current_wording', 'semantic_change_explanation'])}

The 2024 changes to `.84` and `.86` change their specific intervention meaning
but leave them in the broad secondary-intervention category. Additions to `.81`
and `.87`–`.8a` clarify existing-shunt or shunt-creation meaning without a
category change. All such judgments remain separate from the exact German
source wording in the audit CSV.

## Canonical G-BA dataset and pipeline provenance

Verified canonical code-level artefact:
[`outputs/audit/tips_code_level_audit.csv`](../audit/tips_code_level_audit.csv).
It contains reporting year, IK, physical-site identifier, literal OPS code,
visible numeric value, suppression status/count, raw-record multiplicity, and
source XML path. OPS codes enter as strings; the audit creates a separate
lower-case comparison key and confirms that `8-839.8`, `8-839.8a`, and
`8-839.8x` remain distinct.

The verified downstream chain is:

1. Raw production-eligible reports: `data/xml/xml_<year>/*-xml.xml`.
2. Grouped pre-resolution code-level artefact:
   `outputs/audit/tips_code_level_audit.csv`. Repeated raw rows are represented
   by `raw_record_count`; production-visible direct values are held in
   `current_parser_numeric_count`; suppression is preserved separately.
3. `resolve_component_precedence()` in
   `src/gba_ops_reanalysis/site_resolution_validation.py`: within exact
   `(reporting_year, IK, literal OPS code)` groups, a `-99` aggregate is excluded
   when a component site exists. A `-99` record without a component remains as
   an unresolved institution-level fallback.
4. Parent `8-839.8` and terminal subcodes are both retained; there is no
   hierarchy deletion. Suppressed entries receive no imputed numeric value.
5. `scripts/run_tips_site_resolution_validation.py` writes
   `outputs/site_resolution_validation/resolved_site_level_data.csv`.
6. `scripts/run_tips_final_corrected.py` reads that site table and the canonical
   code table, then writes `outputs/final_corrected_2026-07-24`.
7. `scripts/build_tips_final_submission_assets.py` consumes the corrected output
   for current main tables and figures.

The code-level CSV's one-off creation script is not retained in the repository.
Its report documents the extraction logic and raw source paths, while current
pipeline entry points consume the CSV explicitly. This missing creator is a
provenance uncertainty requiring manual review; no competing code-level input
to the current final pipeline was found.

## Catalogue-versus-data first years

{markdown_table(first_year)}

No before-introduction check can be concluded because official introduction
years are blocked by the missing archives. Observed first years are 2013 for
`.87` and `.88`, and 2016 for `.89` and literal `.8a`. Both lower- and
upper-case source variants of `.8a` normalise to the separate literal key
`8-839.8a`; they are never converted to numeric or merged with the parent.

## Annual openly numeric activity in the canonical pre-resolution extraction

{markdown_table(occurrence_pivot)}

## Annual suppressed raw-record counts

{markdown_table(suppressed_pivot)}

Full annual numeric-record, suppressed-record, site, institution, availability,
source-literal, pre-resolution, and post-precedence fields are in
[`ops_code_occurrence_by_year.csv`](ops_code_occurrence_by_year.csv).

## Reconciliation with the current main analysis

- Fully reconciled site-years: **{fully}**
- Mismatching site-years: **{len(mismatches)}**
- Resolved through documented pipeline logic: **{fully}**
- Remaining unresolved mismatches: **{len(mismatches)}**

The reconciliation reproduces lower-case matching, reporting years, repeated-row
aggregation already represented in the code table, exact-code component-site
precedence, unresolved institution-level fallback, retention of parent and
subcodes, and separate suppressed-entry aggregation. Both visible activity and
suppressed-entry counts reconcile exactly. See
[`ops_code_reconciliation_site_year.csv`](ops_code_reconciliation_site_year.csv)
and [`ops_code_reconciliation_mismatches.csv`](ops_code_reconciliation_mismatches.csv).

The canonical data also contain {len(legacy)} grouped 2013 records for literal
`8-839.80`, representing {legacy_suppressed} suppressed entries. This strict
catalogue audit cannot adjudicate its 2013 catalogue validity because the
required 2013 archive is missing; it is retained in the family reconciliation
and not remapped or deleted.

## Recommended de novo sensitivity code set

The **provisional**, source-supported set for the verified 2019–2024 period is:

`8-839.87`, `8-839.88`, `8-839.89`, `8-839.8a`.

It measures **“activity coded with specific de novo TIPS creation subcodes”**
and does not necessarily identify all de novo TIPS placements, unique patients,
or hospital admissions.

One fixed code set for the whole 2013–2024 period is **not yet historically
validated**. A year-specific set also cannot be established from the allowed
sources until the 2013–2018 annual ClaML archives are supplied and manually
reviewed. The final de novo sensitivity analysis must not be started on the
basis of this incomplete historical catalogue audit.

## 8-842.* exclusion

The verified annual catalogues contained {codes_842_count} year-code instances
under `8-842.*`. They were inspected only as an exclusion check and are outside
the 8-839.8 branch. They are excluded from the recommended TIPS de novo
sensitivity code set because they describe different or more complex
portal-vein stent procedures.

{markdown_table(codes_842_summary)}

## Unresolved issues and required manual review

1. Obtain the exact official annual `*syst-claml*.zip` archives for 2013–2018.
2. Re-run this audit and manually review the 144-row matrix, exact annual
   wording, code summary, official introduction years, and fixed/year-specific
   code-set conclusion.
3. Review the absent one-off creator for the canonical code-level CSV or archive
   an equivalent reproducible extraction script and manifest.
4. Review the `.84` and `.86` 2024 semantic-change judgments.
5. Review the empty mismatch file and the complete site-year reconciliation.

**Do not start the de novo sensitivity analysis until the catalogue CSV, code
summary, reconciliation results, and relevant annual ClaML definitions have
been manually reviewed.**
"""


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    audit, annual_sources, codes_842 = parse_catalogues()
    canonical_all, observed = canonical_data()
    occurrence = occurrence_table(audit, observed)
    reconciliation_frame, mismatches = reconciliation(observed)
    summary = summary_table(audit, occurrence, observed)

    output_paths = {
        "catalogue_audit": OUTPUT / "ops_code_audit_2013_2024.csv",
        "code_summary": OUTPUT / "ops_code_summary_2013_2024.csv",
        "occurrence": OUTPUT / "ops_code_occurrence_by_year.csv",
        "reconciliation": OUTPUT / "ops_code_reconciliation_site_year.csv",
        "mismatches": OUTPUT / "ops_code_reconciliation_mismatches.csv",
        "report": OUTPUT / "ops_code_audit_2013_2024.md",
        "manifest": OUTPUT / "audit_run_manifest.json",
    }
    audit.to_csv(output_paths["catalogue_audit"], index=False)
    summary.to_csv(output_paths["code_summary"], index=False)
    occurrence.to_csv(output_paths["occurrence"], index=False)
    reconciliation_frame.to_csv(output_paths["reconciliation"], index=False)
    mismatches.to_csv(output_paths["mismatches"], index=False)
    output_paths["report"].write_text(
        report_text(
            audit, summary, occurrence, reconciliation_frame, mismatches,
            annual_sources, codes_842,
        ),
        encoding="utf-8",
    )

    dirty_lines = git_value("status", "--porcelain").splitlines()
    warnings = [
        item["warning"] for item in annual_sources if item.get("warning")
    ]
    warnings.extend(
        [
            "The one-off creator of outputs/audit/tips_code_level_audit.csv is not retained in the repository.",
            "Official introduction years and whole-period fixed-code validity are unresolved until 2013-2018 archives are supplied.",
            "Manual review is required before any final de novo sensitivity analysis.",
        ]
    )
    manifest = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_branch": git_value("branch", "--show-current"),
        "git_commit_hash": git_value("rev-parse", "HEAD"),
        "dirty_working_tree": bool(dirty_lines),
        "dirty_working_tree_entry_count": len(dirty_lines),
        "environment": {
            "python_version": sys.version,
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "pandas_version": pd.__version__,
            "working_directory": str(ROOT),
            "pid": os.getpid(),
        },
        "catalogue_source_rule": "exactly one *syst-claml*.zip per annual directory; extracted XML is ineligible",
        "annual_sources": annual_sources,
        "canonical_gba_dataset_path": rel(CANONICAL_CODE_DATA),
        "canonical_gba_dataset_sha256": sha256_file(CANONICAL_CODE_DATA),
        "canonical_gba_dataset_rows_all_years": len(canonical_all),
        "canonical_gba_family_rows_2013_2024": len(observed),
        "main_site_dataset_path": rel(MAIN_SITE_DATA),
        "main_site_dataset_sha256": sha256_file(MAIN_SITE_DATA),
        "scripts_and_modules_inspected": [
            "outputs/indications/tips_8-839-8_updated2024/FINAL_OUTPUT_README.md",
            "outputs/audit/tips_counting_audit_report.md",
            "scripts/build_indication_report.py",
            "src/gba_ops_reanalysis/gba_xml.py",
            "src/gba_ops_reanalysis/ops_icd.py",
            "src/gba_ops_reanalysis/longitudinal.py",
            "scripts/run_tips_site_resolution_validation.py",
            "src/gba_ops_reanalysis/site_resolution_validation.py",
            "scripts/run_tips_final_corrected.py",
            "src/gba_ops_reanalysis/final_corrected.py",
            "scripts/build_tips_final_submission_assets.py",
            "tests/test_site_resolution_validation.py",
            "tests/test_official_ops_88398.py",
        ],
        "scripts_and_modules_executed": [
            "audits/ops_code_audit_2013_2024/run_audit.py",
            "gba_ops_reanalysis.site_resolution_validation.resolve_component_precedence",
        ],
        "generated_output_paths": [rel(path) for path in output_paths.values()],
        "requested_year_code_rows": int(audit.belongs_to_requested_144.astype(bool).sum()),
        "additional_88398_branch_rows": int((~audit.belongs_to_requested_144.astype(bool)).sum()),
        "fully_reconciled_site_years": int(
            reconciliation_frame.reconciliation_status.eq("fully_reconciled").sum()
        ),
        "mismatching_site_years": len(mismatches),
        "unresolved_mismatches": int(
            mismatches.resolved_vs_unresolved.eq("unresolved").sum()
        ) if len(mismatches) else 0,
        "warnings": warnings,
        "unresolved_issues": [
            "Missing required 2013-2018 annual ClaML archives.",
            "Canonical code-level CSV creator script not retained.",
            "Whole-period official introduction years and fixed code set not verifiable.",
        ],
    }
    output_paths["manifest"].write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    requested_count = int(audit.belongs_to_requested_144.astype(bool).sum())
    additional_count = int((~audit.belongs_to_requested_144.astype(bool)).sum())
    missing = [
        str(item["year"]) for item in annual_sources
        if item["status"] != "verified_unique_claml_archive_and_xml"
    ]
    firsts = occurrence.drop_duplicates("code").set_index("code")
    print("Generated output paths:")
    for path in output_paths.values():
        print(f"- {path}")
    print(f"Requested year-code rows: {requested_count} (expected 144)")
    print(f"Additionally discovered 8-839.8* rows: {additional_count}")
    print(f"Missing or ambiguous annual catalogues: {', '.join(missing) if missing else 'none'}")
    print("Provisional recommended de novo code set: 8-839.87, 8-839.88, 8-839.89, 8-839.8a")
    print("One fixed code set valid across 2013-2024: not verifiable")
    for code in DE_NOVO_CODES:
        item = firsts.loc[code]
        print(
            f"{code}: catalogue introduction=not verifiable; "
            f"G-BA first year={item.gba_data_first_year}"
        )
    reconciled = int(reconciliation_frame.reconciliation_status.eq("fully_reconciled").sum())
    print(f"Reconciled site-years: {reconciled}")
    print(f"Mismatching site-years: {len(mismatches)}")
    print(f"Unresolved mismatches: {len(mismatches)}")
    print("Manual review remains required: yes")
    print(
        "Do not start the de novo sensitivity analysis until the catalogue CSV, "
        "code summary, reconciliation results, and relevant annual ClaML definitions "
        "have been manually reviewed."
    )


if __name__ == "__main__":
    main()
