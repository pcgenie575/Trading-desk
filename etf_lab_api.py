"""Durable four-stage free-only ETF research workflow."""
import json,time,threading,uuid
from pathlib import Path
from urllib.request import Request,urlopen
from fastapi import Header,HTTPException
from fastapi.responses import HTMLResponse,Response
from etf_protocol import PROTOCOL,SYMBOLS
from daily_research import digest
from corporate_actions import issuer_url,parse_distributions,reconcile
from market_data import TwelveDataAdapter
from etf_research import run

def install(app,services):
    db=services['db'];lock=services['_cycle_lock'];now=services['utcnow'];control=services['require_control'];emit=services['emit'];reserve=services['reserve_credit'];worker_lock=threading.Lock()
    source_dir=Path(services['DB']).resolve().parent/'etf-issuer-sources'
    def row(rid):
        c=db();r=c.execute("SELECT * FROM edge_lab_runs WHERE id=? AND kind='ETF'",(rid,)).fetchone();c.close()
        if not r:raise HTTPException(404,'ETF job not found.')
        r=dict(r)
        for k in ('protocol','payload','dataset'):r[k]=json.loads(r[k])
        return r
    def save(r):
        with lock:
            c=db();c.execute('UPDATE edge_lab_runs SET status=?,payload=?,dataset=? WHERE id=?',(r['status'],json.dumps(r['payload']),json.dumps(r['dataset']),r['id']));c.commit();c.close()
    def summary(r):
        r=json.loads(json.dumps(r));r.pop('dataset',None)
        def prune(v):
            if isinstance(v,dict):
                for k in ('trade_log','risk_decisions','cashflows','equity_curve'):v.pop(k,None)
                for x in v.values():prune(x)
            elif isinstance(v,list):
                for x in v:prune(x)
        prune(r['payload']);return r
    def worker():
        if not worker_lock.acquire(False):return
        try:
            c=db();ids=[r['id'] for r in c.execute("SELECT id FROM edge_lab_runs WHERE kind='ETF' AND status='RUNNING'")];c.close()
            for rid in ids:
                r=row(rid);p=r['payload'];d=r['dataset']
                if digest(r['protocol']['experiment'])!=digest(PROTOCOL):r['status']='PROTOCOL_BLOCKED';p['error']='Registered protocol differs from installed implementation.';save(r);continue
                try:
                    p['stage']='1 · Collect and reconcile input evidence';save(r)
                    source_dir.mkdir(parents=True,exist_ok=True)
                    for s in SYMBOLS:
                        for mode in ('none','splits','all'):
                            key=s+':'+mode
                            if key in d['pages']:continue
                            deadline=time.monotonic()+90
                            while not reserve(False):
                                if time.monotonic()>deadline:raise ValueError('Shared free-data budget unavailable. Resume later; no paid fallback.')
                                time.sleep(12)
                            p['provider_requests']=p.get('provider_requests',0)+1;p['last_request']=key;save(r)
                            d['pages'][key]=TwelveDataAdapter().historical_daily(s,PROTOCOL['warmup_start'],PROTOCOL['development_end'],mode)
                            p['completed_price_pages']=len(d['pages']);save(r);time.sleep(12)
                        if s not in d['distributions']:
                            # Fixed issuer URL only; arbitrary input URLs are never fetched.
                            with urlopen(Request(issuer_url(s),headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as response:content=response.read(8000001)
                            (source_dir/(rid+'-'+s+'.xml')).write_bytes(content)
                            try:parsed=parse_distributions(s,content)
                            except ValueError as e:
                                import hashlib
                                parsed={'symbol':s,'source':issuer_url(s),'source_hash':hashlib.sha256(content).hexdigest(),'coverage_verified':False,'events':[],
                                        'error':str(e),'basis':'Missing worksheet is unknown, not a confirmed absence of distributions.'}
                            parsed['retrieved_at']=now();d['distributions'][s]=parsed;p['completed_issuer_sources']=len(d['distributions']);save(r)
                    checks={};bundle={'reference':d['reference']}
                    for s in SYMBOLS:
                        raw=d['pages'][s+':none']['bars'];split=d['pages'][s+':splits']['bars'];allp=d['pages'][s+':all']['bars'];dist=d['distributions'][s]
                        checks[s]=reconcile(raw,split,allp,dist,d['reference'],PROTOCOL['warmup_start'],PROTOCOL['development_end'])
                        bundle[s]={'raw':raw,'events':dist['events']+checks[s]['inferred_splits'],'distribution_source_hash':dist['source_hash']}
                    p['input_hash']=digest(bundle);p['input_checks']=checks;p['stage']='2 · Fixed ETF universe and inputs recorded';save(r)
                    p['stage']='3 · Shared-account development replay';save(r)
                    result=run(bundle,checks);p['result']=result;p['stage']='4 · Agent evidence report recorded'
                    r['status']='DATA_BLOCKED' if result['data_blocked'] else 'COMPLETE';p['completed_at']=now();save(r)
                    emit('Research Lab','Performance Reviewer','ETF_EVIDENCE_RECORDED',r['status'],'Fixed ETF development evidence and agent report retained; operational desk unchanged.',{'id':rid,'verdict':result['agent_report']['verdict'],'input_hash':p['input_hash']})
                except Exception as e:
                    # Provider adapter redacts its key; other failures report only type.
                    from market_data import MarketDataError
                    p['error']=str(e)[:400] if isinstance(e,(ValueError,MarketDataError)) else type(e).__name__
                    p['failed_stage']=p.get('stage');r['status']='DATA_BLOCKED';save(r)
                    emit('Market Data','Research Lab','ETF_DATA_BLOCKED','REVIEW','ETF research stopped at an unmet input gate.',{'id':rid,'error':p['error']})
        finally:worker_lock.release()
    def start():threading.Thread(target=worker,daemon=True,name='etf-research').start()
    @app.on_event('startup')
    def resume():start()
    @app.get('/etf-research')
    def page():return HTMLResponse(Path(__file__).with_name('etf-research.html').read_text(encoding='utf8'))
    @app.get('/etf-lab')
    def overview():
        c=db();ids=[r['id'] for r in c.execute("SELECT id FROM edge_lab_runs WHERE kind='ETF' ORDER BY ts DESC")];c.close()
        return {'protocol':PROTOCOL,'runs':[summary(row(rid)) for rid in ids],'activation_allowed':False}
    @app.get('/etf-lab/{rid}/dataset')
    def dataset(rid:str):return {'protocol':row(rid)['protocol'],'dataset':row(rid)['dataset']}
    @app.get('/etf-lab/{rid}/issuer/{symbol}')
    def source(rid:str,symbol:str):
        r=row(rid)
        if symbol not in SYMBOLS or symbol not in r['dataset']['distributions']:raise HTTPException(404,'Issuer source not retained.')
        content=(source_dir/(rid+'-'+symbol+'.xml')).read_bytes()
        import hashlib
        if hashlib.sha256(content).hexdigest()!=r['dataset']['distributions'][symbol]['source_hash']:raise HTTPException(409,'Issuer file hash mismatch.')
        return Response(content,media_type='application/xml',headers={'Content-Disposition':'attachment; filename="'+symbol+'-issuer.xml"'})
    @app.get('/etf-lab/{rid}')
    def result(rid:str):
        r=row(rid);r.pop('dataset',None);return r
    @app.post('/etf-lab/start')
    def register(x_control_token:str|None=Header(default=None)):
        control(x_control_token)
        with lock:
            c=db();source=c.execute("SELECT * FROM edge_lab_runs WHERE kind='DAILY' AND status='COMPLETE' ORDER BY ts LIMIT 1").fetchone()
            if not source:c.close();raise HTTPException(422,'Completed daily source calendar required.')
            pages=json.loads(source['dataset']);reference=pages['SPY:2006-01-01']['bars']+pages.get('SPY:2006-01-01:boundary',{}).get('bars',[])
            reference=[b['datetime'] for b in reference]
            protocol={'experiment':PROTOCOL,'calendar_source_run_id':source['id'],'reference_hash':digest(reference)};key=digest(protocol)
            prior=c.execute("SELECT id FROM edge_lab_runs WHERE kind='ETF' AND protocol_key=?",(key,)).fetchone()
            if prior:c.close();return summary(row(prior['id']))
            rid=str(uuid.uuid4());c.execute('INSERT INTO edge_lab_runs VALUES (?,?,?,?,?,?,?,?)',(rid,'ETF',key,now(),'RUNNING',json.dumps(protocol),json.dumps({'stage':'Protocol registered before price collection','provider_requests':0}),json.dumps({'reference':reference,'pages':{},'distributions':{}})));c.commit();c.close()
        emit('Research Lab','ALL','ETF_PROTOCOL_REGISTERED','RESEARCH','One ETF universe and fixed rules registered before historical price collection.',{'id':rid,'protocol_hash':key});start();return summary(row(rid))
    @app.post('/etf-lab/{rid}/retry-data')
    def retry(rid:str,x_control_token:str|None=Header(default=None)):
        control(x_control_token);r=row(rid)
        if r['status']!='DATA_BLOCKED' or r['payload'].get('result'):raise HTTPException(409,'Calculated input failures require investigation, not automatic retries.')
        if r['payload'].get('retries',0)>=2:raise HTTPException(409,'Retry limit reached.')
        r['payload'].setdefault('failed_attempts',[]).append({'ts':now(),'error':r['payload'].pop('error',None),'stage':r['payload'].get('failed_stage')})
        r['payload']['retries']=r['payload'].get('retries',0)+1;r['status']='RUNNING';save(r);start();return summary(r)
    return {'start':start}
