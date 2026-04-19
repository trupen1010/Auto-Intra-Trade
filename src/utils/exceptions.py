"""Custom exception hierarchy for the backtest engine."""


class BacktestEngineError(Exception):
    """Base exception for all backtest engine specific errors."""


class LookaheadBiasError(BacktestEngineError):
    """Raised when code attempts to use future data."""


class InsufficientDataError(BacktestEngineError):
    """Raised when available data is insufficient for computation."""


class InvalidCandleError(BacktestEngineError):
    """Raised when candle data fails schema or value validation."""


class ConfigValidationError(BacktestEngineError):
    """Raised when configuration values are invalid."""


class DataGapError(BacktestEngineError):
    """Raised when required candle continuity is broken."""


class PositionSizeError(BacktestEngineError):
    """Raised when valid position size cannot be computed."""


class TradeStateError(BacktestEngineError):
    """Raised when trade state transitions are invalid."""
