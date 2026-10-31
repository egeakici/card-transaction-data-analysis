"""Pinned factual MCC references, conservative linkage, and row enrichment."""
import csv
import json
import re
from collections import defaultdict

import pdfplumber
import polars as pl
from rapidfuzz import fuzz, process

from .common import ROOT,OUT,DERIVED,CONFIG,ACCESS_DATE,normalize_label,file_hash,collect,canonical_scan,table,report,json_save

VISA_URL='https://usa.visa.com/content/dam/VCOM/download/merchants/visa-merchant-data-standards-manual.pdf'
MC_URL='https://www.mastercard.com/content/dam/mccom/shared/business/support/rules-pdfs/mastercard-quick-reference-booklet-merchant.pdf'
CITI_URL='https://www.citibank.com/tts/solutions/commercial-cards/assets/docs/govt/Merchant-Category-Codes.pdf'


def extract_references():
    pinned=CONFIG/'mcc_reference_snapshot.csv'
    if pinned.exists():
        reference=pl.read_csv(pinned,infer_schema=False)
        reference.write_csv(OUT/'reference/mcc_official.csv')
        if 'mcc_group_raw' in reference.columns:
            reference.filter(pl.col('mcc_group_raw')!=pl.col('mcc_group')).write_csv(OUT/'reference/group_name_normalizations.csv')
        return reference
    facts={}
    with pdfplumber.open(DERIVED/'reference_cache/visa.pdf') as pdf:
        for page_n,page in enumerate(pdf.pages,1):
            if page_n<27:continue
            for grid in page.extract_tables():
                for row_index,row in enumerate(grid):
                    numeric=[i for i,v in enumerate(row[:3]) if re.fullmatch(r'\d{4}',str(v or '').strip())]
                    if not numeric:continue
                    code=row[numeric[0]].strip()
                    # The title/name is the first nonempty cell after the code;
                    # examples and required payment abbreviations are separate.
                    following=[(i,v) for i,v in enumerate(row) if i>numeric[0] and v and str(v).strip()]
                    if not following:continue
                    title_column,title=following[0]
                    title=' '.join(title.split()).replace('\ufffd','-')
                    for continuation in grid[row_index+1:row_index+3]:
                        text=continuation[title_column] if len(continuation)>title_column else None
                        others=[v for j,v in enumerate(continuation) if j!=title_column and v and str(v).strip()]
                        if not text or others or len(text)>110 or re.search(r'(?i)merchants|this MCC|classified|includes|for ',text):break
                        title+=' '+' '.join(text.split()).replace('\ufffd','-')
                    facts.setdefault(code,{'mcc_code':code,'description':title,'network':'Visa','source_url':VISA_URL,'pdf_page':page_n,'reference_status':'current_visa','mcc_group':'unknown','group_source':'','group_page':''})
    # Citi is a historical issuer reference, never silently substituted for the
    # current Visa reference when assessing a source's original numeric codes.
    historical={}
    with pdfplumber.open(DERIVED/'reference_cache/citi.pdf') as pdf:
        for page_n,page in enumerate(pdf.pages,1):
            for line in (page.extract_text() or '').splitlines():
                m=re.match(r'^\s*(\d{4})\s+(.+)',line)
                if m:
                    code,title=m.groups();title=re.split(r'\s+(?:V, M|V,M|V,|M,|TSYS|V$|M$)',title)[0].strip()
                    historical.setdefault(code,(title,page_n))
    for code,(title,page_n) in historical.items():
        if code not in facts:
            facts[code]={'mcc_code':code,'description':title,'network':'Citi historical multi-network','source_url':CITI_URL,'pdf_page':page_n,'reference_status':'historical_citi_only','mcc_group':'unknown','group_source':'','group_page':''}
    # Mastercard's public web extraction is pinned as factual tuples, because
    # direct PDF requests return HTTP 403 in this environment.
    source=DERIVED/'reference_cache/mastercard_lines.tsv'
    code='';title='';mc_facts={};current_range=None;range_facts={}
    for line in source.read_text(encoding='utf-8').splitlines():
        parts=line.split('\t',2)
        if len(parts)!=3:continue
        _,page_n,text=parts
        # Running page headers can name the PREVIOUS MCC. Only the actual table
        # caption establishes the next MCC; otherwise categories shift at pages.
        m=re.search(r'Description of MCC (\d{4}):\s*(.*)',text)
        if m:code,title=m.groups();current_range=None
        ranged=re.search(r'Description of MCCs (\d{4}) through (\d{4}):',text)
        if ranged:current_range=tuple(map(int,ranged.groups()));code=''
        m=re.search(r'MCC Category\s+(?!Description)(.+)',text)
        if m and (code or current_range):
            group=m.group(1).strip()
            if group=='Professional Services and Membership':group+=' Organizations'
            if current_range:range_facts[current_range]=(group,page_n)
            else:mc_facts[code]={'mcc_code':code,'description':title,'mcc_group':group,'group_source':MC_URL,'group_page':page_n}
    for code,fact in facts.items():
        n=int(code)
        if code in mc_facts:
            fact.update({k:mc_facts[code][k] for k in ['mcc_group','group_source','group_page']})
        elif 3000<=n<=3350:
            fact.update(mcc_group='Airlines',group_source=MC_URL,group_page='78')
        elif 3351<=n<=3500:
            fact.update(mcc_group='Automobile/Vehicle Rentals',group_source=MC_URL,group_page='80')
        elif 3501<=n<=3999:
            fact.update(mcc_group='Hotels and Motels',group_source=MC_URL,group_page='81')
    for code,m in mc_facts.items():
        if code not in facts:
            facts[code]={**m,'network':'Mastercard','source_url':MC_URL,'pdf_page':m['group_page'],'reference_status':'current_mastercard_only'}
    reference=pl.DataFrame(sorted(facts.values(),key=lambda r:r['mcc_code']),infer_schema_length=None).with_columns(pl.all().cast(pl.String))
    reference.write_csv(pinned);reference.write_csv(OUT/'reference/mcc_official.csv')
    from .reference_qa import refresh_groups
    refresh_groups()
    reference=pl.read_csv(pinned,infer_schema=False)
    # Retain historical title alternatives for exact linkage.
    alternates=[{'mcc_code':c,'description':t,'source_url':CITI_URL,'pdf_page':str(p)} for c,(t,p) in historical.items()]
    table('mcc_historical_titles.csv',alternates)
    (CONFIG/'mcc_historical_titles.csv').write_bytes((OUT/'tables/mcc_historical_titles.csv').read_bytes())
    print(f'REFERENCE {reference.height} codes; {len(mc_facts)} explicit Mastercard categories',flush=True)
    return reference


def run():
    reference=extract_references()
    if not (OUT/'tables/mcc_historical_titles.csv').exists() and (CONFIG/'mcc_historical_titles.csv').exists():
        (OUT/'tables/mcc_historical_titles.csv').write_bytes((CONFIG/'mcc_historical_titles.csv').read_bytes())
    references={r['mcc_code']:r for r in reference.to_dicts()}
    aliases=defaultdict(set);raw_exact=defaultdict(set)
    for row in reference.to_dicts():
        aliases[normalize_label(row['description'])].add(row['mcc_code']);raw_exact[row['description']].add(row['mcc_code'])
    historical=pl.read_csv(CONFIG/'mcc_historical_titles.csv',infer_schema=False)
    for row in historical.to_dicts():aliases[normalize_label(row['description'])].add(row['mcc_code']);raw_exact[row['description']].add(row['mcc_code'])
    # Numeric code+description pairs in the supplied data are separately marked
    # empirical aliases, not misrepresented as official descriptions.
    observed=collect(canonical_scan().filter((pl.col('mcc_code')!='')&(pl.col('mcc_desc_norm')!='')).group_by('mcc_desc_norm','mcc_code').len())
    empirical=defaultdict(set)
    for row in observed.to_dicts():
        if row['mcc_code'] in references:empirical[row['mcc_desc_norm']].add(row['mcc_code'])
    vocab=collect(canonical_scan().filter(pl.col('mcc_desc_raw')!='').group_by('source_id','mcc_desc_raw','mcc_desc_norm').len().rename({'len':'count'}).sort('source_id','count',descending=[False,True]))
    table('mcc_desc_vocab.csv',vocab)
    names=sorted(aliases);mappings=[]
    for row in vocab.unique(['source_id','mcc_desc_norm']).to_dicts():
        raw=row['mcc_desc_raw'];norm=row['mcc_desc_norm'];sid=row['source_id'];code='';candidate='';method='unmatched';score=0.;review=True
        if len(raw_exact.get(raw,set()))==1:
            code=next(iter(raw_exact[raw]));method='exact';score=100.;review=False
        elif len(aliases.get(norm,set()))==1:
            code=next(iter(aliases[norm]));method='normalized';score=100.;review=False
        elif len(empirical.get(norm,set()))==1:
            code=next(iter(empirical[norm]));method='observed_code_description';score=100.;review=False
        else:
            prefix={c for label,codes in aliases.items() if len(norm)>=16 and label.startswith(norm) for c in codes}
            if len(prefix)==1:
                code=next(iter(prefix));method='unique_prefix';score=100.;review=False
            else:
                hits=process.extract(norm,names,scorer=fuzz.WRatio,limit=2)
                if hits:
                    best,best_score,_=hits[0];score=float(best_score);candidate='|'.join(sorted(aliases[best]))
                    method='fuzzy_candidate'
                    margin=score-hits[1][1] if len(hits)>1 else score
                    if score>=95 and margin>=5 and len(aliases[best])==1:
                        code=next(iter(aliases[best]));method='fuzzy_high_confidence';review=False
        mappings.append({'source_id':sid,'mcc_desc_norm':norm,'mcc_code':code,'candidate_code':candidate,'match_method':method,'match_score':score,'needs_review':review})
    mapping=pl.DataFrame(mappings,infer_schema_length=None)
    table('mcc_desc_to_code.csv',mapping.sort('source_id','mcc_desc_norm'))
    table('mcc_needs_review.csv',mapping.filter(pl.col('needs_review')))
    # Candidate mappings remain separate; only accepted linkage enters metrics.
    join_map=mapping.select('source_id','mcc_desc_norm',pl.col('mcc_code').alias('linked_mcc_code'),'match_method','needs_review').lazy()
    ref=reference.select('mcc_code','mcc_group','reference_status').rename({'mcc_code':'mcc_analysis'}).lazy()
    official_norms=set(aliases)
    data=canonical_scan().join(join_map,on=['source_id','mcc_desc_norm'],how='left').with_columns(
        pl.when(pl.col('mcc_code')!='').then(pl.col('mcc_code')).otherwise(pl.col('linked_mcc_code').fill_null('')).alias('mcc_analysis'),
        ((pl.col('source_id')=='stockport')&pl.col('merchant_raw').map_elements(lambda s:normalize_label(s) in official_norms,return_dtype=pl.Boolean)).alias('merchant_masked')
    ).join(ref,on='mcc_analysis',how='left').with_columns(
        pl.col('mcc_group').fill_null('unknown'),pl.col('reference_status').fill_null('unlisted'),
        pl.when(pl.col('mcc_analysis').cast(pl.Int64,strict=False).is_between(3000,3350)).then(pl.lit('4511'))
          .when(pl.col('mcc_analysis').cast(pl.Int64,strict=False).is_between(3351,3500)).then(pl.lit('7512'))
          .when(pl.col('mcc_analysis').cast(pl.Int64,strict=False).is_between(3501,3999)).then(pl.lit('7011'))
          .otherwise(pl.col('mcc_analysis')).alias('mcc_generic'),
        pl.col('txn_date').str.slice(0,4).alias('year'),pl.col('txn_date').str.slice(0,7).alias('month'),
    )
    data.sink_parquet(DERIVED/'analysis.parquet',compression='zstd',row_group_size=50000,engine='streaming')
    scan=pl.scan_parquet(DERIVED/'analysis.parquet')
    invalid=collect(scan.filter((pl.col('mcc_code')!='')&pl.col('reference_status').is_in(['unlisted','historical_citi_only'])).group_by('source_id','source_file','mcc_code','reference_status').len())
    table('mcc_numeric_needs_review.csv',invalid)
    coverage=collect(scan.group_by('source_id').agg(pl.len().alias('rows'),(pl.col('mcc_code')!='').sum().alias('numeric_code_rows'),(pl.col('mcc_desc_raw')!='').sum().alias('description_rows'),(pl.col('mcc_analysis')!='').sum().alias('linked_code_rows'),(pl.col('mcc_group')!='unknown').sum().alias('known_group_rows'),pl.col('merchant_masked').sum().alias('merchant_masked_rows'),pl.col('mcc_analysis').filter(pl.col('mcc_analysis')!='').n_unique().alias('unique_codes'))).sort('source_id')
    table('label_coverage.csv',coverage)
    schemes=collect(pl.scan_parquet(DERIVED/'purchase_labels.parquet').group_by('source_id','scheme').agg(pl.len().alias('label_rows'),pl.col('value').n_unique().alias('unique_values'))).sort('source_id','scheme')
    table('purchase_label_coverage.csv',schemes)
    descriptions='\n'.join(f'| {r["source_id"]} | {r["rows"]:,} | {r["numeric_code_rows"]:,} | {r["description_rows"]:,} | {r["linked_code_rows"]:,} | {r["known_group_rows"]:,} |' for r in coverage.to_dicts())
    report('02_labels.md','S2','Separate original numeric codes, raw descriptions, accepted reference linkage, and review candidates. Prefix matching requires a unique code and a sufficiently long prefix; fuzzy acceptance requires score >=95 and a runner-up margin >=5.','References differ in date and network. Historical-only or unlisted does not prove an erroneous original code. Description linkage is inferential and may overstate code identity; downstream sensitivity tables retain raw-label results.',f'''The reference contains {reference.height:,} codes. There are {mapping.height:,} source/normalized-description combinations, of which {mapping.filter(pl.col('needs_review')).height:,} require review. Explicit numeric codes are never replaced with a description-derived code.

| Source | Rows | Original numeric MCC | MCC description | Accepted code linkage | Known official group |
| --- | ---: | ---: | ---: | ---: | ---: |
{descriptions}

Indiana's misleadingly named column is retained as description text; its values are not treated as numeric codes. Stockport's purpose-present rows use the internal-category scheme; purpose-absent rows are MCC candidates. That content-based period distinction is auditable in `schema_variants.csv` and its dates are tested in the descriptive tables. Masking detection uses exact normalized reference descriptions, not a guess based only on uppercase text.

Review files: `mcc_needs_review.csv`, `mcc_numeric_needs_review.csv`. The analysis groups follow Mastercard's published MCC Category facts; any absent category remains `unknown`. Brand-specific airline, car-rental, and lodging codes also have a generic-code sensitivity field. Purchase labels are never converted into a new custom taxonomy.
''')
    meta=[]
    for filename,url in [('visa.pdf',VISA_URL),('citi.pdf',CITI_URL),('mastercard_lines.tsv',MC_URL)]:
        p=DERIVED/'reference_cache'/filename
        meta.append({'file':filename,'source_url':url,'access_date':ACCESS_DATE,'sha256':file_hash(p),'license':'copyright; no open redistribution licence identified'})
    json_save(OUT/'reference/reference_manifest.json',meta)
    table('reference_status_counts.csv',reference.group_by('reference_status').len())
    (OUT/'reference/README.md').write_text(f'''# MCC references

Access date: {ACCESS_DATE}. Facts are extracted reproducibly from pinned local snapshots. Primary reference: [Visa Merchant Data Standards Manual, October 2026]({VISA_URL}); historical comparison: [Citi Merchant Category Codes]({CITI_URL}); official upper categories: [Mastercard Quick Reference Booklet, 2 June 2026]({MC_URL}).

The current Visa document is the numeric-code baseline. Historical issuer-only entries and current Mastercard-only entries remain identified in `reference_status`. This is not a historical validity oracle for transactions predating the reference. All source-specific descriptions and spelling variants remain intact in `tables/mcc_desc_vocab.csv`. PDF files remain in the private `derived/reference_cache/` directory. Numeric/category facts, their pages, URLs, and snapshot hashes are in this repository; original manuals are copyright with no open redistribution licence established. Mastercard direct downloads returned HTTP 403; its publicly indexed primary-document text was used, with page provenance retained. Brand ranges follow the Mastercard headings: airlines 3000-3350, car rental 3351-3500, lodging 3501-3999. The generic codes are 4511, 7512, 7011 respectively.

Reproduction uses `data_profile/config/mcc_reference_snapshot.csv` and `mcc_historical_titles.csv` without a changing online dependency. To rebuild reference extraction, retrieve the exact source versions and the primary-document page text, compare the hashes, and remove only the generated reference snapshot. Unknown or unextracted categories are never filled using an undocumented range rule. Range captions are parsed independently of single-code captions so brand-range categories cannot overwrite an earlier generic code. Airline ranges use the published Airlines group, car-rental ranges Automobile/Vehicle Rentals, and hotel ranges Hotels and Motels. Exact original group strings are retained in `mcc_group_raw`; the isolated singular wording Business Service is normalized to the catalogue heading Business Services, with its affected reference code documented in `group_name_normalizations.csv`.
''',encoding='utf-8')
