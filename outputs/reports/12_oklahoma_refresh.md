# Oklahoma Refresh

Research questions: S1-S7.

Inputs: Current source configuration and supplied fiscal-year files; data_profile/config/oklahoma_previous_profile.csv pinned prior aggregate snapshot (commit 8dc7aab).

Method: Reprofile all nineteen prepared fiscal-year inputs; compare with pinned prior aggregates; count every fiscal/calendar month, label and date-source flag.

Limitations: The supplied inputs have already been deduplicated upstream. Original 170-download processing and completeness are not independently verified. Fiscal-year labels, calendar dates, source snapshots and proxy-cluster IDs must remain distinct.

## Replacement of the earlier Oklahoma slice

The refreshed supplied inputs contain **6,883,868 records in 19 fiscal-year files**, replacing the earlier 900,000-record OpenGov slice. Observed transaction/period-derived dates range from **2009-04-14 to 2026-09-30**. Fiscal labels FY2009-FY2027 are not calendar coverage through 2027: FY2027 currently contains July-September 2026. FY2009 and FY2027 have only three observed months each; every intervening fiscal year has twelve observed months. The month grid records endpoint gaps separately from interior gaps; none of this proves complete population capture.

May-June accounts for **17.31%** of refreshed records, compared with **89.00%** in the old slice. Replacing an extract changes the observed population and merchant support; differences must not be interpreted as a temporal or causal effect. `oklahoma_refresh_comparison.csv` compares rows, merchant vocabulary, accepted MCC linkage and seasonal concentration. The informative-item flag is an operational string rule, not a manual validation of product evidence; coded descriptions and unlisted placeholder variants can remain. Proxy clusters were fitted afresh. To bound memory, SVD is now fitted on the same top-50,000 frequent-description reference subset used for vocabulary/IDF, and every unique informative item is transformed and clustered in disk-backed batches. The previous SVD fit used all unique descriptions; cluster IDs and purity changes therefore reflect both changed input and changed representation fit scope. Transaction informativeness now requires at least one informative item after splitting multi-item strings; redaction markers are excluded as placeholders.

## Prepared inputs and date provenance

The supplied upstream note describes 170 original downloads, removal of 222,881 blank rows, 34 overlap-month decisions, cross-file duplicate filtering, omission of cardholder identity fields, and 631 dates imputed from reporting periods. Those operations occurred **before** this profiling run. The original download collection and overlap decision manifests are not present here; their correctness and the note's explanation of OpenGov duplicate totals are not independently verified by this pipeline. The reported date-plus-amount-plus-merchant duplicate key can also match legitimate distinct purchases, and dropping an entire month at a 90% overlap threshold can discard nonmatching purchases. Consequently 6,883,868 means retained prepared records, not a certified count of unique real-world transactions. Current inputs retain 146 distinct upstream resource IDs, not necessarily all original resources.

The upstream note says fiscal years were recomputed from the effective date using a July-June calendar. A zero fiscal-calendar mismatch therefore checks internal consistency of prepared fields; it is not independent validation against original publisher fiscal-year assignments.

All 6,883,868 prepared input records are retained. The 631 `date_source=period` records retain `date_semantics=period`, not an asserted transaction date. No second deduplication or silent date correction is performed. Early fiscal years have reduced MCC-description coverage; use `oklahoma_fiscal_year_coverage.csv` before comparing labels over time. Missing labels are not filled with invented categories.

## Private concatenation and publication

`real-world-datas/Oklahoma Data - USA/birlesik_tam.csv` stacks FY2009 through FY2027 in that order, preserving within-file order and all twelve supplied fields. One header is emitted. Row count and exact decimal amount total reconcile with all source files. SHA-256 verification and the private merge manifest are under `derived/`; the merged CSV is excluded both from profiling input selection and Git.

Only code, reports, aggregate tables, figures, configurations, and audit metadata are prepared for publication. Dataset directories expose only README documentation. New prepared inputs contain no cardholder identity columns, so the prior source-name dictionary cannot be reconstructed. The current privacy check reports this limitation explicitly; address-pattern screening remains active and internal annotation samples remain unpublished. Public cluster examples additionally require at least twenty occurrences of their normalized description and a merchant with at least twenty records; fewer than five examples are retained where support is insufficient. This reduces rare-example disclosure but is not an anonymity certificate.

## Evidence

- `oklahoma_fiscal_year_coverage.csv`: fiscal coverage, dates, exact amount totals, MCC/item-label availability and fiscal-calendar checks.
- `oklahoma_calendar_month_coverage.csv`: complete fiscal month grid and gap classification.
- `oklahoma_date_sources.csv`: original transaction versus period-derived dates.
- `oklahoma_proxy_coverage.csv`: equal row counts for the four freshly generated proxy schemes, reconciled to informative-item transactions.
- `oklahoma_input_field_coverage.csv`: missingness for every supplied field.
- `oklahoma_resource_coverage.csv`: aggregate upstream resource coverage.
- `oklahoma_refresh_comparison.csv`: comparison against the pinned prior aggregate metrics (baseline commit 8dc7aab).
- `source_pool_weights.csv`: source contributions to the refreshed canonical pool; pooled metrics are strongly source-size weighted.
- `oklahoma_refresh_checks.json`: machine-readable refresh checks and upstream processing limitations.

