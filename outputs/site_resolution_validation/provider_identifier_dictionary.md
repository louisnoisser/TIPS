# Provider identifier dictionary

- `ik`: institutional identifier parsed from the first filename segment. One IK may emit
multiple component-site reports.
- `site_identifier`: `IK-Standortnummer`, parsed from the production-eligible XML filename.
- `-99`: Standortnummer 99 aggregate report. It is excluded only when a non-99 report exists for the
same year, IK, and exact OPS code; otherwise it is retained as an unresolved institution provider.
- Component site: any production-eligible non-99 site identifier. `00` is treated as an identifiable
single/component report, not as an aggregate.
- Suppression: `suppressed_flag` and `suppressed_record_count` from the immutable audit; bounds assign
1/2/3 per suppressed source entry.
- Address: explicit `Standortkontaktdaten` and `Krankenhauskontaktdaten` nodes are extracted separately.
An institution address used by a component report is labelled inherited; older generic `Kontaktdaten`
without a distinguishable hierarchy remain unresolved.
- Coordinates: existing local geocode cache keyed by `facility_id`; it covers the current 2024 cohort,
not longitudinal identity.
- Current longitudinal key: production uses `facility_id` at site level and raw `ik` for IK churn.
Identifier stability is not assumed. Confirmed changed-ID continuity requires exact normalized name
and address; fuzzy links remain probable and require review.
- Count interpretation: visible inpatient TIPS-related OPS-coded procedure occurrences/TIPS-related
procedural activity, not patients, admissions, or unique creations.
