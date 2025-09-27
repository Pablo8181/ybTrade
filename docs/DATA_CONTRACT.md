# Data Contract

## 1. Global Time & Units
- All timestamps are **UTC**.
- Daily bars are **closed bars only**: the trading period spans `[00:00:00Z, 24:00:00Z)` and we persist a record only after the full day closes.
- Prices are quoted in the instrument's **quote currency** (e.g., `BTCUSDT` → `USDT`).
- `volume` captures the traded amount of the **base asset** (e.g., BTC), while `quote_volume` measures the monetary turnover in the quote currency (USDT).
- Provider payload fields are normalized into the shared schema described below.

## 2. Table Keys & Joins
- **`raw_klines_daily` (Bronze)**: primary key `(date, symbol, provider)` to keep multiple vendor snapshots.
- **`ohlcv_daily` (Silver)**: primary key `(date, symbol)` after vendor de-duplication and quality checks.
- **`features_spot1d` (Gold)**: primary key `(date, symbol)` aligned one-to-one with `ohlcv_daily`.
- Downstream joins use `(date, symbol)`; macro data joins on `date` (or `date_key`) only.

## 3. Column Dictionary
### `raw_klines_daily` (Bronze)
- `date` (**DATE, UTC**): Trading day start timestamp at `00:00:00Z`.
- `symbol` (**STRING**): Instrument identifier, e.g., `BTCUSDT`.
- `provider` (**STRING**): Data vendor identifier, e.g., `binance`.
- `open`, `high`, `low`, `close` (**FLOAT64**): OHLC prices in the quote currency.
- `volume` (**FLOAT64**): Base asset volume.
- `close_time` (**TIMESTAMP**): Exchange close time for the bar (end boundary).
- `quote_volume` (**FLOAT64**): Quote currency turnover.
- `trades` (**INT64**): Number of trades aggregated into the bar.
- `taker_base` (**FLOAT64**): Base asset bought by takers.
- `taker_quote` (**FLOAT64**): Quote currency bought by takers.
- `vendor_ignore` (**STRING**): Vendor-specific passthrough field.

### `ohlcv_daily` (Silver)
- Same core columns as `raw_klines_daily` except `provider`.
- Enforces a single validated row per `(date, symbol)`.
- Guarantees persistence of closed bars only and removes duplicate vendor records.

### `features_spot1d` (Gold)
- `date`, `symbol` as join keys.
- Trend & moving averages: `sma20`, `sma50`, `sma200`, `ema12`, `ema26`, `ema50`.
- MACD family: `macd`, `macd_sig`, `macd_hist`.
- Momentum: `rsi14`, `roc10`.
- Volume & flow: `vwap_bar`, `vwap_sess`, `vwma20`, `delta`, `cvd`, `tbr`, `rvol20`, `avg_trade`, `obv`, `ad`, `cmf20`, `mfi14`.
- Volatility & bands: `atr14`, `bb_mid`, `bb_up`, `bb_dn`, `bb_w`, `kc_mid`, `kc_up`, `kc_dn`.
- Directional: `di_plus`, `di_minus`, `adx14`, `don20_hi`, `don20_lo`, `don55_hi`, `don55_lo`.
- Structure & signals: `swing_hh`, `swing_hl`, `swing_lh`, `swing_ll`, `bull_div_rsi`, `bear_div_rsi`, `bull_div_cvd`, `bear_div_cvd`.
- Levels: `fib20_382`, `fib20_500`, `fib20_618`, `fib55_382`, `fib55_500`, `fib55_618`, `fib_sw_382`, `fib_sw_500`, `fib_sw_618`, `fibA_382`, `fibA_500`, `fibA_618`.
- All features derive from the Silver table using UTC daily cadence.

## 4. Time Semantics Cheatsheet
- All dates represent the **UTC trading day**.
- `date` derives from the bar open timestamp at `00:00:00Z`.
- We never store partially formed (open) daily bars.
