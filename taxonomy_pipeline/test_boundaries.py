"""Semantic boundaries that matter to the thesis, separate from data integrity."""
import unittest
from inspect_inputs import BASE
from rules import Classifier,label
from run import Adapter

class SemanticBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.c=Classifier(BASE)
    def classify(self,**kw):
        fields=dict(sid='oklahoma',merchant='',desc='',rawcode='',purpose='',procurement='',category='',record_type='')
        fields.update(kw);return self.c.classify(**fields)
    def test_broad_utility_does_not_invent_an_energy_purchase(self):
        self.assertEqual(self.classify(rawcode='4900')[0],'UNRESOLVED_AMBIGUOUS')
    def test_utility_can_be_resolved_by_explicit_purpose(self):
        self.assertEqual(self.classify(rawcode='4900',purpose='Water bill')[0],label('water_and_waste'))
    def test_account_principal_is_not_a_financial_fee(self):
        self.assertEqual(self.classify(sid='moneydata',merchant='SAVE THE CHANGE',category='Savings')[0],'UNRESOLVED_OUT_OF_TAXONOMY')
    def test_actual_bank_fee_remains_in_scope(self):
        self.assertEqual(self.classify(sid='moneydata',merchant='NON-GBP TRANS FEE',category='Others')[0],label('financial_services_and_fees'))
    def test_item_can_change_marketplace_channel_to_purchase_purpose(self):
        r=self.classify(merchant='AMAZON',purpose='Copy paper',rawcode='5999')
        self.assertEqual(r[0],label('office_supplies_and_stationery'));self.assertTrue(r[-1])
    def test_mixed_recognized_basket_does_not_choose_first_rule(self):
        self.assertEqual(self.classify(merchant='AMAZON',purpose='COPY PAPER|SOFTWARE LICENSE')[0],'UNRESOLVED_AMBIGUOUS')
    def test_zero_return_is_preserved_as_nontransaction(self):
        self.assertEqual(self.classify(sid='ipo',merchant='Zero Return',record_type='zero_return')[0],'NOT_A_TRANSACTION')
    def test_unknown_supplier_does_not_become_business_services(self):
        self.assertEqual(self.classify(merchant='XYZZZ')[0],'UNRESOLVED_INSUFFICIENT_EVIDENCE')
    def test_numeric_code_inside_description_is_recognized_and_audited(self):
        r=self.classify(desc='4131 - Bus Lines, Including Charters, Tour Buses')
        self.assertEqual((r[0],r[3],r[5]),(label('public_transit_and_rail'),'4131','embedded_mcc_in_description'))
    def test_indiana_textual_mcc_is_not_treated_as_numeric(self):
        a=Adapter(['Merchant Name','Merchant Category Code','Transaction Amount'],'indiana')
        evidence=a.evidence(['AGENT FEE','Misc Air Carriers, Airlines','-40.00'])
        self.assertEqual(evidence[3],'');self.assertEqual(self.c.classify(*evidence)[0],label('airlines'))
    def test_description_of_service_is_more_informative_than_opaque_name(self):
        self.assertEqual(self.classify(sid='dwp',merchant='PRESTIGE NETWORK',purpose='Payment of interpreter services')[0],label('professional_services'))
    def test_marketplace_hosting_is_not_general_shopping(self):
        self.assertEqual(self.classify(merchant='AMAZON WEB SERVICES')[0],label('it_services_and_hosting'))
    def test_property_rent_has_no_fabricated_leaf(self):
        self.assertEqual(self.classify(rawcode='6513')[0],'UNRESOLVED_OUT_OF_TAXONOMY')
if __name__=='__main__':unittest.main()
