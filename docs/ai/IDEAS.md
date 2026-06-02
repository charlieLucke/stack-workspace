# System Ideas

> Out-of-scope, cross-repo ideas captured during work, to revisit later.
> Single-repo ideas go in that repo's IDEAS.md. Nothing here is committed work.

## Format
- [ ] **YYYY-MM-DD:** Idea description. Which repos it would touch. Why it matters. Rough effort.

---

## Pending

- [ ] **2026-06-02:** Read-only **workspace-introspection MCP server** (new repo
  `workspace-mcp`). Exposes the system to a planning chat (Opus, via the existing
  connector pattern): `get_system_map`, `get_routing`, `get_contract` / `list_contracts`,
  `dependency_graph`, `read_repo_file` (scoped, read-only), `contract_drift`.
  **Why:** closes the `PLANNING.md` gap where Opus in a plain chat can't read the repo
  (today you paste files in by hand). **Scope:** read-only only — no scaffold/check/commit
  over a public connector (security). **Touches:** new repo; reuses `scripts/manifest.py`.
  **Effort:** ~an afternoon, smaller than brain-mcp (no vector DB / GPU). **Do when:** you
  actually feel the friction of pasting files into planning chats — not before (gold-plating).

- [ ] **2026-06-02:** **Startup reconcile for the vault index.** After a cold start, notes
  edited while brain-watcher was *down* are never re-indexed — it's a live-only watchdog
  observer with no baseline catch-up (`brain-mcp/src/brain_mcp/watcher.py` `start()` does no
  scan; `PollingObserver` snapshots at start and only emits later events). A reconcile pass on
  startup should diff the vault against titan's index and re-ingest **only the delta**.
  **Touches (cross-repo):** brain-mcp (the reconcile loop in brain-watcher — the main work)
  **and** titan (enabling piece: expose a per-note content hash or mtime in `GET /notes` so the
  watcher detects drift cheaply without re-reading every file). **Why:** edits made while the
  stack is down silently stay stale in the index — hit this today (the new vault notes won't
  auto-index on restart; they need a manual `touch`/`ingest_note`). **Landing order:** titan
  first (additive hash in `/notes` = contract change), then brain-mcp consumes it.
  **Effort:** small–medium.
