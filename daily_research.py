"""Predeclared daily research. No strategy activation and no parameter search."""
from datetime import date,datetime,timedelta
from dataclasses import asdict,replace
import hashlib,json,math
from execution import COSTS,fill,sized_entry
from cost_diagnostics import metrics

VERSION='daily-edge-v1'
DEVELOPMENT=('SPY','QQQ','IWM','DIA')
VALIDATION=('AAPL','MSFT','AMZN','NVDA','GOOGL','META','TSLA','AMD','JPM','XOM','GLD','TLT','F','INTC','IBM','CSCO')
SYMBOLS=DEVELOPMENT+VALIDATION
VARIANTS=[dict(id='daily_100_20_50',trend=100,breakout=20,exit_ma=50),
 dict(id='daily_200_55_100',trend=200,breakout=55,exit_ma=100),
 dict(id='spy_regime',trend=100,breakout=20,exit_ma=50,regime=True),
 dict(id='atr_stop',trend=100,breakout=20,exit_ma=50,atr_stop=2.5),
 dict(id='atr_trailing',trend=100,breakout=20,exit_ma=50,atr_trailing=3),
 dict(id='relative_strength',trend=100,breakout=20,exit_ma=50,relative_strength=True)]
NEIGHBOURS=[dict(id='neighbour_90_18_45',trend=90,breakout=18,exit_ma=45),dict(id='neighbour_110_22_55',trend=110,breakout=22,exit_ma=55)]
STRESS=replace(COSTS,half_spread_bps=10,slippage_bps=4,fee_per_order=2,fx_bps=70)
PROTOCOL={'version':VERSION,'interval':'1day','development_start':'2006-01-01','development_end':'2015-12-31','validation_start':'2016-01-01','validation_end':'2026-10-09',
 'development_symbols':DEVELOPMENT,'validation_symbols':VALIDATION,'variants':VARIANTS,'baseline_neighbours':NEIGHBOURS,'costs':asdict(COSTS),'stress_costs':asdict(STRESS),
 'selection':'Choose one of six variants using development data only: positive pooled net R under 2x costs, then highest pooled R; tie by declared order. Neighbours never eligible for selection.',
 'holdout_policy':'Only the selected candidate gets one recorded historical validation across development and separate validation symbols. Do not replace a failing candidate or revise this protocol using these results.',
 'promotion':{'min_trades':100,'min_stress_expectancy_r':.15,'min_stress_profit_factor':1.3,'max_top_two_share_of_positive_profit':.35,'positive_net_pnl_without_best_two':True,'better_drawdown_than_same_exposure_passive':True,'positive_on_validation_symbols':True,'neighbour_baseline_stress_positive':True},
 'fill_rule':'Signal at completed daily close; first subsequent observed session open. Skip entry/queued exit if the next SPY session is missing. Protective stop gaps use the opening price; low-before-target conservative assumption.',
 'atr':'Simple mean of 14 true ranges through completed signal day (not Wilder smoothing). ATR trail advances at close for next session; MA exit replaced for trailing variant.',
 'relative_strength':'Top quartile of all eligible symbols with 253 prior daily closes; score is mean of trailing 126- and 252-session price returns, computed on signal date only. At least 12 eligible symbols required.',
 'risk':'Independent $5000/$500/$25 single-symbol sleeves; no portfolio simulation. Fixed 5% stop unless ATR-stop variant; v1 production untouched.',
 'limitations':['Retrospective 2016–2026 validation is not provably untouched. Universe selected today contains survivorship and hindsight bias, even with four additional names.',
 'Split-adjusted price-only data; no dividends, verified corporate-action events, delisted universe, taxes, funding FX or actual currency returns.',
 'Independent sleeves must not be mistaken for one deployable portfolio; overlapping trades and correlations require a later portfolio test.',
 'Passing numeric screens only creates a research candidate; genuine future paper validation and explicit activation review remain required.']}

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def validate_daily(bars,start='2006-01-01',end='2026-10-09'):
    if not bars or len(bars)>6000:raise ValueError('Daily page must contain 1–6000 observations.')
    previous=''
    for b in bars:
        stamp=b['datetime'];d=date.fromisoformat(stamp)
        if len(stamp)!=10 or stamp<=previous or not start<=stamp<=end or d.weekday()>4:raise ValueError('Invalid, duplicate, off-weekday or out-of-range daily date.')
        previous=stamp
        if not all(math.isfinite(b[k]) and 0<b[k]<=1e9 for k in ('open','high','low','close')):raise ValueError('Invalid daily price.')
        if not b['low']<=min(b['open'],b['close'])<=max(b['open'],b['close'])<=b['high']:raise ValueError('Invalid daily OHLC range.')
        if not math.isfinite(b.get('volume',0)) or b.get('volume',0)<0:raise ValueError('Invalid daily volume.')
    return bars

def features(bars):
    closes=[];tr=[];out={}
    periods={200}|{v['trend'] for v in VARIANTS+NEIGHBOURS}|{v['exit_ma'] for v in VARIANTS+NEIGHBOURS}
    for i,b in enumerate(bars):
        prev=closes[-1] if closes else b['close'];closes.append(b['close'])
        tr.append(max(b['high']-b['low'],abs(b['high']-prev),abs(b['low']-prev)))
        out[b['datetime']]={'index':i,'close':b['close'],'atr':sum(tr[-14:])/14 if i>=13 else None,
          'ma':{n:sum(closes[-n:])/n if len(closes)>=n else None for n in periods},
          'momentum':((closes[-1]/closes[-127]-1)+(closes[-1]/closes[-253]-1))/2 if i>=252 else None}
    return out

def context(dataset):
    fs={s:features(b) for s,b in dataset.items()};rs={}
    for day in fs.get('SPY',{}):
        eligible=[(s,f[day]['momentum']) for s,f in fs.items() if day in f and f[day]['momentum'] is not None]
        if len(eligible)>=12:
            ranked=sorted(eligible,key=lambda x:(-x[1],x[0]));rs[day]={s for s,_ in ranked[:math.ceil(len(ranked)/4)]}
    dates=list(fs.get('SPY',{}));nextday={a:b for a,b in zip(dates,dates[1:])}
    return fs,rs,nextday

def simulate_daily(symbol,bars,variant,start,end,cost_model,ctx):
    fs,rs,nextday=ctx;cash=5000.;pos=None;pending=None;trades=[];peak=cash;dd=0.;invested=0;observations=0;skipped=0
    def sell(raw,bar,reason):
        nonlocal cash,pos
        f=fill(raw,pos['qty'],'sell',cost_model);cash+=f['cash'];pnl=f['cash']-pos['cost']
        trades.append({'symbol':symbol,'entry_time':pos['time'],'exit_time':bar['datetime'],'pnl':pnl,'r':pnl/pos['risk'],'risk':pos['risk'],'costs':pos['costs']+f['total_cost'],'reason':reason});pos=None
    for i,b in enumerate(bars):
        day=b['datetime']
        if day<start:continue
        if day>end:break
        observations+=1;feat=fs[symbol][day]
        if pending:
            p=pending;pending=None
            if nextday.get(p['day'])!=day:skipped+=1
            elif p['side']=='sell' and pos:sell(b['open'],b,'DAILY_EXIT')
            elif p['side']=='buy' and not pos:
                f=sized_entry(b['open'],p['stop'],cash,costs=cost_model)
                if f:
                    cash-=f['cash'];pos={'qty':f['qty'],'stop':p['stop'],'cost':f['cash'],'risk':f['planned_loss'],'costs':f['total_cost'],'time':day}
        if pos:
            invested+=1
            if b['low']<=pos['stop']:sell(min(b['open'],pos['stop']),b,'PROTECTIVE_STOP')
            if pos:
                if variant.get('atr_trailing'):
                    pos['stop']=max(pos['stop'],b['close']-variant['atr_trailing']*feat['atr'])
                elif feat['ma'][variant['exit_ma']] is not None and b['close']<feat['ma'][variant['exit_ma']]:pending={'side':'sell','day':day}
        if not pos and not pending and i>=max(variant['trend'],variant['breakout']):
            trend=feat['ma'][variant['trend']]
            good=b['close']>trend and b['close']>max(x['high'] for x in bars[i-variant['breakout']:i])
            if variant.get('regime'):
                spy=fs['SPY'].get(day);spybar=ctx_spy_close(ctx,day) if spy else 0
                good=good and spy is not None and spy['ma'][200] is not None and spybar>spy['ma'][200]
            if variant.get('relative_strength'):good=good and symbol in rs.get(day,set())
            if good:
                stop=b['close']-variant['atr_stop']*feat['atr'] if variant.get('atr_stop') else b['close']*.95
                if stop>0:pending={'side':'buy','day':day,'stop':stop}
        equity=cash+(pos['qty']*b['close'] if pos else 0);peak=max(peak,equity);dd=max(dd,peak-equity)
    terminal=[b for b in bars if start<=b['datetime']<=end]
    if pos and terminal:sell(terminal[-1]['close'],terminal[-1],'END_OF_RESEARCH')
    dd=max(dd,peak-cash)
    return dict(metrics(trades),max_drawdown=dd,time_invested_pct=invested/observations*100 if observations else None,skipped_missing_next_sessions=skipped,trade_log=trades)

def ctx_spy_close(ctx,day):return ctx[0]['SPY'][day]['close']

def passive(bars,start,end,cost_model):
    b=[x for x in bars if start<=x['datetime']<=end]
    if not b:return None
    buy=fill(b[0]['open'],1,'buy',cost_model);qty=(500-cost_model.fee_per_order)/(buy['price']*(1+cost_model.fx_bps/10000))
    buy=fill(b[0]['open'],qty,'buy',cost_model);cash=5000-buy['cash'];peak=5000;dd=0
    for bar in b:
        eq=cash+qty*bar['close'];peak=max(peak,eq);dd=max(dd,peak-eq)
    final=cash+fill(b[-1]['close'],qty,'sell',cost_model)['cash'];dd=max(dd,peak-final)
    return {'net_pnl':final-5000,'max_drawdown':dd,'price_only':True,'exposure':500}

def summarize(dataset,variant,symbols,start,end,cost,ctx):
    results={s:simulate_daily(s,dataset[s],variant,start,end,cost,ctx) for s in symbols};trades=[t for r in results.values() for t in r['trade_log']]
    # Independent sleeves: summed drawdowns is a comparison diagnostic, not portfolio DD.
    return dict(metrics(trades),sum_individual_drawdowns=sum(r['max_drawdown'] for r in results.values()),symbol_results=results)

def run_daily(dataset):
    if set(dataset)!=set(SYMBOLS):raise ValueError('All 20 predeclared symbols must be present; no silent universe replacement.')
    for bars in dataset.values():validate_daily(bars)
    spy_dates={b['datetime'] for b in dataset['SPY']};coverage={}
    for s,bars in dataset.items():
        expected={d for d in spy_dates if bars[0]['datetime']<=d<=bars[-1]['datetime']};actual={b['datetime'] for b in bars}
        coverage[s]={'first':bars[0]['datetime'],'last':bars[-1]['datetime'],'bars':len(bars),'missing_spy_sessions':len(expected-actual),'coverage':len(expected&actual)/len(expected) if expected else 0}
        if actual-spy_dates or coverage[s]['coverage']<.98 or bars[-1]['datetime']!='2026-10-09':raise ValueError('Incomplete or mismatched daily coverage: '+s)
    if dataset['SPY'][0]['datetime']>'2006-01-10' or any(dataset[s][0]['datetime']>'2006-01-10' for s in DEVELOPMENT):raise ValueError('Development history does not reach 2006.')
    if any('2015-12-31' not in {b['datetime'] for b in dataset[s]} for s in DEVELOPMENT):raise ValueError('Development end session missing.')
    ctx=context(dataset)
    for b in dataset['SPY']:ctx[0]['SPY'][b['datetime']]['close']=b['close']
    dev=[]
    for v in VARIANTS+NEIGHBOURS:
        dev.append({'variant':v,'normal':summarize(dataset,v,DEVELOPMENT,'2006-01-01','2015-12-31',COSTS,ctx),'stress':summarize(dataset,v,DEVELOPMENT,'2006-01-01','2015-12-31',STRESS,ctx)})
    eligible=[r for r in dev[:len(VARIANTS)] if (r['stress']['expectancy_r'] or -999)>0]
    winner=max(eligible,key=lambda r:r['stress']['expectancy_r']) if eligible else None
    result={'protocol':PROTOCOL,'dataset_hash':digest(dataset),'coverage':coverage,'development':dev,'selected_candidate':winner['variant']['id'] if winner else None,'historical_validation':None,'numeric_screen_passed':False,'forward_paper_eligible':False,'activation':'Never automatic'}
    if not winner:
        result['decision']='No candidate survived development costs; historical validation not opened.';return result
    v=winner['variant'];normal=summarize(dataset,v,SYMBOLS,'2016-01-01','2026-10-09',COSTS,ctx);stress=summarize(dataset,v,SYMBOLS,'2016-01-01','2026-10-09',STRESS,ctx)
    unseen=[t for s,r in stress['symbol_results'].items() if s in VALIDATION for t in r['trade_log']]
    bases={s:passive(dataset[s],'2016-01-01','2026-10-09',STRESS) for s in SYMBOLS};baseline_dd=sum(x['max_drawdown'] for x in bases.values() if x)
    checks={'trades_100':stress['trades']>=100,'stress_expectancy_015R':stress['expectancy_r'] is not None and stress['expectancy_r']>=.15,
      'stress_profit_factor_13':stress['profit_factor_no_losses'] or (stress['profit_factor'] is not None and stress['profit_factor']>=1.3),
      'top_two_not_dominant':stress['positive_profit_top_two_share'] is not None and stress['positive_profit_top_two_share']<=.35,
      'positive_without_best_two':stress['pnl_excluding_best_two']>0,'better_drawdown':stress['sum_individual_drawdowns']<baseline_dd,
      'validation_symbols_positive':(metrics(unseen)['expectancy_r'] or -999)>0,'baseline_neighbours_positive':all((r['stress']['expectancy_r'] or -999)>0 for r in dev[-2:])}
    result.update(historical_validation={'normal':normal,'stress':stress,'validation_symbols':metrics(unseen),'same_exposure_passive':bases,'promotion_checks':checks},numeric_screen_passed=all(checks.values()),decision='Research screen passed; future and portfolio validation required.' if all(checks.values()) else 'Do not promote; historical validation failed one or more declared screens.')
    return result

