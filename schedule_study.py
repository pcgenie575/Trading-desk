"""One Friday schedule test; reuses the frozen daily baseline without rerunning it."""
import json,hashlib,threading,copy
from pathlib import Path
from weekly_research import simulate
from funding_study import SCENARIOS,funding,settle,screen,VERSION as FUNDING_VERSION,PROTOCOL as FUNDING_PROTOCOL,source_fingerprint as funding_fingerprint
from daily_research import digest
VERSION='weekly-review-v1'
CASES=('funded_reserve','funded_double_costs')
PROTOCOL={'version':VERSION,'symbols':['SPY','QQQ','IWM','DIA'],'start':'2006-01-01','end':'2015-12-31',
 'hypothesis':'Decide new breakout entries and SMA50 exits only at Friday close. Daily protective stops, risk checks, queued fills and account marks remain active.',
 'baseline':'Reuse original unbuffered daily baseline from completed funded-turnover-v1; do not reuse or combine its rejected 1% exit buffer.',
 'candidate':{'trend':100,'breakout':20,'exit_ma':50,'stop_pct':.05,'decision_weekday':4,'exit_buffer_pct':0},
 'friday_holidays':'If Friday has no observed session, skip that week. Do not move decisions to Thursday or use a future weekly close.',
 'execution':'Friday close signals queue for the next observed SPY session open; opening gaps and stops retain original conservative handling.',
 'cost_cases':{k:copy.deepcopy(FUNDING_PROTOCOL['scenarios'][k]) for k in CASES},'funding':copy.deepcopy(FUNDING_PROTOCOL['funding']),
 'sample_and_cost_gates':'Use the same 100-trade, +0.15R stress, PF1.3, drawdown/concentration, lower-turnover and positive funded-return screens as the prior fixed study. Primary funded net must improve too.',
 'input_policy':'Reuse only the exact saved four-ETF 2006–2015 development dataset whose hash matches the completed funding study. Zero provider requests; no holdout prices.',
 'trial_disclosure':'One additional schedule hypothesis on previously inspected development data. Two new candidate calculations and two referenced daily baseline cases; not independent validation.',
 'after_failure':'Retain rejection. No different weekday, threshold, weekly buffer, volatility filter or replacement strategy is attempted automatically.',
 'promotion_allowed':False,'live_changes_allowed':False,
 'limitations':copy.deepcopy(FUNDING_PROTOCOL['limitations'])+['Friday-only MA exits can react later and increase losses; protective stops remain daily.','Observed SPY sessions are a proxy, not an independently certified historical exchange calendar.']}

def fingerprint():
    names=['schedule_study.py','weekly_research.py','funding_study.py','portfolio_research.py','execution.py','risk_policy.py','exposure.py','daily_research.py']
    return {n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in names}

def calculate(dataset,source):
    if source.get('dataset_hash')!=digest(dataset):raise ValueError('Saved development data differs from the funding study hash.')
    if set(dataset)!=set(PROTOCOL['symbols']):raise ValueError('Fixed four-symbol input required.')
    for bars in dataset.values():
        if not bars or bars[0]['datetime']>'2006-01-10' or bars[-1]['datetime']!='2015-12-31':raise ValueError('Full development endpoints required.')
        if [b['datetime'] for b in bars]!=[b['datetime'] for b in dataset['SPY']]:raise ValueError('Daily sessions are not aligned.')
        if any(not PROTOCOL['start']<=b['datetime']<=PROTOCOL['end'] for b in bars):raise ValueError('Only registered development data is allowed.')
    scenarios={}
    for name in CASES:
        settings=SCENARIOS[name];old=source['scenarios'][name]['baseline']
        f=funding(5000,.655,settings['funding_pips'])
        if old['funding']!=f:raise ValueError('Baseline funding assumptions differ.')
        r=simulate(dataset,settings['costs'],review_schedule='friday',initial_cash=f['funded_usd'])
        r['order_count']=2*len(r['trade_log'])+len(r['remaining_unliquidated_symbols'])
        baseline=copy.deepcopy(old)
        for key in ('trade_log','equity_curve','risk_decisions'):baseline['simulation'].pop(key,None)
        scenarios[name]={'baseline':baseline,'candidate':{'simulation':r,'funding':f,'settlement':settle(r['ending_equity'],f,settings['withdrawal_pips'])},'baseline_result_hash':digest(old)}
    gate=screen(scenarios['funded_double_costs']['candidate'],scenarios['funded_double_costs']['baseline'])
    pair=scenarios['funded_reserve'];c=pair['candidate'];b=pair['baseline']
    difference=c['settlement']['net_contributed_capital_usd_equivalent']-b['settlement']['net_contributed_capital_usd_equivalent']
    return {'protocol':PROTOCOL,'dataset_hash':digest(dataset),'scenarios':scenarios,'stress_screen':gate,
      'primary_comparison':{'candidate_minus_baseline_net_usd_equivalent':difference,'baseline_orders':b['simulation']['order_count'],'candidate_orders':c['simulation']['order_count'],'improved_funded_net':difference>0},
      'decision':'FURTHER_VALIDATION_REQUIRED' if gate['passed'] and difference>0 else 'REJECT_DEVELOPMENT',
      'historical_validation':None,'provider_requests':0,'baseline_recalculated':False,'period_reused':True,'promotion_allowed':False,'edge_validated':False}

def install(app,s):
    from fastapi import HTTPException,Header
    from fastapi.responses import HTMLResponse
    lock=threading.Lock()
    @app.on_event('startup')
    def init():
        c=s['db']();c.execute('CREATE TABLE IF NOT EXISTS schedule_studies(id TEXT PRIMARY KEY,registered_at TEXT,status TEXT,protocol TEXT,dataset TEXT,payload TEXT)')
        c.execute("UPDATE schedule_studies SET status='INTERRUPTED' WHERE status IN ('REGISTERED','RUNNING')");c.commit();c.close()
    def overview(full=False):
        c=s['db']();row=c.execute('SELECT * FROM schedule_studies WHERE id=?',(VERSION,)).fetchone();c.close()
        if not row:return {'id':VERSION,'status':'NOT_REGISTERED','protocol':PROTOCOL,'promotion_allowed':False}
        r=dict(row);r.pop('dataset',None)
        for k in ('protocol','payload'):r[k]=json.loads(r[k])
        r['installed_source_matches']=r['protocol']['source_fingerprint']==fingerprint()
        if not full:
            for pair in r['payload'].get('scenarios',{}).values():
                for name in ('baseline','candidate'):
                    for k in ('trade_log','equity_curve','risk_decisions'):pair[name]['simulation'].pop(k,None)
        return r
    @app.get('/weekly-study')
    def page():return HTMLResponse(Path(__file__).with_name('weekly.html').read_text(encoding='utf8'))
    @app.get('/schedule-lab')
    def state():return overview()
    @app.get('/schedule-lab/result')
    def result():return overview(True)
    @app.post('/schedule-lab/register')
    def register(x_control_token:str|None=Header(default=None)):
        s['require_control'](x_control_token)
        if not lock.acquire(False):raise HTTPException(409,'Weekly study is already running.')
        try:
            with s['_cycle_lock']:
                c=s['db']();old=c.execute('SELECT id FROM schedule_studies WHERE id=?',(VERSION,)).fetchone()
                if old:c.close();lock.release();return overview()
                source=c.execute('SELECT id,status,protocol FROM funding_studies WHERE id=?',(FUNDING_VERSION,)).fetchone()
                if not source or source['status']!='COMPLETE':c.close();raise HTTPException(422,'Completed original funding baseline required.')
                p=json.loads(source['protocol'])
                if p['study']!=json.loads(json.dumps(FUNDING_PROTOCOL)) or p['source_fingerprint']!=funding_fingerprint():c.close();raise HTTPException(409,'Original funding protocol/source mismatch; no replacement or rerun.')
                protocol={'study':PROTOCOL,'source_study_id':source['id'],'source_protocol_hash':digest(p),'source_fingerprint':fingerprint()}
                c.execute('INSERT INTO schedule_studies VALUES (?,?,?,?,?,?)',(VERSION,s['utcnow'](),'REGISTERED',json.dumps(protocol),'{}','{}'));c.commit();c.close()
            def worker():
                status='FAILED';payload={}
                try:
                    c=s['db']();row=c.execute('SELECT dataset,payload FROM funding_studies WHERE id=?',(FUNDING_VERSION,)).fetchone();c.close()
                    data=json.loads(row['dataset']);baseline=json.loads(row['payload'])
                    c=s['db']();c.execute('UPDATE schedule_studies SET status=?,dataset=?,payload=? WHERE id=?',('RUNNING',json.dumps(data),json.dumps({'dataset_hash':digest(data),'baseline_payload_hash':digest(baseline)}),VERSION));c.commit();c.close()
                    if protocol['source_fingerprint']!=fingerprint():raise ValueError('Study source changed after registration.')
                    payload=calculate(data,baseline);payload['source_baseline_hash']=digest(baseline);status='COMPLETE'
                except (ValueError,TypeError,KeyError) as ex:payload={'error':str(ex)[:300]};status='DATA_BLOCKED'
                except Exception as ex:payload={'error':type(ex).__name__}
                finally:
                    c=s['db']();c.execute('UPDATE schedule_studies SET status=?,payload=? WHERE id=?',(status,json.dumps(payload),VERSION));c.commit();c.close();lock.release()
            threading.Thread(target=worker,daemon=True,name='fixed-weekly-study').start()
            return {'id':VERSION,'status':'REGISTERED','promotion_allowed':False}
        except Exception:
            if lock.locked():lock.release()
            raise
    return {'overview':overview}
