import unittest,sys,json,math
from pathlib import Path
from datetime import datetime,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from execution import sized_entry,fill
from exposure import correlation,check
from research_engine import compare,simulate,validate_bars
import test_operations as base
room=base.room

class ResearchOperations(base.Operations):
    # Base operations remain in their own suite.
    def test_cost_adjusted_size_and_gap_cash(self):
        f=sized_entry(110,104.5)
        self.assertLessEqual(f['cash'],500);self.assertLessEqual(f['planned_loss'],25)
        self.assertGreater(f['fee'],1);self.assertGreater(f['spread'],0)
        self.assertIsNone(sized_entry(100,104.5))
        room.process_bars(self.bars);self.fill_next();p=room.open_position()
        before=room.get_state()['cash'];room.paper_exit(p,90,self.bars[-1]['datetime'],'GAP')
        closed=room.positions()[0];self.assertLess(closed['realized_pnl'],-25)
        self.assertAlmostEqual(room.get_state()['cash'],5000+closed['realized_pnl'])
        self.assertGreater(closed['estimated_costs'],closed['entry_fee']+closed['exit_fee'])

    def test_correlation_and_unknown_overlap(self):
        a={str(i):100+math.sin(i)*2+i*.1 for i in range(50)}
        rho,n=correlation(a,a);self.assertAlmostEqual(rho,1);self.assertEqual(n,49)
        active=[dict(symbol='SPY',position_value=500)]
        self.assertFalse(check('AAPL',400,active,{'SPY':a,'AAPL':a})[0])
        self.assertFalse(check('AAPL',400,active,{})[0])
        self.assertTrue(check('GLD',400,active,{})[0])
        self.assertFalse(check('MSFT',300,[dict(symbol='AAPL',position_value=500)],{})[0])

    def dataset(self):
        start=datetime(2025,1,1)
        bars=[]
        for i in range(180):
            price=100+i*.15+math.sin(i/5)*3
            bars.append(dict(datetime=(start+timedelta(hours=4*i)).isoformat(sep=' '),open=price-.1,high=price+1,low=price-1,close=price,volume=1000))
        return bars

    def test_research_later_period_costs_and_no_lookahead(self):
        bars=self.dataset();r=compare(bars,126)
        self.assertEqual(len(r['variants']),8);self.assertFalse(r['edge_validated'])
        for v in r['variants']:
            t=v['later_period'];self.assertTrue(all(x['entry_time']>=bars[126]['datetime'] for x in t['trade_log']))
            self.assertAlmostEqual(t['net_pnl'],sum(x['pnl'] for x in t['trade_log']))
            self.assertGreaterEqual(t['estimated_costs'],0)
            for trade in t['trade_log']:self.assertTrue(all(x['qty']>0 for x in trade['exits']))
        changed=[dict(b) for b in bars]
        for b in changed[126:]:
            for k in ('open','high','low','close'):b[k]*=2
        again=compare(changed,126)
        self.assertEqual([v['development'] for v in r['variants']],[v['development'] for v in again['variants']])
        self.assertGreater(r['benchmark_500']['estimated_costs'],0)

    def test_experiment_register_dedupe_reuse_and_persistence(self):
        from fastapi.testclient import TestClient
        with TestClient(room.app) as client:
            self.assertEqual(client.get('/experiments').status_code,401)
            client.auth=('operator','test-password');headers={'X-Control-Token':'test-control-token'}
            p=dict(symbol='SPY',use_cached=False,bars=self.dataset(),source='Synthetic validation only')
            self.assertEqual(client.post('/experiments',json=p).status_code,401)
            first=client.post('/experiments',json=p,headers=headers).json()
            self.assertEqual(first['status'],'COMPLETE');self.assertFalse(first['result']['test_period_reused'])
            self.assertTrue(client.post('/experiments',json=p,headers=headers).json()['reused_existing_run'])
            p['bars'][0]['volume']=2000
            second=client.post('/experiments',json=p,headers=headers).json();self.assertTrue(second['result']['test_period_reused'])
            room.init_db();self.assertEqual(len(client.get('/experiments').json()['runs']),2)
            self.assertEqual(len(client.get('/experiments/'+first['id']+'/dataset').json()['bars']),180)
            self.assertEqual(room.positions(),[]);self.assertEqual(room.get_state()['cash'],5000)
            p['bars'][1]['datetime']=p['bars'][0]['datetime']
            self.assertEqual(client.post('/experiments',json=p,headers=headers).status_code,422)

    def test_ma_exit_queues_and_fills_next_open(self):
        room.process_bars(self.bars);self.fill_next();p=room.open_position()
        bar=dict(self.bars[-1],datetime=(datetime.fromisoformat(self.bars[-1]['datetime'])+timedelta(hours=12)).isoformat(sep=' '),open=108,high=109,low=107,close=108)
        # Raise average without touching protective stop.
        history=[dict(b,open=120,high=121,low=119,close=120) for b in self.bars]+[bar]
        room.process_bars(history);self.assertIsNotNone(room.open_position());self.assertEqual(room.pending_orders()[0]['side'],'sell')
        nextbar=dict(bar,datetime=(datetime.fromisoformat(bar['datetime'])+timedelta(hours=8)).isoformat(sep=' '),open=90,high=92,low=89,close=91)
        room.init_db();room.process_bars(history+[nextbar]);self.assertIsNone(room.open_position())
        self.assertAlmostEqual(room.positions()[0]['exit_price'],90*.9993)

    def test_no_fill_before_decision_and_partial_conservation(self):
        room.process_bars(self.bars)
        too_early=dict(self.bars[-1],datetime=(datetime.fromisoformat(self.bars[-1]['datetime'])+timedelta(hours=4)).isoformat(sep=' '),open=112,high=114,low=111,close=113)
        self.assertEqual(room.process_bars(self.bars+[too_early])['status'],'ORDER_WAIT')
        self.assertIsNone(room.open_position())
        bars=self.dataset()
        for i,b in enumerate(bars):
            price=100+i*2
            b.update(open=price,close=price+1,high=price+1.5,low=price-.1)
        result=simulate(bars,126,'breakout','partial')
        self.assertTrue(any(e['reason']=='PARTIAL_1R' for t in result['trade_log'] for e in t['exits']))
        self.assertAlmostEqual(result['net_pnl'],sum(t['pnl'] for t in result['trade_log']))
        self.assertGreater(result['estimated_costs'],0)

    def test_forward_plan_waits_for_future_period_and_runs_once(self):
        bars=self.dataset();room.save_candles(bars[:179])
        con=room.db();con.execute('INSERT INTO forward_plans VALUES (?,?,?,?,?,?)',('test-forward','SPY',datetime.fromisoformat(bars[60]['datetime']).replace(tzinfo=room.ZoneInfo('America/New_York')).astimezone(room.timezone.utc).isoformat(),json.dumps(room.PROTOCOL,sort_keys=True),'COLLECTING',None));con.commit();con.close()
        room.maybe_forward_research();self.assertEqual(room.experiments()['runs'],[])
        room.save_candles(bars);room.maybe_forward_research()
        runs=room.experiments()['runs'];self.assertEqual(len(runs),1);self.assertEqual(runs[0]['status'],'COMPLETE')
        self.assertEqual(runs[0]['payload']['later_period_label'],'Reserved forward period')
        room.init_db();room.maybe_forward_research();self.assertEqual(len(room.experiments()['runs']),1)

    def test_weekly_report_is_persistent_and_unknown_adherence(self):
        room.maybe_weekly_report();r=room.weekly_reports()[0]['payload']
        self.assertEqual(r['decision'],'continue collecting');self.assertIsNone(r['expectancy_r']);self.assertIsNone(r['rule_adherence_pct'])
        room.init_db();room.maybe_weekly_report();self.assertEqual(len(room.weekly_reports()),1)

# Avoid running inherited methods twice while retaining the shared isolated fixture.
for name in list(base.Operations.__dict__):
    if name.startswith('test_'):setattr(ResearchOperations,name,None)
if __name__=='__main__':unittest.main()

