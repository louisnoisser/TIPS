#!/usr/bin/env python3
"""Build longitudinal hospital-year and yearly OPS/ICD summaries."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gba_ops_reanalysis import config
from gba_ops_reanalysis.longitudinal import run_longitudinal_pipeline
from gba_ops_reanalysis.ops_icd import parse_target_specs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", type=Path, default=config.XML_DIR, help="Folder containing xml_<year> directories")
    parser.add_argument("--out-dir", type=Path, default=config.LONGITUDINAL_OUTPUT_DIR)
    parser.add_argument("--ops-target", action="append", required=True, help="OPS selector in label=selector syntax")
    parser.add_argument("--icd-target", action="append", default=[], help="ICD selector in label=selector syntax")
    parser.add_argument("--denominator-label", default=None, help="ICD label used for rate columns")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ops_targets = parse_target_specs(args.ops_target)
    icd_targets = parse_target_specs(args.icd_target)

    hospital_year, yearly_summary, schema_check = run_longitudinal_pipeline(
        base_dir=args.base_dir,
        out_dir=args.out_dir,
        ops_targets=ops_targets,
        icd_targets=icd_targets,
        denominator_label=args.denominator_label,
    )

    print(f"Hospital-year rows: {len(hospital_year)}")
    print(f"Yearly rows: {len(yearly_summary)}")
    print(f"Schema rows: {len(schema_check)}")
    print(f"Wrote outputs to: {args.out_dir}")


if __name__ == "__main__":
    main()
