"""Independent full-record checks: no source edits, row loss, or changed cells."""
import argparse,csv,json,re,time,zipfile
from collections import Counter
from itertools import zip_longest
import openpyxl
import pyarrow.parquet as pq
from inspect_inputs import BASE,ROOT,readable
from run import DEST,ANALYSIS,digest,fileid,save_json
from rules import LABELS,STATUSES

def verify_file(meta):
    rel=meta['source_file'];original=readable(ROOT/rel);out=DEST/rel
    assert digest(original)==meta['source_sha256'],('source changed',rel)
    assert digest(out)==meta['output_sha256'],('output changed',rel)
    labels=Counter();records=0;cells=0
    if meta['format']=='csv':
        with original.open(encoding='utf-8-sig',newline='') as a,out.open(encoding='utf-8-sig',newline='') as b:
            for n,(source,new) in enumerate(zip_longest(csv.reader(a),csv.reader(b)),1):
                assert source is not None and new is not None,('row count',rel,n)
                assert len(new)==meta['source_columns']+1,('column count',rel,n)
                assert new[:len(source)]==source,('changed original values',rel,n)
                assert all(v=='' for v in new[len(source):-1]),('padding',rel,n)
                if n==meta['header_record']:
                    assert new[-1]=='taxonomy_label';continue
                assert new[-1] in LABELS+STATUSES,('invalid label',rel,n,new[-1])
                labels[new[-1]]+=1;records+=1;cells+=len(source)
    else:
        a=openpyxl.load_workbook(original,read_only=True,data_only=False)
        b=openpyxl.load_workbook(out,read_only=True,data_only=False)
        assert a.sheetnames==b.sheetnames
        for ws,wn,sheetmeta in zip(a,b,meta['sheets']):
            assert (wn.max_row,wn.max_column)==(ws.max_row,ws.max_column+1),(rel,ws.title,'extent')
            for n,(source,new) in enumerate(zip_longest(ws.values,wn.values),1):
                assert source is not None and new is not None
                assert tuple(new[:-1])==tuple(source),('xlsx changed cells',rel,ws.title,n)
                if n==sheetmeta['header_record']:assert new[-1]=='taxonomy_label';continue
                assert new[-1] in LABELS+STATUSES
                labels[new[-1]]+=1;records+=1;cells+=len(source)
        a.close();b.close()
        with zipfile.ZipFile(original) as za,zipfile.ZipFile(out) as zb:
            assert za.namelist()==zb.namelist(),('ZIP entries',rel)
            for name in za.namelist():
                originalbytes=za.read(name);newbytes=zb.read(name)
                if not re.fullmatch(r'xl/worksheets/sheet\d+\.xml',name):
                    assert originalbytes==newbytes,('changed workbook part',rel,name)
                else:
                    # Includes original cell styles, types, formulas and cached values.
                    pattern=rb'<c\b[^>]*?/>|<c\b[^>]*?>.*?</c>'
                    originalcells=set(re.findall(pattern,originalbytes,re.S))
                    newcells=set(re.findall(pattern,newbytes,re.S))
                    assert originalcells.issubset(newcells),('changed original cell XML',rel,name)
    assert dict(labels)==meta['counts'],('distribution mismatch',rel)
    assert records==meta['reader_rows_excluding_header']
    audit=pq.ParquetFile(ANALYSIS/'audit'/f"{meta['file_id']}.parquet")
    ac=Counter();auditrows=0
    for batch in audit.iter_batches(columns=['taxonomy_label'],batch_size=100000):
        values=batch.column(0).to_pylist();ac.update(values);auditrows+=len(values)
    assert ac==labels and auditrows==records,('audit mismatch',rel)
    print(f'PASS {rel}: {records:,} records, {cells:,} source cells',flush=True)
    return {'source_file':rel,'records_verified':records,'source_cells_verified':cells,'original_values_preserved':True,'audit_and_distribution_reconciled':True,'xlsx_original_parts_preserved':meta['format']=='xlsx'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--watch',action='store_true');args=parser.parse_args()
    baseline=json.loads((ANALYSIS/'source_baseline.json').read_text(encoding='utf-8'))
    datafiles=[p for p in ROOT.rglob('*') if p.suffix.lower() in {'.csv','.xlsx'}]
    results={};ruleshash=digest(BASE/'taxonomy_pipeline/rules.py')
    cache=ANALYSIS/'verification_parts';cache.mkdir(exist_ok=True)
    while len(results)<len(datafiles):
        for path in sorted(datafiles):
            rel=path.relative_to(ROOT).as_posix();fid=fileid(rel);mp=ANALYSIS/'manifests'/f'{fid}.json'
            if rel in results:continue
            if not mp.exists():
                if args.watch:continue
                raise AssertionError(('missing output',rel))
            m=json.loads(mp.read_text(encoding='utf-8'))
            if m.get('rules_sha256')!=ruleshash:
                if args.watch:continue
                raise AssertionError(('stale rules',rel))
            cp=cache/f'{fid}.json'
            old=json.loads(cp.read_text(encoding='utf-8')) if cp.exists() else None
            hashes={'source_sha256':m['source_sha256'],'output_sha256':m['output_sha256'],'rules_sha256':ruleshash}
            if old and old.get('hashes')==hashes:
                assert digest(DEST/rel)==m['output_sha256']
                result=old['result'];print('REUSE verified '+rel,flush=True)
            else:
                result=verify_file(m);save_json(cp,{'hashes':hashes,'result':result})
            results[rel]=result
        if len(results)<len(datafiles):time.sleep(5)
    for item in baseline:
        path=ROOT/item['source_file'];q=readable(path)
        assert digest(q)==item['sha256'],('source hash changed',item['source_file'])
        assert path.stat().st_mtime_ns==item['source_stat_mtime_ns']
        if path.suffix.lower() not in {'.csv','.xlsx'}:assert digest(DEST/item['source_file'])==item['sha256']
    rows=list(results.values())
    report={'all_passed':True,'source_files_unchanged':len(baseline),'data_files_verified':len(rows),'records_verified':sum(x['records_verified'] for x in rows),'source_cells_verified':sum(x['source_cells_verified'] for x in rows),'file_results':rows,'restricted_read_note':'Eden/Solihull/Sunderland originals use pre-existing cached copies verified against recorded original SHA-256; original size and mtime also unchanged.'}
    save_json(ANALYSIS/'verification.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='file_results'}),flush=True)
if __name__=='__main__':main()
