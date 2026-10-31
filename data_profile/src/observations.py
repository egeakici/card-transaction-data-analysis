"""Full-data checks of the prompt's sample-derived observations."""
import polars as pl
from .common import DERIVED,collect,table,report


def run():
    scan=pl.scan_parquet(DERIVED/'analysis.parquet')
    rows=[]
    def add(sid,claim,status,numerator,denominator,evidence,explanation):
        rows.append({'source_id':sid,'claim':claim,'status':status,'numerator':numerator,'denominator':denominator,
                     'share':numerator/denominator if denominator else None,'evidence_table':evidence,'explanation':explanation})
    basics=collect(scan.group_by('source_id').agg(pl.len().alias('rows'),pl.col('merchant_raw').str.len_chars().max().alias('max_merchant_length'),(pl.col('merchant_raw').str.len_chars()==18).sum().alias('length18'),(pl.col('mcc_desc_raw').str.len_chars()==40).sum().alias('mcc_length40'),pl.col('mcc_desc_raw').str.len_chars().max().alias('max_mcc_length'),pl.col('mcc_desc_raw').str.contains(r'^\d{4}(?:\.0+)?$').sum().alias('numeric_descriptions'),(pl.col('mcc_code')!='').sum().alias('numeric_codes'),pl.col('address_redacted').sum().alias('address_rows')))
    lookup={r['source_id']:r for r in basics.to_dicts()}
    r=lookup['indiana'];add('indiana','Merchant Category Code contains descriptions rather than numeric codes','supported' if not r['numeric_descriptions'] else 'mixed',r['numeric_descriptions'],r['rows'],'label_coverage.csv','Count exact four-digit strings in the misleadingly named raw-description field; canonical numeric code is empty unless an actual numeric source field exists.')
    r=lookup['moneydata'];add('moneydata','All bank descriptors are at most 18 characters','supported' if r['max_merchant_length']<=18 else 'not_supported',r['length18'],r['rows'],'merchant_lengths.csv',f'Maximum observed descriptor length is {r["max_merchant_length"]}; heaping does not independently establish the bank formatting rule.')
    r=lookup['oklahoma'];add('oklahoma','MCC descriptions are truncated at 40 characters','partly_supported' if r['mcc_length40'] else 'not_supported',r['mcc_length40'],r['rows'],'mcc_desc_vocab.csv',f'Maximum observed raw MCC-description length is {r["max_mcc_length"]}; count at exactly forty is an indicator, not proof every value is truncated.')
    r=lookup['solihull'];add('solihull','No numeric MCC source column is available','supported' if r['numeric_codes']==0 else 'not_supported',r['numeric_codes'],r['rows'],'label_coverage.csv','ProClass and institutional purpose are distinct purchase-label systems, not MCC.')
    add('solihull','Address-like purpose values need masking','supported' if r['address_rows'] else 'not_observed',r['address_rows'],r['rows'],'transformation_impacts.csv','Pattern matches are masked before label persistence; original addresses are never shown.')
    r=lookup['bristol'];add('bristol','Source contains approximately four thousand rows','not_supported',r['rows'],4000,'reconciliation.csv','Full workbooks include all twelve transaction sheets, not just the initially sampled subset.')
    summary=collect(scan.filter((pl.col('source_id')=='indiana')&(pl.col('issuer')!='unknown')).group_by('issuer','fiscal_year').len())
    expected=summary.filter(((pl.col('issuer')=='JPMorgan')&pl.col('fiscal_year').str.contains('2022|2023|2024'))|((pl.col('issuer')=='US Bank')&pl.col('fiscal_year').str.contains('2025|2026|2027')) )['len'].sum()
    add('indiana','Issuer changes cleanly from JPMorgan FY2022-2024 to US Bank FY2025+','supported' if expected==summary['len'].sum() else 'not_supported',expected,summary['len'].sum(),'indiana_issuer_dates.csv','Check actual issuer/fiscal-year cells and overlapping date bounds; no causal issuer effect or single change date is assumed.')
    # Preserve outliers, but make their presence visible before interpreting bounds.
    outliers=collect(scan.filter((pl.col('txn_date')!='')&((pl.col('year')<'2000')|(pl.col('year')>'2026'))).group_by('source_id','source_file','schema_variant','date_raw','date_parse_method').len().rename({'len':'rows'}))
    table('date_outlier_candidates.csv',outliers)
    stock=collect(scan.filter(pl.col('source_id')=='stockport').group_by(pl.col('schema_variant').str.split('_').list.first().alias('scheme_family')).agg(pl.col('txn_date').filter(pl.col('txn_date')!='').min().alias('first_date'),pl.col('txn_date').max().alias('last_date'),pl.len().alias('rows')))
    table('stockport_observed_periods.csv',stock)
    first=stock['first_date'].min();add('stockport','Supplied older records start around 2017','not_supported' if first and first>'2019' else 'partly_supported',stock['rows'].sum(),stock['rows'].sum(),'stockport_observed_periods.csv',f'Earliest parsed supplied record is {first}; calendar-period scheme assignments are validated by row content, not assumed from a sample.')
    table('sample_observation_checks.csv',rows)
    body='\n'.join(f'- **{r["source_id"]} / {r["status"]}:** {r["claim"]}. {r["explanation"]} Evidence: `{r["evidence_table"]}`.' for r in rows)
    report('11_sample_claim_checks.md','S1-S7','Explicit full-data checks of sample-derived claims; deterministic source-field and date/length counts.','Supported here means consistent with the supplied extracts, not verified population metadata or a causal mechanism.',body)
