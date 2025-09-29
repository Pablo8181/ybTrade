# ybTrade Minimal Ops

## Workflows kept
- `_bq_bootstrap.yml`: BigQuery dataset/table bootstrap via OIDC.
- `_sheet_ping.yml`: Google Sheets connectivity probe via OIDC.

## Required GitHub Secrets (values unchanged)
- `WIF_PROVIDER`
- `WIF_SERVICE_ACCOUNT`
- `GCP_PROJECT`
- `SHEET_ID`

These must stay configured for the workflows to run successfully.
