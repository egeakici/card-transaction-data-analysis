# Key findings

All statements below are generated from full-source computed tables. Purity is empirical within-merchant label concentration, not measured prediction accuracy. Scheme denominators overlap and must not be summed.

1. The study contains 3,862,562 canonical records from 11 sources, reconciled against 3,873,387 reader records with 10,825 reason-coded exclusions ([reconciliation.csv](tables/reconciliation.csv)).

2. The supplied Bristol workbooks contain 12,205 transaction rows, rather than the sample-based approximate count ([reconciliation.csv](tables/reconciliation.csv)).

3. The MoneyData workbook contributes 6,567 canonical transactions; its blank worksheet extents and documentation are excluded ([reconciliation.csv](tables/reconciliation.csv)).

4. Delaware has 2,251,316 merchant-bearing rows but 106,177 loose merchant keys (4.72% keys per row) ([merchant_summary.csv](tables/merchant_summary.csv)).

5. Oklahoma has 900,000 merchant-bearing rows but 63,925 loose merchant keys (7.10% keys per row) ([merchant_summary.csv](tables/merchant_summary.csv)).

6. Sunderland has 255,078 merchant-bearing rows but 3,775 loose merchant keys (1.48% keys per row) ([merchant_summary.csv](tables/merchant_summary.csv)).

7. 801,007 of 900,000 dated Oklahoma records (89.00%) occur in May or June ([oklahoma_month_totals.csv](tables/oklahoma_month_totals.csv)).

8. All 18 Oklahoma input extracts have exactly 50,000 rows, a potential extract-cap diagnostic rather than evidence of download completeness ([reconciliation.csv](tables/reconciliation.csv)).

9. 361 Eden records are supplier payments from the explicitly identified period files and are excluded from institutional card analyses ([eden_file_classification.csv](tables/eden_file_classification.csv)).

10. 1,588 Stockport supplier strings exactly match normalized MCC reference descriptions and are flagged as merchant-masked ([label_coverage.csv](tables/label_coverage.csv)).

11. 1,612 of 34,010 Stockport records with both dates (4.74%) have settlement before purchase ([stockport_period_checks.csv](tables/stockport_period_checks.csv)).

12. DWP has 8,015 observed positive amounts at least GBP 500 and no positive amounts below that threshold; negative adjustments require a separate interpretation ([amount_summary.csv](tables/amount_summary.csv)).

13. Indiana has 2,184 shared merchants with unequivocal issuer-era code majorities; 39 differ (1.79%) ([indiana_issuer_shift_summary.csv](tables/indiana_issuer_shift_summary.csv)).

14. For bristol_nature, 8,424 labeled card transactions meet merchant support N>=20; 43.64% occur at merchants with majority-label share >=0.9, with support coverage 70.40% ([purity_summary.csv](tables/purity_summary.csv)).

15. For bristol_sercop, 8,424 labeled card transactions meet merchant support N>=20; 95.54% occur at merchants with majority-label share >=0.9, with support coverage 70.40% ([purity_summary.csv](tables/purity_summary.csv)).

16. For solihull_proclass, 77,714 labeled card transactions meet merchant support N>=20; 26.25% occur at merchants with majority-label share >=0.9, with support coverage 80.56% ([purity_summary.csv](tables/purity_summary.csv)).

17. For oklahoma_proxy_k50, 359,676 labeled card transactions meet merchant support N>=20; 17.99% occur at merchants with majority-label share >=0.9, with support coverage 90.98% ([purity_summary.csv](tables/purity_summary.csv)).

18. For oklahoma_proxy_k200, 359,676 labeled card transactions meet merchant support N>=20; 17.25% occur at merchants with majority-label share >=0.9, with support coverage 90.98% ([purity_summary.csv](tables/purity_summary.csv)).

19. For moneydata_category, 3,124 labeled card transactions meet merchant support N>=20; 97.76% occur at merchants with majority-label share >=0.9, with support coverage 69.53% ([purity_summary.csv](tables/purity_summary.csv)).

20. 0 of 19 official MCC groups have fewer than 100 linked institutional-card transactions or fewer than 20 merchant keys ([coverage_by_group.csv](tables/coverage_by_group.csv)).

21. 469 source/normalized-MCC-description combinations require manual review before candidate codes can be treated as accepted labels ([mcc_needs_review.csv](tables/mcc_needs_review.csv)).
