"""Reapply categories using actual captions, ignoring running page headers."""
import re
import polars as pl
from .common import CONFIG,DERIVED,OUT
from .labels import MC_URL


def refresh_groups():
    facts={};code=''
    for line in (DERIVED/'reference_cache/mastercard_lines.tsv').read_text(encoding='utf-8').splitlines():
        parts=line.split('\t',2)
        if len(parts)!=3:continue
        _,page,text=parts
        m=re.search(r'Description of MCC (\d{4}):\s*(.*)',text)
        if m:code=m.group(1)
        m=re.search(r'MCC Category\s+(?!Description)(.+)',text)
        if m and code:
            group=m.group(1).strip()
            if group=='Professional Services and Membership':group+=' Organizations'
            facts[code]=(group,page)
    df=pl.read_csv(CONFIG/'mcc_reference_snapshot.csv',infer_schema=False)
    rows=[]
    for row in df.to_dicts():
        code=row['mcc_code'];n=int(code)
        if code in facts:group,page=facts[code]
        elif 3000<=n<=3350:group,page='Airlines','78'
        elif 3351<=n<=3500:group,page='Car Rental','80'
        elif 3501<=n<=3999:group,page='Lodging','81'
        else:group,page='unknown',''
        row.update(mcc_group=group,group_page=page,group_source=MC_URL if group!='unknown' else '')
        rows.append(row)
    result=pl.DataFrame(rows,infer_schema_length=None).with_columns(pl.all().cast(pl.String))
    result.write_csv(CONFIG/'mcc_reference_snapshot.csv');result.write_csv(OUT/'reference/mcc_official.csv')
    print(f'REFERENCE GROUP QA: {len(facts)} caption-linked codes',flush=True)


if __name__=='__main__':refresh_groups()
