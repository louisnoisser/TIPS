"""Reusable calculations for the isolated final corrected TIPS analysis."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .site_resolution_validation import THRESHOLDS, structural_metrics


EXPECTED_TOTALS = {
    2008: 1422, 2010: 1419, 2012: 2110, 2013: 2124, 2014: 2511,
    2015: 2546, 2016: 2715, 2017: 2801, 2018: 2977, 2019: 2972,
    2020: 3210, 2021: 4092, 2022: 4418, 2023: 4979, 2024: 5247,
}


OPERATIONAL_GROUPS = {
    "8-839.80": "de_novo_creation",
    "8-839.81": "secondary_intervention",
    "8-839.82": "secondary_intervention",
    "8-839.83": "secondary_intervention",
    "8-839.84": "secondary_intervention",
    "8-839.85": "secondary_intervention",
    "8-839.86": "secondary_intervention",
    "8-839.87": "de_novo_creation",
    "8-839.88": "de_novo_creation",
    "8-839.89": "de_novo_creation",
    "8-839.8a": "de_novo_creation",
    "8-839.8": "parent_code",
    "8-839.8x": "unresolved",
}


def validate_expected_totals(site: pd.DataFrame) -> pd.DataFrame:
    observed = site.groupby("reporting_year")["visible_activity"].sum().astype(int)
    rows = []
    for year, expected in EXPECTED_TOTALS.items():
        value = int(observed.get(year, -1))
        rows.append({
            "reporting_year": year, "expected_visible_activity": expected,
            "observed_visible_activity": value, "difference": value - expected,
            "exact_match": value == expected,
        })
    return pd.DataFrame(rows)


def scenario_metrics(data: pd.DataFrame, definition: str) -> pd.DataFrame:
    frames = []
    for scenario, column in (
        ("visible", "visible_activity"), ("lower", "lower_activity"),
        ("midpoint", "midpoint_activity"), ("upper", "upper_activity"),
    ):
        work = data.copy()
        work["visible_activity"] = work[column]
        metric = structural_metrics(work, definition)
        metric["suppression_scenario"] = scenario
        frames.append(metric)
    return pd.concat(frames, ignore_index=True)


def low_volume_denominators(data: pd.DataFrame, years: tuple[int, ...] = (2008, 2024)) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for year in years:
        group = data[data["reporting_year"] == year]
        numeric = group[group["visible_activity"] > 0]
        rows.append({
            "reporting_year": year, "denominator_type": "openly_reported_numeric_activity",
            "category": "below_20", "count": int((numeric["visible_activity"] < 20).sum()),
            "denominator": len(numeric),
            "percentage": 100 * float((numeric["visible_activity"] < 20).mean()) if len(numeric) else 0,
            "scenario": "visible",
        })
        active = group[(group["visible_activity"] > 0) | (group["suppressed_entries"] > 0)]
        definite_below = active["upper_activity"] < 20
        uncertain = (active["lower_activity"] < 20) & (active["upper_activity"] >= 20)
        definite_above = active["lower_activity"] >= 20
        for category, mask in (
            ("definitely_below_20", definite_below),
            ("uncertain_at_20", uncertain),
            ("definitely_at_or_above_20", definite_above),
        ):
            rows.append({
                "reporting_year": year, "denominator_type": "all_identifiable_active_providers",
                "category": category, "count": int(mask.sum()), "denominator": len(active),
                "percentage": 100 * float(mask.mean()) if len(active) else 0,
                "scenario": "interval_classification",
            })
        for scenario, column in (
            ("lower", "lower_activity"), ("midpoint", "midpoint_activity"), ("upper", "upper_activity")
        ):
            count = int((active[column] < 20).sum())
            rows.append({
                "reporting_year": year, "denominator_type": "all_identifiable_active_providers",
                "category": "below_20", "count": count, "denominator": len(active),
                "percentage": 100 * count / len(active) if len(active) else 0,
                "scenario": scenario,
            })
    return pd.DataFrame(rows)


def exclusive_landscape_2024(site: pd.DataFrame) -> pd.DataFrame:
    active = site[(site["reporting_year"] == 2024) & (site["visible_activity"] > 0)].copy()
    bins = [(4, 19, "4–19"), (20, 49, "20–49"), (50, 99, "50–99"),
            (100, 199, "100–199"), (200, np.inf, "≥200")]
    total = int(active["visible_activity"].sum())
    rows = []
    for lower, upper, label in bins:
        subset = active[(active["visible_activity"] >= lower) & (active["visible_activity"] <= upper)]
        rows.append({
            "volume_category": label, "provider_sites": len(subset),
            "provider_share_pct": 100 * len(subset) / len(active),
            "visible_procedural_activity": int(subset["visible_activity"].sum()),
            "national_activity_share_pct": 100 * subset["visible_activity"].sum() / total,
            "median": float(subset["visible_activity"].median()),
            "q1": float(subset["visible_activity"].quantile(.25)),
            "q3": float(subset["visible_activity"].quantile(.75)),
            "minimum": int(subset["visible_activity"].min()),
            "maximum": int(subset["visible_activity"].max()),
        })
    return pd.DataFrame(rows)


def code_evidence_table(codes: pd.Series) -> pd.DataFrame:
    rows = []
    for code in sorted(set(codes.astype(str)), key=str.lower):
        group = OPERATIONAL_GROUPS.get(code.lower(), "unresolved")
        rows.append({
            "OPS_code": code, "official_description": "", "evidence_source": "repository configuration/audit only",
            "evidence_file_path": "src/gba_ops_reanalysis/config.py; outputs/audit/tips_code_level_audit.csv",
            "verification_status": "operational repository mapping only" if group not in {"unresolved", "parent_code"} else "unresolved",
            "assigned_analytical_group": group,
        })
    return pd.DataFrame(rows)


def code_composition(annotated: pd.DataFrame) -> pd.DataFrame:
    work = annotated[annotated["retained_site_resolution"]].copy()
    work["analytical_group"] = work["OPS_code"].str.lower().map(OPERATIONAL_GROUPS).fillna("unresolved")
    rows = []
    for year, group in work.groupby("reporting_year"):
        total = int(group["visible_count"].sum())
        for category in ("de_novo_creation", "secondary_intervention", "unresolved", "parent_code"):
            subset = group[group["analytical_group"] == category]
            visible = int(subset["visible_count"].sum())
            suppressed = int(subset["suppressed_entries"].sum())
            rows.append({
                "reporting_year": year, "classification_basis": "operational repository mapping only",
                "analytical_group": category, "visible_activity": visible,
                "percentage_total_visible": 100 * visible / total if total else 0,
                "suppressed_entries": suppressed, "lower_activity": visible + suppressed,
                "midpoint_activity": visible + 2 * suppressed,
                "upper_activity": visible + 3 * suppressed,
                "officially_verified": False,
            })
    return pd.DataFrame(rows)


def parent_sensitivity(site: pd.DataFrame, diagnostic: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for event in diagnostic.itertuples():
        base = site[(site["reporting_year"] == event.reporting_year)
                    & (site["site_identifier"] == event.site_identifier)]
        if base.empty:
            continue
        rows.extend([
            {"reporting_year": event.reporting_year, "site_identifier": event.site_identifier,
             "scenario": "A_retain_parent_and_terminal", "activity_removed": 0},
            {"reporting_year": event.reporting_year, "site_identifier": event.site_identifier,
             "scenario": "B_omit_parent", "activity_removed": int(event.parent_visible_value)},
            {"reporting_year": event.reporting_year, "site_identifier": event.site_identifier,
             "scenario": "C_omit_terminal_subcodes", "activity_removed": int(event.subcode_visible_sum)},
        ])
    adjustments = pd.DataFrame(rows)
    output = []
    base_metrics = structural_metrics(site, "physical_site").set_index("reporting_year")
    for scenario in ("A_retain_parent_and_terminal", "B_omit_parent", "C_omit_terminal_subcodes"):
        work = site.copy()
        subset = adjustments[adjustments["scenario"] == scenario]
        mapping = {(r.reporting_year, r.site_identifier): r.activity_removed for r in subset.itertuples()}
        work["visible_activity"] = work.apply(
            lambda r: max(0, r.visible_activity - mapping.get((r.reporting_year, r.site_identifier), 0)), axis=1
        )
        metrics = structural_metrics(work, "physical_site")
        for metric in metrics.itertuples():
            base = base_metrics.loc[metric.reporting_year]
            output.append({
                "reporting_year": metric.reporting_year, "scenario": scenario,
                "affected_records": int((subset["reporting_year"] == metric.reporting_year).sum()),
                "activity_removed": int(subset.loc[subset.reporting_year == metric.reporting_year, "activity_removed"].sum()),
                "visible_national_activity": metric.visible_national_activity,
                "change_national_activity": metric.visible_national_activity - base.visible_national_activity,
                **{f"providers_ge_{t}": getattr(metric, f"providers_ge_{t}") for t in THRESHOLDS},
                **{f"change_providers_ge_{t}": getattr(metric, f"providers_ge_{t}") - base[f"providers_ge_{t}"] for t in THRESHOLDS},
                "top5_share_pct": metric.top5_share_pct,
                "top10_share_pct": metric.top10_share_pct,
                "top20_share_pct": metric.top20_share_pct,
                "hhi_10000": metric.hhi_10000,
                "change_top5_share_pct": metric.top5_share_pct - base.top5_share_pct,
                "change_top10_share_pct": metric.top10_share_pct - base.top10_share_pct,
                "change_top20_share_pct": metric.top20_share_pct - base.top20_share_pct,
                "change_hhi_10000": metric.hhi_10000 - base.hhi_10000,
            })
    return pd.DataFrame(output)

