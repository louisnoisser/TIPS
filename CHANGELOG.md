# Changelog

## 2026-05-08

- Added predefined TIPS 8-839.8* code sets in [`src/gba_ops_reanalysis/config.py`](src/gba_ops_reanalysis/config.py):
  - `CODESET_A_PRIMARY_ONLY`
  - `CODESET_B_LOOSEN`
  - `CODESET_C_INCLUSIVE` (default-equivalent behavior)
- Extended [`scripts/build_indication_report.py`](scripts/build_indication_report.py) with optional `--codeset` to run indication reports against a predefined TIPS code set without rewriting analysis code.
- Added methodological verification script [`scripts/verify_primary_vs_secondary.py`](scripts/verify_primary_vs_secondary.py), producing:
  - `hospital_year_panel.csv`
  - `yearly_summary.csv`
  - `flagged_secondary_only_hospital_years.csv`
  - `persistent_secondary_only_hospitals.csv`
  - `verification_report.md`
- Added orchestration script [`scripts/run_tips_codeset_analysis.py`](scripts/run_tips_codeset_analysis.py), which runs code sets A/B/C into parallel result folders, builds comparison outputs, and runs the verification report.

### CLI usage

Run one report with a predefined code set:

```bash
python scripts/build_indication_report.py \
  --indication-name TIPS \
  --label tips \
  --ops-selector 8-839.8 \
  --codeset A_PRIMARY_ONLY \
  --base-xml-dir data/xml \
  --latest-year 2024 \
  --threshold 25 --threshold 50 --threshold 100 --threshold 200 \
  --main-threshold 50 \
  --strict-threshold 100
```

Run all three code sets + verification bundle:

```bash
python scripts/run_tips_codeset_analysis.py \
  --base-xml-dir data/xml \
  --latest-year 2024 \
  --threshold 25 --threshold 50 --threshold 100 --threshold 200 \
  --main-threshold 50 \
  --strict-threshold 100 \
  --time-bin 30 --time-bin 60 \
  --results-dir results
```
