"""Conservative concentration gates, using saved data only (no extra provider credits)."""
import math
SECTOR={**dict.fromkeys(['AAPL','MSFT','NVDA','AMD'],'Technology'),**dict.fromkeys(['GOOGL','META'],'Communication'),**dict.fromkeys(['AMZN','TSLA'],'Consumer'),'JPM':'Financial','XOM':'Energy','SPY':'Broad ETF','QQQ':'Technology ETF','IWM':'Broad ETF','DIA':'Broad ETF','GLD':'Gold','TLT':'Treasury'}
GROUP={s:(SECTOR[s] if s in ('GLD','TLT') else 'US equity') for s in SECTOR}
LIMITS={'sector_dollars':750,'equity_group_dollars':1000,'correlation_cluster_dollars':750,'correlation_threshold':0.8,'minimum_aligned_returns':30,'maximum_data_age_days':10}

def correlation(a,b):
    shared=sorted(set(a)&set(b));pairs=[]
    for left,right in zip(shared,shared[1:]):
        if a[left]>0 and b[left]>0:pairs.append((a[right]/a[left]-1,b[right]/b[left]-1))
    if len(pairs)<30:return None,len(pairs)
    x,y=zip(*pairs);mx=sum(x)/len(x);my=sum(y)/len(y)
    xx=sum((v-mx)**2 for v in x);yy=sum((v-my)**2 for v in y)
    if not xx or not yy:return None,len(pairs)
    return sum((u-mx)*(v-my) for u,v in pairs)/math.sqrt(xx*yy),len(pairs)

def check(symbol,value,active,series,*,sectors=None,groups=None,equity_groups=None):
    sectors=SECTOR if sectors is None else sectors;groups=GROUP if groups is None else groups
    equity_groups={'US equity'} if equity_groups is None else equity_groups
    sector=sectors.get(symbol,'Unknown');group=groups.get(symbol,'Unknown')
    if value+sum(p['position_value'] for p in active if sectors.get(p['symbol'],'Unknown')==sector)>750+1e-6:return False,'Sector exposure exceeds $750.'
    if group in equity_groups and value+sum(p['position_value'] for p in active if groups.get(p['symbol']) in equity_groups)>1000+1e-6:return False,'US equity overlap exceeds $1,000.'
    cluster=value;details=[]
    for p in active:
        corr,n=correlation(series.get(symbol,{}),series.get(p['symbol'],{}))
        conservative=corr is None and groups.get(p['symbol'])==group
        if conservative or (corr is not None and corr>=.8):cluster+=p['position_value']
        details.append({'symbol':p['symbol'],'correlation':corr,'aligned_returns':n,'fallback':conservative})
    if cluster>750+1e-6:return False,'Correlated exposure exceeds $750 (unknown same-group correlations count as overlapping).'
    return True,{'sector':sector,'group':group,'cluster_dollars':cluster,'pairs':details}
