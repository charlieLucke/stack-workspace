# Routing — rag-system (FILLED EXAMPLE)

> Where a change belongs. Consult this before editing any repo.

## Ownership by responsibility

| If the change is about… | Repo | Notes |
|-------------------------|------|-------|
| Chunking, embeddings, Late Chunking, BGE-M3 | **titan** | engine internals — local decision |
| Hybrid search / RRF / ranking | **titan** | if `/search` response shape changes → contract |
| Qdrant collection / vectors / payload index | **titan** | only titan writes Qdrant |
| titan's HTTP endpoints (any path/param/response) | **titan** | **contract change** → update `contracts/titan.openapi.yaml` + brain-mcp + brain-dashboard |
| An MCP tool's name/args/result | **brain-mcp** | **contract change** → `contracts/brain-mcp.tools.json` (Claude is the consumer) |
| Vault watcher / debounce / which files get ingested | **brain-mcp** | calls titan `/ingest/file` |
| GitHub-OAuth allowlist, Funnel auth | **brain-mcp** | local to brain-mcp |
| Dashboard UI, status polling, log streaming, start/stop | **brain-dashboard** | reads titan `/health` only |
| Inbox extraction, Gemini prompt, note-writing | **obsidian-inbox-watcher** | output must keep `domain:` frontmatter |
| The vault note format / `domain:` field semantics | **system** | shared by inbox-watcher + brain-mcp + titan → workspace decision |
| Planning-time introspection / exposing the workspace to a planning chat | **workspace-mcp** | design-time tool — local decision |

## Cross-repo changes (real examples)

- **"Add a new field to titan's `/search` response"** → contract change. Update
  `contracts/titan.openapi.yaml`, then brain-mcp (the consumer) in the same feature.
  brain-dashboard is unaffected (only uses `/health`).
- **"Change the `domain:` frontmatter rules"** → touches inbox-watcher (writer), brain-mcp
  (watcher/reader), and titan (filter/cache). Workspace plan + decision required.
- **"Rename an MCP tool"** → brain-mcp contract; the consumer is Claude itself, so update
  `contracts/brain-mcp.tools.json` and any tool descriptions.

## Quick decision tree

- Engine-internal (chunking, ranking, Qdrant)? → **titan**, local rules.
- Changes a titan endpoint? → contract → update titan + brain-mcp (+ dashboard if `/health`).
- MCP tool surface? → **brain-mcp** contract.
- Note format / `domain:`? → **system-wide** → workspace plan first.
