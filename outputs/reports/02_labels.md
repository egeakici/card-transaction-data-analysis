# Labels

Research questions: S2.

Inputs: derived/canonical.parquet; derived/purchase_labels.parquet.

Method: Separate original numeric codes, raw descriptions, accepted reference linkage, and review candidates. Prefix matching requires a unique code and a sufficiently long prefix; fuzzy acceptance requires score >=95 and a runner-up margin >=5.

Limitations: References differ in date and network. Historical-only or unlisted does not prove an erroneous original code. Description linkage is inferential and may overstate code identity; downstream sensitivity tables retain raw-label results.

The reference contains 985 codes. There are 2,144 source/normalized-description combinations, of which 469 require review. Explicit numeric codes are never replaced with a description-derived code.

| Source | Rows | Original numeric MCC | MCC description | Accepted code linkage | Known official group |
| --- | ---: | ---: | ---: | ---: | ---: |
| bristol | 12,205 | 12,199 | 12,205 | 12,199 | 12,197 |
| delaware | 2,251,316 | 0 | 2,251,316 | 1,579,233 | 1,578,932 |
| dwp | 8,026 | 2,373 | 0 | 2,373 | 2,363 |
| eden | 1,244 | 719 | 719 | 719 | 715 |
| indiana | 284,124 | 0 | 284,124 | 190,869 | 190,869 |
| ipo | 24 | 0 | 0 | 0 | 0 |
| moneydata | 6,567 | 0 | 0 | 0 | 0 |
| oklahoma | 900,000 | 0 | 881,434 | 643,292 | 641,148 |
| solihull | 109,877 | 0 | 0 | 0 | 0 |
| stockport | 34,010 | 0 | 18,267 | 16,267 | 16,264 |
| sunderland | 255,169 | 0 | 255,078 | 213,625 | 213,622 |

Indiana's misleadingly named column is retained as description text; its values are not treated as numeric codes. Stockport's purpose-present rows use the internal-category scheme; purpose-absent rows are MCC candidates. That content-based period distinction is auditable in `schema_variants.csv` and its dates are tested in the descriptive tables. Masking detection uses exact normalized reference descriptions, not a guess based only on uppercase text.

Review files: `mcc_needs_review.csv`, `mcc_numeric_needs_review.csv`. The analysis groups follow Mastercard's published MCC Category facts; any absent category remains `unknown`. Brand-specific airline, car-rental, and lodging codes also have a generic-code sensitivity field. Purchase labels are never converted into a new custom taxonomy.

