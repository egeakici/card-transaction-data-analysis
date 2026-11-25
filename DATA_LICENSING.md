# Data licensing and publication scope

Evidence reviewed: **2026-11-04**. This is an evidence inventory and project publication policy, not a legal opinion or a guarantee of permission. No written publisher permission has been received, as confirmed by the project owner. No Zenodo DOI, annotated dataset release, or ethics committee decision is documented.

## Software and data have separate terms

The [MIT licence](LICENSE) applies to this project's original software, tests and software-use documentation, including the implementation in `data_profile/`. It does **not** relicense input datasets, converted/merged files, source-derived text or tables, MCC descriptions/manuals, third-party reference snapshots, trademarks or dependencies. These retain their own rights and terms. There is no project-wide CC BY 4.0 licence for the combined data or analytical outputs. Independently authored study reports have no separate blanket licence declared by this change.

The authoritative machine-readable inventory is [licenses.yaml](licenses.yaml). Its `LicenseRef-*` identifiers describe unresolved or custom situations; they are not permission grants. `verified_at` records a checked declaration or restriction, not a permission letter or historical-file audit. `checked_at` also covers failed attempts. A null `license_url` or `verified_at` means permission could not be established. See the manifest's field and tier definitions.

## Source inventory

<!-- BEGIN LICENSE INVENTORY -->

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

<!-- END LICENSE INVENTORY -->

The findings concern the linked current publisher declarations. File-specific notices, acquisition dates and correspondence for every supplied historical snapshot have not been reconstructed. A catalogue website's own footer licence is not evidence that every linked dataset has that licence.

## Conditions and unresolved evidence

- **DWP, IPO and Stockport:** dataset licence links identify [OGL v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Preserve applicable source notices and the acknowledgement in [ATTRIBUTION.md](ATTRIBUTION.md). OGL excludes personal data, unauthorised third-party rights and certain other material; it does not authorise claims of official status or endorsement.
- **MoneyData:** the [version-1 deposit](https://data.mendeley.com/datasets/dnxtg6n4rv/1) declares [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Retain credit and notices, link the licence and source, and identify adaptations. Check the local workbook against that deposit. Its DOI identifies an external source, not a release of this collection.
- **Delaware:** the [publisher metadata](https://data.delaware.gov/Government-and-Finance/State-Employee-Credit-Card-Transactions/nurt-5rqw/about_data) declares Public Domain. This was visible in indexed official-page content; direct rendering was incomplete. No particular dedication instrument is identified, so neither CC0 nor a general public-domain rule for US state records is asserted.
- **Solihull:** [custom council terms](https://www.solihull.gov.uk/copyright-and-license) permit reuse subject to conditions. Carry attribution through sublicences; use the latest information, distinguish amendments and commentary, retain qualifications, and do not imply council approval. Personal data and unauthorised third-party rights are excluded. The latest-version requirement must be reconciled with historical snapshots before release; a blanket CC BY label would not capture these conditions.
- **Bristol:** the [current purchase-card page](https://www.bristol.gov.uk/council/council-spending-and-performance/council-purchase-card-transactions) does not state reuse terms, and the [general copyright policy](https://www.bristol.gov.uk/council/about-our-website/copyright-of-website-content) restricts redistribution. A [historical over-GBP500 catalogue](https://www.data.gov.uk/dataset/1a4c67e7-cc89-4948-82a7-c2ede666535c/purchase-card-spend-over-500) lists OGL, but coverage of the supplied later workbooks is unverified. Hold source content pending scope confirmation.
- **Eden:** the [dataset catalogue](https://www.data.gov.uk/dataset/05cc719e-3dac-4342-b2b4-e350bd4b37c3/council-spending-on-procurement-cards) declares OGL through an unresolved, unversioned link. Do not silently choose v3.0. Confirm the version and coverage of the supplier-payment files included in the supplied merge.
- **Sunderland:** the [purchase-card page](https://www.sunderland.gov.uk/article/13262/Purchase-card-payments?ccp=true) links to OGL v3.0 but also restricts commercial reuse; the [general policy](https://www.sunderland.gov.uk/article/13513/Open-Data-Licence?ccp=true) defaults to CC0 unless otherwise stated. Treat the conflicting terms as unresolved and retain the source-specific credit in [ATTRIBUTION.md](ATTRIBUTION.md).
- **Indiana and Oklahoma:** official portal access was blocked during verification; no licence or written permission was established. This is an evidence gap, not a finding that no licence exists. Oklahoma's underlying fiscal-year packages require individual scope checks; attribution and public access do not themselves establish reuse rights.

## Current repository and derived outputs

Raw/converted/merged transaction files, private Parquet intermediates, caches, annotation samples and internal correspondence stay outside Git under [.gitignore](.gitignore). Existing folder READMEs and source links may be published. Removing personal fields does not create a redistribution licence.

The repository contains scientific reports, figures and aggregate tables. Some existing tables contain source category wording and screened merchant examples; reference snapshots retain third-party descriptions. **These materials have not all been cleared for onward reuse.** Aggregation or an automated privacy-check pass does not establish copyright, database-right or privacy clearance. The `hold` tier applies to copied source content as well as transaction records. Independently computed statistics and independently authored commentary require their own assessment; no blanket licence or legal exception is asserted here. This documentation update does not remove earlier public commits or certify their contents.

Visa, Mastercard and Citi reference material is outside the eleven-source data inventory and outside the MIT grant. See [reference provenance](outputs/reference/README.md) and its linked publisher notices. Factual extraction does not license a whole manual. Synthetic data and the excluded Indonesia dataset are also outside this study's licence assessment.

## Any future data release

Before releasing source records, copied descriptions, record identifiers or annotations, match each file/hash to a documented grant and resolve every hold. Record any actual written permission's scope, permitted recipients/uses, duration, attribution and restrictions; retain the evidence privately under `internal_docs/` and publish only a shareable redacted reference. Permission to analyse must not be reported as permission to redistribute. Rights review and privacy review are separate.

For sources without an established redistribution grant, publish source metadata and independently authored methods; a future identifiers/annotations/retrieval-script package still needs its own rights and privacy review. This repository currently provides source URLs and analysis code, **not a complete official-portal retrieval script**. Do not promise such a package or release it under CC BY before it exists and is cleared. Licence only rights the authors actually hold; retain compatible source notices rather than replacing them with the software licence.

Use [DATA_AVAILABILITY.md](DATA_AVAILABILITY.md), [ETHICS_STATEMENT.md](ETHICS_STATEMENT.md), [ATTRIBUTION.md](ATTRIBUTION.md) and [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md) for the current statements. A later annotated v1.0/Zenodo statement must name the actual version, DOI, cleared sources and exclusions. Any ethics exemption sentence must reproduce an actual institutional determination with its date and decision reference. Neither is available at this review.

## Updating the inventory

Edit `licenses.yaml` only from documented publisher evidence; then refresh the data card and metadata without rerunning the numerical analysis:

```powershell
py -3.13 -m data_profile.src.licensing
py -3.13 -m unittest discover -s data_profile/tests -v
```

Source configurations inherit the registry at runtime. Refresh also updates their stored licensing metadata, the source table here and credits in `ATTRIBUTION.md`. Preserve historical input hashes and record why a status changed. Never infer permission from a successful download or a US state-government publisher alone.
