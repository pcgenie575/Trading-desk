"""Development-only daily portfolio replay; never an activation route."""
from collections import Counter
from dataclasses import asdict
from execution import COSTS,fill,sized_entry
from daily_research import STRESS,context,digest,validate_daily,passive
from risk_policy import assess
from excursions import initial,observe,report
from cost_diagnostics import metrics

RULES={'starting_balance':5000.,'max_position':500.,'max_planned_loss':25.,'daily_loss_stop':75.,'drawdown_freeze':250.}
PROTOCOL={'version':'portfolio-development-v1','symbols':['SPY','QQQ','IWM','DIA'],
 'start':'2006-01-01','end':'2015-12-31','variant':{'trend':100,'breakout':20,'exit_ma':50},
 'costs':asdict(COSTS),'stress_costs':asdict(STRESS),'risk_rules':RULES,
 'purpose':'Diagnostic of the already declared daily baseline under shared capital; no candidate selection, holdout calculation or automatic promotion.',
 'ordering':'At each SPY session: mark all available opens, opening-gap/queued exits, entries in declared symbol order, intrabar stops, close marks, close signals. Queue and fill both use shared risk gates. Drawdown or daily-loss freeze persists to research end.',
 'missing_data':'A missing held-symbol bar blocks all new entries for the session; no invented stop fills. Pending orders expire if the next SPY session is missing.',
 'limits':['Daily migration diagnostic, not an exact replay of live 4h scheduler timing, delayed feed, quality quarantine, signed contracts or downtime.',
 'Split-adjusted synthetic price units for both signals and fills; not raw broker cashflows, dividends or corporate-action accounting.',
 'OHLC cannot identify intrabar ordering. Excursions at intrabar stops are lower bounds. Circuit breakers are evaluated at observed opens/closes and exits, not tick by tick.',
 'Deterministic symbol ordering is an assumption. Research end liquidation is synthetic. No taxes or AUD currency returns.']}

def simulate(dataset,costs=COSTS):
    symbols=PROTOCOL['symbols'];start=PROTOCOL['start'];end=PROTOCOL['end']
    data={s:[b for b in dataset[s] if b['datetime']<=end] for s in symbols}
    for bars in data.values():validate_daily(bars,end=end)
    fs,_,nextday=context(data);by={s:{b['datetime']:b for b in bars} for s,bars in data.items()}
    cash=RULES['starting_balance'];peak=cash;equity=cash;frozen=False;freeze=None;dd=0.
    active={};pending={};marks={};trades=[];decisions=[];curve=[];blocked=Counter();invested=0;days=0;daily=0.
    def mark(day,phase):
        nonlocal peak,equity,frozen,freeze,dd
        equity=cash+sum(p['qty']*marks[s] for s,p in active.items());peak=max(peak,equity);dd=max(dd,peak-equity)
        if peak-equity>=RULES['drawdown_freeze'] and not frozen:
            frozen=True;freeze={'day':day,'phase':phase,'reason':'DRAWDOWN'}
    def sell(s,raw,b,reason,stop=None):
        nonlocal cash,daily,frozen,freeze
        p=active.pop(s);p['excursion']=observe(p['excursion'],b if stop is not None else dict(b,open=raw,low=raw,high=raw),stop)
        f=fill(raw,p['qty'],'sell',costs);pnl=f['cash']-p['position_value'];cash+=f['cash'];daily+=pnl
        trades.append({'symbol':s,'entry_time':p['time'],'exit_time':b['datetime'],'pnl':pnl,'r':pnl/p['planned_loss'],'risk':p['planned_loss'],
                       'costs':p['costs']+f['total_cost'],'reason':reason,'excursions':report(p['excursion']),
                       'loss_exceeded_plan':pnl < -p['planned_loss']-1e-6})
        if daily<=-RULES['daily_loss_stop'] and not frozen:frozen=True;freeze={'day':b['datetime'],'phase':'EXIT','reason':'DAILY_LOSS'}
        mark(b['datetime'],'EXIT')
    def check(s,f,day,phase):
        candidate={'quantity':f['qty'],'entry_reference':f['price'],'stop':f['stop'],'position_value':f['qty']*f['price'],
                   'planned_loss':f['qty']*(f['price']-f['stop']),'cash_cost':f['cash'],'cost_adjusted_risk':f['planned_loss']}
        # No current/future closing prices may enter a fill-time correlation check.
        series={t:{b['datetime']:b['close'] for b in data[t] if b['datetime']<day or (phase=='QUEUE' and b['datetime']==day)} for t in {s,*active}}
        series={t:dict(list(v.items())[-100:]) for t,v in series.items()}
        r=assess(candidate,s,{'cash':cash,'equity':equity,'peak_equity':peak,'frozen':frozen},list(active.values()),daily,series,RULES)
        failed=[c['code'] for c in r['checks'] if c['status']=='FAIL']
        decisions.append({'day':day,'symbol':s,'phase':phase,'approved':r['approved'],'failed_checks':failed})
        if failed:blocked[failed[0]]+=1
        return r['approved']
    for day in by['SPY']:
        if day<start:continue
        days+=1;daily=0.;today={s:by[s].get(day) for s in symbols}
        for s,p in active.items():
            if today[s]:marks[s]=today[s]['open']
        mark(day,'OPEN')
        missing=any(today[s] is None for s in active)
        invested_today=bool(active)
        for s in list(active):
            b=today[s]
            if b and b['open']<=active[s]['stop']:
                sell(s,b['open'],b,'OPENING_GAP_STOP',active[s]['stop']);pending.pop(s,None)
        orders=pending;pending={}
        for s in symbols:
            p=orders.get(s);b=today[s]
            if not p:continue
            if not b or nextday.get(p['day'])!=day:blocked['MISSING_NEXT_SESSION']+=1;continue
            if p['side']=='sell' and s in active:sell(s,b['open'],b,'DAILY_EXIT')
        for s in symbols:
            p=orders.get(s);b=today[s]
            if not p or p['side']!='buy' or not b or nextday.get(p['day'])!=day:continue
            if missing:blocked['MISSING_HELD_DATA']+=1;continue
            f=sized_entry(b['open'],p['stop'],cash,costs=costs)
            if not f:blocked['INVALID_FILL']+=1;continue
            if check(s,f,day,'FILL'):
                invested_today=True
                cash-=f['cash'];marks[s]=b['open']
                active[s]={'symbol':s,'qty':f['qty'],'stop':f['stop'],'position_value':f['cash'],'planned_loss':f['planned_loss'],
                           'costs':f['total_cost'],'time':day,'excursion':initial(b['open'],f['qty'],f['planned_loss'])}
                mark(day,'ENTRY')
        for s in list(active):
            b=today[s];p=active[s]
            if not b:continue
            if b['low']<=p['stop']:sell(s,p['stop'],b,'PROTECTIVE_STOP',p['stop'])
            else:p['excursion']=observe(p['excursion'],b)
        for s in active:
            if today[s]:marks[s]=today[s]['close']
        if invested_today:invested+=1
        mark(day,'CLOSE');curve.append({'day':day,'equity':equity,'peak':peak,'drawdown':peak-equity,'open_positions':len(active),'frozen':frozen,
                                      'gross_book_cost':sum(p['position_value'] for p in active.values()),'planned_loss':sum(p['planned_loss'] for p in active.values())})
        for s in symbols:
            b=today[s]
            if not b:continue
            feat=fs[s][day];v=PROTOCOL['variant'];i=feat['index']
            if s in active:
                if feat['ma'][v['exit_ma']] is not None and b['close']<feat['ma'][v['exit_ma']]:pending[s]={'side':'sell','day':day}
            elif not missing and i>=max(v['trend'],v['breakout']):
                if b['close']>feat['ma'][v['trend']] and b['close']>max(x['high'] for x in data[s][i-v['breakout']:i]):
                    stop=b['close']*.95;f=sized_entry(b['close'],stop,cash,costs=costs)
                    if f and check(s,f,day,'QUEUE'):pending[s]={'side':'buy','day':day,'stop':stop}
    # Do not liquidate at a stale last close when the final session is missing.
    for s in list(active):
        b=by[s].get(curve[-1]['day']) if curve else None
        if b:sell(s,b['close'],b,'END_OF_RESEARCH')
    final_day=curve[-1]['day'] if curve else None
    if final_day:mark(final_day,'TERMINAL')
    return dict(metrics(trades),ending_equity=equity,net_equity_change=equity-5000,max_drawdown=dd,freeze=freeze,
                time_invested_pct=100*invested/days if days else None,remaining_unliquidated_symbols=list(active),
                blocked_checks=dict(blocked),trade_log=trades,risk_decisions=decisions,equity_curve=curve)

def run(dataset):
    # Only development prices are accepted into the recorded input hash.
    data={s:[b for b in dataset[s] if PROTOCOL['start']<=b['datetime']<=PROTOCOL['end']] for s in PROTOCOL['symbols']}
    if any(not b or b[0]['datetime']>'2006-01-10' or b[-1]['datetime']!='2015-12-31' for b in data.values()):raise ValueError('Full development history required.')
    return {'protocol':PROTOCOL,'dataset_hash':digest(data),'normal':simulate(data,COSTS),'stress':simulate(data,STRESS),
            'passive_baseline':{'basis':'$500 SPY buy-and-hold in a $5000 account; fixed exposure, not risk/time matched; price-only, no dividends.',
                                'normal':passive(data['SPY'],PROTOCOL['start'],PROTOCOL['end'],COSTS),
                                'stress':passive(data['SPY'],PROTOCOL['start'],PROTOCOL['end'],STRESS)},
            'historical_validation':None,'forward_paper_eligible':False,'decision':'Diagnostic only. Existing negative development result still blocks candidate promotion.'}
