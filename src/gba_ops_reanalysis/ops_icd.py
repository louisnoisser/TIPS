"""Generic OPS and ICD extraction helpers for single-year G-BA XML cohorts."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pandas as pd

from .gba_xml import (
    aggregate_counts,
    build_full_address,
    code_in_range,
    extract_contact_info,
    iter_diagnosis_counts,
    iter_procedure_counts,
    parse_file_identity,
    report_files,
)

TargetRules = dict[str, dict[str, list[Any]]]


def slugify_label(label: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in label.strip())
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_")


def target_case_column(label: str) -> str:
    return f"{slugify_label(label)}_cases"


def target_codes_column(label: str) -> str:
    return f"{slugify_label(label)}_matched_codes"


def parse_selector(selector: str) -> dict[str, list[Any]]:
    rules: dict[str, list[Any]] = {
        "prefixes": [],
        "ranges": [],
        "exclude_prefixes": [],
    }
    for raw_token in selector.split(","):
        token = raw_token.strip()
        if not token:
            continue
        exclude = token.startswith("!")
        token = token[1:] if exclude else token

        if (
            "-" in token
            and token[0].isalpha()
            and token.split("-", 1)[0]
            and token.split("-", 1)[1]
            and token.split("-", 1)[0][0].isalpha()
        ):
            start_code, end_code = token.split("-", 1)
            rules["ranges"].append((start_code.strip(), end_code.strip()))
            continue

        key = "exclude_prefixes" if exclude else "prefixes"
        rules[key].append(token)
    return rules


def parse_target_specs(specs: list[str]) -> TargetRules:
    targets: TargetRules = {}
    for spec in specs:
        if "=" not in spec:
            raise ValueError(f"Target must use label=selector syntax: {spec}")
        label, selector = spec.split("=", 1)
        label = label.strip()
        selector = selector.strip()
        if not label or not selector:
            raise ValueError(f"Invalid target specification: {spec}")
        targets[label] = parse_selector(selector)
    return targets


def matches_rules(code: str, rules: dict[str, list[Any]]) -> bool:
    if not code:
        return False
    if any(code.startswith(prefix) for prefix in rules.get("exclude_prefixes", [])):
        return False
    if any(code_in_range(code, start_code, end_code) for start_code, end_code in rules.get("ranges", [])):
        return True
    return any(code.startswith(prefix) for prefix in rules.get("prefixes", []))


def _first_non_empty(values: pd.Series) -> str:
    for value in values:
        if pd.notna(value):
            text = str(value).strip()
            if text and text.lower() != "nan":
                return text
    return ""


def extract_hospital_code_totals(
    xml_dir: Path,
    *,
    ops_targets: TargetRules | None = None,
    icd_targets: TargetRules | None = None,
    pattern: str = "*-xml.xml",
) -> pd.DataFrame:
    ops_targets = ops_targets or {}
    icd_targets = icd_targets or {}
    files = report_files(xml_dir, pattern=pattern)
    if not files:
        raise FileNotFoundError(f"No report files found in {xml_dir} with pattern {pattern}")

    rows: list[dict[str, Any]] = []
    fallback_year = int(xml_dir.name.replace("xml_", "")) if xml_dir.name.startswith("xml_") else None

    for index, file_path in enumerate(files, start=1):
        if index % 500 == 0:
            print(f"  parsed {index}/{len(files)} XML files")
        try:
            root = ET.parse(file_path).getroot()
        except Exception:
            continue

        info = extract_contact_info(root)
        ik, standortnummer, year = parse_file_identity(file_path, fallback_year=fallback_year)
        facility_id = f"{ik}-{standortnummer}".strip("-") or file_path.stem
        diagnosis_counts = aggregate_counts(iter_diagnosis_counts(root))
        procedure_counts = aggregate_counts(iter_procedure_counts(root))

        row: dict[str, Any] = {
            "year": year,
            "facility_id": facility_id,
            "ik": ik,
            "standortnummer": standortnummer,
            "hospital_name": info["hospital_name"],
            "street": info["street"],
            "house_number": info["house_number"],
            "postal_code": info["postal_code"],
            "city": info["city"],
            "phone": info["phone"],
            "email": info["email"],
            "full_address": build_full_address(info),
            "file_name": file_path.name,
        }

        for label, rules in ops_targets.items():
            matched = sorted(code for code in procedure_counts if matches_rules(code, rules))
            row[target_case_column(label)] = int(sum(procedure_counts[code] for code in matched))
            row[target_codes_column(label)] = "|".join(matched)

        for label, rules in icd_targets.items():
            matched = sorted(code for code in diagnosis_counts if matches_rules(code, rules))
            row[target_case_column(label)] = int(sum(diagnosis_counts[code] for code in matched))
            row[target_codes_column(label)] = "|".join(matched)

        rows.append(row)

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame

    group_cols = ["year", "facility_id"]
    count_cols = [col for col in frame.columns if col.endswith("_cases")]
    code_cols = [col for col in frame.columns if col.endswith("_matched_codes")]

    aggregated = (
        frame.groupby(group_cols, dropna=False)
        .agg(
            {
                "ik": _first_non_empty,
                "standortnummer": _first_non_empty,
                "hospital_name": _first_non_empty,
                "street": _first_non_empty,
                "house_number": _first_non_empty,
                "postal_code": _first_non_empty,
                "city": _first_non_empty,
                "phone": _first_non_empty,
                "email": _first_non_empty,
                "full_address": _first_non_empty,
                "file_name": _first_non_empty,
                **{col: "sum" for col in count_cols},
                **{
                    col: lambda series: "|".join(
                        sorted({token for value in series for token in str(value).split("|") if token})
                    )
                    for col in code_cols
                },
            }
        )
        .reset_index()
        .sort_values(group_cols)
        .reset_index(drop=True)
    )
    return aggregated


def add_threshold_flags(df: pd.DataFrame, labels: list[str], thresholds: list[int]) -> pd.DataFrame:
    result = df.copy()
    for label in labels:
        case_col = target_case_column(label)
        if case_col not in result.columns:
            continue
        for threshold in thresholds:
            result[f"{slugify_label(label)}_ge_{threshold}"] = result[case_col] >= threshold
    return result


def build_ops_target_summary(df: pd.DataFrame, labels: list[str], thresholds: list[int]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label in labels:
        case_col = target_case_column(label)
        if case_col not in df.columns:
            continue
        row: dict[str, Any] = {
            "target_label": label,
            "case_column": case_col,
            "hospitals_any": int((df[case_col] > 0).sum()),
            "cases_total": int(df[case_col].sum()),
            "median_cases_active_hospital": float(df.loc[df[case_col] > 0, case_col].median())
            if (df[case_col] > 0).any()
            else 0.0,
        }
        for threshold in thresholds:
            row[f"hospitals_ge_{threshold}"] = int((df[case_col] >= threshold).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def build_threshold_centers(
    df: pd.DataFrame,
    *,
    ops_labels: list[str],
    icd_labels: list[str],
    thresholds: list[int],
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    base_columns = [
        "year",
        "facility_id",
        "ik",
        "standortnummer",
        "hospital_name",
        "street",
        "house_number",
        "postal_code",
        "city",
        "phone",
        "email",
        "full_address",
        "file_name",
    ]
    for label in ops_labels:
        case_col = target_case_column(label)
        codes_col = target_codes_column(label)
        if case_col not in df.columns:
            continue
        icd_case_cols = [target_case_column(icd_label) for icd_label in icd_labels if target_case_column(icd_label) in df.columns]
        icd_code_cols = [target_codes_column(icd_label) for icd_label in icd_labels if target_codes_column(icd_label) in df.columns]
        for threshold in thresholds:
            subset = df.loc[df[case_col] >= threshold, base_columns + [case_col, codes_col] + icd_case_cols + icd_code_cols].copy()
            if subset.empty:
                continue
            subset["target_label"] = label
            subset["threshold"] = threshold
            subset["ops_cases"] = subset[case_col]
            subset["ops_matched_codes"] = subset[codes_col]
            subset = subset.drop(columns=[case_col, codes_col])
            rows.append(subset)
    if not rows:
        return pd.DataFrame()
    combined = pd.concat(rows, ignore_index=True)
    return combined.sort_values(["target_label", "threshold", "ops_cases"], ascending=[True, True, False]).reset_index(drop=True)


def write_target_metadata(
    output_path: Path,
    *,
    xml_dir: Path,
    ops_targets: TargetRules,
    icd_targets: TargetRules,
    thresholds: list[int],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "xml_dir": str(xml_dir),
                "ops_targets": ops_targets,
                "icd_targets": icd_targets,
                "thresholds": thresholds,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

