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
