import unittest
import numpy as np
from data_profile.src.common import entropy,normalized_entropy
from data_profile.src.purity import informative,bootstrapped_entropy


class Metrics(unittest.TestCase):
    def test_entropy_and_bootstrap(self):
        self.assertEqual(entropy([20]),0.)
        self.assertAlmostEqual(normalized_entropy([10,10]),1.)
        a=bootstrapped_entropy([30,10],'repeatable')
        b=bootstrapped_entropy([30,10],'repeatable')
        self.assertEqual(a,b)
        self.assertTrue(0<=a[1]<=a[2]<=1)

    def test_placeholder(self):
        self.assertFalse(informative('GENERAL PURCHASE'))
        self.assertFalse(informative('Transaction Line Item'))
        self.assertTrue(informative('COPY PAPER WHITE A4'))

    def test_majority_ties_and_entropy(self):
        import polars as pl
        from data_profile.src.consistency import majority_table
        counts=pl.DataFrame({'source_id':['x','x','x'],'key_loose':['a','a','b'],'mcc':['1','2','3'],'transactions':[10,10,30]})
        result=majority_table(counts,'mcc')
        a=result.filter(pl.col('key_loose')=='a').row(0,named=True)
        self.assertTrue(a['majority_tied'])
        self.assertAlmostEqual(a['entropy_bits'],1)
        self.assertEqual(a['majority_share'],.5)


if __name__=='__main__':unittest.main()
