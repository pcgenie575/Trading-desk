"""Corporate-action-aware, shared-account ETF development experiment."""
from collections import Counter
from execution import COSTS,fill,sized_entry
from daily_research import STRESS,digest
from corporate_actions import signal_features,split_position
from etf_protocol import PROTOCOL,SYMBOLS,RULES,INSTRUMENTS,SECTORS,GROUPS
from excursions import initial,observe,report
from risk_policy import assess
from cost_diagnostics import metrics

def simulate(data,costs=COSTS,passive=False):
    start=PROTOCOL['development_start'];end=PROTOCOL['development_end']
    bars={s:{b['datetime']:b for b in data[s]['raw']} for s in SYMBOLS}
    features={s:signal_features(data[s]['raw'],data[s]['events']) for s in SYMBOLS}
    days=[d for d in data['reference'] if start<=d<=end];nextday={a:b for a,b in zip(days,days[1:])}
    splits={s:{e['effective_date']:e['new_per_old'] for e in data[s]['events'] if e['type']=='split'} for s in SYMBOLS}
    distributions={s:{} for s in SYMBOLS}
    for s in SYMBOLS:
        for e in data[s]['events']:
            if e['type']=='distribution':distributions[s].setdefault(e['ex_date'],[]).append(e)
    cash=5000.;equity=5000.;peak=5000.;dd=0.;frozen=False;freeze=None
    active={};pending={};marks={};receivables=[];trades=[];decisions=[];curve=[];blocked=Counter();cashflows=[];invested=0;daily=0.
    def mark(day,phase):
        nonlocal equity,peak,dd,frozen,freeze
        equity=cash+sum(p['qty']*marks[s] for s,p in active.items())+sum(e['amount'] for e in receivables)
        peak=max(peak,equity);dd=max(dd,peak-equity)
        if not passive and peak-equity>=250 and not frozen:frozen=True;freeze={'day':day,'phase':phase,'reason':'DRAWDOWN'}
    def sell(s,raw,b,reason,stop=None):
        nonlocal cash,daily,frozen,freeze
        p=active.pop(s);p['excursion']=observe(p['excursion'],b if stop is not None else dict(b,open=raw,low=raw,high=raw),stop)
        f=fill(raw,p['qty'],'sell',costs);cash+=f['cash'];pnl=f['cash']-p['position_value']+p['income'];daily+=pnl
        trades.append(dict(symbol=s,entry_time=p['time'],exit_time=b['datetime'],pnl=pnl,r=pnl/p['planned_loss'],risk=p['planned_loss'],
                           costs=p['costs']+f['total_cost'],reason=reason,distributions_earned=p['income'],excursions=report(p['excursion']),loss_exceeded_plan=pnl < -p['planned_loss']-1e-6))
        if not passive and daily<=-75 and not frozen:frozen=True;freeze={'day':b['datetime'],'phase':'EXIT','reason':'DAILY_LOSS'}
        mark(b['datetime'],'EXIT')
    def check(s,f,day,phase,prior):
        c=dict(quantity=f['qty'],entry_reference=f['price'],stop=f['stop'],position_value=f['qty']*f['price'],planned_loss=f['qty']*(f['price']-f['stop']),cash_cost=f['cash'],cost_adjusted_risk=f['planned_loss'])
        asof=day if phase=='QUEUE' else prior
        series={t:features[t].get(asof,{}).get('series',{}) for t in {s,*active}}
        r=assess(c,s,dict(cash=cash,equity=equity,peak_equity=peak,frozen=frozen),list(active.values()),daily,series,RULES,
                 instruments=INSTRUMENTS,sectors=SECTORS,groups=GROUPS,equity_groups={'US equity','International equity'})
        failed=[x['code'] for x in r['checks'] if x['status']=='FAIL'];decisions.append(dict(day=day,symbol=s,phase=phase,approved=r['approved'],failed_checks=failed))
        if failed:blocked[failed[0]]+=1
        return r['approved']
    for index,day in enumerate(days):
        daily=0.;today={s:bars[s].get(day) for s in SYMBOLS};prior=days[index-1] if index else None;invested_today=bool(active)
        # Quantities held overnight qualify, including positions exiting at today's open.
        for s in SYMBOLS:
            ratio=splits[s].get(day,1)
            if ratio!=1:
                if s in active:active[s]=split_position(active[s],ratio);marks[s]/=ratio
                if s in pending and 'stop' in pending[s]:pending[s]['stop']/=ratio
            for event in distributions[s].get(day,[]):
                amount=event['amount']
                if s in active:
                    value=active[s]['qty']*amount;active[s]['income']+=value;active[s]['stop']-=amount
                    receivables.append(dict(symbol=s,ex_date=day,pay_date=event['pay_date'],amount=value));cashflows.append(dict(kind='ENTITLEMENT',symbol=s,day=day,amount=value,pay_date=event['pay_date']))
                if s in pending and 'stop' in pending[s]:pending[s]['stop']-=amount
        payable=[e for e in receivables if e['pay_date']<=day]
        for e in payable:cash+=e['amount'];cashflows.append(dict(kind='PAYMENT',symbol=e['symbol'],day=day,amount=e['amount']))
        receivables=[e for e in receivables if e['pay_date']>day]
        missing=any(today[s] is None for s in active)
        for s in active:
            if today[s]:marks[s]=today[s]['open']
        mark(day,'OPEN')
        if not passive:
            for s in list(active):
                b=today[s]
                if b and b['open']<=active[s]['stop']:sell(s,b['open'],b,'OPENING_GAP_STOP',active[s]['stop']);pending.pop(s,None)
        orders=pending;pending={}
        for s in SYMBOLS:
            p=orders.get(s);b=today[s]
            if not p:continue
            if not b or nextday.get(p['day'])!=day:blocked['MISSING_NEXT_SESSION']+=1;continue
            if p['side']=='sell' and s in active:sell(s,b['open'],b,'DAILY_EXIT')
        for s in SYMBOLS:
            b=today[s];p=orders.get(s)
            if passive:
                if index!=0 or not b:continue
                f=sized_entry(b['open'],b['open']*.5,cash,max_value=300,max_risk=300,costs=costs)
            else:
                if not p or p['side']!='buy' or not b or nextday.get(p['day'])!=day:continue
                if missing:blocked['MISSING_HELD_DATA']+=1;continue
                if p['stop']<=0:blocked['ACTION_INVALIDATED_STOP']+=1;continue
                f=sized_entry(b['open'],p['stop'],cash,costs=costs)
            if not f:blocked['INVALID_FILL']+=1;continue
            if passive or check(s,f,day,'FILL',prior):
                cash-=f['cash'];marks[s]=b['open'];invested_today=True
                active[s]=dict(symbol=s,qty=f['qty'],stop=f['stop'],position_value=f['cash'],planned_loss=f['planned_loss'],costs=f['total_cost'],time=day,income=0.,excursion=initial(b['open'],f['qty'],f['planned_loss']))
                mark(day,'ENTRY')
        for s in list(active):
            b=today[s];p=active[s]
            if not b:continue
            if not passive and b['low']<=p['stop']:sell(s,p['stop'],b,'PROTECTIVE_STOP',p['stop'])
            else:p['excursion']=observe(p['excursion'],b)
        for s in active:
            if today[s]:marks[s]=today[s]['close']
        if invested_today:invested+=1
        mark(day,'CLOSE');curve.append(dict(day=day,equity=equity,peak=peak,drawdown=peak-equity,open_positions=len(active),cash=cash,receivables=sum(e['amount'] for e in receivables),frozen=frozen))
        if passive:continue
        for s in SYMBOLS:
            b=today[s]
            if not b:continue
            feat=features[s][day]
            if s in active:
                if feat['exit_ma'] is not None and b['close']<feat['exit_ma']:pending[s]=dict(side='sell',day=day)
            elif not missing and feat['trend'] is not None and feat['prior_high'] is not None and b['close']>feat['trend'] and b['close']>feat['prior_high']:
                f=sized_entry(b['close'],b['close']*.95,cash,costs=costs)
                if f and check(s,f,day,'QUEUE',prior):pending[s]=dict(side='buy',day=day,stop=b['close']*.95)
    for s in list(active):
        b=bars[s].get(end)
        if b:sell(s,b['close'],b,'END_OF_RESEARCH')
    mark(end,'TERMINAL')
    return dict(metrics(trades),ending_equity=equity,ending_cash=cash,net_equity_change=equity-5000,max_drawdown=dd,freeze=freeze,
                trade_log=trades,equity_curve=curve,risk_decisions=decisions,blocked_checks=dict(blocked),cashflows=cashflows,
                distributions_earned=sum(t['distributions_earned'] for t in trades)+sum(p['income'] for p in active.values()),
                outstanding_receivables=receivables,time_invested_pct=100*invested/len(days) if days else None,remaining_unliquidated_symbols=list(active))

def evidence_report(result):
    checks=result['input_checks'];bad={s:x['issues'] for s,x in checks.items() if not x['passed']}
    if bad:return {'verdict':'INVESTIGATE','recommendation':'Resolve input coverage and corporate-action discrepancies before performance testing.',
                   'data_failures':bad,'sample_size':0,'performance_available':False,'lessons':[{'agent':'Market Data','lesson':'Missing or unreconciled events block trusted portfolio results.'}],'activation_allowed':False}
    stress=result['stress'];m=stress['expectancy_r'];gates=result['development_checks']
    verdict='REJECT' if m is not None and m<=0 else ('ELIGIBLE_FOR_FURTHER_VALIDATION' if all(gates.values()) else 'CONTINUE_COLLECTING')
    by_symbol={s:metrics([t for t in stress['trade_log'] if t['symbol']==s]) for s in SYMBOLS}
    excursions={s:{'trades':len(ts),'mean_mae_r':sum(t['excursions']['mae_r'] for t in ts)/len(ts) if ts else None,
                   'mean_mfe_r':sum(t['excursions']['mfe_r'] for t in ts)/len(ts) if ts else None,
                   'uncertain_stop_bars':sum(t['excursions']['exit_order_uncertain'] for t in ts)} for s in SYMBOLS for ts in [[t for t in stress['trade_log'] if t['symbol']==s]]}
    return {'verdict':verdict,'recommendation':'Do not promote; keep the recorded protocol and investigate the evidence.' if verdict=='REJECT' else 'No activation. Obtain more independent evidence or register fixed validation only when every gate passes.',
            'sample_size':stress['trades'],'expectancy_after_double_costs_r':m,'max_drawdown':stress['max_drawdown'],'rule_adherence':{'source':'Shared deterministic queue/fill gates','rejected_orders':sum(not x['approved'] for x in stress['risk_decisions']),'manual_rule_breaks':'Not applicable in this deterministic simulation.'},
            'development_checks':gates,'by_market':by_symbol,'excursions':excursions,'data_failures':{},'performance_available':True,
            'lessons':[{'agent':'Risk & Compliance','lesson':'Diversification is measured through overlap/correlation limits, not symbol count.'},
                       {'agent':'Paper Trader','lesson':'Distribution entitlement and cash payment occur on different dates; settled cash alone funds entries.'},
                       {'agent':'Performance Reviewer','lesson':'MAE/MFE describes observed trade paths; it does not authorise stop tuning or strategy activation.'}],
            'webull_au_eligibility':'Unverified per symbol; future activation gate remains closed.','activation_allowed':False}

def run(data,checks):
    checks={s:checks.get(s,{'passed':False,'issues':['INPUT_CHECK_MISSING']}) for s in SYMBOLS}
    result={'protocol':PROTOCOL,'input_hash':digest(data),'input_checks':checks,'historical_validation':None,'forward_paper_eligible':False}
    if not all(x['passed'] for x in checks.values()) or set(checks)!=set(SYMBOLS):
        result.update(normal=None,stress=None,development_checks={},data_blocked=True);result['agent_report']=evidence_report(result);return result
    normal=simulate(data,COSTS);stress=simulate(data,STRESS);base={'normal':simulate(data,COSTS,True),'stress':simulate(data,STRESS,True)}
    gates={'trades_100':stress['trades']>=100,'stress_expectancy_015R':stress['expectancy_r'] is not None and stress['expectancy_r']>=.15,
           'profit_factor_13':stress['profit_factor_no_losses'] or (stress['profit_factor'] is not None and stress['profit_factor']>=1.3),
           'best_two_share':stress['positive_profit_top_two_share'] is not None and stress['positive_profit_top_two_share']<=.35,
           'positive_excluding_best_two':stress['pnl_excluding_best_two']>0,'better_drawdown_than_basket':stress['max_drawdown']<base['stress']['max_drawdown'],
           'all_input_checks':True,'no_remaining_positions':not stress['remaining_unliquidated_symbols']}
    result.update(normal=normal,stress=stress,benchmark=base,development_checks=gates,data_blocked=False);result['agent_report']=evidence_report(result);return result
