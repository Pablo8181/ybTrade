# Codex Working Rules
- All changes must flow through pull requests; do not merge or push directly to protected branches.
- Run applicable tests or deterministic checks **before** submitting code when feasible; document the results.
- Every PR description must include: Patch Map, Tests/CI notes, Rollback plan, and Security notes.
- Provide a rollback strategy for any operational change (revert + infrastructure undo steps).
- Never commit secrets, JSON keys, or embed sensitive material; rely on OIDC/WIF and repository secrets only.
- Request and use the minimal permissions necessary; keep outputs deterministic and reproducible.
