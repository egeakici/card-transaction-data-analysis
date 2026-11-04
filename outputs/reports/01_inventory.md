# Inventory

Research questions: S1.

Inputs: outputs/manifest.csv; original paths listed in data_profile/config/sources/*.yaml.

Method: Read supplied files, omit named identity columns if present, hash inputs, and reconcile every reader row.

Limitations: Original download completeness and upstream processing cannot be established from the locally supplied merged files. Workbook formatting extents inflate reader-row counts.

The inventory contains 32 supplied input data files from 11 sources. Oklahoma inputs are already prepared fiscal-year extracts, not the original 170 downloads described in the upstream note. There are 9,857,255 reader records and 9,846,430 canonical records. The Indonesia source and all previously created CSV conversions/concatenations are outside this study, preventing double counting.

| Source | Reader rows | Canonical rows | Excluded rows | Earliest parsed date | Latest parsed date |
| --- | ---: | ---: | ---: | --- | --- |
| bristol | 12,205 | 12,205 | 0 | 2025-04-08 | 2026-06-19 |
| delaware | 2,251,316 | 2,251,316 | 0 | 2014-05-07 | 2026-09-28 |
| dwp | 8,026 | 8,026 | 0 | 2009-04-01 | 2026-09-17 |
| eden | 1,244 | 1,244 | 0 | 2015-04-01 | 2017-12-22 |
| indiana | 284,124 | 284,124 | 0 | 2021-07-01 | 2026-10-01 |
| ipo | 24 | 24 | 0 | 2025-04-17 | 2026-09-29 |
| moneydata | 14,863 | 6,567 | 8,296 | 2015-01-09 | 2022-12-07 |
| oklahoma | 6,883,868 | 6,883,868 | 0 | 2009-04-14 | 2026-09-30 |
| solihull | 112,406 | 109,877 | 2,529 | 1900-01-01 | 2026-09-10 |
| stockport | 34,010 | 34,010 | 0 | 2017-01-05 | 2026-10-01 |
| sunderland | 255,169 | 255,169 | 0 | 2014-10-01 | 2026-09-30 |

See `tables/reconciliation.csv`, `tables/schema_variants.csv`, and `tables/exclusions.csv`. The original row address is `(source_id, source_file, source_sheet, source_row)`; CSV row numbers count parsed CSV records including the header, not physical newlines embedded inside quoted cells. DWP/IPO/Eden upstream provenance remains separate. Unknown date semantics are preserved as unknown.

Workbook reader counts include blank rows in the stored worksheet extent and the MoneyData documentation sheet. Those rows are explicitly excluded; they are not interpreted as transactions. Bristol uses every data sheet from every original workbook, explaining its difference from the approximate sample-based estimate. Solihull excludes blank rows and organization-only note rows rather than treating them as card activity.

