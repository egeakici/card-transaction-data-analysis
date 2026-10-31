"""Purchase-label concentration, proxy item clusters, and bootstrap intervals."""
import hashlib
import json
import re
from collections import Counter,defaultdict

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.stats import chi2_contingency
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer,CountVectorizer
from sklearn.metrics import mutual_info_score

from .common import OUT,DERIVED,SEED,collect,table,report,normalize_label,normalized_entropy,public_merchant_id,json_save
from .privacy import safe_text,safe_merchant
from .plots import save,heatmap

PLACEHOLDERS={
    'GENERAL PURCHASE','GENERAL TRANSACTION','TRANSACTION LINE ITEM','ORDER SUMMARY ITEM',
    'ROOM CHARGES','PARTS EACH','PURCHASE','PURCHASES','TRANSACTION','ITEM','N A','NA',
    'UNKNOWN','NOT PROVIDED','NONE','MISCELLANEOUS','MISC','TRAVEL','SUPPLIES',
}


def informative(value):
    norm=normalize_label(value)
    return bool(norm) and norm not in PLACEHOLDERS and not re.fullmatch(r'(?:GENERAL (?:PURCHASE|TRANSACTION)|TRANSACTION LINE ITEM|ORDER SUMMARY ITEM)(?: \d+)?',norm)


def item_clusters():
    scan=pl.scan_parquet(DERIVED/'analysis.parquet')
    purchases=pl.scan_parquet(DERIVED/'purchase_labels.parquet')
    keys=['source_id','source_file','source_sheet','source_row']
    ok=collect(purchases.filter(pl.col('scheme')=='oklahoma_item_desc').join(scan.select(keys+['key_loose','year','org_unit','mcc_analysis','mcc_group']),on=keys,how='left'))
    flags=ok.with_columns(pl.col('value').map_elements(informative,return_dtype=pl.Boolean).alias('informative'))
    byyear=flags.group_by('year').agg(pl.len().alias('labeled_transactions'),pl.col('informative').sum().alias('informative_transactions')).with_columns((pl.col('informative_transactions')/pl.col('labeled_transactions')).alias('informative_share'))
    byorg=flags.group_by('org_unit').agg(pl.len().alias('labeled_transactions'),pl.col('informative').sum().alias('informative_transactions')).with_columns((pl.col('informative_transactions')/pl.col('labeled_transactions')).alias('informative_share'))
    table('oklahoma_item_informativeness_year.csv',byyear);table('oklahoma_item_informativeness_org.csv',byorg)
    placeholders=flags.filter(~pl.col('informative')).with_columns(pl.col('value').map_elements(normalize_label,return_dtype=pl.String).alias('normalized_placeholder')).group_by('normalized_placeholder').len().sort('len',descending=True)
    table('oklahoma_item_placeholders.csv',placeholders)
    count_items=flags.with_columns(pl.col('value').str.count_matches(r'\|').add(1).alias('items')).group_by('items','informative').len().rename({'len':'transactions'})
    table('oklahoma_items_per_transaction.csv',count_items)
    selected=flags.filter(pl.col('informative'))
    descriptors=Counter();eligible_texts=set()
    support=collect(scan.filter(pl.col('source_id')=='oklahoma').group_by('key_loose').len())
    supports=dict(support.iter_rows())
    transaction_count=0
    for value,key in selected.select('value','key_loose').iter_rows():
        items=[normalize_label(v) for v in value.split('|') if informative(v)]
        if not items:continue
        transaction_count+=1
        descriptors.update(items)
        if supports.get(key,0)>=20:eligible_texts.update(items)
    texts=sorted(descriptors)
    if len(texts)<2:
        json_save(DERIVED/'cluster_method.json',{'status':'unavailable','reason':'Fewer than two informative descriptions'})
        return []
    # The requested all-MiniLM-L6-v2 checkpoint is not in the local cache and
    # unrestricted model downloads are unavailable. Use the explicitly authorized
    # TF-IDF fallback, not a different unreported pretrained checkpoint.
    vectorizer=TfidfVectorizer(analyzer='char',ngram_range=(3,5),min_df=2,max_features=20000,dtype=np.float32,sublinear_tf=True)
    vocabulary_fit=sorted(texts,key=lambda t:(-descriptors[t],t))[:50000]
    vectorizer.fit(vocabulary_fit)
    X=vectorizer.transform(texts)
    index={value:i for i,value in enumerate(texts)}
    weights=np.array([descriptors[t] for t in texts],dtype=np.float32)
    # Human-readable word terms supplement the actual character-ngram features.
    word_vectorizer=CountVectorizer(ngram_range=(1,2),min_df=2,max_features=30000,stop_words='english')
    word_vectorizer.fit(vocabulary_fit)
    words=word_vectorizer.transform(texts);terms=word_vectorizer.get_feature_names_out()
    cluster_rows=[];quality=[]
    label_schema=pa.schema([(c,pa.int64() if c=='source_row' else pa.string()) for c in keys+['scheme','value']])
    proxy_writer=pq.ParquetWriter(DERIVED/'oklahoma_proxy_labels.parquet',label_schema,compression='zstd')
    for requested_k in [50,200]:
        k=min(requested_k,len(texts));model=MiniBatchKMeans(n_clusters=k,random_state=SEED,batch_size=1024,n_init=3,max_iter=100,max_no_improvement=15,reassignment_ratio=.01)
        labels=model.fit_predict(X,sample_weight=weights)
        frequencies=np.bincount(labels,weights=weights,minlength=k)
        for c in range(k):
            members=np.flatnonzero(labels==c)
            if len(members):
                counts=np.asarray(words[members].multiply(weights[members,None]).sum(axis=0)).ravel()
                term_idx=np.argsort(-counts,kind='stable')[:10]
                topterms=[safe_text(terms[i]) for i in term_idx if counts[i]>0]
                examples=[]
                for i in sorted(members,key=lambda i:(-descriptors[texts[i]],texts[i])):
                    if texts[i] in eligible_texts:examples.append(safe_text(texts[i]))
                    if len(examples)==5:break
            else:topterms=[];examples=[]
            cluster_rows.append({'k':requested_k,'actual_k':k,'cluster':c,'item_occurrences':int(frequencies[c]),'unique_descriptions':len(members),'top10_terms':json.dumps(topterms),'examples_up_to5':json.dumps(examples)})
        label_rows=[]
        for row in selected.iter_rows(named=True):
            items=[normalize_label(v) for v in row['value'].split('|') if informative(v)]
            if not items:continue
            cluster_counts=Counter(int(labels[index[item]]) for item in items)
            dominant=sorted(cluster_counts,key=lambda c:(-cluster_counts[c],c))[0]
            identity={key:row[key] for key in keys}
            label_rows.append({**identity,'scheme':f'oklahoma_proxy_k{requested_k}','value':f'cluster_{dominant:03d}'})
            label_rows.append({**identity,'scheme':f'oklahoma_proxy_basket_k{requested_k}','value':'|'.join(f'c{c:03d}' for c in sorted(cluster_counts))})
            if len(label_rows)>=20000:
                proxy_writer.write_table(pa.Table.from_pylist(label_rows,schema=label_schema));label_rows.clear()
        if label_rows:proxy_writer.write_table(pa.Table.from_pylist(label_rows,schema=label_schema))
        quality.append({'k':requested_k,'actual_k':k,'unique_descriptions':len(texts),'vocabulary_fit_unique_descriptions':len(vocabulary_fit),'vocabulary_fit_item_occurrence_coverage':sum(descriptors[t] for t in vocabulary_fit)/sum(descriptors.values()),'item_occurrences':int(weights.sum()),'informative_transactions':transaction_count,'inertia':float(model.inertia_),'nonempty_clusters':int(np.count_nonzero(frequencies))})
        print(f'CLUSTERED Oklahoma k={requested_k}: {len(texts):,} unique descriptions; {transaction_count:,} transactions',flush=True)
    table('oklahoma_item_clusters.csv',cluster_rows);table('oklahoma_clustering_summary.csv',quality)
    proxy_writer.close()
    json_save(DERIVED/'cluster_method.json',{'method':'TF-IDF character 3-5 grams + frequency-weighted MiniBatchKMeans','seed':SEED,'embedding_checkpoint_requested':'sentence-transformers/all-MiniLM-L6-v2','fallback_reason':'Requested checkpoint unavailable locally; no model-network dependency introduced','max_features':20000,'vocabulary_fit':'Most frequent up to 50000 unique informative item descriptions, deterministic count/lexical order; transform and clustering cover all informative items','bootstrap_replicates':1000,'placeholders':sorted(PLACEHOLDERS),'dominant_rule':'One dominant item cluster per transaction; ties choose smallest cluster ID; basket signatures reported separately'})
    return pl.scan_parquet(DERIVED/'oklahoma_proxy_labels.parquet')


def bootstrapped_entropy(counts,identity):
    counts=np.asarray(counts,dtype=np.int64);k=len(counts);n=int(counts.sum())
    if k<=1:return 0.,0.,0.
    seed=int.from_bytes(hashlib.sha256((str(SEED)+identity).encode()).digest()[:8],'big')
    rng=np.random.default_rng(seed)
    draws=rng.multinomial(n,counts/n,size=1000)
    p=draws/n
    logs=np.zeros_like(p,dtype=float);np.log2(p,out=logs,where=p>0)
    boot=-np.sum(p*logs,axis=1)/np.log2(k)
    low,high=np.quantile(boot,[.025,.975])
    return normalized_entropy(counts),float(low),float(high)


def run():
    proxies=item_clusters()
    base=pl.scan_parquet(DERIVED/'analysis.parquet')
    identity=['source_id','source_file','source_sheet','source_row']
    long=pl.scan_parquet(DERIVED/'purchase_labels.parquet')
    # Raw item descriptions have excessive cardinality; the original distribution
    # is retained privately and proxy/basket sensitivities are used for purity.
    long=long.filter(pl.col('scheme')!='oklahoma_item_desc')
    if isinstance(proxies,pl.LazyFrame):
        long=pl.concat([long,proxies],how='vertical')
    joined=long.join(base.select(identity+['key_loose','record_type','merchant_masked','mcc_analysis','mcc_group','org_type']),on=identity,how='left')
    joined=joined.with_columns(pl.col('value').alias('value_exact'),pl.col('value').map_elements(normalize_label,return_dtype=pl.String).alias('value'))
    # DWP is evaluated as exact strings and normalized strings separately.
    exact=joined.filter(pl.col('scheme')=='dwp_purpose').with_columns(pl.lit('dwp_purpose_exact').alias('scheme'),pl.col('value_exact').alias('value'))
    joined=pl.concat([joined,exact],how='vertical')
    joined=joined.filter((pl.col('value')!='')&(pl.col('value')!='ADDRESS_REDACTED'))
    joined.sink_parquet(DERIVED/'purity_label_events.parquet',compression='zstd',engine='streaming')
    events=pl.scan_parquet(DERIVED/'purity_label_events.parquet')
    valid=events.filter((pl.col('key_loose')!='')&~pl.col('merchant_masked')&(pl.col('record_type')=='card_txn')&(pl.col('source_id')!='ipo'))
    counts=collect(valid.group_by('source_id','scheme','key_loose','value').len().rename({'len':'transactions'}))
    counts.write_parquet(DERIVED/'purity_counts.parquet',compression='zstd')
    raw_totals=collect(events.group_by('source_id','scheme').len().rename({'len':'all_label_events'}))
    valid_totals=counts.group_by('source_id','scheme').agg(pl.col('transactions').sum().alias('eligible_record_type_label_events'))
    metrics=[]
    for (sid,scheme,key),df in counts.group_by('source_id','scheme','key_loose'):
        n=int(df['transactions'].sum())
        if n<20:continue
        entropy,low,high=bootstrapped_entropy(df['transactions'].to_list(),sid+'|'+scheme+'|'+key)
        majority=float(df['transactions'].max()/n)
        metrics.append({'source_id':sid,'scheme':scheme,'key_loose':key,'merchant_id':public_merchant_id(key),
            'transactions':n,'unique_labels':df.height,'normalized_entropy':entropy,'entropy_ci_low':low,'entropy_ci_high':high,
            'majority_share':majority,'purity_band':'high' if majority>=.9 else 'medium' if majority>=.7 else 'low'})
    metric=pl.DataFrame(metrics,infer_schema_length=None)
    metric.write_parquet(DERIVED/'merchant_purity.parquet',compression='zstd')
    table('merchant_purity.csv',metric.drop('key_loose'))
    summaries=[]
    for row in raw_totals.sort('source_id','scheme').to_dicts():
        sid,scheme=row['source_id'],row['scheme'];df=metric.filter((pl.col('source_id')==sid)&(pl.col('scheme')==scheme))
        valid_n=valid_totals.filter((pl.col('source_id')==sid)&(pl.col('scheme')==scheme))['eligible_record_type_label_events'].sum()
        eligible=int(df['transactions'].sum())
        totals={band:int(df.filter(pl.col('purity_band')==band)['transactions'].sum()) for band in ['high','medium','low']}
        summaries.append({**row,'valid_record_label_events':valid_n,'supported_merchants':df.height,'supported_transactions':eligible,
            'support_coverage_of_valid':eligible/valid_n if valid_n else None,
            **{f'{band}_transactions':totals[band] for band in totals},
            **{f'{band}_share_supported':totals[band]/eligible if eligible else None for band in totals},
            **{f'{band}_share_all_labeled':totals[band]/row['all_label_events'] if row['all_label_events'] else None for band in totals}})
    summary=pl.DataFrame(summaries,infer_schema_length=None);table('purity_summary.csv',summary)
    # Propagate merchant-level concentration to each observed transaction's MCC
    # to produce transaction-weighted MCC slices with explicit support counts.
    supported=metric.lazy().select('source_id','scheme','key_loose','majority_share','normalized_entropy','purity_band')
    breakdown=collect(valid.join(supported,on=['source_id','scheme','key_loose'],how='inner').group_by('source_id','scheme','mcc_analysis','mcc_group').agg(pl.len().alias('supported_transactions'),(pl.col('purity_band')=='high').mean().alias('high_share'),(pl.col('purity_band')=='low').mean().alias('low_share'),pl.col('majority_share').mean().alias('transaction_weighted_majority_share'),pl.col('normalized_entropy').mean().alias('transaction_weighted_normalized_entropy')))
    table('purity_by_mcc.csv',breakdown)
    lowest=breakdown.filter((pl.col('mcc_analysis')!='')&(pl.col('supported_transactions')>=100)).sort('transaction_weighted_majority_share').head(20)
    table('lowest_purity_mcc_top20.csv',lowest)
    low_merchants=[]
    for row in metric.sort(['majority_share','transactions'],descending=[False,True]).head(30).to_dicts():
        key=row.pop('key_loose');row['key_display']=safe_merchant(key,row['transactions']);low_merchants.append(row)
    table('lowest_purity_merchants_top30.csv',low_merchants)
    table('moneydata_purity_summary.csv',summary.filter(pl.col('source_id')=='moneydata'))
    # MCC association is per source/scheme; do not pool unrelated label systems.
    association=[];cross=collect(valid.filter(pl.col('mcc_group')!='unknown').group_by('source_id','scheme','mcc_group','value').len().rename({'len':'transactions'}))
    # Values can contain purpose details; public cross tables use opaque label IDs.
    table('mcc_purchase_cross_table.csv',cross.with_columns(pl.col('value').map_elements(lambda v:'l_'+hashlib.sha256(v.encode()).hexdigest()[:16],return_dtype=pl.String).alias('purchase_label_id')).drop('value'))
    for (sid,scheme),df in cross.group_by('source_id','scheme'):
        groups=sorted(df['mcc_group'].unique());labels=sorted(df['value'].unique())
        matrix=np.zeros((len(groups),len(labels)),dtype=np.int64);gi={g:i for i,g in enumerate(groups)};li={l:i for i,l in enumerate(labels)}
        for row in df.to_dicts():matrix[gi[row['mcc_group']],li[row['value']]]=row['transactions']
        n=matrix.sum();min_dim=min(matrix.shape)-1
        chi2=float(chi2_contingency(matrix,correction=False)[0]) if min_dim>0 else 0.
        v=float(np.sqrt(chi2/(n*min_dim))) if n and min_dim>0 else None
        mi=float(mutual_info_score(None,None,contingency=matrix)/np.log(2)) if n else None
        label_counts=matrix.sum(axis=0);from .common import entropy
        label_h=entropy(label_counts);explained=mi/label_h if label_h else None
        association.append({'source_id':sid,'scheme':scheme,'transactions':int(n),'mcc_groups':len(groups),'purchase_labels':len(labels),'cramers_v':v,'mutual_information_bits':mi,'purchase_entropy_bits':label_h,'mi_over_label_entropy':explained})
    table('mcc_purchase_association.csv',association)
    primary=summary.filter(~pl.col('scheme').str.contains('basket|exact|code|top')).filter(pl.col('supported_transactions')>0)
    fig,ax=plt.subplots(figsize=(10,max(4,primary.height*.32)))
    labels=(primary['source_id']+' / '+primary['scheme']).to_list();bottom=np.zeros(primary.height)
    for band,color in [('high','#337f6b'),('medium','#d3a448'),('low','#b45d60')]:
        values=primary[f'{band}_share_supported'].to_numpy();ax.barh(labels,values,left=bottom,color=color,label=band);bottom+=values
    ax.set(xlabel='Share of supported labeled transactions',title='Within-merchant purchase-label concentration (N >= 20)',xlim=(0,1));ax.legend(ncol=3,loc='lower right');save(fig,'merchant_purity_bands')
    fig,ax=plt.subplots(figsize=(9,4.5))
    for scheme in sorted(metric['scheme'].unique()):
        df=metric.filter(pl.col('scheme')==scheme).sort('majority_share')
        ax.step(df['majority_share'].to_numpy(),np.cumsum(df['transactions'].to_numpy())/df['transactions'].sum(),label=scheme,where='post',alpha=.7)
    ax.set(xlabel='Merchant majority purchase-label share',ylabel='Cumulative transaction-weighted share',title='Purchase-label concentration sensitivity by scheme');ax.legend(fontsize=5,ncol=3);save(fig,'merchant_purity_cdf')
    rows='\n'.join(f'| {r["source_id"]} | {r["scheme"]} | {r["supported_transactions"]:,} | {r["support_coverage_of_valid"]:.2%} | {r["high_share_supported"]:.2%} | {r["low_share_supported"]:.2%} |' for r in primary.to_dicts())
    report('06_merchant_purity.md','S5','Separate each purchase-label scheme; normalize categorical text; evaluate merchants with >=20 labeled card transactions. Entropy is H/log2(K observed within that merchant); multinomial resampling is equivalent to 1,000 i.i.d. transaction-label bootstrap replicates. Use empirical percentile 95% intervals with fixed observed support and deterministic seed 42.','Label concentration is an observational proxy, not classification accuracy, a causal identity-content relationship, an information-theoretic ceiling, or proof that a statement string identifies a purchase. Label granularity, institutional bookkeeping, merchant-key merging, extraction windows and missing-label selection matter. Bootstrap intervals condition on observed labels, key assignments and proxy clusters; they omit clustering/entity-resolution uncertainty and serial dependence.',f'''# Central result: identity does not uniquely specify transaction contents

The analysis reports concentration, without treating its majority-share number as recovered spending content. High purity means majority share >=0.9, medium means >=0.7 and <0.9, and low means <0.7. Denominators are explicit: `supported_transactions` includes only merchants with N>=20; the same table also gives coverage and shares of all labeled records. Schemes must not be summed because a transaction may carry multiple schemes.

| Source | Scheme | Supported transactions | Support coverage | High-purity share | Low-purity share |
| --- | --- | ---: | ---: | ---: | ---: |
{rows}

Oklahoma: uninformative placeholders are enumerated in `oklahoma_item_placeholders.csv` and the configured rule set. Pipe-separated items are split before proxy construction. The requested embedding checkpoint is unavailable locally; the authorized fallback is character 3-5 gram TF-IDF (20,000 features) and frequency-weighted MiniBatchKMeans with k=50 and k=200, seed 42. To bound vocabulary-construction memory, vocabulary/IDF and readable word-term features are fitted on the most frequent up to 50,000 unique informative descriptions (count then lexical order); transformation, frequency-weighted clustering and purity metrics cover **all** informative items. Vocabulary-fit occurrence coverage is explicitly reported. Clusters are **proxy categories**, not validated product labels. Primary per-transaction proxies use the modal item cluster, with a deterministic smallest-ID tie break. Sorted cluster-basket signatures are a separate sensitivity analysis. Cluster terms/examples, counts and nonempty-cluster diagnostics are in `oklahoma_item_clusters.csv` and `oklahoma_clustering_summary.csv`.

Direct categorical analyses include Bristol Nature and SERCOP, Solihull purpose/ProClass and parsed code/top-level variants where present, Stockport internal category/purpose, Eden purpose, DWP normalized and exact-purpose sensitivity, and MoneyData author categories. Address-like Solihull labels are masked before persistence and excluded from concentration, without printing their original values. Academic MoneyData is a separate consumer reference; transfers/cash/fees are reported in record types and excluded from primary card-only purity.

`merchant_purity.csv` gives merchant entropy, majority share, unique labels and bootstrap intervals; `purity_by_mcc.csv` provides supported transaction-weighted code/group slices; `lowest_purity_mcc_top20.csv` and `lowest_purity_merchants_top30.csv` identify review candidates. MCC/purchase-label associations use Cramer's V and mutual information in bits (`mcc_purchase_association.csv`). Small or sparse contingency tables and high-cardinality purpose vocabularies can inflate association statistics; these are descriptive, without significance or generalization claims.
''')
