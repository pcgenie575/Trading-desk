import unittest
from dataclasses import asdict
from cost_stress import SCENARIOS,PROTOCOL,doubled,diagnose
from cost_scenarios import SCENARIOS as BASE,diagnose as old_diagnose
from research_inventory import slots
import test_research as fixtures

class StressTests(unittest.TestCase):
    def test_all_components_double_and_zero_remains_zero(self):
        self.assertEqual(len(SCENARIOS),14);self.assertEqual(PROTOCOL['calculations'],224)
        for k,c in BASE.items():
            for field in ('half_spread_bps','slippage_bps','fee_per_order','fx_bps'):
                self.assertEqual(getattr(SCENARIOS[k+'_2x'],field),getattr(c,field)*2)
        self.assertEqual(SCENARIOS['etf_usd_balance_2x'].fx_bps,0)
    def test_normal_scenarios_equal_frozen_v2(self):
        bars=fixtures.ResearchOperations().dataset();old=old_diagnose('SPY',bars,126);new=diagnose('SPY',bars,126)
        for a,b in zip(old['variants'],new['variants']):
            for k in BASE:self.assertEqual(a['scenarios'][k],b['scenarios'][k])
        self.assertEqual(new['version'],'cost-diagnostic-v3');self.assertFalse(new['promotion_allowed'])
    def test_counts_derive_from_protocol_and_unknown_is_unknown(self):
        self.assertEqual(slots({'variants':[1,2],'baseline_neighbours':[3]},'DAILY'),3)
        self.assertEqual(slots({'source_protocol':{'entries':[1,2],'exits':[1,2,3]}},'COST'),6)
        self.assertEqual(slots(PROTOCOL,'COST'),8)
        self.assertIsNone(slots({'version':'unrecognized'},'COST'))
        self.assertEqual(slots({'experiment':{'strategy':{'trend':100}}},'ETF'),1)
