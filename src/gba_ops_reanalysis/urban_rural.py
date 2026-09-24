"""Urban-rural classification helpers for center points and coverage unions."""

from __future__ import annotations

import numpy as np
import geopandas as gpd
import pandas as pd
import rasterio
from shapely.geometry import Point

from . import config

URBAN_CODES = [30, 23, 22, 21]
RURAL_CODES = [13, 12, 11]


def _label_smod(values: np.ndarray) -> np.ndarray:
    return np.where(
        np.isin(values, URBAN_CODES),
        "urban",
        np.where(np.isin(values, RURAL_CODES), "rural", "other"),
    )


def add_smod_labels(
    gdf: gpd.GeoDataFrame,
    *,
    raster_path: str | None = None,
) -> gpd.GeoDataFrame:
    raster = raster_path or str(config.DEFAULT_SMOD_RASTER)
    with rasterio.open(raster) as src:
        original_crs = gdf.crs
        sample_gdf = gdf.to_crs(src.crs) if gdf.crs != src.crs else gdf
        coords = [(geom.x, geom.y) for geom in sample_gdf.geometry]
        smod_values = np.array([value[0] for value in src.sample(coords)], dtype="int16")

    result = gdf.copy()
    result["smod_code"] = smod_values
    result["urban_rural"] = _label_smod(smod_values)
    if original_crs is not None and result.crs != original_crs:
        result = result.to_crs(original_crs)
    return result


def classify_points(
    df: pd.DataFrame,
    *,
    lon_col: str = "longitude",
    lat_col: str = "latitude",
    raster_path: str | None = None,
) -> gpd.GeoDataFrame:
    work = df.dropna(subset=[lon_col, lat_col]).copy()
    gdf = gpd.GeoDataFrame(
        work,
        geometry=gpd.points_from_xy(work[lon_col], work[lat_col]),
        crs="EPSG:4326",
    )
    return add_smod_labels(gdf, raster_path=raster_path)


def summarize_point_classes(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    summary = (
        gdf.groupby("urban_rural")
        .size()
        .rename("count")
        .reset_index()
        .sort_values("count", ascending=False)
        .reset_index(drop=True)
    )
    summary["pct"] = (summary["count"] / summary["count"].sum() * 100).round(2)
    return summary


def build_germany_grid(grid_resolution: float = 0.05) -> gpd.GeoDataFrame:
    outline = gpd.read_file(config.GERMANY_OUTLINE).to_crs("EPSG:4326")
    geometry = outline.unary_union
    minx, miny, maxx, maxy = outline.total_bounds
    xs = np.arange(minx, maxx + grid_resolution, grid_resolution)
    ys = np.arange(miny, maxy + grid_resolution, grid_resolution)
    points = [Point(float(x), float(y)) for x in xs for y in ys]
    inside = [point for point in points if geometry.contains(point) or geometry.touches(point)]
    return gpd.GeoDataFrame({"geometry": inside}, crs="EPSG:4326")


def summarize_union_coverage(
    union_gdf: gpd.GeoDataFrame,
    *,
    raster_path: str | None = None,
    grid_resolution: float = 0.05,
) -> pd.DataFrame:
    grid = build_germany_grid(grid_resolution=grid_resolution)
    labeled_grid = add_smod_labels(grid, raster_path=raster_path)

    rows: list[dict[str, object]] = []
    totals_by_class = labeled_grid.groupby("urban_rural").size().to_dict()
    total_points = int(len(labeled_grid))

    for record in union_gdf.itertuples(index=False):
        covered = labeled_grid.intersects(record.geometry)
        subset = labeled_grid.loc[covered].copy()
        covered_counts = subset.groupby("urban_rural").size().to_dict()
        covered_total = int(covered.sum())
        for urban_rural, class_total in totals_by_class.items():
            count = int(covered_counts.get(urban_rural, 0))
            rows.append(
                {
                    "time_minutes": getattr(record, "time_minutes", None),
                    "urban_rural": urban_rural,
                    "covered_points": count,
                    "class_points_total": int(class_total),
                    "pct_of_class_covered": round(100 * count / class_total, 2) if class_total else 0.0,
                    "pct_of_all_covered_points": round(100 * count / covered_total, 2) if covered_total else 0.0,
                    "covered_points_total": covered_total,
                    "all_grid_points_total": total_points,
                }
            )
    return pd.DataFrame(rows).sort_values(["time_minutes", "urban_rural"]).reset_index(drop=True)

