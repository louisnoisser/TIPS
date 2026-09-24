# OPS-specific de-novo TIPS sensitivity analysis, 2013–2024

## Analytical question and endpoint

This sensitivity analysis describes **activity coded with specific de novo TIPS creation subcodes**. It does not estimate unique
procedures, patients, admissions, or complete ascertainment of all newly created shunts.
The primary unit is physical site × reporting year; institution identifiers remain metadata.

## Inputs and provenance

| path | size_bytes | modification_timestamp_utc | sha256 |
| --- | --- | --- | --- |
| outputs/ops_code_audit_2013_2024/ops_code_reconciliation_site_year.csv | 1807229 | 2026-08-03T09:47:32.326756+00:00 | 294b0e5cfb44f4091322f2de25373a3c1d26754cf4bea2dbdee9f3d0bae7ba8d |
| outputs/ops_code_audit_2013_2024/ops_code_audit_2013_2024.csv | 148869 | 2026-08-04T07:55:24.098746+00:00 | f51487d4339f6fac5f9dac5fa5420a26b27ea7331301d9abd225bbbb387e31a2 |
| outputs/ops_code_audit_2013_2024/ops_code_summary_2013_2024.csv | 7826 | 2026-08-04T07:55:24.099264+00:00 | 366bfeb8b70553dc6948cc41ffc3ae90294ee9f733e6e3fa0b4d42128c7473b6 |
| outputs/audit/tips_code_level_audit.csv | 2049916 | 2026-07-17T13:12:29.987277+00:00 | beb19fe8e3af74ae0d6a45ab069409b5e63704c04c7170053f18dce7c845e51d |
| outputs/site_resolution_validation/resolved_site_level_data.csv | 1033428 | 2026-07-23T16:51:51.379397+00:00 | ffada120e835a159efa1adc6e4a15e85be90ba809165b937e5d192c0ba68dc07 |
| outputs/final_corrected_2026-07-24/suppression_final_metrics.csv | 13530 | 2026-07-24T13:09:57.277992+00:00 | d0a52a5d8ea8a250b7d4729a91bae7174272a22752ff772142c8543b7f99cf88 |
| src/gba_ops_reanalysis/site_resolution_validation.py | 31048 | 2026-07-23T16:48:08.016935+00:00 | 217294d3bdeb6cb272e192f7e3706e110dc1b2e1379639d1bc375795f3e983b0 |
| src/gba_ops_reanalysis/final_corrected.py | 10311 | 2026-07-24T13:04:29.831887+00:00 | 054b8429cc7d3fa4e1a1dd53a190b2878bf930359d3ff6cf625b90ec581cc3b8 |
| src/gba_ops_reanalysis/suppression_sensitivity.py | 28767 | 2026-07-11T22:44:08.200747+00:00 | 8ac5f0ea7c98673f4fe550f68324aa4af3221ced99e960feaa63a6317009336c |
| data/xml/xml_2013/260100023-00-2013-xml.xml | 1077210 | 2026-04-01T09:31:05.508826+00:00 | 4be60a63e7bc252811b7ee2302852865abe35321bdb280c951c67a358ba36bcd |
| data/xml/xml_2013/260101488-00-2013-xml.xml | 1193526 | 2026-04-01T09:31:05.715420+00:00 | d5e9d88a138cba74d562bdc0bc6dbee0f1b0f59aa148313042cebb6f347ed425 |
| data/xml/xml_2013/260200400-00-2013-xml.xml | 1277067 | 2026-04-01T09:31:05.788951+00:00 | 75d80cb61fb5a7c8230f72c487b62ae4565f0d37c66adadba92454ddc43dc094 |
| data/xml/xml_2013/260810647-00-2013-xml.xml | 1400997 | 2026-04-01T09:31:07.248507+00:00 | 606a7e880194af75f4448613ccf39daa5e5566c5e6b3ce67d48f58c4eff1c9d3 |
| data/xml/xml_2016/260100023-01-2016-xml.xml | 1149079 | 2026-04-01T09:31:17.559446+00:00 | 03da770b8fe50e2b7e8cff18d320bc9597d53b789d86cf61a20875a6e05b3d79 |
| data/xml/xml_2016/260101488-00-2016-xml.xml | 1516995 | 2026-04-01T09:31:17.763853+00:00 | a6f202484f36161d89c6a1f5b1dc1e53629993a52697b98ecd7a182323712168 |
| data/xml/xml_2016/260310447-00-2016-xml.xml | 1385030 | 2026-04-01T09:31:18.004360+00:00 | 1dd3f981e1b0c5abe8e3ee6da2de27c8b53439b8d2e289628d50ef49b8730c7b |
| data/xml/xml_2016/260810647-00-2016-xml.xml | 2291364 | 2026-04-01T09:31:20.250534+00:00 | 69eef57d064f32330ebd2cbec939ee5a28c894a6f815e047419f821ac59cbb43 |
| data/xml/xml_2024/260100034-771320000-2024-xml.xml | 1047217 | 2026-04-01T09:31:57.099731+00:00 | ec0836480014faba592c7cf6f78f0a648d8d9add220af19d3ca7b11ea4d771d6 |
| data/xml/xml_2024/260101193-772660000-2024-xml.xml | 1789459 | 2026-04-01T09:31:57.173995+00:00 | 56a0f8fb7454a289fd88809b33baab3c139e6cce8248190f9b2892f1a7eb25e3 |
| data/xml/xml_2024/260101488-772073000-2024-xml.xml | 1804154 | 2026-04-01T09:31:57.183998+00:00 | 238a708468038bb1221f7d4f7a22788d49952a032aa5cf98b93827977d049b6a |
| data/xml/xml_2024/260530103-772247000-2024-xml.xml | 4866935 | 2026-04-01T09:31:58.048476+00:00 | 2e317b6b64444e09266fb403b1b9e8b79898912c3f5b62f4cb89b6a9e55f7cc3 |

The canonical code-level source is `outputs/audit/tips_code_level_audit.csv`.
`resolve_component_precedence()` supplies the final exact-code component-site precedence.
`scenario_metrics()` calls the inclusive analysis's `structural_metrics()` function for the
visible, lower, midpoint, and upper suppression scenarios. Suppressed entries add 0, 1, 2,
or 3 units respectively before physical-site metrics are calculated.

## Year-specific exact code sets

- 2013–2015: `8-839.87`, `8-839.88`.
- 2016–2024: `8-839.87`, `8-839.88`, `8-839.89`, `8-839.8a`.

The parent, `.80–.86`, `.8x`, other `8-839.8*`, and all `8-842.*` codes are excluded.
The literal `8-839.8a` is never split, numerically coerced, or merged.

## Site definitions and dual-route method

An identifiable active site has a numeric or suppressed selected-code entry. An openly
numeric site has positive visible selected-code activity. A suppressed-only site has no
positive visible selected-code activity and at least one suppressed selected-code entry.

Route A applies the reconciled production precedence function to the canonical code-level
CSV. Route B independently parses `contributing_code_level_records` in the reconciliation
CSV. The routes agreed exactly for all 1827 selected physical site-years,
including identifiers, selected codes, code-specific values, suppression counts, and totals.

## Annual results

| reporting_year | code_set_regime | applicable_code_set | openly_visible_national_de_novo_activity | inclusive_national_visible_activity | de_novo_to_inclusive_visible_activity_ratio | identifiable_active_de_novo_sites | openly_numeric_de_novo_sites | suppressed_only_de_novo_sites | sites_visible_4_19 | sites_visible_20_49 | sites_visible_50_99 | sites_visible_100_199 | sites_visible_ge_200 | sites_visible_ge_20 | sites_visible_ge_50 | sites_visible_ge_100 | top5_share_pct | top10_share_pct | top20_share_pct | hhi_10000 | effective_number_of_centres | gini | providers_contributing_to_metrics |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013 | two-code (2013–2015) | 8-839.87\|8-839.88 | 1042 | 2124 | 0.490584 | 105 | 51 | 54 | 32 | 17 | 2 | 0 | 0 | 19 | 2 | 0 | 30.1344 | 47.7927 | 69.9616 | 352.2681 | 28.3875 | 0.434082 | 51 |
| 2014 | two-code (2013–2015) | 8-839.87\|8-839.88 | 1291 | 2511 | 0.514138 | 124 | 65 | 59 | 46 | 12 | 6 | 1 | 0 | 19 | 7 | 1 | 32.3005 | 49.1867 | 68.0093 | 343.707 | 29.0945 | 0.498123 | 65 |
| 2015 | two-code (2013–2015) | 8-839.87\|8-839.88 | 1308 | 2546 | 0.513747 | 138 | 64 | 74 | 44 | 14 | 6 | 0 | 0 | 20 | 6 | 0 | 32.0336 | 48.7003 | 68.5015 | 335.69 | 29.7894 | 0.492641 | 64 |
| 2016 | four-code (2016–2024) | 8-839.87\|8-839.88\|8-839.89\|8-839.8a | 1427 | 2715 | 0.525599 | 135 | 70 | 65 | 50 | 11 | 8 | 1 | 0 | 20 | 9 | 1 | 33.2866 | 51.6468 | 71.6889 | 354.3583 | 28.22 | 0.551417 | 70 |
| 2017 | four-code (2016–2024) | 8-839.87\|8-839.88\|8-839.89\|8-839.8a | 1436 | 2801 | 0.512674 | 147 | 79 | 68 | 57 | 12 | 10 | 0 | 0 | 22 | 10 | 0 | 27.0891 | 47.0752 | 66.2256 | 292.0621 | 34.2393 | 0.521702 | 79 |
| 2018 | four-code (2016–2024) | 8-839.87\|8-839.88\|8-839.89\|8-839.8a | 1475 | 2977 | 0.495465 | 151 | 79 | 72 | 58 | 15 | 6 | 0 | 0 | 21 | 6 | 0 | 23.7288 | 40.339 | 62.8475 | 251.7116 | 39.728 | 0.485355 | 79 |
| 2019 | four-code (2016–2024) | 8-839.87\|8-839.88\|8-839.89\|8-839.8a | 1482 | 2972 | 0.498654 | 169 | 84 | 85 | 62 | 13 | 9 | 0 | 0 | 22 | 9 | 0 | 24.9663 | 42.8475 | 61.0661 | 258.0311 | 38.755 | 0.503984 | 84 |
| 2020 | four-code (2016–2024) | 8-839.87\|8-839.88\|8-839.89\|8-839.8a | 1621 | 3210 | 0.504984 | 165 | 87 | 78 | 63 | 16 | 8 | 0 | 0 | 24 | 8 | 0 | 26.095 | 42.628 | 61.2585 | 259.7196 | 38.5031 | 0.512398 | 87 |
| 2021 | four-code (2016–2024) | 8-839.87\|8-839.88\|8-839.89\|8-839.8a | 2032 | 4092 | 0.496579 | 174 | 101 | 73 | 76 | 13 | 10 | 2 | 0 | 25 | 12 | 2 | 23.4744 | 40.0591 | 60.876 | 238.6424 | 41.9037 | 0.537684 | 101 |
| 2022 | four-code (2016–2024) | 8-839.87\|8-839.88\|8-839.89\|8-839.8a | 2119 | 4418 | 0.479629 | 167 | 100 | 67 | 67 | 22 | 10 | 1 | 0 | 33 | 11 | 1 | 22.2747 | 38.084 | 56.8664 | 219.1837 | 45.6238 | 0.506338 | 100 |
| 2023 | four-code (2016–2024) | 8-839.87\|8-839.88\|8-839.89\|8-839.8a | 2261 | 4979 | 0.454107 | 176 | 99 | 77 | 69 | 16 | 11 | 3 | 0 | 30 | 14 | 3 | 24.6351 | 40.2919 | 59.9292 | 248.662 | 40.2152 | 0.530417 | 99 |
| 2024 | four-code (2016–2024) | 8-839.87\|8-839.88\|8-839.89\|8-839.8a | 2548 | 5247 | 0.485611 | 176 | 106 | 70 | 62 | 30 | 10 | 4 | 0 | 44 | 14 | 4 | 21.9388 | 36.6954 | 54.9058 | 210.8743 | 47.4216 | 0.517535 | 106 |

## Code-specific contributions

| reporting_year | code_set_regime | ops_code | applicable_in_year | availability_status | openly_visible_national_activity | suppressed_entry_count | sites_with_openly_numeric_entry | sites_with_suppressed_entry | sites_with_either_entry_type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013 | two-code (2013–2015) | 8-839.87 | True | applicable | 354 | 72 | 22 | 54 | 69 |
| 2013 | two-code (2013–2015) | 8-839.88 | True | applicable | 688 | 76 | 45 | 56 | 82 |
| 2013 | two-code (2013–2015) | 8-839.89 | False | not applicable—absent from annual catalogue |  |  |  |  |  |
| 2013 | two-code (2013–2015) | 8-839.8a | False | not applicable—absent from annual catalogue |  |  |  |  |  |
| 2014 | two-code (2013–2015) | 8-839.87 | True | applicable | 364 | 72 | 23 | 55 | 68 |
| 2014 | two-code (2013–2015) | 8-839.88 | True | applicable | 927 | 81 | 54 | 65 | 99 |
| 2014 | two-code (2013–2015) | 8-839.89 | False | not applicable—absent from annual catalogue |  |  |  |  |  |
| 2014 | two-code (2013–2015) | 8-839.8a | False | not applicable—absent from annual catalogue |  |  |  |  |  |
| 2015 | two-code (2013–2015) | 8-839.87 | True | applicable | 291 | 74 | 26 | 60 | 76 |
| 2015 | two-code (2013–2015) | 8-839.88 | True | applicable | 1017 | 119 | 52 | 81 | 114 |
| 2015 | two-code (2013–2015) | 8-839.89 | False | not applicable—absent from annual catalogue |  |  |  |  |  |
| 2015 | two-code (2013–2015) | 8-839.8a | False | not applicable—absent from annual catalogue |  |  |  |  |  |
| 2016 | four-code (2016–2024) | 8-839.87 | True | applicable | 201 | 69 | 16 | 60 | 70 |
| 2016 | four-code (2016–2024) | 8-839.88 | True | applicable | 1182 | 88 | 63 | 72 | 111 |
| 2016 | four-code (2016–2024) | 8-839.89 | True | applicable | 33 | 23 | 3 | 22 | 24 |
| 2016 | four-code (2016–2024) | 8-839.8a | True | applicable | 11 | 27 | 2 | 24 | 25 |
| 2017 | four-code (2016–2024) | 8-839.87 | True | applicable | 172 | 67 | 18 | 54 | 63 |
| 2017 | four-code (2016–2024) | 8-839.88 | True | applicable | 1213 | 98 | 74 | 71 | 125 |
| 2017 | four-code (2016–2024) | 8-839.89 | True | applicable | 18 | 20 | 2 | 19 | 20 |
| 2017 | four-code (2016–2024) | 8-839.8a | True | applicable | 33 | 30 | 6 | 27 | 32 |
| 2018 | four-code (2016–2024) | 8-839.87 | True | applicable | 156 | 61 | 16 | 52 | 64 |
| 2018 | four-code (2016–2024) | 8-839.88 | True | applicable | 1259 | 108 | 72 | 92 | 141 |
| 2018 | four-code (2016–2024) | 8-839.89 | True | applicable | 40 | 26 | 3 | 21 | 23 |
| 2018 | four-code (2016–2024) | 8-839.8a | True | applicable | 20 | 30 | 4 | 27 | 31 |
| 2019 | four-code (2016–2024) | 8-839.87 | True | applicable | 134 | 86 | 15 | 68 | 78 |
| 2019 | four-code (2016–2024) | 8-839.88 | True | applicable | 1298 | 122 | 79 | 91 | 146 |
| 2019 | four-code (2016–2024) | 8-839.89 | True | applicable | 27 | 20 | 2 | 18 | 20 |
| 2019 | four-code (2016–2024) | 8-839.8a | True | applicable | 23 | 31 | 4 | 29 | 33 |
| 2020 | four-code (2016–2024) | 8-839.87 | True | applicable | 104 | 61 | 12 | 53 | 62 |
| 2020 | four-code (2016–2024) | 8-839.88 | True | applicable | 1472 | 120 | 84 | 91 | 147 |
| 2020 | four-code (2016–2024) | 8-839.89 | True | applicable | 24 | 23 | 2 | 22 | 24 |
| 2020 | four-code (2016–2024) | 8-839.8a | True | applicable | 21 | 39 | 5 | 36 | 39 |
| 2021 | four-code (2016–2024) | 8-839.87 | True | applicable | 123 | 85 | 13 | 73 | 84 |
| 2021 | four-code (2016–2024) | 8-839.88 | True | applicable | 1822 | 114 | 96 | 84 | 153 |
| 2021 | four-code (2016–2024) | 8-839.89 | True | applicable | 27 | 28 | 3 | 25 | 28 |
| 2021 | four-code (2016–2024) | 8-839.8a | True | applicable | 60 | 31 | 8 | 28 | 36 |
| 2022 | four-code (2016–2024) | 8-839.87 | True | applicable | 175 | 51 | 14 | 48 | 61 |
| 2022 | four-code (2016–2024) | 8-839.88 | True | applicable | 1868 | 134 | 97 | 103 | 157 |
| 2022 | four-code (2016–2024) | 8-839.89 | True | applicable | 20 | 27 | 1 | 26 | 26 |
| 2022 | four-code (2016–2024) | 8-839.8a | True | applicable | 56 | 33 | 10 | 31 | 40 |
| 2023 | four-code (2016–2024) | 8-839.87 | True | applicable | 146 | 68 | 13 | 58 | 68 |
| 2023 | four-code (2016–2024) | 8-839.88 | True | applicable | 1997 | 125 | 96 | 99 | 163 |
| 2023 | four-code (2016–2024) | 8-839.89 | True | applicable | 26 | 18 | 2 | 18 | 20 |
| 2023 | four-code (2016–2024) | 8-839.8a | True | applicable | 92 | 48 | 10 | 43 | 48 |
| 2024 | four-code (2016–2024) | 8-839.87 | True | applicable | 145 | 53 | 17 | 49 | 61 |
| 2024 | four-code (2016–2024) | 8-839.88 | True | applicable | 2295 | 120 | 104 | 98 | 162 |
| 2024 | four-code (2016–2024) | 8-839.89 | True | applicable | 8 | 24 | 2 | 23 | 25 |
| 2024 | four-code (2016–2024) | 8-839.8a | True | applicable | 100 | 24 | 13 | 23 | 34 |

Rows for `.89` and `.8a` before 2016 are explicitly marked not applicable and contain no
activity values; catalogue non-availability is not represented as observed zero activity.

## 2015–2016 bridge and stable two-code comparison

| reporting_year | code_set_regime | bridge_focus_year | visible_8_839_87 | suppressed_entries_8_839_87 | visible_8_839_88 | suppressed_entries_8_839_88 | visible_8_839_89 | suppressed_entries_8_839_89 | visible_8_839_8a | suppressed_entries_8_839_8a | visible_8_839_87_plus_8_839_88 | suppressed_8_839_87_plus_8_839_88 | visible_8_839_89_plus_8_839_8a | suppressed_8_839_89_plus_8_839_8a | historically_valid_visible_total | historically_valid_suppressed_entries | stable_two_code_visible_total | stable_two_code_suppressed_entries | historically_valid_absolute_change_2015_2016 | historically_valid_relative_change_2015_2016_pct | stable_two_code_absolute_change_2015_2016 | stable_two_code_relative_change_2015_2016_pct | transition_interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2015 | two-code (2013–2015) | True | 291 | 74 | 1017 | 119 |  |  |  |  | 1308 | 193 |  |  | 1308 | 193 | 1308 | 193 | 119.0 | 9.097859327217126 | 75.0 | 5.73394495412844 | Comparability across 2015 and 2016 may be affected by the introduction of additional specific de-novo subcodes in 2016. The activity reported under 8-839.89 and 8-839.8a quantifies their contribution to the observed 2016 coded total, but does not identify the magnitude of a coding artefact or distinguish coding change from real procedural change. |
| 2016 | four-code (2016–2024) | True | 201 | 69 | 1182 | 88 | 33 | 23 | 11 | 27 | 1383 | 157 | 44 | 50 | 1427 | 207 | 1383 | 157 | 119.0 | 9.097859327217126 | 75.0 | 5.73394495412844 | Comparability across 2015 and 2016 may be affected by the introduction of additional specific de-novo subcodes in 2016. The activity reported under 8-839.89 and 8-839.8a quantifies their contribution to the observed 2016 coded total, but does not identify the magnitude of a coding artefact or distinguish coding change from real procedural change. |

Comparability across 2015 and 2016 may be affected by the introduction of additional
specific de-novo subcodes in 2016. The activity reported under 8-839.89 and 8-839.8a
quantifies their contribution to the observed 2016 coded total, but does not identify the
magnitude of a coding artefact or distinguish coding change from real procedural change.

## Suppression scenarios and concentration

| reporting_year | provider_definition | suppression_scenario | total_scenario_imputed_activity | providers_contributing_to_metrics | top1_share_pct | top5_share_pct | top10_share_pct | top20_share_pct | hhi_10000 | effective_center_count | gini | metric_status | undefined_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013 | physical_site | visible | 1042 | 51 | 9.309 | 30.1344 | 47.7927 | 69.9616 | 352.2681 | 28.3875 | 0.434082 | defined |  |
| 2014 | physical_site | visible | 1291 | 65 | 8.598 | 32.3005 | 49.1867 | 68.0093 | 343.707 | 29.0945 | 0.498123 | defined |  |
| 2015 | physical_site | visible | 1308 | 64 | 7.263 | 32.0336 | 48.7003 | 68.5015 | 335.69 | 29.7894 | 0.492641 | defined |  |
| 2016 | physical_site | visible | 1427 | 70 | 7.5683 | 33.2866 | 51.6468 | 71.6889 | 354.3583 | 28.22 | 0.551417 | defined |  |
| 2017 | physical_site | visible | 1436 | 79 | 6.6852 | 27.0891 | 47.0752 | 66.2256 | 292.0621 | 34.2393 | 0.521702 | defined |  |
| 2018 | physical_site | visible | 1475 | 79 | 4.8814 | 23.7288 | 40.339 | 62.8475 | 251.7116 | 39.728 | 0.485355 | defined |  |
| 2019 | physical_site | visible | 1482 | 84 | 6.2753 | 24.9663 | 42.8475 | 61.0661 | 258.0311 | 38.755 | 0.503984 | defined |  |
| 2020 | physical_site | visible | 1621 | 87 | 5.9223 | 26.095 | 42.628 | 61.2585 | 259.7196 | 38.5031 | 0.512398 | defined |  |
| 2021 | physical_site | visible | 2032 | 101 | 5.8071 | 23.4744 | 40.0591 | 60.876 | 238.6424 | 41.9037 | 0.537684 | defined |  |
| 2022 | physical_site | visible | 2119 | 100 | 5.1911 | 22.2747 | 38.084 | 56.8664 | 219.1837 | 45.6238 | 0.506338 | defined |  |
| 2023 | physical_site | visible | 2261 | 99 | 7.4303 | 24.6351 | 40.2919 | 59.9292 | 248.662 | 40.2152 | 0.530417 | defined |  |
| 2024 | physical_site | visible | 2548 | 106 | 5.1413 | 21.9388 | 36.6954 | 54.9058 | 210.8743 | 47.4216 | 0.517535 | defined |  |
| 2013 | physical_site | lower | 1190 | 105 | 8.4034 | 27.6471 | 43.4454 | 64.3697 | 295.996 | 33.7842 | 0.641873 | defined |  |
| 2014 | physical_site | lower | 1444 | 124 | 7.8947 | 29.5014 | 45.6371 | 63.1579 | 295.0695 | 33.8903 | 0.662273 | defined |  |
| 2015 | physical_site | lower | 1501 | 138 | 6.3291 | 28.3811 | 43.9707 | 61.6922 | 273.4619 | 36.5682 | 0.673179 | defined |  |
| 2016 | physical_site | lower | 1634 | 135 | 6.7931 | 29.9266 | 46.5728 | 65.7283 | 296.5966 | 33.7158 | 0.691282 | defined |  |
| 2017 | physical_site | lower | 1651 | 147 | 6.0569 | 24.1066 | 41.8534 | 60.3876 | 242.1784 | 41.2919 | 0.662629 | defined |  |
| 2018 | physical_site | lower | 1700 | 151 | 4.4706 | 21.0588 | 36.1176 | 57.2353 | 210.9689 | 47.4004 | 0.653237 | defined |  |
| 2019 | physical_site | lower | 1741 | 169 | 5.4566 | 21.7117 | 37.6795 | 55.3705 | 208.4306 | 47.9776 | 0.660275 | defined |  |
| 2020 | physical_site | lower | 1864 | 165 | 5.2575 | 23.2833 | 37.8755 | 55.4185 | 214.2814 | 46.6676 | 0.65716 | defined |  |
| 2021 | physical_site | lower | 2290 | 174 | 5.1528 | 21.2664 | 36.2445 | 55.6769 | 202.2921 | 49.4335 | 0.657105 | defined |  |
| 2022 | physical_site | lower | 2364 | 167 | 4.6531 | 20.3469 | 34.7293 | 52.665 | 189.7434 | 52.7028 | 0.640921 | defined |  |
| 2023 | physical_site | lower | 2520 | 176 | 6.746 | 22.5 | 37.0238 | 55.6349 | 214.8873 | 46.536 | 0.671532 | defined |  |
| 2024 | physical_site | lower | 2769 | 176 | 4.8754 | 20.6212 | 34.5973 | 52.0404 | 190.2623 | 52.559 | 0.658141 | defined |  |
| 2013 | physical_site | midpoint | 1338 | 105 | 7.6981 | 25.8595 | 40.2093 | 60.1644 | 258.9591 | 38.6161 | 0.579571 | defined |  |
| 2014 | physical_site | midpoint | 1597 | 124 | 7.3262 | 27.2386 | 42.7677 | 59.3613 | 260.668 | 38.363 | 0.604112 | defined |  |
| 2015 | physical_site | midpoint | 1694 | 138 | 5.7261 | 25.5608 | 40.3778 | 56.7887 | 233.4094 | 42.8432 | 0.608148 | defined |  |
| 2016 | physical_site | midpoint | 1841 | 135 | 6.1923 | 27.3221 | 43.1831 | 61.271 | 257.6564 | 38.8114 | 0.63418 | defined |  |
| 2017 | physical_site | midpoint | 1866 | 147 | 5.5734 | 21.8114 | 37.8885 | 56.4309 | 210.0946 | 47.5976 | 0.606492 | defined |  |
| 2018 | physical_site | midpoint | 1925 | 151 | 4.1558 | 19.013 | 33.039 | 53.4026 | 184.4628 | 54.2115 | 0.596735 | defined |  |
| 2019 | physical_site | midpoint | 2000 | 169 | 4.85 | 19.3 | 33.85 | 51.45 | 178.18 | 56.123 | 0.595207 | defined |  |
| 2020 | physical_site | midpoint | 2107 | 165 | 4.841 | 21.1201 | 34.4566 | 51.0204 | 184.3314 | 54.2501 | 0.594365 | defined |  |
| 2021 | physical_site | midpoint | 2548 | 174 | 4.6311 | 19.5055 | 33.2025 | 51.5306 | 177.0958 | 56.4666 | 0.602054 | defined |  |
| 2022 | physical_site | midpoint | 2609 | 167 | 4.2162 | 18.7811 | 32.0046 | 49.3292 | 168.7719 | 59.2516 | 0.591894 | defined |  |
| 2023 | physical_site | midpoint | 2779 | 176 | 6.1893 | 20.7629 | 34.4728 | 52.1411 | 190.4571 | 52.5053 | 0.621367 | defined |  |
| 2024 | physical_site | midpoint | 2990 | 176 | 4.6488 | 19.4983 | 32.8094 | 49.5987 | 174.224 | 57.3974 | 0.615818 | defined |  |
| 2013 | physical_site | upper | 1486 | 105 | 7.1332 | 24.428 | 37.6851 | 56.7968 | 233.5843 | 42.8111 | 0.534167 | defined |  |
| 2014 | physical_site | upper | 1750 | 124 | 6.8571 | 25.6571 | 40.4 | 56.3429 | 235.5918 | 42.4463 | 0.560184 | defined |  |
| 2015 | physical_site | upper | 1887 | 138 | 5.2994 | 23.3174 | 37.5199 | 53.4711 | 206.5256 | 48.4201 | 0.560521 | defined |  |
| 2016 | physical_site | upper | 2048 | 135 | 5.7129 | 25.2441 | 40.5273 | 57.7148 | 230.2408 | 43.4328 | 0.591168 | defined |  |
| 2017 | physical_site | upper | 2081 | 147 | 5.1898 | 19.9904 | 34.9351 | 53.2917 | 188.5414 | 53.0388 | 0.567029 | defined |  |
| 2018 | physical_site | upper | 2150 | 151 | 3.907 | 17.3953 | 30.6512 | 50.5581 | 166.3991 | 60.0965 | 0.555244 | defined |  |
| 2019 | physical_site | upper | 2259 | 169 | 4.3825 | 17.4413 | 31.1642 | 48.4728 | 158.6434 | 63.0345 | 0.550498 | defined |  |
| 2020 | physical_site | upper | 2350 | 165 | 4.5532 | 19.4043 | 31.8298 | 47.617 | 163.6722 | 61.0977 | 0.549658 | defined |  |
| 2021 | physical_site | upper | 2806 | 174 | 4.3478 | 18.0684 | 30.8624 | 48.1825 | 159.0269 | 62.8824 | 0.562567 | defined |  |
| 2022 | physical_site | upper | 2854 | 167 | 3.9243 | 17.4842 | 29.9229 | 46.5662 | 153.3961 | 65.1907 | 0.554138 | defined |  |
| 2023 | physical_site | upper | 3038 | 176 | 5.7275 | 19.3878 | 32.3568 | 49.5063 | 172.2682 | 58.049 | 0.582878 | defined |  |
| 2024 | physical_site | upper | 3211 | 176 | 4.4534 | 18.5301 | 31.2675 | 47.5553 | 161.5214 | 61.9113 | 0.582255 | defined |  |

Gini first-to-last directions were {"lower": "increase", "midpoint": "increase", "upper": "increase", "visible": "increase"}.
Direction was consistent across scenarios.
All concentration measures remain descriptive.

## Comparison with inclusive concentration

| reporting_year | selected_subcode_hhi_10000 | selected_subcode_effective_center_count | selected_subcode_gini | inclusive_hhi_10000 | inclusive_effective_center_count | inclusive_gini |
| --- | --- | --- | --- | --- | --- | --- |
| 2013 | 352.2681 | 28.3875 | 0.434082 | 364.288 | 27.4508 | 0.537528 |
| 2014 | 343.707 | 29.0945 | 0.498123 | 404.0414 | 24.7499 | 0.569511 |
| 2015 | 335.69 | 29.7894 | 0.492641 | 368.4291 | 27.1423 | 0.541867 |
| 2016 | 354.3583 | 28.22 | 0.551417 | 360.978 | 27.7025 | 0.580493 |
| 2017 | 292.0621 | 34.2393 | 0.521702 | 283.9387 | 35.2189 | 0.570237 |
| 2018 | 251.7116 | 39.728 | 0.485355 | 264.991 | 37.7371 | 0.54862 |
| 2019 | 258.0311 | 38.755 | 0.503984 | 283.8267 | 35.2328 | 0.574961 |
| 2020 | 259.7196 | 38.5031 | 0.512398 | 291.4452 | 34.3118 | 0.583027 |
| 2021 | 238.6424 | 41.9037 | 0.537684 | 267.6753 | 37.3587 | 0.595626 |
| 2022 | 219.1837 | 45.6238 | 0.506338 | 240.6243 | 41.5586 | 0.570912 |
| 2023 | 248.662 | 40.2152 | 0.530417 | 255.0995 | 39.2004 | 0.599867 |
| 2024 | 210.8743 | 47.4216 | 0.517535 | 225.3928 | 44.367 | 0.567657 |

The two series use the same physical-site definitions and concentration functions, but
different endpoints. Their differences must not be interpreted causally.

## Plausibility gates

| scope | check | passed | failed_count | detail |
| --- | --- | --- | --- | --- |
| physical_site_year | de_novo_visible_le_inclusive | True | 0 | mandatory site-year gate |
| physical_site_year | selected_suppression_le_inclusive | True | 0 | mandatory site-year gate |
| physical_site_year | route_a_route_b_visible | True | 0 | mandatory site-year gate |
| physical_site_year | route_a_route_b_suppression | True | 0 | mandatory site-year gate |
| physical_site_year | no_duplicate_site_years | True | 0 |  |
| physical_site_year | code_visible_sum_equals_total | True | 0 |  |
| physical_site_year | code_suppressed_sum_equals_total | True | 0 |  |
| record | only_year_applicable_exact_codes | True | 0 | parent, secondary, residual, other 8-839.8*, and 8-842.* excluded |
| record | 8_839_8a_literal_preserved | True | 0 | exact string check |
| dual_route | all_fields_exact | True | 0 | identifiers, selected codes, code values, and totals |
| year_2013 | national_selected_le_inclusive | True | 0 |  |
| year_2013 | code_contributions_equal_national | True | 0 |  |
| year_2013 | numeric_plus_suppressed_only_equal_identifiable | True | 0 |  |
| year_2013 | visible_categories_sum_to_numeric | True | 0 |  |
| year_2013 | site_sum_equals_national | True | 0 |  |
| year_2013 | thresholds_monotone | True | 0 |  |
| year_2014 | national_selected_le_inclusive | True | 0 |  |
| year_2014 | code_contributions_equal_national | True | 0 |  |
| year_2014 | numeric_plus_suppressed_only_equal_identifiable | True | 0 |  |
| year_2014 | visible_categories_sum_to_numeric | True | 0 |  |
| year_2014 | site_sum_equals_national | True | 0 |  |
| year_2014 | thresholds_monotone | True | 0 |  |
| year_2015 | national_selected_le_inclusive | True | 0 |  |
| year_2015 | code_contributions_equal_national | True | 0 |  |
| year_2015 | numeric_plus_suppressed_only_equal_identifiable | True | 0 |  |
| year_2015 | visible_categories_sum_to_numeric | True | 0 |  |
| year_2015 | site_sum_equals_national | True | 0 |  |
| year_2015 | thresholds_monotone | True | 0 |  |
| year_2016 | national_selected_le_inclusive | True | 0 |  |
| year_2016 | code_contributions_equal_national | True | 0 |  |
| year_2016 | numeric_plus_suppressed_only_equal_identifiable | True | 0 |  |
| year_2016 | visible_categories_sum_to_numeric | True | 0 |  |
| year_2016 | site_sum_equals_national | True | 0 |  |
| year_2016 | thresholds_monotone | True | 0 |  |
| year_2017 | national_selected_le_inclusive | True | 0 |  |
| year_2017 | code_contributions_equal_national | True | 0 |  |
| year_2017 | numeric_plus_suppressed_only_equal_identifiable | True | 0 |  |
| year_2017 | visible_categories_sum_to_numeric | True | 0 |  |
| year_2017 | site_sum_equals_national | True | 0 |  |
| year_2017 | thresholds_monotone | True | 0 |  |
| year_2018 | national_selected_le_inclusive | True | 0 |  |
| year_2018 | code_contributions_equal_national | True | 0 |  |
| year_2018 | numeric_plus_suppressed_only_equal_identifiable | True | 0 |  |
| year_2018 | visible_categories_sum_to_numeric | True | 0 |  |
| year_2018 | site_sum_equals_national | True | 0 |  |
| year_2018 | thresholds_monotone | True | 0 |  |
| year_2019 | national_selected_le_inclusive | True | 0 |  |
| year_2019 | code_contributions_equal_national | True | 0 |  |
| year_2019 | numeric_plus_suppressed_only_equal_identifiable | True | 0 |  |
| year_2019 | visible_categories_sum_to_numeric | True | 0 |  |
| year_2019 | site_sum_equals_national | True | 0 |  |
| year_2019 | thresholds_monotone | True | 0 |  |
| year_2020 | national_selected_le_inclusive | True | 0 |  |
| year_2020 | code_contributions_equal_national | True | 0 |  |
| year_2020 | numeric_plus_suppressed_only_equal_identifiable | True | 0 |  |
| year_2020 | visible_categories_sum_to_numeric | True | 0 |  |
| year_2020 | site_sum_equals_national | True | 0 |  |
| year_2020 | thresholds_monotone | True | 0 |  |
| year_2021 | national_selected_le_inclusive | True | 0 |  |
| year_2021 | code_contributions_equal_national | True | 0 |  |
| year_2021 | numeric_plus_suppressed_only_equal_identifiable | True | 0 |  |
| year_2021 | visible_categories_sum_to_numeric | True | 0 |  |
| year_2021 | site_sum_equals_national | True | 0 |  |
| year_2021 | thresholds_monotone | True | 0 |  |
| year_2022 | national_selected_le_inclusive | True | 0 |  |
| year_2022 | code_contributions_equal_national | True | 0 |  |
| year_2022 | numeric_plus_suppressed_only_equal_identifiable | True | 0 |  |
| year_2022 | visible_categories_sum_to_numeric | True | 0 |  |
| year_2022 | site_sum_equals_national | True | 0 |  |
| year_2022 | thresholds_monotone | True | 0 |  |
| year_2023 | national_selected_le_inclusive | True | 0 |  |
| year_2023 | code_contributions_equal_national | True | 0 |  |
| year_2023 | numeric_plus_suppressed_only_equal_identifiable | True | 0 |  |
| year_2023 | visible_categories_sum_to_numeric | True | 0 |  |
| year_2023 | site_sum_equals_national | True | 0 |  |
| year_2023 | thresholds_monotone | True | 0 |  |
| year_2024 | national_selected_le_inclusive | True | 0 |  |
| year_2024 | code_contributions_equal_national | True | 0 |  |
| year_2024 | numeric_plus_suppressed_only_equal_identifiable | True | 0 |  |
| year_2024 | visible_categories_sum_to_numeric | True | 0 |  |
| year_2024 | site_sum_equals_national | True | 0 |  |
| year_2024 | thresholds_monotone | True | 0 |  |
| year | 89_and_8a_not_applicable_before_2016 | True | 0 | not represented as observed zero |
| raw_source_spot_check | all_available_spot_checks_pass | True | 0 | 12 passed; 0 not available |

## Raw-source spot checks

| reporting_year | spot_check_type | physical_site_id | institution_id | source_files | selected_codes | canonical_code_values | raw_xml_code_values | calculated_site_year_visible | calculated_site_year_suppressed_entries | validation_status | validation_notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013 | openly_numeric_single_code | 260200400-00 | 260200400 | data/xml/xml_2013/260200400-00-2013-xml.xml | 8-839.88 | {"8-839.87": {"suppressed": 0, "visible": 0}, "8-839.88": {"suppressed": 2, "visible": 4}} | {"8-839.87": {"suppressed": 0, "visible": 0}, "8-839.88": {"suppressed": 2, "visible": 4}} | 4 | 2 | passed | raw XML aggregation equals retained canonical code records |
| 2013 | openly_numeric_multi_code | 260101488-00 | 260101488 | data/xml/xml_2013/260101488-00-2013-xml.xml | 8-839.87\|8-839.88 | {"8-839.87": {"suppressed": 1, "visible": 0}, "8-839.88": {"suppressed": 1, "visible": 5}} | {"8-839.87": {"suppressed": 1, "visible": 0}, "8-839.88": {"suppressed": 1, "visible": 5}} | 5 | 2 | passed | raw XML aggregation equals retained canonical code records |
| 2013 | selected_suppressed_entry | 260100023-00 | 260100023 | data/xml/xml_2013/260100023-00-2013-xml.xml | 8-839.87\|8-839.88 | {"8-839.87": {"suppressed": 1, "visible": 0}, "8-839.88": {"suppressed": 1, "visible": 0}} | {"8-839.87": {"suppressed": 1, "visible": 0}, "8-839.88": {"suppressed": 1, "visible": 0}} | 0 | 2 | passed | raw XML aggregation equals retained canonical code records |
| 2013 | high_volume | 260810647-00 | 260810647 | data/xml/xml_2013/260810647-00-2013-xml.xml | 8-839.87\|8-839.88 | {"8-839.87": {"suppressed": 2, "visible": 35}, "8-839.88": {"suppressed": 1, "visible": 62}} | {"8-839.87": {"suppressed": 2, "visible": 35}, "8-839.88": {"suppressed": 1, "visible": 62}} | 97 | 3 | passed | raw XML aggregation equals retained canonical code records |
| 2016 | openly_numeric_single_code | 260310447-00 | 260310447 | data/xml/xml_2016/260310447-00-2016-xml.xml | 8-839.88 | {"8-839.87": {"suppressed": 0, "visible": 0}, "8-839.88": {"suppressed": 0, "visible": 4}, "8-839.89": {"suppressed": 0, "visible": 0}, "8-839.8a": {"suppressed": 0, "visible": 0}} | {"8-839.87": {"suppressed": 0, "visible": 0}, "8-839.88": {"suppressed": 0, "visible": 4}, "8-839.89": {"suppressed": 0, "visible": 0}, "8-839.8a": {"suppressed": 0, "visible": 0}} | 4 | 0 | passed | raw XML aggregation equals retained canonical code records |
| 2016 | openly_numeric_multi_code | 260101488-00 | 260101488 | data/xml/xml_2016/260101488-00-2016-xml.xml | 8-839.87\|8-839.88 | {"8-839.87": {"suppressed": 1, "visible": 0}, "8-839.88": {"suppressed": 0, "visible": 6}, "8-839.89": {"suppressed": 0, "visible": 0}, "8-839.8a": {"suppressed": 0, "visible": 0}} | {"8-839.87": {"suppressed": 1, "visible": 0}, "8-839.88": {"suppressed": 0, "visible": 6}, "8-839.89": {"suppressed": 0, "visible": 0}, "8-839.8a": {"suppressed": 0, "visible": 0}} | 6 | 1 | passed | raw XML aggregation equals retained canonical code records |
| 2016 | selected_suppressed_entry | 260100023-01 | 260100023 | data/xml/xml_2016/260100023-01-2016-xml.xml | 8-839.87 | {"8-839.87": {"suppressed": 2, "visible": 0}, "8-839.88": {"suppressed": 0, "visible": 0}, "8-839.89": {"suppressed": 0, "visible": 0}, "8-839.8a": {"suppressed": 0, "visible": 0}} | {"8-839.87": {"suppressed": 2, "visible": 0}, "8-839.88": {"suppressed": 0, "visible": 0}, "8-839.89": {"suppressed": 0, "visible": 0}, "8-839.8a": {"suppressed": 0, "visible": 0}} | 0 | 2 | passed | raw XML aggregation equals retained canonical code records |
| 2016 | high_volume | 260810647-00 | 260810647 | data/xml/xml_2016/260810647-00-2016-xml.xml | 8-839.87\|8-839.88\|8-839.8a | {"8-839.87": {"suppressed": 1, "visible": 20}, "8-839.88": {"suppressed": 0, "visible": 88}, "8-839.89": {"suppressed": 0, "visible": 0}, "8-839.8a": {"suppressed": 2, "visible": 0}} | {"8-839.87": {"suppressed": 1, "visible": 20}, "8-839.88": {"suppressed": 0, "visible": 88}, "8-839.89": {"suppressed": 0, "visible": 0}, "8-839.8a": {"suppressed": 2, "visible": 0}} | 108 | 3 | passed | raw XML aggregation equals retained canonical code records |
| 2024 | openly_numeric_single_code | 260101193-772660000 | 260101193 | data/xml/xml_2024/260101193-772660000-2024-xml.xml | 8-839.88 | {"8-839.87": {"suppressed": 0, "visible": 0}, "8-839.88": {"suppressed": 1, "visible": 5}, "8-839.89": {"suppressed": 0, "visible": 0}, "8-839.8a": {"suppressed": 0, "visible": 0}} | {"8-839.87": {"suppressed": 0, "visible": 0}, "8-839.88": {"suppressed": 1, "visible": 5}, "8-839.89": {"suppressed": 0, "visible": 0}, "8-839.8a": {"suppressed": 0, "visible": 0}} | 5 | 1 | passed | raw XML aggregation equals retained canonical code records |
| 2024 | openly_numeric_multi_code | 260101488-772073000 | 260101488 | data/xml/xml_2024/260101488-772073000-2024-xml.xml | 8-839.87\|8-839.88 | {"8-839.87": {"suppressed": 1, "visible": 15}, "8-839.88": {"suppressed": 0, "visible": 20}, "8-839.89": {"suppressed": 0, "visible": 0}, "8-839.8a": {"suppressed": 0, "visible": 0}} | {"8-839.87": {"suppressed": 1, "visible": 15}, "8-839.88": {"suppressed": 0, "visible": 20}, "8-839.89": {"suppressed": 0, "visible": 0}, "8-839.8a": {"suppressed": 0, "visible": 0}} | 35 | 1 | passed | raw XML aggregation equals retained canonical code records |
| 2024 | selected_suppressed_entry | 260100034-771320000 | 260100034 | data/xml/xml_2024/260100034-771320000-2024-xml.xml | 8-839.89 | {"8-839.87": {"suppressed": 0, "visible": 0}, "8-839.88": {"suppressed": 0, "visible": 0}, "8-839.89": {"suppressed": 1, "visible": 0}, "8-839.8a": {"suppressed": 0, "visible": 0}} | {"8-839.87": {"suppressed": 0, "visible": 0}, "8-839.88": {"suppressed": 0, "visible": 0}, "8-839.89": {"suppressed": 1, "visible": 0}, "8-839.8a": {"suppressed": 0, "visible": 0}} | 0 | 1 | passed | raw XML aggregation equals retained canonical code records |
| 2024 | high_volume | 260530103-772247000 | 260530103 | data/xml/xml_2024/260530103-772247000-2024-xml.xml | 8-839.87\|8-839.88\|8-839.89\|8-839.8a | {"8-839.87": {"suppressed": 1, "visible": 0}, "8-839.88": {"suppressed": 2, "visible": 118}, "8-839.89": {"suppressed": 1, "visible": 0}, "8-839.8a": {"suppressed": 0, "visible": 13}} | {"8-839.87": {"suppressed": 1, "visible": 0}, "8-839.88": {"suppressed": 2, "visible": 118}, "8-839.89": {"suppressed": 1, "visible": 0}, "8-839.8a": {"suppressed": 0, "visible": 13}} | 131 | 4 | passed | raw XML aggregation equals retained canonical code records |

## Warnings and limitations

- The endpoint is code-occurrence activity, not patients, admissions, cases, or unique procedures.
- Suppressed entries have unknown true values; scenario estimates use the established 0/1/2/3 assumptions.
- The 2015–2016 code-set transition limits direct comparability.
- Internal validation does not replace independent scientific review.

## Proposed manuscript language (draft only)

**Methods:** As a sensitivity analysis, we quantified activity coded with specific de novo
TIPS creation subcodes using year-specific official OPS definitions and the same physical-site,
precedence, concentration, and suppression rules as the inclusive analysis.

**Results:** Activity coded with specific de novo TIPS creation subcodes was evaluated from
2013 through 2024 using two codes through 2015 and four codes thereafter; annual visible
activity, identifiable physical sites, threshold counts, and concentration estimates are
reported in draft Table S10, with exact agreement between two computational routes.

**Limitation:** Comparability across 2015 and 2016 may be affected by the introduction of
additional specific subcodes, and catalogue availability alone cannot separate coding change
from changes in reported activity.

**Recommended Table S10 columns:** year, applicable exact code set, visible selected-code
activity, inclusive visible activity, ratio, identifiable/numeric/suppressed-only sites,
threshold counts, Top-5/Top-10/Top-20 shares, HHI, effective centre count, and Gini.

## Status

De-novo sensitivity analysis completed and internally validated; ready for independent scientific review.
