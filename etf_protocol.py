"""One declared universe experiment, frozen before its historical price collection."""
from dataclasses import asdict
from execution import COSTS
from daily_research import STRESS
from corporate_actions import ISSUERS
SYMBOLS=('IWM','IEF','EFA','IAU','GSG')
SECTORS={'IWM':'Broad ETF','IEF':'Treasury','EFA':'International equities','IAU':'Gold','GSG':'Commodities'}
GROUPS={'IWM':'US equity','IEF':'Treasury','EFA':'International equity','IAU':'Gold','GSG':'Commodities'}
INSTRUMENTS={s:{'paper_enabled':True,'research_only':True,'webull_au_eligibility':'UNVERIFIED','currency':'USD','name':ISSUERS[s][1]} for s in SYMBOLS}
RULES={'starting_balance':5000.,'max_position':500.,'max_planned_loss':25.,'daily_loss_stop':75.,'drawdown_freeze':250.}
PROTOCOL={'version':'etf-corporate-actions-v1','symbols':SYMBOLS,'instruments':INSTRUMENTS,'sectors':SECTORS,'groups':GROUPS,
 'warmup_start':'2006-01-01','development_start':'2007-01-03','development_end':'2015-12-31',
 'strategy':{'trend':100,'breakout':20,'exit_ma':50,'stop_pct':.05},'costs':asdict(COSTS),'stress_costs':asdict(STRESS),'risk':RULES,
 'selection':'One universe and one baseline; no search, replacements, neighbouring tuning or second strategy.',
 'universe_reason':'US small caps, intermediate Treasuries, developed international equities, gold and commodity futures. One issuer provides publicly downloadable distribution records. Availability of records, not historical returns, determined this universe.',
 'data':'Raw, split-adjusted and all-adjusted daily prices paired by date/OHLC, reconciled with private full issuer distribution exports. Inferred splits require independent verification before metrics.',
 'signals':'Rebase prior prices only when each split or distribution becomes effective; compute SMA100, previous20 high and SMA50 on that as-of history. Signals at completed close, fills at next reference-session open.',
 'cashflows':'Held-at-prior-close positions receive gross USD distribution entitlement on ex-date, receivable included in equity; cash becomes available on payable date. Ex-date buyers do not receive it. Closed-trade P/L includes earned distributions once. Original cost-adjusted R denominator remains fixed.',
 'actions':'Splits scale quantity and rebase stops/excursions without changing economic cost. Distribution stops decrease by per-share cash amount, preserving economic stop risk. Fractions permitted; cash-in-lieu and investor tax/withholding unmodelled.',
 'ordering':'Actions and payable cash, all open marks, opening stops and queued exits, entries in symbol order, intrabar stops, close marks and signals. Queue/fill shared gates. Freeze persists; exits continue.',
 'benchmark':'Same $5000 account with a static equal-weight $1500 gross-cost basket ($300 each) and cash, actual distributions, normal/stress costs. Allocation baseline, not volatility/time matched.',
 'development_gate':{'min_closed_trades':100,'min_stress_expectancy_r':.15,'min_stress_profit_factor':1.3,'max_best_two_positive_profit_share':.35,'positive_excluding_best_two':True,'lower_drawdown_than_basket':True,'all_input_checks':True},
 'holdout_policy':'This release calculates development only. If it passes, register a separate fixed retrospective validation and then genuinely future paper validation. Earlier prices have been viewed; no claim of untouched 2016–2026 evidence.',
 'activation':'Never automatic; all Webull AU symbol eligibility must be verified independently before any activation.',
 'limitations':["Today's surviving ETF universe has selection bias. SPY dates are a saved session proxy, not a certified exchange calendar.",
 'Issuer records obtained today are retrospective, not archived announcement-time feeds. Signals use events only on effective dates.',
 'Gross distributions and estimated execution costs exclude investor withholding, tax, AUD currency performance and funding cashflows.',
 'OHLC excursion bounds, deterministic symbol order and terminal liquidation are simulation assumptions. No live four-hour scheduler replay.']}
