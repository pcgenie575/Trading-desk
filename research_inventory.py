"""Counts describe registered protocols, not independent statistical trials."""
def slots(protocol,kind):
    if isinstance(protocol.get('experiment'),dict):return slots(protocol['experiment'],kind)
    if protocol.get('variants') is not None:
        return len(protocol['variants'])+len(protocol.get('baseline_neighbours',[]))
    if protocol.get('entries') is not None and protocol.get('exits') is not None:
        return len(protocol['entries'])*len(protocol['exits'])
    if kind=='COST':return slots(protocol.get('source_protocol',{}),'ORIGINAL')
    if kind in ('ETF','PORTFOLIO') and (protocol.get('strategy') or protocol.get('variant')):return 1
    return None
