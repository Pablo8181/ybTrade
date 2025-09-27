-- dataset: ybtrade

CREATE TABLE IF NOT EXISTS `{{PROJECT}}.ybtrade.raw_klines_daily` (
  date DATE,
  symbol STRING,
  provider STRING,
  open FLOAT64,
  high FLOAT64,
  low FLOAT64,
  close FLOAT64,
  volume FLOAT64,
  close_time TIMESTAMP,
  quote_volume FLOAT64,
  trades INT64,
  taker_base FLOAT64,
  taker_quote FLOAT64,
  vendor_ignore STRING
)
PARTITION BY date
CLUSTER BY symbol, provider;

CREATE TABLE IF NOT EXISTS `{{PROJECT}}.ybtrade.ohlcv_daily` (
  date DATE,
  symbol STRING,
  open FLOAT64,
  high FLOAT64,
  low FLOAT64,
  close FLOAT64,
  volume FLOAT64,
  close_time TIMESTAMP,
  quote_volume FLOAT64,
  trades INT64,
  taker_base FLOAT64,
  taker_quote FLOAT64
)
PARTITION BY date
CLUSTER BY symbol;

CREATE TABLE IF NOT EXISTS `{{PROJECT}}.ybtrade.features_spot1d` (
  date DATE,
  symbol STRING,
  -- trend
  sma20 FLOAT64, sma50 FLOAT64, sma200 FLOAT64,
  ema12 FLOAT64, ema26 FLOAT64, ema50 FLOAT64,
  macd FLOAT64, macd_sig FLOAT64, macd_hist FLOAT64,
  -- oscillators
  rsi14 FLOAT64, roc10 FLOAT64,
  -- volume/flow
  vwap_bar FLOAT64, vwap_sess FLOAT64, vwma20 FLOAT64,
  delta FLOAT64, cvd FLOAT64, tbr FLOAT64, rvol20 FLOAT64, avg_trade FLOAT64,
  obv FLOAT64, ad FLOAT64, cmf20 FLOAT64, mfi14 FLOAT64,
  -- vol/bands
  atr14 FLOAT64, bb_mid FLOAT64, bb_up FLOAT64, bb_dn FLOAT64, bb_w FLOAT64,
  kc_mid FLOAT64, kc_up FLOAT64, kc_dn FLOAT64,
  -- directional
  di_plus FLOAT64, di_minus FLOAT64, adx14 FLOAT64,
  don20_hi FLOAT64, don20_lo FLOAT64, don55_hi FLOAT64, don55_lo FLOAT64,
  -- structure/divergence
  swing_hh INT64, swing_hl INT64, swing_lh INT64, swing_ll INT64,
  bull_div_rsi INT64, bear_div_rsi INT64, bull_div_cvd INT64, bear_div_cvd INT64,
  -- levels
  fib20_382 FLOAT64, fib20_500 FLOAT64, fib20_618 FLOAT64,
  fib55_382 FLOAT64, fib55_500 FLOAT64, fib55_618 FLOAT64,
  fib_sw_382 FLOAT64, fib_sw_500 FLOAT64, fib_sw_618 FLOAT64,
  fibA_382 FLOAT64, fibA_500 FLOAT64, fibA_618 FLOAT64
)
PARTITION BY date
CLUSTER BY symbol;
