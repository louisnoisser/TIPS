# Federal-state assignment audit

No local postcode-to-state crosswalk or explicit state field was found. Coordinate-derived states were audited but are not treated as independent postcode/address validation. Consequently no threshold network currently passes the federal-state release gate.

| network | observed_sites | validated_state_assignments | unresolved_state_assignments | state_validated_without_coordinates | ambiguous_postcodes | federal_state_release_permitted |
| --- | --- | --- | --- | --- | --- | --- |
| ge100 | 16 | 0 | 16 | 0 | 0 | False |
| ge50 | 31 | 0 | 31 | 0 | 0 | False |
| ge20 | 60 | 0 | 60 | 0 | 0 | False |
| visible | 113 | 0 | 113 | 0 | 0 | False |
| all_active | 193 | 0 | 193 | 0 | 0 | False |
