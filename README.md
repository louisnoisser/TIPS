# TIPS analysis code

This private repository is a clean source snapshot of the German G-BA TIPS
analysis workspace. It contains the current reusable Python implementation,
TIPS-specific analysis entrypoints, tests, and a small evidence subset from the
completed OPS `8-839.8*` catalogue audit.

## Provenance and scope

This is an independent snapshot, not a fork or mirror. It does not contain the
original organization repository's Git history. The source working-tree HEAD
at export time was:

`e162c991af5d699d169240b903a1c35cbb4df5f9`

Large source data, hospital XML files, BfArM/DIMDI catalogue files, routing
graphs, OSM extracts, elevation caches, population rasters, generated reports,
publication assets, archives, backups, and virtual environments are not
included. Their redistribution status is not asserted here.

See [SNAPSHOT_PROVENANCE.md](SNAPSHOT_PROVENANCE.md) for the export boundary
and portability notes.

## Included components

- `src/gba_ops_reanalysis/`: reusable parsing, longitudinal, geographic,
  reporting, site-resolution, suppression, and OPS-validation modules required
  by the TIPS workflow.
- `scripts/`: generic pipeline entrypoints and TIPS-specific validation and
  reporting scripts.
- `audits/ops_code_audit_2013_2024/`: the two audit implementations. Running
  them requires primary sources and intermediate evidence that are deliberately
  excluded from this repository.
- `tests/`: focused tests for the final correction, OPS validation, geography,
  site resolution, and suppression logic.
- `outputs/ops_code_audit_2013_2024/`: selected small derived audit tables and
  reports only; no ClaML XML, PDFs, ZIP archives, backups, or manual-review
  package.

## Environment

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

The repository includes both self-contained tests and regression checks against
excluded analysis assets. In the clean snapshot, the initial test run reports
25 passing tests; the remaining checks stop on missing external catalogue,
site-resolution, geography-release, or publication-output files. Supply those
inputs locally before using the complete regression suite as a release gate.

## External inputs

The analysis code expects inputs supplied locally by an authorized user:

- annual G-BA quality-report XML folders, conventionally under `data/xml/`;
- required boundary files under `spatial/`;
- GHS settlement/population rasters supplied through the documented local paths
  or `GBA_OPS_SMOD_RASTER` and `GBA_OPS_POP_RASTER`;
- a local OpenRouteService deployment using the `driving-car` profile, normally
  reached through `GBA_OPS_ORS_URL`.

These locations are ignored by Git. The code creates generated output and cache
directories locally as needed.

## OPS audit evidence

The selected audit evidence preserves exact code strings, official titles,
classification judgments, row hashes, and source-file hashes. It contains no
embedded ClaML XML. Some inventory and manifest fields retain absolute paths
from the original audit run solely as historical provenance; those paths are
not portable and do not imply that the referenced source files are included.

The 2026-08-17 checkpoint adds the completed de-novo sensitivity and
193/113-site accessibility analysis code together with selected small aggregate
QA, provenance, and reporting tables. Site-level source data, routing
geometries, figures, rasters, catalogues, and other large generated artefacts
remain excluded.
