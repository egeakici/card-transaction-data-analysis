"""Source contracts, immediately projected readers, and canonical records."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import openpyxl
import yaml

from .common import ROOT, CONFIG, parse_amount, parse_date, merchant_keys, normalize_label, redact_address, split_card, split_mcc

SOURCE_META = {
    'delaware': ('Delaware Open Data - USA','USA','state',2251300),
    'oklahoma': ('Oklahoma OpenGov Data - USA','USA','state',900000),
    'indiana': ('Indiana MPH Data - USA','USA','state',284100),
    'sunderland': ('Sunderland Purchase Card Data - UK','UK','council',255100),
    'solihull': ('Solihull Purchase Card Data - UK','UK','council',112000),
    'stockport': ('Stockport Purchase Card Data - UK','UK','council',34000),
    'moneydata': ('Mendeley Laramee Bank Data - UK','UK','academic',6500),
    'bristol': ('Bristol Purchase Card Data - UK','UK','council',4000),
    'eden': ('Eden Council Spending Data - UK','UK','council',1200),
    'dwp': ('DWP Government Card Data - UK','UK','central_gov',8000),
    'ipo': ('IPO Government Spending Data - UK','UK','central_gov',24),
}
PII_COLUMNS = {'Last Name','First Initial','Cardholder Name'}
PUBLISHERS = {
    'delaware':'State of Delaware (Delaware Open Data)',
    'oklahoma':'State of Oklahoma (OpenGov transparency portal)',
    'indiana':'State of Indiana (Management Performance Hub)',
    'sunderland':'Sunderland City Council',
    'solihull':'Solihull Metropolitan Borough Council',
    'stockport':'Stockport Council',
    'moneydata':'MoneyVis research authors (hosted by Mendeley Data)',
    'bristol':'Bristol City Council',
    'eden':'Eden District Council (historical publisher)',
    'dwp':'UK Department for Work and Pensions',
    'ipo':'UK Intellectual Property Office',
}
MAPS = {
 'delaware': dict(merchant=['merchant'], date=['trans_dt'], amount=['merchandise_amt'], mcc_desc=['cat_descr'], org=['dept_name'], id=[], fiscal_year=['fiscal_year'], fiscal_period=['fiscal_period']),
 'oklahoma': dict(merchant=['Merchant'],date=['Transaction Date'],posting=['Posting Date'],amount=['Amount'],mcc_desc=['MCC Description'],org=['Agency Number'],id=['Row ID'],fiscal_year=[],fiscal_period=[],labels={'oklahoma_item_desc':['Item Description']}),
 'indiana': dict(merchant=['Merchant Name'],date=['Transaction Date'],amount=['Transaction Amount'],mcc_desc=['Merchant Category Code'],org=['Agency Name'],id=['Transaction ID'],fiscal_year=['Fiscal Year'],fiscal_period=[]),
 'sunderland': dict(merchant=['MCH.MERCHANT NAME - ORIGINAL','Supplier'],date=['Transaction Date','TRANS DATE'],posting=['FIN.POSTING DATE'],amount=['FIN.PRIMARY TRANSACTION AMOUNT','Transaction Value','TRANSACTION AMOUNT'],mcc_desc=['MCH.MCC DESCRIPTION','Merchant Category/Summary','MERCHANT CATEGORY SUMMARY','MERCHANT CATERGORY/ SUMMARY'],org=['ACC.REPORTS TO INTERMEDIATE LEVEL 3 NAME LINE 1','Directorate','ACC.ACCOUNT NAME'],id=['FIN.FINANCIAL TRANSACTION IDENTIFIER','Transaction Number','TRANS NUMBER','TRAN NUMBER','TRANSACTION NO']),
 'solihull': dict(merchant=['Supplier Name'],date=['Date'],amount=['Net Amount','Amount'],org=['Directorate','Service Area Categorisation','Cost Centre Description'],id=['Transaction Number'],labels={'solihull_proclass':['Procurement Classification: ProClass Label'],'solihull_purpose':['Purpose of Spend'],'solihull_detailed_expenses':['Detailed Expenses Type']}),
 'stockport': dict(merchant=['Supplier (Beneficiary)'],date=['Purchase Date'],posting=['Settlement Date'],amount=['Net Amount (£)','Gross Amount (£)'],org=['Department where exp. Incurred','Service Category Label'],id=['Transaction Number'],labels={'stockport_purpose':['Purpose of Expenditure']}),
 'moneydata': dict(merchant=['Transaction Description'],date=['Transaction Date'],amount=[],org=[],id=['Transaction Number'],labels={'moneydata_category':['Category']}),
 'bristol': dict(merchant=['Supplier Details (Beneficiary) '],date=['Transaction Date'],amount=['Gross Amount Including VAT'],mcc_desc=['Merchant Category'],org=['Cardholder Directorate','Cost Centre Name'],id=[],labels={'bristol_nature':['Nature of Expenditure'],'bristol_sercop':['Expenditure group (SERCOP)']}),
 'eden': dict(merchant=['Merchant','Merchant Name','Supplier Name'],date=['Date Occurred','Date','date','Payment Date'],posting=['Date Posted'],amount=[' Amount','Original Amount','Net Amount','Settlement Amount','Amount (£)','Amount'],mcc_desc=['MCC Description','Mcc Description','mcc description','MCC DESCRIPTION','Mcc description'],mcc=['MCC'],org=['Department','Organisational Unit','Expense Area'],id=['Transaction Number'],labels={'eden_purpose':['Purpose','Extended Description','Expense Type']}),
 'dwp': dict(merchant=['merchant_name'],date=['date'],amount=['amount'],mcc=['merchant_category_code'],org=[],id=['transaction_reference'],labels={'dwp_purpose':['description','FIN.Expense Description','reason','Comment']}),
 'ipo': dict(merchant=['Supplier'],date=['Date'],amount=['Amount'],org=['Expense area','Entity'],id=['Transaction number'],labels={'ipo_expense_type':['Expense type'],'ipo_description':['Description']}),
}


def initialize_configs():
    directory = CONFIG/'sources'
    directory.mkdir(parents=True, exist_ok=True)
    for sid, (folder,country,org,approx) in SOURCE_META.items():
        path = directory/f'{sid}.yaml'
        if path.exists():
            continue
        data = {'source_id':sid,'folder':f'real-world-datas/{folder}','country':country,'org_type':org,
                'reported_approximate_rows':approx, 'license':'unspecified', 'publisher':PUBLISHERS[sid], 'dataset_name':folder,
                'original_extensions':['.xlsx'] if sid in {'bristol','moneydata'} else ['.csv'],
                'exclude_patterns':['birlesik_tam.csv','*__*.csv'], 'column_priority':MAPS[sid],
                'variant_rules': variant_rules(sid), 'date_order':'month_first' if country=='USA' else 'day_first',
                'date_semantics':'unknown' if sid in {'delaware','eden','ipo','dwp','solihull'} else 'transaction'}
        readme=ROOT/data['folder']/'README.md'
        text=readme.read_text(encoding='utf-8-sig') if readme.exists() else ''
        match=re.search(r'https?://\S+', text)
        data['source_url']=match.group() if match else 'unspecified'
        path.write_text(yaml.safe_dump(data,sort_keys=False,allow_unicode=True),encoding='utf-8')


def variant_rules(sid):
    return {
      'sunderland':['bank_export: MCH.MERCHANT NAME - ORIGINAL populated','legacy_merchant: Supplier populated','other: populated-column signature'],
      'solihull':['legacy_cost_centre: Detailed Expenses Type or Expenses Code populated','proclass: Procurement Classification: ProClass Label populated','other'],
      'stockport':['internal: Purpose of Expenditure populated','mcc_candidate: purpose absent and Procurement (Merchant) Category populated','unresolved: both absent'],
      'eden':['upstream filename in kaynak_dosya plus populated-column signature','supplier_payment: period7_2016.csv or period8_2016.csv'],
      'dwp':['numeric_mcc: merchant_category_code populated','purpose_only: no numeric MCC'],
    }.get(sid,['original column signature; workbook sheet identity retained'])


def configurations():
    initialize_configs()
    return [yaml.safe_load(p.read_text(encoding='utf-8')) for p in sorted((CONFIG/'sources').glob('*.yaml'))]


def source_files(config):
    folder=ROOT/config['folder']
    if '.xlsx' in config['original_extensions']:
        return sorted(folder.glob('*.xlsx'))
    return sorted(p for p in folder.glob('*.csv') if p.name!='birlesik_tam.csv' and '__' not in p.stem)


def readable_path(original):
    try:
        with original.open('rb'):
            pass
        return original
    except PermissionError:
        cached=ROOT/'.data_processing/source_access'/original.name
        manifest=json.loads((ROOT/'.data_processing/restricted_original_hashes.json').read_text(encoding='utf-8-sig'))
        expected=next(x['Hash'].lower() for x in manifest if Path(x['Path'])==original)
        from .common import file_hash
        assert file_hash(cached)==expected, 'Read-access copy differs from the original snapshot'
        return cached


def read_records(config, path):
    """Yield original row numbers; personal columns never enter yielded records."""
    sid=config['source_id']
    if path.suffix.lower()=='.xlsx':
        book=openpyxl.load_workbook(path,read_only=True,data_only=True)
        for sheet in book:
            if sid=='moneydata' and sheet.title=='Description of Categories':
                for n,row in enumerate(sheet.values,1):
                    yield sheet.title,n,{},'documentation' if any(v is not None for v in row) else 'blank'
                continue
            header_n=3 if sid=='bristol' else 1
            header=None
            for n,row in enumerate(sheet.values,1):
                if n<header_n:
                    continue
                if n==header_n:
                    header=[str(v) if v is not None else f'__empty_{i}' for i,v in enumerate(row)]
                    continue
                record={h: format_cell(v) for h,v in zip(header,row) if not h.startswith('__empty_')}
                yield sheet.title,n,record,'' if any(record.values()) else 'blank'
        book.close()
    else:
        with readable_path(path).open(encoding='utf-8-sig',newline='') as f:
            if sid=='oklahoma':
                next(f);next(f)
            reader=csv.DictReader(f)
            for n,raw in enumerate(reader,4 if sid=='oklahoma' else 2):
                record={k:(v if v is not None else '') for k,v in raw.items() if k not in PII_COLUMNS}
                yield '',n,record,'' if any(record.values()) else 'blank'


def format_cell(value):
    if value is None:
        return ''
    if hasattr(value,'isoformat'):
        return value.isoformat()
    return str(value)


def first(record, names):
    for name in names:
        value=record.get(name,'')
        if value is not None and str(value).strip():
            return str(value),name
    return '', ''


def signature(record):
    return hashlib.sha256('|'.join(k for k,v in record.items() if str(v or '').strip()).encode()).hexdigest()[:12]


def canonical_record(config, path, sheet, n, record):
    sid=config['source_id']; mapping=config['column_priority']; country=config['country']
    get=lambda field:first(record,mapping.get(field,[]))[0]
    merchant=get('merchant'); date_raw,date_field=first(record,mapping.get('date',[])); amount_raw,amount_field=first(record,mapping.get('amount',[]))
    posting_raw=get('posting')
    variant=signature(record)
    if sid=='sunderland':
        prefix='bank_export' if record.get('MCH.MERCHANT NAME - ORIGINAL') else 'legacy_merchant' if record.get('Supplier') else 'unresolved'
        variant=prefix+'_'+variant
    elif sid=='solihull':
        prefix='legacy_cost_centre' if record.get('Detailed Expenses Type') or record.get('Expenses Code') else 'proclass' if record.get('Procurement Classification: ProClass Label') else 'unresolved'
        variant=prefix+'_'+variant
    elif sid=='stockport':
        prefix='internal' if record.get('Purpose of Expenditure','').strip() else 'mcc_candidate' if record.get('Procurement (Merchant) Category','').strip() else 'unresolved'
        variant=prefix+'_'+variant
    elif sid=='dwp':
        variant=('numeric_mcc' if record.get('merchant_category_code','').strip() else 'purpose_only')+'_'+variant
    elif sid=='eden':
        variant=record.get('kaynak_dosya','unknown')+'|'+variant
    if sid=='solihull' and not merchant and not date_raw and not amount_raw:
        return None, [], 'nontransaction_note'
    if normalize_label(merchant) in {'SUPPLIER NAME','MERCHANT NAME','SUPPLIER','TRANSACTION DESCRIPTION'} and normalize_label(date_raw) in {'DATE','TRANSACTION DATE','PURCHASE DATE','TRANS DT'}:
        return None, [], 'embedded_header'

    txn_date,date_method=parse_date(date_raw,country)
    posting_date,posting_method=parse_date(posting_raw,country)
    if not txn_date and posting_date:
        txn_date=posting_date; date_field='posting_fallback'; date_method=posting_method
    semantics='posting' if date_field=='posting_fallback' or sid=='sunderland' and date_field=='FIN.POSTING DATE' else config['date_semantics']
    amount=parse_amount(amount_raw)
    if sid=='moneydata':
        debit=parse_amount(record.get('Debit Amount')); credit=parse_amount(record.get('Credit Amount'))
        amount=-debit if debit is not None else credit
        amount_field='Debit Amount' if debit is not None else 'Credit Amount'
        amount_raw=record.get(amount_field,'')

    mcc_code=get('mcc').strip(); mcc_desc=get('mcc_desc'); labels=[]
    if mcc_code:
        mcc_code=re.sub(r'\.0+$','',mcc_code)
        if mcc_code.isdigit():mcc_code=mcc_code.zfill(4)
    if sid=='bristol':
        mcc_code,mcc_desc=split_mcc(mcc_desc)
    if sid=='stockport':
        category=record.get('Procurement (Merchant) Category','')
        if variant.startswith('internal'):
            labels.append(('stockport_internal_category',category))
        elif variant.startswith('mcc_candidate'):
            mcc_desc=category
    for scheme,names in mapping.get('labels',{}).items():
        value,_=first(record,names)
        if value:
            value=redact_address(value)
            labels.append((scheme,value))
            if scheme=='solihull_proclass':
                match=re.match(r'^(\d{6})\s*[-:]\s*(.*)',value)
                if match:
                    labels.extend([('solihull_proclass_code',match.group(1)),('solihull_proclass_top',match.group(1)[:2])])

    record_type='card_txn'
    merchant_upper=merchant.upper()
    if sid=='eden' and re.fullmatch(r'period[78]_2016\.csv',record.get('kaynak_dosya',''),re.I):
        record_type='supplier_payment'
    elif sid=='ipo' and ('zero' in record.get('record_type','').lower() or 'ZERO RETURN' in ' '.join(record.values()).upper()):
        record_type='zero_return'
    elif 'FRAUD' in merchant_upper or re.search(r'\b(?:ADJUSTMENT|REVERSAL)\b',merchant_upper):
        record_type='adjustment'
    elif re.search(r'\b(?:AGENT FEE|CASH ADVANCE FEE|SERVICE CHARGE|PURCH FEE)\b',merchant_upper):
        record_type='fee'
    elif sid=='moneydata' and (re.search(r'SAVE THE CHANGE|ESAVINGS|TRANSFER',merchant_upper) or record.get('Transaction Type')=='TFR'):
        record_type='transfer'
    elif sid=='moneydata' and (record.get('Transaction Type') in {'CPT','C/P','CASH'} or 'CASH WITHDRAWAL' in merchant_upper):
        record_type='cash'
    elif not merchant or not txn_date or amount is None:
        record_type='unknown'

    issuer,card_type=split_card(record.get('Pcard or Tcard',''))
    analysis_merchant=merchant
    location_fragment=''
    if sid=='dwp' and re.search(r'\S\s{3,}\S',merchant):
        parts=re.split(r'\s{3,}',merchant,maxsplit=1)
        analysis_merchant,location_fragment=parts[0],parts[1]
    strict,loose,intermediary=merchant_keys(analysis_merchant)
    masked_address=any(v=='ADDRESS_REDACTED' for _,v in labels)
    row = {
       'source_id':sid,'source_file':str(path.relative_to(ROOT)).replace('\\','/'),'source_sheet':sheet,'source_row':n,
       'upstream_source_file':record.get('kaynak_dosya',record.get('source_file','')),
       'upstream_source_url':record.get('source_url',''),'upstream_source_title':record.get('source_title',''),
       'upstream_line_end':record.get('source_line_end',''),
       'schema_variant':variant,'country':country,'org_type':config['org_type'], 'issuer':issuer,'card_type':card_type,
       'txn_date':txn_date or '', 'date_semantics':semantics,'date_parse_method':date_method,'date_raw':date_raw,'date_field':date_field,
       'posting_date':posting_date or '', 'fiscal_year':get('fiscal_year'), 'fiscal_period':get('fiscal_period'),
       'amount':amount,'amount_field':amount_field,'currency':'USD' if country=='USA' else 'GBP','is_negative':amount is not None and amount<0,
       'merchant_raw':merchant,'merchant_masked':False,'merchant_location_fragment':location_fragment,
       'key_strict':strict,'key_loose':loose,'intermediary':intermediary,'mcc_code':mcc_code,'mcc_desc_raw':mcc_desc,
       'mcc_desc_norm':normalize_label(mcc_desc),'purchase_label_raw':labels[0][1] if labels else '',
       'purchase_label_scheme':labels[0][0] if labels else '', 'org_unit':get('org'),'record_type':record_type,
       'transaction_id':get('id'),'transaction_type':record.get('Transaction Type',''),
       'redacted_information':'REDACTED INFORMATION' in merchant_upper,
       'address_redacted':masked_address,
       'raw_row_hash':hashlib.sha256(json.dumps(record,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
    }
    identity={k:row[k] for k in ('source_id','source_file','source_sheet','source_row')}
    long_labels=[{**identity,'scheme':scheme,'value':value} for scheme,value in labels if value.strip()]
    return row,long_labels,''
