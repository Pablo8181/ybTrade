#!/usr/bin/env bash
set -euo pipefail

# Where: tools/verify/a01_verify_bq_location.sh
# What: Quick check that bq runs in the intended location
# Why: Catch region mismatches early in CI

PROJECT_ID="${PROJECT_ID:?PROJECT_ID is required}"
BQ_LOCATION="${BQ_LOCATION:-US}"

ts() { date -u +%FT%T.%3NZ; }

# Return the current @@location (must set first)
OUT="$(bq --location="${BQ_LOCATION}" --project_id="${PROJECT_ID}" query --nouse_legacy_sql --format=json \
  "SET @@location='${BQ_LOCATION}'; SELECT @@location AS loc;")" || {
  echo "$(ts) [ERROR] [verify] step=bq_location ok=false reason=\"bq query failed\" result=FAIL" >&2
  exit 1
}

if echo "$OUT" | grep -q "\"loc\": \"${BQ_LOCATION}\""; then
  echo "$(ts) [INFO] [verify] step=bq_location ok=true loc=${BQ_LOCATION}"
  echo "$(ts) [INFO] [verify] step=bq_location result=PASS"
  exit 0
else
  echo "$(ts) [ERROR] [verify] step=bq_location ok=false reason=\"unexpected @@location\" expected=${BQ_LOCATION} out=${OUT} result=FAIL" >&2
  exit 2
fi

