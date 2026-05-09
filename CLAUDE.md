# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**Auto-Intra-Trade** is a Python 3.12+ backtest engine for testing intraday multi-timeframe trading strategies on Indian equity market data. It implements ATR-based trailing stop signals across three timeframes (1D, 15m, 5m) with strict risk management, realistic execution assumptions, and charges modeling.

The project is **specification-first**: the source of truth is in `docs/backtest_engine_requirements_baseline.md` and `.github/copilot-instructions.md`. See those files for complete trading logic, module contracts, and non-negotiable simulation rules (especially no-lookahead bias and strict timezone handling).

**Not in scope**: live order placement, WebSocket streaming, web UI, portfolio management, derivatives, scaling in/out, or cloud deployment.

---

## Repository Structure

```
src/
├── data/           # Upstox API adapter, candle fetching, validation, transformation
├── db/             # SQLite schema, repository layer, session management
├── engine/         # Risk sizing, charges, trade state models
├── indicators/     # ATR, trailing stop, signal detection, multi-timeframe alignment
├── models/         # Domain dataclasses (Candle, Trade, SignalState, RejectedTrade)
├── upstox/         # OAuth2 token management, API data ingestion (separate from engine)
├── utils/          # Enums, exceptions, datetime helpers
├── reports/        # Trade/rejected trade formatting, summary building, CSV/JSON export
└── config.py       # Pydantic config loader (reads YAML)

scripts/
├── get_upstox_token.py  # Standalone OAuth2 authorization script

tests/unit/        # Unit tests by module
tests/integration/  # Integration tests (full pipelines)
docs/              # Requirements baseline, technical guide, TradingView reference
config/            # JSON/YAML configuration files
```

---

## Quick Start

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run tests
```bash
# All tests
pytest

# Single test file
pytest tests/unit/test_atr.py

# With verbose output
pytest -v

# With coverage
pytest --cov=src tests/
```

### Key Commands

| Task | Command |
|------|---------|
| Run all tests | `pytest` |
| Run single test module | `pytest tests/unit/test_atr.py` |
| Run specific test | `pytest tests/unit/test_atr.py::test_atr_basic` |
| Watch mode (requires pytest-watch) | `ptw` |
| Check types | `python -m mypy src/` (if mypy installed) |

### Configuration
- YAML config file: `config/` directory (referenced in `src/config.py`)
- Config model: `src/models/config_models.py`
- Charges formula: hardcoded in config only, computed in `src/engine/charges.py`

---

## Architecture and Design Principles

### The Data Pipeline

```
Upstox API → Fetch candles → Validate → Transform → SQLite storage
           ↓
      Compute ATR, trailing stop, signal states (per timeframe)
           ↓
      Align multi-timeframe states (no lookahead)
           ↓
      5m-driven event loop: check exits → check entries → log trades
           ↓
      Apply slippage, charges, capital updates
           ↓
      Export trades, rejected trades, metrics → CSV/JSON
```

### Multi-Timeframe Logic
- **1D (daily)**: Sets directional bias only. Uses **only the last fully closed daily candle** (never the in-session partial candle).
- **15m**: Can trigger entry when 1D side agrees. Uses latest fully closed 15m candle.
- **5m**: Drives the main event loop. Can trigger entry only when 1D and 15m are aligned.

**Critical rule**: No lookahead bias. A higher-timeframe candle is available only after its `close_time` has passed.

### Upstox Data Ingestion (Separate Module)

The `src/upstox/` module is **completely isolated from the backtest engine**. Data flows one-way: Upstox API → src/upstox/ → SQLite → engine reads via src/db/.

**The engine never imports from src/upstox/.**

Ingestion pipeline:
```
Upstox API (HTTP)
      ↓
UpstoxClient.fetch_historical_candles() [HTTP adapter, no business logic]
      ↓
ingest_symbol() [orchestrate three timeframes: 1d, 15m, 5m]
      ↓
For each timeframe:
  1. transform_candles() [raw API dict → Candle domain model]
  2. validate_candle_sequence() [schema, gaps, market hours]
  3. CandleRepository.insert_candles() [upsert to SQLite]
      ↓
Returns: dict[timeframe -> candle_count]
```

**Token management:**
- `UpstoxTokenStore`: Persist OAuth2 token to JSON with expiration
- `scripts/get_upstox_token.py`: Standalone script for browser-based authorization flow
- Token stored as: `{ "access_token": "...", "expires_at": "ISO8601" }`

**CLI entry point:**
```bash
python -m src.main ingest \
  --symbol NIFTY --instrument-key "NSE_INDEX|Nifty 50" \
  --start-date 2024-01-01 --end-date 2024-03-31 \
  --db data/candles.db --token-file config/upstox_token.json
```

### Module Contracts (See `.github/copilot-instructions.md` § 7 for complete list)

| Module | Responsibility |
|--------|-----------------|
| `src/data/upstox_client.py` | HTTP adapter for Upstox API — no business logic |
| `src/data/fetcher.py` | Orchestrate fetch and write raw candles to DB |
| `src/data/validator.py` | Schema checks, gap detection, session-hour filtering |
| `src/data/transformer.py` | Timestamp normalization to `Asia/Kolkata`, field casting |
| `src/upstox/auth.py` | OAuth2 token persistence and validation |
| `src/upstox/ingester.py` | Orchestrate candle fetch, transform, validate, insert (three timeframes) |
| `src/upstox/transformer.py` | Convert raw Upstox API candles to Candle domain models |
| `src/indicators/atr.py` | ATR computation only |
| `src/indicators/trailing_stop.py` | Recursive ATR trailing stop (must use for-loop, not vectorized) |
| `src/indicators/signals.py` | Generate signal states (BUY/SELL/NEUTRAL) from trailing stop |
| `src/indicators/mtf_state.py` | Get latest closed state at a given timestamp (anti-lookahead guard) |
| `src/engine/charges.py` | Round-trip charges calculation (brokerage, STT, NSE, GST, SEBI, stamp duty) |
| `src/engine/position.py` | Position size calculation from ATR and risk % |
| `src/engine/risk.py` | Hard stop price computation from ATR sensitivity |
| `src/engine/trade_state.py` | Trade and RejectedTrade domain models |
| `src/reports/trade_formatter.py` | Convert trades to CSV-ready dictionaries |
| `src/reports/summary_builder.py` | Aggregate run-level statistics (PnL, win rate, max drawdown) |
| `src/reports/writer.py` | Write trades, rejected trades, summary, config to CSV/JSON |
| `src/models/` | Dataclass/Pydantic domain models only — no logic |
| `src/utils/` | Pure utilities — datetime, enums, exceptions |

---

## Critical Simulation Rules

These rules are **non-negotiable** and must be enforced in any changes to the backtest engine:

| Rule | Enforcement |
|------|-------------|
| **No lookahead bias** | Only use candles where `candle_close_time <= current_eval_time` for higher timeframes |
| **Closed-candle signals only** | Signal detected on closed bar; entry/exit on next candle (or at `next_open` model) |
| **Exit before entry** | At each 5m bar, evaluate exits first, then entries |
| **Hard SL mandatory** | Compute at entry from ATR. Check on every subsequent bar before other exits |
| **Exit priority** | `HARD_SL` → `TIME_EXIT` → signal exit |
| **One trade at a time** | Block new entries while `active_trade is not None` |
| **No same-candle reversal** | After exit on candle T, no new entry until candle T+1 or later |
| **1D bias constraint** | 1D BUY = only LONG entries; 1D SELL = only SHORT entries |
| **Forced exit time** | Close all open trades at or before 15:10 IST |
| **Position size validation** | Reject trade if computed quantity == 0 |

---

## Timezone Rules

- **Storage**: All timestamps in SQLite as ISO 8601 strings with offset: `2024-01-15T09:20:00+05:30`
- **Python**: All `datetime` objects must be timezone-aware with `zoneinfo.ZoneInfo("Asia/Kolkata")`
- **Do not use**: `pytz` — use `zoneinfo` instead
- **Market hours**: 09:15 IST to 15:30 IST (reject candles outside this range during validation)
- **Helpers**: `src/utils/datetime_utils.py` provides `to_ist()`, `is_market_hours()`, `is_same_session()`

---

## Data Models

### Candle
```python
@dataclass(slots=True)
class Candle:
    symbol: str
    timeframe: str          # "1d", "15m", "5m"
    timestamp: datetime     # timezone-aware, Asia/Kolkata
    open: float
    high: float
    low: float
    close: float
    volume: float
```

### SignalState
```python
@dataclass(slots=True)
class SignalState:
    symbol: str
    timeframe: str
    candle_close_time: datetime
    side: Literal["BUY", "SELL", "NEUTRAL"]
    trailing_stop: float | None
    close_price: float
```

### Trade
```python
@dataclass(slots=True)
class Trade:
    trade_id: str
    symbol: str
    side: Literal["LONG", "SHORT"]
    entry_tf: Literal["5m", "15m"]
    entry_signal_time: datetime
    entry_time: datetime
    entry_signal_price: float
    entry_price: float
    quantity: int
    hard_stop_price: float
    exit_signal_time: datetime | None = None
    exit_time: datetime | None = None
    exit_signal_price: float | None = None
    exit_price: float | None = None
    exit_reason: Literal["HARD_SL", "SIGNAL_5M", "SIGNAL_15M", "TIME_EXIT", "DATA_ERROR"] | None = None
    charges: float = 0.0
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    capital_before_trade: float = 0.0
    capital_after_trade: float = 0.0
```

### RejectedTrade
```python
@dataclass(slots=True)
class RejectedTrade:
    symbol: str
    timestamp: datetime
    timeframe: str
    requested_side: str
    reason: str
```

---

## Code Style and Standards

- **Python version**: 3.12+
- **Type hints**: On all public functions and class attributes (required)
- **Docstrings**: Google style on all public classes and functions
- **Function length**: Aim for ~40 lines max
- **One responsibility**: One class or cohesive group per file
- **Domain models**: Use `@dataclass(slots=True)` for efficiency
- **Exceptions**: Raise named exceptions from `src/utils/exceptions.py` (no bare `Exception`)
- **Configuration**: Flow from `config.py` into functions as arguments — never read config inside business logic modules
- **Logging**: Use standard `logging` library, not `print` for operational output
- **Constrained strings**: Use `Literal` for enum-like string values
- **No global mutable state**

---

## Testing

Tests are located in `tests/unit/` and organized by module. Every source module should have a corresponding test file.

### Running tests
```bash
pytest                      # All tests
pytest -v                   # Verbose
pytest tests/unit/test_atr.py  # Single file
pytest -k test_atr_basic    # By test name pattern
```

### Test expectations

**Unit tests** must cover:
- ATR output against known input
- Trailing stop output for synthetic datasets with direction flips
- MTF state boundary conditions (candle exactly at `as_of` time must be included)
- Hard stop price for LONG and SHORT
- Position size for normal case, zero-distance SL, and zero-result case
- Slippage applied correctly for all four combinations (buy/sell × entry/exit)
- Charges calculation against known turnover

**Integration tests** must cover:
- Full single-symbol single-week run with synthetic data
- 15m-origin LONG trade exiting on 5m signal
- 5m-origin LONG trade exiting on time exit
- SHORT trade mirror cases
- No trade when 1D side disagrees
- Rejected trade log populated correctly
- Report files written to correct paths

### Fixture guidelines
- Use deterministic synthetic candles for logic tests (no large CSV fixtures in repo)
- Mock all Upstox adapter calls — no real API calls in tests
- Timezone-aware fixtures: use `zoneinfo.ZoneInfo("Asia/Kolkata")`

---

## Important Files to Read

**Before making changes:**
1. `.github/copilot-instructions.md` (§ 1–20) — **complete contract for this project**
2. `docs/backtest_engine_requirements_baseline.md` (business rules, exit strategies)
3. `docs/technical_guide_github_copilot_backtest_engine.md` (architecture, execution model)

**For reference:**
- `docs/tradingview.code.md` — Original Pine Script (reference only; visual elements not ported)
- `src/models/` — Review data model definitions before adding new fields
- `src/engine/charges.py` — Charges formula (hardcoded nowhere else)

---

## Common Patterns and Anti-Patterns

### ✅ DO
- Use `zoneinfo.ZoneInfo("Asia/Kolkata")` for all timezone operations
- Filter multi-timeframe states with `<=` (inclusive boundary for no lookahead)
- Enforce "closed-candle signal only" in entry/exit logic
- Use for-loops in `trailing_stop.py` (recursive dependency on previous bar)
- Pass config values as function arguments (config flows in, business logic has no knowledge of config source)
- Test with synthetic deterministic candles

### ❌ DON'T
- Vectorize the trailing stop (`close - nLoss` is wrong — loses recursion)
- Resample 5m to 15m without `.shift(1)` (lookahead bias)
- Re-enter on every bar with the same signal (must be a fresh crossover)
- Hardcode charges, risk %, entry cutoff, or other config values in business logic
- Use `pytz` (use `zoneinfo` instead)
- Port visual elements from Pine Script (plot, colors, alerts, shapes)
- Merge pipeline stages (fetch + compute + simulate in one function)
- Create timestamps in UTC and convert later (create as `Asia/Kolkata` from the start)

---

## Configuration

Configuration is managed via:
- **Schema**: `src/models/config_models.py` (Pydantic models)
- **Loader**: `src/config.py` (reads YAML and returns config object)
- **YAML files**: `config/settings.yaml` and environment-specific overrides
- **Charges formula**: See `.github/copilot-instructions.md` § 11

All charge parameters (brokerage %, STT %, NSE %, etc.) are defined in config only. The `src/engine/charges.py` module implements the formula but reads no config directly.

---

## Example Workflow

### Running a single test during development
```bash
pytest tests/unit/test_atr.py::test_atr_basic -v
```

### Running tests with coverage
```bash
pytest --cov=src --cov-report=html tests/
```

### Adding a new feature
1. Read the relevant section in `.github/copilot-instructions.md`
2. Add test cases first (test-driven development recommended)
3. Implement the feature in the correct module (see module contracts)
4. Run `pytest` to verify all tests pass
5. Verify no lookahead bias was introduced
6. Ensure all timestamps are timezone-aware `Asia/Kolkata`

---

## External References

- **Pydantic documentation**: https://docs.pydantic.dev/ (data validation)
- **Pandas documentation**: https://pandas.pydata.org/ (data manipulation, time-series)
- **Python zoneinfo**: https://docs.python.org/3/library/zoneinfo.html (timezone handling)
- **pytest documentation**: https://docs.pytest.org/ (testing framework)

---

## Key Principles

1. **Specification-first**: Design and logic come from the requirements baseline and copilot instructions, not from assumptions.
2. **No lookahead bias**: The backtest must never peek at future candles. This is more important than any other rule.
3. **Auditability**: Every trade must be reproducible from stored candles and config.
4. **Narrow modules**: One responsibility per module. Each module can be tested in isolation.
5. **Type safety**: Full type hints enable early error detection and IDE support.
6. **Timezone consistency**: All times in `Asia/Kolkata`, all storage as ISO 8601 with offset.
7. **Configuration isolation**: Config values flow in as arguments; business logic never reads config directly.

---

## When in Doubt

1. Check `.github/copilot-instructions.md` first (it is the complete contract).
2. Check the requirements baseline for business rules.
3. Check existing tests in `tests/unit/` for patterns.
4. Check the git history (`git log -p`) for context on similar changes.
5. Reach out if the requirements conflict or are ambiguous.
