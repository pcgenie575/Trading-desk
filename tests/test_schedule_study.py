import unittest,copy,json,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datetime import date
from unittest.mock import patch
from weekly_research import simulate as scheduled
from portfolio_research import simulate as original,PROTOCOL as PORTFOLIO
from funding_study import VERSION as FUNDED,PROTOCOL as FUNDED_PROTOCOL,source_fingerprint as funding_fingerprint,SCENARIOS
from schedule_study import calculate,VERSION,PROTOCOL
from execution import COSTS
from daily_research import STRESS,digest
from test_edge_lab import daily_bars
import test_operations as base
room=base.room

class ScheduleEngine(unittest.TestCase):
    def data(self):
        bars=daily_bars(190)
        for i,b in enumerate(bars):
            p=100+i*.2;b.update(open=p,high=p+.05,low=p-.05,close=p,volume=1000)
        return {s:copy.deepcopy(bars) for s in PORTFOLIO['symbols']}
    def test_daily_mode_exact_parity_with_frozen_engine(self):
        data=self.data()
        for costs in (COSTS,STRESS,SCENARIOS['funded_reserve']['costs'],SCENARIOS['funded_double_costs']['costs']):
            for cash in (5000,4961.832061068702):self.assertEqual(original(data,costs,initial_cash=cash),scheduled(data,costs,initial_cash=cash))
        with self.assertRaises(ValueError):scheduled(data,review_schedule='thursday')
    def test_only_friday_new_decisions_but_daily_marks(self):
        data=self.data();r=scheduled(data,review_schedule='friday')
        queued=[x for x in r['risk_decisions'] if x['phase']=='QUEUE'];self.assertTrue(queued)
        self.assertTrue(all(date.fromisoformat(x['day']).weekday()==4 for x in queued))
        self.assertEqual(len(r['equity_curve']),len(data['SPY']))
        self.assertTrue(all(t['entry_time']>queued[0]['day'] for t in r['trade_log']))
    def test_midweek_gap_exits_and_freeze_are_not_delayed(self):
        data=self.data();prior=scheduled(data,review_schedule='friday');entry=prior['trade_log'][0]['entry_time']
        gap=next(b['datetime'] for b in data['SPY'] if b['datetime']>entry and date.fromisoformat(b['datetime']).weekday()==1)
        for bars in data.values():
            for b in bars:
                if b['datetime']>=gap:b.update(open=60,high=61,low=59,close=60)
        r=scheduled(data,review_schedule='friday');self.assertEqual(r['trade_log'][0]['exit_time'],gap)
        self.assertEqual(r['trade_log'][0]['reason'],'OPENING_GAP_STOP');self.assertTrue(r['freeze'])
        self.assertTrue(all(x['open_positions']==0 for x in r['equity_curve'] if x['day']>=gap))
    def test_friday_absence_does_not_move_decision_to_thursday(self):
        data=self.data();initial=scheduled(data,review_schedule='friday');first=next(x['day'] for x in initial['risk_decisions'] if x['phase']=='QUEUE')
        for symbol in data:data[symbol]=[b for b in data[symbol] if b['datetime']!=first]
        r=scheduled(data,review_schedule='friday');queued=[x['day'] for x in r['risk_decisions'] if x['phase']=='QUEUE']
        self.assertTrue(queued);self.assertTrue(all(date.fromisoformat(x).weekday()==4 for x in queued));self.assertGreater(min(queued),first)
    def test_future_prices_and_modified_baselines_are_rejected(self):
        data=self.data();r=scheduled(data,review_schedule='friday')
        for bars in data.values():bars.append(dict(datetime='2016-01-04',open=1,high=2,low=1,close=1,volume=1))
        self.assertEqual(r,scheduled(data,review_schedule='friday'))
        with self.assertRaises(ValueError):calculate(data,{'dataset_hash':'wrong'})
        self.assertFalse(PROTOCOL['promotion_allowed']);self.assertEqual(PROTOCOL['candidate']['exit_buffer_pct'],0)

class ScheduleWorkflow(unittest.TestCase):
    setUp=base.Operations.setUp
    tearDown=base.Operations.tearDown
    def test_registration_precedes_calculation_and_keeps_prior_study(self):
        from fastapi.testclient import TestClient
        called=[];source_protocol={'study':FUNDED_PROTOCOL,'source_fingerprint':funding_fingerprint()}
        def run(data,baseline):
            c=room.db();row=c.execute('SELECT status,payload FROM schedule_studies WHERE id=?',(VERSION,)).fetchone();c.close()
            self.assertEqual(row['status'],'RUNNING');self.assertTrue(json.loads(row['payload'])['dataset_hash']);called.append(1)
            return {'decision':'REJECT_DEVELOPMENT','promotion_allowed':False,'scenarios':{}}
        with TestClient(room.app) as client:
            self.assertEqual(client.get('/schedule-lab').status_code,401);client.auth=('operator','test-password')
            self.assertEqual(client.post('/schedule-lab/register').status_code,401)
            c=room.db();c.execute('INSERT INTO funding_studies VALUES (?,?,?,?,?,?)',(FUNDED,room.utcnow(),'COMPLETE',json.dumps(source_protocol),json.dumps({'SPY':[]}),json.dumps({'old':'REJECTED'})));c.commit();c.close()
            before=room.get_state();positions=room.positions()
            with patch('schedule_study.calculate',side_effect=run):
                headers={'X-Control-Token':'test-control-token'};self.assertEqual(client.post('/schedule-lab/register',headers=headers).status_code,200)
                for _ in range(100):
                    r=client.get('/schedule-lab').json()
                    if r['status']=='COMPLETE':break
                    time.sleep(.02)
                self.assertEqual(r['status'],'COMPLETE');self.assertTrue(r['installed_source_matches'])
                self.assertEqual(client.post('/schedule-lab/register',headers=headers).json()['status'],'COMPLETE');self.assertEqual(len(called),1)
            self.assertEqual(room.get_state(),before);self.assertEqual(room.positions(),positions)
            c=room.db();self.assertEqual(json.loads(c.execute('SELECT payload FROM funding_studies').fetchone()[0]),{'old':'REJECTED'});c.close()
            inventory=client.get('/research-accountability').json()['records']
            self.assertEqual({x['kind'] for x in inventory},{'FUNDED_TURNOVER','WEEKLY_SCHEDULE'})
            self.assertTrue(all(x['new_hypotheses']==1 for x in inventory))
