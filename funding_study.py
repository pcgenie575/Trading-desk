"""One registered turnover hypothesis; funding is separate from trading costs."""
import math,hashlib,json
from dataclasses import replace,asdict
from pathlib import Path
from execution import COSTS
from daily_research import STRESS,digest
from portfolio_research import simulate,PROTOCOL as PORTFOLIO
VERSION='funded-turnover-v1'
SOURCES={'fx':'https://www.webull.com.au/help/faq/2041-How-is-the-FX-fee-calculated',
 'usd_settlement':'https://www.webull.com.au/help/faq/1617',
 'etf_brokerage':'https://www.webull.com.au/help/faq/1423-How-much-does-it-cost-to-trade',
 'turnover_research':'https://www.nber.org/papers/w20721'}
SCENARIOS={
 'legacy_per_trade':{'costs':COSTS,'funding_pips':0.,'withdrawal_pips':0.,'status':'Unchanged conservative per-trade allowance; not a broker tariff.'},
 'funded_reserve':{'costs':replace(COSTS,version='funded-usd-reserve-v1',fx_bps=0),'funding_pips':.005,'withdrawal_pips':.005,
    'status':'Primary diagnostic: USD proceeds reused; $1/order remains an unverified total fee reserve, not an assertion of ETF brokerage.'},
 'etf_brokerage_floor':{'costs':replace(COSTS,version='funded-etf-fee-floor-v1',fx_bps=0,fee_per_order=0),'funding_pips':.005,'withdrawal_pips':.005,
    'status':'Sensitivity floor only: advertised zero ETF brokerage excludes unverified pass-through/other fees. Not promotion eligible.'},
 'funded_double_costs':{'costs':replace(STRESS,version='funded-usd-stress-v1',fx_bps=0),'funding_pips':.010,'withdrawal_pips':.010,
    'status':'Doubled spread/slippage/fee reserve and conversion spreads; not doubled market volatility.'}}
PROTOCOL={'version':VERSION,'symbols':PORTFOLIO['symbols'],'start':'2006-01-01','end':'2015-12-31',
 'baseline':{'trend':100,'breakout':20,'exit_ma':50,'exit_buffer_pct':0.},
 'candidate':{'trend':100,'breakout':20,'exit_ma':50,'exit_buffer_pct':.01},
 'hypothesis':'One fixed 1% buffer below the daily SMA50 for the existing MA exit; identical entries and unchanged 5% protective stops. No alternative buffer or selection search.',
 'scenarios':{k:dict(v,costs=asdict(v['costs'])) for k,v in SCENARIOS.items()},
 'funding':{'capital_usd_equivalent':5000.,'bank_audusd':.655,'bank_usdaud':'Reciprocal of the same fixed bank reference.',
    'basis':'Illustrative constant FX reference, not historical AUD returns. A 0.005 spread is 50 quoted rate pips, not 0.5% universally.',
    'cash_timing':'Convert the full budget once at funding; use USD cash for every trade; convert terminal equity once at hypothetical withdrawal.',
    'drawdown':'Trade drawdown measured from net funded cash; funding costs remain in contributed-capital return.'},
 'input_policy':'Reuse only the saved four-ETF daily development prices, with existing coverage requirements. No holdout prices or new provider calls.',
 'trial_disclosure':'One new exit hypothesis on previously inspected development data, across four declared cost sensitivities. Eight calculations are not eight independent discoveries.',
 'decision':'Compare funded_reserve candidate with its matching baseline; require 100 stress closed trades, stress expectancy >=0.15R, PF>=1.3, DD<=250 and <=baseline DD, no more than35% positive profit from top2, positive net without top2, positive funded return and lower turnover.',
 'promotion_allowed':False,'live_changes_allowed':False,'sources':SOURCES,
 'limitations':['Split-adjusted synthetic prices; not verified raw ETF cashflows. Dividends and distributions omitted.',
 'No historical exchange-rate path, investor tax, USD cash interest, deposits after funding or verified account-specific fee schedule.',
 'Protective stops and gaps remain binding; a wider MA exit can lose more before an exit. Fewer trades need not improve expectancy.',
 'No live four-hour timing parity. Old failed research, risk limits, ledger and forward registrations stay intact.',
 'Even a passing development screen requires separate input repair, preregistered validation and genuinely future paper evidence.']}

def funding(capital,bank_audusd,pips):
    if not all(math.isfinite(x) for x in (capital,bank_audusd,pips)) or capital<=0 or bank_audusd<=0 or not 0<=pips<bank_audusd:raise ValueError('Invalid funding assumptions.')
    aud=capital/bank_audusd;usd=capital*(1-pips/bank_audusd)
    return {'contributed_aud':aud,'capital_usd_equivalent':capital,'funded_usd':usd,'funding_cost_usd_equivalent':capital-usd,
      'bank_audusd':bank_audusd,'display_audusd':bank_audusd-pips,'pips':pips}

def settle(terminal_usd,f,withdrawal_pips):
    rate=1/f['bank_audusd']
    if not math.isfinite(terminal_usd) or terminal_usd<0 or not math.isfinite(withdrawal_pips) or not 0<=withdrawal_pips<rate:raise ValueError('Invalid terminal conversion.')
    aud=terminal_usd*(rate-withdrawal_pips);withdrawal_cost=terminal_usd*withdrawal_pips*f['bank_audusd']
    trading=terminal_usd-f['funded_usd'];net=aud*f['bank_audusd']-f['capital_usd_equivalent']
    return {'terminal_aud_at_fixed_reference':aud,'net_aud_at_fixed_reference':aud-f['contributed_aud'],
      'trading_pnl_usd':trading,'funding_cost_usd_equivalent':f['funding_cost_usd_equivalent'],
      'withdrawal_cost_usd_equivalent':withdrawal_cost,'net_contributed_capital_usd_equivalent':net,
      'bridge_residual':net-(trading-f['funding_cost_usd_equivalent']-withdrawal_cost),
      'note':'Constant-rate sensitivity including terminal equity liquidation assumption, not historical AUD investment performance.'}

def screen(candidate,baseline):
    c=candidate['simulation'];b=baseline['simulation'];trades=c['trade_log'];positive=sum(max(0,t['pnl']) for t in trades)
    top=sum(sorted((max(0,t['pnl']) for t in trades),reverse=True)[:2]);loss=-sum(min(0,t['pnl']) for t in trades)
    checks={'sample_size':len(trades)>=100,'stress_expectancy':c['expectancy_r'] is not None and c['expectancy_r']>=.15,
      'profit_factor':loss>0 and positive/loss>=1.3,'drawdown':c['max_drawdown']<=250 and c['max_drawdown']<=b['max_drawdown'],
      'concentration':positive>0 and top/positive<=.35,'positive_without_two':sum(t['pnl'] for t in trades)-top>0,
      'positive_after_funding':candidate['settlement']['net_contributed_capital_usd_equivalent']>0,
      'lower_turnover':c['order_count']<b['order_count'],
      'better_net_r':c['expectancy_r'] is not None and b['expectancy_r'] is not None and c['expectancy_r']>b['expectancy_r'],
      'complete_terminal_prices':not c['remaining_unliquidated_symbols'] and not b['remaining_unliquidated_symbols']}
    return {'passed':all(checks.values()),'checks':checks,'promotion_allowed':False}

def calculate(dataset):
    data={s:[b for b in dataset[s] if PROTOCOL['start']<=b['datetime']<=PROTOCOL['end']] for s in PROTOCOL['symbols']}
    if any(not bars or bars[0]['datetime']>'2006-01-10' or bars[-1]['datetime']!='2015-12-31' for bars in data.values()):raise ValueError('Full original development history required; no shortened-period fallback.')
    if any([b['datetime'] for b in bars]!=[b['datetime'] for b in data['SPY']] for bars in data.values()):raise ValueError('Development symbol sessions do not align; investigate missing inputs.')
    scenarios={}
    for name,scenario in SCENARIOS.items():
        f=funding(5000,.655,scenario['funding_pips']);pair={}
        for label,buffer in [('baseline',0.),('candidate',.01)]:
            r=simulate(data,scenario['costs'],exit_buffer_pct=buffer,initial_cash=f['funded_usd'])
            # Terminal closes count as orders; any remaining positions stay explicit.
            r['order_count']=2*len(r['trade_log'])+len(r['remaining_unliquidated_symbols'])
            pair[label]={'simulation':r,'funding':f,'settlement':settle(r['ending_equity'],f,scenario['withdrawal_pips'])}
        scenarios[name]=pair
    gate=screen(scenarios['funded_double_costs']['candidate'],scenarios['funded_double_costs']['baseline'])
    normal=scenarios['funded_reserve'];n=normal['candidate']['simulation'];b=normal['baseline']['simulation']
    improved=normal['candidate']['settlement']['net_contributed_capital_usd_equivalent']>normal['baseline']['settlement']['net_contributed_capital_usd_equivalent']
    return {'protocol':PROTOCOL,'dataset_hash':digest(data),'scenarios':scenarios,'stress_screen':gate,
      'decision':'FURTHER_VALIDATION_REQUIRED' if gate['passed'] and improved else 'REJECT_DEVELOPMENT',
      'primary_comparison':{'candidate_minus_baseline_net_usd_equivalent':normal['candidate']['settlement']['net_contributed_capital_usd_equivalent']-normal['baseline']['settlement']['net_contributed_capital_usd_equivalent'],
        'baseline_orders':b['order_count'],'candidate_orders':n['order_count'],'improved_funded_net':improved},
      'historical_validation':None,'provider_requests':0,'period_reused':True,'promotion_allowed':False,'edge_validated':False}

def source_fingerprint():
    names=['funding_study.py','portfolio_research.py','execution.py','risk_policy.py','exposure.py','daily_research.py']
    return {n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in names}

def install(app,s):
    import threading
    from fastapi import HTTPException,Header
    from fastapi.responses import HTMLResponse
    worker_lock=threading.Lock()
    @app.on_event('startup')
    def init():
        c=s['db']();c.execute('CREATE TABLE IF NOT EXISTS funding_studies(id TEXT PRIMARY KEY,registered_at TEXT,status TEXT,protocol TEXT,dataset TEXT,payload TEXT)')
        c.execute("UPDATE funding_studies SET status='INTERRUPTED' WHERE status IN ('REGISTERED','RUNNING')");c.commit();c.close()
    def get():
        c=s['db']();r=c.execute('SELECT * FROM funding_studies WHERE id=?',(VERSION,)).fetchone();c.close()
        if not r:return {'id':VERSION,'status':'NOT_REGISTERED','protocol':PROTOCOL,'promotion_allowed':False}
        r=dict(r);r.pop('dataset',None)
        for k in ('protocol','payload'):r[k]=json.loads(r[k])
        r['installed_source_matches']=r['protocol']['source_fingerprint']==source_fingerprint()
        return r
    @app.get('/funding-study')
    def page():return HTMLResponse(Path(__file__).with_name('funding.html').read_text(encoding='utf8'))
    @app.get('/funding-lab')
    def overview():return get()
    @app.post('/funding-lab/register')
    def register(x_control_token:str|None=Header(default=None)):
        s['require_control'](x_control_token)
        if not worker_lock.acquire(False):raise HTTPException(409,'One funding study is already running.')
        try:
            with s['_cycle_lock']:
                c=s['db']();old=c.execute('SELECT id FROM funding_studies WHERE id=?',(VERSION,)).fetchone()
                if old:c.close();worker_lock.release();return get()
                source=c.execute("SELECT id,protocol FROM edge_lab_runs WHERE kind='DAILY' AND status='COMPLETE' ORDER BY ts LIMIT 1").fetchone()
                if not source:c.close();raise HTTPException(422,'Completed original daily source required; no new download fallback.')
                from daily_research import PROTOCOL as DAILY_PROTOCOL
                if json.loads(source['protocol'])!=json.loads(json.dumps(DAILY_PROTOCOL)):c.close();raise HTTPException(409,'Original daily source protocol does not match; explicit review required.')
                protocol={'study':PROTOCOL,'source_run_id':source['id'],'original_daily_protocol_hash':digest(json.loads(source['protocol'])),'source_fingerprint':source_fingerprint()}
                # Persist the fixed hypothesis before reading the price dataset.
                c.execute('INSERT INTO funding_studies VALUES (?,?,?,?,?,?)',(VERSION,s['utcnow'](),'REGISTERED',json.dumps(protocol),'{}','{}'));c.commit();c.close()
            def worker():
                status='FAILED';payload={}
                try:
                    c=s['db']();row=c.execute('SELECT dataset FROM edge_lab_runs WHERE id=?',(source['id'],)).fetchone();c.close();pages=json.loads(row['dataset'])
                    data={symbol:pages[symbol+':2006-01-01']['bars']+pages.get(symbol+':2006-01-01:boundary',{}).get('bars',[]) for symbol in PROTOCOL['symbols']}
                    data={symbol:[b for b in bars if PROTOCOL['start']<=b['datetime']<=PROTOCOL['end']] for symbol,bars in data.items()}
                    c=s['db']();c.execute('UPDATE funding_studies SET status=?,dataset=?,payload=? WHERE id=?',('RUNNING',json.dumps(data),json.dumps({'dataset_hash':digest(data)}),VERSION));c.commit();c.close()
                    if protocol['source_fingerprint']!=source_fingerprint():raise ValueError('Installed study source differs from registration.')
                    payload=calculate(data);status='COMPLETE'
                except (ValueError,KeyError,TypeError) as ex:payload={'error':str(ex)[:300]};status='DATA_BLOCKED'
                except Exception as ex:payload={'error':type(ex).__name__}
                finally:
                    c=s['db']();c.execute('UPDATE funding_studies SET status=?,payload=? WHERE id=?',(status,json.dumps(payload),VERSION));c.commit();c.close();worker_lock.release()
            threading.Thread(target=worker,daemon=True,name='fixed-funding-study').start()
            return {'id':VERSION,'status':'REGISTERED','promotion_allowed':False}
        except Exception:
            if worker_lock.locked():worker_lock.release()
            raise
    return {'overview':get}
