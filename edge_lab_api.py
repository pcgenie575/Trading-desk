"""Durable, budgeted research jobs isolated from the operational paper ledger."""
import json,threading,time,uuid
from pathlib import Path
from fastapi import Header,HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel,Field
from daily_research import PROTOCOL,SYMBOLS,digest,run_daily
from cost_diagnostics import diagnose,SCENARIOS
from dataclasses import asdict
from cost_scenarios import PROTOCOL as COST_V2_PROTOCOL,diagnose as diagnose_v2
from cost_stress import PROTOCOL as COST_V3_PROTOCOL,diagnose as diagnose_v3
from research_inventory import slots
from market_data import TwelveDataAdapter
from portfolio_research import PROTOCOL as PORTFOLIO_PROTOCOL,run as run_portfolio

class DiagnosticInput(BaseModel):
    source_run_id:str=Field(min_length=1,max_length=100)

def install(app,services):
    db=services['db'];lock=services['_cycle_lock'];now=services['utcnow'];control=services['require_control'];emit=services['emit'];reserve=services['reserve_credit']
    worker_lock=threading.Lock()
    def save(r):
        with lock:
            c=db();c.execute('UPDATE edge_lab_runs SET status=?,payload=?,dataset=? WHERE id=?',(r['status'],json.dumps(r['payload']),json.dumps(r['dataset']),r['id']));c.commit();c.close()
    def row(rid):
        c=db();r=c.execute('SELECT * FROM edge_lab_runs WHERE id=?',(rid,)).fetchone();c.close()
        if not r:raise HTTPException(404,'Research job not found.')
        r=dict(r)
        for k in ('protocol','payload','dataset'):r[k]=json.loads(r[k])
        return r
    def public(r):
        r=dict(r);r.pop('dataset',None)
        # Summary never discards stored trade logs; full result remains exportable.
        r['payload']=json.loads(json.dumps(r['payload']))
        def prune(v):
            if isinstance(v,dict):
                v.pop('trade_log',None)
                for x in v.values():prune(x)
            elif isinstance(v,list):
                for x in v:prune(x)
        prune(r['payload']);return r
    def create(kind,key,protocol,payload,dataset):
        with lock:
            c=db();prior=c.execute('SELECT id FROM edge_lab_runs WHERE kind=? AND protocol_key=?',(kind,key)).fetchone()
            if prior:c.close();return prior['id'],False
            rid=str(uuid.uuid4());c.execute('INSERT INTO edge_lab_runs VALUES (?,?,?,?,?,?,?,?)',(rid,kind,key,now(),'RUNNING',json.dumps(protocol),json.dumps(payload),json.dumps(dataset)));c.commit();c.close()
            emit('Research Lab','Performance Reviewer','EDGE_PROTOCOL_REGISTERED','RESEARCH','Research protocol durably registered before calculation.',{'id':rid,'kind':kind,'protocol_hash':digest(protocol)})
            return rid,True
    def worker():
        if not worker_lock.acquire(False):return
        try:
            c=db();jobs=[r['id'] for r in c.execute("SELECT id FROM edge_lab_runs WHERE kind='DAILY' AND status='RUNNING'")];c.close()
            for rid in jobs:
                r=row(rid);pages=r['dataset'];progress=r['payload']
                if digest(r['protocol'])!=digest(PROTOCOL):
                    r['status']='PROTOCOL_BLOCKED';progress['error']='Registered protocol differs from installed code; no calculation performed.';save(r);return
                for symbol in SYMBOLS:
                    for start,end in (('2006-01-01','2015-12-31'),('2016-01-01','2026-10-09')):
                        key=symbol+':'+start
                        request_start=start;storage_key=key
                        if key in pages:
                            if pages[key]['bars'][-1]['datetime']==end or key+':boundary' in pages:continue
                            # Preserve earlier date-only responses; supplement their omitted end day.
                            request_start=end;storage_key=key+':boundary'
                        while not reserve(False):time.sleep(12)
                        progress['attempted_requests']=progress.get('attempted_requests',0)+1
                        try:
                            page=TwelveDataAdapter().historical_daily(symbol,request_start,end)
                            pages[storage_key]=page;progress['completed_pages']=sum(':boundary' not in k for k in pages);progress['boundary_supplements']=sum(':boundary' in k for k in pages);progress['last_page']=storage_key
                            r['dataset']=pages;save(r)
                        except Exception as e:
                            progress['error']=str(e)[:400];progress['failed_page']=key;r['status']='DATA_BLOCKED';save(r)
                            emit('Research Lab','Supervisor','DAILY_HISTORY_BLOCKED','REVIEW','Free history collection stopped; no paid fallback or universe substitution.',{'id':rid,'page':key,'error':progress['error']});return
                        time.sleep(12) # at most five research requests/minute, shared six-credit gate
                dataset={s:sum((pages[s+':'+start]['bars']+pages.get(s+':'+start+':boundary',{}).get('bars',[]) for start in ('2006-01-01','2016-01-01')),[]) for s in SYMBOLS}
                # Protocol and exact dataset hash are durable before computing any metric.
                progress['dataset_hash']=digest(dataset);progress['calculation_started_at']=now();save(r)
                try:
                    result=run_daily(dataset);r['payload']=dict(progress,result=result);r['status']='COMPLETE'
                except Exception as e:r['payload']=dict(progress,error=str(e)[:400]);r['status']='FAILED'
                save(r);emit('Research Lab','Performance Reviewer','DAILY_RESEARCH_RECORDED',r['status'],'Daily research retained; operational v1 and its forward plan unchanged.',{'id':rid,'status':r['status']})
        finally:worker_lock.release()
    def start():threading.Thread(target=worker,daemon=True,name='daily-research').start()
    @app.on_event('startup')
    def resume_jobs():
        with lock:
            c=db();c.execute("UPDATE edge_lab_runs SET status='INTERRUPTED' WHERE kind IN ('COST','PORTFOLIO') AND status='RUNNING'");c.commit();c.close()
        start()
    @app.get('/edge')
    def page():return HTMLResponse(Path(__file__).with_name('edge.html').read_text(encoding='utf8'))
    @app.get('/portfolio')
    def portfolio_page():return HTMLResponse(Path(__file__).with_name('portfolio.html').read_text(encoding='utf8'))
    @app.get('/edge-lab')
    def overview():
        c=db();ids=[r['id'] for r in c.execute('SELECT id FROM edge_lab_runs ORDER BY ts DESC LIMIT 20')];c.close()
        return {'daily_protocol':PROTOCOL,'portfolio_protocol':PORTFOLIO_PROTOCOL,'runs':[public(row(rid)) for rid in ids],'operational_strategy_unchanged':True}
    @app.get('/edge-lab/{rid}/dataset')
    def dataset_export(rid:str):
        r=row(rid);return {'protocol':r['protocol'],'dataset':r['dataset']}
    @app.get('/edge-lab/{rid}')
    def result_export(rid:str):
        r=row(rid);r.pop('dataset',None);return r
    @app.post('/edge-lab/cost-diagnostic')
    def cost_diagnostic(payload:DiagnosticInput,x_control_token:str|None=Header(default=None)):
        control(x_control_token)
        c=db();original=c.execute('SELECT * FROM research_runs WHERE id=?',(payload.source_run_id,)).fetchone();c.close()
        if not original or original['status']!='COMPLETE':raise HTTPException(422,'Choose a completed original experiment.')
        bars=json.loads(original['dataset']);old=json.loads(original['payload']);split=old['split_index']
        protocol={'version':'cost-diagnostic-v1','source_run_id':payload.source_run_id,'source_protocol':json.loads(original['protocol']),'scenarios':{k:asdict(v) for k,v in SCENARIOS.items()},'test_period_reused':True}
        rid,created=create('COST',digest(protocol),protocol,{}, {'symbol':original['symbol'],'bars':bars})
        if created:
            r=row(rid)
            try:r['payload']=diagnose(original['symbol'],bars,split);r['status']='COMPLETE'
            except Exception as e:r['status']='FAILED';r['payload']={'error':type(e).__name__}
            save(r)
        return public(row(rid))
    @app.get('/research-accountability')
    def accountability():
        c=db();originals=[dict(x) for x in c.execute('SELECT id,status,protocol FROM research_runs')];labs=[dict(x) for x in c.execute('SELECT id,kind,status,protocol FROM edge_lab_runs')]
        learning=[dict(x) for x in c.execute('SELECT id,status,protocol FROM learning_tests')] if c.execute("SELECT 1 FROM sqlite_master WHERE name='learning_tests'").fetchone() else []
        fixed=[]
        for table,kind,calculations in [('funding_studies','FUNDED_TURNOVER',8),('schedule_studies','WEEKLY_SCHEDULE',2)]:
            if c.execute("SELECT 1 FROM sqlite_master WHERE name=?",(table,)).fetchone():
                fixed.extend(dict(x,kind=kind,calculations=calculations) for x in c.execute('SELECT id,status,protocol FROM '+table))
        c.close()
        inventory=[]
        for x in fixed:
            p=json.loads(x['protocol']);inventory.append({'id':x['id'],'kind':x['kind'],'status':x['status'],'version':p['study']['version'],'registered_strategy_slots':2,'new_hypotheses':1,'cost_method_calculations':x['calculations'],'baseline_reused':True})
        for x in learning:
            p=json.loads(x['protocol']);inventory.append({'id':x['id'],'kind':'LEARNING','status':x['status'],'version':p['version'],'registered_strategy_slots':2,'cost_method_calculations':None})
        for x in originals:
            p=json.loads(x['protocol']);n=slots(p,'ORIGINAL')
            inventory.append({'id':x['id'],'kind':'ORIGINAL','status':x['status'],'version':p.get('version'),'registered_strategy_slots':n,'cost_method_calculations':None})
        for x in labs:
            p=json.loads(x['protocol']);kind=x['kind'];version=p.get('version') or p.get('experiment',{}).get('version')
            n=slots(p,kind)
            calculations=(p.get('calculations') or n*len(p.get('scenarios',{}))*2 if n is not None else None) if kind=='COST' else None
            inventory.append({'id':x['id'],'kind':kind,'status':x['status'],'version':version,'registered_strategy_slots':n,'cost_method_calculations':calculations})
        return {'records':inventory,'record_count':len(inventory),'registered_strategy_slots':sum(x['registered_strategy_slots'] or 0 for x in inventory),
            'unclassified_records':sum(x['registered_strategy_slots'] is None for x in inventory),'count_definition':'Registered configuration slots summed across records, including reused strategies, diagnostic neighbours and blocked jobs. Not a count of independent trials or completed evaluations.',
            'all_time_search_count_known':False,'deflated_sharpe':{'available':False,'reason':'No complete, comparable aligned return matrix and independently justified trial count. A guessed six-strategy N would be misleading.'},
            'probability_of_backtest_overfitting':{'available':False,'reason':'No valid common-period candidate return matrix for symmetric cross-validation.'},
            'diagnostic_only':True,'promotion_allowed':False}
    @app.post('/edge-lab/cost-scenarios')
    def cost_scenarios(payload:DiagnosticInput,x_control_token:str|None=Header(default=None)):
        control(x_control_token)
        c=db();original=c.execute('SELECT * FROM research_runs WHERE id=?',(payload.source_run_id,)).fetchone();c.close()
        if not original or original['status']!='COMPLETE':raise HTTPException(422,'Choose a completed original experiment.')
        bars=json.loads(original['dataset']);old=json.loads(original['payload']);split=old['split_index']
        protocol=dict(COST_V2_PROTOCOL,source_run_id=payload.source_run_id,source_protocol=json.loads(original['protocol']),source_dataset_hash=digest(bars))
        rid,created=create('COST',digest(protocol),protocol,{}, {'symbol':original['symbol'],'bars':bars})
        if created:
            r=row(rid)
            try:r['payload']=diagnose_v2(original['symbol'],bars,split);r['status']='COMPLETE'
            except Exception as e:r['status']='FAILED';r['payload']={'error':type(e).__name__}
            save(r)
        return public(row(rid))
    @app.post('/edge-lab/cost-stress')
    def cost_stress(payload:DiagnosticInput,x_control_token:str|None=Header(default=None)):
        control(x_control_token)
        c=db();original=c.execute('SELECT * FROM research_runs WHERE id=?',(payload.source_run_id,)).fetchone();c.close()
        if not original or original['status']!='COMPLETE':raise HTTPException(422,'Choose a completed original experiment.')
        bars=json.loads(original['dataset']);old=json.loads(original['payload']);split=old['split_index']
        protocol=dict(COST_V3_PROTOCOL,source_run_id=payload.source_run_id,source_protocol=json.loads(original['protocol']),source_dataset_hash=digest(bars))
        rid,created=create('COST',digest(protocol),protocol,{}, {'symbol':original['symbol'],'bars':bars})
        if created:
            r=row(rid)
            try:r['payload']=diagnose_v3(original['symbol'],bars,split);r['status']='COMPLETE'
            except Exception as e:r['status']='FAILED';r['payload']={'error':type(e).__name__}
            save(r)
        return public(row(rid))
    @app.post('/edge-lab/daily')
    def daily(x_control_token:str|None=Header(default=None)):
        control(x_control_token);rid,created=create('DAILY',digest(PROTOCOL),PROTOCOL,{'completed_pages':0,'required_pages':40,'attempted_requests':0,'selection_locked_before_data':True},{})
        if created:start()
        return public(row(rid))
    @app.post('/edge-lab/portfolio')
    def portfolio(payload:DiagnosticInput,x_control_token:str|None=Header(default=None)):
        control(x_control_token);source=row(payload.source_run_id)
        if source['kind']!='DAILY' or source['status']!='COMPLETE':raise HTTPException(422,'A completed daily dataset is required.')
        pages=source['dataset'];data={s:pages[s+':2006-01-01']['bars']+pages.get(s+':2006-01-01:boundary',{}).get('bars',[]) for s in PORTFOLIO_PROTOCOL['symbols']}
        protocol=dict(PORTFOLIO_PROTOCOL,source_run_id=source['id'],source_dataset_hash=source['payload']['dataset_hash'])
        rid,created=create('PORTFOLIO',digest(protocol),protocol,{'development_only':True},data)
        if created:
            r=row(rid)
            try:r['payload'].update(result=run_portfolio(data));r['status']='COMPLETE'
            except Exception as e:r['payload']['error']=str(e)[:400];r['status']='FAILED'
            save(r);emit('Research Lab','Performance Reviewer','PORTFOLIO_REPLAY_RECORDED',r['status'],'Development portfolio replay retained; no holdout calculation or activation.',{'id':rid})
        return public(row(rid))
    @app.post('/edge-lab/{rid}/retry-data')
    def retry(rid:str,x_control_token:str|None=Header(default=None)):
        control(x_control_token);r=row(rid)
        if r['kind']!='DAILY' or r['status']!='DATA_BLOCKED':raise HTTPException(409,'Only blocked data collection can be resumed; completed tests cannot be rerun.')
        if r['payload'].get('retries',0)>=2:raise HTTPException(409,'Two data retries exhausted; investigate entitlement or source failure.')
        r['payload']['retries']=r['payload'].get('retries',0)+1;r['status']='RUNNING';save(r);start();return public(r)
    return {'start':start,'row':row}
