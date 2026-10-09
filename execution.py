from dataclasses import dataclass,asdict
import math

@dataclass(frozen=True)
class Costs:
    version: str='estimated-costs-v2'
    half_spread_bps: float=5.0
    slippage_bps: float=2.0
    fee_per_order: float=1.0
    fx_bps: float=35.0
    note: str='Conservative estimates, not broker tariffs. USD ledger; FX is a per-side AUD funding/repatriation cost allowance, not an AUD conversion or FX return.'

COSTS=Costs()
def fill(raw,qty,side,costs=COSTS):
    if side not in ('buy','sell') or not all(math.isfinite(x) and x>0 for x in (raw,qty)):raise ValueError('Invalid fill')
    price=raw*(1+(1 if side=='buy' else -1)*(costs.half_spread_bps+costs.slippage_bps)/10000)
    spread=qty*raw*costs.half_spread_bps/10000
    slip=qty*raw*costs.slippage_bps/10000
    fx=qty*price*costs.fx_bps/10000
    fee=costs.fee_per_order+fx
    return dict(price=price,qty=qty,spread=spread,slippage=slip,commission=costs.fee_per_order,fx=fx,fee=fee,total_cost=spread+slip+fee,cash=qty*price+(fee if side=='buy' else -fee),model=asdict(costs))

def sized_entry(raw,stop,cash=5000,max_value=500,max_risk=25,costs=COSTS,max_qty=None):
    if raw<=stop:return None
    buy=fill(raw,1,'buy',costs);sell=fill(stop,1,'sell',costs)
    per_unit=buy['price']*(1+costs.fx_bps/10000)-sell['price']*(1-costs.fx_bps/10000)
    qty=min((min(cash,max_value)-costs.fee_per_order)/(buy['price']*(1+costs.fx_bps/10000)),(max_risk-2*costs.fee_per_order)/per_unit)
    if max_qty is not None:qty=min(qty,max_qty)
    if qty<=0:return None
    result=fill(raw,qty,'buy',costs);result['planned_loss']=result['cash']-fill(stop,qty,'sell',costs)['cash'];result['stop']=stop
    return result
