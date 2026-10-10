"""Cost-only sensitivity: preserve the frozen v1 protocol and distinguish path effects."""
from dataclasses import asdict,replace
from execution import COSTS,fill
from research_engine import ENTRIES,EXITS,simulate,fingerprint

SCENARIOS={'current_35bps':COSTS,'fx_0bps':replace(COSTS,fx_bps=0),'fx_10bps':replace(COSTS,fx_bps=10),
 'zero_all_costs':replace(COSTS,half_spread_bps=0,slippage_bps=0,fee_per_order=0,fx_bps=0),
 'double_all_costs':replace(COSTS,half_spread_bps=10,slippage_bps=4,fee_per_order=2,fx_bps=70)}

def metrics(trades):
    n=len(trades);pnl=sum(t['pnl'] for t in trades);wins=sum(max(t['pnl'],0) for t in trades);losses=-sum(min(t['pnl'],0) for t in trades)
    ordered=sorted(trades,key=lambda t:t['pnl'],reverse=True);rest=ordered[2:]
    return {'trades':n,'net_pnl':pnl,'expectancy_r':sum(t['r'] for t in trades)/n if n else None,
      'profit_factor':wins/losses if losses else None,'profit_factor_no_losses':bool(n and wins and not losses),
      'positive_profit_top_two_share':sum(max(t['pnl'],0) for t in ordered[:2])/wins if wins else None,
      'pnl_excluding_best_two':sum(t['pnl'] for t in rest),'expectancy_r_excluding_best_two':sum(t['r'] for t in rest)/len(rest) if rest else None,
      'estimated_costs':sum(t.get('costs',0) for t in trades)}

def matched_reprice(trades,bars,cost_model):
    """Same actual entry quantities, exit times and target prices; original R denominator."""
    opening={b['datetime']:b['open'] for b in bars};out=[]
    for trade in trades:
        qty=sum(e['qty'] for e in trade['exits']);buy=fill(opening[trade['entry_time']],qty,'buy',cost_model)
        sells=[fill(e['price']/(1-(COSTS.half_spread_bps+COSTS.slippage_bps)/10000),e['qty'],'sell',cost_model) for e in trade['exits']]
        pnl=sum(f['cash'] for f in sells)-buy['cash'];risk=trade.get('risk') or (trade['pnl']/trade['r'] if trade['r'] else None)
        # For a zero-P/L trade the original cost-adjusted risk cannot be reconstructed.
        if risk is None:raise ValueError('Original risk denominator unavailable for zero-R trade.')
        out.append({'pnl':pnl,'r':pnl/risk,'costs':buy['total_cost']+sum(f['total_cost'] for f in sells)})
    return metrics(out)

def diagnose(symbol,bars,split):
    variants=[]
    for entry in ENTRIES:
        for exit_style in EXITS:
            baseline=simulate(bars,split,entry,exit_style)
            scenarios={}
            for name,cost in SCENARIOS.items():
                replay=simulate(bars,split,entry,exit_style,cost)
                scenarios[name]={'cost_model':asdict(cost),'resized_simulation':dict(metrics(replay['trade_log']),max_drawdown=replay['max_drawdown'],time_invested_pct=replay['time_invested_pct']),
                  'matched_trade_path':matched_reprice(baseline['trade_log'],bars,cost)}
            gross=scenarios['zero_all_costs']['matched_trade_path']['expectancy_r']
            current=scenarios['current_35bps']['matched_trade_path']['expectancy_r']
            verdict='insufficient_trades' if gross is None else 'signal_lost_before_costs' if gross<=0 else 'costs_erased_gross_gain' if current<=0 else 'positive_in_reused_sample_only'
            variants.append({'entry':entry,'exit':exit_style,'verdict':verdict,'scenarios':scenarios})
    raw=500;buy=fill(100,5,'buy');sell=fill(100,5,'sell')
    return {'version':'cost-diagnostic-v1','symbol':symbol,'dataset_hash':fingerprint(symbol,bars),'bars':len(bars),'start':bars[0]['datetime'],'end':bars[-1]['datetime'],
      'test_start':bars[split]['datetime'],'split_index':split,'variants':variants,'example_round_trip':{'raw_notional':raw,'cost':buy['cash']-sell['cash'],'fraction_of_25_dollar_risk':(buy['cash']-sell['cash'])/25},
      'period_reused':True,'edge_validated':False,'limitations':['These are cost diagnostics on a previously inspected historical period, not a new holdout.',
       'FX zero removes the per-trade allowance; it excludes funding/repatriation and actual AUD/USD returns.',
       'Resized simulations can change quantities, partial targets and trade paths. Matched repricing preserves paths and original cost-adjusted R denominators.',
       'Terminal research liquidations are included; no production strategy or cost model changes.']}

