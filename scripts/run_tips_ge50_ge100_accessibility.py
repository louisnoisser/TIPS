#!/usr/bin/env python3
"""Route and summarize the validated 2024 ≥50 and ≥100 TIPS networks."""

from __future__ import annotations

import argparse
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
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import Window
from rasterio.warp import Resampling, reproject
from shapely.geometry import mapping
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gba_ops_reanalysis import config  # noqa: E402
from gba_ops_reanalysis.isochrones import request_isochrones  # noqa: E402
from gba_ops_reanalysis.urban_rural import RURAL_CODES, URBAN_CODES  # noqa: E402


OUT = ROOT / "outputs/geography_validation_ge50_2026-07-24"
MASTER = OUT / "provider_locations_master_2024.csv"
NETWORKS = {50: 31, 100: 16}
TIME_BINS = [30, 60]
POP_RASTER = ROOT / "spatial/GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif"
SMOD_RASTER = ROOT / "spatial/GHS_SMOD_E2025_GLOBE_R2023A_54009_1000_V2_0.tif"
PREVIOUS = {
    threshold: (
        ROOT
        / "outputs/indications/tips_8-839-8_updated2024/tables/"
        f"isochrone_population_coverage_ge_{threshold}.csv"
    )
    for threshold in NETWORKS
}
EXPECTED_GE100 = {30: 16_035_551, 60: 48_597_532}
EXPECTED_GE50 = {30: 25_708_947, 60: 60_465_819}


def markdown_table(frame: pd.DataFrame) -> str:
    clean = frame.fillna("").astype(str).apply(
        lambda column: column.str.replace("|", r"\|", regex=False)
    )
    return "\n".join([
        "| " + " | ".join(clean.columns) + " |",
        "| " + " | ".join("---" for _ in clean.columns) + " |",
        *[
            "| " + " | ".join(row) + " |"
            for row in clean.itertuples(index=False, name=None)
        ],
    ])


def population_by_class(
    unions: dict[tuple[int, int], object],
) -> tuple[dict[str, int], dict[tuple[int, int], dict[str, int]]]:
    """Independently sum GHS-POP inside Germany and each coverage union."""
    germany = (
        gpd.read_file(config.GERMANY_OUTLINE)
        .to_crs("EPSG:4326")
        .geometry.union_all()
    )
    clipped = {
        key: geometry.intersection(germany) for key, geometry in unions.items()
    }
    totals = {"total": 0.0, "urban": 0.0, "rural": 0.0, "other": 0.0}
    covered = {
        key: {"total": 0.0, "urban": 0.0, "rural": 0.0, "other": 0.0}
        for key in clipped
    }

    with rasterio.open(POP_RASTER) as pop, rasterio.open(SMOD_RASTER) as smod:
        bounds = (
            gpd.GeoSeries([germany], crs="EPSG:4326")
            .to_crs(pop.crs)
            .total_bounds
        )
        raw = rasterio.windows.from_bounds(*bounds, transform=pop.transform)
        row_start = max(0, math.floor(raw.row_off))
        col_start = max(0, math.floor(raw.col_off))
        row_stop = min(pop.height, math.ceil(raw.row_off + raw.height))
        col_stop = min(pop.width, math.ceil(raw.col_off + raw.width))
        tile = 1024
        for row_off in range(row_start, row_stop, tile):
            for col_off in range(col_start, col_stop, tile):
                height = min(tile, row_stop - row_off)
                width = min(tile, col_stop - col_off)
                window = Window(col_off, row_off, width, height)
                transform = pop.window_transform(window)
                values = pop.read(1, window=window).astype("float64", copy=False)
                values[~np.isfinite(values)] = 0
                values[values < 0] = 0
                inside = geometry_mask(
                    [mapping(germany)],
                    out_shape=values.shape,
                    transform=transform,
                    invert=True,
                    all_touched=False,
                )
                if not inside.any():
                    continue
                smod_values = np.full(values.shape, -200, dtype="int16")
                reproject(
                    source=rasterio.band(smod, 1),
                    destination=smod_values,
                    src_transform=smod.transform,
                    src_crs=smod.crs,
                    src_nodata=smod.nodata,
                    dst_transform=transform,
                    dst_crs=pop.crs,
                    dst_nodata=-200,
                    resampling=Resampling.nearest,
                )
                class_masks = {
                    "urban": np.isin(smod_values, URBAN_CODES),
                    "rural": np.isin(smod_values, RURAL_CODES),
                }
                class_masks["other"] = ~(
                    class_masks["urban"] | class_masks["rural"]
                )
                totals["total"] += float(values[inside].sum())
                for label, class_mask in class_masks.items():
                    totals[label] += float(values[inside & class_mask].sum())
                for key, geometry in clipped.items():
                    access = inside & geometry_mask(
                        [mapping(geometry)],
                        out_shape=values.shape,
                        transform=transform,
                        invert=True,
                        all_touched=False,
                    )
                    covered[key]["total"] += float(values[access].sum())
                    for label, class_mask in class_masks.items():
                        covered[key][label] += float(
                            values[access & class_mask].sum()
                        )

    return (
        {key: int(round(value)) for key, value in totals.items()},
        {
            key: {
                label: int(round(value)) for label, value in values.items()
            }
            for key, values in covered.items()
        },
    )


def short_name(name: str) -> str:
    replacements = {
        "Universitätsklinikum": "UK ",
        "Universitätsmedizin": "UM ",
        "UNIVERSITÄTSKLINIKUM": "UK ",
        "Charité - Universitätsmedizin Berlin": "Charité Berlin",
        "Medizinische Hochschule Hannover": "MHH",
        "TUM Klinikum Rechts der Isar": "TUM MRI",
        "Cellitinnen-Krankenhaus St. Vinzenz": "St. Vinzenz Köln",
    }
    result = str(name)
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result.split(" - ")[0]


def marker_size(activity: pd.Series | float) -> pd.Series | float:
    return 28 + 190 * (activity - 50) / 256


def write_figure(
    sites: pd.DataFrame,
    unions: dict[tuple[int, int], object],
) -> list[Path]:
    figures = OUT / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    germany = gpd.read_file(config.GERMANY_OUTLINE).to_crs("EPSG:4326")
    bounds = germany.total_bounds
    thresholds = tuple(NETWORKS)
    fig, axes = plt.subplots(
        1, len(thresholds), figsize=(18.0, 7.7), sharex=True, sharey=True
    )
    axes = np.atleast_1d(axes)

    for ax, threshold, panel in zip(
        axes, thresholds, ("A", "B", "C"), strict=True
    ):
        selected = sites[sites[f"threshold_ge{threshold}"]].copy()
        points = gpd.GeoDataFrame(
            selected,
            geometry=gpd.points_from_xy(selected.longitude, selected.latitude),
            crs="EPSG:4326",
        )
        germany.plot(
            ax=ax, color="#f7f7f4", edgecolor="#666666", linewidth=0.6, zorder=1
        )
        gpd.GeoSeries([unions[(threshold, 60)]], crs="EPSG:4326").plot(
            ax=ax,
            color="#9ecae1",
            edgecolor="#6baed6",
            alpha=0.42,
            linewidth=0.7,
            zorder=2,
        )
        gpd.GeoSeries([unions[(threshold, 30)]], crs="EPSG:4326").plot(
            ax=ax,
            color="#3182bd",
            edgecolor="#08519c",
            alpha=0.47,
            linewidth=0.8,
            zorder=3,
        )
        points.plot(
            ax=ax,
            color="#8b0000",
            edgecolor="white",
            linewidth=0.65,
            markersize=marker_size(points.visible_activity.astype(float)),
            alpha=0.9,
            zorder=4,
        )
        for row in points.nlargest(5, "visible_activity").itertuples(index=False):
            ax.annotate(
                short_name(row.provider_name),
                (row.longitude, row.latitude),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=7.5,
                weight="semibold",
                zorder=5,
            )
        ax.set_xlim(bounds[0] - 0.2, bounds[2] + 0.2)
        ax.set_ylim(bounds[1] - 0.15, bounds[3] + 0.15)
        ax.set_axis_off()
        ax.set_title(
            f"{panel}  ≥{threshold} network ({len(selected)} sites)",
            loc="left",
            fontsize=13,
            weight="bold",
        )

    legend_handles = [
        Patch(
            facecolor="#3182bd", edgecolor="#08519c", alpha=0.47,
            label="30-minute drive time",
        ),
        Patch(
            facecolor="#9ecae1", edgecolor="#6baed6", alpha=0.42,
            label="60-minute drive time",
        ),
        *[
            Line2D(
                [], [], marker="o", linestyle="", color="#8b0000",
                markeredgecolor="white",
                markersize=math.sqrt(float(marker_size(value))),
                label=f"{value} occurrences",
            )
            for value in (20, 100, 300)
        ],
    ]
    fig.legend(
        handles=legend_handles,
        loc="lower center",
        ncol=5,
        frameon=True,
        bbox_to_anchor=(0.5, 0.015),
        fontsize=9,
    )
    fig.subplots_adjust(left=0.02, right=0.98, top=0.96, bottom=0.09, wspace=0.02)
    paths = [
        figures / "Figure4_validated_geographic_accessibility.png",
        figures / "Figure4_validated_geographic_accessibility.pdf",
        figures / "Figure4_validated_geographic_accessibility.svg",
    ]
    for path in paths:
        fig.savefig(
            path,
            dpi=300 if path.suffix == ".png" else None,
            bbox_inches="tight",
        )
    plt.close(fig)
    return paths


def write_state_outputs(master: pd.DataFrame) -> pd.DataFrame:
    state_names = sorted(
        gpd.read_file(ROOT / "spatial/germany-states.geojson")["NAME_1"].unique()
    )
    national_visible = int(master.visible_activity.sum())
    rows = []
    for threshold in (20, 50, 100, 200):
        selected = master[master[f"threshold_ge{threshold}"]].copy()
        network_visible = int(selected.visible_activity.sum())
        for state in state_names:
            group = selected[selected.federal_state == state].sort_values(
                ["visible_activity", "site_id"], ascending=[False, True]
            )
            activity = int(group.visible_activity.sum())
            category_counts = group.exclusive_volume_category.value_counts()
            rows.append({
                "threshold": threshold,
                "federal_state": state,
                "provider_count": len(group),
                "visible_activity": activity,
                "national_visible_activity": national_visible,
                "share_of_national_visible_activity_pct": round(
                    100 * activity / national_visible, 2
                ),
                "network_visible_activity": network_visible,
                "share_of_network_visible_activity_pct": round(
                    100 * activity / network_visible, 2
                ),
                "provider_identifiers": "|".join(group.site_id),
                "exclusive_volume_categories": "|".join(
                    f"{row.site_id}:{row.exclusive_volume_category}"
                    for row in group.itertuples(index=False)
                ),
                "providers_4_19": int(category_counts.get("4–19", 0)),
                "providers_20_49": int(category_counts.get("20–49", 0)),
                "providers_50_99": int(category_counts.get("50–99", 0)),
                "providers_100_199": int(category_counts.get("100–199", 0)),
                "providers_ge200": int(category_counts.get("≥200", 0)),
                "interpretation": (
                    "Qualifying provider sites observed."
                    if len(group)
                    else "No site met this study threshold; this does not imply absence of TIPS care."
                ),
            })
    result = pd.DataFrame(rows)
    result.to_csv(
        OUT / "federal_state_distribution_2024.csv", index=False
    )
    nonzero = result[result.provider_count > 0]
    (OUT / "federal_state_validation_report.md").write_text(
        "# Validated federal-state distribution for threshold networks\n\n"
        "All included sites have validated physical addresses and state assignments. "
        "States with zero qualifying sites are retained in the CSV and are described "
        "only as having no site meeting the study threshold; this must not be "
        "interpreted as absence of TIPS care.\n\n"
        + markdown_table(nonzero)
        + "\n",
        encoding="utf-8",
    )
    return result


def write_table_s5(final: pd.DataFrame, classes: pd.DataFrame) -> pd.DataFrame:
    wide = classes.pivot(
        index=["threshold", "time_minutes"],
        columns="settlement_class",
        values=["covered_population", "pct_class_population_covered"],
    )
    wide.columns = [
        f"{measure}_{settlement}" for measure, settlement in wide.columns
    ]
    wide = wide.reset_index()
    table = final.merge(wide, on=["threshold", "time_minutes"], validate="one_to_one")
    columns = [
        "threshold", "time_minutes", "eligible_sites", "validated_sites",
        "successfully_routed_sites", "failed_routing_sites",
        "covered_population", "germany_population_denominator",
        "pct_population_covered",
        "covered_population_urban", "pct_class_population_covered_urban",
        "covered_population_rural", "pct_class_population_covered_rural",
        "covered_population_other", "pct_class_population_covered_other",
        "final_validation_status",
    ]
    table = table[columns].sort_values(["threshold", "time_minutes"])
    tables = OUT / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    table.to_csv(tables / "TableS5_potential_geographic_accessibility.csv", index=False)
    return table


def main() -> None:
    global OUT, MASTER, NETWORKS, PREVIOUS
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUT)
    parser.add_argument("--master", type=Path, default=MASTER)
    parser.add_argument("--include-ge20", action="store_true")
    args = parser.parse_args()
    OUT = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    MASTER = args.master if args.master.is_absolute() else ROOT / args.master
    if args.include_ge20:
        NETWORKS = {20: 60, 50: 31, 100: 16}
    PREVIOUS = {
        threshold: (
            ROOT
            / "outputs/indications/tips_8-839-8_updated2024/tables/"
            f"isochrone_population_coverage_ge_{threshold}.csv"
        )
        for threshold in NETWORKS
    }
    OUT.mkdir(parents=True, exist_ok=True)
    master = pd.read_csv(
        MASTER, dtype={"ik": str, "site_id": str, "postcode": str}
    )
    minimum_threshold = min(NETWORKS)
    sites = master[master[f"threshold_ge{minimum_threshold}"]].sort_values(
        ["visible_activity", "site_id"], ascending=[False, True]
    ).reset_index(drop=True)
    for threshold, expected in NETWORKS.items():
        selected = sites[sites[f"threshold_ge{threshold}"]]
        if len(selected) != expected:
            raise SystemExit(
                f"Expected {expected} ≥{threshold} sites, found {len(selected)}"
            )
        valid = (
            selected.address_validation_status.eq(
                "validated site-specific address"
            )
            & selected.federal_state_status.str.startswith("validated")
            & selected.coordinate_status.eq(
                "validated physical-site coordinate"
            )
        )
        if not valid.all():
            raise SystemExit(f"Release gate failed for ≥{threshold}")

    routed: dict[str, dict[int, object]] = {}
    audit_rows = []
    for row in sites.itertuples(index=False):
        error = ""
        site_polygons: dict[int, object] = {}
        try:
            responses = request_isochrones(
                float(row.longitude),
                float(row.latitude),
                TIME_BINS,
                max_retries=3,
            )
            site_polygons = dict(zip(TIME_BINS, responses, strict=True))
            for minutes, polygon in site_polygons.items():
                if polygon is None or polygon.is_empty:
                    raise RuntimeError(f"empty {minutes}-minute polygon")
            routed[row.site_id] = site_polygons
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        audit_rows.append({
            "site_id": row.site_id,
            "provider_name": row.provider_name,
            "visible_activity": int(row.visible_activity),
            **{
                f"member_ge{threshold}": bool(
                    getattr(row, f"threshold_ge{threshold}")
                )
                for threshold in NETWORKS
            },
            "validated_coordinate": True,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "routed_30m": 30 in site_polygons,
            "routed_60m": 60 in site_polygons,
            "routing_error": error,
        })
    audit = pd.DataFrame(audit_rows)
    audit.to_csv(
        OUT / "accessibility_routing_audit.csv", index=False
    )
    if (
        audit.routing_error.ne("").any()
        or not audit.routed_30m.all()
        or not audit.routed_60m.all()
    ):
        raise SystemExit("At least one validated site failed routing")

    unions = {}
    for threshold in NETWORKS:
        selected_ids = set(
            sites.loc[sites[f"threshold_ge{threshold}"], "site_id"]
        )
        for minutes in TIME_BINS:
            unions[(threshold, minutes)] = unary_union(
                [routed[site_id][minutes] for site_id in selected_ids]
            )
    gpd.GeoDataFrame(
        [
            {
                "threshold": threshold,
                "time_minutes": minutes,
                "geometry": geometry,
            }
            for (threshold, minutes), geometry in unions.items()
        ],
        geometry="geometry",
        crs="EPSG:4326",
    ).to_file(
        OUT / "accessibility_unions.geojson", driver="GeoJSON"
    )
    feature_rows = []
    for row in sites.itertuples(index=False):
        for minutes in TIME_BINS:
            feature_rows.append({
                "site_id": row.site_id,
                "provider_name": row.provider_name,
                "visible_activity": int(row.visible_activity),
                **{
                    f"member_ge{threshold}": bool(
                        getattr(row, f"threshold_ge{threshold}")
                    )
                    for threshold in NETWORKS
                },
                "time_minutes": minutes,
                "geometry": routed[row.site_id][minutes],
            })
    gpd.GeoDataFrame(
        feature_rows, geometry="geometry", crs="EPSG:4326"
    ).to_file(
        OUT / "accessibility_site_isochrones.geojson",
        driver="GeoJSON",
    )

    totals, covered = population_by_class(unions)
    final_rows, class_rows = [], []
    for threshold, expected in NETWORKS.items():
        previous = (
            pd.read_csv(PREVIOUS[threshold]).set_index("time_minutes")
            if PREVIOUS[threshold].exists()
            else None
        )
        for minutes in TIME_BINS:
            population = covered[(threshold, minutes)]["total"]
            pct = 100 * population / totals["total"]
            previous_population = (
                int(previous.at[minutes, "covered_population"])
                if previous is not None else pd.NA
            )
            previous_pct = (
                float(previous.at[minutes, "pct_population_covered"])
                if previous is not None else pd.NA
            )
            final_rows.append({
                "threshold": threshold,
                "time_minutes": minutes,
                "eligible_sites": expected,
                "validated_sites": expected,
                "successfully_routed_sites": expected,
                "failed_routing_sites": 0,
                "covered_population": population,
                "germany_population_denominator": totals["total"],
                "pct_population_covered": round(pct, 2),
                "previous_covered_population": previous_population,
                "difference_from_previous_population": (
                    population - previous_population
                    if previous is not None else pd.NA
                ),
                "previous_pct_population_covered": previous_pct,
                "difference_from_previous_percentage_points": (
                    round(pct - previous_pct, 2)
                    if previous is not None else pd.NA
                ),
                "final_validation_status": "released",
            })
            for label in ("urban", "rural", "other"):
                class_rows.append({
                    "threshold": threshold,
                    "time_minutes": minutes,
                    "settlement_class": label,
                    "covered_population": covered[(threshold, minutes)][label],
                    "class_population_denominator": totals[label],
                    "pct_class_population_covered": round(
                        100
                        * covered[(threshold, minutes)][label]
                        / totals[label],
                        2,
                    )
                    if totals[label]
                    else 0.0,
                    "final_validation_status": "released",
                })
    final = pd.DataFrame(final_rows).sort_values(
        ["threshold", "time_minutes"]
    )
    classes = pd.DataFrame(class_rows).sort_values(
        ["threshold", "time_minutes", "settlement_class"]
    )
    for threshold, expected_values in (
        (50, EXPECTED_GE50), (100, EXPECTED_GE100)
    ):
        if threshold not in NETWORKS:
            continue
        reproduced = final[final.threshold == threshold].set_index("time_minutes")
        for minutes, expected_population in expected_values.items():
            observed = int(reproduced.at[minutes, "covered_population"])
            if observed != expected_population:
                raise SystemExit(
                    f"≥{threshold} reproduction failed at {minutes} minutes: "
                    f"expected {expected_population}, observed {observed}"
                )
    if totals["total"] != 83_194_667:
        raise SystemExit(
            f"Population denominator mismatch: {totals['total']}"
        )

    final.to_csv(
        OUT / "accessibility_final.csv", index=False
    )
    classes.to_csv(
        OUT / "accessibility_urban_rural_final.csv", index=False
    )
    state_table = write_state_outputs(master)
    table_s5 = write_table_s5(final, classes)
    figure_paths = write_figure(sites, unions)
    graph_info = (
        ROOT / "ors-docker/graphs/driving-car/graph_build_info.yml"
    ).read_text(encoding="utf-8").splitlines()
    metadata = {
        "routing_engine": "OpenRouteService local Docker",
        "profile": config.ORS_PROFILE,
        "graph_metadata": {
            line.split(":", 1)[0]: line.split(":", 1)[1].strip()
            for line in graph_info
            if line.startswith(
                ("graph_build_date:", "osm_date:", "graph_version:")
            )
        },
        "population_raster": str(POP_RASTER.relative_to(ROOT)),
        "settlement_raster": str(SMOD_RASTER.relative_to(ROOT)),
        "population_denominator_reproduced": totals["total"],
        "networks": NETWORKS,
        "successfully_routed_unique_sites": len(sites),
        "time_bins": TIME_BINS,
        "ge50_expected_population": EXPECTED_GE50,
        "ge100_expected_population": EXPECTED_GE100,
        "figures": [
            str(path.relative_to(OUT)) for path in figure_paths
        ],
        "state_rows": len(state_table),
        "table_s5_rows": len(table_s5),
    }
    (
        OUT / "accessibility_metadata.json"
    ).write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (
        OUT / "accessibility_validation_report.md"
    ).write_text(
        "# Validated potential geographic accessibility\n\n"
        f"All {len(sites)} unique validated sites routed successfully at both "
        "time thresholds. The unchanged 31-site ≥50 and 16-site ≥100 subsets "
        "independently reproduced the released population values exactly.\n\n"
        f"## Total population\n\n{markdown_table(final)}\n\n"
        f"## Settlement class\n\n{markdown_table(classes)}\n\n"
        "The Germany and settlement-class denominators were independently summed "
        "from local GHS-POP/GHS-SMOD rasters using the local Germany boundary.\n",
        encoding="utf-8",
    )
    print(final.to_string(index=False))
    print(classes.to_string(index=False))


if __name__ == "__main__":
    main()
