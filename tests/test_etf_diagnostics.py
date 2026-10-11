import unittest, sys, copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from etf_diagnostics import diagnose

class InputDiagnostics(unittest.TestCase):
    def fixture(self):
        p={'symbols':['IEF'],'warmup_start':'2006-01-01','development_end':'2015-12-31'}
        bars=[{'datetime':'2006-01-31','close':100.},{'datetime':'2006-02-01','close':99.}]
        d={'pages':{f'IEF:{m}':{'bars':copy.deepcopy(bars)} for m in ['none','splits','all']},
           'distributions':{'IEF':{'coverage_verified':True,'events':[{'type':'distribution','ex_date':'2006-02-01','amount':1.}]}}}
        c={'IEF':{'passed':False,'issues':['DISTRIBUTION_RECONCILIATION:2006-02-01']}}
        return d,c,p
    def test_missing_adjustment_and_immutability(self):
        d,c,p=self.fixture();before=copy.deepcopy((d,c,p));r=diagnose(d,c,p)
        y=r['rows'][0]['distribution_adjustments_by_year']['2006']
        self.assertEqual(y,{'issuer_events':1,'mismatches':1,'apparently_unadjusted':1})
        self.assertFalse(r['rows'][0]['gate_passed']);self.assertEqual((d,c,p),before)
    def test_matched_adjustment_is_not_missing(self):
        d,c,p=self.fixture();d['pages']['IEF:all']['bars'][0]['close']=99.
        self.assertEqual(diagnose(d,c,p)['rows'][0]['distribution_adjustments_by_year']['2006']['mismatches'],0)
    def test_missing_source_remains_unknown(self):
        d,c,p=self.fixture();d['distributions']={};c['IEF']['issues']=['DISTRIBUTION_SOURCE_UNVERIFIED']
        r=diagnose(d,c,p)['rows'][0];self.assertFalse(r['distribution_coverage_verified']);self.assertTrue(r['next_actions'])
        self.assertEqual(r['distribution_adjustments_by_year'],{})
    def test_split_is_not_a_dividend(self):
        d,c,p=self.fixture();d['distributions']['IEF']['events']=[]
        d['pages']['IEF:none']['bars'][0]['close']=200.
        r=diagnose(d,c,p)['rows'][0];self.assertEqual(r['distribution_adjustments_by_year'],{})
    def test_invalid_and_missing_pairs_not_fabricated(self):
        d,c,p=self.fixture();d['pages']['IEF:all']['bars'][0]['close']=0
        self.assertEqual(diagnose(d,c,p)['rows'][0]['invalid_price_pairs'],1)
        d['pages']['IEF:all']['bars']=[]
        self.assertEqual(diagnose(d,c,p)['rows'][0]['mismatch_examples'],[])
    def test_partial_collection_cannot_pass(self):
        d,c,p=self.fixture();r=diagnose({}, {}, p)
        self.assertFalse(r['rows'][0]['gate_passed']);self.assertTrue(r['rows'][0]['next_actions'])
        self.assertEqual(r['extra_provider_requests'],0);self.assertFalse(r['activation_allowed'])
