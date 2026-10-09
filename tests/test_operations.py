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
                self.assertEqual(result['status'],'NO_NEW_BAR')

if __name__=='__main__': unittest.main()
