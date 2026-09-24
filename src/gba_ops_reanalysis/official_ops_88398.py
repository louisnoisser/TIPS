"""Official year-specific BfArM OPS 8-839.8 catalogue validation.

This module deliberately separates catalogue-derived proposals from author
approval.  A proposal is never treated as an officially verified mapping.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import subprocess
from typing import Iterable
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import pandas as pd


YEARS = tuple(range(2013, 2025))
FAMILY_PARENT = "8-839.8"
ANALYSIS_VERSION = "official-ops-88398-v1"
ALLOWED_CLASSIFICATIONS = {
    "primary_placement",
    "secondary_intervention",
    "unresolved_parent",
    "unresolved_other",
    "invalid_hospital_reported_legacy_code",
}

APPROVED_CODE_CLASSIFICATION = {
    FAMILY_PARENT: "unresolved_parent",
    "8-839.81": "secondary_intervention",
    "8-839.82": "secondary_intervention",
    "8-839.83": "secondary_intervention",
    "8-839.84": "secondary_intervention",
    "8-839.85": "secondary_intervention",
    "8-839.86": "secondary_intervention",
    "8-839.87": "primary_placement",
    "8-839.88": "primary_placement",
    "8-839.89": "primary_placement",
    "8-839.8a": "primary_placement",
    "8-839.8x": "unresolved_other",
}


@dataclass(frozen=True)
class CatalogueSource:
    year: int
    xml_path: Path
    xml_member: str
    xml_bytes: bytes
    xml_sha256: str
    archive_sha256: str
    pdf_path: Path
    pdf_member: str
    pdf_sha256: str
    pdf_archive_sha256: str
    version: str
    publication_date: str
    authority: str

    def reference(self, root: Path, *, pdf: bool = False) -> str:
        path = self.pdf_path if pdf else self.xml_path
        member = self.pdf_member if pdf else self.xml_member
        relative = path.relative_to(root).as_posix()
        return f"{relative}::{member}" if member else relative


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalise_code(value: object) -> str:
    return re.sub(r"\s+", "", str(value)).lower()


def _zip_members(path: Path, suffix: str) -> list[str]:
    with ZipFile(path) as archive:
        return sorted(
            name
            for name in archive.namelist()
            if not name.startswith("__MACOSX/")
            and not Path(name).name.startswith("._")
            and name.lower().endswith(suffix)
        )


def _select_xml(year_dir: Path, year: int) -> tuple[Path, str, bytes]:
    candidates: list[tuple[Path, str]] = []
    for path in sorted(year_dir.rglob("*.xml")):
        name = path.name.lower()
        if f"ops{year}syst" in name and "claml" in name:
            candidates.append((path, ""))
    for archive_path in sorted(year_dir.glob("*.zip")):
        archive_name = archive_path.name.lower()
        if "claml" not in archive_name or "syst" not in archive_name:
            continue
        for member in _zip_members(archive_path, ".xml"):
            name = Path(member).name.lower()
            if f"ops{year}syst" in name and "claml" in name:
                candidates.append((archive_path, member))
    if len(candidates) != 1:
        rendered = ", ".join(f"{p}::{m}" if m else str(p) for p, m in candidates)
        raise ValueError(
            f"Expected exactly one deterministic ClaML source for {year}, "
            f"found {len(candidates)}: {rendered or 'none'}"
        )
    path, member = candidates[0]
    if member:
        with ZipFile(path) as archive:
            data = archive.read(member)
    else:
        data = path.read_bytes()
    return path, member, data


def _select_pdf(year_dir: Path, year: int) -> tuple[Path, str, bytes]:
    candidates: list[tuple[Path, str]] = []
    for path in sorted(year_dir.rglob("*.pdf")):
        name = path.name.lower()
        if f"ops{year}syst" in name and ("referenz" in name or "odt" in name):
            candidates.append((path, ""))
    for archive_path in sorted(year_dir.glob("*.zip")):
        if "pdf" not in archive_path.name.lower():
            continue
        for member in _zip_members(archive_path, ".pdf"):
            name = Path(member).name.lower()
            if f"ops{year}syst" in name and ("referenz" in name or "odt" in name):
                candidates.append((archive_path, member))
    if len(candidates) != 1:
        rendered = ", ".join(f"{p}::{m}" if m else str(p) for p, m in candidates)
        raise ValueError(
            f"Expected exactly one deterministic systematics PDF for {year}, "
            f"found {len(candidates)}: {rendered or 'none'}"
        )
    path, member = candidates[0]
    if member:
        with ZipFile(path) as archive:
            data = archive.read(member)
    else:
        data = path.read_bytes()
    return path, member, data


def _recognise_claml(data: bytes, year: int) -> tuple[str, str, str]:
    root = ET.fromstring(data)
    if root.tag.split("}")[-1] != "ClaML":
        raise ValueError(f"{year}: selected XML root is not ClaML")
    title = root.find("Title")
    if title is None or title.attrib.get("version") != str(year):
        raise ValueError(f"{year}: ClaML Title version does not match catalogue year")
    title_text = " ".join("".join(title.itertext()).split())
    if "Prozedurenschlüssel" not in title_text:
        raise ValueError(f"{year}: selected ClaML is not recognisably an OPS systematics file")
    classes = {node.attrib.get("code") for node in root.findall("Class")}
    if FAMILY_PARENT not in classes:
        raise ValueError(f"{year}: official OPS family {FAMILY_PARENT} is absent")
    identifier = root.find("Identifier")
    authority = identifier.attrib.get("authority", "") if identifier is not None else ""
    return title.attrib.get("version", ""), title.attrib.get("date", ""), authority


def discover_catalogues(catalogue_root: Path) -> list[CatalogueSource]:
    sources: list[CatalogueSource] = []
    for year in YEARS:
        year_dir = catalogue_root / str(year)
        if not year_dir.is_dir():
            raise FileNotFoundError(f"Missing official catalogue directory for {year}: {year_dir}")
        xml_path, xml_member, xml_bytes = _select_xml(year_dir, year)
        pdf_path, pdf_member, pdf_bytes = _select_pdf(year_dir, year)
        version, publication_date, authority = _recognise_claml(xml_bytes, year)
        sources.append(
            CatalogueSource(
                year=year,
                xml_path=xml_path,
                xml_member=xml_member,
                xml_bytes=xml_bytes,
                xml_sha256=sha256_bytes(xml_bytes),
                archive_sha256=sha256_file(xml_path) if xml_member else "",
                pdf_path=pdf_path,
                pdf_member=pdf_member,
                pdf_sha256=sha256_bytes(pdf_bytes),
                pdf_archive_sha256=sha256_file(pdf_path) if pdf_member else "",
                version=version,
                publication_date=publication_date,
                authority=authority,
            )
        )
    return sources


def _clean_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def _rubrics(class_node: ET.Element) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for rubric in class_node.findall("Rubric"):
        kind = rubric.attrib.get("kind", "")
        text = _clean_text(rubric)
        if text:
            result.setdefault(kind, []).append(text)
    return result


def propose_classification(
    code: str, short_label: str, full_label: str, official_notes: str
) -> tuple[str, str]:
    """Propose a conservative mapping using only supplied official wording."""
    if normalise_code(code) == FAMILY_PARENT:
        return (
            "unresolved_parent",
            "The family heading has no terminal procedure meaning and is retained as a parent code.",
        )
    wording = " ".join([short_label, full_label, official_notes]).lower()
    if any(term in wording for term in ("sonstige", "nicht näher bezeichnet", "nicht naeher bezeichnet")):
        return (
            "unresolved_other",
            "The official wording is a residual or otherwise non-specific category.",
        )
    existing_shunt = any(
        term in wording
        for term in ("bestehend", "revision", "thrombol", "thrombekt", "verschluss",
                     "verkleinerung", "verlängerung", "verlaengerung", "vergrößerung",
                     "vergroesserung")
    )
    if existing_shunt:
        return (
            "secondary_intervention",
            "The official wording explicitly describes treatment of an existing shunt or a revision-type intervention.",
        )
    preferred = " ".join([short_label, full_label]).lower()
    if "anlegen" in preferred or "herstellung eines shunt" in wording:
        return (
            "primary_placement",
            "The official wording explicitly describes creation or placement of a portosystemic shunt.",
        )
    if "angioplastie" in preferred:
        return (
            "secondary_intervention",
            "The official terminal wording explicitly describes angioplasty rather than primary shunt placement.",
        )
    return (
        "unresolved_other",
        "The official wording does not support an unambiguous primary-placement or secondary-intervention proposal.",
    )


def extract_family(source: CatalogueSource, catalogue_root: Path) -> list[dict[str, object]]:
    root = ET.fromstring(source.xml_bytes)
    classes = {node.attrib["code"]: node for node in root.findall("Class") if "code" in node.attrib}
    parent = classes[FAMILY_PARENT]
    selected_codes = [FAMILY_PARENT]
    queue = [node.attrib["code"] for node in parent.findall("SubClass")]
    while queue:
        code = queue.pop(0)
        node = classes.get(code)
        if node is None:
            raise ValueError(f"{source.year}: declared subclass {code} is missing")
        children = [child.attrib["code"] for child in node.findall("SubClass")]
        if children:
            queue.extend(children)
        else:
            selected_codes.append(code)

    rows: list[dict[str, object]] = []
    for code in selected_codes:
        node = classes[code]
        rubrics = _rubrics(node)
        short = " | ".join(rubrics.get("preferred", []))
        full = " | ".join(rubrics.get("preferredLong", [])) or short
        note_parts = []
        for kind in ("inclusion", "exclusion", "note"):
            note_parts.extend(f"[{kind}] {text}" for text in rubrics.get(kind, []))
        notes = " | ".join(note_parts)
        proposed, reason = propose_classification(code, short, full, notes)
        parents = [item.attrib.get("code", "") for item in node.findall("SuperClass")]
        children = [item.attrib.get("code", "") for item in node.findall("SubClass")]
        evidence = " | ".join(part for part in (full, notes) if part)
        rows.append(
            {
                "reporting_year": source.year,
                "ops_code_official": code,
                "ops_code_normalised": normalise_code(code),
                "hierarchy_level": 0 if code == FAMILY_PARENT else 1,
                "parent_code": parents[0] if parents else "",
                "official_short_label": short,
                "official_full_label": full,
                "inclusion_notes": " | ".join(rubrics.get("inclusion", [])),
                "exclusion_notes": " | ".join(rubrics.get("exclusion", [])),
                "coding_notes": " | ".join(rubrics.get("note", [])),
                "modifiers_or_child_relationships": "|".join(children),
                "official_notes": notes,
                "proposed_classification": proposed,
                "classification_reason": reason,
                "evidence_excerpt": evidence,
                "source_file": source.reference(catalogue_root),
                "source_sha256": source.xml_sha256,
                "pdf_reference": source.reference(catalogue_root, pdf=True),
                "pdf_sha256": source.pdf_sha256,
                "pdf_archive_sha256": source.pdf_archive_sha256,
                "manual_reviewer_1": "",
                "manual_reviewer_2": "",
                "manual_review_status": "pending",
                "manual_review_comment": "",
                "officially_verified": False,
            }
        )
    return rows


def build_codebook(sources: Iterable[CatalogueSource], catalogue_root: Path) -> pd.DataFrame:
    rows = [row for source in sources for row in extract_family(source, catalogue_root)]
    frame = pd.DataFrame(rows).sort_values(
        ["reporting_year", "ops_code_normalised"]
    ).reset_index(drop=True)
    wording_counts = frame.groupby("ops_code_normalised")["evidence_excerpt"].nunique()
    class_counts = frame.groupby("ops_code_normalised")["proposed_classification"].nunique()
    frame["cross_year_wording_change"] = (
        frame["ops_code_normalised"].map(wording_counts).gt(1)
    )
    frame["cross_year_classification_change"] = (
        frame["ops_code_normalised"].map(class_counts).gt(1)
    )
    frame["requires_separate_year_review"] = (
        frame["cross_year_wording_change"] | frame["cross_year_classification_change"]
    )
    return frame


def build_cross_year_changes(codebook: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    all_years = set(YEARS)
    for code, group in codebook.groupby("ops_code_normalised", sort=True):
        group = group.sort_values("reporting_year")
        present = group.reporting_year.astype(int).tolist()
        wording = group.groupby("evidence_excerpt").reporting_year.apply(
            lambda s: ",".join(map(str, sorted(s.astype(int))))
        )
        hierarchy = group.groupby(
            ["hierarchy_level", "parent_code", "modifiers_or_child_relationships"],
            dropna=False,
        ).reporting_year.apply(lambda s: ",".join(map(str, sorted(s.astype(int)))))
        classifications = group.groupby("proposed_classification").reporting_year.apply(
            lambda s: ",".join(map(str, sorted(s.astype(int))))
        )
        rows.append(
            {
                "ops_code_normalised": code,
                "ops_code_official_variants": "|".join(sorted(group.ops_code_official.unique())),
                "first_year_present": min(present),
                "last_year_present": max(present),
                "years_present": ",".join(map(str, present)),
                "years_absent": ",".join(map(str, sorted(all_years - set(present)))),
                "wording_changed": group.evidence_excerpt.nunique() > 1,
                "wording_by_years": " || ".join(
                    f"{years}: {text}" for text, years in wording.items()
                ),
                "hierarchy_changed": len(hierarchy) > 1,
                "hierarchy_by_years": " || ".join(
                    f"{years}: level={level}, parent={parent}, children={children}"
                    for (level, parent, children), years in hierarchy.items()
                ),
                "proposed_classification_changed": group.proposed_classification.nunique() > 1,
                "classification_by_years": " || ".join(
                    f"{years}: {classification}"
                    for classification, years in classifications.items()
                ),
                "newly_introduced_after_2013": min(present) > min(YEARS),
                "retired_before_2024": max(present) < max(YEARS),
                "manual_review_required": True,
            }
        )
    return pd.DataFrame(rows)


def extract_observed_records(audit_csv: Path) -> pd.DataFrame:
    audit = pd.read_csv(audit_csv, dtype=str, keep_default_na=False)
    required = {
        "reporting_year", "ik", "site_identifier", "OPS_code",
        "current_parser_numeric_count", "suppressed_flag",
        "suppressed_record_count", "source_file",
    }
    missing = required - set(audit.columns)
    if missing:
        raise ValueError(f"Observed audit is missing columns: {sorted(missing)}")
    years = pd.to_numeric(audit.reporting_year, errors="coerce")
    normalised = audit.OPS_code.map(normalise_code)
    selected = audit.loc[
        years.isin(YEARS) & normalised.str.startswith(FAMILY_PARENT)
    ].copy()
    selected["reporting_year"] = pd.to_numeric(
        selected.reporting_year, errors="raise"
    ).astype(int)
    selected["ops_code_normalised"] = selected.OPS_code.map(normalise_code)
    selected["visible_numeric_value"] = pd.to_numeric(
        selected.current_parser_numeric_count.replace("", pd.NA), errors="coerce"
    )
    selected["suppression_status"] = selected.suppressed_flag.map(
        lambda value: str(value).strip().lower() in {"true", "1", "yes"}
    )
    selected["suppressed_entry_count"] = pd.to_numeric(
        selected.suppressed_record_count.replace("", "0"), errors="raise"
    ).astype(int)
    selected = selected.rename(
        columns={
            "site_identifier": "physical_site_identifier",
            "OPS_code": "ops_code_observed",
        }
    )
    columns = [
        "reporting_year", "ik", "physical_site_identifier", "ops_code_observed",
        "ops_code_normalised", "visible_numeric_value", "suppression_status",
        "suppressed_entry_count", "source_file",
    ]
    return selected[columns].sort_values(
        ["reporting_year", "ik", "physical_site_identifier", "ops_code_normalised"]
    ).reset_index(drop=True)


def build_coverage(observed: pd.DataFrame, codebook: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        observed.groupby(["reporting_year", "ops_code_normalised"], as_index=False)
        .agg(
            observed_ops_code=("ops_code_observed", lambda s: "|".join(sorted(set(s)))),
            number_of_records=("ops_code_observed", "size"),
            visible_activity=("visible_numeric_value", lambda s: int(s.fillna(0).sum())),
            number_of_suppressed_entries=("suppressed_entry_count", "sum"),
        )
    )
    matches = codebook[
        [
            "reporting_year", "ops_code_normalised", "ops_code_official",
            "proposed_classification", "manual_review_status", "officially_verified",
        ]
    ]
    counts = matches.groupby(
        ["reporting_year", "ops_code_normalised"]
    ).size().rename("codebook_match_count").reset_index()
    coverage = grouped.merge(counts, how="left").merge(
        matches, how="left", on=["reporting_year", "ops_code_normalised"]
    )
    coverage["codebook_match_count"] = coverage.codebook_match_count.fillna(0).astype(int)
    coverage["official_codebook_match"] = coverage.ops_code_official.fillna("")
    coverage["classification_status"] = "pending_manual_review"
    coverage.loc[coverage.codebook_match_count.eq(0), "classification_status"] = "unmatched"
    coverage.loc[coverage.codebook_match_count.gt(1), "classification_status"] = "duplicate_match"
    return coverage[
        [
            "reporting_year", "observed_ops_code", "ops_code_normalised",
            "official_codebook_match", "codebook_match_count",
            "proposed_classification", "classification_status",
            "number_of_records", "visible_activity", "number_of_suppressed_entries",
            "manual_review_status", "officially_verified",
        ]
    ].sort_values(["reporting_year", "ops_code_normalised"]).reset_index(drop=True)


def build_approved_analysis_mapping(codebook: pd.DataFrame) -> pd.DataFrame:
    """Apply the explicitly approved official mapping and add the 2013 exception."""
    required = {
        "reporting_year", "ops_code_official", "ops_code_normalised",
        "proposed_classification",
    }
    missing = required - set(codebook.columns)
    if missing:
        raise ValueError(f"Official codebook is missing columns: {sorted(missing)}")
    mapping = codebook.copy()
    expected = mapping.ops_code_normalised.map(APPROVED_CODE_CLASSIFICATION)
    if expected.isna().any():
        unknown = sorted(mapping.loc[expected.isna(), "ops_code_normalised"].unique())
        raise ValueError(f"Official codebook contains unapproved codes: {unknown}")
    if not mapping.proposed_classification.eq(expected).all():
        bad = mapping.loc[
            ~mapping.proposed_classification.eq(expected),
            ["reporting_year", "ops_code_normalised", "proposed_classification"],
        ]
        raise ValueError(f"Official wording proposal conflicts with approved mapping:\n{bad}")
    mapping["analysis_classification"] = expected
    mapping["mapping_approval_status"] = "approved_by_explicit_user_instruction"
    mapping["mapping_approval_date"] = "2026-07-28"
    mapping["officially_verified"] = True
    mapping["legacy_handling_rule"] = ""
    mapping["valid_in_reporting_year_catalogue"] = True

    template = {column: "" for column in mapping.columns}
    template.update(
        {
            "reporting_year": 2013,
            "ops_code_official": "",
            "ops_code_normalised": "8-839.80",
            "hierarchy_level": 1,
            "parent_code": FAMILY_PARENT,
            "official_short_label": "",
            "official_full_label": "",
            "official_notes": (
                "Valid in OPS 2012 as 'Perkutanes Anlegen' but absent from OPS 2013."
            ),
            "proposed_classification": "invalid_hospital_reported_legacy_code",
            "analysis_classification": "invalid_hospital_reported_legacy_code",
            "classification_reason": (
                "Approved retained exception for a literal hospital-reported legacy "
                "code. It is not remapped and cannot independently establish primary placement."
            ),
            "evidence_excerpt": (
                "OPS 2012: 8-839.80 Perkutanes Anlegen. OPS 2013 subdivides "
                "primary placement into 8-839.87 and 8-839.88."
            ),
            "source_file": (
                "outputs/official_ops_88398_validation_2026-07-28/"
                "unmatched_2013_883980_provenance/unmatched_2013_883980_provenance.csv"
            ),
            "manual_review_status": "approved_by_explicit_user_instruction",
            "officially_verified": False,
            "mapping_approval_status": "approved_by_explicit_user_instruction",
            "mapping_approval_date": "2026-07-28",
            "legacy_handling_rule": (
                "Retain literal records and suppression. Do not remap, discard, or use "
                "as the sole basis for primary-placement classification."
            ),
            "valid_in_reporting_year_catalogue": False,
        }
    )
    mapping = pd.concat([mapping, pd.DataFrame([template])], ignore_index=True)
    if mapping.duplicated(["reporting_year", "ops_code_normalised"]).any():
        raise ValueError("Approved mapping contains duplicate year-code rows")
    return mapping.sort_values(
        ["reporting_year", "ops_code_normalised"]
    ).reset_index(drop=True)


def validate_approved_mapping(codebook: pd.DataFrame, coverage: pd.DataFrame) -> None:
    """Enforce the author-approval gate before any secondary-only analysis."""
    if not coverage.codebook_match_count.eq(1).all():
        raise ValueError("Not every observed year-code combination has exactly one official match")
    observed_keys = coverage[["reporting_year", "ops_code_normalised"]]
    reviewed = observed_keys.merge(
        codebook,
        on=["reporting_year", "ops_code_normalised"],
        how="left",
        validate="one_to_one",
    )
    approval_status = reviewed.get(
        "mapping_approval_status", reviewed.manual_review_status
    ).astype(str).str.lower()
    approved = approval_status.isin(
        {"approved", "approved_by_explicit_user_instruction"}
    )
    classes = reviewed.get(
        "analysis_classification", reviewed.proposed_classification
    ).astype(str)
    verified = reviewed.officially_verified.astype(str).str.lower().isin({"true", "1"})
    verified_or_approved_invalid = verified | classes.eq(
        "invalid_hospital_reported_legacy_code"
    )
    two_reviewers = (
        reviewed.manual_reviewer_1.astype(str).str.strip().ne("")
        & reviewed.manual_reviewer_2.astype(str).str.strip().ne("")
    )
    explicit_user_approval = approval_status.eq(
        "approved_by_explicit_user_instruction"
    )
    if not (
        approved
        & verified_or_approved_invalid
        & (two_reviewers | explicit_user_approval)
    ).all():
        raise ValueError("Observed mappings are not fully approved by two reviewers")


def classify_site_year_records(joined: pd.DataFrame) -> pd.DataFrame:
    """Classify approved joined records without inferring suppressed counts."""
    required = {
        "reporting_year", "physical_site_identifier", "ik",
        "officially_verified",
        "suppression_status", "visible_numeric_value",
    }
    missing = required - set(joined.columns)
    if missing:
        raise ValueError(f"Joined records are missing columns: {sorted(missing)}")
    if pd.to_numeric(joined.reporting_year, errors="coerce").lt(2013).any():
        raise ValueError("Years before 2013 may not enter secondary-only classification")

    rows: list[dict[str, object]] = []
    keys = ["reporting_year", "physical_site_identifier", "ik"]
    for key, group in joined.groupby(keys, sort=True, dropna=False):
        verified = group.officially_verified.astype(str).str.lower().isin({"true", "1"})
        classification_column = (
            "analysis_classification"
            if "analysis_classification" in group
            else "proposed_classification"
        )
        classes = group[classification_column].astype(str)
        primary = verified & classes.eq("primary_placement")
        secondary = verified & classes.eq("secondary_intervention")
        invalid_legacy = classes.eq("invalid_hospital_reported_legacy_code")
        unresolved = (
            ~verified
            | classes.isin(
                {
                    "unresolved_parent",
                    "unresolved_other",
                    "invalid_hospital_reported_legacy_code",
                }
            )
        )
        visible_activity = int(
            pd.to_numeric(
                group.visible_numeric_value, errors="coerce"
            ).fillna(0).sum()
        )
        if "suppressed_entry_count" in group:
            suppressed_entries = int(
                pd.to_numeric(
                    group.suppressed_entry_count, errors="coerce"
                ).fillna(0).sum()
            )
        else:
            suppressed_entries = int(group.suppression_status.astype(bool).sum())
        all_suppressed = visible_activity == 0 and suppressed_entries > 0
        if primary.any():
            category = "primary_or_mixed"
        elif secondary.any() and not unresolved.any():
            category = "definitely_secondary_only"
        elif all_suppressed:
            category = "suppressed_only_unclassifiable"
        else:
            category = "unresolved"
        rows.append(
            {
                "reporting_year": int(key[0]),
                "physical_site_identifier": key[1],
                "ik": key[2],
                "site_year_classification": category,
                "visible_activity": visible_activity,
                "suppressed_entries": suppressed_entries,
                "all_activity_suppressed": all_suppressed,
                "primary_code_present": bool(primary.any()),
                "secondary_code_present": bool(secondary.any()),
                "unresolved_code_present": bool(unresolved.any()),
                "invalid_legacy_code_present": bool(invalid_legacy.any()),
                "invalid_legacy_suppressed_entries": int(
                    (
                        pd.to_numeric(
                            group.get(
                                "suppressed_entry_count",
                                group.suppression_status.astype(int),
                            ),
                            errors="coerce",
                        ).fillna(0)
                        * invalid_legacy.astype(int)
                    ).sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def classify_sites_longitudinal(
    joined: pd.DataFrame, site_years: pd.DataFrame
) -> pd.DataFrame:
    """Assign exhaustive longitudinal categories from approved record evidence."""
    rows: list[dict[str, object]] = []
    for site, group in joined.groupby("physical_site_identifier", sort=True, dropna=False):
        verified = group.officially_verified.astype(str).str.lower().isin({"true", "1"})
        classification_column = (
            "analysis_classification"
            if "analysis_classification" in group
            else "proposed_classification"
        )
        classes = group[classification_column].astype(str)
        primary = verified & classes.eq("primary_placement")
        visible_secondary = (
            verified
            & classes.eq("secondary_intervention")
            & pd.to_numeric(group.visible_numeric_value, errors="coerce").fillna(0).gt(0)
        )
        unresolved = ~verified | classes.isin(
            {
                "unresolved_parent",
                "unresolved_other",
                "invalid_hospital_reported_legacy_code",
            }
        )
        years = site_years[site_years.physical_site_identifier.eq(site)].copy()
        if primary.any():
            category = "ever_primary"
        elif visible_secondary.any() and not unresolved.any():
            category = "never_primary_visible_secondary_only"
        else:
            category = "never_primary_unresolved"
        annual = years.visible_activity if len(years) else pd.Series(dtype=float)
        suppressed_only_unclassifiable_site = bool(
            int(annual.sum()) == 0
            and not primary.any()
            and not years.site_year_classification.eq(
                "definitely_secondary_only"
            ).any()
        )
        rows.append(
            {
                "physical_site_identifier": site,
                "longitudinal_classification": category,
                "first_active_year": int(years.reporting_year.min()),
                "last_active_year": int(years.reporting_year.max()),
                "number_of_active_years": int(years.reporting_year.nunique()),
                "years_with_primary_placement_code": int(
                    years.primary_code_present.astype(bool).sum()
                ),
                "years_definitely_secondary_only": int(
                    years.site_year_classification.eq("definitely_secondary_only").sum()
                ),
                "unresolved_years": int(
                    years.site_year_classification.isin(
                        ["unresolved", "suppressed_only_unclassifiable"]
                    ).sum()
                ),
                "cumulative_visible_activity": int(annual.sum()),
                "suppressed_entries": int(years.suppressed_entries.sum()),
                "maximum_annual_visible_activity": int(annual.max()),
                "suppressed_only_unclassifiable_site": (
                    suppressed_only_unclassifiable_site
                ),
                "ever_ge20": bool(annual.ge(20).any()),
                "ever_ge50": bool(annual.ge(50).any()),
                "ever_ge100": bool(annual.ge(100).any()),
                "ever_ge200": bool(annual.ge(200).any()),
            }
        )
    return pd.DataFrame(rows)


def source_inventory(
    sources: Iterable[CatalogueSource], catalogue_root: Path
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "catalogue_year": source.year,
                "source_path": source.reference(catalogue_root),
                "original_archive_path": (
                    source.xml_path.relative_to(catalogue_root).as_posix()
                    if source.xml_member else ""
                ),
                "source_filename": (
                    Path(source.xml_member).name if source.xml_member else source.xml_path.name
                ),
                "bfarm_version": source.version,
                "publication_date": source.publication_date,
                "authority": source.authority,
                "source_sha256": source.xml_sha256,
                "archive_sha256": source.archive_sha256,
                "pdf_reference": source.reference(catalogue_root, pdf=True),
            }
            for source in sources
        ]
    )


def git_commit(root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def generation_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
