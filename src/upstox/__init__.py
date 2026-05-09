"""Upstox API data ingestion module.

This module handles OAuth2 token management and historical candle ingestion
from the Upstox API into the local SQLite database.

Data flows one way: Upstox API → src/upstox/ → SQLite DB → engine

The engine never imports from this module.
"""

from src.upstox.auth import UpstoxTokenStore
from src.upstox.exceptions import UpstoxAPIError
from src.upstox.ingester import ingest_symbol
from src.upstox.transformer import transform_candles

__all__ = ["UpstoxTokenStore", "UpstoxAPIError", "ingest_symbol", "transform_candles"]
