"""CLI entry point for the backtest engine."""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

from src.db.schema import create_all_tables
from src.engine.runner import run_backtest
from src.upstox.auth import UpstoxTokenStore
from src.upstox.client import UpstoxClient
from src.upstox.ingester import ingest_symbol
from src.utils.exceptions import ExecutionError

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool = False, debug: bool = False) -> None:
    """Configure logging based on verbosity flags."""
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )


def _parse_date(date_str: str) -> date:
    """Parse ISO8601 date string."""
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD.")


def _load_config(config_path: str) -> dict:
    """Load JSON configuration file."""
    try:
        with open(config_path) as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"Config file not found: {config_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")


def _run_command(args: argparse.Namespace) -> int:
    """Execute 'run' backtest command."""
    start_date = _parse_date(args.start_date)
    end_date = _parse_date(args.end_date)
    config_dict = _load_config(args.config)

    logger.info(f"Running backtest: {args.symbol} ({start_date} to {end_date})")
    result, output_dir = run_backtest(
        symbol=args.symbol,
        start_date=start_date,
        end_date=end_date,
        config_dict=config_dict,
        db_path=args.db,
    )

    net_pnl = sum(t.net_pnl for t in result.trades if t.net_pnl is not None)

    print()
    print("=" * 60)
    print("BACKTEST COMPLETE")
    print("=" * 60)
    print(f"Run ID:        {result.run_id}")
    print(f"Symbol:        {args.symbol}")
    print(f"Total trades:  {len(result.trades)}")
    print(f"Rejected:      {len(result.rejected_trades)}")
    print(f"Net PnL:       \u20b9{net_pnl:,.2f}")
    print(f"Output dir:    {output_dir}")
    print("=" * 60)
    print()

    return 0


def _ingest_command(args: argparse.Namespace) -> int:
    """Execute 'ingest' candle ingestion command."""
    token_store = UpstoxTokenStore(args.token_file)
    token = token_store.load()

    if not token:
        print("No valid token found. Run: python scripts/get_upstox_token.py", file=sys.stderr)
        return 1

    client = UpstoxClient(token)
    start_date = _parse_date(args.start_date)
    end_date = _parse_date(args.end_date)
    fetch_all = getattr(args, "fetch_all", False)

    if fetch_all:
        logger.info(f"Ingesting all available candles for {args.symbol}")
    else:
        logger.info(f"Ingesting candles for {args.symbol} ({start_date} to {end_date})")

    conn = sqlite3.connect(args.db)
    try:
        create_all_tables(conn)
        results = ingest_symbol(
            symbol=args.symbol,
            instrument_key=args.instrument_key,
            timeframes=["1d", "15m", "5m"],
            start_date=start_date,
            end_date=end_date,
            client=client,
            conn=conn,
            fetch_all_available=fetch_all,
        )
    finally:
        conn.close()

    print()
    print("=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"Symbol:  {args.symbol}")
    for tf, count in results.items():
        print(f"  {tf:3s}: {count} candles")
    print("=" * 60)
    print()

    return 0


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:] if None).
    """
    parser = argparse.ArgumentParser(
        prog="auto-intra-trade",
        description="Backtest intraday multi-timeframe trading strategies",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # 'run' command
    run_parser = subparsers.add_parser("run", help="Run a backtest")
    run_parser.add_argument(
        "--symbol",
        required=True,
        type=str,
        help="Instrument symbol (e.g., NIFTY, SBIN)",
    )
    run_parser.add_argument(
        "--start-date",
        required=True,
        type=str,
        help="Start date in ISO format (YYYY-MM-DD)",
    )
    run_parser.add_argument(
        "--end-date",
        required=True,
        type=str,
        help="End date in ISO format (YYYY-MM-DD)",
    )
    run_parser.add_argument(
        "--config",
        required=True,
        type=str,
        help="Path to JSON configuration file",
    )
    run_parser.add_argument(
        "--db",
        required=True,
        type=str,
        help="Path to SQLite database file",
    )
    run_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable INFO-level logging",
    )
    run_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable DEBUG-level logging",
    )

    # 'ingest' command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest candles from Upstox API")
    ingest_parser.add_argument(
        "--symbol",
        required=True,
        type=str,
        help="Trading symbol (e.g., NIFTY, SBIN)",
    )
    ingest_parser.add_argument(
        "--instrument-key",
        required=True,
        type=str,
        help="Upstox instrument key (e.g., NSE_INDEX|Nifty 50)",
    )
    ingest_parser.add_argument(
        "--start-date",
        required=True,
        type=str,
        help="Start date in ISO format (YYYY-MM-DD)",
    )
    ingest_parser.add_argument(
        "--end-date",
        required=True,
        type=str,
        help="End date in ISO format (YYYY-MM-DD)",
    )
    ingest_parser.add_argument(
        "--db",
        required=True,
        type=str,
        help="Path to SQLite database file",
    )
    ingest_parser.add_argument(
        "--token-file",
        default="config/upstox_token.json",
        help="Path to token file (default: config/upstox_token.json)",
    )
    ingest_parser.add_argument(
        "--fetch-all",
        action="store_true",
        help="Fetch all available data from earliest date (ignores --start-date and --end-date)",
    )
    ingest_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable INFO-level logging",
    )
    ingest_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable DEBUG-level logging",
    )

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    try:
        verbose = getattr(args, "verbose", False)
        debug = getattr(args, "debug", False)
        _setup_logging(verbose, debug)

        if args.command == "run":
            return _run_command(args)
        elif args.command == "ingest":
            return _ingest_command(args)
        else:
            parser.print_help()
            return 1

    except (ValueError, ExecutionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.exception("Unexpected error")
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
