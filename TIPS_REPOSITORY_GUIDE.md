# TIPS Repository Guide

This file is a handoff note for future agents or collaborators working in this repository.

Short answer: almost everything needed for the completed TIPS analysis is already in this repository. The main exceptions are:

- the running OpenRouteService instance used for isochrones (`http://localhost:8080/ors`)
- the optional external population raster fallback from the original GeoStroke project if no local copy is present
- online geocoding services if the local geocode cache does not already contain an address

## What this repository contains

This repository is the reusable analysis workspace:

- repo root: [`/Users/larsmasanneck/coding_projects/GBA_OPS_Reanalysis`](/Users/larsmasanneck/coding_projects/GBA_OPS_Reanalysis)
- main README: [`README.md`](README.md)
- Python environment spec: [`requirements.txt`](requirements.txt)
- reusable package: [`src/gba_ops_reanalysis/`](src/gba_ops_reanalysis)
- runnable CLI scripts: [`scripts/`](scripts)

The completed TIPS indication outputs are already stored here:

- main report folder: [`outputs/indications/tips_8-839-8/`](outputs/indications/tips_8-839-8)
- markdown results summary: [`outputs/indications/tips_8-839-8/SUMMARY.md`](outputs/indications/tips_8-839-8/SUMMARY.md)
- machine-readable summary: [`outputs/indications/tips_8-839-8/report_summary.json`](outputs/indications/tips_8-839-8/report_summary.json)
- notebook: [`output/jupyter-notebook/tips-ops-8-839-8-analysis.ipynb`](output/jupyter-notebook/tips-ops-8-839-8-analysis.ipynb)
- static dashboard: [`webapp/tips-ops-8-839-8/index.html`](webapp/tips-ops-8-839-8/index.html)

## Where everything is stored

### Source data

- G-BA XML folders: [`data/xml/`](data/xml)
- available years were used from `xml_2008`, `xml_2010`, and `xml_2012` through `xml_2024`

### Derived intermediate data

- single-year parsed and thresholded outputs: [`data/derived/`](data/derived)
- geocoded center files: [`data/geocoded/`](data/geocoded)
- caches:
  - geocoding cache: [`data/cache/geocode/`](data/cache/geocode)
  - isochrone cache: [`data/cache/isochrones/`](data/cache/isochrones)
  - population cache: [`data/cache/population/`](data/cache/population)

### Spatial assets

- repo spatial folder: [`spatial/`](spatial)
- Germany outline: [`spatial/germany-detailed-boundary_917.geojson`](spatial/germany-detailed-boundary_917.geojson)
- Germany states: [`spatial/germany-states.geojson`](spatial/germany-states.geojson)
- Germany counties: [`spatial/georef-germany-kreis@public.geojson`](spatial/georef-germany-kreis@public.geojson)
- SMOD raster for urban-rural classification: [`spatial/GHS_SMOD_E2025_GLOBE_R2023A_54009_1000_V2_0.tif`](spatial/GHS_SMOD_E2025_GLOBE_R2023A_54009_1000_V2_0.tif)

### TIPS-specific outputs

- report folder: [`outputs/indications/tips_8-839-8/`](outputs/indications/tips_8-839-8)
- tables: [`outputs/indications/tips_8-839-8/tables/`](outputs/indications/tips_8-839-8/tables)
- figures: [`outputs/indications/tips_8-839-8/figures/`](outputs/indications/tips_8-839-8/figures)
- GeoJSON and metadata: [`outputs/indications/tips_8-839-8/geo/`](outputs/indications/tips_8-839-8/geo)

### Longitudinal generic outputs

- generic longitudinal folder: [`outputs/longitudinal/`](outputs/longitudinal)

## Tool index

These are the main entrypoints a future agent should use.

### End-to-end report builders

- full report builder: [`scripts/build_indication_report.py`](scripts/build_indication_report.py)
  - package implementation: [`src/gba_ops_reanalysis/indication_report.py`](src/gba_ops_reanalysis/indication_report.py)
  - use this to create a complete indication report folder from XML inputs
- supplemental analysis builder: [`scripts/build_indication_supplement.py`](scripts/build_indication_supplement.py)
  - package implementation: [`src/gba_ops_reanalysis/indication_supplement.py`](src/gba_ops_reanalysis/indication_supplement.py)
  - use this to add concentration, churn, access trade-off, population, state, and county analyses to an existing report

### Core pipeline steps

- XML OPS and ICD extraction: [`scripts/extract_ops_icd_centers.py`](scripts/extract_ops_icd_centers.py)
  - package implementation: [`src/gba_ops_reanalysis/ops_icd.py`](src/gba_ops_reanalysis/ops_icd.py)
- geocoding: [`scripts/geocode_centers.py`](scripts/geocode_centers.py)
  - package implementation: [`src/gba_ops_reanalysis/geocoding.py`](src/gba_ops_reanalysis/geocoding.py)
- isochrones: [`scripts/generate_isochrones.py`](scripts/generate_isochrones.py)
  - package implementation: [`src/gba_ops_reanalysis/isochrones.py`](src/gba_ops_reanalysis/isochrones.py)
- urban-rural analysis: [`scripts/run_urban_rural_analysis.py`](scripts/run_urban_rural_analysis.py)
  - package implementation: [`src/gba_ops_reanalysis/urban_rural.py`](src/gba_ops_reanalysis/urban_rural.py)
- longitudinal summary: [`scripts/build_longitudinal_summary.py`](scripts/build_longitudinal_summary.py)
  - package implementation: [`src/gba_ops_reanalysis/longitudinal.py`](src/gba_ops_reanalysis/longitudinal.py)

### Reporting outputs around a completed indication

- notebook writer: [`scripts/write_indication_notebook.py`](scripts/write_indication_notebook.py)
  - use this to regenerate the notebook scaffold around an existing report folder
- static web app builder: [`scripts/build_indication_webapp.py`](scripts/build_indication_webapp.py)
  - package implementation: [`src/gba_ops_reanalysis/webapp.py`](src/gba_ops_reanalysis/webapp.py)
  - web assets: [`src/gba_ops_reanalysis/webapp_assets/`](src/gba_ops_reanalysis/webapp_assets)

### Shared configuration

- central paths and defaults: [`src/gba_ops_reanalysis/config.py`](src/gba_ops_reanalysis/config.py)
- XML parsing helpers: [`src/gba_ops_reanalysis/gba_xml.py`](src/gba_ops_reanalysis/gba_xml.py)
- population methods: [`src/gba_ops_reanalysis/population.py`](src/gba_ops_reanalysis/population.py)

## How the TIPS analysis was used

The completed TIPS analysis corresponds to:

- indication name: `TIPS`
- OPS selector prefix: `8-839.8`
- output slug: `tips_8-839-8`
- latest year: `2024`
- threshold set: `1`, `5`, `10`, `25`
- main threshold: `10`
- strict threshold: `25`
- isochrone time bins actually used in the final run: `30` and `60` minutes

The main machine-readable summary is here:

- [`outputs/indications/tips_8-839-8/report_summary.json`](outputs/indications/tips_8-839-8/report_summary.json)

The matched TIPS subcodes recorded in the final report are:

- `8-839.81`
- `8-839.82`
- `8-839.83`
- `8-839.84`
- `8-839.85`
- `8-839.86`
- `8-839.87`
- `8-839.88`
- `8-839.89`
- `8-839.8a`
- `8-839.8x`
- `8-839.8X`

In practice, the TIPS workflow used the generic builders rather than a TIPS-only custom script. The effective sequence was:

1. Build the indication report from the XML folders.
2. Add the supplemental analyses on the created report folder.
3. Generate the notebook that reads directly from the report folder.
4. Generate the static dashboard from the same report folder.

## Recreate or extend the TIPS analysis

Use the repo-local environment first:

```bash
cd /Users/larsmasanneck/coding_projects/GBA_OPS_Reanalysis
source .venv/bin/activate
```

Rebuild the core TIPS report:

```bash
python scripts/build_indication_report.py \
  --indication-name TIPS \
  --label tips \
  --ops-selector 8-839.8 \
  --base-xml-dir data/xml \
  --latest-year 2024 \
  --threshold 1 \
  --threshold 5 \
  --threshold 10 \
  --threshold 25 \
  --main-threshold 10 \
  --strict-threshold 25 \
  --time-bin 30 \
  --time-bin 60 \
  --report-dir outputs/indications/tips_8-839-8
```

Rebuild the supplemental analyses:

```bash
python scripts/build_indication_supplement.py \
  --report-dir outputs/indications/tips_8-839-8
```

Refresh the notebook:

```bash
python scripts/write_indication_notebook.py \
  --notebook output/jupyter-notebook/tips-ops-8-839-8-analysis.ipynb \
  --title "TIPS OPS 8-839.8 analysis" \
  --report-dir outputs/indications/tips_8-839-8 \
  --indication-name TIPS \
  --ops-selector 8-839.8 \
  --latest-year 2024 \
  --main-threshold 10 \
  --strict-threshold 25 \
  --case-col tips_cases
```

Refresh the static dashboard:

```bash
python scripts/build_indication_webapp.py \
  --report-dir outputs/indications/tips_8-839-8 \
  --output-dir webapp/tips-ops-8-839-8 \
  --title "TIPS OPS 8-839.8 Dashboard"
```

## What to open first if you need something quickly

If the goal is to understand the finished TIPS analysis quickly, start here:

- human-readable summary: [`outputs/indications/tips_8-839-8/SUMMARY.md`](outputs/indications/tips_8-839-8/SUMMARY.md)
- machine-readable metadata: [`outputs/indications/tips_8-839-8/report_summary.json`](outputs/indications/tips_8-839-8/report_summary.json)
- notebook: [`output/jupyter-notebook/tips-ops-8-839-8-analysis.ipynb`](output/jupyter-notebook/tips-ops-8-839-8-analysis.ipynb)
- dashboard: [`webapp/tips-ops-8-839-8/index.html`](webapp/tips-ops-8-839-8/index.html)

If the goal is to grab key tables:

- yearly trend table: [`outputs/indications/tips_8-839-8/tables/yearly_summary.csv`](outputs/indications/tips_8-839-8/tables/yearly_summary.csv)
- threshold summary: [`outputs/indications/tips_8-839-8/tables/latest_year_threshold_summary.csv`](outputs/indications/tips_8-839-8/tables/latest_year_threshold_summary.csv)
- latest-year center list: [`outputs/indications/tips_8-839-8/tables/latest_year_hospital_code_totals.csv`](outputs/indications/tips_8-839-8/tables/latest_year_hospital_code_totals.csv)
- geocoded latest-year centers: [`outputs/indications/tips_8-839-8/tables/latest_year_geocoded_all_centers.csv`](outputs/indications/tips_8-839-8/tables/latest_year_geocoded_all_centers.csv)
- state summary: [`outputs/indications/tips_8-839-8/tables/latest_year_state_summary.csv`](outputs/indications/tips_8-839-8/tables/latest_year_state_summary.csv)
- urban-rural summary: [`outputs/indications/tips_8-839-8/tables/latest_year_urban_summary.csv`](outputs/indications/tips_8-839-8/tables/latest_year_urban_summary.csv)
- longitudinal hospital-year table: [`outputs/indications/tips_8-839-8/tables/hospital_year.csv`](outputs/indications/tips_8-839-8/tables/hospital_year.csv)
- longitudinal IK-year table: [`outputs/indications/tips_8-839-8/tables/ik_year.csv`](outputs/indications/tips_8-839-8/tables/ik_year.csv)

If the goal is to grab access and geography outputs:

- `>=10` isochrone centers: [`outputs/indications/tips_8-839-8/geo/isochrones_ge_10_centers.geojson`](outputs/indications/tips_8-839-8/geo/isochrones_ge_10_centers.geojson)
- `>=10` isochrone unions: [`outputs/indications/tips_8-839-8/geo/isochrones_ge_10_unions.geojson`](outputs/indications/tips_8-839-8/geo/isochrones_ge_10_unions.geojson)
- `>=25` isochrone centers: [`outputs/indications/tips_8-839-8/geo/isochrones_ge_25_centers.geojson`](outputs/indications/tips_8-839-8/geo/isochrones_ge_25_centers.geojson)
- `>=25` isochrone unions: [`outputs/indications/tips_8-839-8/geo/isochrones_ge_25_unions.geojson`](outputs/indications/tips_8-839-8/geo/isochrones_ge_25_unions.geojson)
- state access context: [`outputs/indications/tips_8-839-8/tables/state_access_context.csv`](outputs/indications/tips_8-839-8/tables/state_access_context.csv)
- county access context: [`outputs/indications/tips_8-839-8/tables/county_access_context.csv`](outputs/indications/tips_8-839-8/tables/county_access_context.csv)
- state population coverage: [`outputs/indications/tips_8-839-8/tables/state_population_coverage_ge_25.csv`](outputs/indications/tips_8-839-8/tables/state_population_coverage_ge_25.csv)
- county population coverage: [`outputs/indications/tips_8-839-8/tables/county_population_coverage_ge_25.csv`](outputs/indications/tips_8-839-8/tables/county_population_coverage_ge_25.csv)

If the goal is to grab publication-style figures:

- figures folder: [`outputs/indications/tips_8-839-8/figures/`](outputs/indications/tips_8-839-8/figures)
- multipanel isochrone figure: [`outputs/indications/tips_8-839-8/figures/17_isochrone_multipanel_thresholds.png`](outputs/indications/tips_8-839-8/figures/17_isochrone_multipanel_thresholds.png)
- state and county context panel: [`outputs/indications/tips_8-839-8/figures/18_state_county_access_context.png`](outputs/indications/tips_8-839-8/figures/18_state_county_access_context.png)
- county population coverage panel: [`outputs/indications/tips_8-839-8/figures/19_county_population_coverage_multipanel.png`](outputs/indications/tips_8-839-8/figures/19_county_population_coverage_multipanel.png)

## External dependencies that are not fully committed here

### OpenRouteService

Isochrone generation depends on a reachable ORS instance.

- default URL in config: `http://localhost:8080/ors`
- configured in: [`src/gba_ops_reanalysis/config.py`](src/gba_ops_reanalysis/config.py)

### Population raster

Population-based analyses will use one of these in order:

1. `GBA_OPS_POP_RASTER` environment variable
2. a local file in [`spatial/`](spatial)
3. a fallback path into the original GeoStroke project

The fallback logic is defined in:

- [`src/gba_ops_reanalysis/config.py`](src/gba_ops_reanalysis/config.py)

So: population-based methods are implemented in this repo, but the raster itself may still be external if it was not copied locally.

### Geocoding services

If a hospital address is not already cached, geocoding may call:

- Nominatim
- ArcGIS

This logic lives in:

- [`src/gba_ops_reanalysis/geocoding.py`](src/gba_ops_reanalysis/geocoding.py)

If you want reproducibility without network calls, keep and reuse the local geocode cache.

## Practical answer for future agents

If you only need to inspect the finished TIPS work, you do not need the original GeoStroke folder. Everything important for the finished report is already here:

- report outputs
- notebook
- web app
- reusable scripts
- reusable package code
- XML inputs
- spatial boundary assets
- SMOD raster

You only need to reach outside this repo if you want to:

- recompute isochrones without a running ORS service
- recompute population-based outputs without a local or configured population raster
- geocode uncached hospitals without internet access or a prefilled cache

## Recommended first-read files for a new agent

- [`README.md`](README.md)
- [`TIPS_REPOSITORY_GUIDE.md`](TIPS_REPOSITORY_GUIDE.md)
- [`outputs/indications/tips_8-839-8/SUMMARY.md`](outputs/indications/tips_8-839-8/SUMMARY.md)
- [`outputs/indications/tips_8-839-8/report_summary.json`](outputs/indications/tips_8-839-8/report_summary.json)
- [`src/gba_ops_reanalysis/config.py`](src/gba_ops_reanalysis/config.py)

