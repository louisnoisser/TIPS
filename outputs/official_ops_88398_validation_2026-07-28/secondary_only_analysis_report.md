# Secondary-only TIPS coding analysis, 2013–2024

- Generation timestamp: `2026-07-28T11:48:33+00:00`
- Git commit: `e162c991af5d699d169240b903a1c35cbb4df5f9`
- Analysis version: `official-ops-88398-v1-approved-secondary-v1`
- Mapping status: **approved**

## Interpretation boundary

This analysis uses year-specific official BfArM wording and applies only from
2013 onwards. It distinguishes visible numeric activity from the presence of
suppressed code entries. A suppressed primary-placement code is sufficient
evidence of primary placement. No suppressed count is imputed.

The retained 2013 code `8-839.80` is classified as
`invalid_hospital_reported_legacy_code`. It was valid in OPS 2012 as primary
placement but invalid in OPS 2013. It is neither remapped nor discarded and
cannot independently establish primary placement. Every affected site-year also
contains valid 2013 primary code `.87` or `.88`, so its site-year category is
unaffected.

## Longitudinal physical-site results

- Ever-primary sites: 501
- Never-primary visible-secondary-only sites: 2
- Never-primary unresolved sites: 108
- Suppressed-only unclassifiable sites: 15

Among 611 reporting-site identifiers active from 2013 through 2024,
314 had any openly
numeric activity and 297 were
identified exclusively through suppressed entries. Classification remained
longitudinally unresolved for
108 sites.

The longitudinal site table treats each reported physical-site identifier as a
unit. It is not a merger-adjusted facility crosswalk; identifier changes,
restructurings, and unresolved continuity can therefore separate the same
real-world facility across years.

## Site-year results

- Active site-years: 2057
- Primary or mixed: 1827
- Definitely secondary-only: 196
- Unresolved: 2
- Suppressed-only unclassifiable: 32
- Maximum annual visible activity among definitely secondary-only site-years: 8
- Definitely secondary-only threshold counts: >=20: 0, >=50: 0, >=100: 0, >=200: 0

## Institution-level sensitivity

- Ever-primary institutions: 262
- Never-primary visible-secondary-only institutions: 1
- Never-primary unresolved institutions: 84
- Suppressed-only unclassifiable institutions: 11
- Active institution-years: 1917

Institution aggregation is a sensitivity analysis and does not override the
physical-site results.

## Provider expansion and concentration

From 2013 to 2024, openly numeric reporting sites increased by
51 using all classified site-years and by 52
after excluding definitely secondary-only site-years. The largest annual
provider-count difference was 2, the largest visible
activity difference was 11, and the largest absolute HHI
difference was 2.8540.

**The observed provider expansion and concentration findings are not plausibly explained by definitely secondary-only providers.**

This is a descriptive coding-pattern result. It does not establish that
secondary-only providers do or do not exist outside the classifiable reporting
data, and it does not support a negative claim about secondary interventions in
Germany.
