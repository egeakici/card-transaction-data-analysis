# Label Consistency

Research questions: S4, S6.

Inputs: derived/canonical.parquet; derived/purchase_labels.parquet.

Method: For each source/merchant, compute unique labels and majority share; compare only unequivocal source majorities across sources. Report code, generic-code and official-group levels separately, with raw-description and original-numeric sensitivities.

Limitations: Entity-resolution errors, differing reference vintages, truncated labels, ambiguous fuzzy links and legitimate multi-MCC merchants can all induce disagreement. This is descriptive input to a label-ceiling argument, not an experimentally established performance ceiling.

All within-source merchant counts and source-pair majority agreements are saved in `merchant_consistency_*.csv`, `consistency_summary_*.csv`, and `cross_source_agreement_*.csv`. Top inconsistency candidates require at least 20 transactions. Neighbor-code and brand/generic explanations are candidates only. Indiana before/after issuer comparisons are in `indiana_merchant_issuer_shift.csv`; their temporal association does not establish misclassification or causation. Tied majorities are flagged and excluded from the unequivocal agreement denominator.

