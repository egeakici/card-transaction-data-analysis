import unittest
from pathlib import Path
import polars as pl
from data_profile.src.common import CONFIG


class Reference(unittest.TestCase):
    def test_reference_titles_and_page_continuation_categories(self):
        path=CONFIG/'mcc_reference_snapshot.csv'
        if not path.exists():self.skipTest('Reference not yet generated')
        df=pl.read_csv(path,infer_schema=False)
        rows={r['mcc_code']:r for r in df.to_dicts()}
        self.assertEqual(rows['5411']['description'],'Grocery Stores and Supermarkets')
        self.assertEqual(rows['0742']['description'],'Veterinary Services')
        self.assertEqual(rows['3000']['description'],'UNITED AIRLINES')
        self.assertEqual(rows['1520']['mcc_group'],'Contracted Services')
        self.assertEqual(rows['5811']['mcc_group'],'Service Providers')
        self.assertEqual(rows['5999']['mcc_group'],'Miscellaneous Stores')
        self.assertEqual(rows['2842']['mcc_group'],'Wholesale Distributors and Manufacturers')
        self.assertEqual(rows['3000']['mcc_group'],'Airlines')
        self.assertEqual(rows['3351']['mcc_group'],'Automobile/Vehicle Rentals')
        self.assertEqual(rows['3501']['mcc_group'],'Hotels and Motels')
        self.assertEqual(df['mcc_code'].n_unique(),df.height)


if __name__=='__main__':unittest.main()
