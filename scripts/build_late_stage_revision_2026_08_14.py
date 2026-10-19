#!/usr/bin/env python3
"""Build locked Figure 3 candidates and geographic layout previews.

This script never routes providers, builds isochrones, estimates population
coverage, or changes established production outputs.  Newly geocoded points
are preview-only and remain unvalidated.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gba_ops_reanalysis import config  # noqa: E402
from gba_ops_reanalysis.geocoding import geocode_dataframe  # noqa: E402


OUT = ROOT / "outputs/late_stage_revision_2026-08-14"
F3 = OUT / "figure3_comparison"
GEO = OUT / "geo_preflight"
A113 = OUT / "figure4_A113_preview"
A193 = OUT / "figure4_A193_preview"
ACCESS = OUT / "accessibility_verification"
QA = OUT / "qa"

METRICS = ROOT / "outputs/final_corrected_2026-07-24/suppression_final_metrics.csv"
LOCKED_F3_DIR = ROOT / "outputs/late_stage_revision_2026-08-13/figure3"
LOCKED_F3_DATA = LOCKED_F3_DIR / "Figure3_longitudinal_exclusive_categories_data.csv"
MASTER = ROOT / "outputs/final_submission_assets_2026-07-24/geography/provider_locations_master_2024.csv"
NUMERIC_GEOCODED = ROOT / "outputs/indications/tips_8-839-8_updated2024/tables/latest_year_geocoded_all_centers.csv"
VALIDATED_60 = ROOT / "outputs/final_submission_assets_2026-07-24/geography_manual_review_ge20_2024_completed.csv"
UNIONS = ROOT / "outputs/final_submission_assets_2026-07-24/geography/accessibility_unions.geojson"
ACCESSIBILITY = ROOT / "outputs/final_submission_assets_2026-07-24/geography/accessibility_urban_rural_final.csv"

EXPECTED = {
    METRICS: "d0a52a5d8ea8a250b7d4729a91bae7174272a22752ff772142c8543b7f99cf88",
    LOCKED_F3_DATA: "7ec4a2496fbcf19517e36e7ecbdcf79ab93b830b8601668784fbece173f35ad8",
    LOCKED_F3_DIR / "Figure3_longitudinal_exclusive_categories.png": "a15447dd34a2d6faf0ecdb347a60ff96246a7208967fe5764f38f56e72323e54",
    LOCKED_F3_DIR / "Figure3_longitudinal_exclusive_categories.pdf": "42ccf4b4cce7f13ea6c91085c0c0872bc3ffc2b6dcd71661eb040b43fdb19e7e",
}
YEARS = [2008, 2010, *range(2012, 2025)]
CATEGORY_COLUMNS = ["sites_4_19", "sites_20_49", "sites_50_99", "sites_100_199", "sites_ge_200"]
CATEGORY_LABELS = ["4–19", "20–49", "50–99", "100–199", "≥200"]
COLOURS = ["#d9eaf3", "#a8cde1", "#6baed6", "#3182bd", "#08519c"]
GREY = "#a6a6a6"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def set_style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9, "axes.labelsize": 10,
        "xtick.labelsize": 8.5, "ytick.labelsize": 9, "legend.fontsize": 8.5,
        "axes.spines.top": False, "axes.spines.right": False,
        "figure.facecolor": "white", "savefig.facecolor": "white",
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })


def save(fig: plt.Figure, directory: Path, stem: str, *, tight: bool = True) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths = [directory / f"{stem}.png", directory / f"{stem}.pdf"]
    kwargs = {"bbox_inches": "tight"} if tight else {}
    fig.savefig(paths[0], dpi=600, facecolor="white", **kwargs)
    fig.savefig(paths[1], facecolor="white", **kwargs)
    plt.close(fig)
    return paths


def plot_figure3(data: pd.DataFrame, *, include_suppressed: bool, stem: str) -> list[Path]:
    x = np.arange(len(data))
    fig, ax = plt.subplots(figsize=(7.25, 4.75))
    bottom = np.zeros(len(data), dtype=int)
    for column, label, colour in zip(CATEGORY_COLUMNS, CATEGORY_LABELS, COLOURS, strict=True):
        values = data[column].to_numpy(dtype=int)
        ax.bar(x, values, bottom=bottom, width=0.72, color=colour,
               edgecolor="white", linewidth=0.45, label=label)
        bottom += values
    if include_suppressed:
        values = data["suppressed_only_sites"].to_numpy(dtype=int)
        ax.bar(x, values, bottom=bottom, width=0.72, color=GREY,
               edgecolor="white", linewidth=0.45, label="Suppressed-only")
    ax.set_xlabel("Reporting year", labelpad=8)
    ax.set_ylabel(
        "Identifiable active physical sites, n" if include_suppressed
        else "Openly numeric physical sites, n", labelpad=8,
    )
    ax.set_xticks(x, data.reporting_year.astype(str), rotation=45, ha="right")
    ax.set_xlim(-0.65, len(data) - 0.35)
    ymax = 220 if include_suppressed else 125
    ax.set_ylim(0, ymax)
    ax.set_yticks(np.arange(0, ymax + 1, 20))
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#d9d9d9", linewidth=0.6)
    ax.tick_params(axis="x", length=0)
    ax.tick_params(axis="y", length=3, color="#666666")
    legend_args = dict(ncol=6 if include_suppressed else 5, loc="lower center",
                       bbox_to_anchor=(0.5, 1.01), frameon=False, handlelength=1.2,
                       handletextpad=0.45, columnspacing=1.05)
    if not include_suppressed:
        legend_args["title"] = "Visible procedure occurrences"
        legend_args["title_fontsize"] = 8.5
    ax.legend(**legend_args)
    fig.subplots_adjust(left=0.12, right=0.99, bottom=0.20, top=0.83)
    return save(fig, F3, stem, tight=False)


def build_figure3() -> list[Path]:
    for path, expected in EXPECTED.items():
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"Locked source hash mismatch: {path}: {actual}")
    locked = pd.read_csv(LOCKED_F3_DATA)
    metrics = pd.read_csv(METRICS)
    visible = metrics.loc[
        metrics.provider_definition.eq("physical_site")
        & metrics.suppression_scenario.eq("visible")
        & metrics.reporting_year.isin(YEARS)
    ].sort_values("reporting_year").reset_index(drop=True)
    locked = locked.sort_values("reporting_year").reset_index(drop=True)
    if locked.reporting_year.tolist() != YEARS or visible.reporting_year.tolist() != YEARS:
        raise RuntimeError("Figure 3 year sequence failed")
    numeric_sum = locked[CATEGORY_COLUMNS].sum(axis=1).astype(int)
    if not numeric_sum.equals(visible.active_numeric_providers.astype(int)):
        raise RuntimeError("Locked numeric stacks disagree with physical-site/visible metrics")
    candidate_b = locked.copy()
    candidate_b["identifiable_active_physical_sites"] = visible.all_identifiable_active_providers.astype(int)
    candidate_b["suppressed_only_sites"] = (
        candidate_b.identifiable_active_physical_sites - numeric_sum
    ).astype(int)
    candidate_b["candidate_b_stack_sum"] = numeric_sum + candidate_b.suppressed_only_sites
    expected_suppressed = [60, 74, 69, 66, 75, 90, 83, 82, 81, 86, 84, 85, 74, 79, 80]
    if candidate_b.suppressed_only_sites.tolist() != expected_suppressed:
        raise RuntimeError("Suppressed-only annual series failed")
    if not candidate_b.candidate_b_stack_sum.equals(candidate_b.identifiable_active_physical_sites):
        raise RuntimeError("Candidate B stack totals failed")
    data_path = F3 / "Figure3_candidate_B_identifiable_network_data.csv"
    F3.mkdir(parents=True, exist_ok=True)
    candidate_b.to_csv(data_path, index=False)
    paths = [data_path]
    paths += plot_figure3(locked, include_suppressed=False, stem="Figure3_candidate_A_numeric_only")
    paths += plot_figure3(candidate_b, include_suppressed=True, stem="Figure3_candidate_B_identifiable_network")
    checks = [
        ("locked_hashes_match", True),
        ("exact_year_sequence", locked.reporting_year.tolist() == YEARS),
        ("numeric_segments_unchanged", sha256(LOCKED_F3_DATA) == EXPECTED[LOCKED_F3_DATA]),
        ("numeric_stack_matches_physical_site_visible", numeric_sum.equals(visible.active_numeric_providers.astype(int))),
        ("candidate_b_totals_match_identifiable_active", candidate_b.candidate_b_stack_sum.equals(candidate_b.identifiable_active_physical_sites)),
        ("all_counts_non_negative_integers", bool((candidate_b[CATEGORY_COLUMNS + ["suppressed_only_sites"]] >= 0).all().all())),
        ("2008_numeric_total_28", int(numeric_sum.iloc[0]) == 28),
        ("2024_numeric_segments_53_29_15_10_6", locked.loc[locked.reporting_year.eq(2024), CATEGORY_COLUMNS].iloc[0].astype(int).tolist() == [53,29,15,10,6]),
        ("2024_identifiable_total_193", int(candidate_b.iloc[-1].candidate_b_stack_sum) == 193),
    ]
    qa_path = QA / "Figure3_candidates_programmatic_QA.csv"
    QA.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(checks, columns=["check", "passed"]).to_csv(qa_path, index=False)
    return paths + [qa_path]


def bool_col(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().eq("true")


def prepare_geography(do_geocode: bool) -> tuple[pd.DataFrame, pd.DataFrame, list[Path]]:
    master = pd.read_csv(MASTER, dtype={"ik": str, "site_id": str, "postcode": str})
    for column in ["suppressed_only", "threshold_ge20", "threshold_ge50", "threshold_ge100", "threshold_ge200"]:
        master[column] = bool_col(master[column])
    master["visible_activity"] = pd.to_numeric(master.visible_activity, errors="coerce").fillna(0).astype(int)
    if len(master) != 193 or master.site_id.nunique() != 193:
        raise RuntimeError("Canonical 193-site master failed")
    numeric = master.loc[~master.suppressed_only].copy()
    suppressed = master.loc[master.suppressed_only].copy()
    ge20 = numeric.loc[numeric.threshold_ge20].copy()
    below20 = numeric.loc[~numeric.threshold_ge20].copy()
    if (len(numeric), len(suppressed), len(ge20), len(below20)) != (113, 80, 60, 53):
        raise RuntimeError("Provider set reconciliation failed")
    if set(numeric.site_id) & set(suppressed.site_id):
        raise RuntimeError("Numeric/suppressed overlap")

    numeric_source = pd.read_csv(NUMERIC_GEOCODED, dtype=str)
    source_id = "facility_id" if "facility_id" in numeric_source else "site_id"
    if set(numeric_source[source_id]) != set(numeric.site_id):
        raise RuntimeError("113-site geocoded source does not match numeric master")

    candidate113 = numeric.copy()
    candidate113["panel_a_group"] = np.where(candidate113.threshold_ge20, "A_validated_numeric_ge20", "B_unvalidated_numeric_lt20")
    candidate113["preview_coordinate_status"] = np.where(
        candidate113.threshold_ge20, "VALIDATED – LOCKED ≥20 RECORD", "EXISTING PROJECT GEOCODE – NOT MANUALLY VALIDATED"
    )
    candidate113["candidate_status"] = "PROVISIONAL – UNVALIDATED PANEL-A COORDINATES"

    missing_c = suppressed.latitude.isna() | suppressed.longitude.isna()
    geocode_cache = GEO / "suppressed_only_automatic_preview_geocode_cache.csv"
    geocoded_path = GEO / "suppressed_only_automatic_preview_geocodes.csv"
    if missing_c.any() and do_geocode:
        inputs = suppressed.loc[missing_c].copy()
        inputs["facility_id"] = inputs.site_id
        inputs["full_address"] = inputs.original_address
        inputs["postal_code"] = inputs.postcode
        inputs = inputs.drop(
            columns=["latitude", "longitude", "geocode_source", "geocode_query"],
            errors="ignore",
        )
        geocoded = geocode_dataframe(inputs, cache_path=geocode_cache, min_delay_seconds=1.0)
        geocoded.to_csv(geocoded_path, index=False)
    elif geocoded_path.exists():
        geocoded = pd.read_csv(geocoded_path, dtype={"facility_id": str, "site_id": str, "postcode": str})
    else:
        geocoded = pd.DataFrame()
    if not geocoded.empty:
        geocoded = geocoded.set_index("site_id")
        suppressed = suppressed.set_index("site_id")
        for column in ["latitude", "longitude"]:
            suppressed.loc[geocoded.index, column] = pd.to_numeric(geocoded[column], errors="coerce")
        suppressed.loc[geocoded.index, "coordinate_source"] = geocoded["geocode_source"]
        suppressed.loc[geocoded.index, "coordinate_status"] = "AUTOMATIC PREVIEW GEOCODE – NOT VALIDATED"
        suppressed = suppressed.reset_index()
    suppressed["panel_a_group"] = "C_unvalidated_suppressed_only"
    suppressed["preview_coordinate_status"] = np.where(
        suppressed.latitude.notna() & suppressed.longitude.notna(),
        "AUTOMATIC PREVIEW GEOCODE – NOT VALIDATED", "UNPLOTTABLE – AUTOMATIC PREVIEW GEOCODE FAILED",
    )
    suppressed["candidate_status"] = "PROVISIONAL – UNVALIDATED PANEL-A COORDINATES"
    candidate193 = pd.concat([candidate113, suppressed], ignore_index=True, sort=False)

    candidate113_path = GEO / "candidate_113_panel_A_sites.csv"
    candidate193_path = GEO / "candidate_193_panel_A_sites.csv"
    GEO.mkdir(parents=True, exist_ok=True)
    candidate113.to_csv(candidate113_path, index=False)
    candidate193.to_csv(candidate193_path, index=False)
    return candidate113, candidate193, [candidate113_path, candidate193_path, geocoded_path, geocode_cache]


def germany_bounds() -> tuple[gpd.GeoDataFrame, np.ndarray]:
    germany = gpd.read_file(config.GERMANY_OUTLINE).to_crs("EPSG:4326")
    return germany, germany.total_bounds


def coordinate_flags(candidate: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    work = candidate.copy()
    work["latitude"] = pd.to_numeric(work.latitude, errors="coerce")
    work["longitude"] = pd.to_numeric(work.longitude, errors="coerce")
    for row in work.itertuples(index=False):
        base = {"site_id": row.site_id, "ik": row.ik, "provider_name": row.provider_name,
                "city": row.city, "panel_a_group": row.panel_a_group}
        if pd.isna(row.latitude) or pd.isna(row.longitude):
            rows.append({**base, "flag_type": "missing_coordinate", "flag_detail": "No usable preview coordinate"})
        elif not (47.0 <= float(row.latitude) <= 55.2 and 5.5 <= float(row.longitude) <= 15.6):
            rows.append({**base, "flag_type": "outside_germany_bbox", "flag_detail": f"{row.latitude},{row.longitude}"})
        source = str(getattr(row, "coordinate_source", "")).lower()
        status = str(getattr(row, "coordinate_status", "")).lower()
        if any(term in source + " " + status for term in ["postal", "city", "institution-level", "administrative"]):
            rows.append({**base, "flag_type": "possible_low_precision_or_administrative_coordinate", "flag_detail": f"source={source}; status={status}"})
    located = work.dropna(subset=["latitude", "longitude"]).copy()
    germany = gpd.read_file(config.GERMANY_OUTLINE).to_crs("EPSG:4326").geometry.union_all()
    point_geometries = gpd.points_from_xy(located.longitude, located.latitude)
    outside_polygon = ~gpd.GeoSeries(point_geometries, crs="EPSG:4326").within(germany)
    for row in located.loc[outside_polygon.to_numpy()].itertuples(index=False):
        rows.append({"site_id": row.site_id, "ik": row.ik, "provider_name": row.provider_name,
                     "city": row.city, "panel_a_group": row.panel_a_group,
                     "flag_type": "outside_germany_polygon", "flag_detail": f"{row.latitude},{row.longitude}"})
    states = gpd.read_file(ROOT / "spatial/germany-states.geojson").to_crs("EPSG:4326")
    points = gpd.GeoDataFrame(located[["site_id", "federal_state"]].copy(), geometry=point_geometries, crs="EPSG:4326")
    joined = gpd.sjoin(points, states[["NAME_1", "geometry"]], how="left", predicate="within")
    mismatch_ids = joined.loc[
        joined.federal_state.notna() & joined.NAME_1.notna()
        & joined.federal_state.astype(str).str.strip().ne(joined.NAME_1.astype(str).str.strip()), "site_id"
    ].tolist()
    for row in located.loc[located.site_id.isin(mismatch_ids)].itertuples(index=False):
        mapped = joined.loc[joined.site_id.eq(row.site_id), "NAME_1"].iloc[0]
        rows.append({"site_id": row.site_id, "ik": row.ik, "provider_name": row.provider_name,
                     "city": row.city, "panel_a_group": row.panel_a_group,
                     "flag_type": "coordinate_state_inconsistency_review_prompt",
                     "flag_detail": f"reported={row.federal_state}; coordinate={mapped}"})
    located["coord_key"] = located.latitude.round(6).astype(str) + "|" + located.longitude.round(6).astype(str)
    for _, group in located.groupby("coord_key"):
        if len(group) > 1:
            detail = "|".join(group.site_id.astype(str))
            for row in group.itertuples(index=False):
                rows.append({"site_id": row.site_id, "ik": row.ik, "provider_name": row.provider_name,
                             "city": row.city, "panel_a_group": row.panel_a_group,
                             "flag_type": "duplicate_coordinate_review_prompt", "flag_detail": detail})
    for field, flag in [("normalised_address", "duplicate_address_review_prompt"), ("original_address", "identical_original_address_review_prompt")]:
        if field in located:
            for value, group in located.groupby(field, dropna=True):
                if str(value).strip() and len(group) > 1:
                    detail = "|".join(group.site_id.astype(str))
                    for row in group.itertuples(index=False):
                        rows.append({"site_id": row.site_id, "ik": row.ik, "provider_name": row.provider_name,
                                     "city": row.city, "panel_a_group": row.panel_a_group,
                                     "flag_type": flag, "flag_detail": detail})
    for ik, group in located.groupby("ik"):
        if len(group) > 1:
            detail = "|".join(group.site_id.astype(str))
            for row in group.itertuples(index=False):
                rows.append({"site_id": row.site_id, "ik": row.ik, "provider_name": row.provider_name,
                             "city": row.city, "panel_a_group": row.panel_a_group,
                             "flag_type": "possible_multi_campus_review_prompt", "flag_detail": detail})
    return pd.DataFrame(rows, columns=["site_id", "ik", "provider_name", "city", "panel_a_group", "flag_type", "flag_detail"])


PANEL_D_SHORT_LABELS = {
    "260530103-772247000": "UK Bonn",
    "260510018-773410000": "UK Düsseldorf",
    "260930608-771402000": "UK Regensburg",
    "261101015-772563000": "Charité Berlin",
    "260200013-773675000": "UKE Hamburg",
    "260530443-771696000": "St. Vinzenz Köln",
    "260550131-772432000": "UK Münster",
    "260820466-771700000": "UK Heidelberg",
    "260832299-773657000": "UK Freiburg",
    "260810647-772121000": "Klinikum Ludwigsburg",
    "261600736-772874000": "UK Jena",
    "260102343-773448000": "UKSH Kiel",
    "260914050-771736000": "LMU München",
    "260812364-772783000": "Klinikum Stuttgart",
    "261401030-773444000": "UK Dresden",
    "260730161-771621000": "UM Mainz",
}


def marker_area(activity: pd.Series) -> pd.Series:
    """Locked B–D marker-area transform; floor only protects A113 values <13."""
    raw = 28 + 190 * (activity.astype(float) - 50) / 256
    return raw.clip(lower=1.0)


def label_offsets(points: pd.DataFrame) -> dict[str, tuple[int, int]]:
    """Deterministic displacements tailored to the locked 16-site network."""
    by_city = {
        "Kiel": (12, 7), "Hamburg": (-12, -13), "Münster": (10, 5),
        "Düsseldorf": (-18, 4), "Köln": (20, -2), "Bonn": (-10, -16),
        "Mainz": (12, -3), "Heidelberg": (-12, 8), "Ludwigsburg": (-10, 14),
        "Stuttgart": (12, -8), "Freiburg": (-8, -15), "Berlin": (-8, 5),
        "Dresden": (-10, 7), "Jena": (10, 5), "Regensburg": (10, 3),
        "München": (10, -11),
    }
    return {row.site_id: by_city.get(str(row.city), (6, 6)) for row in points.itertuples(index=False)}


def plot_panel(ax, germany, bounds, sites, title, *, unions=None, threshold=None,
               a193=False, label_all=False) -> None:
    germany.plot(ax=ax, color="#f7f7f4", edgecolor="#666666", linewidth=0.55, zorder=1)
    if threshold is not None:
        for minutes, colour, edge, alpha, z in [(60, "#9ecae1", "#6baed6", .42, 2), (30, "#3182bd", "#08519c", .47, 3)]:
            geom = unions.loc[(unions.threshold == threshold) & (unions.time_minutes == minutes), "geometry"].iloc[0]
            gpd.GeoSeries([geom], crs="EPSG:4326").plot(ax=ax, color=colour, edgecolor=edge, alpha=alpha, linewidth=.7, zorder=z)
    points = sites.dropna(subset=["latitude", "longitude"]).copy()
    if a193:
        for suppressed, colour, marker, label in [(False, "#8b0000", "o", "Openly numeric"), (True, "#4d4d4d", "^", "Suppressed-only")]:
            group = points.loc[points.suppressed_only.eq(suppressed)]
            ax.scatter(group.longitude, group.latitude, s=10, c=colour, marker=marker,
                       edgecolors="white", linewidths=.35, alpha=.82, zorder=4, label=label)
    else:
        ax.scatter(points.longitude, points.latitude, s=marker_area(points.visible_activity),
                   c="#8b0000", edgecolors="white", linewidths=.55, alpha=.88, zorder=4)
    if label_all:
        offsets = label_offsets(points)
        for row in points.itertuples(index=False):
            dx, dy = offsets[row.site_id]
            ax.annotate(row.displayed_short_label, (row.longitude, row.latitude), xytext=(dx, dy),
                        textcoords="offset points", fontsize=5.7, weight="semibold",
                        ha="left" if dx >= 0 else "right", va="bottom" if dy >= 0 else "top",
                        bbox=dict(boxstyle="round,pad=0.08", facecolor="white", edgecolor="none", alpha=.68),
                        arrowprops=dict(arrowstyle="-", color="#666666", lw=.35), zorder=5)
    ax.set_xlim(bounds[0] - .2, bounds[2] + .2)
    ax.set_ylim(bounds[1] - .15, bounds[3] + .15)
    ax.set_axis_off()
    ax.set_title(title, loc="left", fontsize=11.5, weight="bold")


def build_labels(master: pd.DataFrame) -> tuple[pd.DataFrame, Path]:
    labels = master.loc[master.threshold_ge100].copy().sort_values(["visible_activity", "site_id"], ascending=[False, True])
    if set(labels.site_id.astype(str)) != set(PANEL_D_SHORT_LABELS):
        raise RuntimeError("Panel D site identities do not match the validated short-label mapping")
    labels["displayed_short_label"] = labels.site_id.astype(str).map(PANEL_D_SHORT_LABELS)
    if len(labels) != 16 or labels.displayed_short_label.nunique() != 16 or labels.displayed_short_label.isna().any():
        raise RuntimeError("Panel D label mapping failed")
    path = GEO / "panel_D_ge100_label_mapping.csv"
    labels[["site_id", "provider_name", "city", "visible_activity", "displayed_short_label"]].to_csv(path, index=False)
    return labels, path


def build_figure4(candidate: pd.DataFrame, *, kind: str) -> list[Path]:
    master = pd.read_csv(MASTER, dtype={"ik": str, "site_id": str, "postcode": str})
    for col in ["suppressed_only", "threshold_ge20", "threshold_ge50", "threshold_ge100"]:
        master[col] = bool_col(master[col])
    master["visible_activity"] = pd.to_numeric(master.visible_activity, errors="coerce").fillna(0).astype(int)
    labels, label_path = build_labels(master)
    label_map = labels.set_index("site_id")["displayed_short_label"]
    master["displayed_short_label"] = master.site_id.map(label_map)
    unions = gpd.read_file(UNIONS).to_crs("EPSG:4326")
    germany, bounds = germany_bounds()
    located = candidate.copy()
    located["latitude"] = pd.to_numeric(located.latitude, errors="coerce")
    located["longitude"] = pd.to_numeric(located.longitude, errors="coerce")
    plotted_n = int(located[["latitude", "longitude"]].notna().all(axis=1).sum())
    expected = 113 if kind == "A113" else 193
    title_n = plotted_n
    fig, axes = plt.subplots(2, 2, figsize=(12.4, 10.6), sharex=True, sharey=True)
    plot_panel(axes[0,0], germany, bounds, located,
               f"A  {'Openly numeric sites' if kind == 'A113' else 'All identifiable active sites'} (n={title_n})",
               a193=(kind == "A193"))
    for ax, threshold, panel in [(axes[0,1],20,"B"), (axes[1,0],50,"C"), (axes[1,1],100,"D")]:
        selected = master.loc[master[f"threshold_ge{threshold}"]].copy()
        plot_panel(ax, germany, bounds, selected, f"{panel}  ≥{threshold} network (n={len(selected)})",
                   unions=unions, threshold=threshold, label_all=(threshold == 100))
    handles = [
        Patch(facecolor="#3182bd", edgecolor="#08519c", alpha=.47, label="30-minute drive time"),
        Patch(facecolor="#9ecae1", edgecolor="#6baed6", alpha=.42, label="60-minute drive time"),
        *[Line2D([], [], marker="o", linestyle="", color="#8b0000", markeredgecolor="white",
                markersize=math.sqrt(float(marker_area(pd.Series([v])).iloc[0])), label=f"{v} occurrences") for v in (20,100,300)],
    ]
    if kind == "A193":
        handles += [Line2D([],[],marker="o",linestyle="",color="#8b0000",markersize=5,label="Openly numeric (Panel A)"),
                    Line2D([],[],marker="^",linestyle="",color="#4d4d4d",markersize=5,label="Suppressed-only (Panel A)")]
    fig.legend(handles=handles, loc="lower center", ncol=4 if kind == "A193" else 5,
               frameon=True, bbox_to_anchor=(.5,.012), fontsize=8)
    warning = "PROVISIONAL LAYOUT PREVIEW – 53 PANEL-A SITES PENDING VALIDATION" if kind == "A113" else "PROVISIONAL LAYOUT PREVIEW – 133 PANEL-A SITES PENDING VALIDATION"
    fig.text(.5, .985, warning, ha="center", va="top", fontsize=9, color="#8b0000", weight="bold")
    fig.subplots_adjust(left=.02, right=.98, top=.955, bottom=.095, wspace=.02, hspace=.06)
    directory = A113 if kind == "A113" else A193
    stem = f"Figure4_{kind}_provisional_layout_preview"
    paths = save(fig, directory, stem)
    qa = pd.DataFrame([{"preview": kind, "candidate_sites": len(candidate), "plotted_sites": plotted_n,
                        "complete": plotted_n == expected, "panel_B_sites": 60, "panel_C_sites": 31,
                        "panel_D_sites": 16, "panel_D_labels": 16,
                        "isochrone_source": str(UNIONS.relative_to(ROOT)),
                        "accessibility_recalculated": False}])
    qa_path = QA / f"Figure4_{kind}_programmatic_QA.csv"
    qa.to_csv(qa_path, index=False)
    return paths + [qa_path, label_path]


def accessibility_check() -> Path:
    data = pd.read_csv(ACCESSIBILITY)
    row = data.loc[(data.threshold == 50) & (data.time_minutes == 30) & data.settlement_class.eq("rural")].iloc[0]
    calculated = 100 * int(row.covered_population) / int(row.class_population_denominator)
    result = pd.DataFrame([{
        "canonical_source": str(ACCESSIBILITY.relative_to(ROOT)), "source_sha256": sha256(ACCESSIBILITY),
        "threshold": 50, "time_minutes": 30, "settlement_class": "rural",
        "covered_population": int(row.covered_population), "class_population_denominator": int(row.class_population_denominator),
        "direct_percentage": calculated, "reported_source_percentage": float(row.pct_class_population_covered),
        "rounded_one_decimal_pct": round(calculated, 1),
        "pass_expected_inputs": int(row.covered_population) == 1702480 and int(row.class_population_denominator) == 22550346,
        "pass_reported_7_5_pct": round(calculated, 1) == 7.5,
        "routing_rerun": False, "population_overlay_rerun": False,
    }])
    ACCESS.mkdir(parents=True, exist_ok=True)
    path = ACCESS / "rural_ge50_30min_direct_verification.csv"
    result.to_csv(path, index=False)
    return path


def write_revision_documents(c113: pd.DataFrame, c193: pd.DataFrame, flags: pd.DataFrame) -> list[Path]:
    corrections_ids = ["260620431-773132000", "260550460-771191000", "260510939-771562000"]
    corrections = c193.loc[c193.site_id.isin(corrections_ids), [
        "site_id", "provider_name", "city", "original_address", "latitude", "longitude",
        "coordinate_status", "manual_status", "manual_address", "manual_latitude",
        "manual_longitude", "manual_source", "manual_notes",
    ]].copy()
    corrections["locked_source"] = str(MASTER.relative_to(ROOT))
    corrections_path = GEO / "known_three_manual_corrections_crosscheck.csv"
    corrections.to_csv(corrections_path, index=False)

    groups = []
    for group, label, total in [
        (c113.loc[c113.panel_a_group.eq("B_unvalidated_numeric_lt20")], "numeric_lt20", 53),
        (c193.loc[c193.panel_a_group.eq("C_unvalidated_suppressed_only")], "suppressed_only", 80),
    ]:
        has = group[["latitude", "longitude"]].notna().all(axis=1)
        group_flags = flags.loc[flags.site_id.isin(group.site_id)]
        groups.append({
            "group": label, "total_sites": total,
            "coordinates_already_in_canonical_source": int(has.sum()) if label == "numeric_lt20" else 0,
            "coordinates_reused_from_other_project_asset": 0,
            "automatically_preview_geocoded": 0 if label == "numeric_lt20" else int(has.sum()),
            "still_unplottable": int((~has).sum()),
            "low_precision_or_administrative_flag_rows": int(group_flags.flag_type.eq("possible_low_precision_or_administrative_coordinate").sum()),
            "duplicate_coordinate_flag_rows": int(group_flags.flag_type.eq("duplicate_coordinate_review_prompt").sum()),
            "outside_germany_polygon_flag_rows": int(group_flags.flag_type.eq("outside_germany_polygon").sum()),
            "all_additional_coordinates_manually_validated": False,
        })
    coordinate_summary_path = GEO / "coordinate_availability_summary.csv"
    pd.DataFrame(groups).to_csv(coordinate_summary_path, index=False)

    f3_text = """# Figure 3 candidate captions and comparison

## Candidate A: numeric-only

Openly numeric physical sites by mutually exclusive visible-activity category in 2008, 2010 and 2012–2024. Categories show 4–19, 20–49, 50–99, 100–199 and ≥200 visible procedure occurrences. Suppressed-only sites are not included. Reporting years 2009 and 2011 are unavailable.

## Candidate B: identifiable network including suppressed-only sites

Identifiable active physical sites in 2008, 2010 and 2012–2024. The five blue segments are mutually exclusive visible-activity categories. The grey `Suppressed-only` segment is a reporting-status category, not a volume category. Exact total site-level activity is unavailable for suppressed-only sites, so they cannot be assigned to a numeric activity category. Total bar height represents all identifiable active physical sites. Reporting years 2009 and 2011 are unavailable.

## Scientific comparison

Candidate A answers the volume-distribution question most directly and retains the clearest category comparison. Candidate B additionally shows the full identifiable provider footprint and makes suppression-related uncertainty visible, but the grey segment is visually dominant in early years and combines a reporting-status category with numeric volume categories. Candidate B therefore adds network-completeness information but is conceptually less homogeneous and partly overlaps information in Figure 1B and Table S3. No final candidate is selected here.
"""
    f3_path = F3 / "Figure3_candidate_captions_and_comparison.md"
    f3_path.write_text(f3_text, encoding="utf-8")

    f4_text = """# Provisional Figure 4 captions and comparison

## A113 preview caption

Provisional 2024 geographic layout preview. Panel A shows all 113 openly numeric physical sites; marker area represents visible site-level activity. Panels B–D show the cumulative ≥20, ≥50 and ≥100 networks with 60, 31 and 16 validated sites. Dark and light blue areas show the established 30- and 60-minute driving-time isochrones in Panels B–D only. All 16 ≥100 sites are labelled in Panel D. No geographic accessibility estimate was calculated for Panel A. Coordinates for 53 Panel-A sites below 20 remain pending manual validation.

## A193 preview caption

Provisional 2024 geographic layout preview. Panel A shows all 193 identifiable active physical sites, including 113 openly numeric sites shown as red circles and 80 suppressed-only sites shown as grey triangles, using equal marker area. Suppressed-only status concerns code-specific reporting and does not define exact total site activity; Panel-A marker size therefore does not represent procedural activity. Panels B–D show the cumulative ≥20, ≥50 and ≥100 networks with 60, 31 and 16 validated sites. Dark and light blue areas show the established 30- and 60-minute driving-time isochrones in Panels B–D only. All 16 ≥100 sites are labelled in Panel D. No geographic accessibility estimate was calculated for Panel A. Coordinates for 133 Panel-A sites remain pending manual validation, including 80 automatic preview geocodes.

## Scientific and visual comparison

A113 corresponds directly to the openly numeric analysis and supports quantitative marker-area encoding, but omits 80 geographically identifiable suppressed-only sites. A193 provides the complete identifiable footprint and the clearest all-identifiable → ≥20 → ≥50 → ≥100 progression, but Panel A is more crowded and cannot encode exact activity for suppressed-only sites. The full-address automatic coordinates are adequate for a broad layout comparison, not for scientific release; duplicate-coordinate and administrative-coordinate review prompts show that the detailed crowding pattern remains sensitive to later validation. No final preview is selected here.
"""
    f4_path = OUT / "Figure4_preview_captions_and_comparison.md"
    f4_path.write_text(f4_text, encoding="utf-8")
    return [corrections_path, coordinate_summary_path, f3_path, f4_path]


def write_final_report(c113: pd.DataFrame, c193: pd.DataFrame, flags: pd.DataFrame) -> Path:
    def item(path: Path) -> str:
        return f"`{path.relative_to(ROOT)}` — SHA-256 `{sha256(path)}`"

    f3b = pd.read_csv(F3 / "Figure3_candidate_B_identifiable_network_data.csv")
    identifiable = ", ".join(f"{int(r.reporting_year)}={int(r.identifiable_active_physical_sites)}" for r in f3b.itertuples())
    suppressed = ", ".join(f"{int(r.reporting_year)}={int(r.suppressed_only_sites)}" for r in f3b.itertuples())
    ftypes = flags.flag_type.value_counts()
    duplicate_clusters = flags.loc[flags.flag_type.eq("duplicate_coordinate_review_prompt"), "flag_detail"].nunique()
    multicampus_clusters = flags.loc[flags.flag_type.eq("possible_multi_campus_review_prompt"), "flag_detail"].nunique()
    report = f"""# Late-stage TIPS revision report, 14 August 2026

## A. Source reconciliation

- Canonical inclusive source: {item(METRICS)}. Figure 3B filter: `provider_definition = physical_site`, `suppression_scenario = visible`, reporting years 2008, 2010 and 2012–2024.
- Locked Figure 3 data: {item(LOCKED_F3_DATA)}.
- Locked Figure 3 PNG: {item(LOCKED_F3_DIR / 'Figure3_longitudinal_exclusive_categories.png')}.
- Locked Figure 3 PDF: {item(LOCKED_F3_DIR / 'Figure3_longitudinal_exclusive_categories.pdf')}.
- Canonical 193-site source: {item(MASTER)}.
- Existing 113-site geocoded source: {item(NUMERIC_GEOCODED)}.
- Locked completed 60-site manual review: {item(VALIDATED_60)}.
- Existing per-site isochrones: {item(ROOT / 'outputs/final_submission_assets_2026-07-24/geography/accessibility_site_isochrones.geojson')}.
- Existing 30-/60-minute union geometries: {item(UNIONS)}.
- Current plotting workflow: {item(ROOT / 'scripts/run_tips_ge50_ge100_accessibility.py')}.
- Map bases: {item(config.GERMANY_OUTLINE)}; {item(ROOT / 'spatial/germany-states.geojson')}. Plot CRS is EPSG:4326.
- Canonical accessibility source: {item(ACCESSIBILITY)}.
- The existing workflow used direct `annotate` calls rather than a reusable label-placement utility. This preview adds deterministic, reviewable offsets for the locked 16-site Panel D only.
- No source-integrity discrepancy was found. The three known corrections are preserved in {item(GEO / 'known_three_manual_corrections_crosscheck.csv')}.

## B. Figure 3 Candidate A

- PNG: {item(F3 / 'Figure3_candidate_A_numeric_only.png')}.
- PDF: {item(F3 / 'Figure3_candidate_A_numeric_only.pdf')}.
- Legend title is `Visible procedure occurrences`; y-axis is `Openly numeric physical sites, n`.
- 2024 stack is exactly 53, 29, 15, 10 and 6, totalling 113; 2008 totals 28.
- Programmatic QA: all 9 checks passed in {item(QA / 'Figure3_candidates_programmatic_QA.csv')}.
- Visual QA: PNG and rendered PDF are readable at manuscript size, balanced and unclipped. The five-category distribution remains visually direct.
- Caption: Openly numeric physical sites by mutually exclusive visible-activity category in 2008, 2010 and 2012–2024. Categories show 4–19, 20–49, 50–99, 100–199 and ≥200 visible procedure occurrences. Suppressed-only sites are not included. Reporting years 2009 and 2011 are unavailable.

## C. Figure 3 Candidate B

- Data: {item(F3 / 'Figure3_candidate_B_identifiable_network_data.csv')}.
- PNG: {item(F3 / 'Figure3_candidate_B_identifiable_network.png')}.
- PDF: {item(F3 / 'Figure3_candidate_B_identifiable_network.pdf')}.
- Identifiable-active series: {identifiable}.
- Suppressed-only series: {suppressed}.
- The physical-site/visible series was used; the five locked numeric series were not altered.
- Y-axis is `Identifiable active physical sites, n`; the six-item legend has no title.
- Programmatic QA: all 9 checks passed. Visual QA: the neutral grey segment is distinguishable and does not obscure the blue stacks, but it dominates early bars and makes the conceptual mixture of volume and reporting status salient. No clipping was found.
- Caption: Identifiable active physical sites in 2008, 2010 and 2012–2024. The five blue segments are mutually exclusive visible-activity categories. The grey `Suppressed-only` segment is a reporting-status category, not a volume category. Exact total site-level activity is unavailable for suppressed-only sites, so they cannot be assigned to a numeric activity category. Total bar height represents all identifiable active physical sites. Reporting years 2009 and 2011 are unavailable.

## D. Figure 3 comparison

Candidate A answers the volume-distribution question more cleanly. Candidate B adds full identifiable-network information and makes suppression visible, but combines unlike category types and partly overlaps Figure 1B/Table S3. The grey series does not prevent reading the numeric stacks, although it materially changes visual emphasis. No final version is selected.

## E. 2024 provider-set reconciliation

All identifiers are unique within the canonical physical-site set. The independently reproduced counts are 193 identifiable active = 113 openly numeric + 80 suppressed-only; 113 openly numeric = 60 ≥20 + 53 <20; 193 − 60 = 133 = 53 + 80. Numeric and suppressed-only sets are disjoint.

## F. Coordinate availability

- Numeric <20: total 53; already present in the canonical 113-site project output 53; reused from another asset 0; new automatic preview geocodes 0; unplottable 0; low-precision/administrative-coordinate prompts 33. Five rows belong to one duplicate-coordinate cluster.
- Suppressed-only: total 80; already present 0; reused from another asset 0; new automatic full-address preview geocodes 80; unplottable 0; generic low-precision flags 0. Two rows form one duplicate-coordinate cluster. All 80 are nevertheless unvalidated.

## G. Geographic preflight

- Candidate 113: {item(GEO / 'candidate_113_panel_A_sites.csv')}.
- Candidate 193: {item(GEO / 'candidate_193_panel_A_sites.csv')}.
- Review flags: {item(GEO / 'automated_geographic_review_flags.csv')}.
- Availability summary: {item(GEO / 'coordinate_availability_summary.csv')}.
- Flag counts are review prompts, not confirmed errors: duplicate coordinate {int(ftypes.get('duplicate_coordinate_review_prompt', 0))} rows/{duplicate_clusters} clusters; address duplication 0; outside detailed Germany polygon {int(ftypes.get('outside_germany_polygon', 0))} row (locked validated Passau border coordinate); state-coordinate inconsistency 0; possible low-precision/administrative coordinate {int(ftypes.get('possible_low_precision_or_administrative_coordinate', 0))} rows; possible same-campus prompts overlap the two duplicate-coordinate clusters; possible multi-campus {int(ftypes.get('possible_multi_campus_review_prompt', 0))} rows/{multicampus_clusters} institution groups. No automatic merge was made.
- No full manual official-source validation was performed.

## H. Figure 4 A113 preview

- PNG: {item(A113 / 'Figure4_A113_provisional_layout_preview.png')}.
- PDF: {item(A113 / 'Figure4_A113_provisional_layout_preview.pdf')}.
- Plotted n=113. Panel A uses the established area transform `s = 28 + 190 × (activity − 50) / 256` points². Since this transform is negative for the newly included smallest values, a technical floor of 1 point² was applied to 38 sites with 4–13 occurrences; this floor is explicit and does not affect Panels B–D.
- Panels B–D use the exact established transform without clipping because all activities are ≥20. Marker semantics are otherwise the same: area represents visible activity.
- QA: {item(QA / 'Figure4_A113_programmatic_QA.csv')}. The broad pattern is readable and unclipped. Very small Panel-A markers appropriately remain visually subordinate, but the detailed pattern depends on 53 unvalidated coordinates.
- Caption is stored in {item(OUT / 'Figure4_preview_captions_and_comparison.md')}.

## I. Figure 4 A193 preview

- PNG: {item(A193 / 'Figure4_A193_provisional_layout_preview.png')}.
- PDF: {item(A193 / 'Figure4_A193_provisional_layout_preview.pdf')}.
- All 193 sites are plotted. Panel A uses equal 10-point² markers: red circles for 113 openly numeric sites and grey triangles for 80 suppressed-only sites. Marker size does not encode activity.
- QA: {item(QA / 'Figure4_A193_programmatic_QA.csv')}. The categorical distinction remains readable, so no alternate identical-symbol render was needed. Crowding is greater in metropolitan clusters and depends materially on 80 automatic, unvalidated coordinates.
- Caption is stored in {item(OUT / 'Figure4_preview_captions_and_comparison.md')}.

## J. Panel D labels

- Mapping: {item(GEO / 'panel_D_ge100_label_mapping.csv')}.
- Network sites=16, intended labels=16, successful unique labels=16. All marker-label associations were built from stable site identifiers. Deterministic displacement, leader lines and rendered PNG/PDF inspection found no omitted label, severe overlap or clipping.

## K. A113 versus A193

A113 preserves correspondence with the quantitative openly numeric analysis and supports activity-scaled markers, but loses the footprint of 80 suppressed-only sites. A193 shows the full identifiable progression to the ≥20/≥50/≥100 panels, but is more crowded and cannot represent Panel-A activity. The full-address preview geocodes are adequate for judging broad layout density, not fine campus placement or scientific release. The unresolved design choice is whether quantitative comparability or maximum identifiable geographic completeness should dominate Panel A; no selection is made.

## L. Rural ≥50 verification

- Source: {item(ACCESSIBILITY)}.
- Numerator 1,702,480; rural denominator 22,550,346; direct calculation 7.549684603508966%; rounded display 7.5%; PASS.
- Machine-readable check: {item(ACCESS / 'rural_ge50_30min_direct_verification.csv')}. Routing, isochrones and population overlays were not rerun.

## M. Consequential manuscript issues

If the later release validation expands beyond 60 sites, surgical wording review will be needed for statements mirrored in `outputs/final_submission_assets_2026-07-24/FINAL_OUTPUT_README.md`, `figure_captions.md`, `table_titles_and_footnotes.md`, `geography/federal_state_validation_report.md` and `tables/TableS4_validated_federal_state_distribution.md`: these currently describe only 60 ≥20 sites as validated, place the 53 <20 sites outside release scope, or withhold the full 113-site state distribution for that reason. No Word file was edited.

## N. Integrity statement

No Word file was modified. No canonical production output was overwritten. No Git history, branch or remote was modified. No new accessibility analysis was performed. No ≥20/≥50/≥100 isochrone was recalculated. No population coverage analysis was rerun. No full manual site-by-site geographic validation was performed. The 80 new coordinates are preview-only and remain unvalidated. Both Figure 4 products are provisional layout previews only.
"""
    path = OUT / "late_stage_revision_report.md"
    path.write_text(report, encoding="utf-8")
    return path


def source_inventory(paths: list[Path]) -> Path:
    sources = [METRICS, LOCKED_F3_DATA, LOCKED_F3_DIR / "Figure3_longitudinal_exclusive_categories.png",
               LOCKED_F3_DIR / "Figure3_longitudinal_exclusive_categories.pdf", MASTER, NUMERIC_GEOCODED,
               VALIDATED_60, UNIONS, ROOT / "outputs/final_submission_assets_2026-07-24/geography/accessibility_site_isochrones.geojson",
               ACCESSIBILITY, ROOT / "outputs/final_submission_assets_2026-07-24/geography/tables/TableS5_potential_geographic_accessibility.csv",
               ROOT / "spatial/germany-states.geojson", config.GERMANY_OUTLINE,
               ROOT / "scripts/run_tips_ge50_ge100_accessibility.py",
               ROOT / "scripts/build_late_stage_revision_2026_08_14.py",
               ROOT / "outputs/final_submission_assets_2026-07-24/geography/geographic_validation_report.md",
               ROOT / "outputs/final_submission_assets_2026-07-24/geography/coordinate_audit_report.md",
               ROOT / "outputs/final_submission_assets_2026-07-24/geography/provider_set_validation.md"]
    rows = [{"path": str(p.relative_to(ROOT)), "size_bytes": p.stat().st_size, "sha256": sha256(p)} for p in sources]
    path = QA / "canonical_source_inventory.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    manifest = OUT / "revision_output_manifest.json"
    outputs = [p for p in paths if p.exists()]
    manifest.write_text(json.dumps({"outputs": [{"path": str(p.relative_to(ROOT)), "size_bytes": p.stat().st_size,
                                                  "sha256": sha256(p)} for p in sorted(set(outputs))]}, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--geocode-missing", action="store_true")
    args = parser.parse_args()
    for directory in [F3, GEO, A113, A193, ACCESS, QA]:
        directory.mkdir(parents=True, exist_ok=True)
    set_style()
    outputs = build_figure3()
    c113, c193, geo_paths = prepare_geography(args.geocode_missing)
    outputs.extend([p for p in geo_paths if p.exists()])
    flags = coordinate_flags(c193)
    flags_path = GEO / "automated_geographic_review_flags.csv"
    flags.to_csv(flags_path, index=False)
    outputs.append(flags_path)
    outputs += build_figure4(c113, kind="A113")
    outputs += build_figure4(c193, kind="A193")
    outputs.append(accessibility_check())
    outputs.extend(write_revision_documents(c113, c193, flags))
    outputs.append(write_final_report(c113, c193, flags))
    outputs.append(ROOT / "scripts/build_late_stage_revision_2026_08_14.py")
    inventory = source_inventory(outputs)
    outputs.append(inventory)
    source_inventory(outputs)
    print(f"Built {len(set(outputs))} revision outputs under {OUT}")


if __name__ == "__main__":
    main()
