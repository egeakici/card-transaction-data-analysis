# Datasheet for the supplied card-related transaction collection

## Motivation

Research questions S1-S7 concern effective sample size, available label systems, statement-descriptor evidence, label agreement, purchase-label concentration, distribution shifts and institutional-card coverage. No predictive model, custom spending taxonomy, annotated labels, or train/test split is produced. Proxy product clustering is descriptive and uses the explicitly authorized fallback.

## Composition

There are 9,846,430 canonical records and 9,723,810 records conservatively classified card_txn. Reader records (9,857,255) reconcile to canonical plus 10,825 explicit exclusions. There are 11 sources: public institutional payment disclosures plus one academic individual-bank-account dataset. Sources are not independent population samples; transactions, descriptors, normalized merchants, and labels have different effective sample sizes. MoneyData is a consumer reference rather than a corporate-card source. IPO contributes only inventory, scope and cross-source overlap diagnostics.

| Source | Publisher | Geography / institution | Canonical rows | Parsed date bounds | Licence | Available MCC rows |
| --- | --- | --- | ---: | --- | --- | --- |
| solihull | Solihull Metropolitan Borough Council | UK / council | 109,877 | 1900-01-01 to 2026-09-10 | [LicenseRef-Solihull-Custom](https://www.solihull.gov.uk/copyright-and-license); conditional_source_terms | 0 numeric MCC; 0 descriptions |
| ipo | Intellectual Property Office | UK / central_gov | 24 | 2025-04-17 to 2026-09-29 | [OGL-UK-3.0](https://www.data.gov.uk/dataset/b4f5e0db-51a6-4f01-9c0c-fe2fe50da0fd/ipo-government-procurement-card-spending); conditional_source_terms | 0 numeric MCC; 0 descriptions |
| oklahoma | State of Oklahoma, Office of Management and Enterprise Services (OMES) | USA / state | 6,883,868 | 2009-04-14 to 2026-09-30 | [LicenseRef-Not-Verified](https://data.ok.gov/); hold | 0 numeric MCC; 6,694,339 descriptions |
| stockport | Stockport Metropolitan Borough Council | UK / council | 34,010 | 2017-01-05 to 2026-10-01 | [OGL-UK-3.0](https://www.data.gov.uk/dataset/42c4d19b-aef7-45d1-bd92-1167d2f8ec68/purchase-card-transactions); conditional_source_terms | 0 numeric MCC; 18,267 descriptions |
| delaware | State of Delaware, Department of Finance, Division of Accounting | USA / state | 2,251,316 | 2014-05-07 to 2026-09-28 | [LicenseRef-Public-Domain-Publisher-Declaration](https://data.delaware.gov/Government-and-Finance/State-Employee-Credit-Card-Transactions/nurt-5rqw/about_data); conditional_source_terms | 0 numeric MCC; 2,251,316 descriptions |
| indiana | State of Indiana, Management Performance Hub | USA / state | 284,124 | 2021-07-01 to 2026-10-01 | [LicenseRef-Not-Verified](https://hub.mph.in.gov/dataset/purchase-and-travel-card-data); hold | 0 numeric MCC; 284,124 descriptions |
| dwp | Department for Work and Pensions | UK / central_gov | 8,026 | 2009-04-01 to 2026-09-17 | [OGL-UK-3.0](https://www.data.gov.uk/dataset/c94529c9-2a1a-469d-a88a-1d52de05484f/dwp-government-procurement-card-payments); conditional_source_terms | 2,373 numeric MCC; 0 descriptions |
| eden | Eden District Council (historical publisher) | UK / council | 1,244 | 2015-04-01 to 2017-12-22 | [LicenseRef-OGL-Version-Unresolved](https://www.data.gov.uk/dataset/05cc719e-3dac-4342-b2b4-e350bd4b37c3/council-spending-on-procurement-cards); hold | 719 numeric MCC; 719 descriptions |
| moneydata | Robert Laramee (Mendeley Data contributor) | UK / academic | 6,567 | 2015-01-09 to 2022-12-07 | [CC-BY-4.0](https://data.mendeley.com/datasets/dnxtg6n4rv/1); conditional_source_terms | 0 numeric MCC; 0 descriptions |
| sunderland | Sunderland City Council | UK / council | 255,169 | 2014-10-01 to 2026-09-30 | [LicenseRef-Sunderland-Conflicting-Terms](https://www.sunderland.gov.uk/article/13262/Purchase-card-payments?ccp=true); hold | 0 numeric MCC; 255,078 descriptions |
| bristol | Bristol City Council | UK / council | 12,205 | 2025-04-08 to 2026-06-19 | [LicenseRef-Bristol-Scope-Unresolved](https://www.bristol.gov.uk/council/council-spending-and-performance/council-purchase-card-transactions); hold | 12,199 numeric MCC; 12,205 descriptions |

Dates are observed parsed fields and can include source anomalies; bounds do not prove continuous coverage. All purchase-label schemes are listed in `tables/purchase_label_coverage.csv`. See original source URLs in configuration and `tables/source_metadata.csv`.

## Collection Process

The user supplied local downloads and already merged source files. The refreshed Oklahoma source consists of 19 prepared fiscal-year CSVs. Its supplied preprocessing note reports removal of blank rows, overlap-month selection, cross-file duplicate filtering, omission of cardholder names, and 631 period-derived dates before delivery. These are upstream operations, not independently reproduced from the unavailable original 170 downloads. The profiling pipeline retains every supplied nonblank record and does not repeat that deduplication. This study has no verified complete collection history before those files. The exact supplied input files, byte sizes, SHA-256 values, headers, row counts, and parse errors are in `manifest.csv`; Oklahoma entries are prepared fiscal-year exports. Row addresses refer to those supplied exports, not to unavailable row addresses in the original 170 downloads. Download/source metadata embedded in DWP, IPO and Eden is retained in the private canonical data. Previously generated folder/global CSV concatenations are excluded from input selection. The Indonesia source is outside the specified eleven-source study.

Public accessibility is not a redistribution grant. Source declarations, restrictions and unresolved terms are recorded in [licenses.yaml](../licenses.yaml); see [DATA_LICENSING.md](../DATA_LICENSING.md). No written permission has been received. MCC factual references cite current Visa, historical Citi, and current Mastercard primary publications and their page/hash provenance; copyright and historical/network differences are explicit in `reference/README.md`.

## Licensing and permissions

The registry review is dated 2026-11-04 and does not certify the licence of every historical local file. Original software is [MIT-licensed](../LICENSE); data, source-derived content and third-party references are excluded from that software grant. No blanket CC BY licence, annotated v1.0 release, Zenodo DOI or ethics committee determination is claimed. See [attribution](../ATTRIBUTION.md), [availability](../DATA_AVAILABILITY.md) and [ethics](../ETHICS_STATEMENT.md). A `hold` blocks redistribution of source records and copied source content pending resolution; `conditional_source_terms` still requires snapshot, notice, excluded-rights and privacy review. Existing aggregate tables and screened examples are not automatically cleared by being public.

| Source | Published licence / assessment | Permission status | Redistribution tier |
| --- | --- | --- | --- |
| bristol | [LicenseRef-Bristol-Scope-Unresolved](https://www.bristol.gov.uk/council/council-spending-and-performance/council-purchase-card-transactions) | scope_unresolved | hold |
| delaware | [LicenseRef-Public-Domain-Publisher-Declaration](https://data.delaware.gov/Government-and-Finance/State-Employee-Credit-Card-Transactions/nurt-5rqw/about_data) | publisher_declared_public_domain | conditional_source_terms |
| dwp | [OGL-UK-3.0](https://www.data.gov.uk/dataset/c94529c9-2a1a-469d-a88a-1d52de05484f/dwp-government-procurement-card-payments) | published_open_license | conditional_source_terms |
| eden | [LicenseRef-OGL-Version-Unresolved](https://www.data.gov.uk/dataset/05cc719e-3dac-4342-b2b4-e350bd4b37c3/council-spending-on-procurement-cards) | license_version_unresolved | hold |
| indiana | [LicenseRef-Not-Verified](https://hub.mph.in.gov/dataset/purchase-and-travel-card-data) | not_verified | hold |
| ipo | [OGL-UK-3.0](https://www.data.gov.uk/dataset/b4f5e0db-51a6-4f01-9c0c-fe2fe50da0fd/ipo-government-procurement-card-spending) | published_open_license | conditional_source_terms |
| moneydata | [CC-BY-4.0](https://data.mendeley.com/datasets/dnxtg6n4rv/1) | published_open_license | conditional_source_terms |
| oklahoma | [LicenseRef-Not-Verified](https://data.ok.gov/) | not_verified | hold |
| solihull | [LicenseRef-Solihull-Custom](https://www.solihull.gov.uk/copyright-and-license) | published_custom_terms | conditional_source_terms |
| stockport | [OGL-UK-3.0](https://www.data.gov.uk/dataset/42c4d19b-aef7-45d1-bd92-1167d2f8ec68/purchase-card-transactions) | published_open_license | conditional_source_terms |
| sunderland | [LicenseRef-Sunderland-Conflicting-Terms](https://www.sunderland.gov.uk/article/13262/Purchase-card-payments?ccp=true) | conflicting_terms | hold |

## Preprocessing

Raw files are read-only. Source-specific column priorities, populated-column variants, date parsing conventions and classification rules are versioned in YAML. Every retained record has its original source file, worksheet and parsed-record row address; excluded rows have reason codes. The supplied Oklahoma fiscal-year extracts already omit the named cardholder columns; the reader additionally excludes those columns if present. No source-name dictionary is available in this refreshed input, so the disclosure check cannot establish absence against original cardholder names. Address-like purpose labels are masked before persistence. Raw merchant strings remain unchanged in private derived data; strict/loose keys, parsed dates/amounts, reference links, record types and official groups are separate fields. There is no additional deduplication in this profiling run; upstream Oklahoma preprocessing is disclosed separately. All operational decisions and affected counts are in `DECISIONS.md`.

## Uses

Suitable for descriptive research on the **supplied extracts**, label systems and evidence limits, subject to linkage and entity-resolution sensitivity. Unsuitable for population-level consumer-spending prevalence, verified receipt-level ground truth, fraud scoring, individual profiling, causal issuer comparisons or an established model-performance ceiling. Purity calculations condition on label coverage, merchant support and institutional label granularity; TF-IDF clusters are unvalidated product proxies. Candidate MCC matches require expert review.

## Distribution

Only code, aggregate tables, report text, and non-personal factual reference snapshots are versioned. Original data and private `derived/` files are excluded from Git and are not published. `annotation/` is internal-only and excluded from Git. Public tables use stable opaque merchant IDs and repeated, screened examples. The automated disclosure check covers street/number patterns and uses full cardholder-name and surname-plus-initial patterns only when source identities are available; the refreshed prepared Oklahoma input provides no such dictionary; it is not a guarantee against every conceivable re-identification attack. Existing user datasets and earlier CSV outputs are preserved and are outside the new publication artifact directory.

## Maintenance

Maintainer: local project owner; contact details not supplied. Publication scope and source-specific holds are documented in [DATA_LICENSING.md](../DATA_LICENSING.md). Access date for reference provenance is 2026-10-31. Reproduce with `python -m data_profile.run --all --no-commit`; the pipeline uses seed 42 and pinned MCC facts. Preserve original hashes, dependency versions and source snapshots; never merge new downloads into a published result without rerunning reconciliation and disclosure tests. Manual review lists are generated, not silently resolved. No claims of future maintenance or dataset completeness are made.
