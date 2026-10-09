import os
import sys
import tempfile
import unittest
import uuid
import time
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['TCR_CONTROL_TOKEN']='test-control-token'
os.environ['TCR_DASHBOARD_PASSWORD']='test-password'
os.environ.pop('TWELVE_DATA_API_KEY',None)
import app as room
from fastapi.testclient import TestClient

class Operations(unittest.TestCase):
    def setUp(self):
        self.tmp=Path(os.getenv('TCR_TEST_DIR',str(Path.cwd()/'work'/'validation')))/str(uuid.uuid4())
        self.tmp.mkdir(parents=True)
        room.DB=str(self.tmp/'ledger.db')
        room.init_db()
        now=datetime.now(ZoneInfo('America/New_York')).replace(tzinfo=None)
        self.bars=[dict(datetime=(now-timedelta(hours=4*(60-i))).isoformat(sep=' '),open=100,high=101,low=99,close=100,volume=1000) for i in range(60)]
        self.bars[-1].update(open=109,high=111,low=108,close=110)
        self.sig=room.signal_from_bars(self.bars)
    def tearDown(self):
        for item in self.tmp.iterdir(): item.unlink()
        self.tmp.rmdir()
    def test_entry_duplicate_restart_and_exit(self):
        result=room.process_bars(self.bars)
        self.assertEqual(result['status'],'PAPER_ENTRY')
        pos=room.open_position()
        self.assertLessEqual(pos['planned_loss'],25+1e-8)
        self.assertLessEqual(pos['position_value'],500+1e-8)
        before=room.get_state()
        room.init_db()
        self.assertEqual(room.get_state(),before)
        self.assertEqual(room.process_bars(self.bars)['status'],'NO_NEW_BAR')
        next_bar=dict(self.bars[-1],datetime=(datetime.fromisoformat(self.bars[-1]['datetime'])+timedelta(hours=4)).isoformat(sep=' '),open=90,high=92,low=89,close=91)
        room.process_bars(self.bars+[next_bar])
        self.assertIsNone(room.open_position())
        closed=room.positions()[0]
        self.assertAlmostEqual(closed['exit_price'],90*(1-0.0002))
        self.assertAlmostEqual(room.get_state()['cash'],5000+closed['realized_pnl'])
        self.assertTrue(any(m['type']=='PAPER_EXIT' for m in room.messages()))
    def test_transaction_rolls_back_on_failure(self):
        before=room.get_state()
        with patch.object(room,'emit',side_effect=RuntimeError('injected failure')):
            with self.assertRaises(RuntimeError): room.paper_enter(self.sig,self.bars[-1])
        self.assertEqual(before,room.get_state())
        self.assertIsNone(room.open_position())
    def test_daily_drawdown_and_invalid_risk(self):
        room.add_daily_pnl(-75)
        self.assertFalse(room.risk_check(self.sig)[0])
        with self.assertRaises(room.HTTPException): room.resume('test-control-token')
        room.add_daily_pnl(75)
        room.set_state('cash',4749)
        room.update_equity(100)
        self.assertTrue(room.get_state()['frozen'])
        self.assertFalse(room.risk_check(self.sig)[0])
        bad=dict(self.sig,quantity=float('nan'))
        self.assertFalse(room.risk_check(bad)[0])
    def test_http_auth_and_dashboard(self):
        with TestClient(room.app) as client:
            for path in ['/','/status','/messages','/positions','/docs']:
                self.assertEqual(client.get(path).status_code,401)
            client.auth=('operator','test-password')
            self.assertEqual(client.get('/').status_code,200)
            self.assertEqual(client.get('/status').json()['state']['cash'],5000)
            self.assertEqual(client.post('/freeze').status_code,401)
            self.assertEqual(client.post('/freeze',headers={'X-Control-Token':'test-control-token'}).status_code,200)
            self.assertEqual(client.get('/healthz').status_code,503)
    def test_scheduler_processes_mock_feed_once(self):
        with patch.dict(os.environ,{'TWELVE_DATA_API_KEY':'test-only'}), patch.object(room.TwelveDataAdapter,'latest_completed_bars',return_value=self.bars):
            with TestClient(room.app) as client:
                client.auth=('operator','test-password')
                for _ in range(100):
                    if room.state_raw().get('last_processed_bar'): break
                    time.sleep(0.01)
                self.assertTrue(client.get('/status').json()['scheduler_running'])
                self.assertEqual(client.get('/healthz').status_code,200)
                self.assertIsNotNone(room.open_position())
                result=client.post('/cycle',headers={'X-Control-Token':'test-control-token'}).json()
                self.assertIn(result['status'],('NO_NEW_BAR','SCAN_CYCLE'))
                self.assertEqual(len([p for p in room.positions() if p['symbol']=='SPY']),1)

    def test_multi_symbol_marks_checkpoints_and_portfolio_caps(self):
        for symbol in ['SPY','AAPL','MSFT']:
            room._local.symbol=symbol
            self.assertEqual(room.process_bars(self.bars)['status'],'PAPER_ENTRY')
            self.assertEqual(room.process_bars(self.bars)['status'],'NO_NEW_BAR')
        room._local.symbol='NVDA'
        self.assertEqual(room.process_bars(self.bars)['status'],'REJECTED')
        self.assertEqual(len(room.open_positions()),3)
        self.assertAlmostEqual(room.get_state()['equity'],room.get_state()['cash']+sum(p['qty']*110 for p in room.open_positions()))
        room._local.symbol='AAPL'
        aapl=room.open_position()
        room.paper_exit(aapl,120,self.bars[-1]['datetime'],'TEST')
        room.update_equity(120)
        self.assertEqual(len(room.open_positions()),2)
        before=room.get_state();room.init_db();self.assertEqual(room.get_state(),before)
        self.assertIn('last_processed_bar:AAPL',room.state_raw())
        room._local.symbol='SPY'

    def test_free_budget_persists_and_reserves_exit_capacity(self):
        day=datetime.now(room.timezone.utc).date().isoformat()
        room.set_state('credits:'+day,room.SCAN_CREDITS)
        self.assertFalse(room.reserve_credit(False))
        self.assertTrue(room.reserve_credit(True))
        room.init_db()
        self.assertEqual(room.coverage()['credits_used_today'],room.SCAN_CREDITS+1)
        room.set_state('credits:'+day,room.DAILY_CREDITS)
        self.assertFalse(room.reserve_credit(True))

    def test_crypto_observation_and_symbol_isolation(self):
        room._local.symbol='BTC/USD'
        self.assertFalse(room.risk_check(self.sig)[0])
        self.assertEqual(room.process_bars(self.bars,allow_entry=False)['status'],'ENTRY_SKIPPED')
        self.assertFalse(room.open_positions())
        room._local.symbol='SPY'
        self.assertEqual(room.process_bars(self.bars)['status'],'PAPER_ENTRY')
        self.assertEqual({b['symbol'] for b in room.candles(1000)},{'SPY','BTC/USD'})
        self.assertEqual(room.coverage()['instruments'][-2]['paper_enabled'],False)

    def test_trade_plan_and_review_persist_without_changing_execution(self):
        room.process_bars(self.bars)
        position=room.open_position();record=room.journal()['trades'][0]
        self.assertEqual({k:record['context']['candidate'][k] for k in self.sig},self.sig)
        self.assertEqual(record['context']['curriculum_version'],room.CURRICULUM_VERSION)
        self.assertIn('learning',record['context']['candidate'])
        self.assertEqual(record['context']['strategy'],'Trend Breakout v1')
        review=room.TradeReviewInput(review_status='reviewed',followed_rules='partial',rule_break='other',notes='<script>test text</script>')
        room.save_trade_review(position['id'],review,'test-control-token')
        room.init_db()
        stored=room.journal()['trades'][0]
        self.assertEqual(stored['notes'],review.notes)
        self.assertEqual(stored['rule_break'],'other')
        self.assertEqual(room.open_position(),position)
        self.assertEqual(stored['context'],record['context'])
        with TestClient(room.app) as client:
            self.assertEqual(client.get('/journal').status_code,401)
            client.auth=('operator','test-password')
            self.assertEqual(client.put('/journal/'+position['id']+'/review',json={}).status_code,401)
            headers={'X-Control-Token':'test-control-token'}
            self.assertEqual(client.put('/journal/missing/review',json={},headers=headers).status_code,404)
            self.assertEqual(client.put('/journal/'+position['id']+'/review',json={'notes':'x'*4001},headers=headers).status_code,422)
            self.assertEqual(client.put('/journal/'+position['id']+'/review',json={'rule_break':'unsupported'},headers=headers).status_code,422)
            self.assertEqual(client.get('/journal-ui.js').status_code,200)

    def test_legacy_trade_review_schema_migrates_without_fabricating_plan(self):
        room.paper_enter(self.sig,self.bars[-1]);pos=room.open_position()
        con=room.db();con.execute('DELETE FROM trade_context');con.execute('DROP TABLE trade_reviews')
        con.execute('CREATE TABLE trade_reviews(trade_id TEXT PRIMARY KEY,updated_at TEXT,review_status TEXT,followed_rules TEXT,notes TEXT)')
        con.execute('INSERT INTO trade_reviews VALUES (?,?,?,?,?)',(pos['id'],'saved','reviewed','yes','existing review'))
        con.commit();con.close();room.init_db()
        record=room.journal()['trades'][0]
        self.assertIsNone(record['context']);self.assertEqual(record['notes'],'existing review');self.assertEqual(record['rule_break'],'none')

    def test_book_curriculum_applies_sizing_checks_and_evidence_limits(self):
        course=room.curriculum();self.assertEqual(len(course['books']),5);self.assertEqual(len(course['agents']),7)
        self.assertTrue(course['self_check']['passed'])
        self.assertTrue(room.risk_check(self.sig)[0])
        self.assertFalse(room.risk_check(dict(self.sig,planned_loss=1))[0])
        self.assertFalse(room.risk_check(dict(self.sig,position_value=1))[0])
        rows=[dict(id='1',status='CLOSED',exit_time='2026-10-01',planned_loss=25,realized_pnl=50),
              dict(id='2',status='CLOSED',exit_time='2026-10-02',planned_loss=25,realized_pnl=-25),
              dict(id='3',status='OPEN',planned_loss=25,realized_pnl=999)]
        review=room.evidence_review(rows)
        self.assertEqual(review['eligible_r_trades'],2);self.assertEqual(review['mean_r'],.5)
        self.assertEqual(review['recent_loss_streak'],1);self.assertFalse(review['edge_validated'])
        many=[dict(rows[0],id=str(i)) for i in range(30)]
        self.assertEqual(room.evidence_review(many)['evidence_status'],'READY_FOR_REVIEW')
        self.assertFalse(room.evidence_review(many)['edge_validated'])
        with TestClient(room.app) as client:
            self.assertEqual(client.get('/training').status_code,401)
            client.auth=('operator','test-password')
            self.assertEqual(client.get('/training').json()['version'],room.CURRICULUM_VERSION)

if __name__=='__main__': unittest.main()
