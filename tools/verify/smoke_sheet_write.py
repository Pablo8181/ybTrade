import os
import sys
from datetime import datetime, timezone

from google.auth import default as google_auth_default
from google.auth.transport.requests import Request as GARequest
from googleapiclient.discovery import build


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def main() -> None:
    sheet_id = os.environ.get("SHEET_ID", "").strip()
    if not sheet_id:
        print('...[ERROR] [verify] step=sheet_write ok=false reason="missing SHEET_ID"')
        sys.exit(2)

    tab = os.environ.get("SHEET_TAB", "smoke").strip() or "smoke"
    cell = os.environ.get("SHEET_CELL", "A1").strip() or "A1"
    value = os.environ.get("SHEET_VALUE", "").strip()
    if not value:
        value = f"smoke-test {_utc_now_iso()}"

    range_a1 = f"{tab}!{cell}"

    try:
        creds, _ = google_auth_default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
        if not creds.valid:
            creds.refresh(GARequest())
        svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
        svc.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=range_a1,
            valueInputOption="USER_ENTERED",
            body={"values": [[value]]},
        ).execute()
        print(f'...[INFO] [verify] step=sheet_write ok=true range="{range_a1}" value="{value}"')
    except Exception as exc:  # pragma: no cover - best effort smoke path
        print(
            '...[ERROR] [verify] step=sheet_write ok=false '
            f'reason="{exc.__class__.__name__}: {str(exc).strip()}"'
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
