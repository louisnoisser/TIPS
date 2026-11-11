# Clean snapshot provenance

- Export date: 2026-08-03
- Source repository branch: `main`
- Source repository HEAD: `e162c991af5d699d169240b903a1c35cbb4df5f9`
- Snapshot basis: current source working tree, including appropriate uncommitted
  source and test files
- Destination: private personal repository `louisnoisser/TIPS`

No `.git` directory, commit, branch, tag, remote, or other Git metadata from the
source repository was copied. This repository begins with one independent root
commit.

## Deliberate exclusions

The snapshot excludes hospital-level XML source data, official BfArM/DIMDI
catalogue XML/PDF/ZIP files, ORS graphs and caches, OSM extracts, elevation
data, population rasters, generated result and publication folders, generated
webapp data, backups, manual-review packages, environments, caches, operating-
system files, credentials, and temporary files.

The 68 absent tracked files from the legacy
`outputs/indications/tips_8-839-8/` directory were obsolete generated outputs.
They were neither restored nor reproduced. Included code generates outputs from
external inputs and does not require those specific deleted files. The excluded
legacy repository guide and README did contain links to them; both were replaced
by snapshot-specific documentation.

## Snapshot-only portability adjustment

The copied `src/gba_ops_reanalysis/config.py` was adjusted only in this clean
repository to remove a legacy absolute path into another user's home directory.
The copied audit continuation script now derives the optional analysis search
directory from `Path.home()` instead of embedding the export machine's home
directory. Population data are resolved from `GBA_OPS_POP_RASTER` or the
conventional local `spatial/` path. The source working tree was not modified.

## Audit evidence boundary

Selected small derived audit CSV, JSON, and Markdown files are retained under
`outputs/ops_code_audit_2013_2024/`. Primary ClaML sources, reconciliation raw
tables not selected for the snapshot, backups, and the manual-review package
are excluded. Absolute paths within retained inventory/manifest fields document
the original audit environment and are nonportable historical metadata.

## Verification at export

All 49 included Python files parsed successfully, and all local package imports
resolved within the selected module closure. The secret scan found no private
keys or recognizable populated GitHub, analysis, AWS, or generic credential
patterns. No embedded ClaML XML was found in the selected audit evidence.

The isolated test run produced 25 passes, 14 failures, and 19 setup errors. The
non-passing checks require deliberately excluded source catalogues or generated
site-resolution, geographic release, and publication-output files. These
external-data dependencies are retained as regression tests rather than being
silently weakened or supplied with copied organization data.

## Checkpoint update: 2026-08-17

The checkpoint at source HEAD `e162c991af5d699d169240b903a1c35cbb4df5f9`
adds the current de-novo sensitivity, late-stage geographic validation, and
193/113-site accessibility scripts. It also retains selected small aggregate
reports, QA tables, manifests, and manuscript-candidate text needed to document
those completed analyses.

The update continues to exclude site-level membership and routing tables,
individual and union geometries, figures, Word files, source XML, official
catalogue files, ORS configuration and runtime data, OSM/elevation assets,
population rasters, archives, and other bulky generated outputs. No source
repository Git metadata or history was copied.


## September 2026 analysis update — 2026-10-19

This update copies the current working-tree versions from
`GBA_OPS_Reanalysis` at source HEAD
`e162c991af5d699d169240b903a1c35cbb4df5f9`:

- `scripts/run_tips_geographic_suppression_sensitivity_2026_09_23.py`;
- the nine non-archive files in
  `outputs/tips_geographic_suppression_sensitivity_2026-09-23/`;
- `scripts/build_late_stage_revision_2026_08_14.py`, including the
  source's 5 September revision;
- `outputs/late_stage_accessibility_193_113_recovery_2026-08-15/sha256_manifest.csv`,
  including the source's 5 September manifest revision.

The source repository and its working files are unchanged. The existing
personal-repository configuration, README, ignore rules, and earlier commits
are retained. No raw XML, routing payloads, raster data, archives, or additional
analysis products are included. The separate 2012 correction has not been
applied by this update.


## Validated 2012 analysis correction — 2026-10-19

This update imports the explicitly selected code and evidence from the separate
validated correction working copy dated 15 October 2026
(`GBA_OPS_Reanalysis_fix2012_2026-10-15`). The original analysis repository and
its working files are not modified.

Report-file selection now also recognizes the upper-case `-XML.xml` suffix.
The additional source report for Potsdam, `261200220-00`, contributes ten visible
procedure occurrences in 2012. The annual visible total changes from 2110 to
2120; all other reporting years remain unchanged, including 2024. Procedure
records are not deduplicated or imputed. Case-normalized filename collisions
are accepted only for identical file contents; divergent contents raise an error.

The update contains ten explicitly selected source/test files and 33 small
validation-evidence files under `outputs/tips_2012_filefix_2026-10-15/`.
It includes the report-selection regression tests and corrected-total checks,
plus the selected existing export/input parametrization needed to reuse the
validated analysis code. No archive, raw XML dataset, manuscript, or new routing
or geocoding product is included.

The following one-off validation scripts are deliberately not imported:

- `scripts/inspect_fix2012_documents.py`: local manuscript/spreadsheet inspection,
  outside the reusable analysis code.
- `scripts/check_fix2012_visuals.py`: local comparison of old/new publication
  images and document extracts.
- `scripts/finalize_fix2012_report.py`: environment-specific report/manifest
  assembly for the complete correction working copy.
- `scripts/check_fix2012_geography.py`: separate geographic-percentage audit
  relying on local document extracts; selected aggregate evidence is retained.
- `scripts/run_fix2012_production.py`: one-off production driver with correction-
  workspace assumptions and source-writing behavior, not a portable entry point.
- `tests/test_fix2012_production.py`: integration checks requiring the full
  correction-output directory rather than this deliberately reduced selection.

`config.py` is deliberately not imported: the existing personal-repository
configuration and its portability adjustment remain unchanged.

The full validation manifest from the correction working copy describes the
larger original validation package, not this smaller 33-file evidence selection.
It is not imported and must not be treated as a manifest of this snapshot.
The retained historical test reports document the complete validation run of
15 October 2026, including checks whose one-off scripts are intentionally absent.


## Submission release — 2026-11-11

The release adds the locked derived CSV inputs and saved geometries needed for
manuscript figures and tables, the corrected site-resolution inputs from the
validated 15 October correction, the checked Figure S1 labels, and a single offline
rendering entrypoint. C193 is the manuscript Figure 4 (see v1.0.1-submission); C113 is an earlier, unused alternative. An authoritative release checksum inventory is provided in
reproducibility/locked_outputs_sha256.csv. Earlier manifests remain historical.

Workflow-attribution metadata was standardized in the current distributed files;
scientific numeric values and calculation formulas were not changed. Where a
CSV's annotation metadata changed, its release checksum is updated accordingly.
Existing Git commits remain unchanged. Raw XML, population/settlement rasters,
archives and routing container data remain excluded. Environment setup, primary
source acquisition and the limits of exact historical routing reproduction are
specified in README.md. The manuscript publication link remains pending.
