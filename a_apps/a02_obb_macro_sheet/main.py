from __future__ import annotations
import os, json, sys, math
from datetime import datetime, timezone
from typing import List, Dict, Any

from openbb import obb  # OpenBB builds interface on first import

from google.auth import default as google_auth_default
from google.auth.transport.requests import Request as GARequest
from googleapiclient.discovery import build

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")

def env(name: str, default: str="") -> str:
    return os.getenv(name, default).strip()

# FRED series for BTC regime context
FRED_SERIES = {
    "DGS1":  "US 1Y Treasury Yield (%)",
    "DGS2":  "US 2Y Treasury Yield (%)",
    "DGS10": "US 10Y Treasury Yield (%)",
    "FEDFUNDS": "Effective Federal Funds Rate (%)",
    "DTWEXBGS": "Trade-Weighted US Dollar Index",
    "VIXCLS": "CBOE VIX (close)",
    "SP500": "S&P 500 Index (FRED series)",
    "DCOILWTICO": "WTI Crude Oil (USD/bbl)",
    "GOLDAMGBD228NLBM": "Gold London AM (USD/oz)",
    "CPIAUCSL": "CPI All Urban Consumers (Index)",
    "M2SL": "M2 Money Stock (Billions USD)",
}

def sheets_service():
    creds,_ = google_auth_default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
    if not creds.valid: creds.refresh(GARequest())
    return build("sheets","v4",credentials=creds, cache_discovery=False)

def ensure_header(svc, sheet_id: str, tab: str):
    header = ["date","id","value","source","desc","yc_2s10s","cpi_yoy","m2_yoy"]
    meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    by_title = {s["properties"]["title"]: s for s in meta.get("sheets", [])}
    if tab not in by_title:
        svc.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests":[{"addSheet":{"properties":{"title": tab}}}]}).execute()
    svc.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{tab}!A1:H1",
        valueInputOption="RAW",
        body={"values":[header]},
    ).execute()

def clear_data_rows(svc, sheet_id: str, tab: str):
    svc.spreadsheets().values().clear(
        spreadsheetId=sheet_id,
        range=f"{tab}!A2:H",
        body={}
    ).execute()

def append_rows(svc, sheet_id: str, tab: str, matrix: List[List[Any]]):
    if not matrix: return
    svc.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=f"{tab}!A2",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": matrix},
    ).execute()

def fred_fetch(symbols: List[str], start_date: str):
    out: Dict[str, List[Dict[str, Any]]] = {}
    for sym in symbols:
        try:
            res = obb.economy.fred_series(symbol=sym, start_date=start_date)
            df = res.to_dataframe()
            rows = []
            for _, r in df.iterrows():
                d = r.get("date") or r.get("Date") or r.name
                v = r.get("value") or r.get("Value")
                if d is None or v is None: continue
                d_str = d.date().isoformat() if hasattr(d, "date") else str(d)[:10]
                try: val = float(v)
                except Exception: continue
                rows.append({"date": d_str, "value": val})
            out[sym] = rows
        except Exception as e:
            print(json.dumps({"ts":utc_now_iso(),"lvl":"WARN","sym":sym,"msg":"fred_fetch failed","err":str(e)[:200]}))
            out[sym] = []
    return out

def compute_derivatives(timeline: Dict[str, Dict[str,float]]):
    out = {}
    dates = sorted(timeline.keys())
    for i, d in enumerate(dates):
        row = timeline[d].copy()
        if "DGS10" in row and "DGS2" in row and isinstance(row["DGS10"], (int,float)) and isinstance(row["DGS2"], (int,float)):
            row["yc_2s10s"] = row["DGS10"] - row["DGS2"]
        row["cpi_yoy"] = ""
        row["m2_yoy"] = ""
        if i >= 12:
            prev = timeline.get(dates[i-12], {})
            if "CPIAUCSL" in row and "CPIAUCSL" in prev and prev["CPIAUCSL"]:
                try: row["cpi_yoy"] = (row["CPIAUCSL"]/prev["CPIAUCSL"] - 1.0)
                except Exception: pass
            if "M2SL" in row and "M2SL" in prev and prev["M2SL"]:
                try: row["m2_yoy"] = (row["M2SL"]/prev["M2SL"] - 1.0)
                except Exception: pass
        out[d] = row
    return out

def main():
    sheet_id = env("SHEET_ID")
    if not sheet_id:
        print(json.dumps({"ts":utc_now_iso(),"lvl":"ERROR","msg":"SHEET_ID missing"})); sys.exit(2)
    tab = env("SHEET_TAB","macro_daily")
    since = env("SINCE","2015-01-01")
    write_mode = env("WRITE_MODE","replace").lower()  # replace|append
    fred_key = env("FRED_API_KEY","")
    if fred_key: os.environ["FRED_API_KEY"] = fred_key

    symbols = list(FRED_SERIES.keys())
    fred = fred_fetch(symbols, start_date=since)
    timeline: Dict[str, Dict[str, Any]] = {}
    for sym, rows in fred.items():
        for r in rows:
            d = r["date"]
            timeline.setdefault(d, {})
            timeline[d][sym] = r["value"]
    enriched = compute_derivatives(timeline)

    matrix = []
    for d in sorted(enriched.keys()):
        row = enriched[d]
        for sym, desc in FRED_SERIES.items():
            val = row.get(sym, "")
            matrix.append([d, sym, val, "fred", desc, row.get("yc_2s10s",""), row.get("cpi_yoy",""), row.get("m2_yoy","")])

    svc = sheets_service()
    ensure_header(svc, sheet_id, tab)
    if write_mode == "replace":
        clear_data_rows(svc, sheet_id, tab)
    append_rows(svc, sheet_id, tab, matrix)
    print(json.dumps({
        "ts": utc_now_iso(),
        "lvl":"INFO",
        "job":"a02_obb_macro_sheet",
        "rows": len(matrix),
        "tab": tab,
        "write_mode": write_mode
    },separators=(",",":")))

if __name__ == "__main__":
    main()
