"""Prepared-source contracts: first-row retention, dates, selection and merge."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from data_profile.src import sources
from data_profile.src import oklahoma_refresh as refresh


class OklahomaRefresh(unittest.TestCase):
    def config(self):
        return next(c for c in sources.configurations() if c['source_id']=='oklahoma')

    def test_prepared_reader_keeps_first_record_and_omits_identity(self):
        cfg=self.config()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'FY2027.csv'
            path.write_text('txn_date,merchant,amount,Last Name,First Initial,Cardholder Name\n2026-07-01,EXAMPLE SHOP,12.30,EXAMPLE,A,A EXAMPLE\n',encoding='utf-8')
            rows=list(sources.read_records(cfg,path))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][1],2)
        self.assertEqual(rows[0][2]['merchant'],'EXAMPLE SHOP')
        self.assertFalse(sources.PII_COLUMNS.intersection(rows[0][2]))

    def test_fiscal_2027_is_not_a_future_transaction_date(self):
        cfg=self.config();path=sources.ROOT/cfg['folder']/'birlesik/oklahoma_FY2027.csv'
        raw={'txn_date':'2026-07-01','date_source':'transaction','merchant':'EXAMPLE SHOP','amount':'12.30','fiscal_year':'2027','agency':'TEST AGENCY','mcc_desc':'Grocery Stores','item_desc':'PAPER','resource_id':'fixture-resource','source_file':'original.csv','package_title':'FY2027'}
        record,labels,reason=sources.canonical_record(cfg,path,'',2,raw)
        self.assertEqual(reason,'')
        self.assertEqual(record['txn_date'],'2026-07-01')
        self.assertEqual(record['fiscal_year'],'2027')
        self.assertEqual(record['upstream_source_file'],'original.csv')
        self.assertEqual(record['upstream_resource_id'],'fixture-resource')
        self.assertEqual(record['date_semantics'],'transaction')
        self.assertEqual(labels[0]['scheme'],'oklahoma_item_desc')

    def test_period_imputation_remains_period_semantics(self):
        cfg=self.config();path=sources.ROOT/cfg['folder']/'birlesik/oklahoma_FY2010.csv'
        raw={'txn_date':'2009-07-01','date_source':'period','merchant':'EXAMPLE SHOP','amount':'12.30','fiscal_year':'2010'}
        record,_,_=sources.canonical_record(cfg,path,'',2,raw)
        self.assertEqual(record['date_semantics'],'period')
        self.assertEqual(record['upstream_date_source'],'period')
        self.assertEqual(record['date_raw'],'2009-07-01')

    def test_only_fiscal_inputs_are_selected(self):
        cfg=self.config()
        with tempfile.TemporaryDirectory() as folder, patch.object(sources,'ROOT',Path(folder)):
            root=Path(folder)/cfg['folder'];(root/'birlesik').mkdir(parents=True)
            for name in ['oklahoma_FY2026.csv','oklahoma_FY2027.csv','birlesik_tam.csv']:
                (root/'birlesik'/name).write_text('amount\n1\n',encoding='utf-8')
            (root/'birlesik_tam.csv').write_text('amount\n1\n',encoding='utf-8')
            selected=sources.source_files(cfg)
            self.assertEqual([p.name for p in selected],['oklahoma_FY2026.csv','oklahoma_FY2027.csv'])

    def test_merge_preserves_quoted_multiline_cells_and_exact_amounts(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);derived=root/'derived';derived.mkdir();data=root/'data';data.mkdir()
            a=data/'FY2026.csv';b=data/'FY2027.csv'
            a.write_bytes(b'amount,merchant\r\n12.30,"SHOP, A\nSECOND LINE"\r\n')
            b.write_bytes(b'amount,merchant\n-0.10,SHOP B')
            cfg={'folder':'data','expected_input_rows':2}
            with patch.object(refresh,'ROOT',root),patch.object(refresh,'DERIVED',derived),patch.object(refresh,'config',return_value=cfg),patch.object(refresh,'source_files',return_value=[a,b]):
                refresh.prepare()
            with (data/'birlesik_tam.csv').open(encoding='utf-8',newline='') as f:
                merged=list(csv.DictReader(f))
            self.assertEqual(merged,[{'amount':'12.30','merchant':'SHOP, A\nSECOND LINE'},{'amount':'-0.10','merchant':'SHOP B'}])
            result=json.loads((derived/'oklahoma_merged_verification.json').read_text())
            self.assertEqual(result['amount_total_usd'],'12.20')
            self.assertEqual(result['rows'],2)
            self.assertEqual(a.read_bytes(),b'amount,merchant\r\n12.30,"SHOP, A\nSECOND LINE"\r\n')


if __name__=='__main__':unittest.main()
