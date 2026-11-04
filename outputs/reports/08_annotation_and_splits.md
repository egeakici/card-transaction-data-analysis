# Annotation And Splits

Research questions: S1, S3, S6.

Inputs: derived/canonical.parquet; derived/purchase_labels.parquet.

Method: Create a deterministic, stratified, unlabelled sample of privacy-eligible distinct strings; count grouped/time/source split feasibility only.

Limitations: Support >=20 and personal-pattern suppression exclude rare descriptors, particularly tiny sources. Stratified inclusion is unequal, so the sample does not estimate class prevalence without appropriate design weights. Merchant overlap is a proxy for leakage risk, not a verified corporate-entity overlap.

Prepared 800 unlabelled strings across 382 eligible strata. `annotation/evidence_sample.csv` and `annotation/guidelines.md` are **internal-only** and excluded from Git. Annotation columns remain empty. No model or data split is trained/created.

Grouped-split statistics in `grouped_split_feasibility.csv` report factual counts plus explicit heuristic thresholds (>=100 merchant keys; >=20 merchants with >=20 records). Temporal candidates in `temporal_split_feasibility.csv` report all observed year cuts and a >=1,000-row-per-side indicator. `cross_source_split_overlap.csv` quantifies how many test merchants are already seen, including Delaware-to-Oklahoma and Delaware-to-UK-pool comparisons. These are planning diagnostics, not recommended or executed experimental splits.

