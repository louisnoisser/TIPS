#!/usr/bin/env python3
"""Routing-free geographic suppression sensitivity for the 2024 TIPS networks.

The script uses the completed 193-site bank of individual 30- and 60-minute
isochrones. It never calls OpenRouteService. Network construction is driven by
explicit sets of stable site identifiers so another site selection can reuse
``unions_from_site_lists`` without changing the coverage method.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import geopandas as gpd
import pandas as pd
import rasterio
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gba_ops_reanalysis.urban_rural import RURAL_CODES, URBAN_CODES  # noqa: E402


OUT = ROOT / "outputs/tips_geographic_suppression_sensitivity_2026-09-23"
MASTER = ROOT / "outputs/late_stage_geo_corrective_qa_2026-08-14/proposed_full_identifiable_network_review_master_corrective_qa.csv"
SITE_DATA = ROOT / "outputs/site_resolution_validation/resolved_site_level_data.csv"
SUPPRESSION_METRICS = ROOT / "outputs/final_corrected_2026-07-24/suppression_final_metrics.csv"
LOCKED_UNIONS = ROOT / "outputs/final_submission_assets_2026-07-24/geography/accessibility_unions.geojson"
LOCKED_SITE_ISO = ROOT / "outputs/final_submission_assets_2026-07-24/geography/accessibility_site_isochrones.geojson"
LOCKED_ACCESS_NATIONAL = ROOT / "outputs/final_submission_assets_2026-07-24/geography/accessibility_final.csv"
LOCKED_ACCESS_CLASS = ROOT / "outputs/final_submission_assets_2026-07-24/geography/accessibility_urban_rural_final.csv"
TABLE_S5 = ROOT / "outputs/final_submission_assets_2026-07-24/tables/TableS5_potential_geographic_accessibility.csv"
RECOVERY_DIR = ROOT / "outputs/late_stage_accessibility_193_113_recovery_2026-08-15"
RECOVERY_SCRIPT = ROOT / "scripts/run_late_stage_accessibility_193_113_recovery_2026_08_15.py"
RECOVERY_CHECKPOINT = RECOVERY_DIR / "routing/checkpoints/routing_checkpoint.csv"
RECOVERY_REFERENCE_UNIONS = {
    ("full_identifiable", 30): RECOVERY_DIR / "isochrones/full_identifiable_reference_30min_union.geojson",
    ("full_identifiable", 60): RECOVERY_DIR / "isochrones/full_identifiable_reference_60min_union.geojson",
    ("openly_numeric", 30): RECOVERY_DIR / "isochrones/openly_numeric_reference_30min_union.geojson",
    ("openly_numeric", 60): RECOVERY_DIR / "isochrones/openly_numeric_reference_60min_union.geojson",
}
RECOVERY_REFERENCE_COVERAGE = {
    "full_identifiable": RECOVERY_DIR / "coverage/full_identifiable_reference_raw_coverage.csv",
    "openly_numeric": RECOVERY_DIR / "coverage/openly_numeric_reference_raw_coverage.csv",
}
ROUTING_METADATA = ROOT / "outputs/late_stage_accessibility_193_113_2026-08-14/inputs_verified/routing_environment_metadata.json"
POPULATION_METADATA = ROOT / "outputs/late_stage_accessibility_193_113_2026-08-14/inputs_verified/population_settlement_metadata.json"
ORS_IDENTITY = RECOVERY_DIR / "preflight/docker_ors_environment_identity.json"
POP = ROOT / "spatial/GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif"
SMOD = ROOT / "spatial/GHS_SMOD_E2025_GLOBE_R2023A_54009_1000_V2_0.tif"
GERMANY = ROOT / "spatial/germany-detailed-boundary_917.geojson"
ORS_CONFIG = ROOT / "ors-docker/config/ors-config.yml"
GRAPH_INFO = ROOT / "ors-docker/graphs/driving-car/graph_build_info.yml"
OSM = ROOT / "ors-docker/files/germany-latest.osm.pbf"

TIMES = (30, 60)
THRESHOLDS = (20, 50, 100)
SCENARIOS = ("visible", "lower", "midpoint", "upper")
SCENARIO_COLUMNS = {
    "visible": "visible_activity",
    "lower": "lower_activity",
    "midpoint": "midpoint_activity",
    "upper": "upper_activity",
}
SCENARIO_MULTIPLIERS = {"visible": 0, "lower": 1, "midpoint": 2, "upper": 3}
GROUPS = ("national", "urban", "rural", "other")
RAW_GROUP = {"national": "total", "urban": "urban", "rural": "rural", "other": "other"}
_SHA256_CACHE: dict[tuple[str, int, int], str] = {}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    stat = path.stat()
    key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
    if key in _SHA256_CACHE:
        return _SHA256_CACHE[key]
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    value = digest.hexdigest()
    _SHA256_CACHE[key] = value
    return value


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def bool_col(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin({"true", "yes", "1"})


def markdown(frame: pd.DataFrame) -> str:
    clean = frame.fillna("").astype(str).apply(lambda c: c.str.replace("|", r"\|", regex=False))
    return "\n".join([
        "| " + " | ".join(clean.columns) + " |",
        "| " + " | ".join("---" for _ in clean.columns) + " |",
        *["| " + " | ".join(row) + " |" for row in clean.itertuples(index=False, name=None)],
    ])


def write_csv(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def write_text(text: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def load_single_geometry(path: Path) -> Any:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if len(payload.get("features", [])) != 1:
        raise RuntimeError(f"Expected exactly one geometry in {path}")
    geometry = shape(payload["features"][0]["geometry"])
    if geometry.is_empty or not geometry.is_valid:
        raise RuntimeError(f"Invalid geometry in {path}")
    return geometry


def load_recovery_module():
    spec = importlib.util.spec_from_file_location("recovery_accessibility", RECOVERY_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_master_and_activity() -> pd.DataFrame:
    master = pd.read_csv(MASTER, dtype={"ik": str, "site_id": str, "postcode": str})
    sites = pd.read_csv(SITE_DATA, dtype={"ik": str, "site_identifier": str})
    sites = sites[sites.reporting_year.eq(2024)].copy()
    keep = [
        "site_identifier", "visible_activity", "suppressed_entries",
        "lower_activity", "midpoint_activity", "upper_activity",
    ]
    work = master.merge(sites[keep], left_on="site_id", right_on="site_identifier", how="outer", validate="one_to_one", indicator=True, suffixes=("_master", ""))
    if not work._merge.eq("both").all():
        raise RuntimeError("The geographic master and resolved 2024 site data do not have identical site IDs")
    work = work.drop(columns=["_merge", "site_identifier"])
    if not work.visible_activity_master.eq(work.visible_activity).all():
        raise RuntimeError("Visible activity differs between the geographic master and resolved site data")
    work["latitude_final"] = pd.to_numeric(work.proposed_latitude)
    work["longitude_final"] = pd.to_numeric(work.proposed_longitude)
    if work[["latitude_final", "longitude_final"]].isna().any().any():
        raise RuntimeError("Validated coordinates are incomplete")
    return work


def add_point_settlement_classes(work: pd.DataFrame) -> pd.DataFrame:
    result = work.copy()
    with rasterio.open(SMOD) as src:
        transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
        coords = [
            transformer.transform(lon, lat)
            for lon, lat in zip(result.longitude_final, result.latitude_final, strict=True)
        ]
        result["ghs_smod_code"] = [int(value[0]) for value in src.sample(coords)]
    result["derived_settlement_category"] = result.ghs_smod_code.map(
        lambda value: "urban" if value in URBAN_CODES else ("rural" if value in RURAL_CODES else "other")
    )
    return result


def load_geometry_bank(site_ids: set[str]) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]]]:
    bank: dict[int, dict[str, Any]] = {30: {}, 60: {}}
    issues: list[dict[str, Any]] = []
    payload = json.loads(LOCKED_SITE_ISO.read_text(encoding="utf-8"))
    for index, feature in enumerate(payload.get("features", [])):
        site_id = str(feature["properties"]["site_id"])
        minutes = int(feature["properties"]["time_minutes"])
        if site_id in bank[minutes]:
            issues.append({"check": "duplicate_geometry", "site_id": site_id, "time_minutes": minutes, "status": "FAIL"})
            continue
        bank[minutes][site_id] = shape(feature["geometry"])
    checkpoint = pd.read_csv(RECOVERY_CHECKPOINT, dtype={"site_id": str})
    checkpoint["completed"] = bool_col(checkpoint.completed)
    if not checkpoint.completed.all():
        raise RuntimeError("Recovery checkpoint contains incomplete rows")
    for record in checkpoint.to_dict("records"):
        for minutes in TIMES:
            path = ROOT / record[f"geometry_{minutes}m_path"]
            if sha256(path) != record[f"geometry_{minutes}m_sha256"]:
                raise RuntimeError(f"Recovery geometry hash mismatch: {path}")
            site_id = record["site_id"]
            if site_id in bank[minutes]:
                issues.append({"check": "duplicate_geometry", "site_id": site_id, "time_minutes": minutes, "status": "FAIL"})
                continue
            bank[minutes][site_id] = load_single_geometry(path)
    for minutes in TIMES:
        missing = sorted(site_ids - set(bank[minutes]))
        extra = sorted(set(bank[minutes]) - site_ids)
        if missing or extra:
            raise RuntimeError(f"Incomplete geometry bank at {minutes} minutes: missing={missing}, extra={extra}")
        for site_id, geometry in bank[minutes].items():
            if geometry.is_empty or not geometry.is_valid:
                raise RuntimeError(f"Invalid site geometry: {site_id}, {minutes}")
    return bank, issues


def unions_from_site_lists(site_lists: dict[str, set[str]], bank: dict[int, dict[str, Any]]) -> dict[tuple[str, int], Any]:
    """Create network unions from explicit stable-site-ID lists without routing."""
    unions: dict[tuple[str, int], Any] = {}
    for network, ids in site_lists.items():
        if len(ids) != len(set(ids)):
            raise RuntimeError(f"Duplicate site IDs in {network}")
        for minutes in TIMES:
            missing = sorted(ids - set(bank[minutes]))
            if missing:
                raise RuntimeError(f"Missing {minutes}-minute isochrones for {network}: {missing}")
            unions[(network, minutes)] = unary_union([bank[minutes][site_id] for site_id in sorted(ids)])
    return unions


def load_locked_visible_unions() -> dict[tuple[str, int], Any]:
    gdf = gpd.read_file(LOCKED_UNIONS).to_crs(4326)
    return {
        (f"visible_ge{int(row.threshold)}", int(row.time_minutes)): row.geometry
        for row in gdf.itertuples(index=False)
    }


def build_site_lists(work: pd.DataFrame) -> dict[str, set[str]]:
    site_lists: dict[str, set[str]] = {
        "full_identifiable": set(work.site_id),
        "openly_numeric": set(work.loc[work.visible_activity.gt(0), "site_id"]),
    }
    for scenario, column in SCENARIO_COLUMNS.items():
        for threshold in THRESHOLDS:
            site_lists[f"{scenario}_ge{threshold}"] = set(work.loc[work[column].ge(threshold), "site_id"])
    return site_lists


def expected_counts_from_established_metrics() -> dict[tuple[str, int], int]:
    metrics = pd.read_csv(SUPPRESSION_METRICS)
    rows = metrics[(metrics.reporting_year.eq(2024)) & metrics.provider_definition.eq("physical_site")]
    expected: dict[tuple[str, int], int] = {}
    for row in rows.itertuples(index=False):
        for threshold in THRESHOLDS:
            expected[(row.suppression_scenario, threshold)] = int(getattr(row, f"providers_ge_{threshold}"))
    return expected


def canonical_visible_values() -> tuple[dict[str, int], dict[tuple[int, int, str], int]]:
    national = pd.read_csv(LOCKED_ACCESS_NATIONAL)
    classes = pd.read_csv(LOCKED_ACCESS_CLASS)
    denominators = {
        "national": int(national.germany_population_denominator.iloc[0]),
        **{
            group: int(classes.loc[classes.settlement_class.eq(group), "class_population_denominator"].iloc[0])
            for group in ("urban", "rural", "other")
        },
    }
    values: dict[tuple[int, int, str], int] = {}
    for threshold in THRESHOLDS:
        for minutes in TIMES:
            row = national[(national.threshold.eq(threshold)) & national.time_minutes.eq(minutes)].iloc[0]
            values[(threshold, minutes, "national")] = int(row.covered_population)
            for group in ("urban", "rural", "other"):
                row = classes[(classes.threshold.eq(threshold)) & classes.time_minutes.eq(minutes) & classes.settlement_class.eq(group)].iloc[0]
                values[(threshold, minutes, group)] = int(row.covered_population)
    return denominators, values


def coverage_rows(
    network_geometries: dict[tuple[str, int], Any],
    site_lists: dict[str, set[str]],
    raw_totals: dict[str, float],
    raw_covered: dict[tuple[str, int], dict[str, float]],
    denominators: dict[str, int],
) -> pd.DataFrame:
    rows = []
    references = {
        "full_identifiable": "full_identifiable",
        "openly_numeric": "openly_numeric",
    }
    for (network, minutes) in sorted(network_geometries):
        if network in references:
            network_type = "reference"
            scenario = references[network]
            threshold: int | None = None
        else:
            scenario, threshold_text = network.split("_ge")
            threshold = int(threshold_text)
            network_type = "threshold"
        for group in GROUPS:
            raw_group = RAW_GROUP[group]
            covered_raw = float(raw_covered[(network, minutes)][raw_group])
            pct = 100 * covered_raw / raw_totals[raw_group]
            rows.append({
                "reporting_year": 2024,
                "network": network,
                "network_type": network_type,
                "volume_threshold": threshold,
                "suppression_scenario": scenario,
                "suppressed_value_per_entry": SCENARIO_MULTIPLIERS.get(scenario),
                "time_minutes": minutes,
                "population_group": group,
                "site_count": len(site_lists[network]),
                "covered_population_raw_float": covered_raw,
                "covered_population": int(round(covered_raw)),
                "population_denominator_raw_float": float(raw_totals[raw_group]),
                "population_denominator": denominators[group],
                "coverage_pct_unrounded": pct,
                "coverage_pct_2dp": round(pct, 2),
            })
    result = pd.DataFrame(rows)
    lookup = result.set_index(["network", "time_minutes", "population_group"])
    diffs = []
    for row in result.itertuples(index=False):
        if row.network_type == "threshold":
            visible = float(lookup.loc[(f"visible_ge{int(row.volume_threshold)}", row.time_minutes, row.population_group), "coverage_pct_unrounded"])
        else:
            visible = float("nan")
        full = float(lookup.loc[("full_identifiable", row.time_minutes, row.population_group), "coverage_pct_unrounded"])
        numeric = float(lookup.loc[("openly_numeric", row.time_minutes, row.population_group), "coverage_pct_unrounded"])
        diffs.append((
            row.coverage_pct_unrounded - visible if row.network_type == "threshold" else float("nan"),
            row.coverage_pct_unrounded - full,
            row.coverage_pct_unrounded - numeric,
        ))
    result[[
        "difference_vs_visible_same_threshold_percentage_points",
        "difference_vs_full_identifiable_percentage_points",
        "difference_vs_openly_numeric_percentage_points",
    ]] = pd.DataFrame(diffs, index=result.index)
    return result.sort_values(["network_type", "volume_threshold", "suppression_scenario", "time_minutes", "population_group"], na_position="first")


def membership_table(work: pd.DataFrame, site_lists: dict[str, set[str]]) -> pd.DataFrame:
    rows = []
    for scenario in SCENARIOS:
        column = SCENARIO_COLUMNS[scenario]
        for threshold in THRESHOLDS:
            network = f"{scenario}_ge{threshold}"
            visible_ids = site_lists[f"visible_ge{threshold}"]
            subset = work[work.site_id.isin(site_lists[network])].copy()
            for row in subset.itertuples(index=False):
                rows.append({
                    "reporting_year": 2024,
                    "volume_threshold": threshold,
                    "suppression_scenario": scenario,
                    "suppressed_value_per_entry": SCENARIO_MULTIPLIERS[scenario],
                    "site_id": row.site_id,
                    "ik": row.ik,
                    "site_name": row.provider_name,
                    "federal_state": row.federal_state,
                    "visible_activity": int(row.visible_activity),
                    "relevant_suppressed_entries": int(row.suppressed_entries),
                    "scenario_volume": int(getattr(row, column)),
                    "ghs_smod_code": int(row.ghs_smod_code),
                    "derived_settlement_category": row.derived_settlement_category,
                    "settlement_classification_missing": False,
                    "added_vs_visible_same_threshold": row.site_id not in visible_ids,
                })
    return pd.DataFrame(rows).sort_values(["volume_threshold", "suppression_scenario", "added_vs_visible_same_threshold", "scenario_volume", "site_id"], ascending=[True, True, True, False, True])


def class_counts(membership: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in membership.groupby(["volume_threshold", "suppression_scenario", "suppressed_value_per_entry"], sort=True):
        threshold, scenario, multiplier = keys
        counts = group.derived_settlement_category.value_counts().to_dict()
        missing = int(group.settlement_classification_missing.sum())
        rows.append({
            "reporting_year": 2024,
            "volume_threshold": threshold,
            "suppression_scenario": scenario,
            "suppressed_value_per_entry": multiplier,
            "site_count": len(group),
            "urban_sites": int(counts.get("urban", 0)),
            "rural_sites": int(counts.get("rural", 0)),
            "other_sites": int(counts.get("other", 0)),
            "missing_settlement_classification": missing,
        })
    return pd.DataFrame(rows).sort_values(["volume_threshold", "suppression_scenario"])


def contribution_table(
    work: pd.DataFrame,
    site_lists: dict[str, set[str]],
    bank: dict[int, dict[str, Any]],
    visible_unions: dict[tuple[str, int], Any],
    raw_totals: dict[str, float],
    denominators: dict[str, int],
    recovery: Any,
) -> pd.DataFrame:
    unique_geometries: dict[tuple[str, int], Any] = {}
    added_by_threshold: dict[int, set[str]] = {}
    for threshold in THRESHOLDS:
        visible_ids = site_lists[f"visible_ge{threshold}"]
        all_added = set().union(*(site_lists[f"{scenario}_ge{threshold}"] - visible_ids for scenario in SCENARIOS[1:]))
        added_by_threshold[threshold] = all_added
        for site_id in sorted(all_added):
            for minutes in TIMES:
                unique_geometries[(f"contribution_ge{threshold}_{site_id}", minutes)] = unary_union([
                    visible_unions[(f"visible_ge{threshold}", minutes)], bank[minutes][site_id]
                ])
    if unique_geometries:
        _, covered = recovery.raw_population_overlay(unique_geometries)
    else:
        covered = {}
    base_geometries = {(f"visible_ge{threshold}", minutes): visible_unions[(f"visible_ge{threshold}", minutes)] for threshold in THRESHOLDS for minutes in TIMES}
    _, base_covered = recovery.raw_population_overlay(base_geometries)
    by_site = work.set_index("site_id")
    rows = []
    for threshold in THRESHOLDS:
        visible_ids = site_lists[f"visible_ge{threshold}"]
        for scenario in SCENARIOS[1:]:
            added = site_lists[f"{scenario}_ge{threshold}"] - visible_ids
            for site_id in sorted(added):
                site = by_site.loc[site_id]
                for minutes in TIMES:
                    key = (f"contribution_ge{threshold}_{site_id}", minutes)
                    base_key = (f"visible_ge{threshold}", minutes)
                    national_raw = covered[key]["total"] - base_covered[base_key]["total"]
                    rural_raw = covered[key]["rural"] - base_covered[base_key]["rural"]
                    rows.append({
                        "reporting_year": 2024,
                        "volume_threshold": threshold,
                        "suppression_scenario": scenario,
                        "suppressed_value_per_entry": SCENARIO_MULTIPLIERS[scenario],
                        "site_id": site_id,
                        "ik": site.ik,
                        "site_name": site.provider_name,
                        "federal_state": site.federal_state,
                        "visible_activity": int(site.visible_activity),
                        "relevant_suppressed_entries": int(site.suppressed_entries),
                        "scenario_volume": int(site[SCENARIO_COLUMNS[scenario]]),
                        "ghs_smod_code": int(site.ghs_smod_code),
                        "derived_settlement_category": site.derived_settlement_category,
                        "time_minutes": minutes,
                        "additional_national_population_raw_float": national_raw,
                        "additional_national_population": int(round(national_raw)),
                        "additional_national_percentage_points": 100 * national_raw / raw_totals["total"],
                        "additional_rural_population_raw_float": rural_raw,
                        "additional_rural_population": int(round(rural_raw)),
                        "additional_rural_percentage_points": 100 * rural_raw / raw_totals["rural"],
                        "contribution_definition": "visible reference network plus this site minus visible reference network",
                        "additivity_warning": "non-additive individual contribution; overlaps between added sites are not summable",
                    })
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    order = result[result.time_minutes.eq(60)][["volume_threshold", "suppression_scenario", "site_id", "additional_rural_percentage_points"]].rename(columns={"additional_rural_percentage_points": "sort_value"})
    result = result.merge(order, on=["volume_threshold", "suppression_scenario", "site_id"], how="left", validate="many_to_one")
    return result.sort_values(["volume_threshold", "suppression_scenario", "sort_value", "site_id", "time_minutes"], ascending=[True, True, False, True, True]).drop(columns="sort_value")


def table_s5_markdown(coverage: pd.DataFrame) -> str:
    threshold = coverage[coverage.network_type.eq("threshold")]
    rows = []
    for (value, scenario, minutes), group in threshold.groupby(["volume_threshold", "suppression_scenario", "time_minutes"], sort=True):
        values = group.set_index("population_group")
        rows.append({
            "threshold": int(value),
            "suppression_scenario": scenario,
            "suppressed_value_per_entry": int(values.suppressed_value_per_entry.iloc[0]),
            "time_minutes": int(minutes),
            "eligible_sites": int(values.site_count.iloc[0]),
            "validated_sites": int(values.site_count.iloc[0]),
            "successfully_routed_sites": int(values.site_count.iloc[0]),
            "failed_routing_sites": 0,
            "covered_population": int(values.loc["national", "covered_population"]),
            "germany_population_denominator": int(values.loc["national", "population_denominator"]),
            "pct_population_covered": round(float(values.loc["national", "coverage_pct_unrounded"]), 2),
            "covered_population_urban": int(values.loc["urban", "covered_population"]),
            "pct_class_population_covered_urban": round(float(values.loc["urban", "coverage_pct_unrounded"]), 2),
            "covered_population_rural": int(values.loc["rural", "covered_population"]),
            "pct_class_population_covered_rural": round(float(values.loc["rural", "coverage_pct_unrounded"]), 2),
            "covered_population_other": int(values.loc["other", "covered_population"]),
            "pct_class_population_covered_other": round(float(values.loc["other", "coverage_pct_unrounded"]), 2),
            "final_validation_status": "routing-free sensitivity validated",
        })
    frame = pd.DataFrame(rows).sort_values(["threshold", "suppression_scenario", "time_minutes"])
    return (
        "# Table S5 format extension. Potential geographic accessibility under 2024 suppression scenarios\n\n"
        + markdown(frame)
        + "\n\nSuppressed entries contribute 0, 1, 2 or 3 procedure occurrences per relevant entry in the visible, lower, midpoint or upper scenario. The midpoint is a scenario and not an estimate of the true value. Coverage uses the existing validated coordinates and site-level isochrones. Urban, rural and other coverage use their own population denominators. The Supplement was not modified.\n"
    )


def qa_table(
    work: pd.DataFrame,
    site_lists: dict[str, set[str]],
    coverage: pd.DataFrame,
    expected_counts: dict[tuple[str, int], int],
    canonical_values: dict[tuple[int, int, str], int],
    denominators: dict[str, int],
    geometry_issues: list[dict[str, Any]],
    classes: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    rows.append({"check": "stable site ID uniqueness", "details": f"{len(work)} rows and {work.site_id.nunique()} unique IDs", "status": "PASS" if len(work) == work.site_id.nunique() else "FAIL"})
    rows.append({"check": "geometry mapping duplicates", "details": str(geometry_issues), "status": "PASS" if not geometry_issues else "FAIL"})
    for scenario in SCENARIOS:
        for threshold in THRESHOLDS:
            observed = len(site_lists[f"{scenario}_ge{threshold}"])
            expected = expected_counts[(scenario, threshold)]
            rows.append({"check": "established suppression count", "network": f"{scenario}_ge{threshold}", "details": f"observed={observed}; expected={expected}", "status": "PASS" if observed == expected else "FAIL"})
        nested = site_lists[f"{scenario}_ge100"] <= site_lists[f"{scenario}_ge50"] <= site_lists[f"{scenario}_ge20"]
        rows.append({"check": "threshold nesting", "network": scenario, "details": "ge100 subset ge50 subset ge20", "status": "PASS" if nested else "FAIL"})
    for threshold in THRESHOLDS:
        nested = site_lists[f"visible_ge{threshold}"] <= site_lists[f"lower_ge{threshold}"] <= site_lists[f"midpoint_ge{threshold}"] <= site_lists[f"upper_ge{threshold}"]
        rows.append({"check": "scenario nesting", "network": f"ge{threshold}", "details": "visible subset lower subset midpoint subset upper", "status": "PASS" if nested else "FAIL"})
    indexed = coverage.set_index(["network", "time_minutes", "population_group"])
    for threshold in THRESHOLDS:
        for minutes in TIMES:
            for group in GROUPS:
                observed = int(indexed.loc[(f"visible_ge{threshold}", minutes, group), "covered_population"])
                expected = canonical_values[(threshold, minutes, group)]
                rows.append({"check": "visible reference reproduction", "network": f"visible_ge{threshold}", "time_minutes": minutes, "population_group": group, "details": f"observed={observed}; canonical={expected}", "status": "PASS" if observed == expected else "FAIL"})
    for network in coverage.network.unique():
        for group in GROUPS:
            g = coverage[(coverage.network.eq(network)) & coverage.population_group.eq(group)].set_index("time_minutes")
            rows.append({"check": "60-minute coverage not below 30-minute", "network": network, "population_group": group, "details": f"60={g.loc[60, 'covered_population_raw_float']}; 30={g.loc[30, 'covered_population_raw_float']}", "status": "PASS" if g.loc[60, "covered_population_raw_float"] >= g.loc[30, "covered_population_raw_float"] else "FAIL"})
    for threshold in THRESHOLDS:
        for minutes in TIMES:
            for group in GROUPS:
                values = [float(indexed.loc[(f"{scenario}_ge{threshold}", minutes, group), "covered_population_raw_float"]) for scenario in SCENARIOS]
                rows.append({"check": "coverage monotonic across scenario expansion", "network": f"ge{threshold}", "time_minutes": minutes, "population_group": group, "details": " <= ".join(map(str, values)), "status": "PASS" if all(a <= b + 1e-8 for a, b in zip(values, values[1:])) else "FAIL"})
    for group in GROUPS:
        unique = coverage.loc[coverage.population_group.eq(group), "population_denominator"].unique()
        rows.append({"check": "constant denominator", "population_group": group, "details": str(unique.tolist()), "status": "PASS" if len(unique) == 1 and int(unique[0]) == denominators[group] else "FAIL"})
    for row in classes.itertuples(index=False):
        total = row.urban_sites + row.rural_sites + row.other_sites + row.missing_settlement_classification
        rows.append({"check": "site settlement counts sum to network", "network": f"{row.suppression_scenario}_ge{row.volume_threshold}", "details": f"classes={total}; sites={row.site_count}", "status": "PASS" if total == row.site_count else "FAIL"})
    visible20 = classes[(classes.volume_threshold.eq(20)) & classes.suppression_scenario.eq("visible")].iloc[0]
    rows.append({"check": "control: all visible ge20 sites urban", "network": "visible_ge20", "details": f"urban={visible20.urban_sites}; total={visible20.site_count}", "status": "PASS" if visible20.urban_sites == visible20.site_count else "FAIL"})
    result = pd.DataFrame(rows)
    if not result.status.eq("PASS").all():
        failed = result[result.status.ne("PASS")]
        raise RuntimeError(f"QA failed:\n{failed.to_string(index=False)}")
    return result


def provenance_report() -> str:
    routing = json.loads(ROUTING_METADATA.read_text(encoding="utf-8"))
    population = json.loads(POPULATION_METADATA.read_text(encoding="utf-8"))
    identity = json.loads(ORS_IDENTITY.read_text(encoding="utf-8"))
    engine = routing["ors_status"]["engine"]
    with rasterio.open(POP) as pop, rasterio.open(SMOD) as smod:
        raster_lines = (
            f"- GHS-POP: `{rel(POP)}`, SHA-256 `{sha256(POP)}`, GHS-POP R2023A, epoch 2025, 3 arcsec, original CRS `{pop.crs}`, pixel size `{pop.res[0]} × {abs(pop.res[1])}` degrees. Evidence: filename, raster metadata and `{rel(POPULATION_METADATA)}`. Status: demonstrated by run artifacts.\n"
            f"- GHS-SMOD: `{rel(SMOD)}`, SHA-256 `{sha256(SMOD)}`, GHS-SMOD R2023A, epoch 2025, 1,000 m, original CRS `{smod.crs}`. Evidence: filename, raster metadata and `{rel(POPULATION_METADATA)}`. Status: demonstrated by run artifacts.\n"
        )
    return f"""# Routing and geodata provenance

## OpenRouteService

- Engine/software version: **{engine['version']}**. Evidence: stored runtime status in `{rel(ROUTING_METADATA)}`, repeated in `{rel(ORS_IDENTITY)}` and the ORS log startup line. Status: demonstrated by run artifacts.
- `graph_version`: **{engine['graph_version']}**. This is a graph-format value and is not evidence of the ORS software version.
- Container tag: `{routing['container_config_image_tag']}`. The tag was mutable and is not sufficient version evidence by itself.
- Image ID: `{routing['image_id']}`.
- Image digest: `{routing['repo_digests'][0]}`. Status: demonstrated by stored Docker inspection metadata.
- Routing profile: `{routing['profile']}`. Status: demonstrated by runtime status and graph metadata.
- Isochrone parameters: time ranges of 30 and 60 minutes, `range_type=time`, `attributes=[area]`, stable validated longitude/latitude pairs and the established helper's largest exterior polygon. Network polygons use `shapely.unary_union`. No new routing was performed for this sensitivity analysis.
- Engine build date: `{engine['build_date']}`. Graph date: `{engine['graph_date']}`. OSM data timestamp: `{engine['osm_date']}`.
- OSM extract: `{rel(OSM)}`, SHA-256 `{sha256(OSM)}`, source filename `germany-latest.osm.pbf`. Germany coverage is indicated by the filename, graph bounds and configuration. The upstream provider, download URL and actual download timestamp are not reconstructable. The filesystem modification time is not treated as a download date.
- Graph construction is evidenced by `ors-docker/logs/ors.log`, which records graph creation from `files/germany-latest.osm.pbf` beginning on 2026-04-01 and by `{rel(GRAPH_INFO)}`. The effective source path was supplied by the stored container environment and overrode the example path in the YAML configuration.

## Population, settlement and boundary data

{raster_lines}- Germany boundary: `{rel(GERMANY)}`, SHA-256 `{sha256(GERMANY)}`. The boundary clips both denominators and coverage geometries. Exact upstream release and licence are not embedded and are not reconstructable from the run artifacts.
- Population overlay: the Germany boundary and isochrones are handled in EPSG:4326. GHS-SMOD is reprojected to each GHS-POP processing window with nearest-neighbour resampling. GHS-POP values are not resampled. Raster inclusion uses `all_touched=False`. EPSG:3035 is used only for geometry-area QA.
- Settlement aggregation: GHS-SMOD codes 30, 23, 22 and 21 map to urban. Codes 13, 12 and 11 map to rural. Every other value maps to other. Point classification uses the original SMOD value sampled at each validated site coordinate.
- Population denominators from the actual raster overlay are national 83,194,666.82777423, urban 60,644,251.4457971, rural 22,550,345.888311617 and other 69.49366551530291 before rounding. The reported integer denominators are 83,194,667, 60,644,251, 22,550,346 and 69. Independently rounded class denominators sum to one fewer person than the independently rounded national denominator.

## Evidence classification

- Demonstrated by run artifacts: ORS 9.8.0, image ID and digest, driving-car profile, graph and OSM timestamps, isochrone parameters, exact raster files, raster metadata, reprojection and resampling, class mapping and analysis denominators.
- Configuration only: the mutable image tag `latest` and paths appearing solely in configuration are not treated as proof without the stored runtime metadata.
- Not reconstructable: OSM provider and download URL, actual OSM download time, exact upstream release/licence of the Germany boundary and any routing parameter left at the ORS default rather than explicitly sent.
"""


def report_text(coverage: pd.DataFrame, contributions: pd.DataFrame, classes: pd.DataFrame, qa: pd.DataFrame) -> str:
    indexed = coverage.set_index(["network", "time_minutes", "population_group"])
    rows20 = []
    for scenario in SCENARIOS:
        n = indexed.loc[(f"{scenario}_ge20", 60, "national")]
        r = indexed.loc[(f"{scenario}_ge20", 60, "rural")]
        rows20.append({
            "scenario": scenario,
            "sites": int(n.site_count),
            "national_60min_pct": round(float(n.coverage_pct_unrounded), 2),
            "national_change_vs_visible_pp": round(float(n.difference_vs_visible_same_threshold_percentage_points), 2),
            "rural_60min_pct": round(float(r.coverage_pct_unrounded), 2),
            "rural_change_vs_visible_pp": round(float(r.difference_vs_visible_same_threshold_percentage_points), 2),
        })
    summary20 = pd.DataFrame(rows20)
    top = contributions[contributions.time_minutes.eq(60)].sort_values("additional_rural_percentage_points", ascending=False).drop_duplicates("site_id").head(10)
    class20 = classes[classes.volume_threshold.eq(20)]
    other = coverage[(coverage.population_group.eq("other")) & coverage.network.str.endswith("ge20")][[
        "suppression_scenario", "time_minutes", "covered_population", "population_denominator", "coverage_pct_2dp"
    ]]
    lower_rural = indexed.loc[("lower_ge20", 60, "rural")]
    upper_rural = indexed.loc[("upper_ge20", 60, "rural")]
    methods = (
        "We conducted a routing-free suppression sensitivity analysis for the 2024 inclusive TIPS-related OPS network. "
        "For each resolved physical site, suppressed code entries contributed one procedure occurrence in the lower scenario, two in the midpoint scenario and three in the upper scenario. "
        "The midpoint was treated as a scenario rather than an estimate. Networks meeting 20, 50 and 100 procedure occurrence thresholds were assembled from stable site identifiers and existing 30-minute and 60-minute driving-car isochrones. "
        "Isochrones were combined before population aggregation to prevent double counting. Coverage was estimated with GHS-POP R2023A epoch 2025 and stratified using GHS-SMOD R2023A epoch 2025 as urban, rural or other."
    )
    scenario_site_counts = {
        scenario: int(indexed.loc[(f"{scenario}_ge20", 60, "national"), "site_count"])
        for scenario in SCENARIOS
    }
    results = (
        f"The visible 20-procedure network contained {scenario_site_counts['visible']} sites and covered {indexed.loc[('visible_ge20', 60, 'national'), 'coverage_pct_unrounded']:.1f}% of the national population and {indexed.loc[('visible_ge20', 60, 'rural'), 'coverage_pct_unrounded']:.1f}% of the rural population within 60 minutes. "
        f"The lower, midpoint and upper scenarios contained {scenario_site_counts['lower']}, {scenario_site_counts['midpoint']} and {scenario_site_counts['upper']} sites. Rural 60-minute coverage increased to {lower_rural.coverage_pct_unrounded:.1f}% in the lower scenario and {upper_rural.coverage_pct_unrounded:.1f}% in the upper scenario, corresponding to {lower_rural.difference_vs_visible_same_threshold_percentage_points:+.1f} and {upper_rural.difference_vs_visible_same_threshold_percentage_points:+.1f} percentage points compared with the visible network. "
        "The direction of the main finding was unchanged because the 60-minute network continued to cover a substantially smaller share of rural than urban population in every suppression scenario."
    )
    return f"""# Geographic suppression sensitivity for 2024

## Scope and inputs

This routing-free analysis uses the inclusive OPS definition, exact-code site precedence, the final 193-site geographic master and the completed bank of individual 30-minute and 60-minute isochrones. Existing final outputs were read but not modified.

## Main results for the 20-procedure threshold

{markdown(summary20)}

## Site settlement classes for the 20-procedure networks

{markdown(class20)}

All 60 sites in the visible 20-procedure network sampled an urban GHS-SMOD class. An urban site can still add access for rural population. Site class and covered-population class are therefore reported separately.

## Largest non-additive rural contributions at 60 minutes

{markdown(top[["volume_threshold", "suppression_scenario", "site_id", "site_name", "derived_settlement_category", "additional_rural_population", "additional_rural_percentage_points"]])}

Each value compares the visible network at the same threshold with that visible network plus one site. Contributions overlap spatially and must not be summed. Scenario gains use the joint union of all selected sites.

## Population group other

{markdown(other)}

The underlying other denominator is 69.4937 people before rounding and 69 after independent presentation rounding. A change of only a few people can therefore produce a large percentage-point difference. The category is reported completely but does not support a separate policy conclusion.

## Plausibility checks

All {len(qa)} checks passed. Stable site IDs were unique, all selected sites had coordinates and both isochrones, threshold and scenario sets were nested, coverage did not decline as a network expanded, 60-minute coverage was never below 30-minute coverage, denominators remained constant and the visible reference networks reproduced all existing covered-population counts exactly.

## Interpretation

Suppression assumptions expand the threshold-qualified networks and improve estimated accessibility. The largest changes occur at the 20-procedure threshold. The comparison does not alter the qualitative finding that rural potential accessibility remains below urban potential accessibility. Results represent TIPS-related procedural activity under the inclusive OPS definition and do not establish de novo TIPS capability.

## English Methods candidate

{methods}

## English Results candidate

{results}

## Provenance

See `routing_and_geodata_provenance.md` for the evidence hierarchy and unresolved metadata.
"""


def manifest_rows(paths: list[tuple[Path, str]]) -> pd.DataFrame:
    rows = []
    for path, role in paths:
        stat = path.stat()
        rows.append({
            "role": role,
            "path": rel(path),
            "size_bytes": stat.st_size,
            "modified_timestamp_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
            "sha256": sha256(path),
        })
    return pd.DataFrame(rows).sort_values(["role", "path"])


def main() -> None:
    if OUT.exists():
        raise RuntimeError(f"Refusing to overwrite existing output directory: {OUT}")
    work = add_point_settlement_classes(load_master_and_activity())
    bank, geometry_issues = load_geometry_bank(set(work.site_id))
    site_lists = build_site_lists(work)
    expected_counts = expected_counts_from_established_metrics()
    for scenario in SCENARIOS:
        for threshold in THRESHOLDS:
            observed = len(site_lists[f"{scenario}_ge{threshold}"])
            if observed != expected_counts[(scenario, threshold)]:
                raise RuntimeError(f"Scenario count mismatch for {scenario} ge{threshold}: {observed}")

    computed_names = {
        key: ids for key, ids in site_lists.items()
        if key not in {"full_identifiable", "openly_numeric"} and not key.startswith("visible_")
    }
    computed_unions = unions_from_site_lists(computed_names, bank)
    visible_unions = load_locked_visible_unions()
    reference_unions = {(network, minutes): load_single_geometry(path) for (network, minutes), path in RECOVERY_REFERENCE_UNIONS.items()}
    all_unions = {**computed_unions, **visible_unions, **reference_unions}
    recovery = load_recovery_module()
    raw_totals, raw_covered = recovery.raw_population_overlay(all_unions)
    denominators, canonical_values = canonical_visible_values()
    coverage = coverage_rows(all_unions, site_lists, raw_totals, raw_covered, denominators)
    membership = membership_table(work, site_lists)
    classes = class_counts(membership)
    contributions = contribution_table(work, site_lists, bank, visible_unions, raw_totals, denominators, recovery)
    qa = qa_table(work, site_lists, coverage, expected_counts, canonical_values, denominators, geometry_issues, classes)

    OUT.mkdir(parents=True, exist_ok=False)
    outputs = [
        write_csv(coverage, OUT / "geographic_suppression_sensitivity_results.csv"),
        write_csv(membership, OUT / "geographic_suppression_network_membership.csv"),
        write_csv(contributions, OUT / "added_site_nonadditive_contributions.csv"),
        write_csv(classes, OUT / "network_site_settlement_class_counts.csv"),
        write_csv(qa, OUT / "plausibility_checks.csv"),
        write_text(table_s5_markdown(coverage), OUT / "TableS5_geographic_suppression_sensitivity.md"),
        write_text(provenance_report(), OUT / "routing_and_geodata_provenance.md"),
    ]
    outputs.append(write_text(report_text(coverage, contributions, classes, qa), OUT / "geographic_suppression_sensitivity_report.md"))

    inputs = [
        (MASTER, "input"), (SITE_DATA, "input"), (SUPPRESSION_METRICS, "input"),
        (LOCKED_UNIONS, "input"), (LOCKED_SITE_ISO, "input"),
        (LOCKED_ACCESS_NATIONAL, "input"), (LOCKED_ACCESS_CLASS, "input"), (TABLE_S5, "input"),
        (RECOVERY_CHECKPOINT, "input"), (RECOVERY_SCRIPT, "input"),
        (ROUTING_METADATA, "input"), (POPULATION_METADATA, "input"), (ORS_IDENTITY, "input"),
        (POP, "input"), (SMOD, "input"), (GERMANY, "input"),
        (ORS_CONFIG, "input"), (GRAPH_INFO, "input"), (OSM, "input"),
        (Path(__file__).resolve(), "analysis_code"),
        *[(path, "input") for path in RECOVERY_REFERENCE_UNIONS.values()],
        *[(path, "input") for path in RECOVERY_REFERENCE_COVERAGE.values()],
        *[(path, "output") for path in outputs],
    ]
    checkpoint = pd.read_csv(RECOVERY_CHECKPOINT, dtype=str)
    recovery_geometry_paths = sorted({
        ROOT / str(value)
        for column in ("geometry_30m_path", "geometry_60m_path")
        for value in checkpoint[column].dropna()
    })
    inputs.extend((path, "input") for path in recovery_geometry_paths)
    manifest = manifest_rows(inputs)
    manifest_path = write_csv(manifest, OUT / "sha256_manifest.csv")
    print(json.dumps({
        "output_directory": rel(OUT),
        "scenario_counts": {f"{scenario}_ge{threshold}": len(site_lists[f"{scenario}_ge{threshold}"]) for scenario in SCENARIOS for threshold in THRESHOLDS},
        "qa_checks": len(qa),
        "manifest_sha256": sha256(manifest_path),
        "outputs": [rel(path) for path in [*outputs, manifest_path]],
    }, indent=2))


if __name__ == "__main__":
    main()
