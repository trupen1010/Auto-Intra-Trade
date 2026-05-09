"""Exceptions raised by the execution engine."""


class ExecutionError(RuntimeError):
    """Raised when a stage in the backtest pipeline fails.

    This exception wraps underlying validation or processing errors and
    provides context about which stage of the pipeline encountered the issue.
    """

    pass
