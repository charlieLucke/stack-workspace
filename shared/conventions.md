# Shared Conventions

> The conventions that must be identical across every service in `rag-system`. Each child
> repo's `docs/ai/CONTEXT.md` should say "Conventions: see workspace `shared/conventions.md`"
> rather than copying these, so there is one source of truth. Edit here only.

## Stack (every service)
- **Language:** Python 3.12+
- **Package manager:** uv (`uv add` / `uv remove`, never hand-edit pyproject deps)
- **Lint/format:** ruff — line length 100, double quotes (see `shared/ruff.toml`)
- **Type checker:** mypy strict
- **Tests:** pytest with coverage
- **CI:** GitHub Actions per repo + the system CI here
- **Pre-commit:** ruff, mypy, hygiene checks

## Cross-service consistency rules
- **Errors at boundaries:** services return structured errors (never raw tracebacks across
  a contract). Each repo maps internal exceptions to its contract's error shape.
- **Logging:** stdlib `logging`, structured where it crosses a boundary; never `print()`.
- **Identifiers:** IDs that travel between services are defined once in the contract and
  never reinterpreted locally.
- **Time:** UTC everywhere on the wire; localize only at the edge.
- **Versioning:** additive contract changes are backward-compatible; removals require a
  consumer-first migration recorded in a workspace plan.

## Commit & branch conventions (every repo)
- Commit format: `<type>: <subject>` (feat, fix, refactor, test, docs, chore), imperative.
- One logical change per commit; never mix a contract change with unrelated refactoring.
