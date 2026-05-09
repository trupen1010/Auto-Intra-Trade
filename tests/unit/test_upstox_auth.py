"""Unit tests for Upstox OAuth2 token management."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from src.upstox.auth import UpstoxTokenStore

IST = ZoneInfo("Asia/Kolkata")


class TestUpstoxTokenStore:
    """Tests for UpstoxTokenStore token persistence."""

    def test_token_store_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """Test saving and loading token roundtrip."""
        token_file = tmp_path / "token.json"
        store = UpstoxTokenStore(str(token_file))

        token = "test_access_token_123"
        expires_at = datetime.now(IST) + timedelta(hours=1)

        store.save(token, expires_at)
        loaded_token = store.load()

        assert loaded_token == token

    def test_token_store_is_valid_true_when_not_expired(self, tmp_path: Path) -> None:
        """Test is_valid returns True for non-expired token."""
        token_file = tmp_path / "token.json"
        store = UpstoxTokenStore(str(token_file))

        token = "test_token"
        expires_at = datetime.now(IST) + timedelta(hours=1)

        store.save(token, expires_at)
        assert store.is_valid() is True

    def test_token_store_is_valid_false_when_expired(self, tmp_path: Path) -> None:
        """Test is_valid returns False for expired token."""
        token_file = tmp_path / "token.json"
        store = UpstoxTokenStore(str(token_file))

        token = "test_token"
        expires_at = datetime.now(IST) - timedelta(minutes=1)

        store.save(token, expires_at)
        assert store.is_valid() is False

    def test_token_store_is_valid_false_when_missing(self, tmp_path: Path) -> None:
        """Test is_valid returns False when token file missing."""
        token_file = tmp_path / "nonexistent" / "token.json"
        store = UpstoxTokenStore(str(token_file))

        assert store.is_valid() is False

    def test_token_store_load_returns_none_when_missing(self, tmp_path: Path) -> None:
        """Test load returns None when token file missing."""
        token_file = tmp_path / "nonexistent" / "token.json"
        store = UpstoxTokenStore(str(token_file))

        assert store.load() is None

    def test_token_store_creates_parent_directory(self, tmp_path: Path) -> None:
        """Test save creates parent directories if missing."""
        token_file = tmp_path / "deep" / "nested" / "token.json"
        store = UpstoxTokenStore(str(token_file))

        token = "test_token"
        expires_at = datetime.now(IST) + timedelta(hours=1)

        store.save(token, expires_at)
        assert token_file.exists()
        assert token_file.parent.exists()
