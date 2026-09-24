# Manual review of the official OPS 8-839.8 mapping

- Generation timestamp: `2026-07-28T11:19:32+00:00`
- Git commit: `e162c991af5d699d169240b903a1c35cbb4df5f9`
- Analysis version: `official-ops-88398-v1`
- Overall approval: **PENDING**

## Mandatory interpretation boundary

This package establishes proposed meanings from official BfArM catalogue wording.
It does not establish an author-approved primary-versus-secondary mapping.
No secondary-only analysis may be considered final until every observed
year-code combination has an approved classification from two reviewers and
`officially_verified` is explicitly set to true.

Reporting years before 2013 are outside the classifiable range because codes
specifically denoting primary TIPS placement were not available across the
earlier period. The years 2008, 2010, and 2012 must never enter a secondary-only
computation. Absence of a primary-placement code before 2013 is not evidence of
secondary-only activity.

## Review summary

- Year-code definitions: 138
- Ambiguous or parent definitions: 24
- Codes with wording or proposed-classification changes: 8
- Observed year-code combinations without exactly one official match: 1

## Ambiguous definitions

| reporting_year | ops_code_official | official_full_label | proposed_classification | pdf_reference |
| --- | --- | --- | --- | --- |
| 2013 | 8-839.8 | Portosystemischer Shunt (TIPSS) | unresolved_parent | 2013/ops2013syst_odt_20121012.pdf |
| 2013 | 8-839.8x | Sonstige | unresolved_other | 2013/ops2013syst_odt_20121012.pdf |
| 2014 | 8-839.8 | Portosystemischer Shunt (TIPSS) | unresolved_parent | 2014/ops2014syst_odt_20131104.pdf |
| 2014 | 8-839.8x | Sonstige | unresolved_other | 2014/ops2014syst_odt_20131104.pdf |
| 2015 | 8-839.8 | Portosystemischer Shunt (TIPSS) | unresolved_parent | 2015/ops2015syst_odt_20141017.pdf |
| 2015 | 8-839.8x | Sonstige | unresolved_other | 2015/ops2015syst_odt_20141017.pdf |
| 2016 | 8-839.8 | Portosystemischer Shunt (TIPSS) | unresolved_parent | 2016/ops2016syst_odt_20151016.pdf |
| 2016 | 8-839.8x | Sonstige | unresolved_other | 2016/ops2016syst_odt_20151016.pdf |
| 2017 | 8-839.8 | Portosystemischer Shunt (TIPSS) | unresolved_parent | 2017/ops2017syst_odt_20161019.pdf |
| 2017 | 8-839.8x | Sonstige | unresolved_other | 2017/ops2017syst_odt_20161019.pdf |
| 2018 | 8-839.8 | Portosystemischer Shunt (TIPS) | unresolved_parent | 2018/ops2018syst_odt_20171018.pdf |
| 2018 | 8-839.8x | Sonstige | unresolved_other | 2018/ops2018syst_odt_20171018.pdf |
| 2019 | 8-839.8 | Portosystemischer Shunt (TIPS) | unresolved_parent | 2019/ops2019syst-pdf-20181203.zip::ops2019syst-pdf-20181203/ops2019syst_referenz_20181203.pdf |
| 2019 | 8-839.8x | Sonstige | unresolved_other | 2019/ops2019syst-pdf-20181203.zip::ops2019syst-pdf-20181203/ops2019syst_referenz_20181203.pdf |
| 2020 | 8-839.8 | Portosystemischer Shunt (TIPS) | unresolved_parent | 2020/ops2020syst-pdf.zip::ops2020syst-pdf/ops2020syst_referenz_20191018.pdf |
| 2020 | 8-839.8x | Sonstige | unresolved_other | 2020/ops2020syst-pdf.zip::ops2020syst-pdf/ops2020syst_referenz_20191018.pdf |
| 2021 | 8-839.8 | Portosystemischer Shunt (TIPS) | unresolved_parent | 2021/ops2021syst-pdf.zip::ops2021syst-pdf/ops2021syst_referenz_20201016.pdf |
| 2021 | 8-839.8x | Sonstige | unresolved_other | 2021/ops2021syst-pdf.zip::ops2021syst-pdf/ops2021syst_referenz_20201016.pdf |
| 2022 | 8-839.8 | Portosystemischer Shunt (TIPS) | unresolved_parent | 2022/ops2022syst-pdf.zip::Klassifikationsdatei/ops2022syst_referenz_20211022.pdf |
| 2022 | 8-839.8x | Sonstige | unresolved_other | 2022/ops2022syst-pdf.zip::Klassifikationsdatei/ops2022syst_referenz_20211022.pdf |
| 2023 | 8-839.8 | Portosystemischer Shunt (TIPS) | unresolved_parent | 2023/ops2023syst-pdf.zip::Klassifikationsdatei/ops2023syst_referenz_20221021.pdf |
| 2023 | 8-839.8x | Sonstige | unresolved_other | 2023/ops2023syst-pdf.zip::Klassifikationsdatei/ops2023syst_referenz_20221021.pdf |
| 2024 | 8-839.8 | Portosystemischer Shunt (TIPS) | unresolved_parent | 2024/ops2024syst-pdf-20231120.zip::Klassifikationsdatei/ops2024syst_referenz_20231120.pdf |
| 2024 | 8-839.8x | Sonstige | unresolved_other | 2024/ops2024syst-pdf-20231120.zip::Klassifikationsdatei/ops2024syst_referenz_20231120.pdf |

## Cross-year changes requiring attention

| ops_code_normalised | first_year_present | last_year_present | wording_changed | proposed_classification_changed | wording_by_years |
| --- | --- | --- | --- | --- | --- |
| 8-839.8 | 2013 | 2024 | True | False | 2018,2019,2020,2021,2022,2023,2024: Portosystemischer Shunt (TIPS) \|\| 2013,2014,2015,2016,2017: Portosystemischer Shunt (TIPSS) |
| 8-839.81 | 2013 | 2024 | True | False | 2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023: Perkutane (Ballon-)Angioplastie \|\| 2024: Perkutane (Ballon-)Angioplastie \| [inclusion] Vergrößerung eines bestehenden portosystemischen Shuntes |
| 8-839.84 | 2013 | 2024 | True | False | 2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023: Perkutane Verkleinerung eines bestehenden portosystemischen Shunts \|\| 2024: Perkutanes Einlegen eines Stents in einen bestehenden portosystemischen Shunt \| [inclusion] Stent-in-TIPS-Stent |
| 8-839.86 | 2013 | 2024 | True | False | 2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023: Revision mit Stenteinlage \|\| 2024: Verlängerung eines bestehenden portosystemischen Shuntes durch Stenteinlage |
| 8-839.87 | 2013 | 2024 | True | False | 2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023: Perkutanes Anlegen eines ungecoverten Stents \|\| 2024: Perkutanes Anlegen eines ungecoverten Stents \| [inclusion] Angioplastie zur Herstellung eines Shuntes zwischen portalvenösen und venösen Lebergefäßen innerhalb des Leberparenchyms |
| 8-839.88 | 2013 | 2024 | True | False | 2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023: Perkutanes Anlegen eines gecoverten Stents \|\| 2024: Perkutanes Anlegen eines gecoverten Stents \| [inclusion] Angioplastie zur Herstellung eines Shuntes zwischen portalvenösen und venösen Lebergefäßen innerhalb des Leberparenchyms |
| 8-839.89 | 2016 | 2024 | True | False | 2017,2018,2019,2020,2021,2022,2023: Perkutanes Anlegen von 2 oder mehr ungecoverten Stents \|\| 2024: Perkutanes Anlegen von 2 oder mehr ungecoverten Stents \| [inclusion] Angioplastie zur Herstellung eines Shuntes zwischen portalvenösen und venösen Lebergefäßen innerhalb des Leberparenchyms \|\| 2016: Perkutanes Anlegen von 2 und mehr ungecoverten Stents |
| 8-839.8a | 2016 | 2024 | True | False | 2017,2018,2019,2020,2021,2022,2023: Perkutanes Anlegen von 2 oder mehr gecoverten Stents \|\| 2024: Perkutanes Anlegen von 2 oder mehr gecoverten Stents \| [inclusion] Angioplastie zur Herstellung eines Shuntes zwischen portalvenösen und venösen Lebergefäßen innerhalb des Leberparenchyms \|\| 2016: Perkutanes Anlegen von 2 und mehr gecoverten Stents |

## Uncovered or multiply matched observed combinations

| reporting_year | observed_ops_code | codebook_match_count | number_of_records | visible_activity | number_of_suppressed_entries |
| --- | --- | --- | --- | --- | --- |
| 2013 | 8-839.80 | 0 | 5 | 0 | 7 |

## Approval fields

Overall reviewer 1: ____________________  Date: __________  Approved: YES / NO

Overall reviewer 2: ____________________  Date: __________  Approved: YES / NO

Overall comment: ____________________________________________________________

## Code-by-code review

### `8-839.8`
| reporting_year | official_full_label | official_notes | proposed_classification | classification_reason | source_file | pdf_reference | manual_reviewer_1 | manual_reviewer_2 | manual_review_status | manual_review_comment | officially_verified |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013 | Portosystemischer Shunt (TIPSS) |  | unresolved_parent | The family heading has no terminal procedure meaning and is retained as a parent code. | 2013/ops2013syst_claml_20121012.xml | 2013/ops2013syst_odt_20121012.pdf |  |  | pending |  | False |
| 2014 | Portosystemischer Shunt (TIPSS) |  | unresolved_parent | The family heading has no terminal procedure meaning and is retained as a parent code. | 2014/ops2014syst_claml_20131104.xml | 2014/ops2014syst_odt_20131104.pdf |  |  | pending |  | False |
| 2015 | Portosystemischer Shunt (TIPSS) |  | unresolved_parent | The family heading has no terminal procedure meaning and is retained as a parent code. | 2015/ops2015syst_claml_20141017.xml | 2015/ops2015syst_odt_20141017.pdf |  |  | pending |  | False |
| 2016 | Portosystemischer Shunt (TIPSS) |  | unresolved_parent | The family heading has no terminal procedure meaning and is retained as a parent code. | 2016/ops2016syst_claml_20151016.xml | 2016/ops2016syst_odt_20151016.pdf |  |  | pending |  | False |
| 2017 | Portosystemischer Shunt (TIPSS) |  | unresolved_parent | The family heading has no terminal procedure meaning and is retained as a parent code. | 2017/ops2017syst_claml_20161019.xml | 2017/ops2017syst_odt_20161019.pdf |  |  | pending |  | False |
| 2018 | Portosystemischer Shunt (TIPS) |  | unresolved_parent | The family heading has no terminal procedure meaning and is retained as a parent code. | 2018/ops2018syst_claml_20171018.xml | 2018/ops2018syst_odt_20171018.pdf |  |  | pending |  | False |
| 2019 | Portosystemischer Shunt (TIPS) |  | unresolved_parent | The family heading has no terminal procedure meaning and is retained as a parent code. | 2019/ops2019syst-claml.zip::ops2019syst-claml/Klassifikationsdateien/ops2019syst_claml_20181019.xml | 2019/ops2019syst-pdf-20181203.zip::ops2019syst-pdf-20181203/ops2019syst_referenz_20181203.pdf |  |  | pending |  | False |
| 2020 | Portosystemischer Shunt (TIPS) |  | unresolved_parent | The family heading has no terminal procedure meaning and is retained as a parent code. | 2020/ops2020syst-claml.zip::ops2020syst-claml/Klassifikationsdateien/ops2020syst_claml_20191018.xml | 2020/ops2020syst-pdf.zip::ops2020syst-pdf/ops2020syst_referenz_20191018.pdf |  |  | pending |  | False |
| 2021 | Portosystemischer Shunt (TIPS) |  | unresolved_parent | The family heading has no terminal procedure meaning and is retained as a parent code. | 2021/ops2021syst-claml.zip::ops2021syst-claml/Klassifikationsdateien/ops2021syst_claml_20201016.xml | 2021/ops2021syst-pdf.zip::ops2021syst-pdf/ops2021syst_referenz_20201016.pdf |  |  | pending |  | False |
| 2022 | Portosystemischer Shunt (TIPS) |  | unresolved_parent | The family heading has no terminal procedure meaning and is retained as a parent code. | 2022/ops2022syst-claml.zip::Klassifikationsdateien/ops2022syst_claml_20211022.xml | 2022/ops2022syst-pdf.zip::Klassifikationsdatei/ops2022syst_referenz_20211022.pdf |  |  | pending |  | False |
| 2023 | Portosystemischer Shunt (TIPS) |  | unresolved_parent | The family heading has no terminal procedure meaning and is retained as a parent code. | 2023/ops2023syst-claml.zip::Klassifikationsdateien/ops2023syst_claml_20221021.xml | 2023/ops2023syst-pdf.zip::Klassifikationsdatei/ops2023syst_referenz_20221021.pdf |  |  | pending |  | False |
| 2024 | Portosystemischer Shunt (TIPS) |  | unresolved_parent | The family heading has no terminal procedure meaning and is retained as a parent code. | 2024/ops2024syst-claml.zip::Klassifikationsdateien/ops2024syst_claml_20231020.xml | 2024/ops2024syst-pdf-20231120.zip::Klassifikationsdatei/ops2024syst_referenz_20231120.pdf |  |  | pending |  | False |

Reviewer 1: ____________________  Decision: __________

Reviewer 2: ____________________  Decision: __________

Comment: ______________________________________________________________
### `8-839.81`
| reporting_year | official_full_label | official_notes | proposed_classification | classification_reason | source_file | pdf_reference | manual_reviewer_1 | manual_reviewer_2 | manual_review_status | manual_review_comment | officially_verified |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013 | Perkutane (Ballon-)Angioplastie |  | secondary_intervention | The official terminal wording explicitly describes angioplasty rather than primary shunt placement. | 2013/ops2013syst_claml_20121012.xml | 2013/ops2013syst_odt_20121012.pdf |  |  | pending |  | False |
| 2014 | Perkutane (Ballon-)Angioplastie |  | secondary_intervention | The official terminal wording explicitly describes angioplasty rather than primary shunt placement. | 2014/ops2014syst_claml_20131104.xml | 2014/ops2014syst_odt_20131104.pdf |  |  | pending |  | False |
| 2015 | Perkutane (Ballon-)Angioplastie |  | secondary_intervention | The official terminal wording explicitly describes angioplasty rather than primary shunt placement. | 2015/ops2015syst_claml_20141017.xml | 2015/ops2015syst_odt_20141017.pdf |  |  | pending |  | False |
| 2016 | Perkutane (Ballon-)Angioplastie |  | secondary_intervention | The official terminal wording explicitly describes angioplasty rather than primary shunt placement. | 2016/ops2016syst_claml_20151016.xml | 2016/ops2016syst_odt_20151016.pdf |  |  | pending |  | False |
| 2017 | Perkutane (Ballon-)Angioplastie |  | secondary_intervention | The official terminal wording explicitly describes angioplasty rather than primary shunt placement. | 2017/ops2017syst_claml_20161019.xml | 2017/ops2017syst_odt_20161019.pdf |  |  | pending |  | False |
| 2018 | Perkutane (Ballon-)Angioplastie |  | secondary_intervention | The official terminal wording explicitly describes angioplasty rather than primary shunt placement. | 2018/ops2018syst_claml_20171018.xml | 2018/ops2018syst_odt_20171018.pdf |  |  | pending |  | False |
| 2019 | Perkutane (Ballon-)Angioplastie |  | secondary_intervention | The official terminal wording explicitly describes angioplasty rather than primary shunt placement. | 2019/ops2019syst-claml.zip::ops2019syst-claml/Klassifikationsdateien/ops2019syst_claml_20181019.xml | 2019/ops2019syst-pdf-20181203.zip::ops2019syst-pdf-20181203/ops2019syst_referenz_20181203.pdf |  |  | pending |  | False |
| 2020 | Perkutane (Ballon-)Angioplastie |  | secondary_intervention | The official terminal wording explicitly describes angioplasty rather than primary shunt placement. | 2020/ops2020syst-claml.zip::ops2020syst-claml/Klassifikationsdateien/ops2020syst_claml_20191018.xml | 2020/ops2020syst-pdf.zip::ops2020syst-pdf/ops2020syst_referenz_20191018.pdf |  |  | pending |  | False |
| 2021 | Perkutane (Ballon-)Angioplastie |  | secondary_intervention | The official terminal wording explicitly describes angioplasty rather than primary shunt placement. | 2021/ops2021syst-claml.zip::ops2021syst-claml/Klassifikationsdateien/ops2021syst_claml_20201016.xml | 2021/ops2021syst-pdf.zip::ops2021syst-pdf/ops2021syst_referenz_20201016.pdf |  |  | pending |  | False |
| 2022 | Perkutane (Ballon-)Angioplastie |  | secondary_intervention | The official terminal wording explicitly describes angioplasty rather than primary shunt placement. | 2022/ops2022syst-claml.zip::Klassifikationsdateien/ops2022syst_claml_20211022.xml | 2022/ops2022syst-pdf.zip::Klassifikationsdatei/ops2022syst_referenz_20211022.pdf |  |  | pending |  | False |
| 2023 | Perkutane (Ballon-)Angioplastie |  | secondary_intervention | The official terminal wording explicitly describes angioplasty rather than primary shunt placement. | 2023/ops2023syst-claml.zip::Klassifikationsdateien/ops2023syst_claml_20221021.xml | 2023/ops2023syst-pdf.zip::Klassifikationsdatei/ops2023syst_referenz_20221021.pdf |  |  | pending |  | False |
| 2024 | Perkutane (Ballon-)Angioplastie | [inclusion] Vergrößerung eines bestehenden portosystemischen Shuntes | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2024/ops2024syst-claml.zip::Klassifikationsdateien/ops2024syst_claml_20231020.xml | 2024/ops2024syst-pdf-20231120.zip::Klassifikationsdatei/ops2024syst_referenz_20231120.pdf |  |  | pending |  | False |

Reviewer 1: ____________________  Decision: __________

Reviewer 2: ____________________  Decision: __________

Comment: ______________________________________________________________
### `8-839.82`
| reporting_year | official_full_label | official_notes | proposed_classification | classification_reason | source_file | pdf_reference | manual_reviewer_1 | manual_reviewer_2 | manual_review_status | manual_review_comment | officially_verified |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013 | Perkutane Thrombolyse |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2013/ops2013syst_claml_20121012.xml | 2013/ops2013syst_odt_20121012.pdf |  |  | pending |  | False |
| 2014 | Perkutane Thrombolyse |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2014/ops2014syst_claml_20131104.xml | 2014/ops2014syst_odt_20131104.pdf |  |  | pending |  | False |
| 2015 | Perkutane Thrombolyse |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2015/ops2015syst_claml_20141017.xml | 2015/ops2015syst_odt_20141017.pdf |  |  | pending |  | False |
| 2016 | Perkutane Thrombolyse |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2016/ops2016syst_claml_20151016.xml | 2016/ops2016syst_odt_20151016.pdf |  |  | pending |  | False |
| 2017 | Perkutane Thrombolyse |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2017/ops2017syst_claml_20161019.xml | 2017/ops2017syst_odt_20161019.pdf |  |  | pending |  | False |
| 2018 | Perkutane Thrombolyse |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2018/ops2018syst_claml_20171018.xml | 2018/ops2018syst_odt_20171018.pdf |  |  | pending |  | False |
| 2019 | Perkutane Thrombolyse |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2019/ops2019syst-claml.zip::ops2019syst-claml/Klassifikationsdateien/ops2019syst_claml_20181019.xml | 2019/ops2019syst-pdf-20181203.zip::ops2019syst-pdf-20181203/ops2019syst_referenz_20181203.pdf |  |  | pending |  | False |
| 2020 | Perkutane Thrombolyse |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2020/ops2020syst-claml.zip::ops2020syst-claml/Klassifikationsdateien/ops2020syst_claml_20191018.xml | 2020/ops2020syst-pdf.zip::ops2020syst-pdf/ops2020syst_referenz_20191018.pdf |  |  | pending |  | False |
| 2021 | Perkutane Thrombolyse |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2021/ops2021syst-claml.zip::ops2021syst-claml/Klassifikationsdateien/ops2021syst_claml_20201016.xml | 2021/ops2021syst-pdf.zip::ops2021syst-pdf/ops2021syst_referenz_20201016.pdf |  |  | pending |  | False |
| 2022 | Perkutane Thrombolyse |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2022/ops2022syst-claml.zip::Klassifikationsdateien/ops2022syst_claml_20211022.xml | 2022/ops2022syst-pdf.zip::Klassifikationsdatei/ops2022syst_referenz_20211022.pdf |  |  | pending |  | False |
| 2023 | Perkutane Thrombolyse |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2023/ops2023syst-claml.zip::Klassifikationsdateien/ops2023syst_claml_20221021.xml | 2023/ops2023syst-pdf.zip::Klassifikationsdatei/ops2023syst_referenz_20221021.pdf |  |  | pending |  | False |
| 2024 | Perkutane Thrombolyse |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2024/ops2024syst-claml.zip::Klassifikationsdateien/ops2024syst_claml_20231020.xml | 2024/ops2024syst-pdf-20231120.zip::Klassifikationsdatei/ops2024syst_referenz_20231120.pdf |  |  | pending |  | False |

Reviewer 1: ____________________  Decision: __________

Reviewer 2: ____________________  Decision: __________

Comment: ______________________________________________________________
### `8-839.83`
| reporting_year | official_full_label | official_notes | proposed_classification | classification_reason | source_file | pdf_reference | manual_reviewer_1 | manual_reviewer_2 | manual_review_status | manual_review_comment | officially_verified |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013 | Perkutane Thrombektomie |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2013/ops2013syst_claml_20121012.xml | 2013/ops2013syst_odt_20121012.pdf |  |  | pending |  | False |
| 2014 | Perkutane Thrombektomie |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2014/ops2014syst_claml_20131104.xml | 2014/ops2014syst_odt_20131104.pdf |  |  | pending |  | False |
| 2015 | Perkutane Thrombektomie |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2015/ops2015syst_claml_20141017.xml | 2015/ops2015syst_odt_20141017.pdf |  |  | pending |  | False |
| 2016 | Perkutane Thrombektomie |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2016/ops2016syst_claml_20151016.xml | 2016/ops2016syst_odt_20151016.pdf |  |  | pending |  | False |
| 2017 | Perkutane Thrombektomie |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2017/ops2017syst_claml_20161019.xml | 2017/ops2017syst_odt_20161019.pdf |  |  | pending |  | False |
| 2018 | Perkutane Thrombektomie |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2018/ops2018syst_claml_20171018.xml | 2018/ops2018syst_odt_20171018.pdf |  |  | pending |  | False |
| 2019 | Perkutane Thrombektomie |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2019/ops2019syst-claml.zip::ops2019syst-claml/Klassifikationsdateien/ops2019syst_claml_20181019.xml | 2019/ops2019syst-pdf-20181203.zip::ops2019syst-pdf-20181203/ops2019syst_referenz_20181203.pdf |  |  | pending |  | False |
| 2020 | Perkutane Thrombektomie |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2020/ops2020syst-claml.zip::ops2020syst-claml/Klassifikationsdateien/ops2020syst_claml_20191018.xml | 2020/ops2020syst-pdf.zip::ops2020syst-pdf/ops2020syst_referenz_20191018.pdf |  |  | pending |  | False |
| 2021 | Perkutane Thrombektomie |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2021/ops2021syst-claml.zip::ops2021syst-claml/Klassifikationsdateien/ops2021syst_claml_20201016.xml | 2021/ops2021syst-pdf.zip::ops2021syst-pdf/ops2021syst_referenz_20201016.pdf |  |  | pending |  | False |
| 2022 | Perkutane Thrombektomie |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2022/ops2022syst-claml.zip::Klassifikationsdateien/ops2022syst_claml_20211022.xml | 2022/ops2022syst-pdf.zip::Klassifikationsdatei/ops2022syst_referenz_20211022.pdf |  |  | pending |  | False |
| 2023 | Perkutane Thrombektomie |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2023/ops2023syst-claml.zip::Klassifikationsdateien/ops2023syst_claml_20221021.xml | 2023/ops2023syst-pdf.zip::Klassifikationsdatei/ops2023syst_referenz_20221021.pdf |  |  | pending |  | False |
| 2024 | Perkutane Thrombektomie |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2024/ops2024syst-claml.zip::Klassifikationsdateien/ops2024syst_claml_20231020.xml | 2024/ops2024syst-pdf-20231120.zip::Klassifikationsdatei/ops2024syst_referenz_20231120.pdf |  |  | pending |  | False |

Reviewer 1: ____________________  Decision: __________

Reviewer 2: ____________________  Decision: __________

Comment: ______________________________________________________________
### `8-839.84`
| reporting_year | official_full_label | official_notes | proposed_classification | classification_reason | source_file | pdf_reference | manual_reviewer_1 | manual_reviewer_2 | manual_review_status | manual_review_comment | officially_verified |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013 | Perkutane Verkleinerung eines bestehenden portosystemischen Shunts |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2013/ops2013syst_claml_20121012.xml | 2013/ops2013syst_odt_20121012.pdf |  |  | pending |  | False |
| 2014 | Perkutane Verkleinerung eines bestehenden portosystemischen Shunts |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2014/ops2014syst_claml_20131104.xml | 2014/ops2014syst_odt_20131104.pdf |  |  | pending |  | False |
| 2015 | Perkutane Verkleinerung eines bestehenden portosystemischen Shunts |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2015/ops2015syst_claml_20141017.xml | 2015/ops2015syst_odt_20141017.pdf |  |  | pending |  | False |
| 2016 | Perkutane Verkleinerung eines bestehenden portosystemischen Shunts |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2016/ops2016syst_claml_20151016.xml | 2016/ops2016syst_odt_20151016.pdf |  |  | pending |  | False |
| 2017 | Perkutane Verkleinerung eines bestehenden portosystemischen Shunts |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2017/ops2017syst_claml_20161019.xml | 2017/ops2017syst_odt_20161019.pdf |  |  | pending |  | False |
| 2018 | Perkutane Verkleinerung eines bestehenden portosystemischen Shunts |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2018/ops2018syst_claml_20171018.xml | 2018/ops2018syst_odt_20171018.pdf |  |  | pending |  | False |
| 2019 | Perkutane Verkleinerung eines bestehenden portosystemischen Shunts |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2019/ops2019syst-claml.zip::ops2019syst-claml/Klassifikationsdateien/ops2019syst_claml_20181019.xml | 2019/ops2019syst-pdf-20181203.zip::ops2019syst-pdf-20181203/ops2019syst_referenz_20181203.pdf |  |  | pending |  | False |
| 2020 | Perkutane Verkleinerung eines bestehenden portosystemischen Shunts |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2020/ops2020syst-claml.zip::ops2020syst-claml/Klassifikationsdateien/ops2020syst_claml_20191018.xml | 2020/ops2020syst-pdf.zip::ops2020syst-pdf/ops2020syst_referenz_20191018.pdf |  |  | pending |  | False |
| 2021 | Perkutane Verkleinerung eines bestehenden portosystemischen Shunts |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2021/ops2021syst-claml.zip::ops2021syst-claml/Klassifikationsdateien/ops2021syst_claml_20201016.xml | 2021/ops2021syst-pdf.zip::ops2021syst-pdf/ops2021syst_referenz_20201016.pdf |  |  | pending |  | False |
| 2022 | Perkutane Verkleinerung eines bestehenden portosystemischen Shunts |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2022/ops2022syst-claml.zip::Klassifikationsdateien/ops2022syst_claml_20211022.xml | 2022/ops2022syst-pdf.zip::Klassifikationsdatei/ops2022syst_referenz_20211022.pdf |  |  | pending |  | False |
| 2023 | Perkutane Verkleinerung eines bestehenden portosystemischen Shunts |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2023/ops2023syst-claml.zip::Klassifikationsdateien/ops2023syst_claml_20221021.xml | 2023/ops2023syst-pdf.zip::Klassifikationsdatei/ops2023syst_referenz_20221021.pdf |  |  | pending |  | False |
| 2024 | Perkutanes Einlegen eines Stents in einen bestehenden portosystemischen Shunt | [inclusion] Stent-in-TIPS-Stent | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2024/ops2024syst-claml.zip::Klassifikationsdateien/ops2024syst_claml_20231020.xml | 2024/ops2024syst-pdf-20231120.zip::Klassifikationsdatei/ops2024syst_referenz_20231120.pdf |  |  | pending |  | False |

Reviewer 1: ____________________  Decision: __________

Reviewer 2: ____________________  Decision: __________

Comment: ______________________________________________________________
### `8-839.85`
| reporting_year | official_full_label | official_notes | proposed_classification | classification_reason | source_file | pdf_reference | manual_reviewer_1 | manual_reviewer_2 | manual_review_status | manual_review_comment | officially_verified |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013 | Perkutaner Verschluss |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2013/ops2013syst_claml_20121012.xml | 2013/ops2013syst_odt_20121012.pdf |  |  | pending |  | False |
| 2014 | Perkutaner Verschluss |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2014/ops2014syst_claml_20131104.xml | 2014/ops2014syst_odt_20131104.pdf |  |  | pending |  | False |
| 2015 | Perkutaner Verschluss |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2015/ops2015syst_claml_20141017.xml | 2015/ops2015syst_odt_20141017.pdf |  |  | pending |  | False |
| 2016 | Perkutaner Verschluss |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2016/ops2016syst_claml_20151016.xml | 2016/ops2016syst_odt_20151016.pdf |  |  | pending |  | False |
| 2017 | Perkutaner Verschluss |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2017/ops2017syst_claml_20161019.xml | 2017/ops2017syst_odt_20161019.pdf |  |  | pending |  | False |
| 2018 | Perkutaner Verschluss |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2018/ops2018syst_claml_20171018.xml | 2018/ops2018syst_odt_20171018.pdf |  |  | pending |  | False |
| 2019 | Perkutaner Verschluss |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2019/ops2019syst-claml.zip::ops2019syst-claml/Klassifikationsdateien/ops2019syst_claml_20181019.xml | 2019/ops2019syst-pdf-20181203.zip::ops2019syst-pdf-20181203/ops2019syst_referenz_20181203.pdf |  |  | pending |  | False |
| 2020 | Perkutaner Verschluss |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2020/ops2020syst-claml.zip::ops2020syst-claml/Klassifikationsdateien/ops2020syst_claml_20191018.xml | 2020/ops2020syst-pdf.zip::ops2020syst-pdf/ops2020syst_referenz_20191018.pdf |  |  | pending |  | False |
| 2021 | Perkutaner Verschluss |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2021/ops2021syst-claml.zip::ops2021syst-claml/Klassifikationsdateien/ops2021syst_claml_20201016.xml | 2021/ops2021syst-pdf.zip::ops2021syst-pdf/ops2021syst_referenz_20201016.pdf |  |  | pending |  | False |
| 2022 | Perkutaner Verschluss |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2022/ops2022syst-claml.zip::Klassifikationsdateien/ops2022syst_claml_20211022.xml | 2022/ops2022syst-pdf.zip::Klassifikationsdatei/ops2022syst_referenz_20211022.pdf |  |  | pending |  | False |
| 2023 | Perkutaner Verschluss |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2023/ops2023syst-claml.zip::Klassifikationsdateien/ops2023syst_claml_20221021.xml | 2023/ops2023syst-pdf.zip::Klassifikationsdatei/ops2023syst_referenz_20221021.pdf |  |  | pending |  | False |
| 2024 | Perkutaner Verschluss |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2024/ops2024syst-claml.zip::Klassifikationsdateien/ops2024syst_claml_20231020.xml | 2024/ops2024syst-pdf-20231120.zip::Klassifikationsdatei/ops2024syst_referenz_20231120.pdf |  |  | pending |  | False |

Reviewer 1: ____________________  Decision: __________

Reviewer 2: ____________________  Decision: __________

Comment: ______________________________________________________________
### `8-839.86`
| reporting_year | official_full_label | official_notes | proposed_classification | classification_reason | source_file | pdf_reference | manual_reviewer_1 | manual_reviewer_2 | manual_review_status | manual_review_comment | officially_verified |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013 | Revision mit Stenteinlage |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2013/ops2013syst_claml_20121012.xml | 2013/ops2013syst_odt_20121012.pdf |  |  | pending |  | False |
| 2014 | Revision mit Stenteinlage |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2014/ops2014syst_claml_20131104.xml | 2014/ops2014syst_odt_20131104.pdf |  |  | pending |  | False |
| 2015 | Revision mit Stenteinlage |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2015/ops2015syst_claml_20141017.xml | 2015/ops2015syst_odt_20141017.pdf |  |  | pending |  | False |
| 2016 | Revision mit Stenteinlage |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2016/ops2016syst_claml_20151016.xml | 2016/ops2016syst_odt_20151016.pdf |  |  | pending |  | False |
| 2017 | Revision mit Stenteinlage |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2017/ops2017syst_claml_20161019.xml | 2017/ops2017syst_odt_20161019.pdf |  |  | pending |  | False |
| 2018 | Revision mit Stenteinlage |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2018/ops2018syst_claml_20171018.xml | 2018/ops2018syst_odt_20171018.pdf |  |  | pending |  | False |
| 2019 | Revision mit Stenteinlage |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2019/ops2019syst-claml.zip::ops2019syst-claml/Klassifikationsdateien/ops2019syst_claml_20181019.xml | 2019/ops2019syst-pdf-20181203.zip::ops2019syst-pdf-20181203/ops2019syst_referenz_20181203.pdf |  |  | pending |  | False |
| 2020 | Revision mit Stenteinlage |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2020/ops2020syst-claml.zip::ops2020syst-claml/Klassifikationsdateien/ops2020syst_claml_20191018.xml | 2020/ops2020syst-pdf.zip::ops2020syst-pdf/ops2020syst_referenz_20191018.pdf |  |  | pending |  | False |
| 2021 | Revision mit Stenteinlage |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2021/ops2021syst-claml.zip::ops2021syst-claml/Klassifikationsdateien/ops2021syst_claml_20201016.xml | 2021/ops2021syst-pdf.zip::ops2021syst-pdf/ops2021syst_referenz_20201016.pdf |  |  | pending |  | False |
| 2022 | Revision mit Stenteinlage |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2022/ops2022syst-claml.zip::Klassifikationsdateien/ops2022syst_claml_20211022.xml | 2022/ops2022syst-pdf.zip::Klassifikationsdatei/ops2022syst_referenz_20211022.pdf |  |  | pending |  | False |
| 2023 | Revision mit Stenteinlage |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2023/ops2023syst-claml.zip::Klassifikationsdateien/ops2023syst_claml_20221021.xml | 2023/ops2023syst-pdf.zip::Klassifikationsdatei/ops2023syst_referenz_20221021.pdf |  |  | pending |  | False |
| 2024 | Verlängerung eines bestehenden portosystemischen Shuntes durch Stenteinlage |  | secondary_intervention | The official wording explicitly describes treatment of an existing shunt or a revision-type intervention. | 2024/ops2024syst-claml.zip::Klassifikationsdateien/ops2024syst_claml_20231020.xml | 2024/ops2024syst-pdf-20231120.zip::Klassifikationsdatei/ops2024syst_referenz_20231120.pdf |  |  | pending |  | False |

Reviewer 1: ____________________  Decision: __________

Reviewer 2: ____________________  Decision: __________

Comment: ______________________________________________________________
### `8-839.87`
| reporting_year | official_full_label | official_notes | proposed_classification | classification_reason | source_file | pdf_reference | manual_reviewer_1 | manual_reviewer_2 | manual_review_status | manual_review_comment | officially_verified |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013 | Perkutanes Anlegen eines ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2013/ops2013syst_claml_20121012.xml | 2013/ops2013syst_odt_20121012.pdf |  |  | pending |  | False |
| 2014 | Perkutanes Anlegen eines ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2014/ops2014syst_claml_20131104.xml | 2014/ops2014syst_odt_20131104.pdf |  |  | pending |  | False |
| 2015 | Perkutanes Anlegen eines ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2015/ops2015syst_claml_20141017.xml | 2015/ops2015syst_odt_20141017.pdf |  |  | pending |  | False |
| 2016 | Perkutanes Anlegen eines ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2016/ops2016syst_claml_20151016.xml | 2016/ops2016syst_odt_20151016.pdf |  |  | pending |  | False |
| 2017 | Perkutanes Anlegen eines ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2017/ops2017syst_claml_20161019.xml | 2017/ops2017syst_odt_20161019.pdf |  |  | pending |  | False |
| 2018 | Perkutanes Anlegen eines ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2018/ops2018syst_claml_20171018.xml | 2018/ops2018syst_odt_20171018.pdf |  |  | pending |  | False |
| 2019 | Perkutanes Anlegen eines ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2019/ops2019syst-claml.zip::ops2019syst-claml/Klassifikationsdateien/ops2019syst_claml_20181019.xml | 2019/ops2019syst-pdf-20181203.zip::ops2019syst-pdf-20181203/ops2019syst_referenz_20181203.pdf |  |  | pending |  | False |
| 2020 | Perkutanes Anlegen eines ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2020/ops2020syst-claml.zip::ops2020syst-claml/Klassifikationsdateien/ops2020syst_claml_20191018.xml | 2020/ops2020syst-pdf.zip::ops2020syst-pdf/ops2020syst_referenz_20191018.pdf |  |  | pending |  | False |
| 2021 | Perkutanes Anlegen eines ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2021/ops2021syst-claml.zip::ops2021syst-claml/Klassifikationsdateien/ops2021syst_claml_20201016.xml | 2021/ops2021syst-pdf.zip::ops2021syst-pdf/ops2021syst_referenz_20201016.pdf |  |  | pending |  | False |
| 2022 | Perkutanes Anlegen eines ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2022/ops2022syst-claml.zip::Klassifikationsdateien/ops2022syst_claml_20211022.xml | 2022/ops2022syst-pdf.zip::Klassifikationsdatei/ops2022syst_referenz_20211022.pdf |  |  | pending |  | False |
| 2023 | Perkutanes Anlegen eines ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2023/ops2023syst-claml.zip::Klassifikationsdateien/ops2023syst_claml_20221021.xml | 2023/ops2023syst-pdf.zip::Klassifikationsdatei/ops2023syst_referenz_20221021.pdf |  |  | pending |  | False |
| 2024 | Perkutanes Anlegen eines ungecoverten Stents | [inclusion] Angioplastie zur Herstellung eines Shuntes zwischen portalvenösen und venösen Lebergefäßen innerhalb des Leberparenchyms | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2024/ops2024syst-claml.zip::Klassifikationsdateien/ops2024syst_claml_20231020.xml | 2024/ops2024syst-pdf-20231120.zip::Klassifikationsdatei/ops2024syst_referenz_20231120.pdf |  |  | pending |  | False |

Reviewer 1: ____________________  Decision: __________

Reviewer 2: ____________________  Decision: __________

Comment: ______________________________________________________________
### `8-839.88`
| reporting_year | official_full_label | official_notes | proposed_classification | classification_reason | source_file | pdf_reference | manual_reviewer_1 | manual_reviewer_2 | manual_review_status | manual_review_comment | officially_verified |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013 | Perkutanes Anlegen eines gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2013/ops2013syst_claml_20121012.xml | 2013/ops2013syst_odt_20121012.pdf |  |  | pending |  | False |
| 2014 | Perkutanes Anlegen eines gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2014/ops2014syst_claml_20131104.xml | 2014/ops2014syst_odt_20131104.pdf |  |  | pending |  | False |
| 2015 | Perkutanes Anlegen eines gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2015/ops2015syst_claml_20141017.xml | 2015/ops2015syst_odt_20141017.pdf |  |  | pending |  | False |
| 2016 | Perkutanes Anlegen eines gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2016/ops2016syst_claml_20151016.xml | 2016/ops2016syst_odt_20151016.pdf |  |  | pending |  | False |
| 2017 | Perkutanes Anlegen eines gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2017/ops2017syst_claml_20161019.xml | 2017/ops2017syst_odt_20161019.pdf |  |  | pending |  | False |
| 2018 | Perkutanes Anlegen eines gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2018/ops2018syst_claml_20171018.xml | 2018/ops2018syst_odt_20171018.pdf |  |  | pending |  | False |
| 2019 | Perkutanes Anlegen eines gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2019/ops2019syst-claml.zip::ops2019syst-claml/Klassifikationsdateien/ops2019syst_claml_20181019.xml | 2019/ops2019syst-pdf-20181203.zip::ops2019syst-pdf-20181203/ops2019syst_referenz_20181203.pdf |  |  | pending |  | False |
| 2020 | Perkutanes Anlegen eines gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2020/ops2020syst-claml.zip::ops2020syst-claml/Klassifikationsdateien/ops2020syst_claml_20191018.xml | 2020/ops2020syst-pdf.zip::ops2020syst-pdf/ops2020syst_referenz_20191018.pdf |  |  | pending |  | False |
| 2021 | Perkutanes Anlegen eines gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2021/ops2021syst-claml.zip::ops2021syst-claml/Klassifikationsdateien/ops2021syst_claml_20201016.xml | 2021/ops2021syst-pdf.zip::ops2021syst-pdf/ops2021syst_referenz_20201016.pdf |  |  | pending |  | False |
| 2022 | Perkutanes Anlegen eines gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2022/ops2022syst-claml.zip::Klassifikationsdateien/ops2022syst_claml_20211022.xml | 2022/ops2022syst-pdf.zip::Klassifikationsdatei/ops2022syst_referenz_20211022.pdf |  |  | pending |  | False |
| 2023 | Perkutanes Anlegen eines gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2023/ops2023syst-claml.zip::Klassifikationsdateien/ops2023syst_claml_20221021.xml | 2023/ops2023syst-pdf.zip::Klassifikationsdatei/ops2023syst_referenz_20221021.pdf |  |  | pending |  | False |
| 2024 | Perkutanes Anlegen eines gecoverten Stents | [inclusion] Angioplastie zur Herstellung eines Shuntes zwischen portalvenösen und venösen Lebergefäßen innerhalb des Leberparenchyms | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2024/ops2024syst-claml.zip::Klassifikationsdateien/ops2024syst_claml_20231020.xml | 2024/ops2024syst-pdf-20231120.zip::Klassifikationsdatei/ops2024syst_referenz_20231120.pdf |  |  | pending |  | False |

Reviewer 1: ____________________  Decision: __________

Reviewer 2: ____________________  Decision: __________

Comment: ______________________________________________________________
### `8-839.89`
| reporting_year | official_full_label | official_notes | proposed_classification | classification_reason | source_file | pdf_reference | manual_reviewer_1 | manual_reviewer_2 | manual_review_status | manual_review_comment | officially_verified |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2016 | Perkutanes Anlegen von 2 und mehr ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2016/ops2016syst_claml_20151016.xml | 2016/ops2016syst_odt_20151016.pdf |  |  | pending |  | False |
| 2017 | Perkutanes Anlegen von 2 oder mehr ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2017/ops2017syst_claml_20161019.xml | 2017/ops2017syst_odt_20161019.pdf |  |  | pending |  | False |
| 2018 | Perkutanes Anlegen von 2 oder mehr ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2018/ops2018syst_claml_20171018.xml | 2018/ops2018syst_odt_20171018.pdf |  |  | pending |  | False |
| 2019 | Perkutanes Anlegen von 2 oder mehr ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2019/ops2019syst-claml.zip::ops2019syst-claml/Klassifikationsdateien/ops2019syst_claml_20181019.xml | 2019/ops2019syst-pdf-20181203.zip::ops2019syst-pdf-20181203/ops2019syst_referenz_20181203.pdf |  |  | pending |  | False |
| 2020 | Perkutanes Anlegen von 2 oder mehr ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2020/ops2020syst-claml.zip::ops2020syst-claml/Klassifikationsdateien/ops2020syst_claml_20191018.xml | 2020/ops2020syst-pdf.zip::ops2020syst-pdf/ops2020syst_referenz_20191018.pdf |  |  | pending |  | False |
| 2021 | Perkutanes Anlegen von 2 oder mehr ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2021/ops2021syst-claml.zip::ops2021syst-claml/Klassifikationsdateien/ops2021syst_claml_20201016.xml | 2021/ops2021syst-pdf.zip::ops2021syst-pdf/ops2021syst_referenz_20201016.pdf |  |  | pending |  | False |
| 2022 | Perkutanes Anlegen von 2 oder mehr ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2022/ops2022syst-claml.zip::Klassifikationsdateien/ops2022syst_claml_20211022.xml | 2022/ops2022syst-pdf.zip::Klassifikationsdatei/ops2022syst_referenz_20211022.pdf |  |  | pending |  | False |
| 2023 | Perkutanes Anlegen von 2 oder mehr ungecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2023/ops2023syst-claml.zip::Klassifikationsdateien/ops2023syst_claml_20221021.xml | 2023/ops2023syst-pdf.zip::Klassifikationsdatei/ops2023syst_referenz_20221021.pdf |  |  | pending |  | False |
| 2024 | Perkutanes Anlegen von 2 oder mehr ungecoverten Stents | [inclusion] Angioplastie zur Herstellung eines Shuntes zwischen portalvenösen und venösen Lebergefäßen innerhalb des Leberparenchyms | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2024/ops2024syst-claml.zip::Klassifikationsdateien/ops2024syst_claml_20231020.xml | 2024/ops2024syst-pdf-20231120.zip::Klassifikationsdatei/ops2024syst_referenz_20231120.pdf |  |  | pending |  | False |

Reviewer 1: ____________________  Decision: __________

Reviewer 2: ____________________  Decision: __________

Comment: ______________________________________________________________
### `8-839.8a`
| reporting_year | official_full_label | official_notes | proposed_classification | classification_reason | source_file | pdf_reference | manual_reviewer_1 | manual_reviewer_2 | manual_review_status | manual_review_comment | officially_verified |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2016 | Perkutanes Anlegen von 2 und mehr gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2016/ops2016syst_claml_20151016.xml | 2016/ops2016syst_odt_20151016.pdf |  |  | pending |  | False |
| 2017 | Perkutanes Anlegen von 2 oder mehr gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2017/ops2017syst_claml_20161019.xml | 2017/ops2017syst_odt_20161019.pdf |  |  | pending |  | False |
| 2018 | Perkutanes Anlegen von 2 oder mehr gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2018/ops2018syst_claml_20171018.xml | 2018/ops2018syst_odt_20171018.pdf |  |  | pending |  | False |
| 2019 | Perkutanes Anlegen von 2 oder mehr gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2019/ops2019syst-claml.zip::ops2019syst-claml/Klassifikationsdateien/ops2019syst_claml_20181019.xml | 2019/ops2019syst-pdf-20181203.zip::ops2019syst-pdf-20181203/ops2019syst_referenz_20181203.pdf |  |  | pending |  | False |
| 2020 | Perkutanes Anlegen von 2 oder mehr gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2020/ops2020syst-claml.zip::ops2020syst-claml/Klassifikationsdateien/ops2020syst_claml_20191018.xml | 2020/ops2020syst-pdf.zip::ops2020syst-pdf/ops2020syst_referenz_20191018.pdf |  |  | pending |  | False |
| 2021 | Perkutanes Anlegen von 2 oder mehr gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2021/ops2021syst-claml.zip::ops2021syst-claml/Klassifikationsdateien/ops2021syst_claml_20201016.xml | 2021/ops2021syst-pdf.zip::ops2021syst-pdf/ops2021syst_referenz_20201016.pdf |  |  | pending |  | False |
| 2022 | Perkutanes Anlegen von 2 oder mehr gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2022/ops2022syst-claml.zip::Klassifikationsdateien/ops2022syst_claml_20211022.xml | 2022/ops2022syst-pdf.zip::Klassifikationsdatei/ops2022syst_referenz_20211022.pdf |  |  | pending |  | False |
| 2023 | Perkutanes Anlegen von 2 oder mehr gecoverten Stents |  | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2023/ops2023syst-claml.zip::Klassifikationsdateien/ops2023syst_claml_20221021.xml | 2023/ops2023syst-pdf.zip::Klassifikationsdatei/ops2023syst_referenz_20221021.pdf |  |  | pending |  | False |
| 2024 | Perkutanes Anlegen von 2 oder mehr gecoverten Stents | [inclusion] Angioplastie zur Herstellung eines Shuntes zwischen portalvenösen und venösen Lebergefäßen innerhalb des Leberparenchyms | primary_placement | The official wording explicitly describes creation or placement of a portosystemic shunt. | 2024/ops2024syst-claml.zip::Klassifikationsdateien/ops2024syst_claml_20231020.xml | 2024/ops2024syst-pdf-20231120.zip::Klassifikationsdatei/ops2024syst_referenz_20231120.pdf |  |  | pending |  | False |

Reviewer 1: ____________________  Decision: __________

Reviewer 2: ____________________  Decision: __________

Comment: ______________________________________________________________
### `8-839.8x`
| reporting_year | official_full_label | official_notes | proposed_classification | classification_reason | source_file | pdf_reference | manual_reviewer_1 | manual_reviewer_2 | manual_review_status | manual_review_comment | officially_verified |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013 | Sonstige |  | unresolved_other | The official wording is a residual or otherwise non-specific category. | 2013/ops2013syst_claml_20121012.xml | 2013/ops2013syst_odt_20121012.pdf |  |  | pending |  | False |
| 2014 | Sonstige |  | unresolved_other | The official wording is a residual or otherwise non-specific category. | 2014/ops2014syst_claml_20131104.xml | 2014/ops2014syst_odt_20131104.pdf |  |  | pending |  | False |
| 2015 | Sonstige |  | unresolved_other | The official wording is a residual or otherwise non-specific category. | 2015/ops2015syst_claml_20141017.xml | 2015/ops2015syst_odt_20141017.pdf |  |  | pending |  | False |
| 2016 | Sonstige |  | unresolved_other | The official wording is a residual or otherwise non-specific category. | 2016/ops2016syst_claml_20151016.xml | 2016/ops2016syst_odt_20151016.pdf |  |  | pending |  | False |
| 2017 | Sonstige |  | unresolved_other | The official wording is a residual or otherwise non-specific category. | 2017/ops2017syst_claml_20161019.xml | 2017/ops2017syst_odt_20161019.pdf |  |  | pending |  | False |
| 2018 | Sonstige |  | unresolved_other | The official wording is a residual or otherwise non-specific category. | 2018/ops2018syst_claml_20171018.xml | 2018/ops2018syst_odt_20171018.pdf |  |  | pending |  | False |
| 2019 | Sonstige |  | unresolved_other | The official wording is a residual or otherwise non-specific category. | 2019/ops2019syst-claml.zip::ops2019syst-claml/Klassifikationsdateien/ops2019syst_claml_20181019.xml | 2019/ops2019syst-pdf-20181203.zip::ops2019syst-pdf-20181203/ops2019syst_referenz_20181203.pdf |  |  | pending |  | False |
| 2020 | Sonstige |  | unresolved_other | The official wording is a residual or otherwise non-specific category. | 2020/ops2020syst-claml.zip::ops2020syst-claml/Klassifikationsdateien/ops2020syst_claml_20191018.xml | 2020/ops2020syst-pdf.zip::ops2020syst-pdf/ops2020syst_referenz_20191018.pdf |  |  | pending |  | False |
| 2021 | Sonstige |  | unresolved_other | The official wording is a residual or otherwise non-specific category. | 2021/ops2021syst-claml.zip::ops2021syst-claml/Klassifikationsdateien/ops2021syst_claml_20201016.xml | 2021/ops2021syst-pdf.zip::ops2021syst-pdf/ops2021syst_referenz_20201016.pdf |  |  | pending |  | False |
| 2022 | Sonstige |  | unresolved_other | The official wording is a residual or otherwise non-specific category. | 2022/ops2022syst-claml.zip::Klassifikationsdateien/ops2022syst_claml_20211022.xml | 2022/ops2022syst-pdf.zip::Klassifikationsdatei/ops2022syst_referenz_20211022.pdf |  |  | pending |  | False |
| 2023 | Sonstige |  | unresolved_other | The official wording is a residual or otherwise non-specific category. | 2023/ops2023syst-claml.zip::Klassifikationsdateien/ops2023syst_claml_20221021.xml | 2023/ops2023syst-pdf.zip::Klassifikationsdatei/ops2023syst_referenz_20221021.pdf |  |  | pending |  | False |
| 2024 | Sonstige |  | unresolved_other | The official wording is a residual or otherwise non-specific category. | 2024/ops2024syst-claml.zip::Klassifikationsdateien/ops2024syst_claml_20231020.xml | 2024/ops2024syst-pdf-20231120.zip::Klassifikationsdatei/ops2024syst_referenz_20231120.pdf |  |  | pending |  | False |

Reviewer 1: ____________________  Decision: __________

Reviewer 2: ____________________  Decision: __________

Comment: ______________________________________________________________

