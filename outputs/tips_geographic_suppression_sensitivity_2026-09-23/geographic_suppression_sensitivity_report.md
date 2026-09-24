# Geographic suppression sensitivity for 2024

## Scope and inputs

This routing-free analysis uses the inclusive OPS definition, exact-code site precedence, the final 193-site geographic master and the completed bank of individual 30-minute and 60-minute isochrones. Existing final outputs were read but not modified.

## Main results for the 20-procedure threshold

| scenario | sites | national_60min_pct | national_change_vs_visible_pp | rural_60min_pct | rural_change_vs_visible_pp |
| --- | --- | --- | --- | --- | --- |
| visible | 60 | 82.91 | 0.0 | 66.66 | 0.0 |
| lower | 69 | 85.12 | 2.21 | 71.46 | 4.8 |
| midpoint | 74 | 85.78 | 2.87 | 73.14 | 6.48 |
| upper | 81 | 86.32 | 3.41 | 73.96 | 7.3 |

## Site settlement classes for the 20-procedure networks

| reporting_year | volume_threshold | suppression_scenario | suppressed_value_per_entry | site_count | urban_sites | rural_sites | other_sites | missing_settlement_classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024 | 20 | lower | 1 | 69 | 69 | 0 | 0 | 0 |
| 2024 | 20 | midpoint | 2 | 74 | 74 | 0 | 0 | 0 |
| 2024 | 20 | upper | 3 | 81 | 80 | 1 | 0 | 0 |
| 2024 | 20 | visible | 0 | 60 | 60 | 0 | 0 | 0 |

All 60 sites in the visible 20-procedure network sampled an urban GHS-SMOD class. An urban site can still add access for rural population. Site class and covered-population class are therefore reported separately.

## Largest non-additive rural contributions at 60 minutes

| volume_threshold | suppression_scenario | site_id | site_name | derived_settlement_category | additional_rural_population | additional_rural_percentage_points |
| --- | --- | --- | --- | --- | --- | --- |
| 50 | upper | 260950567-771175000 | Universitätsklinikum Erlangen | urban | 731667 | 3.2445929873406367 |
| 100 | upper | 260320597-771519000 | Medizinische Hochschule Hannover | urban | 695528 | 3.0843334088025807 |
| 100 | upper | 261500289-773667000 | Universitätsklinikum Magdeburg A. ö. R. - Standort: Leipziger Straße | urban | 532883 | 2.3630800046475575 |
| 20 | lower | 260960079-773642000 | Universitätsklinikum Würzburg | urban | 510011 | 2.2616558180206536 |
| 100 | midpoint | 260612124-772858000 | Universitätsklinikum Frankfurt | urban | 426601 | 1.8917717525216522 |
| 50 | upper | 260920069-772859000 | Klinikum Passau | urban | 292047 | 1.295090539059261 |
| 20 | midpoint | 260940198-771124000 | Sana Klinikum Hof | urban | 254926 | 1.1304743597779479 |
| 50 | midpoint | 260200079-772901000 | Asklepios Klinikum Harburg | urban | 198910 | 0.8820722417946675 |
| 20 | midpoint | 260930129-771930000 | Kliniken Nordoberpfalz AG - Weiden | urban | 191388 | 0.8487122430211687 |
| 20 | upper | 261200721-773088000 | Medizinische Universität Lausitz - Carl Thiem | urban | 190989 | 0.8469466879428554 |

Each value compares the visible network at the same threshold with that visible network plus one site. Contributions overlap spatially and must not be summed. Scenario gains use the joint union of all selected sites.

## Population group other

| suppression_scenario | time_minutes | covered_population | population_denominator | coverage_pct_2dp |
| --- | --- | --- | --- | --- |
| lower | 30 | 1 | 69 | 1.36 |
| lower | 60 | 21 | 69 | 29.85 |
| midpoint | 30 | 1 | 69 | 1.36 |
| midpoint | 60 | 21 | 69 | 29.93 |
| upper | 30 | 1 | 69 | 1.43 |
| upper | 60 | 23 | 69 | 32.65 |
| visible | 30 | 1 | 69 | 1.36 |
| visible | 60 | 21 | 69 | 29.85 |

The underlying other denominator is 69.4937 people before rounding and 69 after independent presentation rounding. A change of only a few people can therefore produce a large percentage-point difference. The category is reported completely but does not support a separate policy conclusion.

## Plausibility checks

All 142 checks passed. Stable site IDs were unique, all selected sites had coordinates and both isochrones, threshold and scenario sets were nested, coverage did not decline as a network expanded, 60-minute coverage was never below 30-minute coverage, denominators remained constant and the visible reference networks reproduced all existing covered-population counts exactly.

## Interpretation

Suppression assumptions expand the threshold-qualified networks and improve estimated accessibility. The largest changes occur at the 20-procedure threshold. The comparison does not alter the qualitative finding that rural potential accessibility remains below urban potential accessibility. Results represent TIPS-related procedural activity under the inclusive OPS definition and do not establish de novo TIPS capability.

## English Methods candidate

We conducted a routing-free suppression sensitivity analysis for the 2024 inclusive TIPS-related OPS network. For each resolved physical site, suppressed code entries contributed one procedure occurrence in the lower scenario, two in the midpoint scenario and three in the upper scenario. The midpoint was treated as a scenario rather than an estimate. Networks meeting 20, 50 and 100 procedure occurrence thresholds were assembled from stable site identifiers and existing 30-minute and 60-minute driving-car isochrones. Isochrones were combined before population aggregation to prevent double counting. Coverage was estimated with GHS-POP R2023A epoch 2025 and stratified using GHS-SMOD R2023A epoch 2025 as urban, rural or other.

## English Results candidate

The visible 20-procedure network contained 60 sites and covered 82.9% of the national population and 66.7% of the rural population within 60 minutes. The lower, midpoint and upper scenarios contained 69, 74 and 81 sites. Rural 60-minute coverage increased to 71.5% in the lower scenario and 74.0% in the upper scenario, corresponding to +4.8 and +7.3 percentage points compared with the visible network. The direction of the main finding was unchanged because the 60-minute network continued to cover a substantially smaller share of rural than urban population in every suppression scenario.

## Provenance

See `routing_and_geodata_provenance.md` for the evidence hierarchy and unresolved metadata.
