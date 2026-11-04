# Datasheet for the supplied card-related transaction collection

## Motivation

Research questions S1-S7 concern effective sample size, available label systems, statement-descriptor evidence, label agreement, purchase-label concentration, distribution shifts and institutional-card coverage. No predictive model, custom spending taxonomy, annotated labels, or train/test split is produced. Proxy product clustering is descriptive and uses the explicitly authorized fallback.

## Composition

There are 9,846,430 canonical records and 9,723,810 records conservatively classified card_txn. Reader records (9,857,255) reconcile to canonical plus 10,825 explicit exclusions. There are 11 sources: public institutional payment disclosures plus one academic individual-bank-account dataset. Sources are not independent population samples; transactions, descriptors, normalized merchants, and labels have different effective sample sizes. MoneyData is a consumer reference rather than a corporate-card source. IPO contributes only inventory, scope and cross-source overlap diagnostics.

| Source | Publisher | Geography / institution | Canonical rows | Parsed date bounds | Licence | Available MCC rows |
| --- | --- | --- | ---: | --- | --- | --- |
| solihull | Solihull Metropolitan Borough Council | UK / council | 109,877 | 1900-01-01 to 2026-09-10 | unspecified | 0 numeric MCC; 0 descriptions |
| ipo | UK Intellectual Property Office | UK / central_gov | 24 | 2025-04-17 to 2026-09-29 | unspecified | 0 numeric MCC; 0 descriptions |
| oklahoma | State of Oklahoma, Office of Management and Enterprise Services (OMES) | USA / state | 6,883,868 | 2009-04-14 to 2026-09-30 | unspecified | 0 numeric MCC; 6,694,339 descriptions |
| stockport | Stockport Council | UK / council | 34,010 | 2017-01-05 to 2026-10-01 | unspecified | 0 numeric MCC; 18,267 descriptions |
| delaware | State of Delaware (Delaware Open Data) | USA / state | 2,251,316 | 2014-05-07 to 2026-09-28 | unspecified | 0 numeric MCC; 2,251,316 descriptions |
| indiana | State of Indiana (Management Performance Hub) | USA / state | 284,124 | 2021-07-01 to 2026-10-01 | unspecified | 0 numeric MCC; 284,124 descriptions |
| dwp | UK Department for Work and Pensions | UK / central_gov | 8,026 | 2009-04-01 to 2026-09-17 | unspecified | 2,373 numeric MCC; 0 descriptions |
| eden | Eden District Council (historical publisher) | UK / council | 1,244 | 2015-04-01 to 2017-12-22 | unspecified | 719 numeric MCC; 719 descriptions |
| moneydata | MoneyVis research authors (hosted by Mendeley Data) | UK / academic | 6,567 | 2015-01-09 to 2022-12-07 | unspecified | 0 numeric MCC; 0 descriptions |
| sunderland | Sunderland City Council | UK / council | 255,169 | 2014-10-01 to 2026-09-30 | unspecified | 0 numeric MCC; 255,078 descriptions |
| bristol | Bristol City Council | UK / council | 12,205 | 2025-04-08 to 2026-06-19 | unspecified | 12,199 numeric MCC; 12,205 descriptions |

Dates are observed parsed fields and can include source anomalies; bounds do not prove continuous coverage. All purchase-label schemes are listed in `tables/purchase_label_coverage.csv`. See original source URLs in configuration and `tables/source_metadata.csv`.

## Collection Process

The user supplied local downloads and already merged source files. The refreshed Oklahoma source consists of 19 prepared fiscal-year CSVs. Its supplied preprocessing note reports removal of blank rows, overlap-month selection, cross-file duplicate filtering, omission of cardholder names, and 631 period-derived dates before delivery. These are upstream operations, not independently reproduced from the unavailable original 170 downloads. The profiling pipeline retains every supplied nonblank record and does not repeat that deduplication. This study has no verified complete collection history before those files. The exact supplied input files, byte sizes, SHA-256 values, headers, row counts, and parse errors are in `manifest.csv`; Oklahoma entries are prepared fiscal-year exports. Row addresses refer to those supplied exports, not to unavailable row addresses in the original 170 downloads. Download/source metadata embedded in DWP, IPO and Eden is retained in the private canonical data. Previously generated folder/global CSV concatenations are excluded from input selection. The Indonesia source is outside the specified eleven-source study.

Publicly accessible does not imply an open redistribution licence. Source licences are recorded as unspecified unless established from supplied provenance. MCC factual references cite current Visa, historical Citi, and current Mastercard primary publications and their page/hash provenance; copyright and historical/network differences are explicit in `reference/README.md`.

## Preprocessing

Raw files are read-only. Source-specific column priorities, populated-column variants, date parsing conventions and classification rules are versioned in YAML. Every retained record has its original source file, worksheet and parsed-record row address; excluded rows have reason codes. The supplied Oklahoma fiscal-year extracts already omit the named cardholder columns; the reader additionally excludes those columns if present. No source-name dictionary is available in this refreshed input, so the disclosure check cannot establish absence against original cardholder names. Address-like purpose labels are masked before persistence. Raw merchant strings remain unchanged in private derived data; strict/loose keys, parsed dates/amounts, reference links, record types and official groups are separate fields. There is no additional deduplication in this profiling run; upstream Oklahoma preprocessing is disclosed separately. All operational decisions and affected counts are in `DECISIONS.md`.

## Uses

Suitable for descriptive research on the **supplied extracts**, label systems and evidence limits, subject to linkage and entity-resolution sensitivity. Unsuitable for population-level consumer-spending prevalence, verified receipt-level ground truth, fraud scoring, individual profiling, causal issuer comparisons or an established model-performance ceiling. Purity calculations condition on label coverage, merchant support and institutional label granularity; TF-IDF clusters are unvalidated product proxies. Candidate MCC matches require expert review.

## Distribution

Only code, aggregate tables, report text, and non-personal factual reference snapshots are versioned. Original data and private `derived/` files are excluded from Git and are not published. `annotation/` is internal-only and excluded from Git. Public tables use stable opaque merchant IDs and repeated, screened examples. The automated disclosure check covers street/number patterns and uses full cardholder-name and surname-plus-initial patterns only when source identities are available; the refreshed prepared Oklahoma input provides no such dictionary; it is not a guarantee against every conceivable re-identification attack. Existing user datasets and earlier CSV outputs are preserved and are outside the new publication artifact directory.

## Maintenance

Maintainer: local project owner; contact and release policy unspecified. Access date for reference provenance is 2026-10-31. Reproduce with `python -m data_profile.run --all --no-commit`; the pipeline uses seed 42 and pinned MCC facts. Preserve original hashes, dependency versions and source snapshots; never merge new downloads into a published result without rerunning reconciliation and disclosure tests. Manual review lists are generated, not silently resolved. No claims of future maintenance or dataset completeness are made.
