# System Decisions Log

> Architecture Decision Records for **cross-repo** choices only. Decisions about a single
> repo's internals belong in that repo's `docs/ai/DECISIONS.md`. Append-only.

## Format

```
## YYYY-MM-DD: Short title
**Decision:** What we decided
**Reasoning:** Why
**Alternatives considered:** What we rejected and why
**Consequences:** What this implies going forward
```

---

## Initial decisions (template defaults)

## 2026-XX-XX: Multi-repo over monorepo
**Decision:** The system is a set of independent repos joined by contracts, coordinated by
this workspace meta-repo — not a single monorepo.
**Reasoning:** Services deploy and version independently; each stays standalone-runnable and
small enough for an agent to hold in context; boundaries are enforced by contracts, not
convention.
**Alternatives considered:** Monorepo (simpler cross-repo refactor, but couples deploys and
blurs ownership). Git submodules (reproducible but painful UX; agents stumble on detached
HEAD).
**Consequences:** Repos are cloned via the `repos.yaml` manifest into `repos/` (gitignored).
Cross-repo coordination happens through contracts, workspace plans, and `workspace.sh`.

## 2026-XX-XX: Contracts are the only coupling
**Decision:** Repos may only depend on each other through interfaces recorded in
`docs/ai/CONTRACTS.md` + `contracts/`. No reaching into another repo's internals.
**Reasoning:** Keeps repos swappable and independently testable; makes breakage detectable
(`workspace.sh contracts`) instead of silent.
**Consequences:** Every published interface needs a contract entry; contract changes are
Opus-level and must update all consumers.

## 2026-XX-XX: Each service is built from the single-repo template
**Decision:** New services are scaffolded from `charlieLucke/python-template` via
`./workspace.sh new`, inheriting uv + ruff + mypy-strict + pytest + pre-commit + CI and the
`docs/ai/` workflow.
**Reasoning:** One set of conventions and one quality gate per repo; the workspace only adds
the system layer on top instead of reinventing per-repo tooling.
**Consequences:** Per-repo conventions live in `shared/` and are pulled in, not copied by hand.

## 2026-06-02: New service `workspace-mcp` for design-time introspection
**Decision:** We are introducing a new repository/service `workspace-mcp` that serves as a read-only MCP server exposing the workspace meta-repo structure, configuration, and code.
**Reasoning:** To allow planning agents (like Opus) to inspect the workspace structure, routing, contracts, and repository code without requiring manual copy-pasting. It runs only at design time, separate from the RAG runtime path, keeping the RAG services clean and decoupled.
**Alternatives considered:** Putting the workspace tools into `brain-mcp` (rejected because `brain-mcp` handles runtime vault RAG and shouldn't contain workspace-level development/introspection capabilities; different lifecycle/deployment cadence).
**Consequences:** A new service is registered in `repos.yaml` on port 9300. It must strictly enforce a read-only boundary to avoid remote code execution or unauthorized repository mutations.
