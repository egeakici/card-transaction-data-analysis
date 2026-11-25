"""Export aggregate taxonomy findings without transaction records or examples."""
import csv
import hashlib
import html
import json
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

from analyze import page, table, disttable, fmt, pct, link
from run import BASE, ANALYSIS, write_csv, save_json
from rules import LABELS, STATUSES, TAXONOMY

OUT=BASE/'outputs/taxonomy'
CSV_TABLES={
    'dataset_summary.csv', 'all_label_distributions.csv',
    'all_file_label_distributions.csv', 'pool_label_distribution.csv',
    'evidence_distribution.csv', 'mcc_split_diagnostics.csv',
    'taxonomy_merge_diagnostics.csv',
}
FORBIDDEN_COLUMNS={'merchant','merchant_name','transaction_text','procurement_text',
    'original_category','source_row','transaction_id','transaction_reference',
    'mcc_description_raw','review_notes','annotator_id'}

def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        fields=reader.fieldnames
        rows=list(reader)
    return fields,rows

def export_csv(name):
    fields,rows=read_csv(ANALYSIS/name)
    assert not FORBIDDEN_COLUMNS.intersection(fields),(name,fields)
    write_csv(OUT/name,fields,rows)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    verification=json.loads((ANALYSIS/'verification.json').read_text(encoding='utf-8'))
    assert verification['all_passed'] and verification['data_files_verified']==58
    summary=json.loads((ANALYSIS/'analysis_summary.json').read_text(encoding='utf-8'))
    summary['verification_file']='verification_summary.json'
    save_json(OUT/'analysis_summary.json',summary)
    save_json(OUT/'verification_summary.json',{k:verification[k] for k in [
        'all_passed','source_files_unchanged','data_files_verified',
        'records_verified','source_cells_verified']})
    save_json(OUT/'taxonomy.json',json.loads((ANALYSIS/'rules/taxonomy.json').read_text(encoding='utf-8')))
    for name in sorted(CSV_TABLES):export_csv(name)

    # Retain numeric MCCs and our taxonomy, never copied source descriptions.
    fields,rows=read_csv(ANALYSIS/'mcc_taxonomy_crosstab.csv')
    keys=['source_id','mcc_code_linked','mcc_only_label','taxonomy_label','evidence_method']
    cross=Counter()
    for r in rows:cross[tuple(r[k] for k in keys)]+=int(r['rows'])
    write_csv(OUT/'mcc_taxonomy_crosstab.csv',keys+['rows'],[
        dict(zip(keys+['rows'],(*key,num))) for key,num in sorted(cross.items())])
    _,inventory=read_csv(ANALYSIS/'file_inventory.csv')
    inventory_fields=['source_file','source_id','format','is_primary_input',
        'reader_rows_excluding_header','transaction_candidate_rows','resolved_rows',
        'resolved_fraction','nontransaction_rows','file_id']
    write_csv(OUT/'file_inventory.csv',inventory_fields,[{k:r[k] for k in inventory_fields} for r in inventory])
    figure_names=['coverage_comparison.png','coverage_comparison.svg',
                  'main_category_heatmap.png','main_category_heatmap.svg']
    (OUT/'figures').mkdir(exist_ok=True)
    for name in figure_names:(OUT/'figures'/name).write_bytes((ANALYSIS/'figures'/name).read_bytes())

    _,datasets=read_csv(OUT/'dataset_summary.csv')
    _,distributions=read_csv(OUT/'all_label_distributions.csv')
    counts=defaultdict(Counter)
    for r in distributions:counts[r['source_id']][r['taxonomy_label']]=int(r['rows'])
    _,file_distributions=read_csv(OUT/'all_file_label_distributions.csv')
    filecounts=defaultdict(Counter)
    for r in file_distributions:filecounts[r['source_file']][r['taxonomy_label']]=int(r['rows'])
    _,pooled=read_csv(OUT/'pool_label_distribution.csv')
    pool=Counter({r['taxonomy_label']:int(r['rows']) for r in pooled})
    assert sum(pool[x] for x in LABELS)==summary['pool_resolved']
    assert len(distributions)==11*76 and len(file_distributions)==58*76

    sparse=[]
    for sid,c in sorted(counts.items()):
        values=[c[x] for x in LABELS]
        sparse.append({'source_id':sid,'active_classes':sum(n>0 for n in values),
            'zero_classes':sum(n==0 for n in values),'classes_1_to_9':sum(0<n<10 for n in values),
            'classes_at_least_100':sum(n>=100 for n in values),
            'classes_at_least_1000':sum(n>=1000 for n in values),
            'top5_share_of_resolved':sum(sorted(values,reverse=True)[:5])/sum(values)})
    write_csv(OUT/'class_sparsity.csv',list(sparse[0]),sparse)

    for r in datasets:
        sid=r['source_id'];c=counts[sid]
        body='<p><a href="../ANALIZ_RAPORU.html">Genel rapor</a></p>'
        body+=f'<p>İşlem adayı: {fmt(int(r["transaction_candidate_rows"]))}. Taxonomy kapsamı: {pct(int(r["taxonomy_resolved_rows"]),int(r["transaction_candidate_rows"]))}.</p>'
        body+='<p>72 alt kategorinin tamamı ve dört işlem/etiketleme durumu gösterilmiştir. Sayılar otomatik atamadır; insan doğrulaması yapılmış altın standart değildir.</p>'
        body+=disttable(c)
        target=OUT/'sources'/f'{sid}.html';target.parent.mkdir(exist_ok=True)
        target.write_text(page(sid+' taxonomy dağılımı',body),encoding='utf-8')
    for r in inventory:
        body='<p><a href="../ANALIZ_RAPORU.html">Genel rapor</a></p><p>'+html.escape(r['source_file'])+'</p>'
        body+='<p>'+('Ana havuz girdisi.' if r['is_primary_input']=='True' else 'Dönüşüm/birleşik kopya; ana havuza eklenmez.')+'</p>'
        body+=disttable(filecounts[r['source_file']])
        target=OUT/'files'/f"{r['file_id']}.html";target.parent.mkdir(exist_ok=True)
        target.write_text(page('Dosya bazında taxonomy dağılımı',body),encoding='utf-8')

    body='<p>16 ana kategori, 72 alt kategori. Bu paket toplu sayımlar, oranlar ve grafiklerden oluşur. İşlem kayıtları, satıcı örnekleri ve satır düzeyindeki denetim dosyaları pakete dahil değildir.</p>'
    body+=f'<p><b>{summary["data_files"]} fiziksel dosyada {fmt(summary["physical_reader_rows"])} satır işlendi.</b> Tekrar kopyaları dışlanan ana havuz, {summary["sources"]} kaynaktan {summary["primary_files"]} özgün girdi ve {fmt(summary["pool_transaction_candidates"])} işlem adayı içerir. Bu sayı benzersiz işlem sayısı değildir; kaynak içindeki tekrarlar silinmedi.</p>'
    body+=f'<p>Taxonomy kapsamı <b>{pct(summary["pool_resolved"],summary["pool_transaction_candidates"])}</b>; yalnız MCC’den aynı taxonomy’ye dönüşüm kapsamı <b>{pct(summary["mcc_only_resolved"],summary["pool_transaction_candidates"])}</b>.</p>'
    body+='<p class="note">Kapsam doğruluk değildir. MCC’siz bir kayda etiket atanması MCC’nin hatalı olduğunu göstermez. Bu sonuçlar MCC’ye üstünlük tezini kanıtlamaz; bağımsız ve kör insan etiketlemesi gerekir. Henüz kompakt/dengelenmiş eğitim seti üretilmedi.</p>'
    body+='<h2>Kaynak bazında sonuçlar</h2>'+table(['Kaynak','İşlem adayı','Etiketli','Taxonomy kapsamı','MCC dönüşümü','Aktif alt kategori'],[
        [link(f'sources/{r["source_id"]}.html',r['source_id']),fmt(int(r['transaction_candidate_rows'])),fmt(int(r['taxonomy_resolved_rows'])),pct(int(r['taxonomy_resolved_rows']),int(r['transaction_candidate_rows'])),pct(int(r['mcc_only_resolved_rows']),int(r['transaction_candidate_rows'])),r['active_leaf_categories']] for r in datasets])
    body+='<img src="figures/coverage_comparison.png" alt="Kapsam karşılaştırması"><img src="figures/main_category_heatmap.png" alt="Ana kategori dağılımı">'
    body+='<h2>Birleşik havuzdaki 72 alt kategori</h2><p>Sıfır veya düşük sayım kaynakta gerçekten işlem bulunmadığını kanıtlamaz. Etiketleme kuralları ve sınıflar arasındaki sınırlar da sonucu etkiler. Özellikle online_subscriptions ve exams_and_certification, kompakt eğitim seti örneklenmeden önce ayrıca incelenmelidir.</p>'+disttable(pool)
    body+='<h2>Seyreklik</h2>'+table(['Kaynak','Dolu','Boş','1–9 satır','En az 100','En az 1.000'],[[r['source_id'],r['active_classes'],r['zero_classes'],r['classes_1_to_9'],r['classes_at_least_100'],r['classes_at_least_1000']] for r in sparse])
    body+='<h2>CSV ve yöntem dosyaları</h2><ul>'+''.join('<li>'+link(name,name)+'</li>' for name in sorted(CSV_TABLES|{'mcc_taxonomy_crosstab.csv','class_sparsity.csv','file_inventory.csv','analysis_summary.json','taxonomy.json','verification_summary.json'}))+'</ul>'
    body+='<p>MCC çapraz tablosu yalnız kodlar, taxonomy etiketleri, yöntem ve sayımları içerir. Kaynak MCC açıklamaları çıkarılarak aynı anahtarlar tekrar toplandı. Entropi ve ayrışma tabloları yapısal ölçülerdir; doğruluk göstergesi değildir. Tutarlar/para birimleri birleştirilmedi.</p>'
    body+='<h2>58 dosyanın ayrı dağılımları</h2>'+table(['Dosya','Ana havuza dahil','Tüm kayıtlar'],[[link(f'files/{r["file_id"]}.html',r['source_file']),r['is_primary_input'],fmt(int(r['reader_rows_excluding_header']))] for r in inventory])
    body+='<h2>Yöntem ve doğrulama</h2><p>Dar işlem açıklaması, satıcı kuralları, MCC kodu/açıklaması ve sınırlı kaynak kategorileri kullanıldı. Çelişkili, yetersiz veya kapsam dışı kanıtlar açık durum değerleriyle korundu. NOT_A_TRANSACTION işlem paydasına dahil değildir. Yalnız MCC dönüşümü ve taxonomy aynı kategori sözlüğüne göre karşılaştırılır.</p>'
    body+='<p>Özgün girdi seçimi kamu harcaması ağırlıklıdır; genel tüketici harcamalarını temsil ettiği varsayılamaz. Eski tüm-kaynaklar birleşimi güncel kaynaklarla aynı içerikte olmadığı için ana havuza alınmadı. Doğrudan okunamayan üç özgün CSV için daha önce kaydedilmiş özgün hash’lerle eşitliği doğrulanmış erişim kopyaları kullanıldı. Kaynak dosyaların boyut/değişiklik zamanları da kontrol edildi.</p>'
    body+=f'<p>{verification["data_files_verified"]} dosyanın {fmt(verification["records_verified"])} satırı ve {fmt(verification["source_cells_verified"])} özgün hücresi kontrol edildi. Kaynak klasöre yazılmadı. Kod: '+link('../../taxonomy_pipeline/README.txt','yeniden üretim yönergeleri')+'; '+link('../../taxonomy_pipeline/rules.py','etiketleme kuralları')+'.</p>'
    (OUT/'ANALIZ_RAPORU.html').write_text(page('72 sınıflı taxonomy: toplu etiketleme sonuçları',body),encoding='utf-8')

    # GitHub renders the root README, so the headline results are visible there.
    start='<!-- BEGIN TAXONOMY RESULTS -->';end='<!-- END TAXONOMY RESULTS -->'
    section=f'''{start}
## Taxonomy labeling results

Aggregate results for the 16-parent, 72-leaf taxonomy are available in
[outputs/taxonomy](outputs/taxonomy/ANALIZ_RAPORU.html). Download/open the HTML
report locally; GitHub displays HTML source rather than rendering a website.

| Measure | Result |
| --- | ---: |
| Physical data files processed | {summary['data_files']} |
| Reader records across all copies | {summary['physical_reader_rows']:,} |
| Primary inputs / sources | {summary['primary_files']} / {summary['sources']} |
| Transaction candidates in the primary pool | {summary['pool_transaction_candidates']:,} |
| Taxonomy-assigned rows | {summary['pool_resolved']:,} |
| Taxonomy coverage | {summary['pool_coverage']:.2%} |
| MCC-only conversion coverage | {summary['mcc_only_coverage']:.2%} |
| Observed taxonomy leaves | {summary['active_leaves']} / 72 |

The [source × label distribution](outputs/taxonomy/all_label_distributions.csv),
[pooled 72-class counts](outputs/taxonomy/pool_label_distribution.csv),
[source summaries](outputs/taxonomy/dataset_summary.csv) and
[class sparsity](outputs/taxonomy/class_sparsity.csv) are directly readable on GitHub.
Zero/rare predictions do not establish absence in the underlying data. These are
automatic weak labels; coverage is not accuracy or proof of superiority to MCC.
The compact training dataset has not yet been built. Counts are records, not
unique merchants or deduplicated transactions.

Only aggregate results are included here. Transaction files, merchant examples,
annotation samples, raw category wording and row-level audit files remain local.
Source/reference terms remain as documented in [DATA_LICENSING.md](DATA_LICENSING.md).
Regenerate this aggregate package after local analysis:

```powershell
python taxonomy_pipeline/export_results.py
```
{end}'''
    readme=BASE/'README.md';text=readme.read_text(encoding='utf-8')
    if start in text:text=text[:text.index(start)]+section+text[text.index(end)+len(end):]
    else:text=text.rstrip()+'\n\n'+section+'\n'
    readme.write_text(text,encoding='utf-8')
    validate()

def validate():
    _,inventory=read_csv(OUT/'file_inventory.csv')
    _,datasets=read_csv(OUT/'dataset_summary.csv')
    allowed=CSV_TABLES|{'mcc_taxonomy_crosstab.csv','class_sparsity.csv',
        'file_inventory.csv','analysis_summary.json','taxonomy.json',
        'verification_summary.json','ANALIZ_RAPORU.html','export_manifest.json'}
    allowed|={f'files/{r["file_id"]}.html' for r in inventory}
    allowed|={f'sources/{r["source_id"]}.html' for r in datasets}
    allowed|={f'figures/{name}' for name in ['coverage_comparison.png',
        'coverage_comparison.svg','main_category_heatmap.png','main_category_heatmap.svg']}
    actual={p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file()}
    assert not actual-allowed,('Unexpected file in aggregate package',actual-allowed)
    assert not (allowed-{'export_manifest.json'})-actual,('Missing aggregate result',allowed-actual)
    class Links(HTMLParser):
        def handle_starttag(self,tag,attrs):
            for k,v in attrs:
                if k in {'href','src'} and v and not urlparse(v).scheme:
                    assert (self.path.parent/unquote(v).split('#')[0]).exists(),(self.path,v)
    for p in OUT.rglob('*'):
        if not p.is_file():continue
        assert p.stat().st_size<2_000_000,(p,'unexpected large output')
        assert p.suffix in {'.csv','.json','.html','.png','.svg'},p
        if p.suffix=='.csv':
            fields,_=read_csv(p);assert not FORBIDDEN_COLUMNS.intersection(fields),p
        if p.suffix=='.html':
            parser=Links();parser.path=p;parser.feed(p.read_text(encoding='utf-8'))
    files=[p for p in OUT.rglob('*') if p.is_file()]
    save_json(OUT/'export_manifest.json',{'export_kind':'aggregate_results_only',
        'excluded':['transaction_records','merchant_examples','raw_mcc_descriptions',
                    'annotation_samples','row_level_audits','private_absolute_paths'],
        'files':[{'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,
            'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files) if p.name!='export_manifest.json']})
    print(json.dumps({'aggregate_files':sum(p.is_file() for p in OUT.rglob('*')),
        'source_distribution_rows':11*76,'physical_file_distribution_rows':58*76,
        'local_links':'passed','transaction_records_included':False}))

if __name__=='__main__':main()
