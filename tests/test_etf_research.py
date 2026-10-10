import unittest,sys,copy,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_edge_lab import daily_bars
from corporate_actions import signal_features,split_position,reconcile,parse_distributions
from etf_research import simulate,run
from etf_protocol import SYMBOLS,PROTOCOL
from excursions import initial,report
from execution import COSTS

class CorporateResearch(unittest.TestCase):
    def data(self):
        bars=daily_bars(125)
        for i,b in enumerate(bars):p=100+i;b.update(open=p,low=p-.1,high=p+.1,close=p)
        return dict(reference=[b['datetime'] for b in bars],**{s:{'raw':copy.deepcopy(bars),'events':[]} for s in SYMBOLS})
    def protocol(self,data):return dict(PROTOCOL,development_start=data['reference'][100],development_end=data['reference'][-1])

    def test_past_features_unchanged_by_future_actions(self):
        d=self.data();bars=d['IWM']['raw'];events=[dict(type='distribution',ex_date=bars[120]['datetime'],pay_date=bars[124]['datetime'],amount=1)]
        first=signal_features(bars,[]);second=signal_features(bars,events)
        self.assertEqual({k:v for k,v in first.items() if k<bars[120]['datetime']},{k:v for k,v in second.items() if k<bars[120]['datetime']})
        self.assertNotEqual(first[bars[120]['datetime']]['exit_ma'],second[bars[120]['datetime']]['exit_ma'])

    def test_split_keeps_economic_cost_r_and_excursions(self):
        p=dict(qty=2,stop=95,position_value=201,planned_loss=25,excursion=initial(100,2,25))
        p['excursion'].update(lowest_observed=90,highest_observed=120)
        q=split_position(p,4)
        self.assertEqual(q['qty']*q['stop'],p['qty']*p['stop']);self.assertEqual(q['position_value'],p['position_value'])
        self.assertEqual(report(q['excursion'])['mae_dollars'],report(p['excursion'])['mae_dollars'])
        self.assertEqual(report(q['excursion'])['mfe_r'],report(p['excursion'])['mfe_r'])

    def test_split_does_not_create_a_false_stop_or_change_profit(self):
        d=self.data()
        with patch('etf_research.PROTOCOL',self.protocol(d)):base=simulate(d)
        split=copy.deepcopy(d);stamp=d['reference'][110]
        for s in SYMBOLS:
            split[s]['events']=[dict(type='split',effective_date=stamp,new_per_old=2)]
            for b in split[s]['raw'][110:]:
                for k in ('open','low','high','close'):b[k]/=2
        with patch('etf_research.PROTOCOL',self.protocol(d)):r=simulate(split)
        self.assertEqual([t['reason'] for t in base['trade_log']],[t['reason'] for t in r['trade_log']])
        self.assertAlmostEqual(base['net_pnl'],r['net_pnl'],places=8)

    def test_ex_date_entitlement_receivable_payment_and_no_double_count(self):
        d=self.data();ex=d['reference'][110];pay=d['reference'][115]
        for s in SYMBOLS:d[s]['events']=[dict(type='distribution',ex_date=ex,pay_date=pay,amount=1)]
        with patch('etf_research.PROTOCOL',self.protocol(d)):r=simulate(d)
        self.assertGreater(r['distributions_earned'],0)
        self.assertAlmostEqual(sum(f['amount'] for f in r['cashflows'] if f['kind']=='PAYMENT'),r['distributions_earned'])
        self.assertAlmostEqual(r['ending_equity']-5000,r['net_pnl'])
        self.assertGreater(next(p['receivables'] for p in r['equity_curve'] if p['day']==ex),0)
        for s in SYMBOLS:d[s]['events']=[dict(type='distribution',ex_date=d['reference'][101],pay_date=pay,amount=1)]
        with patch('etf_research.PROTOCOL',self.protocol(d)):r=simulate(d)
        self.assertEqual(r['distributions_earned'],0) # purchases on ex-date are not entitled

    def test_unpaid_income_is_equity_but_not_spendable_cash(self):
        d=self.data()
        for s in SYMBOLS:d[s]['events']=[dict(type='distribution',ex_date=d['reference'][120],pay_date='2015-01-02',amount=1)]
        with patch('etf_research.PROTOCOL',self.protocol(d)):r=simulate(d)
        receivable=sum(e['amount'] for e in r['outstanding_receivables'])
        self.assertGreater(receivable,0);self.assertAlmostEqual(r['ending_equity'],r['ending_cash']+receivable)

    def test_reconciliation_blocks_missing_events_sessions_and_unverified_split(self):
        raw=[dict(datetime='2006-01-03',open=100,high=101,low=99,close=100,volume=1),dict(datetime='2015-12-31',open=99,high=100,low=98,close=99,volume=1)]
        allp=copy.deepcopy(raw)
        for k in ('open','high','low','close'):allp[0][k]*=.99
        dist={'events':[dict(type='distribution',ex_date='2015-12-31',pay_date='2016-01-05',amount=1)]}
        good=reconcile(raw,raw,allp,dist,[b['datetime'] for b in raw],'2006-01-01','2015-12-31');self.assertTrue(good['passed'])
        self.assertFalse(reconcile(raw,raw,allp,{'events':[]},[b['datetime'] for b in raw],'2006-01-01','2015-12-31')['passed'])
        self.assertFalse(reconcile(raw,raw,allp,dist,['2006-01-03','2015-12-30','2015-12-31'],'2006-01-01','2015-12-31')['passed'])
        adjusted=copy.deepcopy(raw)
        for k in ('open','high','low','close'):adjusted[0][k]/=2
        result=reconcile(raw,adjusted,adjusted,{'events':[]},[b['datetime'] for b in raw],'2006-01-01','2015-12-31')
        self.assertIn('SPLIT_EVENT_REQUIRES_INDEPENDENT_VERIFICATION',result['issues'])

    def test_bad_inputs_block_all_performance_calculation(self):
        d=self.data();checks={s:{'passed':False,'issues':['MISSING_EVENT']} for s in SYMBOLS}
        with patch('etf_research.simulate',side_effect=AssertionError('Must not calculate')):r=run(d,checks)
        self.assertIsNone(r['stress']);self.assertEqual(r['agent_report']['verdict'],'INVESTIGATE');self.assertFalse(r['forward_paper_eligible'])

    def test_missing_distribution_sheet_is_not_assumed_zero(self):
        with self.assertRaises(ValueError):parse_distributions('IEF',b'<ss:Workbook xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"/>')

import test_operations as base
class ETFWorkflow(base.Operations):
    def test_auth_registration_deduplication_and_preserved_ledger(self):
        from fastapi.testclient import TestClient
        room=base.room
        c=room.db();c.execute('INSERT INTO edge_lab_runs VALUES (?,?,?,?,?,?,?,?)',('daily-source','DAILY','fixture',room.utcnow(),'COMPLETE','{}','{}',json.dumps({'SPY:2006-01-01':{'bars':[{'datetime':'2006-01-03'}]}})));c.commit();c.close()
        with patch('etf_lab_api.threading.Thread'):
            with TestClient(room.app) as client:
                self.assertEqual(client.get('/etf-lab').status_code,401);client.auth=('operator','test-password')
                self.assertEqual(client.post('/etf-lab/start').status_code,401)
                h={'X-Control-Token':'test-control-token'};first=client.post('/etf-lab/start',headers=h).json();second=client.post('/etf-lab/start',headers=h).json()
                self.assertEqual(first['id'],second['id']);self.assertEqual(first['payload']['provider_requests'],0)
                self.assertEqual(first['dataset'] if 'dataset' in first else None,None)
                self.assertEqual(client.post('/etf-lab/'+first['id']+'/retry-data',headers=h).status_code,409)
                self.assertFalse(client.get('/etf-lab').json()['activation_allowed'])
                room.init_db();self.assertEqual(client.get('/etf-lab/'+first['id']).json()['protocol'],first['protocol'])
                self.assertEqual(room.positions(),[]);self.assertEqual(room.get_state()['cash'],5000)
                self.assertNotIn('IAU',room.INSTRUMENTS)

for name in list(base.Operations.__dict__):
    if name.startswith('test_'):setattr(ETFWorkflow,name,None)
