# Coverage

Research questions: S7.

Inputs: derived/canonical.parquet; derived/purchase_labels.parquet.

Method: Institutional card_txn records, linked official groups, unique loose merchant keys, explicit weak-coverage thresholds and sensitive-code checks.

Limitations: Coverage is conditional on accepted MCC linkage and uncertain merchant resolution. Academic MoneyData and IPO are excluded from institutional-card coverage. Observed absence cannot establish an institutional prohibition. Consumer/B2B orientation is an analyst-defined descriptive grouping, not a network taxonomy or observed purchaser identity.

The official reference supplies 19 upper groups. Under the requested rule (<100 transactions OR <20 merchant keys), 0 groups are weakly represented and 0 have no observed linked institutional-card transactions (`coverage_by_group.csv`).

Codes 6010, 6011 and 7995 are checked explicitly in `policy_sensitive_code_totals.csv`, including zero totals. Classification into B2B-oriented uses only Wholesale Distributors and Manufacturers; consumer-adjacent uses the published groups Airlines, Automobile/Vehicle Rentals, Hotels and Motels, Clothing Stores, Retail Stores, Miscellaneous Stores, Personal Service Providers, Transportation. All other categories remain mixed_or_unknown. This coarse orientation rule is separate from MCC reference linkage and does not create a task-specific spending taxonomy.

