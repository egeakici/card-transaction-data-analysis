"""Append labels without changing source files; row-complete, resumable exports."""
import argparse, csv, hashlib, html, json, re, shutil, subprocess, sys, time, zipfile
from collections import Counter, defaultdict
from itertools import zip_longest
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape
import openpyxl
import pyarrow as pa
import pyarrow.parquet as pq

from inspect_inputs import BASE, ROOT, readable
from rules import Classifier, TAXONOMY, LABELS, STATUSES, VERSION, norm, CODE_MAP, AMBIGUOUS_CODES, GAP_CODES, MERCHANT_RULES, ITEM_RULES, PROCUREMENT_RULES, DESCRIPTION_RULES, code_label

DEST=BASE/'real-world-datas-taxonomy'
ANALYSIS=DEST/'_taxonomy_analysis'
FOLDERS={'Delaware':'delaware','Oklahoma':'oklahoma','Indiana':'indiana','Sunderland':'sunderland','Solihull':'solihull','Stockport':'stockport','Mendeley Laramee':'moneydata','Bristol':'bristol','Eden':'eden','DWP':'dwp','IPO':'ipo','Mendeley Engel':'indonesia'}
M=['merchant','merchant_name','MCH.MERCHANT NAME - ORIGINAL','Supplier Details (Beneficiary) ','Supplier (Beneficiary)','Merchant','Merchant Name','Supplier Name','Supplier','Transaction Description','Outlet']
D=['mcc_desc','cat_descr','MCH.MCC DESCRIPTION','Merchant Category/Summary','MERCHANT CATEGORY SUMMARY','MERCHANT CATERGORY/ SUMMARY','Merchant Category','MCC Description','Mcc Description','mcc description','MCC DESCRIPTION','Mcc description']
C=['merchant_category_code','MCC','Merchant Category Code']
P=['item_desc','Item Description','description','Description','FIN.Expense Description','FIN.EXPENSE DESCRIPTION','Nature of Expenditure','Purpose of Spend','Detailed Expenses Type','Purpose of Expenditure','Extended Description','Expense Type','Expense type','reason','Comment','ProductName']
PR=['Procurement Classification: ProClass Label','Procurement (Merchant) Category','Purpose']
DATES=['txn_date','Transaction Date','trans_dt','date','Date Occurred','Date','Payment Date','Purchase Date','FIN.POSTING DATE','TRANS DATE']
AMOUNTS=['amount','Amount','merchandise_amt','Transaction Amount','Gross Amount Including VAT','Transaction Value','TRANSACTION AMOUNT','FIN.PRIMARY TRANSACTION AMOUNT','Net Amount',' Amount','Original Amount','Settlement Amount','Debit Amount','Credit Amount']

def source_id(path_or_folder):
    name=str(path_or_folder)
    return next((sid for prefix,sid in FOLDERS.items() if prefix in name),'combined' if 'birlesik-veriler' in name else 'unknown')
def primary(path):
    rel=path.relative_to(ROOT); sid=source_id(rel.parts[0])
    if sid=='combined': return False
    if sid=='oklahoma': return path.parent.name=='birlesik' and re.fullmatch(r'oklahoma_FY\d{4}\.csv',path.name) is not None
    if sid in {'bristol','moneydata'}: return path.suffix.lower()=='.xlsx'
    return path.suffix.lower()=='.csv' and path.name!='birlesik_tam.csv' and '__' not in path.name
def fileid(rel): return hashlib.sha256(str(rel).encode()).hexdigest()[:16]
def digest(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def save_json(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def write_csv(p,fields,rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)

class Adapter:
    def __init__(self,header,sid):
        self.header=header; self.sid=sid
        self.index={h:i for i,h in enumerate(header)}
        def ix(names): return [self.index[n] for n in names if n in self.index]
        self.mi=ix(M); self.di=ix(D); self.ci=ix(C); self.pi=ix(P); self.pri=ix(PR)
        self.datei=ix(DATES); self.ai=ix(AMOUNTS+[n for n in header if 'Amount (' in n]); self.srci=self.index.get('kaynak_klasor');self.cati=self.index.get('Category');self.rti=self.index.get('record_type')
    @staticmethod
    def first(row,indices):
        for i in indices:
            if i<len(row) and row[i] is not None and str(row[i]).strip(): return str(row[i])
        return ''
    def evidence(self,row):
        sid=self.sid
        if self.srci is not None and self.srci<len(row): sid=source_id(row[self.srci])
        m=self.first(row,self.mi); d=self.first(row,self.di); c=self.first(row,self.ci)
        if c and not re.fullmatch(r'\d{1,4}(?:\.0)?',c.strip()):
            d=d or c; c=''
        # Stockport mixes MCC titles and procurement classes in this column;
        # only the factual reference linker can turn its value into an MCC.
        procurement=self.first(row,self.pri)
        if not d and sid in {'stockport','eden'}: d=procurement
        purpose=' | '.join(str(row[i]) for i in self.pi if i<len(row) and row[i] is not None and str(row[i]).strip())
        cat=str(row[self.cati] or '') if self.cati is not None and self.cati<len(row) else ''
        rt=str(row[self.rti] or '') if self.rti is not None and self.rti<len(row) else ''
        if not any(str(v or '').strip() for v in row): rt='blank'
        elif m in M or self.first(row,self.datei) in DATES: rt='repeated_header'
        elif not m and not self.first(row,self.datei) and not self.first(row,self.ai): rt='note'
        return sid,m,d,c,purpose,procurement,cat,rt

AUDIT_SCHEMA=pa.schema([('source_sheet',pa.string()),('source_row',pa.int64()),('source_id',pa.string()),('taxonomy_label',pa.string()),('evidence_method',pa.string()),('rule_id',pa.string()),('mcc_code_linked',pa.string()),('mcc_only_label',pa.string()),('mcc_link_method',pa.string()),('needs_review',pa.bool_()),('mcc_disagreement',pa.bool_())])
class Stats:
    def __init__(self,rel,isprimary):
        self.rel=rel;self.id=fileid(rel);self.isprimary=isprimary;self.sid=source_id(rel)
        self.counts=Counter();self.methods=Counter();self.cross=Counter();self.review=Counter();self.examples={};self.examples_n=Counter();self.sheetcounts=Counter();self.disagreement=0;self.resolved=0;self.trans=0;self.numeric=0;self.linked=0;self.base_resolved=0;self.extra=0;self.changed=0;self.sourcecounts=Counter()
        self.audit=pq.ParquetWriter(ANALYSIS/'audit'/f'{self.id}.parquet',AUDIT_SCHEMA,compression='zstd'); self.buffer=[]
        self.payload=hashlib.sha256()
    def add(self,sheet,n,row,evidence,result):
        sid,m,d,c,p,pr,cat,rt=evidence
        lab,method,rule,code,baseline,linkmethod,review,conflict=result
        self.counts[lab]+=1;self.methods[(method,lab)]+=1;self.sheetcounts[(sheet,lab)]+=1;self.sourcecounts[sid]+=1
        self.cross[(code,d,baseline,lab,method)]+=1
        istrans=lab!='NOT_A_TRANSACTION'; self.trans+=istrans
        self.resolved+=lab in LABELS;self.disagreement+=conflict
        self.numeric+=bool(c) and istrans;self.linked+=bool(code) and istrans;self.base_resolved+=bool(baseline) and istrans
        self.extra+=lab in LABELS and not baseline and istrans;self.changed+=lab in LABELS and bool(baseline) and lab!=baseline and istrans
        self.buffer.append((sheet,n,sid,lab,method,rule,code,baseline,linkmethod,review,conflict))
        # Hash typed input payload independently of output serialization.
        self.payload.update(json.dumps([sheet,n,list(row)],ensure_ascii=True,default=str,separators=(',',':')).encode())
        key=(sid,lab,method,conflict)
        self.examples_n[key]+=1
        # Stable first distinct examples, capped per stratum; address links to original.
        values=(m,d,p,pr,cat)
        bucket=self.examples.setdefault(key,{})
        if len(bucket)<8 and values not in bucket: bucket[values]=(sheet,n,result)
        if lab.startswith('UNRESOLVED') or conflict:
            self.review[(sid,lab,m,d,rule)]+=1
        if len(self.buffer)>=25000: self.flush()
    def flush(self):
        if self.buffer:
            self.audit.write_table(pa.Table.from_arrays([pa.array(v,type=f.type) for v,f in zip(zip(*self.buffer),AUDIT_SCHEMA)],schema=AUDIT_SCHEMA));self.buffer.clear()
    def finish(self,meta):
        self.flush();self.audit.close()
        total=sum(self.counts.values()); resolved=sum(self.counts[x] for x in LABELS)
        meta.update({'rules_sha256':digest(BASE/'taxonomy_pipeline/rules.py'),'file_id':self.id,'source_file':self.rel,'source_id':self.sid,'is_primary_input':self.isprimary,'reader_rows_excluding_header':total,'transaction_candidate_rows':self.trans,'resolved_rows':resolved,'resolved_fraction':resolved/self.trans if self.trans else None,'nontransaction_rows':self.counts['NOT_A_TRANSACTION'],'numeric_mcc_rows':self.numeric,'linked_mcc_rows':self.linked,'mcc_only_resolved_rows':self.base_resolved,'additional_resolved_rows':self.extra,'changed_from_mcc_rows':self.changed,'source_payload_sha256':self.payload.hexdigest(),'counts':dict(self.counts),'methods':[[*k,v] for k,v in self.methods.items()],'sheetcounts':[[*k,v] for k,v in self.sheetcounts.items()],'contained_sources':dict(self.sourcecounts)})
        rows=[{'taxonomy_label':l,'main_category':l.split('.')[0] if '.' in l else '', 'rows':self.counts[l],'share_all_rows':self.counts[l]/total if total else 0,'share_transaction_candidates':self.counts[l]/self.trans if self.trans and l!='NOT_A_TRANSACTION' else None,'share_resolved':self.counts[l]/resolved if resolved and l in LABELS else None} for l in LABELS+STATUSES]
        folder=ANALYSIS/'files'/self.id
        write_csv(folder/'label_distribution.csv',list(rows[0]),rows)
        cross=[dict(zip(['mcc_code_linked','mcc_description_raw','mcc_only_label','taxonomy_label','evidence_method','rows'],(*k,n))) for k,n in self.cross.most_common()]
        write_csv(folder/'mcc_taxonomy_crosstab.csv',['mcc_code_linked','mcc_description_raw','mcc_only_label','taxonomy_label','evidence_method','rows'],cross)
        review=[dict(zip(['source_id','taxonomy_label','merchant','mcc_description_raw','rule_id','rows'],(*k,n))) for k,n in self.review.most_common()]
        write_csv(folder/'review_groups.csv',['source_id','taxonomy_label','merchant','mcc_description_raw','rule_id','rows'],review)
        examples=[]
        for key,bucket in self.examples.items():
            for values,(sheet,n,result) in bucket.items():
                examples.append(dict(zip(['source_id','taxonomy_label','evidence_method','mcc_disagreement','merchant','mcc_description_raw','transaction_text','procurement_text','original_category','source_sheet','source_row','rule_id','mcc_code_linked','mcc_only_label'],(*key,*values,sheet,n,result[2],result[3],result[4]))))
        write_csv(folder/'evidence_examples.csv',['source_id','taxonomy_label','evidence_method','mcc_disagreement','merchant','mcc_description_raw','transaction_text','procurement_text','original_category','source_sheet','source_row','rule_id','mcc_code_linked','mcc_only_label'],examples)
        save_json(ANALYSIS/'manifests'/f'{self.id}.json',meta)
        return meta

def csv_export(path,classifier):
    rel=path.relative_to(ROOT).as_posix(); inp=readable(path); out=DEST/rel;out.parent.mkdir(parents=True,exist_ok=True)
    skip=2 if source_id(rel)=='bristol' and '__' in path.name else 0
    documentation='__02_Description of Categories' in path.name
    stats=Stats(rel,primary(path)); widths=Counter(); sourcehash=digest(inp)
    with inp.open(encoding='utf-8-sig',newline='') as f, out.with_suffix('.csv.partial').open('w',encoding='utf-8-sig',newline='') as g:
        reader=csv.reader(f);writer=csv.writer(g,lineterminator='\n')
        preamble=[next(reader) for _ in range(skip)];header=next(reader)
        assert 'taxonomy_label' not in header,rel
        adapter=Adapter(header,source_id(rel)); width=len(header)
        for n,row in enumerate(preamble,1):
            assert len(row)<=width,(rel,n)
            ev=(adapter.sid,'','','','','','','preamble');result=classifier.classify(*ev)
            writer.writerow(row+['']*(width-len(row))+[result[0]]);stats.add('',n,row,ev,result)
        writer.writerow(header+['taxonomy_label'])
        for n,row in enumerate(reader,skip+2):
            widths[len(row)]+=1
            if len(row)>width: raise ValueError(f'{rel}:{n} has {len(row)} cells > header {width}')
            ev=adapter.evidence(row)
            if documentation: ev=(*ev[:-1],'documentation')
            result=classifier.classify(*ev)
            writer.writerow(row+['']*(width-len(row))+[result[0]])
            stats.add('',n,row,ev,result)
    out.with_suffix('.csv.partial').replace(out)
    return stats.finish({'format':'csv','source_sha256':sourcehash,'read_path':inp.relative_to(BASE).as_posix(),'output_sha256':digest(out),'source_columns':width,'header_record':skip+1,'original_width_counts':dict(widths),'sheets':[]})

def column_name(n):
    s=''
    while n: n,r=divmod(n-1,26);s=chr(65+r)+s
    return s

def xlsx_export(path,classifier):
    rel=path.relative_to(ROOT).as_posix();out=DEST/rel;out.parent.mkdir(parents=True,exist_ok=True);sid=source_id(rel)
    stats=Stats(rel,primary(path));book=openpyxl.load_workbook(path,read_only=True,data_only=False)
    by_sheet={};sheetmeta=[]
    for ws in book:
        header_n=3 if sid=='bristol' else 1
        rows=ws.iter_rows(values_only=True); labels={};width=ws.max_column;adapter=None
        documentation=ws.title=='Description of Categories'
        for n,row in enumerate(rows,1):
            if n==header_n:
                header=[str(v) if v is not None else '' for v in row];assert 'taxonomy_label' not in header
                adapter=Adapter(header,sid);labels[n]='taxonomy_label';continue
            if n<header_n: ev=(sid,'','','','','','','preamble')
            else:
                ev=adapter.evidence(row)
                if documentation: ev=(*ev[:-1],'documentation')
            result=classifier.classify(*ev);labels[n]=result[0];stats.add(ws.title,n,row,ev,result)
        by_sheet[ws.title]=(width,ws.max_row,labels)
        sheetmeta.append({'name':ws.title,'header_record':header_n,'source_columns':width,'source_rows':ws.max_row})
    book.close()
    scratch=BASE/'.data_processing/taxonomy_author';scratch.mkdir(parents=True,exist_ok=True)
    request=scratch/(stats.id+'.json'); authored=scratch/(stats.id+'.xlsx')
    save_json(request,[{'name':name,'labels':[lab[n] for n in range(1,maxrow+1)]} for name,(width,maxrow,lab) in by_sheet.items()])
    subprocess.run(['node',str(BASE/'taxonomy_pipeline/author_labels.mjs'),str(request),str(authored)],check=True,capture_output=True,text=True)
    authored_labels={}
    with zipfile.ZipFile(authored) as az:
        ns0={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        shared=[]
        if 'xl/sharedStrings.xml' in az.namelist():
            shared=[''.join(x.itertext()) for x in ET.fromstring(az.read('xl/sharedStrings.xml'))]
        for i,name in enumerate(by_sheet,1):
            root=ET.fromstring(az.read(f'xl/worksheets/sheet{i}.xml'))
            vals={}
            for c in root.findall('.//m:sheetData/m:row/m:c',ns0):
                n=int(re.search(r'\d+',c.attrib['r']).group())
                if c.attrib.get('t')=='s':value=shared[int(c.find('m:v',ns0).text)]
                elif c.attrib.get('t')=='inlineStr':value=''.join(c.find('m:is',ns0).itertext())
                else:value=c.find('m:v',ns0).text
                vals[n]=value
            assert vals==by_sheet[name][2],f'Artifact label export differs: {name}'
            authored_labels[name]=vals
    # Surgical OOXML patch preserves all original cells, formula caches, styles,
    # drawings, relationships and nonworksheet parts. No workbook reserialization.
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    rns='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(out.with_suffix('.xlsx.partial'),'w') as zout:
        wb=ET.fromstring(zin.read('xl/workbook.xml'));rels=ET.fromstring(zin.read('xl/_rels/workbook.xml.rels'))
        targets={e.attrib['Id']:e.attrib['Target'] for e in rels}
        patches={}
        for sheet in wb.find('m:sheets',ns):
            target=targets[sheet.attrib[rns]]; target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            name=sheet.attrib['name'];width,maxrow,_=by_sheet[name]
            patches[target]=(width,maxrow,authored_labels[name])
        for entry in zin.infolist():
            data=zin.read(entry.filename)
            if entry.filename in patches:
                width,maxrow,labels=patches[entry.filename];column=column_name(width+1);txt=data.decode('utf-8')
                def cell(n):return f'<c r="{column}{n}" t="inlineStr"><is><t>{escape(labels[n])}</t></is></c>'
                original_rows={int(m.group(1)):m.group(0) for m in re.finditer(r'<row\b[^>]*\br="(\d+)"[^>]*(?:/>|>.*?</row>)',txt,re.S)}
                rendered=[]
                for n in range(1,maxrow+1):
                    existing=original_rows.get(n,f'<row r="{n}"></row>')
                    if existing.endswith('/>'):existing=existing[:-2]+'></row>'
                    rendered.append(existing.replace('</row>',cell(n)+'</row>'))
                txt=re.sub(r'<sheetData>.*?</sheetData>','<sheetData>'+''.join(rendered)+'</sheetData>',txt,count=1,flags=re.S)
                txt=re.sub(r'<dimension\b[^>]*/>',f'<dimension ref="A1:{column}{maxrow}"/>',txt,count=1)
                # New label width; original column definitions remain intact.
                colxml=f'<col min="{width+1}" max="{width+1}" width="72" customWidth="1"/>'
                if '</cols>' in txt: txt=txt.replace('</cols>',colxml+'</cols>',1)
                else: txt=txt.replace('<sheetData>','<cols>'+colxml+'</cols><sheetData>',1)
                data=txt.encode('utf-8')
            zout.writestr(entry,data)
    out.with_suffix('.xlsx.partial').replace(out)
    return stats.finish({'format':'xlsx','source_sha256':digest(path),'read_path':path.relative_to(BASE).as_posix(),'output_sha256':digest(out),'sheets':sheetmeta})

def export_rules(classifier):
    save_json(ANALYSIS/'rules/taxonomy.json',{'version':VERSION,'categories':{k:v.split() for k,v in TAXONOMY.items()},'label_format':'MAIN_CATEGORY.subcategory','operational_statuses':STATUSES})
    rows=[]
    for kind,rules in [('merchant',MERCHANT_RULES),('transaction_text',ITEM_RULES),('procurement_text',PROCUREMENT_RULES),('mcc_description_semantic',DESCRIPTION_RULES)]:
        for n,(child,regex) in enumerate(rules,1):rows.append({'rule_type':kind,'rule_id':str(n)+':'+child,'subcategory':child,'regex':regex})
    write_csv(ANALYSIS/'rules/text_rules.csv',['rule_type','rule_id','subcategory','regex'],rows)
    write_csv(ANALYSIS/'rules/mcc_crosswalk.csv',['mcc_code','taxonomy_label','crosswalk_status'],[{'mcc_code':c,'taxonomy_label':code_label(c),'crosswalk_status':'mapped' if code_label(c) else 'taxonomy_gap' if c in GAP_CODES else 'ambiguous' if c in AMBIGUOUS_CODES else 'unmapped'} for c in sorted(classifier.ref_codes|set(CODE_MAP)|AMBIGUOUS_CODES|GAP_CODES)])

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--pilot',action='store_true');parser.add_argument('--resume',action='store_true');parser.add_argument('--match',default='');args=parser.parse_args()
    for p in ['audit','files','manifests','rules']: (ANALYSIS/p).mkdir(parents=True,exist_ok=True)
    classifier=Classifier(BASE);export_rules(classifier)
    datafiles=sorted((p for p in ROOT.rglob('*') if p.suffix.lower() in {'.csv','.xlsx'}),key=lambda p:(not primary(p),p.stat().st_size))
    # Inventory includes every source file, not just the earlier study selection.
    baseline=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file():continue
        q=readable(p); baseline.append({'source_file':p.relative_to(ROOT).as_posix(),'bytes':q.stat().st_size,'sha256':digest(q),'read_path':q.relative_to(BASE).as_posix(),'source_stat_size':p.stat().st_size,'source_stat_mtime_ns':p.stat().st_mtime_ns})
    baselinepath=ANALYSIS/'source_baseline.json'
    if baselinepath.exists():
        old=json.loads(baselinepath.read_text(encoding='utf-8'));assert old==baseline,'Source files changed since initial run'
    else:save_json(baselinepath,baseline)
    for p in sorted(ROOT.rglob('*')):
        if p.is_dir(): (DEST/p.relative_to(ROOT)).mkdir(parents=True,exist_ok=True)
        elif p.suffix.lower() not in {'.csv','.xlsx'}:shutil.copyfile(readable(p),DEST/p.relative_to(ROOT))
    if args.pilot: datafiles=[p for p in datafiles if p.suffix=='.xlsx' or source_id(p)=='ipo']
    if args.match: datafiles=[p for p in datafiles if args.match.lower() in p.as_posix().lower()]
    for p in datafiles:
        rel=p.relative_to(ROOT).as_posix();fid=fileid(rel);manifest=ANALYSIS/'manifests'/f'{fid}.json'
        if args.resume and manifest.exists() and json.loads(manifest.read_text(encoding='utf-8')).get('rules_sha256')==digest(BASE/'taxonomy_pipeline/rules.py'):
            meta=json.loads(manifest.read_text(encoding='utf-8'))
            assert digest(DEST/rel)==meta['output_sha256'],rel
            print('RESUME verified '+rel,flush=True);continue
        start=time.time();meta=xlsx_export(p,classifier) if p.suffix.lower()=='.xlsx' else csv_export(p,classifier)
        print(f"DONE {rel}: {meta['reader_rows_excluding_header']:,} rows; {meta['resolved_rows']:,} mapped; {time.time()-start:.1f}s",flush=True)
    print('EXPORT COMPLETE',flush=True)
if __name__=='__main__':main()
