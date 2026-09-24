# Preliminary official OPS 8-839.8 codebook validation report

- Generation timestamp: `2026-07-28T11:19:32+00:00`
- Git commit: `e162c991af5d699d169240b903a1c35cbb4df5f9`
- Analysis version: `official-ops-88398-v1`
- Manual-review status: **pending**
- Secondary-only analysis release gate: **FAIL — manual approval and catalogue coverage resolution required**

## Scope and evidence boundary

The mapping proposals were derived exclusively from the official year-specific
ClaML wording. The repository's operational code mapping was not used as
evidence. It may only be compared after official manual approval.

Reporting years before 2013 are outside the classifiable range. In particular,
2008, 2010, and 2012 are excluded from every secondary-only computation and an
absence of a primary-placement code in those years must not be interpreted as
secondary-only activity.

## Catalogue sources

- 2013: `2013/ops2013syst_claml_20121012.xml`, SHA-256 `0e965ba2497d176e0a3feb4aa65adf61ba942a48a02963ce0efe858d53a712ee`, PDF `2013/ops2013syst_odt_20121012.pdf`
- 2014: `2014/ops2014syst_claml_20131104.xml`, SHA-256 `90b1a4676aed409da0db313bd735a07be49fc79080ae88459bff9eca676359cc`, PDF `2014/ops2014syst_odt_20131104.pdf`
- 2015: `2015/ops2015syst_claml_20141017.xml`, SHA-256 `e8858a5373ee105f4c6aa26cf8718e7c6a8c1c1e30a6bd3381bd6601bcbcaec8`, PDF `2015/ops2015syst_odt_20141017.pdf`
- 2016: `2016/ops2016syst_claml_20151016.xml`, SHA-256 `390830d8021d5bf6024b9a2d4a59099b18aeb7960df58d93f8ff35bb4c63876d`, PDF `2016/ops2016syst_odt_20151016.pdf`
- 2017: `2017/ops2017syst_claml_20161019.xml`, SHA-256 `1a01defe650df9c98091bc8046754ca4e5d02bffbc61fe81d5071641683b0ac5`, PDF `2017/ops2017syst_odt_20161019.pdf`
- 2018: `2018/ops2018syst_claml_20171018.xml`, SHA-256 `ea7f93017c3c519c884d4f8da306f14f75f98e6ca7b15ec10a866b891556c8e2`, PDF `2018/ops2018syst_odt_20171018.pdf`
- 2019: `2019/ops2019syst-claml.zip::ops2019syst-claml/Klassifikationsdateien/ops2019syst_claml_20181019.xml`, SHA-256 `edc9c958b9e59e38307736053e3215438a234708e594cc59ee777af3e430c58f`, PDF `2019/ops2019syst-pdf-20181203.zip::ops2019syst-pdf-20181203/ops2019syst_referenz_20181203.pdf`
- 2020: `2020/ops2020syst-claml.zip::ops2020syst-claml/Klassifikationsdateien/ops2020syst_claml_20191018.xml`, SHA-256 `91983d4e30e184b9c299fabb9c6d0783efc925cda344c3f83922bfd272bd4879`, PDF `2020/ops2020syst-pdf.zip::ops2020syst-pdf/ops2020syst_referenz_20191018.pdf`
- 2021: `2021/ops2021syst-claml.zip::ops2021syst-claml/Klassifikationsdateien/ops2021syst_claml_20201016.xml`, SHA-256 `8f0e9950f5873a93c52ae614c11130aad032f5159bdadb70eb80e2f3d544acc0`, PDF `2021/ops2021syst-pdf.zip::ops2021syst-pdf/ops2021syst_referenz_20201016.pdf`
- 2022: `2022/ops2022syst-claml.zip::Klassifikationsdateien/ops2022syst_claml_20211022.xml`, SHA-256 `31fd2f6863cbf368dfa202bfb71936ee4404a4097253c047cf4c9e5a142c1481`, PDF `2022/ops2022syst-pdf.zip::Klassifikationsdatei/ops2022syst_referenz_20211022.pdf`
- 2023: `2023/ops2023syst-claml.zip::Klassifikationsdateien/ops2023syst_claml_20221021.xml`, SHA-256 `ecea2866934b97a9294a9d677bc30e0eac4d0a9ec322f51a0e7cd9b546f74705`, PDF `2023/ops2023syst-pdf.zip::Klassifikationsdatei/ops2023syst_referenz_20221021.pdf`
- 2024: `2024/ops2024syst-claml.zip::Klassifikationsdateien/ops2024syst_claml_20231020.xml`, SHA-256 `0baf9c97efdfe1dc5c66ac50fb35b3d6fb1144614cde44515ff2eb829d694110`, PDF `2024/ops2024syst-pdf-20231120.zip::Klassifikationsdatei/ops2024syst_referenz_20231120.pdf`

All 12 required years were discovered deterministically and passed
the OPS ClaML identity checks.

## Extracted family

- Unique year-code definitions: 138
- Unique normalised codes: 12
- Parent definitions: 12
- Residual or otherwise ambiguous definitions: 12
- Codes with wording changes: 8
- Codes with proposed-classification changes: 0
- Automatically verified definitions: 0

## Observed-code coverage

- Observed 2013–2024 records: 7582
- Observed year-code combinations: 131
- Exactly one catalogue match: 130
- Unmatched combinations: 1
- Duplicate matches: 0
- Exactly matched combinations still pending manual review: 130

### Unmatched combinations

| reporting_year | observed_ops_code | number_of_records | visible_activity | number_of_suppressed_entries |
| --- | --- | --- | --- | --- |
| 2013 | 8-839.80 | 5 | 0 | 7 |

## Preliminary activity reconciliation

| reporting_year | records | pre_resolution_visible_activity | reproduced_visible_activity | visible_national_activity | difference | exact_match | suppressed_entries |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2013 | 453 | 2330 | 2124 | 2124 | 0 | True | 355 |
| 2014 | 520 | 2787 | 2511 | 2511 | 0 | True | 417 |
| 2015 | 589 | 2837 | 2546 | 2546 | 0 | True | 471 |
| 2016 | 630 | 2942 | 2715 | 2715 | 0 | True | 510 |
| 2017 | 655 | 3066 | 2801 | 2801 | 0 | True | 490 |
| 2018 | 720 | 3499 | 2977 | 2977 | 0 | True | 558 |
| 2019 | 734 | 3413 | 2972 | 2972 | 0 | True | 586 |
| 2020 | 606 | 3210 | 3210 | 3210 | 0 | True | 469 |
| 2021 | 669 | 4092 | 4092 | 4092 | 0 | True | 492 |
| 2022 | 647 | 4418 | 4418 | 4418 | 0 | True | 484 |
| 2023 | 686 | 4979 | 4979 | 4979 | 0 | True | 503 |
| 2024 | 673 | 5247 | 5247 | 5247 | 0 | True | 491 |

Component-site precedence reproduces the validated annual physical-site totals
exactly, including 5,247 visible procedure occurrences in 2024. The unmatched
2013 code has five suppressed entries and zero visible activity, but it still
blocks codebook coverage and classification. No
primary-versus-secondary site classification, secondary-only analysis, or
manuscript conclusion was generated.

## Required next action

Two reviewers must approve every observed year-code definition. All unmatched
combinations must be resolved before the approved analysis can run. The reviewed
codebook must retain year-specific definitions and must not set
`officially_verified` to true without explicit author approval.
