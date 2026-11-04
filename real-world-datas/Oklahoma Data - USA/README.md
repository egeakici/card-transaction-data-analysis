# Oklahoma PCard Data - USA

Publisher: State of Oklahoma, Office of Management and Enterprise Services (OMES). Supplied provenance identifies the [data.ok.gov portal](https://data.ok.gov/) Purchase Card fiscal-year datasets as the source. This refresh replaces the earlier limited OpenGov slice.

The local `birlesik/` directory contains nineteen prepared fiscal-year files, FY2009-FY2027, with 6,883,868 retained records. Observed dates span 2009-04-14 to 2026-09-30. FY2027 currently means July-September 2026; it does not imply future calendar transactions. Full population completeness is not established.

The supplied preparation note reports blank-row removal, overlap and duplicate filtering, omitted cardholder names, and 631 dates derived from reporting periods before these inputs were delivered. Those operations are disclosed rather than independently reproduced; this profiling run applies no additional deduplication.

`birlesik_tam.csv` is a private concatenation of the nineteen fiscal files in ascending fiscal-year order. The twelve supplied columns and within-file row order are preserved. It is excluded from both profiling input selection and Git. All dataset CSVs and other local data files remain unpublished; this directory exposes README documentation only.

See the [source configuration](../../data_profile/config/sources/oklahoma.yaml), [refresh report](../../outputs/reports/12_oklahoma_refresh.md), and [fiscal-year coverage](../../outputs/tables/oklahoma_fiscal_year_coverage.csv). Analysis code, aggregate tables, figures, and reports are versioned separately under `data_profile/` and `outputs/`.
