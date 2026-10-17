import unittest,json,sys,copy,subprocess,os
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
import test_operations as base
from profit_evidence import reconcile
from execution import fill
from evidence_lab import VERSION,collect
room=base.room

class Accounting(unittest.TestCase):
    def test_cost_bridge_and_legacy_unknown(self):
        buy=fill(100,2,'buy');sell=fill(110,2,'sell')
        p=dict(id='t',symbol='SPY',status='CLOSED',qty=2,position_value=buy['cash'],realized_pnl=sell['cash']-buy['cash'])
        state={'cash':5000+p['realized_pnl'],'equity':5000+p['realized_pnl']}
        r=reconcile([p],{}, {('t','buy'):buy,('t','sell'):sell},{},state,5000)
        self.assertAlmostEqual(r['trades'][0]['gross_before_recorded_costs'],20)
        self.assertEqual(r['incomplete_cost_trades'],0);self.assertAlmostEqual(r['cash_residual'],0)
        r=reconcile([p],{}, {('t','sell'):sell},{},state,5000)
        self.assertEqual(r['incomplete_cost_trades'],1);self.assertIsNone(r['trades'][0]['gross_before_recorded_costs'])
        self.assertFalse(r['gross_expectancy_available']);self.assertEqual(r['trades'][0]['missing_sides'],['buy'])
    def test_missing_mark_and_inconsistent_cash_are_visible(self):
        buy=fill(100,2,'buy');p=dict(id='t',symbol='AAPL',status='OPEN',qty=2,position_value=buy['cash'])
        r=reconcile([p],{}, {('t','buy'):buy},{},{'cash':4800,'equity':5000},5000)
        self.assertIsNone(r['open_mark_net']);self.assertIsNone(r['equity_residual']);self.assertNotEqual(r['cash_residual'],0)
        r=reconcile([p],{}, {('t','buy'):buy},{'AAPL':110},{'cash':5000-buy['cash'],'equity':5000-buy['cash']+220},5000)
        self.assertAlmostEqual(r['trades'][0]['gross_before_recorded_costs'],20)

class EvidenceWorkflow(unittest.TestCase):
    setUp=base.Operations.setUp
    tearDown=base.Operations.tearDown
    fill_next=base.Operations.fill_next
    def test_atomic_fills_reconcile_and_restart_does_not_backfill(self):
        room.process_bars(self.bars);self.fill_next();p=room.open_position()
        room.paper_exit(p,120,self.bars[-1]['datetime'],'TEST')
        evidence=room.EVIDENCE_LAB['overview']();profit=evidence['profit']
        self.assertEqual(profit['incomplete_cost_trades'],0);self.assertAlmostEqual(profit['cash_residual'],0)
        self.assertTrue(profit['trades'][0]['cashflows_reconcile'])
        c=room.db();self.assertEqual(c.execute('SELECT COUNT(*) FROM execution_evidence').fetchone()[0],2)
        c.execute('DELETE FROM execution_evidence');c.execute('DELETE FROM trade_context');c.commit();c.close()
        room.init_db();self.assertEqual(room.EVIDENCE_LAB['overview']()['profit']['incomplete_cost_trades'],1)
    def test_shadow_deduplicates_and_never_invents_profit(self):
        room.emit('Risk & Compliance','Paper Trader','REJECTED','BLOCKED','Test rejection',{'proposal_id':'p'})
        room.emit('Risk & Compliance','Paper Trader','REJECTED','BLOCKED','Test rejection',{'proposal_id':'p'})
        r=room.EVIDENCE_LAB['overview']()['shadow'];self.assertEqual(r['total'],1)
        self.assertIsNone(r['rows'][0]['payload']['counterfactual_pnl']);self.assertIsNone(r['rows'][0]['follow_up']['reference'])
        self.assertEqual(room.positions(),[])
    def test_future_collection_is_immutable_and_not_retroactive(self):
        room.EVIDENCE_LAB['setup']();c=room.db();plan=dict(c.execute('SELECT * FROM paired_collection').fetchone())
        registered=datetime.fromisoformat(plan['registered_at']);future=(registered+timedelta(days=2)).astimezone(timezone.utc)
        # Explicit UTC candle time exercises the strict after-registration boundary.
        b=dict(datetime=future.isoformat(),open=100,high=102,low=99,close=101,volume=100)
        collect(c,room.__dict__,'SPY',[dict(b,datetime=(registered-timedelta(days=2)).isoformat())],room.utcnow())
        collect(c,room.__dict__,'SPY',[b],room.utcnow());collect(c,room.__dict__,'SPY',[dict(b,close=102)],room.utcnow());c.commit()
        rows=c.execute('SELECT payload FROM paired_observations').fetchall();c.close()
        self.assertEqual(len(rows),1);self.assertEqual(json.loads(rows[0][0])['close'],101)
        a=room.EVIDENCE_LAB['overview']();self.assertFalse(a['paired']['candidate_orders_allowed']);self.assertEqual(a['paired']['status'],'WAITING_DEVELOPMENT_GATE')
        room.EVIDENCE_LAB['setup']();self.assertEqual(room.EVIDENCE_LAB['overview']()['paired']['registered_at'],plan['registered_at'])
    def test_replay_and_pages_require_existing_auth_and_control(self):
        from fastapi.testclient import TestClient
        with TestClient(room.app) as client:
            for path in ('/evidence','/evidence-lab','/profit-evidence'):self.assertEqual(client.get(path).status_code,401)
            client.auth=('operator','test-password');self.assertEqual(client.post('/evidence-lab/replay').status_code,401)
            self.assertEqual(client.get('/evidence-lab').status_code,200)
            with patch.object(room.TwelveDataAdapter,'latest_completed_bars',side_effect=AssertionError('No provider calls')):
                before=room.get_state();client.get('/evidence-lab');self.assertEqual(before,room.get_state())

class IsolatedReplay(unittest.TestCase):
    def test_virtual_clock_real_contracts_no_live_db_and_revision_freeze(self):
        from data_quality import slots,NY
        day=datetime(2026,1,5).date();bars=[]
        while len(bars)<70:
            for t in slots(day):
                p=100+len(bars)*.3
                bars.append(dict(datetime=t.strftime('%Y-%m-%d %H:%M:%S'),open=p,high=p+.15,low=p-.15,close=p+.1,volume=1000))
            day+=timedelta(days=1)
        events=[]
        for n in range(55,len(bars)+1):
            seen=datetime.fromisoformat(bars[n-1]['datetime']).replace(tzinfo=NY).astimezone(timezone.utc)+timedelta(hours=4,minutes=16)
            events.append(dict(symbol='SPY',observed_at=seen.isoformat(),bars=copy.deepcopy(bars[:n])))
        tmp=Path(os.getenv('TCR_TEST_DIR',str(Path.cwd()/'work'/'validation')));tmp.mkdir(parents=True,exist_ok=True)
        import tempfile
        with tempfile.TemporaryDirectory(dir=tmp) as d:
            source=Path(d)/'events.json';source.write_text(json.dumps(events));sentinel=Path(d)/'live.db';sentinel.write_bytes(b'DO NOT TOUCH')
            env=dict(os.environ,TCR_DB=str(sentinel))
            script=Path(__file__).resolve().parents[1]/'engine_replay.py'
            a=subprocess.run([sys.executable,str(script),str(source)],capture_output=True,text=True,env=env,timeout=60)
            self.assertEqual(a.returncode,0,a.stderr);r=json.loads(a.stdout)
            self.assertEqual(sentinel.read_bytes(),b'DO NOT TOUCH');self.assertEqual(r['provider_requests'],0)
            self.assertTrue(r['risk_decisions']);self.assertTrue(any(x['phase']=='FILL' for x in r['risk_decisions']))
            self.assertTrue(r['positions']);self.assertFalse(r['activation_allowed']);self.assertAlmostEqual(r['profit']['cash_residual'],0)
            changed=copy.deepcopy(events[-1]);changed['observed_at']=(datetime.fromisoformat(changed['observed_at'])+timedelta(minutes=2)).isoformat();changed['bars'][-2]['open']+=1
            changed['bars'][-2]['high']+=2;events.append(changed);source.write_text(json.dumps(events))
            b=subprocess.run([sys.executable,str(script),str(source)],capture_output=True,text=True,env=env,timeout=60)
            self.assertEqual(b.returncode,0,b.stderr);q=json.loads(b.stdout)
            self.assertTrue(q['account']['frozen']);self.assertIn('HISTORICAL_REVISION',q['account']['freeze_reason'])
            self.assertEqual([(p['entry_price'],p['qty']) for p in r['positions']],[(p['entry_price'],p['qty']) for p in q['positions']])
