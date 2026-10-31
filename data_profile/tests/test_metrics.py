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


if __name__=='__main__':unittest.main()
