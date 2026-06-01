# rag-system

A local, single-workstation retrieval-augmented generation stack


## What this is

A system is built from **independent service repos** connected only by explicit
**contracts** (HTTP APIs, message schemas). Each repo is standalone-runnable and owns
its own tests, CI, and `docs/ai/`. This workspace adds the layer that no single repo
can hold:

| Layer | Lives in | Owns |
|-------|----------|------|
| **System** | this repo | architecture across repos, contracts, cross-repo plans/handoff, shared conventions, system quality gate |
| **Service** | `repos/<name>/` | one bounded responsibility, its own code/tests/CI and local `docs/ai/` |

## Layout

```
repos.yaml            Manifest: every service, its role, contracts, dependency edges
workspace.sh          clone-all · sync · for-each · check · new · contracts
init-workspace.sh     One-time: fill placeholders, git init, self-delete
docs/ai/              System-level agent brain (see below)
  SYSTEM.md           The map: all services, dependency graph, end-to-end data flow
  ROUTING.md          "Which repo owns what / where to make a change"
  CONTRACTS.md        Human source-of-truth for inter-service APIs
  DECISIONS.md        Cross-repo ADRs only (per-repo decisions stay local)
  CURRENT_TASK.md     The active feature that spans repos
  HANDOFF.md          System handoff: which repos at which commit
  IDEAS.md            Parking lot
  plans/              Opus-authored plans that coordinate multiple repos
contracts/            Machine-readable contracts (OpenAPI, JSON Schema, …)
shared/               DRY convention fragments pulled into each child repo
repos/                Cloned child repos (gitignored, each its own git repo)
.github/workflows/    Orchestrating CI: per-repo check + contract verify + smoke
examples/rag-system/  A fully filled-in example system
```

## Commands

```bash
./workspace.sh clone            # clone every service in repos.yaml into repos/
./workspace.sh sync             # git pull --ff-only every service
./workspace.sh status           # short git status of every service
./workspace.sh new <name> <desc># scaffold a new service from the template + register it
./workspace.sh foreach '<cmd>'  # run a shell command in every service repo
./workspace.sh check            # per-repo `make check` + contract verify (the gate)
./workspace.sh contracts        # verify each service still matches its published contract
./workspace.sh lock             # write repos.lock pinning each service to its HEAD commit
./workspace.sh graph            # print the dependency graph from repos.yaml
```

## Working with AI tools

Read `CLAUDE.md` first (mirrored as `AGENTS.md` / `GEMINI.md`). It defines the
**multi-repo operating rules** that sit on top of each child repo's own agent rules:
locate-before-editing via `ROUTING.md`, contracts-are-law, one-feature-one-plan, and
the system quality gate. Child repos keep their own `CLAUDE.md` for local work.

## License

TBD
