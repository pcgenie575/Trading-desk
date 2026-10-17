import unittest,json,sys,time,copy
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from funding_study import funding,settle,calculate,screen,PROTOCOL,VERSION
from portfolio_research import simulate,PROTOCOL as PORTFOLIO
from execution import COSTS
from test_edge_lab import daily_bars
import test_operations as base
room=base.room

class FundingMath(unittest.TestCase):
    def test_funding_once_withdrawal_once_and_exact_bridge(self):
        f=funding(5000,.655,.005);r=settle(f['funded_usd'],f,.005)
        self.assertAlmostEqual(f['funded_usd'],4961.832061068702)
        self.assertLess(r['net_contributed_capital_usd_equivalent'],0)
        self.assertAlmostEqual(r['bridge_residual'],0,places=8)
        self.assertNotAlmostEqual(f['funding_cost_usd_equivalent'],5000*.005)
        clean=funding(5000,.655,0);self.assertEqual(clean['funded_usd'],5000)
        self.assertAlmostEqual(settle(5100,clean,0)['net_contributed_capital_usd_equivalent'],100)
    def test_invalid_rates_and_money_rejected(self):
        for args in ((-1,.65,.005),(5000,0,0),(5000,.65,.7),(5000,float('nan'),0)):
            with self.assertRaises(ValueError):funding(*args)
        with self.assertRaises(ValueError):settle(-1,funding(5000,.655,.005),0)
    def data(self):
        bars=daily_bars(160)
        for i,b in enumerate(bars):
            p=100+i*.2
            if 110<=i<=113:p=116.5
            b.update(open=p,high=p+.05,low=p-.05,close=p,volume=1000)
        return {s:copy.deepcopy(bars) for s in PORTFOLIO['symbols']}
    def test_buffer_uses_same_stops_and_can_avoid_a_small_ma_cross(self):
        d=self.data();normal=simulate(d);buffer=simulate(d,exit_buffer_pct=.01)
        self.assertEqual(normal,simulate(d,exit_buffer_pct=0,initial_cash=5000))
        self.assertTrue(normal['trade_log']);self.assertTrue(buffer['trade_log'])
        self.assertLess(normal['trade_log'][0]['exit_time'],buffer['trade_log'][0]['exit_time'])
        for bars in d.values():
            for b in bars[110:]:b.update(open=80,high=81,low=79,close=80)
        a=simulate(d);b=simulate(d,exit_buffer_pct=.01)
        self.assertEqual(a['trade_log'][0],b['trade_log'][0]);self.assertEqual(a['trade_log'][0]['reason'],'OPENING_GAP_STOP')
        self.assertTrue(a['freeze']);self.assertTrue(b['freeze'])
    def test_no_future_prices_or_live_cost_mutation(self):
        data=self.data();a=simulate(data,exit_buffer_pct=.01,initial_cash=4960)
        for bars in data.values():bars.append(dict(datetime='2016-01-04',open=1,high=2,low=1,close=1,volume=1))
        self.assertEqual(a,simulate(data,exit_buffer_pct=.01,initial_cash=4960));self.assertEqual(COSTS.fx_bps,35)
        with self.assertRaises(ValueError):calculate(data)
    def test_small_or_cost_floor_samples_do_not_qualify(self):
        m={'trade_log':[],'expectancy_r':None,'max_drawdown':0,'order_count':0,'remaining_unliquidated_symbols':[]}
        c={'simulation':m,'settlement':{'net_contributed_capital_usd_equivalent':100}}
        gate=screen(c,c);self.assertFalse(gate['passed']);self.assertFalse(gate['promotion_allowed'])
        self.assertFalse(PROTOCOL['promotion_allowed']);self.assertEqual(PROTOCOL['candidate']['exit_buffer_pct'],.01)

class FundingWorkflow(unittest.TestCase):
    setUp=base.Operations.setUp
    tearDown=base.Operations.tearDown
    def test_registration_precedes_math_and_existing_results_are_preserved(self):
        from fastapi.testclient import TestClient
        from daily_research import PROTOCOL as DAILY
        pages={s+':2006-01-01':{'bars':[dict(datetime='2006-01-03',open=100,high=101,low=99,close=100,volume=1)]} for s in PORTFOLIO['symbols']}
        c=room.db();c.execute('INSERT INTO edge_lab_runs VALUES (?,?,?,?,?,?,?,?)',('source','DAILY','key',room.utcnow(),'COMPLETE',json.dumps(DAILY),json.dumps({'old_result':'REJECTED'}),json.dumps(pages)));c.commit();c.close()
        calls=[]
        def compute(data):
            c=room.db();row=c.execute('SELECT * FROM funding_studies WHERE id=?',(VERSION,)).fetchone();c.close()
            self.assertEqual(row['status'],'RUNNING');self.assertTrue(json.loads(row['payload'])['dataset_hash']);calls.append(1)
            return {'decision':'REJECT_DEVELOPMENT','promotion_allowed':False,'scenarios':{}}
        with patch('funding_study.calculate',side_effect=compute):
            with TestClient(room.app) as client:
                self.assertEqual(client.get('/funding-lab').status_code,401)
                client.auth=('operator','test-password');self.assertEqual(client.post('/funding-lab/register').status_code,401)
                before=room.get_state();positions=room.positions()
                headers={'X-Control-Token':'test-control-token'}
                self.assertEqual(client.post('/funding-lab/register',headers=headers).status_code,200)
                for _ in range(100):
                    result=client.get('/funding-lab').json()
                    if result['status']=='COMPLETE':break
                    time.sleep(.02)
                self.assertEqual(result['status'],'COMPLETE');self.assertTrue(result['installed_source_matches'])
                self.assertEqual(client.post('/funding-lab/register',headers=headers).json()['status'],'COMPLETE')
                self.assertEqual(len(calls),1);self.assertEqual(room.get_state(),before);self.assertEqual(room.positions(),positions)
                c=room.db();self.assertEqual(json.loads(c.execute("SELECT payload FROM edge_lab_runs WHERE id='source'").fetchone()[0]),{'old_result':'REJECTED'});c.close()
