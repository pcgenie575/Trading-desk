import unittest,copy,json,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datetime import date
from unittest.mock import patch
from volatility_research import simulate as scheduled
from portfolio_research import simulate as original,PROTOCOL as PORTFOLIO
from funding_study import VERSION as FUNDED,PROTOCOL as FUNDED_PROTOCOL,source_fingerprint as funding_fingerprint,SCENARIOS
from volatility_study import calculate,VERSION,PROTOCOL
from execution import COSTS
from daily_research import STRESS,digest
from test_edge_lab import daily_bars
import test_operations as base
room=base.room

class VolatilityEngine(unittest.TestCase):
    def data(self):
        bars=daily_bars(190)
        for i,b in enumerate(bars):
            price=100+i*.2;b.update(open=price,high=price+.05,low=price-.05,close=price,volume=1000)
        return {s:copy.deepcopy(bars) for s in PORTFOLIO['symbols']}
    def test_disabled_mode_exact_parity(self):
        data=self.data()
        for costs in (COSTS,STRESS,SCENARIOS['funded_reserve']['costs'],SCENARIOS['funded_double_costs']['costs']):
            for cash in (5000,4961.832061068702):self.assertEqual(original(data,costs,initial_cash=cash),scheduled(data,costs,initial_cash=cash))
    def test_scale_only_reduces_and_requires_valid_completed_history(self):
        from volatility_research import risk_scale
        self.assertIsNone(risk_scale([100]*20))
        self.assertIsNone(risk_scale([100]*20+[float('nan')]))
        self.assertEqual(risk_scale([100]*21),1)
        self.assertLess(risk_scale([100 if i%2 else 110 for i in range(21)]),.2)
    def test_caps_are_saved_at_signal_and_never_increased_at_fill(self):
        from execution import sized_entry as real_size
        from volatility_research import risk_scale
        calls=[]
        def capture(raw,stop,cash,**kwargs):
            result=real_size(raw,stop,cash,**kwargs);calls.append((kwargs,result));return result
        data=self.data()
        with patch('volatility_research.risk_scale',return_value=.4),patch('volatility_research.sized_entry',side_effect=capture):
            result=scheduled(data,volatility_cap=True)
        self.assertTrue(result['trade_log'])
        for kw,fill in calls:
            self.assertEqual(kw['max_value'],200);self.assertEqual(kw['max_risk'],10)
            if fill:self.assertLessEqual(fill['planned_loss'],10+1e-8)
            if 'max_qty' in kw and fill:self.assertLessEqual(fill['qty'],kw['max_qty'])
        with patch('volatility_research.risk_scale',return_value=None):
            blocked=scheduled(data,volatility_cap=True)
        self.assertFalse(blocked['trade_log']);self.assertTrue(blocked['blocked_checks']['VOLATILITY_INPUT'])
    def test_future_prices_do_not_change_completed_history(self):
        data=self.data();before=scheduled(data,volatility_cap=True)
        for bars in data.values():bars.append(dict(datetime='2016-01-04',open=1,high=2,low=1,close=1,volume=1))
        self.assertEqual(before,scheduled(data,volatility_cap=True))
        with self.assertRaises(ValueError):calculate(data,{'dataset_hash':'wrong'})

class VolatilityWorkflow(unittest.TestCase):
    setUp=base.Operations.setUp
    tearDown=base.Operations.tearDown
    def test_registration_precedes_calculation_and_keeps_prior_study(self):
        from fastapi.testclient import TestClient
        called=[];source_protocol={'study':FUNDED_PROTOCOL,'source_fingerprint':funding_fingerprint()}
        def run(data,baseline):
            c=room.db();row=c.execute('SELECT status,payload FROM volatility_studies WHERE id=?',(VERSION,)).fetchone();c.close()
            self.assertEqual(row['status'],'RUNNING');self.assertTrue(json.loads(row['payload'])['dataset_hash']);called.append(1)
            return {'decision':'REJECT_DEVELOPMENT','promotion_allowed':False,'scenarios':{}}
        with TestClient(room.app) as client:
            self.assertEqual(client.get('/volatility-lab').status_code,401);client.auth=('operator','test-password')
            self.assertEqual(client.post('/volatility-lab/register').status_code,401)
            c=room.db();c.execute('INSERT INTO funding_studies VALUES (?,?,?,?,?,?)',(FUNDED,room.utcnow(),'COMPLETE',json.dumps(source_protocol),json.dumps({'SPY':[]}),json.dumps({'old':'REJECTED'})));c.commit();c.close()
            before=room.get_state();positions=room.positions()
            with patch('volatility_study.calculate',side_effect=run):
                headers={'X-Control-Token':'test-control-token'};self.assertEqual(client.post('/volatility-lab/register',headers=headers).status_code,200)
                for _ in range(100):
                    r=client.get('/volatility-lab').json()
                    if r['status']=='COMPLETE':break
                    time.sleep(.02)
                self.assertEqual(r['status'],'COMPLETE');self.assertTrue(r['installed_source_matches'])
                self.assertEqual(client.post('/volatility-lab/register',headers=headers).json()['status'],'COMPLETE');self.assertEqual(len(called),1)
            self.assertEqual(room.get_state(),before);self.assertEqual(room.positions(),positions)
            c=room.db();self.assertEqual(json.loads(c.execute('SELECT payload FROM funding_studies').fetchone()[0]),{'old':'REJECTED'});c.close()
            inventory=client.get('/research-accountability').json()['records']
            self.assertEqual({x['kind'] for x in inventory},{'FUNDED_TURNOVER','VOLATILITY_RISK'})
            self.assertTrue(all(x['new_hypotheses']==1 for x in inventory))
