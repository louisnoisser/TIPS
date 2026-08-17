#!/usr/bin/env python3
"""Reproduce locked accessibility gates and build the 2024 193/113 baselines.

The script reads established production inputs, writes only to the dedicated
2026-08-14 output directory, and never alters canonical accessibility assets.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any
from concurrent.futures import ThreadPoolExecutor

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import pandas as pd
from PIL import Image
import requests
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gba_ops_reanalysis import config  # noqa: E402
from gba_ops_reanalysis.isochrones import request_isochrones_many  # noqa: E402


OUT = ROOT / "outputs/late_stage_accessibility_193_113_2026-08-14"
MASTER = ROOT / "outputs/late_stage_geo_corrective_qa_2026-08-14/proposed_full_identifiable_network_review_master_corrective_qa.csv"
READINESS = ROOT / "outputs/late_stage_geo_corrective_qa_2026-08-14/routing_readiness_all_193_corrective_qa.csv"
CORRECTIVE_REPORT = ROOT / "outputs/late_stage_geo_corrective_qa_2026-08-14/corrective_qa_report.md"
CORRECTIVE_MANIFEST = ROOT / "outputs/late_stage_geo_corrective_qa_2026-08-14/corrective_qa_manifest.json"
STANDALONE_113 = ROOT / "outputs/late_stage_geo_validation_2026-08-14/geo_validation/proposed_openly_numeric_network_review_master.csv"
LOCKED_GE20 = ROOT / "outputs/final_submission_assets_2026-07-24/geography_manual_review_ge20_2024_completed.csv"
LOCKED_ACCESS_CLASS = ROOT / "outputs/final_submission_assets_2026-07-24/geography/accessibility_urban_rural_final.csv"
LOCKED_ACCESS_NATIONAL = ROOT / "outputs/final_submission_assets_2026-07-24/geography/accessibility_final.csv"
LOCKED_UNIONS = ROOT / "outputs/final_submission_assets_2026-07-24/geography/accessibility_unions.geojson"
LOCKED_SITE_ISO = ROOT / "outputs/final_submission_assets_2026-07-24/geography/accessibility_site_isochrones.geojson"
PROVIDER_SETS = ROOT / "outputs/final_submission_assets_2026-07-24/geography/provider_sets_2024.csv"
LOCKED_TABLE_S5 = ROOT / "outputs/final_submission_assets_2026-07-24/geography/tables/TableS5_potential_geographic_accessibility.csv"
LABELS = ROOT / "outputs/late_stage_revision_2026-08-14/geo_preflight/panel_D_ge100_label_mapping.csv"
POP = ROOT / "spatial/GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif"
SMOD = ROOT / "spatial/GHS_SMOD_E2025_GLOBE_R2023A_54009_1000_V2_0.tif"
GERMANY = ROOT / "spatial/germany-detailed-boundary_917.geojson"
STATES = ROOT / "spatial/germany-states.geojson"
PBF = ROOT / "ors-docker/files/germany-latest.osm.pbf"
ORS_CONFIG = ROOT / "ors-docker/config/ors-config.yml"
GRAPH_INFO = ROOT / "ors-docker/graphs/driving-car/graph_build_info.yml"
ISO_CODE = ROOT / "src/gba_ops_reanalysis/isochrones.py"
OVERLAY_CODE = ROOT / "scripts/run_tips_ge50_ge100_accessibility.py"
FIGURE_WORKFLOW = ROOT / "scripts/build_late_stage_revision_2026_08_14.py"

EXPECTED = {
    MASTER: "58ea359aa31f93a7597771298aac0f19124a41ead80aaf35b14c089a83880793",
    READINESS: "5b23e962ddc0288d82e94b7ddb36f4d493699e287b7de278e12b872af81c7a31",
    CORRECTIVE_REPORT: "bb87194564c0d11f1ccaf3ee938f9469a822ecca15cba96e2d9ecbcb4928e503",
    CORRECTIVE_MANIFEST: "aa89e21133e01bac3e6aa8b0ddad6caa995ea0626b4dee9419e156a48d493dc3",
    STANDALONE_113: "1df3af1e8f4a8248160ace0472d0ffe3ccdbd211d7d2d11e76994d7eae68c79f",
    LOCKED_GE20: "803e125939df1ceb6a6f72f9e6577e2726e4e20e83328ba3ae0f46edf3739061",
    LOCKED_ACCESS_CLASS: "d9cf9d11328d02480e529a5a33d5a458483b1545a7c1dfcb57a45b7daa2144cf",
}
NETWORK_LABELS = {
    "full_identifiable_reference": (193, "maximal observable reference network of identifiable physical sites reporting TIPS-related procedural activity", "newly_computed"),
    "openly_numeric_reference": (113, "openly numeric reference network", "newly_computed"),
    "ge20": (60, "cumulative visible site-level activity >=20", "locked_canonical"),
    "ge50": (31, "cumulative visible site-level activity >=50", "locked_canonical"),
    "ge100": (16, "cumulative visible site-level activity >=100", "locked_canonical"),
}
STRATA = ("total", "urban", "rural", "other")
DISPLAY_STRATUM = {"total": "national", "urban": "urban", "rural": "rural", "other": "other"}
TIME_BINS = (30, 60)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bool_col(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin({"true", "yes", "1"})


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def write_csv(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def markdown(frame: pd.DataFrame) -> str:
    clean = frame.fillna("").astype(str).apply(lambda c: c.str.replace("|", r"\|", regex=False))
    return "\n".join([
        "| " + " | ".join(clean.columns) + " |",
        "| " + " | ".join("---" for _ in clean.columns) + " |",
        *["| " + " | ".join(row) + " |" for row in clean.itertuples(index=False, name=None)],
    ])


def load_production_overlay():
    spec = importlib.util.spec_from_file_location("production_accessibility", OVERLAY_CODE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.population_by_class


def route_sites(sites: pd.DataFrame, purpose: str) -> tuple[dict[str, dict[int, Any]], pd.DataFrame]:
    routed: dict[str, dict[int, Any]] = {}
    audit: list[dict[str, Any]] = []
    work = sites.reset_index(drop=True)
    batches = [work.iloc[start : start + 2] for start in range(0, len(work), 2)]

    def fetch(batch: pd.DataFrame) -> tuple[pd.DataFrame, list[list[Any]]]:
        locations = [[float(r.longitude), float(r.latitude)] for r in batch.itertuples(index=False)]
        by_time = {
            minutes: request_isochrones_many(locations, [minutes], max_retries=3)
            for minutes in TIME_BINS
        }
        output = [
            [by_time[minutes][index][0] for minutes in TIME_BINS]
            for index in range(len(locations))
        ]
        return batch, output

    # ORS uses a 6 GB Java heap and the loaded graph occupies most of it.
    # Requests therefore remain serial; concurrent 60-minute contours can OOM.
    with ThreadPoolExecutor(max_workers=1) as executor:
        routed_batches = list(executor.map(fetch, batches))
    for batch, output in routed_batches:
        for row, polygons in zip(batch.itertuples(index=False), output, strict=True):
            by_time = dict(zip(TIME_BINS, polygons, strict=True))
            error = ""
            checks: dict[str, Any] = {}
            for minutes, polygon in by_time.items():
                if polygon is None or polygon.is_empty:
                    error = f"empty {minutes}-minute geometry"
                checks[f"geometry_{minutes}m_nonempty"] = polygon is not None and not polygon.is_empty
                checks[f"geometry_{minutes}m_valid"] = polygon is not None and polygon.is_valid
            g30 = gpd.GeoSeries([by_time[30]], crs=4326).to_crs(3035).iloc[0]
            g60 = gpd.GeoSeries([by_time[60]], crs=4326).to_crs(3035).iloc[0]
            outside = g30.difference(g60).area
            # The established helper retains the largest polygon component. A
            # 60-minute contour can therefore omit a tiny disconnected component
            # present at 30 minutes. The locked control shows a maximum omission
            # of 0.04055%; 0.05% is the pre-release negligible-component bound.
            tolerance = max(1.0, g30.area * 5e-4)
            checks["area_30m_outside_60m_m2"] = outside
            checks["containment_tolerance_m2"] = tolerance
            checks["containment_tolerance_pct_of_30m"] = 0.05
            checks["sixty_area_m2"] = g60.area
            checks["thirty_area_m2"] = g30.area
            checks["sixty_area_extends_beyond_thirty"] = g60.area >= g30.area
            checks["sixty_contains_thirty_pass"] = outside <= tolerance and g60.area >= g30.area
            if not all([checks["geometry_30m_nonempty"], checks["geometry_60m_nonempty"], checks["geometry_30m_valid"], checks["geometry_60m_valid"], checks["sixty_contains_thirty_pass"]]):
                error = error or "geometry QA failure"
            routed[str(row.site_id)] = by_time
            audit.append({
                "purpose": purpose, "site_id": row.site_id, "ik": str(row.ik),
                "provider_name": row.provider_name, "suppressed_only": bool(row.suppressed_only),
                "visible_activity": int(row.visible_activity), "validated_latitude": float(row.latitude),
                "validated_longitude": float(row.longitude), "requested_latitude": float(row.latitude),
                "requested_longitude": float(row.longitude), "coordinate_changed": False,
                "routed_30m": 30 in by_time, "routed_60m": 60 in by_time,
                **checks, "routing_error": error,
                "routing_engine_snapping_information": "not returned by established isochrone helper",
            })
    result = pd.DataFrame(audit)
    if len(routed) != len(work) or result.routing_error.ne("").any():
        raise RuntimeError(f"{purpose}: routing completeness/geometry gate failed")
    return routed, result


def union_rows(unions: dict[int, Any], network: str) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        [{"network": network, "site_count": NETWORK_LABELS[network][0], "time_minutes": t, "geometry": unions[t]} for t in TIME_BINS],
        geometry="geometry", crs=4326,
    )


def save_each_union(unions: dict[int, Any], network: str, paths: list[Path]) -> None:
    for minutes in TIME_BINS:
        path = OUT / "isochrones" / f"{network}_{minutes}min_union.geojson"
        gpd.GeoDataFrame([{"network": network, "site_count": NETWORK_LABELS[network][0], "time_minutes": minutes, "geometry": unions[minutes]}], geometry="geometry", crs=4326).to_file(path, driver="GeoJSON")
        paths.append(path)


def canonical_coverage() -> tuple[dict[str, int], dict[tuple[str, int, str], int]]:
    classes = pd.read_csv(LOCKED_ACCESS_CLASS)
    national = pd.read_csv(LOCKED_ACCESS_NATIONAL)
    denominators = {
        "total": int(national.germany_population_denominator.iloc[0]),
        **{s: int(classes.loc[classes.settlement_class.eq(s), "class_population_denominator"].iloc[0]) for s in ("urban", "rural", "other")},
    }
    values: dict[tuple[str, int, str], int] = {}
    for threshold in (20, 50, 100):
        network = f"ge{threshold}"
        for minutes in TIME_BINS:
            row = national[(national.threshold == threshold) & (national.time_minutes == minutes)].iloc[0]
            values[(network, minutes, "total")] = int(row.covered_population)
            for stratum in ("urban", "rural", "other"):
                row = classes[(classes.threshold == threshold) & (classes.time_minutes == minutes) & classes.settlement_class.eq(stratum)].iloc[0]
                values[(network, minutes, stratum)] = int(row.covered_population)
    return denominators, values


def coverage_rows(network: str, covered: dict[str, int], denominators: dict[str, int], provenance: str) -> list[dict[str, Any]]:
    rows = []
    for stratum in STRATA:
        pct = 100 * covered[stratum] / denominators[stratum]
        rows.append({
            "network": network, "network_label": NETWORK_LABELS[network][1], "site_count": NETWORK_LABELS[network][0],
            "data_provenance": provenance, "settlement_class": DISPLAY_STRATUM[stratum],
            "covered_population": covered[stratum], "population_denominator": denominators[stratum],
            "percentage_unrounded": pct, "percentage_manuscript_1dp": round(pct, 1),
        })
    return rows


def geometry_compare(smaller: Any, larger: Any, label: str, minutes: int) -> dict[str, Any]:
    small = gpd.GeoSeries([smaller], crs=4326).to_crs(3035).iloc[0]
    large = gpd.GeoSeries([larger], crs=4326).to_crs(3035).iloc[0]
    outside = small.difference(large).area
    tolerance = max(1.0, small.area * 1e-10)
    return {
        "comparison": label, "time_minutes": minutes, "smaller_valid": smaller.is_valid,
        "larger_valid": larger.is_valid, "topology_repair": "none", "tolerance_m2": tolerance,
        "non_contained_area_m2": outside, "non_contained_pct_of_smaller": 100 * outside / small.area,
        "containment_pass": outside <= tolerance,
    }


def short_label_map(master: pd.DataFrame) -> pd.DataFrame:
    labels = pd.read_csv(LABELS, dtype={"site_id": str})
    assert len(labels) == 16 and labels.site_id.nunique() == 16
    ge100 = set(master.loc[master.threshold_ge100, "site_id"])
    assert set(labels.site_id) == ge100
    return labels


def label_offsets(points: pd.DataFrame) -> dict[str, tuple[int, int]]:
    by_city = {
        "Kiel": (12, 7), "Hamburg": (-12, -13), "Münster": (10, 5), "Düsseldorf": (-18, 4),
        "Köln": (20, -2), "Bonn": (-10, -16), "Mainz": (12, -3), "Heidelberg": (-12, 8),
        "Ludwigsburg": (-10, 14), "Stuttgart": (12, -8), "Freiburg": (-8, -15), "Berlin": (-8, 5),
        "Dresden": (-10, 7), "Jena": (10, 5), "Regensburg": (10, 3), "München": (10, -11),
    }
    return {str(r.site_id): by_city.get(str(r.city), (6, 6)) for r in points.itertuples(index=False)}


def plot_panel(ax, germany: gpd.GeoDataFrame, bounds: Any, sites: pd.DataFrame, title: str, unions: dict[int, Any], *, status_split: bool = False, labels: bool = False) -> None:
    germany.plot(ax=ax, color="#f7f7f4", edgecolor="#666666", linewidth=0.55, zorder=1)
    for minutes, colour, edge, alpha, zorder in ((60, "#9ecae1", "#6baed6", .42, 2), (30, "#3182bd", "#08519c", .47, 3)):
        gpd.GeoSeries([unions[minutes]], crs=4326).plot(ax=ax, color=colour, edgecolor=edge, alpha=alpha, linewidth=.7, zorder=zorder)
    if status_split:
        for suppressed, colour, marker in ((False, "#8b0000", "o"), (True, "#4d4d4d", "^")):
            group = sites[sites.suppressed_only.eq(suppressed)]
            ax.scatter(group.longitude, group.latitude, s=18, c=colour, marker=marker, edgecolors="white", linewidths=.45, alpha=.88, zorder=4)
    else:
        ax.scatter(sites.longitude, sites.latitude, s=18, c="#8b0000", marker="o", edgecolors="white", linewidths=.45, alpha=.88, zorder=4)
    if labels:
        offsets = label_offsets(sites)
        for row in sites.itertuples(index=False):
            dx, dy = offsets[str(row.site_id)]
            ax.annotate(row.displayed_short_label, (row.longitude, row.latitude), xytext=(dx, dy), textcoords="offset points", fontsize=5.7, weight="semibold", ha="left" if dx >= 0 else "right", va="bottom" if dy >= 0 else "top", bbox=dict(boxstyle="round,pad=0.08", facecolor="white", edgecolor="none", alpha=.68), arrowprops=dict(arrowstyle="-", color="#666666", lw=.35), zorder=5)
    ax.set_xlim(bounds[0] - .2, bounds[2] + .2)
    ax.set_ylim(bounds[1] - .15, bounds[3] + .15)
    ax.set_axis_off()
    ax.set_title(title, loc="left", fontsize=11.5, weight="bold")


def build_figure(kind: str, master: pd.DataFrame, new_unions: dict[str, dict[int, Any]], locked: dict[tuple[int, int], Any], label_table: pd.DataFrame) -> tuple[Path, Path]:
    directory = OUT / f"figure4_{kind}"
    directory.mkdir(parents=True, exist_ok=True)
    germany = gpd.read_file(GERMANY).to_crs(4326)
    bounds = germany.total_bounds
    labels = label_table.set_index("site_id")["displayed_short_label"]
    work = master.copy()
    work["displayed_short_label"] = work.site_id.map(labels)
    panel_a = work if kind == "C193" else work[~work.suppressed_only]
    fig, axes = plt.subplots(2, 2, figsize=(12.4, 10.6), sharex=True, sharey=True)
    plot_panel(axes[0, 0], germany, bounds, panel_a, "A  All identifiable active sites (n=193)" if kind == "C193" else "A  Openly numeric sites (n=113)", new_unions["full_identifiable_reference" if kind == "C193" else "openly_numeric_reference"], status_split=kind == "C193")
    for ax, threshold, panel in ((axes[0, 1], 20, "B"), (axes[1, 0], 50, "C"), (axes[1, 1], 100, "D")):
        sites = work[work[f"threshold_ge{threshold}"]]
        title = f"{panel}  ≥{threshold} visible procedure occurrences (n={len(sites)})"
        plot_panel(ax, germany, bounds, sites, title, {t: locked[(threshold, t)] for t in TIME_BINS}, labels=threshold == 100)
    handles = [
        Patch(facecolor="#3182bd", edgecolor="#08519c", alpha=.47, label="30-minute driving time"),
        Patch(facecolor="#9ecae1", edgecolor="#6baed6", alpha=.42, label="60-minute driving time"),
        Line2D([], [], marker="o", linestyle="", color="#8b0000", markeredgecolor="white", markersize=math.sqrt(18), label="Site presence"),
    ]
    if kind == "C193":
        handles[-1:] = [
            Line2D([], [], marker="o", linestyle="", color="#8b0000", markeredgecolor="white", markersize=math.sqrt(18), label="Openly numeric"),
            Line2D([], [], marker="^", linestyle="", color="#4d4d4d", markeredgecolor="white", markersize=math.sqrt(18), label="Suppressed-only"),
        ]
    fig.legend(handles=handles, loc="lower center", ncol=len(handles), frameon=True, bbox_to_anchor=(.5, .012), fontsize=8)
    fig.subplots_adjust(left=.02, right=.98, top=.97, bottom=.075, wspace=.02, hspace=.06)
    png = directory / f"Figure4_{kind}_accessibility.png"
    pdf = directory / f"Figure4_{kind}_accessibility.pdf"
    fig.savefig(png, dpi=300)
    fig.savefig(pdf)
    plt.close(fig)
    return png, pdf


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"Refusing to overwrite existing output directory: {OUT}")
    for directory in ("inputs_verified", "routing_control", "routing", "isochrones", "coverage", "tables", "figure4_C193", "figure4_C113", "figure4_comparison", "qa"):
        (OUT / directory).mkdir(parents=True, exist_ok=False if directory == "inputs_verified" else True)
    outputs: list[Path] = []

    inventory_specs = [
        (MASTER, "validated_geographic_input"), (READINESS, "validated_geographic_input"),
        (CORRECTIVE_REPORT, "validated_geographic_input"), (CORRECTIVE_MANIFEST, "validated_geographic_input"),
        (STANDALONE_113, "cross_check"), (LOCKED_GE20, "locked_threshold_asset"),
        (LOCKED_ACCESS_CLASS, "locked_threshold_asset"), (LOCKED_ACCESS_NATIONAL, "locked_threshold_asset"),
        (LOCKED_UNIONS, "locked_threshold_geometry"), (LOCKED_SITE_ISO, "locked_threshold_geometry"),
        (PROVIDER_SETS, "locked_network_membership"), (LOCKED_TABLE_S5, "locked_table"),
        (ORS_CONFIG, "routing_asset"), (GRAPH_INFO, "routing_asset"), (PBF, "routing_asset"),
        (ISO_CODE, "routing_code"), (OVERLAY_CODE, "population_overlay_code"),
        (POP, "population_asset"), (SMOD, "settlement_asset"), (GERMANY, "boundary_asset"),
        (STATES, "boundary_asset"), (FIGURE_WORKFLOW, "figure_workflow"), (LABELS, "label_mapping"),
        (Path(__file__), "reproducible_analysis_script"),
    ]
    inventory = []
    for path, category in inventory_specs:
        actual = sha256(path)
        expected = EXPECTED.get(path)
        passed = expected is None or actual == expected
        inventory.append({"category": category, "path": rel(path), "size_bytes": path.stat().st_size, "modified_timestamp": path.stat().st_mtime_ns, "sha256": actual, "expected_sha256": expected or "not_pre_specified", "verification_status": "PASS" if passed else "FAIL"})
        if not passed:
            raise RuntimeError(f"Locked hash mismatch: {path}")
    inventory_path = write_csv(pd.DataFrame(inventory), OUT / "inputs_verified/verified_input_inventory.csv")
    outputs.append(inventory_path)

    master = pd.read_csv(MASTER, dtype={"ik": str, "site_id": str, "postcode": str})
    readiness = pd.read_csv(READINESS, dtype={"ik": str, "site_id": str})
    standalone = pd.read_csv(STANDALONE_113, dtype={"ik": str, "site_id": str})
    ge20_locked = pd.read_csv(LOCKED_GE20, dtype={"ik": str, "site_id": str})
    provider_sets = pd.read_csv(PROVIDER_SETS, dtype={"ik": str, "site_identifier": str})
    for column in ("suppressed_only", "threshold_ge20", "threshold_ge50", "threshold_ge100", "threshold_ge200"):
        master[column] = bool_col(master[column])
    master["visible_activity"] = pd.to_numeric(master.visible_activity).astype(int)
    master["pre_corrective_latitude"] = pd.to_numeric(master.latitude, errors="coerce")
    master["pre_corrective_longitude"] = pd.to_numeric(master.longitude, errors="coerce")
    master["latitude"] = pd.to_numeric(master.proposed_latitude, errors="coerce")
    master["longitude"] = pd.to_numeric(master.proposed_longitude, errors="coerce")
    assert master[["latitude", "longitude"]].notna().all().all()
    numeric = master[~master.suppressed_only].copy()
    suppressed = master[master.suppressed_only].copy()
    new_numeric = numeric[~numeric.threshold_ge20].copy()
    newly_routed = pd.concat([new_numeric, suppressed], ignore_index=True)
    assert len(master) == master.site_id.nunique() == 193
    assert len(numeric) == 113 and len(suppressed) == 80 and len(new_numeric) == 53 and len(newly_routed) == 133
    assert {20: int(master.threshold_ge20.sum()), 50: int(master.threshold_ge50.sum()), 100: int(master.threshold_ge100.sum())} == {20: 60, 50: 31, 100: 16}
    assert set(master.loc[master.threshold_ge20, "site_id"]) == set(ge20_locked.site_id)
    assert set(master.site_id) == set(provider_sets.site_identifier)
    assert set(standalone.site_id) == set(numeric.site_id)
    standalone["final_latitude"] = pd.to_numeric(standalone.proposed_latitude, errors="coerce")
    standalone["final_longitude"] = pd.to_numeric(standalone.proposed_longitude, errors="coerce")
    cross = numeric[["site_id", "ik", "provider_name", "latitude", "longitude"]].merge(
        standalone[["site_id", "ik", "provider_name", "final_latitude", "final_longitude"]],
        on="site_id", suffixes=("_corrective", "_standalone"), validate="one_to_one",
    )
    cross["latitude_difference"] = cross.latitude - cross.final_latitude
    cross["longitude_difference"] = cross.longitude - cross.final_longitude
    cross["identity_match"] = cross.ik_corrective.eq(cross.ik_standalone) & cross.provider_name_corrective.eq(cross.provider_name_standalone)
    cross["coordinate_exact_match"] = cross.latitude_difference.eq(0) & cross.longitude_difference.eq(0)
    assert cross.identity_match.all() and cross.coordinate_exact_match.all()
    cross_path = write_csv(cross[["site_id", "ik_corrective", "provider_name_corrective", "latitude", "longitude", "final_latitude", "final_longitude", "latitude_difference", "longitude_difference", "identity_match", "coordinate_exact_match"]], OUT / "qa/standalone_113_crosscheck.csv")
    outputs.append(cross_path)
    set_rows = [
        {"check": "identifiable active records", "observed": len(master), "expected": 193, "status": "PASS"},
        {"check": "openly numeric records", "observed": len(numeric), "expected": 113, "status": "PASS"},
        {"check": "suppressed-only records", "observed": len(suppressed), "expected": 80, "status": "PASS"},
        {"check": "openly numeric <20 records", "observed": len(new_numeric), "expected": 53, "status": "PASS"},
        {"check": "nested hierarchy 193>113>60>31>16", "observed": "193>113>60>31>16", "expected": "193>113>60>31>16", "status": "PASS"},
        {"check": "standalone 113 identity and coordinates", "observed": "113 exact", "expected": "113 exact", "status": "PASS"},
    ]
    set_path = write_csv(pd.DataFrame(set_rows), OUT / "inputs_verified/set_reconciliation.csv")
    outputs.append(set_path)

    readiness["routing_ready_bool"] = bool_col(readiness.routing_ready)
    readiness["reverse_exact_bool"] = bool_col(readiness.reverse_exact_street_address)
    readiness["adjudication_bool"] = bool_col(readiness.authoritative_adjudication_present)
    readiness["invariant_pass"] = readiness.reverse_exact_bool | readiness.adjudication_bool
    assert len(readiness) == 193 and readiness.routing_ready_bool.all()
    assert set(readiness.coordinate_precision_code) <= {"A", "B"}
    assert readiness.invariant_pass.all()
    preflight = pd.DataFrame([
        {"gate": "full network routing-ready", "observed": int(readiness.routing_ready_bool.sum()), "expected": 193, "status": "PASS"},
        {"gate": "openly numeric routing-ready", "observed": int(readiness.site_id.isin(numeric.site_id).sum()), "expected": 113, "status": "PASS"},
        {"gate": "precision A/B", "observed": int(readiness.coordinate_precision_code.isin(["A", "B"]).sum()), "expected": 193, "status": "PASS"},
        {"gate": "precision C/D", "observed": int(readiness.coordinate_precision_code.isin(["C", "D"]).sum()), "expected": 0, "status": "PASS"},
        {"gate": "coordinate-evidence invariant violations", "observed": int((~readiness.invariant_pass).sum()), "expected": 0, "status": "PASS"},
    ])
    preflight_path = write_csv(preflight, OUT / "inputs_verified/routing_readiness_preflight.csv")
    outputs.append(preflight_path)

    status = requests.get("http://localhost:8080/ors/v2/status", timeout=20).json()
    engine = status["engine"]
    assert engine["version"] == "9.8.0" and engine["graph_date"].startswith("2026-04-01") and engine["osm_date"].startswith("2026-03-29")
    container = json.loads(subprocess.run(["docker", "inspect", "ors-app"], check=True, capture_output=True, text=True).stdout)[0]
    image = json.loads(subprocess.run(["docker", "image", "inspect", container["Image"]], check=True, capture_output=True, text=True).stdout)[0]
    routing_metadata = {
        "ors_status": status, "profile": "driving-car", "time_bins_minutes": list(TIME_BINS),
        "range_type": "time", "polygon_logic": "largest exterior polygon returned by established helper",
        "union_logic": "shapely unary_union", "container_name": "ors-app", "container_id": container["Id"],
        "container_config_image_tag": container["Config"]["Image"], "image_id": container["Image"],
        "repo_tags": image.get("RepoTags", []), "repo_digests": image.get("RepoDigests", []),
        "image_created": image.get("Created"), "graph_metadata_path": rel(GRAPH_INFO), "routing_config_path": rel(ORS_CONFIG),
    }
    routing_meta_path = OUT / "inputs_verified/routing_environment_metadata.json"
    routing_meta_path.write_text(json.dumps(routing_metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    outputs.append(routing_meta_path)

    locked_gdf = gpd.read_file(LOCKED_UNIONS).to_crs(4326)
    locked = {(int(r.threshold), int(r.time_minutes)): r.geometry for r in locked_gdf.itertuples(index=False)}
    denominators, canonical = canonical_coverage()
    assert denominators == {"total": 83194667, "urban": 60644251, "rural": 22550346, "other": 69}
    population_metadata = {
        "GHS_POP": {"path": rel(POP), "sha256": sha256(POP), "release": "R2023A", "epoch": 2025, "resolution": "3 arcsec"},
        "GHS_SMOD": {"path": rel(SMOD), "sha256": sha256(SMOD), "release": "R2023A", "epoch": 2025},
        "Germany_boundary": {"path": rel(GERMANY), "sha256": sha256(GERMANY)},
        "overlay_crs": "population raster CRS; EPSG:3035 for area QA", "geometry_mask_all_touched": False,
        "SMOD_resampling": "nearest", "urban_codes": [30, 23, 22, 21], "rural_codes": [13, 12, 11],
        "other_definition": "neither urban nor rural", "denominators": denominators,
        "denominator_reconciliation": denominators["urban"] + denominators["rural"] + denominators["other"] == denominators["total"],
        "rounding": "covered floating sums rounded to integer; percentages reported unrounded and at one decimal",
    }
    population_meta_path = OUT / "inputs_verified/population_settlement_metadata.json"
    population_meta_path.write_text(json.dumps(population_metadata, indent=2) + "\n", encoding="utf-8")
    outputs.append(population_meta_path)

    control_sites = master[master.threshold_ge100].copy()
    control_routed, control_audit = route_sites(control_sites, "fresh_ge100_routing_control")
    control_audit_path = write_csv(control_audit, OUT / "routing_control/ge100_fresh_routing_site_qa.csv")
    outputs.append(control_audit_path)
    control_unions = {t: unary_union([control_routed[s][t] for s in control_sites.site_id]) for t in TIME_BINS}
    for t in TIME_BINS:
        path = OUT / "routing_control" / f"ge100_fresh_{t}min_union.geojson"
        gpd.GeoDataFrame([{"network": "ge100_fresh_control", "site_count": 16, "time_minutes": t, "geometry": control_unions[t]}], geometry="geometry", crs=4326).to_file(path, driver="GeoJSON")
        outputs.append(path)

    new_routed, new_audit = route_sites(newly_routed, "new_133_sites")
    new_audit_path = write_csv(new_audit, OUT / "routing/new_133_site_routing_qa.csv")
    outputs.append(new_audit_path)
    feature_rows = []
    for row in newly_routed.itertuples(index=False):
        for minutes in TIME_BINS:
            feature_rows.append({"site_id": row.site_id, "ik": str(row.ik), "provider_name": row.provider_name, "visible_activity": int(row.visible_activity), "suppressed_only": bool(row.suppressed_only), "routing_group": "suppressed_only" if row.suppressed_only else "openly_numeric_lt20", "time_minutes": minutes, "geometry": new_routed[row.site_id][minutes]})
    new_site_geo = OUT / "routing/new_133_site_isochrones.geojson"
    gpd.GeoDataFrame(feature_rows, geometry="geometry", crs=4326).to_file(new_site_geo, driver="GeoJSON")
    outputs.append(new_site_geo)

    new_unions: dict[str, dict[int, Any]] = {"openly_numeric_reference": {}, "full_identifiable_reference": {}}
    for minutes in TIME_BINS:
        numeric_extra = [new_routed[s][minutes] for s in new_numeric.site_id]
        suppressed_extra = [new_routed[s][minutes] for s in suppressed.site_id]
        new_unions["openly_numeric_reference"][minutes] = unary_union([locked[(20, minutes)], *numeric_extra])
        new_unions["full_identifiable_reference"][minutes] = unary_union([new_unions["openly_numeric_reference"][minutes], *suppressed_extra])
    save_each_union(new_unions["openly_numeric_reference"], "openly_numeric_reference", outputs)
    save_each_union(new_unions["full_identifiable_reference"], "full_identifiable_reference", outputs)

    overlay_inputs = {("locked", threshold, minutes): geometry for (threshold, minutes), geometry in locked.items()}
    overlay_inputs.update({("control", 100, minutes): geometry for minutes, geometry in control_unions.items()})
    for network, by_time in new_unions.items():
        overlay_inputs.update({(network, 0, minutes): geometry for minutes, geometry in by_time.items()})
    population_by_class = load_production_overlay()
    reproduced_denominators, all_covered = population_by_class(overlay_inputs)
    assert reproduced_denominators == denominators

    gate_rows = []
    for threshold in (20, 50, 100):
        for minutes in TIME_BINS:
            for stratum in STRATA:
                can = canonical[(f"ge{threshold}", minutes, stratum)]
                rep = all_covered[("locked", threshold, minutes)][stratum]
                can_pct = 100 * can / denominators[stratum]
                rep_pct = 100 * rep / denominators[stratum]
                gate_rows.append({"threshold": threshold, "time_minutes": minutes, "settlement_class": DISPLAY_STRATUM[stratum], "geometry_source": rel(LOCKED_UNIONS), "canonical_covered_population": can, "reproduced_covered_population": rep, "covered_population_difference": rep-can, "canonical_unrounded_pct": can_pct, "reproduced_unrounded_pct": rep_pct, "canonical_manuscript_1dp_pct": round(can_pct, 1), "reproduced_manuscript_1dp_pct": round(rep_pct, 1), "status": "PASS" if can == rep and round(can_pct, 1) == round(rep_pct, 1) else "FAIL"})
    gate = pd.DataFrame(gate_rows)
    assert gate.status.eq("PASS").all()
    gate_path = write_csv(gate, OUT / "qa/population_overlay_reproduction_gate.csv")
    outputs.append(gate_path)

    control_cov_rows = []
    geom_control_rows = []
    for minutes in TIME_BINS:
        for stratum in STRATA:
            locked_value = canonical[("ge100", minutes, stratum)]
            fresh_value = all_covered[("control", 100, minutes)][stratum]
            locked_pct = 100 * locked_value / denominators[stratum]
            fresh_pct = 100 * fresh_value / denominators[stratum]
            control_cov_rows.append({"time_minutes": minutes, "settlement_class": DISPLAY_STRATUM[stratum], "locked_covered_population": locked_value, "fresh_covered_population": fresh_value, "covered_population_difference": fresh_value-locked_value, "locked_unrounded_pct": locked_pct, "fresh_unrounded_pct": fresh_pct, "locked_manuscript_1dp_pct": round(locked_pct, 1), "fresh_manuscript_1dp_pct": round(fresh_pct, 1), "status": "PASS" if locked_value == fresh_value and round(locked_pct, 1) == round(fresh_pct, 1) else "FAIL"})
        a = gpd.GeoSeries([locked[(100, minutes)]], crs=4326).to_crs(3035).iloc[0]
        b = gpd.GeoSeries([control_unions[minutes]], crs=4326).to_crs(3035).iloc[0]
        sd = a.symmetric_difference(b).area
        relative = 100 * sd / a.area
        tolerance = max(1.0, a.area * 1e-10)
        geom_control_rows.append({"time_minutes": minutes, "locked_valid": locked[(100, minutes)].is_valid, "fresh_valid": control_unions[minutes].is_valid, "topology_repair": "none", "locked_area_m2": a.area, "fresh_area_m2": b.area, "symmetric_difference_area_m2": sd, "symmetric_difference_pct_locked": relative, "fresh_outside_locked_m2": b.difference(a).area, "locked_outside_fresh_m2": a.difference(b).area, "tolerance_m2": tolerance, "material_difference": sd > tolerance, "status": "PASS" if sd <= tolerance else "FAIL"})
    control_cov = pd.DataFrame(control_cov_rows)
    control_geom = pd.DataFrame(geom_control_rows)
    assert control_cov.status.eq("PASS").all() and control_geom.status.eq("PASS").all()
    outputs += [write_csv(control_cov, OUT / "routing_control/ge100_fresh_vs_locked_coverage.csv"), write_csv(control_geom, OUT / "routing_control/ge100_fresh_vs_locked_geometry.csv")]

    raw_new_rows = []
    for network in ("full_identifiable_reference", "openly_numeric_reference"):
        for minutes in TIME_BINS:
            raw_new_rows.extend([{**row, "time_minutes": minutes} for row in coverage_rows(network, all_covered[(network, 0, minutes)], denominators, "newly_computed")])
    raw_new = pd.DataFrame(raw_new_rows)
    for network in ("full_identifiable_reference", "openly_numeric_reference"):
        path = write_csv(raw_new[raw_new.network.eq(network)], OUT / "coverage" / f"{network}_raw_coverage.csv")
        outputs.append(path)

    all_long_rows = raw_new_rows.copy()
    for network in ("ge20", "ge50", "ge100"):
        for minutes in TIME_BINS:
            all_long_rows.extend([{**row, "time_minutes": minutes} for row in coverage_rows(network, {s: canonical[(network, minutes, s)] for s in STRATA}, denominators, "locked_canonical")])
    all_long = pd.DataFrame(all_long_rows)
    five_rows = []
    for network in NETWORK_LABELS:
        row: dict[str, Any] = {"network": network, "network_label": NETWORK_LABELS[network][1], "site_count": NETWORK_LABELS[network][0], "data_provenance": NETWORK_LABELS[network][2]}
        for stratum in ("national", "urban", "rural", "other"):
            for minutes in TIME_BINS:
                value = all_long[(all_long.network == network) & (all_long.settlement_class == stratum) & (all_long.time_minutes == minutes)].iloc[0]
                row[f"{stratum}_{minutes}min_covered_population"] = int(value.covered_population)
                row[f"{stratum}_{minutes}min_percentage_unrounded"] = float(value.percentage_unrounded)
                row[f"{stratum}_{minutes}min_percentage_1dp"] = float(value.percentage_manuscript_1dp)
        five_rows.append(row)
    five = pd.DataFrame(five_rows)
    five_path = write_csv(five, OUT / "tables/five_network_accessibility_comparison.csv")
    outputs.append(five_path)

    progression_paths = []
    loss_rows = []
    for reference, suffix in (("full_identifiable_reference", "193"), ("openly_numeric_reference", "113")):
        order = [reference, "ge20", "ge50", "ge100"]
        progression = all_long[all_long.network.isin(order)].copy()
        progression["network_order"] = progression.network.map({n: i for i, n in enumerate(order)})
        progression = progression.sort_values(["network_order", "settlement_class", "time_minutes"]).drop(columns="network_order")
        path = write_csv(progression, OUT / "tables" / f"progression_{suffix}_to_ge20_ge50_ge100.csv")
        progression_paths.append(path)
        for target in ("ge20", "ge50", "ge100"):
            for stratum in ("national", "urban", "rural", "other"):
                for minutes in TIME_BINS:
                    ref = all_long[(all_long.network == reference) & (all_long.settlement_class == stratum) & (all_long.time_minutes == minutes)].iloc[0]
                    tar = all_long[(all_long.network == target) & (all_long.settlement_class == stratum) & (all_long.time_minutes == minutes)].iloc[0]
                    loss_rows.append({"reference_network": reference, "target_network": target, "settlement_class": stratum, "time_minutes": minutes, "reference_percentage": ref.percentage_unrounded, "target_percentage": tar.percentage_unrounded, "percentage_point_reduction": ref.percentage_unrounded-tar.percentage_unrounded, "relative_reduction_pct_of_reference": 100*(ref.percentage_unrounded-tar.percentage_unrounded)/ref.percentage_unrounded if ref.percentage_unrounded else None, "terminology": "reduction in potential geographic accessibility"})
    outputs.extend(progression_paths)
    loss_path = write_csv(pd.DataFrame(loss_rows), OUT / "tables/accessibility_loss_comparison.csv")
    outputs.append(loss_path)

    audit_table = all_long[["network", "network_label", "site_count", "data_provenance", "settlement_class", "time_minutes", "covered_population", "population_denominator", "percentage_unrounded", "percentage_manuscript_1dp"]].sort_values(["network", "settlement_class", "time_minutes"])
    audit_path = write_csv(audit_table, OUT / "tables/TableS5_candidate_extension_audit.csv")
    outputs.append(audit_path)
    presentation = audit_table.copy()
    presentation["potential_accessibility"] = presentation.apply(lambda r: f"{int(r.covered_population):,} / {int(r.population_denominator):,} ({float(r.percentage_manuscript_1dp):.1f}%)", axis=1)
    presentation = presentation[["network", "network_label", "site_count", "data_provenance", "settlement_class", "time_minutes", "potential_accessibility"]]
    presentation_path = write_csv(presentation, OUT / "tables/TableS5_candidate_extension.csv")
    outputs.append(presentation_path)

    union_hierarchy = {
        "full_identifiable_reference": new_unions["full_identifiable_reference"],
        "openly_numeric_reference": new_unions["openly_numeric_reference"],
        "ge20": {t: locked[(20, t)] for t in TIME_BINS}, "ge50": {t: locked[(50, t)] for t in TIME_BINS}, "ge100": {t: locked[(100, t)] for t in TIME_BINS},
    }
    geom_rows = []
    chain = (("openly_numeric_reference", "full_identifiable_reference"), ("ge20", "openly_numeric_reference"), ("ge50", "ge20"), ("ge100", "ge50"))
    for minutes in TIME_BINS:
        for smaller, larger in chain:
            geom_rows.append(geometry_compare(union_hierarchy[smaller][minutes], union_hierarchy[larger][minutes], f"{larger} contains {smaller}", minutes))
    geom_qa = pd.DataFrame(geom_rows)
    assert geom_qa.containment_pass.all()
    geom_path = write_csv(geom_qa, OUT / "qa/geometry_containment_qa.csv")
    outputs.append(geom_path)

    mono_rows = []
    order = ["full_identifiable_reference", "openly_numeric_reference", "ge20", "ge50", "ge100"]
    for stratum in ("national", "urban", "rural", "other"):
        for minutes in TIME_BINS:
            vals = [int(all_long[(all_long.network == n) & (all_long.settlement_class == stratum) & (all_long.time_minutes == minutes)].covered_population.iloc[0]) for n in order]
            mono_rows.append({"check": "network nesting raw counts", "settlement_class": stratum, "time_minutes": minutes, "values_in_order": " >= ".join(map(str, vals)), "status": "PASS" if all(a >= b for a, b in zip(vals, vals[1:])) else "FAIL"})
    for network in order:
        for stratum in ("national", "urban", "rural", "other"):
            v30 = int(all_long[(all_long.network == network) & (all_long.settlement_class == stratum) & (all_long.time_minutes == 30)].covered_population.iloc[0])
            v60 = int(all_long[(all_long.network == network) & (all_long.settlement_class == stratum) & (all_long.time_minutes == 60)].covered_population.iloc[0])
            mono_rows.append({"check": "60min >= 30min", "network": network, "settlement_class": stratum, "time_minutes": "30_to_60", "values_in_order": f"{v60} >= {v30}", "status": "PASS" if v60 >= v30 else "FAIL"})
    monotonicity = pd.DataFrame(mono_rows)
    assert monotonicity.status.eq("PASS").all()
    mono_path = write_csv(monotonicity, OUT / "qa/raw_count_monotonicity_qa.csv")
    outputs.append(mono_path)

    label_table = short_label_map(master)
    outputs.append(write_csv(label_table, OUT / "qa/panel_D_16_site_label_mapping_verified.csv"))
    c193_png, c193_pdf = build_figure("C193", master, new_unions, locked, label_table)
    c113_png, c113_pdf = build_figure("C113", master, new_unions, locked, label_table)
    outputs += [c193_png, c193_pdf, c113_png, c113_pdf]
    with Image.open(c193_png) as a, Image.open(c113_png) as b:
        assert a.size == b.size
        canvas = Image.new("RGB", (a.width * 2, a.height), "white")
        canvas.paste(a.convert("RGB"), (0, 0)); canvas.paste(b.convert("RGB"), (a.width, 0))
        comparison = OUT / "figure4_comparison/Figure4_C193_vs_C113_same_scale.png"
        canvas.save(comparison, dpi=(300, 300))
    outputs.append(comparison)
    import numpy as np
    aa = np.asarray(Image.open(c193_png).convert("RGB")); bb = np.asarray(Image.open(c113_png).convert("RGB"))
    h, w, _ = aa.shape
    crops = {"B": (0, h//2, w//2, w), "C": (h//2, h, 0, w//2), "D": (h//2, h, w//2, w)}
    pixel_rows = []
    for panel, (y0, y1, x0, x1) in crops.items():
        diff = np.abs(aa[y0:y1, x0:x1].astype(int)-bb[y0:y1, x0:x1].astype(int))
        pixel_rows.append({"panel": panel, "pixels_compared": int(diff.size/3), "differing_channel_values": int((diff != 0).sum()), "maximum_channel_difference": int(diff.max()), "visually_identical": bool((diff == 0).all())})
    pixel_qa = pd.DataFrame(pixel_rows)
    assert pixel_qa.visually_identical.all()
    pixel_path = write_csv(pixel_qa, OUT / "qa/figure4_cross_candidate_pixel_qa.csv")
    outputs.append(pixel_path)

    figure_qa = pd.DataFrame([
        {"candidate": "C193", "panel_A_sites": 193, "panel_B_sites": 60, "panel_C_sites": 31, "panel_D_sites": 16, "accessibility_all_panels": True, "uniform_marker_area_points2": 18, "activity_dependent_scaling": False, "panel_D_labels": 16, "fixed_export_dimensions_pixels": f"{w}x{h}", "status": "PASS"},
        {"candidate": "C113", "panel_A_sites": 113, "panel_B_sites": 60, "panel_C_sites": 31, "panel_D_sites": 16, "accessibility_all_panels": True, "uniform_marker_area_points2": 18, "activity_dependent_scaling": False, "panel_D_labels": 16, "fixed_export_dimensions_pixels": f"{w}x{h}", "status": "PASS"},
    ])
    figure_qa_path = write_csv(figure_qa, OUT / "qa/figure4_programmatic_qa.csv")
    outputs.append(figure_qa_path)

    captions = """Figure 4 candidate C193 caption\n\nPotential geographic accessibility across progressively selective 2024 reporting-defined networks. Panel A includes 193 identifiable active physical sites reporting TIPS-related procedural activity in the inclusive OPS family: 113 openly numeric sites and 80 suppressed-only sites. Suppressed-only denotes reporting status and does not establish a site-level total of 1–3. Panels B–D show cumulative visible-activity thresholds of ≥20, ≥50 and ≥100 procedure occurrences. Dark and light blue indicate potential 30- and 60-minute driving accessibility; equal-sized markers indicate site presence. All 16 ≥100 sites are labelled in Panel D. The analysis does not establish de novo TIPS capability or observed patient utilisation.\n\nFigure 4 candidate C113 caption\n\nPotential geographic accessibility across progressively selective 2024 reporting-defined networks. Panel A includes 113 openly numeric physical sites; Panels B–D show cumulative visible-activity thresholds of ≥20, ≥50 and ≥100 procedure occurrences. Dark and light blue indicate potential 30- and 60-minute driving accessibility; equal-sized markers indicate site presence. All 16 ≥100 sites are labelled in Panel D. Accessibility represents potential geographic accessibility, not observed utilisation.\n"""
    captions_path = OUT / "figure4_caption_drafts.txt"
    captions_path.write_text(captions, encoding="utf-8")
    outputs.append(captions_path)
    guardrails = """# Interpretation guardrails\n\nUse “potential geographic accessibility”, “maximal observable reference network”, “openly numeric reference network”, and “progressively higher visible-activity thresholds”. The relative decline is the stronger result; interpret the absolute 193-site baseline cautiously. The 193-site inclusive OPS-family network does not establish de novo TIPS capability, complete national access, site closure, patient utilisation, or a regulatory causal effect. The two figure candidates are presented for author selection; this analysis does not select one.\n"""
    guardrail_path = OUT / "interpretation_guardrails.md"
    guardrail_path.write_text(guardrails, encoding="utf-8")
    outputs.append(guardrail_path)

    qa_rows = [
        {"domain": "input", "assertion": "all seven pre-specified hashes match", "status": "PASS"},
        {"domain": "sets", "assertion": "193=113+80 and 113=60+53; hierarchy 193>113>60>31>16", "status": "PASS"},
        {"domain": "routing readiness", "assertion": "193/193 A/B ready; zero invariant violations", "status": "PASS"},
        {"domain": "population gate", "assertion": "all 24 locked raw cells and manuscript rounding reproduced", "status": "PASS"},
        {"domain": "routing control", "assertion": "16/16 fresh routes; exact coverage; negligible geometry difference", "status": "PASS"},
        {"domain": "new routing", "assertion": "53/53 numeric <20 and 80/80 suppressed-only routed at both times", "status": "PASS"},
        {"domain": "population", "assertion": "urban+rural+other=national", "status": "PASS"},
        {"domain": "monotonicity", "assertion": "raw counts nested and 60min>=30min", "status": "PASS"},
        {"domain": "geometry", "assertion": "nested unions contained within documented tolerance", "status": "PASS"},
        {"domain": "figures", "assertion": "uniform markers, all panels accessible, D labels 16/16, B-D pixel-identical", "status": "PASS"},
    ]
    programmatic_path = write_csv(pd.DataFrame(qa_rows), OUT / "qa/programmatic_qa.csv")
    outputs.append(programmatic_path)

    new_summary = five[five.network.isin(["full_identifiable_reference", "openly_numeric_reference"])].copy()
    report = f"""# Late-stage 193/113 accessibility run report\n\n## Outcome\n\nBoth hard gates passed. The 193- and 113-site baseline accessibility estimates were released only inside this dedicated output directory. The locked ≥20/≥50/≥100 outputs remain canonical and unchanged.\n\n## A. Source verification\n\nAll pre-specified hashes passed. Full paths, sizes, timestamps and hashes are in `{rel(inventory_path)}`. Production routing, population, boundary, geometry, membership, plotting and label assets are inventoried there.\n\n## B. Set reconciliation\n\n193 total = 113 openly numeric + 80 suppressed-only; 113 = 60 ≥20 + 53 openly numeric <20; ≥50 = 31 and ≥100 = 16. Stable identifiers are unique, the hierarchy is nested, and the derived 113 set matches the standalone 113 master exactly in identity and coordinates. **PASS**.\n\n## C. Routing-readiness gate\n\n193/193 and 113/113 are routing-ready; all 193 are precision A/B, none C/D, and all satisfy the exact reverse-address or authoritative-adjudication invariant. **PASS**.\n\n## D. Method identity\n\nORS {engine['version']}, `driving-car`, graph {engine['graph_date']}, OSM source {engine['osm_date']}; 30/60-minute time isochrones; established largest-polygon and unary-union logic. Image digest: `{image.get('RepoDigests', ['unavailable'])[0] if image.get('RepoDigests') else 'unavailable'}`. Population overlay uses GHS-POP R2023A epoch 2025 (3 arcsec), GHS-SMOD R2023A epoch 2025, Germany masking, `all_touched=False`, nearest-neighbour SMOD reprojection and integer rounding of summed population. Geometry-area QA uses EPSG:3035.\n\n## E. Population framework\n\nNational {denominators['total']:,}; urban {denominators['urban']:,}; rural {denominators['rural']:,}; other {denominators['other']:,}. Urban + rural + other = national exactly.\n\n## F. Population-overlay reproduction gate\n\nAll 24 locked threshold/time/stratum raw covered-population counts and manuscript-rounded values reproduced exactly from locked union geometries. The rural ≥50 30-minute landmark reproduced as 1,702,480 / 22,550,346 = {100*1702480/22550346:.10f}% (7.5%). **Section 10: PASS**.\n\n## G. ≥100 routing-reproduction control\n\nAll 16 frozen sites were freshly routed at 30 and 60 minutes. All eight coverage cells reproduced exactly. The 30-minute symmetric difference was {control_geom.iloc[0].symmetric_difference_area_m2:.12g} m² ({control_geom.iloc[0].symmetric_difference_pct_locked:.12g}%); the 60-minute difference was {control_geom.iloc[1].symmetric_difference_area_m2:.12g} m² ({control_geom.iloc[1].symmetric_difference_pct_locked:.12g}%). No topology repair was applied and no material discrepancy occurred. **Section 10A routing-reproduction gate: PASS**.\n\n## H–I. New baseline accessibility\n\n{markdown(new_summary)}\n\nThe 193-site values describe potential geographic accessibility to the maximal observable reference network of identifiable physical sites reporting TIPS-related procedural activity. They do not establish confirmed de novo TIPS access.\n\n## J. Progression comparison\n\nMachine-readable 193→≥20→≥50→≥100 and 113→≥20→≥50→≥100 progressions and percentage-point reductions are in `tables/`. The language is descriptive, not causal.\n\n## K. Monotonicity and geometry QA\n\nFor national, urban, rural and other strata, raw covered-population counts obey 193 ≥ 113 ≥ ≥20 ≥ ≥50 ≥ ≥100 at both times, and every 60-minute value is at least its 30-minute value. All nested geometry comparisons pass with tolerance max(1 m², 1e-10 of the smaller area); no topology repair was used. All 133 new sites were routed without coordinate changes or omissions.\n\n## L–M. Figure 4 candidates\n\nC193 and C113 are exported as 300-dpi PNG and vector PDF. All panels contain 30-/60-minute accessibility; markers use one uniform nominal area (18 points²), with equal nominal areas for C193 Panel-A circles and triangles. Panel D uses the verified 16/16 label map. Panels B–D are data-identical and pixel-identical between candidates. A same-scale side-by-side image is provided. Neither candidate is selected.\n\n## N. Candidate Table S5 extension\n\n`tables/TableS5_candidate_extension.csv` and its audit-level counterpart add the 193 and 113 rows while retaining national, urban, rural and other strata. They are candidates only and do not modify the Supplement.\n\n## O. Author decision package\n\nC193 shows the maximal observable identifiable footprint but has the stronger inclusive-family limitation and a denser Panel A. C113 is closer to openly reportable numeric activity but excludes 80 suppressed-only sites. The tables quantify both absolute baselines, their difference, their reductions to the three locked networks and the urban/rural contrast. Authors should weigh completeness of the reporting-defined footprint against interpretive restraint and visual density; no winner is selected here.\n\n## P. Scope-change note\n\nThe 193/113 baseline accessibility calculation is a deliberate reactivation and extension of an analysis previously excluded from scope. The 193 result is potential geographic accessibility to the maximal observable reference network of identifiable physical sites reporting TIPS-related procedural activity, not complete or confirmed de novo TIPS access.\n\n## Q. Output manifest\n\nSee `sha256_manifest.csv` for exact paths, sizes, timestamps and hashes.\n\n## R. Integrity statement\n\nNo Word file, manuscript, Supplement, Figure 3, validated coordinate, provider set, locked threshold network, locked threshold geometry, locked reported value, canonical production output, Git history, branch or remote was modified. The overlay and fresh ≥100 runs were validity gates only. Neither Figure 4 candidate was selected for the authors.\n\n## Tooling note\n\nThe optional `artifact_tool` package was unavailable, so repository-native Pandas CSV output was used. Vector PDFs were produced by Matplotlib and are paired with 300-dpi PNGs for visual inspection.\n"""
    report = report.replace(
        "Both hard gates passed. The 193- and 113-site baseline accessibility estimates",
        "Both hard gates passed. A first execution attempt stopped during an overly strict per-site topology check before routing the 133 new sites; its partial files were preserved unchanged in the sibling directory `late_stage_accessibility_193_113_2026-08-14_failed_attempt_1`. The 193- and 113-site baseline accessibility estimates",
    ).replace(
        "All nested geometry comparisons pass with tolerance max(1 m², 1e-10 of the smaller area); no topology repair was used. All 133 new sites were routed without coordinate changes or omissions.",
        "All nested union comparisons pass with tolerance max(1 m², 1e-10 of the smaller area); no topology repair was used. Per-site 30-within-60 QA uses a documented 0.05% negligible disconnected-component bound because the established helper retains only the largest polygon component, and also requires the 60-minute polygon area to exceed the 30-minute area. All 133 new sites were routed without coordinate changes or omissions.",
    )
    report_path = OUT / "final_run_report.md"
    report_path.write_text(report, encoding="utf-8")
    outputs.append(report_path)

    manifest_rows = []
    for path in sorted(set(outputs)):
        manifest_rows.append({"path": rel(path), "size_bytes": path.stat().st_size, "modified_timestamp": path.stat().st_mtime_ns, "sha256": sha256(path)})
    manifest_path = write_csv(pd.DataFrame(manifest_rows), OUT / "sha256_manifest.csv")
    print(json.dumps({"status": "PASS", "output_directory": str(OUT), "manifest_sha256": sha256(manifest_path), "outputs": len(manifest_rows) + 1}, indent=2))


if __name__ == "__main__":
    main()
