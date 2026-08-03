"""Population coverage helpers based on the GeoStroke raster workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import rasterio.mask
from rasterio.io import DatasetReader
from shapely.geometry import MultiPolygon, Polygon, mapping

from . import config

Geometry = Polygon | MultiPolygon


def population_raster_path(raster_path: Path | str | None = None) -> Path:
    path = Path(raster_path or config.DEFAULT_POP_RASTER)
    if not path.exists():
        raise FileNotFoundError(
            f"Population raster not found: {path}. "
            "Set GBA_OPS_POP_RASTER to a valid GHS population raster."
        )
    return path


def _safe_mask(src: DatasetReader, geom: Geometry) -> np.ndarray:
    try:
        out_image, _ = rasterio.mask.mask(src, [mapping(geom)], crop=True)
    except Exception:
        out_image, _ = rasterio.mask.mask(src, geom, crop=True)  # type: ignore[arg-type]

    arr = out_image[0].astype("float64", copy=False)
    if src.nodata is not None:
        arr[arr == src.nodata] = 0
    arr[~np.isfinite(arr)] = 0
    arr[arr < 0] = 0
    return arr


def _population_within_src(src: DatasetReader, geom: Geometry) -> int:
    if geom is None or geom.is_empty:
        return 0
    geom_for_mask = geom
    if src.crs and str(src.crs) != "EPSG:4326":
        geom_for_mask = gpd.GeoSeries([geom], crs="EPSG:4326").to_crs(src.crs).iloc[0]
    arr = _safe_mask(src, geom_for_mask)  # type: ignore[arg-type]
    return int(round(float(arr.sum())))


def population_within(geom: Geometry, raster_path: Path | str | None = None) -> int:
    if geom is None or geom.is_empty:
        return 0
    path = population_raster_path(raster_path)
    with rasterio.open(path) as src:
        return _population_within_src(src, geom)


def _cache_json_path(name: str) -> Path:
    return config.POPULATION_CACHE_DIR / f"{name}.json"


def _cache_csv_path(name: str) -> Path:
    return config.POPULATION_CACHE_DIR / f"{name}.csv"


def _clean_geo_value(value: Any) -> str:
    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return text.strip().strip("'\"")


def region_population_table(
    regions_gdf: gpd.GeoDataFrame,
    *,
    region_cols: list[str],
    cache_name: str,
    raster_path: Path | str | None = None,
) -> pd.DataFrame:
    path = population_raster_path(raster_path)
    cache_key = f"{cache_name}_{path.name}".replace(".", "_")
    cache_path = _cache_csv_path(cache_key)
    if cache_path.exists():
        cached = pd.read_csv(cache_path, dtype={column: "string" for column in region_cols})
        for column in region_cols:
            cached[column] = cached[column].fillna("").astype(str)
        return cached

    rows: list[dict[str, Any]] = []
    with rasterio.open(path) as src:
        for record in regions_gdf.itertuples(index=False):
            row = {column: getattr(record, column) for column in region_cols}
            row["population_total"] = _population_within_src(src, record.geometry)
            rows.append(row)
    result = pd.DataFrame(rows)
    result.to_csv(cache_path, index=False)
    return result


def germany_population_total(raster_path: Path | str | None = None) -> int:
    path = population_raster_path(raster_path)
    cache_name = f"germany_total_{path.name}".replace(".", "_")
    cache_path = _cache_json_path(cache_name)
    if cache_path.exists():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        return int(cached["population_total"])

    outline = gpd.read_file(config.GERMANY_OUTLINE).to_crs("EPSG:4326")
    total = population_within(outline.unary_union, path)
    cache_path.write_text(json.dumps({"population_total": total}, indent=2), encoding="utf-8")
    return total


def state_population_table(raster_path: Path | str | None = None) -> pd.DataFrame:
    states = gpd.read_file(config.GERMANY_STATES).to_crs("EPSG:4326")
    state_col = next((col for col in ("NAME_1", "lan_name", "name", "NAME") if col in states.columns), None)
    if state_col is None:
        raise KeyError("No state name column found in state GeoJSON")
    states = states.rename(columns={state_col: "state_name"})
    return region_population_table(
        states[["state_name", "geometry"]].copy(),
        region_cols=["state_name"],
        cache_name="state_population",
        raster_path=raster_path,
    )

def county_population_table(raster_path: Path | str | None = None) -> pd.DataFrame:
    counties = gpd.read_file(config.GERMANY_COUNTIES).to_crs("EPSG:4326")
    counties = counties.assign(
        county_code=counties["krs_code"].map(_clean_geo_value),
        county_name=counties["krs_name"].map(_clean_geo_value),
        state_name=counties["lan_name"].map(_clean_geo_value),
        county_type=counties["krs_type"].map(_clean_geo_value),
    )
    result = region_population_table(
        counties[["county_code", "county_name", "state_name", "county_type", "geometry"]].copy(),
        region_cols=["county_code", "county_name", "state_name", "county_type"],
        cache_name="county_population",
        raster_path=raster_path,
    )
    result["county_code"] = result["county_code"].map(_clean_geo_value).map(
        lambda value: value.zfill(5) if value.isdigit() and len(value) < 5 else value
    )
    result["county_name"] = result["county_name"].astype(str)
    result["state_name"] = result["state_name"].astype(str)
    result["county_type"] = result["county_type"].astype(str)
    return result.sort_values(["state_name", "county_name"]).reset_index(drop=True)


def summarize_regional_population_coverage(
    union_gdf: gpd.GeoDataFrame,
    regions_gdf: gpd.GeoDataFrame,
    *,
    region_cols: list[str],
    raster_path: Path | str | None = None,
    population_col: str = "population_total",
) -> pd.DataFrame:
    path = population_raster_path(raster_path)
    rows: list[dict[str, Any]] = []
    with rasterio.open(path) as src:
        for union_row in union_gdf.itertuples(index=False):
            time_minutes = int(getattr(union_row, "time_minutes"))
            union_geom = union_row.geometry
            for region_row in regions_gdf.itertuples(index=False):
                total_population = int(getattr(region_row, population_col, 0) or 0)
                covered_population = 0
                if union_geom is not None and not union_geom.is_empty:
                    intersection = union_geom.intersection(region_row.geometry)
                    covered_population = _population_within_src(src, intersection)
                covered_population = int(min(total_population, max(0, covered_population)))
                row = {column: getattr(region_row, column) for column in region_cols}
                row.update(
                    {
                        "time_minutes": time_minutes,
                        "covered_population": covered_population,
                        "population_total": total_population,
                        "pct_population_covered": round(100 * covered_population / total_population, 2)
                        if total_population
                        else 0.0,
                        "population_uncovered": int(max(0, total_population - covered_population)),
                    }
                )
                rows.append(row)
    return pd.DataFrame(rows).sort_values(region_cols + ["time_minutes"]).reset_index(drop=True)


def summarize_union_population_coverage(
    union_gdf: gpd.GeoDataFrame,
    *,
    raster_path: Path | str | None = None,
    denominator_population: int | None = None,
) -> pd.DataFrame:
    path = population_raster_path(raster_path)
    denominator = int(denominator_population or germany_population_total(path) or config.POP_TOTAL_FALLBACK)
    rows: list[dict[str, Any]] = []
    for record in union_gdf.itertuples(index=False):
        covered_population = int(min(denominator, max(0, population_within(record.geometry, path))))
        rows.append(
            {
                "time_minutes": int(getattr(record, "time_minutes")),
                "covered_population": covered_population,
                "population_total": denominator,
                "pct_population_covered": round(100 * covered_population / denominator, 2) if denominator else 0.0,
                "population_uncovered": int(max(0, denominator - covered_population)),
            }
        )
    return pd.DataFrame(rows).sort_values("time_minutes").reset_index(drop=True)


__all__ = [
    "county_population_table",
    "germany_population_total",
    "population_raster_path",
    "population_within",
    "region_population_table",
    "summarize_regional_population_coverage",
    "state_population_table",
    "summarize_union_population_coverage",
]
