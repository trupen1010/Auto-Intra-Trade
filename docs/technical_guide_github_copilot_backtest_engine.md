# Technical Guide for GitHub Copilot

Version: 1.0  
Date: 2026-04-19  
Project: Intraday Multi-Timeframe Backtest Engine  
Purpose: Provide enough technical detail, constraints, interfaces, prompts, and acceptance rules so GitHub Copilot can generate the project code in small reliable steps.

---

## 1. Purpose of This Guide

This document is not the business requirement document.
This document is the engineering guide that tells Copilot exactly what to build, what not to build, how modules should talk to each other, and how code should be validated.

The target outcome is a Python codebase that can:
- fetch historical candle data,
- store it in SQLite,
- calculate indicators,
- simulate trades candle by candle,
- apply charges and slippage,
- generate auditable reports.

This phase is backtesting only.
No live trading code should be generated in this phase.

---

## 2. Stack Decision

### 2.1 Language
Use **Python 3.12+**.

### 2.2 Main reasons
- Better numerical and dataframe ecosystem for backtesting.
- Easier candle-by-candle simulation and reporting.
- Strong testing support.
- Easier GitHub Copilot output quality for data-heavy systems.

### 2.3 Core libraries
Use only these libraries in baseline version unless explicitly approved:
- `pandas`
- `numpy`
- `sqlalchemy`
- `pydantic`
- `pyyaml`
- `pytest`
- `python-dotenv`
- `loguru` or standard `logging`
- `requests` or official Upstox SDK adapter layer

Optional later:
- `plotly` for charts
- `jinja2` for HTML reports

Do not use large backtesting frameworks like `backtrader` or `backtesting.py` in baseline version.
We need a custom engine because the logic depends on strict multi-timeframe state handling and custom execution rules.

---

## 3. Project Scope

### 3.1 In scope
- historical data ingestion from Upstox source
- SQLite storage
- candle validation and cleaning
- indicator calculation
- multi-timeframe state generation
- candle-by-candle simulation
- position sizing
- charges and slippage
- trade logs
- summary reports
- unit tests and integration tests

### 3.2 Out of scope
- live trading
- WebSocket streaming
- broker order execution
- portfolio optimization
- UI dashboard
- cloud deployment scripts
- options and futures
- partial profit booking

---

## 4. Engineering Principles

1. All calculations must be reproducible.
2. No lookahead bias is allowed.
3. All signals must come from closed candles only.
4. Every trade must be auditable from stored candles.
5. Keep modules small and testable.
6. Prefer explicit state over hidden dataframe tricks.
7. Use type hints everywhere.
8. Use dataclasses or Pydantic models for clear contracts.
9. Keep business rules in code, not in comments only.
10. Do not mix data fetching, indicator logic, and simulation logic in one file.

---

## 5. Repository Layout

Use this repository structure exactly:

```text
project-root/
├── README.md
├── pyproject.toml
├── .env.example
├── config/
│   ├── settings.yaml
│   └── symbols.yaml
├── docs/
│   ├── requirements_baseline.md
│   └── technical_guide_copilot.md
├── data/
│   ├── raw/
│   ├── processed/
│   └── reports/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── constants.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── candle.py
│   │   ├── signal.py
│   │   ├── trade.py
│   │   ├── report.py
│   │   └── config_models.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── schema.py
│   │   ├── repository.py
│   │   └── sqlite_service.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── upstox_client.py
│   │   ├── fetcher.py
│   │   ├── validator.py
│   │   ├── transformer.py
│   │   └── resampler.py
│   ├── indicators/
│   │   ├── __init__.py
│   │   ├── atr.py
│   │   ├── trailing_stop.py
│   │   ├── signals.py
│   │   └── mtf_state.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── backtest_engine.py
│   │   ├── execution_model.py
│   │   ├── risk_manager.py
│   │   ├── charges.py
│   │   ├── slippage.py
│   │   ├── session_rules.py
│   │   └── trade_manager.py
│   ├── reports/
│   │   ├── __init__.py
│   │   ├── trade_log.py
│   │   ├── metrics.py
│   │   └── exporter.py
│   └── utils/
│       ├── __init__.py
│       ├── datetime_utils.py
│       ├── enums.py
│       └── exceptions.py
└── tests/
    ├── conftest.py
    ├── fixtures/
    ├── unit/
    └── integration/
```

---

## 6. Coding Standards for Copilot

Copilot-generated code must follow these rules:

- Use Python type hints on all public functions.
- Use docstrings on all public classes and functions.
- Keep functions under about 40 lines where possible.
- One responsibility per file.
- No global mutable state.
- No notebook-style code in source files.
- No hidden side effects.
- Raise explicit exceptions for invalid input.
- All timestamps must be timezone-aware and use `Asia/Kolkata` internally.
- Use `Decimal` only if needed for money math; otherwise use float consistently and round only at reporting boundaries.

---

## 7. Domain Models

Copilot should create these core models first.

### 7.1 Candle model
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(slots=True)
class Candle:
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
```

### 7.2 Signal state model
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

SignalSide = Literal["BUY", "SELL", "NEUTRAL"]

@dataclass(slots=True)
class SignalState:
    symbol: str
    timeframe: str
    candle_close_time: datetime
    side: SignalSide
    trailing_stop: float | None
    close_price: float
```

### 7.3 Trade model
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

TradeSide = Literal["LONG", "SHORT"]
EntryTF = Literal["5m", "15m"]
ExitReason = Literal["HARD_SL", "SIGNAL_5M", "SIGNAL_15M", "TIME_EXIT", "DATA_ERROR"]

@dataclass(slots=True)
class Trade:
    trade_id: str
    symbol: str
    side: TradeSide
    entry_tf: EntryTF
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
    exit_reason: ExitReason | None = None
    charges: float = 0.0
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
```

### 7.4 Rejected trade model
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(slots=True)
class RejectedTrade:
    symbol: str
    timestamp: datetime
    timeframe: str
    requested_side: str
    reason: str
```

---

## 8. Configuration Contract

Create a YAML-driven configuration.
The config file must fully control the backtest without code changes.

### 8.1 Example `config/settings.yaml`
```yaml
project:
  timezone: Asia/Kolkata
  initial_capital: 100000.0

data:
  db_path: data/processed/backtest.sqlite3
  use_resample_from_5m: false
  validate_gaps: true
  fail_on_gaps: true

strategy:
  atr_period: 20
  sensitivity: 3
  hard_sl_atr_multiplier: 1.5
  risk_per_trade_pct: 0.01
  allow_short: true
  warmup_bars_5m: 200
  warmup_bars_15m: 100
  warmup_bars_1d: 250

execution:
  entry_model: next_open
  exit_model: next_open
  slippage_pct: 0.0005
  entry_cutoff_time: "15:00"
  forced_exit_time: "15:10"
  one_trade_at_a_time: true
  same_candle_reentry_block: true

charges:
  brokerage_pct: 0.0005
  brokerage_cap_per_order: 20.0
  stt_sell_pct: 0.00025
  transaction_pct: 0.0000297
  gst_pct: 0.18
  sebi_pct: 0.000001
  stamp_duty_buy_pct: 0.00003
```

### 8.2 Config loader requirements
- Validate with Pydantic.
- Fail fast on missing keys.
- Parse times into `datetime.time` objects.
- Support environment variable override for secrets and DB path if needed.

---

## 9. Database Design

Use SQLite for baseline.
Store raw candles, processed candles, signal states, trades, rejected trades, and run summaries.

### 9.1 Tables

#### `candles`
```sql
CREATE TABLE candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    source TEXT,
    UNIQUE(symbol, timeframe, timestamp)
);
```

#### `signals`
```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    candle_close_time TEXT NOT NULL,
    side TEXT NOT NULL,
    trailing_stop REAL,
    close_price REAL NOT NULL,
    UNIQUE(symbol, timeframe, candle_close_time)
);
```

#### `trades`
```sql
CREATE TABLE trades (
    trade_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    entry_tf TEXT NOT NULL,
    entry_signal_time TEXT NOT NULL,
    entry_time TEXT NOT NULL,
    entry_signal_price REAL NOT NULL,
    entry_price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    hard_stop_price REAL NOT NULL,
    exit_signal_time TEXT,
    exit_time TEXT,
    exit_signal_price REAL,
    exit_price REAL,
    exit_reason TEXT,
    charges REAL NOT NULL,
    gross_pnl REAL NOT NULL,
    net_pnl REAL NOT NULL,
    capital_before_trade REAL NOT NULL,
    capital_after_trade REAL NOT NULL
);
```

#### `rejected_trades`
```sql
CREATE TABLE rejected_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    requested_side TEXT NOT NULL,
    reason TEXT NOT NULL
);
```

#### `backtest_runs`
```sql
CREATE TABLE backtest_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    config_snapshot TEXT NOT NULL,
    symbols TEXT NOT NULL,
    date_from TEXT NOT NULL,
    date_to TEXT NOT NULL,
    total_trades INTEGER DEFAULT 0,
    net_profit REAL DEFAULT 0,
    max_drawdown REAL DEFAULT 0
);
```

### 9.2 Indexes
Create indexes on:
- `(symbol, timeframe, timestamp)` for candles
- `(symbol, timeframe, candle_close_time)` for signals
- `(symbol, entry_time)` for trades

---

## 10. Data Pipeline

### 10.1 Step order
The data pipeline must run in this order:

1. Fetch historical candles from Upstox source.
2. Normalize timestamps to `Asia/Kolkata`.
3. Validate schema and numeric fields.
4. Remove duplicates.
5. Detect gaps and out-of-order rows.
6. Store clean candles in SQLite.
7. Build timeframe alignment maps.
8. Only then start indicator and backtest steps.

### 10.2 Fetcher requirements
The fetcher module must:
- fetch per symbol and timeframe,
- support retry with backoff,
- log all API failures,
- avoid duplicate inserts,
- support incremental sync,
- save raw response for debugging if enabled.

### 10.3 Validator requirements
The validator must check:
- missing required columns,
- duplicate timestamps,
- `high < low` invalid bars,
- negative price or volume,
- timestamps outside market hours,
- non-monotonic ordering,
- session gaps.

### 10.4 Gap policy
If `fail_on_gaps` is true, the run must stop and create a validation report.
If false, the run may continue but must mark the affected symbol/date range in the final report.

---

## 11. Indicator Implementation Guide

The baseline engine only needs the ATR trailing-stop signal logic.
Do not implement visual-only Pine Script elements.

### 11.1 ATR function
Create `compute_atr(df: pd.DataFrame, period: int) -> pd.Series`

Requirements:
- use standard true range
- use rolling logic consistent across all timeframes
- return `NaN` until enough bars exist

### 11.2 Trailing stop function
Create:
```python
def compute_atr_trailing_stop(close: pd.Series, atr: pd.Series, sensitivity: int) -> tuple[pd.Series, pd.Series]:
    ...
```

Requirements:
- compute in strict candle order with a Python loop
- output both trailing stop and state side
- side values should be `BUY`, `SELL`, or `NEUTRAL`
- no vectorized shortcut that changes logic

### 11.3 Signal function
Create:
```python
def generate_signal_states(df: pd.DataFrame, atr_period: int, sensitivity: int) -> pd.DataFrame:
    ...
```

Expected output columns:
- `timestamp`
- `close`
- `atr`
- `trailing_stop`
- `signal_side`
- `buy_signal`
- `sell_signal`

### 11.4 Closed-candle rule
Signals become eligible only after the candle is closed.
The execution engine must not use the same candle close as a filled execution unless that execution model is explicitly chosen.
Default is `next_open`.

---

## 12. Multi-Timeframe Alignment Guide

This is the most important logic area.
Copilot must not simplify it incorrectly.

### 12.1 Core rule
At each 5-minute decision point, the engine may only read:
- the latest fully closed 5m signal,
- the latest fully closed 15m signal,
- the latest fully closed 1d signal.

### 12.2 Alignment method
Build helper functions:
```python
def get_latest_closed_state(states_df: pd.DataFrame, as_of: datetime) -> SignalState | None:
    ...

def build_timeframe_state_cache(...) -> dict:
    ...
```

### 12.3 No lookahead rule
Never join higher timeframe rows by nearest future timestamp.
Only use rows where `candle_close_time <= current_5m_time`.

### 12.4 Daily signal rule
Use the last fully closed daily candle only.
A current day's incomplete daily bar must never affect the session.

---

## 13. Entry Logic Guide

Implement entry logic in `trade_manager.py` using pure functions wherever possible.

### 13.1 Long entry from 15m
Open a long trade when all are true:
- no active trade exists,
- entry time is before entry cut-off,
- latest closed 1d state is `BUY`,
- latest closed 15m candle creates a fresh `BUY` signal,
- execution candle is valid,
- quantity after risk sizing is greater than zero.

### 13.2 Long entry from 5m
Open a long trade when all are true:
- no active trade exists,
- entry time is before entry cut-off,
- latest closed 1d state is `BUY`,
- latest closed 15m state is already `BUY`,
- latest closed 5m candle creates a fresh `BUY` signal,
- quantity after risk sizing is greater than zero.

### 13.3 Short entries
Same logic as above, mirrored for `SELL` and short trades.
Only create short entries if config allows shorts.

### 13.4 Fresh signal definition
A fresh signal means the current state crossed into the new side on the just-closed candle.
Do not re-enter repeatedly on every candle that remains in the same state.

### 13.5 Same-candle block
If a trade exits on the current candle, no new trade may open on that same candle.

---

## 14. Exit Logic Guide

### 14.1 Exit priority
Use this fixed order:
1. Hard stop loss
2. Forced time exit
3. Signal-based exit

### 14.2 Hard stop logic
For long:
- if candle low breaches hard stop, exit the trade.

For short:
- if candle high breaches hard stop, exit the trade.

Use configurable execution assumptions for stop fills.
Baseline assumption:
- fill at stop price or next open based on selected execution model.

### 14.3 Signal exits for 15m-origin trade
If `entry_tf = 15m`, exit on:
- fresh opposite 5m signal, or
- fresh opposite 15m signal.

### 14.4 Signal exits for 5m-origin trade
If `entry_tf = 5m`, exit only on:
- fresh opposite 5m signal.

### 14.5 Time exit
Any open trade must be exited at or before forced exit time.
No trade may remain open after session end.

---

## 15. Execution Model Guide

Create an execution module so fill rules are isolated.

### 15.1 Supported execution models in baseline
- `next_open`
- `close_price`

Default: `next_open`

### 15.2 Entry fill
For `next_open`:
- signal forms on closed candle `t`
- order fills on next eligible candle open `t+1`

### 15.3 Exit fill
For `next_open`:
- exit signal forms on closed candle `t`
- order fills on next eligible candle open `t+1`

### 15.4 Slippage
Apply adverse slippage after determining the base fill price.
- long entry: increase price
- long exit: decrease price
- short entry: decrease price
- short exit: increase price

Create a dedicated function:
```python
def apply_slippage(price: float, side: str, action: str, slippage_pct: float) -> float:
    ...
```

---

## 16. Risk Management Guide

### 16.1 Hard stop at entry
Set hard stop immediately at entry based on ATR at signal/entry.
Default:
- long hard stop = `entry_price - 1.5 * atr`
- short hard stop = `entry_price + 1.5 * atr`

### 16.2 Quantity calculation
Create:
```python
def compute_position_size(capital: float, risk_pct: float, entry_price: float, hard_stop_price: float, leverage: float | None = None, max_qty: int | None = None) -> int:
    ...
```

Rules:
- risk amount = `capital * risk_pct`
- stop distance must be `> 0`
- quantity must be floored to integer
- quantity must be capped by leverage/capital constraints if configured
- if quantity is `0`, reject trade

### 16.3 One-trade-at-a-time
Trade manager must enforce a single active trade at strategy level.
Do not allow pyramiding.

---

## 17. Charges Model Guide

Create `charges.py` with one public function:
```python
def calculate_round_trip_charges(buy_turnover: float, sell_turnover: float, config: ChargesConfig) -> float:
    ...
```

Rules:
- brokerage applies per order
- STT applies on sell side only
- GST applies on brokerage + transaction charges
- stamp duty applies on buy side only
- return rounded total charges

Also provide a helper that accepts entry/exit/qty and computes turnover internally.

---

## 18. Reporting Guide

### 18.1 Trade log exporter
Generate CSV for:
- completed trades
- rejected trades
- run summary

### 18.2 Summary metrics function
Create:
```python
def compute_summary_metrics(trades_df: pd.DataFrame, initial_capital: float) -> dict[str, float]:
    ...
```

Required metrics:
- total trades
- wins
- losses
- win rate
- gross profit
- gross loss
- net profit
- average win
- average loss
- profit factor
- expectancy
- total charges
- max drawdown
- average duration
- trades by entry timeframe
- trades by exit reason

### 18.3 Output directory structure
Every run must create a unique folder:
```text
data/reports/{run_id}/
├── trades.csv
├── rejected_trades.csv
├── summary.json
├── config_snapshot.yaml
└── validation_report.json
```

---

## 19. Test Plan for Copilot

Copilot must generate tests alongside code.
Do not defer tests until the end.

### 19.1 Unit tests required
Create unit tests for:
- ATR calculation
- trailing stop logic
- fresh signal detection
- 5m/15m/1d state alignment
- hard stop price calculation
- quantity calculation
- slippage function
- charges function
- forced exit logic
- same-candle re-entry block

### 19.2 Integration tests required
Create integration tests for:
- one symbol, one week, synthetic candles
- long entry from 15m and exit from 5m
- long entry from 5m and exit from 5m
- short trade mirror case
- no-trade when 1d filter disagrees
- forced exit at 15:10
- gap validation failure
- complete backtest run writes expected files

### 19.3 Fixture strategy
Use small deterministic fixtures.
Do not use huge data fixtures in tests.
Synthetic candles are preferred for logic tests because expected output can be asserted exactly.

---

## 20. Copilot Task Sequence

Use this exact generation order.
Do not ask Copilot to generate the entire project at once.

1. Create configuration models and loader.
2. Create domain models.
3. Create SQLite schema and repository layer.
4. Create candle validator and transformer.
5. Create ATR function.
6. Create ATR trailing-stop function.
7. Create signal generation functions.
8. Create timeframe alignment helpers.
9. Create slippage and charges modules.
10. Create risk manager.
11. Create trade manager entry rules.
12. Create trade manager exit rules.
13. Create backtest engine event loop.
14. Create report exporters.
15. Create summary metrics.
16. Add CLI entrypoint.
17. Add unit tests.
18. Add integration tests.

---

## 21. Copilot Prompt Templates

Use these prompts directly in GitHub Copilot Chat.

### 21.1 Prompt for config loader
```text
Create Python Pydantic config models for a backtest engine using the YAML structure below. Add strict validation, parse entry_cutoff_time and forced_exit_time into time objects, and provide a load_settings(path: str) function. Use Python 3.12 type hints and docstrings.
```

### 21.2 Prompt for ATR
```text
Create a pure Python module src/indicators/atr.py with a function compute_atr(df: pd.DataFrame, period: int) -> pd.Series. Input dataframe columns are open, high, low, close. Use standard true range and rolling ATR. Add unit tests for normal data, insufficient data, and invalid columns.
```

### 21.3 Prompt for trailing stop
```text
Create src/indicators/trailing_stop.py for the ATR trailing-stop logic from a Pine Script style recursive rule. Do not vectorize shortcuts. Compute candle by candle in a loop and return trailing_stop, signal_side, buy_signal, sell_signal. Add unit tests with a synthetic dataset where direction flips can be asserted exactly.
```

### 21.4 Prompt for timeframe alignment
```text
Create src/indicators/mtf_state.py with helpers that return the latest fully closed 5m, 15m, and 1d signal states as of a given 5m candle time. Prevent lookahead bias by only allowing candle_close_time <= current_time. Add tests for boundary timestamps.
```

### 21.5 Prompt for trade manager
```text
Create src/engine/trade_manager.py implementing entry and exit decisions for a multi-timeframe intraday strategy. Rules: 1d sets direction, 15m can trigger entry, 5m can trigger entry only when 1d and 15m are already aligned, one trade at a time, no same-candle reversal, 15m-origin trades can exit on 5m or 15m opposite signal, 5m-origin trades exit only on 5m opposite signal, hard stop and forced exit override signal exits. Return structured decision objects and add tests.
```

### 21.6 Prompt for backtest loop
```text
Create src/engine/backtest_engine.py implementing an event-loop backtest over 5-minute candles. At each 5-minute candle, load the latest fully closed 15m and 1d states, evaluate exits first, then entries, execute with next_open fills, apply slippage and charges, update capital, and persist trades and rejected trades. Add integration tests with synthetic candles.
```

### 21.7 Prompt for reports
```text
Create src/reports/exporter.py and src/reports/metrics.py to export completed trades, rejected trades, and summary metrics to CSV and JSON. Include max drawdown, win rate, gross profit, gross loss, net profit, expectancy, total charges, average duration, trades by exit reason, and trades by entry timeframe. Add tests.
```

---

## 22. Anti-Patterns Copilot Must Avoid

Do not generate any of the following:
- a giant single-file script
- hidden lookahead joins
- direct mixing of data fetch and trade simulation in one function
- signal generation using future bars
- repeated re-entry on every candle in same state
- entry and exit on the same candle unless config explicitly allows it
- implicit timezone conversion without tests
- silent exception swallowing
- hardcoded symbol names inside business logic
- hardcoded brokerage values outside config
- rounding P&L too early in the pipeline
- using chart-only Pine variables in core engine logic

---

## 23. Manual Review Checklist

Every Copilot-generated PR must be reviewed against this checklist:

### 23.1 Logic review
- Are only closed candles used?
- Is higher timeframe data aligned without lookahead?
- Is the trailing-stop logic truly recursive?
- Are fresh signals distinguished from ongoing state?
- Are exits evaluated before entries?
- Is same-candle re-entry blocked?

### 23.2 Code review
- Are type hints complete?
- Are tests included?
- Are functions small and readable?
- Are logs useful but not noisy?
- Is error handling explicit?

### 23.3 Output review
- Do trades.csv and summary.json reconcile?
- Can one sample trade be manually reproduced from candle data?
- Are rejected trades recorded with reason?

---

## 24. Definition of Done

A module is done only when:
- code is implemented,
- unit tests pass,
- integration tests pass where relevant,
- mypy-friendly type hints are present,
- docstrings exist,
- config-driven behavior is respected,
- outputs are written to the expected paths,
- no lookahead bias is introduced.

The baseline project is done only when a full backtest run can be executed end to end on at least one symbol and produce a complete trade log and summary report.

---

## 25. Final Instruction to Copilot

Build this project incrementally.
Never rewrite the whole repository in one step.
Generate one module at a time with tests.
When a requirement is ambiguous, choose the option that preserves backtest integrity, auditability, and no-lookahead behavior.
