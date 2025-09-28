# Master Brief

## Objectives
- Deliver a low-touch Bitcoin swing/day trading pipeline with reliable daily feature generation, bounded backtests, and a 06:50 Europe/Bratislava report.
- Maintain paper-trading stability (48h burn-in) before escalating to live execution.
- Keep run costs ≤ $5/month by leveraging managed GCP services and idempotent workloads.
- Ensure idea-to-PR cycle time ≤ 1 day with deterministic builds and enforced documentation updates.

### Non-goals
- Running live trades until Option-A guardrails and KPIs are met.
- Building bespoke broker connectivity outside of Freqtrade integrations.
- Maintaining long-lived service credentials or manual infrastructure.

### Constraints
- Workload Identity Federation only; no JSON keys or plaintext secrets.
- CSV hygiene: UTF-8 (no BOM), LF line endings, ISO-8601Z timestamps, stable header order.
- Append-only storage semantics with explicit versioning when compaction is required.
- Paper-first execution until KPIs demonstrate ≥99% on-time reporting, DQ drift of 0, and backtest variance within ±0.5%.

### Principles
- Correctness and security precede convenience; observability is mandatory for every hop.
- Deterministic, replayable pipelines with least-privilege IAM scopes.
- Structured logging (`YYYY-MM-DDTHH:mm:ss.sssZ [LEVEL] [mod] msg | k=v …`) across services.
- Bounded experimentation: automate roll-forward/rollback paths.

## Architecture
### Option-C (Current)
- Cloud Run Job `a01-obb-pullDaily` pulls ~12 feature sources via OpenBB + partner APIs.
- Features land in Google Cloud Storage as Parquet (primary) and CSV/JSON (interchange) adhering to contracts below.
- Freqtrade backtests run in paper mode with bounded lookbacks; outputs assessed for variance drift.
- Daily report compiled and published by 06:50 Europe/Bratislava with KPI summary (on-time %, DQ drift, bt variance).

### Option-A (Target)
- Promotion to automated execution path once KPIs ≥ thresholds for 14 consecutive runs.
- Orchestrated feature store, live order management, and automated guardrails with rollback automation.
- Expanded observability: real-time dashboards, alerting on SLA breaches, and automated RCAs.

## Data Contracts
| Domain | Examples | Format | Refresh | Notes |
|--------|----------|--------|---------|-------|
| Macro | CPI, PMI, rates | Parquet + CSV snapshot | Daily 06:20 local | ISO-8601Z timestamps, full history append |
| Derivatives | BTC futures basis, funding rates | Parquet + JSON delta | Daily 06:20 local | Contract IDs normalized, counterparty metadata |
| Sentiment | Crypto news, social scores | Parquet + JSON | Daily 06:20 local | Language + source provenance required |
| Crypto-adjacent | On-chain flows, exchange balances | Parquet | Daily 06:20 local | Rolling 30-day retention, anomaly tags |

All datasets must respect schema versioning, stable column ordering, and checksums to detect drift.

## Workflows
- **Timezone**: Europe/Bratislava (CET/CEST); UTC offsets noted per activity.
- **Daily schedule**:
  - 06:20 local (≈04:20Z): trigger OpenBB pulls and partner fetchers.
  - 06:30 local (≈04:30Z): materialize feature sets, validate contracts, stage backtests.
  - 06:40 local (≈04:40Z): evaluate KPIs (on-time %, DQ drift, bt variance) and paper-trade stability.
  - 06:50 local (≈04:50Z): publish report + alerting summary.
- **Backtests**: Freqtrade bounded lookbacks, daily reset, results stored as Parquet + CSV for replay.
- **Reporting**: Structured JSON payload with KPIs + append-only CSV archive.

## Security & Observability
- Authentication via GitHub OIDC → Google Cloud Workload Identity Federation; runtime SA `ft-runtime@warm-melody-458521-g7.iam.gserviceaccount.com`.
- No secrets committed; environment variables injected at deploy time (`DRY_RUN`, `PROJECT_ID`).
- Cloud Logging enforced with structured log lines and trace correlation when available.
- Monitoring KPIs: on-time execution ≥99%, DQ drift = 0 tolerated events, backtest variance |Δ| ≤ 0.5%, paper mode stability ≥48h.

## Decisions Log Stub, Risks, Open Questions
- Decisions tracked in [`docs/DECISIONS.md`](DECISIONS.md); new decisions require ID, rationale, and status.
- **Risks**:
  - External API quota fluctuations impacting 06:20 pulls.
  - Data drift or schema shifts from providers causing contract violations.
  - Cloud Run cold-start latency pushing against SLA without buffering.
- **Open Questions**:
  - When do we elevate to Option-B intermediate staging (semi-automated) before Option-A?
  - Do we require dedicated data quality scoring per source or aggregated across domains?
  - What additional alerting is necessary for paper-trade breach scenarios?
