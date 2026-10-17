import unittest,sys,json,copy,hashlib
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from price_source_review import parse_yahoo,compare_prices,compare_events,build_review,render,VERSION,IDS,profile,source_url
import test_operations as base
room=base.room

def fixture(symbol='IEF'):
    timestamps=[int(datetime(2006,1,d,14,30,tzinfo=timezone.utc).timestamp()) for d in (3,4)]
    data={'chart':{'error':None,'result':[{'meta':{'symbol':symbol,'currency':'USD','instrumentType':'ETF','exchangeTimezoneName':'America/New_York','dataGranularity':'1d'},'timestamp':timestamps,'indicators':{'quote':[{'open':[100,100],'high':[101,101],'low':[99,99],'close':[100,100],'volume':[10,10]}],'adjclose':[{'adjclose':[100,100]}]}}]}}
    parsed=parse_yahoo(data,symbol);original={'reference':[b['datetime'] for b in parsed['bars']],'pages':{s+':none':{'bars':copy.deepcopy(parsed['bars'])} for s in ('IEF','GSG')},'distributions':{s:{'coverage_verified':False,'events':[]} for s in ('IEF','GSG')}}
    return data,original

def captures():
    attempts=[];responses={};requests=[]
    for key in IDS:
        provider,symbol=key.split('-');data,_=fixture(symbol);url=source_url(provider,symbol)
        item={'id':key,'provider':provider,'symbol':symbol,'url':url};requests.append(item)
        raw=json.dumps(data).encode() if provider=='Yahoo' else b'<html>not price data</html>'
        responses[key]=raw;attempts.append(dict(item,status='RECEIVED',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    return {'version':VERSION,'max_requests':4,'retry_allowed':False,'requests':requests},attempts,responses

class SourceParsing(unittest.TestCase):
    def test_identity_null_and_out_of_range_values_are_rejected(self):
        data,_=fixture();self.assertEqual(len(parse_yahoo(data,'IEF')['bars']),2)
        for variant in ('symbol','null','length','future','range'):
            x=copy.deepcopy(data);r=x['chart']['result'][0]
            if variant=='symbol':r['meta']['symbol']='SPY'
            if variant=='null':r['indicators']['quote'][0]['close'][0]=None
            if variant=='length':r['indicators']['adjclose'][0]['adjclose'].pop()
            if variant=='future':r['timestamp'][-1]=int(datetime(2016,1,4,14,30,tzinfo=timezone.utc).timestamp())
            if variant=='range':r['indicators']['quote'][0]['low'][0]=102
            with self.subTest(variant=variant),self.assertRaises(ValueError):parse_yahoo(x,'IEF')
    def test_fixed_ohlc_tolerance_and_no_mutation(self):
        data,_=fixture();a=parse_yahoo(data,'IEF')['bars'];b=copy.deepcopy(a);before=copy.deepcopy((a,b))
        self.assertTrue(compare_prices(a,b)['all_overlapping_ohlc_within_tolerance']);self.assertEqual((a,b),before)
        b[0]['high']+=.021;r=compare_prices(a,b);self.assertEqual(r['mismatched_sessions'],1);self.assertEqual(r['mismatches_by_year'],{'2006':1})
    def test_rounding_does_not_clear_strict_event_gate_or_unknown_source(self):
        issuer={'coverage_verified':True,'events':[{'type':'distribution','ex_date':'2006-02-01','amount':.26352}]}
        r=compare_events([{'ex_date':'2006-02-01','amount':.264}],issuer)
        self.assertEqual(r['amount_discrepancies'],1);self.assertEqual(r['discrepancies_compatible_with_three_decimal_rounding'],1);self.assertFalse(r['reconciled'])
        issuer['coverage_verified']=False;self.assertFalse(compare_events([],issuer)['reconciled'])
        r=compare_events([{'ex_date':'2006-02-01','amount':.27}],issuer);self.assertEqual(r['unexplained_amount_discrepancies'],1)
    def test_all_sources_and_hashes_are_required_and_no_promotion(self):
        p,a,r=captures();_,source=fixture();before=copy.deepcopy(source);summary=build_review(p,a,r,source)
        self.assertEqual(source,before);self.assertFalse(summary['performance_calculation_allowed']);self.assertEqual(summary['public_source_requests'],4)
        self.assertEqual(summary['results'][2]['status'],'NOT_PRICE_DATA')
        self.assertTrue(all(not x['profile']['production_eligible'] for x in summary['results'] if 'profile' in x))
        r[IDS[0]]+=b'bad'
        with self.assertRaises(ValueError):build_review(p,a,r,source)
        with self.assertRaises(ValueError):build_review(p,a[:-1],r,source)
    def test_html_escapes_source_errors_and_has_no_write_controls(self):
        page=render({'status':'RECORDED','summary':{'results':[{'id':'test','status':'INVALID_DATA','reason':'<script>bad</script>'}]}})
        self.assertNotIn('<script>',page);self.assertIn('&lt;script&gt;',page);self.assertNotIn('<form',page)

class SourceWorkflow(unittest.TestCase):
    setUp=base.Operations.setUp
    def tearDown(self):
        folder=self.tmp/VERSION
        if folder.exists():
            for name in ['plan.json','attempts.json']+[k+'.response' for k in IDS]:(folder/name).unlink(missing_ok=True)
            folder.rmdir()
        base.Operations.tearDown(self)
    def test_auth_record_once_original_preservation_restart_and_tampering(self):
        from fastapi.testclient import TestClient
        plan,attempts,responses=captures();_,source=fixture();folder=Path(room.DB).resolve().parent/VERSION;folder.mkdir(exist_ok=True)
        (folder/'plan.json').write_text(json.dumps(plan));(folder/'attempts.json').write_text(json.dumps(attempts))
        for key,body in responses.items():(folder/(key+'.response')).write_bytes(body)
        with TestClient(room.app) as client:
            self.assertEqual(client.get('/price-source-review').status_code,401);client.auth=('operator','test-password')
            self.assertEqual(client.post('/price-source-review/record').status_code,401)
            c=room.db();c.execute('INSERT INTO edge_lab_runs VALUES (?,?,?,?,?,?,?,?)',('old-etf','ETF','old-key',room.utcnow(),'DATA_BLOCKED','{}','{}',json.dumps(source)));c.commit();before=c.execute('SELECT * FROM edge_lab_runs').fetchall();c.close()
            positions=room.positions();state=room.get_state();headers={'X-Control-Token':'test-control-token'}
            r=client.post('/price-source-review/record',headers=headers);self.assertEqual(r.status_code,200);r=r.json();self.assertEqual(r['status'],'RECORDED')
            self.assertTrue(r['retained_integrity']);self.assertEqual(client.post('/price-source-review/record',headers=headers).json(),r)
            c=room.db();self.assertEqual(c.execute('SELECT * FROM edge_lab_runs').fetchall(),before);c.close()
            self.assertEqual(room.positions(),positions);self.assertEqual(room.get_state(),state)
        with TestClient(room.app) as client:
            client.auth=('operator','test-password');self.assertEqual(client.get('/price-source-review').json(),r)
            c=room.db();p=json.loads(c.execute('SELECT payload FROM price_source_reviews').fetchone()[0]);p['responses'][IDS[0]]+='tampered';c.execute('UPDATE price_source_reviews SET payload=?',(json.dumps(p),));c.commit();c.close()
            blocked=client.get('/price-source-review').json();self.assertEqual(blocked['status'],'EVIDENCE_BLOCKED');self.assertNotIn('results',blocked['summary'])
