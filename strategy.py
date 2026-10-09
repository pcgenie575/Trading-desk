from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass(frozen=True)
class StrategyConfig:
    trend_ma: int = 50
    breakout_lookback: int = 10
    exit_ma: int = 20
    starting_balance: float = 5000.0
    max_position: float = 500.0
    max_planned_loss: float = 25.0
    stop_pct: float = 0.05
    slippage_bps: float = 2.0
    commission_per_order: float = 1.0

CONFIG = StrategyConfig()

def sma(values: List[float], n: int) -> Optional[float]:
    return None if len(values) < n else sum(values[-n:]) / n

def signal_from_bars(bars: List[Dict], cfg: StrategyConfig = CONFIG):
    needed = max(cfg.trend_ma, cfg.exit_ma, cfg.breakout_lookback + 1)
    if len(bars) < needed:
        return {"signal": "NO_TRADE", "reason": f"Need at least {needed} completed bars."}

    closes = [float(b["close"]) for b in bars]
    close = closes[-1]
    trend = sma(closes, cfg.trend_ma)
    exit_ma = sma(closes, cfg.exit_ma)
    prior = bars[-(cfg.breakout_lookback + 1):-1]
    breakout_high = max(float(b["high"]) for b in prior)

    if close > trend and close > breakout_high:
        stop = close * (1.0 - cfg.stop_pct)
        risk_per_share = close - stop
        risk_qty = cfg.max_planned_loss / risk_per_share
        value_qty = cfg.max_position / close
        qty = max(0.0, min(risk_qty, value_qty))
        return {
            "signal": "CANDIDATE",
            "reason": "Close > 50-bar SMA and > prior 10-bar high.",
            "entry_reference": close,
            "stop": stop,
            "quantity": qty,
            "position_value": qty * close,
            "planned_loss": qty * risk_per_share,
            "trend_ma": trend,
            "exit_ma": exit_ma,
            "breakout_high": breakout_high,
        }

    return {
        "signal": "WATCH",
        "reason": "Entry conditions are not both satisfied.",
        "close": close,
        "trend_ma": trend,
        "exit_ma": exit_ma,
        "breakout_high": breakout_high,
    }

def backtest(bars: List[Dict], cfg: StrategyConfig = CONFIG):
    # Research uses a frozen shared cost model and fixed protocol, not ad-hoc tuning.
    from research_engine import validate_bars, compare
    if cfg != CONFIG:raise ValueError('Custom settings require a new recorded research protocol.')
    validate_bars(bars)
    return compare(bars,int(len(bars)*.7))
