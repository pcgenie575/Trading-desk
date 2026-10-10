"""Pure risk gates shared by operations and portfolio research.
Contracts, quality checks and atomic ledger writes remain operational controls.
"""
import math
from agent_curriculum import candidate_integrity
from exposure import check as exposure_check,SECTOR,GROUP
from universe import INSTRUMENTS,MAX_OPEN,MAX_EXPOSURE,MAX_PORTFOLIO_PLANNED_LOSS

def assess(candidate, symbol, s, active, daily_realized, series, rules):
    checks=[]
    def gate(code,passed,detail):checks.append({'code':code,'status':'PASS' if passed else 'FAIL','detail':detail if not passed or isinstance(detail,dict) else 'Within configured constraint.'})
    consistent,reason=candidate_integrity(candidate)
    gate('SIZING_INTEGRITY',consistent,reason)
    if not consistent:return {'approved':False,'reason':'Book-informed sizing check: '+reason,'checks':checks}
    risk_value=candidate.get('cash_cost',candidate['position_value']);risk_loss=candidate.get('cost_adjusted_risk',candidate['planned_loss'])
    if not all(type(v) in (int,float) and math.isfinite(v) and v>0 for v in (risk_value,risk_loss)):
        gate('COST_ADJUSTED_VALUES',False,'Costs and loss must be finite and positive.')
        return {'approved':False,'reason':'Invalid cost-adjusted values.','checks':checks}
    gate('DRAWDOWN',s['peak_equity']-s['equity']<rules['drawdown_freeze'],'Drawdown circuit breaker reached.')
    gate('NOT_FROZEN',not s['frozen'],'System is frozen.')
    gate('NO_DUPLICATE_POSITION',not any(p['symbol']==symbol for p in active),'An open position already exists for this symbol.')
    gate('POSITION_COUNT',len(active)<MAX_OPEN,'Maximum open positions reached.')
    gate('PORTFOLIO_COST',sum(p['position_value'] for p in active)+risk_value<=MAX_EXPOSURE+1e-6,'Portfolio exposure limit reached.')
    gate('PORTFOLIO_LOSS',sum(p['planned_loss'] for p in active)+risk_loss<=MAX_PORTFOLIO_PLANNED_LOSS+1e-6,'Portfolio planned-loss limit reached.')
    gate('CASH',risk_value<=s['cash'],'Insufficient paper cash.')
    gate('PAPER_ELIGIBLE',bool(INSTRUMENTS.get(symbol,{}).get('paper_enabled')),'Instrument is observation only.')
    gate('DAILY_LOSS',daily_realized>-rules['daily_loss_stop'],'Daily loss circuit breaker reached.')
    gate('POSITION_COST',risk_value<=rules['max_position']+1e-6,'Maximum position exceeded.')
    gate('POSITION_LOSS',risk_loss<=rules['max_planned_loss']+1e-6,'Maximum planned loss exceeded.')
    sector=SECTOR.get(symbol,'Unknown');group=GROUP.get(symbol,'Unknown')
    gate('SECTOR',risk_value+sum(p['position_value'] for p in active if SECTOR.get(p['symbol'],'Unknown')==sector)<=750+1e-6,'Sector exposure exceeds $750.')
    gate('EQUITY_GROUP',group!='US equity' or risk_value+sum(p['position_value'] for p in active if GROUP.get(p['symbol'])==group)<=1000+1e-6,'US equity overlap exceeds $1,000.')
    allowed,details=exposure_check(symbol,risk_value,active,series)
    gate('CONCENTRATION_COMBINED',allowed,details)
    failed=[c for c in checks if c['status']=='FAIL']
    return {'approved':not failed,'reason':failed[0]['detail'] if failed else 'All deterministic risk and concentration checks passed.','checks':checks}
