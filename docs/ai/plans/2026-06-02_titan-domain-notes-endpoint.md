# Plan: `GET /domains/{domain}/notes` (titan)

- **Date:** 2026-06-02
- **Author:** Opus (planning)
- **Implementer target:** Sonnet
- **Status:** ready

## Goal
Add an additive read endpoint to titan that lists the indexed notes within a single
domain. It mirrors the existing `GET /notes` but filtered to one domain. Enables
per-domain views (dashboard panel, inspection, targeted cleanup) with one call.

## Why this is a workspace-level plan
The change is additive *inside* titan, but titan's HTTP surface is a published
**contract** (`contracts/titan.openapi.yaml`). So it touches two repos: `titan` (code)
and this workspace (the contract). **No consumer must change** — the endpoint is purely
additive (brain-mcp and brain-dashboard are unaffected). A future dashboard panel MAY
consume it later; that is out of scope here.

## Affected repos & landing order
1. `repos/titan` (provider) — implement endpoint + tests.
2. workspace — update `contracts/titan.openapi.yaml` + `docs/ai/CONTRACTS.md`.

Order is not critical (additive), but do titan first, then sync the contract.

## Decisions already made — do NOT re-decide
- **Path:** `GET /domains/{domain}/notes` (REST nesting under the existing `/domains`).
- **Schema reuse:** reuse `NoteInfo` (schemas.py:104) and `NotesResponse` (schemas.py:110).
  Do **not** add a new schema.
- **Filtering:** use a Qdrant `scroll_filter` on the `domain` payload field. Mirror the
  filter construction already used in `src/titan/search.py`:
  `Filter(must=[FieldCondition(key="domain", match=MatchValue(value=domain))])`.
  The `domain` payload index already exists, so this is efficient and consistent.
  Do **not** scan all chunks and post-filter in Python.
- **Unknown / empty domain:** return `200` with `notes=[]`, `total=0` (NOT 404) —
  consistent with `/domains` returning an empty list, and simpler for consumers.
- **503 guard:** if `state.qdrant_client is None`, raise `HTTPException(503, ...)` exactly
  like `list_notes` does.

## Steps

### titan — endpoint (`src/titan/service/routes.py`)
1. Add a new route immediately after `list_notes` (after ~line 470), in its own section
   comment. Signature: `async def list_domain_notes(domain: str) -> NotesResponse`.
   Decorator: `@router.get("/domains/{domain}/notes", response_model=NotesResponse)`.
2. Body: copy the scroll-and-aggregate loop from `list_notes`, but pass
   `scroll_filter=<the domain Filter above>` to `state.qdrant_client.scroll(...)`.
   Import `Filter, FieldCondition, MatchValue` from `qdrant_client.models` *locally inside
   the function* (same style as search.py) — no new top-level import.
3. Keep the 503 guard, the 256-page scroll loop, the `with_payload=["source_path",
   "domain"]`, and the final `NotesResponse(notes=sorted-by-source_path, total=len)`
   exactly as in `list_notes`.
4. Update the module docstring endpoint list at the top of `routes.py` (add one line).

### titan — tests (`tests/integration/test_service.py`)
5. Add `test_domain_notes_isolation`, mirroring `test_search_domain_isolation`: ingest one
   note in domain A and one in domain B via the existing `tmp_vault` + `/ingest/file`
   pattern, then `app_client.get("/domains/<A>/notes")` and assert status 200, every
   returned note has `domain == A`, and `total` equals A's note count.
6. Add `test_domain_notes_unknown`: `GET /domains/zzz/notes` → 200 with `notes == []`,
   `total == 0`.

### workspace — contract
7. In `contracts/titan.openapi.yaml`, add the path `/domains/{domain}/notes`: a required
   `domain` path parameter (string) and a 200 response whose body mirrors the `/notes`
   entry (array of `{source_path, domain, chunk_count}` + `total`).
8. In `docs/ai/CONTRACTS.md`, add the new endpoint to titan's "Surface" list.

## Verification (the gate)
- `cd repos/titan && make check` → ruff + mypy (strict) + pytest all green, including the
  two new tests.
- With titan running (`titan-service` + Qdrant up): from the workspace,
  `./workspace.sh contracts` → titan shows **OK** (no DRIFT): the live `/openapi.json` now
  contains the new path and matches the committed contract. (If titan is down it SKIPs —
  not a failure, but the live check is the real proof.)
- `./workspace.sh check` overall green.

## Out of scope
- A brain-mcp MCP tool for this endpoint.
- A brain-dashboard UI panel.
- Pagination / large-collection optimization (the vault is small; a filtered scroll is fine).

## Files to touch (checklist)
- [ ] `repos/titan/src/titan/service/routes.py` — new route + docstring line
- [ ] `repos/titan/tests/integration/test_service.py` — 2 tests
- [ ] `contracts/titan.openapi.yaml` — new path
- [ ] `docs/ai/CONTRACTS.md` — titan surface line
