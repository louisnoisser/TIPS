#!/usr/bin/env python3
"""Route and summarize the fully validated 2024 ≥100 TIPS network."""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
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


OUT = ROOT / "outputs/geography_validation_ge100_2026-07-24"
MASTER = OUT / "provider_locations_master_2024.csv"
TIME_BINS = [30, 60]
POP_RASTER = ROOT / "spatial/GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif"
SMOD_RASTER = ROOT / "spatial/GHS_SMOD_E2025_GLOBE_R2023A_54009_1000_V2_0.tif"
PREVIOUS = (
    ROOT / "outputs/indications/tips_8-839-8_updated2024/tables/"
    "isochrone_population_coverage_ge_100.csv"
)


def markdown_table(frame: pd.DataFrame) -> str:
    clean = frame.fillna("").astype(str).apply(
        lambda column: column.str.replace("|", r"\|", regex=False)
    )
    return "\n".join([
        "| " + " | ".join(clean.columns) + " |",
        "| " + " | ".join("---" for _ in clean.columns) + " |",
        *["| " + " | ".join(row) + " |" for row in clean.itertuples(index=False, name=None)],
    ])


def population_by_class(
    unions: dict[int, object],
) -> tuple[dict[str, int], dict[int, dict[str, int]]]:
    """Independently sum GHS-POP inside Germany and each coverage union."""
    germany = gpd.read_file(config.GERMANY_OUTLINE).to_crs("EPSG:4326").geometry.union_all()
    clipped = {minutes: geometry.intersection(germany) for minutes, geometry in unions.items()}
    totals = {"total": 0.0, "urban": 0.0, "rural": 0.0, "other": 0.0}
    covered = {
        minutes: {"total": 0.0, "urban": 0.0, "rural": 0.0, "other": 0.0}
        for minutes in TIME_BINS
    }

    with rasterio.open(POP_RASTER) as pop, rasterio.open(SMOD_RASTER) as smod:
        bounds = gpd.GeoSeries([germany], crs="EPSG:4326").to_crs(pop.crs).total_bounds
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
                    [mapping(germany)], out_shape=values.shape, transform=transform,
                    invert=True, all_touched=False,
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
                class_masks["other"] = ~(class_masks["urban"] | class_masks["rural"])
                totals["total"] += float(values[inside].sum())
                for label, class_mask in class_masks.items():
                    totals[label] += float(values[inside & class_mask].sum())
                for minutes, geometry in clipped.items():
                    access = inside & geometry_mask(
                        [mapping(geometry)], out_shape=values.shape, transform=transform,
                        invert=True, all_touched=False,
                    )
                    covered[minutes]["total"] += float(values[access].sum())
                    for label, class_mask in class_masks.items():
                        covered[minutes][label] += float(values[access & class_mask].sum())

    return (
        {key: int(round(value)) for key, value in totals.items()},
        {
            minutes: {key: int(round(value)) for key, value in values.items()}
            for minutes, values in covered.items()
        },
    )


def write_figure(sites: pd.DataFrame, unions: dict[int, object]) -> list[Path]:
    figures = OUT / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    germany = gpd.read_file(config.GERMANY_OUTLINE).to_crs("EPSG:4326")
    points = gpd.GeoDataFrame(
        sites.copy(),
        geometry=gpd.points_from_xy(sites.longitude, sites.latitude),
        crs="EPSG:4326",
    )
    fig, ax = plt.subplots(figsize=(9.2, 10.5))
    germany.plot(ax=ax, color="#f6f6f3", edgecolor="#666666", linewidth=0.65, zorder=1)
    gpd.GeoSeries([unions[60]], crs="EPSG:4326").plot(
        ax=ax, color="#9ecae1", edgecolor="#3182bd", alpha=0.42, linewidth=0.8, zorder=2,
    )
    gpd.GeoSeries([unions[30]], crs="EPSG:4326").plot(
        ax=ax, color="#3182bd", edgecolor="#08519c", alpha=0.45, linewidth=0.9, zorder=3,
    )
    activity = sites.visible_activity.astype(float)
    sizes = 45 + 220 * (activity - activity.min()) / max(1, activity.max() - activity.min())
    points.plot(
        ax=ax, color="#7f0000", edgecolor="white", linewidth=0.8,
        markersize=sizes, alpha=0.9, zorder=4,
    )
    for row in points.nlargest(6, "visible_activity").itertuples(index=False):
        label = str(row.provider_name).replace("Universitätsklinikum", "UK ").replace(
            "Universitätsmedizin", "UM "
        )
        ax.annotate(
            label, (row.longitude, row.latitude), xytext=(5, 5),
            textcoords="offset points", fontsize=8.5, weight="semibold", zorder=5,
        )
    legend_values = [100, 200, 300]
    legend_handles = [
        ax.scatter([], [], s=45 + 220 * (value - activity.min()) / max(1, activity.max() - activity.min()),
                   color="#7f0000", edgecolor="white", linewidth=0.8, label=f"{value} cases")
        for value in legend_values
    ]
    ax.legend(
        handles=legend_handles, title="2024 site activity", loc="lower left",
        frameon=True, fontsize=9, title_fontsize=9.5,
    )
    ax.set_title(
        "Validated 2024 TIPS ≥100-site network (16 physical sites)\n"
        "Driving-time coverage: 30 minutes (dark) and 60 minutes (light)",
        fontsize=13, weight="bold",
    )
    ax.set_axis_off()
    fig.tight_layout()
    paths = [
        figures / "ge100_validated_accessibility.png",
        figures / "ge100_validated_accessibility.pdf",
        figures / "ge100_validated_accessibility.svg",
    ]
    for path in paths:
        fig.savefig(path, dpi=300 if path.suffix == ".png" else None, bbox_inches="tight")
    plt.close(fig)
    return paths


def main() -> None:
    sites = pd.read_csv(MASTER, dtype={"ik": str, "site_id": str})
    sites = sites[sites.threshold_ge100].sort_values(
        ["visible_activity", "site_id"], ascending=[False, True]
    ).reset_index(drop=True)
    if len(sites) != 16:
        raise SystemExit(f"Expected 16 ≥100 sites, found {len(sites)}")
    required = (
        sites.address_validation_status.eq("validated site-specific address")
        & sites.federal_state_status.str.startswith("validated")
        & sites.coordinate_status.eq("validated physical-site coordinate")
    )
    if not required.all():
        bad = sites.loc[~required, ["site_id", "provider_name"]]
        raise SystemExit(f"Release gate failed:\n{bad.to_string(index=False)}")

    polygons = {minutes: [] for minutes in TIME_BINS}
    audit_rows = []
    for row in sites.itertuples(index=False):
        error = ""
        routed = {}
        try:
            site_polygons = request_isochrones(
                float(row.longitude), float(row.latitude), TIME_BINS, max_retries=3
            )
            routed = dict(zip(TIME_BINS, site_polygons, strict=True))
            for minutes, polygon in routed.items():
                if polygon is None or polygon.is_empty:
                    raise RuntimeError(f"empty {minutes}-minute polygon")
                polygons[minutes].append(polygon)
        except Exception as exc:  # recorded per site; final release then stops
            error = f"{type(exc).__name__}: {exc}"
        audit_rows.append({
            "site_id": row.site_id, "provider_name": row.provider_name,
            "visible_activity": int(row.visible_activity), "eligible": True,
            "validated_coordinate": True, "latitude": row.latitude,
            "longitude": row.longitude, "routed_30m": 30 in routed,
            "routed_60m": 60 in routed, "routing_error": error,
        })
    audit = pd.DataFrame(audit_rows)
    audit.to_csv(OUT / "accessibility_ge100_routing_audit.csv", index=False)
    if audit.routing_error.ne("").any() or not (
        audit.routed_30m.all() and audit.routed_60m.all()
    ):
        failures = audit.loc[audit.routing_error.ne(""), ["site_id", "routing_error"]]
        (OUT / "accessibility_ge100_validation_report.md").write_text(
            "# ≥100 accessibility validation\n\nRouting failed; no final result was released.\n\n"
            + markdown_table(failures) + "\n",
            encoding="utf-8",
        )
        raise SystemExit("At least one validated site failed routing")

    unions = {minutes: unary_union(site_polygons) for minutes, site_polygons in polygons.items()}
    union_gdf = gpd.GeoDataFrame(
        [{"time_minutes": minutes, "geometry": unions[minutes]} for minutes in TIME_BINS],
        geometry="geometry", crs="EPSG:4326",
    )
    union_gdf.to_file(OUT / "accessibility_ge100_unions.geojson", driver="GeoJSON")
    feature_rows = []
    for site_index, row in sites.iterrows():
        for minutes in TIME_BINS:
            feature_rows.append({
                "site_id": row.site_id, "provider_name": row.provider_name,
                "visible_activity": int(row.visible_activity), "time_minutes": minutes,
                "geometry": polygons[minutes][site_index],
            })
    gpd.GeoDataFrame(feature_rows, geometry="geometry", crs="EPSG:4326").to_file(
        OUT / "accessibility_ge100_site_isochrones.geojson", driver="GeoJSON"
    )

    totals, covered = population_by_class(unions)
    previous = pd.read_csv(PREVIOUS).set_index("time_minutes")
    final_rows, class_rows = [], []
    for minutes in TIME_BINS:
        population = covered[minutes]["total"]
        pct = 100 * population / totals["total"]
        previous_population = int(previous.at[minutes, "covered_population"])
        previous_pct = float(previous.at[minutes, "pct_population_covered"])
        final_rows.append({
            "threshold": 100, "time_minutes": minutes, "eligible_sites": 16,
            "validated_sites": 16, "successfully_routed_sites": 16,
            "failed_routing_sites": 0, "covered_population": population,
            "germany_population_denominator": totals["total"],
            "pct_population_covered": round(pct, 2),
            "previous_covered_population": previous_population,
            "difference_from_previous_population": population - previous_population,
            "previous_pct_population_covered": previous_pct,
            "difference_from_previous_percentage_points": round(pct - previous_pct, 2),
            "final_validation_status": "released",
        })
        for label in ("urban", "rural", "other"):
            class_rows.append({
                "threshold": 100, "time_minutes": minutes, "settlement_class": label,
                "covered_population": covered[minutes][label],
                "class_population_denominator": totals[label],
                "pct_class_population_covered": round(
                    100 * covered[minutes][label] / totals[label], 2
                ) if totals[label] else 0.0,
                "final_validation_status": "released",
            })
    final = pd.DataFrame(final_rows)
    classes = pd.DataFrame(class_rows)
    final.to_csv(OUT / "accessibility_ge100_final.csv", index=False)
    classes.to_csv(OUT / "accessibility_ge100_urban_rural_final.csv", index=False)
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
            if line.startswith(("graph_build_date:", "osm_date:", "graph_version:"))
        },
        "population_raster": str(POP_RASTER.relative_to(ROOT)),
        "settlement_raster": str(SMOD_RASTER.relative_to(ROOT)),
        "population_denominator_reproduced": totals["total"],
        "eligible_sites": 16,
        "successfully_routed_sites": 16,
        "time_bins": TIME_BINS,
        "figures": [str(path.relative_to(OUT)) for path in figure_paths],
    }
    (OUT / "accessibility_ge100_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    report_table = markdown_table(final)
    class_table = markdown_table(classes)
    (OUT / "accessibility_ge100_validation_report.md").write_text(
        "# Validated ≥100 potential geographic accessibility\n\n"
        "All 16 eligible physical sites had validated coordinates and all 16 routed "
        "successfully at both time thresholds. The result is released for the ≥100 "
        "network only.\n\n"
        f"## Total population\n\n{report_table}\n\n"
        f"## Settlement-class population\n\n{class_table}\n\n"
        "The Germany denominator and settlement-class denominators were independently "
        "summed from the local GHS-POP raster within the local Germany boundary. "
        "GHS-SMOD was reprojected with nearest-neighbour classification to the "
        "population grid. No ≥20 or ≥50 accessibility result was generated.\n",
        encoding="utf-8",
    )
    print(final.to_string(index=False))
    print(classes.to_string(index=False))


if __name__ == "__main__":
    main()
