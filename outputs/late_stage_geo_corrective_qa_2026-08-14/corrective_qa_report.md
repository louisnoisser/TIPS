# Corrective geographic QA report — 2026-08-14

## A. Record resolution

- Queried site_id: `260341444-772466000`
- Matches: 1
- Resolved site: `Ammerland-Klinik Westerstede`
- Result: **PASS**

All expected pre-change values matched exactly: Lange Straße 38, coordinate 53.2579622, 7.9184201, `nominatim_full_address`, reverse exact-address false, precision A and routing-ready yes. No prior explicit adjudication existed.

## B. Westerstede adjudication

- Coordinate before/after: `53.2579622, 7.9184201` / unchanged
- Precision before/after: A / A
- Routing-ready before/after: yes / yes
- Authoritative sources: https://ammerland-klinik.de/klinikzentrum-westerstede; https://www.ammerland-klinik.de/_downloads/AMKL-Lageplan-Neubau-Querformat_2025-08-05-131147_oyxb.pdf; https://www.bundeswehr.de/service/locationSearch/bw-de/5995288/term-search
- Rationale: Official Ammerland-Klinik evidence states that Ammerland-Klinik GmbH and Bundeswehrkrankenhaus Westerstede jointly form Klinikzentrum Westerstede at Lange Straße 38 and provide care at one location. The official campus plan shows the Ammerland buildings and Bundeswehrkrankenhaus on the connected Klinikzentrum campus between the Lange Straße entrance and Mozartstraße. The reverse result naming Bundeswehrkrankenhaus/Mozartstraße therefore identifies the shared clinical campus rather than a wrong hospital location; reverse_exact_street_address=False does not invalidate the campus coordinate.

## C. Generic invariant

Canonical records checked=193; A/B routing-ready records checked=193; satisfying=193; failing=0. The generic assertion was applied without a Westerstede special case: `A/B AND routing_ready=yes -> reverse_exact_street_address=True OR authoritative_adjudication_present=True`.

## D. Reverse=False audit

Reverse=False records=10; authoritative adjudications among them=10; unexplained A/B routing-ready records=0.

## E. Preservation checks

Five Vivantes coordinates unchanged: PASS. Ketteler coordinate unchanged: PASS. Ketteler verified address remains `Lichtenplattenweg 85, 63071 Offenbach`: PASS. RoMed coordinate unchanged: PASS. All 60 locked ≥20 coordinates unchanged: PASS. Every pre-existing field in the 193 routing table and proposed full-network master is value-identical; only new evidence/QA columns were appended.

The openly numeric master was not regenerated because Westerstede is suppressed-only and no openly numeric evidence/status field changed. Its source SHA-256 remains `1df3af1e8f4a8248160ace0472d0ffe3ccdbd211d7d2d11e76994d7eae68c79f`.

## F. Updated outputs

- `outputs/late_stage_geo_corrective_qa_2026-08-14/westerstede_corrected_adjudicated_record.csv` — SHA-256 `8139d1c3362d77b80fa77c2dddf6aefce3d57943bb6ec81f8556a53d3838a165`
- `outputs/late_stage_geo_corrective_qa_2026-08-14/evidence/authoritative_coordinate_adjudications_updated.csv` — SHA-256 `6327fabcfa7d6d54b3b7c65d836c9497f6d4569fc039e8bd02c0818a9754079f`
- `outputs/late_stage_geo_corrective_qa_2026-08-14/qa/routing_readiness_invariant_all_193.csv` — SHA-256 `1182eca18ca0c89380ae57fa0d74661f40844d337641ecf8d0d2597dbd91a096`
- `outputs/late_stage_geo_corrective_qa_2026-08-14/qa/reverse_false_records_qa.csv` — SHA-256 `8c73cd6a39ec02ba82a5dcd5900e41e44e672f5756228c365626ce39b881d149`
- `outputs/late_stage_geo_corrective_qa_2026-08-14/routing_readiness_all_193_corrective_qa.csv` — SHA-256 `5b23e962ddc0288d82e94b7ddb36f4d493699e287b7de278e12b872af81c7a31`
- `outputs/late_stage_geo_corrective_qa_2026-08-14/proposed_full_identifiable_network_review_master_corrective_qa.csv` — SHA-256 `58ea359aa31f93a7597771298aac0f19124a41ead80aaf35b14c089a83880793`
- `outputs/late_stage_geo_corrective_qa_2026-08-14/qa/preservation_crosscheck.csv` — SHA-256 `6cf7ee7c97e90e978049b0354e21f496b3f768b32f53f73eb43874a6ad6d93c5`
- `outputs/late_stage_geo_corrective_qa_2026-08-14/qa/programmatic_qa.csv` — SHA-256 `1730b90be8bfc2d287437bb5cda54ebd63de7f4dc1cae33301285fb04363e032`

## G. Readiness conclusion

Openly numeric network routing-ready: 113/113. Full identifiable network routing-ready: 193/193. Unexplained coordinate-evidence guardrail failures: 0. Technical routing readiness does not itself authorise accessibility analysis.

## H. Integrity statement

No routing, isochrone generation, population coverage, Figure 4 or accessibility analysis was performed. Figure 3 and all Word files were untouched. No canonical production or completed-validation output was overwritten. No Git history, branch or remote was modified. No unrelated validated geographic value changed.
