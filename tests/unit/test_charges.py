import pytest

from src.engine.charges import calculate_round_trip_charges


def test_charges_all_components_sum_correctly() -> None:
    entry_price = 100.0
    exit_price = 110.0
    quantity = 10
    brokerage_pct = 0.001
    stt_pct = 0.0005
    exchange_pct = 0.0002
    sebi_pct = 0.0001
    gst_pct = 0.18
    stamp_pct = 0.0003

    entry_notional = entry_price * quantity
    exit_notional = exit_price * quantity
    turnover = entry_notional + exit_notional

    brokerage = turnover * brokerage_pct
    stt = exit_notional * stt_pct
    exchange = turnover * exchange_pct
    sebi = turnover * sebi_pct
    gst = (brokerage + exchange) * gst_pct
    stamp = entry_notional * stamp_pct
    expected = brokerage + stt + exchange + sebi + gst + stamp

    charges = calculate_round_trip_charges(
        entry_price=entry_price,
        exit_price=exit_price,
        quantity=quantity,
        brokerage_pct=brokerage_pct,
        stt_pct=stt_pct,
        exchange_pct=exchange_pct,
        sebi_pct=sebi_pct,
        gst_pct=gst_pct,
        stamp_pct=stamp_pct,
    )
    assert charges == pytest.approx(expected)


def test_charges_returns_zero_for_all_zero_rates() -> None:
    charges = calculate_round_trip_charges(
        entry_price=100.0,
        exit_price=110.0,
        quantity=10,
        brokerage_pct=0.0,
        stt_pct=0.0,
        exchange_pct=0.0,
        sebi_pct=0.0,
        gst_pct=0.0,
        stamp_pct=0.0,
    )
    assert charges == 0.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"brokerage_pct": -0.001},
        {"stt_pct": -0.001},
        {"exchange_pct": -0.001},
        {"sebi_pct": -0.001},
        {"gst_pct": -0.001},
        {"stamp_pct": -0.001},
    ],
)
def test_charges_raises_on_negative_rate(kwargs: dict[str, float]) -> None:
    base_kwargs = {
        "brokerage_pct": 0.0,
        "stt_pct": 0.0,
        "exchange_pct": 0.0,
        "sebi_pct": 0.0,
        "gst_pct": 0.0,
        "stamp_pct": 0.0,
    }
    base_kwargs.update(kwargs)

    with pytest.raises(ValueError):
        calculate_round_trip_charges(
            entry_price=100.0,
            exit_price=110.0,
            quantity=10,
            **base_kwargs,
        )
