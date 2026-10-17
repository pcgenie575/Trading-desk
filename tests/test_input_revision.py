import unittest,sys,json,copy,hashlib
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from input_revision import build,back_adjusted_close,normalised_levels,require_complete,VERSION,SYMBOLS
from price_source_review import digest,VERSION as PARENT
from corporate_actions import signal_features
import test_operations as base
room=base.room

def fixture():
    dates=['2006-01-03','2015-12-31'];bars=[dict(datetime=dates[0],open=100.,high=101.,low=99.,close=100.,volume=10),dict(datetime=dates[1],open=99.,high=100.,low=98.,close=99.,volume=10)]
    event={'type':'distribution','ex_date':dates[1],'pay_date':'2016-01-04','amount':1.,'currency':'USD'}
    original={'reference':dates,'pages':{},'distributions':{}};originals={};parsed={}
    for s in SYMBOLS:
        content=s.encode();originals[s]=content
        parsed[s]={'events':[copy.deepcopy(event)],'coverage_verified':True,'source_hash':hashlib.sha256(content).hexdigest(),'source':'issuer'}
        original['distributions'][s]=copy.deepcopy(parsed[s])
        for mode in ('none','splits','all'):
            b=copy.deepcopy(bars)
            if mode=='all' and s!='IEF':
                for k in ('open','high','low','close'):b[0][k]*=.99
            original['pages'][s+':'+mode]={'bars':b,'adjustment_requested':mode,'meta':{'symbol':s,'currency':'USD','interval':'1day'}}
    payload={'chart':{'error':None,'result':[{'meta':{'symbol':'IEF','currency':'USD','instrumentType':'ETF','exchangeTimezoneName':'America/New_York','dataGranularity':'1d'},'timestamp':[int(datetime(2006,1,3,14,30,tzinfo=timezone.utc).timestamp()),int(datetime(2015,12,31,14,30,tzinfo=timezone.utc).timestamp())],'indicators':{'quote':[{k:[b[k] for b in bars] for k in ('open','high','low','close','volume')}],'adjclose':[{'adjclose':[99.,99.]}]}}]}}
    text=json.dumps(payload);parent={'summary':{'source_dataset_hash':digest(original),'results':[{'id':'Yahoo-IEF','sha256':hashlib.sha256(text.encode()).hexdigest()}]},'responses':{'Yahoo-IEF':text}}
    return original,parent,originals,parsed

class RevisionTools(unittest.TestCase):
    def test_three_components_assemble_without_replacing_original_or_removing_blockers(self):
        o,p,files,parsed=fixture();before=copy.deepcopy(o)
        with patch('input_revision.parse_distributions',side_effect=lambda s,c:copy.deepcopy(parsed[s])):m,b=build(o,p,files)
        self.assertEqual(o,before);self.assertEqual(m['assembled_components'],3);self.assertEqual(set(m['components']),set(SYMBOLS))
        self.assertEqual(set(b['assets']),{'IWM','IEF','EFA'});self.assertEqual(b['assets']['IEF']['raw'],o['pages']['IEF:none']['bars'])
        self.assertNotIn('adjusted_close',b['assets']['IEF']);self.assertFalse(m['ready_for_simulation'])
        self.assertTrue(m['components']['IEF']['evidence']['normalised_level_check']['matched'])
        with self.assertRaises(ValueError):require_complete(m)
        all_ready=copy.deepcopy(m)
        for x in all_ready['components'].values():x['status']='ASSEMBLED_FOR_REVIEW'
        with self.assertRaises(ValueError):require_complete(all_ready)
    def test_issuer_or_source_tampering_fails_and_no_asset_fallback(self):
        for kind in ('issuer','publisher','missing_asset'):
            o,p,files,parsed=fixture()
            if kind=='issuer':files['IEF']=b'changed'
            if kind=='publisher':p['responses']['Yahoo-IEF']+='changed'
            if kind=='missing_asset':o['pages'].pop('GSG:none');p['summary']['source_dataset_hash']=digest(o)
            with patch('input_revision.parse_distributions',side_effect=lambda s,c:copy.deepcopy(parsed[s])):
                with self.subTest(kind=kind),self.assertRaises(ValueError):build(o,p,files)
    def test_diagnostic_adjustments_never_become_as_of_signal_history(self):
        o,p,files,parsed=fixture();raw=o['pages']['IEF:none']['bars'];events=parsed['IEF']['events']
        derived=back_adjusted_close(raw,events);self.assertEqual(derived[raw[0]['datetime']],99.)
        old=signal_features(raw,[]);new=signal_features(raw,events)
        self.assertEqual(old[raw[0]['datetime']],new[raw[0]['datetime']])
        changed=copy.deepcopy(events);changed[0]['amount']=2.
        self.assertFalse(normalised_levels(back_adjusted_close(raw,changed),derived)['matched'])

class RevisionWorkflow(unittest.TestCase):
    setUp=base.Operations.setUp
    def tearDown(self):
        folder=self.tmp/'etf-issuer-sources'
        if folder.exists():
            for s in ('IWM','IEF','EFA'):(folder/('old-etf-'+s+'.xml')).unlink(missing_ok=True)
            folder.rmdir()
        base.Operations.tearDown(self)
    def test_auth_idempotence_parent_preservation_restart_backup_payload_and_tampering(self):
        from fastapi.testclient import TestClient
        o,p,files,parsed=fixture();folder=Path(room.DB).resolve().parent/'etf-issuer-sources';folder.mkdir(exist_ok=True)
        for s in ('IWM','IEF','EFA'):(folder/('old-etf-'+s+'.xml')).write_bytes(files[s])
        with TestClient(room.app) as client:
            self.assertEqual(client.get('/input-revision/bundle').status_code,401);client.auth=('operator','test-password')
            self.assertEqual(client.post('/input-revision/build').status_code,401)
            c=room.db();c.execute('INSERT INTO edge_lab_runs VALUES (?,?,?,?,?,?,?,?)',('old-etf','ETF','old-key',room.utcnow(),'DATA_BLOCKED','{}','{}',json.dumps(o)))
            c.execute('INSERT INTO price_source_reviews VALUES (?,?,?,?)',(PARENT,room.utcnow(),json.dumps({'original_etf_id':'old-etf','summary_hash':digest(p['summary'])}),json.dumps(p)));c.commit();before=c.execute('SELECT * FROM edge_lab_runs').fetchall();c.close();positions=room.positions();state=room.get_state()
            with patch('input_revision.parse_distributions',side_effect=lambda s,c:copy.deepcopy(parsed[s])):
                headers={'X-Control-Token':'test-control-token'};r=client.post('/input-revision/build',headers=headers)
                self.assertEqual(r.status_code,200);r=r.json();self.assertEqual(r['status'],'PARTIAL_DRAFT');self.assertTrue(r['installed_source_matches'])
                self.assertEqual(client.post('/input-revision/build',headers=headers).json(),r)
            export=client.get('/input-revision/bundle').json();self.assertNotIn('issuer_originals',export['bundle'])
            c=room.db();self.assertEqual(c.execute('SELECT * FROM edge_lab_runs').fetchall(),before);stored=json.loads(c.execute('SELECT bundle FROM input_revisions').fetchone()[0]);self.assertEqual(set(stored['issuer_originals']),{'IWM','IEF','EFA'});c.close()
            self.assertEqual(room.positions(),positions);self.assertEqual(room.get_state(),state)
        with TestClient(room.app) as client:
            client.auth=('operator','test-password');self.assertEqual(client.get('/input-revision').json(),r)
            c=room.db();stored['draft']['assets']['IEF']['raw'][0]['close']=1;c.execute('UPDATE input_revisions SET bundle=?',(json.dumps(stored),));c.commit();c.close()
            self.assertEqual(client.get('/input-revision').json()['status'],'EVIDENCE_BLOCKED');self.assertEqual(client.get('/input-revision/bundle').status_code,409)
