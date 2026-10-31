"""Targeted non-destructive refresh after discovering dotted UK source dates."""
import csv
import json
import os

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

from .common import ROOT,OUT,DERIVED,json_save,collect
from .sources import configurations,source_files,read_records,canonical_record


def refresh_stockport():
    config=next(c for c in configurations() if c['source_id']=='stockport')
    rows=[]
    for path in source_files(config):
        for sheet,n,raw,reason in read_records(config,path):
            if reason:continue
            record,_,reason=canonical_record(config,path,sheet,n,raw)
            if not reason:rows.append(record)
    old=collect(pl.scan_parquet(DERIVED/'canonical.parquet').filter(pl.col('source_id')=='stockport').select('source_row','raw_row_hash','txn_date','posting_date','record_type'))
    assert len(rows)==old.height
    hashes=dict(old.select('source_row','raw_row_hash').iter_rows())
    assert all(hashes[r['source_row']]==r['raw_row_hash'] for r in rows)
    file=DERIVED/'canonical.parquet';reader=pq.ParquetFile(file);schema=reader.schema_arrow
    temp=DERIVED/'canonical.date_refresh.parquet';written=False
    with pq.ParquetWriter(temp,schema,compression='zstd') as writer:
        for batch in reader.iter_batches(batch_size=20000):
            values=batch.column(schema.get_field_index('source_id')).to_pylist()
            if 'stockport' in values:
                if not written:
                    writer.write_table(pa.Table.from_pylist(rows,schema=schema));written=True
                batch=batch.filter(pa.array([v!='stockport' for v in values]))
            if batch.num_rows:writer.write_batch(batch)
    del reader;os.replace(temp,file)
    dates=[r['txn_date'] for r in rows if r['txn_date']]
    for target in [OUT/'manifest.csv',OUT/'tables/reconciliation.csv']:
        df=pl.read_csv(target,infer_schema_length=10000).with_columns(
            pl.when(pl.col('source_id')=='stockport').then(pl.lit(min(dates))).otherwise(pl.col('date_min')).alias('date_min'),
            pl.when(pl.col('source_id')=='stockport').then(pl.lit(max(dates))).otherwise(pl.col('date_max')).alias('date_max'))
        df.write_csv(target)
    summary=json.loads((DERIVED/'ingest_summary.json').read_text())
    for r in summary['sources']:
        if r['source_id']=='stockport':r.update(date_min=min(dates),date_max=max(dates))
    json_save(DERIVED/'ingest_summary.json',summary)
    new=pl.DataFrame(rows,infer_schema_length=None)
    result={'source_id':'stockport','raw_hashes_unchanged':True,'rows':len(rows),
       'previous_parsed_transaction_dates':old.filter(pl.col('txn_date')!='').height,
       'updated_parsed_transaction_dates':new.filter(pl.col('txn_date')!='').height,
       'previous_parsed_settlement_dates':old.filter(pl.col('posting_date')!='').height,
       'updated_parsed_settlement_dates':new.filter(pl.col('posting_date')!='').height,
       'rule':'Recognize dd.mm.yyyy without changing any original source cell'}
    json_save(DERIVED/'date_refresh_audit.json',result)
    from .ingest import verify_reconciliation
    verify_reconciliation();print(result,flush=True)


if __name__=='__main__':refresh_stockport()
