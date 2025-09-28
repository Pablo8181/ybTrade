#!/usr/bin/env bash
set -euo pipefail

# Where: tools/bq/a01_bq_bootstrap_run.sh
# What: Run bootstrap.sql with a consistent BigQuery location, overriding any mismatches
# Why: Prevent "Location ... not consistent with current execution region" errors

PROJECT_ID="${PROJECT_ID:?PROJECT_ID is required}"
# Default to US; can be overridden by env/repo var BQ_LOCATION (e.g., EU or europe-central2)
BQ_LOCATION="${BQ_LOCATION:-US}"

ts() { date -u +%FT%T.%3NZ; }
echo "$(ts) [job] [bq] bootstrap start | project=${PROJECT_ID} bq_location=${BQ_LOCATION}"

# Allow workflow to point BIGQUERYRC to the repo copy
export BIGQUERYRC="${BIGQUERYRC:-}"

# Prepare temp SQL enforcing a single location
WORK_SQL="$(mktemp)"
WORK_SQL2="$(mktemp)"

# 1) Normalize any explicit dataset/table CREATE options to our chosen location
#    e.g., CREATE SCHEMA ... OPTIONS(location="US")
sed -E 's/OPTIONS\(\s*location\s*=\s*"[^"]+"\s*\)/OPTIONS(location="'${BQ_LOCATION}'")/Ig' \
  tools/bq/bootstrap.sql > "${WORK_SQL}"

# 2) Prepend SET @@location to force job execution region (must be the first statement)
{
  echo "SET @@location='${BQ_LOCATION}';"
  cat "${WORK_SQL}"
} > "${WORK_SQL2}"

# 3) Execute
bq --project_id="${PROJECT_ID}" --location="${BQ_LOCATION}" query --nouse_legacy_sql < "${WORK_SQL2}"
rc=$?

rm -f "${WORK_SQL}" "${WORK_SQL2}"

if [[ $rc -eq 0 ]]; then
  echo "$(ts) [job] [bq] bootstrap done | project=${PROJECT_ID} bq_location=${BQ_LOCATION} ok=true"
else
  echo "$(ts) [job] [bq] bootstrap failed | project=${PROJECT_ID} bq_location=${BQ_LOCATION} ok=false" >&2
fi
exit $rc

