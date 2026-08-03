#!/usr/bin/env python3
"""Extract OPS/ICD hospital counts and threshold cohorts from a single XML year."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gba_ops_reanalysis import config
from gba_ops_reanalysis.gba_xml import discover_year_dirs
from gba_ops_reanalysis.ops_icd import (
    add_threshold_flags,
    build_ops_target_summary,
    build_threshold_centers,
    extract_hospital_code_totals,
    parse_target_specs,
    slugify_label,
    target_case_column,
    write_target_metadata,
)


def latest_xml_dir() -> Path:
    year_dirs = discover_year_dirs(config.XML_DIR)
    if not year_dirs:
        raise FileNotFoundError(f"No xml_<year> directories found under {config.XML_DIR}")
    return year_dirs[-1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml-dir", type=Path, default=None, help="XML year folder, e.g. data/xml/xml_2024")
    parser.add_argument("--ops-target", action="append", required=True, help="OPS selector in label=selector syntax")
    parser.add_argument("--icd-target", action="append", default=[], help="ICD selector in label=selector syntax")
    parser.add_argument("--threshold", action="append", type=int, default=None, help="Threshold for center cohorts")
    parser.add_argument("--denominator-label", default=None, help="ICD label used to compute OPS-to-ICD percentages")
    parser.add_argument("--pattern", default="*-xml.xml")
    parser.add_argument("--out-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    xml_dir = args.xml_dir or latest_xml_dir()
    ops_targets = parse_target_specs(args.ops_target)
    icd_targets = parse_target_specs(args.icd_target)
    thresholds = sorted(set(args.threshold or [10, 25]))
    out_dir = args.out_dir or (config.DERIVED_DIR / xml_dir.name)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Extracting from: {xml_dir}")
    print(f"OPS targets: {list(ops_targets)}")
    if icd_targets:
        print(f"ICD targets: {list(icd_targets)}")

    hospital_df = extract_hospital_code_totals(
        xml_dir,
        ops_targets=ops_targets,
        icd_targets=icd_targets,
        pattern=args.pattern,
    )

    if args.denominator_label and args.denominator_label in icd_targets:
        denominator_slug = slugify_label(args.denominator_label)
        denominator_col = target_case_column(args.denominator_label)
        denominator = hospital_df[denominator_col].where(hospital_df[denominator_col] != 0)
        for label in ops_targets:
            case_col = target_case_column(label)
            rate_col = f"{slugify_label(label)}_pct_of_{denominator_slug}"
            hospital_df[rate_col] = (
                hospital_df[case_col]
                .div(denominator)
                .mul(100)
                .round(2)
                .fillna(0.0)
            )

    hospital_df = add_threshold_flags(hospital_df, list(ops_targets), thresholds)
    summary_df = build_ops_target_summary(hospital_df, list(ops_targets), thresholds)
    threshold_df = build_threshold_centers(
        hospital_df,
        ops_labels=list(ops_targets),
        icd_labels=list(icd_targets),
        thresholds=thresholds,
    )

    hospital_path = out_dir / "hospital_code_totals.csv"
    summary_path = out_dir / "ops_target_summary.csv"
    threshold_path = out_dir / "centers_above_thresholds.csv"
    metadata_path = out_dir / "target_metadata.json"

    hospital_df.to_csv(hospital_path, index=False)
    summary_df.to_csv(summary_path, index=False)
    threshold_df.to_csv(threshold_path, index=False)
    write_target_metadata(
        metadata_path,
        xml_dir=xml_dir,
        ops_targets=ops_targets,
        icd_targets=icd_targets,
        thresholds=thresholds,
    )

    print(f"Wrote: {hospital_path}")
    print(f"Wrote: {summary_path}")
    print(f"Wrote: {threshold_path}")
    print(f"Wrote: {metadata_path}")


if __name__ == "__main__":
    main()
