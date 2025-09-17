import os, datetime, json
print(json.dumps({
  "ts": datetime.datetime.utcnow().isoformat()+"Z",
  "msg": "a01_obb_pullDaily DRY_RUN",
  "env": {k: os.environ.get(k) for k in ["DRY_RUN","PROJECT_ID"]}
}))
