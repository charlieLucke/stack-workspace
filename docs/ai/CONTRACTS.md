# Contracts — rag-system (FILLED EXAMPLE)

> The two real coupling surfaces in this system: titan's HTTP API and brain-mcp's MCP
> tools. Plus one implicit contract — the vault note format — that ties three repos together.

---

## Contract: titan HTTP API

- **Provider:** repos/titan
- **Consumers:** repos/brain-mcp (search + ingest), repos/brain-dashboard (`/health` only)
- **Machine-readable:** `contracts/titan.openapi.yaml`
- **Transport:** HTTP, `127.0.0.1:8765` (local only)

### Surface
- `GET /health` — BGE-M3 loaded? Qdrant reachable? VRAM use, collection name, ColBERT dim.
- `POST /search` — hybrid search `{query, domain?, top_k}` → ranked chunks.
- `POST /ingest/file` — (re)index one file.
- `GET /domains` — domains with chunk counts.
- `GET /notes` — indexed notes grouped by file; each entry includes `source_path`, `domain`, `chunk_count`, and `content_hash` (sha256 of the note's raw bytes; `null` for legacy/PDF chunks ingested before this field was introduced).
- `GET /domains/{domain}/notes` — notes for a single domain; same fields as `/notes` (incl. `content_hash`); unknown domain → 200 with empty list.
- `POST /find_related` — semantically related documents.
- `DELETE /chunks` — remove a file's chunks.
- `GET /stats` — runtime metrics: uptime, total chunks, domain count, cache hit rate, search-latency p50/p95/max, cache entry count, last-ingest age. In-memory counters, reset on restart; answers even when degraded.

### Invariants & gotchas
- titan binds **127.0.0.1 only** — single-user, no auth/TLS at this layer by design.
- Re-ingest is **upsert-before-delete** (new `run_id`); consumers must not assume an atomic
  swap window.
- `domain` is an optional filter on `/search` and the cache-invalidation key on ingest.

---

## Contract: brain-mcp MCP tools

- **Provider:** repos/brain-mcp
- **Consumers:** Claude (via the custom connector over Tailscale Funnel)
- **Machine-readable:** `contracts/brain-mcp.tools.json`
- **Transport:** MCP over HTTP, `:9100`, GitHub-OAuth gated (allowlist `charlieLucke`)

### Surface
Six tools: `query_knowledge`, `ingest_note`, `list_domains`, `find_related`, `list_notes`,
`delete_note`. Each maps to one or more titan HTTP calls.

### Invariants & gotchas
- Query decomposition is **not** used on the MCP path (Claude decomposes itself).
- Tool results must stay stable for the connector; renaming a tool breaks Claude's calls.
- "Titan unreachable" from a tool means the titan→Qdrant chain below is down, not an MCP bug.

---

## Contract: vault note format (implicit)

- **Provider/Writers:** repos/obsidian-inbox-watcher (and the human editing notes)
- **Consumers:** repos/brain-mcp (watcher → titan `/ingest/file`), repos/titan (domain filter)
- **Machine-readable:** none — enforced by convention, documented here.

### Surface
A Markdown note with YAML frontmatter containing a `domain:` field (`lernen` / `projekte` /
`system` / `business`). `indexed: false` opts a note out (and removes its chunks).

### Invariants & gotchas
- **No `domain:` → not indexed.** This is the single most important shared invariant.
- Changing the allowed domain values touches all three repos → a workspace-level change.
