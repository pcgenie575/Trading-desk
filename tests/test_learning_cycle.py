import unittest,sys,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from learning_cycle import review,screen
import test_operations as base

class LearningEvidence(unittest.TestCase):
    def test_open_profit_is_not_learning_sample(self):
        r=review([{'status':'OPEN','realized_pnl':100}],{})
        self.assertEqual(r['closed_trades'],0);self.assertIsNone(r['mean_r']);self.assertEqual(r['decision'],'COLLECT_MORE')
    def test_freeze_and_bad_feed_is_investigate(self):
        self.assertEqual(review([],{'decision':'pause'})['decision'],'INVESTIGATE')
    def test_concentrated_and_small_results_cannot_pass(self):
        self.assertFalse(screen({'trade_log':[{'pnl':100}], 'expectancy_r':4})['passed'])
    def test_broad_cost_stress_result_can_pass(self):
        r=screen({'trade_log':[{'pnl':10}]*70+[{'pnl':-5}]*30,'expectancy_r':.22})
        self.assertTrue(r['passed'])

class LearningWorkflow(base.Operations):
    def seed_test(self):
        from learning_cycle import TEST_PROTOCOL,VERSION,fingerprint
        from test_edge_lab import daily_bars
        bars=daily_bars(180);proto=dict(TEST_PROTOCOL,dataset_hash=fingerprint('SPY',bars))
        c=base.room.db();c.execute('CREATE TABLE IF NOT EXISTS learning_tests(id TEXT PRIMARY KEY,registered_at TEXT,status TEXT,protocol TEXT,dataset TEXT,payload TEXT)')
        c.execute('INSERT INTO learning_tests VALUES (?,?,?,?,?,?)',(VERSION,base.room.utcnow(),'DEVELOPMENT_RUNNING',json.dumps(proto),json.dumps(bars),'{}'));c.commit();c.close()
    def test_rejected_test_is_not_repeated_and_protocol_change_blocks(self):
        self.seed_test()
        with patch('learning_cycle.simulate',return_value={'trade_log':[], 'expectancy_r':None,'max_drawdown':0}) as sim:
            base.room.LEARNING_CYCLE['tick']();self.assertEqual(sim.call_count,3)
            base.room.LEARNING_CYCLE['tick']();self.assertEqual(sim.call_count,3)
        self.assertEqual(base.room.LEARNING_CYCLE['overview']()['automatic_tests'][0]['status'],'REJECTED')
        c=base.room.db();c.execute("UPDATE learning_tests SET protocol='{}'");c.commit();c.close();base.room.LEARNING_CYCLE['tick']()
        self.assertEqual(base.room.LEARNING_CYCLE['overview']()['automatic_tests'][0]['status'],'PROTOCOL_BLOCKED')
    def test_qualifying_development_reserves_future_before_scoring(self):
        self.seed_test()
        def metric(*args):return {'trade_log':[{'pnl':10}]*70+[{'pnl':-5}]*30,'expectancy_r':.22 if args[3]=='trailing' else .1,'max_drawdown':5 if args[3]=='trailing' else 10}
        with patch('learning_cycle.simulate',side_effect=metric) as sim:
            base.room.LEARNING_CYCLE['tick']();job=base.room.LEARNING_CYCLE['overview']()['automatic_tests'][0]
            self.assertEqual(job['status'],'FORWARD_COLLECTING');self.assertIn('forward_registered_at',job['payload']);self.assertNotIn('forward_stress',job['payload'])
            base.room.LEARNING_CYCLE['tick']();self.assertEqual(sim.call_count,3)
        self.assertEqual(base.room.positions(),[])
    def test_freeze_prevents_research_without_unfreezing(self):
        self.seed_test();base.room.set_state('frozen','true')
        with patch('learning_cycle.simulate',side_effect=AssertionError('Must not run')):base.room.LEARNING_CYCLE['tick']()
        self.assertTrue(base.room.get_state()['frozen']);self.assertEqual(base.room.positions(),[])
    def test_future_test_retains_both_datasets_and_never_activates(self):
        from test_edge_lab import daily_bars
        self.seed_test();bars=daily_bars(1050)
        c=base.room.db();c.execute('UPDATE learning_tests SET status=?,payload=?',('FORWARD_COLLECTING',json.dumps({'forward_registered_at':bars[50]['datetime']+'T00:00:00+00:00'})))
        for b in bars:c.execute('INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)',('SPY','4h',b['datetime'],b['open'],b['high'],b['low'],b['close'],b['volume']))
        c.commit();c.close()
        def metric(*args):return {'trade_log':[{'pnl':10}]*70+[{'pnl':-5}]*30,'expectancy_r':.22 if args[3]=='trailing' else .1,'max_drawdown':5 if args[3]=='trailing' else 10}
        with patch('learning_cycle.simulate',side_effect=metric) as sim:
            base.room.LEARNING_CYCLE['tick']();base.room.LEARNING_CYCLE['tick']();self.assertEqual(sim.call_count,3)
        job=base.room.LEARNING_CYCLE['overview']()['automatic_tests'][0];self.assertEqual(job['status'],'PORTFOLIO_REVIEW_REQUIRED')
        c=base.room.db();dataset=json.loads(c.execute('SELECT dataset FROM learning_tests').fetchone()[0]);c.close()
        self.assertEqual(len(dataset['development']),180);self.assertEqual(len(dataset['forward']),1050)
        self.assertEqual(base.room.positions(),[]);self.assertEqual(base.room.get_state()['cash'],5000)
    def test_weekly_idempotence_approval_auth_and_ledger_unchanged(self):
        from fastapi.testclient import TestClient
        room=base.room;room.LEARNING_CYCLE['tick']();first=room.LEARNING_CYCLE['overview']();room.LEARNING_CYCLE['tick']();second=room.LEARNING_CYCLE['overview']()
        self.assertEqual(first,second);self.assertEqual(room.positions(),[]);self.assertEqual(first['automatic_tests'],[])
        cycle=first['cycles'][0];entry='auto-learning-'+cycle['week'];self.assertEqual(room.knowledge_for_agent('Analyst'),[x for x in room.knowledge_for_agent('Analyst') if x['id']!=entry])
        with patch.object(room,'start_scheduler'):
            with TestClient(room.app) as client:
                self.assertEqual(client.get('/learning-cycle').status_code,401);client.auth=('operator','test-password')
                self.assertEqual(client.get('/learning').status_code,200)
                body={'week':cycle['week'],'evidence_hash':cycle['evidence_hash'],'note':'Evidence reviewed'}
                self.assertEqual(client.post('/learning-cycle/approve-lesson',json=body).status_code,401)
                h={'X-Control-Token':'test-control-token'}
                self.assertEqual(client.post('/learning-cycle/approve-lesson',json=dict(body,evidence_hash='wrong'),headers=h).status_code,409)
                self.assertEqual(client.post('/learning-cycle/approve-lesson',json=body,headers=h).json()['status'],'LESSON_APPROVED')
                self.assertFalse(client.post('/learning-cycle/approve-lesson',json=body,headers=h).json()['strategy_changed'])
                room.init_db();self.assertEqual(len(room.LEARNING_CYCLE['overview']()['approvals']),1)
                self.assertEqual(room.positions(),[]);self.assertEqual(room.get_state()['cash'],5000)

for name in list(base.Operations.__dict__):
    if name.startswith('test_'):setattr(LearningWorkflow,name,None)
