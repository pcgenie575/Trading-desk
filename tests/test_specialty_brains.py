import json
from unittest.mock import patch
from fastapi.testclient import TestClient
import test_operations as base
room=base.room
class SpecialtyBrains(base.Operations):
    def report(self,role):return next(r for r in room.specialty_reports() if r['role']==role)
    def test_empty_evidence_never_claims_profit_or_adherence(self):
        r=self.report('Performance Reviewer');m={x['label']:x['value'] for x in r['metrics']}
        self.assertIsNone(m['Win rate %']);self.assertIsNone(m['Expectancy R']);self.assertIsNone(m['Reviewed adherence %'])
        self.assertEqual(len(room.specialty_reports()),6)
    def test_cash_mismatch_is_detected_without_repair(self):
        con=room.db();con.execute("UPDATE state SET value=? WHERE key='cash'",(json.dumps(4999),));con.commit();con.close()
        r=self.report('Logger');self.assertEqual(r['checks'][0]['status'],'REVIEW');self.assertEqual(room.get_state()['cash'],4999)
    def test_risk_threshold_and_missing_context(self):
        room.process_bars(self.bars);self.fill_next();r=self.report('Risk & Compliance')
        self.assertTrue(all(c['status']=='PASS' for c in r['checks']))
        con=room.db();con.execute('DELETE FROM trade_context');con.commit();con.close()
        self.assertEqual(self.report('Logger')['checks'][1]['status'],'REVIEW')
    def test_snapshot_dedup_and_immutable_knowledge(self):
        room.save_specialty_reports();room.save_specialty_reports();old=room.agent_brain_history('Logger');self.assertEqual(len(old),1)
        draft=room.create_knowledge(room.KnowledgeInput(title='Audit lesson',content='Keep records',agents=['Logger']),'test-control-token')
        self.assertNotIn(draft['id'],[k['id'] for k in self.report('Logger')['knowledge']])
        room.update_knowledge(draft['id'],room.KnowledgeInput(expected_version=1,title='Audit lesson',content='Keep records',evidence='Reviewed',status='approved',agents=['Logger']),'test-control-token')
        room.save_specialty_reports();self.assertNotIn(draft['id'],[k['id'] for k in old[0]['knowledge']]);self.assertEqual(len(room.agent_brain_history('Logger')),2)
        room.init_db();self.assertEqual(len(room.agent_brain_history('Logger')),2)
    def test_auth_and_preview_has_no_side_effects(self):
        with TestClient(room.app) as client:
            for path in ['/brains','/agent-brains','/agent-brains/Logger/history']:self.assertEqual(client.get(path).status_code,401)
            client.auth=('operator','test-password');before=room.state_raw();ps=room.positions();history=room.agent_brain_history('Logger')
            with patch.object(room.TwelveDataAdapter,'latest_completed_bars',side_effect=AssertionError('No provider calls')):
                self.assertEqual(client.get('/agent-brains').status_code,200)
            self.assertEqual(room.state_raw(),before);self.assertEqual(room.positions(),ps);self.assertEqual(room.agent_brain_history('Logger'),history)
            self.assertEqual(client.get('/agent-brains/unknown/history').status_code,404)
for name in base.Operations.__dict__:
    if name.startswith('test_'):setattr(SpecialtyBrains,name,None)
