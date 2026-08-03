"""OpenRouteService-backed isochrone generation helpers."""

from __future__ import annotations

import json
import pickle
import time
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Polygon, shape
from shapely.ops import unary_union

from . import config


def cache_path(minutes: int, tag: str) -> Path:
    return config.ISOCHRONE_CACHE_DIR / f"poly{minutes}_{tag}.pkl"


def test_ors_connectivity() -> bool:
    for health_url in (f"{config.ORS_BASE_URL}/health", f"{config.ORS_BASE_URL}/v2/health"):
        try:
            response = requests.get(health_url, timeout=10)
            if response.ok:
                return True
        except requests.RequestException:
            continue
    try:
        request_isochrones(13.4050, 52.5200, [10], max_retries=1)
        return True
    except Exception:
        return False


def _largest_polygon(geometry: Any) -> Polygon:
    geom = shape(geometry)
    if geom.geom_type == "Polygon":
        return Polygon(geom.exterior.coords)
    if geom.geom_type == "MultiPolygon":
        largest = max(geom.geoms, key=lambda item: item.area)
        return Polygon(largest.exterior.coords)
    return Polygon()


def _post_isochrones(payload: dict[str, Any], *, max_retries: int) -> dict[str, Any]:
    response = None
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{config.ORS_BASE_URL}/v2/isochrones/{config.ORS_PROFILE}",
                json=payload,
                timeout=config.ORS_TIMEOUT,
            )
            response.raise_for_status()
            break
        except requests.HTTPError as exc:
            if attempt == max_retries - 1:
                status = exc.response.status_code if exc.response is not None else "unknown"
                body = (exc.response.text or "").strip() if exc.response is not None else ""
                locations = payload.get("locations", [])
                ranges = payload.get("range", [])
                preview = locations[:2]
                message = (
                    f"ORS HTTP {status} for {len(locations)} locations and {len(ranges)} ranges "
                    f"(profile={config.ORS_PROFILE}, endpoint={config.ORS_BASE_URL}/v2/isochrones/{config.ORS_PROFILE}). "
                    f"Payload preview locations={preview}, ranges={ranges}. "
                    f"Response body: {body[:500]}"
                )
                raise requests.HTTPError(message, response=exc.response) from exc
            time.sleep(2 ** attempt)
        except requests.RequestException:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
    return response.json() if response is not None else {}


def _is_ors_max_interval_limit(exc: requests.HTTPError) -> bool:
    if exc.response is None or exc.response.status_code != 400:
        return False
    body = (exc.response.text or "").lower()
    return '"code":3012' in body or "maximum value of 1" in body


def _store_isochrone_features(data: dict[str, Any], grouped: dict[int, dict[int, Polygon]]) -> None:
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        group_index = int(props.get("group_index", 0))
        value = int(round(float(props.get("value", 0))))
        grouped.setdefault(group_index, {})[value] = _largest_polygon(feature["geometry"])


def request_isochrones_many(
    locations: list[list[float]],
    time_bins: list[int],
    *,
    max_retries: int = 3,
    speed_factor: float = 1.0,
    include_area: bool = True,
) -> list[list[Polygon]]:
    if not locations:
        return []

    ranges_seconds = [int(minutes * speed_factor * 60) for minutes in time_bins]
    max_ranges_per_request = 10
    grouped: dict[int, dict[int, Polygon]] = {index: {} for index in range(len(locations))}

    for offset in range(0, len(ranges_seconds), max_ranges_per_request):
        chunk = ranges_seconds[offset : offset + max_ranges_per_request]
        payload = {
            "locations": locations,
            "range_type": "time",
            "range": chunk,
        }
        if include_area:
            payload["attributes"] = ["area"]
        try:
            data = _post_isochrones(payload, max_retries=max_retries)
            _store_isochrone_features(data, grouped)
        except requests.HTTPError as exc:
            # Some local ORS setups allow only one isochrone per request.
            # In that case we keep the same output time bins but split per range.
            if _is_ors_max_interval_limit(exc) and len(chunk) > 1:
                for seconds in chunk:
                    single_payload = {
                        "locations": locations,
                        "range_type": "time",
                        "range": [seconds],
                    }
                    if include_area:
                        single_payload["attributes"] = ["area"]
                    single_data = _post_isochrones(single_payload, max_retries=max_retries)
                    _store_isochrone_features(single_data, grouped)
                continue
            raise

    polygons_by_location: list[list[Polygon]] = []
    for group_index in range(len(locations)):
        feature_map = grouped.get(group_index, {})
        missing = [seconds for seconds in ranges_seconds if seconds not in feature_map]
        if missing:
            raise RuntimeError(
                f"Missing isochrone polygons for location {group_index}: "
                f"expected {ranges_seconds}, got {sorted(feature_map)}"
            )
        polygons_by_location.append([feature_map[seconds] for seconds in ranges_seconds])
    return polygons_by_location


def request_isochrones(
    lon: float,
    lat: float,
    time_bins: list[int],
    *,
    max_retries: int = 3,
    speed_factor: float = 1.0,
    include_area: bool = True,
) -> list[Polygon]:
    return request_isochrones_many(
        [[lon, lat]],
        time_bins,
        max_retries=max_retries,
        speed_factor=speed_factor,
        include_area=include_area,
    )[0]


def save_polygons(polygons_by_time: dict[int, list[Polygon]], tag: str) -> None:
    config.ISOCHRONE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for minutes, polygons in polygons_by_time.items():
        with open(cache_path(minutes, tag), "wb") as handle:
            pickle.dump(polygons, handle, protocol=pickle.HIGHEST_PROTOCOL)


def load_polygons(time_bins: list[int], tag: str) -> dict[int, list[Polygon]]:
    polygons_by_time: dict[int, list[Polygon]] = {}
    for minutes in time_bins:
        with open(cache_path(minutes, tag), "rb") as handle:
            polygons_by_time[minutes] = pickle.load(handle)
    return polygons_by_time


def generate_isochrone_cache(
    df: pd.DataFrame,
    *,
    tag: str,
    time_bins: list[int],
    force_recalc: bool = False,
    max_retries: int = 3,
    speed_factor: float = 1.0,
    max_locations_per_request: int | None = None,
    include_area: bool = True,
) -> dict[int, list[Polygon]]:
    if not force_recalc and all(cache_path(minutes, tag).exists() for minutes in time_bins):
        return load_polygons(time_bins, tag)

    work = df.dropna(subset=["longitude", "latitude"]).reset_index(drop=True)
    polygons_by_time = {minutes: [] for minutes in time_bins}
    batch_size = max(1, int(max_locations_per_request or config.ORS_MAX_LOCATIONS_PER_REQUEST))

    for start in range(0, len(work), batch_size):
        stop = min(start + batch_size, len(work))
        batch = work.iloc[start:stop]
        if stop % 25 == 0 or stop == len(work):
            print(f"  generated {stop}/{len(work)} center isochrone sets")
        batch_locations = [[float(row.longitude), float(row.latitude)] for row in batch.itertuples(index=False)]
        try:
            batch_polygons = request_isochrones_many(
                batch_locations,
                time_bins,
                max_retries=max_retries,
                speed_factor=speed_factor,
                include_area=include_area,
            )
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status == 400 and len(batch_locations) > 1:
                print(
                    f"  ORS returned HTTP 400 for batch size {len(batch_locations)} "
                    f"(rows {start}-{stop - 1}); retrying as single-location requests."
                )
                batch_polygons = []
                for location in batch_locations:
                    single = request_isochrones_many(
                        [location],
                        time_bins,
                        max_retries=max_retries,
                        speed_factor=speed_factor,
                        include_area=include_area,
                    )
                    batch_polygons.extend(single)
            else:
                raise
        for polygons in batch_polygons:
            for minutes, polygon in zip(time_bins, polygons, strict=True):
                polygons_by_time[minutes].append(polygon)

    save_polygons(polygons_by_time, tag)
    return polygons_by_time


def export_isochrones(
    df: pd.DataFrame,
    polygons_by_time: dict[int, list[Polygon]],
    *,
    tag: str,
) -> tuple[Path, Path, Path]:
    work = df.dropna(subset=["longitude", "latitude"]).reset_index(drop=True)
    feature_rows: list[dict[str, object]] = []

    for row_index, row in work.iterrows():
        for minutes, polygons in polygons_by_time.items():
            polygon = polygons[row_index]
            if polygon.is_empty:
                continue
            feature_rows.append(
                {
                    "target_label": row.get("target_label", ""),
                    "threshold": row.get("threshold", ""),
                    "facility_id": row.get("facility_id", ""),
                    "hospital_name": row.get("hospital_name", ""),
                    "ops_cases": row.get("ops_cases", None),
                    "time_minutes": minutes,
                    "geometry": polygon,
                }
            )

    feature_path = config.ISOCHRONE_OUTPUT_DIR / f"{tag}_centers.geojson"
    union_path = config.ISOCHRONE_OUTPUT_DIR / f"{tag}_unions.geojson"
    meta_path = config.ISOCHRONE_OUTPUT_DIR / f"{tag}_meta.json"

    feature_gdf = gpd.GeoDataFrame(feature_rows, geometry="geometry", crs="EPSG:4326")
    feature_gdf.to_file(feature_path, driver="GeoJSON")

    union_rows = []
    for minutes, polygons in polygons_by_time.items():
        valid = [polygon for polygon in polygons if polygon and not polygon.is_empty]
        union_rows.append({"time_minutes": minutes, "geometry": unary_union(valid) if valid else Polygon()})
    union_gdf = gpd.GeoDataFrame(union_rows, geometry="geometry", crs="EPSG:4326")
    union_gdf.to_file(union_path, driver="GeoJSON")

    meta_path.write_text(
        json.dumps(
            {
                "tag": tag,
                "time_bins": sorted(polygons_by_time),
                "center_count": int(len(work)),
                "cache_files": [str(cache_path(minutes, tag)) for minutes in sorted(polygons_by_time)],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return feature_path, union_path, meta_path
