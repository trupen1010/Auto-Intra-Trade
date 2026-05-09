#!/usr/bin/env python3
"""Generate and persist Upstox OAuth2 access token.

This script handles the OAuth2 authorization flow:
  1. Reads UPSTOX_API_KEY, UPSTOX_API_SECRET, UPSTOX_REDIRECT_URI from environment
  2. Prints authorization URL for user to open in browser
  3. Prompts for authorization code from redirect URL
  4. Exchanges code for access token via Upstox API
  5. Saves token to config/upstox_token.json

Usage:
  python scripts/get_upstox_token.py

Environment variables required:
  UPSTOX_API_KEY      OAuth2 application key (get from Upstox dashboard)
  UPSTOX_API_SECRET   OAuth2 application secret
  UPSTOX_REDIRECT_URI Authorized redirect URI (default: http://localhost:8080/callback)
"""

from __future__ import annotations

import json
import os
import sys
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

try:
    import requests
except ImportError:
    print("Error: 'requests' library not installed. Run: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> None:  # type: ignore[misc]
        pass

IST = ZoneInfo("Asia/Kolkata")


def main() -> int:
    """Execute OAuth2 token generation flow.

    Returns:
        0 on success, 1 on failure.
    """
    load_dotenv()

    api_key = os.getenv("UPSTOX_API_KEY")
    api_secret = os.getenv("UPSTOX_API_SECRET")
    redirect_uri = os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:8080/callback")

    if not api_key or not api_secret:
        print("Error: UPSTOX_API_KEY and UPSTOX_API_SECRET environment variables required.")
        print("Set them in a .env file or export them:")
        print("  export UPSTOX_API_KEY=your_key")
        print("  export UPSTOX_API_SECRET=your_secret")
        return 1

    auth_url = "https://api.upstox.com/v2/login/authorization/dialog"
    params = {
        "client_id": api_key,
        "redirect_uri": redirect_uri,
    }
    full_auth_url = f"{auth_url}?{urlencode(params)}"

    print("\n" + "=" * 70)
    print("UPSTOX OAUTH2 AUTHORIZATION")
    print("=" * 70)
    print("\nOpening browser for authorization...")
    print(f"If browser does not open, visit:\n  {full_auth_url}\n")

    webbrowser.open(full_auth_url)

    auth_code = input("Enter authorization code from redirect URL: ").strip()
    if not auth_code:
        print("Error: Authorization code required.")
        return 1

    token_url = "https://api.upstox.com/v2/login/authorization/token"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "code": auth_code,
        "client_id": api_key,
        "client_secret": api_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    try:
        response = requests.post(token_url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error: Failed to exchange authorization code: {e}")
        return 1

    try:
        payload = response.json()
    except ValueError as e:
        print(f"Error: Received non-JSON response: {e}")
        return 1

    access_token = payload.get("access_token")
    expires_in = payload.get("expires_in")

    if not access_token:
        error = payload.get("error", "Unknown error")
        error_desc = payload.get("error_description", "")
        print(f"Error: {error} — {error_desc}")
        return 1

    expires_at = datetime.now(IST) + timedelta(seconds=expires_in or 3600)

    token_file = Path("config/upstox_token.json")
    token_file.parent.mkdir(parents=True, exist_ok=True)

    token_data = {
        "access_token": access_token,
        "expires_at": expires_at.isoformat(),
    }

    with open(token_file, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"\n✓ Token saved to {token_file}")
    print(f"  Expires at: {expires_at.isoformat()}")
    print("\nYou can now run backtests:")
    print("  python -m src.main ingest --symbol NIFTY ...")
    print("\n" + "=" * 70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
