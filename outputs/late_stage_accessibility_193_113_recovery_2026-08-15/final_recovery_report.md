# TIPS 193/113 accessibility recovery report

## A. Recovery context

The previous run stopped after Java heap exhaustion. Docker Desktop allocation was intentionally changed from 7.9 to 11 GB memory and 1.0 to 1.5 GB swap, with 8 CPUs. The same existing `ors-app` container was used. Java remained `-Xmx6g`; no image, graph, OSM, configuration or profile changed.

## B. ORS identity

ORS 9.8.0; image `sha256:2ee0dcf4aeccd7852f443dfbae03a0ea96537753360e42e682a32cb9e72f929b`; digest `openrouteservice/openrouteservice@sha256:2ee0dcf4aeccd7852f443dfbae03a0ea96537753360e42e682a32cb9e72f929b`; `driving-car`; graph `2026-04-01T12:04:19Z`; OSM `2026-03-29T20:20:46Z`; config `b1f86ee8e119be137897f86d1058df051451332e5bdaa56fc46ee956e811e7c0`; graph metadata `74db950055dc75514dbd1be8d64f6c37dc5755ed96ccfa3d494dae51f68d8667`; Java `-Xmx6g`. **PASS**.

## C. Set reconciliation

193 identifiable = 113 openly numeric + 80 suppressed-only; 113 = 60 ≥20 + 53 <20; ≥50=31; ≥100=16. Identifiers are unique, sets are nested and the standalone 113 identity/final coordinates match exactly. **PASS**.

## D. Routing readiness

193/193 and 113/113 ready; every routed site is A/B; invariant failures 0. **PASS**.

## E. Denominator reconciliation

| national_raw | urban_raw | rural_raw | other_raw | class_raw_sum | class_raw_minus_national | national_rounded | urban_rounded | rural_rounded | other_rounded | rounded_class_sum | rounded_class_sum_minus_national | classification | locked_denominators_retained |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 83194666.82777423 | 60644251.4457971 | 22550345.888311617 | 69.49366551530291 | 83194666.82777423 | 0.0 | 83194667 | 60644251 | 22550346 | 69 | 83194666 | -1 | benign_independent_rounding_artefact | True |

The unrounded class sums reconcile within floating-point precision. Independently rounding national and the three classes produces the one-person integer discrepancy; locked denominators are retained unchanged. **PASS**.

## F. Population-overlay gate

All 24 locked threshold/time/stratum cells reproduced exactly in raw integer count and manuscript rounding, including 1,702,480 / 22,550,346 = 7.5496846035% (7.5%). **PASS**.

## G. ≥100 routing-control gate

16/16 sites routed serially at both times with unchanged coordinates, valid non-empty geometries and per-site 30/60 QA. All eight coverage cells reproduced exactly. Fresh-vs-locked symmetric differences are documented in `routing_control/ge100_fresh_vs_locked_geometry.csv`; no material difference occurred. **PASS**.

## H. Serial routing of new sites

Openly numeric <20: 53/53; suppressed-only: 80/80; total 133/133. Requests were strictly serial, split by time, immediately persisted and checkpointed. ORS restarts during new-site routing: 0. OOM: no. Health monitoring is in `routing/health_monitoring/ors_health_memory_log.csv`.

## I–J. New accessibility

| network | site_count | network_definition | data_provenance | national_30min_covered_population | national_30min_percentage_unrounded | national_30min_percentage_1dp | urban_30min_covered_population | urban_30min_percentage_unrounded | urban_30min_percentage_1dp | rural_30min_covered_population | rural_30min_percentage_unrounded | rural_30min_percentage_1dp | other_30min_covered_population | other_30min_percentage_unrounded | other_30min_percentage_1dp | national_60min_covered_population | national_60min_percentage_unrounded | national_60min_percentage_1dp | urban_60min_covered_population | urban_60min_percentage_unrounded | urban_60min_percentage_1dp | rural_60min_covered_population | rural_60min_percentage_unrounded | rural_60min_percentage_1dp | other_60min_covered_population | other_60min_percentage_unrounded | other_60min_percentage_1dp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full_identifiable_reference | 193 | maximal observable reference network of identifiable physical sites reporting TIPS-related procedural activity | newly_computed | 54607076 | 65.63771209036753 | 65.6 | 46703475 | 77.01220516351995 | 77.0 | 7903591 | 35.0486462602392 | 35.0 | 10 | 14.492753623188406 | 14.5 | 79233461 | 95.23862989919775 | 95.2 | 58927969 | 97.16991805208379 | 97.2 | 20305458 | 90.04499531847537 | 90.0 | 35 | 50.72463768115942 | 50.7 |
| openly_numeric_reference | 113 | openly numeric reference network | newly_computed | 46315905 | 55.67172352525914 | 55.7 | 40979520 | 67.5736270532882 | 67.6 | 5336379 | 23.664288787409294 | 23.7 | 6 | 8.695652173913043 | 8.7 | 74994578 | 90.14349201013088 | 90.1 | 56999047 | 93.98920105386412 | 94.0 | 17995500 | 79.80143630612142 | 79.8 | 31 | 44.927536231884055 | 44.9 |

The 193 estimate is potential geographic accessibility to the maximal observable reference network of identifiable physical sites reporting TIPS-related procedural activity; it does not establish complete or confirmed de novo TIPS access.

## K. Progression comparison

The 193→≥20→≥50→≥100 and 113→≥20→≥50→≥100 tables and percentage-point reductions are in `tables/`. Interpretation is descriptive, not causal.

## L. Scientific QA

Raw national/urban/rural/other counts are monotonic across nested networks at both times; every 60-minute result is at least its 30-minute result. Union containment passes with tolerance max(1 m², 1e-8 of smaller area), equivalent to at most 1e-6% and covering only projection/topology precision effects. Per-site 30/60 QA distinguishes ‘contains’ from ‘extends beyond’: under the established largest-component polygon logic it requires at least 90% overlap of the 30-minute principal component and a larger 60-minute area. Exact omitted component areas remain audit-visible.

## M–N. Figure 4 candidates

C193 and C113 are supplied as 300-dpi PNG and vector PDF. All four panels contain accessibility polygons, all site markers use 18 points² without volume encoding, Panel D labels 16/16 sites, and Panels B–D are data- and pixel-identical between candidates. Neither candidate is selected.

## O. Candidate Table S5

The rounded candidate and raw audit tables are in `tables/`, including national, urban, rural and other values. The Supplement was not modified.

## P. Author-decision package

The five-network and loss tables quantify the two absolute baselines, their difference, reductions to locked networks and urban/rural contrast. C193 shows the maximal reporting-defined footprint but is denser and has the inclusive-family limitation; C113 is visually sparser and restricted to openly numeric sites. No winner is selected.

## Q. Scope change

The 193/113 baseline is a deliberate reactivation and extension of an analysis previously excluded from scope.

## R. Integrity statement

No Word file, manuscript, Supplement, Figure 3, validated coordinate, provider set, locked threshold network, locked geometry, locked reported value, ORS image, graph or configuration, canonical production output, Git history, branch or remote was modified. Java remained `-Xmx6g`; the Docker Desktop allocation change is documented. No final Figure 4 candidate was selected.
