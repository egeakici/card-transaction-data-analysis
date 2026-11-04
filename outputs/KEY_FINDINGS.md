# Key findings

All statements below are generated from full-source computed tables. Purity is empirical within-merchant label concentration, not measured prediction accuracy. Scheme denominators overlap and must not be summed.

1. The study contains 9,846,430 canonical records from 11 sources, reconciled against 9,857,255 reader records with 10,825 reason-coded exclusions ([reconciliation.csv](tables/reconciliation.csv)).

2. Oklahoma contributes 6,883,868 of 9,846,430 canonical records (69.91%); pooled results are consequently dominated by its source population ([source_pool_weights.csv](tables/source_pool_weights.csv)).

3. The supplied Bristol workbooks contain 12,205 transaction rows, rather than the sample-based approximate count ([reconciliation.csv](tables/reconciliation.csv)).

4. The MoneyData workbook contributes 6,567 canonical transactions; its blank worksheet extents and documentation are excluded ([reconciliation.csv](tables/reconciliation.csv)).

5. Delaware has 2,251,316 merchant-bearing rows but 106,177 loose merchant keys (4.72% keys per row) ([merchant_summary.csv](tables/merchant_summary.csv)).

6. Oklahoma has 6,883,868 merchant-bearing rows but 228,843 loose merchant keys (3.32% keys per row) ([merchant_summary.csv](tables/merchant_summary.csv)).

7. Sunderland has 255,078 merchant-bearing rows but 3,775 loose merchant keys (1.48% keys per row) ([merchant_summary.csv](tables/merchant_summary.csv)).

8. 1,191,629 of 6,883,868 dated Oklahoma records (17.31%) occur in May or June ([oklahoma_month_totals.csv](tables/oklahoma_month_totals.csv)).

9. The refreshed Oklahoma input has 19 fiscal-year files with 40 to 490,749 records per file; equal-sized extraction caps are not assumed ([reconciliation.csv](tables/reconciliation.csv)).

10. Oklahoma fiscal-year labels span 2009-2027, while observed dates span 2009-04-14 to 2026-09-30; fiscal-year labels do not imply future calendar transactions ([oklahoma_fiscal_year_coverage.csv](tables/oklahoma_fiscal_year_coverage.csv)).

11. Oklahoma FY2010 has MCC descriptions on 1,954 of 144,803 records (1.35%); missing early labels limit longitudinal MCC comparisons ([oklahoma_fiscal_year_coverage.csv](tables/oklahoma_fiscal_year_coverage.csv)).

12. 631 Oklahoma dates were imputed from reporting periods before ingestion and remain explicitly marked as period dates ([oklahoma_date_sources.csv](tables/oklahoma_date_sources.csv)).

13. 361 Eden records are supplier payments from the explicitly identified period files and are excluded from institutional card analyses ([eden_file_classification.csv](tables/eden_file_classification.csv)).

14. Oklahoma has MCC descriptions on 6,694,339 records (97.25% of all source records), but accepted description-to-code linkage on 4,981,642 (72.37%); linked codes are inferred and are not original numeric source codes ([label_coverage.csv](tables/label_coverage.csv)).

15. 1,588 Stockport supplier strings exactly match normalized MCC reference descriptions and are flagged as merchant-masked ([label_coverage.csv](tables/label_coverage.csv)).

16. 1,612 of 34,010 Stockport records with both dates (4.74%) have settlement before purchase ([stockport_period_checks.csv](tables/stockport_period_checks.csv)).

17. DWP has 8,015 observed positive amounts at least GBP 500 and no positive amounts below that threshold; negative adjustments require a separate interpretation ([amount_summary.csv](tables/amount_summary.csv)).

18. Indiana has 2,184 shared merchants with unequivocal issuer-era code majorities; 39 differ (1.79%) ([indiana_issuer_shift_summary.csv](tables/indiana_issuer_shift_summary.csv)).

19. For bristol_nature, 8,424 labeled card transactions meet merchant support N>=20; 43.64% occur at merchants with majority-label share >=0.9, with support coverage 70.40% ([purity_summary.csv](tables/purity_summary.csv)).

20. For bristol_sercop, 8,424 labeled card transactions meet merchant support N>=20; 95.54% occur at merchants with majority-label share >=0.9, with support coverage 70.40% ([purity_summary.csv](tables/purity_summary.csv)).

21. For solihull_proclass, 77,714 labeled card transactions meet merchant support N>=20; 26.25% occur at merchants with majority-label share >=0.9, with support coverage 80.56% ([purity_summary.csv](tables/purity_summary.csv)).

22. For oklahoma_proxy_k50, 2,845,345 labeled card transactions meet merchant support N>=20; 20.92% occur at merchants with majority-label share >=0.9, with support coverage 96.08% ([purity_summary.csv](tables/purity_summary.csv)).

23. For oklahoma_proxy_k200, 2,845,345 labeled card transactions meet merchant support N>=20; 18.94% occur at merchants with majority-label share >=0.9, with support coverage 96.08% ([purity_summary.csv](tables/purity_summary.csv)).

24. For moneydata_category, 3,124 labeled card transactions meet merchant support N>=20; 97.76% occur at merchants with majority-label share >=0.9, with support coverage 69.53% ([purity_summary.csv](tables/purity_summary.csv)).

25. 0 of 19 official MCC groups have fewer than 100 linked institutional-card transactions or fewer than 20 merchant keys ([coverage_by_group.csv](tables/coverage_by_group.csv)).

26. 497 source/normalized-MCC-description combinations require manual review before candidate codes can be treated as accepted labels ([mcc_needs_review.csv](tables/mcc_needs_review.csv)).
