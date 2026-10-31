# Amount Time Org

Research questions: S6, S7.

Inputs: derived/canonical.parquet; derived/purchase_labels.parquet.

Method: Full-source quantiles (Polars default nearest interpolation), negative-amount rates, monthly/date concentration, duplicate fingerprints, IDs, organization shares and source-specific calendar checks.

Limitations: No currency conversion; source publication thresholds and download windows are selection mechanisms. Amount negative rates use all canonical records as denominator. MoneyData debits are represented as negative and credits as positive: its negative-share statistic denotes outflows, not a refund rate, and must not be compared as a like-for-like refund measure with public spending files. Negative public-source amounts can be reversals/refunds but their meanings are not individually verified. Oklahoma exact-row duplicates exclude the three personal columns; all other raw fields, including transaction IDs and upstream provenance, remain in the fingerprint. Duplicate IDs need not be duplicate transactions.

All amounts remain in native currency. `amount_summary.csv` directly tests the proposed GBP 500 publication lower bound, instead of assuming it. `date_concentration_yearly.csv` quantifies date heaping; heaping alone does not identify statement dates. `delaware_fiscal_calendar_check.csv` tests the July fiscal-calendar claim against actual parsed dates.

Oklahoma calendar-month shares are in `oklahoma_month_totals.csv` and `oklahoma_month_distribution.csv`. Equal-sized original file extracts and sparse month coverage must not be interpreted as annual census sampling. Stockport chronology and label-period assumptions are tested in `stockport_period_checks.csv`; Eden file classifications and adjacent-code candidates are explicit tables. Records are never deduplicated or rewritten.

`figures/monthly_coverage_timeline.pdf` shows every calendar month, with no-record cells blank and logarithmic record counts. The seasonal month-of-year heatmap is a separate figure. Pre-2000 date outliers remain in the tables and are excluded only from the displayed timeline so they do not compress the observed modern download windows into unreadable cells.

