import os, sys, json
from google.auth import default as google_auth_default
from google.auth.transport.requests import Request as GARequest
from googleapiclient.discovery import build

def main():
    sheet_id=os.environ.get("SHEET_ID","")
    tab=os.environ.get("SHEET_TAB","spot1d")
    if not sheet_id:
        print('...[ERROR] [verify] step=sheet_schema ok=false reason="missing SHEET_ID"'); sys.exit(2)
    creds,_=google_auth_default(scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    if not creds.valid: creds.refresh(GARequest())
    svc=build("sheets","v4",credentials=creds, cache_discovery=False)
    vals=svc.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"{tab}!1:1").execute().get("values",[[]])[0]
    ok = (len(vals) >= 12) and any(h.startswith("openTime (") for h in vals) and any(h.startswith("fibA_618 (") for h in vals)
    print(f'...[INFO] [verify] step=sheet_schema ok={str(ok).lower()} cols={len(vals)}')
    sys.exit(0 if ok else 1)

if __name__=="__main__":
    main()
