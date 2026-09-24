# Late-stage geographic validation report

## A. Source integrity

All 13 locked input hashes passed exactly.

| role | path | expected_sha256 | actual_sha256 | result |
| --- | --- | --- | --- | --- |
| institutional/automatic starting coordinate or locked upstream asset | outputs/late_stage_revision_2026-08-14/late_stage_revision_report.md | 4b2807d72763835059ea6c737029cf0dd7e7d24ec627b3b751baf7c00b2f9f60 | 4b2807d72763835059ea6c737029cf0dd7e7d24ec627b3b751baf7c00b2f9f60 | PASS |
| institutional/automatic starting coordinate or locked upstream asset | scripts/build_late_stage_revision_2026_08_14.py | 6bfcc22c37745136c923def08e6b6b0896f927af55a692b337e4201ba4d81978 | 6bfcc22c37745136c923def08e6b6b0896f927af55a692b337e4201ba4d81978 | PASS |
| institutional/automatic starting coordinate or locked upstream asset | outputs/late_stage_revision_2026-08-14/revision_output_manifest.json | 81e1bcdbeaa7b6c526db39575f87d28acc30de9d6a90578087998388ae61dc66 | 81e1bcdbeaa7b6c526db39575f87d28acc30de9d6a90578087998388ae61dc66 | PASS |
| canonical set source | outputs/final_submission_assets_2026-07-24/geography/provider_locations_master_2024.csv | 646e6fe5ae3b1dff2aade2e58bc63e46d9014b45faa8976f2e4e56f4c6c2e536 | 646e6fe5ae3b1dff2aade2e58bc63e46d9014b45faa8976f2e4e56f4c6c2e536 | PASS |
| institutional/automatic starting coordinate or locked upstream asset | outputs/indications/tips_8-839-8_updated2024/tables/latest_year_geocoded_all_centers.csv | fe0f1a54796a66cebbc19ce5a982072f1346b90a15293e1389fff174544f56c0 | fe0f1a54796a66cebbc19ce5a982072f1346b90a15293e1389fff174544f56c0 | PASS |
| locked manually validated coordinates | outputs/final_submission_assets_2026-07-24/geography_manual_review_ge20_2024_completed.csv | 803e125939df1ceb6a6f72f9e6577e2726e4e20e83328ba3ae0f46edf3739061 | 803e125939df1ceb6a6f72f9e6577e2726e4e20e83328ba3ae0f46edf3739061 | PASS |
| institutional/automatic starting coordinate or locked upstream asset | outputs/late_stage_revision_2026-08-14/geo_preflight/candidate_113_panel_A_sites.csv | 352d2d180c5e443fe2b1f82557993c6de4dee6ad1a3e2e56c66a3271cf779f4f | 352d2d180c5e443fe2b1f82557993c6de4dee6ad1a3e2e56c66a3271cf779f4f | PASS |
| institutional/automatic starting coordinate or locked upstream asset | outputs/late_stage_revision_2026-08-14/geo_preflight/candidate_193_panel_A_sites.csv | f1d9515cdf7b4a6b16113f11d6651ea574bd93f03a07ee74aa77ab6bfe326d81 | f1d9515cdf7b4a6b16113f11d6651ea574bd93f03a07ee74aa77ab6bfe326d81 | PASS |
| institutional/automatic starting coordinate or locked upstream asset | outputs/late_stage_revision_2026-08-14/geo_preflight/automated_geographic_review_flags.csv | 9901a22a0f47041f47345e19f6958eb56d8004eba6a6a8952da7901cf8e8880f | 9901a22a0f47041f47345e19f6958eb56d8004eba6a6a8952da7901cf8e8880f | PASS |
| institutional/automatic starting coordinate or locked upstream asset | outputs/late_stage_revision_2026-08-14/geo_preflight/known_three_manual_corrections_crosscheck.csv | 8779ed0fd184f8b58a935754b7456d9c6c8086c3f734491455b2224bf9706137 | 8779ed0fd184f8b58a935754b7456d9c6c8086c3f734491455b2224bf9706137 | PASS |
| institutional/automatic starting coordinate or locked upstream asset | outputs/late_stage_revision_2026-08-14/figure3_comparison/Figure3_candidate_B_identifiable_network_data.csv | 53c20066b45a7b9b08a06ab6c9ac3d2992892b2832c8515a52e2822090946500 | 53c20066b45a7b9b08a06ab6c9ac3d2992892b2832c8515a52e2822090946500 | PASS |
| institutional/automatic starting coordinate or locked upstream asset | outputs/late_stage_revision_2026-08-14/figure3_comparison/Figure3_candidate_B_identifiable_network.png | b5ed804d11711958ad230847911e0dcb24c0f4d86233efb1969e4a3a7dba09be | b5ed804d11711958ad230847911e0dcb24c0f4d86233efb1969e4a3a7dba09be | PASS |
| institutional/automatic starting coordinate or locked upstream asset | outputs/late_stage_revision_2026-08-14/figure3_comparison/Figure3_candidate_B_identifiable_network.pdf | a4991b1f0a5eb8179dd7672d0d64bf7cd11b26ba5a3428647bcd9eb18bd0f9b3 | a4991b1f0a5eb8179dd7672d0d64bf7cd11b26ba5a3428647bcd9eb18bd0f9b3 | PASS |

The canonical 193-record set comes from `outputs/final_submission_assets_2026-07-24/geography/provider_locations_master_2024.csv` — SHA-256 `646e6fe5ae3b1dff2aade2e58bc63e46d9014b45faa8976f2e4e56f4c6c2e536`. The completed manual evidence for the locked 60 comes from `outputs/final_submission_assets_2026-07-24/geography_manual_review_ge20_2024_completed.csv` — SHA-256 `803e125939df1ceb6a6f72f9e6577e2726e4e20e83328ba3ae0f46edf3739061`; all 60 have `manual_status`, address confirmation and coordinate confirmation equal to `validated`, supporting their mapping to precision A without routine re-review. The 53 existing numeric and 80 automatic preview coordinates were treated only as starting values: `outputs/late_stage_revision_2026-08-14/geo_preflight/candidate_193_panel_A_sites.csv` — SHA-256 `f1d9515cdf7b4a6b16113f11d6651ea574bd93f03a07ee74aa77ab6bfe326d81`.

## B. Figure 3 finalisation

PNG: `outputs/late_stage_geo_validation_2026-08-14/figure3_finalisation/Figure3B_final_selected_legend_wording.png` — SHA-256 `91dc44063f1302e2101b78e0b72c1bd53b4857537548fd06a81380bbbd7d9aff`. PDF: `outputs/late_stage_geo_validation_2026-08-14/figure3_finalisation/Figure3B_final_selected_legend_wording.pdf` — SHA-256 `bd3fdde5702047cae35640eeed3baa4f0e20d851d72cb617b2c7887be476a938`. Exact grey-legend wording: `1–3 per code entry (suppressed)`. All data, years, stacks, colours, axes and totals are unchanged; 2008=88 and 2024=193. The supplied caption is consistent with the figure. Programmatic QA passed and the PNG/PDF were rendered for visual inspection.

## C. Review-scope reconciliation

Locked validated records=60; numeric <20 reviewed=53; suppressed-only reviewed=80; newly reviewed=133; canonical records represented=193.

## D. Numeric <20 validation

| group | records | precision_A | precision_B | precision_C | precision_D | routing_ready_yes | routing_ready_no |
| --- | --- | --- | --- | --- | --- | --- | --- |
| numeric_lt20 | 53 | 6 | 47 | 0 | 0 | 53 | 0 |

Status counts: {'READY_FOR_HUMAN_APPROVAL': 53}. Address corrections=0; coordinate corrections=5. Precision A/B/C/D={'A': 6, 'B': 47, 'C': 0, 'D': 0}; routing-ready yes/no={'yes': 53, 'no': 0}. All 33 records whose starting coordinates had institution-level provenance were resolved to their explicit G-BA clinical site/address; remaining institution-level coordinate concerns=0. The five-record Vivantes cluster was resolved as distinct G-BA sites with five corrected clinical-address coordinates. Duplicate/alias concerns=0; institution-level artefact concerns=0.

## E. Suppressed-only validation

| group | records | precision_A | precision_B | precision_C | precision_D | routing_ready_yes | routing_ready_no |
| --- | --- | --- | --- | --- | --- | --- | --- |
| suppressed_only | 80 | 18 | 62 | 0 | 0 | 80 | 0 |

Status counts: {'READY_FOR_HUMAN_APPROVAL': 80}. Address corrections=1; coordinate corrections=2. Precision A/B/C/D={'A': 18, 'B': 62, 'C': 0, 'D': 0}; routing-ready yes/no={'yes': 80, 'no': 0}. All 80 inclusive OPS-family memberships, suppressed-only definitions and explicit physical-site reporting statuses were confirmed from the corresponding 2024 G-BA structured reports. All 80 automatic previews were upgraded to A/B only after the authoritative G-BA clinical address was established and the coordinate was shown to resolve to that address/campus; remaining C/D=0. Institution-level artefact concerns=0; duplicates against the numeric network=0; duplicates within the suppressed-only set=0.

## F. Set integrity

Canonical input=193 and all 193 are represented in review accounting. Records without set-integrity concern=193; proposed duplicates/aliases=0; proposed institution-level artefacts=0; unresolved set-integrity cases=0. Evidence-supported distinct physical-site count if the proposed review is accepted=193. No separate cleaned dataset was created because no set-integrity correction is supported. This is not final until human approval.

## G. Coordinate precision and routing readiness

| group | records | precision_A | precision_B | precision_C | precision_D | routing_ready_yes | routing_ready_no |
| --- | --- | --- | --- | --- | --- | --- | --- |
| locked_ge20 | 60 | 60 | 0 | 0 | 0 | 60 | 0 |
| numeric_lt20 | 53 | 6 | 47 | 0 | 0 | 53 | 0 |
| suppressed_only | 80 | 18 | 62 | 0 | 0 | 80 | 0 |
| new_review_scope | 133 | 24 | 109 | 0 | 0 | 133 | 0 |
| all_canonical | 193 | 84 | 109 | 0 | 0 | 193 | 0 |

All arithmetic completeness assertions passed for 60, 53, 80, 133 and 193 reviewed records.

## H. Output datasets

- `outputs/late_stage_geo_validation_2026-08-14/figure3_finalisation/Figure3B_final_selected_legend_wording.png` — SHA-256 `91dc44063f1302e2101b78e0b72c1bd53b4857537548fd06a81380bbbd7d9aff`
- `outputs/late_stage_geo_validation_2026-08-14/figure3_finalisation/Figure3B_final_selected_legend_wording.pdf` — SHA-256 `bd3fdde5702047cae35640eeed3baa4f0e20d851d72cb617b2c7887be476a938`
- `outputs/late_stage_geo_validation_2026-08-14/qa/Figure3B_finalisation_QA.csv` — SHA-256 `fe9fbdd813e763f09e75ce1bb9d7306244624e4605e59d4e80cbdc1fe8b2ff0f`
- `outputs/late_stage_geo_validation_2026-08-14/geo_validation/evidence/nominatim_exact_address_corrections.csv` — SHA-256 `dfc2067c8897b97f86dd11a497be372054df407f043ae04d855fdc08456015b6`
- `outputs/late_stage_geo_validation_2026-08-14/geo_validation/evidence/nominatim_reverse_coordinate_evidence.csv` — SHA-256 `b70508b76329ab03c1a5cce9fe52a9fc26d9bf39d262995727b0229c12939cb8`
- `outputs/late_stage_geo_validation_2026-08-14/geo_validation/additional_133_site_validation.csv` — SHA-256 `ff00191ec9ea4ff79bcd36b46eebdd6c3def834132b4c914cb5db0f4a0cfaa1a`
- `outputs/late_stage_geo_validation_2026-08-14/geo_validation/routing_readiness_all_193.csv` — SHA-256 `d3f9fda1257986f384b812dc4f9bcfe4c878cf9f6ea207c8525a5dca60599715`
- `outputs/late_stage_geo_validation_2026-08-14/geo_validation/proposed_full_identifiable_network_review_master.csv` — SHA-256 `dd26689f63106b8551b325916806b1cede28e9a15a89d47d37593e6dc2b347d4`
- `outputs/late_stage_geo_validation_2026-08-14/geo_validation/proposed_openly_numeric_network_review_master.csv` — SHA-256 `1df3af1e8f4a8248160ace0472d0ffe3ccdbd211d7d2d11e76994d7eae68c79f`
- `outputs/late_stage_geo_validation_2026-08-14/geo_validation/proposed_corrections.csv` — SHA-256 `8d065d7f53d4b4f87d1ac34028f275fa5912838c91eaa15ac9a015d7736c0a16`
- `outputs/late_stage_geo_validation_2026-08-14/geo_validation/evidence/evidence_source_inventory.csv` — SHA-256 `888f568a353e0d17cde79a58e6dc307e738991ad7037a41c33db37174e0ea545`
- `outputs/late_stage_geo_validation_2026-08-14/geo_validation/evidence/official_source_coordinate_adjudications.csv` — SHA-256 `cbc4bd1d5c00e9ce94c5eb380f59f400713c4bffe7efd3d7b3d22b5611d5a418`
- `outputs/late_stage_geo_validation_2026-08-14/geo_validation/review_dossier/full_133_site_validation_dossier.html` — SHA-256 `65601f905bd1e7e62b1c280f81da1debae7212416828fb9e49a10f06d65380a2`
- `outputs/late_stage_geo_validation_2026-08-14/geo_validation/decision_required/decision_required_records.csv` — SHA-256 `5da9f7fd8fdd43a736a55165d7d6a13aefdd59c4510e5f29e3e6d377975a5554`
- `outputs/late_stage_geo_validation_2026-08-14/geo_validation/decision_required/decision_required_dossier.html` — SHA-256 `115c7fd037c9bde649ee093bb8a421ad6b9f84e16fdb27626cba5c741edb9282`
- `outputs/late_stage_geo_validation_2026-08-14/geo_validation/set_integrity_report.md` — SHA-256 `acc02fd19e8c2f240e79e767c0d5f56917a9795afe2c8d04c18ec8c1ba628ba1`
- `outputs/late_stage_geo_validation_2026-08-14/qa/geographic_validation_programmatic_QA.csv` — SHA-256 `cc472e47fc1e7b117682ee7ed63a6d86b555b11c919fcf251311210bfef10b43`
- `outputs/late_stage_geo_validation_2026-08-14/qa/precision_routing_summary.csv` — SHA-256 `7c97c01635308aeb70448482b8e588059c1929479dff4ac8c7436469ec659d47`

## I. Remaining human decisions

Decision-required records=0. The complete row-level list is `outputs/late_stage_geo_validation_2026-08-14/geo_validation/decision_required/decision_required_records.csv` — SHA-256 `5da9f7fd8fdd43a736a55165d7d6a13aefdd59c4510e5f29e3e6d377975a5554`. No records require an explicit case-level decision before a later isochrone run; Louis's overall scientific approval of the proposed review masters is still required. No record is silently excluded.

## J. Readiness for future accessibility analysis

Openly numeric reference network: 113/113 routing-ready; unresolved=0; set-integrity decisions=0. Full identifiable reference network: 193/193 routing-ready; unresolved=0; set-integrity decisions=0. The technical validation prerequisite is satisfied, but a new accessibility run is not scientifically authorised until Louis reviews and explicitly approves the dossier and proposed set interpretation. No accessibility calculation was performed.

## K. Scope-change note

Any future full-network coverage analysis would deliberately reactivate a previously excluded scope. Preferred framing: `maximal observable reference network of identifiable physical sites reporting TIPS-related procedural activity`. A parallel openly numeric reference calculation is planned to assess dependence on reporting definition. No accessibility calculation was authorised here.

## L. Integrity statement

No Word file was modified. No canonical production file was overwritten. No Git history, branch or remote was modified. No routing was performed, no isochrone was generated, no population overlay or coverage calculation was performed, Table S5 was not recalculated and Figure 4 was not rebuilt. No author-level approval is claimed. Automatic preview coordinates were not treated as validated without official G-BA address evidence and coordinate-resolution checks.
