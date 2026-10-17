"""One reduction-only volatility sizing test; reuses the frozen daily baseline without rerunning it."""
import json,hashlib,threading,copy
from pathlib import Path
from volatility_research import simulate
from funding_study import SCENARIOS,funding,settle,screen,VERSION as FUNDING_VERSION,PROTOCOL as FUNDING_PROTOCOL,source_fingerprint as funding_fingerprint
from daily_research import digest
VERSION='volatility-cap-v1'
CASES=('funded_reserve','funded_double_costs')
PROTOCOL={'version':VERSION,'symbols':['SPY','QQQ','IWM','DIA'],'start':'2006-01-01','end':'2015-12-31',
 'hypothesis':'Reduce entry caps using min(1, 15% / annualised 20-session sample volatility of simple close returns). Daily baseline signals and exits remain unchanged.',
 'baseline':'Reuse original unbuffered daily funded-turnover-v1 baseline; do not combine Friday decisions or rejected exit buffer.',
 'candidate':{'trend':100,'breakout':20,'exit_ma':50,'stop_pct':.05,'volatility_returns':20,'annualisation':252,'target_volatility':.15},
 'sizing':'Scale both $500 value and $25 all-in planned-loss caps. Save signal-close scale and quantity; next-open fill may not exceed either. No resizing held positions. Invalid/insufficient returns block entry; valid zero volatility uses scale 1.',
 'cost_cases':{k:copy.deepcopy(FUNDING_PROTOCOL['scenarios'][k]) for k in CASES},'funding':copy.deepcopy(FUNDING_PROTOCOL['funding']),
 'sample_and_cost_gates':'100 stress trades, expectancy >=0.15R, PF>=1.3, drawdown <=250 and baseline, top two <=35% positive P&L, positive excluding top two, positive after funding, better net R, complete liquidation, improved primary funded net. Lower turnover is descriptive, not a gate for a sizing hypothesis.',
 'input_policy':'Exact saved four-ETF 2006–2015 development dataset with matching hash. No provider requests or holdout access.',
 'trial_disclosure':'One additional fixed sizing hypothesis on previously inspected development data; two candidate calculations and reused baseline. Not independent validation.',
 'after_failure':'Retain rejection; no target/window search or automatic replacement.',
 'promotion_allowed':False,'live_changes_allowed':False,
 'limitations':copy.deepcopy(FUNDING_PROTOCOL['limitations'])+['Entry cap is not continuous portfolio volatility targeting. Smaller risk can change R denominators; assess dollar return and drawdown too.','Fixed fees can prevent very small positions. Gaps can exceed planned risk.']}

def screen(candidate,baseline):
    from funding_study import screen as original_screen
    result=original_screen(candidate,baseline)
    result['checks'].pop('lower_turnover')
    result['passed']=all(result['checks'].values())
    return result

def fingerprint():
    names=['volatility_study.py','volatility_research.py','funding_study.py','portfolio_research.py','execution.py','risk_policy.py','exposure.py','daily_research.py']
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
        r=simulate(dataset,settings['costs'],volatility_cap=True,initial_cash=f['funded_usd'])
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
        c=s['db']();c.execute('CREATE TABLE IF NOT EXISTS volatility_studies(id TEXT PRIMARY KEY,registered_at TEXT,status TEXT,protocol TEXT,dataset TEXT,payload TEXT)')
        c.execute("UPDATE volatility_studies SET status='INTERRUPTED' WHERE status IN ('REGISTERED','RUNNING')");c.commit();c.close()
    def overview(full=False):
        c=s['db']();row=c.execute('SELECT * FROM volatility_studies WHERE id=?',(VERSION,)).fetchone();c.close()
        if not row:return {'id':VERSION,'status':'NOT_REGISTERED','protocol':PROTOCOL,'promotion_allowed':False}
        r=dict(row);r.pop('dataset',None)
        for k in ('protocol','payload'):r[k]=json.loads(r[k])
        r['installed_source_matches']=r['protocol']['source_fingerprint']==fingerprint()
        if not full:
            for pair in r['payload'].get('scenarios',{}).values():
                for name in ('baseline','candidate'):
                    for k in ('trade_log','equity_curve','risk_decisions'):pair[name]['simulation'].pop(k,None)
        return r
    @app.get('/volatility-study')
    def page():return HTMLResponse(Path(__file__).with_name('volatility.html').read_text(encoding='utf8'))
    @app.get('/volatility-lab')
    def state():return overview()
    @app.get('/volatility-lab/result')
    def result():return overview(True)
    @app.post('/volatility-lab/register')
    def register(x_control_token:str|None=Header(default=None)):
        s['require_control'](x_control_token)
        if not lock.acquire(False):raise HTTPException(409,'Volatility study is already running.')
        try:
            with s['_cycle_lock']:
                c=s['db']();old=c.execute('SELECT id FROM volatility_studies WHERE id=?',(VERSION,)).fetchone()
                if old:c.close();lock.release();return overview()
                source=c.execute('SELECT id,status,protocol FROM funding_studies WHERE id=?',(FUNDING_VERSION,)).fetchone()
                if not source or source['status']!='COMPLETE':c.close();raise HTTPException(422,'Completed original funding baseline required.')
                p=json.loads(source['protocol'])
                if p['study']!=json.loads(json.dumps(FUNDING_PROTOCOL)) or p['source_fingerprint']!=funding_fingerprint():c.close();raise HTTPException(409,'Original funding protocol/source mismatch; no replacement or rerun.')
                protocol={'study':PROTOCOL,'source_study_id':source['id'],'source_protocol_hash':digest(p),'source_fingerprint':fingerprint()}
                c.execute('INSERT INTO volatility_studies VALUES (?,?,?,?,?,?)',(VERSION,s['utcnow'](),'REGISTERED',json.dumps(protocol),'{}','{}'));c.commit();c.close()
            def worker():
                status='FAILED';payload={}
                try:
                    c=s['db']();row=c.execute('SELECT dataset,payload FROM funding_studies WHERE id=?',(FUNDING_VERSION,)).fetchone();c.close()
                    data=json.loads(row['dataset']);baseline=json.loads(row['payload'])
                    c=s['db']();c.execute('UPDATE volatility_studies SET status=?,dataset=?,payload=? WHERE id=?',('RUNNING',json.dumps(data),json.dumps({'dataset_hash':digest(data),'baseline_payload_hash':digest(baseline)}),VERSION));c.commit();c.close()
                    if protocol['source_fingerprint']!=fingerprint():raise ValueError('Study source changed after registration.')
                    payload=calculate(data,baseline);payload['source_baseline_hash']=digest(baseline);status='COMPLETE'
                except (ValueError,TypeError,KeyError) as ex:payload={'error':str(ex)[:300]};status='DATA_BLOCKED'
                except Exception as ex:payload={'error':type(ex).__name__}
                finally:
                    c=s['db']();c.execute('UPDATE volatility_studies SET status=?,payload=? WHERE id=?',(status,json.dumps(payload),VERSION));c.commit();c.close();lock.release()
            threading.Thread(target=worker,daemon=True,name='fixed-volatility-study').start()
            return {'id':VERSION,'status':'REGISTERED','promotion_allowed':False}
        except Exception:
            if lock.locked():lock.release()
            raise
    return {'overview':overview}
