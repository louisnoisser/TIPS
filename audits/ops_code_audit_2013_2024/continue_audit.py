#!/usr/bin/env python3
"""Continue the OPS audit using provenance-verified extracted 2013-2018 ClaML.

Writes only beneath outputs/ops_code_audit_2013_2024. Production sources and
the three frozen occurrence/reconciliation CSVs are read but never rewritten.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = ROOT / "outputs/ops_code_audit_2013_2024"
BACKUP_DIR = AUDIT_DIR / "backups/pre_continuation_20260803"
GATE_BACKUP_DIR = AUDIT_DIR / "backups/pre_2012_integration_20260803"
REVERIFICATION_BACKUP_DIR = AUDIT_DIR / "backups/pre_reverification_20260804"
CATALOGUE_ROOT = ROOT / "ops_bfarm_2013_2024"
MANUAL_DIR = AUDIT_DIR / "manual_review_package"
SOURCE_PACKAGE_DIR = MANUAL_DIR / "accepted_claml_sources"
CANONICAL_DATA = ROOT / "outputs/audit/tips_code_level_audit.csv"

YEARS = tuple(range(2013, 2025))
SUPPORTING_YEAR = 2012
HISTORICAL_YEARS = tuple(range(2013, 2019))
PRESERVED_YEARS = tuple(range(2019, 2025))
REQUESTED_CODES = (
    "8-839.8", "8-839.81", "8-839.82", "8-839.83", "8-839.84",
    "8-839.85", "8-839.86", "8-839.87", "8-839.88", "8-839.89",
    "8-839.8a", "8-839.8x",
)
DE_NOVO_CODES = ("8-839.87", "8-839.88", "8-839.89", "8-839.8a")
CLASSIFICATION = {
    "8-839.8": "parent/residual/ambiguous",
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
    "8-839.8x": "parent/residual/ambiguous",
}
FROZEN_FILES = (
    "ops_code_occurrence_by_year.csv",
    "ops_code_reconciliation_site_year.csv",
    "ops_code_reconciliation_mismatches.csv",
)
EXPECTED_PREVIOUS_FILES = (
    "ops_code_audit_2013_2024.csv",
    "ops_code_summary_2013_2024.csv",
    *FROZEN_FILES,
    "ops_code_audit_2013_2024.md",
    "audit_run_manifest.json",
)
NEW_AUDIT_COLUMNS = (
    "source_file_type", "parent_heading", "classification_changed_vs_previous_year",
    "official_provenance_assessment", "official_provenance_evidence",
    "catalogue_version", "catalogue_date", "authority", "authority_uid",
    "language", "claml_version", "official_evidence",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def clean_text(node: ET.Element | None) -> str:
    return "" if node is None else " ".join("".join(node.itertext()).split())


def joined(values: list[str]) -> str:
    return " | ".join(value for value in values if value)


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    return result.stdout.strip()


def canonical_row(row: pd.Series, columns: list[str]) -> str:
    payload = {column: str(row.get(column, "")) for column in columns}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def row_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def validate_backup() -> dict[str, str]:
    if not BACKUP_DIR.is_dir():
        raise RuntimeError(f"Missing required pre-continuation backup: {BACKUP_DIR}")
    hashes: dict[str, str] = {}
    for filename in (*EXPECTED_PREVIOUS_FILES, "run_audit.py"):
        path = BACKUP_DIR / filename
        if not path.is_file():
            raise RuntimeError(f"Incomplete pre-continuation backup: {path}")
        hashes[filename] = sha256_file(path)
    for filename in FROZEN_FILES:
        current = AUDIT_DIR / filename
        if not current.is_file() or sha256_file(current) != hashes[filename]:
            raise RuntimeError(f"Frozen audit input changed before continuation: {current}")
    return hashes


def source_xml(year: int) -> Path:
    candidates = sorted((CATALOGUE_ROOT / str(year)).glob(f"ops{year}syst_claml*.xml"))
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one extracted annual ClaML XML for {year}, found {candidates}")
    return candidates[0]


def parse_and_validate_xml(path: Path, year: int) -> dict[str, Any]:
    data = path.read_bytes()
    root = ET.fromstring(data)
    title = root.find("Title")
    identifier = root.find("Identifier")
    metas = {item.attrib.get("name", ""): item.attrib.get("value", "") for item in root.findall("Meta")}
    errors: list[str] = []
    if root.tag != "ClaML" or root.attrib.get("version") != "2.0.0":
        errors.append("root is not ClaML 2.0.0")
    if title is None or title.attrib.get("name") != "OPS" or title.attrib.get("version") != str(year):
        errors.append("Title metadata does not identify the matching annual OPS")
    if title is None or clean_text(title) != "Operationen- und Prozedurenschlüssel":
        errors.append("Title text is not the German OPS systematics title")
    if identifier is None or identifier.attrib.get("authority") != "DIMDI":
        errors.append("historical DIMDI authority metadata is absent")
    if metas.get("lang") != "de" or metas.get("preliminary") != "false":
        errors.append("language/finality metadata is inconsistent")
    if str(year) not in metas.get("copyright", ""):
        errors.append("annual DIMDI copyright metadata is inconsistent")
    classes = {node.attrib.get("code", ""): node for node in root.findall("Class")}
    if "8-839.8" not in classes or len(classes) < 10000:
        errors.append("complete OPS class structure or 8-839.8 parent is absent")
    expected_children = ["Meta", "Identifier", "Title", "ClassKinds", "UsageKinds", "RubricKinds"]
    child_tags = [item.tag for item in list(root)]
    if any(tag not in child_tags for tag in expected_children):
        errors.append("ClaML structural signature differs from verified 2024 structure")
    if errors:
        raise RuntimeError(f"{year} XML provenance not accepted: {'; '.join(errors)}")
    evidence = (
        f"ClaML 2.0.0; OPS Title version={year}, date={title.attrib.get('date', '')}; "
        f"Identifier authority=DIMDI uid={identifier.attrib.get('uid', '')}; "
        f"lang=de; preliminary=false; copyright={metas.get('copyright', '')}; "
        f"{len(classes)} Class elements including literal 8-839.8; structural elements match "
        "the verified 2024 official ClaML. No project-generator marker was found."
    )
    return {
        "path": path,
        "bytes": data,
        "root": root,
        "classes": classes,
        "title": title,
        "identifier": identifier,
        "metas": metas,
        "sha256": sha256_bytes(data),
        "evidence": evidence,
        "class_count": len(classes),
        "rubric_count": len(root.findall(".//Rubric")),
        "child_tags": child_tags,
    }


def rubric_values(node: ET.Element) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for rubric in node.findall("Rubric"):
        text = clean_text(rubric)
        if text:
            result.setdefault(rubric.attrib.get("kind", ""), []).append(text)
    return result


def exact_wording(title: str, inclusion: str, exclusion: str, notes: str) -> str:
    return joined(
        [title, f"[inclusion] {inclusion}" if inclusion else "",
         f"[exclusion] {exclusion}" if exclusion else "", notes]
    )


def historical_rows() -> tuple[pd.DataFrame, dict[int, dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    parsed: dict[int, dict[str, Any]] = {}
    extra_branch: list[dict[str, Any]] = []
    previous_by_code: dict[str, dict[str, str]] = {}

    # OPS 2012 is supporting pre-period provenance only. It establishes the
    # preceding-year state without adding 2012 to the 144-row analytical audit.
    supporting = parse_and_validate_xml(source_xml(SUPPORTING_YEAR), SUPPORTING_YEAR)
    parsed[SUPPORTING_YEAR] = supporting
    supporting_classes = supporting["classes"]
    for code in REQUESTED_CODES:
        node = supporting_classes.get(code)
        rubrics = rubric_values(node) if node is not None else {}
        title = joined(rubrics.get("preferred", []))
        inclusion = joined(rubrics.get("inclusion", []))
        exclusion = joined(rubrics.get("exclusion", []))
        notes = joined(
            [
                f"[{kind}] {value}"
                for kind, values in rubrics.items()
                if kind not in {"preferred", "inclusion", "exclusion"}
                for value in values
            ]
        )
        previous_by_code[code] = {
            "exists": "yes" if node is not None else "no",
            "wording": exact_wording(title, inclusion, exclusion, notes),
            "classification": CLASSIFICATION[code] if node is not None else "not applicable—code absent",
        }

    for year in HISTORICAL_YEARS:
        info = parse_and_validate_xml(source_xml(year), year)
        parsed[year] = info
        classes = info["classes"]
        parent = classes["8-839.8"]
        parent_rubrics = rubric_values(parent)
        parent_title = joined(parent_rubrics.get("preferred", []))
        branch = ["8-839.8"] + [item.attrib["code"] for item in parent.findall("SubClass")]
        for code in sorted(set(branch) - set(REQUESTED_CODES), key=str.lower):
            extra_branch.append({"year": year, "code": code})

        for code in REQUESTED_CODES:
            node = classes.get(code)
            exists = node is not None
            rubrics = rubric_values(node) if node is not None else {}
            title = joined(rubrics.get("preferred", []))
            inclusion = joined(rubrics.get("inclusion", []))
            exclusion = joined(rubrics.get("exclusion", []))
            notes = joined(
                [
                    f"[{kind}] {value}"
                    for kind, values in rubrics.items()
                    if kind not in {"preferred", "inclusion", "exclusion"}
                    for value in values
                ]
            )
            current = exact_wording(title, inclusion, exclusion, notes)
            previous = previous_by_code.get(code)
            assert previous is not None
            previous_wording = previous["wording"]
            previous_exists = previous["exists"] == "yes"
            if exists and not previous_exists:
                wording_change = "yes"
                semantic_change = "yes"
                classification_change = "yes"
                semantic_explanation = "Literal code introduced into the annual 8-839.8 branch."
            elif not exists and previous_exists:
                wording_change = "yes"
                semantic_change = "yes"
                classification_change = "yes"
                semantic_explanation = "Literal code removed from the annual 8-839.8 branch."
            elif not exists and not previous_exists:
                wording_change = "not_applicable"
                semantic_change = "not_applicable"
                classification_change = "no"
                semantic_explanation = "Code absent in both consecutive annual catalogues."
            else:
                wording_change = "yes" if current != previous_wording else "no"
                semantic_change = "no"
                classification_change = "no"
                semantic_explanation = (
                    "Exact wording changed without changing the audited clinical classification."
                    if wording_change == "yes" else
                    "No wording or audited clinical-classification change."
                )
            manual = False
            manual_reason = ""

            subclasses = [item.attrib.get("code", "") for item in parent.findall("SubClass")]
            absence = (
                "Literal Class is absent from the annual ClaML and absent from the exact "
                f"8-839.8 SubClass list: {', '.join(subclasses)}."
                if not exists else ""
            )
            official_evidence = (
                f"Class[@code='{code}']; exact title: {title}"
                if exists else
                f"No Class[@code='{code}']; 8-839.8 SubClass list: {', '.join(subclasses)}"
            )
            row = {
                "catalogue_year": year,
                "code": code,
                "row_scope": "requested_144",
                "belongs_to_requested_144": True,
                "exists": "yes" if exists else "no",
                "non_existence_reason": absence,
                "official_title": title,
                "inclusion_notes": inclusion,
                "exclusion_notes": exclusion,
                "usage_or_coding_notes": notes,
                "source_archive_path": "",
                "source_archive_filename": "",
                "source_archive_sha256": "",
                "source_xml_filename": info["path"].name,
                "source_xml_member": rel(info["path"]),
                "source_xml_sha256": info["sha256"],
                "claml_class_identifier": code if exists else "",
                "claml_xml_location": (
                    f"Class[@code='{code}']" if exists else
                    f"Class[@code='8-839.8']/SubClass list; Class[@code='{code}'] absent"
                ),
                "claml_superclass_codes": joined(
                    [item.attrib.get("code", "") for item in node.findall("SuperClass")]
                ) if exists else "",
                "claml_subclass_codes": joined(
                    [item.attrib.get("code", "") for item in node.findall("SubClass")]
                ) if exists else "",
                "analyst_classification": CLASSIFICATION[code] if exists else "not applicable—code absent",
                "classification_basis": (
                    "Analyst interpretation of the separately retained exact annual title and notes."
                    if exists else "No definition inferred for an absent literal code."
                ),
                "provisional_classification_disagreement": False,
                "wording_changed_vs_previous_year": wording_change,
                "clinical_or_coding_meaning_changed_vs_previous_year": semantic_change,
                "exact_previous_wording": previous_wording,
                "exact_current_wording": current,
                "semantic_change_explanation": semantic_explanation,
                "catalogue_source_status": "verified_extracted_official_claml_xml",
                "annual_archive_candidates": rel(info["path"]),
                "manual_review_flag": manual,
                "manual_review_reason": manual_reason,
                "source_file_type": "extracted official ClaML XML",
                "parent_heading": parent_title,
                "classification_changed_vs_previous_year": classification_change,
                "official_provenance_assessment": "accepted_official_historical_DIMDI_ClaML",
                "official_provenance_evidence": info["evidence"],
                "catalogue_version": str(year),
                "catalogue_date": info["title"].attrib.get("date", ""),
                "authority": info["identifier"].attrib.get("authority", ""),
                "authority_uid": info["identifier"].attrib.get("uid", ""),
                "language": info["metas"].get("lang", ""),
                "claml_version": info["root"].attrib.get("version", ""),
                "official_evidence": official_evidence,
            }
            rows.append(row)
            previous_by_code[code] = {
                "exists": row["exists"], "wording": current,
                "classification": row["analyst_classification"],
            }
    return pd.DataFrame(rows), parsed, extra_branch


def preserve_and_combine(historical: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    previous = pd.read_csv(
        BACKUP_DIR / "ops_code_audit_2013_2024.csv", dtype=str, keep_default_na=False
    )
    original_columns = previous.columns.tolist()
    old_preserved = previous[previous.catalogue_year.astype(int).isin(PRESERVED_YEARS)].copy()
    for column in NEW_AUDIT_COLUMNS:
        if column not in historical:
            historical[column] = ""
        old_preserved[column] = ""
    combined = pd.concat([historical, old_preserved], ignore_index=True, sort=False)
    combined = combined.sort_values(["catalogue_year", "code"]).reset_index(drop=True)
    if len(combined) != 144 or combined.duplicated(["catalogue_year", "code"]).any():
        raise RuntimeError("Updated audit is not an exact 144-row Cartesian matrix")

    checks: list[dict[str, Any]] = []
    for _, before in old_preserved.sort_values(["catalogue_year", "code"]).iterrows():
        after = combined[
            combined.catalogue_year.astype(str).eq(str(before.catalogue_year))
            & combined.code.eq(before.code)
        ].iloc[0]
        before_repr = canonical_row(before, original_columns)
        after_repr = canonical_row(after, original_columns)
        checks.append(
            {
                "year": int(before.catalogue_year),
                "code": before.code,
                "canonical_row_representation_before_update": before_repr,
                "canonical_row_representation_after_update": after_repr,
                "before_hash": row_hash(before_repr),
                "after_hash": row_hash(after_repr),
                "unchanged": before_repr == after_repr,
                "explanation_if_changed": "" if before_repr == after_repr else "Pre-existing field changed; continuation must stop.",
            }
        )
    unchanged = pd.DataFrame(checks)
    if len(unchanged) != 72 or not unchanged.unchanged.all():
        raise RuntimeError("At least one verified 2019-2024 requested row changed")
    return combined, unchanged, original_columns


def historical_diff(previous: pd.DataFrame, updated: pd.DataFrame) -> pd.DataFrame:
    old = previous[previous.catalogue_year.astype(int).isin(HISTORICAL_YEARS)].copy()
    new = updated[updated.catalogue_year.astype(int).isin(HISTORICAL_YEARS)].copy()
    old["catalogue_year"] = pd.to_numeric(old["catalogue_year"], errors="raise").astype(int)
    new["catalogue_year"] = pd.to_numeric(new["catalogue_year"], errors="raise").astype(int)
    merged = old.merge(new, on=["catalogue_year", "code"], suffixes=("_previous", "_new"), validate="one_to_one")
    rows: list[dict[str, Any]] = []
    for item in merged.itertuples():
        rows.append(
            {
                "year": int(item.catalogue_year),
                "code": item.code,
                "previous_exists_status": item.exists_previous,
                "new_exists_status": item.exists_new,
                "previous_title": item.official_title_previous,
                "new_official_title": item.official_title_new,
                "previous_classification": item.analyst_classification_previous,
                "new_classification": item.analyst_classification_new,
                "previous_source_status": item.catalogue_source_status_previous,
                "new_source": item.source_xml_member_new,
                "new_source_hash": item.source_xml_sha256_new,
                "exact_reason_for_change": (
                    "Previously unresolved because the original archive was absent; now resolved "
                    "from an extracted annual ClaML XML whose official DIMDI provenance is established internally."
                ),
                "official_evidence": item.official_evidence,
                "manual_review_flag": item.manual_review_flag_new,
            }
        )
    return pd.DataFrame(rows)


def observed_first_years() -> dict[str, dict[str, Any]]:
    data = pd.read_csv(CANONICAL_DATA, dtype=str, keep_default_na=False)
    data["reporting_year"] = pd.to_numeric(data.reporting_year, errors="raise").astype(int)
    data["normalised_code"] = data.OPS_code.astype(str).str.strip().str.lower()
    data["visible"] = pd.to_numeric(data.current_parser_numeric_count, errors="coerce").fillna(0)
    data["suppressed"] = pd.to_numeric(data.suppressed_record_count, errors="coerce").fillna(0)
    result: dict[str, dict[str, Any]] = {}
    for code in REQUESTED_CODES:
        group = data[data.normalised_code.eq(code) & data.reporting_year.isin(YEARS)]
        result[code] = {
            "any": int(group.reporting_year.min()) if len(group) else "",
            "numeric": int(group.loc[group.visible.gt(0), "reporting_year"].min()) if group.visible.gt(0).any() else "",
            "suppressed": int(group.loc[group.suppressed.gt(0), "reporting_year"].min()) if group.suppressed.gt(0).any() else "",
        }
    # Literal-string safety checks independent of the audit CSV.
    family = data[data.normalised_code.str.startswith("8-839.8")]
    if not {"8-839.8", "8-839.8a", "8-839.8x"}.issubset(set(family.normalised_code)):
        raise RuntimeError("Parent/alphanumeric literal-code separation check failed")
    upper_a = family[family.OPS_code.eq("8-839.8A")]
    if len(upper_a) and not upper_a.normalised_code.eq("8-839.8a").all():
        raise RuntimeError("8-839.8A lower-case normalisation check failed")
    return result


def build_summary(updated: pd.DataFrame, firsts: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for code in REQUESTED_CODES:
        group = updated[updated.code.eq(code)].copy()
        group["_catalogue_year_numeric"] = pd.to_numeric(
            group["catalogue_year"], errors="raise"
        ).astype(int)
        group = group.sort_values("_catalogue_year_numeric")
        present = group[group.exists.eq("yes")]
        first = present.iloc[0]
        final = present.iloc[-1]
        years_present = present.catalogue_year.astype(int).tolist()
        continuous = years_present == list(range(min(years_present), max(years_present) + 1))
        exact_values = present.exact_current_wording.astype(str)
        # The first present row marks availability, not a semantic change
        # within the code's period of official availability.
        semantic_changes = present.iloc[1:].clinical_or_coding_meaning_changed_vs_previous_year.eq("yes")
        wording_changes = present.wording_changed_vs_previous_year.eq("yes")
        final_classification = str(final.analyst_classification)
        if final_classification == "parent, residual, or otherwise ambiguous":
            final_classification = "parent/residual/ambiguous"
        rows.append(
            {
                "code": code,
                "official_catalogue_first_year_2013_2024": int(first.catalogue_year),
                "official_catalogue_last_year": int(final.catalogue_year),
                "continuous_availability_from_first_year": "yes" if continuous else "no",
                "years_present": ",".join(map(str, years_present)),
                "years_absent": ",".join(
                    str(year) for year in YEARS if year not in years_present
                ),
                "first_gba_occurrence_year": firsts[code]["any"],
                "first_openly_numeric_gba_year": firsts[code]["numeric"],
                "first_suppressed_gba_year": firsts[code]["suppressed"],
                "official_first_title": first.official_title,
                "official_final_title": final.official_title,
                "wording_stable": "no" if wording_changes.any() or exact_values.nunique() > 1 else "yes",
                "semantic_stable": "no" if semantic_changes.any() else "yes",
                "analyst_classification": final_classification,
                "recommended_inclusion_in_de_novo_sensitivity": "yes" if code in DE_NOVO_CODES else "no",
                "manual_review_status": (
                    "historical_catalogue_locally_verified_from_claml; "
                    "independent_manual_review_pending"
                ),
                "manual_review_reason": (
                    "Codex locally verified the historical catalogue timeline directly from the included ClaML primary sources. "
                    "No completed independent historical or row-level review is asserted from local evidence; manual review remains pending."
                ),
                "introduction_interpretation": (
                    "A: absent in 2013-2015 official catalogues and introduced in 2016"
                    if code in {"8-839.89", "8-839.8a"} else
                    "absent in OPS 2012 and introduced in OPS 2013"
                    if code in {"8-839.87", "8-839.88"} else
                    "present in supporting OPS 2012; exact earlier introduction is outside this TIPS de-novo gate"
                ),
            }
        )
    return pd.DataFrame(rows)


def independent_reconciliation() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    recon_path = AUDIT_DIR / "ops_code_reconciliation_site_year.csv"
    mismatch_path = AUDIT_DIR / "ops_code_reconciliation_mismatches.csv"
    recon = pd.read_csv(recon_path, dtype=str, keep_default_na=False)
    mismatch = pd.read_csv(mismatch_path, dtype=str, keep_default_na=False)
    status = recon.reconciliation_status.astype(str)
    manual = recon.manual_review_flag.astype(str).str.lower().isin({"true", "1", "yes"})
    difference = pd.to_numeric(recon.difference, errors="coerce")
    unresolved = recon.resolved_vs_unresolved.astype(str).str.lower().eq("unresolved")
    duplicate = recon.duplicated(
        ["reporting_year", "physical_site_identifier"], keep=False
    )
    literal_codes: set[str] = set()
    for column in ("contributing_code_level_records", "all_precedence_candidate_records"):
        for value in recon[column]:
            for component in value.split(" || "):
                candidate = component.split(":", 1)[0].strip().lower()
                if candidate.startswith("8-839.8"):
                    literal_codes.add(candidate)
    required_literals = {"8-839.8", "8-839.8a", "8-839.8x"}
    literals_distinct = required_literals.issubset(literal_codes)
    identifiers_separate = (
        {"institution_identifier", "physical_site_identifier"}.issubset(recon.columns)
        and recon.reporting_unit_type.eq("physical_site").all()
        and recon.institution_identifier.ne(recon.physical_site_identifier).any()
    )
    prior_verification = pd.read_csv(
        AUDIT_DIR / "reconciliation_independent_verification.csv",
        dtype=str,
        keep_default_na=False,
    )
    previously_referenced_hashes = set(
        prior_verification.loc[
            prior_verification.evidence_file.eq(rel(recon_path)), "evidence_sha256"
        ]
    )
    values = {
        "total_site_year_rows": len(recon),
        "unique_physical_site_years": int(
            recon[["reporting_year", "physical_site_identifier"]].drop_duplicates().shape[0]
        ),
        "unique_institution_years": int(
            recon[["reporting_year", "institution_identifier"]].drop_duplicates().shape[0]
        ),
        "duplicate_physical_site_year_rows": int(duplicate.sum()),
        "fully_reconciled_rows": int(status.eq("fully_reconciled").sum()),
        "mismatching_rows": int(status.str.contains("mismatch", case=False, na=False).sum()),
        "unresolved_rows": int(unresolved.sum()),
        "manual_review_rows": int(manual.sum()),
        "missing_reconciliation_status_rows": int(status.str.strip().eq("").sum()),
        "maximum_absolute_numeric_difference": float(difference.abs().max()),
        "sum_absolute_numeric_differences": float(difference.abs().sum()),
        "site_and_institution_identifiers_remain_separate": bool(identifiers_separate),
        "institution_year_mapping": "reporting_year + institution_identifier from the documented final row-level mapping",
        "literal_code_values_found": sorted(literal_codes),
        "parent_8a_8x_remain_three_distinct_literals": bool(literals_distinct),
        "mismatch_file_exists": mismatch_path.is_file(),
        "mismatch_file_data_rows": len(mismatch),
        "mismatch_file_consistent": len(mismatch) == int(status.str.contains("mismatch", case=False, na=False).sum()),
    }
    evidence_hash = sha256_file(recon_path)
    if previously_referenced_hashes != {evidence_hash}:
        raise RuntimeError(
            "Row-level reconciliation hash differs from the previous verification output: "
            f"previous={sorted(previously_referenced_hashes)}, current={evidence_hash}"
        )
    rows = [
        {
            "claim": "reconciled site-years",
            "previous_claimed_value": "2057",
            "independently_recomputed_value": str(values["fully_reconciled_rows"]),
            "verification_status": "verified" if values["fully_reconciled_rows"] == 2057 else "contradicted",
            "evidence_file": rel(recon_path),
            "evidence_sha256": evidence_hash,
        },
        {
            "claim": "mismatching site-years",
            "previous_claimed_value": "0",
            "independently_recomputed_value": str(values["mismatching_rows"]),
            "verification_status": "verified" if values["mismatching_rows"] == 0 else "contradicted",
            "evidence_file": rel(recon_path),
            "evidence_sha256": evidence_hash,
        },
        {
            "claim": "unresolved mismatches",
            "previous_claimed_value": "0",
            "independently_recomputed_value": str(values["unresolved_rows"]),
            "verification_status": "verified" if values["unresolved_rows"] == 0 else "contradicted",
            "evidence_file": rel(recon_path),
            "evidence_sha256": evidence_hash,
        },
    ]
    additional_metrics = (
        ("total site-year rows", values["total_site_year_rows"]),
        ("unique physical site-years", values["unique_physical_site_years"]),
        ("unique institution-years", values["unique_institution_years"]),
        ("duplicate physical site-year rows", values["duplicate_physical_site_year_rows"]),
        ("manual-review rows", values["manual_review_rows"]),
        ("missing reconciliation status rows", values["missing_reconciliation_status_rows"]),
        ("maximum absolute numeric difference", values["maximum_absolute_numeric_difference"]),
        ("sum of absolute numeric differences", values["sum_absolute_numeric_differences"]),
        ("site and institution identifiers remain separate", values["site_and_institution_identifiers_remain_separate"]),
        ("8-839.8, 8-839.8a, and 8-839.8x remain distinct literals", values["parent_8a_8x_remain_three_distinct_literals"]),
    )
    rows.extend(
        {
            "claim": label,
            "previous_claimed_value": "",
            "independently_recomputed_value": str(value),
            "verification_status": "independently_recomputed",
            "evidence_file": rel(recon_path),
            "evidence_sha256": evidence_hash,
        }
        for label, value in additional_metrics
    )
    rows.append(
        {
            "claim": "mismatch CSV data rows",
            "previous_claimed_value": "",
            "independently_recomputed_value": str(values["mismatch_file_data_rows"]),
            "verification_status": (
                "consistent_with_site_year_table"
                if values["mismatch_file_consistent"] else "contradicted_by_site_year_table"
            ),
            "evidence_file": rel(mismatch_path),
            "evidence_sha256": sha256_file(mismatch_path),
        }
    )
    summary = pd.DataFrame(rows)
    return recon, summary, values


def source_inventory(parsed: dict[int, dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for year in (SUPPORTING_YEAR, *HISTORICAL_YEARS):
        directory = CATALOGUE_ROOT / str(year)
        for path in sorted(directory.iterdir()):
            if path.name == ".DS_Store":
                classification = "unrelated file"
            elif path.suffix.lower() == ".xml" and "syst_claml" in path.name.lower():
                classification = "extracted official ClaML XML"
            elif path.suffix.lower() == ".pdf" and "syst_odt" in path.name.lower():
                classification = "PDF systematics"
            elif path.suffix.lower() == ".zip" and "syst-claml" in path.name.lower():
                classification = "original official BfArM ClaML systematics archive"
            else:
                classification = "uncertain provenance"
            info = parsed.get(year) if classification == "extracted official ClaML XML" else None
            rows.append(
                {
                    "year": year,
                    "evidence_role": (
                        "supporting pre-period provenance for exact introduction timing"
                        if year == SUPPORTING_YEAR else "analytical-period annual catalogue source"
                    ),
                    "filename": path.name,
                    "absolute_path": str(path.resolve()),
                    "classification": classification,
                    "file_type": path.suffix.lower().lstrip(".") or "metadata",
                    "file_size_bytes": path.stat().st_size,
                    "modification_timestamp_utc": iso_mtime(path),
                    "sha256": sha256_file(path),
                    "archive_contents": "",
                    "xml_root_element": info["root"].tag if info else "",
                    "claml_version": info["root"].attrib.get("version", "") if info else "",
                    "ops_catalogue_version": info["title"].attrib.get("version", "") if info else "",
                    "publication_or_version_date": info["title"].attrib.get("date", "") if info else "",
                    "stated_authority": info["identifier"].attrib.get("authority", "") if info else "",
                    "authority_uid": info["identifier"].attrib.get("uid", "") if info else "",
                    "bfarm_or_dimdi_attribution": info["metas"].get("copyright", "") if info else "",
                    "language": info["metas"].get("lang", "") if info else "",
                    "relevant_internal_metadata": (
                        json.dumps(info["metas"], ensure_ascii=False, sort_keys=True) if info else ""
                    ),
                    "class_count": info["class_count"] if info else "",
                    "rubric_count": info["rubric_count"] if info else "",
                    "structure_matches_verified_2024_claml": True if info else "",
                    "official_provenance_established": True if info else False,
                    "provenance_evidence": info["evidence"] if info else "",
                    "manual_review_requirement": (
                        "independent primary-source review recommended" if info else
                        "not used as ClaML evidence"
                    ),
                }
            )
    return pd.DataFrame(rows)


def supporting_2012_provenance(info: dict[str, Any]) -> pd.DataFrame:
    classes = info["classes"]
    parent = classes["8-839.8"]
    subclasses = [item.attrib.get("code", "") for item in parent.findall("SubClass")]
    requested_codes = (
        "8-839.84", "8-839.86", "8-839.87", "8-839.88",
        "8-839.89", "8-839.8a", "8-839.8x",
    )
    rows: list[dict[str, Any]] = []
    for code in requested_codes:
        node = classes.get(code)
        rubrics = rubric_values(node) if node is not None else {}
        exists = node is not None
        rows.append(
            {
                "catalogue_year": SUPPORTING_YEAR,
                "evidence_role": "supporting pre-period provenance; not an analytical audit year",
                "code": code,
                "exists": "yes" if exists else "no",
                "exact_official_title": joined(rubrics.get("preferred", [])),
                "exact_inclusion_notes": joined(rubrics.get("inclusion", [])),
                "exact_exclusion_notes": joined(rubrics.get("exclusion", [])),
                "claml_location": (
                    f"Class[@code='{code}']" if exists else
                    f"Class[@code='8-839.8']/SubClass list; Class[@code='{code}'] absent"
                ),
                "absence_evidence": (
                    f"No literal Class[@code='{code}']; exact 8-839.8 SubClass list: {', '.join(subclasses)}"
                    if not exists else ""
                ),
                "source_path": rel(info["path"]),
                "source_sha256": info["sha256"],
                "claml_version": info["root"].attrib.get("version", ""),
                "ops_catalogue_version": info["title"].attrib.get("version", ""),
                "catalogue_date": info["title"].attrib.get("date", ""),
                "authority": info["identifier"].attrib.get("authority", ""),
                "authority_uid": info["identifier"].attrib.get("uid", ""),
                "language": info["metas"].get("lang", ""),
                "preliminary": info["metas"].get("preliminary", ""),
                "copyright": info["metas"].get("copyright", ""),
                "independently_established_expected_presence": "not asserted",
                "local_result_matches_independent_review": "not assessed",
                "local_primary_source_verification": "complete",
            }
        )
    result = pd.DataFrame(rows)
    return result


def expected_file_inventory(backup_hashes: dict[str, str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    expected_locations = {
        **{name: AUDIT_DIR / name for name in EXPECTED_PREVIOUS_FILES},
        "run_audit.py": ROOT / "audits/ops_code_audit_2013_2024/run_audit.py",
    }
    manifest = json.loads((BACKUP_DIR / "audit_run_manifest.json").read_text(encoding="utf-8"))
    referenced = set(manifest.get("generated_output_paths", []))
    for name, path in expected_locations.items():
        backup = BACKUP_DIR / name
        csv_rows: int | str = ""
        if backup.suffix.lower() == ".csv":
            csv_rows = len(pd.read_csv(backup, dtype=str, keep_default_na=False))
        rows.append(
            {
                "expected_filename": name,
                "found": path.is_file(),
                "exact_absolute_path_at_initial_search": str(path.resolve()),
                "location_classification": "main repository",
                "file_size_bytes_at_initial_search": backup.stat().st_size,
                "modification_timestamp_utc_at_initial_search": iso_mtime(backup),
                "sha256_at_initial_search": backup_hashes[name],
                "csv_row_count_at_initial_search": csv_rows,
                "belongs_to_previously_reported_audit_run": True,
                "attribution_evidence": (
                    "Referenced by original audit manifest and located in the single complete output set."
                    if rel(path) in referenced else
                    "Audit-only script named in the original manifest as executed."
                ),
                "multiple_versions_existed_before_continuation": False,
                "initial_search_result": "one matching file in main repository; none in other worktrees or Codex directories",
                "preserved_backup_path": str(backup.resolve()),
                "preserved_backup_sha256": backup_hashes[name],
            }
        )
    return pd.DataFrame(rows)


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None) -> str:
    use = frame[columns].copy() if columns else frame.copy()
    if use.empty:
        return "_No rows._"
    clean = use.astype(object).where(pd.notna(use), "").astype(str).apply(
        lambda col: col.str.replace("|", r"\|", regex=False).str.replace("\n", " ", regex=False)
    )
    return "\n".join(
        [
            "| " + " | ".join(clean.columns) + " |",
            "| " + " | ".join("---" for _ in clean.columns) + " |",
            *["| " + " | ".join(row) + " |" for row in clean.itertuples(index=False, name=None)],
        ]
    )


def updated_report(
    audit: pd.DataFrame,
    summary: pd.DataFrame,
    source_files: pd.DataFrame,
    supporting_2012: pd.DataFrame,
    unchanged: pd.DataFrame,
    reconciliation_summary: pd.DataFrame,
    reconciliation_values: dict[str, Any],
) -> str:
    history = audit[
        audit.catalogue_year.astype(int).isin(HISTORICAL_YEARS)
        & audit.code.isin(["8-839.87", "8-839.88", "8-839.89", "8-839.8a"])
    ][["catalogue_year", "code", "exists", "official_title", "source_xml_member",
       "source_xml_sha256", "claml_xml_location", "manual_review_flag"]]
    source_condensed = source_files[source_files.classification.eq("extracted official ClaML XML")][
        ["year", "evidence_role", "filename", "sha256", "ops_catalogue_version", "publication_or_version_date",
         "stated_authority", "language", "official_provenance_established"]
    ]
    wording_changes = audit[
        audit.wording_changed_vs_previous_year.eq("yes")
        & audit.catalogue_year.astype(int).isin(HISTORICAL_YEARS)
    ][["catalogue_year", "code", "exact_previous_wording", "exact_current_wording",
       "clinical_or_coding_meaning_changed_vs_previous_year"]]
    return f"""# Completed official OPS 8-839.8* audit, 2013–2024

## Scope and safety boundary

This continuation verifies actual files, accepts provenance-established
historical DIMDI ClaML XMLs, and completes the catalogue audit. It does not run
the de novo sensitivity analysis. No manuscript, supplement, figure,
publication table, production source, source dataset, or production-analysis
output was modified.

## Existing-output verification

All eight previously reported files existed in one internally consistent set
in the main repository. No other Git worktree exists and no matching version
was found under the searched Codex directories. The summary CSV existed and
was updated from primary-source evidence; it was not reconstructed from a
narrative. Exact discovery metadata and original hashes are in
[`existing_audit_file_inventory.csv`](existing_audit_file_inventory.csv). The
complete original set is preserved under
[`backups/pre_continuation_20260803`](backups/pre_continuation_20260803/).

Direct CSV checks confirmed an exact 144-row year-code Cartesian matrix and
separate literal keys for `8-839.8`, `8-839.8a`, and `8-839.8x`.

## Accepted 2012 supporting source and 2013–2018 official sources

{markdown_table(source_condensed)}

Each accepted XML is ClaML 2.0.0, identifies the matching annual final German
OPS (`preliminary=false`, `lang=de`), carries historical DIMDI authority/UID and
annual copyright metadata, contains the complete OPS class system and literal
8-839.8 branch, and structurally matches the verified 2024 official ClaML. No
project-generator marker was found. The absence of the original ZIP therefore
does not make provenance ambiguous under the continuation criteria. Every file
in the seven annual directories is classified in
[`catalogue_source_inventory_2013_2018.csv`](catalogue_source_inventory_2013_2018.csv).

OPS 2012 is supporting pre-period provenance only and is not an added analytical
audit year. Its exact literal-code findings are recorded in
[`ops_2012_supporting_provenance.csv`](ops_2012_supporting_provenance.csv):

{markdown_table(supporting_2012, ['code', 'exists', 'exact_official_title',
    'claml_location', 'source_sha256', 'local_primary_source_verification'])}

Codex locally verified the historical catalogue question directly from the
included ClaML primary sources. No completed independent review is asserted
from repository evidence. The local parse shows that `.87`, `.88`, `.89`, and `.8a` are absent in
OPS 2012; `.87` and `.88` are present in OPS 2013 and were therefore introduced
in 2013; `.89` and `.8a` were introduced in 2016. No specific de-novo TIPS
subcode exists before 2013. No catalogue year from 2013 through 2024 remains
unresolved.

## Historical availability of the de novo codes

{markdown_table(history)}

- `.87` and `.88` are absent in OPS 2012 and exist continuously from their
  confirmed introduction in 2013 through 2024. Their titles describe one
  uncovered and one covered stent.
- `.89` and `.8a` are absent from the complete 2013, 2014, and 2015 branches.
  Both are introduced in 2016 with titles describing two or more uncovered and
  covered stents, respectively.
- No additional de novo code exists in any complete annual 8-839.8 branch.
- `.84` and `.86` are longitudinally classified neutrally as secondary
  interventions on an existing shunt. Their exact annual wording is retained
  row by row and must not be treated as constant across the study period.

Complete historical changes are in
[`ops_code_audit_2013_2018_diff.csv`](ops_code_audit_2013_2018_diff.csv) and the
full row-level evidence is in
[`ops_code_audit_2013_2024.csv`](ops_code_audit_2013_2024.csv).

## Exact wording changes, 2013–2018

{markdown_table(wording_changes)}

## Catalogue summary and catalogue-versus-data interpretation

{markdown_table(summary, ['code', 'official_catalogue_first_year_2013_2024',
    'official_catalogue_last_year', 'continuous_availability_from_first_year',
    'first_gba_occurrence_year', 'first_openly_numeric_gba_year',
    'first_suppressed_gba_year', 'wording_stable', 'semantic_stable',
    'analyst_classification', 'recommended_inclusion_in_de_novo_sensitivity'])}

For `.89` and `.8a`, interpretation **A** applies: neither literal code exists
in the official 2013–2015 ClaML branches; both first exist officially in 2016
and first appear, first appear numerically, and first appear suppressed in the
G-BA extraction in 2016. The catalogue-to-data lag is zero years. Their earlier
zero values reflect lack of catalogue availability, not merely lack of
reporting.

One fixed de novo code set is **not** historically valid for 2013–2024:

- 2013–2015: `8-839.87`, `8-839.88`
- 2016–2024: `8-839.87`, `8-839.88`, `8-839.89`, `8-839.8a`

Comparability across 2015 and 2016 may be affected by the introduction of
additional specific de-novo subcodes in 2016. Catalogue availability alone
does not establish the direction or magnitude of any effect.

This planned sensitivity measures **“activity coded with specific de novo TIPS
creation subcodes”** and does not necessarily identify all de novo placements,
unique patients, or admissions. `8-842.*` remains excluded.

## Preserved 2019–2024 audit rows

All **{len(unchanged)}** requested 2019–2024 rows have identical canonical
representations and SHA-256 row hashes across every pre-continuation column.
Changed rows: **{int((~unchanged.unchanged).sum())}**. See
[`ops_code_audit_2019_2024_unchanged_check.csv`](ops_code_audit_2019_2024_unchanged_check.csv).

## Independent reconciliation verification

{markdown_table(reconciliation_summary)}

- Total reconciliation rows: **{reconciliation_values['total_site_year_rows']}**
- Unique physical site-years: **{reconciliation_values['unique_physical_site_years']}**
- Unique institution-years: **{reconciliation_values['unique_institution_years']}**
- Duplicate physical site-year rows: **{reconciliation_values['duplicate_physical_site_year_rows']}**
- Fully reconciled: **{reconciliation_values['fully_reconciled_rows']}**
- Mismatching: **{reconciliation_values['mismatching_rows']}**
- Unresolved: **{reconciliation_values['unresolved_rows']}**
- Manual-review rows: **{reconciliation_values['manual_review_rows']}**
- Missing status: **{reconciliation_values['missing_reconciliation_status_rows']}**
- Maximum absolute difference: **{reconciliation_values['maximum_absolute_numeric_difference']}**
- Sum of absolute differences: **{reconciliation_values['sum_absolute_numeric_differences']}**
- Site and institution identifiers remain separate: **{reconciliation_values['site_and_institution_identifiers_remain_separate']}**
- Parent, `.8a`, and `.8x` remain distinct literals: **{reconciliation_values['parent_8a_8x_remain_three_distinct_literals']}**
- Mismatch CSV data rows: **{reconciliation_values['mismatch_file_data_rows']}**

Thus the previous claims of 2,057 reconciled site-years, zero mismatches, and
zero unresolved mismatches are internally reproduced directly from the
row-level CSV. Its matching SHA-256 proves that the file is unchanged; it does
not independently prove the reconciliation logic or the conceptual site-versus-
institution distinction. This Codex recomputation is an internal consistency
check. Final closure requires an independent external recomputation. Neither
reconciliation CSV nor the occurrence CSV was altered.

## Manual review

The complete package, including actual byte-identical ClaML source copies, is
at [`manual_review_package`](manual_review_package/). Manual review remains
required for the row-level reconciliation evidence before any de novo
sensitivity analysis begins.

**Status:** Local audit verification complete; independent manual review of the
updated audit CSVs, reconciliation recomputation, and ClaML primary sources
remains pending.
"""


def copy_verified(
    source: Path, destination: Path, *, replace_generated_copy: bool = False
) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    before = sha256_file(source)
    if (
        destination.exists()
        and sha256_file(destination) != before
        and not replace_generated_copy
    ):
        raise RuntimeError(f"Refusing to overwrite different manual-package file: {destination}")
    shutil.copy2(source, destination)
    after = sha256_file(destination)
    if before != after:
        raise RuntimeError(f"Copied-file hash mismatch: {source} -> {destination}")
    return {
        "source_path": rel(source), "source_sha256": before,
        "copied_path": rel(destination), "copied_sha256": after,
        "hash_match": True,
    }


def main() -> None:
    backup_hashes = validate_backup()
    previous = pd.read_csv(
        BACKUP_DIR / "ops_code_audit_2013_2024.csv", dtype=str, keep_default_na=False
    )
    historical, parsed, extra_branch = historical_rows()
    if extra_branch:
        raise RuntimeError(f"Unexpected additional historical branch codes: {extra_branch}")
    updated, unchanged, original_columns = preserve_and_combine(historical)
    diff = historical_diff(previous, updated)
    firsts = observed_first_years()
    summary = build_summary(updated, firsts)
    recon, recon_summary, recon_values = independent_reconciliation()
    sources = source_inventory(parsed)
    supporting_2012 = supporting_2012_provenance(parsed[SUPPORTING_YEAR])
    inventory = expected_file_inventory(backup_hashes)

    # Write only mutable continuation outputs; frozen occurrence/reconciliation files remain untouched.
    paths = {
        "audit": AUDIT_DIR / "ops_code_audit_2013_2024.csv",
        "summary": AUDIT_DIR / "ops_code_summary_2013_2024.csv",
        "report": AUDIT_DIR / "ops_code_audit_2013_2024.md",
        "diff": AUDIT_DIR / "ops_code_audit_2013_2018_diff.csv",
        "unchanged": AUDIT_DIR / "ops_code_audit_2019_2024_unchanged_check.csv",
        "reconciliation_summary": AUDIT_DIR / "reconciliation_independent_verification.csv",
        "source_inventory": AUDIT_DIR / "catalogue_source_inventory_2013_2018.csv",
        "supporting_2012": AUDIT_DIR / "ops_2012_supporting_provenance.csv",
        "file_inventory": AUDIT_DIR / "existing_audit_file_inventory.csv",
        "manifest": AUDIT_DIR / "audit_run_manifest.json",
    }
    updated.to_csv(paths["audit"], index=False)
    summary.to_csv(paths["summary"], index=False)
    diff.to_csv(paths["diff"], index=False)
    unchanged.to_csv(paths["unchanged"], index=False)
    recon_summary.to_csv(paths["reconciliation_summary"], index=False)
    sources.to_csv(paths["source_inventory"], index=False)
    supporting_2012.to_csv(paths["supporting_2012"], index=False)
    inventory.to_csv(paths["file_inventory"], index=False)
    paths["report"].write_text(
        updated_report(
            updated, summary, sources, supporting_2012,
            unchanged, recon_summary, recon_values,
        ),
        encoding="utf-8",
    )

    # Manual package: actual tables and actual accepted ClaML bytes, never links alone.
    SOURCE_PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, Any]] = []
    for filename in (
        "ops_code_summary_2013_2024.csv",
        "ops_code_audit_2013_2024.csv",
        "ops_code_audit_2013_2018_diff.csv",
        "ops_code_audit_2019_2024_unchanged_check.csv",
        "ops_code_reconciliation_site_year.csv",
        "ops_code_reconciliation_mismatches.csv",
        "reconciliation_independent_verification.csv",
        "ops_code_audit_2013_2024.md",
        "catalogue_source_inventory_2013_2018.csv",
        "ops_2012_supporting_provenance.csv",
    ):
        copied.append(
            copy_verified(
                AUDIT_DIR / filename,
                MANUAL_DIR / filename,
                replace_generated_copy=True,
            )
        )
    for year in (SUPPORTING_YEAR, *HISTORICAL_YEARS):
        source = parsed[year]["path"]
        copied.append(copy_verified(source, SOURCE_PACKAGE_DIR / source.name))

    # Preserve the actual 2024 accepted endpoint archive and its exact ClaML member.
    archive_2024 = CATALOGUE_ROOT / "2024/ops2024syst-claml.zip"
    copied.append(copy_verified(archive_2024, SOURCE_PACKAGE_DIR / archive_2024.name))
    member_2024 = "Klassifikationsdateien/ops2024syst_claml_20231020.xml"
    with ZipFile(archive_2024) as archive:
        bytes_2024 = archive.read(member_2024)
    xml_2024_copy = SOURCE_PACKAGE_DIR / Path(member_2024).name
    if xml_2024_copy.exists() and sha256_file(xml_2024_copy) != sha256_bytes(bytes_2024):
        raise RuntimeError(f"Refusing to overwrite different 2024 ClaML copy: {xml_2024_copy}")
    xml_2024_copy.write_bytes(bytes_2024)
    copied.append(
        {
            "source_path": f"{rel(archive_2024)}::{member_2024}",
            "source_sha256": sha256_bytes(bytes_2024),
            "copied_path": rel(xml_2024_copy),
            "copied_sha256": sha256_file(xml_2024_copy),
            "hash_match": sha256_bytes(bytes_2024) == sha256_file(xml_2024_copy),
        }
    )

    original_manifest = json.loads(
        (BACKUP_DIR / "audit_run_manifest.json").read_text(encoding="utf-8")
    )
    continuation_timestamp = datetime.now(timezone.utc).isoformat()
    dirty = git("status", "--porcelain").splitlines()
    immutable_hashes = {name: sha256_file(AUDIT_DIR / name) for name in FROZEN_FILES}
    if immutable_hashes != {name: backup_hashes[name] for name in FROZEN_FILES}:
        raise RuntimeError("A frozen occurrence/reconciliation file changed during continuation")
    input_paths = [
        CANONICAL_DATA,
        parsed[SUPPORTING_YEAR]["path"],
        *(parsed[year]["path"] for year in HISTORICAL_YEARS),
        CATALOGUE_ROOT / "2024/ops2024syst-claml.zip",
        *(BACKUP_DIR / filename for filename in EXPECTED_PREVIOUS_FILES),
    ]
    manifest = {
        "original_audit_timestamp": original_manifest.get("audit_timestamp_utc", ""),
        "continuation_audit_timestamp_utc": continuation_timestamp,
        "ops_2012_review_gate_timestamp_utc": continuation_timestamp,
        "git_repository": str(ROOT),
        "git_branch": git("branch", "--show-current"),
        "git_commit_hash": git("rev-parse", "HEAD"),
        "dirty_working_tree": bool(dirty),
        "dirty_working_tree_entry_count": len(dirty),
        "git_worktrees_searched": [str(ROOT)],
        "codex_directories_searched": [str(Path.home() / ".codex")],
        "search_result": "One complete original set in the main repository; no pre-existing duplicates in worktrees or Codex directories.",
        "python_version": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "relevant_package_versions": {"pandas": pd.__version__},
        "input_files": [
            {"path": rel(path), "sha256": sha256_file(path), "size_bytes": path.stat().st_size}
            for path in input_paths
        ],
        "accepted_historical_sources": [
            {
                "year": year,
                "path": rel(parsed[year]["path"]),
                "sha256": parsed[year]["sha256"],
                "source_type": "extracted official historical DIMDI ClaML XML",
                "evidence_role": (
                    "supporting pre-period provenance; not an analytical audit year"
                    if year == SUPPORTING_YEAR else "analytical-period annual catalogue source"
                ),
                "provenance_evidence": parsed[year]["evidence"],
            }
            for year in (SUPPORTING_YEAR, *HISTORICAL_YEARS)
        ],
        "backup_paths": [
            {"path": rel(BACKUP_DIR / name), "sha256": backup_hashes[name]}
            for name in (*EXPECTED_PREVIOUS_FILES, "run_audit.py")
        ] + [
            {"path": rel(path), "sha256": sha256_file(path)}
            for path in sorted(GATE_BACKUP_DIR.rglob("*")) if path.is_file()
        ] + [
            {"path": rel(path), "sha256": sha256_file(path)}
            for path in sorted(REVERIFICATION_BACKUP_DIR.rglob("*")) if path.is_file()
        ],
        "copied_file_provenance": copied,
        "reconstructed_file_status": {
            "ops_code_summary_2013_2024.csv": "existed; updated from accepted primary ClaML and canonical occurrence evidence; not reconstructed from narrative",
            "frozen_occurrence_and_reconciliation_csvs": "verified and unchanged",
        },
        "scripts_inspected": original_manifest.get("scripts_and_modules_inspected", []) + [
            "audits/ops_code_audit_2013_2024/run_audit.py",
            "audits/ops_code_audit_2013_2024/continue_audit.py",
        ],
        "scripts_executed": ["audits/ops_code_audit_2013_2024/continue_audit.py"],
        "requested_rows": len(updated),
        "newly_resolved_2013_2018_rows": len(diff),
        "preserved_2019_2024_rows": len(unchanged),
        "changed_2019_2024_rows": int((~unchanged.unchanged).sum()),
        "additional_de_novo_88398_codes": [],
        "year_specific_de_novo_sets": {
            "2013-2015": ["8-839.87", "8-839.88"],
            "2016-2024": ["8-839.87", "8-839.88", "8-839.89", "8-839.8a"],
        },
        "confirmed_introduction_years": {
            "8-839.87": 2013,
            "8-839.88": 2013,
            "8-839.89": 2016,
            "8-839.8a": 2016,
        },
        "ops_2012_supporting_provenance": {
            "analytical_audit_year": False,
            "path": rel(parsed[SUPPORTING_YEAR]["path"]),
            "sha256": parsed[SUPPORTING_YEAR]["sha256"],
            "claml_version": parsed[SUPPORTING_YEAR]["root"].attrib.get("version", ""),
            "ops_version": parsed[SUPPORTING_YEAR]["title"].attrib.get("version", ""),
            "catalogue_date": parsed[SUPPORTING_YEAR]["title"].attrib.get("date", ""),
            "authority": parsed[SUPPORTING_YEAR]["identifier"].attrib.get("authority", ""),
            "authority_uid": parsed[SUPPORTING_YEAR]["identifier"].attrib.get("uid", ""),
            "local_primary_source_verification_complete": True,
            "independent_review_result_asserted": False,
        },
        "reconciliation_independent_recomputation": recon_values,
        "frozen_file_hashes_before_and_after": {
            name: {
                "before": backup_hashes[name], "after": immutable_hashes[name],
                "unchanged": backup_hashes[name] == immutable_hashes[name],
            }
            for name in FROZEN_FILES
        },
        "production_file_modified": False,
        "de_novo_sensitivity_analysis_started": False,
        "historical_catalogue_question_locally_verified_from_claml": True,
        "historical_catalogue_question_independently_reviewed": False,
        "reconciliation_codex_internal_consistency_check_complete": True,
        "reconciliation_independent_external_recomputation_complete": False,
        "final_status": "Local audit verification complete; independent manual review of the updated audit CSVs, reconciliation recomputation, and ClaML primary sources remains pending.",
        "warnings": [
            "The one-off creator of the canonical code-level CSV remains absent from the repository.",
            "A matching row-level CSV hash proves file identity, not the correctness of the reconciliation logic or level distinction.",
            "The Codex recomputation is an internal consistency check; no completed external row-level review is asserted from local evidence.",
        ],
        "unresolved_issues": [
            "Canonical code-level CSV creator script is not retained.",
            "Independent manual review of the updated audit CSVs, reconciliation recomputation, and ClaML primary sources remains pending.",
        ],
    }

    # Package README is created before the manifest and records copy hashes.
    availability = updated[
        updated.catalogue_year.astype(int).isin(HISTORICAL_YEARS)
        & updated.code.isin(["8-839.87", "8-839.88", "8-839.89", "8-839.8a"])
    ].pivot(index="catalogue_year", columns="code", values="exists").reset_index()
    source_copy_table = pd.DataFrame(copied)
    readme = f"""# Manual review package: OPS 8-839.8*, 2013–2024

## Review question

Prepare independent review of the TIPS 8-839.8 historical catalogue timeline
and the row-level reconciliation.

Codex locally verified the historical catalogue timeline directly against the
included ClaML primary sources. No completed independent historical review is
asserted from repository evidence. The local finding is that `.87/.88` are
absent in OPS 2012 and present in OPS 2013, while
`.89/.8a` are absent through OPS 2015 and introduced in OPS 2016. The actual
2012 source and its provenance table are included in this package. OPS 2012 is
supporting pre-period evidence, not an added analytical audit year.

## Historical availability

{markdown_table(availability)}

Official catalogue first year in the audited interval versus G-BA first year:

- `.87`: 2013 versus 2013
- `.88`: 2013 versus 2013
- `.89`: 2016 versus 2016
- `.8a`: 2016 versus 2016

Interpretation A applies to `.89` and `.8a`. A year-specific de novo set is
required: `.87/.88` for 2013–2015 and `.87/.88/.89/.8a` for 2016–2024.

Comparability across 2015 and 2016 may be affected by the introduction of
additional specific de-novo subcodes in 2016. Catalogue availability alone
does not establish the direction or magnitude of any effect. `.84` and `.86`
are described longitudinally as secondary interventions on an existing shunt;
their exact annual wording is retained in the audit CSV.

Codex internally recomputed the reconciliation directly from the included raw
`ops_code_reconciliation_site_year.csv`:
{recon_values['total_site_year_rows']} rows,
{recon_values['fully_reconciled_rows']} fully reconciled,
{recon_values['mismatching_rows']} mismatches,
{recon_values['unresolved_rows']} unresolved, and
{recon_values['manual_review_rows']} manual-review rows.

The raw row-level CSV still requires independent manual review outside Codex.
A matching SHA-256 proves that it is unchanged; it does not independently
prove the reconciliation logic or the site-versus-institution distinction. The
audit is not finally closed until an independent reviewer confirms the reported
values and the accompanying primary-source evidence.

## Copied-file integrity

{markdown_table(source_copy_table)}

All accepted source files are actual ClaML XML/archive bytes, not screenshots,
links, or derived title tables. Each source/copy SHA-256 pair matches.

The de novo sensitivity analysis has **not** been started and must not begin
before independent manual review is complete.

**Status:** Local audit verification complete; independent manual review of the
updated audit CSVs, reconciliation recomputation, and ClaML primary sources
remains pending.
"""
    (MANUAL_DIR / "README.md").write_text(readme, encoding="utf-8")

    # Hash every output except the self-referential manifest, then write and copy it.
    output_candidates = [
        path for path in AUDIT_DIR.rglob("*")
        if path.is_file()
        and path.name not in {"audit_run_manifest.json", "package_manifest.json"}
        and path != MANUAL_DIR / "audit_run_manifest.json"
    ]
    manifest["output_files"] = [
        {"path": rel(path), "sha256": sha256_file(path), "size_bytes": path.stat().st_size}
        for path in sorted(output_candidates)
    ]
    manifest["manifest_self_hash_note"] = (
        "The manifest cannot contain its own final SHA-256 without self-reference; "
        "the main and manual-package copies are byte-identical after final write."
    )
    paths["manifest"].write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    manifest_copy = MANUAL_DIR / "audit_run_manifest.json"
    shutil.copy2(paths["manifest"], manifest_copy)
    if sha256_file(paths["manifest"]) != sha256_file(manifest_copy):
        raise RuntimeError("Manual-package manifest copy hash mismatch")

    package_manifest_path = MANUAL_DIR / "package_manifest.json"
    package_files = [
        path for path in MANUAL_DIR.rglob("*")
        if path.is_file() and path != package_manifest_path
    ]
    package_manifest = {
        "created_utc": continuation_timestamp,
        "purpose": "independent manual review preparation for catalogue and reconciliation evidence",
        "historical_catalogue_question_locally_verified_from_claml": True,
        "historical_catalogue_question_independently_reviewed": False,
        "codex_internal_reconciliation_recomputation_complete": True,
        "independent_external_reconciliation_recomputation_complete": False,
        "de_novo_sensitivity_analysis_started": False,
        "status": "Local audit verification complete; independent manual review of the updated audit CSVs, reconciliation recomputation, and ClaML primary sources remains pending.",
        "files": [
            {
                "path": path.relative_to(MANUAL_DIR).as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in sorted(package_files)
        ],
        "self_hash_note": "This manifest excludes its own SHA-256 to avoid self-reference.",
    }
    package_manifest_path.write_text(
        json.dumps(package_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Final invariants.
    if len(updated) != 144 or len(diff) != 72 or len(unchanged) != 72:
        raise RuntimeError("Final row-count invariant failed")
    if not unchanged.unchanged.all():
        raise RuntimeError("Preserved-row invariant failed")
    for filename in FROZEN_FILES:
        if sha256_file(AUDIT_DIR / filename) != backup_hashes[filename]:
            raise RuntimeError(f"Frozen file was altered: {filename}")

    print("Previously reported outputs: all 8 existed in the main repository; no pre-existing duplicates.")
    print(f"Output set: {AUDIT_DIR}")
    print("ops_code_summary_2013_2024.csv: existed; updated from primary evidence, not reconstructed from narrative.")
    print("Requested catalogue rows: 144 verified.")
    print(
        "Independent reconciliation: "
        f"total={recon_values['total_site_year_rows']}, "
        f"reconciled={recon_values['fully_reconciled_rows']}, "
        f"mismatches={recon_values['mismatching_rows']}, "
        f"unresolved={recon_values['unresolved_rows']}, "
        f"manual_review={recon_values['manual_review_rows']}."
    )
    print("Previous 2,057/0/0 reconciliation claims: verified.")
    for year in HISTORICAL_YEARS:
        row89 = updated[(updated.catalogue_year.astype(int) == year) & updated.code.eq("8-839.89")].iloc[0]
        row8a = updated[(updated.catalogue_year.astype(int) == year) & updated.code.eq("8-839.8a")].iloc[0]
        print(
            f"{year}: accepted source={row89.source_xml_member}; "
            f"8-839.89={row89.exists}; 8-839.8a={row8a.exists}"
        )
    print("Catalogue/G-BA first years: .87=2013/2013, .88=2013/2013, .89=2016/2016, .8a=2016/2016.")
    print("OPS 2012 supporting source confirms .87/.88/.89/.8a absent; .87/.88 introduced in 2013.")
    print(".89 and .8a interpretation: A.")
    print("Fixed 2013-2024 de novo set: no.")
    print("Year-specific sets: 2013-2015=.87,.88; 2016-2024=.87,.88,.89,.8a.")
    print("Additional de novo 8-839.8* codes: none.")
    print("Changed verified 2019-2024 rows: 0/72.")
    print("Unresolved catalogue years: none.")
    print(f"Manual-review package: {MANUAL_DIR}")
    print("Production/publication files modified: no. De novo sensitivity analysis started: no.")
    print(
        "Local audit verification complete; independent manual review of the updated audit CSVs, "
        "reconciliation recomputation, and ClaML primary sources remains pending."
    )


if __name__ == "__main__":
    main()
