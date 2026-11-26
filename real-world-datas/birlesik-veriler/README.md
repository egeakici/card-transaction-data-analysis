# Güncel birleşik kaynak verisi

`tum_kaynaklar_birlesik.csv`: 9,847,852 veri satırı, 11 kaynak, 166 özgün alan ve 2 kaynak izleme alanı.
Oklahoma güncel FY2009–FY2027 sürümüdür: 6.883.868 satır. Endonezya dahil değildir.

## Sütunlar ve izlenebilirlik

Sütunlar konuma göre değil, özgün başlık adları birebir eşleştirilerek hizalandı.
`Amount`, `amount` ve ` Amount` gibi farklı adlar ayrı tutuldu. Başlıklar ve hücre değerleri değiştirilmedi.
Aynı başlığı kullanan kaynaklar aynı sütuna yazılır; o kaynakta bulunmayan sütunlar boş bırakılır.
`sutun_esleme.csv`, her kaynak alanının birleşik dosyadaki sütun numarasını ve adını gösterir.

- `kaynak_klasor`: Satırın geldiği kaynak klasörü. Girdi bu klasördeki `birlesik_tam.csv` dosyasıdır.
- `kaynak_satir_no`: O girdi CSV'sindeki kayıt numarası; başlık 1, ilk veri kaydı 2'dir.
  Hücre içi satır sonları nedeniyle fiziksel metin satırı numarası değildir.

UTF-8 BOM, virgül ayırıcı, CRLF satır sonları kullanıldı. Sayı, tarih ve kimlik yazımları korunmuştur.
Bu ham birleşime yeni MCC kodu veya `taxonomy_label` eklenmedi.
CSV okurken baştaki sıfırları korumak için alanları metin olarak okuyun; boş değerleri kendiliğinden sayıya çevirmeyin.

## Satır kapsamı

| Kaynak | Satır |
| --- | ---: |
| bristol | 12,205 |
| delaware | 2,251,316 |
| dwp | 8,026 |
| eden | 1,244 |
| indiana | 284,124 |
| ipo | 24 |
| moneydata | 6,609 |
| oklahoma | 6,883,868 |
| solihull | 111,257 |
| stockport | 34,010 |
| sunderland | 255,169 |
| Toplam | 9,847,852 |

Her kaynağın birleşik CSV'si yalnızca bir kez kullanıldı. Özgün dosyalar ve dönüşüm kopyaları ayrıca eklenmedi.
Kaynak içi tekrarlar silinmedi; satırlar filtrelenmedi. MoneyData'daki 42 açıklama satırı ve
Solihull'daki 1.380 işlem dışı not satırı korunur. Bu nedenle toplam, 9.846.430 satırlı
kanonik analizden 1.422 fazladır. Model eğitimi için işlem/etiket uygunluğu ayrıca seçilmelidir.

## Doğrulama

İkinci tam okumada her çıktı satırı özgün CSV kaydıyla bütün hücreleri, boş sütunları,
kaynak bilgisi ve sırası dahil birebir karşılaştırıldı. Girdi dosyalarının SHA-256 değerleri
işlem öncesi ve sonrası aynı kaldı. Ayrıntılar `birlestirme_raporu.json`, kaynak sayıları
`kaynak_ozeti.csv` dosyasındadır. Büyük CSV'yi Excel'in çalışma sayfası satır sınırı nedeniyle
Python/Polars gibi bir veri okuyucuyla kullanın.
