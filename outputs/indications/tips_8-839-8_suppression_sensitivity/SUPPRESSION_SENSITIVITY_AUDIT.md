# TIPS Suppression Sensitivity Audit

## Assumptions and parser logic

- Each TIPS procedure entry carrying a privacy tag represents 1-3 cases.
- Scenario values are additive per site: visible-only uses published integers; lower-bound adds 1, midpoint adds 2, and upper-bound adds 3 per suppressed entry.
- Direct normal count tags are the only source of visible_count.
- Nested privacy metadata such as Anzahl_FA_Datenschutz=1 is recorded only as a privacy tag and is never interpreted as a published case count.
- Threshold interval classes are definitely_below when upper_count < threshold, uncertain when lower_count < threshold <= upper_count, and definitely_above when lower_count >= threshold.
- Turnover is (entered + exited) / union of active site IDs versus the previous available report year. It is undefined for 2008.

## Visible-only regression

Status: **passed**

| active_centers | cases_total | centers_ge_20 | centers_lt_20 | cases_lt_20 |
| --- | --- | --- | --- | --- |
| 113 | 5247 | 60 | 53 | 568 |

Reference: `outputs/indications/tips_8-839-8_updated2024/tables/latest_year_hospital_code_totals.csv`

## XML scan

- Files scanned: 35163
- TIPS entries parsed: 11158
- Suppressed entries: 7976
- Privacy entries outside the existing inpatient procedure scope: 7
- Excluded element breakdown: {'2012:Ambulante_Operation': 1, '2020:Ambulante_Operation': 2, '2021:Ambulante_Operation': 2, '2024:Ambulante_Operation': 2}
- XML parse errors: 0

## 2024 composition

| year | numerically_active_centers | suppression_only_centers | visible_plus_suppressed_centers | visible_without_suppression_centers | suppressed_entries | active_centers_visible-only | national_volume_visible-only | active_centers_lower-bound | national_volume_lower-bound | active_centers_midpoint | national_volume_midpoint | active_centers_upper-bound | national_volume_upper-bound |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024 | 113 | 80 | 99 | 14 | 560 | 113 | 5247 | 193 | 5807 | 193 | 6367 | 193 | 6927 |

## 2024 interval classification

| year | threshold | definitely_below | uncertain | definitely_above | active_centers |
| --- | --- | --- | --- | --- | --- |
| 2024 | 20 | 112 | 12 | 69 | 193 |
| 2024 | 50 | 151 | 9 | 33 | 193 |
| 2024 | 100 | 174 | 3 | 16 | 193 |
| 2024 | 200 | 187 | 0 | 6 | 193 |

## 2008 and 2024 scenario comparison

| year | scenario | national_volume | active_centers | centers_below | cases_below | centers_ge_20 | centers_ge_50 | centers_ge_100 | centers_ge_200 | top_5_share_pct | top_10_share_pct | top_20_share_pct | hhi_10000 | effective_center_count | gini | median | range | turnover_pct | uncertain_ge_20 | uncertain_ge_50 | uncertain_ge_100 | uncertain_ge_200 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2008 | lower-bound | 1601 | 88 | 68 | 203 | 20 | 11 | 4 | 1 | 43.6602 | 64.772 | 87.3204 | 569.6666 | 17.5541 | 0.766233 | 2.0 | 1-205 |  | 2 | 2 | 1 | 1 |
| 2008 | midpoint | 1780 | 88 | 68 | 324 | 20 | 13 | 5 | 1 | 40.9551 | 60.3371 | 81.7978 | 501.799 | 19.9283 | 0.713458 | 4.0 | 2-206 |  | 2 | 2 | 1 | 1 |
| 2008 | upper-bound | 1959 | 88 | 66 | 403 | 22 | 13 | 5 | 2 | 38.7443 | 56.7126 | 77.2843 | 452.5572 | 22.0967 | 0.671533 | 6.0 | 3-212 |  | 2 | 2 | 1 | 1 |
| 2008 | visible-only | 1422 | 28 | 11 | 134 | 17 | 11 | 3 | 1 | 47.0464 | 70.3938 | 94.2335 | 666.4313 | 15.0053 | 0.475035 | 38.5 | 6-204 |  | 2 | 2 | 1 | 1 |
| 2024 | lower-bound | 5807 | 193 | 124 | 673 | 69 | 33 | 16 | 6 | 21.5085 | 34.8717 | 53.8144 | 199.1999 | 50.2008 | 0.696845 | 10.0 | 1-318 | 28.6996 | 12 | 9 | 3 | 0 |
| 2024 | midpoint | 6367 | 193 | 119 | 831 | 74 | 38 | 18 | 6 | 20.0565 | 32.6684 | 50.6832 | 179.6814 | 55.6541 | 0.65736 | 12.0 | 2-330 | 28.6996 | 12 | 9 | 3 | 0 |
| 2024 | upper-bound | 6927 | 193 | 112 | 919 | 81 | 42 | 19 | 6 | 18.8393 | 30.908 | 48.1882 | 164.7578 | 60.6951 | 0.625923 | 14.0 | 3-342 | 28.6996 | 12 | 9 | 3 | 0 |
| 2024 | visible-only | 5247 | 113 | 53 | 568 | 60 | 31 | 16 | 6 | 23.2704 | 37.6215 | 57.7282 | 225.3928 | 44.367 | 0.567657 | 23.0 | 4-306 | 33.5821 | 12 | 9 | 3 | 0 |

## Geography decision

- Existing >=50 and >=100 isochrones and population-coverage outputs were not recalculated or modified.
- The largest 2024 suppression-only upper-bound site count is 27; therefore no suppression-only site can reach >=50 or >=100.
- This suppression-only argument does not by itself exclude changes among mixed visible-plus-suppressed sites. Those observed membership changes are listed below and in `tables/geographic_threshold_membership_audit_2024.csv`.
- Changes at >=20 are sensitivity classifications only and do not alter the canonical geographic analysis.

| threshold | centers_with_any_membership_change |
| --- | --- |
| 20 | 21 |
| 50 | 11 |
| 100 | 3 |

## Output isolation

All files in this directory are parallel sensitivity outputs. The canonical final report directory and its isochrone/coverage files were not written.
