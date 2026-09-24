#!/usr/bin/env python3
"""Run SMOD-based urban-rural summaries for center points or isochrone unions."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import geopandas as gpd
import pandas as pd

from gba_ops_reanalysis import config
from gba_ops_reanalysis.urban_rural import (
    classify_points,
    summarize_point_classes,
    summarize_union_coverage,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--points-csv", type=Path, default=None, help="CSV with longitude/latitude columns")
    parser.add_argument("--union-geojson", type=Path, default=None, help="Union GeoJSON from generate_isochrones.py")
    parser.add_argument("--lon-col", default="longitude")
    parser.add_argument("--lat-col", default="latitude")
    parser.add_argument("--grid-resolution", type=float, default=0.05)
    parser.add_argument("--raster-path", default=str(config.DEFAULT_SMOD_RASTER))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.points_csv and not args.union_geojson:
        raise ValueError("Provide --points-csv and/or --union-geojson")

    if args.points_csv:
        points_df = pd.read_csv(args.points_csv)
        points_gdf = classify_points(
            points_df,
            lon_col=args.lon_col,
            lat_col=args.lat_col,
            raster_path=args.raster_path,
        )
        point_out = args.points_csv.with_name(f"{args.points_csv.stem}_urban_rural.csv")
        summary_out = args.points_csv.with_name(f"{args.points_csv.stem}_urban_rural_summary.csv")
        points_gdf.drop(columns="geometry").to_csv(point_out, index=False)
        summarize_point_classes(points_gdf).to_csv(summary_out, index=False)
        print(f"Wrote: {point_out}")
        print(f"Wrote: {summary_out}")

    if args.union_geojson:
        union_gdf = gpd.read_file(args.union_geojson)
        coverage_df = summarize_union_coverage(
            union_gdf,
            raster_path=args.raster_path,
            grid_resolution=args.grid_resolution,
        )
        coverage_out = args.union_geojson.with_name(f"{args.union_geojson.stem}_urban_rural_coverage.csv")
        coverage_df.to_csv(coverage_out, index=False)
        print(f"Wrote: {coverage_out}")


if __name__ == "__main__":
    main()
