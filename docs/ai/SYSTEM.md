# System Map — rag-system (FILLED EXAMPLE)

> A real instantiation: charlie's local RAG stack. Four independent repos in ~/projects,
> joined only by titan's HTTP API and a shared vault-note format.

## What this system does

A local, single-workstation knowledge system. Documents (Markdown notes, PDFs, and inbox
files like PDF/DOCX/URLs) are turned into a searchable vector database and exposed to
Claude. titan is the engine; brain-mcp bridges it to Claude; brain-dashboard operates it;
obsidian-inbox-watcher feeds raw documents in. Everything runs locally — no cloud RAG.

## Services

| Service (`repos/<name>`) | Role | Consumes | Exposes | Port |
|--------------------------|------|----------|---------|------|
| **titan** | RAG engine: ingest + hybrid search over Qdrant | — (Qdrant, GPU) | HTTP API (`contracts/titan.openapi.yaml`) | 8765 (127.0.0.1) |
| **brain-mcp** | MCP server + vault watcher; makes notes searchable for Claude | titan | MCP tools (`contracts/brain-mcp.tools.json`) | 9100 (0.0.0.0) |
| **brain-dashboard** | Web control panel: status, logs, start/stop | titan (`/health`) | web UI (not a contract) | 9200 |
| **obsidian-inbox-watcher** | Raw docs → Gemini → vault note | — | vault note format | — (worker) |

## Dependency graph

```
brain-dashboard ──▶ titan ◀── brain-mcp
                                  ▲
                                  │ (watches vault notes/inbox/)
                    obsidian-inbox-watcher
```

- `brain-mcp` and `brain-dashboard` call **titan over HTTP**. titan depends on no repo —
  only on local infra (Qdrant container, the BGE-M3 model on the GPU).
- `obsidian-inbox-watcher` doesn't call anyone; it **writes Markdown notes** into the vault
  inbox. brain-mcp's *watcher* component then ingests them into titan. The coupling is the
  **vault note format** (a `domain:` frontmatter field), not an API call.

## End-to-end data flow

**Ingest (note path):** edit/drop a `.md` in the vault → brain-mcp's `brain-watcher` debounces
30 s → `POST titan /ingest/file` → Docling/Markdown read → header chunking → BGE-M3 Late
Chunking (dense+sparse+colbert) → upsert into Qdrant.

**Ingest (document path):** drop PDF/DOCX/URL in the inbox → obsidian-inbox-watcher extracts
text → Gemini classifies/summarizes → writes a `.md` with `domain:` to `notes/inbox/` →
(rejoins the note path above via brain-watcher).

**Query:** Claude calls an MCP tool on brain-mcp (`query_knowledge`) → brain-mcp →
`POST titan /search` (hybrid dense+sparse+ColBERT, RRF) → ranked chunks → Claude composes
the answer.

**Operate:** brain-dashboard polls `titan /health` every 3 s, streams systemd/Qdrant logs
via SSE, and starts/stops the stack — it observes and controls, it is not in the data path.

## Boundaries & invariants

- **titan is the only writer of Qdrant.** No other repo touches the vector DB directly.
- **`domain:` frontmatter is mandatory** for a note to be indexed; it is the shared
  identifier that ties the inbox-watcher's output to titan's domain filter and cache.
- **Re-ingest is upsert-before-delete** (new `run_id`, old chunks removed after) — no repo
  may assume a note's chunks vanish mid-update.
- **Service startup order:** Qdrant (Docker) → titan → brain-mcp / brain-watcher. A
  consumer that gets "Titan unreachable" means the chain below it isn't up.

## Deployment topology

- All services run in **WSL2 (Ubuntu)** as systemd user services on the workstation
  `charliespc`. Qdrant runs in **Docker Desktop on Windows** (`qdrant_workstation`, ports
  6333/6334).
- titan binds `127.0.0.1:8765` (local only, by design). brain-mcp binds `0.0.0.0:9100` and
  is exposed publicly via **Tailscale Funnel** (`charliespc.taild04050.ts.net`), gated by
  GitHub-OAuth allowlist — the only service reachable from outside.
- External dependencies (not repos): Qdrant, the BGE-M3 model (GPU), the Gemini API
  (inbox-watcher only), Tailscale.
