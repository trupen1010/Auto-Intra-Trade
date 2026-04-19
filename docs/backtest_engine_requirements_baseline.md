# Backtest Engine Requirements Baseline

Version: 1.0
Date: 2026-04-19
Project: Intraday Multi-Timeframe Backtest Engine
Purpose: Baseline requirements document for building a backtest engine only

## 1. Objective

This project will build a **Backtest Engine** to test an intraday stock trading logic on historical Indian equity market data.

The goal is to answer one question clearly:

> Does this logic make money after realistic costs, execution assumptions, and rule constraints?

This project is **not** for TradingView strategy development.
This project is **not** for live auto-trading in the first phase.
This project is **not** for broker order execution in the first phase.

The first phase is only for:
- historical data collection,
- indicator calculation,
- candle-by-candle simulation,
- trade logging,
- performance reporting,
- rule validation.

---

## 2. Source Logic Review

The original Pine Script contains many plotted values, colors, labels, and alerts.
Not all of them affect actual trade decisions.
For the backtest engine, we will keep only the computations that directly affect entry, exit, risk, or trade state.
Everything else will be removed from the engine design.

---

## 3. Visual-Only Parts Removed

The following parts from the Pine Script are visual-only or incomplete and will **not** be part of the backtest engine core logic:

### 3.1 Moving-average visuals removed
- `ma_fill_color`
- the MA fill background
- plotted MA lines used only for chart display
- mislabeled MA names such as `MA-100` for `SMA(50)` and `MA-44` for `SMA(22)`
- MA color display logic when it is used only to color a line and not to trigger a trade

### 3.2 SuperTrend visuals removed
- `bodyMiddle` plot
- `upTrend` plot
- `downTrend` plot
- SuperTrend fill shading

### 3.3 Signal display items removed
- `plotshape(buy)`
- `plotshape(sell)`
- `barcolor`
- alert messages
- any chart-only title, color, shape, or offset setting

### 3.4 Bollinger Bands removed from baseline logic
- `basis`, `upper`, and `lower` are currently calculated but not used by the trade rules
- therefore Bollinger Bands are removed from version 1 baseline
- they may be added later only if explicitly defined as an entry or exit rule

---

## 4. Trade Logic Kept in Baseline

The baseline backtest engine will only keep the logic that has a direct say in trade decisions.

### 4.1 Core signal logic kept
- `ATR(period=20)`
- `nLoss = keyvalue * ATR`
- recursive ATR trailing stop calculation
- crossover of `close` above ATR trailing stop = Buy signal
- crossunder of `close` below ATR trailing stop = Sell signal
- position state tracking from the trailing stop logic

### 4.2 Multi-timeframe trade rules kept
- 1 Day timeframe decides market side bias
- 15 Minute timeframe can trigger a trade when the 1 Day side agrees
- 5 Minute timeframe can trigger a trade when 1 Day and 15 Minute are already aligned in the same direction
- one trade at a time
- only trade in the same direction as the active 1 Day bias

### 4.3 Risk and session rules kept
- risk only 1% to 2% of total capital per trade
- no overnight positions
- if no exit appears earlier, exit before the intraday closing window
- no immediate opposite-side reversal trade at exit

---

## 5. Clean Baseline Strategy Definition

This is the simplified baseline strategy definition that the backtest engine must implement.

### 5.1 Direction filter
The engine must first determine the active side from the **last fully closed 1 Day candle**.

- If the 1 Day signal is Buy, only long trades are allowed.
- If the 1 Day signal is Sell, only short trades are allowed.
- If the 1 Day signal is neutral or invalid, no trade is allowed.

### 5.2 Entry rule using 15 Minute
A new trade may start from the 15 Minute timeframe only when:
- the latest fully closed 1 Day signal is Buy and the latest fully closed 15 Minute candle creates a Buy signal, or
- the latest fully closed 1 Day signal is Sell and the latest fully closed 15 Minute candle creates a Sell signal.

This trade must be tagged as `entry_tf = 15m`.

### 5.3 Entry rule using 5 Minute
A new trade may start from the 5 Minute timeframe only when:
- the 1 Day signal is already active in one direction,
- the 15 Minute signal is already active in the same direction,
- and the latest fully closed 5 Minute candle creates a fresh signal in that same direction.

This trade must be tagged as `entry_tf = 5m`.

### 5.4 One-trade rule
The system must allow only one open trade at a time per tested strategy instance.
No second trade may open while another trade is active.

---

## 6. Signal Definition

The baseline signal will be derived from the ATR trailing stop logic from the source script.

### 6.1 Inputs
- `src = close`
- `keyvalue = 3` by default, configurable
- `atrperiod = 20` by default, configurable
- `xATR = ATR(atrperiod)`
- `nLoss = keyvalue * xATR`

### 6.2 Trailing stop rules
For each candle, the ATR trailing stop is computed recursively using the previous trailing stop value.
This means the value cannot be treated as a simple vector-only formula.
It must be computed in strict candle order.

### 6.3 Buy signal
A Buy signal occurs when `close` crosses above the ATR trailing stop.

### 6.4 Sell signal
A Sell signal occurs when `close` crosses below the ATR trailing stop.

### 6.5 Signal state
Each timeframe must maintain its latest valid state:
- `BUY`
- `SELL`
- `NEUTRAL`

The state must be based only on fully closed candles.

---

## 7. Backtest-Specific Rules

These rules are mandatory because a backtest engine must avoid false performance.

### 7.1 No lookahead bias
The engine must never use future candle data.
A higher timeframe value becomes available only after that timeframe candle has fully closed.

Examples:
- a 15 Minute candle is usable only after its close time,
- a 1 Day candle is usable only after market close,
- a 5 Minute candle may not read an unfinished 15 Minute or 1 Day candle.

### 7.2 Closed-candle execution rule
All entries and exits must be generated from **closed candle signals only**.
The engine may execute at the next candle open or at a configurable execution model, but it must be consistent across the whole backtest.

### 7.3 Warmup rule
The engine must not allow any trade until enough historical candles exist to compute all required indicators correctly.

Minimum warmup must cover:
- ATR period,
- recursive trailing stop stabilization,
- any future added higher timeframe calculations.

### 7.4 Market hours rule
The engine must simulate only valid Indian equity intraday session candles.
Invalid timestamps must be rejected or cleaned during data preparation.

### 7.5 First valid signal timing rule
At session open, the engine must wait until the first relevant candle is fully closed.
Example:
- 5 Minute logic becomes valid only after the first 5 Minute candle closes,
- 15 Minute logic becomes valid only after the first 15 Minute candle closes.

---

## 8. Exit Rules

### 8.1 Hard stop loss is mandatory
The original script does not define a true hard stop loss.
The backtest engine must add one.

At entry time, the engine must calculate a hard stop using an ATR-based formula.
Baseline default:
- Long trade hard stop = `entry_price - (hard_sl_atr_multiplier * ATR_at_entry)`
- Short trade hard stop = `entry_price + (hard_sl_atr_multiplier * ATR_at_entry)`

Default `hard_sl_atr_multiplier` = `1.5`, configurable.

### 8.2 Exit priority order
If multiple exits are possible, the engine must apply them in this order:

1. Hard stop loss
2. Forced time exit
3. Signal-based exit according to trade origin timeframe

### 8.3 Forced time exit
If no valid exit happens earlier, the engine must close the trade before the end-of-session safety window.

Baseline default:
- no new trades after a configurable cut-off time,
- force exit all open trades at or before `15:10 IST`.

### 8.4 Exit logic for trades started on 15 Minute
If a trade began from a 15 Minute entry signal, then exit may be triggered by:
- a valid 5 Minute opposite signal, or
- a valid 15 Minute opposite signal, or
- hard stop loss, or
- time exit.

The earliest valid exit wins after exit priority is applied.

### 8.5 Exit logic for trades started on 5 Minute
If a trade began from a 5 Minute entry signal, then exit may be triggered by:
- a valid 5 Minute opposite signal, or
- hard stop loss, or
- time exit.

### 8.6 No reversal on exit candle
When a trade exits, the engine must not open an opposite trade on the same candle.
The next entry check may happen only from the next eligible candle.

---

## 9. Position Sizing and Risk Rules

### 9.1 Capital risk rule
Each trade must risk at most `1% to 2%` of current available capital.
This must be configurable.

### 9.2 Quantity calculation rule
Position size must be computed from stop distance, not from leverage alone.

Formula:
- `risk_amount = available_capital * risk_percent`
- `stop_distance = abs(entry_price - hard_stop_price)`
- `raw_qty = floor(risk_amount / stop_distance)`

### 9.3 Quantity caps
Final quantity must also obey:
- broker/exchange leverage limit,
- available capital,
- minimum tradeable quantity,
- maximum position cap set by configuration.

If final quantity becomes zero, the trade must be skipped and logged as rejected.

### 9.4 One-trade-at-a-time rule
Only one open trade is allowed at a time in the engine instance.
No pyramiding.
No scaling in.
No scaling out in baseline version.

---

## 10. Charges Model

The backtest must include realistic charges on every completed round-trip trade.

### 10.1 Baseline charge model
- Brokerage: lower of `₹20` or `0.05%` per executed order
- STT: `0.025%` on sell side
- Transaction charges: `0.00297%` on turnover
- GST: `18%` on brokerage + transaction charges
- SEBI charges: `0.0001%`
- Stamp duty: `0.003%` on buy side

### 10.2 Round-trip rule
A completed trade includes two orders.
Charges must be applied accordingly.
The backtest report must show both gross P&L and net P&L after charges.

---

## 11. Slippage and Execution Assumptions

A backtest without slippage is too optimistic.
The engine must support configurable slippage.

### 11.1 Baseline slippage model
Default slippage must be percentage-based and configurable.
Suggested baseline default:
- `0.05%` adverse slippage on entry,
- `0.05%` adverse slippage on exit.

### 11.2 Execution model
Baseline execution model must be clearly fixed in config.
Recommended default:
- signal is detected on a closed candle,
- trade is executed on the next candle open.

The same rule must apply consistently to all timeframes.

---

## 12. Data Requirements

### 12.1 Required timeframes
The backtest must use:
- 1 Day candles,
- 15 Minute candles,
- 5 Minute candles.

### 12.2 Required data fields
Each candle must contain at least:
- symbol
- timestamp
- open
- high
- low
- close
- volume

### 12.3 Data storage
Historical data must be stored locally in SQLite for repeatable backtests.

### 12.4 Data quality rules
Before any backtest starts, the engine must validate:
- missing candles,
- duplicate timestamps,
- invalid market hours,
- out-of-order rows,
- incomplete timeframe mapping.

### 12.5 Higher timeframe alignment rule
The 1 Day and 15 Minute data used at any 5 Minute decision point must only include fully closed higher-timeframe candles.
This rule is mandatory.

---

## 13. State Management Rules

### 13.1 Timeframe state
The engine must maintain the latest closed signal state for each timeframe per symbol:
- 1 Day state
- 15 Minute state
- 5 Minute state

### 13.2 Cross-session persistence
Because the strategy depends on previous active signals, the backtest logic must carry state correctly across session boundaries.
A fresh trading day must still know the previous closed 1 Day and 15 Minute states.

### 13.3 Trade state
At all times the engine must know:
- whether a trade is open,
- direction,
- entry timeframe,
- entry time,
- entry price,
- quantity,
- hard stop,
- running MFE/MAE,
- pending exit reason if any.

---

## 14. Reporting Requirements

The project output must make every trade auditable.

### 14.1 Mandatory trade log fields
Each trade record must contain:
- trade_id
- symbol
- trade_date
- side
- entry_datetime
- entry_timeframe
- entry_signal_price
- actual_entry_price
- exit_datetime
- exit_signal_price
- actual_exit_price
- exit_reason
- quantity
- hard_stop_at_entry
- gross_pnl
- charges
- net_pnl
- risk_amount
- capital_before_trade
- capital_after_trade
- 1D_state_at_entry
- 15M_state_at_entry
- 5M_state_at_entry

### 14.2 Mandatory summary metrics
The backtest report must include at least:
- total trades
- win rate
- loss rate
- gross profit
- gross loss
- net profit
- average win
- average loss
- profit factor
- expectancy
- max drawdown
- return on capital
- total charges paid
- average trade duration
- trades by exit reason
- trades by timeframe of entry

### 14.3 Rejected trade log
The engine must also log rejected trades with reason, such as:
- against 1 Day bias
- active trade already exists
- quantity zero
- after entry cut-off time
- invalid data
- warmup incomplete

---

## 15. Out of Scope for Baseline Phase

The following are intentionally out of scope for this baseline requirements version:
- live trading execution,
- Upstox order placement,
- WebSocket streaming,
- portfolio-level multi-position management,
- portfolio optimization,
- partial profit booking,
- advanced slippage modeling from order book data,
- options/futures support,
- UI dashboard,
- TradingView script generation.

---

## 16. Configuration Parameters

All of the following must be configurable without changing code:
- symbols list
- backtest date range
- timeframe mapping
- ATR period
- sensitivity / keyvalue
- hard stop ATR multiplier
- risk percentage per trade
- slippage percentage
- brokerage model values
- session entry cut-off time
- forced exit time
- leverage limits or margin assumptions
- execution model
- warmup candles

---

## 17. Acceptance Criteria

The baseline backtest engine will be considered correct only if all points below are satisfied.

### 17.1 Logic correctness
- The engine reproduces the ATR trailing stop logic candle by candle.
- The engine generates 1 Day, 15 Minute, and 5 Minute signal states only from closed candles.
- The engine follows the one-trade-at-a-time rule.
- The engine never opens a trade against the active 1 Day side.

### 17.2 Backtest integrity
- No lookahead bias exists.
- No unfinished higher-timeframe candle is used.
- Charges are applied correctly on every completed trade.
- Slippage is applied consistently.
- State persists correctly across session boundaries.

### 17.3 Report quality
- Every trade can be manually verified from the stored candles.
- Every trade has a clear entry reason and exit reason.
- Performance metrics match the underlying trade log exactly.

---

## 18. Baseline Implementation Summary

The baseline engine will therefore do only this:

1. Load validated historical 1 Day, 15 Minute, and 5 Minute candles.
2. Compute ATR trailing stop and signal states for each timeframe.
3. Use 1 Day as direction filter.
4. Use 15 Minute for primary trade trigger.
5. Use 5 Minute for lower-timeframe confirmation trigger when 1 Day and 15 Minute are already aligned.
6. Simulate one trade at a time candle by candle.
7. Apply hard stop, signal exit, time exit, charges, and slippage.
8. Produce a complete auditable report.

This document is the approved baseline for the project unless explicitly revised.
