"""Sensitivity analysis for privacy-suppressed TIPS OPS counts."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .gba_xml import (
    COUNT_NAMES,
    PROCEDURE_CODE_NAMES,
    PROCEDURE_PATTERNS,
    discover_year_dirs,
    extract_contact_info,
    find_first_int,
    find_first_text,
    parse_file_identity,
    report_files,
)

TIPS_PREFIX = "8-839.8"
THRESHOLDS = (20, 50, 100, 200)
SCENARIO_COLUMNS = {
    "visible-only": "visible_count",
    "lower-bound": "lower_count",
    "midpoint": "midpoint_count",
    "upper-bound": "upper_count",
}
EXPECTED_VISIBLE_2024 = {
    "active_centers": 113,
    "cases_total": 5_247,
    "centers_ge_20": 60,
    "centers_lt_20": 53,
    "cases_lt_20": 568,
}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _suppression_tags(procedure: ET.Element) -> list[str]:
    """Return privacy tag names, never their metadata values."""
    return sorted(
        {
            _local_name(element.tag)
            for element in procedure.iter()
            if element is not procedure and "datenschutz" in _local_name(element.tag).lower()
        }
    )


def parse_tips_procedure(procedure: ET.Element) -> dict[str, Any] | None:
    """Parse one TIPS procedure into visible and imputed scenario counts."""
    code = find_first_text(procedure, PROCEDURE_CODE_NAMES).strip()
    if not code.lower().startswith(TIPS_PREFIX.lower()):
        return None

    visible_count = find_first_int(procedure, COUNT_NAMES)
    privacy_tags = _suppression_tags(procedure)
    suppression_flag = bool(privacy_tags)

    # Nested values such as Anzahl_FA_Datenschutz=1 are metadata. Only direct
    # normal count fields contribute to visible_count; each privacy entry adds
    # exactly one imputed unit per sensitivity multiplier.
    return {
        "ops_code": code,
        "visible_count": int(visible_count),
        "suppression_flag": suppression_flag,
        "suppression_tags": "|".join(privacy_tags),
        "lower_count": int(visible_count + (1 if suppression_flag else 0)),
        "midpoint_count": int(visible_count + (2 if suppression_flag else 0)),
        "upper_count": int(visible_count + (3 if suppression_flag else 0)),
    }


def iter_tips_entries(root: ET.Element) -> Iterable[dict[str, Any]]:
    for pattern in PROCEDURE_PATTERNS:
        for procedure in root.findall(pattern):
            parsed = parse_tips_procedure(procedure)
            if parsed is not None:
                yield parsed


def parse_tips_entry_panel(base_xml_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    files_scanned = 0
    files_parsed = 0
    parse_errors = 0
    excluded_privacy_by_year_and_element: dict[tuple[int, str], int] = {}
    pipeline_element_names = {pattern.replace(".//", "") for pattern in PROCEDURE_PATTERNS}

    for year_dir in discover_year_dirs(base_xml_dir):
        year = int(year_dir.name.replace("xml_", ""))
        for file_path in report_files(year_dir):
            files_scanned += 1
            payload = file_path.read_bytes()
            if TIPS_PREFIX.encode("ascii") not in payload:
                continue
            try:
                root = ET.fromstring(payload)
            except ET.ParseError:
                parse_errors += 1
                continue
            files_parsed += 1

            entries = list(iter_tips_entries(root))
            for element in root.iter():
                element_name = _local_name(element.tag)
                if element_name in pipeline_element_names:
                    continue
                parsed_outside_scope = parse_tips_procedure(element)
                if parsed_outside_scope and parsed_outside_scope["suppression_flag"]:
                    key = (year, element_name)
                    excluded_privacy_by_year_and_element[key] = excluded_privacy_by_year_and_element.get(key, 0) + 1
            if not entries:
                continue
            ik, standortnummer, parsed_year = parse_file_identity(file_path, fallback_year=year)
            facility_id = f"{ik}-{standortnummer}".strip("-") or file_path.stem
            contact = extract_contact_info(root)
            for entry_number, entry in enumerate(entries, start=1):
                rows.append(
                    {
                        "year": int(parsed_year or year),
                        "facility_id": facility_id,
                        "ik": ik,
                        "standortnummer": standortnummer,
                        "hospital_name": contact["hospital_name"],
                        "city": contact["city"],
                        "postal_code": contact["postal_code"],
                        "source_file": str(file_path),
                        "entry_number": entry_number,
                        **entry,
                    }
                )

    entry_panel = pd.DataFrame(rows)
    if entry_panel.empty:
        raise RuntimeError(f"No TIPS entries found below {base_xml_dir}")
    entry_panel = entry_panel.sort_values(
        ["year", "facility_id", "entry_number"]
    ).reset_index(drop=True)
    metadata = {
        "base_xml_dir": str(base_xml_dir),
        "year_dirs": [path.name for path in discover_year_dirs(base_xml_dir)],
        "files_scanned": files_scanned,
        "files_with_tips_text_parsed": files_parsed,
        "parse_errors": parse_errors,
        "tips_entries": int(len(entry_panel)),
        "suppressed_entries": int(entry_panel["suppression_flag"].sum()),
        "excluded_privacy_entries_outside_pipeline_scope": int(sum(excluded_privacy_by_year_and_element.values())),
        "excluded_privacy_entries_by_year_and_element": {
            f"{year}:{element_name}": count
            for (year, element_name), count in sorted(excluded_privacy_by_year_and_element.items())
        },
    }
    return entry_panel, metadata


def _representative_text(values: pd.Series) -> str:
    cleaned = [str(value).strip() for value in values.fillna("") if str(value).strip()]
    return cleaned[-1] if cleaned else ""


def build_facility_year(entry_panel: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        entry_panel.groupby(["year", "facility_id"], dropna=False)
        .agg(
            ik=("ik", _representative_text),
            standortnummer=("standortnummer", _representative_text),
            hospital_name=("hospital_name", _representative_text),
            city=("city", _representative_text),
            postal_code=("postal_code", _representative_text),
            source_file=("source_file", _representative_text),
            tips_entries=("ops_code", "size"),
            suppressed_entries=("suppression_flag", "sum"),
            visible_count=("visible_count", "sum"),
            lower_count=("lower_count", "sum"),
            midpoint_count=("midpoint_count", "sum"),
            upper_count=("upper_count", "sum"),
            matched_codes=("ops_code", lambda s: "|".join(sorted(set(s)))),
        )
        .reset_index()
    )
    grouped["suppressed_entries"] = grouped["suppressed_entries"].astype(int)
    grouped["has_visible"] = grouped["visible_count"] > 0
    grouped["has_suppression"] = grouped["suppressed_entries"] > 0
    grouped["activity_type"] = np.select(
        [
            grouped["has_visible"] & grouped["has_suppression"],
            grouped["has_visible"],
            grouped["has_suppression"],
        ],
        ["visible-plus-suppressed", "visible-only", "suppression-only"],
        default="no-count",
    )
    return grouped.sort_values(["year", "facility_id"]).reset_index(drop=True)


def build_ik_year(facility_year: pd.DataFrame) -> pd.DataFrame:
    return (
        facility_year.groupby(["year", "ik"], dropna=False)
        .agg(
            hospital_name=("hospital_name", _representative_text),
            city=("city", _representative_text),
            facilities=("facility_id", "nunique"),
            tips_entries=("tips_entries", "sum"),
            suppressed_entries=("suppressed_entries", "sum"),
            visible_count=("visible_count", "sum"),
            lower_count=("lower_count", "sum"),
            midpoint_count=("midpoint_count", "sum"),
            upper_count=("upper_count", "sum"),
        )
        .reset_index()
        .sort_values(["year", "ik"])
        .reset_index(drop=True)
    )


def _gini(values: pd.Series) -> float:
    arr = np.sort(pd.to_numeric(values, errors="coerce").fillna(0).astype(float).to_numpy())
    if len(arr) == 0 or arr.sum() <= 0:
        return 0.0
    index = np.arange(1, len(arr) + 1)
    return float((2 * np.sum(index * arr) / (len(arr) * arr.sum())) - (len(arr) + 1) / len(arr))


def build_yearly_metrics(panel: pd.DataFrame, *, id_col: str, level: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    years = sorted(int(year) for year in panel["year"].unique())
    for scenario, count_col in SCENARIO_COLUMNS.items():
        previous_active: set[str] | None = None
        previous_year: int | None = None
        for year in years:
            group = panel.loc[panel["year"] == year].copy()
            active = group.loc[group[count_col] > 0].copy()
            values = active[count_col].astype(float)
            total = float(values.sum())
            sorted_values = values.sort_values(ascending=False)
            shares = values / total if total else pd.Series(dtype=float)
            active_ids = set(active[id_col].astype(str))
            entered = exited = 0
            turnover = np.nan
            if previous_active is not None:
                entered = len(active_ids - previous_active)
                exited = len(previous_active - active_ids)
                union = active_ids | previous_active
                turnover = 100.0 * (entered + exited) / len(union) if union else 0.0
            rows.append(
                {
                    "level": level,
                    "scenario": scenario,
                    "year": year,
                    "previous_year": previous_year,
                    "active_centers": int(len(active)),
                    "national_volume": int(total),
                    "top_5_share_pct": round(100 * sorted_values.head(5).sum() / total, 4) if total else 0.0,
                    "top_10_share_pct": round(100 * sorted_values.head(10).sum() / total, 4) if total else 0.0,
                    "top_20_share_pct": round(100 * sorted_values.head(20).sum() / total, 4) if total else 0.0,
                    "hhi_10000": round(float(np.square(shares).sum() * 10_000), 4) if total else 0.0,
                    "effective_center_count": round(float(1 / np.square(shares).sum()), 4)
                    if total and np.square(shares).sum()
                    else 0.0,
                    "gini": round(_gini(values), 6),
                    "median": float(values.median()) if not values.empty else 0.0,
                    "minimum": int(values.min()) if not values.empty else 0,
                    "maximum": int(values.max()) if not values.empty else 0,
                    "range": f"{int(values.min())}-{int(values.max())}" if not values.empty else "0-0",
                    "entered_since_previous": entered,
                    "exited_since_previous": exited,
                    "turnover_pct": round(float(turnover), 4) if pd.notna(turnover) else np.nan,
                }
            )
            previous_active = active_ids
            previous_year = year
    return pd.DataFrame(rows).sort_values(["level", "scenario", "year"]).reset_index(drop=True)


def build_point_threshold_summary(facility_year: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for scenario, count_col in SCENARIO_COLUMNS.items():
        for year, group in facility_year.groupby("year"):
            active = group.loc[group[count_col] > 0]
            for threshold in THRESHOLDS:
                below = active.loc[active[count_col] < threshold]
                above = active.loc[active[count_col] >= threshold]
                rows.append(
                    {
                        "scenario": scenario,
                        "year": int(year),
                        "threshold": threshold,
                        "active_centers": int(len(active)),
                        "centers_below": int(len(below)),
                        "cases_below": int(below[count_col].sum()),
                        "centers_at_or_above": int(len(above)),
                        "cases_at_or_above": int(above[count_col].sum()),
                    }
                )
    return pd.DataFrame(rows).sort_values(["scenario", "year", "threshold"]).reset_index(drop=True)


def build_interval_classification(facility_year: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    active = facility_year.loc[facility_year["upper_count"] > 0]
    identity_cols = [
        "year",
        "facility_id",
        "ik",
        "hospital_name",
        "city",
        "activity_type",
        "suppressed_entries",
        "visible_count",
        "lower_count",
        "midpoint_count",
        "upper_count",
    ]
    for _, row in active.iterrows():
        base = {column: row[column] for column in identity_cols}
        for threshold in THRESHOLDS:
            if row["upper_count"] < threshold:
                classification = "definitely_below"
            elif row["lower_count"] >= threshold:
                classification = "definitely_above"
            else:
                classification = "uncertain"
            rows.append({**base, "threshold": threshold, "classification": classification})
    return pd.DataFrame(rows).sort_values(["year", "threshold", "classification", "facility_id"]).reset_index(drop=True)


def build_interval_summary(classification: pd.DataFrame) -> pd.DataFrame:
    expected = ["definitely_below", "uncertain", "definitely_above"]
    summary = (
        classification.groupby(["year", "threshold", "classification"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=expected, fill_value=0)
        .reset_index()
    )
    summary["active_centers"] = summary[expected].sum(axis=1)
    return summary


def validate_visible_2024(facility_year: pd.DataFrame, reference_report_dir: Path) -> dict[str, Any]:
    latest = facility_year.loc[facility_year["year"] == 2024]
    active = latest.loc[latest["visible_count"] > 0]
    below = active.loc[active["visible_count"] < 20]
    actual = {
        "active_centers": int(len(active)),
        "cases_total": int(active["visible_count"].sum()),
        "centers_ge_20": int((active["visible_count"] >= 20).sum()),
        "centers_lt_20": int(len(below)),
        "cases_lt_20": int(below["visible_count"].sum()),
    }
    differences = {
        key: {"expected": expected, "actual": actual[key]}
        for key, expected in EXPECTED_VISIBLE_2024.items()
        if actual[key] != expected
    }

    reference_path = reference_report_dir / "tables" / "latest_year_hospital_code_totals.csv"
    if not reference_path.exists():
        differences["reference_file"] = {"expected": str(reference_path), "actual": "missing"}
    else:
        reference = pd.read_csv(reference_path)
        reference = reference.loc[reference["tips_cases"] > 0, ["facility_id", "tips_cases"]]
        observed = active[["facility_id", "visible_count"]].rename(columns={"visible_count": "tips_cases"})
        merged = reference.merge(observed, on="facility_id", how="outer", suffixes=("_reference", "_observed"))
        mismatched = merged.loc[
            merged["tips_cases_reference"].fillna(-1) != merged["tips_cases_observed"].fillna(-1)
        ]
        if not mismatched.empty:
            differences["facility_case_rows"] = {
                "expected": "exact match to final 2024 table",
                "actual": f"{len(mismatched)} mismatched rows",
            }

    if differences:
        raise RuntimeError(
            "Visible-only regression failed; no sensitivity outputs were written. "
            + json.dumps(differences, ensure_ascii=False)
        )
    return {"status": "passed", "expected": EXPECTED_VISIBLE_2024, "actual": actual, "reference": str(reference_path)}


def build_2024_composition(facility_year: pd.DataFrame) -> pd.DataFrame:
    latest = facility_year.loc[facility_year["year"] == 2024]
    row: dict[str, Any] = {
        "year": 2024,
        "numerically_active_centers": int((latest["visible_count"] > 0).sum()),
        "suppression_only_centers": int((latest["activity_type"] == "suppression-only").sum()),
        "visible_plus_suppressed_centers": int((latest["activity_type"] == "visible-plus-suppressed").sum()),
        "visible_without_suppression_centers": int((latest["activity_type"] == "visible-only").sum()),
        "suppressed_entries": int(latest["suppressed_entries"].sum()),
    }
    for scenario, count_col in SCENARIO_COLUMNS.items():
        row[f"active_centers_{scenario}"] = int((latest[count_col] > 0).sum())
        row[f"national_volume_{scenario}"] = int(latest[count_col].sum())
    return pd.DataFrame([row])


def build_comparison(
    metrics: pd.DataFrame,
    threshold_summary: pd.DataFrame,
    interval_summary: pd.DataFrame,
) -> pd.DataFrame:
    selected = metrics.loc[(metrics["level"] == "facility") & metrics["year"].isin([2008, 2024])].copy()
    thresholds = threshold_summary.loc[threshold_summary["year"].isin([2008, 2024])].copy()
    above = thresholds.pivot(index=["scenario", "year"], columns="threshold", values="centers_at_or_above")
    above.columns = [f"centers_ge_{int(column)}" for column in above.columns]
    below20 = thresholds.loc[thresholds["threshold"] == 20, ["scenario", "year", "centers_below", "cases_below"]]
    uncertain = interval_summary.loc[interval_summary["year"].isin([2008, 2024])].pivot(
        index="year", columns="threshold", values="uncertain"
    )
    uncertain.columns = [f"uncertain_ge_{int(column)}" for column in uncertain.columns]
    result = selected.merge(above.reset_index(), on=["scenario", "year"], how="left")
    result = result.merge(below20, on=["scenario", "year"], how="left")
    result = result.merge(uncertain.reset_index(), on="year", how="left")
    keep = [
        "year",
        "scenario",
        "national_volume",
        "active_centers",
        "centers_below",
        "cases_below",
        "centers_ge_20",
        "centers_ge_50",
        "centers_ge_100",
        "centers_ge_200",
        "top_5_share_pct",
        "top_10_share_pct",
        "top_20_share_pct",
        "hhi_10000",
        "effective_center_count",
        "gini",
        "median",
        "range",
        "turnover_pct",
        "uncertain_ge_20",
        "uncertain_ge_50",
        "uncertain_ge_100",
        "uncertain_ge_200",
    ]
    return result[keep].sort_values(["year", "scenario"]).reset_index(drop=True)


def build_geography_membership_audit(facility_year: pd.DataFrame) -> pd.DataFrame:
    latest = facility_year.loc[(facility_year["year"] == 2024) & (facility_year["upper_count"] > 0)].copy()
    rows: list[dict[str, Any]] = []
    for _, row in latest.iterrows():
        for threshold in (20, 50, 100):
            record = {
                "facility_id": row["facility_id"],
                "ik": row["ik"],
                "hospital_name": row["hospital_name"],
                "activity_type": row["activity_type"],
                "suppressed_entries": row["suppressed_entries"],
                "visible_count": row["visible_count"],
                "lower_count": row["lower_count"],
                "midpoint_count": row["midpoint_count"],
                "upper_count": row["upper_count"],
                "threshold": threshold,
            }
            for scenario, count_col in SCENARIO_COLUMNS.items():
                record[f"included_{scenario}"] = bool(row[count_col] >= threshold)
            record["changes_vs_visible"] = any(
                record[f"included_{scenario}"] != record["included_visible-only"]
                for scenario in ("lower-bound", "midpoint", "upper-bound")
            )
            rows.append(record)
    return pd.DataFrame(rows).sort_values(["threshold", "changes_vs_visible", "facility_id"], ascending=[True, False, True])


def _markdown_table(frame: pd.DataFrame) -> list[str]:
    if frame.empty:
        return ["No rows."]
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(row[col]) else str(row[col]) for col in columns) + " |")
    return lines


def write_audit(
    output_dir: Path,
    *,
    metadata: dict[str, Any],
    regression: dict[str, Any],
    composition: pd.DataFrame,
    comparison: pd.DataFrame,
    interval_summary: pd.DataFrame,
    facility_year: pd.DataFrame,
    geography_audit: pd.DataFrame,
) -> None:
    latest_intervals = interval_summary.loc[interval_summary["year"] == 2024]
    suppression_only = facility_year.loc[
        (facility_year["year"] == 2024) & (facility_year["activity_type"] == "suppression-only")
    ]
    max_suppression_only_upper = int(suppression_only["upper_count"].max()) if not suppression_only.empty else 0
    changed_geo = (
        geography_audit.loc[geography_audit["changes_vs_visible"]]
        .groupby("threshold")
        .size()
        .rename("centers_with_any_membership_change")
        .reset_index()
    )
    lines = [
        "# TIPS Suppression Sensitivity Audit",
        "",
        "## Assumptions and parser logic",
        "",
        "- Each TIPS procedure entry carrying a privacy tag represents 1-3 cases.",
        "- Scenario values are additive per site: visible-only uses published integers; lower-bound adds 1, midpoint adds 2, and upper-bound adds 3 per suppressed entry.",
        "- Direct normal count tags are the only source of visible_count.",
        "- Nested privacy metadata such as Anzahl_FA_Datenschutz=1 is recorded only as a privacy tag and is never interpreted as a published case count.",
        "- Threshold interval classes are definitely_below when upper_count < threshold, uncertain when lower_count < threshold <= upper_count, and definitely_above when lower_count >= threshold.",
        "- Turnover is (entered + exited) / union of active site IDs versus the previous available report year. It is undefined for 2008.",
        "",
        "## Visible-only regression",
        "",
        f"Status: **{regression['status']}**",
        "",
        *(_markdown_table(pd.DataFrame([regression["actual"]]))),
        "",
        f"Reference: `{regression['reference']}`",
        "",
        "## XML scan",
        "",
        f"- Files scanned: {metadata['files_scanned']}",
        f"- TIPS entries parsed: {metadata['tips_entries']}",
        f"- Suppressed entries: {metadata['suppressed_entries']}",
        f"- Privacy entries outside the existing inpatient procedure scope: {metadata['excluded_privacy_entries_outside_pipeline_scope']}",
        f"- Excluded element breakdown: {metadata['excluded_privacy_entries_by_year_and_element']}",
        f"- XML parse errors: {metadata['parse_errors']}",
        "",
        "## 2024 composition",
        "",
        *(_markdown_table(composition)),
        "",
        "## 2024 interval classification",
        "",
        *(_markdown_table(latest_intervals)),
        "",
        "## 2008 and 2024 scenario comparison",
        "",
        *(_markdown_table(comparison)),
        "",
        "## Geography decision",
        "",
        "- Existing >=50 and >=100 isochrones and population-coverage outputs were not recalculated or modified.",
        f"- The largest 2024 suppression-only upper-bound site count is {max_suppression_only_upper}; therefore no suppression-only site can reach >=50 or >=100.",
        "- This suppression-only argument does not by itself exclude changes among mixed visible-plus-suppressed sites. Those observed membership changes are listed below and in `tables/geographic_threshold_membership_audit_2024.csv`.",
        "- Changes at >=20 are sensitivity classifications only and do not alter the canonical geographic analysis.",
        "",
        *(_markdown_table(changed_geo)),
        "",
        "## Output isolation",
        "",
        "All files in this directory are parallel sensitivity outputs. The canonical final report directory and its isochrone/coverage files were not written.",
    ]
    (output_dir / "SUPPRESSION_SENSITIVITY_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_suppression_sensitivity(
    *,
    base_xml_dir: Path,
    output_dir: Path,
    reference_report_dir: Path,
) -> dict[str, Any]:
    entry_panel, metadata = parse_tips_entry_panel(base_xml_dir)
    facility_year = build_facility_year(entry_panel)
    ik_year = build_ik_year(facility_year)

    # This runs before output_dir is created, so a regression failure leaves no
    # partial sensitivity result behind.
    regression = validate_visible_2024(facility_year, reference_report_dir)

    facility_metrics = build_yearly_metrics(facility_year, id_col="facility_id", level="facility")
    ik_metrics = build_yearly_metrics(ik_year, id_col="ik", level="ik")
    metrics = pd.concat([facility_metrics, ik_metrics], ignore_index=True)
    point_thresholds = build_point_threshold_summary(facility_year)
    interval_classification = build_interval_classification(facility_year)
    interval_summary = build_interval_summary(interval_classification)
    composition = build_2024_composition(facility_year)
    comparison = build_comparison(metrics, point_thresholds, interval_summary)
    geography_audit = build_geography_membership_audit(facility_year)
    suppression_distribution = (
        facility_year.loc[facility_year["suppressed_entries"] > 0]
        .groupby(["year", "suppressed_entries"])
        .size()
        .rename("centers")
        .reset_index()
        .sort_values(["year", "suppressed_entries"])
    )

    suppression_only_2024 = facility_year.loc[
        (facility_year["year"] == 2024) & (facility_year["activity_type"] == "suppression-only")
    ]
    if not suppression_only_2024.empty and int(suppression_only_2024["upper_count"].max()) >= 50:
        raise RuntimeError("A 2024 suppression-only site can reach >=50; geography non-recalculation is invalid.")

    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    entry_panel.to_csv(tables_dir / "tips_ops_entry_sensitivity.csv", index=False)
    facility_year.to_csv(tables_dir / "facility_year_sensitivity.csv", index=False)
    ik_year.to_csv(tables_dir / "ik_year_sensitivity.csv", index=False)
    metrics.to_csv(tables_dir / "yearly_scenario_metrics.csv", index=False)
    point_thresholds.to_csv(tables_dir / "point_threshold_summary.csv", index=False)
    interval_classification.to_csv(tables_dir / "threshold_interval_classification.csv", index=False)
    interval_summary.to_csv(tables_dir / "threshold_interval_summary.csv", index=False)
    composition.to_csv(tables_dir / "composition_2024.csv", index=False)
    suppression_distribution.to_csv(tables_dir / "suppressed_entries_distribution.csv", index=False)
    suppression_distribution.loc[suppression_distribution["year"] == 2024].to_csv(
        tables_dir / "suppressed_entries_distribution_2024.csv", index=False
    )
    comparison.to_csv(tables_dir / "comparison_2008_2024.csv", index=False)
    geography_audit.to_csv(tables_dir / "geographic_threshold_membership_audit_2024.csv", index=False)
    (tables_dir / "suppression_sensitivity_metadata.json").write_text(
        json.dumps(
            {
                **metadata,
                "scenarios": SCENARIO_COLUMNS,
                "thresholds": list(THRESHOLDS),
                "regression": regression,
                "reference_report_dir": str(reference_report_dir),
                "isochrones_recalculated": False,
                "population_coverage_recalculated": False,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    write_audit(
        output_dir,
        metadata=metadata,
        regression=regression,
        composition=composition,
        comparison=comparison,
        interval_summary=interval_summary,
        facility_year=facility_year,
        geography_audit=geography_audit,
    )
    return {
        "output_dir": str(output_dir),
        "regression": regression,
        "composition_2024": composition.iloc[0].to_dict(),
    }
