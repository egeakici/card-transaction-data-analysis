# Decisions and affected counts

All impact counts are computed; events can overlap across schemes. Defaults that cannot be validated remain explicit assumptions or unknowns.

### Input selection

Affected reader rows/records/events: 9,857,255. Only original files in eleven declared source folders; exclude Indonesia, prior worksheet CSV conversions, folder merges and global merge to avoid repeated counting.

### Non-destructive derivation

Affected reader rows/records/events: 9,846,430. Original strings/dates/amounts remain in original files. Parsed values and keys are separate fields in private canonical/analysis Parquet; no cleaned raw-data release.

### Oklahoma personal columns

Affected reader rows/records/events: 0. Count only reader rows whose supplied headers actually contain Last Name, First Initial or Cardholder Name. The current prepared inputs already omit them, so no additional identity-field removal is claimed. Projection remains a safeguard if those columns are present; no identifier list is persisted and the current source-name dictionary is unavailable.

### Solihull address masking

Affected reader rows/records/events: 902. Mask street/number pattern as ADDRESS_REDACTED before storing labels; never print original purpose examples; masked label events excluded from purity.

### Unknown date meaning

Affected reader rows/records/events: 2,370,286. Do not infer statement dates from heaping; retain unknown when field semantics are unverified.

### Date convention

Affected reader rows/records/events: 9,846,430. USA ambiguous slash dates use month-first, UK use day-first; ISO and typed worksheet dates take precedence; UK-invalid-first alternatives may parse under the other convention. ISO-typed Excel dates are not reinterpreted.

### MoneyData amount sign

Affected reader rows/records/events: 6,567. Debits become negative, credits positive; original Debit Amount and Credit Amount remain in the original workbook. These negative amounts denote bank outflows, not refunds, and are not comparable to a public-source negative/refund rate.

### Excel serial date conversion

Affected reader rows/records/events: 689. Recognize numeric serials 20000-60000; Excel origin 1899-12-30. Other outlier dates remain visible, not corrected.

### Dotted UK date parsing

Affected reader rows/records/events: 17,137. Recognize dd.mm.yyyy and dotted settlement dates in Stockport. Original cell text and raw-row fingerprints remain unchanged; dependent analyses are recomputed.

### Strict merchant key

Affected reader rows/records/events: 5,094,867. NFKC uppercase; longest configured prefix first; remove 3+-digit runs, store-number patterns and alphanumeric reference tokens; preserve raw merchant. A reference-only Amazon marketplace descriptor retains its marketplace identity.

### Loose merchant aliases

Affected reader rows/records/events: 1,307,270. Only explicit merchant_aliases.yaml patterns and six supplied source-city suffixes; alias effect counts below; dictionary entries are hypotheses, not verified entity matches.

### MCC description normalization

Affected reader rows/records/events: 9,516,048. NFKC uppercase, punctuation/space collapse and AND/& equivalence. Raw spelling is preserved.

### Description-to-code linkage

Affected reader rows/records/events: 6,981,636. Exact, normalized, unambiguous observed code-description, unique >=16-character prefix, then fuzzy >=95 with margin >=5; every other candidate remains needs_review. Inferred labels never overwrite source codes.

### Reference validity

Affected reader rows/records/events: 15,291. Current Visa, historical Citi and explicit Mastercard facts retain network/version status. Unlisted or historical-only is review-worthy, not proof of source corruption.

### Official group caption parsing

Affected reader rows/records/events: 6,976,157. Parse single-code and code-range captions independently. Brand ranges retain the exact published upper categories. Original group wording is retained in mcc_group_raw; one singular catalogue-wording variant is documented in reference/group_name_normalizations.csv.

### Stockport label scheme

Affected reader rows/records/events: 34,010. Purpose-present rows use internal category; purpose-absent rows with category are MCC candidates. Do not impose unverified calendar-year cutoffs. Exact normalized MCC descriptions in supplier field are masked.

### Primary card filter

Affected reader rows/records/events: 122,620. Supplier payments, zero returns, fees, adjustments, transfers, cash and unknown records stay canonical but are excluded from primary card-only label/purity/coverage analysis.

### Purity support

Affected reader rows/records/events: 11,687,242. Support N>=20 separately per merchant/source/scheme; event counts across schemes overlap and are not a unique-transaction total. Majority bands: >=.9, [.7,.9), <.7. Report support coverage.

### Purity uncertainty

Affected reader rows/records/events: 17,365. 1000 empirical i.i.d. bootstrap replicates, seed42-derived per identity. Normalize by fixed observed within-merchant label count; clustering, key and temporal dependence uncertainty are outside these intervals.

### Annotation sample

Affected reader rows/records/events: 800. Unlabelled, internal-only, distinct source/descriptor strings with >=20 within-source merchant support and identifier/address screening; deterministic source/group/length/prefix round-robin; unequal inclusion, no prevalence claim.

### Duplicate retention

Affected reader rows/records/events: 9,846,430. No additional duplicates removed during profiling. Supplied Oklahoma fiscal-year inputs were deduplicated upstream; the upstream note is recorded but the original 170-download process is not independently verified. Duplicate counts below apply to retained prepared inputs.

## Explicit exclusions

| Source | Reason | Reader rows |
| --- | --- | ---: |
| solihull | blank | 1,149 |
| moneydata | blank | 8,254 |
| moneydata | documentation | 42 |
| solihull | nontransaction_note | 1,380 |

## Schema variants and column priorities

`data_profile/config/sources/*.yaml` specifies ordered fallback columns and variant rules. Every populated-column signature is counted below; fallback never moves a raw cell or overwrites the source. Different valid values in fallback candidates are not silently reconciled; variant-level field coverage and reviews expose uncertainty.

Every manually configured brand-alias pattern, including zero-effect patterns, is counted separately by source in `tables/merchant_alias_impacts.csv`. The exact regex and target are retained; these counts distinguish matching an already-canonical name from changing a key.

| Source | Variant | Canonical records |
| --- | --- | ---: |
| eden | `council-spending-on-procurement-cards-january-2017.csv|cc4425b4e1e8` | 1 |
| ipo | `e196151697ff` | 1 |
| eden | `edendc01_transactionreport-april-15.csv|2d2c4f3496c1` | 1 |
| eden | `edendc01_transactionreport-april-15.csv|cc4425b4e1e8` | 1 |
| dwp | `numeric_mcc_59ea085f4c3f` | 1 |
| solihull | `proclass_30c71ec027ab` | 1 |
| dwp | `purpose_only_9050b5c95f3b` | 1 |
| dwp | `numeric_mcc_60f77fd26cd4` | 12 |
| dwp | `numeric_mcc_92ed0025f7ac` | 12 |
| solihull | `legacy_cost_centre_9ab28b3f5cc6` | 121 |
| stockport | `mcc_candidate_3e7b9a538b07` | 122 |
| bristol | `e93dffd829d5` | 12,205 |
| solihull | `legacy_cost_centre_43d1650423e6` | 13,001 |
| moneydata | `b527d69df6df` | 14 |
| eden | `council-spending-on-procurement-cards-december-2017.csv|9ffd3a7b97b6` | 14 |
| eden | `edendc01_merchantreportaugust15.csv|cc1434df3192` | 14 |
| eden | `transactionreportjune15.csv|cc1434df3192` | 14 |
| dwp | `numeric_mcc_f63f52d6256d` | 1,427 |
| eden | `edendc_april2017.csv|8e30a5c013d8` | 15 |
| stockport | `internal_db9556f62952` | 15,050 |
| sunderland | `legacy_merchant_6297c1f24e3e` | 152,834 |
| dwp | `purpose_only_ef16c6588cf4` | 157 |
| dwp | `numeric_mcc_2614b30bf794` | 166 |
| stockport | `mcc_candidate_6aac4b3db1fe` | 168 |
| oklahoma | `c2c396893af9` | 1,695 |
| stockport | `unresolved_e4cab1bd666f` | 17 |
| eden | `period8_2016.csv|e0fa34373555` | 176 |
| stockport | `mcc_candidate_6835b5076f80` | 17,793 |
| stockport | `mcc_candidate_0969830d5856` | 184 |
| eden | `period7_2016.csv|e0fa34373555` | 185 |
| oklahoma | `6d09c48b2c84` | 188,898 |
| moneydata | `230616046f24` | 19 |
| ipo | `32beaf4ab63c` | 19 |
| eden | `edendc01_transactionreportdecember15.csv|11a565863d5e` | 19 |
| sunderland | `legacy_merchant_fc404fb9cf80` | 19,845 |
| eden | `edendc_march2017.csv|cc4425b4e1e8` | 2 |
| sunderland | `unresolved_32a88e2efedc` | 2 |
| sunderland | `unresolved_577fb5245be3` | 2 |
| eden | `council-spending-on-procurement-cards-during-december-2016.csv|f7eea67e42e3` | 20 |
| eden | `edendc01_transactionreport_october.csv|fbbadcf6b6b0` | 20 |
| sunderland | `legacy_merchant_a48a27f0becc` | 2,057 |
| eden | `edendc01_merchantreportseptember.csv|cc1434df3192` | 21 |
| eden | `edendc01_september16.csv|ad4e295b2b9e` | 22 |
| eden | `edendc01_transactionreportjuly15.csv|f982aa7a1ac2` | 22 |
| delaware | `0f9c644450b2` | 2,251,316 |
| eden | `council-spending-on-procurement-cards-june-2017.csv|f7eea67e42e3` | 25 |
| eden | `edendc01_april16.csv|f982aa7a1ac2` | 25 |
| eden | `edendc01_july16.csv|f7eea67e42e3` | 26 |
| eden | `edendc01_transactionreport-april-15.csv|484e3de760ab` | 26 |
| eden | `edendc01_transactionreport-november.csv|e47cbd02a17b` | 26 |
| sunderland | `unresolved_4c26758ecf71` | 26 |
| indiana | `4aad71ed4df6` | 284,119 |
| eden | `edendc01_transactionreportmarch.csv|638279b43548` | 29 |
| dwp | `numeric_mcc_02f59bf3b279` | 29 |
| dwp | `numeric_mcc_f06cddf71152` | 3 |
| sunderland | `unresolved_1acf7fa36507` | 3 |
| sunderland | `unresolved_9b875669e760` | 3 |
| eden | `council-spending-on-procurement-cards-september-2017.csv|9ffd3a7b97b6` | 30 |
| eden | `edendc01_may16.csv|f7eea67e42e3` | 30 |
| eden | `edendc01_transactionreportmay15-4.csv|afa2d12dac3e` | 30 |
| stockport | `internal_bf62acdfafc6` | 303 |
| dwp | `purpose_only_f182f0e0d469` | 31 |
| eden | `edendc01_transaction-reportfeb16.csv|8e30a5c013d8` | 32 |
| eden | `edendc01_transaction-reportjanuary16.csv|c726b2ee7a6b` | 32 |
| eden | `edendc01_june16.csv|bb872b24d8df` | 33 |
| sunderland | `bank_export_fa0a14ce83ce` | 332 |
| eden | `edendc_may2017.csv|11a565863d5e` | 35 |
| eden | `council-spending-on-procurement-cards-november-2017.csv|9ffd3a7b97b6` | 36 |
| stockport | `internal_3ae52faf7e32` | 373 |
| sunderland | `legacy_merchant_064e460bf63e` | 3,782 |
| eden | `council-spending-on-procurement-cards-during-february-2017.csv|8e30a5c013d8` | 38 |
| eden | `council-spending-on-procurement-cards-october-2017.csv|9ffd3a7b97b6` | 38 |
| moneydata | `ea0126fd3deb` | 384 |
| eden | `council-spending-on-procurement-cards-january-2017.csv|8e30a5c013d8` | 39 |
| eden | `edendc_march2017.csv|f982aa7a1ac2` | 39 |
| ipo | `6d3bb525555c` | 4 |
| dwp | `purpose_only_9d89f4b92d6d` | 4 |
| eden | `council-spending-on-procurement-cards-august-2017.csv|9ffd3a7b97b6` | 41 |
| eden | `council-spending-on-procurement-cards-july-2017.csv|292c07063552` | 41 |
| sunderland | `legacy_merchant_f3b8587efa75` | 41,196 |
| sunderland | `legacy_merchant_fa1df780cb6e` | 4,380 |
| eden | `edendc01_august16.csv|f7eea67e42e3` | 46 |
| sunderland | `unresolved_fb3d219d7616` | 48 |
| sunderland | `legacy_merchant_5cc4c5b27471` | 4,842 |
| moneydata | `33acdbc7e9ca` | 5 |
| indiana | `95835713e547` | 5 |
| dwp | `numeric_mcc_66f4d6fec56e` | 5 |
| sunderland | `legacy_merchant_949cfd416189` | 5,068 |
| dwp | `purpose_only_078bfe0aac99` | 5,396 |
| moneydata | `a904c9bf3ccb` | 5,431 |
| dwp | `purpose_only_fff93ca1e840` | 55 |
| sunderland | `legacy_merchant_fae40b55b293` | 5,774 |
| moneydata | `53fa24fbeb84` | 61 |
| oklahoma | `2a877c02e79f` | 631 |
| moneydata | `43c553460ba5` | 653 |
| oklahoma | `0a5febaef11e` | 6,692,644 |
| sunderland | `unresolved_bb1cf3bd4042` | 7 |
| sunderland | `legacy_merchant_c5815c394773` | 7,082 |
| dwp | `numeric_mcc_825ba52bcf07` | 718 |
| sunderland | `bank_export_74b6a6bbb95a` | 7,794 |
| dwp | `purpose_only_6e8eeeb7427b` | 9 |
| solihull | `proclass_a57539b1c45e` | 911 |
| sunderland | `bank_export_32e753b521cf` | 92 |
| solihull | `proclass_b2897688d738` | 95,843 |

## Eden file classification

Only the two explicitly identified supplier-payment period files are classified supplier_payment; the other supplied filenames denote procurement-card disclosures or merchant reports. Unknown/missing merchant/date/amount combinations remain record_type unknown rather than being forced into card_txn.

| Upstream file | Record type | Rows |
| --- | --- | ---: |
| `council-spending-on-procurement-cards-august-2017.csv` | card_txn | 41 |
| `council-spending-on-procurement-cards-december-2017.csv` | card_txn | 14 |
| `council-spending-on-procurement-cards-during-december-2016.csv` | card_txn | 20 |
| `council-spending-on-procurement-cards-during-february-2017.csv` | card_txn | 38 |
| `council-spending-on-procurement-cards-january-2017.csv` | card_txn | 39 |
| `council-spending-on-procurement-cards-january-2017.csv` | unknown | 1 |
| `council-spending-on-procurement-cards-july-2017.csv` | card_txn | 41 |
| `council-spending-on-procurement-cards-june-2017.csv` | card_txn | 25 |
| `council-spending-on-procurement-cards-november-2017.csv` | card_txn | 36 |
| `council-spending-on-procurement-cards-october-2017.csv` | card_txn | 38 |
| `council-spending-on-procurement-cards-september-2017.csv` | card_txn | 30 |
| `edendc01_april16.csv` | card_txn | 25 |
| `edendc01_august16.csv` | card_txn | 46 |
| `edendc01_july16.csv` | card_txn | 26 |
| `edendc01_june16.csv` | card_txn | 33 |
| `edendc01_may16.csv` | card_txn | 30 |
| `edendc01_merchantreportaugust15.csv` | card_txn | 14 |
| `edendc01_merchantreportseptember.csv` | card_txn | 21 |
| `edendc01_september16.csv` | card_txn | 22 |
| `edendc01_transaction-reportfeb16.csv` | card_txn | 32 |
| `edendc01_transaction-reportjanuary16.csv` | card_txn | 32 |
| `edendc01_transactionreport-april-15.csv` | card_txn | 26 |
| `edendc01_transactionreport-april-15.csv` | unknown | 2 |
| `edendc01_transactionreport-november.csv` | card_txn | 26 |
| `edendc01_transactionreport_october.csv` | card_txn | 20 |
| `edendc01_transactionreportdecember15.csv` | card_txn | 19 |
| `edendc01_transactionreportjuly15.csv` | card_txn | 22 |
| `edendc01_transactionreportmarch.csv` | card_txn | 29 |
| `edendc01_transactionreportmay15-4.csv` | card_txn | 30 |
| `edendc_april2017.csv` | card_txn | 15 |
| `edendc_march2017.csv` | card_txn | 39 |
| `edendc_march2017.csv` | unknown | 2 |
| `edendc_may2017.csv` | card_txn | 35 |
| `period7_2016.csv` | supplier_payment | 185 |
| `period8_2016.csv` | supplier_payment | 176 |
| `transactionreportjune15.csv` | card_txn | 14 |

## Reference, proxy and disclosure limits

See `reference/README.md` for pinned sources and copyright. Oklahoma proxy categories use TF-IDF character 3-5 grams, a seeded 64-component TruncatedSVD projection with L2 normalization, then frequency-weighted MiniBatchKMeans, k=50 and k=200, seed42, max_features=20000, max_iter=150, n_init=5, batch_size=4096. Vocabulary, IDF, readable term features, and SVD are fitted on the same most frequent up to 50,000 unique informative descriptions to bound memory; all informative items are transformed/clustered in disk-backed batches. Earlier SVD fit used all unique items, so input changes and changed representation fit scope both affect the refreshed proxy results; cluster IDs are not aligned across runs. The occurrence coverage of that fit subset is reported. Preliminary direct sparse-distance clustering was rejected because of severe cluster concentration. The projection was added in response to that methodological failure, not to optimize the purity result; final largest-cluster shares and explained variance are computed in `tables/oklahoma_clustering_summary.csv`. Requested MiniLM-L6-v2 was not cached, so the explicitly authorized fallback is used. Placeholders and per-transaction dominant/basket rules are in `derived/cluster_method.json` and `tables/oklahoma_item_placeholders.csv`. Clusters are not a validated product taxonomy and need semantic review. Primary findings never pool label schemes as though their event counts were independent transactions.

Ambiguous common surnames can occur in ordinary English and institutional/company descriptions. Where source identity columns are available, disclosure screening tests complete normalized cardholder names and surname-plus-initial combinations, not every standalone English word that can also be a surname; such an all-word test would be scientifically uninterpretable. This operational limitation is reported, not presented as complete anonymization. Oklahoma personal columns are absent from all derived analytical schemas. The refreshed prepared inputs omit those source identity columns, so this run has no cardholder-name dictionary; name absence cannot be checked against the unavailable original downloads. Address screening remains active. The prior user-provided raw files and pre-existing concatenations remain untouched and are not claimed to be anonymized by this task.
