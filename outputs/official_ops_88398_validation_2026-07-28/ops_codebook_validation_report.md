# Approved official OPS 8-839.8 codebook validation report

- Generation timestamp: `2026-07-28T11:48:33+00:00`
- Git commit: `e162c991af5d699d169240b903a1c35cbb4df5f9`
- Analysis version: `official-ops-88398-v1-approved-secondary-v1`
- Mapping approval: **explicit user approval dated 2026-07-28**
- Secondary-only analysis release gate: **PASS**

## Approved mapping

- `8-839.81` to `8-839.86`: `secondary_intervention`
- `8-839.87`, `8-839.88`, `8-839.89`, `8-839.8a`: `primary_placement`
- `8-839.8`: `unresolved_parent`
- `8-839.8x`: `unresolved_other`
- 2013 `8-839.80`: `invalid_hospital_reported_legacy_code`

The official BfArM catalogue supplies 138 year-code definitions.
The additional row is an approved analytical exception, not an official 2013
code. It was valid in OPS 2012 as primary placement but invalid in OPS 2013.
It is retained literally, is not remapped to `.87` or `.88`, is not discarded,
and cannot independently establish primary placement.

## Coverage

- Observed year-code combinations: 131
- Uniquely matched to an approved mapping: 131
- Unmatched combinations: 0
- Duplicate matches: 0
- Legacy grouped records: 5
- Legacy literal occurrences: 7
- Legacy suppressed entries: 7
- Legacy visible activity: 0

All five affected 2013 site-years also contain valid 2013 primary-placement code
`8-839.87` or `8-839.88`. Their `primary_or_mixed` classification therefore does
not depend on the invalid legacy code.

## Reconciliation

All 12 reporting years reproduce the validated physical-site
visible national totals exactly. No retained record or visible procedure
occurrence was lost or duplicated during mapping. The 2024 total is 5,247.

## Classification integrity

- Site-years classified: 2057
- Mutually exclusive categories: 4
- Missing classifications: 0
- Site-years containing the invalid legacy code: 5

Years before 2013 are excluded. Suppressed primary entries count as evidence of
primary placement. Absence of a visible primary count is never treated as
secondary-only when a suppressed primary entry exists.
