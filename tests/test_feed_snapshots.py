import unittest,sys,copy,json
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from feed_snapshots import preserve_observed,historical_available,phase
from data_quality import assess
import test_operations as base

class FeedSnapshots(unittest.TestCase):
    def fixture(self):
        b=dict(datetime='2026-10-12 09:30:00',open=100,high=101,low=99,close=100,volume=100)
        raw=dict(b,close=100.05,volume=10000);saved={b['datetime']:b};origins={b['datetime']:{'first_seen':'2026-10-12T18:00:00+00:00','source_phase':'LIMITED_INTRADAY'}}
        return b,raw,saved,origins
    def test_documented_rollover_preserves_original_inputs_not_revised_prices(self):
        b,raw,saved,origins=self.fixture();before=copy.deepcopy((raw,saved,origins))
        bars,events=preserve_observed('SPY',[raw],saved,origins,datetime(2026,10,13,18,tzinfo=timezone.utc))
        self.assertEqual(bars,[b]);self.assertEqual(len(events),1);self.assertEqual((raw,saved,origins),before)
        self.assertFalse(assess('SPY',bars,now=datetime(2026,10,13,18,tzinfo=timezone.utc),saved=saved)['quarantined'])
    def test_unknown_and_final_history_revisions_remain_quarantined(self):
        b,raw,saved,origins=self.fixture()
        for source in ({},{b['datetime']:dict(origins[b['datetime']],source_phase='HISTORICAL')},{b['datetime']:dict(origins[b['datetime']],source_phase='REVIEWED_HISTORICAL')}):
            bars,events=preserve_observed('SPY',[raw],saved,source,datetime(2026,10,13,18,tzinfo=timezone.utc));self.assertEqual(bars,[raw]);self.assertFalse(events)
            self.assertTrue(assess('SPY',bars,now=datetime(2026,10,13,18,tzinfo=timezone.utc),saved=saved)['quarantined'])
    def test_premature_large_invalid_and_crypto_changes_are_not_hidden(self):
        b,raw,saved,origins=self.fixture()
        cases=[('SPY',raw,datetime(2026,10,12,21,tzinfo=timezone.utc)),('SPY',dict(raw,open=100.2),datetime(2026,10,13,18,tzinfo=timezone.utc)),('SPY',dict(raw,close=102),datetime(2026,10,13,18,tzinfo=timezone.utc)),('BTC/USD',raw,datetime(2026,10,13,18,tzinfo=timezone.utc))]
        for symbol,bar,now in cases:
            actual,events=preserve_observed(symbol,[bar],saved,origins,now);self.assertEqual(actual,[bar]);self.assertFalse(events)
    def test_weekends_holidays_dst_and_unknown_calendar(self):
        self.assertEqual(historical_available('2026-07-02 09:30:00').isoformat(),'2026-07-06T04:00:00+00:00')
        self.assertEqual(historical_available('2026-10-30 09:30:00').isoformat(),'2026-11-02T05:00:00+00:00')
        self.assertIsNone(historical_available('2028-12-29 09:30:00'))
        self.assertEqual(phase('2026-10-12 09:30:00','2026-10-12T18:00:00+00:00'),'LIMITED_INTRADAY')

class FeedPersistence(base.Operations):
    def test_only_new_candles_get_origins_and_raw_provider_evidence_survives(self):
        room=base.room;b=dict(datetime='2026-10-12 09:30:00',open=100,high=101,low=99,close=100,volume=100)
        with patch.object(room,'utcnow',return_value='2026-10-12T18:00:00+00:00'):room.save_candles([b])
        room.save_candles([dict(b,close=100.05,volume=10000)])
        c=room.db();origin=dict(c.execute('SELECT * FROM candle_origins').fetchone());c.close();self.assertEqual(origin['source_phase'],'LIMITED_INTRADAY')
        report=room.check_data_quality([dict(b,close=100.05,volume=10000)])
        self.assertEqual(report['canonical_bars'],[b]);self.assertEqual(len(report['source_transitions']),1)
        c=room.db();saved=json.loads(c.execute('SELECT payload FROM quality_reports WHERE context_hash=?',(report['context_hash'],)).fetchone()[0]);c.close()
        self.assertEqual(saved['input_bars'][0]['close'],100);self.assertEqual(saved['provider_input_bars'][0]['close'],100.05)
        room.init_db();c=room.db();self.assertEqual(c.execute('SELECT COUNT(*) FROM candle_origins').fetchone()[0],1);c.close()
        self.assertEqual(room.positions(),[])

for name in list(base.Operations.__dict__):
    if name.startswith('test_'):setattr(FeedPersistence,name,None)
