from datetime import datetime, timedelta, timezone

import pytest

from app.backtester import Candle, max_drawdown_pct, run_ma_crossover, simple_moving_average


def make_candles(closes: list[float]) -> list[Candle]:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return [
        Candle(
            time=start + timedelta(hours=index),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=1.0,
        )
        for index, close in enumerate(closes)
    ]


def test_simple_moving_average_returns_none_until_window_is_ready() -> None:
    assert simple_moving_average([1, 2, 3, 4], 3) == [None, None, 2, 3]


def test_max_drawdown_pct_tracks_worst_peak_to_trough() -> None:
    assert max_drawdown_pct([100, 120, 90, 150, 135]) == pytest.approx(-25.0)


def test_run_ma_crossover_generates_trades_and_equity_curve() -> None:
    candles = make_candles([10, 9, 8, 9, 10, 12, 14, 13, 12, 11, 10])

    result = run_ma_crossover(
        candles=candles,
        fast_window=2,
        slow_window=3,
        initial_cash=1000,
        fee_bps=0,
    )

    assert result["metrics"]["trade_count"] == 1
    assert result["trades"][0]["entry_price"] == 10
    assert result["trades"][0]["exit_price"] == 12
    assert result["metrics"]["final_equity"] == pytest.approx(1200)
    assert len(result["equity_points"]) == len(candles)


def test_run_ma_crossover_rejects_invalid_windows() -> None:
    with pytest.raises(ValueError, match="fast_window"):
        run_ma_crossover(make_candles([1, 2, 3, 4]), 5, 5, 1000, 0)


def test_trade_pnl_includes_entry_and_exit_fees() -> None:
    candles = make_candles([10, 9, 8, 9, 10, 12, 14, 13, 12, 11, 10])

    result = run_ma_crossover(
        candles=candles,
        fast_window=2,
        slow_window=3,
        initial_cash=1000,
        fee_bps=100,
    )

    assert result["metrics"]["trade_count"] == 1
    assert result["trades"][0]["pnl"] == pytest.approx(176.12)
    assert result["metrics"]["final_equity"] == pytest.approx(1176.12)


def test_open_position_is_closed_on_final_candle() -> None:
    candles = make_candles([10, 9, 8, 9, 10, 12, 14])

    result = run_ma_crossover(
        candles=candles,
        fast_window=2,
        slow_window=3,
        initial_cash=1000,
        fee_bps=0,
    )

    assert result["metrics"]["trade_count"] == 1
    assert result["trades"][0]["exit_time"] == candles[-1].time
    assert result["metrics"]["final_equity"] == pytest.approx(1400)
    assert result["equity_points"][-1]["position_qty"] == 0


def test_run_ma_crossover_rejects_too_few_candles() -> None:
    with pytest.raises(ValueError, match="not enough candles"):
        run_ma_crossover(make_candles([1, 2, 3]), 2, 3, 1000, 0)
