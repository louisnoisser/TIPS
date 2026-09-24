# TIPS pre-submission code snapshot provenance

## Purpose

This repository is an independent, curated code and audit snapshot prepared for a subsequent independent review. It must not be interpreted as proof that every manuscript result can be reproduced from the files included here.

## Source

- Source repository: `https://github.com/MasanneckLab/GBA_OPS_Reanalysis`
- Source working directory: `/Users/LouisNoisser/Documents/GitHub/GBA_OPS_Reanalysis`
- Source branch at snapshot time: `main`
- Source basis commit: `e162c991af5d699d169240b903a1c35cbb4df5f9`
- Expected basis commit supplied for the snapshot: `e162c991af5d699d169240b903a1c35cbb4df5f9`
- Basis comparison: exact match
- Remote state observed before snapshot: `origin/main` was 33 commits ahead at `7946f4d0c78d9ce58bb72544dec596fea1e74c46`
- The 33 newer laboratory-repository commits were not merged, rebased, copied or otherwise incorporated.
- Relevant uncommitted TIPS working-tree files were copied from their current filesystem state.
- The source `.git` directory, Git index, branches, remotes and history were not copied.

The source repository was read only while this snapshot was assembled. A separate Git history was initialized in a new directory.

## Included scope

- Reusable TIPS and generic OPS analysis modules needed by the current workflow
- TIPS-oriented command-line scripts and audit scripts
- Relevant automated tests
- Python dependency and packaging metadata
- Repository documentation and handoff guidance
- Compact analytical CSV, JSON, Markdown and text outputs for the current TIPS workflow
- The 2024 geographic suppression sensitivity analysis, its QA records, provenance report and manifest
- OPS mapping, site-resolution, de-novo, suppression, geography and accessibility audit records selected for independent review

`SHA256_MANIFEST.csv` records the relative path, byte size and SHA-256 digest of every committed snapshot file except the manifest itself.

## Deliberately excluded inputs and artefacts

The following local material was deliberately not copied:

- G-BA source XML files under `data/xml/`
- BfArM catalogue downloads and archives under `ops_bfarm_2013_2024/`
- GHS-POP and GHS-SMOD rasters and other large spatial data under `spatial/`
- OpenStreetMap extracts, OpenRouteService graphs, container runtime data and logs under `ors-docker/`
- Geocoding, population and isochrone caches under `data/cache/`
- Python virtual environments, bytecode, test caches and operating-system metadata
- Large generated figures, raster products, GeoJSON geometry banks and ZIP archives
- Manuscript, supplement, submission, correspondence, internal-comment and caption-draft files
- The previously tracked legacy output directory that is deleted in the source working tree

Complete reruns may require the excluded G-BA XML inputs, the year-specific BfArM catalogues, the population and settlement rasters, the Germany boundary data, validated geocoding inputs and the persisted OpenRouteService isochrones or an equivalent routing environment. Their absence is an explicit reproducibility boundary of this snapshot.

## Licence and attribution

No root `LICENSE`, `COPYING` or `NOTICE` file and no explicit project licence declaration were found in the source repository at snapshot time. This snapshot preserves existing source headers and attribution text but does not add or imply a new licence for code originating from `MasanneckLab/GBA_OPS_Reanalysis` or for third-party material. The snapshot was created under the repository user's explicit authorization for private audit preservation.

## Target

- Personal repository: `https://github.com/louisnoisser/TIPS`
- Visibility at preflight: private, established because the unauthenticated GitHub API returned not found while authenticated Git access resolved the repository
- Existing target history: preserved
- Snapshot branch: `tips/pre-submission-2026-09`
- Relationship to target `main`: independent and intentionally unrelated history

