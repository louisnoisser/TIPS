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
The copied audit continuation script now derives the optional Codex search
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
keys or recognizable populated GitHub, OpenAI, AWS, or generic credential
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
