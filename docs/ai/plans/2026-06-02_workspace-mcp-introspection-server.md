# Plan: `workspace-mcp` — read-only workspace-introspection MCP server (NEW REPO)

- **Date:** 2026-06-02
- **Author:** Opus (planning)
- **Implementer target:** Sonnet
- **Status:** ready
- **Tracks IDEAS.md:** "Read-only workspace-introspection MCP server" (2026-06-02)

## Goal
A small **read-only** MCP server that exposes the *workspace meta-repo itself* — system map,
routing, contracts, dependency graph, scoped file reads — to a planning chat. It closes the gap
`PLANNING.md` calls out explicitly ("No repo access? ... ask the user to paste the files"): a
planning model (Opus, via the same connector pattern brain-mcp already uses) can then **read the
system directly** instead of you hand-pasting `SYSTEM.md`/`ROUTING.md`/`CONTRACTS.md`/code.

This is a **new service**, not an edit to an existing repo (see "Why a new repo").

## Why this is a workspace-level plan
It creates a **new module boundary** — itself a workspace-level decision (record it in
`docs/ai/DECISIONS.md`) — and registers a new node in `repos.yaml` + `SYSTEM.md` + `ROUTING.md`.

## Why a new repo (not a module inside brain-mcp)
Different bounded responsibility and lifecycle:
- **brain-mcp** serves the *vault contents* to Claude for Q&A at **runtime**.
- **workspace-mcp** serves the *workspace meta-repo* (docs, manifest, contracts) to a *planning*
  chat at **design time**. It owns no vault, no Qdrant, no GPU; it deploys/releases on its own
  cadence and would be embarrassing to couple to the RAG runtime.
They share a transport *pattern*, not a deployment. Independent lifecycle ⇒ new repo. (Resisting
the opposite trap too: it is genuinely a separate concern, not "brain-mcp but bigger.")

## Affected repos & landing order
A new provider that **nothing else consumes**, so it simply lands and goes green on its own:
1. workspace: scaffold + register the repo, design its contract, record the decision.
2. `repos/workspace-mcp`: implement the read-only server + tests.

No existing repo changes. (titan is only *optionally* read for the drift tool — see stretch.)

## Decisions already made — do NOT re-decide

### Read-only is a hard security boundary
- **Only read tools.** No `new`/`adopt`/`check`/`commit`/scaffold/shell-mutation tools, ever.
  This server is meant to be reachable over the **same public path as brain-mcp** (Tailscale
  Funnel + GitHub-OAuth allowlist). A public connector that can write the repo or run arbitrary
  commands is unacceptable. Every tool is a pure read.
- **Auth + transport mirror brain-mcp exactly.** Reuse the pattern in
  `repos/brain-mcp/src/brain_mcp/{mcp_server.py,auth.py,config.py}`: `FastMCP`,
  `OAuthProxy` via a `build_github_auth` helper, `GitHubAllowlistVerifier`, a pydantic-settings
  `Settings` with env prefix `WORKSPACE_`, and a `main()` that switches `stdio`/`http` transport.
  Copy auth.py (~30 lines) into the new repo — repos stay decoupled (same rationale as brain-mcp's
  local schema copy); note in a comment that it mirrors `brain-mcp/auth.py`.
- **Port 9300.** 8765 (titan), 9100 (brain-mcp), 9200 (dashboard) are taken; 9300 is free.

### Configuration
- `WORKSPACE_ROOT: Path` — the workspace meta-repo root (the dir containing `repos.yaml`).
  Default: resolve upward from the package, or accept an env var; in deployment it points at
  `~/projects/rag-workspace`. **All file access is rooted here.**
- Reuse the standard brain-mcp auth/transport settings (`WORKSPACE_MCP_TRANSPORT`,
  `_HOST`, `_PORT`, `_MCP_AUTH`, `_MCP_BASE_URL`, `WORKSPACE_GITHUB_CLIENT_ID/_SECRET/_ALLOWED_LOGINS`).

### Reusing `scripts/manifest.py` (don't duplicate manifest logic)
- For graph/consumers/names, **shell out** to the workspace's own script:
  `python3 {WORKSPACE_ROOT}/scripts/manifest.py <subcommand>` (e.g. `graph`, `names`,
  `consumers <name>`). That reuses the real, tested logic rather than re-parsing YAML.
- For doc/contract **content**, read the files directly (`WORKSPACE_ROOT/docs/ai/*.md`,
  `WORKSPACE_ROOT/contracts/*`). They're plain text.

### `read_repo_file` is the one tool with attack surface — pin the sandbox
- Signature: `read_repo_file(repo: str, relpath: str) -> str`.
- `repo` must be one of the manifest's service names (reject otherwise).
- Resolve `base = (WORKSPACE_ROOT/"repos"/repo).resolve()` (this follows the symlink to the real
  repo) and `target = (base / relpath).resolve()`; **reject** unless `target.is_relative_to(base)`
  (blocks `..`/absolute escapes — mirror titan's `_path_check`, routes.py:202).
- Read-only; refuse non-files; cap at a sane size (e.g. 200 KB) and return text only.

### Tool set (final, all read-only)
1. `list_repos()` → service names + roles (from `manifest.py names` + `field <name> role`).
2. `get_system_map()` → `docs/ai/SYSTEM.md`.
3. `get_routing()` → `docs/ai/ROUTING.md`.
4. `get_contracts_overview()` → `docs/ai/CONTRACTS.md`.
5. `list_contracts()` → filenames in `contracts/`.
6. `get_contract(name)` → contents of `contracts/<name>` (sandboxed to the `contracts/` dir).
7. `dependency_graph()` → output of `manifest.py graph` (consumer → provider edges).
8. `read_repo_file(repo, relpath)` → scoped read (above).
9. **(stretch, optional)** `contract_drift(service)` → shell `scripts/contract_diff.py` against the
   service's live spec; returns in-sync / drift / skipped. Needs the service running, so mark it
   clearly as best-effort and ship it only if Stage 2 has room.

## Steps

### Stage 1 — scaffold, contract, registration (workspace)
1. `./workspace.sh new workspace-mcp "Read-only MCP server exposing the workspace to planning chats"`
   — scaffolds from `charlieLucke/python-template` into `repos/workspace-mcp`.
2. **Design the contract first** (boundary before code):
   - Create `contracts/workspace-mcp.tools.json` mirroring the shape of
     `contracts/brain-mcp.tools.json` — list each tool name + a one-line description + args.
   - Add a **"Contract: workspace-mcp MCP tools"** section to `docs/ai/CONTRACTS.md`
     (provider: repos/workspace-mcp; consumer: a planning chat via the connector; transport: MCP
     over HTTP `:9300`, GitHub-OAuth gated; invariant: **read-only**).
3. Register in `repos.yaml`:
   ```
   - name: workspace-mcp
     role: Read-only MCP server exposing the workspace (map, routing, contracts, graph) to planning chats
     consumes: []          # reads workspace files; no runtime dependency on other services
     exposes: contracts/workspace-mcp.tools.json
     port: 9300
   ```
   (If the stretch drift tool is included, set `consumes: [titan]` and note it reads `/openapi.json`.)
4. Update `docs/ai/SYSTEM.md`: add workspace-mcp to the Services table and a one-line note in the
   graph/data-flow section (it sits *beside* the runtime graph — a design-time reader of the repo,
   not in the data path; say so explicitly so it isn't mistaken for a runtime dependency).
5. Update `docs/ai/ROUTING.md`: add a row — "planning-time introspection / exposing the workspace
   to a planning chat → **workspace-mcp**".
6. `./workspace.sh adopt workspace-mcp` — drops `repos/workspace-mcp/docs/ai/SYSTEM_LINK.md` and
   patches its CLAUDE/AGENTS/GEMINI "Read These First".
7. Record the decision in `docs/ai/DECISIONS.md` (new module boundary: why a separate repo, the
   read-only constraint, the shared connector/auth pattern).

### Stage 2 — implement the server (repos/workspace-mcp)
8. `src/workspace_mcp/config.py` — `Settings(BaseSettings)` with `env_prefix="WORKSPACE_"`:
   `workspace_root: Path`, transport/host/port (default 9300), and the GitHub-OAuth fields.
   Mirror `brain_mcp/config.py`.
9. `src/workspace_mcp/auth.py` — copy `brain_mcp/auth.py` (`GitHubAllowlistVerifier` +
   `build_github_auth`); comment that it mirrors brain-mcp.
10. `src/workspace_mcp/server.py` — `FastMCP("workspace", auth=_build_auth())` (mirror
    `mcp_server.py:_build_auth`), plus the read-only tools above. Helpers:
    - `_read(rel: str) -> str` — read a file under `WORKSPACE_ROOT`, sandboxed via `is_relative_to`.
    - `_manifest(*args) -> str` — `subprocess.run([sys.executable, str(WORKSPACE_ROOT/"scripts/manifest.py"), *args], cwd=WORKSPACE_ROOT, capture_output=True, text=True, check=True)`, return stdout.
    - Each tool wraps these and returns Markdown/text; on error return a short `"Error: ..."`
      string (mirror brain-mcp's tool error style — never raise to the transport).
11. `src/workspace_mcp/main.py` (or `__main__`) — `main()` switching stdio/http transport, mirror
    `mcp_server.py:main`.
12. **Tests** (`tests/`): build a `tmp_workspace` fixture writing a minimal `repos.yaml` + a few
    `docs/ai/*.md` + a `contracts/foo.yaml` + a fake `repos/<svc>/` dir, point `WORKSPACE_ROOT` at
    it, and assert each tool returns the expected content. **Required:** a path-traversal test —
    `read_repo_file("titan", "../../secret")` and `get_contract("../config")` are rejected. Mirror
    the offline/mocked style of `brain-mcp/tests/test_mcp_tools.py`.
13. Fill `repos/workspace-mcp/docs/ai/CONTEXT.md` briefly (what the repo is, the read-only rule).

## Tracking
Workspace `docs/ai/CURRENT_TASK.md` → this plan; new repo's `CURRENT_TASK.md` → back to it.
Natural handoff point: between Stage 1 (repo exists, registered, contract drafted) and Stage 2.

## Verification
- **Stage 1:** `repos/workspace-mcp` exists with template tooling; `./workspace.sh status` lists it;
  `./workspace.sh check` (manifest validates — `workspace-mcp` present, contract file exists) green;
  `repos.yaml`/`SYSTEM.md`/`ROUTING.md`/`CONTRACTS.md`/`DECISIONS.md` updated.
- **Stage 2 static:** `cd repos/workspace-mcp && make check` (ruff + mypy-strict + pytest, incl. the
  tool tests + the path-traversal rejection test).
- **Stage 2 runtime:** run `workspace-mcp` over **stdio** locally (`WORKSPACE_ROOT` → the workspace)
  and exercise the tools (FastMCP dev/inspector or a smoke script): `get_system_map`,
  `dependency_graph`, `read_repo_file("titan","README.md")` return real content; a `..` path is
  refused. (Public HTTP/Funnel deployment is a separate ops step, not part of this plan.)
- `./workspace.sh check` green overall.

## Out of scope
- Any write/mutating capability (scaffold, adopt, commit, run) — permanently out by design.
- Public Funnel/systemd deployment + the GitHub OAuth app setup (an ops follow-up).
- A vector index over the docs / semantic search of the workspace (this is structural reads only).
- Auto-syncing the contract JSON from the live tool list (hand-maintained for now, like brain-mcp).
- The `contract_drift` tool unless Stage 2 has room (it's the only one needing a live service).

## Files to touch (checklist)
**Stage 1 — workspace**
- [ ] `repos.yaml` — new `workspace-mcp` service entry
- [ ] `contracts/workspace-mcp.tools.json` — tool contract
- [ ] `docs/ai/CONTRACTS.md` — new contract section
- [ ] `docs/ai/SYSTEM.md` — services table + note
- [ ] `docs/ai/ROUTING.md` — ownership row
- [ ] `docs/ai/DECISIONS.md` — new-module-boundary decision
- [ ] `repos/workspace-mcp/docs/ai/SYSTEM_LINK.md` — via `./workspace.sh adopt`
**Stage 2 — repos/workspace-mcp**
- [ ] `src/workspace_mcp/config.py`
- [ ] `src/workspace_mcp/auth.py`
- [ ] `src/workspace_mcp/server.py`
- [ ] `src/workspace_mcp/main.py` (entry point)
- [ ] `tests/` — per-tool tests + path-traversal rejection test
- [ ] `repos/workspace-mcp/docs/ai/CONTEXT.md`
