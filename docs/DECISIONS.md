# Decisions Log

| ID | Date (UTC) | Decision | Rationale | Impact | Status |
|----|------------|----------|-----------|--------|--------|
| D-001 | 2025-09-20 | Option-C now → Option-A on thresholds | Stabilize data + paper trading before automation; promote once KPIs met. | Reduces operational risk, enforces measurable gates. | Accepted |
| D-002 | 2025-09-20 | OpenBB for features; Freqtrade for exec | Leverage mature tooling for data sourcing and strategy validation. | Accelerates delivery, aligns with paper-first workflow. | Accepted |
| D-003 | 2025-09-20 | CSV/UTC rules enforced in CI | Prevent schema drift and timezone ambiguity across exports. | Ensures downstream compatibility and auditability. | Accepted |
| D-004 | 2025-09-20 | OIDC/WIF only; no JSON keys | Eliminate long-lived secrets while enabling GitHub→GCP auth. | Improves security posture and compliance. | Accepted |
| D-005 | 2025-09-20 | Paper-first; gated live | Require ≥48h stability before enabling live orders. | Guards capital and builds operational confidence. | Accepted |
