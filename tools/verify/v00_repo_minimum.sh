#!/usr/bin/env bash
set -euo pipefail

TS() { date -u +"%Y-%m-%dT%H:%M:%S.%3NZ"; }
PASS() { echo "$(TS) [INFO] [verify] step=$1 result=PASS"; }
FAIL() { echo "$(TS) [ERROR] [verify] step=$1 result=FAIL reason=\"$2\"" >&2; exit 1; }

step="workflows_exist"
expected_workflows=(".github/workflows/_bq_bootstrap.yml" ".github/workflows/_sheet_ping.yml")
for wf in "${expected_workflows[@]}"; do
  [[ -f "$wf" ]] || FAIL "$step" "missing $wf"
done
count=$(find .github/workflows -maxdepth 1 -name '*.yml' | wc -l | tr -d ' ')
if [[ "$count" != "2" ]]; then
  FAIL "$step" "unexpected workflow count=$count"
fi
PASS "$step"

step="bq_assets"
[[ -f tools/bq/a01_bq_bootstrap_run.sh ]] || FAIL "$step" "missing tools/bq/a01_bq_bootstrap_run.sh"
[[ -f tools/bq/bootstrap.sql ]] || FAIL "$step" "missing tools/bq/bootstrap.sql"
PASS "$step"

step="sheet_assets"
[[ -f tools/verify/a01_verify_bq_location.sh ]] || FAIL "$step" "missing tools/verify/a01_verify_bq_location.sh"
PASS "$step"

PASS "repo_minimum_complete"
