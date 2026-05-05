import pytest

from src.engine.risk import compute_hard_sl, compute_position_size
from src.utils.enums import SignalSide


def test_position_size_standard_case() -> None:
    qty = compute_position_size(
        capital=100_000.0,
        risk_pct=0.01,
        entry_price=100.0,
        hard_sl_price=98.0,
    )
    assert qty == 500


def test_position_size_minimum_is_one() -> None:
    qty = compute_position_size(
        capital=100.0,
        risk_pct=0.01,
        entry_price=100.0,
        hard_sl_price=50.0,
    )
    assert qty == 1


def test_position_size_raises_if_sl_equals_entry() -> None:
    with pytest.raises(ValueError, match="sl_distance"):
        compute_position_size(
            capital=100_000.0,
            risk_pct=0.01,
            entry_price=100.0,
            hard_sl_price=100.0,
        )


def test_hard_sl_buy_is_below_entry() -> None:
    hard_sl = compute_hard_sl(
        entry_price=100.0,
        direction=SignalSide.BUY,
        atr=2.0,
        sl_atr_multiplier=1.5,
    )
    assert hard_sl == pytest.approx(97.0)
    assert hard_sl < 100.0


def test_hard_sl_sell_is_above_entry() -> None:
    hard_sl = compute_hard_sl(
        entry_price=100.0,
        direction=SignalSide.SELL,
        atr=2.0,
        sl_atr_multiplier=1.5,
    )
    assert hard_sl == pytest.approx(103.0)
    assert hard_sl > 100.0


def test_hard_sl_raises_if_atr_zero() -> None:
    with pytest.raises(ValueError, match="atr"):
        compute_hard_sl(
            entry_price=100.0,
            direction=SignalSide.BUY,
            atr=0.0,
            sl_atr_multiplier=1.5,
        )

