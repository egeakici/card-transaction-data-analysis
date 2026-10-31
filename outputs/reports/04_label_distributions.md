# Label Distributions

Research questions: S2, S6.

Inputs: derived/canonical.parquet; derived/purchase_labels.parquet.

Method: Counts, observed-category entropy/Gini, base-2 Jensen-Shannon divergence, yearly category/vocabulary profiles, and issuer-era comparisons.

Limitations: Only card_txn records enter primary MCC distributions. Linkage coverage and unmapped records must accompany results; JSD excludes unknown groups and is conditional on matched records. Issuer eras are confounded with time, agencies, and card type.

There are 8 sources with known MCC-group observations. Distribution summaries are in `label_distribution_summary.csv`; source-pair divergence is in `mcc_group_js_divergence.csv`. Gini is computed across observed category counts, not spending amounts or a zero-filled universe. Original numeric-code sensitivities remain separate.

Indiana issuer date bounds and overlap are computed from transaction-date fields, not inferred only from fiscal years: `indiana_issuer_dates.csv`. Description vocabulary shifts and known-group divergence are in `indiana_issuer_distribution.csv` and `indiana_issuer_js_divergence.csv`. Any overlap of date intervals means there is no single clean issuer transition date.

