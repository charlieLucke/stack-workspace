# Routing — stack-workspace

> Where a change belongs. Consult this before editing any repo.
>
> The test this file has to pass, set by `plan-zentrales-dashboard`: **does it answer a
> change question you would otherwise have had to guess at?** A row that only restates
> a repo's name is not pulling its weight. The rows below were written against the
> questions that were actually ambiguous at seven repos.

## Ownership by responsibility

| If the change is about… | Repo | Notes |
|-------------------------|------|-------|
| Chunking, embeddings, Late Chunking, BGE-M3 | **titan** | engine internals — local decision |
| Hybrid search / RRF / ranking | **titan** | if the `/search` response shape changes → contract |
| Qdrant collection / vectors / payload index | **titan** | only titan writes Qdrant |
| titan's HTTP endpoints (any path/param/response) | **titan** | **contract change** → update `contracts/titan.openapi.yaml` + brain-mcp + homebase |
| An MCP tool's name/args/result | **brain-mcp** | **contract change** → `contracts/brain-mcp.tools.json` (Claude is the consumer) |
| Vault watcher / debounce / which files get ingested | **brain-mcp** | calls titan `/ingest/file` |
| GitHub-OAuth allowlist, Funnel auth | **brain-mcp** | local to brain-mcp |
| Dashboard UI, status polling, log streaming, start/stop | **homebase** | reads titan `/health` only |
| Inbox extraction, Gemini prompt, note-writing | **obsidian-inbox-watcher** | output must keep `domain:` frontmatter |
| The vault note format / `domain:` field semantics | **system** | shared by inbox-watcher + brain-mcp + titan → workspace decision |
| Planning-time introspection / exposing the workspace to a planning chat | **workspace-mcp** | design-time tool — local decision |
| Transcription, ticket extraction, the prompt that drafts a ticket | **meeting-tickets** | its output lands on the board, not in another repo |
| Reading, claiming or moving a card | **planka-mcp** | the board is the interface; the two Planka repos never call each other |
| Whether a ticket draft is *approved* | **the Planka board** | not a repo. A review UI in homebase would repeat the ADR violation of 2026-08-07 |
| The Planka board's list/column structure | **system** | both Planka repos encode it → workspace decision, not one repo's call |
| A caddy route or a new path under the one Funnel | **workspace-mcp** | the Caddyfile lives in `repos/workspace-mcp/deploy/`, even though it fronts three servers |

## The rows that only exist since 2026-09-04

`plan-zentrales-dashboard` imported three foreign codebases into homebase. Until Phase 2
turns them into modules they sit untouched under `imported/`, and that creates
boundaries that did not exist before:

| If the change is about… | Where | Notes |
|-------------------------|-------|-------|
| Anything under `homebase/imported/` | **nowhere yet** | it is imported *verbatim* and must stay byte-identical until Phase 2. ruff is excluded from it on purpose. Fixing a bug there before Phase 2 means the import is no longer what it claims to be |
| The wake-on-LAN **button** | **homebase** | "everything in one place" is about operating it |
| The wake-on-LAN **sender** | **the hub**, not this repo | a VPS cannot broadcast into the home LAN, and the thing that wakes the workstation must never depend on the workstation |
| Cold start / full shutdown of the stack | **stays a `.bat` script** | homebase runs *inside* WSL: it cannot start Docker Desktop, and `wsl --shutdown` would kill its own caller |
| Reachability lamps, status views from the scripts | **homebase** | the checking-and-reporting half is exactly what a web UI does well — Phase 5 |
| An interactive SSH session (`Mini-PC`, `coolify-prod`) | **stays a `.bat` script** | rebuilding it in the browser means running a web terminal, which is an attack surface out of all proportion to a shortcut |
| Which machine a homebase module is deployed to | **system** | forced by runtime rights, not preference → workspace decision. See SYSTEM.md, "Deployment topology" |
| Any real tailnet host, address or login name | **the vault, never a repo** | repos carry placeholders only. The vault is private; a repo is only private today |

## Cross-repo changes (real examples)

- **"Add a new field to titan's `/search` response"** → contract change. Update
  `contracts/titan.openapi.yaml`, then brain-mcp (the consumer) in the same feature.
  homebase is unaffected (it only uses `/health`).
- **"Change the `domain:` frontmatter rules"** → touches inbox-watcher (writer),
  brain-mcp (watcher/reader) and titan (filter/cache). Workspace plan + decision.
- **"Rename an MCP tool"** → brain-mcp contract; the consumer is Claude itself, so
  update `contracts/brain-mcp.tools.json` and the tool descriptions.
- **"Add a column to the Planka board"** → both meeting-tickets (writes cards into it)
  and planka-mcp (reads and moves them) encode the structure. Neither owns it alone.
- **"Expose homebase from outside"** → not a routing question at all. It is blocked on
  the auth rebuild: the token gate is empty by default and the service drives systemd.

## Quick decision tree

- Engine-internal (chunking, ranking, Qdrant)? → **titan**, local rules.
- Changes a titan endpoint? → contract → titan + brain-mcp (+ homebase if `/health`).
- MCP tool surface? → **brain-mcp** (or **planka-mcp**) contract.
- Note format / `domain:`? → **system-wide** → workspace plan first.
- Touches the board's shape? → **system-wide** → both Planka repos.
- Under `homebase/imported/`? → **wait for Phase 2.**
- Needs a real host or address? → **the vault.**
