"""Longitudinal OPS and ICD summary helpers across yearly XML folders."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pandas as pd

from .gba_xml import (
    extract_contact_info,
    find_first_text,
    iter_diagnosis_counts,
    iter_procedure_counts,
    parse_file_identity,
    report_files,
    discover_year_dirs,
)
from .ops_icd import TargetRules, matches_rules, parse_target_specs, slugify_label, target_case_column


def _ratio(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return round(100.0 * numerator / denominator, 2)


def summarize_year(
    xml_dir: Path,
    *,
    ops_targets: TargetRules,
    icd_targets: TargetRules,
    summary_threshold: int = 25,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    year = int(xml_dir.name.replace("xml_", ""))
    files = report_files(xml_dir)
    if not files:
        raise FileNotFoundError(f"No report files found in {xml_dir}")

    facilities: dict[str, dict[str, Any]] = {}
    schema: dict[str, Any] = {
        "year": year,
        "report_file_count": len(files),
        "files_with_contact_tags": 0,
        "files_with_hauptdiagnose": 0,
        "files_with_prozedur": 0,
        "files_with_ops_301": 0,
        "files_with_icd_10": 0,
    }
    for label in ops_targets:
        schema[f"{slugify_label(label)}_codes_present"] = set()
    for label in icd_targets:
        schema[f"{slugify_label(label)}_codes_present"] = set()

    for index, file_path in enumerate(files, start=1):
        if index % 500 == 0:
            print(f"  {xml_dir.name}: parsed {index}/{len(files)} reports")
        try:
            root = ET.parse(file_path).getroot()
        except Exception:
            continue

        ik, standortnummer, parsed_year = parse_file_identity(file_path, fallback_year=year)
        facility_id = f"{ik}-{standortnummer}".strip("-") or file_path.stem
        row = facilities.setdefault(
            facility_id,
            {
                "year": parsed_year,
                "facility_id": facility_id,
                "ik": ik,
                "standortnummer": standortnummer,
                "hospital_name": "",
                "city": "",
                "postal_code": "",
                "street": "",
                "house_number": "",
                "phone": "",
                "email": "",
                "source_file_count": 0,
                **{target_case_column(label): 0 for label in ops_targets},
                **{target_case_column(label): 0 for label in icd_targets},
            },
        )
        row["source_file_count"] = int(row["source_file_count"]) + 1

        contact = extract_contact_info(root)
        if any(contact.values()):
            schema["files_with_contact_tags"] += 1
            for key, value in contact.items():
                if value and not row[key]:
                    row[key] = value

        diagnoses = list(iter_diagnosis_counts(root))
        procedures = list(iter_procedure_counts(root))
        if diagnoses:
            schema["files_with_hauptdiagnose"] += 1
        if procedures:
            schema["files_with_prozedur"] += 1
        if root.find(".//ICD_10") is not None:
            schema["files_with_icd_10"] += 1
        if root.find(".//OPS_301") is not None:
            schema["files_with_ops_301"] += 1

        for code, cases in diagnoses:
            for label, rules in icd_targets.items():
                if matches_rules(code, rules):
                    row[target_case_column(label)] = int(row[target_case_column(label)]) + int(cases)
                    schema[f"{slugify_label(label)}_codes_present"].add(code)

        for code, cases in procedures:
            for label, rules in ops_targets.items():
                if matches_rules(code, rules):
                    row[target_case_column(label)] = int(row[target_case_column(label)]) + int(cases)
                    schema[f"{slugify_label(label)}_codes_present"].add(code)

    hospital_df = pd.DataFrame(facilities.values()).sort_values(["year", "facility_id"]).reset_index(drop=True)
    for label in ops_targets:
        slug = slugify_label(label)
        case_col = target_case_column(label)
        hospital_df[f"{slug}_ge_10"] = hospital_df[case_col] >= 10
        hospital_df[f"{slug}_ge_{summary_threshold}"] = hospital_df[case_col] >= summary_threshold

    yearly: dict[str, Any] = {
        "year": year,
        "report_file_count": int(len(files)),
        "reporting_facilities": int(len(hospital_df)),
    }

    for label in icd_targets:
        case_col = target_case_column(label)
        slug = slugify_label(label)
        yearly[f"{slug}_facilities_any"] = int((hospital_df[case_col] > 0).sum())
        yearly[f"{slug}_cases_total"] = int(hospital_df[case_col].sum())

    for label in ops_targets:
        case_col = target_case_column(label)
        slug = slugify_label(label)
        active = hospital_df.loc[hospital_df[case_col] > 0, case_col]
        yearly[f"{slug}_hospitals_any"] = int((hospital_df[case_col] > 0).sum())
        yearly[f"{slug}_hospitals_10plus"] = int((hospital_df[case_col] >= 10).sum())
        yearly[f"{slug}_hospitals_{summary_threshold}plus"] = int(
            (hospital_df[case_col] >= summary_threshold).sum()
        )
        yearly[f"{slug}_cases_total"] = int(hospital_df[case_col].sum())
        yearly[f"{slug}_median_cases_active_hospital"] = float(active.median()) if not active.empty else 0.0
        yearly[f"{slug}_p90_cases_active_hospital"] = float(active.quantile(0.9)) if not active.empty else 0.0
        yearly[f"{slug}_share_cases_in_{summary_threshold}plus_hospitals"] = _ratio(
            float(hospital_df.loc[hospital_df[case_col] >= summary_threshold, case_col].sum()),
            float(yearly[f"{slug}_cases_total"]),
        )

    if len(ops_targets) == 2:
        first, second = list(ops_targets)[:2]
        first_col = target_case_column(first)
        second_col = target_case_column(second)
        first_slug = slugify_label(first)
        second_slug = slugify_label(second)
        yearly[f"{first_slug}_{second_slug}_hospitals_any"] = int(
            ((hospital_df[first_col] > 0) & (hospital_df[second_col] > 0)).sum()
        )
        yearly[f"{first_slug}_{second_slug}_hospitals_{summary_threshold}plus"] = int(
            (
                (hospital_df[first_col] >= summary_threshold)
                & (hospital_df[second_col] >= summary_threshold)
            ).sum()
        )

    for key, value in list(schema.items()):
        if isinstance(value, set):
            schema[key] = "|".join(sorted(value))

    return hospital_df, yearly, schema


def run_longitudinal_pipeline(
    *,
    base_dir: Path,
    out_dir: Path,
    ops_targets: TargetRules,
    icd_targets: TargetRules,
    denominator_label: str | None = None,
    summary_threshold: int = 25,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    year_dirs = discover_year_dirs(base_dir)
    if not year_dirs:
        raise FileNotFoundError(f"No xml_<year> directories found below {base_dir}")

    hospital_frames: list[pd.DataFrame] = []
    yearly_rows: list[dict[str, Any]] = []
    schema_rows: list[dict[str, Any]] = []

    for xml_dir in year_dirs:
        print(f"Processing {xml_dir.name} ...")
        hospital_df, yearly_row, schema_row = summarize_year(
            xml_dir,
            ops_targets=ops_targets,
            icd_targets=icd_targets,
            summary_threshold=summary_threshold,
        )
        hospital_frames.append(hospital_df)
        yearly_rows.append(yearly_row)
        schema_rows.append(schema_row)

    hospital_year = pd.concat(hospital_frames, ignore_index=True).sort_values(["year", "facility_id"]).reset_index(drop=True)
    yearly_summary = pd.DataFrame(yearly_rows).sort_values("year").reset_index(drop=True)
    schema_check = pd.DataFrame(schema_rows).sort_values("year").reset_index(drop=True)

    if denominator_label and denominator_label in icd_targets:
        denominator_slug = slugify_label(denominator_label)
        denominator_col = f"{denominator_slug}_cases_total"
        for label in ops_targets:
            slug = slugify_label(label)
            yearly_summary[f"{slug}_pct_of_{denominator_slug}"] = yearly_summary.apply(
                lambda row: _ratio(float(row[f"{slug}_cases_total"]), float(row.get(denominator_col, 0))),
                axis=1,
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    hospital_path = out_dir / "gba_longitudinal_hospital_year.csv"
    yearly_path = out_dir / "gba_longitudinal_yearly_summary.csv"
    schema_path = out_dir / "gba_longitudinal_schema_check.csv"
    sources_path = out_dir / "gba_longitudinal_sources.json"

    hospital_year.to_csv(hospital_path, index=False)
    yearly_summary.to_csv(yearly_path, index=False)
    schema_check.to_csv(schema_path, index=False)
    sources_path.write_text(
        json.dumps(
            {
                "base_dir": str(base_dir),
                "year_dirs": [path.name for path in year_dirs],
                "ops_targets": ops_targets,
                "icd_targets": icd_targets,
                "denominator_label": denominator_label,
                "summary_threshold": summary_threshold,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return hospital_year, yearly_summary, schema_check


__all__ = [
    "parse_target_specs",
    "run_longitudinal_pipeline",
]
