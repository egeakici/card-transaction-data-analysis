# Sample Claim Checks

Research questions: S1-S7.

Inputs: derived/canonical.parquet; derived/purchase_labels.parquet.

Method: Explicit full-data checks of sample-derived claims; deterministic source-field and date/length counts.

Limitations: Supported here means consistent with the supplied extracts, not verified population metadata or a causal mechanism.

- **indiana / supported:** Merchant Category Code contains descriptions rather than numeric codes. Count exact four-digit strings in the misleadingly named raw-description field; canonical numeric code is empty unless an actual numeric source field exists. Evidence: `label_coverage.csv`.
- **moneydata / not_supported:** All bank descriptors are at most 18 characters. Maximum observed descriptor length is 21; heaping does not independently establish the bank formatting rule. Evidence: `merchant_lengths.csv`.
- **oklahoma / partly_supported:** MCC descriptions are truncated at 40 characters. Maximum observed raw MCC-description length is 61; count at exactly forty is an indicator, not proof every value is truncated. Evidence: `mcc_desc_vocab.csv`.
- **solihull / supported:** No numeric MCC source column is available. ProClass and institutional purpose are distinct purchase-label systems, not MCC. Evidence: `label_coverage.csv`.
- **solihull / supported:** Address-like purpose values need masking. Pattern matches are masked before label persistence; original addresses are never shown. Evidence: `transformation_impacts.csv`.
- **bristol / not_supported:** Source contains approximately four thousand rows. Full workbooks include all twelve transaction sheets, not just the initially sampled subset. Evidence: `reconciliation.csv`.
- **indiana / not_supported:** Issuer changes cleanly from JPMorgan FY2022-2024 to US Bank FY2025+. Check actual issuer/fiscal-year cells and overlapping date bounds; no causal issuer effect or single change date is assumed. Evidence: `indiana_issuer_dates.csv`.
- **stockport / partly_supported:** Supplied older records start around 2017. Earliest parsed supplied record is 2017-01-05; calendar-period scheme assignments are validated by row content, not assumed from a sample. Evidence: `stockport_observed_periods.csv`.
