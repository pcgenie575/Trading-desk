"""Separate registration for doubled costs; earlier diagnostics remain immutable."""
from dataclasses import replace,asdict
from cost_scenarios import SCENARIOS as BASE,PROTOCOL as PRIOR,diagnose as run

def doubled(cost):
    return replace(cost,version=cost.version+'-stress-2x',half_spread_bps=cost.half_spread_bps*2,
        slippage_bps=cost.slippage_bps*2,fee_per_order=cost.fee_per_order*2,fx_bps=cost.fx_bps*2)

SCENARIOS={k+suffix:(doubled(c) if suffix=='_2x' else c) for k,c in BASE.items() for suffix in ('','_2x')}
PROTOCOL=dict(PRIOR,version='cost-diagnostic-v3',scenarios={k:asdict(c) for k,c in SCENARIOS.items()},calculations=224,
    statistical_status='Eight reused strategy configurations, fourteen normal/stress scenarios, two methods: 224 calculations, not independent strategies.',
    stress_rule='Double spread, slippage, commission and per-trade FX. Zero-cost values remain zero. No selection, activation or new holdout.')
def diagnose(symbol,bars,split):return run(symbol,bars,split,cost_scenarios=SCENARIOS,protocol=PROTOCOL)
