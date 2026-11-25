"""Reassemble a proven byte-concatenation; never infer equivalence from counts."""
import csv,hashlib,json,shutil
from collections import Counter
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from run import BASE,ROOT,DEST,ANALYSIS,AUDIT_SCHEMA,digest,fileid,save_json,write_csv
from rules import LABELS,STATUSES

def main():
    rel='Oklahoma Data - USA/birlesik_tam.csv';fid=fileid(rel)
    paths=sorted((ROOT/'Oklahoma Data - USA/birlesik').glob('oklahoma_FY*.csv'))
    metas=[json.loads((ANALYSIS/'manifests'/f'{fileid(p.relative_to(ROOT).as_posix())}.json').read_text(encoding='utf-8')) for p in paths]
    assert len(metas)==19 and all(m['rules_sha256']==digest(BASE/'taxonomy_pipeline/rules.py') for m in metas)
    source=ROOT/rel;combinedhash=hashlib.sha256()
    with source.open('rb') as f:header=f.readline()
    combinedhash.update(header)
    for path in paths:
        with path.open('rb') as f:
            first=f.readline();assert first.rstrip(b'\r\n')==header.rstrip(b'\r\n')
            while chunk:=f.read(4*1024*1024):combinedhash.update(chunk)
    actual=digest(source)
    assert combinedhash.hexdigest()==actual,'Fiscal-year concatenation is not byte-identical to supplied merged data'
    print('PROVEN: original merged bytes equal ordered fiscal-year data bytes',flush=True)
    out=DEST/rel;temporary=out.with_suffix('.csv.partial')
    with temporary.open('wb') as g:
        for i,m in enumerate(metas):
            with (DEST/m['source_file']).open('rb') as f:
                first=f.readline()
                if i==0:g.write(first)
                shutil.copyfileobj(f,g,length=4*1024*1024)
    temporary.replace(out)
    counts=Counter();methods=Counter();cross=Counter();review=Counter();contained=Counter();examples=[];offset=0
    with pq.ParquetWriter(ANALYSIS/'audit'/f'{fid}.parquet',AUDIT_SCHEMA,compression='zstd') as w:
        for m in metas:
            counts.update(m['counts']);contained.update(m['contained_sources'])
            for method,lab,n in m['methods']:methods[(method,lab)]+=n
            for batch in pq.ParquetFile(ANALYSIS/'audit'/f"{m['file_id']}.parquet").iter_batches(batch_size=100000):
                table=pa.Table.from_batches([batch]);idx=table.schema.get_field_index('source_row')
                table=table.set_column(idx,'source_row',pc.add(table['source_row'],pa.scalar(offset,pa.int64())))
                w.write_table(table)
            folder=ANALYSIS/'files'/m['file_id']
            with (folder/'mcc_taxonomy_crosstab.csv').open(encoding='utf-8-sig',newline='') as f:
                for r in csv.DictReader(f):cross[tuple(r[k] for k in ['mcc_code_linked','mcc_description_raw','mcc_only_label','taxonomy_label','evidence_method'])]+=int(r['rows'])
            with (folder/'review_groups.csv').open(encoding='utf-8-sig',newline='') as f:
                for r in csv.DictReader(f):review[tuple(r[k] for k in ['source_id','taxonomy_label','merchant','mcc_description_raw','rule_id'])]+=int(r['rows'])
            with (folder/'evidence_examples.csv').open(encoding='utf-8-sig',newline='') as f:
                for r in csv.DictReader(f):r['source_row']=int(r['source_row'])+offset;examples.append(r)
            offset+=m['reader_rows_excluding_header']
    meta={**metas[0],'file_id':fid,'source_file':rel,'read_path':source.relative_to(BASE).as_posix(),'is_primary_input':False,'source_sha256':actual,'output_sha256':digest(out),'source_payload_sha256':None,'counts':dict(counts),'methods':[[*k,v] for k,v in methods.items()],'sheetcounts':[['',lab,num] for lab,num in counts.items()],'contained_sources':dict(contained),'original_width_counts':{'12':offset},'reused_proven_concatenation':[m['source_file'] for m in metas]}
    for k in ['reader_rows_excluding_header','transaction_candidate_rows','resolved_rows','nontransaction_rows','numeric_mcc_rows','linked_mcc_rows','mcc_only_resolved_rows','additional_resolved_rows','changed_from_mcc_rows']:meta[k]=sum(m[k] for m in metas)
    meta['resolved_fraction']=meta['resolved_rows']/meta['transaction_candidate_rows']
    n=meta['transaction_candidate_rows'];total=sum(counts.values());res=meta['resolved_rows'];folder=ANALYSIS/'files'/fid
    distribution=[{'taxonomy_label':l,'main_category':l.split('.')[0] if '.' in l else '', 'rows':counts[l],'share_all_rows':counts[l]/total,'share_transaction_candidates':counts[l]/n if l!='NOT_A_TRANSACTION' else None,'share_resolved':counts[l]/res if l in LABELS else None} for l in LABELS+STATUSES]
    write_csv(folder/'label_distribution.csv',list(distribution[0]),distribution)
    crossfields=['mcc_code_linked','mcc_description_raw','mcc_only_label','taxonomy_label','evidence_method','rows']
    write_csv(folder/'mcc_taxonomy_crosstab.csv',crossfields,[dict(zip(crossfields,(*k,num))) for k,num in cross.most_common()])
    reviewfields=['source_id','taxonomy_label','merchant','mcc_description_raw','rule_id','rows']
    write_csv(folder/'review_groups.csv',reviewfields,[dict(zip(reviewfields,(*k,num))) for k,num in review.most_common()])
    write_csv(folder/'evidence_examples.csv',list(examples[0]),examples)
    save_json(ANALYSIS/'manifests'/f'{fid}.json',meta)
    print(f'REUSED verified concatenation: {offset:,} rows',flush=True)
if __name__=='__main__':main()
