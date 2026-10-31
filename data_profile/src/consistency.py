"""Observed and linked label distributions, shifts, and consistency inputs."""
from collections import defaultdict
from itertools import combinations
import math

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from scipy.spatial.distance import jensenshannon

from .common import OUT,DERIVED,collect,table,report,entropy,public_merchant_id
from .privacy import safe_merchant
from .plots import save,heatmap,bar


def gini(counts):
    a=np.sort(np.asarray(counts,dtype=float))
    return float(2*np.sum(np.arange(1,len(a)+1)*a)/(len(a)*a.sum())-(len(a)+1)/len(a)) if len(a) and a.sum() else 0.


def majority_table(counts,label):
    rows=[]
    for (sid,key),df in counts.group_by('source_id','key_loose'):
        df=df.sort(['transactions',label],descending=[True,False]);total=df['transactions'].sum();maximum=df['transactions'].max()
        rows.append({'source_id':sid,'key_loose':key,'transactions':total,'unique_labels':df.height,'majority_label':df[label][0],
                     'majority_share':maximum/total,'majority_tied':df.filter(pl.col('transactions')==maximum).height>1,
                     'entropy_bits':entropy(df['transactions'].to_list())})
    return pl.DataFrame(rows,infer_schema_length=None)


def run():
    scan=pl.scan_parquet(DERIVED/'analysis.parquet')
    card=scan.filter(pl.col('record_type')=='card_txn')
    labeled=card.filter((pl.col('mcc_analysis')!='')&~pl.col('merchant_masked')&(pl.col('key_loose')!=''))
    distributions={};summaries=[]
    for label in ['mcc_analysis','mcc_group']:
        df=collect(card.filter(pl.col(label)!='').group_by('source_id',label).len().rename({'len':'transactions'}))
        df=df.with_columns((pl.col('transactions')/pl.col('transactions').sum().over('source_id')).alias('share')).sort(['source_id','transactions',label],descending=[False,True,False])
        table('mcc_code_distribution.csv' if label=='mcc_analysis' else 'mcc_group_distribution.csv',df)
        for (sid,),part in df.group_by('source_id'):
            summaries.append({'source_id':sid,'level':label,'labeled_transactions':part['transactions'].sum(),'unique_labels':part.height,'shannon_bits':entropy(part['transactions'].to_list()),'gini_observed_categories':gini(part['transactions'].to_list())})
        distributions[label]=df
    table('label_distribution_summary.csv',summaries)
    table('mcc_top30.csv',distributions['mcc_analysis'].filter(pl.col('mcc_analysis')!='').group_by('source_id',maintain_order=True).head(30))
    group=distributions['mcc_group'].filter(pl.col('mcc_group')!='unknown');sources=sorted(group['source_id'].unique());groups=sorted(group['mcc_group'].unique());vectors={}
    for sid in sources:
        counts=dict(group.filter(pl.col('source_id')==sid).select('mcc_group','transactions').iter_rows());vectors[sid]=np.array([counts.get(g,0) for g in groups],dtype=float)
    js=[];matrix=np.zeros((len(sources),len(sources)))
    for i,a in enumerate(sources):
        for j,b in enumerate(sources):
            value=float(jensenshannon(vectors[a],vectors[b],base=2)**2)
            js.append({'source_a':a,'source_b':b,'js_divergence_bits':value});matrix[i,j]=value
    table('mcc_group_js_divergence.csv',js)
    heatmap(matrix,sources,sources,'MCC-group distribution differences','mcc_group_js_divergence','Jensen-Shannon divergence (bits)',0,1)
    years=collect(card.filter(pl.col('source_id').is_in(['delaware','oklahoma','indiana'])&(pl.col('year')!='')).group_by('source_id','year','mcc_group').len().rename({'len':'transactions'}).with_columns((pl.col('transactions')/pl.col('transactions').sum().over('source_id','year')).alias('share')))
    table('mcc_group_by_year.csv',years)
    vocab_year=collect(card.filter(pl.col('mcc_desc_raw')!='').group_by('source_id','year').agg(pl.col('mcc_desc_raw').n_unique().alias('raw_vocab'),pl.col('mcc_desc_norm').n_unique().alias('normalized_vocab'),(pl.col('mcc_desc_raw')==pl.col('mcc_desc_raw').str.to_uppercase()).mean().alias('uppercase_description_share')))
    table('mcc_vocab_by_year.csv',vocab_year)
    raw_consistency=collect(card.filter((pl.col('mcc_desc_norm')!='')&(pl.col('key_loose')!='')).group_by('source_id','key_loose','mcc_desc_norm').len().rename({'len':'transactions'}))
    raw_maj=majority_table(raw_consistency,'mcc_desc_norm')
    raw_maj.select(pl.exclude('key_loose'),pl.col('key_loose').map_elements(public_merchant_id,return_dtype=pl.String).alias('merchant_id')).write_csv(OUT/'tables/raw_description_consistency.csv')

    for level in ['mcc_analysis','mcc_generic','mcc_group']:
        counts=collect(labeled.group_by('source_id','key_loose',level).len().rename({'len':'transactions'}))
        counts.write_parquet(DERIVED/f'merchant_{level}_counts.parquet')
        majority=majority_table(counts,level);majority.write_parquet(DERIVED/f'majority_{level}.parquet')
        public=majority.with_columns(pl.col('key_loose').map_elements(public_merchant_id,return_dtype=pl.String).alias('merchant_id')).drop('key_loose')
        table(f'merchant_consistency_{level}.csv',public)
        summary=majority.group_by('source_id').agg(pl.len().alias('merchants'),pl.col('transactions').sum().alias('labeled_transactions'),pl.col('transactions').filter(pl.col('unique_labels')==1).sum().alias('transactions_at_single_label_merchants'),(pl.col('unique_labels')>1).sum().alias('multilabel_merchants')).with_columns((pl.col('transactions_at_single_label_merchants')/pl.col('labeled_transactions')).alias('single_label_transaction_share'))
        table(f'consistency_summary_{level}.csv',summary)
        candidates=majority.filter(pl.col('transactions')>=20).sort(['majority_share','transactions'],descending=[False,True]).head(50)
        candidate_rows=[]
        for row in candidates.to_dicts():
            key=row.pop('key_loose');sid=row['source_id'];labels=set(counts.filter((pl.col('source_id')==sid)&(pl.col('key_loose')==key))[level])
            numeric=sorted(int(c) for c in labels if str(c).isdigit())
            if any(3000<=c<=3999 for c in numeric) and any(c in [4511,7011,7512] for c in numeric):kind='brand_generic_candidate'
            elif any(abs(a-b)<=1 or {a,b}=={5399,5999} for a,b in combinations(numeric,2)):kind='neighbor_code_candidate'
            else:kind='other_candidate'
            candidate_rows.append({**row,'merchant_id':public_merchant_id(key),'key_display':safe_merchant(key,row['transactions']),'candidate_type':kind,'labels':'|'.join(sorted(labels))})
        table(f'inconsistent_top50_{level}.csv',candidate_rows)
        # Unequivocal source majorities only; tied majority assignments are not
        # made to appear more consistent by choosing one arbitrarily.
        cross=[]
        majors={sid:{r['key_loose']:r for r in majority.filter((pl.col('source_id')==sid)&~pl.col('majority_tied')).to_dicts()} for sid in majority['source_id'].unique()}
        for a,b in combinations(sorted(majors),2):
            shared=set(majors[a])&set(majors[b]);agree=sum(majors[a][k]['majority_label']==majors[b][k]['majority_label'] for k in shared)
            cross.append({'source_a':a,'source_b':b,'shared_unequivocal_merchants':len(shared),'agreeing_merchants':agree,'agreement_share':agree/len(shared) if shared else None})
        table(f'cross_source_agreement_{level}.csv',cross)

    # Primary consistency sensitivity: ORIGINAL numeric codes only.
    original=collect(card.filter((pl.col('mcc_code')!='')&(pl.col('key_loose')!='')).group_by('source_id','key_loose','mcc_code').len().rename({'len':'transactions'}))
    if original.height:
        original_majority=majority_table(original,'mcc_code')
        table('original_numeric_consistency.csv',original_majority.with_columns(pl.col('key_loose').map_elements(public_merchant_id,return_dtype=pl.String).alias('merchant_id')).drop('key_loose'))

    indiana=card.filter(pl.col('source_id')=='indiana')
    issuer=collect(indiana.group_by('issuer','card_type','fiscal_year','year','mcc_group').len().rename({'len':'transactions'}))
    table('indiana_issuer_distribution.csv',issuer)
    boundaries=collect(indiana.group_by('issuer','card_type').agg(pl.len().alias('transactions'),pl.col('txn_date').filter(pl.col('txn_date')!='').min().alias('first_date'),pl.col('txn_date').max().alias('last_date')))
    table('indiana_issuer_dates.csv',boundaries)
    byissuer=collect(indiana.filter((pl.col('mcc_analysis')!='')&(pl.col('key_loose')!='')).group_by('issuer','key_loose','mcc_analysis').len().rename({'len':'transactions'}))
    issuer_major={}
    for (iss,key),df in byissuer.group_by('issuer','key_loose'):
        df=df.sort(['transactions','mcc_analysis'],descending=[True,False]);mx=df['transactions'].max()
        issuer_major.setdefault(iss,{})[key]=(df['mcc_analysis'][0],df['transactions'].sum(),df.filter(pl.col('transactions')==mx).height==1)
    shifts=[]
    for a,b in combinations(sorted(issuer_major),2):
        common=set(issuer_major[a])&set(issuer_major[b])
        for key in sorted(common):
            aa,na,ta=issuer_major[a][key];bb,nb,tb=issuer_major[b][key]
            shifts.append({'issuer_a':a,'issuer_b':b,'merchant_id':public_merchant_id(key),'code_a':aa,'code_b':bb,'transactions_a':na,'transactions_b':nb,'changed':aa!=bb,'unequivocal':ta and tb})
    table('indiana_merchant_issuer_shift.csv',shifts)
    table('indiana_issuer_shift_summary.csv',[{'shared_merchants':len(shifts),'unequivocal_merchants':sum(r['unequivocal'] for r in shifts),'changed_unequivocal_merchants':sum(r['changed'] and r['unequivocal'] for r in shifts),'changed_share':sum(r['changed'] and r['unequivocal'] for r in shifts)/sum(r['unequivocal'] for r in shifts) if any(r['unequivocal'] for r in shifts) else None}])
    # Explicit distribution comparison of observed description vocabulary avoids
    # attributing every issuer-era difference to an issuer causal effect.
    issuer_group=collect(indiana.filter(pl.col('mcc_group')!='unknown').group_by('issuer','mcc_group').len())
    issuer_js=[]
    for a,b in combinations(sorted(issuer_group['issuer'].unique()),2):
        gg=sorted(issuer_group['mcc_group'].unique());va=dict(issuer_group.filter(pl.col('issuer')==a).select('mcc_group','len').iter_rows());vb=dict(issuer_group.filter(pl.col('issuer')==b).select('mcc_group','len').iter_rows())
        issuer_js.append({'issuer_a':a,'issuer_b':b,'js_divergence_bits':float(jensenshannon([va.get(g,0) for g in gg],[vb.get(g,0) for g in gg],base=2)**2)})
    table('indiana_issuer_js_divergence.csv',issuer_js)
    report('04_label_distributions.md','S2, S6','Counts, observed-category entropy/Gini, base-2 Jensen-Shannon divergence, yearly category/vocabulary profiles, and issuer-era comparisons.','Only card_txn records enter primary MCC distributions. Linkage coverage and unmapped records must accompany results; JSD excludes unknown groups and is conditional on matched records. Issuer eras are confounded with time, agencies, and card type.',f'''There are {len(sources):,} sources with known MCC-group observations. Distribution summaries are in `label_distribution_summary.csv`; source-pair divergence is in `mcc_group_js_divergence.csv`. Gini is computed across observed category counts, not spending amounts or a zero-filled universe. Original numeric-code sensitivities remain separate.

Indiana issuer date bounds and overlap are computed from transaction-date fields, not inferred only from fiscal years: `indiana_issuer_dates.csv`. Description vocabulary shifts and known-group divergence are in `indiana_issuer_distribution.csv` and `indiana_issuer_js_divergence.csv`. Any overlap of date intervals means there is no single clean issuer transition date.
''')
    report('05_label_consistency.md','S4, S6','For each source/merchant, compute unique labels and majority share; compare only unequivocal source majorities across sources. Report code, generic-code and official-group levels separately, with raw-description and original-numeric sensitivities.','Entity-resolution errors, differing reference vintages, truncated labels, ambiguous fuzzy links and legitimate multi-MCC merchants can all induce disagreement. This is descriptive input to a label-ceiling argument, not an experimentally established performance ceiling.', '''All within-source merchant counts and source-pair majority agreements are saved in `merchant_consistency_*.csv`, `consistency_summary_*.csv`, and `cross_source_agreement_*.csv`. Top inconsistency candidates require at least 20 transactions. Neighbor-code and brand/generic explanations are candidates only. Indiana before/after issuer comparisons are in `indiana_merchant_issuer_shift.csv`; their temporal association does not establish misclassification or causation. Tied majorities are flagged and excluded from the unequivocal agreement denominator.
''')
