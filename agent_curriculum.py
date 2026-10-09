"""Original engineering lessons informed by public author/publisher descriptions.

This is a versioned rule-based curriculum, not model fine-tuning or full-book ingestion.
"""
import math, hashlib, json
VERSION='book-curriculum-v1'
BOOKS=[
 {'id':'elder','title':'The New Trading for a Living','author':'Alexander Elder','source':'https://www.elder.com/books',
  'lesson':'Connect a defined plan, risk control and recorded review.','roles':['Analyst','Risk & Compliance','Logger','Supervisor']},
 {'id':'tharp','title':'Trade Your Way to Financial Freedom','author':'Van K. Tharp','source':'https://vantharpinstitute.com/product/trade-your-way-to-financial-freedom/',
  'lesson':'Evaluate position sizing, exits and distributions of R-multiples.','roles':['Risk & Compliance','Paper Trader','Performance Reviewer']},
 {'id':'douglas','title':'Trading in the Zone','author':'Mark Douglas','source':'https://www.penguinrandomhouse.com/books/350665/trading-in-the-zone-by-mark-douglas/9781440625411/',
  'lesson':'Use a consistent process and assess uncertain outcomes across a series.','roles':['Analyst','Paper Trader','Supervisor','Performance Reviewer']},
 {'id':'minervini','title':'Trade Like a Stock Market Wizard','author':'Mark Minervini','source':'https://www.mheducation.com/highered/mhp/product/trade-like-stock-market-wizard-how-achieve-super-performance-stocks-any-market.html',
  'lesson':'Study trend-aligned stock selection and disciplined loss management.','roles':['Analyst','Risk & Compliance']},
 {'id':'aronson','title':'Evidence-Based Technical Analysis','author':'David R. Aronson','source':'https://onlinelibrary.wiley.com/doi/book/10.1002/9781118268315',
  'lesson':'Test explicit hypotheses and account for data-mining bias.','roles':['Market Data','Analyst','Logger','Performance Reviewer','Supervisor']},
]
AGENTS={
 'Market Data':{'books':['aronson'],'practice':'Validate identity, currency and completed OHLC data; expose failures and freshness.','active':'Existing feed validation and persisted coverage.'},
 'Analyst':{'books':['elder','douglas','minervini','aronson'],'practice':'Record objective trend/breakout evidence and the curriculum version; keep hypotheses separate from approved rules.','active':'Book-informed annotations on every fresh entry analysis; original signal rules retained.'},
 'Risk & Compliance':{'books':['elder','tharp','minervini'],'practice':'Check that quantity, capital and planned loss agree before applying position, portfolio and circuit-breaker limits.','active':'New candidate arithmetic-integrity gate plus existing risk limits.'},
 'Paper Trader':{'books':['tharp','douglas'],'practice':'Follow approved sizing and exits consistently, model slippage, and never scale risk after a loss.','active':'Existing deterministic execution; new records capture curriculum version.'},
 'Logger':{'books':['elder','aronson'],'practice':'Preserve the original plan, configuration, learning evidence and decisions without inventing missing historical context.','active':'New curriculum provenance in plan snapshots and audit records.'},
 'Supervisor':{'books':['elder','douglas','aronson'],'practice':'Maintain operational freezes; keep research changes versioned and require evidence before changing rules.','active':'Startup curriculum self-checks and existing recovery/circuit-breaker monitoring.'},
 'Performance Reviewer':{'books':['tharp','douglas','aronson'],'practice':'Report eligible R results, sample size and loss streaks; separate process compliance from outcome and flag missing validation.','active':'New evidence review in saved performance reports.'},
}
FINGERPRINT=hashlib.sha256(json.dumps({'version':VERSION,'books':BOOKS,'agents':AGENTS},sort_keys=True).encode()).hexdigest()[:16]

def candidate_integrity(candidate):
    keys=('quantity','position_value','planned_loss','stop','entry_reference')
    if not all(type(candidate.get(k)) in (int,float) and math.isfinite(candidate[k]) and candidate[k]>0 for k in keys):
        return False,'Candidate requires finite positive numbers.'
    if candidate['stop']>=candidate['entry_reference']:return False,'Stop must be below a long entry.'
    capital=candidate['quantity']*candidate['entry_reference']
    loss=candidate['quantity']*(candidate['entry_reference']-candidate['stop'])
    if not math.isclose(capital,candidate['position_value'],rel_tol=1e-6,abs_tol=1e-6):return False,'Quantity and position value do not agree.'
    if not math.isclose(loss,candidate['planned_loss'],rel_tol=1e-6,abs_tol=1e-6):return False,'Quantity, stop and planned loss do not agree.'
    return True,'Candidate sizing arithmetic is consistent.'

def analyst_guidance(signal):
    candidate=signal.get('signal')=='CANDIDATE'
    checks={'signal':signal.get('signal'),'trend_and_breakout_trigger':candidate,'sizing_integrity':candidate_integrity(signal)[0] if candidate else None}
    return {'curriculum':VERSION,'fingerprint':FINGERPRINT,'books':['elder','douglas','minervini','aronson'],
      'checks':checks,'application':'Observes the existing completed-bar strategy; no new entry rule activated.',
      'research_limits':['No full SEPA implementation','Fundamentals and relative-strength ranking are unavailable in this feed','Four-hour data does not implement daily/weekly trend templates']}

def evidence_review(rows):
    closed=sorted((p for p in rows if p.get('status')=='CLOSED'),key=lambda p:(p.get('exit_time') or '',p.get('id') or ''))
    eligible=[p for p in closed if type(p.get('planned_loss')) in (int,float) and math.isfinite(p['planned_loss']) and p['planned_loss']>0 and type(p.get('realized_pnl')) in (int,float) and math.isfinite(p['realized_pnl'])]
    rs=[p['realized_pnl']/p['planned_loss'] for p in eligible]
    streak=0
    for p in reversed(closed):
        if (p.get('realized_pnl') or 0)<0:streak+=1
        else:break
    return {'curriculum':VERSION,'closed_trades':len(closed),'eligible_r_trades':len(rs),'mean_r':sum(rs)/len(rs) if rs else None,
      'recent_loss_streak':streak,'evidence_status':'COLLECTING' if len(rs)<30 else 'READY_FOR_REVIEW',
      'minimum_review_sample':30,'edge_validated':False,
      'next_steps':['Keep strategy configuration fixed during the sample','Use a separate out-of-sample period','Stress costs and execution assumptions','Account for correlated trades and multiple strategy trials'],
      'sample_note':'Thirty eligible trades is our review milestone, not statistical proof or a book-prescribed threshold.'}

def curriculum_self_check():
    valid={'entry_reference':100,'stop':95,'quantity':5,'position_value':500,'planned_loss':25}
    scenarios={'consistent_sizing':candidate_integrity(valid)[0],
      'reject_capital_mismatch':not candidate_integrity(dict(valid,position_value=1))[0],
      'reject_loss_mismatch':not candidate_integrity(dict(valid,planned_loss=1))[0],
      'reject_nonfinite':not candidate_integrity(dict(valid,quantity=float('nan')))[0],
      'reject_invalid_stop':not candidate_integrity(dict(valid,stop=101))[0],
      'no_edge_from_empty_sample':evidence_review([])['mean_r'] is None and not evidence_review([])['edge_validated']}
    return {'passed':all(scenarios.values()),'scenarios':scenarios}

def curriculum():
    return {'version':VERSION,'fingerprint':FINGERPRINT,'method':'Coded lessons and operational checks; no AI-model weight training',
      'source_basis':'Public author/publisher descriptions; full books have not been ingested',
      'selection_basis':'Five books selected for this swing-paper desk; not an objective global top-five ranking',
      'books':BOOKS,'agents':AGENTS,'self_check':curriculum_self_check(),
      'research_only':['New stock-selection systems','Daily/weekly trend templates','Out-of-sample strategy variants'],
      'operating_policy':'Paper only, free data only. Existing entries/exits and risk limits remain in force.'}
