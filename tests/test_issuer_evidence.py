import unittest,sys,json,copy,tempfile,hashlib
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from issuer_evidence import catalog,verify,overlay,render,VERSION
import test_operations as base
room=base.room

def fixture():
    spec=catalog();gsg=[]
    for row in spec['gsg_no_distribution_periods']:
        gsg.append(row['source']+' The Trust made no distributions to Shareholders during the fiscal years ended December 31, '+row['end'][:4]+' and '+row['start'][:4]+'. The Trust has no obligation.')
    split=spec['iau_split'];captures={'gsg-web-excerpts':'--------------------------------------------------------------------------------'.join(gsg),'iau-split-web-excerpt':split['source']+' IAU/TSX: IGT 10 for 1 split NYSEArca on June 24, 2010'}
    for key,value in captures.items():spec['captures'][key]['sha256']=hashlib.sha256(value.encode()).hexdigest()
    return spec,captures

class SourceChecks(unittest.TestCase):
    def test_explicit_contiguous_coverage_and_scope(self):
        s,c=fixture();before=copy.deepcopy((s,c));r=verify(s,c)
        self.assertEqual(r['coverage_start'],'2006-07-10');self.assertEqual(r['coverage_end'],'2015-12-31')
        self.assertFalse(r['original_gate_overridden']);self.assertFalse(r['performance_calculation_allowed']);self.assertEqual((s,c),before)
    def test_missing_tampered_or_wrong_period_sources_fail_closed(self):
        for case in ('hash','gap','missing_period','wrong_host','no_statement'):
            s,c=fixture()
            if case=='hash':c['gsg-web-excerpts']+=' changed'
            if case=='gap':s['gsg_no_distribution_periods'][1]['start']='2008-01-02'
            if case=='missing_period':s['gsg_no_distribution_periods'].pop()
            if case=='wrong_host':s['gsg_no_distribution_periods'][0]['source']='https://example.com/filing'
            if case=='no_statement':
                c['gsg-web-excerpts']=c['gsg-web-excerpts'].replace('made no distributions','may make distributions')
                s['captures']['gsg-web-excerpts']['sha256']=hashlib.sha256(c['gsg-web-excerpts'].encode()).hexdigest()
            with self.subTest(case=case),self.assertRaises((ValueError,KeyError)):verify(s,c)
    def test_original_blockers_and_split_match_are_not_overwritten(self):
        s,c=fixture();source={'id':'old','status':'DATA_BLOCKED','payload':{'input_hash':'original','input_checks':{'IAU':{'issues':['DISTRIBUTION_SOURCE_UNVERIFIED'],'inferred_splits':[{'effective_date':'2010-06-24','new_per_old':9.999999917}]},'GSG':{'issues':['WARMUP_HISTORY_TOO_SHORT']}}}}
        before=copy.deepcopy(source);r=overlay(verify(s,c),source)
        self.assertTrue(r['iau_provider_split_matches']);self.assertEqual(source,before);self.assertEqual(r['original_input_hash'],'original')
        self.assertEqual(r['original_issues']['GSG'],['WARMUP_HISTORY_TOO_SHORT']);self.assertFalse(r['performance_calculation_allowed'])
        source['payload']['input_checks']['IAU']['inferred_splits'][0]['new_per_old']=2
        self.assertFalse(overlay(verify(s,c),source)['iau_provider_split_matches'])
    def test_page_escapes_evidence_and_is_read_only(self):
        s,c=fixture();s['limitations'].append('<script>bad()</script>')
        html=render({'status':'RECORDED','catalog':s,'result':{'original_issues':{'GSG':['<img>']}}})
        self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>',html);self.assertNotIn('<form',html)
        self.assertIn('not downloaded original filing bytes',html)

class SourceWorkflow(unittest.TestCase):
    setUp=base.Operations.setUp
    def tearDown(self):
        folder=self.tmp/'issuer-audit-captures'
        if folder.exists():
            for name in ('gsg-web-excerpts.txt','iau-split-web-excerpt.txt'):
                (folder/name).unlink(missing_ok=True)
            folder.rmdir()
        base.Operations.tearDown(self)
    def test_authenticated_record_once_no_original_mutation_and_restart(self):
        from fastapi.testclient import TestClient
        spec,captures=fixture();folder=Path(room.DB).resolve().parent/'issuer-audit-captures';folder.mkdir(exist_ok=True)
        for key,meta in spec['captures'].items():(folder/meta['filename']).write_text(captures[key],encoding='utf8')
        with patch('issuer_evidence.catalog',return_value=spec):
            with TestClient(room.app) as client:
                self.assertEqual(client.get('/issuer-audit').status_code,401);client.auth=('operator','test-password')
                self.assertEqual(client.post('/issuer-audit/record').status_code,401)
                state=room.get_state();positions=room.positions();headers={'X-Control-Token':'test-control-token'}
                r=client.post('/issuer-audit/record',headers=headers);self.assertEqual(r.status_code,200);r=r.json()
                self.assertEqual(r['status'],'RECORDED');self.assertTrue(r['stored_capture_integrity'])
                self.assertEqual(client.post('/issuer-audit/record',headers=headers).json(),r)
                self.assertEqual(client.get('/issuer-audit/source/gsg-web-excerpts').text,captures['gsg-web-excerpts'])
                self.assertEqual(client.get('/issuer-audit/source/unknown').status_code,404)
                self.assertEqual(room.get_state(),state);self.assertEqual(room.positions(),positions)
            with TestClient(room.app) as client:
                client.auth=('operator','test-password');self.assertEqual(client.get('/issuer-audit').json(),r)
                c=room.db();p=json.loads(c.execute('SELECT payload FROM issuer_evidence').fetchone()[0]);p['captures']['gsg-web-excerpts']+=' bad';c.execute('UPDATE issuer_evidence SET payload=?',(json.dumps(p),));c.commit();c.close()
                blocked=client.get('/issuer-audit').json();self.assertEqual(blocked['status'],'EVIDENCE_BLOCKED');self.assertNotIn('gsg_distribution_statement_coverage',blocked['result'])
                self.assertEqual(client.get('/issuer-audit/source/gsg-web-excerpts').status_code,409)
