# Quality And Limitations

Research questions: S1-S7.

Inputs: derived/canonical.parquet; derived/purchase_labels.parquet.

Method: Unit tests, exact reconciliation, unchanged-input hashes, label-event uniqueness, provenance completeness and automatic disclosure screening.

Limitations: Privacy tests cover specified patterns and known identifiers, not every possible personal name or re-identification risk. Manual review is still needed for ambiguous codes, schema semantics and qualitative annotation examples.

11 sources reconcile, 32 data-file hashes match their starting values, and 9,846,430 canonical records have complete source provenance. See `quality_checks.json` and `privacy_checks.json`. Descriptive bootstrap intervals, fuzzy reference linkage and proxy clusters do not replace independent validation.
