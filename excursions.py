"""Price excursions, with explicit limits when OHLC cannot establish exit order."""
def initial(entry, quantity, risk, complete=True):
    return {'entry_reference':entry,'quantity':quantity,'initial_risk':risk,
            'lowest_observed':entry,'highest_observed':entry,'last_bar':None,
            'complete_since_entry':complete,'exit_order_uncertain':False,'bars_observed':0}

def observe(state, bar, stop=None):
    state=dict(state)
    if state['last_bar'] and bar['datetime']<=state['last_bar']:return state
    # An opening gap exits immediately. An intrabar stop does not reveal whether
    # the high happened before the stop: include only prices guaranteed to precede exit.
    if stop is not None:
        low=min(bar['open'],stop);high=bar['open']
        state['exit_order_uncertain']=state['exit_order_uncertain'] or bar['open']>stop
    else:low=bar['low'];high=bar['high']
    state['lowest_observed']=min(state['lowest_observed'],low)
    state['highest_observed']=max(state['highest_observed'],high)
    state['last_bar']=bar['datetime'];state['bars_observed']+=1
    return state

def report(state):
    entry=state['entry_reference'];qty=state['quantity'];risk=state['initial_risk']
    adverse=max(0,entry-state['lowest_observed']);favourable=max(0,state['highest_observed']-entry)
    return dict(state,mae_pct=100*adverse/entry,mfe_pct=100*favourable/entry,
                mae_dollars=adverse*qty,mfe_dollars=favourable*qty,
                mae_r=adverse*qty/risk,mfe_r=favourable*qty/risk,
                basis='Raw price movement before costs; lower bounds when exit order or earlier history is unknown.')
