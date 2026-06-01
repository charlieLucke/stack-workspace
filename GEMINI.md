# Agent Instructions – Multi-Repo System

> This file is mirrored across `CLAUDE.md`, `AGENTS.md`, and `GEMINI.md` so the same
> instructions load in any AI environment. Do not edit one without updating the others.

You are operating inside a **system made of multiple independent repos**, connected only
by explicit contracts. This is the *workspace* (meta-repo) layer. Each service repo under
`repos/` is itself a single-repo project with its own `CLAUDE.md` and `docs/ai/`.

Two layers, two jobs:

- **Here (workspace):** the system-level "what" and "how repos relate" — architecture
  across repos, contracts between them, plans that span repos, the system quality gate.
- **There (each `repos/<name>/`):** the per-repo "how" — idiomatic, tested code that fits
  that one repo. Its own `CLAUDE.md` governs work *inside* it.

As in the single-repo template: **architectural decisions are made by a planning model
(Opus) and saved as plans; implementation is delegated to a faster model.** The multi-repo
layer adds one rule on top — *a change that crosses a repo boundary or touches a contract
is always an Opus-level decision.*

---

## Read These First (every session)

1. `docs/ai/SYSTEM.md` — the map: services, dependency graph, end-to-end data flow
2. `docs/ai/ROUTING.md` — which repo owns what; where a given change belongs
3. `docs/ai/CURRENT_TASK.md` — the active cross-repo feature (if any)
4. `docs/ai/HANDOFF.md` — if resuming an interrupted cross-repo session, start here
5. The relevant plan in `docs/ai/plans/` if the task references one
6. Then, **inside the repo you'll edit**, that repo's own `CLAUDE.md` + `docs/ai/CONTEXT.md`

If any of these are missing or empty, ask the user before guessing.

---

## First-Time Setup

If this is a fresh workspace (README still says `SYSTEM_NAME`, `repos.yaml` has an empty
`services:` list, `docs/ai/SYSTEM.md` is still a stub):

1. Ask the user for the system name, description, and what they're building.
2. Offer to run `./init-workspace.sh <name> "<desc>"`.
3. Interview the user and fill in `docs/ai/SYSTEM.md` (the service list + dependency graph).
4. Scaffold the first services with `./workspace.sh new <name> "<desc>"`.
5. Only then proceed with actual work.

---

## The Multi-Repo Operating Rules

These four rules are the whole point of this layer. Everything else is detail.

### 1. Locate before editing
Never start editing in a repo because it's the one you happened to open. For any task:
1. Consult `ROUTING.md` to find which repo **owns** the behavior.
2. If the task touches exactly one repo, hand off into that repo and follow *its* rules.
3. If the task crosses repos, it needs a **workspace plan** (next rule) before any edit.

### 2. One feature, many repos, one plan
A feature that spans repos gets a **single** Opus plan in `docs/ai/plans/`, naming the
per-repo sub-changes and the order they must land. Then:
- The workspace `CURRENT_TASK.md` tracks the overall feature.
- Each affected repo's local `CURRENT_TASK.md` references the workspace plan, not a copy.
- Implement repo-by-repo in dependency order (providers before consumers).

### 3. Contracts are law
The only thing holding the repos together is the contract registry (`docs/ai/CONTRACTS.md`
+ machine-readable files in `contracts/`). Therefore:
- **Never change a published interface without updating its contract AND every consumer**
  listed in `repos.yaml` (`consumes:` edges).
- A contract change is an **Opus-level decision** — stop and escalate, don't improvise.
- Provider and consumers must land in the agreed order; record it in the plan.
- After any change near a boundary, run `./workspace.sh contracts` to verify drift.

### 4. The system quality gate is `./workspace.sh check`
`make check` proves one repo is green. `./workspace.sh check` proves the *system* is:
every repo's gate passes **and** contracts still match. A cross-repo task is not done
until this is green. Don't merge a provider change that reds a consumer.

---

## Inherit the single-repo discipline

Everything from the single-repo template still applies **inside** each repo — read before
writing, push complexity into deterministic tooling (`make`), self-anneal on errors, stay
in scope, be token-conscious, update living documents. This file does not repeat those;
each repo's `CLAUDE.md` carries them. Do not contradict them from up here.

---

## When to Stop and Escalate to the Planning Model (Opus)

Stop and flag for Opus consultation if you encounter:

- **Any contract change** (endpoint shape, message schema, a new `consumes:` edge).
- A new repo / service boundary, or moving responsibility between repos.
- A change that must land in a specific cross-repo order to avoid breaking a consumer.
- Two services that disagree about the shape of shared data.
- A shared convention change in `shared/` (it propagates to every repo).
- Plus all the single-repo escalation triggers, when working inside a repo.

For everything else: proceed.

---

## File Organization (workspace level)

```
docs/ai/
├── SYSTEM.md         # Services, dependency graph, end-to-end data flow
├── ROUTING.md        # Which repo owns what; where a change belongs
├── CONTRACTS.md      # Human source-of-truth for inter-service contracts
├── DECISIONS.md      # Cross-repo ADRs only
├── CURRENT_TASK.md   # Active cross-repo feature
├── HANDOFF.md        # System handoff (which repos at which commit)
├── IDEAS.md          # Out-of-scope ideas
├── PLANNING.md       # Opus planning brief — load into a planning chat to author plans
└── plans/            # Opus plans that coordinate multiple repos
contracts/            # Machine-readable contracts (OpenAPI, JSON Schema, …)
shared/               # Convention fragments DRY-pulled into each child repo
repos.yaml            # Manifest (the dependency graph lives here, as data)
```

**Where does X belong?**
- A decision about *one* repo → that repo's `docs/ai/DECISIONS.md`.
- A decision about *how repos relate* → workspace `docs/ai/DECISIONS.md`.
- A plan touching one repo → that repo's `docs/ai/plans/`.
- A plan touching several → workspace `docs/ai/plans/`.

---

## System Handoff Format

When ending a cross-repo session, write or overwrite `docs/ai/HANDOFF.md`:

```markdown
# System Handoff – YYYY-MM-DD HH:MM
Model: <which model wrote this>

## Feature in progress
- Workspace plan: docs/ai/plans/<file>

## Repos touched (and commit/branch each is on)
- repos/<name> @ <branch/sha> — <what changed, what's left>

## Landed so far (in dependency order)
- ...

## Next concrete step (which repo, which change)
- ...

## Contract status
- [ ] contracts/ updated   [ ] all consumers updated   [ ] `workspace.sh contracts` green

## Open questions / decisions needed (Opus)
- ...
```

---

## Anti-Patterns (do not do)

- Don't edit a child repo without first checking `ROUTING.md` — you may be in the wrong one.
- Don't change a provider's interface and leave consumers for "later".
- Don't copy a shared convention into one repo by hand — change it in `shared/` and propagate.
- Don't duplicate a service's internals up here; the workspace knows *contracts*, not guts.
- Don't land a cross-repo feature with `./workspace.sh check` red.
- Don't invent a new repo or boundary without an Opus decision in workspace `DECISIONS.md`.

---

## Summary

You sit above several independent repos. Locate the right repo before touching anything,
treat contracts as law, give every cross-repo feature one plan, and keep the whole system
green with `./workspace.sh check`. Inside a repo, defer to its own `CLAUDE.md`.

Be precise. Respect boundaries. Keep the contracts honest.
