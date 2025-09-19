import json
import os
from datetime import datetime, timezone


def build_payload() -> dict:
    dry_run = os.getenv("DRY_RUN", "")
    project_id = os.getenv("PROJECT_ID", "")

    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "msg": "a01_obb_pullDaily DRY_RUN" if dry_run.lower() == "true" else "a01_obb_pullDaily",  # noqa: E501
        "env": {
            "DRY_RUN": dry_run,
            "PROJECT_ID": project_id,
        },
    }


def main() -> None:
    payload = build_payload()
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
