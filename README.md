# TIPS analysis: submission release

Reproducible analysis of TIPS-related OPS `8-839.8*` procedural activity in German
G-BA hospital quality reports, with physical-site resolution, provider-volume
and concentration metrics, suppression sensitivity, potential geographic
accessibility, and de novo subcode sensitivity.

This release locks the validated submission inputs, including the 2012 filename
correction (Potsdam `261200220-00`: annual visible activity 2110 → 2120).
Other years remain unchanged. In 2024 there are 193 identifiable active sites,
113 with openly numeric activity, 80 suppressed-only sites and 5,247 visible
procedure occurrences. Counts represent procedure-code activity, not unique
patients or unique TIPS creations. Accessibility is potential driving-time access,
not observed treatment access.

Manuscript: publication link/DOI pending. No publication identifier has been
assigned in this repository; this section and CITATION.cff will be updated when
published. Cite the versioned software using [CITATION.cff](CITATION.cff).

## Structure

- `src/gba_ops_reanalysis/`: XML parsing and reusable scientific calculations.
- `scripts/`: original analysis entrypoints and the offline submission renderer.
- `tests/`: regression checks and self-contained unit tests.
- `outputs/`: locked derived CSV inputs, QA evidence, site/union GeoJSON and
  historical intermediate tables, kept at original relative paths for the
  existing pipeline. `outputs/site_resolution_validation/` contains the corrected
  site-level input. `outputs/tips_2012_filefix_2026-10-15/` is authoritative for
  corrected annual tables and geographic display corrections.
- `spatial/`: the small map boundaries used by the figure code; no rasters.
- `reproducibility/locked_outputs_sha256.csv`: exact release input checksums.
- `reproducibility/external_inputs.json`: external raster/routing versions and
  recorded hashes. `environment.lock.txt` records the tested package versions.
- `results/`: newly generated figures/tables; ignored by Git.

Historical tables under other output directories are retained as evidence and
may reflect an earlier stage. Use the command below and the authoritative paths
above for submission assets. Historical audit manifests describe their original
packages, not this selected release; use the release lock for integrity checks.

## Environment

Python 3.11+ is required; the release verification used Python 3.13. Create a
virtual environment and install the package and its plotting/test dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
```

`requirements.txt` contains supported dependency ranges. For the exact tested
versions, use `python -m pip install -r reproducibility/environment.lock.txt`.
Native GDAL/PROJ libraries are supplied by the supported geospatial wheels or
must be available on the host. Do not put credentials in tracked files.

## Reproduce from locked derived inputs (no downloads or routing needed)

Run all commands from the repository root. The existing configuration creates
empty local work directories on import. The locked inputs are never overwritten
by the submission renderer; select a new output directory for each run.

1. Validate every locked CSV/GeoJSON and key scientific invariants:

   ```bash
   PYTHONPATH=src:scripts python scripts/reproduce_submission.py --verify-only
   ```

2. Run focused regression checks against the included corrected site data:

   ```bash
   PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts \
     GBA_OPS_SITE_DATA=outputs/site_resolution_validation/resolved_site_level_data.csv \
     python -m pytest -q -p no:cacheprovider \
     tests/test_report_file_selection.py tests/test_final_corrected.py
   ```

3. Render Figures 1–2 with the existing plot functions; the selected Figure 3B
   using the corrected validated stack; both saved Figure 4 candidates (C113 and
   C193) using saved 30/60-minute geometries; and all four short-name Figure S1
   panels. Export the locked corrected tables, de novo sensitivity and geographic
   sensitivity CSVs in the same run:

   ```bash
   PYTHONPATH=src:scripts python scripts/reproduce_submission.py \
     --output-dir results/submission-v1
   ```

   The original recorded workflow did not select a final Figure 4 candidate.
   Both are preserved and named explicitly; this release does not invent a choice.
   Figure S1 uses the checked names, including Klinikum Dortmund Mitte and
   Cellitinnen-Krankenhaus St. Petrus, Wuppertal. It checks single-line/unique labels
   and text bounding boxes at 600 dpi.

4. Inspect `results/submission-v1/reproduction_summary.json`, `qa/`, PDF/PNG/SVG
   figures and `tables/`. Table S10 inputs are in
   `outputs/de_novo_sensitivity_2013_2024/` and
   `outputs/de_novo_accessibility_sensitivity_2026-08-16/`; corrected Panel C
   percentages are locked in
   `outputs/tips_2012_filefix_2026-10-15/geography/TableS10_PanelC_corrected.csv`.
   Site-level activity is in `outputs/site_resolution_validation/`; concentration
   and suppression metrics in `outputs/final_corrected_2026-07-24/`; isochrone
   coverage in `outputs/final_submission_assets_2026-07-24/geography/` and
   `outputs/late_stage_accessibility_193_113_recovery_2026-08-15/coverage/`.

The complete test suite includes historical checks requiring excluded external
catalogues/data and is not equivalent to the focused release gate above.

## Rebuild from primary sources

Primary inputs are intentionally not redistributed. Their original terms remain
applicable. The MIT license applies to project software, not to third-party raw
data or map-data rights.

1. **G-BA quality-report XML:** request/download the machine-readable reports
   through the [G-BA data portal](https://qb-datenportal.g-ba.de/). Its XML download
   requires an order and verified access; the PDF reference database is not a
   substitute for the raw XML. The series covers 2008, 2010 and 2012–2024 (no
   interpolation of 2009 or 2011). Arrange the downloaded originals as
   `data/xml/xml_YYYY/*-xml.xml`, retaining upper-case variants such as `-XML.xml`.
   The case-insensitive selector preserves the Potsdam 2012 report. Run
   `python scripts/rebuild_tips_code_level_audit.py --output-dir results/code-audit`
   to reproduce the legacy audit and verify the single corrected addition;
   it requires the locked legacy audit in `outputs/audit/`.
2. **Population:** obtain [GHS-POP R2023A](https://human-settlement.emergency.copernicus.eu/ghs_pop2023.php)
   through the [official download wizard](https://human-settlement.emergency.copernicus.eu/downloadWizard.php).
   Exact file: `GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif`
   (epoch 2025, EPSG:4326, 3 arcsec, V1.0).
3. **Settlement model:** obtain [GHS-SMOD R2023A, V2.0](https://human-settlement.emergency.copernicus.eu/ghs_smod2023.php).
   Exact file: `GHS_SMOD_E2025_GLOBE_R2023A_54009_1000_V2_0.tif`
   (epoch 2025, World Mollweide EPSG:54009, 1 km). Put both rasters in `spatial/`,
   or use `GBA_OPS_POP_RASTER` and `GBA_OPS_SMOD_RASTER` for generic entrypoints.
   Urban codes: 30/23/22/21; rural: 13/12/11. Other classes are retained separately;
   settlement resampling is nearest neighbour. Exact original hashes are in
   `reproducibility/external_inputs.json`.
4. **Routing:** deploy **OpenRouteService 9.8.0** with `driving-car`, following
   the [official Docker instructions](https://giscience.github.io/openrouteservice/run-instance/running-with-docker).
   Pin the recorded image digest
   `openrouteservice/openrouteservice@sha256:2ee0dcf4aeccd7852f443dfbae03a0ea96537753360e42e682a32cb9e72f929b`
   rather than `latest`. The recorded OSM data timestamp is
   `2026-03-29T20:20:46Z`, graph date `2026-04-01T12:04:19Z`.
   Obtain the corresponding Germany extract from
   [Geofabrik](https://download.geofabrik.de/europe/germany.html) or the original
   archived extract; today's `germany-latest.osm.pbf` cannot reproduce that historical
   graph exactly. Keep it and all graph/elevation/cache/container data local.
   The geographic drivers document their original config/graph hashes and expect
   the local `ors-docker/` runtime paths; restore the matching original routing
   configuration when doing a raw rebuild. Set `GBA_OPS_ORS_URL` for generic routing
   entrypoints (default `http://localhost:8080/ors`).
5. Rebuild parsing/site resolution and corrected metrics with the corresponding
   original entrypoints (`extract_ops_icd_centers.py`,
   `run_tips_site_resolution_validation.py`, `run_tips_final_corrected.py`), using
   `--help` for explicit input/output paths. The site-resolution validation driver
   intentionally checks the legacy production extract before applying corrections;
   do not point its legacy gate at a partially corrected extract. The submission
   renderer above avoids this historical bootstrap dependency by consuming the
   validated corrected site CSV directly.
6. De novo sensitivity is implemented by `run_tips_de_novo_sensitivity.py`;
   geographic overlay/routing by
   `run_late_stage_accessibility_193_113_recovery_2026_08_15.py`,
   `run_de_novo_accessibility_sensitivity_2026_08_16.py` and
   `run_tips_geographic_suppression_sensitivity_2026_09_23.py`. These historical
   full-rebuild drivers enforce provenance hashes and can require the original
   routing configuration/OSM even when reusing saved geometry. Use new output
   destinations and matching primary inputs; do not overwrite the release lock.

Exact historical raw-data/routing reproduction requires the recorded source
versions and matching configuration, not merely the same software version.
The included locked CSVs/geometries support offline figure/table reproduction
without distributing those large primary assets.

## License and citation

Project code: [MIT](LICENSE). Derived G-BA evidence and third-party geographic
inputs retain their source attribution and applicable usage terms.
Cite the release as specified in [CITATION.cff](CITATION.cff).
