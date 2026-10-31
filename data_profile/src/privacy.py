"""In-memory identifier guards; no cardholder identifier list is persisted."""
import csv
import json
import re
import io
from functools import lru_cache

from .common import ROOT,OUT,ADDRESS,normalize_label,public_merchant_id,json_save


@lru_cache(maxsize=1)
def identifiers():
    names=set();surname_initial=set()
    folder=ROOT/'real-world-datas/Oklahoma OpenGov Data - USA'
    for path in sorted(folder.glob('*.csv')):
        if path.name=='birlesik_tam.csv':continue
        with path.open(encoding='utf-8-sig',newline='') as f:
            next(f);next(f)
            reader=csv.DictReader(f)
            for row in reader:
                full=normalize_label(row.get('Cardholder Name',''))
                if len(full)>=4:names.add(full)
                last=normalize_label(row.get('Last Name',''));initial=normalize_label(row.get('First Initial',''))
                if last and initial:surname_initial.add(last+' '+initial)
    return names|surname_initial


def personal_name_hit(text):
    normalized=normalize_label(text)
    tokens=normalized.split()
    blocked=identifiers()
    for width in range(2,7):
        for i in range(len(tokens)-width+1):
            if ' '.join(tokens[i:i+width]) in blocked:return True
    return normalized in blocked


def safe_text(text):
    text=str(text or '')
    if ADDRESS.search(text):return 'ADDRESS_REDACTED'
    if personal_name_hit(text):return 'PERSON_REDACTED'
    return text


def safe_merchant(key, count):
    # Repeated keys reduce disclosure risk; the independent identifier/address
    # guard still applies. Public tables retain a stable opaque ID for linkage.
    return safe_text(key) if count>=20 else public_merchant_id(key)


def sanitize_text_outputs():
    """Redact personal patterns in cells and prose before final delivery."""
    changes=[]
    for path in sorted(OUT.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in {'.csv','.md','.json','.txt','.tsv'}:continue
        if path.name=='privacy_checks.json':continue
        text=path.read_text(encoding='utf-8-sig')
        if path.suffix=='.csv':
            rows=list(csv.reader(io.StringIO(text)))
            redacted=0
            for row in rows[1:]:
                for i,value in enumerate(row):
                    new=safe_text(value)
                    if new!=value:row[i]=new;redacted+=1
            if redacted:
                with path.open('w',encoding='utf-8',newline='') as f:
                    writer=csv.writer(f,lineterminator='\n');writer.writerows(rows)
                changes.append({'file':path.relative_to(OUT).as_posix(),'cells_redacted':redacted})
        else:
            # Only matching identifier spans are removed; ambiguous surnames
            # used as ordinary English words cannot identify a cardholder.
            original=text
            text=ADDRESS.sub('ADDRESS_REDACTED',text)
            for line in text.splitlines():
                if personal_name_hit(line):
                    # Preserve links and metadata; redact actual matching spans.
                    for name in sorted(identifiers(),key=len,reverse=True):
                        pattern=r'(?i)(?<!\w)'+r'[\s,.-]+'.join(map(re.escape,name.split()))+r'(?!\w)'
                        text=re.sub(pattern,'PERSON_REDACTED',text)
            if text!=original:
                path.write_text(text,encoding='utf-8');changes.append({'file':path.relative_to(OUT).as_posix(),'text_redacted':True})
    return changes


def privacy_check():
    failures=[];files=0
    for path in sorted(OUT.rglob('*')):
        if not path.is_file():continue
        suffix=path.suffix.lower()
        if suffix in {'.csv','.md','.json','.txt','.tsv'}:
            text=path.read_text(encoding='utf-8-sig')
        elif suffix=='.pdf':
            import pdfplumber
            with pdfplumber.open(path) as pdf:text='\n'.join(p.extract_text() or '' for p in pdf.pages)
        elif suffix=='.png':
            # Plot text is independently checked in its equivalent PDF; binary
            # PNG bytes are not a meaningful text representation.
            assert path.with_suffix('.pdf').exists(),path
            continue
        else:continue
        files+=1
        if ADDRESS.search(text):failures.append({'file':path.relative_to(OUT).as_posix(),'type':'address'})
        for line in text.splitlines():
            if personal_name_hit(line):
                failures.append({'file':path.relative_to(OUT).as_posix(),'type':'cardholder_identifier'});break
    result={'status':'passed' if not failures else 'failed','files_scanned':files,
       'cardholder_identifier_patterns':len(identifiers()),'failures':failures,
       'scope':'Exact normalized full cardholder names and surname-plus-initial combinations; street/number patterns. Standalone common surnames are ambiguous and are not evidence of a personal identity. No claim of complete anonymization of all conceivable PII.',
       'png_scope':'Equivalent PDF text checked; figures use source/category labels and opaque merchant IDs, not source personal columns.'}
    json_save(OUT/'privacy_checks.json',result)
    assert not failures,[(x['file'],x['type']) for x in failures]
    return result
