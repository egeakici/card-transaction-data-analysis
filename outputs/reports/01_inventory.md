# Inventory

Research questions: S1.

Inputs: Original files in data_profile/config/sources/*.yaml; outputs/manifest.csv.

Method: Read original files with row provenance, immediately project out Oklahoma personal columns, hash inputs and reconcile all rows.

Limitations: Workbook stored extents include blank rows; merged upstream sources cannot recover unavailable original download files.

The study has 31 original data files, 11 sources and 3,862,562 canonical records. All reconciliation differences are zero.

| Source | Reader records | Canonical | Excluded | Difference from approximate prompt count |
| --- | ---: | ---: | ---: | ---: |
| bristol | 12,205 | 12,205 | 0 | +8,205 |
| delaware | 2,251,316 | 2,251,316 | 0 | +16 |
| dwp | 8,026 | 8,026 | 0 | +26 |
| eden | 1,244 | 1,244 | 0 | +44 |
| indiana | 284,124 | 284,124 | 0 | +24 |
| ipo | 24 | 24 | 0 | +0 |
| moneydata | 14,863 | 6,567 | 8,296 | +67 |
| oklahoma | 900,000 | 900,000 | 0 | +0 |
| solihull | 112,406 | 109,877 | 2,529 | -2,123 |
| stockport | 34,010 | 34,010 | 0 | +10 |
| sunderland | 255,169 | 255,169 | 0 | +69 |

`manifest.csv` provides original input hashes, columns, dates and file sizes; `tables/schema_variants.csv` and `tables/exclusions.csv` provide variant counts and reasoned omissions. The Indonesia source and previous derived CSV conversions/concatenations are excluded to prevent double counting. All Bristol workbooks and transaction sheets are included. MoneyData blank worksheet extents and its documentation sheet are counted explicitly as exclusions. Solihull organization-only notes are excluded, while true missing-data records remain flagged unknown.

Initial full-source QA found 2 Delaware rows whose merchant value literally equals a field-name string but whose dates and amounts are valid. Those records were retained. Embedded-header detection now requires a header-like date as well as a header-like merchant. Their original row positions and all original fields remain traceable; `tests/test_parsers.py` prevents this over-filtering. No source file was altered.

