# Auto-Intra-Trade

A Python 3.12+ backtest engine for testing intraday multi-timeframe trading strategies on Indian equity market data. Implements ATR-based trailing stop signals across three timeframes (1D, 15m, 5m) with strict risk management, realistic execution assumptions, and comprehensive charges modeling.

## Requirements

- **Python 3.12+**
- **SQLite** (included with Python)
- See `requirements.txt` for dependencies

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run a Backtest

```bash
python -m src.main run \
  --symbol NIFTY \
  --start-date 2024-01-01 \
  --end-date 2024-03-31 \
  --config config/sample_config.json \
  --db data/candles.db
```

### 3. View Results

Backtest results are written to `data/reports/{run_id}/`:
- **trades.csv** — Closed trades with entry/exit details and PnL
- **rejected_trades.csv** — Rejected entry attempts
- **summary.json** — Run-level statistics (win rate, max drawdown, final capital)
- **config_snapshot.json** — Configuration snapshot (excludes runtime arrays)

## CLI Options

```
usage: auto-intra-trade run [options]

required arguments:
  --symbol SYMBOL          Instrument symbol (e.g., NIFTY, SBIN)
  --start-date DATE        Start date in ISO format (YYYY-MM-DD)
  --end-date DATE          End date in ISO format (YYYY-MM-DD)
  --config PATH            Path to JSON configuration file
  --db PATH                Path to SQLite database file

optional arguments:
  --verbose                Enable INFO-level logging
  --debug                  Enable DEBUG-level logging
  -h, --help               Show help message
```

### Example with Logging

```bash
python -m src.main run \
  --symbol SBIN \
  --start-date 2024-01-01 \
  --end-date 2024-02-29 \
  --config config/sample_config.json \
  --db data/candles.db \
  --verbose
```

## Configuration

Configuration is supplied as a JSON file. See `config/sample_config.json` for an example with realistic Zerodha intraday charges:

```json
{
  "initial_capital": 500000,
  "risk_per_trade_pct": 0.01,
  "sl_atr_multiplier": 1.5,
  "atr_period": 14,
  "atr_sensitivity": 1,
  "entry_cutoff_time": "15:00",
  "session_end_time": "15:15",
  "charges": {
    "brokerage_pct": 0.0003,
    "brokerage_cap_per_order": 20.0,
    "stt_sell_pct": 0.00025,
    "transaction_pct": 0.0000345,
    "sebi_pct": 0.000001,
    "gst_pct": 0.18,
    "stamp_duty_buy_pct": 0.00015
  }
}
```

## Repository Structure

```
Auto-Intra-Trade/
├── src/
│   ├── data/              # Upstox API adapter, candle fetching, validation, transformation
│   ├── db/                # SQLite schema, repository layer
│   ├── engine/            # Risk sizing, charges, trade state, simulation, execution
│   ├── indicators/        # ATR, trailing stop, signal detection, multi-timeframe alignment
│   ├── models/            # Domain dataclasses (Candle, Trade, Config, etc.)
│   ├── reports/           # Report generation (CSV/JSON export)
│   ├── utils/             # Enums, exceptions, datetime helpers
│   ├── config.py          # Pydantic config loader
│   ├── main.py            # CLI entry point
│   └── __main__.py        # Allow python -m src
├── tests/
│   ├── unit/              # Unit tests by module
│   └── integration/       # Integration tests
├── config/                # YAML/JSON configuration files
│   └── sample_config.json # Example config with realistic charges
├── data/
│   ├── reports/           # Backtest output directory (run_id)
│   └── candles.db         # SQLite candle database
├── requirements.txt       # Python dependencies
├── pytest.ini             # pytest configuration
└── README.md              # This file
```

## Architecture

### Data Pipeline

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

- **1D (daily)**: Sets directional bias only. Uses only the last fully closed daily candle.
- **15m**: Can trigger entry when 1D side agrees. Uses latest fully closed 15m candle.
- **5m**: Drives the main event loop. Can trigger entry only when 1D and 15m are aligned.

**Critical rule**: No lookahead bias. A higher-timeframe candle is available only after its close time has passed.

### Module Responsibilities

| Module | Responsibility |
|--------|-----------------|
| `src/data/` | Fetch candles from Upstox, validate, transform, write to SQLite |
| `src/indicators/` | Compute ATR, trailing stops, signal states, multi-timeframe alignment |
| `src/engine/` | Risk sizing, charges, trade state models, candle-by-candle simulation |
| `src/models/` | Domain dataclasses (immutable, no logic) |
| `src/reports/` | Format trades/rejections, calculate summary statistics, write CSV/JSON |
| `src/utils/` | Pure utilities (datetime, enums, exceptions) |

## Testing

Run all tests:

```bash
pytest
```

Run specific test file:

```bash
pytest tests/unit/test_atr.py -v
```

Run with coverage:

```bash
pytest --cov=src tests/
```

## Key Design Principles

1. **Specification-first**: Design and logic flow from the requirements baseline, not assumptions.
2. **No lookahead bias**: The backtest never peeks at future candles.
3. **Auditability**: Every trade is reproducible from stored candles and config.
4. **Narrow modules**: One responsibility per module, testable in isolation.
5. **Type safety**: Full type hints enable early error detection.
6. **Timezone consistency**: All times in `Asia/Kolkata`, all storage as ISO 8601 with offset.
7. **Configuration isolation**: Config values flow as arguments; business logic never reads config directly.

## Simulation Rules (Non-Negotiable)

| Rule | Enforcement |
|------|-------------|
| **No lookahead bias** | Only use candles where `close_time <= current_eval_time` |
| **Closed-candle signals only** | Signal detected on closed bar; entry/exit on next candle |
| **Exit before entry** | Evaluate exits first, then entries each 5m bar |
| **Hard SL mandatory** | Computed at entry from ATR, checked before other exits |
| **Exit priority** | `HARD_SL` → `TIME_EXIT` → signal exit |
| **One trade at a time** | No pyramiding, no simultaneous positions |
| **No same-candle reversal** | After exit on candle T, new entry not before T+1 |
| **1D bias constraint** | 1D BUY = LONG only; 1D SELL = SHORT only |
| **Forced exit time** | Close all trades at or before entry cutoff time |
| **Position size validation** | Reject trade if computed quantity == 0 |

## Output Format

Each backtest run produces a report directory with:

1. **trades.csv** — Closed trades (see columns in writer.py)
2. **rejected_trades.csv** — Rejected entry attempts
3. **summary.json** — Run-level statistics:
   - Total trades, winning trades, losing trades
   - Win rate %, gross PnL, total charges, net PnL
   - Max drawdown, average trade PnL, largest win/loss
   - Initial capital, final capital
4. **config_snapshot.json** — Full config (for audit trail)

## Documentation

For complete technical details:
- See **`.github/copilot-instructions.md`** for full specification
- See **`docs/backtest_engine_requirements_baseline.md`** for business rules
- See **`CLAUDE.md`** for architecture and patterns

## Development

To run a single test during development:

```bash
pytest tests/unit/test_atr.py::test_atr_basic -v
```

To check types (if mypy installed):

```bash
python -m mypy src/
```

## License

Proprietary.
