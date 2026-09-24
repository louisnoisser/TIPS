#!/usr/bin/env python3
"""Build supplemental analyses from an existing indication report directory."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gba_ops_reanalysis.indication_supplement import build_indication_supplement


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument(
        "--require-population",
        action="store_true",
        help="Fail if the GHS-POP raster is unavailable instead of silently skipping population outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_indication_supplement(args.report_dir, require_population=args.require_population)
    print(f"Supplemented report: {result['report_dir']}")
    print(f"Tables: {result['tables_dir']}")
    print(f"Figures: {result['figures_dir']}")


if __name__ == "__main__":
    main()
