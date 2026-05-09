"""Exceptions for Upstox API interactions."""

from __future__ import annotations


class UpstoxAPIError(RuntimeError):
    """Raised when Upstox API returns an error response."""

    def __init__(self, status_code: int, body: str) -> None:
        """Initialize API error.

        Args:
            status_code: HTTP status code from Upstox API.
            body: Response body text.
        """
        self.status_code = status_code
        self.body = body
        super().__init__(f"Upstox API error {status_code}: {body}")
