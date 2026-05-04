"""Signal transition detection from trailing-stop side output."""

from __future__ import annotations

import pandas as pd

from src.indicators.atr import compute_atr
from src.indicators.trailing_stop import compute_trailing_stop
from src.models.candle import Candle
from src.models.signal_state import SignalTransition
from src.utils.enums import SignalSide


def detect_signals(sides: list[SignalSide]) -> list[SignalTransition]:
    """Detect fresh signal transitions from per-bar side states.

    A fresh signal is emitted only on bars where the side changes from the
    previous bar. Index 0 is never fresh because there is no prior state.

    Args:
        sides: Per-bar signal sides produced by trailing-stop computation.

    Returns:
        Signal states aligned 1:1 with ``sides`` containing transition flags.
    """
    states: list[SignalTransition] = []
    for idx, side in enumerate(sides):
        is_fresh = idx > 0 and sides[idx - 1] != side
        states.append(SignalTransition(side=side, is_fresh=is_fresh, bar_index=idx))
    return states


def _build_candles(df: pd.DataFrame) -> list[Candle]:
    """Build Candle objects from required signal-generation dataframe columns."""
    required_columns = {"timestamp", "open", "high", "low", "close"}
    missing = required_columns - set(df.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Missing required columns: {missing_text}")

    candles: list[Candle] = []
    for idx, row in df.iterrows():
        volume = float(row["volume"]) if "volume" in df.columns else 0.0
        timeframe = str(row["timeframe"]) if "timeframe" in df.columns else "5m"
        symbol = str(row["symbol"]) if "symbol" in df.columns else "UNKNOWN"
        candles.append(
            Candle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=pd.Timestamp(row["timestamp"]).to_pydatetime(),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=volume,
            )
        )
    return candles


def generate_signal_states(
    df: pd.DataFrame,
    atr_period: int,
    sensitivity: int,
) -> pd.DataFrame:
    """Generate indicator states and fresh transition signal columns.

    Args:
        df: Candle dataframe with at least timestamp and OHLC columns.
        atr_period: ATR lookback period.
        sensitivity: ATR multiplier used for trailing stop distance.

    Returns:
        DataFrame with timestamp, close, atr, trailing_stop, signal_side,
        buy_signal, and sell_signal columns.
    """
    candles = _build_candles(df)
    atr_values = compute_atr(candles, atr_period)
    trailing_stop, sides = compute_trailing_stop(candles, atr_values, sensitivity)
    transitions = detect_signals(sides)

    return pd.DataFrame(
        {
            "timestamp": df["timestamp"].tolist(),
            "close": [c.close for c in candles],
            "atr": atr_values,
            "trailing_stop": trailing_stop,
            "signal_side": [side.value for side in sides],
            "buy_signal": [
                state.is_fresh and state.side == SignalSide.BUY for state in transitions
            ],
            "sell_signal": [
                state.is_fresh and state.side == SignalSide.SELL for state in transitions
            ],
        }
    )
