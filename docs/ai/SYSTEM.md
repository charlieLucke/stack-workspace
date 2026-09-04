# System Map — stack-workspace

> Renamed from `rag-workspace` on 2026-09-04. The old name described what happened to
> land in here first. A workspace is a **development** coordination layer, not a
> deployment unit — there is no reason for locally-running and elsewhere-running
> services to be kept apart in it.
>
> Convention, inherited and kept: **no tailnet hostnames or addresses in this repo.**
> Placeholders like `<workstation>` and `<your-tailnet-host>.ts.net` are deliberate;
> the real values live in the vault, which is private, while this repo is only private
> *today*.

## What this system does

Two halves that were always operated by the same person and are now coordinated in one
place:

- **A local knowledge system.** Documents (Markdown notes, PDFs, inbox files) become a
  searchable vector database and are exposed to Claude. titan is the engine; brain-mcp
  bridges it; obsidian-inbox-watcher feeds it. Everything local — no cloud RAG.
- **The tools around client work.** meeting-tickets turns recorded client conversations
  into reviewed ticket drafts on a Planka board; planka-mcp gives Claude Code that board
  back to work from. Together they close the loop from a spoken sentence to code.

Over both sits **homebase**, the single control surface. It is not part of any data
path — it observes and controls.

## Services

| Service (`repos/<name>`) | Role | Consumes | Exposes | Port |
|--------------------------|------|----------|---------|------|
| **titan** | RAG engine: ingest + hybrid search over Qdrant | — (Qdrant, GPU) | HTTP API (`contracts/titan.openapi.yaml`) | 8765 (127.0.0.1) |
| **brain-mcp** | MCP server + vault watcher; makes notes searchable for Claude | titan | MCP tools (`contracts/brain-mcp.tools.json`) | 9100 (0.0.0.0) |
| **homebase** | The control surface: status, logs, start/stop — growing to front everything here | titan (`/health`) | web UI (not a contract) | 9200 |
| **obsidian-inbox-watcher** | Raw docs → Gemini → vault note | — | vault note format | — (worker) |
| **workspace-mcp** | Read-only MCP server exposing the workspace to planning chats | — | MCP tools (`contracts/workspace-mcp.tools.json`) | 9300 (0.0.0.0) |
| **meeting-tickets** | Recorded client conversations → reviewed ticket drafts → Planka cards | — (Planka HTTP API) | a CLI, not a service | — |
| **planka-mcp** | Gives Claude Code one Planka board: view, claim, work, return for review | — (Planka HTTP API) | MCP tools (no contract extracted yet) | 9101 |

`homebase` was `brain-dashboard` until 2026-09-04. Its Python package, its
`BRAIN_DASH_` env prefix and its unit name still carry the old name; those change in
Phase 2 of `plan-zentrales-dashboard`.

## Dependency graph

```
homebase ──▶ titan ◀── brain-mcp
                           ▲
                           │ (watches vault notes/inbox/)
             obsidian-inbox-watcher

meeting-tickets ──▶ Planka ◀── planka-mcp        (Planka is infra on the hub,
                                                   not a repo here)

workspace-mcp (planning-time introspection, beside the runtime graph)
```

- `brain-mcp` and `homebase` call **titan over HTTP**. titan depends on no repo — only
  on local infra (Qdrant container, BGE-M3 on the GPU).
- `obsidian-inbox-watcher` calls no one; it **writes Markdown notes** into the vault
  inbox, and brain-mcp's watcher ingests them. The coupling is the **vault note format**
  (a `domain:` frontmatter field), not an API call.
- `meeting-tickets` and `planka-mcp` do **not** talk to each other. Both talk to the
  same Planka instance — one writes cards, the other reads and moves them. The board is
  the interface between them, which is why moving a card *is* the feedback.
- `workspace-mcp` is a **design-time** server exposing this meta-repo to a planning
  chat. It is not in any runtime path.

## End-to-end data flow

**Ingest (note path):** edit/drop a `.md` in the vault → brain-mcp's `brain-watcher`
debounces 30 s → `POST titan /ingest/file` → Docling/Markdown read → header chunking →
BGE-M3 Late Chunking (dense+sparse+colbert) → upsert into Qdrant.

**Ingest (document path):** drop PDF/DOCX/URL in the inbox → obsidian-inbox-watcher
extracts text → Gemini classifies/summarizes → writes a `.md` with `domain:` to
`notes/inbox/` → rejoins the note path above.

**Query:** Claude calls `query_knowledge` on brain-mcp → `POST titan /search` (hybrid
dense+sparse+ColBERT, RRF) → ranked chunks → Claude composes the answer.

**Client work:** a recorded conversation → meeting-tickets → reviewed ticket drafts →
Planka cards → planka-mcp hands one to Claude Code → work → back to the board for review.

**Operate:** homebase polls `titan /health` every 3 s, streams systemd/Qdrant logs via
SSE, and starts/stops the stack — it observes and controls, it is not in the data path.

## Boundaries & invariants

- **titan is the only writer of Qdrant.** No other repo touches the vector DB directly.
- **`domain:` frontmatter is mandatory** for a note to be indexed; it is the shared
  identifier tying the inbox-watcher's output to titan's domain filter and cache.
- **Re-ingest is upsert-before-delete** (new `run_id`, old chunks removed after) — no
  repo may assume a note's chunks vanish mid-update.
- **Service startup order:** Qdrant (Docker) → titan → brain-mcp / brain-watcher. A
  consumer seeing "Titan unreachable" means the chain below it is not up.
- **The Planka board is the review surface for ticket drafts.** A second review UI
  inside homebase would repeat the ADR violation of 2026-08-07. homebase may *show* the
  board; it does not become a place to approve drafts.
- **homebase is one codebase, not one process.** Its modules need different runtime
  rights — RAG needs `systemctl --user` inside WSL, the wake module needs host
  networking and the host's SSH keys, Minecraft needs the Docker socket. A shared image
  is possible; a shared set of permissions is not, or every process carries the rights
  of all three.

## Deployment topology

Three machines, because the hardware forces it — not for convenience:

| Where | What runs there | Why it cannot move |
|---|---|---|
| Workstation `<workstation>` (WSL2) | titan, brain-mcp, homebase, workspace-mcp, caddy | the GPU (BGE-M3, faster-whisper `large-v3`) and `systemctl --user` over the stack |
| Hub (always-on mini PC) | obsidian-inbox-watcher, Planka, the wake endpoint | wake-on-LAN is a **LAN broadcast**, and the machine that wakes the workstation must not depend on the workstation |
| Minecraft host | the Minecraft module, when it exists | Docker socket and RCON on the internal network |

- titan binds `127.0.0.1:8765` (local only, by design). brain-mcp binds `0.0.0.0:9100`,
  exposed via **Tailscale Funnel** behind a GitHub-OAuth allowlist. One caddy on 8088
  fronts brain-mcp, workspace-mcp (`/ws`) and planka-mcp (`/planka`); **all three answer
  only while the workstation is on.**
- 🔴 **homebase is not yet fit to be publicly reachable.** It binds `0.0.0.0`, can drive
  systemd units and kill Windows processes, and its `BRAIN_DASH_AUTH_TOKEN` gate is
  **empty by default**, which makes the middleware a no-op. The auth rebuild comes
  before any exposure, not after.
- External dependencies (not repos): Qdrant, BGE-M3 on the GPU, the Gemini API
  (inbox-watcher only), Planka, Tailscale.
