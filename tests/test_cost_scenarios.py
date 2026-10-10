import unittest,sys,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cost_scenarios import SCENARIOS,PROTOCOL,diagnose,attributed_metrics
from cost_diagnostics import SCENARIOS as OLD_SCENARIOS
from execution import COSTS,fill
from research_engine import simulate
import test_research as research_tests
import test_operations as base

class CostMath(unittest.TestCase):
    def test_roundtrip_scenarios_and_original_costs_unchanged(self):
        expected={'current_35bps':6.2,'stock_per_trade_fx':7.7,'stock_fx_10bps':3.7,'stock_usd_balance':2.7,'etf_per_trade_fx':5.7,'etf_usd_balance':.7,'zero_all_costs':0}
        for name,c in SCENARIOS.items():self.assertAlmostEqual(fill(100,5,'buy',c)['cash']-fill(100,5,'sell',c)['cash'],expected[name],places=7)
        self.assertEqual(COSTS.fx_bps,35);self.assertEqual(COSTS.fee_per_order,1);self.assertEqual(len(OLD_SCENARIOS),5)
        self.assertEqual(PROTOCOL['calculations'],len(PROTOCOL['variants'])*len(SCENARIOS)*2)
    def test_fixed_partial_path_cost_attribution(self):
        bars=[{'datetime':'entry','open':100}];buy=fill(100,5,'buy');exits=[fill(105,2.5,'sell'),fill(95,2.5,'sell')];pnl=sum(x['cash'] for x in exits)-buy['cash']
        r={'net_pnl':pnl,'trade_log':[{'entry_time':'entry','risk':25,'pnl':pnl,'r':pnl/25,'exits':[{'qty':x['qty'],'price':x['price']} for x in exits]}]}
        for c in SCENARIOS.values():
            m=attributed_metrics(r['trade_log'],bars,c)
            self.assertAlmostEqual(m['gross_expectancy_r']-m['cost_per_trade_r'],m['expectancy_r'])
        m=attributed_metrics(r['trade_log'],bars,COSTS)
        self.assertAlmostEqual(m['net_pnl'],r['net_pnl'])
        self.assertIsNone(attributed_metrics([],bars,COSTS)['cost_per_trade_r'])
    def test_every_declared_scenario_runs_without_activation(self):
        r=diagnose('SPY',research_tests.ResearchOperations().dataset(),126)
        self.assertEqual(len(r['variants']),8);self.assertFalse(r['promotion_allowed']);self.assertFalse(r['edge_validated'])
        for v in r['variants']:
            self.assertEqual(set(v['scenarios']),set(SCENARIOS))
            for x in v['scenarios'].values():
                m=x['resized_simulation']
                if m['trades']:self.assertAlmostEqual(m['gross_expectancy_r']-m['cost_per_trade_r'],m['expectancy_r'])

class CostAPI(base.Operations):
    def test_versioned_registration_auth_dedup_and_preservation(self):
        from fastapi.testclient import TestClient
        room=base.room;bars=research_tests.ResearchOperations().dataset();c=room.db()
        c.execute('INSERT INTO research_runs VALUES (?,?,?,?,?,?,?,?,?,?)',('source',room.utcnow(),'SPY','test-key',json.dumps(room.PROTOCOL),'start','end','COMPLETE',json.dumps({'split_index':126}),json.dumps(bars)));c.commit();c.close()
        with patch('edge_lab_api.threading.Thread'),TestClient(room.app) as client:
            self.assertEqual(client.get('/research-accountability').status_code,401);client.auth=('operator','test-password')
            self.assertEqual(client.post('/edge-lab/cost-scenarios',json={'source_run_id':'source'}).status_code,401)
            headers={'X-Control-Token':'test-control-token'}
            a=client.post('/edge-lab/cost-scenarios',json={'source_run_id':'source'},headers=headers).json()
            b=client.post('/edge-lab/cost-scenarios',json={'source_run_id':'source'},headers=headers).json()
            self.assertEqual(a['id'],b['id']);self.assertEqual(a['status'],'COMPLETE');self.assertEqual(a['protocol']['version'],'cost-diagnostic-v2')
            q=client.get('/research-accountability').json();self.assertEqual(q['registered_strategy_slots'],16);self.assertFalse(q['deflated_sharpe']['available'])
            frozen=client.get('/edge-lab/'+a['id']).json()
            self.assertEqual(client.post('/edge-lab/cost-stress',json={'source_run_id':'source'}).status_code,401)
            stress=client.post('/edge-lab/cost-stress',json={'source_run_id':'source'},headers=headers).json()
            self.assertEqual(stress['status'],'COMPLETE');self.assertEqual(stress['protocol']['calculations'],224)
            self.assertEqual(client.post('/edge-lab/cost-stress',json={'source_run_id':'source'},headers=headers).json()['id'],stress['id'])
            self.assertEqual(client.get('/edge-lab/'+a['id']).json(),frozen)
            self.assertEqual(client.get('/research-accountability').json()['registered_strategy_slots'],24)
            self.assertEqual(room.positions(),[]);self.assertEqual(room.get_state()['cash'],5000)
            c=room.db();old=c.execute('SELECT payload FROM research_runs WHERE id=?',('source',)).fetchone();c.close();self.assertEqual(json.loads(old['payload']),{'split_index':126})
            room.init_db();self.assertEqual(client.get('/edge-lab/'+a['id']).json()['protocol'],a['protocol'])

for name in list(base.Operations.__dict__):
    if name.startswith('test_'):setattr(CostAPI,name,None)
