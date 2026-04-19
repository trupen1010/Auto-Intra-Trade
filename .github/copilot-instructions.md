# Copilot Instructions for Auto-Intra-Trade

> This file is the **Copilot agent rulebook** for this repository.
> It extends the two baseline documents (`backtest_engine_requirements_baseline.md` and
> `technical_guide_github_copilot_backtest_engine.md`) with strict generation rules,
> module-level contracts, and a working session protocol.
> Read this file **before** reading any source file. Follow every rule below without exception.

***

## 1. Repository Reality

This repository is **specification-first**. The source of truth is:

| File | Role |
|---|---|
| `docs/backtest_engine_requirements_baseline.md` | Business rules, trading logic, exit rules, charges |
| `docs/technical_guide_github_copilot_backtest_engine.md` | Architecture, module layout, interfaces, task sequence |
| `docs/tradingview.code.md` | Original Pine Script (reference only — do not port visual elements) |

**Never invent features not described in those three files.**
If you are unsure whether something is in scope, check the out-of-scope list in the requirements baseline before generating.

***

## 2. Hard Scope Boundary

The baseline scope is a **Python 3.12+ backtest engine only.**

**This project does NOT include:**
- Live broker order placement
- WebSocket or streaming connections
- Upstox order API calls
- A web dashboard or UI
- Multi-asset portfolio management
- Options or futures instruments
- Partial profit booking or scaling in/out
- Cloud deployment scripts

If a task would require any of the above, **refuse and explain what is out of scope.**

***

## 3. The Exact Pipeline

Generate code only along this pipeline boundary. Nothing outside of it belongs in baseline.

```
Upstox adapter/fetcher layer
          |
          v
  Candle validator + transformer
          |
          v
    SQLite storage layer
          |
          v
  Indicator computation (ATR, ATR trailing stop, signal states)
          |
          v
  Multi-timeframe state alignment (1D / 15m / 5m)
          |
          v
  Candle-by-candle backtest simulation loop
  (entry rules → exit rules → execution model → slippage → charges → capital update)
          |
          v
  Trade log + rejected trades + run summary → CSV/JSON reports
```

***

## 4. Strategy Boundary

Only the **ATR trailing-stop signal logic** from the Pine Script is in scope.
Everything else in the Pine Script is a visual element and must NOT be ported.

**Retained from Pine Script:**
- `ATR(period=20)` computation
- `nLoss = keyvalue * ATR` (keyvalue default 3)
- Recursive ATR trailing-stop (`xATRTrailingStop`) candle-by-candle state
- Crossover of `close` above trailing stop → Buy signal
- Crossunder of `close` below trailing stop → Sell signal
- Position state tracking (`pos`)

**Explicitly excluded from the engine (visual-only Pine elements):**
- All `plot()`, `plotshape()`, `fill()`, `barcolor()`
- `ma_fill_color`, `ma_color`, all MA visuals
- `bodyMiddle`, `upTrend`, `downTrend` SuperTrend plots
- `alert()` messages
- Bollinger Bands calculations (no role in baseline trade rules)
- Any `offset`, `style`, `color`, `textcolor`, `size` Pine arguments

***

## 5. The Timeframe Contract

This is the most critical logic rule. Get this wrong and the backtest is invalid.

```
1D  → sets the directional bias only
       └── only use the LAST FULLY CLOSED daily candle (previous trading day close)
           never use the current in-session partially formed daily candle

15m → can trigger a trade entry when 1D side agrees
       └── only read the latest fully closed 15m candle at decision time

5m  → can trigger a trade entry ONLY when 1D and 15m are BOTH already aligned
       └── the 5m event loop is the main simulation clock
           at each 5m candle: check what 15m and 1D states have closed <= current_5m_candle_time
```

**No lookahead is ever acceptable.**
A higher-timeframe bar is available only after its close timestamp has passed.

***

## 6. Critical Simulation Rules

These rules are non-negotiable. Every generated simulation module must enforce all of them.

| Rule | Enforcement |
|---|---|
| No lookahead bias | Only `candle_close_time <= current_5m_time` for higher TF lookups |
| Closed-candle signals only | Detect signal on closed bar; execute at next candle open by default |
| Exit before entry at each bar | Always evaluate exits first, then entries, in the event loop |
| Hard SL is mandatory | Compute hard stop at entry from ATR; check on every subsequent bar |
| Exit priority order | `HARD_SL` → `TIME_EXIT` → signal exit |
| One trade at a time | Block new entries while `active_trade is not None` |
| No same-candle reversal | After exit on candle T, no new entry until candle T+1 or later |
| No opposite-side entry against 1D | 1D BUY = only LONG entries allowed; 1D SELL = only SHORT entries allowed |
| Forced exit time | Close all open trades at or before 15:10 IST regardless of signal state |
| Position size validation | Reject trade if computed quantity == 0; log to rejected_trades |

***

## 7. Module Contracts

When generating any source file, use these exact module boundaries.
Do not merge responsibilities across boundaries.

| Module | Single responsibility |
|---|---|
| `src/data/upstox_client.py` | HTTP adapter for Upstox API only — no business logic |
| `src/data/fetcher.py` | Orchestrates fetch per symbol/timeframe, writes raw to DB |
| `src/data/validator.py` | Schema checks, gap detection, duplicate removal, session-hour filtering |
| `src/data/transformer.py` | Timestamp normalization to `Asia/Kolkata`, OHLCV field casting |
| `src/data/resampler.py` | Optional: resample 5m to 15m/1D if not fetching natively |
| `src/indicators/atr.py` | `compute_atr(df, period)` only |
| `src/indicators/trailing_stop.py` | Recursive ATR trailing stop and position state — loop-based only |
| `src/indicators/signals.py` | `generate_signal_states(df, atr_period, sensitivity)` |
| `src/indicators/mtf_state.py` | `get_latest_closed_state(states_df, as_of_datetime)` — no-lookahead alignment |
| `src/engine/backtest_engine.py` | The main event loop — wires everything together |
| `src/engine/execution_model.py` | Fill price logic for `next_open` and `close_price` models |
| `src/engine/risk_manager.py` | Hard stop price + position size calculation |
| `src/engine/charges.py` | `calculate_round_trip_charges(buy_turnover, sell_turnover, config)` |
| `src/engine/slippage.py` | `apply_slippage(price, side, action, slippage_pct)` |
| `src/engine/session_rules.py` | Candle validity, entry cut-off time, forced exit time checks |
| `src/engine/trade_manager.py` | Entry and exit decision logic using closed-bar states |
| `src/reports/trade_log.py` | Trade and rejected trade data formatting |
| `src/reports/metrics.py` | Summary metric calculations from completed trade list |
| `src/reports/exporter.py` | CSV + JSON file writing to `data/reports/{run_id}/` |
| `src/db/schema.py` | SQLAlchemy table definitions only |
| `src/db/repository.py` | DB read/write functions — no business logic |
| `src/config.py` | Pydantic config loader from YAML |
| `src/models/` | Dataclass/Pydantic domain models only — no logic |
| `src/utils/` | Pure utility functions — datetime helpers, enums, custom exceptions |

***

## 8. Data Model Contracts

Use these exact models. Do not add fields silently. Changes to models require explicit instruction.

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
    candle_close_time: datetime   # timezone-aware, Asia/Kolkata
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
    state_1d_at_entry: str = ""
    state_15m_at_entry: str = ""
    state_5m_at_entry: str = ""
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

***

## 9. Indicator Implementation Contracts

### ATR (atr.py)
- Signature: `compute_atr(df: pd.DataFrame, period: int) -> pd.Series`
- Input must have `high`, `low`, `close` columns
- Return `NaN` for first `period - 1` rows
- Do not use any external TA library — implement true range and rolling mean directly

### ATR Trailing Stop (trailing_stop.py)
- Signature: `compute_atr_trailing_stop(close: pd.Series, atr: pd.Series, sensitivity: int) -> tuple[pd.Series, pd.Series]`
- Returns `(trailing_stop_series, signal_side_series)`
- Signal side values are string `"BUY"`, `"SELL"`, `"NEUTRAL"`
- **MUST use a Python for-loop.** Do not vectorize. The value depends on its own previous bar.
- This is the most critical function in the codebase. It must exactly replicate the Pine Script `xATRTrailingStop` logic.

The Pine Script reference:
```pinescript
iff_1 = src > nz(xATRTrailingStop[1], 0) ? src - nLoss : src + nLoss
iff_2 = src < nz(xATRTrailingStop[1], 0) and src[1] < nz(xATRTrailingStop[1], 0)
        ? math.min(nz(xATRTrailingStop[1]), src + nLoss) : iff_1
xATRTrailingStop := src > nz(xATRTrailingStop[1], 0) and src[1] > nz(xATRTrailingStop[1], 0)
                    ? math.max(nz(xATRTrailingStop[1]), src - nLoss) : iff_2
```

### MTF Alignment (mtf_state.py)
- Signature: `get_latest_closed_state(states_df: pd.DataFrame, as_of: datetime) -> SignalState | None`
- Filter: `states_df[states_df["candle_close_time"] <= as_of]`
- Return the row with the latest `candle_close_time` or `None` if empty
- This function is the primary anti-lookahead guard — never relax the `<=` filter

***

## 10. Entry and Exit Logic Contracts

### Long Entry from 15m Trigger
All of the following must be true:
1. `active_trade is None`
2. `current_time < entry_cutoff_time`
3. Latest closed 1D state is `BUY`
4. Latest closed 15m candle has a **fresh** `BUY` signal (state changed to BUY on this exact candle)
5. Computed quantity > 0
6. Current candle is not the same candle as the last exit

Tag result: `entry_tf = "15m"`

### Long Entry from 5m Trigger
All of the following must be true:
1. `active_trade is None`
2. `current_time < entry_cutoff_time`
3. Latest closed 1D state is `BUY`
4. Latest closed 15m state is `BUY` (already active — not necessarily fresh)
5. Latest closed 5m candle has a **fresh** `BUY` signal
6. Computed quantity > 0
7. Current candle is not the same candle as the last exit

Tag result: `entry_tf = "5m"`

### Short entries
Mirror exactly, with `SELL` and `SHORT`.

### Fresh signal definition
A signal is **fresh** only when the state on the current bar is different from the state on the previous bar (i.e., a crossover or crossunder just happened). Do not re-enter on every bar that stays in the same side.

### Exit priority at each 5m bar
```
1. Check hard stop first:
   - LONG: if candle.low <= hard_stop_price → exit at hard_stop_price (or next_open if model)
   - SHORT: if candle.high >= hard_stop_price → exit at hard_stop_price

2. Check time exit:
   - if current_time >= forced_exit_time → exit at next available price

3. Check signal-based exit:
   - if entry_tf == "15m":
       exit on fresh opposite 5m signal OR fresh opposite 15m signal
   - if entry_tf == "5m":
       exit on fresh opposite 5m signal only
```

***

## 11. Charges Formula Contract

No charge value is hardcoded anywhere except `src/config.py` and the YAML config.

```python
def calculate_round_trip_charges(
    buy_turnover: float,
    sell_turnover: float,
    config: ChargesConfig
) -> float:
    brokerage = (
        min(config.brokerage_cap_per_order, config.brokerage_pct * buy_turnover) +
        min(config.brokerage_cap_per_order, config.brokerage_pct * sell_turnover)
    )
    stt           = config.stt_sell_pct * sell_turnover
    nse_charges   = config.transaction_pct * (buy_turnover + sell_turnover)
    gst           = config.gst_pct * (brokerage + nse_charges)
    sebi          = config.sebi_pct * (buy_turnover + sell_turnover)
    stamp_duty    = config.stamp_duty_buy_pct * buy_turnover
    return round(brokerage + stt + nse_charges + gst + sebi + stamp_duty, 2)
```

***

## 12. Timezone Rules

- All timestamps stored in and retrieved from SQLite must be ISO 8601 strings: `2024-01-15T09:20:00+05:30`
- All `datetime` objects in Python must be timezone-aware with `Asia/Kolkata`
- Use `zoneinfo.ZoneInfo("Asia/Kolkata")` — do not use `pytz`
- Market session hours: 09:15 IST to 15:30 IST — reject any candle outside this window during validation
- The `datetime_utils.py` module must provide: `to_ist(dt)`, `is_market_hours(dt)`, `is_same_session(dt1, dt2)`

***

## 13. Testing Contract

Tests must be generated alongside every source module.
Do not defer tests.

### Unit tests must cover:
- ATR output for known input
- Trailing stop output for a known synthetic dataset with at least one direction flip
- MTF state alignment boundary (candle exactly at `as_of` time must be included)
- Hard stop price for LONG and SHORT
- Position size for normal case, zero-distance SL, and zero-result case
- Slippage applied in correct direction for all four combinations (buy/sell × entry/exit)
- Charges for a known turnover with expected output

### Integration tests must cover:
- Full single-symbol single-week run with synthetic data
- 15m-origin LONG trade that exits on 5m signal
- 5m-origin LONG trade that exits on time exit
- SHORT trade mirror case
- No trade when 1D side disagrees
- Rejected trade log has correct entry when quantity = 0
- Report files are written to `data/reports/{run_id}/`

### Fixture rules:
- Use deterministic synthetic candles for all logic tests
- Do not embed large CSV fixtures in the repo
- Do not write tests that make real API calls — use mocks for all Upstox adapter calls

***

## 14. Code Style Rules

Follow these in every generated file.

- Python 3.12+ syntax and features
- Type hints on every public function and class attribute
- Docstrings on every public class and function using Google style
- Functions must be under ~40 lines where possible
- One class or one cohesive group of functions per file
- No global mutable state
- Use `Literal` for constrained string values
- Use `dataclass(slots=True)` for domain models
- Raise named exceptions from `src/utils/exceptions.py` — no bare `Exception`
- Log with `logging` standard library; do not use `print` for operational output
- Configuration values must flow from `config.py` into functions as arguments — never read config inside business logic modules directly

***

## 15. Anti-Patterns to Never Generate

```text
# NEVER do this:
xATRTrailingStop = close - nLoss  # vectorized — WRONG, loses recursion

# NEVER do this:
df_15m = df_5m.resample("15min").agg({...})  # without .shift(1) — WRONG, lookahead

# NEVER do this:
if signal_side == "BUY":  # on every bar — WRONG, must be fresh/crossover only
    open_trade()

# NEVER do this:
BROKERAGE = 20  # hardcoded inside engine — WRONG, must come from config

# NEVER do this:
import pytz  # WRONG — use zoneinfo

# NEVER do this (Pine-only visual, not trade logic):
ma_fill_color = "green" if close > sma_200 else "red"

# NEVER mix pipeline stages:
def fetch_and_compute_and_simulate():  # WRONG — one responsibility per module
    ...
```

***

## 16. Report Output Contract

Every backtest run must produce these files under `data/reports/{run_id}/`:

| File | Contents |
|---|---|
| `trades.csv` | All completed trades with all fields from the `Trade` model |
| `rejected_trades.csv` | All rejected entries with reason |
| `summary.json` | All aggregate metrics from `compute_summary_metrics()` |
| `config_snapshot.yaml` | Exact copy of the config used for this run |
| `validation_report.json` | Gap/duplicate/error summary from data validation step |

The `run_id` must be a timestamped unique string: `YYYYMMDD_HHMMSS_{symbol_slug}`.

***

## 17. Generation Sequence

Generate modules in this exact order.
Complete one module with tests before starting the next.

```
Step  1: src/utils/enums.py, exceptions.py, datetime_utils.py
Step  2: src/models/candle.py, signal.py, trade.py, report.py, config_models.py
Step  3: src/config.py + config/settings.yaml
Step  4: src/db/schema.py + src/db/repository.py + src/db/sqlite_service.py
Step  5: src/data/upstox_client.py (adapter only, mockable)
Step  6: src/data/transformer.py + src/data/validator.py
Step  7: src/data/fetcher.py
Step  8: src/indicators/atr.py
Step  9: src/indicators/trailing_stop.py  ← most critical, test heavily
Step 10: src/indicators/signals.py
Step 11: src/indicators/mtf_state.py  ← second most critical, test boundary cases
Step 12: src/engine/slippage.py + src/engine/charges.py
Step 13: src/engine/risk_manager.py
Step 14: src/engine/session_rules.py + src/engine/execution_model.py
Step 15: src/engine/trade_manager.py
Step 16: src/engine/backtest_engine.py
Step 17: src/reports/trade_log.py + metrics.py + exporter.py
Step 18: src/main.py (CLI entrypoint)
Step 19: Integration tests
```

***

## 18. Conflict Resolution

If any two instructions conflict, use this priority:

1. Backtest integrity and no-lookahead behavior
2. Auditability — every trade reproducible from stored candles
3. Requirements baseline document
4. This Copilot instructions file
5. Technical guide document

***

## 19. Definition of Done per Module

A module is done only when:
- [ ] Code is implemented with full type hints and docstrings
- [ ] All functions under ~40 lines
- [ ] Unit tests pass
- [ ] Integration tests pass (where applicable)
- [ ] No hardcoded business values
- [ ] No lookahead violation introduced
- [ ] No responsibilities merged across module boundaries
- [ ] All timestamps are timezone-aware `Asia/Kolkata`
- [ ] Output files written to correct paths
- [ ] The module can be tested in isolation with mocked dependencies

***

## 20. Final Instruction

Build this project **one module at a time** in the generation sequence above.
Never rewrite the whole repository in a single step.
When a requirement is ambiguous, always choose the option that:
- preserves no-lookahead behavior,
- makes trades auditable and reproducible,
- keeps modules narrow and independently testable.

This file, the requirements baseline, and the technical guide are the complete contract.
Do not invent, assume, or extrapolate beyond them.