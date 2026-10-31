"""Effective sample sizes, evidence sparsity, and cross-source overlap."""
from collections import defaultdict
from itertools import combinations
import json

import matplotlib.pyplot as plt
import numpy as np
import polars as pl

from .common import OUT,DERIVED,collect,table,report,public_merchant_id,json_save
from .privacy import safe_merchant
from .plots import save,heatmap,bar


def run():
    scan=pl.scan_parquet(DERIVED/'analysis.parquet')
    base=scan.filter((pl.col('merchant_raw')!='')&~pl.col('merchant_masked'))
    summary=collect(base.group_by('source_id').agg(pl.len().alias('rows_with_merchant'),
        pl.col('merchant_raw').n_unique().alias('unique_raw'),pl.col('key_strict').filter(pl.col('key_strict')!='').n_unique().alias('unique_strict'),
        pl.col('key_loose').filter(pl.col('key_loose')!='').n_unique().alias('unique_loose'),
        pl.col('merchant_raw').str.len_chars().mean().alias('mean_characters'),
        (pl.col('merchant_raw').str.len_chars()<5).mean().alias('under5_share'),
        pl.col('merchant_raw').str.contains(r'\d').mean().alias('has_digit_share'),
        ((pl.col('merchant_raw')==pl.col('merchant_raw').str.to_uppercase())&pl.col('merchant_raw').str.contains(r'[A-Za-z]')).mean().alias('uppercase_share'),
        (pl.col('intermediary')!='').mean().alias('intermediary_share'),
        pl.col('merchant_raw').str.to_uppercase().str.contains(r'WWW\.|\.COM|\.CO\.UK|MKTP|MKTPLACE|ONLINE|ECOM').mean().alias('online_indicator_share'),
        pl.col('record_type').is_in(['adjustment','fee','transfer','cash']).mean().alias('nonmerchant_pattern_share')
    )).sort('source_id').with_columns((pl.col('unique_raw')/pl.col('rows_with_merchant')).alias('raw_per_row'),(pl.col('unique_strict')/pl.col('rows_with_merchant')).alias('strict_per_row'),(pl.col('unique_loose')/pl.col('rows_with_merchant')).alias('loose_per_row'))
    table('merchant_summary.csv',summary)
    frequencies=collect(base.filter(pl.col('key_loose')!='').group_by('source_id','country','key_loose').len().rename({'len':'transactions'}).sort(['source_id','transactions','key_loose'],descending=[False,True,False]))
    frequencies.write_parquet(DERIVED/'merchant_frequencies.parquet')
    sets={};top=[];concentration=[];singletons=[];curves=[]
    for (sid,),df in frequencies.group_by('source_id',maintain_order=True):
        df=df.sort(['transactions','key_loose'],descending=[True,False]);n=df['transactions'].sum();counts=df['transactions'].to_numpy();sets[sid]=set(df['key_loose'])
        for rank,row in enumerate(df.head(50).to_dicts(),1):
            top.append({'source_id':sid,'rank':rank,'merchant_id':public_merchant_id(row['key_loose']),'key_display':safe_merchant(row['key_loose'],row['transactions']),'transactions':row['transactions'],'share':row['transactions']/n})
        for k in [10,100,1000,10000]:
            concentration.append({'source_id':sid,'k':k,'actual_keys':min(k,len(counts)),'transaction_share':float(counts[:k].sum()/n)})
        singletons.append({'source_id':sid,'keys':len(counts),'singleton_keys':int(np.sum(counts==1)),'singleton_key_share':float(np.mean(counts==1)),'singleton_transaction_share':float(np.sum(counts==1)/n)})
        for rank in np.unique(np.geomspace(1,len(counts),min(200,len(counts))).astype(int)):
            curves.append({'source_id':sid,'rank':int(rank),'count':int(counts[rank-1]),'cumulative_share':float(counts[:rank].sum()/n)})
    table('merchant_top50.csv',top);table('merchant_concentration.csv',concentration);table('merchant_singletons.csv',singletons);table('merchant_zipf.csv',curves)
    lengths=collect(base.with_columns(pl.col('merchant_raw').str.len_chars().alias('length'),pl.col('merchant_raw').str.count_matches(r'\S+').alias('tokens')).group_by('source_id','length','tokens').len().rename({'len':'transactions'}))
    table('merchant_lengths.csv',lengths)
    truncation=[]
    for sid in sorted(sets):
        df=lengths.filter(pl.col('source_id')==sid);counts=dict(df.group_by('length').agg(pl.col('transactions').sum()).iter_rows());total=sum(counts.values())
        for boundary in [18,22,25,40]:
            exact=counts.get(boundary,0);neighbors=np.mean([counts.get(boundary-1,0),counts.get(boundary+1,0)])
            truncation.append({'source_id':sid,'boundary':boundary,'exact_rows':exact,'exact_share':exact/total,'neighbor_mean':float(neighbors),'spike_ratio':exact/neighbors if neighbors else None,'interpretation':'heaping_indicator_not_proof_of_truncation'})
    table('truncation_indicators.csv',truncation)
    prefixes=collect(base.filter(pl.col('intermediary')!='').group_by('source_id','intermediary').len().rename({'len':'transactions'}));table('intermediary_prefixes.csv',prefixes)
    overlaps=[];sources=sorted(sets);matrix=np.zeros((len(sources),len(sources)))
    for i,a in enumerate(sources):
        for j,b in enumerate(sources):
            shared=sets[a]&sets[b];union=sets[a]|sets[b];value=len(shared)/len(union) if union else 0
            matrix[i,j]=value
            overlaps.append({'source_a':a,'source_b':b,'shared_merchants':len(shared),'jaccard':value,'test_covered_by_train_share':len(shared)/len(sets[b]) if sets[b] else 0})
    table('merchant_overlap.csv',overlaps)
    key_sources=defaultdict(set)
    for sid,keys in sets.items():
        for key in keys:key_sources[key].add(sid)
    table('shared_merchant_summary.csv',[{'keys_in_two_or_more_sources':sum(len(v)>=2 for v in key_sources.values()),'keys_in_all_sources':sum(len(v)==len(sources) for v in key_sources.values())}])
    cross=[]
    for (key,),df in frequencies.group_by('key_loose'):
        if len(set(df['country']))>1:
            total=df['transactions'].sum();cross.append({'merchant_id':public_merchant_id(key),'key_display':safe_merchant(key,total),'transactions':total,'source_count':df['source_id'].n_unique()})
    table('us_uk_shared_top100.csv',sorted(cross,key=lambda r:-r['transactions'])[:100])
    heatmap(matrix,sources,sources,'Merchant overlap by source','merchant_jaccard','Jaccard similarity',0,1)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for sid in sources:
        rows=[r for r in curves if r['source_id']==sid]
        axes[0].loglog([r['rank'] for r in rows],[r['count'] for r in rows],label=sid)
        axes[1].semilogx([r['rank'] for r in rows],[r['cumulative_share'] for r in rows],label=sid)
    axes[0].set(xlabel='Merchant rank',ylabel='Transactions',title='Merchant frequency (Zipf view)')
    axes[1].set(xlabel='Top k merchants',ylabel='Cumulative transaction share',title='Concentration');axes[1].legend(fontsize=6,ncol=2)
    save(fig,'merchant_frequency_concentration')
    fig,ax=plt.subplots(figsize=(9,5))
    for sid in sources:
        rows=lengths.filter(pl.col('source_id')==sid).group_by('length').agg(pl.col('transactions').sum()).sort('length')
        xx=rows['length'].to_numpy();yy=rows['transactions'].to_numpy();mask=xx<=70
        ax.plot(xx[mask],yy[mask]/yy.sum(),label=sid,alpha=.8)
    for x in [18,22,25,40]:ax.axvline(x,color='gray',lw=.6,ls='--')
    ax.set(xlabel='Merchant string length (characters)',ylabel='Transaction share',title='Descriptor length and candidate truncation boundaries');ax.legend(fontsize=6,ncol=2);save(fig,'merchant_length_heaping')
    bar(summary['unique_loose'].to_list(),summary['source_id'].to_list(),'Effective sample size: normalized merchant keys','effective_sample_size','Unique loose keys',log=True)
    rows='\n'.join(f'| {r["source_id"]} | {r["rows_with_merchant"]:,} | {r["unique_raw"]:,} | {r["unique_strict"]:,} | {r["unique_loose"]:,} | {r["intermediary_share"]:.2%} |' for r in summary.to_dicts())
    report('03_merchant_strings.md','S1, S3','Two deterministic merchant keys, explicit intermediary separation, frequency concentration, length/token histograms, and set-based source overlap.','Normalized keys approximate merchants, not verified legal entities. Alias merging and location removal can merge distinct merchants; strict-key sensitivity counts are retained. Length spikes indicate possible truncation, not a verified bank-format limit. Rare merchant strings are suppressed from public examples.',f'''| Source | Merchant-bearing rows | Raw strings | Strict keys | Loose keys | Intermediary share |
| --- | ---: | ---: | ---: | ---: | ---: |
{rows}

All records are retained in the inventory. These string metrics exclude empty merchants and exact reference-description-masked Stockport strings. Card-only sensitivity metrics are provided separately by record type in the descriptive analysis. Top keys and cross-country overlaps use stable opaque merchant IDs; displayed examples require support >=20 and an identifier/address guard. Counts of empty normalized keys and all aliases are documented in decisions. See `merchant_concentration.csv`, `merchant_singletons.csv`, `merchant_lengths.csv`, `truncation_indicators.csv`, and `merchant_overlap.csv`.
''')
