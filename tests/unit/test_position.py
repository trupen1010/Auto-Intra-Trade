from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.engine.position import OpenPosition
from src.engine.trade_state import EngineTradeState
from src.utils.enums import EntryTF, ExitReason, SignalSide


IST = ZoneInfo("Asia/Kolkata")


def _dt(hour: int, minute: int) -> datetime:
    return datetime(2024, 1, 1, hour, minute, tzinfo=IST)


def test_to_closed_trade_buy_profit() -> None:
    trade = EngineTradeState(
        run_id="run1",
        symbol="ABC",
        timeframe_entry=EntryTF.FIVE_MINUTE,
        direction=SignalSide.BUY,
        entry_time=_dt(9, 20),
        entry_price=100.0,
        quantity=10,
        hard_sl=95.0,
    )
    position = OpenPosition(trade=trade, current_stop=97.0)

    closed = position.to_closed_trade(
        exit_time=_dt(9, 25),
        exit_price=110.0,
        exit_reason=ExitReason.SIGNAL_EXIT,
        charges=0.0,
    )

    assert closed.pnl_points == pytest.approx(10.0, abs=1e-4)
    assert closed.pnl_rupees == pytest.approx(100.0, abs=1e-4)
    assert closed.net_pnl == pytest.approx(100.0, abs=1e-4)


def test_to_closed_trade_sell_profit() -> None:
    trade = EngineTradeState(
        run_id="run1",
        symbol="ABC",
        timeframe_entry=EntryTF.FIFTEEN_MINUTE,
        direction=SignalSide.SELL,
        entry_time=_dt(10, 0),
        entry_price=200.0,
        quantity=5,
        hard_sl=210.0,
    )
    position = OpenPosition(trade=trade, current_stop=205.0)

    closed = position.to_closed_trade(
        exit_time=_dt(10, 5),
        exit_price=180.0,
        exit_reason=ExitReason.TIME_EXIT,
        charges=0.0,
    )

    assert closed.pnl_points == pytest.approx(20.0, abs=1e-4)
    assert closed.pnl_rupees == pytest.approx(100.0, abs=1e-4)


def test_to_closed_trade_charges_reduce_net_pnl() -> None:
    trade = EngineTradeState(
        run_id="run1",
        symbol="ABC",
        timeframe_entry=EntryTF.FIVE_MINUTE,
        direction=SignalSide.BUY,
        entry_time=_dt(11, 0),
        entry_price=100.0,
        quantity=10,
        hard_sl=90.0,
    )
    position = OpenPosition(trade=trade, current_stop=95.0)

    # charges precomputed by caller (e.g. via calculate_round_trip_charges)
    precomputed_charges = 21.0
    closed = position.to_closed_trade(
        exit_time=_dt(11, 5),
        exit_price=110.0,
        exit_reason=ExitReason.SIGNAL_EXIT,
        charges=precomputed_charges,
    )

    assert closed.charges == pytest.approx(21.0, abs=1e-4)
    assert closed.net_pnl == pytest.approx(79.0, abs=1e-4)


def test_pnl_points_sign_correct_for_loss() -> None:
    buy_trade = EngineTradeState(
        run_id="run1",
        symbol="ABC",
        timeframe_entry=EntryTF.FIVE_MINUTE,
        direction=SignalSide.BUY,
        entry_time=_dt(12, 0),
        entry_price=100.0,
        quantity=1,
        hard_sl=95.0,
    )
    buy_closed = OpenPosition(trade=buy_trade, current_stop=97.0).to_closed_trade(
        exit_time=_dt(12, 5),
        exit_price=90.0,
        exit_reason=ExitReason.HARD_SL,
        charges=0.0,
    )
    assert buy_closed.pnl_points == pytest.approx(-10.0, abs=1e-4)

    sell_trade = EngineTradeState(
        run_id="run1",
        symbol="ABC",
        timeframe_entry=EntryTF.FIFTEEN_MINUTE,
        direction=SignalSide.SELL,
        entry_time=_dt(12, 0),
        entry_price=100.0,
        quantity=1,
        hard_sl=105.0,
    )
    sell_closed = OpenPosition(trade=sell_trade, current_stop=103.0).to_closed_trade(
        exit_time=_dt(12, 15),
        exit_price=110.0,
        exit_reason=ExitReason.HARD_SL,
        charges=0.0,
    )
    assert sell_closed.pnl_points == pytest.approx(-10.0, abs=1e-4)


