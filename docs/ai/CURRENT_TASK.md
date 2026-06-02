# Current Cross-Repo Task

> Only for features that span more than one repo. Single-repo work is tracked in that
> repo's own CURRENT_TASK.md. Keep this short.

## Goal
Implement a one-shot startup reconcile pass in brain-watcher (brain-mcp) that diffs the vault against titan's index and re-ingests/deletes only the delta, using content_hash as the drift signal.

## Workspace plan
[2026-06-02_vault-index-startup-reconcile.md](file:///home/charl/projects/rag-workspace/docs/ai/plans/2026-06-02_vault-index-startup-reconcile.md)

## Per-repo sub-steps (in landing order: providers before consumers)
- [x] repos/titan — `content_hash` payload key on ingest + expose on GET `/notes` and GET `/domains/{domain}/notes` (+ update contract)
- [x] repos/brain-mcp — mirror `content_hash` in schema, implement `_reconcile()`, call at startup, and add tests

## Contract checklist
- [x] contracts/ updated
- [x] CONTRACTS.md updated
- [x] all consumers updated
- [x] `./workspace.sh contracts` green

## Blockers
None. Feature is fully landed, verified, committed, and `./workspace.sh check` is green.
