from __future__ import annotations
import os, json, time, math, sys
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple


import requests

# Google Sheets (ADC / WIF)
from google.auth import default as google_auth_default
from google.auth.transport.requests import Request as GARequest
from googleapiclient.discovery import build

ISO_MS = "%Y-%m-%dT%H:%M:%S.%fZ"

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")

def _col_letters(n: int) -> str:
    """1->A, 26->Z, 27->AA..."""
    s=""
    while n>0:
        n,r = divmod(n-1,26)
        s = chr(65+r)+s
    return s

def env(name: str, default: str="") -> str:
    return os.getenv(name, default).strip()

# ---------- Providers ----------
def _binance_klines_daily(symbol: str, start_iso_date: str, limit: int=1000) -> List[List]:
    bases = [
        "https://data-api.binance.vision",
        "https://api.binance.com",
        "https://api-gcp.binance.com",
        "https://api1.binance.com","https://api2.binance.com","https://api3.binance.com","https://api4.binance.com",
    ]
    start_ms = int(datetime.fromisoformat(start_iso_date+"T00:00:00+00:00").timestamp()*1000)
    out: List[List] = []
    cur = start_ms
    while True:
        path = f"/api/v3/klines?symbol={symbol}&interval=1d&limit={limit}&startTime={cur}"
        ok, last_err = None, None
        for b in bases:
            try:
                time.sleep(0.12)
                r = requests.get(b+path, timeout=30)
                if 200 <= r.status_code < 300:
                    ok = r.json()
                    break
                last_err = Exception(f"HTTP {r.status_code} {r.text[:160]}")
            except Exception as e:
                last_err = e
        if ok is None:
            raise last_err or Exception("All bases failed")
        if not ok:
            break
        # keep CLOSED bars only (<= today 00:00 UTC - 1ms)
        last_closed_ms = int(datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()*1000) - 1
        closed = [row for row in ok if int(row[6]) <= last_closed_ms]
        out.extend(closed)
        if len(ok) < limit:
            break
        cur = int(ok[-1][0]) + 1
    return out

def _openbb_klines_daily(symbol: str) -> List[List]:
    # Seam for later; keep shape compatible with Binance kline array of 12 fields
    raise NotImplementedError("Enable OpenBB later; keep provider=openbb seam.")

def get_raw_klines(provider: str, symbol: str, since: str) -> List[List]:
    if provider.lower() == "openbb":
        return _openbb_klines_daily(symbol)
    return _binance_klines_daily(symbol, since)

# ---------- Indicator Library (port of your Apps Script) ----------
# Notes:
# - We work on arrays of floats; non-finite -> '' (empty) to mirror Sheets behavior.
# - Functions return lists same length as inputs.

def _sma(arr, period):
    out=['']*len(arr); q=[]; s=0.0
    for i,v in enumerate(arr):
        if not _is_num(v): out[i]=''; continue
        q.append(v); s+=v
        if len(q)>period: s-=q.pop(0)
        out[i]= (s/period) if len(q)==period else ''
    return out

def _ema(arr, period):
    out=['']*len(arr); k=2.0/(period+1); seed=None; cnt=0; s=0.0
    for i,v in enumerate(arr):
        if not _is_num(v): out[i]=''; seed=None; cnt=0; s=0.0; continue
        if seed is None:
            s+=v; cnt+=1
            out[i]= (s/period) if cnt==period else ''
            if cnt==period: seed=out[i]
        else:
            seed = (v - seed)*k + seed
            out[i]=seed
    return out

def _rma(arr, period):
    out=['']*len(arr); seed=None; cnt=0; s=0.0
    for i,v in enumerate(arr):
        if not _is_num(v): out[i]=''; seed=None; cnt=0; s=0.0; continue
        if seed is None:
            s+=v; cnt+=1
            out[i]= (s/period) if cnt==period else ''
            if cnt==period: seed=out[i]
        else:
            seed = (seed*(period-1)+v)/period
            out[i]=seed
    return out

def _stddev(arr, period):
    out=['']*len(arr); q=[]; s=0.0; s2=0.0
    for i,v in enumerate(arr):
        if not _is_num(v): out[i]=''; continue
        q.append(v); s+=v; s2+=v*v
        if len(q)>period:
            x=q.pop(0); s-=x; s2-=x*x
        if len(q)==period:
            mean=s/period; var=max((s2/period)-mean*mean,0.0); out[i]=var**0.5
        else: out[i]=''
    return out

def _roll_max(arr, period):
    out=['']*len(arr); dq=[]
    for i,v in enumerate(arr):
        if not _is_num(v): out[i]=''; continue
        while dq and dq[-1][1] <= v: dq.pop()
        dq.append((i,v))
        start=i-period+1
        while dq and dq[0][0] < start: dq.pop(0)
        out[i]= dq[0][1] if start>=0 else ''
    return out

def _roll_min(arr, period):
    out=['']*len(arr); dq=[]
    for i,v in enumerate(arr):
        if not _is_num(v): out[i]=''; continue
        while dq and dq[-1][1] >= v: dq.pop()
        dq.append((i,v))
        start=i-period+1
        while dq and dq[0][0] < start: dq.pop(0)
        out[i]= dq[0][1] if start>=0 else ''
    return out

def _is_num(x):
    return isinstance(x,(int,float)) and math.isfinite(x)

# ---------- Full pipeline ----------
def build_header() -> List[str]:
    # EXACT names (name + " (desc)") matching your Apps Script spec.base + spec.ind
    base = [
      ("openTime","Candle open time in UTC as Date. Represents the start of a 24 hour daily bar. Only fully closed days are stored. Use to index the series and to join with external datasets and to filter time ranges."),
      ("open","Trade price in usdt at the bar open. Taken from the first trade of the daily session. Used for gap checks session to session and for calculating returns and for candle body size diagnostics."),
      ("high","Highest traded price within the daily session. Captures intraday extremes and breakout attempts. Useful for Donchian channels and for volatility studies and for stop placement logic and for wick analysis."),
      ("low","Lowest traded price within the daily session. Captures intraday extremes and liquidity sweeps. Useful for Donchian channels and for volatility studies and for identifying swing lows and for risk management levels."),
      ("close","Trade price in usdt at the bar close. End of session print. Used by most indicators as the primary input. Drives moving averages momentum oscillators and end of day signals used in decisions."),
      ("volume","Base asset volume traded during the daily session. Unit is BTC. Used to confirm moves and to compute money flow metrics and to weight prices for VWAP like measures and to gauge market participation."),
      ("closeTime","Candle close time in UTC as Date. Represents the end of the 24 hour daily bar exclusive bound. Together with openTime defines the temporal extent and helps verify only closed bars are saved."),
      ("qav","Quote asset volume in usdt summed across trades within the daily session. Approximates money turnover. Useful to estimate per bar VWAP as qav divided by volume and to compare liquidity regimes across time."),
      ("ntr","Number of trades within the daily session. Proxy for market activity and fragmentation. Combined with volume gives average trade size which hints at retail versus larger flow dominance."),
      ("tbb","Base asset volume bought by taker side during the session. Represents aggressive market buy activity that removes liquidity. Used to estimate net order flow bias when compared to total volume."),
      ("tbq","Quote asset volume in usdt bought by taker side during the session. Provides the money value of aggressive buying. Complements tbb and supports order flow diagnostics and liquidity analysis."),
      ("ignore","Reserved field per Binance response. Kept for compatibility to maintain column alignment with the raw kline format. Not used in calculations and can be ignored for analysis.")
    ]
    ind = [
      ("delta","Net aggressive flow per day estimated as two times taker base minus total base volume. Positive values indicate buy pressure dominance. Negative values indicate sell pressure. Used to build cumulative volume delta."),
      ("cvd","Cumulative volume delta which sums per bar delta through time. Tracks the path of aggressive pressure. Divergences between cvd and price may hint at absorption or distribution by passive liquidity."),
      ("tbr","Taker buy ratio as taker base divided by total volume. Measures how much of traded volume came from aggressive buyers. Values near one suggest strong buy pressure. Values near zero suggest strong sell pressure."),
      ("rvol20","Relative volume over the last twenty sessions computed as today volume divided by the twenty day simple average of volume. Detects participation spikes and droughts and helps filter breakouts by strength."),
      ("avg_trade","Average trade size proxy computed as volume divided by number of trades. Larger values suggest fewer bigger prints and possible professional activity. Smaller values suggest more fragmented retail like activity."),
      ("vwap_bar","Per bar VWAP approximation computed as qav divided by volume. Serves as a daily fair value estimate. Comparison of close versus this level indicates premium or discount within the session."),
      ("vwap_sess","Cumulative session VWAP from the start of the dataset computed as running sum of qav divided by running sum of volume. Acts as a long horizon fair value anchor for mean reversion or trend evaluation."),
      ("vwma20","Twenty day volume weighted moving average of close. Gives more weight to high participation days. Helps differentiate moves supported by volume from moves on thin activity which may be less reliable."),
      ("sma20","Simple moving average of close over twenty sessions. Short term trend proxy. Often used with price crossovers and with distance to average filters to avoid chasing stretched conditions."),
      ("sma50","Simple moving average of close over fifty sessions. Intermediate trend proxy. Works as a common support or resistance reference and defines the mid term bias for many participants."),
      ("sma200","Simple moving average of close over two hundred sessions. Long term trend gauge. Popular for bull or bear regime definition and for mapping high level support or resistance zones."),
      ("ema12","Exponential moving average of close over twelve sessions. Reacts faster than simple averages. Used within MACD to capture recent momentum and to reduce lag in crossover systems."),
      ("ema26","Exponential moving average of close over twenty six sessions. Slower leg of MACD calculations. Provides a baseline momentum reference to compare against the faster ema."),
      ("ema50","Exponential moving average of close over fifty sessions. Alternative intermediate trend smoother. Slightly faster response than sma50 due to exponential weighting which emphasizes recent data."),
      ("macd","Moving Average Convergence Divergence defined as ema12 minus ema26. Positive values show upside momentum. Negative values show downside momentum. Useful for momentum swings and centerline crosses."),
      ("macd_sig","Signal line for MACD computed as exponential moving average of macd over nine sessions. Used to generate macd crossing signal events and to smooth raw macd fluctuations."),
      ("macd_hist","MACD histogram defined as macd minus macd_sig. Visualizes momentum impulses. Expanding histogram suggests acceleration. Contracting histogram suggests deceleration and possible pivot risk."),
      ("rsi14","Wilder Relative Strength Index over fourteen sessions on close. Values above seventy hint at overbought risk and values below thirty hint at oversold risk. Divergences with price can signal exhaustion."),
      ("roc10","Rate of change over ten sessions computed as close divided by close ten bars ago minus one. Measures percentage change speed. Useful for momentum filters and for ranking periods by acceleration."),
      ("obv","On Balance Volume cumulative measure that adds volume when close rises and subtracts volume when close falls. Tracks whether volume confirms the direction of price trends."),
      ("ad","Accumulation Distribution line cumulative form. Computes close location value times volume and sums over time. Rises when closes are near highs on volume. Falls when closes are near lows on volume."),
      ("cmf20","Chaikin Money Flow over twenty sessions defined as the ratio of the sum of close location value times volume to the sum of volume. Positive values suggest accumulation. Negative values suggest distribution."),
      ("mfi14","Money Flow Index over fourteen sessions. RSI like oscillator that uses typical price and volume. Identifies overbought and oversold with volume sensitivity which can improve signal quality in some regimes."),
      ("atr14","Average True Range over fourteen sessions using Wilder smoothing. Measures typical daily movement size. Useful for stop placement position sizing and volatility regime detection."),
      ("bb_mid","Bollinger middle band which is the twenty day simple moving average of close. Serves as a mean reference for upper and lower bands and for pullback targeting in trends."),
      ("bb_up","Upper Bollinger band computed as middle band plus two standard deviations of close over twenty sessions. Marks high side envelope used for breakout studies and stretch detection."),
      ("bb_dn","Lower Bollinger band computed as middle band minus two standard deviations of close over twenty sessions. Marks low side envelope used for breakdown studies and stretch detection."),
      ("bb_w","Relative Bollinger width computed as band distance divided by middle band. Acts as a normalized volatility gauge to compare across price levels and long histories."),
      ("kc_mid","Keltner channel middle line as exponential moving average of close over twenty sessions. Forms the center for channels based on average true range envelopes."),
      ("kc_up","Upper Keltner channel computed as middle line plus two times atr14. Highlights expansion relative to typical range and often frames trend followers entries and trailing exits."),
      ("kc_dn","Lower Keltner channel computed as middle line minus two times atr14. Highlights contraction and breakdown risk and can assist with oversold bounce filters in ranges."),
      ("di_plus","Directional indicator plus computed from positive directional movement with Wilder smoothing divided by atr14 and scaled by one hundred. Indicates strength of upward movement component."),
      ("di_minus","Directional indicator minus computed from negative directional movement with Wilder smoothing divided by atr14 and scaled by one hundred. Indicates strength of downward movement component."),
      ("adx14","Average Directional Index over fourteen sessions using Wilder smoothing of DX. Measures trend strength without regard to direction. Higher values indicate stronger trends."),
      ("don20_hi","Donchian twenty bar highest high. Marks breakout level for short term trend following systems and for stop placement above ranges."),
      ("don20_lo","Donchian twenty bar lowest low. Marks breakdown level for short term trend following systems and for stop placement below ranges."),
      ("don55_hi","Donchian fifty five bar highest high. Classic long term Turtle breakout threshold used to capture large trends and to avoid noise."),
      ("don55_lo","Donchian fifty five bar lowest low. Classic long term Turtle breakdown threshold used for exits and short signals in trend systems."),
      ("swing_hh","Flag equals one when a new swing high exceeds the prior confirmed swing high under a k equals three fractal with amplitude and spacing filters. Helps confirm uptrend structure."),
      ("swing_hl","Flag equals one when a new swing low is higher than the prior confirmed swing low under a k equals three fractal with amplitude and spacing filters. Helps confirm constructive pullbacks."),
      ("swing_lh","Flag equals one when a new swing high is lower than the prior confirmed swing high which signals possible downtrend continuation or weakening rallies under the same pivot rules."),
      ("swing_ll","Flag equals one when a new swing low undercuts the prior confirmed swing low which signals downtrend continuation risk and momentum to the downside."),
      ("bull_div_rsi","Flag equals one when price makes a lower low while RSI makes a higher low based on recent pivots. Suggests bullish divergence and potential reversal or loss of downside momentum."),
      ("bear_div_rsi","Flag equals one when price makes a higher high while RSI makes a lower high based on recent pivots. Suggests bearish divergence and potential reversal or loss of upside momentum."),
      ("bull_div_cvd","Flag equals one when price makes a lower low while CVD makes a higher low. Implies buyers absorb sells at lows and may precede upward mean reversion."),
      ("bear_div_cvd","Flag equals one when price makes a higher high while CVD makes a lower high. Implies sellers absorb buys near highs and may precede downward mean reversion."),
      ("fib20_382","Fibonacci retracement at 38.2 percent of the last twenty bar range using rolling high and low. Provides pullback targets and support estimation within short term swings."),
      ("fib20_500","Fibonacci level at 50 percent of the last twenty bar range. Common midpoint used for balance tests and for fair value reversion checks."),
      ("fib20_618","Fibonacci retracement at 61.8 percent of the last twenty bar range. Classic golden ratio area where trends often resume after corrective legs."),
      ("fib55_382","Fibonacci retracement at 38.2 percent of the last fifty five bar range. Useful for medium term pullback zones and for scale in planning."),
      ("fib55_500","Fibonacci level at 50 percent of the last fifty five bar range. Midpoint focus for mean reversion and for decision checkpoints."),
      ("fib55_618","Fibonacci retracement at 61.8 percent of the last fifty five bar range. Key support or resistance zone for medium term legs."),
      ("fib_sw_382","Swing anchored Fibonacci 38.2 percent using the most recent confirmed swing low and swing high pair from fractal pivots. Updates as new swings confirm and frames reaction zones."),
      ("fib_sw_500","Swing anchored Fibonacci 50 percent using the most recent confirmed swing pair. Marks fair value area between last key low and high."),
      ("fib_sw_618","Swing anchored Fibonacci 61.8 percent using the most recent confirmed swing pair. Classic continuation zone after corrections."),
      ("fibA_382","Event anchored Fibonacci 38.2 percent using the last detected cross between sma50 and sma200 as anchor window. If no cross exists the earliest available region is used. Helps tie levels to regime shifts."),
      ("fibA_500","Event anchored Fibonacci 50 percent from the same anchor window. Serves as balanced retracement or reaction area in the current regime."),
      ("fibA_618","Event anchored Fibonacci 61.8 percent from the same anchor window. Key continuation zone once corrective pressure fades.")
    ]
    return [f"{n} ({d})" for (n,d) in base+ind]

def _to_series(nums: List[Any]) -> List[float]:
    return [float(x) if _is_num(float(x)) else float('nan') for x in nums]


def compute_all(rows: List[List[Any]]) -> Tuple[List[str], List[List[Any]]]:
    header = build_header()
    # Map raw Binance arrays → base columns with ms→string for times
    n = len(rows)
    if n==0:
        return header, []

def compute_all(rows: List[List]) -> List[List]:
    # Map raw Binance arrays → base columns with ms→string for times
    n = len(rows)
    if n==0: return []

    o_ms = [int(r[0]) for r in rows]
    o  = [float(r[1]) for r in rows]
    h  = [float(r[2]) for r in rows]
    l  = [float(r[3]) for r in rows]
    c  = [float(r[4]) for r in rows]
    v  = [float(r[5]) for r in rows]
    c_ms= [int(r[6]) for r in rows]
    qav= [float(r[7]) for r in rows]
    ntr= [float(r[8]) for r in rows]
    tbb= [float(r[9]) for r in rows]
    tbq= [float(r[10]) for r in rows]
    ign= [r[11] for r in rows]

    # Base time string conversion
    def ms2str(ms): return datetime.fromtimestamp(ms/1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    openTime_str  = [ms2str(x) for x in o_ms]
    closeTime_str = [ms2str(x) for x in c_ms]

    # ---- Indicators (matching your JS) ----
    # Volume & Flow
    delta = [(2*tbb[i] - v[i]) if (math.isfinite(v[i]) and math.isfinite(tbb[i])) else '' for i in range(n)]
    cvd=[]; s=0.0
    for i in range(n):
        x = delta[i]
        if x=='' or not math.isfinite(x): cvd.append(''); continue
        s += x; cvd.append(s)
    tbr = [(tbb[i]/v[i]) if (math.isfinite(v[i]) and v[i]!=0 and math.isfinite(tbb[i])) else '' for i in range(n)]
    smaV20 = _sma(v,20)
    rvol20=[(v[i]/smaV20[i]) if (math.isfinite(v[i]) and _is_num(smaV20[i]) and smaV20[i]!=0) else '' for i in range(n)]
    avg_trade=[(v[i]/ntr[i]) if (math.isfinite(v[i]) and math.isfinite(ntr[i]) and ntr[i]!=0) else '' for i in range(n)]

    # VWAP-like
    vwap_bar=[(qav[i]/v[i]) if (math.isfinite(qav[i]) and math.isfinite(v[i]) and v[i]!=0) else '' for i in range(n)]
    vwap_sess=[]; sumQ=0.0; sumV=0.0
    for i in range(n):
        qi,vi=qav[i],v[i]
        if math.isfinite(qi) and math.isfinite(vi) and vi!=0:
            sumQ += qi; sumV += vi; vwap_sess.append((sumQ/sumV) if sumV!=0 else '')
        else:
            vwap_sess.append((sumQ/sumV) if sumV!=0 else '')
    # VWMA20
    vwma20=['']*n; qC=[]; qV=[]; sumCV=0.0; sumVv=0.0
    for i in range(n):
        ci,vi=c[i],v[i]
        if math.isfinite(ci) and math.isfinite(vi):
            qC.append(ci*vi); qV.append(vi); sumCV+=ci*vi; sumVv+=vi
            if len(qC)>20:
                sumCV-=qC.pop(0); sumVv-=qV.pop(0)
            vwma20[i] = (sumCV/sumVv) if (len(qC)==20 and sumVv!=0) else ''
        else:
            vwma20[i] = ''

    # Momentum / Trend
    sma20=_sma(c,20); sma50=_sma(c,50); sma200=_sma(c,200)
    ema12=_ema(c,12); ema26=_ema(c,26); ema50=_ema(c,50)
    macd=[(ema12[i]-ema26[i]) if (_is_num(ema12[i]) and _is_num(ema26[i])) else '' for i in range(n)]
    macd_sig=_ema(macd,9)
    macd_hist=[(macd[i]-macd_sig[i]) if (_is_num(macd[i]) and _is_num(macd_sig[i])) else '' for i in range(n)]
    # RSI14 (Wilder)
    rsi14=['']*n
    if n>=15:
        gain=0.0; loss=0.0
        ok=True
        for i in range(1,15):
            if not (math.isfinite(c[i]) and math.isfinite(c[i-1])): ok=False; break
            d=c[i]-c[i-1]; gain+=max(d,0); loss+=max(-d,0)
        if ok:
            ag=gain/14; al=loss/14
            rsi14[14] = 100 if al==0 else (100 - 100/(1+ag/al))
            for i in range(15,n):
                if not (math.isfinite(c[i]) and math.isfinite(c[i-1])): rsi14[i]=''; continue
                d=c[i]-c[i-1]; g=max(d,0); l=max(-d,0)
                ag=(ag*13+g)/14; al=(al*13+l)/14
                rsi14[i] = 100 if al==0 else (100 - 100/(1+ag/al))
    roc10=[(c[i]/c[i-10]-1) if (i>=10 and math.isfinite(c[i]) and math.isfinite(c[i-10]) and c[i-10]!=0) else '' for i in range(n)]
    obv=['']*n; s=0.0
    for i in range(n):
        if i==0 or not (math.isfinite(c[i]) and math.isfinite(c[i-1]) and math.isfinite(v[i])): obv[i]=''; continue
        sign = 1 if c[i]>c[i-1] else (-1 if c[i]<c[i-1] else 0)
        s += sign*v[i]; obv[i]=s

    # ATR14
    prevC=[(c[i-1] if i>0 else math.nan) for i in range(n)]
    trRaw=[max(h[i]-l[i], abs(h[i]-prevC[i]), abs(l[i]-prevC[i])) if (i>0 and math.isfinite(h[i]) and math.isfinite(l[i]) and math.isfinite(prevC[i])) else '' for i in range(n)]
    atr14=_rma(trRaw,14)

    # Money Flow
    CLV=[(((c[i]-l[i])-(h[i]-c[i]))/(h[i]-l[i])) if (math.isfinite(h[i]) and math.isfinite(l[i]) and math.isfinite(c[i]) and (h[i]-l[i])>0) else 0 for i in range(n)]
    ad=[]; s=0.0
    for i in range(n):
        v_ = (CLV[i]*v[i]) if (math.isfinite(CLV[i]) and math.isfinite(v[i])) else float('nan')
        if not math.isfinite(v_): ad.append(''); continue
        s+=v_; ad.append(s)
    cmf20=['']*n; qNum=[]; qDen=[]; sNum=0.0; sDen=0.0
    for i in range(n):
        num = (CLV[i]*v[i]) if (math.isfinite(CLV[i]) and math.isfinite(v[i])) else float('nan')
        den = v[i] if math.isfinite(v[i]) else float('nan')
        if math.isfinite(num) and math.isfinite(den):
            qNum.append(num); sNum+=num; qDen.append(den); sDen+=den
            if len(qNum)>20: sNum-=qNum.pop(0); sDen-=qDen.pop(0)
            cmf20[i]=(sNum/sDen) if (len(qNum)==20 and sDen!=0) else ''
        else: cmf20[i]=''
    tp=[((h[i]+l[i]+c[i])/3) if (math.isfinite(h[i]) and math.isfinite(l[i]) and math.isfinite(c[i])) else float('nan') for i in range(n)]
    rmf=[(tp[i]*v[i]) if (math.isfinite(tp[i]) and math.isfinite(v[i])) else float('nan') for i in range(n)]
    mfi14=['']*n; posQ=[]; negQ=[]; posS=0.0; negS=0.0
    for i in range(n):
        if i==0 or not (math.isfinite(tp[i]) and math.isfinite(tp[i-1]) and math.isfinite(rmf[i])): mfi14[i]=''; continue
        isPos = tp[i]>tp[i-1]; isNeg = tp[i]<tp[i-1]
        pos = rmf[i] if isPos else 0.0; neg = rmf[i] if isNeg else 0.0
        posQ.append(pos); negQ.append(neg); posS+=pos; negS+=neg
        if len(posQ)>14: posS-=posQ.pop(0); negS-=negQ.pop(0)
        mfi14[i] = 100 if negS==0 else (100 - 100/(1+(posS/negS))) if len(posQ)==14 else ''

    # Bands/Channels
    stdev20=_stddev(c,20); bb_mid=sma20
    bb_up=[(bb_mid[i]+2*stdev20[i]) if (_is_num(bb_mid[i]) and _is_num(stdev20[i])) else '' for i in range(n)]
    bb_dn=[(bb_mid[i]-2*stdev20[i]) if (_is_num(bb_mid[i]) and _is_num(stdev20[i])) else '' for i in range(n)]
    bb_w=[((bb_up[i]-bb_dn[i])/bb_mid[i]) if (_is_num(bb_mid[i]) and _is_num(bb_up[i]) and _is_num(bb_dn[i]) and bb_mid[i]!=0) else '' for i in range(n)]
    kc_mid=_ema(c,20)
    kc_up=[(kc_mid[i]+2*atr14[i]) if (_is_num(kc_mid[i]) and _is_num(atr14[i])) else '' for i in range(n)]
    kc_dn=[(kc_mid[i]-2*atr14[i]) if (_is_num(kc_mid[i]) and _is_num(atr14[i])) else '' for i in range(n)]

    # DI/ADX/Donchian
    plusDM=[(max(h[i]-h[i-1],0) if (i>0 and math.isfinite(h[i]) and math.isfinite(h[i-1]) and math.isfinite(l[i]) and math.isfinite(l[i-1]) and (h[i]-h[i-1])>(l[i-1]-l[i])) else 0) if i>0 else '' for i in range(n)]
    minusDM=[(max(l[i-1]-l[i],0) if (i>0 and math.isfinite(h[i]) and math.isfinite(h[i-1]) and math.isfinite(l[i]) and math.isfinite(l[i-1]) and (l[i-1]-l[i])>(h[i]-h[i-1])) else 0) if i>0 else '' for i in range(n)]
    rPlus=_rma(plusDM,14); rMinus=_rma(minusDM,14); tr14=atr14
    di_plus=[(100*rPlus[i]/tr14[i]) if (_is_num(rPlus[i]) and _is_num(tr14[i]) and tr14[i]!=0) else '' for i in range(n)]
    di_minus=[(100*rMinus[i]/tr14[i]) if (_is_num(rMinus[i]) and _is_num(tr14[i]) and tr14[i]!=0) else '' for i in range(n)]
    DX=[(100*abs(di_plus[i]-di_minus[i])/(di_plus[i]+di_minus[i])) if (_is_num(di_plus[i]) and _is_num(di_minus[i]) and (di_plus[i]+di_minus[i])!=0) else '' for i in range(n)]
    adx14=_rma(DX,14)
    don20_hi=_roll_max(h,20); don20_lo=_roll_min(l,20)
    don55_hi=_roll_max(h,55); don55_lo=_roll_min(l,55)

    # Pivots & Divergences (simplified parity to JS flags)
    def pivots_price(k=3, ampK=0.5, minSep=5):
        isHigh=[False]*n; isLow=[False]*n
        for i in range(k,n-k):
            hi=all(math.isfinite(h[i]) and math.isfinite(h[i-j]) and math.isfinite(h[i+j]) and h[i]>h[i-j] and h[i]>h[i+j] for j in range(1,k+1))
            lo=all(math.isfinite(l[i]) and math.isfinite(l[i-j]) and math.isfinite(l[i+j]) and l[i]<l[i-j] and l[i]<l[i+j] for j in range(1,k+1))
            isHigh[i]=hi; isLow[i]=lo
        highs=[]; lows=[]; lastHi=-9999; lastLo=-9999
        for i in range(n):
            if isHigh[i] and (i-lastHi)>=minSep: highs.append((i,h[i])); lastHi=i
            if isLow[i]  and (i-lastLo)>=minSep: lows.append((i,l[i]));  lastLo=i
        swing_hh=[0]*n; swing_hl=[0]*n; swing_lh=[0]*n; swing_ll=[0]*n
        for j in range(1,len(highs)):
            prev,cur=highs[j-1],highs[j]
            swing_hh[cur[0]] = 1 if cur[1]>prev[1] else 0
            swing_lh[cur[0]] = 1 if cur[1]<prev[1] else 0
        for j in range(1,len(lows)):
            prev,cur=lows[j-1],lows[j]
            swing_hl[cur[0]] = 1 if cur[1]>prev[1] else 0
            swing_ll[cur[0]] = 1 if cur[1]<prev[1] else 0
        return highs, lows, swing_hh, swing_hl, swing_lh, swing_ll
    highs,lows,swing_hh,swing_hl,swing_lh,swing_ll = pivots_price()

    def last_two(p): return p[-2:] if len(p)>=2 else []
    # RSI/CVD divergences (use smoothed cvd via RMA(5) as in JS spirit)
    cvd_smooth=_rma([x if _is_num(x) else '' for x in cvd],5)
    def piv_scalar(x, k=3, minSep=5):
        # pick extrema similarly
        hi=[]; lo=[]; lastHi=-9999; lastLo=-9999
        for i in range(k,n-k):
            def ok(idx): return _is_num(x[idx])
            if all(ok(i) and ok(i-j) and ok(i+j) and x[i]>x[i-j] and x[i]>x[i+j] for j in range(1,k+1)):
                if (i-lastHi)>=minSep: hi.append((i,x[i])); lastHi=i
            if all(ok(i) and ok(i-j) and ok(i+j) and x[i]<x[i-j] and x[i]<x[i+j] for j in range(1,k+1)):
                if (i-lastLo)>=minSep: lo.append((i,x[i])); lastLo=i
        return hi, lo
    rsi_hi,rsi_lo = piv_scalar(rsi14)
    cvd_hi,cvd_lo = piv_scalar(cvd_smooth)
    bull_div_rsi=[0]*n; bear_div_rsi=[0]*n; bull_div_cvd=[0]*n; bear_div_cvd=[0]*n
    if len(lows)>=2 and len(rsi_lo)>=2:
        (i1,p1),(i2,p2)=lows[-2],lows[-1]; (j1,a1),(j2,a2)=rsi_lo[-2],rsi_lo[-1]
        if p2<p1 and a2>a1: bull_div_rsi[i2]=1
    if len(highs)>=2 and len(rsi_hi)>=2:
        (i1,p1),(i2,p2)=highs[-2],highs[-1]; (j1,a1),(j2,a2)=rsi_hi[-2],rsi_hi[-1]
        if p2>p1 and a2<a1: bear_div_rsi[i2]=1
    if len(lows)>=2 and len(cvd_lo)>=2:
        (i1,p1),(i2,p2)=lows[-2],lows[-1]; (j1,a1),(j2,a2)=cvd_lo[-2],cvd_lo[-1]
        if p2<p1 and a2>a1: bull_div_cvd[i2]=1
    if len(highs)>=2 and len(cvd_hi)>=2:
        (i1,p1),(i2,p2)=highs[-2],highs[-1]; (j1,a1),(j2,a2)=cvd_hi[-2],cvd_hi[-1]
        if p2>p1 and a2<a1: bear_div_cvd[i2]=1

    # Fibonacci sets
    lo20=_roll_min(l,20); hi20=_roll_max(h,20)
    lo55=_roll_min(l,55); hi55=_roll_max(h,55)
    def fib(lo,hi,ratio):
        return [(lo[i]+ratio*(hi[i]-lo[i])) if (_is_num(lo[i]) and _is_num(hi[i])) else '' for i in range(n)]
    fib20_382=fib(lo20,hi20,0.382); fib20_500=fib(lo20,hi20,0.5); fib20_618=fib(lo20,hi20,0.618)
    fib55_382=fib(lo55,hi55,0.382); fib55_500=fib(lo55,hi55,0.5); fib55_618=fib(lo55,hi55,0.618)

    # Swing-anchored fibs (simplified lastLeg fill)
    # Build arrays L/H that hold last confirmed swing low/high values forward
    Larr=['']*n; Harr=['']*n; lastL=None; lastH=None
    for i in range(n):
        if any(x[0]==i for x in lows): lastL=l[i]
        if any(x[0]==i for x in highs): lastH=h[i]
        if lastL is not None and lastH is not None:
            Larr[i]=lastL; Harr[i]=lastH
    fib_sw_382=fib(Larr,Harr,0.382); fib_sw_500=fib(Larr,Harr,0.5); fib_sw_618=fib(Larr,Harr,0.618)

    # Event-anchored (sma50 x sma200) index
    anchorIdx=0
    for i in range(1,n):
        if not (_is_num(sma50[i]) and _is_num(sma200[i]) and _is_num(sma50[i-1]) and _is_num(sma200[i-1])): continue
        prev=sma50[i-1]-sma200[i-1]; cur=sma50[i]-sma200[i]
        if (prev<=0 and cur>0) or (prev>=0 and cur<0): anchorIdx=i
    minSince=[ '' if i<anchorIdx else min([l[j] for j in range(anchorIdx,i+1) if math.isfinite(l[j])] or [float('inf')]) for i in range(n)]
    maxSince=[ '' if i<anchorIdx else max([h[j] for j in range(anchorIdx,i+1) if math.isfinite(h[j])] or [float('-inf')]) for i in range(n)]
    fibA_382=fib(minSince,maxSince,0.382); fibA_500=fib(minSince,maxSince,0.5); fibA_618=fib(minSince,maxSince,0.618)

    # Assemble matrix (base + ind), preserving order

    header = build_header()

    matrix=[]
    for i in range(n):
        base_row = [
          openTime_str[i], o[i],h[i],l[i],c[i],v[i], closeTime_str[i], qav[i],ntr[i],tbb[i],tbq[i], ign[i]
        ]
        ind_row = [
          delta[i],cvd[i],tbr[i],rvol20[i],avg_trade[i],
          vwap_bar[i],vwap_sess[i],vwma20[i],
          sma20[i],sma50[i],sma200[i],ema12[i],ema26[i],ema50[i],macd[i],macd_sig[i],macd_hist[i],rsi14[i],roc10[i],obv[i],
          ad[i],cmf20[i],mfi14[i],
          atr14[i],bb_mid[i],bb_up[i],bb_dn[i],bb_w[i],kc_mid[i],kc_up[i],kc_dn[i],
          di_plus[i],di_minus[i],adx14[i],don20_hi[i],don20_lo[i],don55_hi[i],don55_lo[i],
          swing_hh[i],swing_hl[i],swing_lh[i],swing_ll[i],bull_div_rsi[i],bear_div_rsi[i],bull_div_cvd[i],bear_div_cvd[i],
          fib20_382[i],fib20_500[i],fib20_618[i],fib55_382[i],fib55_500[i],fib55_618[i],fib_sw_382[i],fib_sw_500[i],fib_sw_618[i],fibA_382[i],fibA_500[i],fibA_618[i]
        ]
        matrix.append(base_row+ind_row)
    return header, matrix

# ---------- Sheets ----------
def sheets_service():
    creds,_ = google_auth_default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
    if not creds.valid: creds.refresh(GARequest())
    return build("sheets","v4",credentials=creds, cache_discovery=False)

def ensure_header(svc, sheet_id: str, tab: str, header: List[str]):
    meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    by_title = {s["properties"]["title"]: s for s in meta.get("sheets", [])}
    req=[]
    if tab not in by_title:
        req.append({"addSheet":{"properties":{"title": tab}}})
    if req:
        svc.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": req}).execute()
    end_col = _col_letters(len(header))
    svc.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{tab}!A1:{end_col}1",
        valueInputOption="RAW",
        body={"values":[header]},
    ).execute()

def clear_data_rows(svc, sheet_id: str, tab: str):
    svc.spreadsheets().values().clear(
        spreadsheetId=sheet_id,
        range=f"{tab}!A2:ZZZ",
        body={}
    ).execute()

def append_rows(svc, sheet_id: str, tab: str, matrix: List[List]):
    if not matrix: return
    svc.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=f"{tab}!A2",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": matrix},
    ).execute()

def main():
    provider = env("PROVIDER","binance")
    symbol   = env("SYMBOL","BTCUSDT")
    since    = env("SINCE","2017-01-01")
    sheet_id = env("SHEET_ID")
    tab      = env("SHEET_TAB","spot1d")
    write_mode = env("WRITE_MODE","replace").lower()  # replace|append
    if not sheet_id:
        print(json.dumps({"ts":utc_now_iso(),"lvl":"ERROR","msg":"SHEET_ID missing"})); sys.exit(2)
    rows = get_raw_klines(provider, symbol, since)
    header, matrix = compute_all(rows)
    svc = sheets_service()
    ensure_header(svc, sheet_id, tab, header)
    if write_mode == "replace":
        clear_data_rows(svc, sheet_id, tab)
    append_rows(svc, sheet_id, tab, matrix)
    print(json.dumps({
        "ts": utc_now_iso(),
        "lvl":"INFO",
        "job":"a01_bsp_pullDaily_sheet_full",
        "rows":len(matrix),
        "sheet_tab":tab,
        "write_mode": write_mode
    },separators=(",",":")))

if __name__ == "__main__":
    main()
