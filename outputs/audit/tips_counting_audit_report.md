# Audit of TIPS counting and aggregation

Date: 2026-07-17  
Scope: existing `data/xml/xml_<year>` inputs and the production route used for `outputs/indications/tips_8-839-8_updated2024`  
Constraint observed: no existing source, manuscript, figure, or analytical output was changed. Only the six requested files in `outputs/audit/` were created.

## Executive conclusion

**Double counting is demonstrated at the report-aggregation level and possible, but not directly measurable, at the patient/admission level.**

1. **Demonstrated site/aggregate duplication.** The production parser accepts both component-site reports and `Standortnummer 99` Gesamtberichte as separate `facility_id` values, then sums them again by IK. In 2012–2019, 276 IK-years have both report types. In 271 IK-years the visible `-99` total exactly equals the component-site total; those exact pairs contain 2,312 visible counts. All coexisting `-99` reports contribute 2,325 visible counts to the current national sums. This is genuine duplicate aggregation of institutional totals, not merely a hypothetical patient overlap. The responsible code is `src/gba_ops_reanalysis/gba_xml.py:95-102`, `src/gba_ops_reanalysis/longitudinal.py:65-86,112-118`, and `src/gba_ops_reanalysis/indication_supplement.py:173-188`.

2. **Demonstrated mixing of different procedure types.** The prefix selector matches every code beginning `8-839.8`, and every visible code-specific frequency is added. Across all available years, 24,136/47,868 (50.42%) of current visible counts are de novo creation codes, 21,933 (45.82%) are secondary-intervention codes, 1,656 (3.46%) are other/unspecified codes, and 143 (0.30%) are exact parent-code counts. The responsible code is `src/gba_ops_reanalysis/ops_icd.py:41-67,84-91` and `src/gba_ops_reanalysis/longitudinal.py:112-116`.

3. **Parent-child overlap is real but small.** Ten of 2,668 matched site-years (0.37%) contain exact `8-839.8` and a terminal subcode. Removing the exact parent in those site-years reduces the full-period total by 143, compared with 21,392 for the maximum-code diagnostic and 2,325 for site-report precedence. Parent-child coexistence therefore does not explain most of the excess.

4. **Patient-level double counting cannot be resolved from these XMLs.** G-BA reports a department-level absolute frequency for each terminal OPS code, with no admission or patient identifier. A creation and a later angioplasty/revision may concern the same TIPS or different admissions; the aggregate XML cannot distinguish them. Multiple code-specific counts must not be interpreted as unique patients, admissions, or placements.

The current measure is therefore best called **“visible inpatient TIPS-related OPS-coded procedure occurrences”** (or shorter, “visible TIPS-related OPS activity”). The unqualified labels **“TIPS procedures,” “TIPS placements,” “patients,” or “cases” are not defensible** for the current prefix sum.

For a manuscript about de novo TIPS provision, the most defensible primary definition is **H: site-precedence primary creation**: retain `8-839.80` in historical years and `8-839.87/.88/.89/.8a` (case-insensitive) when available, and exclude `-99` aggregate reports whenever component-site reports for the same IK-year are present. It is a visible-only lower bound because privacy-suppressed values remain unknown. Retain the inclusive site-precedence sum, Gu code set, and maximum-code diagnostic as sensitivities; the hierarchy diagnostic adds little.

## 1. Current production logic

The final run used `--ops-selector 8-839.8` and thresholds 20, 50, 100, and 200 (`outputs/indications/tips_8-839-8_updated2024/threshold_audit_final.md:16-28`). `scripts/build_indication_report.py:25-43,47-70` passes the selector to `build_indication_report`; `src/gba_ops_reanalysis/indication_report.py:536-560` converts it to target rules and runs both the latest-year and longitudinal extraction.

### Files, functions, raw fields, and grouping keys

| Stage | Exact implementation | Raw fields / keys | Effect |
|---|---|---|---|
| Discover production inputs | `report_files`, `src/gba_ops_reanalysis/gba_xml.py:52-57` | glob `*-xml.xml` | Only pipeline-eligible filenames are used; `-Land.xml`, `-bund.xml`, and case-mismatched names are outside this glob. This is another possible benchmark difference. |
| Identify OPS rows | `PROCEDURE_PATTERNS`, `PROCEDURE_CODE_NAMES`, `src/gba_ops_reanalysis/gba_xml.py:20-28`; `iter_procedure_counts`, lines 179-185 | `.//Prozedur`; `OPS_301` (fallback aliases exist) | Ambulatory-operation elements are not selected; the audit labels these B-X.7 department records as inpatient. |
| Parse counts | `find_first_int`, `src/gba_ops_reanalysis/gba_xml.py:83-92`; `iter_procedure_counts`, lines 179-185 | direct `Fallzahl` or `Anzahl` (fallback aliases exist) | Non-numeric and privacy-only rows become zero and are discarded. `Fallzahl_Datenschutz`, `Anzahl_Datenschutz`, and nested `*_Gesamtbericht_mit_Datenschutz` are not parsed by production code. |
| Match family | `parse_selector` and `matches_rules`, `src/gba_ops_reanalysis/ops_icd.py:41-67,84-91` | prefix `8-839.8` | All terminal codes, exact parent records, historical `.80`, and upper-case source variants match. |
| Sum repeated same-code rows | `aggregate_counts`, `src/gba_ops_reanalysis/gba_xml.py:188-192`; used at `src/gba_ops_reanalysis/ops_icd.py:127-131` | OPS code within one XML report | Repeated department rows for the same code are added. In the audit, 1,831 site-year-code rows represent more than one raw XML record (maximum 15). |
| Sum different codes in a site-year | `extract_hospital_code_totals`, `src/gba_ops_reanalysis/ops_icd.py:149-152`; longitudinal equivalent `summarize_year`, `src/gba_ops_reanalysis/longitudinal.py:112-116` | `year + facility_id`; `facility_id = IK-Standortnummer` | **Yes: all matched codes are summed.** |
| Collapse duplicate files for a site | `extract_hospital_code_totals`, `src/gba_ops_reanalysis/ops_icd.py:165-195` | `year + facility_id` | Count columns are summed again if multiple eligible files resolve to one site-year. |
| National totals and active sites | `summarize_year`, `src/gba_ops_reanalysis/longitudinal.py:118-152` | site-year rows | National total is the sum of site-year prefix sums; active/threshold flags use the same sum. |
| Threshold outputs | `yearly_threshold_sensitivity`, `src/gba_ops_reanalysis/indication_report.py:229-244`; latest year `threshold_summary_latest_year`, lines 133-150 | site count `>=20/50/100/200` | A site can cross a threshold through addition of different codes. |
| IK aggregation | `aggregate_ik_year`, `src/gba_ops_reanalysis/indication_supplement.py:173-188` | `year + ik` | All `facility_id` rows are summed, including a `-99` aggregate report plus its component sites. |
| Concentration | `build_yearly_concentration_summary`, `src/gba_ops_reanalysis/indication_supplement.py:148-170` | positive site-year totals | Computes top shares, HHI, effective center count, and Gini from the prefix sums. |

### Unit and documentation evidence

The 2008 G-BA data description calls the procedure field `Fallzahl`, defines it as an **absolute count**, requires the OPS code to be terminal, and requires `Fallzahl_Datenschutz` when the count is no more than five: [G-BA Qb-R 2008, Anhang 1, §4.14.1.5-2.1, p.46](https://www.g-ba.de/downloads/62-492-524/2009-07-16_Qb-R-2008_gesamt.pdf).

The 2024 description is more explicit: `Anzahl` is an absolute number, and the frequency of an OPS code is how often the corresponding procedure was performed by the department during the reporting year; it again requires terminal OPS codes: [G-BA 2024 data description, §3.15.1.7.1.1, pp.181-182](https://www.g-ba.de/downloads/17-98-5893/2025-04-17_Qb-R_Anlage_Berichtsjahr-2024_Anhang-1.pdf).

Therefore, a code-specific value is evidence of **coded procedure frequency**, not evidence that it is a unique case/admission. The XML field name changed from `Fallzahl` to `Anzahl`, but neither schema supplies a cross-code patient identifier.

The OPS meanings are also heterogeneous. The official catalogue identifies `.81` angioplasty, `.82` thrombolysis, `.83` thrombectomy, `.84` shunt reduction, `.85` closure, `.86` revision with stent, `.87-.8a` de novo stent creation, and `.8x` other: [BfArM OPS 2018, 8-839.8](https://klassifikationen.bfarm.de/ops/kode-suche/htmlops2018/block-8-80...8-85.htm). Historical `.80` is a creation code; `.87/.88` were introduced when creation was divided into uncovered/covered stents: [BfArM OPS 2013 change note](https://klassifikationen.bfarm.de/ops/kode-suche/htmlops2013/zusatz-03-kommentar.htm).

The `-99` mechanism is documented separately: a Gesamtbericht takes the union of component-site procedure codes and sums their counts; privacy-aware totals use `Anzahl_Gesamtbericht_mit_Datenschutz`: [G-BA 2018 Gesamtbericht aggregation guide, B-X.7, p.76](https://www.g-ba.de/downloads/17-98-4787/2019-09-04_Anlage-1_Qb2018_Aggregationsanleitung-Gesamtbericht.pdf). It is consequently incorrect to add a visible `-99` total to the same IK's component-site totals.

Actual records confirm every field form. Examples include `data/xml/xml_2008/260914050-00-2008-xml.xml:7521-7522` (`OPS_301` plus visible `Fallzahl`), the same file at lines 7749-7750 (`Fallzahl_Datenschutz`), `data/xml/xml_2018/260920069-01-2018-xml.xml:6672-6673` (`OPS_301` plus visible `Anzahl`), and `data/xml/xml_2012/260571421-99-2012-xml.xml:30043-30046` (privacy-aware Gesamtbericht wrapper). The audit preserves all these forms; production code preserves only direct visible numeric values.

## 2. Audit datasets and definitions

`outputs/audit/tips_code_level_audit.csv` has 8,328 site-year-code rows representing 11,158 raw matching XML procedure records. Its `numeric_count` includes visible direct or nested Gesamtbericht values; `current_parser_numeric_count` isolates what production code actually counts. There are 6,429 rows with a privacy signal and 534 rows using a Gesamtbericht count wrapper. Nested visible subtotals add 212 values that production currently ignores.

`outputs/audit/tips_site_year_overlap_audit.csv` has 2,668 site-years. It includes all requested overlap fields, site-report type and precedence flags, and exhaustive threshold categories under each definition.

The annual comparison includes the six requested definitions plus two diagnostics required by the discovered report-level duplication:

- **A current:** sum every direct visible matched code count in every production-eligible site report.
- **B maximum:** largest direct visible matched code count per site-year; lower diagnostic only.
- **C hierarchy:** exclude exact `8-839.8` when any terminal code exists.
- **D Gu:** exact requested set `.8, .81, .82, .83, .85, .87, .88, .89, .8a, .8x` (case-insensitive for source variants).
- **E primary creation:** `.80, .87, .88, .89, .8a`.
- **F secondary intervention:** `.81-.86`.
- **G site-precedence current:** A, but set `-99` to zero whenever component-site reports exist for the same IK-year.
- **H site-precedence primary creation:** E with the same site precedence.

Missing source years 2009 and 2011 are represented as unavailable/blank, not zero.

## 3. Overlap within site-years

Of 2,668 site-years containing at least one visible or suppressed matched record:

| Matched-code pattern | Site-years | Percent |
|---|---:|---:|
| One distinct code | 623 | 23.35% |
| Two distinct codes | 711 | 26.65% |
| Three or more distinct codes | 1,334 | 50.00% |
| Exact `8-839.8` plus terminal code(s) | 10 | 0.37% |
| Multiple terminal codes | 2,043 | 76.57% |

The general parent contributes only 0.30% of current visible volume. Primary and secondary codes contribute 50.42% and 45.82%, respectively. Thus, almost half of the current measure is explicitly non-primary activity. The large number of multi-code site-years establishes scope for admission/patient overlap but does not prove which records refer to the same patient.

Parent-child coexistence contributes 143 counts to `A - C`. By comparison, multi-code selection contributes 21,392 to `A - B`, and coexisting Gesamtberichte contribute 2,325 to `A - G`. The latter is demonstrated duplicate aggregation; `A - B` is only a lower diagnostic because legitimate separate procedures are also removed.

## 4. Annual totals

Complete 2008-2024 values and ratios to A are in `outputs/audit/tips_annual_aggregation_comparison.csv`.

| Year | A current | B maximum | C hierarchy | D Gu | E primary | G site precedence | H site-precedence primary |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2008 | 1,422 | 1,000 | 1,371 | 549 | 873 | 1,422 | 873 |
| 2010 | 1,419 | 998 | 1,335 | 588 | 831 | 1,419 | 831 |
| 2012 | 2,207 | 1,381 | 2,207 | 881 | 1,263 | 2,110 | 1,205 |
| 2013 | 2,330 | 1,259 | 2,326 | 2,238 | 1,142 | 2,124 | 1,042 |
| 2014 | 2,787 | 1,459 | 2,783 | 2,664 | 1,430 | 2,511 | 1,291 |
| 2015 | 2,837 | 1,490 | 2,837 | 2,701 | 1,446 | 2,546 | 1,308 |
| 2016 | 2,942 | 1,620 | 2,942 | 2,830 | 1,543 | 2,715 | 1,427 |
| 2017 | 3,066 | 1,747 | 3,066 | 2,910 | 1,564 | 2,801 | 1,436 |
| 2018 | 3,499 | 1,910 | 3,499 | 3,323 | 1,727 | 2,977 | 1,475 |
| 2019 | 3,413 | 1,911 | 3,413 | 3,248 | 1,736 | 2,972 | 1,482 |
| 2020 | 3,210 | 1,808 | 3,210 | 3,066 | 1,621 | 3,210 | 1,621 |
| 2021 | 4,092 | 2,245 | 4,092 | 3,886 | 2,032 | 4,092 | 2,032 |
| 2022 | 4,418 | 2,328 | 4,418 | 4,216 | 2,119 | 4,418 | 2,119 |
| 2023 | 4,979 | 2,563 | 4,979 | 4,620 | 2,261 | 4,979 | 2,261 |
| 2024 | 5,247 | 2,757 | 5,247 | 4,974 | 2,548 | 5,247 | 2,548 |

The site-precedence correction is zero after 2019 because the production-eligible input set no longer contains coexisting visible `-99` records for matched activity. It is substantial in 2018 (522 counts; 14.92% of A) and 2019 (441; 12.92%). It does not explain the 2008 excess.

## 5. Provider volume and apparent overcounting

Among visible active site-years, Spearman correlation between current volume and `current/maximum` is **rho=0.613** (n=1,327); correlation with `current/Gu` is **rho=0.548** (n=1,269), and with `current/primary` is **rho=0.495** (n=1,195). Median `current/maximum` rises across current-volume quartiles from 1.00 to 1.80, 1.82, and 1.93 (median current volumes 5, 12, 27, and 79). Larger providers therefore accumulate more distinct code-specific activity. This descriptive association means concentration based on the inclusive sum can differ systematically by provider size; it is not a causal test and partly reflects the mathematical construction of the ratio.

## 6. Structural results and robustness

All site- and IK-level metrics are in `outputs/audit/tips_structural_metrics_comparison.csv`. Requested A-D definitions are present; E-H are included to make the recommended construct and the report-level duplication auditable.

For 2024 at site level:

| Definition | Count | Active | >=20 | >=50 | >=100 | >=200 | Top-5 | Top-10 | Top-20 | HHI | Effective centers | Gini |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A current | 5,247 | 113 | 60 | 31 | 16 | 6 | 23.27% | 37.62% | 57.73% | 225.39 | 44.37 | 0.5677 |
| B maximum | 2,757 | 113 | 43 | 17 | 4 | 0 | 20.67% | 34.68% | 54.15% | 200.63 | 49.84 | 0.5199 |
| C hierarchy | 5,247 | 113 | 60 | 31 | 16 | 6 | 23.27% | 37.62% | 57.73% | 225.39 | 44.37 | 0.5677 |
| D Gu | 4,974 | 113 | 60 | 30 | 15 | 3 | 22.44% | 36.37% | 56.13% | 216.27 | 46.24 | 0.5551 |
| E/H primary | 2,548 | 106 | 44 | 14 | 4 | 0 | 21.94% | 36.70% | 54.91% | 210.87 | 47.42 | 0.5175 |

Threshold membership is exhaustively identified by hospital/site in the `threshold_category_*` and `threshold_category_changed_*` columns of `tips_site_year_overlap_audit.csv`. Across all years, compared with A:

- C changes only 1 site-year at each of >=20, >=50, and >=100, and none at >=200.
- D loses 46, 32, 25, and 6 site-years at >=20, >=50, >=100, and >=200.
- B loses 238, 130, 105, and 25.
- E loses 268, 142, 110, and 25.

The current >=20/50/100/200 classifications are **robust to parent removal**, fairly robust to the Gu set at >=20/50, but **not robust to a distinct-creation construct or the maximum diagnostic**, especially at >=100 and >=200. For 2024, primary creation changes the current 60/31/16/6 sites to 44/14/4/0.

No requested concentration trend reverses direction. Across available years, Spearman correlations with year are negative for top-5/top-10/top-20 share and HHI and positive for effective center count under A, B, C, D, E, G, and H. The main decentralization conclusion is therefore robust for these size-weighted measures. Gini rises under every definition, showing that inequality among active providers can increase even as national top shares and HHI fall; the manuscript should state both rather than call every concentration measure unidirectional.

## 7. External benchmarks

The complete table is `outputs/audit/tips_external_benchmark_comparison.csv`. Gu reports nationwide DRG **admissions/patients with TIPS insertion**, with 1,209 in 2008 and 2,093 in 2018: [Gu et al., Table 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC10503680/). Loosen reports InEK TIPS patients identified with `8-839.8, .81, .82, .83, .85, .87, .88, .89, .8a, .8x`, rising from 2,180 in 2019 to 2,954 in 2023: [Loosen et al., methods and Figure 1](https://www.mdpi.com/2075-4418/15/15/1902).

| Year | Published source | Published count | A current | G site precedence | B maximum | H site-precedence primary |
|---:|---|---:|---:|---:|---:|---:|
| 2008 | Gu DRG | 1,209 | 1,422 | 1,422 | 1,000 | 873 |
| 2018 | Gu DRG | 2,093 | 3,499 | 2,977 | 1,910 | 1,475 |
| 2019 | Loosen InEK | 2,180 | 3,413 | 2,972 | 1,911 | 1,482 |
| 2020 | Loosen InEK | 2,264 | 3,210 | 3,210 | 1,808 | 1,621 |
| 2021 | Loosen InEK | 2,702 | 4,092 | 4,092 | 2,245 | 2,032 |
| 2022 | Loosen InEK | 2,805 | 4,418 | 4,418 | 2,328 | 2,119 |
| 2023 | Loosen InEK | 2,954 | 4,979 | 4,979 | 2,563 | 2,261 |

These values should not be forced to agree:

- **Unit:** G-BA contains department/code procedure frequencies; Gu analyzes admissions, and Loosen describes patients/placements from aggregated InEK data.
- **Code handling:** a patient-level DRG/InEK query can select an admission once when any code is present; G-BA prefix summation adds every code frequency.
- **Primary versus secondary:** A includes creation, angioplasty, thrombolysis, thrombectomy, shunt reduction, closure, revision, and other activity.
- **Site versus institution:** production A double-counts coexisting aggregate `-99` and component reports in 2012-2019.
- **Suppression:** visible-only G-BA totals are lower bounds; 6,429 code-level rows carry a privacy signal.
- **Reporting selection:** production uses only files matched by `*-xml.xml` (`src/gba_ops_reanalysis/gba_xml.py:52-57`), while the source folders also contain other report filename variants.
- **Reporting requirements/data quality:** G-BA requires terminal codes, yet 12 exact `8-839.8` site-year-code rows exist, so actual XML does not perfectly obey the documented rule.

The fact that B is numerically closest in several benchmark years does not validate B. The maximum can discard genuine separate interventions and is retained only as a lower diagnostic.

## 8. Manuscript and output implications

### Recommended primary and sensitivities

- **Primary:** H site-precedence primary creation, described as visible de novo TIPS creation-code occurrences. State explicitly that privacy suppression makes it a lower bound.
- **Sensitivity 1:** G site-precedence inclusive TIPS-related OPS activity.
- **Sensitivity 2:** D Gu code set with site precedence added in any manuscript implementation.
- **Sensitivity 3:** B maximum-code diagnostic, explicitly not an estimate of truth.
- **Hierarchy:** retain as a narrow data-quality diagnostic; it is nearly identical to A.

### Tables 1 and S1-S3

Any table currently reporting the prefix sum as cases, patients, placements, or procedures must be relabeled or recalculated. Table 1 should use H for annual national creation volume and provider thresholds if the scientific question is de novo TIPS provision. Supplementary tables listing centers, threshold categories, or concentration should be regenerated from the same definition. A separate sensitivity table can show A/G, D, and B. The current threshold categories cannot be carried unchanged into a creation-only primary analysis.

### Figures 1-3

Any panel using annual volume, active-center counts, threshold counts, rankings, shares, HHI, effective centers, or Gini must be regenerated from the chosen primary definition. In the existing output naming, this directly affects `figures/01_yearly_trends.png`, `02_threshold_counts_latest_year.png`, `03_top_centers_latest_year.png`, `04_case_distribution_latest_year.png`, and `11_concentration_trends.png`; their production inputs are written at `src/gba_ops_reanalysis/indication_report.py:576-595` and `src/gba_ops_reanalysis/indication_supplement.py:148-170`.

No geographic isochrone was recalculated in this audit. Because 2024 creation-only thresholds are materially smaller than current thresholds, maps and access estimates based on >=50 or >=100 should not be treated as robust until the primary counting definition is finalized and those analyses are rerun.

## 9. Deliverables and validation

- `outputs/audit/tips_counting_audit_report.md`
- `outputs/audit/tips_code_level_audit.csv`
- `outputs/audit/tips_site_year_overlap_audit.csv`
- `outputs/audit/tips_annual_aggregation_comparison.csv`
- `outputs/audit/tips_structural_metrics_comparison.csv`
- `outputs/audit/tips_external_benchmark_comparison.csv`

Validation checks reproduced production A exactly for every available year, including 2008=1,422, 2018=3,499, 2023=4,979, and 2024=5,247. Requested years without local inputs (2009 and 2011) are explicitly marked unavailable. Counts in all comparison tables are visible-only unless the code-level table's raw `numeric_count` is being inspected.
