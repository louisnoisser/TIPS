# Site-resolution validation decision

1. **Legacy reproduction:** yes, all 15 available years exactly.
2. **Removed legacy visible counts:** 2325; annual values are in `site_resolution_summary_by_year.csv`.
3. **Exact year–IK–code overlaps:** 783.
4. **Exact aggregate/component equality:** 211/213 groups with an assessable numeric aggregate;
570 hidden aggregate values are not assessable.
5. **Nonzero differences compatible with known suppression (1–3 each):** 0.
6. **Assessable unexplained nonzero residuals:** 2.
7. **Reporting granularity:** 99-only share was 0.0% in 2008
and 0.0% in 2024; dual 99/component reporting
peaked at 52 institutions and ended at
0, while identifiable component reporting increased.
8. **Provider growth:** physical-site and IK results are reported in `site_vs_institution_metrics.csv`.
9–11. **Concentration/decentralisation:** directions under both definitions are documented in
`site_vs_institution_summary.md`; the size-weighted conclusion must be read with the Gini result.
12–13. **Geography:** the 2024-only cache does not validate the longitudinal physical-site geography;
218 of 670 physical
identifiers have an explicit site-address node, while
43 have coordinates demonstrably generated from
such an address; accessibility analysis is not ready.
14–15. **Identity/turnover:** confirmed changed-ID links=45, probable=125.
Of the confirmed changes, 0 involve a 99 transition. At ≥20,
raw physical-site entry/exit events are 159/116, versus
155/112 after confirmed continuity and
118/75 after additionally including probable links.
4 probable links involve a 99 transition. Mergers, ownership
changes, renaming, and unresolved churn cannot be reliably separated; Table S6 is not validated.
16. **2024 rankings:** legacy and corrected physical-site top 20 are identical because no 2024
99/component overlap exists. IK aggregation combines two Schleswig-Holstein university sites
(institution rank 5); Cologne enters the institutional top 20. Full ranks are in the comparison CSV.
17–21. **OPS catalogues:** none are physically present/readable. All requested meanings, including
`8-839.80`, remain unresolved; a continuous creation-only series cannot be recommended.
22. **Known numerical revisions:** totals and provider metrics for overlap years require aggregate-99
deduplication; turnover and accessibility claims require further identity/geography validation.
23. **Robust conclusions:** see the two-definition direction table; no patient/creation interpretation is valid.
24. **Recommended final definition:** inclusive visible TIPS-related OPS activity with exact-code
physical-site precedence may be the primary structural definition, with IK-level and suppression
sensitivities. A creation-only sensitivity is deferred pending official catalogue verification.

**Decision:** proceed with component-precedence structural rebuilding only. Do not yet rebuild
accessibility, turnover claims, creation-only series, manuscript, or final figures.
