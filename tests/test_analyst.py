import unittest,math,json
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from fastapi.testclient import TestClient
import test_operations as base
from analyst_tools import analyse,atr,rsi,trend
room=base.room

class AnalystTools(base.Operations):
    def series(self,n=90,direction=1):
        start=datetime(2025,1,1,9,30)
        return [dict(datetime=(start+timedelta(hours=i*4)).isoformat(sep=' '),open=100+direction*i*.2,close=100+direction*i*.2+.1,high=100+direction*i*.2+1,low=100+direction*i*.2-1,volume=1000) for i in range(n)]
    def now(self,bars):return datetime.fromisoformat(bars[-1]['datetime']).replace(tzinfo=room.ZoneInfo('America/New_York')).astimezone(timezone.utc)+timedelta(hours=4,minutes=20)
    def test_known_rsi_atr_and_insufficient_data(self):
        self.assertEqual(rsi(list(range(1,30))),100);self.assertEqual(rsi(list(range(30,1,-1))),0);self.assertEqual(rsi([100]*30),50)
        self.assertIsNone(rsi([100]*14));self.assertIsNone(atr(self.series(14)))
        gap=[dict(open=100,high=101,low=99,close=100),dict(open=110,high=112,low=109,close=111)]
        self.assertEqual(atr(gap,1),12)
    def test_rising_falling_and_volume_context(self):
        up=self.series();self.assertEqual(trend(up)['regime'],'UPTREND');self.assertEqual(trend(self.series(direction=-1))['regime'],'DOWNTREND')
        up[-1]['volume']=2000;r=analyse('AAPL',up,up,now=self.now(up))
        self.assertAlmostEqual(r['volume_ratio'],2);self.assertAlmostEqual(r['relative_strength']['excess_percentage_points'],0)
        self.assertIsNone(analyse('AAPL',self.series(30),now=self.now(up))['trend']['sma50'])
    def test_future_data_cannot_change_report(self):
        bars=self.series();now=self.now(bars);first=analyse('AAPL',bars,bars,now=now)
        future=dict(bars[-1],datetime=(datetime.fromisoformat(bars[-1]['datetime'])+timedelta(hours=8)).isoformat(sep=' '),open=300,high=302,low=299,close=301)
        second=analyse('AAPL',bars+[future],bars+[future],now=now)
        for key in ('trend','market','relative_strength','rsi14','atr14','context_hash','series'):self.assertEqual(first[key],second[key])
    def test_unaligned_benchmark_and_missing_volume_remain_unknown(self):
        bars=self.series();now=self.now(bars);bars[-1]['volume']=0
        r=analyse('AAPL',bars,bars[:-1],now=now)
        self.assertIsNone(r['relative_strength']);self.assertIsNone(r['volume_ratio'])
        self.assertTrue(any('not aligned' in f for f in r['flags']))
        self.assertIsNone(analyse('SPY',bars,bars,now=now)['relative_strength'])
    def test_snapshot_history_and_trade_policy_are_preserved(self):
        first=room.process_bars(self.bars);self.assertEqual(first['status'],'ENTRY_QUEUED')
        reports=room.analyst_analysis_history('SPY');self.assertEqual(len(reports),1)
        room.process_bars(self.bars);self.assertEqual(len(room.analyst_analysis_history('SPY')),1)
        self.fill_next();p=room.journal()['trades'][0];self.assertIn('analysis',p['context']['candidate'])
        before=room.get_state();room.init_db();self.assertEqual(room.get_state(),before)
        self.assertTrue(room.analyst_analysis_history('SPY'))
    def test_brain_auth_read_only_and_knowledge_provenance(self):
        room.process_bars(self.bars);old=room.analyst_analysis_history('SPY')[0]
        draft=room.create_knowledge(room.KnowledgeInput(title='Trend evidence',content='<script>text only</script>',agents=['Analyst']),'test-control-token')
        self.assertNotIn(draft['id'],[k['id'] for k in room.build_analysis('SPY')['knowledge']])
        room.update_knowledge(draft['id'],room.KnowledgeInput(expected_version=1,title='Trend evidence',content='<script>text only</script>',evidence='Review assumptions',status='approved',agents=['Analyst']),'test-control-token')
        current=room.build_analysis('SPY');self.assertIn(draft['id'],[k['id'] for k in current['knowledge']]);self.assertNotIn(draft['id'],[k['id'] for k in old['knowledge']])
        with TestClient(room.app) as client:
            self.assertEqual(client.get('/analyst').status_code,401);self.assertEqual(client.get('/analyst-analysis').status_code,401)
            client.auth=('operator','test-password');before=room.get_state();positions=room.positions();raw=room.state_raw()
            with patch.object(room.TwelveDataAdapter,'latest_completed_bars',side_effect=AssertionError('Must use saved data')):
                response=client.get('/analyst-analysis');self.assertEqual(response.status_code,200);self.assertEqual(len(response.json()['reports']),16);self.assertEqual(response.json()['extra_provider_requests'],0)
            self.assertEqual(room.get_state(),before);self.assertEqual(room.positions(),positions);self.assertEqual(room.state_raw(),raw)
            self.assertEqual(client.get('/analyst-analysis/UNKNOWN/history').status_code,404)

for name in list(base.Operations.__dict__):
    if name.startswith('test_'):setattr(AnalystTools,name,None)
if __name__=='__main__':unittest.main()
