import csv
from collections import Counter
from pathlib import Path
from inspect_inputs import readable, ROOT
for folder, name in [('Mendeley Laramee Bank Data - UK','laramee26openBankTransactionData__01_Anonymized Original with Catego.csv'),('Solihull Purchase Card Data - UK','solihull_purchase_data.csv'),('Stockport Purchase Card Data - UK','purchase_card_all.csv'),('IPO Government Spending Data - UK','ipo_payments_merged.csv')]:
    with readable(ROOT/folder/name).open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        columns=[c for c in reader.fieldnames if c in ['Category','Procurement Classification: ProClass Label','Purpose of Expenditure','Procurement (Merchant) Category','Expense type','Description']]
        counts={k:Counter() for k in columns}
        for row in reader:
            for k in columns: counts[k][row.get(k,'')]+=1
    print(folder, {k:v.most_common(35) for k,v in counts.items()})
print('Oklahoma old header:',next(csv.reader((ROOT/'Oklahoma Data - USA/birlesik_tam.csv').open(encoding='utf-8-sig'))))
