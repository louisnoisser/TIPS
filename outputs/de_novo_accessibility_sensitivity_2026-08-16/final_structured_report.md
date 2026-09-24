# 2024 selected de-novo-code accessibility sensitivity

## A. Input verification

All locked selected-code, geographic and completed-accessibility hashes matched. The 2024 selected-code counts reproduced exactly: visible activity 2,548; identifiable sites 176; openly numeric sites 106; selected-code suppressed-only sites 70; membership-only thresholds 44/14/4/0 for ≥20/≥50/≥100/≥200. **PASS**.

## B. Geometry-bank preflight

The expected 193 stable site IDs had 193/193 individual 30-minute and 193/193 individual 60-minute geometries. Provenance comprised 60 sites in the locked ≥20 site-geometry bank and 133 recovery-routed sites. Duplicate mappings, missing IDs, extra IDs and unmatched recovery files were all zero. The run remained routing-free: ORS was neither started nor queried. **PASS**.

## C. Selected-code membership

Selected-code membership comprised 176 identifiable sites, including 106 openly numeric and 70 selected-code suppressed-only sites. There were 17 inclusive-identifiable sites without identified selected-code activity and 7 inclusive-openly-numeric sites without numeric selected-code activity. Absence of selected-code activity is not interpreted as secondary-intervention-only or absence of de novo activity.

| inclusive_reporting_status | selected_code_reporting_status | site_count |
| --- | --- | --- |
| inclusive_openly_numeric | selected_code_openly_numeric | 106 |
| inclusive_openly_numeric | selected_code_suppressed_only | 7 |
| inclusive_openly_numeric | no_selected_code_activity_identified | 0 |
| inclusive_suppressed_only | selected_code_openly_numeric | 0 |
| inclusive_suppressed_only | selected_code_suppressed_only | 63 |
| inclusive_suppressed_only | no_selected_code_activity_identified | 17 |

## D. Inclusive reproduction gate

All 16 network/time/stratum raw integer covered-population counts and manuscript-rounded values for reconstructed 193 and 113 networks reproduced the completed analysis exactly. All four reconstructed unions matched their persisted recovery reference within the completed-analysis tolerance `max(1 m², 1e-8 × reference area)`. **PASS**.

| network | time_minutes | symmetric_difference_area_m2 | symmetric_difference_pct_reference | containment_status | tolerance_m2 | status |
| --- | --- | --- | --- | --- | --- | --- |
| inclusive_identifiable | 30 | 1.29032188640161 | 1.213792961799643e-09 | mutual_within_tolerance | 1063.0494054673875 | PASS |
| inclusive_identifiable | 60 | 10.539793089497302 | 3.4948366512387022e-09 | mutual_within_tolerance | 3015.818517801569 | PASS |
| inclusive_openly_numeric | 30 | 0.804561249061986 | 1.0850116422781994e-09 | mutual_within_tolerance | 741.5231484269132 | PASS |
| inclusive_openly_numeric | 60 | 5.295741721206126 | 2.026312150711123e-09 | mutual_within_tolerance | 2613.487620526588 | PASS |

## E–F. Selected-code reference-network accessibility

| Network | Sites | Drive time | Population covered | National % | Urban % | Rural % | Other % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Specific de novo-code identifiable network | 176 | 30 | 53393877 | 64.2 | 75.6 | 33.3 | 13.0 |
| Specific de novo-code identifiable network | 176 | 60 | 78519586 | 94.4 | 96.6 | 88.5 | 49.3 |
| Specific de novo-code openly numeric network | 106 | 30 | 45435762 | 54.6 | 66.6 | 22.5 | 1.4 |
| Specific de novo-code openly numeric network | 106 | 60 | 74298091 | 89.3 | 93.4 | 78.3 | 33.3 |

The 176-site network comprises identifiable physical sites reporting activity under specific de novo TIPS creation subcodes; it does not establish confirmed de novo TIPS capability. The 106-site network is restricted to openly numeric selected-code reporting.

## G. Sensitivity comparison

Differences below are signed as selected-code minus inclusive. No significance testing or arbitrary similarity threshold was applied.

| comparison | settlement_class | time_minutes | covered_population_difference_selected_minus_inclusive | percentage_point_difference_selected_minus_inclusive |
| --- | --- | --- | --- | --- |
| 176 selected-code minus 193 inclusive | national | 30 | -1213199 | -1.4582653477055203 |
| 176 selected-code minus 193 inclusive | urban | 30 | -829322 | -1.3675195691673991 |
| 176 selected-code minus 193 inclusive | rural | 30 | -383876 | -1.7023064745880205 |
| 176 selected-code minus 193 inclusive | other | 30 | -1 | -1.4492753623188417 |
| 176 selected-code minus 193 inclusive | national | 60 | -713875 | -0.8580778380902672 |
| 176 selected-code minus 193 inclusive | urban | 60 | -366282 | -0.6039847041725466 |
| 176 selected-code minus 193 inclusive | rural | 60 | -347594 | -1.5414131561440314 |
| 176 selected-code minus 193 inclusive | other | 60 | -1 | -1.4492753623188435 |
| 106 selected-code minus 113 inclusive | national | 30 | -880143 | -1.0579319946073014 |
| 106 selected-code minus 113 inclusive | urban | 30 | -612121 | -1.0093636081019497 |
| 106 selected-code minus 113 inclusive | rural | 30 | -268017 | -1.1885272181633049 |
| 106 selected-code minus 113 inclusive | other | 30 | -5 | -7.246376811594202 |
| 106 selected-code minus 113 inclusive | national | 60 | -696487 | -0.8371774599446269 |
| 106 selected-code minus 113 inclusive | urban | 60 | -351509 | -0.579624604482305 |
| 106 selected-code minus 113 inclusive | rural | 60 | -344970 | -1.5297769710495714 |
| 106 selected-code minus 113 inclusive | other | 60 | -8 | -11.59420289855072 |

## H. QA

Raw coverage nesting, 60-minute ≥30-minute coverage, exact membership, complete geometry availability and selected-code union containment all passed. Geometry tests used `max(1 m², 1e-8 × smaller/reference area)`, equivalent to at most `1e-6%` of area. **PASS**.

## I. Candidate Table S10 Panel C

The manuscript-ready and audit-level tables are stored under `tables/`. Suggested footnote: Selected-code networks include physical sites reporting activity under OPS 8-839.87, 8-839.88, 8-839.89 or 8-839.8a in 2024. Identifiable sites include sites with numeric or exclusively suppressed selected-code entries, whereas openly numeric sites have at least one numeric selected-code contribution. These reporting-defined networks do not establish complete ascertainment of all sites capable of de novo TIPS creation.

## J. Candidate manuscript wording

### Methods

We performed a geographic sensitivity analysis restricted to 176 identifiable and 106 openly numeric physical sites reporting activity under specific de novo TIPS creation subcodes in 2024. The analysis used the same validated coordinates, existing site-level isochrones and population framework as the inclusive reference-network analysis.

### Results

Restricting the identifiable network from 193 inclusive sites to 176 selected-code sites changed 60-minute national accessibility from 95.2% to 94.4% (-0.9 percentage points) and rural accessibility from 90.0% to 88.5% (-1.5 percentage points). For the openly numeric networks, restriction from 113 to 106 sites changed the corresponding national estimate from 90.1% to 89.3% (-0.8 percentage points) and the rural estimate from 79.8% to 78.3% (-1.5 percentage points).

### Limitations

Because the inclusive OPS family also captures secondary interventions, presence in the 193-site reference network indicates reported TIPS-related procedural activity and does not establish de novo TIPS capability; accessibility was therefore additionally examined in networks restricted to sites reporting specific de novo creation subcodes, for which 60-minute national accessibility was 94.4% among 176 identifiable sites and 89.3% among 106 openly numeric sites, compared with 95.2% and 90.1% in the respective inclusive networks. However, selected-code reporting remains reporting-defined and does not establish complete ascertainment of all sites capable of de novo TIPS creation.

### Discussion

Optional discussion sentence: The reporting-defined selected-code restriction provides a descriptive sensitivity analysis of the broad reference-network accessibility estimates while retaining uncertainty about complete ascertainment of de novo TIPS capability.

## K. Integrity

No Word document, manuscript, Supplement, Figure 3, Figure 4, Table S5, existing Table S10, validated coordinate, provider set, population asset, ORS configuration, canonical production output, Git history, branch or remote was modified. No geocoding or ORS routing occurred. No selected-code threshold accessibility was calculated. No commit or push occurred.
