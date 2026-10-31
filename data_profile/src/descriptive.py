"""Amounts, dates, duplicates, organization concentration, and coverage."""
import json
from collections import Counter

import matplotlib.pyplot as plt
import numpy as np
import polars as pl

from .common import OUT,DERIVED,collect,table,report
from .plots import save,bar,heatmap
from .privacy import safe_text


def run():
    data=pl.scan_parquet(DERIVED/'analysis.parquet')
    amounts=collect(data.group_by('source_id','currency').agg(pl.len().alias('canonical_rows'),
        pl.col('amount').count().alias('nonmissing_amounts'),pl.col('amount').min().alias('minimum'),pl.col('amount').quantile(.25).alias('q25'),pl.col('amount').median().alias('median'),pl.col('amount').quantile(.75).alias('q75'),pl.col('amount').quantile(.95).alias('q95'),pl.col('amount').max().alias('maximum'),pl.col('is_negative').mean().alias('negative_share'),
        ((pl.col('amount')>0)&(pl.col('amount')<500)).sum().alias('positive_below_500'),(pl.col('amount')==500).sum().alias('exactly_500'),(pl.col('amount')>=500).sum().alias('at_least_500'))).sort('source_id')
    table('amount_summary.csv',amounts)
    time=collect(data.filter(pl.col('month')!='').group_by('source_id','month').len().rename({'len':'transactions'}).sort('source_id','month'))
    table('monthly_coverage.csv',time)
    date_quality=collect(data.group_by('source_id','date_semantics','date_parse_method','date_field').len().rename({'len':'rows'}))
    table('date_parse_quality.csv',date_quality)
    invalid_dates=collect(data.filter((pl.col('date_raw')!='')&(pl.col('txn_date')=='')).group_by('source_id','schema_variant').len().rename({'len':'rows'}))
    table('unparsed_date_counts.csv',invalid_dates)
    days=collect(data.filter(pl.col('txn_date')!='').group_by('source_id','year','month','txn_date').len().rename({'len':'transactions'}))
    heaping=days.group_by('source_id','year','month').agg(pl.col('transactions').sum().alias('month_transactions'),pl.col('transactions').max().alias('largest_date_transactions'),pl.len().alias('distinct_dates')).with_columns((pl.col('largest_date_transactions')/pl.col('month_transactions')).alias('largest_date_share'))
    table('date_concentration_monthly.csv',heaping)
    yearly=heaping.group_by('source_id','year').agg(pl.col('month_transactions').sum().alias('transactions'),(pl.col('largest_date_transactions').sum()/pl.col('month_transactions').sum()).alias('weighted_largest_date_share'),pl.col('largest_date_share').max().alias('maximum_month_single_date_share'),pl.len().alias('observed_months'))
    table('date_concentration_yearly.csv',yearly)
    fiscal=collect(data.filter((pl.col('source_id')=='delaware')&(pl.col('txn_date')!='')).with_columns(
        pl.col('year').cast(pl.Int32,strict=False).alias('calendar_year'),pl.col('txn_date').str.slice(5,2).cast(pl.Int32).alias('calendar_month'),
        pl.col('fiscal_year').str.extract(r'(\d{4})',1).cast(pl.Int32,strict=False).alias('fy'),pl.col('fiscal_period').cast(pl.Int32,strict=False).alias('fp')
    ).with_columns((pl.col('calendar_year')+(pl.col('calendar_month')>=7).cast(pl.Int32)).alias('expected_fy'),(((pl.col('calendar_month')-7)%12)+1).alias('expected_fp')).group_by('fiscal_year','fiscal_period').agg(pl.len().alias('rows'),(pl.col('fy')==pl.col('expected_fy')).sum().alias('july_year_matches'),(pl.col('fp')==pl.col('expected_fp')).sum().alias('july_period_matches')))
    table('delaware_fiscal_calendar_check.csv',fiscal)
    duplicates=collect(data.group_by('source_id','raw_row_hash').len().filter(pl.col('len')>1).group_by('source_id').agg(pl.len().alias('duplicate_groups'),(pl.col('len')-1).sum().alias('duplicate_excess_rows')))
    table('exact_duplicates.csv',duplicates)
    id_duplicates=collect(data.filter(pl.col('transaction_id')!='').group_by('source_id','transaction_id').len().filter(pl.col('len')>1).group_by('source_id').agg(pl.len().alias('repeated_ids'),(pl.col('len')-1).sum().alias('repeated_id_excess_rows')))
    table('transaction_id_duplicates.csv',id_duplicates)
    # Complete zero rows distinguish no duplicates from an unavailable ID field.
    duplicate_summary=collect(data.group_by('source_id').agg(pl.len().alias('canonical_rows'),(pl.col('transaction_id')!='').sum().alias('rows_with_transaction_id'))).join(duplicates,on='source_id',how='left').join(id_duplicates,on='source_id',how='left').with_columns(pl.col('duplicate_groups','duplicate_excess_rows','repeated_ids','repeated_id_excess_rows').fill_null(0))
    table('duplicate_summary.csv',duplicate_summary)
    org=collect(data.filter(pl.col('org_unit')!='').group_by('source_id','org_unit').len().rename({'len':'transactions'})).with_columns((pl.col('transactions')/pl.col('transactions').sum().over('source_id')).alias('share')).sort(['source_id','transactions'],descending=[False,True])
    table('organization_top10.csv',org.group_by('source_id',maintain_order=True).head(10).with_columns(pl.col('org_unit').map_elements(safe_text,return_dtype=pl.String)))
    orgsummary=org.group_by('source_id',maintain_order=True).head(10).group_by('source_id').agg(pl.col('transactions').sum().alias('top10_transactions'),pl.col('share').sum().alias('top10_share'))
    table('organization_concentration.csv',orgsummary)
    records=collect(data.group_by('source_id','record_type').len().rename({'len':'transactions'}).with_columns((pl.col('transactions')/pl.col('transactions').sum().over('source_id')).alias('share')))
    table('record_types.csv',records)
    table('moneydata_transaction_types.csv',collect(data.filter(pl.col('source_id')=='moneydata').group_by('transaction_type','record_type').len().rename({'len':'transactions'})))
    stockport=collect(data.filter(pl.col('source_id')=='stockport').group_by('schema_variant','year').agg(pl.len().alias('rows'),((pl.col('posting_date')!='')&(pl.col('txn_date')!='')).sum().alias('both_dates'),((pl.col('posting_date')!='')&(pl.col('txn_date')!='')&(pl.col('posting_date')<pl.col('txn_date'))).sum().alias('settlement_before_purchase'),pl.col('merchant_masked').sum().alias('merchant_masked_rows')))
    table('stockport_period_checks.csv',stockport)
    eden=collect(data.filter(pl.col('source_id')=='eden').group_by('upstream_source_file','record_type').agg(pl.len().alias('rows'),pl.col('redacted_information').sum().alias('redacted_information_rows')))
    table('eden_file_classification.csv',eden)
    # Explicit month-of-year distribution makes the downloaded Oklahoma sample
    # concentration visible instead of assuming continuous year-round coverage.
    oklahoma=collect(data.filter(pl.col('source_id')=='oklahoma').with_columns(pl.col('txn_date').str.slice(5,2).alias('calendar_month')).group_by('year','calendar_month').len().rename({'len':'transactions'}).with_columns((pl.col('transactions')/pl.col('transactions').sum().over('year')).alias('within_year_share')))
    table('oklahoma_month_distribution.csv',oklahoma)
    monthall=oklahoma.group_by('calendar_month').agg(pl.col('transactions').sum()).with_columns((pl.col('transactions')/pl.col('transactions').sum()).alias('share'))
    table('oklahoma_month_totals.csv',monthall)
    # Possible sequential-code errors: candidates only, preserving row order.
    adjacent=collect(data.filter((pl.col('source_id')=='eden')&(pl.col('mcc_code')!='')).sort('source_file','source_row').with_columns(pl.col('mcc_code').cast(pl.Int32,strict=False).alias('numeric')).with_columns(pl.col('numeric').shift(1).alias('previous_code'),pl.col('key_loose').shift(1).alias('previous_key'),pl.col('upstream_source_file').shift(1).alias('previous_upstream')).filter((pl.col('key_loose')==pl.col('previous_key'))&(pl.col('upstream_source_file')==pl.col('previous_upstream'))&((pl.col('numeric')-pl.col('previous_code')).abs()==1)).select('source_file','source_row','upstream_source_file','mcc_code','previous_code'))
    table('eden_adjacent_code_candidates.csv',adjacent)
    cards=data.filter((pl.col('record_type')=='card_txn')&(pl.col('org_type')!='academic')&(pl.col('source_id')!='ipo'))
    coverage=collect(cards.filter((pl.col('mcc_group')!='unknown')&~pl.col('merchant_masked')&(pl.col('key_loose')!='')).group_by('mcc_group').agg(pl.len().alias('transactions'),pl.col('key_loose').n_unique().alias('merchants')))
    ref=pl.read_csv(OUT/'reference/mcc_official.csv',infer_schema=False)
    allgroups=pl.DataFrame({'mcc_group':sorted(set(ref['mcc_group'])-{'unknown'})})
    coverage=allgroups.join(coverage,on='mcc_group',how='left').with_columns(pl.col('transactions','merchants').fill_null(0)).with_columns(((pl.col('transactions')<100)|(pl.col('merchants')<20)).alias('weakly_represented'),(pl.col('transactions')==0).alias('unobserved'))
    table('coverage_by_group.csv',coverage)
    country_distribution=collect(cards.group_by('country','mcc_group').len().rename({'len':'transactions'}).with_columns((pl.col('transactions')/pl.col('transactions').sum().over('country')).alias('share')))
    table('mcc_group_by_country.csv',country_distribution)
    from scipy.spatial.distance import jensenshannon
    group_names=sorted(set(country_distribution['mcc_group'])-{'unknown'});country_js=[]
    countries=sorted(country_distribution['country'].unique())
    from itertools import combinations
    for a,b in combinations(countries,2):
        da=dict(country_distribution.filter(pl.col('country')==a).select('mcc_group','transactions').iter_rows());db=dict(country_distribution.filter(pl.col('country')==b).select('mcc_group','transactions').iter_rows())
        country_js.append({'country_a':a,'country_b':b,'js_divergence_bits':float(jensenshannon([da.get(g,0) for g in group_names],[db.get(g,0) for g in group_names],base=2)**2),'interpretation':'transaction_weighted_supplied_extracts_conditioned_on_known_groups'})
    table('country_mcc_group_js_divergence.csv',country_js)
    restricted=collect(cards.filter(pl.col('mcc_analysis').is_in(['6010','6011','7995'])).group_by('source_id','mcc_analysis').len().rename({'len':'transactions'}))
    table('policy_sensitive_codes.csv',restricted)
    restricted_full=pl.DataFrame({'mcc_code':['6010','6011','7995']}).join(restricted.group_by('mcc_analysis').agg(pl.col('transactions').sum()),left_on='mcc_code',right_on='mcc_analysis',how='left').with_columns(pl.col('transactions').fill_null(0))
    table('policy_sensitive_code_totals.csv',restricted_full)
    consumer_groups=['Airlines','Car Rental','Lodging','Clothing Stores','Retail Stores','Miscellaneous Stores','Personal Service Providers','Transportation']
    b2b_groups=['Wholesale Distributors and Manufacturers']
    orientation=collect(cards.with_columns(pl.when(pl.col('mcc_group').is_in(b2b_groups)).then(pl.lit('B2B-oriented'))
        .when(pl.col('mcc_group').is_in(consumer_groups)).then(pl.lit('consumer-adjacent'))
        .otherwise(pl.lit('mixed_or_unknown')).alias('orientation')).group_by('source_id','orientation').len().rename({'len':'transactions'}).with_columns((pl.col('transactions')/pl.col('transactions').sum().over('source_id')).alias('share')))
    table('consumer_b2b_orientation.csv',orientation)
    # Figures: aggregate counts only, never expose personal values.
    fig,ax=plt.subplots(figsize=(9,5))
    bins=np.linspace(-3,6,100);histograms=[]
    for sid in sorted(amounts['source_id'].unique()):
        df=collect(data.filter((pl.col('source_id')==sid)&(pl.col('amount')>0)).select('amount'))
        hist,edges=np.histogram(np.log10(df['amount'].to_numpy()),bins=bins)
        ax.plot((edges[:-1]+edges[1:])/2,hist/max(1,hist.sum()),label=sid)
    ax.set(xlabel='log10 positive transaction amount (native currency)',ylabel='Share of positive amounts',title='Amount distributions; currencies are not pooled');ax.legend(fontsize=6,ncol=2);save(fig,'amount_distribution')
    # Annual calendar-month heatmap retains seasonality without an unreadable
    # 150-column monthly time axis. Exact missing calendar months remain CSV.
    heat=collect(data.filter(pl.col('txn_date')!='').with_columns(pl.col('txn_date').str.slice(5,2).alias('calendar_month')).group_by('source_id','calendar_month').len())
    ss=sorted(heat['source_id'].unique());mm=[f'{x:02d}' for x in range(1,13)]
    lookup={(r['source_id'],r['calendar_month']):r['len'] for r in heat.to_dicts()}
    array=np.array([[lookup.get((s,m),0) for m in mm] for s in ss],float);array/=np.maximum(array.sum(axis=1,keepdims=True),1)
    heatmap(array,ss,mm,'Observed calendar-month concentration','calendar_month_heatmap','Within-source share',0,None)
    # A genuine source-by-calendar-month timeline shows gaps across years;
    # the separate month-of-year figure above diagnoses seasonality.
    from matplotlib.colors import LogNorm
    timeline=time.filter(pl.col('month')>='2000-01')
    earliest=timeline['month'].min();latest=timeline['month'].max()
    ey,em=map(int,earliest.split('-'));ly,lm=map(int,latest.split('-'))
    month_keys=[f'{index//12:04d}-{index%12+1:02d}' for index in range(ey*12+em-1,ly*12+lm)]
    source_names=sorted(timeline['source_id'].unique())
    lookup={(r['source_id'],r['month']):r['transactions'] for r in timeline.to_dicts()}
    values=np.array([[lookup.get((s,m),0) for m in month_keys] for s in source_names],float)
    masked=np.ma.masked_where(values==0,values)
    fig,ax=plt.subplots(figsize=(14,5))
    image=ax.imshow(masked,aspect='auto',cmap='viridis',norm=LogNorm(vmin=1,vmax=values.max()))
    ticks=[i for i,m in enumerate(month_keys) if m.endswith('-01')]
    ax.set(yticks=range(len(source_names)),yticklabels=source_names,xticks=ticks,xticklabels=[month_keys[i][:4] for i in ticks],xlabel='Calendar month (annual tick marks)',title='Monthly coverage of supplied extracts; blank cells mean no observed records')
    ax.tick_params(axis='x',rotation=45);fig.colorbar(image,ax=ax,label='Transactions (log scale)',shrink=.8)
    save(fig,'monthly_coverage_timeline')
    bar(coverage.sort('transactions',descending=True)['transactions'].to_list(),coverage.sort('transactions',descending=True)['mcc_group'].to_list(),'Institutional-card coverage by official MCC group','coverage_by_group','Card transactions',log=True)
    total500=amounts.filter(pl.col('source_id').is_in(['dwp','ipo']))
    report('07_amount_time_org.md','S6, S7','Full-source quantiles (Polars default nearest interpolation), negative-amount rates, monthly/date concentration, duplicate fingerprints, IDs, organization shares and source-specific calendar checks.','No currency conversion; source publication thresholds and download windows are selection mechanisms. Amount negative rates use all canonical records as denominator. MoneyData debits are represented as negative and credits as positive: its negative-share statistic denotes outflows, not a refund rate, and must not be compared as a like-for-like refund measure with public spending files. Negative public-source amounts can be reversals/refunds but their meanings are not individually verified. Oklahoma exact-row duplicates exclude the three personal columns; all other raw fields, including transaction IDs and upstream provenance, remain in the fingerprint. Duplicate IDs need not be duplicate transactions.',f'''All amounts remain in native currency. `amount_summary.csv` directly tests the proposed GBP 500 publication lower bound, instead of assuming it. `date_concentration_yearly.csv` quantifies date heaping; heaping alone does not identify statement dates. `delaware_fiscal_calendar_check.csv` tests the July fiscal-calendar claim against actual parsed dates.

Oklahoma calendar-month shares are in `oklahoma_month_totals.csv` and `oklahoma_month_distribution.csv`. Equal-sized original file extracts and sparse month coverage must not be interpreted as annual census sampling. Stockport chronology and label-period assumptions are tested in `stockport_period_checks.csv`; Eden file classifications and adjacent-code candidates are explicit tables. Records are never deduplicated or rewritten.

`figures/monthly_coverage_timeline.pdf` shows every calendar month, with no-record cells blank and logarithmic record counts. The seasonal month-of-year heatmap is a separate figure. Pre-2000 date outliers remain in the tables and are excluded only from the displayed timeline so they do not compress the observed modern download windows into unreadable cells.
''')
    report('09_coverage.md','S7','Institutional card_txn records, linked official groups, unique loose merchant keys, explicit weak-coverage thresholds and sensitive-code checks.','Coverage is conditional on accepted MCC linkage and uncertain merchant resolution. Academic MoneyData and IPO are excluded from institutional-card coverage. Observed absence cannot establish an institutional prohibition. Consumer/B2B orientation is an analyst-defined descriptive grouping, not a network taxonomy or observed purchaser identity.',f'''The official reference supplies {coverage.height:,} upper groups. Under the requested rule (<100 transactions OR <20 merchant keys), {coverage.filter(pl.col('weakly_represented')).height:,} groups are weakly represented and {coverage.filter(pl.col('unobserved')).height:,} have no observed linked institutional-card transactions (`coverage_by_group.csv`).

Codes 6010, 6011 and 7995 are checked explicitly in `policy_sensitive_code_totals.csv`, including zero totals. Classification into B2B-oriented uses only Wholesale Distributors and Manufacturers; consumer-adjacent uses the published groups {', '.join(consumer_groups)}. All other categories remain mixed_or_unknown. This coarse orientation rule is separate from MCC reference linkage and does not create a task-specific spending taxonomy.
''')
