"""Frozen daily-engine replica with reduction-only entry volatility caps.

Daily mode must remain exactly equal to the original portfolio engine in parity
tests. Original engine and existing funding-study source are not edited.
"""
import math,statistics
from collections import Counter
from execution import COSTS,fill,sized_entry
from daily_research import context,validate_daily
from risk_policy import assess
from excursions import initial,observe,report
from cost_diagnostics import metrics
from portfolio_research import RULES,PROTOCOL

def risk_scale(closes):
    """Twenty simple completed returns; no later prices or upward sizing."""
    if len(closes)<21 or any(not math.isfinite(x) or x<=0 for x in closes[-21:]):return None
    returns=[b/a-1 for a,b in zip(closes[-21:-1],closes[-20:])]
    vol=statistics.stdev(returns)*math.sqrt(252)
    return min(1.,.15/vol) if vol else 1.

def simulate(dataset,costs=COSTS,*,volatility_cap=False,initial_cash=5000.):
    exit_buffer_pct=0.
    import math
    if not math.isfinite(exit_buffer_pct) or not 0<=exit_buffer_pct<=.01:raise ValueError('Exit buffer outside registered diagnostic bounds.')
    if not math.isfinite(initial_cash) or not 0<initial_cash<=5000:raise ValueError('Invalid initial diagnostic cash.')
    symbols=PROTOCOL['symbols'];start=PROTOCOL['start'];end=PROTOCOL['end']
    data={s:[b for b in dataset[s] if b['datetime']<=end] for s in symbols}
    for bars in data.values():validate_daily(bars,end=end)
    fs,_,nextday=context(data);by={s:{b['datetime']:b for b in bars} for s,bars in data.items()}
    cash=initial_cash;peak=cash;equity=cash;frozen=False;freeze=None;dd=0.
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
            f=sized_entry(b['open'],p['stop'],cash,costs=costs,**({'max_value':500*p['scale'],'max_risk':25*p['scale'],'max_qty':p['max_qty']} if volatility_cap else {}))
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
                if feat['ma'][v['exit_ma']] is not None and b['close']<feat['ma'][v['exit_ma']]*(1-exit_buffer_pct):pending[s]={'side':'sell','day':day}
            elif not missing and i>=max(v['trend'],v['breakout']):
                if b['close']>feat['ma'][v['trend']] and b['close']>max(x['high'] for x in data[s][i-v['breakout']:i]):
                    scale=risk_scale([x['close'] for x in data[s][:i+1]]) if volatility_cap else 1.
                    if scale is None:blocked['VOLATILITY_INPUT']+=1;continue
                    stop=b['close']*.95;f=sized_entry(b['close'],stop,cash,costs=costs,**({'max_value':500*scale,'max_risk':25*scale} if volatility_cap else {}))
                    if f and check(s,f,day,'QUEUE'):pending[s]={'side':'buy','day':day,'stop':stop,'scale':scale,'max_qty':f['qty']}
    # Do not liquidate at a stale last close when the final session is missing.
    for s in list(active):
        b=by[s].get(curve[-1]['day']) if curve else None
        if b:sell(s,b['close'],b,'END_OF_RESEARCH')
    final_day=curve[-1]['day'] if curve else None
    if final_day:mark(final_day,'TERMINAL')
    return dict(metrics(trades),ending_equity=equity,net_equity_change=equity-initial_cash,max_drawdown=dd,freeze=freeze,
                time_invested_pct=100*invested/days if days else None,remaining_unliquidated_symbols=list(active),
                blocked_checks=dict(blocked),trade_log=trades,risk_decisions=decisions,equity_curve=curve)
