"""Regression tests for data-specific ambiguities and non-destructive parsing."""
import unittest
from data_profile.src.common import parse_amount,parse_date,merchant_keys,split_card,split_mcc,redact_address


class Parsers(unittest.TestCase):
    def test_dates(self):
        self.assertEqual(parse_date('05/28/2024','USA')[0],'2024-05-28')
        self.assertEqual(parse_date('13/12/2018')[0],'2018-12-13')
        self.assertEqual(parse_date('2023-05-22T00:00:00.000Z')[0],'2023-05-22')
        self.assertEqual(parse_date('45853')[1],'excel_serial')
        self.assertEqual(parse_date('not a date')[1],'unparsed')
        self.assertEqual(parse_date('10-02-2026')[0],'2026-02-10')
        self.assertEqual(parse_date('16.10.2026')[0],'2026-10-16')
        self.assertEqual(parse_date('09.03.2017')[0],'2017-03-09')

    def test_amount(self):
        self.assertEqual(parse_amount('£1,234.90'),1234.9)
        self.assertEqual(parse_amount('.90'),.9)
        self.assertEqual(parse_amount('(12.50)'),-12.5)
        self.assertIsNone(parse_amount('unknown'))

    def test_mcc_card(self):
        self.assertEqual(split_mcc('5411 - Grocery Stores'),('5411','Grocery Stores'))
        self.assertEqual(split_card('USBKT'),('US Bank','T'))
        self.assertEqual(split_card('JPMCP'),('JPMorgan','P'))
        self.assertEqual(split_card('unexpected'),('unknown','unknown'))

    def test_keys(self):
        strict,loose,prefix=merchant_keys('SQ *CAFE #123 LONDON')
        self.assertEqual(strict,'CAFE LONDON')
        self.assertEqual(prefix,'SQ *')
        self.assertEqual(merchant_keys('WAL-MART 2345')[1],'WALMART')
        self.assertEqual(merchant_keys('STAPLS 123')[1],'STAPLES')
        self.assertNotEqual(merchant_keys('ALPHA CAFE')[1],merchant_keys('BETA CAFE')[1])
        self.assertEqual(merchant_keys('PAYPAL *STORE A1B2')[0],'STORE')

    def test_address(self):
        self.assertEqual(redact_address('123 Example Lane'),'ADDRESS_REDACTED')
        self.assertEqual(redact_address('GENERAL CREDITORS'),'GENERAL CREDITORS')

    def test_generic_merchant_is_not_necessarily_a_header(self):
        from pathlib import Path
        from data_profile.src.sources import configurations,canonical_record
        from data_profile.src.common import ROOT
        config=next(c for c in configurations() if c['source_id']=='delaware')
        path=ROOT/config['folder']/'state_employee_credit_card_transactions.csv'
        row={'merchant':'MERCHANT NAME','trans_dt':'2017-01-18T00:00:00.000','merchandise_amt':'28.75','cat_descr':'Eating Places Restaurants'}
        record,labels,reason=canonical_record(config,path,'',2,row)
        self.assertEqual(reason,'')
        self.assertEqual(record['merchant_raw'],'MERCHANT NAME')


if __name__=='__main__':
    unittest.main()
