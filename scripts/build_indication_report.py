#!/usr/bin/env python3
"""Build a full output folder for one OPS indication."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gba_ops_reanalysis import config
from gba_ops_reanalysis.indication_report import (
    DEFAULT_MAIN_THRESHOLD,
    DEFAULT_STRICT_THRESHOLD,
    DEFAULT_THRESHOLDS,
    build_indication_report,
    slugify_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--indication-name", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--ops-selector", required=True)
    parser.add_argument(
        "--codeset",
        choices=sorted(config.TIPS_CODESETS.keys()),
        default=None,
        help="Optional predefined TIPS 8-839.8* code set override.",
    )
    parser.add_argument("--base-xml-dir", type=Path, default=config.XML_DIR)
    parser.add_argument("--latest-year", type=int, default=None)
    parser.add_argument("--threshold", action="append", type=int, default=None)
    parser.add_argument("--main-threshold", type=int, default=DEFAULT_MAIN_THRESHOLD)
    parser.add_argument("--strict-threshold", type=int, default=DEFAULT_STRICT_THRESHOLD)
    parser.add_argument("--time-bin", action="append", type=int, default=None)
    parser.add_argument("--grid-resolution", type=float, default=0.05)
    parser.add_argument("--report-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    thresholds = sorted(set(args.threshold or DEFAULT_THRESHOLDS))
    time_bins = sorted(set(args.time_bin or [30, 60, 90, 120]))
    selector = config.codeset_to_selector(config.TIPS_CODESETS[args.codeset]) if args.codeset else args.ops_selector
    selector_slug = f"{slugify_text(args.ops_selector)}_{slugify_text(args.codeset)}" if args.codeset else slugify_text(args.ops_selector)
    report_dir = args.report_dir or (
        config.OUTPUTS_DIR / "indications" / f"{slugify_text(args.indication_name)}_{selector_slug}"
    )
    result = build_indication_report(
        indication_name=args.indication_name,
        ops_selector=selector,
        label=args.label,
        base_xml_dir=args.base_xml_dir,
        report_dir=report_dir,
        codeset=args.codeset,
        cache_tag=selector_slug,
        latest_year=args.latest_year,
        thresholds=thresholds,
        main_threshold=args.main_threshold,
        strict_threshold=args.strict_threshold,
        time_bins=time_bins,
        grid_resolution=args.grid_resolution,
    )
    print(f"Report directory: {result['report_dir']}")
    if args.codeset:
        print(f"Codeset: {args.codeset}")
        print(f"Selector: {selector}")
    print(f"Latest year: {result['latest_year']}")
    print(f"Tables: {result['tables_dir']}")
    print(f"Figures: {result['figures_dir']}")
    print(f"Geo: {result['geo_dir']}")


if __name__ == "__main__":
    main()
