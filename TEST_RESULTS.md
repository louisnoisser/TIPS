# Snapshot test results

Test date: 2026-09-24

Environment:

- Python interpreter: source project's existing `.venv`
- Snapshot import path: `PYTHONPATH=src`
- Bytecode generation disabled
- Pytest cache disabled
- No routing requests, downloads or analysis production runs were performed

## Executable isolated test set

The unit and audit tests whose declared inputs are included in this snapshot were run explicitly.

Result: **33 passed in 1.13 seconds**.

Covered areas included final corrected aggregation logic, site-resolution logic, suppression sensitivity logic, reusable geography validation functions and OPS classification and reconciliation checks that operate on retained compact audit files.

## Full-suite boundary check

A full invocation was also attempted to identify missing-input boundaries.

Result: **33 passed, 1 failed and 14 setup errors**.

The non-passing cases were attributable to deliberately excluded inputs rather than a newly observed computational mismatch:

- BfArM catalogue directories under `ops_bfarm_2013_2024/` were excluded as a large third-party source collection.
- Geography release-package tests require the excluded `geography_validation_ge50_2026-07-24` and `geography_validation_ge100_2026-07-24` geometry and figure packages.
- One annual reconciliation control test requires `outputs/final_submission_assets_2026-07-24/tables/TableS1_corrected_annual_site_metrics.csv`, which was excluded with submission assets.

No missing input was downloaded or regenerated to satisfy these tests. These limitations must remain visible during the independent audit.
