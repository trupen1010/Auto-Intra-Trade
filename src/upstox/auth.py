"""OAuth2 token management for Upstox API."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


class UpstoxTokenStore:
    """Manages Upstox OAuth2 access token persistence and expiration checks.

    Token is stored as JSON: { "access_token": "...", "expires_at": "ISO8601" }

    To obtain a token:
      python scripts/get_upstox_token.py

    This will prompt you to authorize via browser, then save the token locally.
    """

    def __init__(self, token_file: str = "config/upstox_token.json") -> None:
        """Initialize token store.

        Args:
            token_file: Path to JSON file storing the access token and expiration.
        """
        self._token_file = Path(token_file)

    def load(self) -> str | None:
        """Load and validate the stored access token.

        Returns:
            Access token string if valid and not expired, None otherwise.
        """
        if not self._token_file.exists():
            return None

        try:
            with open(self._token_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

        token = data.get("access_token")
        expires_at_str = data.get("expires_at")

        if not token or not expires_at_str:
            return None

        try:
            expires_at = datetime.fromisoformat(expires_at_str).astimezone(IST)
            if datetime.now(IST) >= expires_at:
                return None
        except ValueError:
            return None

        return token

    def save(self, token: str, expires_at: datetime) -> None:
        """Persist access token with expiration timestamp.

        Args:
            token: Access token string from Upstox OAuth flow.
            expires_at: Token expiration datetime (timezone-aware).
        """
        self._token_file.parent.mkdir(parents=True, exist_ok=True)

        expires_at_ist = expires_at.astimezone(IST)
        data = {
            "access_token": token,
            "expires_at": expires_at_ist.isoformat(),
        }

        with open(self._token_file, "w") as f:
            json.dump(data, f, indent=2)

    def is_valid(self) -> bool:
        """Check if a valid non-expired token is stored.

        Returns:
            True if token exists and has not expired, False otherwise.
        """
        return self.load() is not None
