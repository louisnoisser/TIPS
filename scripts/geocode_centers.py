#!/usr/bin/env python3
"""Geocode XML-derived center cohorts using local cache plus public geocoders."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd

from gba_ops_reanalysis import config
from gba_ops_reanalysis.geocoding import geocode_dataframe


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Input CSV from extract_ops_icd_centers.py")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--cache-path", type=Path, default=None)
    parser.add_argument("--target-label", default=None, help="Optional target label filter")
    parser.add_argument("--threshold", type=int, default=None, help="Optional threshold filter")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = pd.read_csv(args.input)
    if args.target_label and "target_label" in df.columns:
        df = df.loc[df["target_label"] == args.target_label].copy()
    if args.threshold is not None and "threshold" in df.columns:
        df = df.loc[df["threshold"] == args.threshold].copy()

    output_path = args.output or (config.GEOCODED_DIR / f"{args.input.stem}_geocoded.csv")
    cache_path = args.cache_path or (config.GEOCODE_CACHE_DIR / f"{args.input.stem}_cache.csv")

    geocoded = geocode_dataframe(df, cache_path=cache_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    geocoded.to_csv(output_path, index=False)

    print(f"Input rows: {len(df)}")
    print(f"Geocoded rows with coordinates: {int(geocoded['latitude'].notna().sum())}")
    print(f"Wrote: {output_path}")
    print(f"Cache: {cache_path}")


if __name__ == "__main__":
    main()
