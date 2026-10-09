import os
import json
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import math

class MarketDataError(Exception):
    pass

class TwelveDataAdapter:
    BASE = "https://api.twelvedata.com/time_series"

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("TWELVE_DATA_API_KEY")

    def latest_completed_bars(self, symbol="SPY", interval="4h", outputsize=30):
        if not self.api_key:
            raise MarketDataError("TWELVE_DATA_API_KEY is not configured.")

        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
            "timezone": "America/New_York",
            "apikey": self.api_key,
        }
        req = Request(self.BASE + "?" + urlencode(params), headers={"User-Agent":"TradingControlRoom/2.0"})
        try:
            with urlopen(req, timeout=15) as r:
                payload = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            raise MarketDataError(f"Market-data request failed ({type(e).__name__})")

        if payload.get("status") == "error" or "values" not in payload:
            raise MarketDataError(str(payload.get("message", "Unexpected market-data response.")).replace(self.api_key, '[redacted]'))

        meta=payload.get('meta',{})
        if meta.get('symbol')!=symbol:
            raise MarketDataError('Provider returned a different instrument.')
        if '/' in symbol:
            if meta.get('currency_quote')!='US Dollar':
                raise MarketDataError('Crypto quote currency must be USD.')
        elif meta.get('currency')!='USD' or meta.get('exchange') not in ('NASDAQ','NYSE','NYSE Arca','NYSE MKT','AMEX','CBOE','BATS'):
            raise MarketDataError('Instrument is not verified as a USD US listing.')

        bars = []
        for x in reversed(payload["values"]):
            bars.append({
                "datetime": x["datetime"],
                "open": float(x["open"]),
                "high": float(x["high"]),
                "low": float(x["low"]),
                "close": float(x["close"]),
                "volume": float(x.get("volume") or 0),
            })
        now=datetime.now(timezone.utc)
        completed=[]
        for bar in bars:
            opened=datetime.fromisoformat(bar["datetime"]).replace(tzinfo=ZoneInfo("America/New_York"))
            if not all(math.isfinite(bar[k]) and bar[k] > 0 for k in ("open","high","low","close")):
                raise MarketDataError("Invalid OHLC data.")
            if not bar["low"] <= min(bar["open"],bar["close"]) <= max(bar["open"],bar["close"]) <= bar["high"]:
                raise MarketDataError("Inconsistent OHLC data.")
            # Conservative completion: wait the entire interval plus provider delay.
            if opened.astimezone(timezone.utc)+timedelta(hours=4, minutes=15) <= now:
                completed.append(bar)
        return sorted(completed,key=lambda b:b["datetime"])
