# GBA OPS Reanalysis

This repository is a reusable, script-first workspace for reanalyzing German G-BA hospital quality-report XML files across arbitrary OPS and ICD selections.

It standardizes the workflows that were previously spread across project-specific notebooks:

1. OPS/ICD center extraction with thresholds, in the style of the `AUDEBERT` work.
2. Center geocoding from XML-derived hospital addresses.
3. Isochrone generation for selected center cohorts.
4. Urban/rural summaries for center locations and isochrone coverage.
5. Population-based isochrone coverage and population-adjusted state summaries.
6. Longitudinal hospital-year and yearly summary outputs across all available `xml_<year>` folders.

## What this repo is for

Use this repository if you want to rerun the G-BA analyses for:

- different OPS codes,
- different ICD denominators,
- different case thresholds,
- single-year center analyses,
- or longitudinal analyses across all available XML years.

The design goal is to avoid editing notebooks whenever the clinical code set changes.
You should be able to rerun most analyses by changing command-line arguments only.

## Repository layout

- `data/xml/`: copied G-BA XML year folders.
- `data/derived/`: parsed hospital tables and threshold cohorts.
- `data/geocoded/`: geocoded center tables.
- `data/cache/`: reusable caches, including isochrone pickles.
- `spatial/`: small spatial assets used by the scripts.
- `src/gba_ops_reanalysis/`: reusable parsing and analysis package.
- `scripts/`: command-line entrypoints for the standard workflows.
- `webapp/`: generated static dashboards for indication reports.

## Included data

This repo already contains:

- `data/xml/xml_2008` to `data/xml/xml_2024`
- Germany outline, state, and county files in `spatial/`
- the SMOD raster used for urban/rural classification in `spatial/`
- report/supplement scripts that can add population-weighted access summaries when a GHS population raster is available

It does not ship with a committed virtual environment, but a local `.venv` can be created in the repo root and is ignored by Git.

## Setup

### 1. Create and activate the environment

Use Python 3.11 or newer. On this machine, `python3` currently resolves to 3.9, so use the explicit pyenv interpreter path or any other Python 3.11+ binary.

```bash
cd /Users/larsmasanneck/coding_projects/GBA_OPS_Reanalysis
/Users/larsmasanneck/.pyenv/versions/3.11.11/bin/python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 2. Check the environment

```bash
python -c "import pandas, geopandas, rasterio, shapely, requests; print('environment ok')"
```

### 3. Optional: check ORS before isochrones

```bash
python scripts/generate_isochrones.py \
  --input data/derived/xml_2024/centers_above_thresholds.csv \
  --test-only
```

If ORS is not running, isochrone generation will fail until the service is available.

## Core workflow

In practice, most analyses follow this order:

1. Extract OPS and ICD counts from one XML year.
2. Filter hospitals by threshold.
3. Geocode the selected hospitals.
4. Generate isochrones for the selected cohort.
5. Run urban/rural summaries.
6. Optionally run the longitudinal pipeline across all year folders.

## Standard commands

### 1. Extract OPS/ICD center tables

Example for IVT and MT with an `I63` denominator from `xml_2024`:

```bash
python scripts/extract_ops_icd_centers.py \
  --xml-dir data/xml/xml_2024 \
  --ops-target ivt=8-020.8 \
  --ops-target mt=8-836.80 \
  --icd-target i63=I63 \
  --threshold 10 \
  --threshold 25 \
  --denominator-label i63
```

This writes:

- `data/derived/xml_2024/hospital_code_totals.csv`
- `data/derived/xml_2024/ops_target_summary.csv`
- `data/derived/xml_2024/centers_above_thresholds.csv`
- `data/derived/xml_2024/target_metadata.json`

Important output fields:

- `ops_target_summary.csv`: one line per OPS target with total cases and hospitals above each threshold
- `centers_above_thresholds.csv`: one line per selected center cohort entry
- `hospital_code_totals.csv`: full hospital-level counts before threshold filtering

### 2. Geocode a threshold cohort

Geocode all extracted threshold cohorts:

```bash
python scripts/geocode_centers.py \
  --input data/derived/xml_2024/centers_above_thresholds.csv \
  --output data/geocoded/xml_2024_centers_geocoded.csv
```

Geocode only one target and threshold:

```bash
python scripts/geocode_centers.py \
  --input data/derived/xml_2024/centers_above_thresholds.csv \
  --target-label ivt \
  --threshold 25 \
  --output data/geocoded/xml_2024_ivt_ge25_geocoded.csv
```

This adds:

- `latitude`
- `longitude`
- `geocode_source`
- `geocode_query`

### 3. Generate isochrones

```bash
python scripts/generate_isochrones.py \
  --input data/geocoded/xml_2024_ivt_ge25_geocoded.csv \
  --target-label ivt \
  --threshold 25 \
  --time-bins 15 30 45 60 \
  --tag ivt_2024_ge25
```

This writes:

- `outputs/isochrones/ivt_2024_ge25_centers.geojson`
- `outputs/isochrones/ivt_2024_ge25_unions.geojson`
- `outputs/isochrones/ivt_2024_ge25_meta.json`
- cached polygon pickles in `data/cache/isochrones/`

If you want to rerun without cache:

```bash
python scripts/generate_isochrones.py \
  --input data/geocoded/xml_2024_ivt_ge25_geocoded.csv \
  --target-label ivt \
  --threshold 25 \
  --time-bins 15 30 45 60 \
  --tag ivt_2024_ge25 \
  --force-recalc
```

### 4. Run urban/rural summaries

Point-based center classification:

```bash
python scripts/run_urban_rural_analysis.py \
  --points-csv data/geocoded/xml_2024_centers_geocoded.csv \
  --lon-col longitude \
  --lat-col latitude
```

Isochrone coverage summary:

```bash
python scripts/run_urban_rural_analysis.py \
  --union-geojson outputs/isochrones/ivt_2024_ge25_unions.geojson \
  --grid-resolution 0.05
```

This produces:

- point-level files ending in `_urban_rural.csv`
- point summaries ending in `_urban_rural_summary.csv`
- union coverage summaries ending in `_urban_rural_coverage.csv`

### 5. Build longitudinal summaries

```bash
python scripts/build_longitudinal_summary.py \
  --base-dir data/xml \
  --ops-target ivt=8-020.8 \
  --ops-target mt=8-836.80 \
  --icd-target i63=I63 \
  --denominator-label i63
```

This writes:

- `outputs/longitudinal/gba_longitudinal_hospital_year.csv`
- `outputs/longitudinal/gba_longitudinal_yearly_summary.csv`
- `outputs/longitudinal/gba_longitudinal_schema_check.csv`
- `outputs/longitudinal/gba_longitudinal_sources.json`

### 6. Build a static web dashboard

Once an indication report exists under `outputs/indications/<slug>/`, you can turn it into a self-contained local dashboard:

```bash
python scripts/build_indication_webapp.py \
  --report-dir outputs/indications/tips_8-839-8 \
  --output-dir webapp/tips-ops-8-839-8 \
  --title "TIPS OPS 8-839.8 Dashboard"
```

This writes:

- `webapp/tips-ops-8-839-8/index.html`
- `webapp/tips-ops-8-839-8/data.js`
- `webapp/tips-ops-8-839-8/assets/figures/*.png`

The dashboard is static and can be opened directly in a browser from the generated `index.html`.
If you prefer serving it over HTTP:

```bash
cd /Users/larsmasanneck/coding_projects/GBA_OPS_Reanalysis
python -m http.server 8765
```

Then open:

- `http://127.0.0.1:8765/webapp/tips-ops-8-839-8/index.html`

### 7. Build the interactive ICD/OPS quality-report explorer

This repository now also includes a lightweight FastAPI dashboard for the most recent locally available G-BA report year. It builds a searchable ICD/OPS code index, geocodes all hospitals, precomputes 15/30/45/60 minute isochrones per unique hospital coordinate, and serves an interactive Germany map plus unioned isochrone map.

The dashboard supports two entry modes:

- curated clinical concepts for lay-oriented exploration, for example `Stroke or TIA`, `Mechanical thrombectomy`, or `Hip replacement surgery`
- free ICD/OPS prefix search for advanced users who want to work directly with raw report codes

Build the latest-year explorer dataset:

```bash
python scripts/build_quality_dashboard.py \
  --batch-size 10 \
  --workers 4
```

By default this writes to:

- `outputs/dashboard/quality_report_explorer_<latest-year>/quality_dashboard.db`
- `outputs/dashboard/quality_report_explorer_<latest-year>/metadata.json`
- `outputs/dashboard/quality_report_explorer_<latest-year>/geography/*.geojson`

Run the local app:

```bash
python scripts/run_quality_dashboard.py \
  --host 127.0.0.1 \
  --port 8011
```

Then open:

- `http://127.0.0.1:8011`

Useful options:

- `--xml-dir data/xml/xml_2024` to force a specific report year
- `--output-dir outputs/dashboard/quality_report_explorer_2024` to point the app at an already-built dataset
- `--force-reindex`, `--force-geocode`, or `--force-isochrones` to rebuild specific cache layers

API endpoints exposed by the explorer:

- `/api/health`
- `/api/bootstrap`
- `/api/search?code_type=ops&q=8-839`
- `/api/query?code_type=icd&code=I63&threshold=50`
- `/api/query?concept_id=stroke_any_icd&threshold=50`

### 8. Run the explorer in Docker

The included `Dockerfile` keeps the image small and expects the prebuilt dashboard dataset to be mounted into the container.

Build the image:

```bash
docker build -t gba-quality-dashboard .
```

Run it against the built explorer dataset:

```bash
docker run --rm \
  -p 8000:8000 \
  -e GBA_QUALITY_DASHBOARD_DIR=/data/dashboard \
  -v /Users/larsmasanneck/coding_projects/GBA_OPS_Reanalysis/outputs/dashboard/quality_report_explorer_2024:/data/dashboard:ro \
  gba-quality-dashboard
```

Then open:

- `http://127.0.0.1:8000`

If you rebuild the dataset for a different year, just mount that output directory instead.

## Examples for other OPS reanalyses

### Example: broader thrombectomy code family

```bash
python scripts/extract_ops_icd_centers.py \
  --xml-dir data/xml/xml_2024 \
  --ops-target mt_broad=8-836.8 \
  --icd-target i63=I63 \
  --threshold 10 \
  --threshold 25 \
  --threshold 50 \
  --denominator-label i63
```

### Example: stroke unit procedure codes

```bash
python scripts/extract_ops_icd_centers.py \
  --xml-dir data/xml/xml_2024 \
  --ops-target su_regional=8-98b \
  --ops-target su_extended=8-981 \
  --icd-target stroke_all=I60-I64,G45,!G45.4 \
  --threshold 25 \
  --threshold 100 \
  --denominator-label stroke_all
```

### Example: single custom cohort workflow

```bash
python scripts/extract_ops_icd_centers.py \
  --xml-dir data/xml/xml_2024 \
  --ops-target custom=8-020.8 \
  --icd-target i63=I63 \
  --threshold 25 \
  --denominator-label i63

python scripts/geocode_centers.py \
  --input data/derived/xml_2024/centers_above_thresholds.csv \
  --target-label custom \
  --threshold 25 \
  --output data/geocoded/custom_2024_ge25.csv

python scripts/generate_isochrones.py \
  --input data/geocoded/custom_2024_ge25.csv \
  --target-label custom \
  --threshold 25 \
  --time-bins 15 30 45 60 \
  --tag custom_2024_ge25

python scripts/run_urban_rural_analysis.py \
  --points-csv data/geocoded/custom_2024_ge25.csv

python scripts/run_urban_rural_analysis.py \
  --union-geojson outputs/isochrones/custom_2024_ge25_unions.geojson
```

## Selector syntax

`--ops-target` and `--icd-target` use `label=selector` syntax.

Selectors accept comma-separated tokens:

- `8-020.8`: prefix match
- `I63`: prefix match
- `I60-I64`: inclusive range
- `G45,!G45.4`: include `G45*`, exclude `G45.4*`

The matching is prefix-based unless you use a range.

Examples:

- `mt=8-836.80` matches `8-836.80*`
- `mt_broad=8-836.8` matches the broader thrombectomy family
- `stroke_all=I60-I64,G45,!G45.4` reproduces the broader stroke/TIA convention

## Spatial assets

The repository is set up to copy the small boundary files into `spatial/`.
The default SMOD raster path is:

- `spatial/GHS_SMOD_E2025_GLOBE_R2023A_54009_1000_V2_0.tif`

You can override it with:

```bash
export GBA_OPS_SMOD_RASTER=/absolute/path/to/your/smod.tif
```

Population-based access summaries use the GHS population raster. The repo first looks for:

- `spatial/GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif`

If that file is not present, it can be set explicitly with:

```bash
export GBA_OPS_POP_RASTER=/absolute/path/to/your/GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif
```

On this machine, the code also falls back to the original GeoStroke raster path if that file exists.

The ORS endpoint defaults to `http://localhost:8080/ors` and can be overridden with:

```bash
export GBA_OPS_ORS_URL=http://localhost:8080/ors
```

## Important notes

- The extraction scripts intentionally focus on `*-xml.xml` report files for case-based analysis.
- Geocoding uses public providers and local CSV caching. The first run is slower than later reruns.
- Isochrone generation depends on a reachable ORS instance.
- Population-based access outputs depend on a reachable population raster via `GBA_OPS_POP_RASTER` or the local fallback path.
- The longitudinal pipeline can take a while across all year folders because it parses every report file.
- `.venv`, `data/geocoded/`, `data/derived/`, `data/cache/`, and `outputs/` are intended as local working artifacts.

## Full indication reports

For a reusable indication-specific output folder with tables, figures, geo files, and a notebook-ready summary:

```bash
python scripts/build_indication_report.py \
  --indication-name TIPS \
  --label tips \
  --ops-selector 8-839.8 \
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

Then add supplemental outputs, including concentration, churn, and population-based access summaries:

```bash
python scripts/build_indication_supplement.py \
  --report-dir outputs/indications/tips_8-839-8
```

The supplement step writes, among others:

- `tables/isochrone_population_coverage_ge_10.csv`
- `tables/isochrone_population_coverage_ge_25.csv`
- `tables/population_tradeoff_ge_10_vs_ge_25.csv`
- `tables/latest_year_state_population_rates.csv`
- `figures/15_population_coverage_ge_10_vs_ge_25.png`
- `figures/16_state_case_rates_per_million.png`

## Recommended first run

If you just want to confirm the repo works end-to-end, run this exact sequence:

```bash
source .venv/bin/activate

python scripts/extract_ops_icd_centers.py \
  --xml-dir data/xml/xml_2024 \
  --ops-target ivt=8-020.8 \
  --ops-target mt=8-836.80 \
  --icd-target i63=I63 \
  --threshold 10 \
  --threshold 25 \
  --denominator-label i63

python scripts/geocode_centers.py \
  --input data/derived/xml_2024/centers_above_thresholds.csv \
  --target-label ivt \
  --threshold 25 \
  --output data/geocoded/xml_2024_ivt_ge25_geocoded.csv

python scripts/generate_isochrones.py \
  --input data/geocoded/xml_2024_ivt_ge25_geocoded.csv \
  --target-label ivt \
  --threshold 25 \
  --time-bins 15 30 \
  --tag ivt_2024_ge25_test

python scripts/run_urban_rural_analysis.py \
  --points-csv data/geocoded/xml_2024_ivt_ge25_geocoded.csv

python scripts/run_urban_rural_analysis.py \
  --union-geojson outputs/isochrones/ivt_2024_ge25_test_unions.geojson \
  --grid-resolution 0.1
```
