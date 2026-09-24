#!/usr/bin/env python3
"""Trace literal 8-839.80 entries in the five affected 2013 hospital XML files."""

from __future__ import annotations

from collections import defaultdict
import hashlib
from pathlib import Path
import re

from lxml import etree
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "outputs" / "audit" / "tips_code_level_audit.csv"
OUTPUT = (
    ROOT / "outputs" / "official_ops_88398_validation_2026-07-28"
    / "unmatched_2013_883980_provenance"
)
OFFICIAL_2012 = (
    "https://klassifikationen.bfarm.de/ops/kode-suche/"
    "htmlops2012/block-8-80...8-85.htm"
)
OFFICIAL_2013 = (
    "https://klassifikationen.bfarm.de/ops/kode-suche/"
    "htmlops2013/block-8-80...8-85.htm"
)
OFFICIAL_2013_CHANGE = (
    "https://klassifikationen.bfarm.de/ops/kode-suche/"
    "htmlops2013/zusatz-03-kommentar.htm"
)
FINAL_STATUS = "invalid_hospital_reported_legacy_code"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clean(value: object) -> str:
    return " ".join(str(value or "").split())


def threshold_label(value: int, suppressed: int) -> str:
    if value >= 200:
        return ">=200"
    if value >= 100:
        return "100-199"
    if value >= 50:
        return "50-99"
    if value >= 20:
        return "20-49"
    if value >= 4:
        return "4-19"
    if value > 0:
        return "1-3"
    return "suppressed-only" if suppressed else "no family activity"


def procedure_summary(node: etree._Element) -> tuple[str, int, bool]:
    code = clean(node.findtext("OPS_301"))
    numeric = clean(node.findtext("Anzahl"))
    suppressed = node.find("Anzahl_Datenschutz") is not None
    return code, int(numeric) if numeric else 0, suppressed


def family_summary(root: etree._Element) -> tuple[str, int, int, set[str]]:
    grouped: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for code_node in root.xpath(
        './/OPS_301[starts-with(normalize-space(text()), "8-839.8")]'
    ):
        code, numeric, suppressed = procedure_summary(code_node.getparent())
        grouped[code][0] += 1
        grouped[code][1] += numeric
        grouped[code][2] += int(suppressed)
    rendered = " | ".join(
        f"{code} [literal occurrences={values[0]}, visible={values[1]}, "
        f"suppressed entries={values[2]}]"
        for code, values in sorted(grouped.items())
        if code != "8-839.80"
    )
    visible = sum(values[1] for values in grouped.values())
    suppressed = sum(values[2] for values in grouped.values())
    return rendered, visible, suppressed, set(grouped)


def exact_source_contexts(text: str) -> list[tuple[str, str, str]]:
    procedure_pattern = re.compile(r"<Prozedur\b[^>]*>.*?</Prozedur>", re.DOTALL)
    code_pattern = re.compile(
        r"<OPS_301\b[^>]*>\s*8-839\.80\s*</OPS_301>", re.DOTALL
    )
    blocks = list(procedure_pattern.finditer(text))
    results: list[tuple[str, str, str]] = []
    for index, block in enumerate(blocks):
        code_match = code_pattern.search(block.group(0))
        if not code_match:
            continue
        first = max(0, index - 1)
        last = min(len(blocks) - 1, index + 1)
        context = text[blocks[first].start():blocks[last].end()]
        suppression = re.search(
            r"<Anzahl_Datenschutz\b[^>]*(?:/\s*>|>.*?</Anzahl_Datenschutz>)",
            block.group(0),
            re.DOTALL,
        )
        results.append(
            (
                code_match.group(0),
                suppression.group(0) if suppression else "",
                context,
            )
        )
    return results


def build_rows() -> pd.DataFrame:
    audit = pd.read_csv(AUDIT, dtype=str, keep_default_na=False)
    affected = audit[
        audit.reporting_year.eq("2013")
        & audit.OPS_code.str.strip().str.lower().eq("8-839.80")
    ].copy()
    if len(affected) != 5:
        raise ValueError(f"Expected five affected source files, found {len(affected)}")

    rows: list[dict[str, object]] = []
    for audit_row in affected.itertuples(index=False):
        path = ROOT / audit_row.source_file
        text = path.read_text(encoding="utf-8-sig")
        document = etree.parse(str(path))
        root = document.getroot()
        hits = root.xpath('.//OPS_301[normalize-space(text()) = "8-839.80"]')
        raw_contexts = exact_source_contexts(text)
        if len(hits) != len(raw_contexts):
            raise ValueError(
                f"{path}: parsed {len(hits)} hits but found {len(raw_contexts)} raw contexts"
            )

        adjacent_family, visible, suppressed, family_codes = family_summary(root)
        if not family_codes.intersection({"8-839.87", "8-839.88"}):
            raise ValueError(f"{path}: expected a valid 2013 primary-placement code")
        institution_name = clean(root.findtext(".//Krankenhaus/Kontaktdaten/Name"))
        document_date = clean(root.findtext(".//Datensatz/Datum"))
        producer = clean(root.findtext(".//Producer"))
        for occurrence_index, (hit, raw) in enumerate(zip(hits, raw_contexts), start=1):
            procedure = hit.getparent()
            department_nodes = hit.xpath(
                "ancestor::Organisationseinheit_Fachabteilung[1]"
            )
            department = department_nodes[0] if department_nodes else None
            siblings = [
                node for node in procedure.getparent()
                if etree.QName(node).localname == "Prozedur"
            ]
            sibling_index = siblings.index(procedure)
            nearby = siblings[max(0, sibling_index - 2):sibling_index + 3]
            nearby_summary = " | ".join(
                f"{code} [{('suppressed' if is_suppressed else f'visible={numeric}')}]"
                for code, numeric, is_suppressed in map(procedure_summary, nearby)
            )
            rows.append(
                {
                    "occurrence_id": f"{audit_row.site_identifier}#{occurrence_index}",
                    "source_filename": audit_row.source_file,
                    "source_sha256": sha256(path),
                    "institution_identifier": audit_row.ik,
                    "physical_site_identifier": audit_row.site_identifier,
                    "institution_name": institution_name or audit_row.hospital_name,
                    "document_reporting_year": 2013,
                    "document_reporting_year_basis": (
                        "Repository reporting-year directory, source filename, and "
                        "pre-aggregation audit assignment"
                    ),
                    "document_generation_date": document_date,
                    "document_producer": producer,
                    "xml_xpath": document.getpath(hit),
                    "department_number": (
                        clean(department.findtext("Gliederungsnummer"))
                        if department is not None else ""
                    ),
                    "department_name": (
                        clean(department.findtext("Name"))
                        if department is not None else ""
                    ),
                    "exact_xml_element": raw[0],
                    "suppression_xml_element": raw[1],
                    "surrounding_xml_context": raw[2],
                    "appears_literally_in_source": True,
                    "entry_suppressed": procedure.find("Anzahl_Datenschutz") is not None,
                    "visible_numeric_value": (
                        clean(procedure.findtext("Anzahl"))
                    ),
                    "immediate_nearby_procedure_records": nearby_summary,
                    "adjacent_88398_codes_same_hospital_year": adjacent_family,
                    "same_hospital_year_visible_88398_activity": visible,
                    "same_hospital_year_suppressed_88398_entries": suppressed,
                    "threshold_classification_without_883980": threshold_label(
                        visible, suppressed
                    ),
                    "valid_in_official_ops_2012": True,
                    "official_ops_2012_label": "Perkutanes Anlegen",
                    "official_ops_2012_reference": OFFICIAL_2012,
                    "valid_in_official_ops_2013": False,
                    "official_ops_2013_context": (
                        "8-839.80 is absent. Primary placement is subdivided into "
                        "8-839.87 (uncovered stent) and 8-839.88 (covered stent)."
                    ),
                    "official_ops_2013_reference": OFFICIAL_2013,
                    "official_ops_2013_change_reference": OFFICIAL_2013_CHANGE,
                    "provenance_assessment": (
                        "Literal, suppressed use of a terminal code valid in OPS 2012 "
                        "but retired for OPS 2013. Its presence in five independent "
                        "hospital files produced by three software systems, alongside "
                        "valid 2013 replacement codes, supports hospital-reported legacy "
                        "coding rather than a parser or schema artefact."
                    ),
                    "appears_to_be": "invalid hospital-reported legacy code",
                    "historical_legacy_code_evidence": (
                        "Yes. The exact code and label are valid in OPS 2012 and "
                        "the code was retired when primary placement was subdivided "
                        "for OPS 2013."
                    ),
                    "invalid_hospital_reported_code_evidence": (
                        "Yes. It appears literally in a reporting-year 2013 hospital "
                        "procedure record although it is absent from OPS 2013."
                    ),
                    "schema_artefact_assessment": (
                        "No evidence that the schema generated or transformed the "
                        "value. At most, the reporting schema permitted a syntactically "
                        "well-formed but year-invalid OPS string."
                    ),
                    "parser_issue_assessment": (
                        "No. The parser returns the exact literal text held in OPS_301 "
                        "and correctly preserves Anzahl_Datenschutz suppression."
                    ),
                    "recommended_final_status": FINAL_STATUS,
                    "affects_visible_national_activity": False,
                    "visible_national_activity_effect": (
                        "No. All seven literal occurrences are suppressed and contribute "
                        "zero openly numeric activity."
                    ),
                    "affects_site_counts": False,
                    "site_count_effect": (
                        "No. Every affected hospital-year contains other 8-839.8* codes, "
                        "so no site is identified solely by 8-839.80."
                    ),
                    "affects_threshold_classification": False,
                    "threshold_effect": (
                        "No. The code has no visible numeric value and therefore changes "
                        "no visible-volume threshold."
                    ),
                    "affects_planned_secondary_only_analysis": True,
                    "secondary_only_effect": (
                        "Yes at the catalogue-coverage gate. The invalid legacy code must "
                        "remain explicit and approved as such. It does not change the "
                        "substantive category of these five hospital-years because each "
                        "also contains valid 2013 primary-placement code 8-839.87 or "
                        "8-839.88, visible or suppressed."
                    ),
                }
            )
    result = pd.DataFrame(rows)
    if len(result) != 7:
        raise ValueError(f"Expected seven literal XML occurrences, found {len(result)}")
    return result


def markdown_report(frame: pd.DataFrame) -> str:
    file_summary = (
        frame.groupby(
            [
                "source_filename", "institution_identifier",
                "physical_site_identifier", "institution_name",
            ],
            as_index=False,
        )
        .agg(
            literal_occurrences=("occurrence_id", "size"),
            document_generation_date=("document_generation_date", "first"),
            document_producer=("document_producer", "first"),
            adjacent_codes=("adjacent_88398_codes_same_hospital_year", "first"),
            visible_activity=("same_hospital_year_visible_88398_activity", "first"),
            threshold=("threshold_classification_without_883980", "first"),
        )
    )
    lines = [
        "# Provenance of unmatched 2013 OPS code 8-839.80",
        "",
        "## Final status",
        "",
        f"**`{FINAL_STATUS}`**",
        "",
        "`8-839.80` is a valid official OPS 2012 terminal code, labelled "
        "\"Perkutanes Anlegen\". It is not valid in OPS 2013. The official 2013 "
        "change commentary states that primary placement was subdivided into "
        "`8-839.87` for an uncovered stent and `8-839.88` for a covered stent.",
        "",
        "The string occurs literally seven times in five 2013 hospital XML files. "
        "Every occurrence is an `OPS_301` value paired with "
        "`Anzahl_Datenschutz`. The files were produced by three independent "
        "quality-report software products. This rules out a parser-created value "
        "and makes a shared single-software artefact unlikely. The evidence is most "
        "consistent with hospitals carrying a retired 2012 code into 2013 reports.",
        "",
        "No code has been remapped or discarded.",
        "",
        "## Official references",
        "",
        f"- [Official OPS 2012 family]({OFFICIAL_2012})",
        f"- [Official OPS 2013 family]({OFFICIAL_2013})",
        f"- [Official OPS 2013 change commentary]({OFFICIAL_2013_CHANGE})",
        "",
        "## Five affected source files",
        "",
        "| Source | IK | Physical site | Institution | Literal occurrences | "
        "Generated | Visible family activity | Threshold without 8-839.80 |",
        "|---|---|---|---|---:|---|---:|---|",
    ]
    for row in file_summary.itertuples(index=False):
        lines.append(
            f"| `{row.source_filename}` | `{row.institution_identifier}` | "
            f"`{row.physical_site_identifier}` | {row.institution_name} | "
            f"{row.literal_occurrences} | {row.document_generation_date} | "
            f"{row.visible_activity} | {row.threshold} |"
        )
    lines.extend(
        [
            "",
            "## Analytical effects",
            "",
            "- **Visible national activity:** unaffected. All seven occurrences are "
            "suppressed and contribute zero visible activity.",
            "- **Site counts:** unaffected. Every file contains other `8-839.8*` "
            "records, so no site depends solely on `8-839.80` for identification.",
            "- **Threshold classification:** unaffected because there is no visible "
            "numeric count attached to `8-839.80`.",
            "- **Planned secondary-only analysis:** affected at the validation gate. "
            "The invalid legacy entries must remain explicit and receive an approved "
            "handling decision. They do not alter the substantive classification of "
            "these five hospital-years because each also reports valid 2013 primary "
            "placement code `.87` or `.88`, visibly or under suppression.",
            "",
            "## Adjacent 8-839.8 family records by source",
            "",
        ]
    )
    for row in file_summary.itertuples(index=False):
        lines.extend(
            [
                f"### `{row.source_filename}`",
                "",
                row.adjacent_codes,
                "",
            ]
        )
    lines.extend(["## Literal occurrences and XML context", ""])
    for row in frame.itertuples(index=False):
        lines.extend(
            [
                f"### `{row.occurrence_id}`",
                "",
                f"- XPath: `{row.xml_xpath}`",
                f"- Department: `{row.department_number}` {row.department_name}",
                f"- Literal element: `{row.exact_xml_element}`",
                f"- Suppression element: `{row.suppression_xml_element}`",
                f"- Immediate nearby records: {row.immediate_nearby_procedure_records}",
                "",
                "Exact source context, comprising the immediately preceding procedure, "
                "the affected procedure, and the immediately following procedure:",
                "",
                "```xml",
                row.surrounding_xml_context,
                "```",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    frame = build_rows()
    csv_path = OUTPUT / "unmatched_2013_883980_provenance.csv"
    md_path = OUTPUT / "unmatched_2013_883980_provenance.md"
    frame.to_csv(csv_path, index=False)
    md_path.write_text(markdown_report(frame), encoding="utf-8")
    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")
    print(f"Files: {frame.source_filename.nunique()}, literal occurrences: {len(frame)}")
    print(f"Final status: {FINAL_STATUS}")


if __name__ == "__main__":
    main()
