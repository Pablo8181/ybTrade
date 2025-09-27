-- BigQuery bootstrap for ybTrade (idempotent)
-- Uses the invoking project as default; no hard-coded project IDs.

-- Create schema (dataset) in europe-central2 if missing
CREATE SCHEMA IF NOT EXISTS `trading`
OPTIONS(
  location = "europe-central2",
  description = "Core trading datasets: Bronze raw OHLCV, Silver/Gold features"
);

-- Bronze: daily OHLCV with Binance fields; key (date, symbol)
CREATE TABLE IF NOT EXISTS `trading.ohlcv_1d` (
  date   DATE    NOT NULL,
  symbol STRING  NOT NULL,
  open   NUMERIC,
  high   NUMERIC,
  low    NUMERIC,
  close  NUMERIC,
  volume NUMERIC,
  qav    NUMERIC,  -- quote_asset_volume
  ntr    INT64,    -- number_of_trades
  tbb    NUMERIC,  -- taker_buy_base_asset_volume
  tbq    NUMERIC   -- taker_buy_quote_asset_volume
)
PARTITION BY date
CLUSTER BY symbol
OPTIONS (description = "Daily OHLCV (Binance-style); partitioned by date, clustered by symbol");

-- Silver/Gold: computed features; key (date, symbol)
CREATE TABLE IF NOT EXISTS `trading.features_1d` (
  date   DATE    NOT NULL,
  symbol STRING  NOT NULL,
  rsi_14 NUMERIC,
  atr_14 NUMERIC,
  macd_12_26_9 NUMERIC,
  macd_signal_12_26_9 NUMERIC,
  donchian_upper_20 NUMERIC,
  donchian_lower_20 NUMERIC
)
PARTITION BY date
CLUSTER BY symbol
OPTIONS (description = "Daily features keyed by (date,symbol); indicator windows in column names");
