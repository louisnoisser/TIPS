#!/usr/bin/env python3
"""Generate ORS isochrones for a geocoded center cohort."""

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
from gba_ops_reanalysis.isochrones import (
    export_isochrones,
    generate_isochrone_cache,
    test_ors_connectivity,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Geocoded CSV")
    parser.add_argument("--target-label", default=None, help="Optional target label filter")
    parser.add_argument("--threshold", type=int, default=None, help="Optional threshold filter")
    parser.add_argument("--time-bins", nargs="+", type=int, default=[15, 30, 45, 60])
    parser.add_argument("--tag", default=None, help="Cache/export tag")
    parser.add_argument("--force-recalc", action="store_true")
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--speed-factor", type=float, default=1.0)
    parser.add_argument("--test-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not test_ors_connectivity():
        raise RuntimeError(f"OpenRouteService is not reachable at {config.ORS_BASE_URL}")
    if args.test_only:
        print(f"ORS reachable at {config.ORS_BASE_URL}")
        return

    df = pd.read_csv(args.input)
    if args.target_label and "target_label" in df.columns:
        df = df.loc[df["target_label"] == args.target_label].copy()
    if args.threshold is not None and "threshold" in df.columns:
        df = df.loc[df["threshold"] == args.threshold].copy()

    tag_parts = [args.input.stem]
    if args.target_label:
        tag_parts.append(args.target_label)
    if args.threshold is not None:
        tag_parts.append(f"ge{args.threshold}")
    tag = args.tag or "_".join(tag_parts)

    polygons = generate_isochrone_cache(
        df,
        tag=tag,
        time_bins=sorted(args.time_bins),
        force_recalc=args.force_recalc,
        max_retries=args.max_retries,
        speed_factor=args.speed_factor,
    )
    centers_path, unions_path, meta_path = export_isochrones(df, polygons, tag=tag)

    print(f"Cohort rows: {len(df)}")
    print(f"Wrote: {centers_path}")
    print(f"Wrote: {unions_path}")
    print(f"Wrote: {meta_path}")


if __name__ == "__main__":
    main()
