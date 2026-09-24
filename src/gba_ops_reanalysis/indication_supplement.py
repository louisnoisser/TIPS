"""Supplemental analyses built from an existing indication report directory."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any

import matplotlib

matplotlib.use("Agg")

import geopandas as gpd
import matplotlib.lines as mlines
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize

from . import config
from .isochrones import export_isochrones, generate_isochrone_cache
from .population import (
    county_population_table,
    germany_population_total,
    population_raster_path,
    state_population_table,
    summarize_regional_population_coverage,
    summarize_union_population_coverage,
)
from .urban_rural import add_smod_labels


def _require_table(tables_dir: Path, name: str) -> pd.DataFrame:
    path = tables_dir / name
    if not path.exists():
        raise FileNotFoundError(f"Missing required table: {path}")
    return pd.read_csv(path)


def _representative_text(values: pd.Series) -> str:
    cleaned = [str(value).strip() for value in values.fillna("") if str(value).strip()]
    return cleaned[-1] if cleaned else ""


def _gini(values: pd.Series) -> float:
    arr = np.sort(values.astype(float).to_numpy())
    if len(arr) == 0 or arr.sum() <= 0:
        return 0.0
    index = np.arange(1, len(arr) + 1)
    return float((2 * np.sum(index * arr) / (len(arr) * arr.sum())) - (len(arr) + 1) / len(arr))


def _clean_geo_value(value: Any) -> str:
    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return text.strip().strip("'\"")


def _slugify_text(text: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(text).strip())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def _normalize_county_code_frame(df: pd.DataFrame) -> pd.DataFrame:
    if "county_code" in df.columns:
        df = df.copy()
        df["county_code"] = df["county_code"].map(_clean_geo_value)
    return df


def _read_outline() -> gpd.GeoDataFrame:
    return gpd.read_file(config.GERMANY_OUTLINE).to_crs("EPSG:4326")


def _read_states() -> gpd.GeoDataFrame:
    states = gpd.read_file(config.GERMANY_STATES).to_crs("EPSG:4326")
    state_col = next((col for col in ("NAME_1", "lan_name", "name", "NAME") if col in states.columns), None)
    if state_col is None:
        raise KeyError("No state name column found in state GeoJSON")
    states = states.rename(columns={state_col: "state_name"})
    return states[["state_name", "geometry"]].copy()


def _read_counties() -> gpd.GeoDataFrame:
    counties = gpd.read_file(config.GERMANY_COUNTIES).to_crs("EPSG:4326")
    counties = counties.assign(
        county_code=counties["krs_code"].map(_clean_geo_value),
        county_name=counties["krs_name"].map(_clean_geo_value),
        state_name=counties["lan_name"].map(_clean_geo_value),
        county_type=counties["krs_type"].map(_clean_geo_value),
    )
    centroid_frame = gpd.GeoDataFrame(
        counties[["county_code"]].copy(),
        geometry=counties.to_crs("EPSG:3857").centroid,
        crs="EPSG:3857",
    ).to_crs("EPSG:4326")
    centroid_labels = add_smod_labels(centroid_frame)[["county_code", "urban_rural"]]
    counties = counties.merge(centroid_labels, on="county_code", how="left")
    counties["urban_rural"] = counties["urban_rural"].fillna("other")
    return counties[["county_code", "county_name", "state_name", "county_type", "urban_rural", "geometry"]].copy()


def _make_point_gdf(df: pd.DataFrame) -> gpd.GeoDataFrame:
    work = df.dropna(subset=["longitude", "latitude"]).copy()
    return gpd.GeoDataFrame(
        work,
        geometry=gpd.points_from_xy(work["longitude"], work["latitude"]),
        crs="EPSG:4326",
    )


def _assign_counties(all_centers: pd.DataFrame) -> pd.DataFrame:
    counties = _read_counties()
    joined = gpd.sjoin(
        _make_point_gdf(all_centers),
        counties[["county_code", "county_name", "state_name", "county_type", "urban_rural", "geometry"]],
        how="left",
        predicate="within",
    ).drop(columns=["index_right"], errors="ignore")
    joined["county_name"] = joined["county_name"].fillna("Unknown")
    joined["county_code"] = joined["county_code"].fillna("")
    joined["county_type"] = joined["county_type"].fillna("Unknown")
    joined["state_name"] = joined["state_name_right"].fillna(joined.get("state_name_left", "Unknown"))
    if "urban_rural_right" in joined.columns:
        joined["county_urban_rural"] = joined["urban_rural_right"].fillna("other")
    else:
        joined["county_urban_rural"] = "other"
    if "urban_rural_left" in joined.columns:
        joined["urban_rural"] = joined["urban_rural_left"]
    joined = joined.drop(
        columns=[
            "geometry",
            "state_name_left",
            "state_name_right",
            "urban_rural_left",
            "urban_rural_right",
        ],
        errors="ignore",
    )
    return pd.DataFrame(joined)


def build_yearly_concentration_summary(hospital_year: pd.DataFrame, case_col: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for year, group in hospital_year.groupby("year", dropna=False):
        active = group.loc[pd.to_numeric(group[case_col], errors="coerce").fillna(0) > 0].copy()
        active[case_col] = pd.to_numeric(active[case_col], errors="coerce").fillna(0)
        total_cases = float(active[case_col].sum())
        shares = active[case_col] / total_cases if total_cases else pd.Series(dtype=float)
        active_sorted = active.sort_values(case_col, ascending=False)
        rows.append(
            {
                "year": int(year),
                "active_centers": int(len(active)),
                "cases_total": int(total_cases),
                "top_1_share_pct": round(100 * active_sorted[case_col].head(1).sum() / total_cases, 2) if total_cases else 0.0,
                "top_5_share_pct": round(100 * active_sorted[case_col].head(5).sum() / total_cases, 2) if total_cases else 0.0,
                "top_10_share_pct": round(100 * active_sorted[case_col].head(10).sum() / total_cases, 2) if total_cases else 0.0,
                "top_20_share_pct": round(100 * active_sorted[case_col].head(20).sum() / total_cases, 2) if total_cases else 0.0,
                "hhi_10000": round(float(np.square(shares).sum() * 10000), 2) if total_cases else 0.0,
                "effective_center_count": round(float(1 / np.square(shares).sum()), 2) if total_cases and np.square(shares).sum() else 0.0,
                "gini_cases": round(_gini(active[case_col]), 4),
            }
        )
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def aggregate_ik_year(hospital_year: pd.DataFrame, case_col: str) -> pd.DataFrame:
    work = hospital_year.copy()
    work[case_col] = pd.to_numeric(work[case_col], errors="coerce").fillna(0)
    grouped = (
        work.groupby(["year", "ik"], dropna=False)
        .agg(
            cases=(case_col, "sum"),
            facilities=("facility_id", "nunique"),
            hospital_name=("hospital_name", _representative_text),
            city=("city", _representative_text),
        )
        .reset_index()
        .sort_values(["year", "cases", "ik"], ascending=[True, False, True])
        .reset_index(drop=True)
    )
    return grouped


def build_top_ik_all_years(ik_year: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for ik, group in ik_year.groupby("ik", dropna=False):
        active = group.loc[group["cases"] > 0].sort_values("year")
        if active.empty:
            continue
        latest = active.iloc[-1]
        rows.append(
            {
                "ik": ik,
                "hospital_name": latest["hospital_name"],
                "city": latest["city"],
                "total_cases": int(active["cases"].sum()),
                "years_active": int(active["year"].nunique()),
                "first_year": int(active["year"].min()),
                "last_year": int(active["year"].max()),
                "max_single_year_cases": int(active["cases"].max()),
            }
        )
    return pd.DataFrame(rows).sort_values(["total_cases", "years_active"], ascending=[False, False]).reset_index(drop=True)


def build_threshold_churn_by_ik(ik_year: pd.DataFrame, thresholds: list[int]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    years = sorted(int(year) for year in ik_year["year"].dropna().unique())
    for threshold in sorted(set(thresholds)):
        year_sets = {
            year: set(ik_year.loc[(ik_year["year"] == year) & (ik_year["cases"] >= threshold), "ik"].astype(str))
            for year in years
        }
        for previous_year, year in zip(years[:-1], years[1:], strict=True):
            previous_set = year_sets[previous_year]
            current_set = year_sets[year]
            retained = previous_set & current_set
            entered = current_set - previous_set
            exited = previous_set - current_set
            rows.append(
                {
                    "threshold": threshold,
                    "previous_year": previous_year,
                    "year": year,
                    "previous_iks": len(previous_set),
                    "current_iks": len(current_set),
                    "retained_iks": len(retained),
                    "entered_iks": len(entered),
                    "exited_iks": len(exited),
                    "retention_rate_prev_pct": round(100 * len(retained) / len(previous_set), 2) if previous_set else 0.0,
                    "new_share_current_pct": round(100 * len(entered) / len(current_set), 2) if current_set else 0.0,
                }
            )
    return pd.DataFrame(rows).sort_values(["threshold", "year"]).reset_index(drop=True)


def build_coverage_tradeoff(coverage_main: pd.DataFrame, coverage_strict: pd.DataFrame, *, main_threshold: int, strict_threshold: int) -> pd.DataFrame:
    merged = coverage_main.merge(
        coverage_strict,
        on=["time_minutes", "urban_rural"],
        how="inner",
        suffixes=(f"_ge_{main_threshold}", f"_ge_{strict_threshold}"),
    )
    merged["coverage_gap_pct_points"] = (
        merged[f"pct_of_class_covered_ge_{main_threshold}"] - merged[f"pct_of_class_covered_ge_{strict_threshold}"]
    ).round(2)
    merged["coverage_retained_pct"] = np.where(
        merged[f"pct_of_class_covered_ge_{main_threshold}"] > 0,
        100 * merged[f"pct_of_class_covered_ge_{strict_threshold}"] / merged[f"pct_of_class_covered_ge_{main_threshold}"],
        0.0,
    ).round(2)
    return merged.sort_values(["time_minutes", "urban_rural"]).reset_index(drop=True)


def build_population_tradeoff(
    coverage_main: pd.DataFrame,
    coverage_strict: pd.DataFrame,
    *,
    main_threshold: int,
    strict_threshold: int,
) -> pd.DataFrame:
    merged = coverage_main.merge(
        coverage_strict,
        on=["time_minutes", "population_total"],
        how="inner",
        suffixes=(f"_ge_{main_threshold}", f"_ge_{strict_threshold}"),
    )
    merged["coverage_gap_pct_points"] = (
        merged[f"pct_population_covered_ge_{main_threshold}"] - merged[f"pct_population_covered_ge_{strict_threshold}"]
    ).round(2)
    merged["population_retained_pct"] = np.where(
        merged[f"pct_population_covered_ge_{main_threshold}"] > 0,
        100 * merged[f"pct_population_covered_ge_{strict_threshold}"] / merged[f"pct_population_covered_ge_{main_threshold}"],
        0.0,
    ).round(2)
    return merged.sort_values("time_minutes").reset_index(drop=True)


def build_state_population_rates(state_summary: pd.DataFrame, state_pop: pd.DataFrame) -> pd.DataFrame:
    merged = state_summary.merge(state_pop, on="state_name", how="left")
    merged["population_total"] = pd.to_numeric(merged["population_total"], errors="coerce").fillna(0).astype(int)
    merged["cases_per_million"] = np.where(
        merged["population_total"] > 0,
        1_000_000 * merged["total_cases"] / merged["population_total"],
        0.0,
    ).round(2)
    merged["hospitals_per_million"] = np.where(
        merged["population_total"] > 0,
        1_000_000 * merged["hospitals"] / merged["population_total"],
        0.0,
    ).round(2)
    return merged.sort_values(["threshold", "cases_per_million"], ascending=[True, False]).reset_index(drop=True)


def build_region_provider_summary(
    centers_df: pd.DataFrame,
    region_frame: pd.DataFrame,
    *,
    case_col: str,
    thresholds: list[int],
    join_cols: list[str],
) -> pd.DataFrame:
    work = centers_df.copy()
    work[case_col] = pd.to_numeric(work[case_col], errors="coerce").fillna(0)
    base = region_frame.drop(columns=["geometry"], errors="ignore").copy()

    rows: list[pd.DataFrame] = []
    for threshold in sorted(set(thresholds)):
        subset = work.loc[work[case_col] >= threshold].copy()
        grouped = (
            subset.groupby(join_cols, dropna=False)
            .agg(hospitals=("facility_id", "nunique"), total_cases=(case_col, "sum"), median_cases=(case_col, "median"))
            .reset_index()
        )
        merged = base.merge(grouped, on=join_cols, how="left")
        merged["threshold"] = threshold
        merged["hospitals"] = pd.to_numeric(merged["hospitals"], errors="coerce").fillna(0).astype(int)
        merged["total_cases"] = pd.to_numeric(merged["total_cases"], errors="coerce").fillna(0).astype(int)
        merged["median_cases"] = pd.to_numeric(merged["median_cases"], errors="coerce").fillna(0.0)
        merged["population_total"] = pd.to_numeric(merged["population_total"], errors="coerce").fillna(0).astype(int)
        merged["cases_per_million"] = np.where(
            merged["population_total"] > 0,
            1_000_000 * merged["total_cases"] / merged["population_total"],
            0.0,
        ).round(2)
        merged["hospitals_per_million"] = np.where(
            merged["population_total"] > 0,
            1_000_000 * merged["hospitals"] / merged["population_total"],
            0.0,
        ).round(2)
        rows.append(merged)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def build_regional_access_context(
    region_frame: pd.DataFrame,
    provider_summary: pd.DataFrame,
    coverage_tables: dict[int, pd.DataFrame],
    national_coverage_tables: dict[int, pd.DataFrame],
    *,
    join_cols: list[str],
) -> pd.DataFrame:
    context = region_frame.drop(columns=["geometry"], errors="ignore").copy()

    for threshold, coverage in coverage_tables.items():
        pivot = (
            coverage.pivot_table(index=join_cols, columns="time_minutes", values="pct_population_covered", fill_value=0)
            .reset_index()
        )
        rename_map = {
            time_minutes: f"coverage_ge_{threshold}_{int(time_minutes)}m_pct"
            for time_minutes in pivot.columns
            if time_minutes not in join_cols
        }
        pivot = pivot.rename(columns=rename_map)
        context = context.merge(pivot, on=join_cols, how="left")

        national_map = {
            int(row["time_minutes"]): float(row["pct_population_covered"])
            for _, row in national_coverage_tables[threshold].iterrows()
        }
        for time_minutes, national_pct in national_map.items():
            coverage_col = f"coverage_ge_{threshold}_{time_minutes}m_pct"
            if coverage_col in context.columns:
                context[coverage_col] = pd.to_numeric(context[coverage_col], errors="coerce").fillna(0.0)
                context[f"gap_vs_germany_ge_{threshold}_{time_minutes}m_pp"] = (
                    context[coverage_col] - national_pct
                ).round(2)
                context[f"covered_ge_{threshold}_{time_minutes}m"] = context[coverage_col] > 50

    for threshold in sorted(int(value) for value in provider_summary["threshold"].dropna().unique()):
        subset = provider_summary.loc[provider_summary["threshold"] == threshold].copy()
        subset = subset.rename(
            columns={
                "hospitals": f"centers_ge_{threshold}",
                "total_cases": f"cases_ge_{threshold}",
                "median_cases": f"median_cases_ge_{threshold}",
                "cases_per_million": f"cases_per_million_ge_{threshold}",
                "hospitals_per_million": f"centers_per_million_ge_{threshold}",
            }
        )
        keep_cols = join_cols + [
            f"centers_ge_{threshold}",
            f"cases_ge_{threshold}",
            f"median_cases_ge_{threshold}",
            f"cases_per_million_ge_{threshold}",
            f"centers_per_million_ge_{threshold}",
        ]
        context = context.merge(subset[keep_cols], on=join_cols, how="left")

    numeric_cols = [column for column in context.columns if column.endswith(("_pct", "_pp")) or "_ge_" in column and column.startswith(("centers", "cases", "median_cases"))]
    for column in numeric_cols:
        context[column] = pd.to_numeric(context[column], errors="coerce").fillna(0)
    return context


def _move_output(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    src.replace(dest)


def _load_or_build_csv(
    path: Path,
    builder: Any,
    *,
    expected_thresholds: list[int] | None = None,
    required_columns: list[str] | None = None,
) -> pd.DataFrame:
    if path.exists():
        frame = pd.read_csv(path)
        if required_columns and not set(required_columns).issubset(frame.columns):
            pass
        elif expected_thresholds is None or "threshold" not in frame.columns:
            return frame
        else:
            actual = sorted(pd.to_numeric(frame["threshold"], errors="coerce").dropna().astype(int).unique().tolist())
            if actual == sorted(expected_thresholds):
                return frame
    frame = builder()
    frame.to_csv(path, index=False)
    return frame


def _write_figure_strategy(figures_dir: Path, *, main_threshold: int, strict_threshold: int) -> None:
    main_files = [
        "01_yearly_trends.png",
        "02_threshold_counts_latest_year.png",
        "11_concentration_trends.png",
        f"09_isochrone_map_ge_{main_threshold}.png",
        f"10_isochrone_coverage_ge_{main_threshold}.png",
        f"13_coverage_tradeoff_ge_{main_threshold}_vs_ge_{strict_threshold}.png",
        f"15_population_coverage_ge_{main_threshold}_vs_ge_{strict_threshold}.png",
        "17_isochrone_multipanel_thresholds.png",
    ]
    supplement_files = [
        "03_top_centers_latest_year.png",
        "04_case_distribution_latest_year.png",
        f"05_state_summary_ge_{main_threshold}.png",
        "06_urban_rural_centers.png",
        f"07_centers_map_ge_{main_threshold}.png",
        f"08_centers_map_ge_{strict_threshold}.png",
        f"09_isochrone_map_ge_{strict_threshold}.png",
        f"10_isochrone_coverage_ge_{strict_threshold}.png",
        "12_threshold_churn_by_ik.png",
        "14_top_ik_all_years.png",
        "16_state_case_rates_per_million.png",
        "18_state_county_access_context.png",
        "19_county_population_coverage_multipanel.png",
    ]

    rows: list[dict[str, str]] = []
    category_map = {
        "paper_main": main_files,
        "paper_supplement": supplement_files,
    }
    for category, names in category_map.items():
        category_dir = figures_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        for name in names:
            source = figures_dir / name
            if not source.exists():
                continue
            target = category_dir / name
            shutil.copy2(source, target)
            rows.append(
                {
                    "category": category,
                    "file": name,
                    "source_path": str(source),
                    "curated_path": str(target),
                }
            )

    if rows:
        pd.DataFrame(rows).to_csv(figures_dir / "figure_strategy.csv", index=False)
        markdown_lines = [
            "# Figure Strategy",
            "",
            "Main figures are copied to `figures/paper_main/`.",
            "Supplement figures are copied to `figures/paper_supplement/`.",
            "",
            "## Main",
        ]
        markdown_lines.extend([f"- `{name}`" for name in main_files])
        markdown_lines.extend(["", "## Supplement"])
        markdown_lines.extend([f"- `{name}`" for name in supplement_files])
        (figures_dir / "FIGURE_STRATEGY.md").write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")


def _ensure_threshold_isochrones(
    *,
    report_dir: Path,
    summary: dict[str, Any],
    threshold: int,
    case_col: str,
    time_bins: list[int],
) -> tuple[Path, Path]:
    tables_dir = report_dir / "tables"
    geo_dir = report_dir / "geo"
    centers_path = tables_dir / f"latest_year_centers_ge_{threshold}.csv"
    union_dest = geo_dir / f"isochrones_ge_{threshold}_unions.geojson"
    centers_dest = geo_dir / f"isochrones_ge_{threshold}_centers.geojson"
    meta_dest = geo_dir / f"isochrones_ge_{threshold}_meta.json"

    if union_dest.exists() and centers_dest.exists():
        return centers_dest, union_dest

    subset = pd.read_csv(centers_path)
    if subset.empty:
        raise ValueError(f"No centers available for threshold >= {threshold}")

    subset = subset.dropna(subset=["longitude", "latitude"]).copy()
    subset["ops_cases"] = pd.to_numeric(subset[case_col], errors="coerce").fillna(0).astype(int)
    subset["threshold"] = threshold
    subset["target_label"] = summary.get("indication_name", "")

    tag = f"{_slugify_text(summary['indication_name'])}_{_slugify_text(summary['ops_selector'])}_ge_{threshold}"
    polygons = generate_isochrone_cache(
        subset,
        tag=tag,
        time_bins=time_bins,
        force_recalc=False,
        max_retries=3,
        speed_factor=1.0,
        max_locations_per_request=2,
    )
    centers_geo, union_geo, meta_json = export_isochrones(subset, polygons, tag=tag)
    _move_output(centers_geo, centers_dest)
    _move_output(union_geo, union_dest)
    _move_output(meta_json, meta_dest)
    return centers_dest, union_dest


def plot_concentration_trends(df: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(12, 10), constrained_layout=True)
    axes[0].plot(df["year"], df["top_5_share_pct"], marker="o", linewidth=2, label="Top 5 share", color="#134074")
    axes[0].plot(df["year"], df["top_10_share_pct"], marker="o", linewidth=2, label="Top 10 share", color="#0b6e4f")
    axes[0].plot(df["year"], df["top_20_share_pct"], marker="o", linewidth=2, label="Top 20 share", color="#c1121f")
    axes[0].set_ylabel("Share of national volume (%)")
    axes[0].set_title("Center concentration over time")
    axes[0].grid(alpha=0.3)
    axes[0].legend(frameon=False)

    axes[1].plot(df["year"], df["hhi_10000"], marker="o", linewidth=2, color="#6a4c93", label="HHI")
    twin = axes[1].twinx()
    twin.plot(df["year"], df["effective_center_count"], marker="o", linewidth=2, color="#f9844a", label="Effective centers")
    axes[1].set_ylabel("HHI (0-10,000)")
    twin.set_ylabel("Effective center count")
    axes[1].set_title("Concentration index and effective center count")
    axes[1].grid(alpha=0.3)
    handles_left, labels_left = axes[1].get_legend_handles_labels()
    handles_right, labels_right = twin.get_legend_handles_labels()
    axes[1].legend(handles_left + handles_right, labels_left + labels_right, frameon=False, loc="upper left")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_threshold_churn(df: pd.DataFrame, output_path: Path) -> None:
    thresholds = sorted(int(value) for value in df["threshold"].dropna().unique())
    fig, axes = plt.subplots(len(thresholds), 1, figsize=(12, 4.5 * max(1, len(thresholds))), constrained_layout=True)
    axes_list = axes if isinstance(axes, np.ndarray) else np.array([axes])
    for axis, threshold in zip(axes_list, thresholds, strict=True):
        subset = df.loc[df["threshold"] == threshold].copy()
        labels = subset["year"].astype(int).astype(str)
        x = np.arange(len(subset))
        axis.bar(x, subset["retained_iks"], color="#134074", label="Retained")
        axis.bar(x, subset["entered_iks"], bottom=subset["retained_iks"], color="#0b6e4f", label="Entered")
        axis.plot(x, subset["exited_iks"], marker="o", linewidth=2, color="#c1121f", label="Exited")
        axis.set_xticks(x)
        axis.set_xticklabels(labels)
        axis.set_ylabel("IK count")
        axis.set_title(f"IK-level churn for centers with >= {threshold} cases")
        axis.grid(alpha=0.3, axis="y")
        axis.legend(frameon=False)
    axes_list[-1].set_xlabel("Available year")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_coverage_tradeoff(df: pd.DataFrame, output_path: Path, *, main_threshold: int, strict_threshold: int) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    pivot_gap = df.pivot(index="time_minutes", columns="urban_rural", values="coverage_gap_pct_points").fillna(0)
    pivot_retained = df.pivot(index="time_minutes", columns="urban_rural", values="coverage_retained_pct").fillna(0)
    colors = {"urban": "#c1121f", "rural": "#134074", "other": "#6c757d"}

    x = np.arange(len(pivot_gap.index))
    categories = list(pivot_gap.columns)
    width = 0.25 if categories else 0.25
    for idx, category in enumerate(categories):
        axes[0].bar(
            x + (idx - (len(categories) - 1) / 2) * width,
            pivot_gap[category],
            width=width,
            label=str(category),
            color=colors.get(str(category), "#6c757d"),
        )
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(pivot_gap.index.astype(str))
    axes[0].set_xlabel("Travel time (minutes)")
    axes[0].set_ylabel("Coverage loss (pct points)")
    axes[0].set_title(f"Coverage loss from >= {main_threshold} to >= {strict_threshold}")
    axes[0].legend(frameon=False)

    for category in pivot_retained.columns:
        axes[1].plot(
            pivot_retained.index,
            pivot_retained[category],
            marker="o",
            linewidth=2,
            label=str(category),
            color=colors.get(str(category), "#6c757d"),
        )
    axes[1].set_xlabel("Travel time (minutes)")
    axes[1].set_ylabel("Percent of main-network coverage retained")
    axes[1].set_ylim(0, 105)
    axes[1].set_title("Coverage retained in stricter network")
    axes[1].grid(alpha=0.3)
    axes[1].legend(frameon=False)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_top_ik_all_years(df: pd.DataFrame, output_path: Path, n: int = 15) -> None:
    subset = df.head(n).sort_values("total_cases", ascending=True)
    fig, ax = plt.subplots(figsize=(12, 8), constrained_layout=True)
    ax.barh(subset["hospital_name"], subset["total_cases"], color="#0b6e4f")
    ax.set_xlabel("Cases across all available years")
    ax.set_title(f"Top {len(subset)} IK-aggregated centers across all available years")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_population_coverage(
    coverage_main: pd.DataFrame,
    coverage_strict: pd.DataFrame,
    output_path: Path,
    *,
    main_threshold: int,
    strict_threshold: int,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    ax.plot(
        coverage_main["time_minutes"],
        coverage_main["pct_population_covered"],
        marker="o",
        linewidth=2.8,
        color="#134074",
        label=f">= {main_threshold} cases",
    )
    ax.plot(
        coverage_strict["time_minutes"],
        coverage_strict["pct_population_covered"],
        marker="o",
        linewidth=2.8,
        color="#c1121f",
        label=f">= {strict_threshold} cases",
    )
    if not coverage_main.empty:
        main_last = coverage_main.sort_values("time_minutes").iloc[-1]
        ax.annotate(
            f"{float(main_last['pct_population_covered']):.1f}%",
            xy=(main_last["time_minutes"], main_last["pct_population_covered"]),
            xytext=(6, 6),
            textcoords="offset points",
            color="#134074",
            fontsize=9,
        )
    if not coverage_strict.empty:
        strict_last = coverage_strict.sort_values("time_minutes").iloc[-1]
        ax.annotate(
            f"{float(strict_last['pct_population_covered']):.1f}%",
            xy=(strict_last["time_minutes"], strict_last["pct_population_covered"]),
            xytext=(6, -12),
            textcoords="offset points",
            color="#c1121f",
            fontsize=9,
        )
    ax.set_xlabel("Travel time (minutes)")
    ax.set_ylabel("Population covered in Germany (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Population-based isochrone coverage")
    ax.grid(alpha=0.3, axis="both")
    ax.legend(frameon=False)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_state_population_rates(df: pd.DataFrame, output_path: Path, *, threshold: int) -> None:
    subset = df.loc[df["threshold"] == threshold].head(15).sort_values("cases_per_million", ascending=True)
    fig, ax = plt.subplots(figsize=(12, 8), constrained_layout=True)
    ax.barh(subset["state_name"], subset["cases_per_million"], color="#f9844a")
    ax.set_xlabel("Cases per 1,000,000 population")
    ax.set_title(f"State-level case rates (threshold >= {threshold})")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_threshold_isochrone_panel(
    ax: plt.Axes,
    outline: gpd.GeoDataFrame,
    union_gdf: gpd.GeoDataFrame,
    centers_df: pd.DataFrame,
    *,
    title: str,
    letter: str,
    case_col: str,
) -> None:
    palette = ["#d9f0ff", "#74c0e3", "#1d91c0", "#225ea8", "#0c2c84"]
    outline.plot(ax=ax, color="#f8f8f8", edgecolor="#7f7f7f", linewidth=0.7)
    for idx, (_, row) in enumerate(union_gdf.sort_values("time_minutes", ascending=False).iterrows()):
        gpd.GeoSeries([row.geometry], crs="EPSG:4326").plot(
            ax=ax,
            color=palette[min(idx, len(palette) - 1)],
            alpha=0.4,
            edgecolor="#173f5f",
            linewidth=0.5,
        )
    if not centers_df.empty:
        ax.scatter(
            centers_df["longitude"],
            centers_df["latitude"],
            s=np.clip(pd.to_numeric(centers_df[case_col], errors="coerce").fillna(0) * 1.5, 10, 140),
            color="#b02a37",
            alpha=0.8,
            edgecolors="white",
            linewidths=0.2,
        )
    ax.set_axis_off()
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.text(0.01, 0.98, letter, transform=ax.transAxes, va="top", ha="left", fontweight="bold", fontsize=12)


def plot_isochrone_threshold_multipanel(
    panels: list[dict[str, Any]],
    output_path: Path,
    *,
    case_col: str,
) -> None:
    outline = _read_outline()
    fig, axes = plt.subplots(2, 2, figsize=(16, 18), constrained_layout=True)
    axes_flat = axes.flatten()

    for ax, panel, letter in zip(axes_flat, panels, ["A", "B", "C", "D"], strict=False):
        _plot_threshold_isochrone_panel(
            ax,
            outline,
            panel["union_gdf"],
            panel["centers_df"],
            title=panel["title"],
            letter=letter,
            case_col=case_col,
        )

    for ax in axes_flat[len(panels) :]:
        ax.set_axis_off()

    legend_time_bins = sorted(
        {
            int(value)
            for panel in panels
            for value in panel["union_gdf"]["time_minutes"].dropna().astype(int).tolist()
        }
    )
    legend_handles = [
        mpatches.Patch(color=color, label=f"{minutes} min")
        for minutes, color in zip(legend_time_bins, ["#0c2c84", "#225ea8", "#1d91c0", "#74c0e3", "#d9f0ff"][-len(legend_time_bins) :], strict=False)
    ]
    legend_handles.append(
        mlines.Line2D([], [], color="#b02a37", marker="o", linestyle="", markersize=6, label="Center")
    )
    fig.legend(legend_handles, [handle.get_label() for handle in legend_handles], loc="lower center", ncol=max(3, len(legend_handles)), frameon=False)
    fig.suptitle("Isochrone comparison across center thresholds", y=1.01, fontsize=15, fontweight="bold")
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_state_county_access_context(
    state_context: pd.DataFrame,
    county_context: pd.DataFrame,
    output_path: Path,
    *,
    main_threshold: int,
    strict_threshold: int,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(18, 8), constrained_layout=True)

    state_sorted = state_context.sort_values(f"coverage_ge_{strict_threshold}_60m_pct", ascending=True)
    y_state = np.arange(len(state_sorted))
    axes[0].barh(
        y_state,
        state_sorted[f"coverage_ge_{main_threshold}_60m_pct"],
        color="#74c0e3",
        alpha=0.75,
        label=f">= {main_threshold} cases",
    )
    axes[0].barh(
        y_state,
        state_sorted[f"coverage_ge_{strict_threshold}_60m_pct"],
        color="#0b7285",
        alpha=0.9,
        label=f">= {strict_threshold} cases",
    )
    axes[0].set_yticks(y_state)
    axes[0].set_yticklabels(state_sorted["state_name"])
    axes[0].set_xlabel("Population covered within 60 min (%)")
    axes[0].set_title("State-level access context")
    axes[0].grid(alpha=0.25, axis="x")
    axes[0].legend(frameon=False)

    county_sorted = county_context.sort_values(f"coverage_ge_{strict_threshold}_60m_pct", ascending=True).head(15).copy()
    county_sorted["county_label"] = county_sorted["county_name"] + " (" + county_sorted["state_name"] + ")"
    colors = county_sorted["urban_rural"].map({"urban": "#c1121f", "rural": "#134074", "other": "#6c757d"}).fillna("#6c757d")
    y_county = np.arange(len(county_sorted))
    axes[1].barh(y_county, county_sorted[f"coverage_ge_{strict_threshold}_60m_pct"], color=colors)
    national_line = float(
        state_context[f"coverage_ge_{strict_threshold}_60m_pct"].mul(state_context["population_total"]).sum()
        / state_context["population_total"].sum()
    )
    axes[1].axvline(national_line, color="#212529", linestyle="--", linewidth=1.2, label="National weighted mean")
    axes[1].set_yticks(y_county)
    axes[1].set_yticklabels(county_sorted["county_label"])
    axes[1].set_xlabel("Population covered within 60 min (%)")
    axes[1].set_title(f"Lowest-access counties for >= {strict_threshold} network")
    axes[1].grid(alpha=0.25, axis="x")
    axes[1].legend(frameon=False)

    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_county_access_multipanel(
    county_geometries: gpd.GeoDataFrame,
    coverage_main: pd.DataFrame,
    coverage_strict: pd.DataFrame,
    output_path: Path,
    *,
    main_threshold: int,
    strict_threshold: int,
) -> None:
    states = _read_states()
    coverage_lookup = {
        (main_threshold, int(time_minutes)): coverage_main.loc[coverage_main["time_minutes"] == time_minutes].copy()
        for time_minutes in sorted(int(value) for value in coverage_main["time_minutes"].dropna().unique())
    }
    coverage_lookup.update(
        {
            (strict_threshold, int(time_minutes)): coverage_strict.loc[coverage_strict["time_minutes"] == time_minutes].copy()
            for time_minutes in sorted(int(value) for value in coverage_strict["time_minutes"].dropna().unique())
        }
    )

    specs = [
        (main_threshold, 30),
        (main_threshold, 60),
        (strict_threshold, 30),
        (strict_threshold, 60),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(18, 18), constrained_layout=True)
    axes_flat = axes.flatten()
    norm = Normalize(vmin=0, vmax=100)
    cmap = plt.cm.YlGnBu

    for ax, (threshold, time_minutes), letter in zip(axes_flat, specs, ["A", "B", "C", "D"], strict=False):
        coverage = coverage_lookup[(threshold, time_minutes)]
        merged = county_geometries.merge(
            coverage[["county_code", "pct_population_covered"]],
            on="county_code",
            how="left",
        )
        merged["pct_population_covered"] = pd.to_numeric(merged["pct_population_covered"], errors="coerce").fillna(0.0)
        merged.plot(
            column="pct_population_covered",
            ax=ax,
            cmap=cmap,
            vmin=0,
            vmax=100,
            linewidth=0.15,
            edgecolor="white",
        )
        states.boundary.plot(ax=ax, color="#333333", linewidth=0.35)
        ax.set_axis_off()
        ax.set_title(f">= {threshold} cases, {time_minutes} min", fontsize=11, fontweight="bold")
        ax.text(0.01, 0.98, letter, transform=ax.transAxes, va="top", ha="left", fontweight="bold", fontsize=12)

    colorbar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=axes_flat.tolist(), shrink=0.65, pad=0.02)
    colorbar.set_label("County population covered (%)")
    fig.suptitle("County-level population access to TIPS centers", y=1.01, fontsize=15, fontweight="bold")
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _population_raster_metadata(path: Path) -> dict[str, Any]:
    name = path.name
    epoch = next((part[1:] for part in name.split("_") if part.startswith("E") and part[1:].isdigit()), None)
    release = next((part for part in name.split("_") if part.startswith("R") and any(char.isdigit() for char in part)), None)
    return {
        "raster_path": str(path),
        "raster_name": name,
        "ghs_epoch": epoch,
        "ghs_release": release,
    }


def _write_population_access_metadata(
    report_dir: Path,
    *,
    payload: dict[str, Any],
) -> None:
    tables_dir = report_dir / "tables"
    metadata_path = tables_dir / "population_access_metadata.json"
    metadata_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    summary_path = report_dir / "report_summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["population_access"] = {
            **payload,
            "metadata_file": str(metadata_path.relative_to(report_dir)),
        }
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def build_indication_supplement(report_dir: Path, *, require_population: bool = False) -> dict[str, str]:
    report_dir = report_dir.resolve()
    tables_dir = report_dir / "tables"
    figures_dir = report_dir / "figures"
    geo_dir = report_dir / "geo"
    summary = json.loads((report_dir / "report_summary.json").read_text(encoding="utf-8"))
    case_col = summary["case_col"]
    main_threshold = int(summary["main_threshold"])
    strict_threshold = int(summary["strict_threshold"])
    time_bins = sorted(int(value) for value in summary.get("time_bins", [30, 60]))
    thresholds = sorted(int(row["threshold"]) for row in summary.get("threshold_summary", []))

    hospital_year = _require_table(tables_dir, "hospital_year.csv")
    concentration = build_yearly_concentration_summary(hospital_year, case_col)
    ik_year = aggregate_ik_year(hospital_year, case_col)
    top_ik = build_top_ik_all_years(ik_year)
    churn = build_threshold_churn_by_ik(ik_year, [main_threshold, strict_threshold])

    coverage_main = _require_table(tables_dir, f"isochrone_coverage_urban_rural_ge_{main_threshold}.csv")
    coverage_strict = _require_table(tables_dir, f"isochrone_coverage_urban_rural_ge_{strict_threshold}.csv")
    coverage_tradeoff = build_coverage_tradeoff(
        coverage_main,
        coverage_strict,
        main_threshold=main_threshold,
        strict_threshold=strict_threshold,
    )
    state_summary = _require_table(tables_dir, "latest_year_state_summary.csv")

    all_centers = _normalize_county_code_frame(_load_or_build_csv(
        tables_dir / "latest_year_centers_ge_1_with_counties.csv",
        lambda: _assign_counties(_require_table(tables_dir, "latest_year_centers_ge_1.csv")),
    ))

    population_supported = True
    population_skip_reason: str | None = None
    population_metadata: dict[str, Any] | None = None
    try:
        pop_raster = population_raster_path()
        population_metadata = _population_raster_metadata(pop_raster)
        state_pop_table = state_population_table()
        county_pop_table = county_population_table()
    except FileNotFoundError as exc:
        population_supported = False
        population_skip_reason = str(exc)
        print(f"Population-dependent supplement outputs skipped: {exc}")
        state_pop_table = pd.DataFrame(columns=["state_name", "population_total"])
        county_pop_table = pd.DataFrame(columns=["county_code", "county_name", "state_name", "county_type", "population_total"])
        _write_population_access_metadata(
            report_dir,
            payload={
                "status": "skipped",
                "reason": population_skip_reason,
                "main_threshold": main_threshold,
                "strict_threshold": strict_threshold,
                "time_bins": time_bins,
                "expected_outputs": [
                    f"tables/isochrone_population_coverage_ge_{main_threshold}.csv",
                    f"tables/isochrone_population_coverage_ge_{strict_threshold}.csv",
                    f"tables/population_tradeoff_ge_{main_threshold}_vs_ge_{strict_threshold}.csv",
                ],
            },
        )
        if require_population:
            raise RuntimeError(
                "Population coverage was required, but the GHS-POP raster is missing. "
                f"{population_skip_reason}"
            ) from exc

    state_frame = _read_states().merge(state_pop_table, on="state_name", how="left")
    county_frame = _normalize_county_code_frame(_read_counties()).merge(
        county_pop_table,
        on=["county_code", "county_name", "state_name", "county_type"],
        how="left",
    )
    county_frame["population_total"] = pd.to_numeric(county_frame["population_total"], errors="coerce").fillna(0).astype(int)
    state_frame["population_total"] = pd.to_numeric(state_frame["population_total"], errors="coerce").fillna(0).astype(int)

    state_provider_rates = _load_or_build_csv(
        tables_dir / "latest_year_state_provider_rates.csv",
        lambda: build_region_provider_summary(
            all_centers,
            state_frame,
            case_col=case_col,
            thresholds=thresholds,
            join_cols=["state_name"],
        ),
        expected_thresholds=thresholds,
    )
    county_provider_rates = _normalize_county_code_frame(_load_or_build_csv(
        tables_dir / "latest_year_county_provider_rates.csv",
        lambda: build_region_provider_summary(
            all_centers,
            county_frame,
            case_col=case_col,
            thresholds=thresholds,
            join_cols=["county_code", "county_name", "state_name"],
        ),
        expected_thresholds=thresholds,
    ))

    population_coverage_lookup: dict[int, pd.DataFrame] = {}

    if population_supported and (geo_dir / f"isochrones_ge_{main_threshold}_unions.geojson").exists():
        germany_pop_total = germany_population_total()
        pop_cov_main = summarize_union_population_coverage(
            gpd.read_file(geo_dir / f"isochrones_ge_{main_threshold}_unions.geojson"),
            denominator_population=germany_pop_total,
        )
        pop_cov_strict = summarize_union_population_coverage(
            gpd.read_file(geo_dir / f"isochrones_ge_{strict_threshold}_unions.geojson"),
            denominator_population=germany_pop_total,
        )
        pop_tradeoff = build_population_tradeoff(
            pop_cov_main,
            pop_cov_strict,
            main_threshold=main_threshold,
            strict_threshold=strict_threshold,
        )
        state_rates = build_state_population_rates(state_summary, state_pop_table)

        pop_cov_main.to_csv(tables_dir / f"isochrone_population_coverage_ge_{main_threshold}.csv", index=False)
        pop_cov_strict.to_csv(tables_dir / f"isochrone_population_coverage_ge_{strict_threshold}.csv", index=False)
        pop_tradeoff.to_csv(
            tables_dir / f"population_tradeoff_ge_{main_threshold}_vs_ge_{strict_threshold}.csv",
            index=False,
        )
        state_rates.to_csv(tables_dir / "latest_year_state_population_rates.csv", index=False)
        population_coverage_lookup = {
            main_threshold: pop_cov_main,
            strict_threshold: pop_cov_strict,
        }
        _write_population_access_metadata(
            report_dir,
            payload={
                "status": "complete",
                **(population_metadata or {}),
                "denominator_source": "GHS-POP raster cells within Germany boundary",
                "population_total": int(germany_pop_total),
                "main_threshold": main_threshold,
                "strict_threshold": strict_threshold,
                "time_bins": time_bins,
                "outputs": [
                    f"tables/isochrone_population_coverage_ge_{main_threshold}.csv",
                    f"tables/isochrone_population_coverage_ge_{strict_threshold}.csv",
                    f"tables/population_tradeoff_ge_{main_threshold}_vs_ge_{strict_threshold}.csv",
                ],
            },
        )

        state_coverage_main = _load_or_build_csv(
            tables_dir / f"state_population_coverage_ge_{main_threshold}.csv",
            lambda: summarize_regional_population_coverage(
                gpd.read_file(geo_dir / f"isochrones_ge_{main_threshold}_unions.geojson"),
                state_frame,
                region_cols=["state_name"],
            ),
        )
        state_coverage_strict = _load_or_build_csv(
            tables_dir / f"state_population_coverage_ge_{strict_threshold}.csv",
            lambda: summarize_regional_population_coverage(
                gpd.read_file(geo_dir / f"isochrones_ge_{strict_threshold}_unions.geojson"),
                state_frame,
                region_cols=["state_name"],
            ),
        )
        county_coverage_main = _normalize_county_code_frame(_load_or_build_csv(
            tables_dir / f"county_population_coverage_ge_{main_threshold}.csv",
            lambda: summarize_regional_population_coverage(
                gpd.read_file(geo_dir / f"isochrones_ge_{main_threshold}_unions.geojson"),
                county_frame,
                region_cols=["county_code", "county_name", "state_name", "county_type", "urban_rural"],
            ),
        ))
        county_coverage_strict = _normalize_county_code_frame(_load_or_build_csv(
            tables_dir / f"county_population_coverage_ge_{strict_threshold}.csv",
            lambda: summarize_regional_population_coverage(
                gpd.read_file(geo_dir / f"isochrones_ge_{strict_threshold}_unions.geojson"),
                county_frame,
                region_cols=["county_code", "county_name", "state_name", "county_type", "urban_rural"],
            ),
        ))

        county_counts = county_frame.groupby("state_name", dropna=False).size().rename("county_count").reset_index()
        state_context = _load_or_build_csv(
            tables_dir / "state_access_context.csv",
            lambda: build_regional_access_context(
                state_frame.merge(county_counts, on="state_name", how="left"),
                state_provider_rates,
                {
                    main_threshold: state_coverage_main,
                    strict_threshold: state_coverage_strict,
                },
                {
                    main_threshold: pop_cov_main,
                    strict_threshold: pop_cov_strict,
                },
                join_cols=["state_name"],
            ),
            required_columns=[
                f"coverage_ge_{main_threshold}_{time_bins[0]}m_pct",
                f"coverage_ge_{strict_threshold}_{time_bins[0]}m_pct",
            ],
        )
        county_context = _normalize_county_code_frame(_load_or_build_csv(
            tables_dir / "county_access_context.csv",
            lambda: build_regional_access_context(
                county_frame,
                county_provider_rates,
                {
                    main_threshold: county_coverage_main,
                    strict_threshold: county_coverage_strict,
                },
                {
                    main_threshold: pop_cov_main,
                    strict_threshold: pop_cov_strict,
                },
                join_cols=["county_code", "county_name", "state_name"],
            ),
            required_columns=[
                f"coverage_ge_{main_threshold}_{time_bins[0]}m_pct",
                f"coverage_ge_{strict_threshold}_{time_bins[0]}m_pct",
            ],
        ))

        plot_population_coverage(
            pop_cov_main,
            pop_cov_strict,
            figures_dir / f"15_population_coverage_ge_{main_threshold}_vs_ge_{strict_threshold}.png",
            main_threshold=main_threshold,
            strict_threshold=strict_threshold,
        )
        plot_state_population_rates(
            state_rates,
            figures_dir / "16_state_case_rates_per_million.png",
            threshold=1,
        )
        plot_state_county_access_context(
            state_context,
            county_context,
            figures_dir / "18_state_county_access_context.png",
            main_threshold=main_threshold,
            strict_threshold=strict_threshold,
        )
        plot_county_access_multipanel(
            county_frame,
            county_coverage_main,
            county_coverage_strict,
            figures_dir / "19_county_population_coverage_multipanel.png",
            main_threshold=main_threshold,
            strict_threshold=strict_threshold,
        )

    threshold_meta = {int(row["threshold"]): row for row in summary.get("threshold_summary", [])}
    panels: list[dict[str, Any]] = []
    selected_times = time_bins[:1] if len(time_bins) == 1 else [time_bins[0], time_bins[-1]]
    for threshold in [main_threshold, strict_threshold]:
        union_path = geo_dir / f"isochrones_ge_{threshold}_unions.geojson"
        centers_path = tables_dir / f"latest_year_centers_ge_{threshold}.csv"
        if not union_path.exists() or not centers_path.exists():
            continue
        union_full = gpd.read_file(union_path).to_crs("EPSG:4326")
        centers_df = pd.read_csv(centers_path)
        threshold_row = threshold_meta.get(threshold, {})
        pop_lookup = {
            int(row["time_minutes"]): float(row["pct_population_covered"])
            for _, row in population_coverage_lookup.get(threshold, pd.DataFrame()).iterrows()
        }
        for time_minutes in selected_times:
            union_subset = union_full.loc[union_full["time_minutes"] == time_minutes].copy()
            if union_subset.empty:
                continue
            coverage_pct = pop_lookup.get(int(time_minutes), 0.0)
            title = (
                f">= {threshold} cases, {int(time_minutes)} min\n"
                f"{int(threshold_row.get('hospitals', 0))} centers, {coverage_pct:.1f}% population coverage"
            )
            panels.append(
                {
                    "threshold": threshold,
                    "title": title,
                    "union_gdf": union_subset,
                    "centers_df": centers_df,
                }
            )

    if panels:
        plot_isochrone_threshold_multipanel(
            panels[:4],
            figures_dir / "17_isochrone_multipanel_thresholds.png",
            case_col=case_col,
        )

    concentration.to_csv(tables_dir / "yearly_concentration_summary.csv", index=False)
    ik_year.to_csv(tables_dir / "ik_year.csv", index=False)
    top_ik.to_csv(tables_dir / "top_ik_all_years.csv", index=False)
    churn.to_csv(tables_dir / "threshold_churn_by_ik.csv", index=False)
    coverage_tradeoff.to_csv(
        tables_dir / f"coverage_tradeoff_ge_{main_threshold}_vs_ge_{strict_threshold}.csv",
        index=False,
    )

    plot_concentration_trends(concentration, figures_dir / "11_concentration_trends.png")
    plot_threshold_churn(churn, figures_dir / "12_threshold_churn_by_ik.png")
    plot_coverage_tradeoff(
        coverage_tradeoff,
        figures_dir / f"13_coverage_tradeoff_ge_{main_threshold}_vs_ge_{strict_threshold}.png",
        main_threshold=main_threshold,
        strict_threshold=strict_threshold,
    )
    plot_top_ik_all_years(top_ik, figures_dir / "14_top_ik_all_years.png")
    _write_figure_strategy(
        figures_dir,
        main_threshold=main_threshold,
        strict_threshold=strict_threshold,
    )

    return {
        "report_dir": str(report_dir),
        "tables_dir": str(tables_dir),
        "figures_dir": str(figures_dir),
    }


__all__ = ["build_indication_supplement"]
