"""Explicit free-data watchlist; not the complete Webull tradable catalogue."""
US_SYMBOLS = ('SPY','QQQ','IWM','DIA','AAPL','MSFT','AMZN','NVDA','GOOGL','META','TSLA','AMD','JPM','XOM','GLD','TLT')
INSTRUMENTS = {s:dict(symbol=s,asset='US share/ETF',currency='USD',timezone='America/New_York',paper_enabled=True) for s in US_SYMBOLS}
INSTRUMENTS.update({s:dict(symbol=s,asset='Crypto',currency='USD',timezone='America/New_York',paper_enabled=False) for s in ('BTC/USD','ETH/USD')})
# Crypto is observed only: exchange-aggregated data does not model Webull spreads/fees.
DAILY_CREDITS = 720
SCAN_CREDITS = 600
OPEN_REFRESH_SECONDS = 900
SCAN_REFRESH_SECONDS = 3600
MAX_OPEN = 3
MAX_EXPOSURE = 1500.0
MAX_PORTFOLIO_PLANNED_LOSS = 75.0
