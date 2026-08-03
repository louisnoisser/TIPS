"""Reusable indication-level reporting for one OPS code family."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config
from .geocoding import geocode_dataframe
from .gba_xml import discover_year_dirs
from .isochrones import export_isochrones, generate_isochrone_cache
from .longitudinal import run_longitudinal_pipeline
from .ops_icd import (
    build_ops_target_summary,
    extract_hospital_code_totals,
    parse_target_specs,
    slugify_label,
    target_case_column,
    target_codes_column,
)
from .urban_rural import classify_points, summarize_union_coverage

DEFAULT_BASE_THRESHOLD = 1
DEFAULT_THRESHOLDS = [20, 50, 100, 200]
DEFAULT_MAIN_THRESHOLD = 50
DEFAULT_STRICT_THRESHOLD = 100
STATE_NEAREST_FALLBACK_MAX_DISTANCE_M = 1_000
STATE_NEAREST_FALLBACK_CRS = "EPSG:25832"


def slugify_text(text: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in text.strip())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def _infer_center_type_suffix(hospital_name: str) -> str:
    name = " ".join(str(hospital_name).strip().lower().split())
    if not name or name == "nan":
        return ""

    uh_markers = [
        "university hospital",
        "universitätsklinikum",
        "universitaetsklinikum",
        "universitätsmedizin",
        "universitaetsmedizin",
        "uniklinik",
        "unimedizin",
        "charité",
        "charite",
        " lmu ",
        " uke ",
    ]
    if any(marker in f" {name} " for marker in uh_markers):
        return "UH"

    ch_markers = [
        "klinikum",
        "krankenhaus",
        "hospital",
        "städt",
        "staedt",
        "kommunal",
        "kreisklinik",
    ]
    if any(marker in name for marker in ch_markers):
        return "CH"
    return ""


def _short_center_label(row: pd.Series) -> str:
    city = str(row.get("city", "")).strip()
    if not city or city.lower() == "nan":
        city = str(row.get("hospital_name", "")).strip()
    if not city:
        city = "Unknown"
    suffix = _infer_center_type_suffix(str(row.get("hospital_name", "")))
    return f"{city} ({suffix})" if suffix else city


def latest_year_dir(base_dir: Path) -> Path:
    year_dirs = discover_year_dirs(base_dir)
    if not year_dirs:
        raise FileNotFoundError(f"No xml_<year> directories found under {base_dir}")
    return year_dirs[-1]


def ensure_report_dirs(report_dir: Path) -> dict[str, Path]:
    paths = {
        "root": report_dir,
        "tables": report_dir / "tables",
        "figures": report_dir / "figures",
        "geo": report_dir / "geo",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _read_states() -> tuple[gpd.GeoDataFrame, str]:
    states = gpd.read_file(config.GERMANY_STATES).to_crs("EPSG:4326")
    for column in ("NAME_1", "lan_name", "name", "NAME"):
        if column in states.columns:
            return states, column
    raise KeyError("No state name column found in state GeoJSON")


def _read_outline() -> gpd.GeoDataFrame:
    return gpd.read_file(config.GERMANY_OUTLINE).to_crs("EPSG:4326")


def _make_point_gdf(df: pd.DataFrame) -> gpd.GeoDataFrame:
    work = df.dropna(subset=["longitude", "latitude"]).copy()
    return gpd.GeoDataFrame(
        work,
        geometry=gpd.points_from_xy(work["longitude"], work["latitude"]),
        crs="EPSG:4326",
    )


def threshold_summary_latest_year(latest_any: pd.DataFrame, case_col: str, thresholds: list[int]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    total_cases = float(latest_any[case_col].sum())
    total_hospitals = int(len(latest_any))
    for threshold in thresholds:
        subset = latest_any.loc[latest_any[case_col] >= threshold].copy()
        rows.append(
            {
                "threshold": threshold,
                "hospitals": int(len(subset)),
                "pct_of_hospitals_any": round(100 * len(subset) / total_hospitals, 2) if total_hospitals else 0.0,
                "cases_in_threshold": int(subset[case_col].sum()),
                "pct_of_cases_total": round(100 * subset[case_col].sum() / total_cases, 2) if total_cases else 0.0,
                "median_cases": float(subset[case_col].median()) if not subset.empty else 0.0,
                "max_cases": int(subset[case_col].max()) if not subset.empty else 0,
            }
        )
    return pd.DataFrame(rows)


def matched_subcodes_table(latest_any: pd.DataFrame, codes_col: str) -> pd.DataFrame:
    counts: dict[str, int] = {}
    for value in latest_any[codes_col].fillna(""):
        for code in [token.strip() for token in str(value).split("|") if token.strip()]:
            counts[code] = counts.get(code, 0) + 1
    rows = [{"matched_subcode": code, "hospitals_with_subcode": count} for code, count in counts.items()]
    return pd.DataFrame(rows).sort_values(["hospitals_with_subcode", "matched_subcode"], ascending=[False, True]).reset_index(drop=True)


def enrich_with_state_and_urbanity(geocoded_all: pd.DataFrame, case_col: str) -> pd.DataFrame:
    point_gdf = classify_points(geocoded_all)
    states, state_col = _read_states()
    joined = gpd.sjoin(
        point_gdf,
        states[[state_col, "geometry"]],
        how="left",
        predicate="within",
    ).drop(columns=["index_right"], errors="ignore")

    # Keep the exact point-in-state join as primary logic. Some valid hospitals
    # geocode a few meters outside the state boundary; only repair those if the
    # nearest state polygon is within a strict 1 km tolerance.
    unknown_mask = joined[state_col].isna() & joined.geometry.notna()
    if unknown_mask.any():
        states_metric = states[[state_col, "geometry"]].to_crs(STATE_NEAREST_FALLBACK_CRS)
        unknown_metric = gpd.GeoDataFrame(
            joined.loc[unknown_mask, ["geometry"]].copy(),
            geometry="geometry",
            crs=joined.crs,
        ).to_crs(STATE_NEAREST_FALLBACK_CRS)
        for index, row in unknown_metric.iterrows():
            distances = states_metric.geometry.distance(row.geometry)
            nearest_index = distances.idxmin()
            nearest_distance = float(distances.loc[nearest_index])
            if nearest_distance <= STATE_NEAREST_FALLBACK_MAX_DISTANCE_M:
                joined.loc[index, state_col] = states_metric.loc[nearest_index, state_col]

    joined = joined.rename(columns={state_col: "state_name"})
    joined["state_name"] = joined["state_name"].fillna("Unknown")
    result = pd.DataFrame(joined.drop(columns="geometry"))
    result[case_col] = pd.to_numeric(result[case_col], errors="coerce").fillna(0).astype(int)
    return result


def state_summary_table(enriched: pd.DataFrame, case_col: str, thresholds: list[int]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        subset = enriched.loc[enriched[case_col] >= threshold].copy()
        grouped = (
            subset.groupby("state_name", dropna=False)
            .agg(hospitals=("facility_id", "nunique"), total_cases=(case_col, "sum"), median_cases=(case_col, "median"))
            .reset_index()
        )
        grouped["threshold"] = threshold
        rows.append(grouped)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True).sort_values(["threshold", "total_cases"], ascending=[True, False]).reset_index(drop=True)


def urban_summary_table(enriched: pd.DataFrame, case_col: str, thresholds: list[int]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        subset = enriched.loc[enriched[case_col] >= threshold].copy()
        grouped = (
            subset.groupby("urban_rural", dropna=False)
            .agg(hospitals=("facility_id", "nunique"), total_cases=(case_col, "sum"), median_cases=(case_col, "median"))
            .reset_index()
        )
        grouped["threshold"] = threshold
        rows.append(grouped)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True).sort_values(["threshold", "total_cases"], ascending=[True, False]).reset_index(drop=True)


def yearly_threshold_sensitivity(hospital_year: pd.DataFrame, case_col: str, thresholds: list[int]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for year, group in hospital_year.groupby("year", dropna=False):
        total_cases = float(group[case_col].sum())
        for threshold in thresholds:
            subset = group.loc[group[case_col] >= threshold]
            rows.append(
                {
                    "year": int(year),
                    "threshold": threshold,
                    "hospitals": int(len(subset)),
                    "cases_in_threshold": int(subset[case_col].sum()),
                    "pct_of_year_cases": round(100 * subset[case_col].sum() / total_cases, 2) if total_cases else 0.0,
                }
            )
    return pd.DataFrame(rows).sort_values(["year", "threshold"]).reset_index(drop=True)


def top_centers_all_years(hospital_year: pd.DataFrame, case_col: str) -> pd.DataFrame:
    grouped = (
        hospital_year.groupby(["facility_id", "ik", "standortnummer", "hospital_name", "city"], dropna=False)
        .agg(
            total_cases=(case_col, "sum"),
            years_active=("year", "nunique"),
            first_year=("year", "min"),
            last_year=("year", "max"),
            max_single_year_cases=(case_col, "max"),
        )
        .reset_index()
        .sort_values(["total_cases", "years_active"], ascending=[False, False])
        .reset_index(drop=True)
    )
    return grouped


def plot_yearly_trends(
    yearly_summary: pd.DataFrame,
    threshold_sensitivity: pd.DataFrame,
    case_slug: str,
    indication_name: str,
    output_path: Path,
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(12, 10), constrained_layout=True)
    years = yearly_summary["year"]
    axes[0].plot(years, yearly_summary[f"{case_slug}_cases_total"], marker="o", linewidth=2.5, color="#134074")
    axes[0].set_title(f"Annual {indication_name} procedure volume")
    axes[0].set_ylabel("Cases")
    axes[0].grid(alpha=0.3)

    thresholds = sorted(int(value) for value in threshold_sensitivity["threshold"].dropna().unique())
    # Keep the trend panel readable with many thresholds.
    display_thresholds = thresholds if len(thresholds) <= 5 else [threshold for threshold in thresholds if threshold != min(thresholds)]
    cmap = plt.cm.get_cmap("viridis", max(len(display_thresholds), 2))
    for index, threshold in enumerate(display_thresholds):
        color = cmap(index / max(len(display_thresholds) - 1, 1))
        subset = threshold_sensitivity.loc[threshold_sensitivity["threshold"] == threshold]
        axes[1].plot(subset["year"], subset["hospitals"], marker="o", linewidth=2, label=f">= {threshold} cases", color=color)
    axes[1].set_title(f"Annual {indication_name} center counts by selected thresholds")
    axes[1].set_ylabel("Centers")
    axes[1].set_xlabel("Year")
    axes[1].grid(alpha=0.3)
    axes[1].legend(frameon=False)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_threshold_counts(threshold_summary: pd.DataFrame, indication_name: str, latest_year: int, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    plot_df = (
        threshold_summary.loc[pd.to_numeric(threshold_summary["threshold"], errors="coerce") >= 10]
        .sort_values("threshold")
        .reset_index(drop=True)
    )
    ax.bar(plot_df["threshold"].astype(str), plot_df["hospitals"], color="#134074")
    ax.set_title(f"{latest_year} {indication_name} centers by threshold")
    ax.set_xlabel("Minimum annual cases per center")
    ax.set_ylabel("Centers")
    for _, row in plot_df.iterrows():
        ax.text(str(row["threshold"]), row["hospitals"] + 1, str(int(row["hospitals"])), ha="center", va="bottom", fontsize=9)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_top_centers(top_centers: pd.DataFrame, case_col: str, indication_name: str, latest_year: int, output_path: Path, n: int = 15) -> None:
    subset = top_centers.head(n).copy()
    subset["display_label"] = subset.apply(_short_center_label, axis=1)
    label_counts: dict[str, int] = {}
    display_labels: list[str] = []
    for label in subset["display_label"]:
        label_counts[label] = label_counts.get(label, 0) + 1
        suffix = f" #{label_counts[label]}" if label_counts[label] > 1 else ""
        display_labels.append(f"{label}{suffix}")
    subset["display_label_plot"] = display_labels
    subset = subset.sort_values(case_col, ascending=True)
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.barh(subset["display_label_plot"], subset[case_col], color="#0b6e4f")
    ax.set_title(f"Top {len(subset)} {latest_year} {indication_name} centers")
    ax.set_xlabel("Cases")
    ax.grid(alpha=0.2, axis="x")
    plt.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_case_distribution(latest_any: pd.DataFrame, case_col: str, indication_name: str, latest_year: int, output_path: Path) -> None:
    values = latest_any[case_col].astype(float)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    axes[0].hist(values, bins=20, color="#134074", edgecolor="white")
    axes[0].set_title(f"{latest_year} case distribution")
    axes[0].set_xlabel("Cases per hospital")
    axes[0].set_ylabel("Hospitals")

    sorted_values = np.sort(values.values)
    cumulative_cases = np.cumsum(sorted_values) / sorted_values.sum()
    cumulative_hospitals = np.arange(1, len(sorted_values) + 1) / len(sorted_values)
    axes[1].plot(cumulative_hospitals, cumulative_cases, color="#c1121f", linewidth=2)
    axes[1].plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=1)
    axes[1].set_title("Center concentration (Lorenz-style curve)")
    axes[1].set_xlabel("Cumulative share of hospitals")
    axes[1].set_ylabel("Cumulative share of cases")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_state_summary(state_summary: pd.DataFrame, indication_name: str, latest_year: int, output_path: Path, threshold: int) -> None:
    subset = state_summary.loc[state_summary["threshold"] == threshold].head(15).sort_values("total_cases", ascending=True)
    fig, ax = plt.subplots(figsize=(12, 8), constrained_layout=True)
    ax.barh(subset["state_name"], subset["total_cases"], color="#f9844a")
    ax.set_title(f"{latest_year} {indication_name} cases by state (>= {threshold} cases per center)")
    ax.set_xlabel("Cases")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_urban_summary(urban_summary: pd.DataFrame, indication_name: str, latest_year: int, output_path: Path) -> None:
    pivot = urban_summary.pivot_table(index="threshold", columns="urban_rural", values="hospitals", fill_value=0).reset_index()
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    x = np.arange(len(pivot))
    width = 0.25
    categories = [c for c in ["urban", "rural", "other"] if c in pivot.columns]
    for idx, category in enumerate(categories):
        ax.bar(x + (idx - (len(categories) - 1) / 2) * width, pivot[category], width=width, label=category)
    ax.set_xticks(x)
    ax.set_xticklabels(pivot["threshold"].astype(str))
    ax.set_xlabel("Minimum annual cases per center")
    ax.set_ylabel("Hospitals")
    ax.set_title(f"{latest_year} {indication_name} center urban-rural mix by threshold")
    ax.legend(frameon=False)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_centers_map(
    enriched: pd.DataFrame,
    case_col: str,
    indication_name: str,
    latest_year: int,
    output_path: Path,
    threshold: int,
) -> None:
    subset = enriched.loc[enriched[case_col] >= threshold].copy()
    gdf = _make_point_gdf(subset)
    outline = _read_outline()
    fig, ax = plt.subplots(figsize=(10, 12), constrained_layout=True)
    outline.plot(ax=ax, color="#f5f5f5", edgecolor="#7f7f7f", linewidth=0.8)
    if not gdf.empty:
        sizes = np.clip(np.sqrt(pd.to_numeric(gdf[case_col], errors="coerce").fillna(0.0)) * 16, 16, 220)
        urbanity_share = gdf["urban_rural"].value_counts(normalize=True, dropna=False)
        dominant_share = float(urbanity_share.iloc[0]) if not urbanity_share.empty else 1.0
        if dominant_share >= 0.85:
            gdf.plot(
                ax=ax,
                markersize=sizes,
                color="#0b6e4f",
                alpha=0.75,
                edgecolor="white",
                linewidth=0.3,
            )
        else:
            colors = {"urban": "#c1121f", "rural": "#1d4e89", "other": "#6c757d"}
            for category, frame in gdf.groupby("urban_rural", dropna=False):
                frame.plot(
                    ax=ax,
                    markersize=sizes.loc[frame.index],
                    color=colors.get(str(category), "#6c757d"),
                    alpha=0.75,
                    edgecolor="white",
                    linewidth=0.35,
                    label=str(category),
                )
            ax.legend(frameon=False, title="Urbanity", loc="lower left")
    ax.set_axis_off()
    ax.set_title(f"{latest_year} {indication_name} centers in Germany (>= {threshold} cases)")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_isochrone_map(
    union_geojson: Path,
    centers_csv: Path,
    case_col: str,
    indication_name: str,
    latest_year: int,
    output_path: Path,
    threshold: int,
) -> None:
    union_gdf = gpd.read_file(union_geojson).to_crs("EPSG:4326")
    centers_df = pd.read_csv(centers_csv)
    centers_gdf = _make_point_gdf(centers_df)
    outline = _read_outline()
    fig, ax = plt.subplots(figsize=(10, 12), constrained_layout=True)
    outline.plot(ax=ax, color="#f5f5f5", edgecolor="#7f7f7f", linewidth=0.8)
    palette = ["#d7eef8", "#a9d6e5", "#74b9d6", "#4096c7", "#1f6992"]
    for idx, (_, row) in enumerate(union_gdf.sort_values("time_minutes", ascending=False).iterrows()):
        gpd.GeoSeries([row.geometry], crs="EPSG:4326").plot(
            ax=ax,
            color=palette[min(idx, len(palette) - 1)],
            alpha=0.25,
            edgecolor="#355070",
            linewidth=0.5,
            label=f"{int(row['time_minutes'])} min",
        )
    if not centers_gdf.empty:
        centers_gdf.plot(
            ax=ax,
            color="#b23a48",
            markersize=np.clip(np.sqrt(pd.to_numeric(centers_gdf[case_col], errors="coerce").fillna(0.0)) * 14, 18, 180),
            edgecolor="white",
            linewidth=0.35,
        )
    handles, labels = ax.get_legend_handles_labels()
    dedup: dict[str, Any] = {}
    for handle, label in zip(handles, labels, strict=False):
        dedup.setdefault(label, handle)
    ax.legend(dedup.values(), dedup.keys(), frameon=False, title="Travel time")
    ax.set_axis_off()
    ax.set_title(f"{latest_year} {indication_name} access isochrones (>= {threshold} cases)")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_coverage_summary(coverage_df: pd.DataFrame, indication_name: str, output_path: Path, threshold: int) -> None:
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    for category, subset in coverage_df.groupby("urban_rural", dropna=False):
        ax.plot(subset["time_minutes"], subset["pct_of_class_covered"], marker="o", linewidth=2, label=str(category))
    ax.set_title(f"{indication_name} isochrone coverage by urbanity (>= {threshold} cases)")
    ax.set_xlabel("Travel time (minutes)")
    ax.set_ylabel("Percent of class covered")
    ax.grid(alpha=0.3)
    ax.legend(frameon=False)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def summary_payload(
    *,
    indication_name: str,
    ops_selector: str,
    codeset: str | None,
    latest_year: int,
    latest_any: pd.DataFrame,
    case_col: str,
    threshold_summary: pd.DataFrame,
    yearly_summary: pd.DataFrame,
    matched_codes: pd.DataFrame,
    main_threshold: int,
    strict_threshold: int,
    time_bins: list[int],
) -> dict[str, Any]:
    latest_row = yearly_summary.loc[yearly_summary["year"] == latest_year].iloc[0].to_dict()
    previous = yearly_summary.loc[yearly_summary["year"] < latest_year]
    prev_row = previous.iloc[-1].to_dict() if not previous.empty else {}
    return {
        "indication_name": indication_name,
        "ops_selector": ops_selector,
        "codeset": codeset,
        "case_col": case_col,
        "latest_year": latest_year,
        "latest_year_cases_total": int(latest_any[case_col].sum()),
        "latest_year_hospitals_any": int(len(latest_any)),
        "threshold_summary": threshold_summary.to_dict(orient="records"),
        "main_threshold": main_threshold,
        "strict_threshold": strict_threshold,
        "time_bins": time_bins,
        "matched_subcodes": matched_codes["matched_subcode"].tolist(),
        "latest_year_row": latest_row,
        "previous_year_row": prev_row,
    }


def build_indication_report(
    *,
    indication_name: str,
    ops_selector: str,
    label: str,
    base_xml_dir: Path,
    report_dir: Path,
    codeset: str | None = None,
    cache_tag: str | None = None,
    geocode_cache_tag: str | None = None,
    latest_year: int | None = None,
    thresholds: list[int] | None = None,
    main_threshold: int = DEFAULT_MAIN_THRESHOLD,
    strict_threshold: int = DEFAULT_STRICT_THRESHOLD,
    time_bins: list[int] | None = None,
    grid_resolution: float = 0.05,
) -> dict[str, Any]:
    thresholds = sorted(set((thresholds or DEFAULT_THRESHOLDS) + [main_threshold, strict_threshold]))
    thresholds = [threshold for threshold in thresholds if threshold >= 10]
    base_threshold = DEFAULT_BASE_THRESHOLD
    threshold_summary_thresholds = sorted(set([base_threshold] + thresholds))
    time_bins = sorted(set(time_bins or [30, 60, 90, 120]))
    dirs = ensure_report_dirs(report_dir)
    ops_targets = parse_target_specs([f"{label}={ops_selector}"])
    case_col = target_case_column(label)
    codes_col = target_codes_column(label)

    latest_xml = latest_year_dir(base_xml_dir) if latest_year is None else base_xml_dir / f"xml_{latest_year}"
    latest_year = int(latest_xml.name.replace("xml_", ""))
    latest_df = extract_hospital_code_totals(latest_xml, ops_targets=ops_targets)
    latest_any = latest_df.loc[latest_df[case_col] > 0].copy().sort_values(case_col, ascending=False).reset_index(drop=True)
    threshold_summary = threshold_summary_latest_year(latest_any, case_col, threshold_summary_thresholds)
    matched_codes = matched_subcodes_table(latest_any, codes_col)

    hospital_year, yearly_summary, schema_check = run_longitudinal_pipeline(
        base_dir=base_xml_dir,
        out_dir=dirs["tables"] / "tmp_longitudinal",
        ops_targets=ops_targets,
        icd_targets={},
        denominator_label=None,
        summary_threshold=min(thresholds),
    )
    threshold_sensitivity = yearly_threshold_sensitivity(hospital_year, case_col, thresholds)
    top_all_years = top_centers_all_years(hospital_year, case_col)

    tag_slug = slugify_text(cache_tag) if cache_tag else slugify_text(ops_selector)
    geocode_tag_slug = slugify_text(geocode_cache_tag) if geocode_cache_tag else tag_slug

    geocoded_all = geocode_dataframe(
        latest_any,
        cache_path=config.GEOCODE_CACHE_DIR / f"{slugify_text(indication_name)}_{geocode_tag_slug}_geocode_cache.csv",
    )
    geocoded_all = geocoded_all.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)
    enriched = enrich_with_state_and_urbanity(geocoded_all, case_col)
    state_summary = state_summary_table(enriched, case_col, thresholds)
    urban_summary = urban_summary_table(enriched, case_col, thresholds)

    latest_any.to_csv(dirs["tables"] / "latest_year_hospital_code_totals.csv", index=False)
    threshold_summary.to_csv(dirs["tables"] / "latest_year_threshold_summary.csv", index=False)
    matched_codes.to_csv(dirs["tables"] / "latest_year_matched_subcodes.csv", index=False)
    top_all_years.to_csv(dirs["tables"] / "top_centers_all_years.csv", index=False)
    yearly_summary.to_csv(dirs["tables"] / "yearly_summary.csv", index=False)
    hospital_year.to_csv(dirs["tables"] / "hospital_year.csv", index=False)
    schema_check.to_csv(dirs["tables"] / "schema_check.csv", index=False)
    threshold_sensitivity.to_csv(dirs["tables"] / "yearly_threshold_sensitivity.csv", index=False)
    geocoded_all.to_csv(dirs["tables"] / "latest_year_geocoded_all_centers.csv", index=False)
    state_summary.to_csv(dirs["tables"] / "latest_year_state_summary.csv", index=False)
    urban_summary.to_csv(dirs["tables"] / "latest_year_urban_summary.csv", index=False)

    for threshold in sorted(set([base_threshold] + thresholds)):
        subset = enriched.loc[enriched[case_col] >= threshold].copy()
        subset.to_csv(dirs["tables"] / f"latest_year_centers_ge_{threshold}.csv", index=False)

    plot_yearly_trends(yearly_summary, threshold_sensitivity, slugify_label(label), indication_name, dirs["figures"] / "01_yearly_trends.png")
    plot_threshold_counts(threshold_summary, indication_name, latest_year, dirs["figures"] / "02_threshold_counts_latest_year.png")
    plot_top_centers(latest_any, case_col, indication_name, latest_year, dirs["figures"] / "03_top_centers_latest_year.png", n=15)
    plot_case_distribution(latest_any, case_col, indication_name, latest_year, dirs["figures"] / "04_case_distribution_latest_year.png")
    plot_state_summary(
        state_summary,
        indication_name,
        latest_year,
        dirs["figures"] / f"05_state_summary_ge_{main_threshold}.png",
        threshold=main_threshold,
    )
    plot_urban_summary(urban_summary, indication_name, latest_year, dirs["figures"] / "06_urban_rural_centers.png")
    plot_centers_map(enriched, case_col, indication_name, latest_year, dirs["figures"] / f"07_centers_map_ge_{main_threshold}.png", threshold=main_threshold)
    plot_centers_map(enriched, case_col, indication_name, latest_year, dirs["figures"] / f"08_centers_map_ge_{strict_threshold}.png", threshold=strict_threshold)

    for threshold in sorted({main_threshold, strict_threshold}):
        subset = enriched.loc[enriched[case_col] >= threshold].copy()
        if subset.empty:
            continue
        subset["ops_cases"] = subset[case_col]
        subset["threshold"] = threshold
        threshold_csv = dirs["tables"] / f"latest_year_centers_ge_{threshold}.csv"
        polygons = generate_isochrone_cache(
            subset,
            tag=f"{slugify_text(indication_name)}_{tag_slug}_ge_{threshold}",
            time_bins=time_bins,
            force_recalc=False,
            max_retries=3,
            speed_factor=1.0,
        )
        centers_geojson, unions_geojson, meta_json = export_isochrones(
            subset,
            polygons,
            tag=f"{slugify_text(indication_name)}_{tag_slug}_ge_{threshold}",
        )
        centers_geojson.rename(dirs["geo"] / f"isochrones_ge_{threshold}_centers.geojson")
        unions_geojson.rename(dirs["geo"] / f"isochrones_ge_{threshold}_unions.geojson")
        meta_json.rename(dirs["geo"] / f"isochrones_ge_{threshold}_meta.json")
        coverage = summarize_union_coverage(
            gpd.read_file(dirs["geo"] / f"isochrones_ge_{threshold}_unions.geojson"),
            grid_resolution=grid_resolution,
        )
        coverage.to_csv(dirs["tables"] / f"isochrone_coverage_urban_rural_ge_{threshold}.csv", index=False)
        plot_isochrone_map(
            dirs["geo"] / f"isochrones_ge_{threshold}_unions.geojson",
            threshold_csv,
            case_col,
            indication_name,
            latest_year,
            dirs["figures"] / f"09_isochrone_map_ge_{threshold}.png",
            threshold,
        )
        plot_coverage_summary(
            coverage,
            indication_name,
            dirs["figures"] / f"10_isochrone_coverage_ge_{threshold}.png",
            threshold,
        )

    summary = summary_payload(
        indication_name=indication_name,
        ops_selector=ops_selector,
        codeset=codeset,
        latest_year=latest_year,
        latest_any=latest_any,
        case_col=case_col,
        threshold_summary=threshold_summary,
        yearly_summary=yearly_summary,
        matched_codes=matched_codes,
        main_threshold=main_threshold,
        strict_threshold=strict_threshold,
        time_bins=time_bins,
    )
    (dirs["root"] / "report_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return {
        "report_dir": str(dirs["root"]),
        "latest_year": latest_year,
        "case_col": case_col,
        "tables_dir": str(dirs["tables"]),
        "figures_dir": str(dirs["figures"]),
        "geo_dir": str(dirs["geo"]),
        "summary": summary,
    }
