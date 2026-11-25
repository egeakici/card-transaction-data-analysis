"""Detailed distributions, nonduplicating study pool and honest MCC comparison."""
import csv,html,json,math,shutil
from collections import Counter,defaultdict
from pathlib import Path
from urllib.parse import quote
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from run import BASE,DEST,ROOT,ANALYSIS,write_csv,save_json,fileid,digest,M,D,C,P,PR,DATES,AMOUNTS
from rules import LABELS,STATUSES,TAXONOMY,VERSION

CSS='''body{font:16px/1.6 system-ui,sans-serif;color:#1d2939;background:#f7f9fc;margin:0}main{max-width:1400px;margin:auto;padding:40px}h1{font-size:32px}h2{margin-top:42px}h3{margin-top:28px}a{color:#215cb0}table{border-collapse:collapse;width:100%;background:white;margin:18px 0;font-size:14px}th,td{padding:9px 12px;text-align:left;border-bottom:1px solid #dfe5ec;vertical-align:top}th{background:#e8eef7;position:sticky;top:0}td.num,th.num{text-align:right;white-space:nowrap}code{background:#e9edf3;padding:2px 5px;overflow-wrap:anywhere}img{display:block;width:100%;max-width:1300px;margin:24px auto}.note{padding:16px 20px;background:#fff3d4;border-left:4px solid #ae7300}.scroll{overflow:auto}.muted{color:#5e6a7b}details{background:#fff;padding:8px 16px;margin:12px 0}summary{cursor:pointer;font-weight:600}.stats{display:flex;gap:24px;flex-wrap:wrap}.stat{padding:18px;background:white;min-width:180px}.stat b{display:block;font-size:28px}'''
def page(title,body):return '<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>'+CSS+'</style><main><h1>'+html.escape(title)+'</h1>'+body+'</main></html>'
def fmt(n):return f'{n:,}'.replace(',','.')
def pct(n,d):return f'%{100*n/d:.2f}' if d else 'uygulanamaz'
def table(headers,rows):
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+html.escape(str(h))+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def link(path,label):return f'<a href="{quote(str(path).replace(chr(92),chr(47)),safe="/._-")}">{html.escape(label)}</a>'
def distribution(counts):
    n=sum(v for k,v in counts.items() if k!='NOT_A_TRANSACTION');resolved=sum(counts[x] for x in LABELS);total=sum(counts.values())
    return [{'taxonomy_label':l,'main_category':l.split('.')[0] if '.' in l else '', 'rows':counts[l],'share_all_rows':counts[l]/total if total else None,'share_transaction_candidates':counts[l]/n if n and l!='NOT_A_TRANSACTION' else None,'share_resolved':counts[l]/resolved if resolved and l in LABELS else None} for l in LABELS+STATUSES]
def disttable(counts):
    n=sum(v for k,v in counts.items() if k!='NOT_A_TRANSACTION')
    rows=[]
    for parent,children in TAXONOMY.items():
        subtotal=sum(counts[parent+'.'+x] for x in children.split())
        rows.append([f'<b>{parent}</b>',f'<b>{fmt(subtotal)}</b>',f'<b>{pct(subtotal,n)}</b>'])
        for child in children.split():
            value=counts[parent+'.'+child]
            rows.append(['&emsp;'+child,fmt(value),pct(value,n)])
    for s in STATUSES:rows.append([s,fmt(counts[s]),pct(counts[s],n) if s!='NOT_A_TRANSACTION' else 'işlem dışı'])
    return table(['Kategori / alt kategori','Satır','İşlem adayı içindeki pay'],rows)
def entropy(counter):
    n=sum(counter.values());return -sum((x/n)*math.log2(x/n) for x in counter.values() if x) if n else None
def savecsv(name,rows,fields=None):
    write_csv(ANALYSIS/name,fields or list(rows[0]),rows)

def main():
    metas=[json.loads(p.read_text(encoding='utf-8')) for p in (ANALYSIS/'manifests').glob('*.json')]
    expected={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.suffix.lower() in {'.csv','.xlsx'}}
    assert {m['source_file'] for m in metas}==expected,'Run all exports first'
    provenance=[]
    for src,name in [('taxonomy_pipeline/rules.py','classifier.py'),('data_profile/config/mcc_reference_snapshot.csv','mcc_reference_snapshot.csv'),('data_profile/config/mcc_historical_titles.csv','mcc_historical_titles.csv'),('outputs/tables/mcc_desc_to_code.csv','source_mcc_description_links.csv')]:
        shutil.copyfile(BASE/src,ANALYSIS/'rules'/name)
        provenance.append({'original_path':src,'copied_file':name,'sha256':digest(BASE/src)})
    save_json(ANALYSIS/'rules/provenance.json',{'version':VERSION,'sources':provenance,'field_priority':{'merchant':M,'mcc_description':D,'mcc_code':C,'transaction_or_purpose_text':P,'procurement':PR,'date':DATES,'amount':AMOUNTS},'source_link_selection':'Only rows with nonempty mcc_code and needs_review=false are reused; fuzzy candidates are not accepted.','label_priority':['record_status','bank_account_flow_gap','explicit_provider_disambiguation','single_narrow_transaction_text_match','mixed_recognized_text_abstention','merchant_rule','mcc_baseline','known_taxonomy_gap','known_ambiguous_mcc','procurement_text','narrow_source_category','unresolved']})
    primary=[m for m in metas if m['is_primary_input']]
    bysource=defaultdict(list)
    for m in primary:bysource[m['source_id']].append(m)
    summaries=[];sourcecounts={};allcounts=Counter();methodrows=[];allcross=[];reviewall=[];exampleall=[]
    for sid,group in sorted(bysource.items()):
        counts=Counter();methods=Counter();cross=Counter();review=Counter();examples=[]
        for m in group:
            counts.update(m['counts'])
            for method,lab,n in m['methods']:methods[(method,lab)]+=n
            folder=ANALYSIS/'files'/m['file_id']
            with (folder/'mcc_taxonomy_crosstab.csv').open(encoding='utf-8-sig',newline='') as f:
                for r in csv.DictReader(f):cross[(r['mcc_code_linked'],r['mcc_description_raw'],r['mcc_only_label'],r['taxonomy_label'],r['evidence_method'])]+=int(r['rows'])
            with (folder/'review_groups.csv').open(encoding='utf-8-sig',newline='') as f:
                for r in csv.DictReader(f):review[(r['taxonomy_label'],r['merchant'],r['mcc_description_raw'],r['rule_id'])]+=int(r['rows'])
            with (folder/'evidence_examples.csv').open(encoding='utf-8-sig',newline='') as f:
                for r in csv.DictReader(f):r['source_file']=m['source_file'];examples.append(r)
        sourcecounts[sid]=counts;allcounts.update(counts)
        n=sum(m['transaction_candidate_rows'] for m in group);res=sum(m['resolved_rows'] for m in group);base=sum(m['mcc_only_resolved_rows'] for m in group)
        row={'source_id':sid,'primary_files':len(group),'all_reader_rows':sum(counts.values()),'nontransaction_rows':counts['NOT_A_TRANSACTION'],'transaction_candidate_rows':n,'taxonomy_resolved_rows':res,'taxonomy_coverage':res/n if n else None,'mcc_only_resolved_rows':base,'mcc_only_coverage':base/n if n else None,'coverage_difference_pp':100*(res-base)/n if n else None,'numeric_mcc_rows':sum(m['numeric_mcc_rows'] for m in group),'linked_mcc_rows':sum(m['linked_mcc_rows'] for m in group),'additional_resolved_rows':sum(m['additional_resolved_rows'] for m in group),'changed_from_mcc_rows':sum(m['changed_from_mcc_rows'] for m in group),'unresolved_ambiguous_rows':counts['UNRESOLVED_AMBIGUOUS'],'unresolved_insufficient_rows':counts['UNRESOLVED_INSUFFICIENT_EVIDENCE'],'out_of_taxonomy_rows':counts['UNRESOLVED_OUT_OF_TAXONOMY'],'active_leaf_categories':sum(bool(counts[x]) for x in LABELS),'active_main_categories':sum(any(counts[parent+'.'+child] for child in children.split()) for parent,children in TAXONOMY.items()),'taxonomy_entropy_bits':entropy({x:counts[x] for x in LABELS})}
        summaries.append(row)
        dr=distribution(counts);savecsv(f'sources/{sid}/label_distribution.csv',dr)
        mainrows=[{'main_category':p,'rows':sum(counts[p+'.'+c] for c in children.split()),'share_transaction_candidates':sum(counts[p+'.'+c] for c in children.split())/n if n else None} for p,children in TAXONOMY.items()]
        savecsv(f'sources/{sid}/main_category_distribution.csv',mainrows)
        mr=[{'source_id':sid,'evidence_method':method,'taxonomy_label':lab,'rows':num} for (method,lab),num in methods.most_common()];methodrows.extend(mr);savecsv(f'sources/{sid}/evidence_distribution.csv',mr)
        cr=[dict(zip(['source_id','mcc_code_linked','mcc_description_raw','mcc_only_label','taxonomy_label','evidence_method','rows'],(sid,*key,num))) for key,num in cross.most_common()];allcross.extend(cr);savecsv(f'sources/{sid}/mcc_taxonomy_crosstab.csv',cr)
        original_desc=Counter();linkedcodes=Counter()
        for (code,description,baseline,lab,method),num in cross.items():
            if lab=='NOT_A_TRANSACTION':continue
            original_desc[description]+=num
            if code:linkedcodes[code]+=num
        savecsv(f'sources/{sid}/mcc_description_distribution.csv',[{'mcc_description_raw':d,'rows':num,'share_transaction_candidates':num/n if n else None,'description_missing':not bool(d.strip())} for d,num in original_desc.most_common()])
        savecsv(f'sources/{sid}/linked_mcc_distribution.csv',[{'mcc_code_linked':code,'rows':num,'share_transaction_candidates':num/n if n else None} for code,num in linkedcodes.most_common()],['mcc_code_linked','rows','share_transaction_candidates'])
        row['distinct_nonempty_mcc_descriptions']=sum(bool(x.strip()) for x in original_desc)
        row['distinct_linked_mcc_codes']=len(linkedcodes)
        row['mcc_description_entropy_bits']=entropy({d:num for d,num in original_desc.items() if d.strip()})
        row['linked_mcc_entropy_bits']=entropy(linkedcodes)
        row['mcc_resolved_but_taxonomy_abstained_rows']=base-res+row['additional_resolved_rows']
        assert row['mcc_resolved_but_taxonomy_abstained_rows']>=0
        rr=[dict(zip(['source_id','taxonomy_label','merchant','mcc_description_raw','rule_id','rows'],(sid,*key,num))) for key,num in review.most_common()];reviewall.extend(rr);savecsv(f'sources/{sid}/review_groups.csv',rr,['source_id','taxonomy_label','merchant','mcc_description_raw','rule_id','rows'])
        exampleall.extend(examples);savecsv(f'sources/{sid}/evidence_examples.csv',examples,list(examples[0]))
        body=f'<p><a href="../../../ANALIZ_RAPORU.html">Genel rapor</a></p><p>Özgün girdi seçimi: {len(group)} dosya. <b>{fmt(n)}</b> işlem adayı; taxonomy kapsamı <b>{pct(res,n)}</b>; MCC’den aynı taxonomy’ye doğrudan dönüşüm kapsamı <b>{pct(base,n)}</b>.</p>'
        body+='<p class="note">Bu oranlar doğruluk değildir. Kaynak MCC’leri ve kategori açıklamaları otomatik kurallarda kullanıldı. Eksik/belirsiz kayıtlar kapsam paydasında tutuldu; açıklama/boş satırlar ayrı sayıldı.</p>'
        body+='<p>'+', '.join(link(name,name) for name in ['label_distribution.csv','main_category_distribution.csv','mcc_description_distribution.csv','linked_mcc_distribution.csv','evidence_distribution.csv','mcc_taxonomy_crosstab.csv','review_groups.csv','evidence_examples.csv'])+'</p>'
        body+='<h2>Dosya seçimi ve dosyalar arasındaki farklar</h2>'+table(['Dosya','Tüm kayıtlar','İşlem adayı','Etiketli','Taxonomy kapsamı','Yalnız MCC dönüşümü'],[[html.escape(m['source_file']),fmt(m['reader_rows_excluding_header']),fmt(m['transaction_candidate_rows']),fmt(m['resolved_rows']),pct(m['resolved_rows'],m['transaction_candidate_rows']),pct(m['mcc_only_resolved_rows'],m['transaction_candidate_rows'])] for m in group])
        body+='<h2>72 alt kategorinin tamamı</h2>'+disttable(counts)
        body+='<h2>En sık incelenecek satıcı / MCC grupları</h2>'+table(['Durum','Satıcı','MCC açıklaması','Kural','Satır'],[[html.escape(r['taxonomy_label']),html.escape(r['merchant']),html.escape(r['mcc_description_raw']),html.escape(r['rule_id']),fmt(r['rows'])] for r in rr[:35]])
        (ANALYSIS/f'sources/{sid}/report.html').write_text(page(sid+' veri seti analizi',body),encoding='utf-8')
    savecsv('dataset_summary.csv',summaries)
    savecsv('all_label_distributions.csv',[{'source_id':sid,**r} for sid,counts in sorted(sourcecounts.items()) for r in distribution(counts)])
    savecsv('all_file_label_distributions.csv',[{'source_file':m['source_file'],'source_id':m['source_id'],'is_primary_input':m['is_primary_input'],**r} for m in sorted(metas,key=lambda x:x['source_file']) for r in distribution(Counter(m['counts']))])
    savecsv('pool_label_distribution.csv',distribution(allcounts))
    savecsv('evidence_distribution.csv',methodrows)
    savecsv('mcc_taxonomy_crosstab.csv',allcross)
    savecsv('review_groups.csv',reviewall)
    # Splitting/merging diagnostics describe structure only, never semantic accuracy.
    codegroups=defaultdict(Counter)
    for r in allcross:
        if r['mcc_code_linked'] and r['taxonomy_label'] in LABELS:codegroups[(r['source_id'],r['mcc_code_linked'])][r['taxonomy_label']]+=r['rows']
    splits=[{'source_id':sid,'mcc_code_linked':code,'resolved_rows':sum(v.values()),'taxonomy_leaves':len(v),'conditional_taxonomy_entropy_bits':entropy(v),'dominant_taxonomy_label':v.most_common(1)[0][0],'dominant_share':v.most_common(1)[0][1]/sum(v.values())} for (sid,code),v in sorted(codegroups.items())]
    savecsv('mcc_split_diagnostics.csv',splits)
    merged=defaultdict(set)
    for r in allcross:
        if r['mcc_code_linked'] and r['taxonomy_label'] in LABELS:merged[(r['source_id'],r['taxonomy_label'])].add(r['mcc_code_linked'])
    savecsv('taxonomy_merge_diagnostics.csv',[{'source_id':sid,'taxonomy_label':lab,'distinct_linked_mcc_codes':len(codes),'linked_mcc_codes':'|'.join(sorted(codes))} for (sid,lab),codes in sorted(merged.items())])
    # Review examples are intentionally qualitative, capped first-distinct examples.
    # Blank gold columns prevent automatic predictions from being presented as truth.
    reviewed=[];samplecounts=Counter()
    for r in exampleall:
        base=r['mcc_only_label'];lab=r['taxonomy_label']
        stratum='unresolved' if lab in STATUSES else 'additional' if not base else 'disagreement' if lab!=base else 'same_as_mcc'
        k=(r['source_id'],stratum)
        if samplecounts[k]>=40 or lab=='NOT_A_TRANSACTION':continue
        samplecounts[k]+=1
        reviewed.append({**r,'review_stratum':stratum,'human_taxonomy_label':'','human_purchase_purpose':'','mcc_fit_rating_1_to_5':'','taxonomy_fit_rating_1_to_5':'','annotator_id':'','review_notes':''})
    savecsv('qualitative_review_template.csv',reviewed)
    inventoryfields=['source_file','source_id','format','is_primary_input','reader_rows_excluding_header','transaction_candidate_rows','resolved_rows','resolved_fraction','nontransaction_rows','numeric_mcc_rows','linked_mcc_rows','mcc_only_resolved_rows','additional_resolved_rows','changed_from_mcc_rows','file_id','source_sha256','output_sha256']
    savecsv('file_inventory.csv',[{k:m[k] for k in inventoryfields} for m in sorted(metas,key=lambda x:x['source_file'])])
    # Every physical file gets its own complete distribution and HTML entry.
    for m in metas:
        counts=Counter(m['counts']);fid=m['file_id']
        body='<p><a href="../../../ANALIZ_RAPORU.html">Genel rapor</a></p><p>'+html.escape(m['source_file'])+'</p>'
        body+='<p>'+('Ana havuza dahil özgün girdi.' if m['is_primary_input'] else 'Birleşik/dönüştürülmüş kopya: tekrar sayımı önlemek için ana havuza dahil değil.')+'</p>'
        body+='<p>'+', '.join(link(x,x) for x in ['label_distribution.csv','mcc_taxonomy_crosstab.csv','review_groups.csv','evidence_examples.csv'])+'</p>'+disttable(counts)
        body+='<h2>Dosyadaki kaynak kimlikleri</h2>'+table(['Kaynak','Tüm okuyucu kayıtları'],[[html.escape(sid),fmt(num)] for sid,num in sorted(m['contained_sources'].items())])
        if m['format']=='xlsx':
            sheetcounts=defaultdict(Counter)
            for sheet,lab,num in m['sheetcounts']:sheetcounts[sheet][lab]+=num
            sr=[{'source_sheet':sheet,**r} for sheet,c in sheetcounts.items() for r in distribution(c)]
            savecsv(f'files/{fid}/sheet_label_distribution.csv',sr)
            body+='<h2>Her çalışma sayfası ayrı</h2><p>'+link('sheet_label_distribution.csv','Sayfa bazında bütün etiket dağılımları')+'</p>'
            for sheet,c in sheetcounts.items():body+='<details><summary>'+html.escape(sheet)+'</summary>'+disttable(c)+'</details>'
        (ANALYSIS/'files'/fid/'report.html').write_text(page('Dosya bazında etiket dağılımı',body),encoding='utf-8')
    figures=ANALYSIS/'figures';figures.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
    ordered=sorted(summaries,key=lambda r:r['taxonomy_coverage'])
    y=np.arange(len(ordered));fig,ax=plt.subplots(figsize=(11,6.8))
    ax.barh(y-.18,[100*r['mcc_only_coverage'] for r in ordered],.34,label='MCC’den doğrudan taxonomy dönüşümü',color='#93a9c7')
    bars=ax.barh(y+.18,[100*r['taxonomy_coverage'] for r in ordered],.34,label='Tüm mevcut kanıtlarla taxonomy',color='#245aa8')
    ax.set_yticks(y,[r['source_id'] for r in ordered]);ax.set_xlim(0,112);ax.set_xlabel('İşlem adayları içinde bir alt kategori atanabilen satırlar (%)')
    ax.bar_label(bars,fmt='%.1f%%',padding=5);ax.legend(loc='lower right',fontsize=9);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    ax.set_title('Kapsam karşılaştırması · doğruluk ölçümü değildir',loc='left',pad=18)
    fig.tight_layout();fig.savefig(figures/'coverage_comparison.png',dpi=170);fig.savefig(figures/'coverage_comparison.svg');plt.close(fig)
    sources=sorted(sourcecounts);parents=list(TAXONOMY)
    matrix=np.array([[100*sum(sourcecounts[s][p+'.'+c] for c in TAXONOMY[p].split())/next(r['transaction_candidate_rows'] for r in summaries if r['source_id']==s) for p in parents] for s in sources])
    fig,ax=plt.subplots(figsize=(14,7));im=ax.imshow(matrix,cmap='Blues',vmin=0,vmax=max(20,matrix.max()),aspect='auto');ax.set_yticks(range(len(sources)),sources);ax.set_xticks(range(len(parents)),[p.replace('_',' ') for p in parents],rotation=50,ha='right',fontsize=8)
    for i in range(len(sources)):
        for j in range(len(parents)):
            if matrix[i,j]>=1:ax.text(j,i,f'{matrix[i,j]:.0f}',ha='center',va='center',fontsize=8,color='white' if matrix[i,j]>matrix.max()*.55 else '#18334f')
    fig.colorbar(im,ax=ax,label='İşlem adayları içinde pay (%)',shrink=.75);ax.set_title('Ana kategori dağılımları · özgün girdiler',loc='left',pad=18);fig.tight_layout();fig.savefig(figures/'main_category_heatmap.png',dpi=170);fig.savefig(figures/'main_category_heatmap.svg');plt.close(fig)
    n=sum(r['transaction_candidate_rows'] for r in summaries);res=sum(r['taxonomy_resolved_rows'] for r in summaries);base=sum(r['mcc_only_resolved_rows'] for r in summaries);totalphysical=sum(m['reader_rows_excluding_header'] for m in metas)
    save_json(ANALYSIS/'analysis_summary.json',{'version':VERSION,'sources':len(summaries),'data_files':len(metas),'primary_files':len(primary),'physical_reader_rows':totalphysical,'pool_transaction_candidates':n,'pool_resolved':res,'pool_coverage':res/n,'mcc_only_resolved':base,'mcc_only_coverage':base/n,'pool_counts':dict(allcounts),'active_leaves':sum(bool(allcounts[x]) for x in LABELS),'verification_file':'verification.json'})
    body='<p class="muted">25 Kasım 2026 · Kural sürümü '+VERSION+' · 16 ana kategori, 72 alt kategori</p>'
    body+=f'<div class="stats"><div class="stat"><b>{len(metas)}</b>etiketlenen CSV / Excel</div><div class="stat"><b>{len(primary)}</b>ana havuz girdisi</div><div class="stat"><b>{fmt(n)}</b>işlem adayı</div><div class="stat"><b>{pct(res,n)}</b>taxonomy kapsamı</div></div>'
    body+='<h2>Tez sorusuna mevcut verinin yanıtı</h2>'
    body+=f'<p>Mevcut kurallar ana havuzdaki {fmt(n)} işlem adayının {fmt(res)} satırına (%{100*res/n:.2f}) bir alt kategori atadı. Aynı taxonomy’ye yalnız MCC üzerinden doğrudan dönüşüm {fmt(base)} satırı (%{100*base/n:.2f}) kapsıyor. Bu fark net kapsam değişimidir: ek kanıtla çözülen satırlardan, kanıt çatışması nedeniyle çekimser kalınan önceden çözülebilir satırlar çıkarılır. İki bileşen özet CSV’de ayrı verilmiştir.</p>'
    body+='<p>Ana havuzun 10 kaynağı kamu harcaması, biri kişisel banka hareketleridir. Bu bileşim genel tüketici kart harcamalarının temsilî bir örneklemi değildir. Uygunluk iddiası bu kaynakların bağlamında değerlendirilmelidir.</p>'
    body+='<p class="note"><b>“MCC’den daha doğru temsil ediyor” tezi henüz kanıtlanmış değildir.</b> Taxonomy tahminlerinde MCC de kullanıldığı için döngüsel doğrulama riski vardır. Kapsam, kategori sayısı, entropi ve satıcı tutarlılığı doğruluk yerine geçmez. Çelişki satırları otomatik düzeltmenin doğruluğu olarak yorumlanamaz.</p>'
    body+='<p>Taxonomy satıcı türünü (online_marketplaces, supermarkets), ürün/hizmeti (software_and_apps) ve kullanım amacını bir arada içeriyor. Örneğin Amazon’dan ofis kâğıdı alımı hem kanal hem ürün bakımından tanımlanabilir. Burada açık işlem açıklaması önceliklidir; sonrasında satıcı, MCC ve diğer kategori kanıtları gelir. Tezde değerlendirme birimi ve bu öncelik önceden sabitlenmelidir.</p>'
    body+='<h2>Veri setlerini tek tek inceleyin</h2>'+table(['Veri seti','İşlem adayı','Taxonomy kapsamı','Yalnız MCC dönüşümü','Fark (puan)','Ek atanabilen','MCC ile farklı etiket','Aktif alt kategori'],[[link(f'_taxonomy_analysis/sources/{r["source_id"]}/report.html',r['source_id']),fmt(r['transaction_candidate_rows']),pct(r['taxonomy_resolved_rows'],r['transaction_candidate_rows']),pct(r['mcc_only_resolved_rows'],r['transaction_candidate_rows']),f'{r["coverage_difference_pp"]:+.2f}',fmt(r['additional_resolved_rows']),fmt(r['changed_from_mcc_rows']),r['active_leaf_categories']] for r in summaries])
    body+='<img src="_taxonomy_analysis/figures/coverage_comparison.png" alt="Kaynak bazında etiket kapsamı karşılaştırması"><img src="_taxonomy_analysis/figures/main_category_heatmap.png" alt="Ana kategorilerin veri setlerine dağılımı">'
    body+='<h2>Taxonomy’nin boşlukları</h2><p>Etiket verilmeyen gerçek işlemler üç ayrı durumda tutuldu. Bu durumlar 72 alt kategoriye eklenmiş yeni kategoriler değildir; her satırı korumak için kullanılan denetim değerleridir.</p>'+table(['Değer','Anlamı','Ana havuzda satır'],[[s,{'UNRESOLVED_INSUFFICIENT_EVIDENCE':'Mevcut alanlardan güvenilir alt kategori seçilemiyor.','UNRESOLVED_AMBIGUOUS':'Birden çok alt kategori mümkün veya açıklama birden fazla ürünü içeriyor.','UNRESOLVED_OUT_OF_TAXONOMY':'İşlem anlamı mevcut 72 alt kategoriyle karşılanmıyor.','NOT_A_TRANSACTION':'Boş/açıklama/üstbilgi/Zero Return satırı; işlem paydasına dahil değil.'}[s],fmt(allcounts[s])] for s in STATUSES])
    inactive=[x for x in LABELS if not allcounts[x]]
    body+='<p>Bu kurallarla ana havuzda gözlenmeyen alt kategoriler: '+(', '.join('<code>'+x+'</code>' for x in inactive) or 'yok')+'. Sıfır gözlem kategori gereksizliğini kanıtlamaz; veri örnekleminin bileşimi ve kural kapsamı da etkili olabilir.</p>'
    body+='<h2>Tekrar sayımı ve veri bütünlüğü</h2>'
    body+=f'<p>58 fiziksel veri dosyasında toplam {fmt(totalphysical)} okuyucu kaydı etiketlendi (üstbilgiler hariç). Bu toplam bağımsız işlem sayısı değildir. Genel havuz özgün Bristol ve Laramee çalışma kitaplarını, Oklahoma mali yıl dosyalarını ve diğer kaynakların özgün CSV’lerini kullanır. Birleşik CSV’ler ve Excel dönüşümleri ayrı raporlanır. Özgün girdilerin kendi içindeki tekrarlar silinmedi; işlem adayı sayısı benzersiz işlem sayısı değildir.</p>'
    body+='<p>Eski tüm-kaynaklar birleşik dosyası, güncel kaynak seçiminden farklı içerik ve artık ayrı klasörü bulunmayan kaynak satırları içerebilir. Bu dosya da eksiksiz etiketlendi; güncel havuz yerine kullanılmadı. Kaynaklarda hiçbir veri veya hücre silinmedi. Etiket dışındaki çalışma kitabı bölümleri ve kaynak hücrelerin XML’i korunarak yalnız son sütun eklendi. CSV değerleri, sıra ve satır sayısı korundu; çıktı UTF-8 BOM ve LF satır sonlarıyla yazıldı.</p>'
    body+='<p>Eden, Solihull ve Sunderland özgün CSV’lerine doğrudan okuma erişimi yoktu. Önceden oluşturulmuş erişim kopyaları, kaydedilmiş özgün SHA-256 değerleriyle eşitlikleri doğrulanarak kullanıldı. Özgün dosyaların boyut ve değişiklik zamanları da denetlendi.</p>'
    body+='<p>'+link('_taxonomy_analysis/verification.json','Tüm dosyalar için satır/hücre/hash doğrulaması')+' · '+link('_taxonomy_analysis/source_baseline.json','Kaynak dosya başlangıç hash’leri')+' · '+link('_taxonomy_analysis/file_inventory.csv','Tüm dosyaların envanteri')+'</p>'
    body+='<h2>Bağımsız doğrulama ile tez testi</h2><ol><li>Hedefi açıkça tanımlayın: satıcı faaliyet türü mü, satın alınan ürün/hizmet mi? İşlem açıklaması olmayan kayıtlarda ürün düzeyinde doğruluk ölçülemez.</li><li>Kaynak, zaman, MCC, uyuşmazlık ve çözülemeyen durumlara göre önceden tanımlı katmanlı rastgele örneklem seçin. Satıcıları eğitim/test arasında ayırın. Pooled sonuçlara büyük Oklahoma kaynağının hâkim olmasına karşı kaynak başına sonuçları ve makro ortalamayı da raporlayın.</li><li>En az iki değerlendiriciye otomatik etiketi ve MCC’yi göstermeden özgün işlem kanıtını etiketletin. Anlaşmazlıkları ayrıca çözün; değerlendiriciler arası uyumu raporlayın.</li><li>MCC-only, yalnız metin/satıcı ve MCC+metin yöntemlerini aynı bağımsız örneklemde karşılaştırın. Alt/ana kategori doğruluğu, macro-F1, kaynak bazında kapsam, çekimser kalma ve temsil uygunluğu puanlarını birlikte değerlendirin. Kapsam eşitleyerek veya risk–kapsam eğrileriyle seçim yanlılığını kontrol edin.</li><li>Eşleştirilmiş sonuçlar için satıcı/kaynak kümelerini dikkate alan bootstrap güven aralıkları kullanın. MCC’nin kendi amacıyla uyumlu satıcı türü değerlendirmesini ayrıca raporlayın; ürün taxonomy’sine bire bir karşılığının olmamasını otomatik hata saymayın.</li></ol>'
    body+='<p>'+link('_taxonomy_analysis/qualitative_review_template.csv','İnsan incelemesi için nitel örnek şablonu')+' ilk farklı örneklerden oluşur; rastgele/temsilî örneklem değildir ve hipotez testinde doğrudan kullanılmamalıdır. İnsan etiketi ve uygunluk puanı alanları özellikle boş bırakılmıştır.</p>'
    body+='<h2>İndirilebilir analiz tabloları</h2><p>MCC ayrışma/birleşme tabloları yalnız etiket atanabilen ve MCC bağlantısı bulunan satırları kullanır. Taxonomy entropisi etiketli, MCC entropisi ilgili MCC bilgisi bulunan satırlarda hesaplanır; paydalar farklı olabilir. Bu ölçüler doğrudan başarı karşılaştırması değildir. Dağılımlar harcama tutarı değil satır sayısı üzerinden hesaplandı; kaynaklar arasında para birimi veya tutar birleştirilmedi.</p><ul>'+''.join('<li>'+link('_taxonomy_analysis/'+name,title)+'</li>' for name,title in [('dataset_summary.csv','Veri seti bazında tüm özet ölçüler'),('all_label_distributions.csv','Her kaynak için 72 etiket + durum dağılımları'),('pool_label_distribution.csv','Tekrar kopyaları dışlanmış havuz dağılımı'),('mcc_taxonomy_crosstab.csv','MCC–taxonomy ayrıntılı çapraz tablosu'),('mcc_split_diagnostics.csv','Bir MCC’nin birden çok taxonomy etiketine ayrılması'),('taxonomy_merge_diagnostics.csv','Bir taxonomy etiketinde birleştirilen MCC’ler'),('evidence_distribution.csv','Etiketin dayandığı kanıtın dağılımı'),('review_groups.csv','Kapsam boşlukları ve uyuşmazlıklar'),('rules/taxonomy.json','72 etiketin tam sözlüğü'),('rules/mcc_crosswalk.csv','İncelenebilir MCC eşleme tablosu'),('rules/text_rules.csv','Satıcı, işlem ve satın alma sınıfı kuralları')])+'</ul>'
    body+='<h2>Fiziksel dosyalar: her birinin dağılımı</h2>'+table(['Dosya','Rol','Tüm kayıtlar','Etiketlenen işlem'],[[link(f'_taxonomy_analysis/files/{m["file_id"]}/report.html',m['source_file']),'özgün girdi' if m['is_primary_input'] else 'dönüşüm / birleşik kopya',fmt(m['reader_rows_excluding_header']),fmt(m['resolved_rows'])] for m in sorted(metas,key=lambda x:x['source_file'])])
    body+='<h2>Yöntem ve kaynaklar</h2><p>Etiketler insan tarafından doğrulanmış altın standart değildir; sürümlenmiş deterministik kurallarla üretilmiş zayıf etiketlerdir. MCC açıklamalarından kod bağlantısında projedeki sabitlenmiş resmî MCC referansları ve önceden inceleme gerektirmediği işaretlenmiş bağlantılar kullanıldı. Bu çalışmada yeni yaklaşık/fuzzy kod eşleştirmesi yapılmadı. Bir MCC’nin birden fazla alt kategoriyi kapsaması halinde ek kanıt olmadan rastgele alt kategori seçilmedi.</p>'
    body+='<p>MCC’nin satıcının iş türünü belirttiği tanımı: <a href="https://www.citibank.com/tts/solutions/commercial-cards/assets/docs/govt/Merchant-Category-Codes.pdf">Citi Merchant Category Codes</a>. Sabitlenmiş referanslar: <a href="https://usa.visa.com/content/dam/VCOM/download/merchants/visa-merchant-data-standards-manual.pdf">Visa Merchant Data Standards Manual</a>, <a href="https://www.mastercard.com/content/dam/mccom/shared/business/support/rules-pdfs/mastercard-quick-reference-booklet-merchant.pdf">Mastercard Quick Reference Booklet</a>. MCC eşleme tercihleri araştırma amaçlıdır; ödeme ağı tarafından onaylanmış taxonomy değildir. Ek satıcı kontrolü: <a href="https://www.prestigenetwork.com/services/interpreting-services/">Prestige Network interpreting</a>, <a href="https://www.quadient.com/en-us/learn/why-your-neopost-machine-now-says-quadient">Quadient/Neopost ürün kapsamı</a>. Neopost için yalnız satıcı adından alt kategori zorlanmadı; franking kredisi açıkça belirtilen açıklamalar posta hizmetine eşlendi.</p>'
    (DEST/'ANALIZ_RAPORU.html').write_text(page('Gerçek veri setleri: taxonomy ve MCC analizi',body),encoding='utf-8')
    print(json.dumps({'files':len(metas),'sources':len(summaries),'pool_rows':n,'resolved':res,'coverage':res/n,'mcc_only':base/n,'physical_rows':totalphysical}),flush=True)
if __name__=='__main__':main()
