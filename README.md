# Card Transaction Data Analysis

`card-transaction-data-analysis` provides reproducible scientific analysis of 11 real-world transaction data sources from the United States and the United Kingdom. The project examines source coverage, merchant descriptions, Merchant Category Codes (MCC), purchase labels, label consistency, merchant purity, amounts, and time distributions.

The analysis is descriptive. It does not train a predictive classifier or create a train/test split. Unsupervised proxy clusters are exploratory categories and require semantic review.

## Results and documentation

Start with the [key findings](outputs/KEY_FINDINGS.md) and [data card](outputs/DATA_CARD.md). The [artifact index](outputs/README.md) links to the reports, tables, and figures; entries marked internal-only are intentionally absent from Git.

The refreshed run (2026-11-04) reconciles **9,857,255 reader records** into **9,846,430 canonical rows** and **10,825 excluded rows**, with exclusion reasons retained. Hash verification confirms that all **32 supplied input files** remain unchanged. See the [quality checks](outputs/quality_checks.json) and [input manifest](outputs/manifest.csv).

Additional documentation:

- [Methodological decisions and limitations](outputs/DECISIONS.md)
- [Scientific reports](outputs/reports/)
- [Aggregate CSV tables](outputs/tables/)
- [Figures: 300 dpi PNG and vector PDF](outputs/figures/)
- [Disclosure checks](outputs/privacy_checks.json)
- [Artifact checks](outputs/artifact_checks.json)
- [Recorded Python and package versions](outputs/environment.json)

## Sources and scope

Source configurations cover Bristol, Delaware, DWP, Eden, Indiana, IPO, MoneyData, Oklahoma, Solihull, Stockport, and Sunderland. Their schemas, paths, and source-specific rules are documented in [data_profile/config/sources](data_profile/config/sources/).

The supplied Indonesia dataset and synthetic datasets are outside this study. Previously generated XLSX-to-CSV conversions and concatenated CSVs are excluded from analysis inputs to prevent double counting. Source labels and descriptive proxy labels remain distinct, and source provenance is retained.

## Repository structure

```text
data_profile/             Analysis code, source configurations, and tests
outputs/                  Reports, aggregate tables, figures, and audit metadata
real-world-datas/         Source-folder READMEs; original/converted data stays local
synthetic-gen-datas/      Dataset READMEs; synthetic data stays local, outside scope
derived/                 Canonical Parquet files and intermediates (local only)
.data_processing/         Earlier preparation scripts and access cache (local only)
```

Original inputs, converted and merged transaction CSVs, private derived data, access caches, and internal annotation material are excluded from Git through [.gitignore](.gitignore). Within the two dataset directories, only files named `README.md` are eligible for tracking. These documents preserve the visible source-folder structure without distributing the datasets.

The public repository is [egeakici/card-transaction-data-analysis](https://github.com/egeakici/card-transaction-data-analysis). Its publication scope includes analysis code, source configurations, scientific reports, aggregate tables, figures, and audit metadata. Some analytical tables retain source category descriptions and screened merchant examples; they are not a release of the original transaction records. A clone does not contain the input datasets, transaction-level Parquet intermediates, or internal annotation samples.

## Setup

The recorded environment uses Python 3.13.2 on Windows. From the repository root, create an environment and install the direct dependency versions used for the analysis:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r data_profile/requirements.lock.txt
```

The [dependency pins](data_profile/requirements.lock.txt) record direct dependencies; the [environment record](outputs/environment.json) documents the completed run.

## Reproduce the analysis

Obtain authorized copies of the exact supplied input snapshots and place them at the paths declared in the source configurations under `real-world-datas/`. Oklahoma requires the nineteen prepared fiscal-year exports matching this snapshot and the supplied preprocessing note. Reconstructing those exports from the unavailable original 170-download collection is outside this analysis pipeline. Compare the supplied inputs with the recorded manifest. Grant read access to the originals on your own machine; the existing access cache is machine-specific and is not distributed.

Run the complete pipeline and parser/analysis tests:

```powershell
.\.venv\Scripts\python.exe -m data_profile.run --all --no-commit
.\.venv\Scripts\python.exe -m unittest discover -s data_profile/tests -v
```

The pipeline writes derived files and regenerates analysis outputs while preserving original inputs. Stages run sequentially, and reconciliation must pass before downstream analysis. Randomized operations use seed 42.

To rerun a stage after its prerequisites have completed:

```powershell
.\.venv\Scripts\python.exe -m data_profile.run --stage descriptive --no-commit
```

Available stages are `ingest`, `labels`, `merchants`, `consistency`, `purity`, `descriptive`, `annotation`, and `finalize`. `--reuse-canonical` skips ingestion when the existing canonical data passes reconciliation. `--reuse-proxies` reuses completed proxy labels when rerunning the purity stage. Without `--no-commit`, the runner creates local Git commits after completed stages.

## Interpretation and disclosure

Source populations, observation periods, schemas, and label granularity differ. Reported merchant purity is a descriptive measure of label consistency, not predictive accuracy. Proxy clusters are unvalidated, and review candidates are not automatic corrections. Consult the data card and reports before pooling sources or interpreting comparisons.

The prepared Oklahoma inputs already omit named cardholder columns; no original source-name dictionary is available for this refreshed run. The reader omits such fields if present, address-like descriptions are masked, and published merchant examples undergo support and disclosure screening. These checks do not certify complete anonymity. `outputs/annotation/` contains internal annotation material and is excluded from Git along with private intermediates.

## Licensing

No project-wide license has been declared. Source datasets and reference manuals retain their respective terms; this repository does not grant redistribution rights to those materials. See the source documentation and [reference records](outputs/reference/reference_manifest.json).

## Oklahoma refresh (2026-11-04)

Oklahoma now contributes **6,883,868 prepared records** from nineteen fiscal-year files (FY2009-FY2027), replacing the earlier 900,000-row slice. Observed dates span **2009-04-14 to 2026-09-30**; FY2027 means July-September 2026 in this snapshot. Upstream deduplication and 631 period-derived dates are disclosed, and no further deduplication is applied during profiling. The source's original 170-download processing and population completeness are not independently verified.

See the [refresh report](outputs/reports/12_oklahoma_refresh.md), [fiscal-year coverage](outputs/tables/oklahoma_fiscal_year_coverage.csv), [old/new comparison](outputs/tables/oklahoma_refresh_comparison.csv), and [refresh checks](outputs/oklahoma_refresh_checks.json). All sources and proxy clusters were recomputed from the current inputs. Earlier outputs are privately archived under `derived/history/`; the separately created Oklahoma merged CSV remains local and excluded from profiling inputs.
