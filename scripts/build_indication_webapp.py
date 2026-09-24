#!/usr/bin/env python3
"""Build a static web dashboard for one indication report."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gba_ops_reanalysis.webapp import build_indication_webapp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--title", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_indication_webapp(
        report_dir=args.report_dir,
        output_dir=args.output_dir,
        title=args.title,
    )
    print(f"Built app in: {result['output_dir']}")
    print(f"Open: {result['index_html']}")


if __name__ == "__main__":
    main()
