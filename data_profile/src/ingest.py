"""Bounded-memory ingestion with explicit exclusions and reconciliation."""
import csv
import json
from collections import Counter
from datetime import datetime

import pyarrow as pa
import pyarrow.parquet as pq

from .common import ROOT, OUT, DERIVED, file_hash, json_save, mkdirs, report, table
from .sources import configurations, source_files, readable_path, read_records, canonical_record


def arrow_schema(row):
    return pa.schema([(key, pa.float64() if key=='amount' else pa.int64() if key=='source_row' else pa.bool_() if isinstance(value,bool) else pa.string()) for key,value in row.items()])


def ingest():
    mkdirs()
    configs=configurations()
    from .oklahoma_refresh import prepare
    prepare()
    manifest=[]; reconciliations=[]; variants=Counter(); exclusions=Counter(); field_coverage=Counter()
    canonical_writer=None; labels_writer=None; exclusion_writer=None
    label_schema=pa.schema([(c,pa.int64() if c=='source_row' else pa.string()) for c in ['source_id','source_file','source_sheet','source_row','scheme','value']])
    exclusion_schema=pa.schema([(c,pa.int64() if c=='source_row' else pa.string()) for c in ['source_id','source_file','source_sheet','source_row','reason']])
    buffers=[];label_buffer=[];excluded_buffer=[]; canonical_schema=None
    baseline={str(p.relative_to(ROOT)).replace('\\','/'):file_hash(readable_path(p)) for config in configs for p in source_files(config)}
    json_save(DERIVED/'raw_hash_baseline.json',baseline)

    def flush():
        nonlocal canonical_writer,labels_writer,exclusion_writer,canonical_schema
        if buffers:
            if canonical_schema is None:
                canonical_schema=arrow_schema(buffers[0])
                canonical_writer=pq.ParquetWriter(DERIVED/'canonical.parquet',canonical_schema,compression='zstd',use_dictionary=True)
            canonical_writer.write_table(pa.Table.from_pylist(buffers,schema=canonical_schema))
            buffers.clear()
        if label_buffer:
            if labels_writer is None:
                labels_writer=pq.ParquetWriter(DERIVED/'purchase_labels.parquet',label_schema,compression='zstd')
            labels_writer.write_table(pa.Table.from_pylist(label_buffer,schema=label_schema));label_buffer.clear()
        if excluded_buffer:
            if exclusion_writer is None:
                exclusion_writer=pq.ParquetWriter(DERIVED/'excluded_rows.parquet',exclusion_schema,compression='zstd')
            exclusion_writer.write_table(pa.Table.from_pylist(excluded_buffer,schema=exclusion_schema));excluded_buffer.clear()

    for config in configs:
        sid=config['source_id'];raw_count=0;canonical_count=0;excluded_count=0;dates=[];source_files_count=0
        for path in source_files(config):
            source_files_count+=1
            relative=str(path.relative_to(ROOT)).replace('\\','/')
            nraw=ncanonical=nexcluded=0;file_dates=[];file_variants=Counter();header=[];sheets=set()
            for sheet,n,record,reason in read_records(config,path):
                nraw+=1;sheets.add(sheet)
                if record and not header:header=list(record)
                for column,value in record.items():
                    field_coverage[(sid,column)]+=bool(str(value or '').strip())
                if not reason:
                    canonical,labels,reason=canonical_record(config,path,sheet,n,record)
                if reason:
                    nexcluded+=1;exclusions[(sid,relative,reason)]+=1
                    excluded_buffer.append({'source_id':sid,'source_file':relative,'source_sheet':sheet,'source_row':n,'reason':reason})
                else:
                    ncanonical+=1
                    buffers.append(canonical);label_buffer.extend(labels)
                    variants[(sid,canonical['schema_variant'])]+=1;file_variants[canonical['schema_variant']]+=1
                    if canonical['txn_date']:file_dates.append(canonical['txn_date'])
                if len(buffers)>=20000 or len(label_buffer)>=20000 or len(excluded_buffer)>=20000:
                    flush()
            flush()
            assert nraw==ncanonical+nexcluded
            # Record original headers, including excluded identifier column NAMES.
            if path.suffix.lower()=='.csv':
                with readable_path(path).open(encoding='utf-8-sig',newline='') as f:
                    for _ in range(config.get('csv_skiprows',2 if sid=='oklahoma' else 0)):next(f)
                    header=next(csv.reader(f))
            manifest.append({'source_id':sid,'source_file':relative,'bytes':path.stat().st_size,
                'sha256':baseline[relative],'encoding':'OOXML ZIP' if path.suffix=='.xlsx' else 'utf-8-sig',
                'delimiter':'worksheet' if path.suffix=='.xlsx' else ',', 'raw_rows':nraw,'canonical_rows':ncanonical,'excluded_rows':nexcluded,
                'columns_json':json.dumps(header,ensure_ascii=False),'schema_variants':len(file_variants),'sheets':len(sheets),
                'date_min':min(file_dates) if file_dates else '', 'date_max':max(file_dates) if file_dates else '',
                'read_errors':0})
            raw_count+=nraw;canonical_count+=ncanonical;excluded_count+=nexcluded
            if file_dates:dates.extend([min(file_dates),max(file_dates)])
            print(f'  READ {sid}/{path.name}: {ncanonical:,} retained; {nexcluded:,} excluded',flush=True)
        if config.get('expected_input_rows') is not None:
            assert raw_count==config['expected_input_rows'],f'Unexpected input count for {sid}: {raw_count}'
        reconciliations.append({'source_id':sid,'raw_rows':raw_count,'canonical_rows':canonical_count,'excluded_rows':excluded_count,
            'difference':raw_count-canonical_count-excluded_count,'reported_approximate_rows':config['reported_approximate_rows'],
            'canonical_minus_reported':canonical_count-config['reported_approximate_rows'],'file_count':source_files_count,
            'date_min':min(dates) if dates else '', 'date_max':max(dates) if dates else ''})
        print(f'INGESTED {sid}: raw={raw_count:,}; canonical={canonical_count:,}; excluded={excluded_count:,}',flush=True)
    for writer in [canonical_writer,labels_writer,exclusion_writer]:
        if writer is not None:writer.close()
    table('reconciliation.csv',reconciliations)
    table('schema_variants.csv',[{'source_id':s,'schema_variant':v,'rows':n} for (s,v),n in sorted(variants.items())])
    table('exclusions.csv',[{'source_id':s,'source_file':f,'reason':r,'rows':n} for (s,f,r),n in sorted(exclusions.items())])
    table('raw_field_coverage.csv',[{'source_id':s,'column':c,'nonempty_rows':n} for (s,c),n in sorted(field_coverage.items())])
    with (OUT/'manifest.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(manifest[0]),lineterminator='\n');writer.writeheader();writer.writerows(manifest)
    verify_reconciliation()
    total_raw=sum(x['raw_rows'] for x in reconciliations);total=sum(x['canonical_rows'] for x in reconciliations)
    rows='\n'.join(f'| {x["source_id"]} | {x["raw_rows"]:,} | {x["canonical_rows"]:,} | {x["excluded_rows"]:,} | {x["date_min"]} | {x["date_max"]} |' for x in reconciliations)
    body=f'''The inventory contains {len(manifest):,} supplied input data files from {len(configs):,} sources. Oklahoma inputs are already prepared fiscal-year extracts, not the original 170 downloads described in the upstream note. There are {total_raw:,} reader records and {total:,} canonical records. The Indonesia source and all previously created CSV conversions/concatenations are outside this study, preventing double counting.

| Source | Reader rows | Canonical rows | Excluded rows | Earliest parsed date | Latest parsed date |
| --- | ---: | ---: | ---: | --- | --- |
{rows}

See `tables/reconciliation.csv`, `tables/schema_variants.csv`, and `tables/exclusions.csv`. The original row address is `(source_id, source_file, source_sheet, source_row)`; CSV row numbers count parsed CSV records including the header, not physical newlines embedded inside quoted cells. DWP/IPO/Eden upstream provenance remains separate. Unknown date semantics are preserved as unknown.

Workbook reader counts include blank rows in the stored worksheet extent and the MoneyData documentation sheet. Those rows are explicitly excluded; they are not interpreted as transactions. Bristol uses every data sheet from every original workbook, explaining its difference from the approximate sample-based estimate. Solihull excludes blank rows and organization-only note rows rather than treating them as card activity.
'''
    report('01_inventory.md','S1','Read supplied files, omit named identity columns if present, hash inputs, and reconcile every reader row.','Original download completeness and upstream processing cannot be established from the locally supplied merged files. Workbook formatting extents inflate reader-row counts.',body,inputs='outputs/manifest.csv; original paths listed in data_profile/config/sources/*.yaml')
    json_save(DERIVED/'ingest_summary.json',{'sources':reconciliations,'raw_files':len(manifest),'canonical_rows':total,'completed_utc':datetime.now().isoformat()})


def verify_reconciliation():
    import polars as pl
    from .common import collect
    counts=collect(pl.scan_parquet(DERIVED/'canonical.parquet').group_by('source_id').len())
    counts=dict(counts.iter_rows())
    reconciliation=pl.read_csv(OUT/'tables/reconciliation.csv')
    for row in reconciliation.iter_rows(named=True):
        assert row['difference']==0
        assert counts[row['source_id']]==row['canonical_rows']
    schema=pq.read_schema(DERIVED/'canonical.parquet')
    assert not {'Last Name','First Initial','Cardholder Name'}.intersection(schema.names)
    print('RECONCILIATION PASSED for all sources',flush=True)
