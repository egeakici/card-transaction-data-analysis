"""Non-destructive Oklahoma concatenation and refreshed coverage diagnostics."""
from pathlib import Path
import csv
import hashlib
import json
import re
import shutil

import polars as pl

from .common import ROOT, OUT, DERIVED, collect, file_hash, json_save, table, report
from .sources import configurations, source_files


def config():
    return next(c for c in configurations() if c['source_id']=='oklahoma')


def input_scan():
    return pl.scan_csv(source_files(config()), infer_schema=False)


def prepare():
    """Stack fiscal-year files in order; preserve cell bytes and input files."""
    cfg=config(); paths=source_files(cfg)
    output=ROOT/cfg['folder']/'birlesik_tam.csv'
    temporary=output.with_suffix('.csv.partial')
    if output.exists():
        history=DERIVED/'history/merged_csv';history.mkdir(parents=True,exist_ok=True)
        previous=history/(file_hash(output)+'.csv')
        if not previous.exists():shutil.copy2(output,previous)
    columns=None; sources=[]
    with temporary.open('wb') as writer:
        for path in paths:
            with path.open('rb') as reader:
                header=reader.readline().lstrip(b'\xef\xbb\xbf').rstrip(b'\r\n')
                if columns is None:
                    columns=next(csv.reader([header.decode('utf-8')]))
                    writer.write(header+b'\n')
                else:
                    assert next(csv.reader([header.decode('utf-8')]))==columns, path.name
                shutil.copyfileobj(reader,writer,length=2**20)
                with path.open('rb') as tail:
                    tail.seek(-1,2);last=tail.read(1)
                if last not in (b'\n',b'\r'):writer.write(b'\n')
            sources.append({'path':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size,'sha256':file_hash(path)})
    totals=lambda scan:collect(scan.select(pl.len().alias('rows'),pl.col('amount').cast(pl.Decimal(24,2),strict=False).sum().cast(pl.String).alias('amount_total_usd'),pl.col('amount').cast(pl.Decimal(24,2),strict=False).null_count().alias('unparsed_amounts'))).row(0,named=True)
    original=totals(input_scan());merged=totals(pl.scan_csv(temporary,infer_schema=False))
    assert original==merged,(original,merged)
    assert original['rows']==cfg['expected_input_rows']
    temporary.replace(output)
    result={'status':'passed','output':output.relative_to(ROOT).as_posix(),'rows':original['rows'],'amount_total_usd':original['amount_total_usd'],'unparsed_amounts':original['unparsed_amounts'],'columns':columns,'source_order':[p.name for p in paths],'source_files':sources,'sha256':file_hash(output),'bytes':output.stat().st_size,'rule':'Fiscal years ascending; retain within-file order, original fields and cell bytes; header once; no deduplication, sorting within files, or value normalization','excluded_from_profiling_inputs':True,'excluded_from_git':True}
    json_save(DERIVED/'oklahoma_merged_verification.json',result)
    print(f"OKLAHOMA MERGE VERIFIED: {original['rows']:,} rows; USD {original['amount_total_usd']}; {len(paths)} files",flush=True)


def audit():
    cfg=config();raw=input_scan()
    proxy_counts=collect(pl.scan_parquet(DERIVED/'oklahoma_proxy_labels.parquet').group_by('scheme').agg(pl.len().alias('rows'),pl.col('value').n_unique().alias('distinct_proxy_labels')))
    clustering=pl.read_csv(OUT/'tables/oklahoma_clustering_summary.csv')
    expected_info=int(clustering['informative_transactions'][0])
    expected_schemes={'oklahoma_proxy_k50','oklahoma_proxy_basket_k50','oklahoma_proxy_k200','oklahoma_proxy_basket_k200'}
    assert set(proxy_counts['scheme'])==expected_schemes
    assert all(n==expected_info for n in proxy_counts['rows'])
    table('oklahoma_proxy_coverage.csv',proxy_counts)
    date_sources=collect(raw.group_by('date_source').len().rename({'len':'rows'}))
    table('oklahoma_date_sources.csv',date_sources)
    prepared=raw.with_columns(pl.col('txn_date').str.slice(5,2).cast(pl.Int32).alias('_month'),pl.col('txn_date').str.slice(0,4).cast(pl.Int32).alias('_year'),pl.col('fiscal_year').cast(pl.Int32).alias('_fy'))
    fy=collect(prepared.group_by('fiscal_year').agg(pl.len().alias('rows'),pl.col('txn_date').min().alias('first_date'),pl.col('txn_date').max().alias('last_date'),pl.col('txn_date').str.slice(0,7).n_unique().alias('months_observed'),(pl.col('date_source')=='period').sum().alias('period_imputed_dates'),pl.col('amount').cast(pl.Decimal(24,2),strict=False).sum().cast(pl.String).alias('amount_total_usd'),pl.col('mcc_desc').fill_null('').str.strip_chars().ne('').sum().alias('mcc_description_rows'),pl.col('item_desc').fill_null('').str.strip_chars().ne('').sum().alias('item_description_rows'),(pl.col('_fy')!=(pl.col('_year')+(pl.col('_month')>=7).cast(pl.Int32))).sum().alias('fiscal_year_mismatches'))).sort('fiscal_year')
    table('oklahoma_fiscal_year_coverage.csv',fy)
    months=collect(raw.with_columns(pl.col('txn_date').str.slice(0,7).alias('month')).group_by('month').agg(pl.len().alias('rows'),(pl.col('date_source')=='period').sum().alias('period_imputed_dates')))
    observed={r['month']:r for r in months.to_dicts()};first=min(observed);last=max(observed);grid=[]
    for fiscal in range(int(fy['fiscal_year'].min()),int(fy['fiscal_year'].max())+1):
        for month in list(range(7,13))+list(range(1,7)):
            calendar_year=fiscal-1 if month>=7 else fiscal
            key=f'{calendar_year:04d}-{month:02d}';r=observed.get(key,{})
            grid.append({'fiscal_year':fiscal,'calendar_month':key,'rows':r.get('rows',0),'period_imputed_dates':r.get('period_imputed_dates',0),'coverage_status':'observed' if key in observed else 'before_first_observation' if key<first else 'after_last_observation' if key>last else 'gap_within_observed_range'})
    table('oklahoma_calendar_month_coverage.csv',grid)
    schema=raw.collect_schema().names();quality=[]
    values=collect(raw.select([expr for col in schema for expr in [pl.col(col).is_not_null().sum().alias(col+'__present'),pl.col(col).fill_null('').str.strip_chars().eq('').sum().alias(col+'__blank')]])).row(0,named=True)
    total=int(fy['rows'].sum())
    for col in schema:
        quality.append({'column':col,'rows':total,'non_null_rows':values[col+'__present'],'blank_or_null_rows':values[col+'__blank'],'nonblank_share':1-values[col+'__blank']/total})
    table('oklahoma_input_field_coverage.csv',quality)
    provenance=collect(raw.group_by('resource_id').agg(pl.len().alias('rows'),pl.col('source_file').n_unique().alias('upstream_file_names'),pl.col('fiscal_year').n_unique().alias('fiscal_years')))
    table('oklahoma_resource_coverage.csv',provenance)
    baseline=pl.read_csv(ROOT/'data_profile/config/oklahoma_previous_profile.csv')
    old_values={r['metric']:r['value'] for r in baseline.to_dicts()}
    comparisons=[]
    for filename,metrics in [('reconciliation.csv',['canonical_rows','raw_rows','excluded_rows']),('merchant_summary.csv',['unique_raw','unique_strict','unique_loose']),('label_coverage.csv',['description_rows','linked_code_rows','known_group_rows']),('oklahoma_month_totals.csv',[])]:
        after=pl.read_csv(OUT/'tables'/filename,infer_schema_length=10000)
        if metrics:
            b=after.filter(pl.col('source_id')=='oklahoma').row(0,named=True)
            for metric in metrics:
                comparisons.append({'metric':metric,'previous':float(old_values[metric]),'refreshed':float(b[metric]),'difference':float(b[metric]-old_values[metric]),'evidence_table':filename})
        else:
            def share(df):
                return df.filter(pl.col('calendar_month').cast(pl.String).str.zfill(2).is_in(['05','06']))['transactions'].sum()/df['transactions'].sum()
            a=old_values['may_june_share'];b=share(after)
            comparisons.append({'metric':'may_june_share','previous':a,'refreshed':b,'difference':b-a,'evidence_table':filename})
    table('oklahoma_refresh_comparison.csv',comparisons)
    reconciliation=pl.read_csv(OUT/'tables/reconciliation.csv')
    weights=reconciliation.select('source_id','canonical_rows').with_columns((pl.col('canonical_rows')/pl.col('canonical_rows').sum()).alias('canonical_pool_share'))
    table('source_pool_weights.csv',weights)
    mayjune=next(r for r in comparisons if r['metric']=='may_june_share')
    note=ROOT/cfg['upstream_processing']['evidence_note']
    json_save(OUT/'oklahoma_refresh_checks.json',{'status':'passed','analysis_run_date':'2026-11-04','source_input_files':len(source_files(cfg)),'input_rows':total,'informative_item_transactions':expected_info,'proxy_labels_per_scheme':expected_info,'proxy_schemes':sorted(expected_schemes),'source_stage':cfg['input_stage'],'fiscal_year_mismatches':int(fy['fiscal_year_mismatches'].sum()),'interior_missing_months':sum(r['coverage_status']=='gap_within_observed_range' for r in grid),'observed_first_date':fy['first_date'].min(),'observed_last_date':fy['last_date'].max(),'observed_upstream_resource_ids':provenance.height,'upstream_note_sha256':file_hash(note),'upstream_processing':cfg['upstream_processing'],'merged_csv':{'status':'passed','path':json.loads((DERIVED/'oklahoma_merged_verification.json').read_text())['output'],'rows':total,'not_distributed':True}})
    assert int(fy['fiscal_year_mismatches'].sum())==0
    body=f'''## Replacement of the earlier Oklahoma slice

The refreshed supplied inputs contain **{total:,} records in {fy.height} fiscal-year files**, replacing the earlier 900,000-record OpenGov slice. Observed transaction/period-derived dates range from **{fy['first_date'].min()} to {fy['last_date'].max()}**. Fiscal labels FY2009-FY2027 are not calendar coverage through 2027: FY2027 currently contains July-September 2026. FY2009 and FY2027 have only three observed months each; every intervening fiscal year has twelve observed months. The month grid records endpoint gaps separately from interior gaps; none of this proves complete population capture.

May-June accounts for **{mayjune['refreshed']:.2%}** of refreshed records, compared with **{mayjune['previous']:.2%}** in the old slice. Replacing an extract changes the observed population and merchant support; differences must not be interpreted as a temporal or causal effect. `oklahoma_refresh_comparison.csv` compares rows, merchant vocabulary, accepted MCC linkage and seasonal concentration. The informative-item flag is an operational string rule, not a manual validation of product evidence; coded descriptions and unlisted placeholder variants can remain. Proxy clusters were fitted afresh. To bound memory, SVD is now fitted on the same top-50,000 frequent-description reference subset used for vocabulary/IDF, and every unique informative item is transformed and clustered in disk-backed batches. The previous SVD fit used all unique descriptions; cluster IDs and purity changes therefore reflect both changed input and changed representation fit scope. Transaction informativeness now requires at least one informative item after splitting multi-item strings; redaction markers are excluded as placeholders.

## Prepared inputs and date provenance

The supplied upstream note describes 170 original downloads, removal of 222,881 blank rows, 34 overlap-month decisions, cross-file duplicate filtering, omission of cardholder identity fields, and 631 dates imputed from reporting periods. Those operations occurred **before** this profiling run. The original download collection and overlap decision manifests are not present here; their correctness and the note's explanation of OpenGov duplicate totals are not independently verified by this pipeline. The reported date-plus-amount-plus-merchant duplicate key can also match legitimate distinct purchases, and dropping an entire month at a 90% overlap threshold can discard nonmatching purchases. Consequently 6,883,868 means retained prepared records, not a certified count of unique real-world transactions. Current inputs retain {provenance.height} distinct upstream resource IDs, not necessarily all original resources.

The upstream note says fiscal years were recomputed from the effective date using a July-June calendar. A zero fiscal-calendar mismatch therefore checks internal consistency of prepared fields; it is not independent validation against original publisher fiscal-year assignments.

All {total:,} prepared input records are retained. The 631 `date_source=period` records retain `date_semantics=period`, not an asserted transaction date. No second deduplication or silent date correction is performed. Early fiscal years have reduced MCC-description coverage; use `oklahoma_fiscal_year_coverage.csv` before comparing labels over time. Missing labels are not filled with invented categories.

## Private concatenation and publication

`real-world-datas/Oklahoma Data - USA/birlesik_tam.csv` stacks FY2009 through FY2027 in that order, preserving within-file order and all twelve supplied fields. One header is emitted. Row count and exact decimal amount total reconcile with all source files. SHA-256 verification and the private merge manifest are under `derived/`; the merged CSV is excluded both from profiling input selection and Git.

Only code, reports, aggregate tables, figures, configurations, and audit metadata are prepared for publication. Dataset directories expose only README documentation. New prepared inputs contain no cardholder identity columns, so the prior source-name dictionary cannot be reconstructed. The current privacy check reports this limitation explicitly; address-pattern screening remains active and internal annotation samples remain unpublished. Public cluster examples additionally require at least twenty occurrences of their normalized description and a merchant with at least twenty records; fewer than five examples are retained where support is insufficient. This reduces rare-example disclosure but is not an anonymity certificate.

## Evidence

- `oklahoma_fiscal_year_coverage.csv`: fiscal coverage, dates, exact amount totals, MCC/item-label availability and fiscal-calendar checks.
- `oklahoma_calendar_month_coverage.csv`: complete fiscal month grid and gap classification.
- `oklahoma_date_sources.csv`: original transaction versus period-derived dates.
- `oklahoma_proxy_coverage.csv`: equal row counts for the four freshly generated proxy schemes, reconciled to informative-item transactions.
- `oklahoma_input_field_coverage.csv`: missingness for every supplied field.
- `oklahoma_resource_coverage.csv`: aggregate upstream resource coverage.
- `oklahoma_refresh_comparison.csv`: comparison against the pinned prior aggregate metrics (baseline commit 8dc7aab).
- `source_pool_weights.csv`: source contributions to the refreshed canonical pool; pooled metrics are strongly source-size weighted.
- `oklahoma_refresh_checks.json`: machine-readable refresh checks and upstream processing limitations.
'''
    report('12_oklahoma_refresh.md','S1-S7','Reprofile all nineteen prepared fiscal-year inputs; compare with pinned prior aggregates; count every fiscal/calendar month, label and date-source flag.','The supplied inputs have already been deduplicated upstream. Original 170-download processing and completeness are not independently verified. Fiscal-year labels, calendar dates, source snapshots and proxy-cluster IDs must remain distinct.',body,inputs='Current source configuration and supplied fiscal-year files; data_profile/config/oklahoma_previous_profile.csv pinned prior aggregate snapshot (commit 8dc7aab)')


def update_root_readme():
    path=ROOT/'README.md';text=path.read_text(encoding='utf-8')
    recon=pl.read_csv(OUT/'tables/reconciliation.csv')
    raw=int(recon['raw_rows'].sum());canonical=int(recon['canonical_rows'].sum());excluded=int(recon['excluded_rows'].sum())
    checks=json.loads((OUT/'quality_checks.json').read_text())
    text=re.sub(r'The recorded run reconciles .*?See the \[quality checks\]\(outputs/quality_checks.json\) and \[input manifest\]\(outputs/manifest.csv\)\.',f'The refreshed run (2026-11-04) reconciles **{raw:,} reader records** into **{canonical:,} canonical rows** and **{excluded:,} excluded rows**, with exclusion reasons retained. Hash verification confirms that all **{checks["source_data_files_hash_unchanged"]} supplied input files** remain unchanged. See the [quality checks](outputs/quality_checks.json) and [input manifest](outputs/manifest.csv).',text)
    text=text.replace('Direct cardholder identity fields are omitted during ingestion,','The prepared Oklahoma inputs already omit named cardholder columns; no original source-name dictionary is available for this refreshed run. The reader omits such fields if present,')
    if '## Oklahoma refresh' not in text:
        text+='''\n## Oklahoma refresh (2026-11-04)

Oklahoma now contributes **6,883,868 prepared records** from nineteen fiscal-year files (FY2009-FY2027), replacing the earlier 900,000-row slice. Observed dates span **2009-04-14 to 2026-09-30**; FY2027 means July-September 2026 in this snapshot. Upstream deduplication and 631 period-derived dates are disclosed, and no further deduplication is applied during profiling. The source's original 170-download processing and population completeness are not independently verified.

See the [refresh report](outputs/reports/12_oklahoma_refresh.md), [fiscal-year coverage](outputs/tables/oklahoma_fiscal_year_coverage.csv), [old/new comparison](outputs/tables/oklahoma_refresh_comparison.csv), and [refresh checks](outputs/oklahoma_refresh_checks.json). All sources and proxy clusters were recomputed from the current inputs. Earlier outputs are privately archived under `derived/history/`; the separately created Oklahoma merged CSV remains local and excluded from profiling inputs.
'''
    path.write_text(text,encoding='utf-8')
