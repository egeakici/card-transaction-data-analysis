"""Generated paper-facing summaries, decision ledger, environment and QA."""
import csv
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime

import polars as pl

from .common import ROOT,OUT,DERIVED,CONFIG,collect,table,report,file_hash,json_save,ACCESS_DATE
from .sources import configurations,source_files,readable_path
from .privacy import sanitize_text_outputs,privacy_check


def read(name):
    return pl.read_csv(OUT/'tables'/name,infer_schema_length=10000)


def percent(value):
    return 'unavailable' if value is None else f'{value:.2%}'


def run():
    reconciliation=read('reconciliation.csv');merchants=read('merchant_summary.csv');purity=read('purity_summary.csv');coverage=read('label_coverage.csv');amounts=read('amount_summary.csv')
    total=int(reconciliation['canonical_rows'].sum());raw=int(reconciliation['raw_rows'].sum());excluded=int(reconciliation['excluded_rows'].sum())
    card_counts=read('record_types.csv');cards=int(card_counts.filter(pl.col('record_type')=='card_txn')['transactions'].sum())
    settings=configurations();configs={x['source_id']:x for x in settings}
    findings=[]
    def add(text,path):findings.append(f'{text} ([{path}](tables/{path})).')
    add(f'The study contains {total:,} canonical records from {reconciliation.height:,} sources, reconciled against {raw:,} reader records with {excluded:,} reason-coded exclusions','reconciliation.csv')
    add(f'The supplied Bristol workbooks contain {int(reconciliation.filter(pl.col("source_id")=="bristol")["canonical_rows"][0]):,} transaction rows, rather than the sample-based approximate count','reconciliation.csv')
    add(f'The MoneyData workbook contributes {int(reconciliation.filter(pl.col("source_id")=="moneydata")["canonical_rows"][0]):,} canonical transactions; its blank worksheet extents and documentation are excluded','reconciliation.csv')
    for sid in ['delaware','oklahoma','sunderland']:
        r=merchants.filter(pl.col('source_id')==sid).row(0,named=True)
        add(f'{sid.title()} has {r["rows_with_merchant"]:,} merchant-bearing rows but {r["unique_loose"]:,} loose merchant keys ({r["loose_per_row"]:.2%} keys per row)','merchant_summary.csv')
    ok=read('oklahoma_month_totals.csv');mayjune=ok.filter(pl.col('calendar_month').cast(pl.String).str.zfill(2).is_in(['05','06']))['transactions'].sum();oktotal=ok['transactions'].sum()
    add(f'{mayjune:,} of {oktotal:,} dated Oklahoma records ({mayjune/oktotal:.2%}) occur in May or June','oklahoma_month_totals.csv')
    manifest=pl.read_csv(OUT/'manifest.csv');okfiles=manifest.filter(pl.col('source_id')=='oklahoma')
    add(f'All {okfiles.height:,} Oklahoma input extracts have exactly {int(okfiles["raw_rows"][0]):,} rows, a potential extract-cap diagnostic rather than evidence of download completeness','reconciliation.csv')
    eden=read('eden_file_classification.csv');supplier=int(eden.filter(pl.col('record_type')=='supplier_payment')['rows'].sum())
    add(f'{supplier:,} Eden records are supplier payments from the explicitly identified period files and are excluded from institutional card analyses','eden_file_classification.csv')
    masked=int(coverage.filter(pl.col('source_id')=='stockport')['merchant_masked_rows'][0])
    add(f'{masked:,} Stockport supplier strings exactly match normalized MCC reference descriptions and are flagged as merchant-masked','label_coverage.csv')
    stock=read('stockport_period_checks.csv');both=stock['both_dates'].sum();before=stock['settlement_before_purchase'].sum()
    add(f'{before:,} of {both:,} Stockport records with both dates ({before/both:.2%}) have settlement before purchase','stockport_period_checks.csv')
    dwp=amounts.filter(pl.col('source_id')=='dwp').row(0,named=True)
    if dwp['positive_below_500']:
        add(f'DWP includes {dwp["positive_below_500"]:,} positive amounts below GBP 500, so a strict positive-payment lower bound is unsupported','amount_summary.csv')
    else:
        add(f'DWP has {dwp["at_least_500"]:,} observed positive amounts at least GBP 500 and no positive amounts below that threshold; negative adjustments require a separate interpretation','amount_summary.csv')
    issuer=read('indiana_issuer_shift_summary.csv').row(0,named=True)
    add(f'Indiana has {issuer["unequivocal_merchants"]:,} shared merchants with unequivocal issuer-era code majorities; {issuer["changed_unequivocal_merchants"]:,} differ ({percent(issuer["changed_share"])})','indiana_issuer_shift_summary.csv')
    examples=[('bristol','bristol_nature'),('bristol','bristol_sercop'),('solihull','solihull_proclass'),('oklahoma','oklahoma_proxy_k50'),('oklahoma','oklahoma_proxy_k200'),('moneydata','moneydata_category')]
    for sid,scheme in examples:
        df=purity.filter((pl.col('source_id')==sid)&(pl.col('scheme')==scheme))
        if df.height:
            r=df.row(0,named=True)
            add(f'For {scheme}, {r["supported_transactions"]:,} labeled card transactions meet merchant support N>=20; {percent(r["high_share_supported"])} occur at merchants with majority-label share >=0.9, with support coverage {percent(r["support_coverage_of_valid"])}','purity_summary.csv')
    weak=read('coverage_by_group.csv')
    add(f'{weak.filter(pl.col("weakly_represented")).height:,} of {weak.height:,} official MCC groups have fewer than 100 linked institutional-card transactions or fewer than 20 merchant keys','coverage_by_group.csv')
    review=read('mcc_needs_review.csv');add(f'{review.height:,} source/normalized-MCC-description combinations require manual review before candidate codes can be treated as accepted labels','mcc_needs_review.csv')
    (OUT/'KEY_FINDINGS.md').write_text('# Key findings\n\nAll statements below are generated from full-source computed tables. Purity is empirical within-merchant label concentration, not measured prediction accuracy. Scheme denominators overlap and must not be summed.\n\n'+'\n\n'.join(f'{i}. {line}' for i,line in enumerate(findings,1))+'\n',encoding='utf-8')
    # DATA CARD: source-specific composition is programmatically generated.
    rows=[]
    for r in reconciliation.to_dicts():
        sid=r['source_id'];cfg=configs[sid];lab=coverage.filter(pl.col('source_id')==sid).row(0,named=True)
        rows.append(f'| {sid} | {cfg["publisher"]} | {cfg["country"]} / {cfg["org_type"]} | {r["canonical_rows"]:,} | {r["date_min"]} to {r["date_max"]} | {cfg["license"]} | {lab["numeric_code_rows"]:,} numeric MCC; {lab["description_rows"]:,} descriptions |')
    card=f'''# Datasheet for the supplied card-related transaction collection

## Motivation

Research questions S1-S7 concern effective sample size, available label systems, statement-descriptor evidence, label agreement, purchase-label concentration, distribution shifts and institutional-card coverage. No predictive model, custom spending taxonomy, annotated labels, or train/test split is produced. Proxy product clustering is descriptive and uses the explicitly authorized fallback.

## Composition

There are {total:,} canonical records and {cards:,} records conservatively classified card_txn. Reader records ({raw:,}) reconcile to canonical plus {excluded:,} explicit exclusions. There are {reconciliation.height:,} sources: public institutional payment disclosures plus one academic individual-bank-account dataset. Sources are not independent population samples; transactions, descriptors, normalized merchants, and labels have different effective sample sizes. MoneyData is a consumer reference rather than a corporate-card source. IPO contributes only inventory, scope and cross-source overlap diagnostics.

| Source | Publisher | Geography / institution | Canonical rows | Parsed date bounds | Licence | Available MCC rows |
| --- | --- | --- | ---: | --- | --- | --- |
{chr(10).join(rows)}

Dates are observed parsed fields and can include source anomalies; bounds do not prove continuous coverage. All purchase-label schemes are listed in `tables/purchase_label_coverage.csv`. See original source URLs in configuration and `tables/source_metadata.csv`.

## Collection Process

The user supplied local downloads and already merged source files. This study has no verified complete collection history before those files. The exact original files, byte sizes, SHA-256 values, headers, row counts, and parse errors are in `manifest.csv`. Download/source metadata embedded in DWP, IPO and Eden is retained in the private canonical data. Previously generated folder/global CSV concatenations are excluded from input selection. The Indonesia source is outside the specified eleven-source study.

Publicly accessible does not imply an open redistribution licence. Source licences are recorded as unspecified unless established from supplied provenance. MCC factual references cite current Visa, historical Citi, and current Mastercard primary publications and their page/hash provenance; copyright and historical/network differences are explicit in `reference/README.md`.

## Preprocessing

Raw files are read-only. Source-specific column priorities, populated-column variants, date parsing conventions and classification rules are versioned in YAML. Every retained record has its original source file, worksheet and parsed-record row address; excluded rows have reason codes. Oklahoma's personal columns are omitted at reader projection. Address-like purpose labels are masked before persistence. Raw merchant strings remain unchanged in private derived data; strict/loose keys, parsed dates/amounts, reference links, record types and official groups are separate fields. There is no deduplication. All operational decisions and affected counts are in `DECISIONS.md`.

## Uses

Suitable for descriptive research on the **supplied extracts**, label systems and evidence limits, subject to linkage and entity-resolution sensitivity. Unsuitable for population-level consumer-spending prevalence, verified receipt-level ground truth, fraud scoring, individual profiling, causal issuer comparisons or an established model-performance ceiling. Purity calculations condition on label coverage, merchant support and institutional label granularity; TF-IDF clusters are unvalidated product proxies. Candidate MCC matches require expert review.

## Distribution

Only code, aggregate tables, report text, and non-personal factual reference snapshots are versioned. Original data and private `derived/` files are excluded from Git and are not published. `annotation/` is internal-only and excluded from Git. Public tables use stable opaque merchant IDs and repeated, screened examples. The automated disclosure check covers full cardholder-name patterns, surname-plus-initial combinations and street/number patterns; it is not a guarantee against every conceivable re-identification attack. Existing user datasets and earlier CSV outputs are preserved and are outside the new publication artifact directory.

## Maintenance

Maintainer: local project owner; contact and release policy unspecified. Access date for reference provenance is {ACCESS_DATE}. Reproduce with `python -m data_profile.run --all`; the pipeline uses seed 42 and pinned MCC facts. Preserve original hashes, dependency versions and source snapshots; never merge new downloads into a published result without rerunning reconciliation and disclosure tests. Manual review lists are generated, not silently resolved. No claims of future maintenance or dataset completeness are made.
'''
    (OUT/'DATA_CARD.md').write_text(card,encoding='utf-8')
    table('source_metadata.csv',[{'source_id':s,'publisher':c['publisher'],'country':c['country'],'org_type':c['org_type'],'source_url':c['source_url'],'license':c['license']} for s,c in configs.items()])
    # Every major transform has an impact count and an auditable rule.
    analysis=pl.scan_parquet(DERIVED/'analysis.parquet')
    changes=collect(analysis.group_by('source_id').agg(pl.len().alias('rows'),(pl.col('merchant_raw')!=pl.col('key_strict')).sum().alias('strict_key_changed'),(pl.col('key_strict')!=pl.col('key_loose')).sum().alias('loose_key_changed'),(pl.col('key_loose')=='').sum().alias('empty_loose_keys'),(pl.col('intermediary')!='').sum().alias('intermediary_separated'),pl.col('address_redacted').sum().alias('address_redacted_rows'),pl.col('merchant_masked').sum().alias('merchant_masked_rows'),(pl.col('date_parse_method')=='excel_serial').sum().alias('excel_serial_dates'),(pl.col('date_parse_method')=='unparsed').sum().alias('unparsed_dates'),(pl.col('date_semantics')=='unknown').sum().alias('unknown_date_semantics'),(pl.col('record_type')!='card_txn').sum().alias('non_card_records'),(pl.col('mcc_code')!='').sum().alias('original_numeric_codes'),((pl.col('mcc_code')=='')&(pl.col('mcc_analysis')!='')).sum().alias('description_linked_codes')))
    table('transformation_impacts.csv',changes)
    from .observations import run as check_observations
    check_observations()
    decisions=[
      ('Input selection',raw,'Only original files in eleven declared source folders; exclude Indonesia, prior worksheet CSV conversions, folder merges and global merge to avoid repeated counting.'),
      ('Non-destructive derivation',total,'Original strings/dates/amounts remain in original files. Parsed values and keys are separate fields in private canonical/analysis Parquet; no cleaned raw-data release.'),
      ('Oklahoma personal columns',int(reconciliation.filter(pl.col('source_id')=='oklahoma')['raw_rows'][0]),'Drop Last Name, First Initial and Cardholder Name at reader projection; do not persist any identifier list. Raw-row duplicate fingerprint excludes those personal fields.'),
      ('Solihull address masking',int(changes['address_redacted_rows'].sum()),'Mask street/number pattern as ADDRESS_REDACTED before storing labels; never print original purpose examples; masked label events excluded from purity.'),
      ('Unknown date meaning',int(changes['unknown_date_semantics'].sum()),'Do not infer statement dates from heaping; retain unknown when field semantics are unverified.'),
      ('Date convention',total,'USA ambiguous slash dates use month-first, UK use day-first; ISO and typed worksheet dates take precedence; UK-invalid-first alternatives may parse under the other convention. ISO-typed Excel dates are not reinterpreted.'),
      ('MoneyData amount sign',int(reconciliation.filter(pl.col('source_id')=='moneydata')['canonical_rows'][0]),'Debits become negative, credits positive; original Debit Amount and Credit Amount remain in the original workbook. These negative amounts denote bank outflows, not refunds, and are not comparable to a public-source negative/refund rate.'),
      ('Excel serial date conversion',int(changes['excel_serial_dates'].sum()),'Recognize numeric serials 20000-60000; Excel origin 1899-12-30. Other outlier dates remain visible, not corrected.'),
      ('Strict merchant key',int(changes['strict_key_changed'].sum()),'NFKC uppercase; longest configured prefix first; remove 3+-digit runs, store-number patterns and alphanumeric reference tokens; preserve raw merchant. A reference-only Amazon marketplace descriptor retains its marketplace identity.'),
      ('Loose merchant aliases',int(changes['loose_key_changed'].sum()),'Only explicit merchant_aliases.yaml patterns and six supplied source-city suffixes; alias effect counts below; dictionary entries are hypotheses, not verified entity matches.'),
      ('MCC description normalization',int(coverage['description_rows'].sum()),'NFKC uppercase, punctuation/space collapse and AND/& equivalence. Raw spelling is preserved.'),
      ('Description-to-code linkage',int(changes['description_linked_codes'].sum()),'Exact, normalized, unambiguous observed code-description, unique >=16-character prefix, then fuzzy >=95 with margin >=5; every other candidate remains needs_review. Inferred labels never overwrite source codes.'),
      ('Reference validity',int(changes['original_numeric_codes'].sum()),'Current Visa, historical Citi and explicit Mastercard facts retain network/version status. Unlisted or historical-only is review-worthy, not proof of source corruption.'),
      ('Stockport label scheme',int(reconciliation.filter(pl.col('source_id')=='stockport')['canonical_rows'][0]),'Purpose-present rows use internal category; purpose-absent rows with category are MCC candidates. Do not impose unverified calendar-year cutoffs. Exact normalized MCC descriptions in supplier field are masked.'),
      ('Primary card filter',int(changes['non_card_records'].sum()),'Supplier payments, zero returns, fees, adjustments, transfers, cash and unknown records stay canonical but are excluded from primary card-only label/purity/coverage analysis.'),
      ('Purity support',int(purity['supported_transactions'].sum()),'Support N>=20 separately per merchant/source/scheme; event counts across schemes overlap and are not a unique-transaction total. Majority bands: >=.9, [.7,.9), <.7. Report support coverage.'),
      ('Purity uncertainty',int(purity['supported_merchants'].sum()),'1000 empirical i.i.d. bootstrap replicates, seed42-derived per identity. Normalize by fixed observed within-merchant label count; clustering, key and temporal dependence uncertainty are outside these intervals.'),
      ('Annotation sample',800,'Unlabelled, internal-only, distinct source/descriptor strings with >=20 within-source merchant support and identifier/address screening; deterministic source/group/length/prefix round-robin; unequal inclusion, no prevalence claim.'),
      ('Duplicate retention',total,'No duplicates removed. All counts are audit statistics; personal-field-excluded exact fingerprints are clearly identified for Oklahoma.'),
    ]
    table('decision_impacts.csv',[{'decision':name,'affected_rows_or_events':count,'rule':rule} for name,count,rule in decisions])
    excluded_rows=read('exclusions.csv')
    extext='\n'.join(f'| {r["source_id"]} | {r["reason"]} | {r["rows"]:,} |' for r in excluded_rows.to_dicts())
    variant=read('schema_variants.csv');varianttext='\n'.join(f'| {r["source_id"]} | `{r["schema_variant"]}` | {r["rows"]:,} |' for r in variant.to_dicts())
    decisiontext='\n\n'.join(f'### {name}\n\nAffected reader rows/records/events: {count:,}. {rule}' for name,count,rule in decisions)
    eden=read('eden_file_classification.csv');edentext='\n'.join(f'| `{r["upstream_source_file"]}` | {r["record_type"]} | {r["rows"]:,} |' for r in eden.to_dicts())
    (OUT/'DECISIONS.md').write_text(f'''# Decisions and affected counts

All impact counts are computed; events can overlap across schemes. Defaults that cannot be validated remain explicit assumptions or unknowns.

{decisiontext}

## Explicit exclusions

| Source | Reason | Reader rows |
| --- | --- | ---: |
{extext}

## Schema variants and column priorities

`data_profile/config/sources/*.yaml` specifies ordered fallback columns and variant rules. Every populated-column signature is counted below; fallback never moves a raw cell or overwrites the source. Different valid values in fallback candidates are not silently reconciled; variant-level field coverage and reviews expose uncertainty.

| Source | Variant | Canonical records |
| --- | --- | ---: |
{varianttext}

## Eden file classification

Only the two explicitly identified supplier-payment period files are classified supplier_payment; the other supplied filenames denote procurement-card disclosures or merchant reports. Unknown/missing merchant/date/amount combinations remain record_type unknown rather than being forced into card_txn.

| Upstream file | Record type | Rows |
| --- | --- | ---: |
{edentext}

## Reference, proxy and disclosure limits

See `reference/README.md` for pinned sources and copyright. Oklahoma proxy categories use TF-IDF character 3-5 grams, a seeded 64-component TruncatedSVD projection with L2 normalization, then frequency-weighted MiniBatchKMeans, k=50 and k=200, seed42, max_features=20000, max_iter=150, n_init=5, batch_size=4096. Vocabulary and IDF are fitted on the most frequent up to 50,000 unique informative descriptions to bound memory; all informative items are transformed/clustered. The occurrence coverage of that fit subset is reported. Preliminary direct sparse-distance clustering was rejected because of severe cluster concentration. The projection was added in response to that methodological failure, not to optimize the purity result; final largest-cluster shares and explained variance are computed in `tables/oklahoma_clustering_summary.csv`. Requested MiniLM-L6-v2 was not cached, so the explicitly authorized fallback is used. Placeholders and per-transaction dominant/basket rules are in `derived/cluster_method.json` and `tables/oklahoma_item_placeholders.csv`. Clusters are not a validated product taxonomy and need semantic review. Primary findings never pool label schemes as though their event counts were independent transactions.

Ambiguous common surnames can occur in ordinary English and institutional/company descriptions. Disclosure screening tests complete normalized cardholder names and surname-plus-initial combinations, not every standalone English word that can also be a surname; such an all-word test would be scientifically uninterpretable. This operational limitation is reported, not presented as complete anonymization. Oklahoma personal columns are absent from all derived analytical schemas. The prior user-provided raw files and pre-existing concatenations remain untouched and are not claimed to be anonymized by this task.
''',encoding='utf-8')
    # QA: no source or derived row loss, source hashes, event integrity, and parsers.
    subprocess.run([sys.executable,'-m','unittest','discover','-s','data_profile/tests','-v'],cwd=ROOT,check=True)
    from .ingest import verify_reconciliation
    verify_reconciliation()
    baseline=json.loads((DERIVED/'raw_hash_baseline.json').read_text())
    unchanged=0
    for cfg in settings:
        for path in source_files(cfg):
            key=str(path.relative_to(ROOT)).replace('\\','/')
            assert file_hash(readable_path(path))==baseline[key],key
            unchanged+=1
    label_duplicate=collect(pl.scan_parquet(DERIVED/'purchase_labels.parquet').group_by('source_id','source_file','source_sheet','source_row','scheme').len().filter(pl.col('len')>1))
    assert label_duplicate.height==0,'Duplicate labels per record and scheme'
    null_identity=collect(analysis.select(pl.col('source_file').is_null().sum(),pl.col('source_row').is_null().sum())).row(0)
    assert sum(null_identity)==0
    environment={'python':sys.version,'platform':platform.platform(),'packages':{},'seed':42,'access_date':ACCESS_DATE}
    for package in ['polars','pyarrow','numpy','scipy','scikit-learn','matplotlib','PyYAML','rapidfuzz','openpyxl','pdfplumber']:
        try:environment['packages'][package]=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:environment['packages'][package]='unavailable'
    json_save(OUT/'environment.json',environment)
    timings=json.loads((DERIVED/'stage_timings.json').read_text())
    qa={'status':'passed','reconciled_sources':reconciliation.height,'source_data_files_hash_unchanged':unchanged,'canonical_rows':total,'reader_rows':raw,'excluded_rows':excluded,'duplicate_purchase_label_events':label_duplicate.height,'nonmissing_provenance':True,'parser_test_suite':'passed','seed':42}
    json_save(OUT/'quality_checks.json',qa)
    report('10_quality_and_limitations.md','S1-S7','Unit tests, exact reconciliation, unchanged-input hashes, label-event uniqueness, provenance completeness and automatic disclosure screening.','Privacy tests cover specified patterns and known identifiers, not every possible personal name or re-identification risk. Manual review is still needed for ambiguous codes, schema semantics and qualitative annotation examples.',f'{reconciliation.height} sources reconcile, {unchanged} data-file hashes match their starting values, and {total:,} canonical records have complete source provenance. See `quality_checks.json` and `privacy_checks.json`. Descriptive bootstrap intervals, fuzzy reference linkage and proxy clusters do not replace independent validation.')
    artifacts=[]
    for path in sorted(OUT.rglob('*')):
        if path.is_file() and path.suffix in {'.csv','.md','.pdf','.png','.json'} and path.name!='README.md':
            artifacts.append(f'- [{path.relative_to(OUT).as_posix()}]({path.relative_to(OUT).as_posix()})')
    timing_text='\n'.join(f'- {stage}: {seconds:.1f} seconds' for stage,seconds in timings.items())
    (OUT/'README.md').write_text(f'''# Reproducible full-source profiling artifacts

Main entry points: [Key findings](KEY_FINDINGS.md), [Data card](DATA_CARD.md), [Decision ledger](DECISIONS.md), [Input manifest](manifest.csv), [Quality checks](quality_checks.json), [Disclosure checks](privacy_checks.json).

## Reproduction

From the project root, use Python with `data_profile/requirements.txt` installed:

```powershell
python -m data_profile.run --all
python -m unittest discover -s data_profile/tests -v
```

`--stage ingest|labels|merchants|consistency|purity|descriptive|annotation|finalize` reruns a stage. `--all --reuse-canonical` rechecks reconciliation and skips raw ingestion. `--no-commit` omits stage commits in restricted environments. Stages are sequential; no label analysis runs before reconciliation. All randomness uses seed 42. The code uses bounded row buffers, streaming Parquet scans, and conservative worker limits. Pinned reference facts prevent unnoticed online-list changes. Stage commits apply only to code and public-safe outputs; originals, private derived data, and annotation material are ignored by Git.

Original files stay in their existing `real-world-datas/<source folder>/` locations; no `data/raw/` relocation was made. `derived/canonical.parquet`, `purchase_labels.parquet`, `analysis.parquet` and other intermediates are **private and unpublished**. The supplied Indonesia folder and all earlier generated concatenations/conversions are excluded. A verified readable cache is used only when Windows denies direct reads of supplied Eden/Solihull/Sunderland files; hashes must match original snapshots. Reproduction on another machine should grant read access to originals rather than copy this machine-specific cache.

**`annotation/` is internal-only.** It contains an unlabelled sample and draft protocol, is not committed, and is not cleared for public release. Generated merchant examples require repeated support and identifier/address screening. These checks do not certify total anonymity. All reports are English. Figures use one style file, native units, PNG at 300 dpi and vector PDF.

## Recorded runtime and environment

{timing_text}

These are measured execution times, not estimates; finalized stage duration is added to run_state after completion. Exact package versions are in `environment.json`. System Python was used because the bundled runtime lacks the requested scientific/Parquet/clustering packages. No predictive model was trained; unsupervised proxy clustering is a requested descriptive step.

## Artifact index

{chr(10).join(artifacts)}
''',encoding='utf-8')
    from .artifact_qa import run as artifact_qa
    artifact_qa()
    redactions=sanitize_text_outputs()
    json_save(OUT/'disclosure_redactions.json',redactions)
    result=privacy_check()
    print(f'FINAL QA PASSED: {unchanged} raw hashes; {total:,} canonical rows; {result["files_scanned"]} text/PDF files privacy-scanned',flush=True)
