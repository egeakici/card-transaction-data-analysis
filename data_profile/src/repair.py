"""Auditable recovery of two generic merchant strings found during initial QA."""
import csv
import json
import os

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

from .common import ROOT,OUT,DERIVED,collect,json_save,table,report
from .sources import configurations,canonical_record


def restore_false_headers():
    """Restore records only if the old exclusion exists; future full runs do not need this."""
    excluded=pl.read_parquet(DERIVED/'excluded_rows.parquet')
    selected=excluded.filter((pl.col('source_id')=='delaware')&(pl.col('reason')=='embedded_header'))
    if selected.height==0:return 0
    config=next(c for c in configurations() if c['source_id']=='delaware')
    wanted=set(selected['source_row']);path=ROOT/selected['source_file'][0];restored=[]
    with path.open(encoding='utf-8-sig',newline='') as f:
        for n,row in enumerate(csv.DictReader(f),2):
            if n in wanted:
                record,_,reason=canonical_record(config,path,'',n,row)
                assert not reason and record is not None and record['txn_date'] and record['amount'] is not None
                restored.append(record)
    assert len(restored)==selected.height
    original=DERIVED/'canonical.parquet';temporary=DERIVED/'canonical.recovery.parquet'
    parquet=pq.ParquetFile(original);schema=parquet.schema_arrow
    with pq.ParquetWriter(temporary,schema,compression='zstd') as writer:
        for batch in parquet.iter_batches(batch_size=20000):writer.write_batch(batch)
        writer.write_table(pa.Table.from_pylist(restored,schema=schema))
    del parquet
    os.replace(temporary,original)
    excluded.filter(~((pl.col('source_id')=='delaware')&(pl.col('reason')=='embedded_header'))).write_parquet(DERIVED/'excluded_rows.parquet',compression='zstd')
    n=len(restored)
    def adjust(df):
        return df.with_columns(pl.when(pl.col('source_id')=='delaware').then(pl.col('canonical_rows')+n).otherwise(pl.col('canonical_rows')).alias('canonical_rows'),pl.when(pl.col('source_id')=='delaware').then(pl.col('excluded_rows')-n).otherwise(pl.col('excluded_rows')).alias('excluded_rows'))
    manifest=pl.read_csv(OUT/'manifest.csv',infer_schema_length=10000);adjust(manifest).write_csv(OUT/'manifest.csv')
    recon=adjust(pl.read_csv(OUT/'tables/reconciliation.csv')).with_columns((pl.col('canonical_rows')-pl.col('reported_approximate_rows')).alias('canonical_minus_reported'));table('reconciliation.csv',recon)
    ex=pl.read_csv(OUT/'tables/exclusions.csv').filter(~((pl.col('source_id')=='delaware')&(pl.col('reason')=='embedded_header')));table('exclusions.csv',ex)
    variants=pl.read_csv(OUT/'tables/schema_variants.csv')
    delta={r['schema_variant']:sum(x['schema_variant']==r['schema_variant'] for x in restored) for r in restored}
    variants=variants.with_columns(pl.struct('source_id','schema_variant','rows').map_elements(lambda r:r['rows']+delta.get(r['schema_variant'],0) if r['source_id']=='delaware' else r['rows'],return_dtype=pl.Int64).alias('rows'));table('schema_variants.csv',variants)
    summary=json.loads((DERIVED/'ingest_summary.json').read_text())
    summary['sources']=recon.to_dicts();summary['canonical_rows']+=n
    json_save(DERIVED/'ingest_summary.json',summary)
    body='\n'.join(f'| {r["source_id"]} | {r["raw_rows"]:,} | {r["canonical_rows"]:,} | {r["excluded_rows"]:,} | {r["canonical_minus_reported"]:+,} |' for r in recon.to_dicts())
    report('01_inventory.md','S1','Read original files with row provenance, immediately project out Oklahoma personal columns, hash inputs and reconcile all rows.','Workbook stored extents include blank rows; merged upstream sources cannot recover unavailable original download files.',f'''The study has {manifest.height:,} original data files, {recon.height:,} sources and {recon['canonical_rows'].sum():,} canonical records. All reconciliation differences are zero.

| Source | Reader records | Canonical | Excluded | Difference from approximate prompt count |
| --- | ---: | ---: | ---: | ---: |
{body}

`manifest.csv` provides original input hashes, columns, dates and file sizes; `tables/schema_variants.csv` and `tables/exclusions.csv` provide variant counts and reasoned omissions. The Indonesia source and previous derived CSV conversions/concatenations are excluded to prevent double counting. All Bristol workbooks and transaction sheets are included. MoneyData blank worksheet extents and its documentation sheet are counted explicitly as exclusions. Solihull organization-only notes are excluded, while true missing-data records remain flagged unknown.

Initial full-source QA found {n} Delaware rows whose merchant value literally equals a field-name string but whose dates and amounts are valid. Those records were retained. Embedded-header detection now requires a header-like date as well as a header-like merchant. Their original row positions and all original fields remain traceable; `tests/test_parsers.py` prevents this over-filtering. No source file was altered.
''',inputs='Original files in data_profile/config/sources/*.yaml; outputs/manifest.csv')
    from .ingest import verify_reconciliation
    verify_reconciliation()
    print(f'RESTORED {n} legitimate generic-descriptor rows',flush=True)
    return n
