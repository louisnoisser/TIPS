# Final TIPS Output

This is the canonical final output directory for the updated 2024 TIPS analysis.

## Canonical Directories

- Figures: `outputs/indications/tips_8-839-8_updated2024/figures/`
- Tables: `outputs/indications/tips_8-839-8_updated2024/tables/`

Use the top-level `figures/` directory as the canonical source for current final figures. The `paper_main/` and `paper_supplement/` subdirectories are auxiliary curated copies and are not the source of truth.

## Final Thresholds

The final analytical thresholds are:

- >=20 cases/year
- >=50 cases/year
- >=100 cases/year
- >=200 cases/year

The main geographic/population thresholds are >=50 and >=100.

## Population Raster

Population coverage uses GHS-POP E2025:

- Raster: `spatial/GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif`
- Epoch: 2025
- Denominator source: total population represented in the GHS-POP grid within the German national boundary

## Audit

See `threshold_audit_final.md` for the final threshold audit, commands used to regenerate the report, figure modification times, remaining stale-findings classification, and population metadata.
