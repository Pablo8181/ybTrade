
from __future__ import annotations
import json
import os
from datetime import datetime, timezone

def utc_now_iso() -> str:
    """Return the current UTC time in ISO-8601 with Z suffix."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def main() -> None:
    payload = {
        "ts": utc_now_iso(),
        "msg": "a01_obb_pullDaily DRY_RUN" if os.getenv("DRY_RUN", "").lower() == "true" else "a01_obb_pullDaily",
        "env": {
            "DRY_RUN": os.getenv("DRY_RUN", ""),
            "PROJECT_ID": os.getenv("PROJECT_ID", ""),
        },
    }
    print(json.dumps(payload, separators=(",", ":")))

if __name__ == "__main__":
    main()
