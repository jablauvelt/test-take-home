from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List


@dataclass(frozen=True)
class Candle:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


def simple_moving_average(values: List[float], window: int) -> List[float | None]:
    if window <= 0:
        raise ValueError("window must be positive")

    averages: List[float | None] = []
    rolling_sum = 0.0
    for index, value in enumerate(values):
        rolling_sum += value
        if index >= window:
            rolling_sum -= values[index - window]
        averages.append(rolling_sum / window if index >= window - 1 else None)
    return averages


def max_drawdown_pct(equity_values: List[float]) -> float:
    peak = 0.0
    worst = 0.0
    for equity in equity_values:
        peak = max(peak, equity)
        if peak > 0:
            worst = min(worst, (equity - peak) / peak)
    return worst * 100


def run_ma_crossover(
    candles: List[Candle],
    fast_window: int,
    slow_window: int,
    initial_cash: float,
    fee_bps: float,
) -> Dict[str, Any]:
    if fast_window >= slow_window:
        raise ValueError("fast_window must be smaller than slow_window")
    if len(candles) < slow_window + 1:
        raise ValueError("not enough candles to run the selected windows")

    closes = [candle.close for candle in candles]
    fast_ma = simple_moving_average(closes, fast_window)
    slow_ma = simple_moving_average(closes, slow_window)
    fee_rate = fee_bps / 10_000

    cash = initial_cash
    position_qty = 0.0
    entry_price = 0.0
    entry_cost = 0.0
    entry_time: datetime | None = None
    trades: List[Dict[str, Any]] = []
    equity_points: List[Dict[str, Any]] = []

    for index, candle in enumerate(candles):
        price = candle.close
        current_fast = fast_ma[index]
        current_slow = slow_ma[index]
        previous_fast = fast_ma[index - 1] if index > 0 else None
        previous_slow = slow_ma[index - 1] if index > 0 else None

        if all(value is not None for value in [current_fast, current_slow, previous_fast, previous_slow]):
            crossed_up = previous_fast <= previous_slow and current_fast > current_slow
            crossed_down = previous_fast >= previous_slow and current_fast < current_slow

            if crossed_up and cash > 0 and position_qty == 0:
                entry_cost = cash
                spendable = cash * (1 - fee_rate)
                position_qty = spendable / price
                cash = 0.0
                entry_price = price
                entry_time = candle.time
            elif crossed_down and position_qty > 0 and entry_time is not None:
                proceeds = position_qty * price * (1 - fee_rate)
                pnl = proceeds - entry_cost
                trades.append(
                    {
                        "entry_time": entry_time,
                        "exit_time": candle.time,
                        "entry_price": entry_price,
                        "exit_price": price,
                        "quantity": position_qty,
                        "pnl": pnl,
                        "return_pct": pnl / entry_cost * 100,
                    }
                )
                cash = proceeds
                position_qty = 0.0
                entry_price = 0.0
                entry_cost = 0.0
                entry_time = None

        equity = cash + position_qty * price
        equity_points.append(
            {
                "time": candle.time,
                "equity": equity,
                "cash": cash,
                "position_qty": position_qty,
                "close_price": price,
            }
        )

    last_candle = candles[-1]
    if position_qty > 0 and entry_time is not None:
        proceeds = position_qty * last_candle.close * (1 - fee_rate)
        pnl = proceeds - entry_cost
        trades.append(
            {
                "entry_time": entry_time,
                "exit_time": last_candle.time,
                "entry_price": entry_price,
                "exit_price": last_candle.close,
                "quantity": position_qty,
                "pnl": pnl,
                "return_pct": pnl / entry_cost * 100,
            }
        )
        cash = proceeds
        position_qty = 0.0
        equity_points[-1] = {
            "time": last_candle.time,
            "equity": cash,
            "cash": cash,
            "position_qty": 0.0,
            "close_price": last_candle.close,
        }

    final_equity = equity_points[-1]["equity"]
    winning_trades = [trade for trade in trades if trade["pnl"] > 0]
    trade_returns = [trade["return_pct"] for trade in trades]

    return {
        "metrics": {
            "final_equity": final_equity,
            "total_return_pct": (final_equity - initial_cash) / initial_cash * 100,
            "max_drawdown_pct": max_drawdown_pct([point["equity"] for point in equity_points]),
            "trade_count": len(trades),
            "win_rate_pct": (len(winning_trades) / len(trades) * 100) if trades else 0.0,
            "avg_trade_return_pct": (sum(trade_returns) / len(trade_returns)) if trade_returns else 0.0,
        },
        "trades": trades,
        "equity_points": equity_points,
    }
