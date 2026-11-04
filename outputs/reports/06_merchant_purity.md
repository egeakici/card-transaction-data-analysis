# Merchant Purity

Research questions: S5.

Inputs: derived/canonical.parquet; derived/purchase_labels.parquet.

Method: Separate each purchase-label scheme; normalize categorical text; evaluate merchants with >=20 labeled card transactions. Entropy is H/log2(K observed within that merchant); multinomial resampling is equivalent to 1,000 i.i.d. transaction-label bootstrap replicates. Use empirical percentile 95% intervals with fixed observed support and deterministic seed 42.

Limitations: Label concentration is an observational proxy, not classification accuracy, a causal identity-content relationship, an information-theoretic ceiling, or proof that a statement string identifies a purchase. Label granularity, institutional bookkeeping, merchant-key merging, extraction windows and missing-label selection matter. Bootstrap intervals condition on observed labels, key assignments and proxy clusters; they omit clustering/entity-resolution uncertainty and serial dependence.

# Merchant identity and observed purchase-label concentration

The analysis reports concentration, without treating its majority-share number as recovered spending content. High purity means majority share >=0.9, medium means >=0.7 and <0.9, and low means <0.7. Denominators are explicit: `supported_transactions` includes only merchants with N>=20; the same table also gives coverage and shares of all labeled records. Schemes must not be summed because a transaction may carry multiple schemes.

| Source | Scheme | Supported transactions | Support coverage | High-purity share | Low-purity share |
| --- | --- | ---: | ---: | ---: | ---: |
| bristol | bristol_nature | 8,424 | 70.40% | 43.64% | 45.57% |
| bristol | bristol_sercop | 8,424 | 70.40% | 95.54% | 3.56% |
| dwp | dwp_purpose | 5,316 | 68.24% | 64.79% | 16.70% |
| eden | eden_purpose | 63 | 39.87% | 0.00% | 100.00% |
| moneydata | moneydata_category | 3,124 | 69.53% | 97.76% | 1.60% |
| oklahoma | oklahoma_proxy_k200 | 2,845,345 | 96.08% | 18.94% | 76.06% |
| oklahoma | oklahoma_proxy_k50 | 2,845,345 | 96.08% | 20.92% | 74.31% |
| solihull | solihull_detailed_expenses | 8,777 | 67.01% | 2.92% | 92.65% |
| solihull | solihull_proclass | 77,714 | 80.56% | 26.25% | 53.95% |
| solihull | solihull_purpose | 77,357 | 80.52% | 1.81% | 90.21% |
| stockport | stockport_internal_category | 9,785 | 68.48% | 20.04% | 36.29% |
| stockport | stockport_purpose | 9,786 | 68.48% | 16.87% | 34.82% |

Oklahoma: uninformative placeholders are enumerated in `oklahoma_item_placeholders.csv` and the configured rule set. Pipe-separated items are split before proxy construction. The requested embedding checkpoint is unavailable locally; the authorized fallback starts with character 3-5 gram TF-IDF (20,000 features). Preliminary direct sparse-distance clustering exhibited severe concentration and is not used as evidence of purchase purity. The operational fallback uses a seeded 64-component TruncatedSVD projection and L2 normalization before frequency-weighted MiniBatchKMeans with k=50 and k=200, seed 42 (batch_size=4096, n_init=5, max_iter=150). This is a documented representation choice, not supervised category learning. To bound memory, vocabulary/IDF, readable word-term features, and the SVD representation are fitted on the same most frequent up to 50,000 unique informative descriptions (count then lexical order); transformation, frequency-weighted clustering and purity metrics cover **all** informative items in bounded batches with disk-backed embeddings. The earlier run fitted SVD on all unique descriptions. This changed fit scope and the refreshed input both affect proxy results; old and new cluster IDs are not aligned. A transaction is informative only when at least one pipe-separated item is informative, and redaction markers are placeholders. Vocabulary-fit occurrence coverage, explained variance and largest-cluster share are explicit diagnostics. SVD explained variance refers to its frequent-description reference fit, not to the entire item population. Clusters are **proxy categories**, not validated product labels, and still need semantic review even if collapse is absent. Primary per-transaction proxies use the modal item cluster, with a deterministic smallest-ID tie break. Sorted cluster-basket signatures are a separate sensitivity analysis. Public cluster examples additionally require at least twenty occurrences of the normalized item description across the supplied Oklahoma data, as well as a merchant with at least twenty records. Some clusters may therefore have fewer than five examples. No source-name dictionary exists in these prepared inputs; this rule reduces rare-example disclosure without establishing complete anonymity. Cluster terms/examples and counts are in `oklahoma_item_clusters.csv` and `oklahoma_clustering_summary.csv`.

Direct categorical analyses include Bristol Nature and SERCOP, Solihull purpose/ProClass and parsed code/top-level variants where present, Stockport internal category/purpose, Eden purpose, DWP normalized and exact-purpose sensitivity, and MoneyData author categories. Address-like Solihull labels are masked before persistence and excluded from concentration, without printing their original values. Academic MoneyData is a separate consumer reference; transfers/cash/fees are reported in record types and excluded from primary card-only purity.

`merchant_purity.csv` gives merchant entropy, majority share, unique labels and bootstrap intervals; `purity_by_mcc.csv` provides supported transaction-weighted code/group slices; `lowest_purity_mcc_top20.csv` and `lowest_purity_merchants_top30.csv` identify review candidates. MCC/purchase-label associations use Cramer's V and mutual information in bits (`mcc_purchase_association.csv`). Small or sparse contingency tables and high-cardinality purpose vocabularies can inflate association statistics; these are descriptive, without significance or generalization claims.

