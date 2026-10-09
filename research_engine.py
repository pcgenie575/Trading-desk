"""Fixed research variants; no automatic parameter optimization or activation."""
from dataclasses import asdict
from datetime import datetime,timedelta
import hashlib,json,math
from strategy import signal_from_bars,sma,CONFIG
from execution import COSTS,fill,sized_entry
VERSION='swing-research-v2'
ENTRIES=('breakout','trend_pullback')
EXITS=('full','trailing','time','partial')
PROTOCOL={'version':VERSION,'entries':ENTRIES,'exits':EXITS,'trend_ma':50,'breakout_lookback':10,'pullback_ma':20,'stop_pct':.05,'trailing_pct':.05,'time_bars':10,'partial_target_r':1,'partial_fraction':.5,'costs':asdict(COSTS),'fill_rule':'First opening at least 4h15m after signal timestamp; conservative delayed-feed approximation','selection':'Fixed eight variants; no optimizer, all results retained. Baseline entry/exit stays active in paper.'}

def validate_bars(bars):
    if not 120<=len(bars)<=5000:raise ValueError('Provide 120–5000 ordered 4-hour OHLC bars.')
    previous=None
    for b in bars:
        stamp=datetime.fromisoformat(b['datetime'])
        if stamp.tzinfo is not None:raise ValueError('Use naive America/New_York candle timestamps.')
        if previous is not None and stamp<=previous:raise ValueError('Bars must be unique and strictly chronological.')
        previous=stamp
        if not all(math.isfinite(b[k]) and 1e-8<=b[k]<=1e9 for k in ('open','high','low','close')):raise ValueError('OHLC values must be finite US-instrument prices between 0.00000001 and 1 billion.')
        if not math.isfinite(b.get('volume',0)) or b.get('volume',0)<0:raise ValueError('Volume must be finite and nonnegative.')
        if not b['low']<=min(b['open'],b['close'])<=max(b['open'],b['close'])<=b['high']:raise ValueError('Invalid OHLC range.')
    return bars

def fingerprint(symbol,bars):return hashlib.sha256(json.dumps([symbol,bars],sort_keys=True,separators=(',',':')).encode()).hexdigest()

def entry_signal(window,entry):
    if entry=='breakout':return signal_from_bars(window).get('signal')=='CANDIDATE'
    c=[b['close'] for b in window]
    if len(c)<51:return False
    trend=sma(c,50);prior_trend=sma(c[:-1],50);ma=sma(c,20)
    return c[-1]>trend and trend>prior_trend and window[-2]['low']<=sma(c[:-1],20) and c[-1]>ma and c[-1]>c[-2]

def simulate(bars,start,entry,exit_style):
    cash=5000.;pos=None;pending=None;trades=[];curve=[];peak=cash;dd=0;invested=0;costs=0
    def sell(raw,qty,bar,reason):
        nonlocal cash,pos,costs
        f=fill(raw,qty,'sell');cash+=f['cash'];pos['proceeds']+=f['cash'];pos['costs']+=f['total_cost'];costs+=f['total_cost'];pos['remaining']-=qty
        pos['exits'].append(dict(time=bar['datetime'],qty=qty,price=f['price'],reason=reason,costs=f['total_cost']))
        if pos['remaining']<=1e-9:
            pnl=pos['proceeds']-pos['cost'];trades.append(dict(entry_time=pos['time'],exit_time=bar['datetime'],pnl=pnl,r=pnl/pos['risk'],costs=pos['costs'],exits=pos['exits']));pos=None
    for i in range(start,len(bars)):
        bar=bars[i]
        # Signals are determined on earlier completed candles, filled at this bar's open.
        if pending and datetime.fromisoformat(bar['datetime'])>=datetime.fromisoformat(pending['signal_time'])+timedelta(hours=4,minutes=15):
            action=pending;pending=None
            if action['side']=='sell' and pos:sell(min(bar['open'],pos['stop']) if bar['open']<pos['stop'] else bar['open'],pos['remaining'],bar,action['reason'])
            elif action['side']=='buy' and pos is None:
                f=sized_entry(bar['open'],action['stop'],cash)
                if f:
                    cash-=f['cash'];costs+=f['total_cost'];pos=dict(qty=f['qty'],remaining=f['qty'],stop=action['stop'],price=f['price'],risk=f['planned_loss'],cost=f['cash'],proceeds=0,costs=f['total_cost'],time=bar['datetime'],index=i,partial=False,exits=[])
        if pos:
            invested+=1
            # Stop precedes target when both touched: conservative ambiguous OHLC ordering.
            if bar['low']<=pos['stop']:sell(min(bar['open'],pos['stop']),pos['remaining'],bar,'PROTECTIVE_STOP')
            if pos and exit_style=='partial' and not pos['partial']:
                target=pos['price']+pos['risk']/pos['qty']
                if bar['high']>=target:
                    pos['partial']=True;sell(target,pos['qty']*.5,bar,'PARTIAL_1R')
            if pos:
                below=bar['close']<sma([b['close'] for b in bars[:i+1]],20)
                if below or (exit_style=='time' and i-pos['index']>=10):pending=dict(side='sell',signal_time=bar['datetime'],reason='TIME_EXIT' if exit_style=='time' and i-pos['index']>=10 else 'MA_EXIT')
                if exit_style=='trailing':pos['stop']=max(pos['stop'],bar['close']*.95) # active only next candle
        if pos is None and pending is None and i<len(bars)-1 and entry_signal(bars[:i+1],entry):pending=dict(side='buy',signal_time=bar['datetime'],stop=bar['close']*.95)
        equity=cash+(pos['remaining']*bar['close'] if pos else 0);peak=max(peak,equity);dd=max(dd,peak-equity);curve.append(dict(time=bar['datetime'],equity=equity,peak=peak))
    # Explicit terminal liquidation for comparisons; never used as a live exit rule.
    if pos:sell(bars[-1]['close'],pos['remaining'],bars[-1],'END_OF_RESEARCH')
    if curve:curve[-1]['equity']=cash;peak=max(peak,cash);dd=max(dd,peak-cash);curve[-1]['peak']=peak
    pnl=cash-5000;return dict(entry=entry,exit=exit_style,trades=len(trades),net_pnl=pnl,return_pct=pnl/5000*100,max_drawdown=dd,time_invested_pct=invested/(len(bars)-start)*100,expectancy_r=sum(t['r'] for t in trades)/len(trades) if trades else None,estimated_costs=costs,trade_log=trades,equity_curve=curve)

def benchmark(bars,start,capital):
    first=bars[start]['open'];f=fill(first,(capital-COSTS.fee_per_order)/(first*(1+(COSTS.half_spread_bps+COSTS.slippage_bps)/10000)*(1+COSTS.fx_bps/10000)),'buy');last=fill(bars[-1]['close'],f['qty'],'sell');peak=5000.;dd=0;curve=[]
    for bar in bars[start:]:
        equity=5000-f['cash']+f['qty']*bar['close'];peak=max(peak,equity);dd=max(dd,peak-equity);curve.append(dict(time=bar['datetime'],equity=equity))
    pnl=last['cash']-f['cash'];dd=max(dd,peak-(5000+pnl));curve[-1]['equity']=5000+pnl
    return dict(exposure=capital,net_pnl=pnl,return_pct=pnl/5000*100,max_drawdown=dd,time_invested_pct=100,estimated_costs=f['total_cost']+last['total_cost'],equity_curve=curve,note='Price-only buy-and-hold of the same instrument and dates. No dividends, taxes or FX market returns; estimated round-trip costs applied.')

def compare(bars,split):
    results=[]
    for entry in ENTRIES:
        for exit_style in EXITS:
            development=simulate(bars[:split],50,entry,exit_style);later=simulate(bars,split,entry,exit_style)
            base=benchmark(bars,split,500);later['minus_passive_pnl']=later['net_pnl']-base['net_pnl']
            results.append(dict(development=development,later_period=later))
    return dict(protocol=PROTOCOL,split_time=bars[split]['datetime'],variants=results,benchmark_500=benchmark(bars,split,500),benchmark_full_capital=benchmark(bars,split,5000),edge_validated=False,limitations=['Delayed 4-hour OHLC reconstruction (signal candle +4h15m before eligible opening); no quotes, dividends, taxes, corporate-action validation or intrabar path.','Predeclared variants do not prove an edge. Later data may already be known outside this lab. Reused periods are explicitly labeled.','Single instrument, one position; no portfolio correlation backtest. Partial and alternate exits are research only.'])
