# Merchant Strings

Research questions: S1, S3.

Inputs: derived/canonical.parquet; derived/purchase_labels.parquet.

Method: Two deterministic merchant keys, explicit intermediary separation, frequency concentration, length/token histograms, and set-based source overlap.

Limitations: Normalized keys approximate merchants, not verified legal entities. Alias merging and location removal can merge distinct merchants; strict-key sensitivity counts are retained. Length spikes indicate possible truncation, not a verified bank-format limit. Rare merchant strings are suppressed from public examples.

| Source | Merchant-bearing rows | Raw strings | Strict keys | Loose keys | Intermediary share |
| --- | ---: | ---: | ---: | ---: | ---: |
| bristol | 12,205 | 2,984 | 1,537 | 1,528 | 4.78% |
| delaware | 2,251,316 | 436,557 | 106,249 | 106,177 | 10.32% |
| dwp | 8,013 | 1,889 | 1,186 | 1,178 | 0.21% |
| eden | 1,239 | 442 | 408 | 400 | 1.78% |
| indiana | 284,124 | 46,391 | 15,638 | 15,603 | 11.80% |
| ipo | 24 | 14 | 7 | 7 | 0.00% |
| moneydata | 6,567 | 908 | 703 | 687 | 0.41% |
| oklahoma | 900,000 | 202,293 | 64,126 | 63,925 | 0.58% |
| solihull | 109,876 | 12,702 | 9,055 | 8,918 | 1.47% |
| stockport | 32,422 | 7,350 | 3,596 | 3,471 | 0.63% |
| sunderland | 255,078 | 6,996 | 3,885 | 3,775 | 0.21% |

All records are retained in the inventory. These string metrics exclude empty merchants and exact reference-description-masked Stockport strings. Card-only sensitivity metrics are provided separately by record type in the descriptive analysis. Top keys and cross-country overlaps use stable opaque merchant IDs; displayed examples require support >=20 and an identifier/address guard. Counts of empty normalized keys and all aliases are documented in decisions. See `merchant_concentration.csv`, `merchant_singletons.csv`, `merchant_lengths.csv`, `truncation_indicators.csv`, and `merchant_overlap.csv`.

