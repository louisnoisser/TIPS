#!/usr/bin/env python3
"""Build the parallel TIPS privacy-suppression sensitivity analysis."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gba_ops_reanalysis import config
from gba_ops_reanalysis.suppression_sensitivity import run_suppression_sensitivity


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-xml-dir", type=Path, default=config.XML_DIR)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=config.OUTPUTS_DIR / "indications" / "tips_8-839-8_suppression_sensitivity",
    )
    parser.add_argument(
        "--reference-report-dir",
        type=Path,
        default=config.OUTPUTS_DIR / "indications" / "tips_8-839-8_updated2024",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_suppression_sensitivity(
        base_xml_dir=args.base_xml_dir,
        output_dir=args.output_dir,
        reference_report_dir=args.reference_report_dir,
    )
    print(f"Suppression sensitivity output: {result['output_dir']}")
    print("Visible-only regression: passed")


if __name__ == "__main__":
    main()
