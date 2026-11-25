import csv, json, hashlib
from pathlib import Path
from itertools import islice
import openpyxl

BASE=Path(__file__).resolve().parents[1]
ROOT=BASE/'real-world-datas'
def readable(p):
    try:
        with p.open('rb'): pass
        return p
    except PermissionError:
        q=BASE/'.data_processing/source_access'/p.name
        entries=json.loads((BASE/'.data_processing/restricted_original_hashes.json').read_text(encoding='utf-8-sig'))
        expected=next(x['Hash'].lower() for x in entries if Path(x['Path']).name==p.name)
        assert hashlib.file_digest(q.open('rb'),'sha256').hexdigest()==expected
        return q

if __name__=='__main__':
    for p in ROOT.rglob('*.csv'):
        if 'FY20' in p.name and 'FY2010' not in p.name: continue
        with readable(p).open(encoding='utf-8-sig',newline='') as f:
            rows=list(islice(csv.reader(f),5))
        print(json.dumps({'file':p.relative_to(ROOT).as_posix(),'rows':rows},ensure_ascii=True))
    for p in ROOT.rglob('*.xlsx'):
        wb=openpyxl.load_workbook(p,read_only=True,data_only=True)
        print(json.dumps({'file':p.name,'sheets':[{'name':s.title,'extent':[s.max_row,s.max_column],'rows':list(islice(s.values,4))} for s in wb]},default=str,ensure_ascii=True))
        wb.close()
