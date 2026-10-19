#!/usr/bin/env python3
"""Run the approved OPS-specific TIPS de-novo subcode sensitivity audit."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Any
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gba_ops_reanalysis.final_corrected import scenario_metrics  # noqa: E402
from gba_ops_reanalysis.site_resolution_validation import (  # noqa: E402
    THRESHOLDS,
    resolve_component_precedence,
    structural_metrics,
)
from gba_ops_reanalysis.suppression_sensitivity import iter_tips_entries  # noqa: E402


YEARS = tuple(range(2013, 2025))
TWO_CODES = ("8-839.87", "8-839.88")
FOUR_CODES = ("8-839.87", "8-839.88", "8-839.89", "8-839.8a")
ALL_SELECTED_CODES = FOUR_CODES
EXPECTED_HASHES = {
    "outputs/ops_code_audit_2013_2024/ops_code_reconciliation_site_year.csv":
        "294b0e5cfb44f4091322f2de25373a3c1d26754cf4bea2dbdee9f3d0bae7ba8d",
    "outputs/ops_code_audit_2013_2024/ops_code_audit_2013_2024.csv":
        "f51487d4339f6fac5f9dac5fa5420a26b27ea7331301d9abd225bbbb387e31a2",
    "outputs/ops_code_audit_2013_2024/ops_code_summary_2013_2024.csv":
        "366bfeb8b70553dc6948cc41ffc3ae90294ee9f733e6e3fa0b4d42128c7473b6",
}
INPUT_PATHS = (
    "outputs/ops_code_audit_2013_2024/ops_code_reconciliation_site_year.csv",
    "outputs/ops_code_audit_2013_2024/ops_code_audit_2013_2024.csv",
    "outputs/ops_code_audit_2013_2024/ops_code_summary_2013_2024.csv",
    "outputs/audit/tips_code_level_audit.csv",
    "outputs/site_resolution_validation/resolved_site_level_data.csv",
    "outputs/final_corrected_2026-07-24/suppression_final_metrics.csv",
    "src/gba_ops_reanalysis/site_resolution_validation.py",
    "src/gba_ops_reanalysis/final_corrected.py",
    "src/gba_ops_reanalysis/suppression_sensitivity.py",
)
ENDPOINT = "activity coded with specific de novo TIPS creation subcodes"
RECORD_PATTERN = re.compile(
    r"^(?P<code>[^:]+):visible=(?P<visible>\d+),"
    r"suppressed=(?P<suppressed>\d+),source=(?P<source>.+)$"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    return result.stdout.strip()


def file_record(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": relative(path),
        "absolute_path": str(path.resolve()),
        "size_bytes": stat.st_size,
        "modification_timestamp_utc": datetime.fromtimestamp(
            stat.st_mtime, timezone.utc
        ).isoformat(),
        "sha256": sha256_file(path),
    }


def applicable_codes(year: int) -> tuple[str, ...]:
    return TWO_CODES if year <= 2015 else FOUR_CODES


def regime(year: int) -> str:
    return "two-code (2013–2015)" if year <= 2015 else "four-code (2016–2024)"


def code_token(code: str) -> str:
    return code.replace("-", "_").replace(".", "_")


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    clean = frame.copy().fillna("").astype(str)
    clean = clean.apply(
        lambda col: col.str.replace("|", r"\|", regex=False).str.replace("\n", " ", regex=False)
    )
    header = "| " + " | ".join(clean.columns) + " |"
    rule = "| " + " | ".join("---" for _ in clean.columns) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in clean.itertuples(index=False, name=None)]
    return "\n".join([header, rule, *rows])


def verify_inputs() -> tuple[dict[str, Path], list[dict[str, Any]], dict[str, Any]]:
    paths = {item: ROOT / item for item in INPUT_PATHS}
    missing = [item for item, path in paths.items() if not path.is_file()]
    if missing:
        raise RuntimeError(f"Missing required input files: {missing}")
    records = [file_record(paths[item]) for item in INPUT_PATHS]
    for item, expected in EXPECTED_HASHES.items():
        actual = sha256_file(paths[item])
        if actual != expected:
            raise RuntimeError(f"Input hash gate failed for {item}: {actual} != {expected}")

    recon = pd.read_csv(paths[INPUT_PATHS[0]], dtype=str, keep_default_na=False)
    properties = {
        "rows": len(recon),
        "unique_physical_site_years": int(
            recon[["reporting_year", "physical_site_identifier"]].drop_duplicates().shape[0]
        ),
        "unique_institution_years": int(
            recon[["reporting_year", "institution_identifier"]].drop_duplicates().shape[0]
        ),
        "duplicate_physical_site_years": int(
            recon.duplicated(["reporting_year", "physical_site_identifier"]).sum()
        ),
        "mismatches": int(recon.reconciliation_status.ne("fully_reconciled").sum()),
        "unresolved": int(recon.resolved_vs_unresolved.eq("unresolved").sum()),
        "manual_review": int(recon.manual_review_flag.str.lower().isin({"true", "1", "yes"}).sum()),
    }
    expected_properties = {
        "rows": 2057,
        "unique_physical_site_years": 2057,
        "unique_institution_years": 1917,
        "duplicate_physical_site_years": 0,
        "mismatches": 0,
        "unresolved": 0,
        "manual_review": 0,
    }
    if properties != expected_properties:
        raise RuntimeError(f"Reconciliation property gate failed: {properties}")

    audit = pd.read_csv(paths[INPUT_PATHS[1]], dtype=str, keep_default_na=False)
    summary = pd.read_csv(paths[INPUT_PATHS[2]], dtype=str, keep_default_na=False)
    if len(audit) != 144 or len(summary) != 12:
        raise RuntimeError("Audit row-count gate failed")
    for year in YEARS:
        expected = set(applicable_codes(year))
        observed = set(
            audit.loc[
                audit.catalogue_year.astype(int).eq(year)
                & audit.code.isin(ALL_SELECTED_CODES)
                & audit.exists.eq("yes"),
                "code",
            ]
        )
        if observed != expected:
            raise RuntimeError(
                f"Historical code-set gate failed for {year}: {sorted(observed)}"
            )
    return paths, records, properties


def aggregate_selected_records(records: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    keys = ["reporting_year", "ik", "site_identifier"]
    for key, group in records.groupby(keys, sort=True, dropna=False):
        year = int(key[0])
        row: dict[str, Any] = {
            "reporting_year": year,
            "institution_id": str(key[1]),
            "physical_site_id": str(key[2]),
            "site_name": next((str(x) for x in group.site_name if str(x).strip()), ""),
            "contributing_selected_codes": "|".join(sorted(set(group.code_normalised))),
            "selected_source_files": "|".join(sorted(set(group.source_file.astype(str)))),
        }
        for code in ALL_SELECTED_CODES:
            subset = group[group.code_normalised.eq(code)]
            token = code_token(code)
            row[f"visible_{token}"] = int(subset.visible_value.sum())
            row[f"suppressed_entries_{token}"] = int(subset.suppressed_value.sum())
        row["de_novo_visible_activity"] = int(group.visible_value.sum())
        row["de_novo_suppressed_entry_count"] = int(group.suppressed_value.sum())
        rows.append(row)
    return pd.DataFrame(rows).sort_values(keys[:1] + ["physical_site_id"]).reset_index(drop=True)


def route_a(code_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    code = pd.read_csv(code_path, dtype={"ik": str}, keep_default_na=False)
    code["reporting_year"] = pd.to_numeric(code.reporting_year, errors="raise").astype(int)
    code["OPS_code"] = code.OPS_code.astype(str).str.strip()
    code["code_normalised"] = code.OPS_code.str.lower()
    annotated, _ = resolve_component_precedence(code)
    retained = annotated[
        annotated.reporting_year.isin(YEARS)
        & annotated.retained_site_resolution.astype(bool)
        & ~annotated.unresolved_institution_provider.astype(bool)
    ].copy()
    retained["code_normalised"] = retained.OPS_code.astype(str).str.strip().str.lower()
    applicable = retained.apply(
        lambda row: row.code_normalised in applicable_codes(int(row.reporting_year)), axis=1
    )
    selected = retained[applicable].copy()
    selected = selected.rename(
        columns={
            "hospital_name": "site_name",
            "visible_count": "visible_value",
            "suppressed_entries": "suppressed_value",
        }
    )
    selected["visible_value"] = pd.to_numeric(selected.visible_value).astype(int)
    selected["suppressed_value"] = pd.to_numeric(selected.suppressed_value).astype(int)
    selected["source_file"] = selected.source_file.astype(str)
    selected["source_path_matches_site_year"] = selected.apply(
        lambda row: Path(row.source_file).name.casefold()
        == f"{row.site_identifier}-{int(row.reporting_year)}-xml.xml".casefold(),
        axis=1,
    )
    selected["source_file_exists"] = selected.source_file.map(
        lambda value: (ROOT / value).is_file()
    )
    if not selected.source_path_matches_site_year.all() or not selected.source_file_exists.all():
        raise RuntimeError("Route A source-path/site-year validation failed")
    return aggregate_selected_records(selected), selected, annotated


def route_b(reconciliation_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    recon = pd.read_csv(reconciliation_path, dtype=str, keep_default_na=False)
    rows: list[dict[str, Any]] = []
    for parent in recon.itertuples(index=False):
        for text in str(parent.contributing_code_level_records).split(" || "):
            match = RECORD_PATTERN.fullmatch(text)
            if not match:
                raise RuntimeError(
                    f"Cannot parse contributing record for {parent.physical_site_identifier}: {text}"
                )
            code = match.group("code").strip().lower()
            year = int(parent.reporting_year)
            if code not in applicable_codes(year):
                continue
            source = match.group("source")
            rows.append(
                {
                    "reporting_year": year,
                    "ik": str(parent.institution_identifier),
                    "site_identifier": str(parent.physical_site_identifier),
                    "site_name": str(parent.site_name),
                    "code_normalised": code,
                    "visible_value": int(match.group("visible")),
                    "suppressed_value": int(match.group("suppressed")),
                    "source_file": source,
                    "source_path_matches_site_year": Path(source).name.casefold()
                    == f"{parent.physical_site_identifier}-{year}-xml.xml".casefold(),
                    "source_file_exists": (ROOT / source).is_file(),
                }
            )
    records = pd.DataFrame(rows)
    if records.empty:
        raise RuntimeError("Route B produced no selected records")
    if not records.source_path_matches_site_year.all() or not records.source_file_exists.all():
        raise RuntimeError("Route B source-path/site-year validation failed")
    return aggregate_selected_records(records), records


def compare_routes(a: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:
    keys = ["reporting_year", "institution_id", "physical_site_id"]
    compare_columns = [
        "contributing_selected_codes",
        *(f"visible_{code_token(code)}" for code in ALL_SELECTED_CODES),
        *(f"suppressed_entries_{code_token(code)}" for code in ALL_SELECTED_CODES),
        "de_novo_visible_activity",
        "de_novo_suppressed_entry_count",
    ]
    joined = a[keys + compare_columns].merge(
        b[keys + compare_columns], on=keys, how="outer", suffixes=("_route_a", "_route_b"),
        indicator=True, validate="one_to_one",
    )
    joined["identifier_agreement"] = joined._merge.eq("both")
    for column in compare_columns:
        joined[f"{column}_agreement"] = (
            joined[f"{column}_route_a"].fillna("__missing__").astype(str)
            == joined[f"{column}_route_b"].fillna("__missing__").astype(str)
        )
    agreement_columns = [x for x in joined if x.endswith("_agreement")]
    joined["all_route_fields_agree"] = joined[agreement_columns].all(axis=1)
    if not joined.all_route_fields_agree.all():
        failed = joined[~joined.all_route_fields_agree]
        raise RuntimeError(f"Route A/B disagreement in {len(failed)} physical site-years")
    return joined.drop(columns="_merge")


def build_site_year(
    route: pd.DataFrame, route_compare: pd.DataFrame, inclusive_path: Path,
    reconciliation_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    inclusive = pd.read_csv(inclusive_path, dtype={"ik": str}, keep_default_na=False)
    inclusive["reporting_year"] = pd.to_numeric(inclusive.reporting_year).astype(int)
    inclusive = inclusive[inclusive.reporting_year.isin(YEARS)].copy()
    inclusive = inclusive.rename(
        columns={"ik": "institution_id", "site_identifier": "physical_site_id"}
    )
    reconciliation = pd.read_csv(reconciliation_path, dtype=str, keep_default_na=False)
    reconciliation["reporting_year"] = reconciliation.reporting_year.astype(int)
    key_check = inclusive.merge(
        reconciliation,
        left_on=["reporting_year", "institution_id", "physical_site_id"],
        right_on=["reporting_year", "institution_identifier", "physical_site_identifier"],
        how="outer", indicator=True, validate="one_to_one",
    )
    if not key_check._merge.eq("both").all():
        raise RuntimeError("Final inclusive source and reconciliation keys differ")
    if not (
        pd.to_numeric(key_check.visible_activity).astype(int)
        == pd.to_numeric(key_check.main_analysis_visible_activity).astype(int)
    ).all() or not (
        pd.to_numeric(key_check.suppressed_entries).astype(int)
        == pd.to_numeric(key_check.main_analysis_suppressed_entry_count).astype(int)
    ).all():
        raise RuntimeError("Final inclusive source values differ from reconciliation")

    keep = inclusive[[
        "reporting_year", "institution_id", "physical_site_id", "visible_activity",
        "suppressed_entries", "reporting_unit_type",
    ]].rename(
        columns={
            "visible_activity": "inclusive_visible_activity",
            "suppressed_entries": "inclusive_suppressed_entry_count",
        }
    )
    output = route.merge(
        keep, on=["reporting_year", "institution_id", "physical_site_id"],
        how="left", validate="one_to_one",
    )
    if output.inclusive_visible_activity.isna().any():
        raise RuntimeError("Selected physical site-year missing from inclusive source")
    for column in ["inclusive_visible_activity", "inclusive_suppressed_entry_count"]:
        output[column] = pd.to_numeric(output[column]).astype(int)
    output["code_set_regime"] = output.reporting_year.map(regime)
    output["applicable_code_set"] = output.reporting_year.map(
        lambda year: "|".join(applicable_codes(int(year)))
    )
    for code in ("8-839.89", "8-839.8a"):
        token = code_token(code)
        mask = output.reporting_year.le(2015)
        output.loc[mask, f"visible_{token}"] = pd.NA
        output.loc[mask, f"suppressed_entries_{token}"] = pd.NA
    output["de_novo_minus_inclusive_visible"] = (
        output.de_novo_visible_activity - output.inclusive_visible_activity
    )
    output["de_novo_minus_inclusive_suppressed_entries"] = (
        output.de_novo_suppressed_entry_count - output.inclusive_suppressed_entry_count
    )
    output["identifiable_active_de_novo_site"] = True
    output["openly_numeric_de_novo_site"] = output.de_novo_visible_activity.gt(0)
    output["suppressed_only_de_novo_site"] = (
        output.de_novo_visible_activity.eq(0)
        & output.de_novo_suppressed_entry_count.gt(0)
    )
    output["any_selected_code_occurrence"] = (
        output.de_novo_visible_activity.gt(0)
        | output.de_novo_suppressed_entry_count.gt(0)
    )
    output["route_a_route_b_visible_agreement"] = True
    output["route_a_route_b_suppression_agreement"] = True
    output["de_novo_le_inclusive_visible_ok"] = (
        output.de_novo_visible_activity.le(output.inclusive_visible_activity)
    )
    output["selected_suppression_le_inclusive_suppression_ok"] = (
        output.de_novo_suppressed_entry_count.le(output.inclusive_suppressed_entry_count)
    )
    valid = (
        output.de_novo_le_inclusive_visible_ok
        & output.selected_suppression_le_inclusive_suppression_ok
        & output.any_selected_code_occurrence
    )
    output["validation_status"] = np.where(valid, "passed", "failed")
    output["validation_notes"] = np.where(valid, "all mandatory site-year gates passed", "inspect failed flags")
    columns = [
        "reporting_year", "institution_id", "physical_site_id", "site_name",
        "code_set_regime", "applicable_code_set", "contributing_selected_codes",
        *(f"visible_{code_token(code)}" for code in ALL_SELECTED_CODES),
        *(f"suppressed_entries_{code_token(code)}" for code in ALL_SELECTED_CODES),
        "de_novo_visible_activity", "de_novo_suppressed_entry_count",
        "inclusive_visible_activity", "inclusive_suppressed_entry_count",
        "de_novo_minus_inclusive_visible", "de_novo_minus_inclusive_suppressed_entries",
        "identifiable_active_de_novo_site", "openly_numeric_de_novo_site",
        "suppressed_only_de_novo_site", "any_selected_code_occurrence",
        "route_a_route_b_visible_agreement", "route_a_route_b_suppression_agreement",
        "de_novo_le_inclusive_visible_ok", "selected_suppression_le_inclusive_suppression_ok",
        "validation_status", "validation_notes",
    ]
    return output[columns].sort_values(["reporting_year", "physical_site_id"]), inclusive


def build_contributions(records: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for year in YEARS:
        for code in ALL_SELECTED_CODES:
            applicable = code in applicable_codes(year)
            subset = records[
                records.reporting_year.eq(year) & records.code_normalised.eq(code)
            ]
            values: dict[str, Any]
            if applicable:
                values = {
                    "openly_visible_national_activity": int(subset.visible_value.sum()),
                    "suppressed_entry_count": int(subset.suppressed_value.sum()),
                    "sites_with_openly_numeric_entry": int(
                        subset.loc[subset.visible_value.gt(0), "site_identifier"].nunique()
                    ),
                    "sites_with_suppressed_entry": int(
                        subset.loc[subset.suppressed_value.gt(0), "site_identifier"].nunique()
                    ),
                    "sites_with_either_entry_type": int(subset.site_identifier.nunique()),
                }
            else:
                values = {key: pd.NA for key in (
                    "openly_visible_national_activity", "suppressed_entry_count",
                    "sites_with_openly_numeric_entry", "sites_with_suppressed_entry",
                    "sites_with_either_entry_type",
                )}
            rows.append({
                "reporting_year": year,
                "code_set_regime": regime(year),
                "ops_code": code,
                "applicable_in_year": applicable,
                "availability_status": "applicable" if applicable else "not applicable—absent from annual catalogue",
                **values,
            })
    return pd.DataFrame(rows)


def build_concentration(site_year: pd.DataFrame) -> pd.DataFrame:
    panel = site_year.rename(
        columns={
            "de_novo_visible_activity": "visible_activity",
            "de_novo_suppressed_entry_count": "suppressed_entries",
        }
    ).copy()
    panel["lower_activity"] = panel.visible_activity + panel.suppressed_entries
    panel["midpoint_activity"] = panel.visible_activity + 2 * panel.suppressed_entries
    panel["upper_activity"] = panel.visible_activity + 3 * panel.suppressed_entries
    metrics = scenario_metrics(panel, "physical_site")
    scenario_columns = {
        "visible": "visible_activity", "lower": "lower_activity",
        "midpoint": "midpoint_activity", "upper": "upper_activity",
    }
    top1: list[float] = []
    statuses: list[str] = []
    reasons: list[str] = []
    for row in metrics.itertuples(index=False):
        values = pd.to_numeric(
            panel.loc[panel.reporting_year.eq(row.reporting_year), scenario_columns[row.suppression_scenario]],
            errors="coerce",
        ).fillna(0)
        active = values[values.gt(0)].sort_values(ascending=False)
        total = float(active.sum())
        top1.append(round(100 * float(active.head(1).sum()) / total, 4) if total else np.nan)
        statuses.append("defined" if total else "undefined")
        reasons.append("" if total else "no positive provider activity in scenario")
    metrics["top1_share_pct"] = top1
    metrics["providers_contributing_to_metrics"] = metrics.active_numeric_providers
    metrics["total_scenario_imputed_activity"] = metrics.visible_national_activity
    metrics["metric_status"] = statuses
    metrics["undefined_reason"] = reasons
    return metrics[[
        "reporting_year", "provider_definition", "suppression_scenario",
        "total_scenario_imputed_activity", "providers_contributing_to_metrics",
        "top1_share_pct", "top5_share_pct", "top10_share_pct", "top20_share_pct",
        "hhi_10000", "effective_center_count", "gini", "metric_status", "undefined_reason",
    ]]


def build_annual(
    site_year: pd.DataFrame, inclusive: pd.DataFrame, concentration: pd.DataFrame,
) -> pd.DataFrame:
    visible_metrics = structural_metrics(
        site_year.rename(columns={
            "de_novo_visible_activity": "visible_activity",
            "de_novo_suppressed_entry_count": "suppressed_entries",
        }),
        "physical_site",
    )
    visible_scenario = concentration[concentration.suppression_scenario.eq("visible")]
    rows: list[dict[str, Any]] = []
    for year in YEARS:
        group = site_year[site_year.reporting_year.eq(year)]
        numeric = group[group.openly_numeric_de_novo_site]
        visible = numeric.de_novo_visible_activity
        inclusive_total = int(
            pd.to_numeric(
                inclusive.loc[inclusive.reporting_year.eq(year), "visible_activity"]
            ).sum()
        )
        metric = visible_metrics[visible_metrics.reporting_year.eq(year)].iloc[0]
        concentration_row = visible_scenario[visible_scenario.reporting_year.eq(year)].iloc[0]
        rows.append({
            "reporting_year": year,
            "code_set_regime": regime(year),
            "applicable_code_set": "|".join(applicable_codes(year)),
            "openly_visible_national_de_novo_activity": int(group.de_novo_visible_activity.sum()),
            "inclusive_national_visible_activity": inclusive_total,
            "de_novo_to_inclusive_visible_activity_ratio": (
                round(float(group.de_novo_visible_activity.sum()) / inclusive_total, 6)
                if inclusive_total else np.nan
            ),
            "identifiable_active_de_novo_sites": len(group),
            "openly_numeric_de_novo_sites": int(group.openly_numeric_de_novo_site.sum()),
            "suppressed_only_de_novo_sites": int(group.suppressed_only_de_novo_site.sum()),
            "sites_visible_4_19": int(visible.between(4, 19).sum()),
            "sites_visible_20_49": int(visible.between(20, 49).sum()),
            "sites_visible_50_99": int(visible.between(50, 99).sum()),
            "sites_visible_100_199": int(visible.between(100, 199).sum()),
            "sites_visible_ge_200": int(visible.ge(200).sum()),
            **{f"sites_visible_ge_{threshold}": int(visible.ge(threshold).sum()) for threshold in THRESHOLDS},
            "top5_share_pct": metric.top5_share_pct,
            "top10_share_pct": metric.top10_share_pct,
            "top20_share_pct": metric.top20_share_pct,
            "hhi_10000": metric.hhi_10000,
            "effective_number_of_centres": metric.effective_center_count,
            "gini": metric.gini,
            "providers_contributing_to_metrics": concentration_row.providers_contributing_to_metrics,
        })
    return pd.DataFrame(rows)


def build_bridge(records: pd.DataFrame, site_year: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    totals = site_year.groupby("reporting_year").agg(
        historically_valid_visible_total=("de_novo_visible_activity", "sum"),
        historically_valid_suppressed_entries=("de_novo_suppressed_entry_count", "sum"),
    )
    for year in YEARS:
        row: dict[str, Any] = {
            "reporting_year": year,
            "code_set_regime": regime(year),
            "bridge_focus_year": year in {2015, 2016},
        }
        for code in ALL_SELECTED_CODES:
            subset = records[
                records.reporting_year.eq(year) & records.code_normalised.eq(code)
            ]
            token = code_token(code)
            if code in applicable_codes(year):
                row[f"visible_{token}"] = int(subset.visible_value.sum())
                row[f"suppressed_entries_{token}"] = int(subset.suppressed_value.sum())
            else:
                row[f"visible_{token}"] = pd.NA
                row[f"suppressed_entries_{token}"] = pd.NA
        row["visible_8_839_87_plus_8_839_88"] = int(
            records.loc[
                records.reporting_year.eq(year) & records.code_normalised.isin(TWO_CODES),
                "visible_value",
            ].sum()
        )
        row["suppressed_8_839_87_plus_8_839_88"] = int(
            records.loc[
                records.reporting_year.eq(year) & records.code_normalised.isin(TWO_CODES),
                "suppressed_value",
            ].sum()
        )
        if year >= 2016:
            row["visible_8_839_89_plus_8_839_8a"] = int(
                records.loc[
                    records.reporting_year.eq(year)
                    & records.code_normalised.isin(("8-839.89", "8-839.8a")),
                    "visible_value",
                ].sum()
            )
            row["suppressed_8_839_89_plus_8_839_8a"] = int(
                records.loc[
                    records.reporting_year.eq(year)
                    & records.code_normalised.isin(("8-839.89", "8-839.8a")),
                    "suppressed_value",
                ].sum()
            )
        else:
            row["visible_8_839_89_plus_8_839_8a"] = pd.NA
            row["suppressed_8_839_89_plus_8_839_8a"] = pd.NA
        row.update(totals.loc[year].astype(int).to_dict())
        row["stable_two_code_visible_total"] = row["visible_8_839_87_plus_8_839_88"]
        row["stable_two_code_suppressed_entries"] = row["suppressed_8_839_87_plus_8_839_88"]
        rows.append(row)
    bridge = pd.DataFrame(rows)
    y15 = bridge[bridge.reporting_year.eq(2015)].iloc[0]
    y16 = bridge[bridge.reporting_year.eq(2016)].iloc[0]
    hist_abs = int(y16.historically_valid_visible_total - y15.historically_valid_visible_total)
    stable_abs = int(y16.stable_two_code_visible_total - y15.stable_two_code_visible_total)
    for year in (2015, 2016):
        mask = bridge.reporting_year.eq(year)
        bridge.loc[mask, "historically_valid_absolute_change_2015_2016"] = hist_abs
        bridge.loc[mask, "historically_valid_relative_change_2015_2016_pct"] = (
            100 * hist_abs / y15.historically_valid_visible_total
            if y15.historically_valid_visible_total else np.nan
        )
        bridge.loc[mask, "stable_two_code_absolute_change_2015_2016"] = stable_abs
        bridge.loc[mask, "stable_two_code_relative_change_2015_2016_pct"] = (
            100 * stable_abs / y15.stable_two_code_visible_total
            if y15.stable_two_code_visible_total else np.nan
        )
    bridge["transition_interpretation"] = ""
    bridge.loc[bridge.reporting_year.isin([2015, 2016]), "transition_interpretation"] = (
        "Comparability across 2015 and 2016 may be affected by the introduction "
        "of additional specific de-novo subcodes in 2016. The activity reported "
        "under 8-839.89 and 8-839.8a quantifies their contribution to the observed "
        "2016 coded total, but does not identify the magnitude of a coding artefact "
        "or distinguish coding change from real procedural change."
    )
    return bridge


def raw_xml_values(source_files: list[str], year: int) -> dict[str, dict[str, int]]:
    result = {code: {"visible": 0, "suppressed": 0} for code in applicable_codes(year)}
    for source in source_files:
        xml_root = ET.parse(ROOT / source).getroot()
        for entry in iter_tips_entries(xml_root):
            code = str(entry["ops_code"]).strip().lower()
            if code in result:
                result[code]["visible"] += int(entry["visible_count"])
                result[code]["suppressed"] += int(bool(entry["suppression_flag"]))
    return result


def build_spot_checks(records: pd.DataFrame, site_year: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for year in (2013, 2016, 2024):
        group = site_year[site_year.reporting_year.eq(year)].copy()
        group["code_count"] = group.contributing_selected_codes.str.split("|").map(len)
        candidates = {
            "openly_numeric_single_code": group[
                group.openly_numeric_de_novo_site & group.code_count.eq(1)
            ].sort_values("physical_site_id"),
            "openly_numeric_multi_code": group[
                group.openly_numeric_de_novo_site & group.code_count.ge(2)
            ].sort_values("physical_site_id"),
            "selected_suppressed_entry": group[
                group.de_novo_suppressed_entry_count.gt(0)
            ].sort_values("physical_site_id"),
            "high_volume": group.sort_values(
                ["de_novo_visible_activity", "physical_site_id"], ascending=[False, True]
            ),
        }
        for category, available in candidates.items():
            if available.empty:
                rows.append({
                    "reporting_year": year, "spot_check_type": category,
                    "validation_status": "not_available", "validation_notes": "no eligible site-year",
                })
                continue
            chosen = available.iloc[0]
            selected = records[
                records.reporting_year.eq(year)
                & records.site_identifier.astype(str).eq(str(chosen.physical_site_id))
                & records.ik.astype(str).eq(str(chosen.institution_id))
            ]
            sources = sorted(set(selected.source_file.astype(str)))
            canonical = {
                code: {
                    "visible": int(selected.loc[selected.code_normalised.eq(code), "visible_value"].sum()),
                    "suppressed": int(selected.loc[selected.code_normalised.eq(code), "suppressed_value"].sum()),
                }
                for code in applicable_codes(year)
            }
            raw = raw_xml_values(sources, year)
            passed = canonical == raw
            rows.append({
                "reporting_year": year,
                "spot_check_type": category,
                "physical_site_id": chosen.physical_site_id,
                "institution_id": chosen.institution_id,
                "source_files": "|".join(sources),
                "selected_codes": chosen.contributing_selected_codes,
                "canonical_code_values": json.dumps(canonical, sort_keys=True),
                "raw_xml_code_values": json.dumps(raw, sort_keys=True),
                "calculated_site_year_visible": int(chosen.de_novo_visible_activity),
                "calculated_site_year_suppressed_entries": int(chosen.de_novo_suppressed_entry_count),
                "validation_status": "passed" if passed else "failed",
                "validation_notes": "raw XML aggregation equals retained canonical code records" if passed else "raw XML mismatch",
            })
    return pd.DataFrame(rows)


def validation_checks(
    site_year: pd.DataFrame, annual: pd.DataFrame, contributions: pd.DataFrame,
    route_compare: pd.DataFrame, records: pd.DataFrame, spot: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    def add(scope: str, name: str, passed: bool, failures: int, detail: str) -> None:
        rows.append({"scope": scope, "check": name, "passed": bool(passed), "failed_count": int(failures), "detail": detail})

    site_checks = {
        "de_novo_visible_le_inclusive": site_year.de_novo_le_inclusive_visible_ok,
        "selected_suppression_le_inclusive": site_year.selected_suppression_le_inclusive_suppression_ok,
        "route_a_route_b_visible": site_year.route_a_route_b_visible_agreement,
        "route_a_route_b_suppression": site_year.route_a_route_b_suppression_agreement,
    }
    for name, values in site_checks.items():
        add("physical_site_year", name, values.all(), int((~values).sum()), "mandatory site-year gate")
    add("physical_site_year", "no_duplicate_site_years", not site_year.duplicated(["reporting_year", "physical_site_id"]).any(), int(site_year.duplicated(["reporting_year", "physical_site_id"]).sum()), "")
    code_visible = sum(
        pd.to_numeric(site_year[f"visible_{code_token(code)}"], errors="coerce").fillna(0)
        for code in ALL_SELECTED_CODES
    )
    code_suppressed = sum(
        pd.to_numeric(site_year[f"suppressed_entries_{code_token(code)}"], errors="coerce").fillna(0)
        for code in ALL_SELECTED_CODES
    )
    add("physical_site_year", "code_visible_sum_equals_total", code_visible.eq(site_year.de_novo_visible_activity).all(), int(code_visible.ne(site_year.de_novo_visible_activity).sum()), "")
    add("physical_site_year", "code_suppressed_sum_equals_total", code_suppressed.eq(site_year.de_novo_suppressed_entry_count).all(), int(code_suppressed.ne(site_year.de_novo_suppressed_entry_count).sum()), "")
    allowed = records.apply(lambda row: row.code_normalised in applicable_codes(int(row.reporting_year)), axis=1)
    add("record", "only_year_applicable_exact_codes", allowed.all(), int((~allowed).sum()), "parent, secondary, residual, other 8-839.8*, and 8-842.* excluded")
    add("record", "8_839_8a_literal_preserved", "8-839.8a" in set(records.code_normalised), 0 if "8-839.8a" in set(records.code_normalised) else 1, "exact string check")
    add("dual_route", "all_fields_exact", route_compare.all_route_fields_agree.all(), int((~route_compare.all_route_fields_agree).sum()), "identifiers, selected codes, code values, and totals")
    for row in annual.itertuples(index=False):
        year_group = site_year[site_year.reporting_year.eq(row.reporting_year)]
        applicable_contrib = contributions[
            contributions.reporting_year.eq(row.reporting_year) & contributions.applicable_in_year
        ]
        checks = {
            "national_selected_le_inclusive": row.openly_visible_national_de_novo_activity <= row.inclusive_national_visible_activity,
            "code_contributions_equal_national": int(applicable_contrib.openly_visible_national_activity.sum()) == row.openly_visible_national_de_novo_activity,
            "numeric_plus_suppressed_only_equal_identifiable": row.openly_numeric_de_novo_sites + row.suppressed_only_de_novo_sites == row.identifiable_active_de_novo_sites,
            "visible_categories_sum_to_numeric": row.sites_visible_4_19 + row.sites_visible_20_49 + row.sites_visible_50_99 + row.sites_visible_100_199 + row.sites_visible_ge_200 == row.openly_numeric_de_novo_sites,
            "site_sum_equals_national": int(year_group.de_novo_visible_activity.sum()) == row.openly_visible_national_de_novo_activity,
            "thresholds_monotone": row.sites_visible_ge_20 >= row.sites_visible_ge_50 >= row.sites_visible_ge_100 >= row.sites_visible_ge_200,
        }
        for name, passed in checks.items(): add(f"year_{row.reporting_year}", name, passed, 0 if passed else 1, "")
    pre = contributions[contributions.reporting_year.le(2015) & contributions.ops_code.isin(("8-839.89", "8-839.8a"))]
    add("year", "89_and_8a_not_applicable_before_2016", (~pre.applicable_in_year).all() and pre.openly_visible_national_activity.isna().all(), 0 if ((~pre.applicable_in_year).all() and pre.openly_visible_national_activity.isna().all()) else 1, "not represented as observed zero")
    failed_spots = spot.validation_status.eq("failed")
    add("raw_source_spot_check", "all_available_spot_checks_pass", not failed_spots.any(), int(failed_spots.sum()), f"{spot.validation_status.eq('passed').sum()} passed; {spot.validation_status.eq('not_available').sum()} not available")
    return pd.DataFrame(rows)


def table_s10(annual: pd.DataFrame) -> pd.DataFrame:
    return annual[[
        "reporting_year", "applicable_code_set",
        "openly_visible_national_de_novo_activity", "inclusive_national_visible_activity",
        "de_novo_to_inclusive_visible_activity_ratio", "identifiable_active_de_novo_sites",
        "openly_numeric_de_novo_sites", "suppressed_only_de_novo_sites",
        "sites_visible_ge_20", "sites_visible_ge_50", "sites_visible_ge_100",
        "sites_visible_ge_200", "top5_share_pct", "top10_share_pct", "top20_share_pct",
        "hhi_10000", "effective_number_of_centres", "gini",
    ]].copy()


def build_report(
    inputs: list[dict[str, Any]], annual: pd.DataFrame, contributions: pd.DataFrame,
    bridge: pd.DataFrame, concentration: pd.DataFrame, checks: pd.DataFrame,
    spot: pd.DataFrame, route_compare: pd.DataFrame, inclusive_reference: pd.DataFrame,
) -> str:
    focus_bridge = bridge[bridge.reporting_year.isin([2015, 2016])]
    visible_concentration = concentration[concentration.suppression_scenario.eq("visible")]
    inclusive_visible = inclusive_reference[
        inclusive_reference.provider_definition.eq("physical_site")
        & inclusive_reference.suppression_scenario.eq("visible")
        & inclusive_reference.reporting_year.isin(YEARS)
    ][["reporting_year", "hhi_10000", "effective_center_count", "gini"]].rename(
        columns={
            "hhi_10000": "inclusive_hhi_10000",
            "effective_center_count": "inclusive_effective_center_count",
            "gini": "inclusive_gini",
        }
    )
    comparison = visible_concentration[[
        "reporting_year", "hhi_10000", "effective_center_count", "gini"
    ]].rename(columns={
        "hhi_10000": "selected_subcode_hhi_10000",
        "effective_center_count": "selected_subcode_effective_center_count",
        "gini": "selected_subcode_gini",
    }).merge(inclusive_visible, on="reporting_year", validate="one_to_one")
    gini_directions = {}
    for scenario, group in concentration.groupby("suppression_scenario"):
        ordered = group.sort_values("reporting_year")
        change = float(ordered.gini.iloc[-1] - ordered.gini.iloc[0])
        gini_directions[scenario] = "increase" if change > 0 else "decrease" if change < 0 else "no_change"
    direction_consistent = len(set(gini_directions.values())) == 1
    status = (
        "De-novo sensitivity analysis completed and internally validated; ready for independent scientific review."
        if checks.passed.all() else
        "De-novo sensitivity analysis completed with unresolved validation issues; not ready for manuscript integration."
    )
    input_table = pd.DataFrame(inputs)[["path", "size_bytes", "modification_timestamp_utc", "sha256"]]
    return f"""# OPS-specific de-novo TIPS sensitivity analysis, 2013–2024

## Analytical question and endpoint

This sensitivity analysis describes **{ENDPOINT}**. It does not estimate unique
procedures, patients, admissions, or complete ascertainment of all newly created shunts.
The primary unit is physical site × reporting year; institution identifiers remain metadata.

## Inputs and provenance

{markdown_table(input_table)}

The canonical code-level source is `outputs/audit/tips_code_level_audit.csv`.
`resolve_component_precedence()` supplies the final exact-code component-site precedence.
`scenario_metrics()` calls the inclusive analysis's `structural_metrics()` function for the
visible, lower, midpoint, and upper suppression scenarios. Suppressed entries add 0, 1, 2,
or 3 units respectively before physical-site metrics are calculated.

## Year-specific exact code sets

- 2013–2015: `8-839.87`, `8-839.88`.
- 2016–2024: `8-839.87`, `8-839.88`, `8-839.89`, `8-839.8a`.

The parent, `.80–.86`, `.8x`, other `8-839.8*`, and all `8-842.*` codes are excluded.
The literal `8-839.8a` is never split, numerically coerced, or merged.

## Site definitions and dual-route method

An identifiable active site has a numeric or suppressed selected-code entry. An openly
numeric site has positive visible selected-code activity. A suppressed-only site has no
positive visible selected-code activity and at least one suppressed selected-code entry.

Route A applies the reconciled production precedence function to the canonical code-level
CSV. Route B independently parses `contributing_code_level_records` in the reconciliation
CSV. The routes agreed exactly for all {len(route_compare)} selected physical site-years,
including identifiers, selected codes, code-specific values, suppression counts, and totals.

## Annual results

{markdown_table(annual)}

## Code-specific contributions

{markdown_table(contributions)}

Rows for `.89` and `.8a` before 2016 are explicitly marked not applicable and contain no
activity values; catalogue non-availability is not represented as observed zero activity.

## 2015–2016 bridge and stable two-code comparison

{markdown_table(focus_bridge)}

Comparability across 2015 and 2016 may be affected by the introduction of additional
specific de-novo subcodes in 2016. The activity reported under 8-839.89 and 8-839.8a
quantifies their contribution to the observed 2016 coded total, but does not identify the
magnitude of a coding artefact or distinguish coding change from real procedural change.

## Suppression scenarios and concentration

{markdown_table(concentration)}

Gini first-to-last directions were {json.dumps(gini_directions, sort_keys=True)}.
Direction was {'consistent' if direction_consistent else 'not consistent'} across scenarios.
All concentration measures remain descriptive.

## Comparison with inclusive concentration

{markdown_table(comparison)}

The two series use the same physical-site definitions and concentration functions, but
different endpoints. Their differences must not be interpreted causally.

## Plausibility gates

{markdown_table(checks)}

## Raw-source spot checks

{markdown_table(spot)}

## Warnings and limitations

- The endpoint is code-occurrence activity, not patients, admissions, cases, or unique procedures.
- Suppressed entries have unknown true values; scenario estimates use the established 0/1/2/3 assumptions.
- The 2015–2016 code-set transition limits direct comparability.
- Internal validation does not replace independent scientific review.

## Proposed manuscript language (draft only)

**Methods:** As a sensitivity analysis, we quantified activity coded with specific de novo
TIPS creation subcodes using year-specific official OPS definitions and the same physical-site,
precedence, concentration, and suppression rules as the inclusive analysis.

**Results:** Activity coded with specific de novo TIPS creation subcodes was evaluated from
2013 through 2024 using two codes through 2015 and four codes thereafter; annual visible
activity, identifiable physical sites, threshold counts, and concentration estimates are
reported in draft Table S10, with exact agreement between two computational routes.

**Limitation:** Comparability across 2015 and 2016 may be affected by the introduction of
additional specific subcodes, and catalogue availability alone cannot separate coding change
from changes in reported activity.

**Recommended Table S10 columns:** year, applicable exact code set, visible selected-code
activity, inclusive visible activity, ratio, identifiable/numeric/suppressed-only sites,
threshold counts, Top-5/Top-10/Top-20 shares, HHI, effective centre count, and Gini.

## Status

{status}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path,
        default=ROOT / "outputs/de_novo_sensitivity_2013_2024",
    )
    args = parser.parse_args()
    out = args.output_dir.resolve()
    if out != (ROOT / "outputs/de_novo_sensitivity_2013_2024").resolve():
        raise RuntimeError("This approved run is restricted to the dedicated output directory")
    out.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    initial_git = {
        "branch": git("branch", "--show-current"),
        "head": git("rev-parse", "HEAD"),
        "dirty_working_tree": bool(git("status", "--porcelain=v1")),
        "dirty_working_tree_entry_count": len(git("status", "--porcelain=v1").splitlines()),
        "staged_file_count": len(git("diff", "--cached", "--name-only").splitlines()),
        "remotes": git("remote", "-v").splitlines(),
    }

    paths, input_records, reconciliation_properties = verify_inputs()
    route_a_site, route_a_records, _ = route_a(paths["outputs/audit/tips_code_level_audit.csv"])
    route_b_site, _ = route_b(paths["outputs/ops_code_audit_2013_2024/ops_code_reconciliation_site_year.csv"])
    route_compare = compare_routes(route_a_site, route_b_site)
    route_compare.to_csv(out / "de_novo_dual_route_validation.csv", index=False)
    site_year, inclusive = build_site_year(
        route_a_site, route_compare,
        paths["outputs/site_resolution_validation/resolved_site_level_data.csv"],
        paths["outputs/ops_code_audit_2013_2024/ops_code_reconciliation_site_year.csv"],
    )
    site_year.to_csv(out / "de_novo_site_year_2013_2024.csv", index=False)
    contributions = build_contributions(route_a_records)
    contributions.to_csv(out / "de_novo_code_contribution_by_year.csv", index=False)
    concentration = build_concentration(site_year)
    concentration.to_csv(out / "de_novo_concentration_by_year_and_scenario.csv", index=False)
    annual = build_annual(site_year, inclusive, concentration)
    annual.to_csv(out / "de_novo_annual_metrics_2013_2024.csv", index=False)
    bridge = build_bridge(route_a_records, site_year)
    bridge.to_csv(out / "de_novo_2015_2016_bridge.csv", index=False)
    spot = build_spot_checks(route_a_records, site_year)
    spot.to_csv(out / "de_novo_raw_source_spot_checks.csv", index=False)
    raw_xml_paths = sorted(
        {
            ROOT / source
            for sources in spot.source_files
            for source in str(sources).split("|")
            if source
        }
    )
    missing_raw_xml = [str(path) for path in raw_xml_paths if not path.is_file()]
    if missing_raw_xml:
        raise RuntimeError(f"Raw XML spot-check input files are missing: {missing_raw_xml}")
    recorded_paths = {record["absolute_path"] for record in input_records}
    input_records.extend(
        file_record(path) for path in raw_xml_paths if str(path.resolve()) not in recorded_paths
    )
    pd.DataFrame(input_records).to_csv(out / "de_novo_input_provenance.csv", index=False)
    checks = validation_checks(
        site_year, annual, contributions, route_compare, route_a_records, spot
    )
    checks.to_csv(out / "de_novo_validation_checks.csv", index=False)
    if not checks.passed.all():
        raise RuntimeError(
            f"Substantive validation failed in {(~checks.passed).sum()} checks; "
            "Table S10 and report were not produced"
        )

    table = table_s10(annual)
    table.to_csv(out / "table_s10_de_novo_sensitivity_draft.csv", index=False)
    footnotes = (
        "Year-specific availability: .87/.88 apply throughout; .89/.8a apply from 2016. "
        "Suppressed entries are excluded from visible numerical categories. The provider unit is "
        "the physical site. Values describe code occurrences, not patients, cases, admissions, or "
        "unique procedures. Comparability across 2015–2016 is limited by the code-set transition."
    )
    (out / "table_s10_de_novo_sensitivity_draft.md").write_text(
        "# Draft Table S10\n\n" + markdown_table(table) + "\n\n" + footnotes + "\n",
        encoding="utf-8",
    )
    inclusive_reference = pd.read_csv(
        paths["outputs/final_corrected_2026-07-24/suppression_final_metrics.csv"]
    )
    report = build_report(
        input_records, annual, contributions, bridge, concentration, checks,
        spot, route_compare, inclusive_reference,
    )
    (out / "de_novo_sensitivity_2013_2024.md").write_text(report, encoding="utf-8")

    output_files = [p for p in out.iterdir() if p.is_file() and p.name != "de_novo_run_manifest.json"]
    manifest = {
        "execution_timestamp_utc": timestamp,
        "git_initial": initial_git,
        "environment": {
            "python": sys.version,
            "executable": sys.executable,
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "inputs": input_records,
        "input_verification": {
            "expected_hashes_matched": True,
            "reconciliation_properties": reconciliation_properties,
            "historical_code_set_matched_audit": True,
            "site_and_institution_levels_separate": True,
        },
        "analysis_script": file_record(Path(__file__)),
        "production_functions_reused": [
            "gba_ops_reanalysis.site_resolution_validation.resolve_component_precedence",
            "gba_ops_reanalysis.site_resolution_validation.structural_metrics",
            "gba_ops_reanalysis.site_resolution_validation.gini (via structural_metrics)",
            "gba_ops_reanalysis.final_corrected.scenario_metrics",
            "gba_ops_reanalysis.suppression_sensitivity.iter_tips_entries (raw XML spot checks)",
        ],
        "selected_codes_by_year": {str(year): list(applicable_codes(year)) for year in YEARS},
        "suppression_scenarios": {
            "visible": "visible activity only; suppressed entry adds 0",
            "lower": "each suppressed entry adds 1",
            "midpoint": "each suppressed entry adds 2",
            "upper": "each suppressed entry adds 3",
        },
        "row_counts": {
            "active_physical_site_years": len(site_year),
            "route_comparison_rows": len(route_compare),
            "annual_rows": len(annual),
            "code_contribution_rows": len(contributions),
            "concentration_rows": len(concentration),
            "spot_check_rows": len(spot),
        },
        "route_agreement": {
            "all_rows_and_fields_exact": bool(route_compare.all_route_fields_agree.all()),
            "failed_rows": int((~route_compare.all_route_fields_agree).sum()),
        },
        "plausibility_gates": checks.to_dict(orient="records"),
        "raw_source_spot_checks": spot.to_dict(orient="records"),
        "warnings": [
            "The endpoint is code-occurrence activity, not patients, admissions, cases, or unique procedures.",
            "Suppressed-entry scenario values are assumptions, not observed counts.",
            "The 2015–2016 code-set transition limits direct comparability.",
        ],
        "unresolved_issues": [],
        "production_files_modified": False,
        "manuscript_or_supplement_modified": False,
        "established_inclusive_outputs_overwritten": False,
        "commit_or_push_performed": False,
        "branch_or_remote_changed": False,
        "outputs": [file_record(path) for path in sorted(output_files)],
        "manifest_self_hash_note": "The manifest excludes its own SHA-256 to avoid self-reference.",
        "status": "De-novo sensitivity analysis completed and internally validated; ready for independent scientific review.",
    }
    (out / "de_novo_run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Canonical dataset: {paths['outputs/audit/tips_code_level_audit.csv']}")
    for record in input_records:
        print(f"INPUT {record['path']} sha256={record['sha256']} verified=yes")
    print(annual[[
        "reporting_year", "openly_visible_national_de_novo_activity",
        "identifiable_active_de_novo_sites", "openly_numeric_de_novo_sites",
        "suppressed_only_de_novo_sites",
    ]].to_string(index=False))
    latest = annual[annual.reporting_year.eq(2024)].iloc[0]
    print("2024", latest.to_dict())
    print("2015-2016", bridge[bridge.reporting_year.isin([2015, 2016])].to_dict(orient="records"))
    print(f"Plausibility gates: {checks.passed.sum()}/{len(checks)} passed")
    print(f"Route A/B exact agreement: {route_compare.all_route_fields_agree.all()}")
    print(f"Raw spot checks: {(spot.validation_status == 'passed').sum()}/{len(spot)} passed")
    for path in sorted(out.iterdir()):
        if path.is_file():
            print(f"OUTPUT {path.name} sha256={sha256_file(path)}")
    print("Table S10 draft: ready for independent scientific review; not manuscript-integrated.")
    print("No manuscript, supplement, established inclusive output, or production code modified.")
    print("No commit, push, branch change, or remote change performed.")
    print("De-novo sensitivity analysis completed and internally validated; ready for independent scientific review.")


if __name__ == "__main__":
    main()
