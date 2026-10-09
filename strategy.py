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
    commission_per_order: float = 0.0

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
    needed = max(cfg.trend_ma, cfg.exit_ma, cfg.breakout_lookback + 1)
    if len(bars) <= needed:
        return {"error": f"Need more than {needed} bars for a backtest."}

    cash = cfg.starting_balance
    peak = cash
    max_drawdown = 0.0
    position = None
    trades = []
    equity_curve = []

    for i in range(needed, len(bars)):
        window = bars[:i+1]
        bar = bars[i]
        close = float(bar["close"])
        low = float(bar["low"])
        closes = [float(x["close"]) for x in window]
        exit_ma = sma(closes, cfg.exit_ma)

        if position:
            raw_exit = None
            exit_reason = None
            if low <= position["stop"]:
                raw_exit = position["stop"]
                exit_reason = "PROTECTIVE_STOP"
            elif exit_ma is not None and close < exit_ma:
                raw_exit = close
                exit_reason = "CLOSE_BELOW_20_SMA"

            if exit_reason:
                exit_price = raw_exit * (1.0 - cfg.slippage_bps / 10000.0)
                proceeds = position["qty"] * exit_price - cfg.commission_per_order
                cash += proceeds
                trades.append({
                    "entry_time": position["entry_time"],
                    "exit_time": bar["datetime"],
                    "entry_price": position["entry_price"],
                    "exit_price": exit_price,
                    "qty": position["qty"],
                    "pnl": proceeds - position["cost"],
                    "exit_reason": exit_reason,
                })
                position = None

        if not position:
            sig = signal_from_bars(window, cfg)
            if sig["signal"] == "CANDIDATE":
                entry = close * (1.0 + cfg.slippage_bps / 10000.0)
                qty = min(sig["quantity"], max(0.0, cash - cfg.commission_per_order) / entry)
                cost = qty * entry + cfg.commission_per_order
                if qty > 0 and cost <= cash:
                    cash -= cost
                    position = {
                        "entry_time": bar["datetime"],
                        "entry_price": entry,
                        "qty": qty,
                        "stop": sig["stop"],
                        "cost": cost,
                    }

        equity = cash + (position["qty"] * close if position else 0.0)
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
        equity_curve.append({"datetime": bar["datetime"], "equity": equity})

    if position:
        last = bars[-1]
        exit_price = float(last["close"]) * (1.0 - cfg.slippage_bps / 10000.0)
        proceeds = position["qty"] * exit_price - cfg.commission_per_order
        cash += proceeds
        trades.append({
            "entry_time": position["entry_time"],
            "exit_time": last["datetime"],
            "entry_price": position["entry_price"],
            "exit_price": exit_price,
            "qty": position["qty"],
            "pnl": proceeds - position["cost"],
            "exit_reason": "END_OF_TEST",
        })

    wins = sum(t["pnl"] > 0 for t in trades)
    total_pnl = cash - cfg.starting_balance
    first = float(bars[needed]["close"])
    last = float(bars[-1]["close"])
    hold_qty = min(cfg.max_position / first, cfg.starting_balance / first)
    passive_pnl = hold_qty * (last - first)

    return {
        "starting_balance": cfg.starting_balance,
        "ending_balance": cash,
        "total_pnl": total_pnl,
        "return_pct": total_pnl / cfg.starting_balance * 100.0,
        "trades": len(trades),
        "wins": wins,
        "losses": len(trades) - wins,
        "win_rate_pct": (wins / len(trades) * 100.0) if trades else 0.0,
        "max_drawdown_dollars": max_drawdown,
        "passive_500_exposure_pnl": passive_pnl,
        "strategy_minus_passive_pnl": total_pnl - passive_pnl,
        "slippage_bps": cfg.slippage_bps,
        "commission_per_order": cfg.commission_per_order,
        "trade_log": trades,
        "equity_curve": equity_curve,
    }
