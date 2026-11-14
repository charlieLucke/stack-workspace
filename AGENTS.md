# Agent Instructions: Multi-Repo System

> Single source for every coding agent. `CLAUDE.md` and `GEMINI.md` only import this file;
> edit here, nowhere else.

You are in the **workspace** (meta-repo) of a system made of independent repos that are
connected only by explicit contracts. Each service under `repos/` is a single-repo project
with its own `AGENTS.md` (older repos: `CLAUDE.md`) and `docs/ai/`.

- **Here:** how the repos relate. Architecture across repos, contracts between them, plans
  that span repos, the system quality gate.
- **There (each `repos/NAME/`):** how one repo is built. Its own instructions govern work
  inside it; this file does not repeat or override them.

A change that crosses a repo boundary or touches a contract is a **planning-level
decision**: it needs a workspace plan and the user's go before any edit. Everything else
you decide and do.

## Read These First

Read on demand, not as a ritual. Open what the task touches:

1. `docs/ai/ROUTING.md`: which repo owns what, before you edit anything
2. `docs/ai/SYSTEM.md`: services, dependency graph, end-to-end data flow
3. `docs/ai/CONTRACTS.md` and `contracts/`: before a change near a boundary
4. The plan in `docs/ai/plans/`: if the task names one; follow it and flag deviations
5. Inside the repo you will edit: that repo's own `AGENTS.md`

If `repos.yaml` has an empty `services:` list, the system is not set up yet: fill in
`docs/ai/SYSTEM.md` with the user, then scaffold services with
`./workspace.sh new my-service "Short description"`.

## The four operating rules

### 1. Locate before editing
Never edit a repo because it is the one you happened to open. `ROUTING.md` says which repo
owns the behavior. One repo affected: work inside it under its own rules. Several repos
affected: workspace plan first (rule 2).

### 2. One feature, many repos, one plan
A feature that spans repos gets a single plan in `docs/ai/plans/`, naming the per-repo
changes and the order they land. Implement repo by repo in dependency order, providers
before consumers. When the feature runs across sessions or tools, track it in the workspace
`docs/ai/CURRENT_TASK.md`; a repo's local notes reference the workspace plan, they do not
copy it.

### 3. Contracts are law
- Never change a published interface without updating its contract and every consumer
  listed in `repos.yaml` (`consumes:` edges).
- A contract change is a planning-level decision: stop and ask, do not improvise.
- After any change near a boundary run `./workspace.sh contracts` to check for drift.

### 4. The system gate is `./workspace.sh check`
`make check` proves one repo is green. `./workspace.sh check` proves the system is: every
repo's gate passes and the contracts still match. A cross-repo task is not done until it is
green, and you show the command and its output. Do not merge a provider change that turns
a consumer red.

## Stop and ask first

- Any contract change: endpoint shape, message schema, a new `consumes:` edge
- A new repo or service boundary, or responsibility moving between repos
- A change that must land in a specific cross-repo order to keep a consumer working
- Two services that disagree about the shape of shared data
- A change in `shared/`, because it propagates to every repo

## Where things belong

- A decision about one repo: that repo's `docs/ai/DECISIONS.md`
- A decision about how repos relate: workspace `docs/ai/DECISIONS.md`
- A plan touching one repo: that repo's `docs/ai/plans/`; touching several: workspace
  `docs/ai/plans/`
- A shared convention: `shared/`, then `./workspace.sh sync-shared`. Never copy it into
  one repo by hand.
- `docs/ai/PLANNING.md` is the brief for a planning session that authors workspace plans.

## Handing over

Only when the user asks for a handoff or the work moves to another tool or model: overwrite
`docs/ai/HANDOFF.md` using the headings already in that file (repos touched and their
commits, what landed, next step, contract status). Within one tool, resuming the session
is enough.

## Known pitfalls

*(Append what cost time once, so it does not cost time twice.)*
