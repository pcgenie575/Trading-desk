import unittest,sys,json,copy,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from input_integrity import audit_bars
from gsg_forensics import analyse,facts,quarterly,render,VERSION,PARENT
from price_source_review import build_review,digest
from test_price_source_review import captures,fixture
import test_operations as base
room=base.room

class IntegrityTools(unittest.TestCase):
    def bars(self):
        return [dict(datetime=f'2008-01-{d:02}',open=100.,high=100.,low=100.,close=100.,volume=0) for d in (2,3,4,7,8,9)]
    def test_long_run_flag_does_not_certify_source_or_mutate_input(self):
        bars=self.bars();before=copy.deepcopy(bars);r=audit_bars(bars)
        self.assertTrue(r['requires_source_review']);self.assertEqual(r['longest_flat_run_sessions'],6);self.assertEqual(r['by_year']['2008']['flat_ohlc_sessions'],6)
        self.assertFalse(r['source_certified']);self.assertEqual(bars,before)
        bars[2]['high']=101;r=audit_bars(bars);self.assertFalse(r['requires_source_review']);self.assertFalse(r['source_certified'])
    def test_single_flat_bar_is_not_a_long_run_and_invalid_bars_fail(self):
        bars=self.bars()[:1];self.assertFalse(audit_bars(bars)['requires_source_review'])
        bars[0]['low']=float('nan')
        with self.assertRaises(ValueError):audit_bars(bars)
    def test_intraday_and_closing_ranges_remain_separate(self):
        bars=self.bars();bars[0].update(high=110,low=90)
        r=quarterly(bars,{'rows':[{'year':2008,'quarter':1,'reported_high':100,'reported_low':100,'source':'source'}]})
        self.assertEqual(r['closing_extrema_matches'],1);self.assertEqual(r['intraday_extrema_matches'],0);self.assertFalse(r['source_certified'])
    def test_retained_parent_hash_and_reference_scope_fail_closed(self):
        plan,attempts,responses=captures();_,source=fixture();parent={'summary':build_review(plan,attempts,responses,source),'responses':{k:v.decode() for k,v in responses.items()}}
        before=copy.deepcopy(source);r=analyse(source,parent,facts());self.assertEqual(source,before);self.assertFalse(r['performance_calculation_allowed'])
        bad=copy.deepcopy(parent);bad['responses']['Yahoo-GSG']+='bad'
        with self.assertRaises(ValueError):analyse(source,bad,facts())
        references=facts();references['rows'].pop()
        with self.assertRaises(ValueError):analyse(source,parent,references)
    def test_page_escapes_source_content(self):
        p,a,responses=captures();_,original=fixture();r=analyse(original,{'summary':build_review(p,a,responses,original),'responses':{k:v.decode() for k,v in responses.items()}},facts());r['limitations'].append('<script>bad</script>')
        html=render({'status':'RECORDED','summary':r});self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>',html);self.assertNotIn('<form',html)

class ForensicWorkflow(unittest.TestCase):
    setUp=base.Operations.setUp
    tearDown=base.Operations.tearDown
    def test_auth_once_parent_preservation_restart_and_summary_integrity(self):
        from fastapi.testclient import TestClient
        plan,attempts,responses=captures();_,source=fixture();payload={'summary':build_review(plan,attempts,responses,source),'responses':{k:v.decode() for k,v in responses.items()}}
        protocol={'original_etf_id':'old-etf','summary_hash':digest(payload['summary'])}
        with TestClient(room.app) as client:
            self.assertEqual(client.get('/gsg-forensics').status_code,401);client.auth=('operator','test-password')
            self.assertEqual(client.post('/gsg-forensics/record').status_code,401)
            c=room.db();c.execute('INSERT INTO edge_lab_runs VALUES (?,?,?,?,?,?,?,?)',('old-etf','ETF','old-key',room.utcnow(),'DATA_BLOCKED','{}','{}',json.dumps(source)))
            c.execute('INSERT INTO price_source_reviews VALUES (?,?,?,?)',(PARENT,room.utcnow(),json.dumps(protocol),json.dumps(payload)));c.commit();original=c.execute('SELECT * FROM edge_lab_runs').fetchall();parent=c.execute('SELECT * FROM price_source_reviews WHERE id=?',(PARENT,)).fetchone();c.close()
            state=room.get_state();positions=room.positions();headers={'X-Control-Token':'test-control-token'}
            r=client.post('/gsg-forensics/record',headers=headers);self.assertEqual(r.status_code,200);r=r.json();self.assertEqual(r['status'],'RECORDED');self.assertTrue(r['installed_source_matches'])
            self.assertEqual(client.post('/gsg-forensics/record',headers=headers).json(),r)
            c=room.db();self.assertEqual(c.execute('SELECT * FROM edge_lab_runs').fetchall(),original);self.assertEqual(c.execute('SELECT * FROM price_source_reviews WHERE id=?',(PARENT,)).fetchone(),parent);c.close()
            self.assertEqual(room.get_state(),state);self.assertEqual(room.positions(),positions)
        with TestClient(room.app) as client:
            client.auth=('operator','test-password');self.assertEqual(client.get('/gsg-forensics').json(),r)
            c=room.db();p=json.loads(c.execute('SELECT payload FROM price_source_reviews WHERE id=?',(VERSION,)).fetchone()[0]);p['summary']['decision']='tampered';c.execute('UPDATE price_source_reviews SET payload=? WHERE id=?',(json.dumps(p),VERSION));c.commit();c.close()
            r=client.get('/gsg-forensics').json();self.assertEqual(r['status'],'EVIDENCE_BLOCKED');self.assertNotIn('saved_gsg',r['summary'])
