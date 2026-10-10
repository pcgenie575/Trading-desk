"""Registered sensitivity assumptions, never a replacement for operational costs."""
from dataclasses import asdict, replace
from execution import COSTS, fill
from cost_diagnostics import matched_reprice, metrics
from research_engine import ENTRIES, EXITS, simulate, fingerprint

VERSION='cost-diagnostic-v2'
SCENARIOS={
    'current_35bps': COSTS,
    'stock_per_trade_fx': replace(COSTS,version='scenario-stock-50bps-v1',fx_bps=50),
    'stock_fx_10bps': replace(COSTS,version='scenario-stock-10bps-v1',fx_bps=10),
    'stock_usd_balance': replace(COSTS,version='scenario-stock-usd-v1',fx_bps=0),
    'etf_per_trade_fx': replace(COSTS,version='scenario-etf-50bps-v1',fee_per_order=0,fx_bps=50),
    'etf_usd_balance': replace(COSTS,version='scenario-etf-usd-v1',fee_per_order=0,fx_bps=0),
    'zero_all_costs': replace(COSTS,version='scenario-gross-v1',half_spread_bps=0,slippage_bps=0,fee_per_order=0,fx_bps=0),
}
PROTOCOL={'version':VERSION,'scenarios':{k:asdict(v) for k,v in SCENARIOS.items()},
    'variants':[{'entry':e,'exit':x} for e in ENTRIES for x in EXITS],
    'selection':'None; fixed-path cost attribution and resized sensitivity only.',
    'calculations':112,'test_period_reused':True,'live_costs_unchanged':True,
    'fee_status':'Unconfirmed sensitivity assumptions, not an account-specific tariff.',
    'fx_status':'50 bps is a sensitivity value. Webull describes an exchange-rate spread; do not treat pips as a universal percentage.',
    'asx_status':'Not run: no validated ASX dataset or ASX-specific spread/order/currency settings.',
    'usd_balance_status':'Zero per-trade FX excludes separate funding/repatriation conversion costs and currency returns.',
    'statistical_status':'Eight reused strategy configurations, seven cost scenarios, two calculation methods. These 112 calculations are not 112 independent strategies.',
    'promotion_allowed':False}

def attributed_metrics(trades,bars,cost):
    result=matched_reprice(trades,bars,cost)
    gross=matched_reprice(trades,bars,SCENARIOS['zero_all_costs'])
    result['gross_expectancy_r']=gross['expectancy_r']
    result['cost_per_trade_r']=(gross['expectancy_r']-result['expectancy_r']) if trades else None
    result['risk_denominator']='Original cost-adjusted planned loss for each fixed-path trade.'
    return result

def diagnose(symbol,bars,split):
    variants=[]
    for entry in ENTRIES:
        for exit_style in EXITS:
            baseline=simulate(bars,split,entry,exit_style)
            scenarios={}
            for name,cost in SCENARIOS.items():
                replay=simulate(bars,split,entry,exit_style,cost)
                m=metrics(replay['trade_log'])
                m['cost_per_trade_r']=sum(t['costs']/t['risk'] for t in replay['trade_log'])/m['trades'] if m['trades'] else None
                m['gross_expectancy_r']=sum((t['pnl']+t['costs'])/t['risk'] for t in replay['trade_log'])/m['trades'] if m['trades'] else None
                scenarios[name]={'cost_model':asdict(cost),'matched_trade_path':attributed_metrics(baseline['trade_log'],bars,cost),
                    'resized_simulation':dict(m,max_drawdown=replay['max_drawdown'],time_invested_pct=replay['time_invested_pct'])}
            variants.append({'entry':entry,'exit':exit_style,'scenarios':scenarios})
    examples={}
    for name,cost in SCENARIOS.items():
        amount=fill(100,5,'buy',cost)['cash']-fill(100,5,'sell',cost)['cash']
        examples[name]={'raw_notional':500,'round_trip_cost':amount,'cost_in_25_dollar_risk':amount/25}
    return {'version':VERSION,'symbol':symbol,'dataset_hash':fingerprint(symbol,bars),'bars':len(bars),
        'start':bars[0]['datetime'],'end':bars[-1]['datetime'],'split_index':split,'test_start':bars[split]['datetime'],
        'variants':variants,'examples':examples,'period_reused':True,'edge_validated':False,'promotion_allowed':False,
        'trial_disclosure':PROTOCOL['statistical_status'],
        'limitations':['Existing SPY survivor, short four-hour history, small trade count and inspected period; no independent validation.',
            'Gross means no simulated execution costs on the same fills, not a newly traded signal.',
            'Dividends, investor tax, funding conversion, currency returns and regulatory fees are omitted.',
            'Resizing can change target levels, order counts and paths; it does not isolate costs.',
            'ASX and new allocation strategies were not tested. No production rule or risk cap was changed.']}
