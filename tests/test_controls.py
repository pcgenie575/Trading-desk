import json,copy,unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from fastapi.testclient import TestClient
import test_operations as base
from data_quality import assess,NY,slots,expected
room=base.room

class Controls(base.Operations):
    def queued(self):
        room.process_bars(self.bars);con=room.db();row=con.execute("SELECT payload FROM pending_orders WHERE symbol='SPY'").fetchone();con.close();return json.loads(row[0])
    def later(self):
        b=dict(self.bars[-1],datetime=(datetime.fromisoformat(self.bars[-1]['datetime'])+timedelta(hours=8)).isoformat(sep=' '),open=112,high=114,low=111,close=113)
        room.save_candles([b]);room.check_data_quality([b]);return dict(b,fill_open=b['open'])
    def test_contract_binds_exact_proposal_and_prevents_replay(self):
        proposal=self.queued();bar=self.later()
        for key,value in [('quantity',proposal['quantity']*2),('symbol','AAPL'),('stop',1),('side','SHORT')]:
            self.assertFalse(room.validate_approval(dict(proposal,**{key:value}),bar)[0])
        room._local.symbol='AAPL'
        try:self.assertFalse(room.validate_approval(proposal,bar)[0])
        finally:room._local.symbol='SPY'
        self.assertFalse(room.validate_approval(proposal,dict(bar,open=1,fill_open=1))[0])
        self.assertFalse(room.validate_approval(proposal,dict(bar,datetime=(datetime.fromisoformat(bar['datetime'])+timedelta(days=8)).isoformat(sep=' ')))[0])
        tid=room.paper_enter(proposal,bar);self.assertIsNotNone(tid);self.assertIsNone(room.paper_enter(proposal,bar))
        con=room.db();self.assertEqual(con.execute('SELECT COUNT(*) FROM decision_consumptions').fetchone()[0],1);self.assertEqual(con.execute('SELECT COUNT(*) FROM risk_decisions').fetchone()[0],2);con.close()
        context=room.journal()['trades'][0]['context'];self.assertEqual(context['decision_contract']['proposal_id'],proposal['proposal_id']);self.assertIn('entry_regime',context['attribution'])
    def test_fresh_risk_veto_at_fill_and_unsigned_entry_block(self):
        proposal=self.queued();bar=self.later();room.freeze_system('Test veto')
        self.assertIsNone(room.paper_enter(proposal,bar));self.assertEqual(room.positions(),[])
        r=room.decision_evidence()['proposals'][0]['decisions'];self.assertEqual(r[-1]['decision'],'REJECT');self.assertTrue(any(c['code']=='NOT_FROZEN' and c['status']=='FAIL' for c in r[-1]['payload']['checks']))
        self.assertIsNone(room.paper_enter(self.sig,bar));self.assertEqual(room.get_state()['cash'],5000)
    def test_signature_tamper_and_transaction_rollback(self):
        proposal=self.queued();bar=self.later();con=room.db();row=con.execute('SELECT payload FROM risk_decisions WHERE id=?',(proposal['approval_id'],)).fetchone();payload=json.loads(row[0]);payload['signature']='0'*64;con.execute('UPDATE risk_decisions SET payload=? WHERE id=?',(json.dumps(payload),proposal['approval_id']));con.commit();con.close()
        self.assertFalse(room.validate_approval(proposal,bar)[0])
        # Direct database edits are detectable here; the DB is not a tamper-proof store.
    def test_consumption_and_ledger_roll_back_together(self):
        proposal=self.queued();bar=self.later();before=room.get_state();real_emit=room.emit
        def broken(sender,recipient,typ,*args,**kwargs):
            if typ=='PAPER_ENTRY':raise RuntimeError('Post-consumption failure')
            return real_emit(sender,recipient,typ,*args,**kwargs)
        with patch.object(room,'emit',side_effect=broken):
            with self.assertRaises(RuntimeError):room.paper_enter(proposal,bar)
        self.assertEqual(room.get_state(),before);self.assertEqual(room.positions(),[])
        con=room.db();self.assertEqual(con.execute('SELECT COUNT(*) FROM decision_consumptions').fetchone()[0],0);self.assertEqual(con.execute("SELECT COUNT(*) FROM risk_decisions WHERE phase='FILL'").fetchone()[0],0);con.close()
        room.init_db();self.assertTrue(room.validate_approval(proposal,bar)[0]);self.assertIsNotNone(room.paper_enter(proposal,bar))
        room.init_db();self.assertFalse(room.validate_approval(proposal,bar)[0])
    def test_missing_sessions_block_entries_but_trusted_stop_exit_remains(self):
        self.queued();self.fill_next();pos=room.open_position();self.quality_patch.stop()
        bars=[dict(datetime='2026-10-08 09:30:00',open=110,high=111,low=109,close=110,volume=1000),dict(datetime='2026-10-09 09:30:00',open=90,high=92,low=89,close=91,volume=1000)]
        # Move fixture checkpoint back to the earlier real session; never use this in production.
        room.set_state('last_processed_bar','2026-10-08 09:30:00')
        now=datetime(2026,10,9,14,tzinfo=NY).astimezone(timezone.utc)
        with patch.object(room,'assess_quality',side_effect=lambda symbol,bars,**kw:assess(symbol,bars,now=now,**kw)):
            result=room.process_bars(bars)
        self.assertEqual(result['status'],'POSITION_REVIEWED');self.assertIsNone(room.open_position());self.assertEqual(room.positions()[0]['exit_reason'],'PROTECTIVE_STOP')
    def test_legacy_cancel_and_new_contract_restart(self):
        con=room.db();con.execute('INSERT INTO pending_orders VALUES (?,?,?,?)',('AAPL','buy',self.bars[-1]['datetime'],json.dumps(self.sig)));con.execute('INSERT INTO pending_orders VALUES (?,?,?,?)',('GLD','sell',self.bars[-1]['datetime'],json.dumps({'trade_id':'legacy','reason':'EXIT'})));con.commit();con.close()
        proposal=self.queued();room.cancel_legacy_entries();room.init_db()
        self.assertEqual({o['symbol'] for o in room.pending_orders()},{'SPY','GLD'});self.assertTrue(room.validate_approval(proposal,self.later())[0]);self.assertTrue(any(m['type']=='LEGACY_ORDER_CANCELLED' for m in room.messages()))
    def test_gate_details_and_attribution_do_not_invent_legacy_regime(self):
        r=room.risk_assessment(self.sig);self.assertTrue(r['approved']);self.assertTrue({'CASH','SECTOR','EQUITY_GROUP','DAILY_LOSS','DRAWDOWN'}<={c['code'] for c in r['checks']})
        self.queued();self.fill_next();p=room.open_position();room.paper_exit(p,90,self.bars[-1]['datetime'],'TEST_EXIT');group=room.attribution()['groups'][0]
        self.assertAlmostEqual(group['net_pnl'],room.positions()[0]['realized_pnl']);self.assertEqual(group['entry_regime'],'MIXED')
        con=room.db();payload=json.loads(con.execute('SELECT payload FROM trade_context').fetchone()[0]);payload.pop('attribution');con.execute('UPDATE trade_context SET payload=?',(json.dumps(payload),));con.commit();con.close()
        self.assertEqual(room.attribution()['groups'][0]['entry_regime'],'UNKNOWN')
    def test_read_only_authenticated_evidence_and_history(self):
        self.queued()
        with TestClient(room.app) as client:
            for path in ['/controls','/decision-evidence','/attribution','/data-quality/SPY/history']:self.assertEqual(client.get(path).status_code,401)
            client.auth=('operator','test-password');before=room.state_raw();ps=room.positions();evidence=room.decision_evidence()
            with patch.object(room.TwelveDataAdapter,'latest_completed_bars',side_effect=AssertionError('No provider calls')):
                self.assertEqual(client.get('/decision-evidence').json()['total'],1);self.assertEqual(client.get('/attribution').json()['closed_trades'],0)
            self.assertEqual(before,room.state_raw());self.assertEqual(ps,room.positions());self.assertEqual(evidence,room.decision_evidence());self.assertEqual(client.get('/data-quality/NO/history').status_code,404)
    def test_real_quality_gate_quarantines_and_keeps_checkpoint_cash(self):
        self.quality_patch.stop();bar=dict(datetime='2026-10-09 09:30:00',open=100,high=101,low=99,close=100,volume=1000)
        before=room.get_state();bad=dict(bar,high=98)
        result=room.process_bars([bad]);self.assertEqual(result['status'],'DATA_QUARANTINED');self.assertEqual(room.get_state()['cash'],before['cash']);self.assertNotIn('last_processed_bar',room.state_raw());self.assertIsNone(room.latest_saved_bar())
        with self.assertRaises(room.HTTPException):room.resume('test-control-token')
        nanbar=dict(bar,volume=float('nan'));room.check_data_quality([nanbar]);saved=room.quality_history('SPY')[0]
        self.assertEqual(saved['input_bars'][0]['volume'],'nan');json.dumps(saved,allow_nan=False)
    def test_reviewed_revision_preserves_original_and_requires_resume(self):
        self.quality_patch.stop();bar=dict(datetime='2026-10-09 13:30:00',open=100,high=101,low=99,close=100,volume=1000)
        clock=patch.object(room,'assess_quality',side_effect=lambda symbol,bars,**kw:assess(symbol,bars,now=datetime(2026,10,9,18,tzinfo=NY).astimezone(timezone.utc),**kw));clock.start();self.addCleanup(clock.stop)
        room.save_candles([bar]);revised=dict(bar,low=98.99);report=room.check_data_quality([revised]);room.freeze_system('Revision review')
        room.seed_quality_reports();self.assertTrue(json.loads(room.state_raw()['quality:SPY'])['quarantined'])
        body=room.RevisionReview(expected_hash=report['context_hash'],reason='Reviewed provider correction with original evidence retained')
        with self.assertRaises(room.HTTPException):room.accept_candle_revision('SPY',body,'bad-token')
        result=room.accept_candle_revision('SPY',body,'test-control-token');self.assertTrue(result['frozen']);self.assertFalse(result['quality']['quarantined']);self.assertAlmostEqual(room.latest_saved_bar()['low'],98.99)
        con=room.db();record=json.loads(con.execute('SELECT payload FROM candle_revision_reviews').fetchone()[0]);con.close();self.assertEqual(record[0]['original']['low'],99)
        with self.assertRaises(room.HTTPException):room.accept_candle_revision('SPY',body,'test-control-token')
        room.resume('test-control-token');self.assertFalse(room.get_state()['frozen'])
    def test_revision_review_refuses_active_orders_and_other_anomalies(self):
        self.quality_patch.stop();clock=patch.object(room,'assess_quality',side_effect=lambda symbol,bars,**kw:assess(symbol,bars,now=datetime(2026,10,9,18,tzinfo=NY).astimezone(timezone.utc),**kw));clock.start();self.addCleanup(clock.stop)
        bar=dict(datetime='2026-10-09 13:30:00',open=100,high=101,low=99,close=100,volume=1000);room.save_candles([bar]);report=room.check_data_quality([dict(bar,low=98.99)])
        con=room.db();con.execute('INSERT INTO pending_orders VALUES (?,?,?,?)',('SPY','sell',bar['datetime'],'{}'));con.commit();con.close()
        body=room.RevisionReview(expected_hash=report['context_hash'],reason='Review correction')
        with self.assertRaises(room.HTTPException):room.accept_candle_revision('SPY',body,'test-control-token')
        self.assertEqual(room.latest_saved_bar()['low'],99)
    def held_revision_fixture(self,new_close=100):
        self.quality_patch.stop();now=datetime(2026,10,9,18,tzinfo=NY).astimezone(timezone.utc)
        clock=patch.object(room,'assess_quality',side_effect=lambda symbol,bars,**kw:assess(symbol,bars,now=now,**kw));clock.start();self.addCleanup(clock.stop)
        times=expected(datetime(2026,9,1,9,30,tzinfo=NY),datetime(2026,10,9,13,30,tzinfo=NY))[-30:]
        bars=[dict(datetime=t.replace(tzinfo=None).isoformat(sep=' '),open=100,high=101,low=99,close=100,volume=1000) for t in times];room.save_candles(bars);room.set_state('last_processed_bar',bars[-1]['datetime'])
        con=room.db();con.execute('INSERT INTO positions (id,symbol,status,entry_time,entry_price,qty,stop,position_value,planned_loss) VALUES (?,?,?,?,?,?,?,?,?)',('held','SPY','OPEN',bars[-2]['datetime'],100,1,95,100,5));con.commit();con.close()
        bars[-1]=dict(bars[-1],low=98.95,close=new_close);report=room.check_data_quality(bars)
        return room.RevisionReview(expected_hash=report['context_hash'],reason='Held-position incident review with exit invariants',held_position_review=True)
    def test_held_review_preserves_exit_predicates_and_position(self):
        body=self.held_revision_fixture();before=room.positions();r=room.accept_candle_revision('SPY',body,'test-control-token');self.assertTrue(r['held_position_review']['stop_gap_ma_exit_predicates_unchanged']);self.assertEqual(room.positions(),before)
    def test_held_review_rejects_changed_ma_exit(self):
        body=self.held_revision_fixture(new_close=99.95)
        with self.assertRaises(room.HTTPException):room.accept_candle_revision('SPY',body,'test-control-token')
        self.assertEqual(room.latest_saved_bar()['close'],100)
    def test_real_production_path_calendar_contract_and_fill(self):
        self.quality_patch.stop();end=datetime(2026,10,8,13,30,tzinfo=NY);times=expected(end-timedelta(days=60),end)[-60:]
        bars=[dict(datetime=t.replace(tzinfo=None).isoformat(sep=' '),open=100,high=101,low=99,close=100,volume=1000) for t in times];bars[-1].update(open=109,high=111,low=108,close=110)
        decision_time=end.astimezone(timezone.utc)+timedelta(hours=4,minutes=20)
        class DecisionClock(datetime):
            @classmethod
            def now(cls,tz=None):return decision_time.astimezone(tz) if tz else decision_time.replace(tzinfo=None)
        with patch.object(room,'datetime',DecisionClock),patch.object(room,'assess_quality',side_effect=lambda symbol,bars,**kw:assess(symbol,bars,now=decision_time,**kw)),patch.object(room,'utcnow',return_value=decision_time.isoformat()):
            self.assertEqual(room.process_bars(bars)['status'],'ENTRY_QUEUED')
        nextbar=dict(datetime='2026-10-09 09:30:00',open=112,high=114,low=111,close=113,volume=1000);done=datetime(2026,10,9,14,tzinfo=NY).astimezone(timezone.utc)
        with patch.object(room,'assess_quality',side_effect=lambda symbol,bars,**kw:assess(symbol,bars,now=done,**kw)):
            self.assertEqual(room.process_bars(bars+[nextbar])['status'],'PAPER_ENTRY')
        self.assertEqual(len(room.positions()),1)

for name in base.Operations.__dict__:
    if name.startswith('test_'):setattr(Controls,name,None)

class CalendarQuality(unittest.TestCase):
    def bar(self,t,price=100):return dict(datetime=t,open=price,high=price+1,low=price-1,close=price,volume=1000)
    def test_holidays_weekends_early_closes_and_dst(self):
        self.assertEqual(slots(datetime(2026,7,3).date()),[]);self.assertEqual(slots(datetime(2026,10,10).date()),[])
        self.assertEqual(len(slots(datetime(2026,11,27).date())),1);self.assertEqual(len(slots(datetime(2026,12,24).date())),1)
        self.assertEqual(slots(datetime(2026,3,6).date())[0].utcoffset(),timedelta(hours=-5));self.assertEqual(slots(datetime(2026,3,9).date())[0].utcoffset(),timedelta(hours=-4))
        bars=[self.bar('2026-10-09 09:30:00'),self.bar('2026-10-09 13:30:00')];r=assess('SPY',bars,datetime(2026,10,11,12,tzinfo=NY).astimezone(timezone.utc));self.assertTrue(r['entry_allowed']);self.assertTrue(r['warnings'])
    def test_missing_stale_future_duplicate_revision_and_gap(self):
        bars=[self.bar('2026-10-08 09:30:00'),self.bar('2026-10-09 09:30:00')];now=datetime(2026,10,9,14,tzinfo=NY).astimezone(timezone.utc)
        r=assess('SPY',bars,now);self.assertFalse(r['entry_allowed']);self.assertFalse(r['quarantined']);self.assertIn('MISSING_SESSION_BARS',[i['code'] for i in r['issues']])
        self.assertIn('STALE_SESSION_DATA',[i['code'] for i in assess('SPY',[bars[0]],now)['issues']])
        for supplied in [bars+[self.bar('2026-10-09 13:30:00')],[bars[0],bars[0]],[bars[0],self.bar('2026-10-08 13:30:00',50)]]:self.assertTrue(assess('SPY',supplied,now)['quarantined'])
        self.assertTrue(assess('SPY',[bars[0]],now,saved={bars[0]['datetime']:dict(bars[0],close=99)})['quarantined'])
        self.assertFalse(assess('SPY',[bars[0]],now,saved={bars[0]['datetime']:dict(bars[0],close=100.000001)})['quarantined'])
        self.assertFalse(assess('SPY',[self.bar('2029-10-09 09:30:00')],datetime(2029,10,9,18,tzinfo=NY).astimezone(timezone.utc))['entry_allowed'])
