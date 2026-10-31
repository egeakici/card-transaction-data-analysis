"""Internal, unlabelled evidence sample and split-feasibility summaries."""
import csv
import hashlib
import json
from collections import defaultdict

import numpy as np
import polars as pl

from .common import OUT,DERIVED,SEED,collect,table,report,public_merchant_id,json_save
from .privacy import safe_text,personal_name_hit


def run():
    scan=pl.scan_parquet(DERIVED/'analysis.parquet')
    base=scan.filter((pl.col('record_type')=='card_txn')&(pl.col('key_loose')!='')&~pl.col('merchant_masked')&(pl.col('source_id')!='ipo'))
    frequencies=collect(base.group_by('source_id','key_loose').len())
    supported=frequencies.filter(pl.col('len')>=20).select('source_id','key_loose').lazy()
    candidates=collect(base.join(supported,on=['source_id','key_loose'],how='inner').select('source_id','merchant_raw','mcc_desc_raw','amount','mcc_group','intermediary','key_loose').unique(subset=['source_id','merchant_raw'],keep='first',maintain_order=True))
    rows=[]
    for row in candidates.to_dicts():
        merchant=row['merchant_raw']
        if safe_text(merchant)!=merchant:continue
        n=len(merchant);band='<5' if n<5 else '5-17' if n<18 else '18-24' if n<25 else '25-39' if n<40 else '40+'
        stratum=(row['source_id'],row['mcc_group'],band,bool(row['intermediary']))
        digest=hashlib.sha256((str(SEED)+'|'+row['source_id']+'|'+merchant).encode()).hexdigest()
        rows.append({**row,'stratum':stratum,'rank':digest})
    strata=defaultdict(list)
    for row in rows:strata[row['stratum']].append(row)
    for values in strata.values():values.sort(key=lambda r:r['rank'])
    # Round-robin stratification first covers every eligible stratum, then cycles
    # deterministically; inclusion probabilities are unequal and are not hidden.
    chosen=[];ordered=sorted(strata);depth=0
    while len(chosen)<800:
        added=0
        for stratum in ordered:
            if len(strata[stratum])>depth:
                chosen.append(strata[stratum][depth]);added+=1
                if len(chosen)==800:break
        if not added:break
        depth+=1
    assert len(chosen)==800,f'Only {len(chosen)} privacy-eligible distinct strings available'
    annotation=OUT/'annotation'
    with (annotation/'evidence_sample.csv').open('w',encoding='utf-8',newline='') as f:
        fields=['sample_id','source_id','merchant_raw','mcc_desc_raw','amount','annotator_A','annotator_B']
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader()
        for i,row in enumerate(chosen,1):
            writer.writerow({'sample_id':f'E{i:04d}','source_id':row['source_id'],'merchant_raw':row['merchant_raw'],'mcc_desc_raw':safe_text(row['mcc_desc_raw']),'amount':row['amount'],'annotator_A':'','annotator_B':''})
    allocations=pl.DataFrame([{'source_id':r['source_id'],'mcc_group':r['mcc_group'],'length_band':r['stratum'][2],'has_intermediary':r['stratum'][3]} for r in chosen]).group_by('source_id','mcc_group','length_band','has_intermediary').len().rename({'len':'sample_strings'})
    table('annotation_allocations.csv',allocations)
    # Illustrative examples are not annotations of the sampled records.
    examples={'A':[],'B':[],'C':[],'D':[]}
    for row in sorted(rows,key=lambda r:r['rank']):
        upper=row['merchant_raw'].upper();key=row['key_loose']
        if key in {'AMAZON','WALMART'} or 'ARGOS' in upper:group='B'
        elif any(term in upper for term in ['FEE','PAYMENT','UNKNOWN','FRAUD']) or len(upper)<6 or (row['intermediary'] and key not in {'AMAZON','WALMART'} and len(key)<12):group='C'
        elif any(term in upper for term in ['PARKING','TRAIN','BUS TICKET','POSTAGE','CAR PARK']):group='D'
        elif any(term in upper for term in ['AIRLINES','PASSPORT','RAILWAY','HOTEL','RESTAURANT','COFFEE']):group='A'
        else:continue
        if len(examples[group])<3 and row['merchant_raw'] not in examples[group]:examples[group].append(row['merchant_raw'])
    # If fewer safe observed examples exist, do not invent supporting examples.
    example_text='\n'.join(f'- {group}: '+('; '.join(f'`{v}`' for v in values) if values else 'No safe supported example selected; expert review required.') for group,values in examples.items())
    (annotation/'guidelines.md').write_text(f'''# Internal evidence-sufficiency annotation protocol

**Internal use only.** The sample is unlabelled. Annotators work independently and do not consult MCC or amount before judging the descriptor. The supplied contextual columns can be hidden during the first pass. Record A/B/C/D in annotator_A or annotator_B. Preserve uncertainty in a separate adjudication worksheet; never alter original transaction data.

- **A**: a recognisable single-purpose merchant; identity strongly suggests a broad spending category.
- **B**: recognisable, multi-category merchant; identity alone does not establish the purchased item.
- **C**: identity is uncertain or a nonmerchant/obscured descriptor.
- **D**: descriptor explicitly adds product/service evidence beyond identity.

Priority for overlapping classes: D when explicit product/service evidence is present; otherwise B, then A, otherwise C. A is a descriptor-level evidence judgement, not a claim about actual receipts. Adjudicate disagreements after independent annotation; report agreement and class definitions before using labels. Do not infer a purchase merely from the reference MCC.

Observed examples below are **illustrative candidates**, selected by transparent string rules for expert review, not ground-truth labels. Each uses a normalized merchant with >=20 card records and passes identifier/address screening:

{example_text}

The sample contains {len(chosen)} unique source/descriptor strings. Deterministic hash ranks use seed {SEED}; round-robin allocation over source x linked MCC group x length band x intermediary-presence ensures broad coverage. It is a purposive, unequal-probability sample and is unsuitable for unweighted population class-prevalence estimates. Rare or personal-pattern strings are excluded. No train/test split is created.
''',encoding='utf-8')
    summary=collect(base.group_by('source_id').agg(pl.len().alias('card_transactions'),pl.col('key_loose').n_unique().alias('merchant_keys'))).join(frequencies.group_by('source_id').agg((pl.col('len')>=20).sum().alias('merchants_with_20_records')),on='source_id',how='left').with_columns((pl.col('merchant_keys')>=100).alias('at_least_100_merchants'),(pl.col('merchants_with_20_records')>=20).alias('at_least_20_supported_merchants'))
    table('grouped_split_feasibility.csv',summary)
    yearly=collect(base.filter(pl.col('year')!='').group_by('source_id','year').agg(pl.len().alias('transactions'),pl.col('key_loose').n_unique().alias('merchants')))
    temporal=[]
    for (sid,),df in yearly.group_by('source_id'):
        for year in sorted(df['year'].unique())[:-1]:
            before=df.filter(pl.col('year')<=year)['transactions'].sum();after=df.filter(pl.col('year')>year)['transactions'].sum()
            temporal.append({'source_id':sid,'cut_year':year,'train_through_year_rows':before,'test_after_year_rows':after,'both_sides_at_least_1000':before>=1000 and after>=1000})
    table('temporal_split_feasibility.csv',temporal)
    keys=collect(base.select('source_id','country','key_loose').unique())
    sets={sid:set(df['key_loose']) for (sid,),df in keys.group_by('source_id')}
    uk=set(keys.filter(pl.col('country')=='UK')['key_loose']);cross=[]
    for train,trainset in sorted(sets.items()):
        for test,testset in sorted(sets.items()):
            if train==test:continue
            common=trainset&testset
            cross.append({'train_source':train,'test_source':test,'test_merchants':len(testset),'seen_test_merchants':len(common),'test_merchant_seen_share':len(common)/len(testset) if testset else None})
        if train=='delaware':
            cross.append({'train_source':train,'test_source':'UK_pool','test_merchants':len(uk),'seen_test_merchants':len(trainset&uk),'test_merchant_seen_share':len(trainset&uk)/len(uk) if uk else None})
    table('cross_source_split_overlap.csv',cross)
    table('annotation_example_counts.csv',[{'class':c,'selected_examples':len(v),'required_examples':3} for c,v in examples.items()])
    report('08_annotation_and_splits.md','S1, S3, S6','Create a deterministic, stratified, unlabelled sample of privacy-eligible distinct strings; count grouped/time/source split feasibility only.','Support >=20 and personal-pattern suppression exclude rare descriptors, particularly tiny sources. Stratified inclusion is unequal, so the sample does not estimate class prevalence without appropriate design weights. Merchant overlap is a proxy for leakage risk, not a verified corporate-entity overlap.',f'''Prepared {len(chosen)} unlabelled strings across {len(strata)} eligible strata. `annotation/evidence_sample.csv` and `annotation/guidelines.md` are **internal-only** and excluded from Git. Annotation columns remain empty. No model or data split is trained/created.

Grouped-split statistics in `grouped_split_feasibility.csv` report factual counts plus explicit heuristic thresholds (>=100 merchant keys; >=20 merchants with >=20 records). Temporal candidates in `temporal_split_feasibility.csv` report all observed year cuts and a >=1,000-row-per-side indicator. `cross_source_split_overlap.csv` quantifies how many test merchants are already seen, including Delaware-to-Oklahoma and Delaware-to-UK-pool comparisons. These are planning diagnostics, not recommended or executed experimental splits.
''')
