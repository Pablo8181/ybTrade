# ybTrade

## Overview
ybTrade delivers a low-touch Bitcoin swing/day trading pipeline that currently operates in Option-C (data pull + paper validation) while defining the runway to Option-A (fully automated execution). The platform ingests multi-source features, runs bounded backtests, and produces a 06:50 Europe/Bratislava daily report so the desk can act with confidence.

```
Option-C (Now)                  Threshold Gatekeeper                  Option-A (Target)
┌────────────────────────┐      ┌────────────────────────────┐      ┌────────────────────────────┐
│ OpenBB pull + paper bt │ ───▶ │ KPIs ≥ SLA & guardrails    │ ───▶ │ Automated exec + live ops │
└────────────────────────┘      └────────────────────────────┘      └────────────────────────────┘
```

## Quickstart
1. **Trigger CI/CD**
   - Push to the `dev` branch or run the `CI Deploy` workflow manually (Actions → CI Deploy → _Run workflow_).
   - Optional: provide the pull request number when manually dispatching so the workflow posts deployment details back to the PR.
2. **Run the daily job locally**
   ```bash
   export DRY_RUN=true PROJECT_ID=${PROJECT_ID:-"your-gcp-project-id"}
   python a_apps/a01_obb_pullDaily/main.py
   ```
3. **Inspect Cloud Run job results**
   - Logs Explorer: `https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_job%22%0Aresource.labels.job_name%3D%22a01-obb-pullDaily%22&project=warm-melody-458521-g7`

## Authentication & Secrets
- Workload Identity Federation (OIDC) only; no long-lived keys.
- GitHub repository secrets referenced by automation:
  - `WIF_PROVIDER`
  - `WIF_SERVICE_ACCOUNT`
  - `GCP_PROJECT`
  - `GCP_REGION`
  - `RUNTIME_SA_EMAIL`

## CI/CD Flow
1. GitHub Actions checks out the repo and authenticates to Google Cloud via OIDC.
2. A Docker image is built from `a_apps/a01_obb_pullDaily`, tagged as `${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/trading/app:${GITHUB_SHA}`, and pushed to Artifact Registry.
3. Cloud Run Job `a01-obb-pullDaily` is deployed (idempotently) with deterministic env vars.
4. The job is executed once with `--wait`; its status and logs are reported back to the triggering PR when available.

## Daily Timeline (Europe/Bratislava)
| Local Time | UTC (approx.) | Activity |
|------------|----------------|----------|
| 06:20      | 04:20Z         | Kick off data pulls (OpenBB + macro, derivatives, sentiment, crypto-adjacent sources). |
| 06:30      | 04:30Z         | Transform features to Parquet + CSV/JSON, validate contracts, and stage bounded Freqtrade backtests. |
| 06:40      | 04:40Z         | Review paper-trade stability checks, KPI thresholds, and DQ drift metrics. |
| 06:50      | 04:50Z         | Publish swing/day trading report to stakeholders. |

## Definition of Done Checklist
- [ ] Source integration or logic change has automated tests or a deterministic replay.
- [ ] `README.md`, `docs/MASTER_BRIEF.md`, and `docs/DECISIONS.md` updated when business logic or architecture shifts.
- [ ] CI Deploy workflow succeeds (image pushed, job deployed, execution status succeeded).
- [ ] Structured logs emit `YYYY-MM-DDTHH:mm:ss.sssZ [LEVEL] [mod] msg | k=v …`.
- [ ] Data outputs respect UTF-8 LF, ISO-8601Z timestamps, stable schema, and append-only behavior.
- [ ] Rollback plan documented in the PR (revert + delete/roll back Cloud Run job if required).

### a01_bsp_pullDaily_sheet_full
- **What:** Cloud Run Job that writes BTCUSDT 1d OHLCV **and all indicators** into Google Sheets tab `spot1d`.
- **Why:** Single source of truth for your early PoC; later we may split raw vs features for scale.
- **Secrets:** `SHEET_ID`, `GCP_PROJECT`, `GCP_WIF_PROVIDER`, `RUNTIME_SA_EMAIL`, `GCP_REGION`.
- **Share:** Give Editor access to `${RUNTIME_SA_EMAIL}` on the Sheet.
- **Smoke write:** Run `python tools/verify/smoke_sheet_write.py` with `SHEET_ID` exported and optionally `SHEET_TAB`/`SHEET_CELL`/`SHEET_VALUE`. Defaults write the UTC timestamp into tab `smoke`, cell `A1` so you can confirm the service account has edit rights without touching production tabs.

Run (manual):
1. GitHub → Actions → **a01_bsp_pullDaily_sheet_full** → **Run workflow**
2. Inputs (optional): `since=2017-01-01`, `provider=binance`, `symbol=BTCUSDT`
3. Open the Sheet: verify tab **spot1d** has header + rows.

Schema:
Single header row exactly as in your Apps Script (`name (description)`), base columns first (12), then all indicators.
