# Plan: Startup reconcile for the vault index (titan note-hash → brain-watcher reconcile)

- **Date:** 2026-06-02
- **Author:** Opus (planning)
- **Implementer target:** Sonnet
- **Status:** ready
- **Tracks IDEAS.md:** "Startup reconcile for the vault index" (2026-06-02)

## Goal
After a cold start, notes that were **edited, created, or deleted while brain-watcher was
down** are never reconciled — `PollingObserver` snapshots the tree at `start()` and only emits
*subsequent* events (`watcher.py:142` does no baseline scan). So edits made while the stack is
off stay stale in titan's index until a manual `touch`/`ingest_note`. This feature adds a
**one-shot reconcile pass on watcher startup** that diffs the vault against titan's index and
re-ingests/deletes **only the delta**.

The cheap, exact drift signal is a **per-note content hash** exposed by titan in `GET /notes`.
The watcher computes the same hash locally and compares.

## Why this is a workspace-level plan
It crosses a repo boundary **and** changes a published contract:
- **titan** gains a new payload field and a new **additive** field on its `/notes` +
  `/domains/{domain}/notes` responses → `contracts/titan.openapi.yaml` changes.
- **brain-mcp** consumes that new field.

Additive only — no consumer breaks. But the consumer (brain-mcp) cannot be verified until the
provider field exists in titan's **live** `/openapi.json`, so this lands **provider-first** and
is implemented in two stages.

## Affected repos & landing order
1. **Stage 1 — `repos/titan` (provider).** Add `content_hash` to the chunk payload at ingest +
   expose it on the notes responses. Update `contracts/titan.openapi.yaml` + `docs/ai/CONTRACTS.md`.
   Must land **and go green (with titan running)** before Stage 2.
2. **Stage 2 — `repos/brain-mcp` (consumer).** Mirror the field in its local schema, add the
   reconcile pass to `VaultWatcher`, add tests.

Each stage leaves `./workspace.sh check` green on its own.

## Decisions already made — do NOT re-decide

### The drift signal is a content hash, NOT mtime
- **`content_hash = sha256 of the note file's raw bytes on disk`**, hex digest.
- **Why hash, not mtime:** the vault lives on a 9p mount (`/mnt/f`). mtime is unreliable across
  the Windows↔WSL boundary and changes on `touch`/copy without a content change → false drift.
  A content hash is exact: identical content ⇒ identical hash; drift only on a real edit.
- **Hash the RAW file bytes** (`hashlib.sha256(file_path.read_bytes()).hexdigest()`), not the
  frontmatter-stripped body. This is the contract both sides must agree on: titan hashes the
  file it was handed; the watcher hashes the same file from disk — no need to replicate titan's
  frontmatter parsing or chunking to get a matching hash.

### titan side
- **Compute the hash once per ingest** in `ingest_file_endpoint` (routes.py), not per chunk.
  Pass it into `make_point`; store it under payload key `"content_hash"`.
- **`make_point` signature gains a required `content_hash: str` parameter.** Its only caller is
  `routes.py:291`; update that one call. The CLI/PDF path (`upsert_to_qdrant`) is **out of scope**
  — PDFs are not watcher-managed (the watcher only handles `.md` via `/ingest/file`), so their
  chunks simply carry no hash.
- **`NoteInfo` gains `content_hash: str | None = None`** (schemas.py:104). Optional + nullable so
  that chunks ingested *before* this change (no hash in payload) and PDF chunks return `null`.
- **Both** `GET /notes` (routes.py:434) **and** `GET /domains/{domain}/notes` (routes.py:476) add
  `"content_hash"` to their `with_payload` list and to the per-`source_path` aggregation (take the
  first chunk's value via `setdefault`). Keep them symmetric.
- **No `/notes` behaviour change otherwise** — same scroll loop, same 503 guard, same sort.

### brain-mcp side
- **Mirror the field**: add `content_hash: str | None = None` to brain-mcp's local `NoteInfo`
  (schemas.py:61). (Local copy is intentional decoupling — see the file's own docstring.)
- **Reconcile runs once, on the worker thread, before the debounce loop.** Add a `_reconcile()`
  method and call it at the very top of `_worker()` (watcher.py:195), wrapped in try/except so a
  reconcile failure can never kill the worker. Rationale: it runs *after* `start()` has already
  started the observer (so live events are captured concurrently and nothing is missed), it does
  not block `start()`/signal handling, and it serializes naturally with the worker's own ingests.
- **One attempt, best-effort.** If `_ensure_titan_available()` is False at reconcile time, log and
  return — do not loop. Reconcile is downtime catch-up, not critical path; the live watcher +
  cooldown handle ongoing edits. (Retry-when-titan-recovers is explicitly out of scope for v1.)
- **Delta rules** (compare on `str(path.resolve())`; titan stores absolute `source_path` and both
  `VAULT_ROOT`s resolve to `/mnt/f/vault`, so the strings match):
  - **On disk, not in index** → ingest (`self._ingest(path)`).
  - **In index, hash differs OR index hash is `null`** → ingest. (Null ⇒ legacy/PDF or
    pre-hash chunk; re-ingest is a safe idempotent upsert-before-delete and backfills the hash.
    Accept that the **first** reconcile after deploy re-ingests every not-yet-hashed note once.)
  - **Hash matches** → skip (the whole point — no needless re-embedding).
  - **In index, file gone** → delete (`self._handle_delete(path)`), **but only if** the
    `source_path` is under `vault_root` **and** ends in `.md`. This guard protects CLI-ingested
    PDFs and any out-of-vault entries from being wiped by the watcher.
- **Reuse existing internals** for the actions: `_ingest` (has its own titan guard +
  reschedule-on-error) and `_handle_delete` (queues if titan down). `_reconcile` only *computes*
  the delta and dispatches; it does not re-implement ingest/delete or HTTP handling.
- **Skip ignored paths** via the existing `_should_ignore(path, vault_root)` when walking the vault.

## Steps

### Stage 1 — titan (provider)

**`repos/titan/src/titan/service/schemas.py`**
1. Add `content_hash: str | None = None` to `NoteInfo` (after `chunk_count`, line ~107).

**`repos/titan/src/titan/ingest.py`**
2. Change `make_point(chunk, file_path, domain, run_id)` → add `content_hash: str` param
   (def at line 781). In the returned `PointStruct` payload (line ~818) add
   `"content_hash": content_hash,`.

**`repos/titan/src/titan/service/routes.py`**
3. Add `import hashlib` to the top-level imports (line ~20 block).
4. In `ingest_file_endpoint`, after the file-exists check and before/after `read_markdown`
   (around line 252), compute once:
   `content_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()`.
   (Only on the non-skip path — `indexed:false` deletes, it doesn't ingest, so no hash needed.)
5. Update the call at line 291: `make_point(c, file_path, domain, run_id, content_hash)`.
6. In `list_notes` (line 434): add `"content_hash"` to `with_payload=[...]` (line 453); add a
   `hashes: dict[str, str | None] = {}` map and `hashes.setdefault(source_path, payload.get("content_hash"))`
   inside the loop; build `NoteInfo(..., content_hash=hashes[sp])`.
7. Apply the **same** three edits to `list_domain_notes` (line 476): `with_payload` (line 499),
   the `hashes` map, and the `NoteInfo(...)` construction. Keep the two handlers symmetric.
8. Update the module docstring endpoint list only if wording needs it (no new endpoint, so likely
   no change).

**`repos/titan/tests/integration/test_service.py`** (all `@pytest.mark.integration`)
9. `test_notes_include_content_hash`: ingest one note via the existing `tmp_vault` +
   `patch("titan.service.routes.VAULT_ROOT", tmp_vault)` + `POST /ingest/file` pattern (mirror
   `test_ingest_new_note`, line 212). Then `GET /notes`; assert the note's `content_hash` is a
   64-char hex string and equals `hashlib.sha256(note.read_bytes()).hexdigest()`.
10. `test_content_hash_changes_on_edit`: ingest, read hash; rewrite the file with new content,
    re-ingest, `GET /notes`; assert the `content_hash` changed.

**workspace contract**
11. In `contracts/titan.openapi.yaml`, add `content_hash: { type: string, nullable: true }` to the
    note object under **both** `/notes` and `/domains/{domain}/notes` 200 response schemas
    (the `/notes` entry currently has only a one-line description — expand it to the explicit
    schema mirroring `/domains/{domain}/notes` while adding the field, so both list the field).
12. In `docs/ai/CONTRACTS.md`, update the titan "Surface" lines for `/notes` and
    `/domains/{domain}/notes` to mention `content_hash` (sha256 of the note's raw bytes; null for
    legacy/PDF chunks).

### Stage 2 — brain-mcp (consumer) — only after Stage 1 is live & green

**`repos/brain-mcp/src/brain_mcp/schemas.py`**
13. Add `content_hash: str | None = None` to `NoteInfo` (line 61).

**`repos/brain-mcp/src/brain_mcp/watcher.py`**
14. Add `import hashlib` (top of file).
15. Add a `_reconcile(self) -> None` method implementing the delta rules above:
    - `if not self._ensure_titan_available(): log.info(...); return`.
    - `indexed = {n.source_path: n for n in self.titan_client.list_notes().notes}`.
    - Walk `self.vault_root.rglob("*.md")`, skip `_should_ignore(p, self.vault_root)`; build
      `on_disk = {str(p.resolve()): p}` and `local_hash = hashlib.sha256(p.read_bytes()).hexdigest()`.
    - Ingest set: paths on disk where `key not in indexed` OR
      `indexed[key].content_hash != local_hash` (this covers the null-hash case).
    - Delete set: `key in indexed` and `key not in on_disk` and key endswith `.md` and
      `Path(key).is_relative_to(self.vault_root)`.
    - Dispatch: `self._ingest(p)` for ingests, `self._handle_delete(Path(key))` for deletes.
    - Log a one-line summary (`reconcile: N ingested, M deleted, K unchanged`).
16. Call `self._reconcile()` at the top of `_worker()` (line ~196), inside a `try/except Exception`
    that logs and continues into the `while` loop. Guard so it runs once.

**`repos/brain-mcp/tests/test_watcher.py`** (reuse the `mock_client` + `vault_root` fixtures)
17. `test_reconcile_ingests_missing_note`: write `a.md` in `vault_root`;
    `mock_client.list_notes.return_value = NotesResponse(notes=[], total=0)`;
    call `watcher._reconcile()`; assert `mock_client.ingest_file` called with `a.md`'s resolved path.
18. `test_reconcile_reingests_changed_note`: write `a.md`; stub `list_notes` to return a `NoteInfo`
    for `a.md` with a **wrong** `content_hash`; assert `ingest_file` called.
19. `test_reconcile_skips_unchanged_note`: stub `list_notes` with the **correct**
    `sha256(a.md.read_bytes())`; assert `ingest_file` NOT called.
20. `test_reconcile_deletes_orphan`: no file on disk; `list_notes` returns a `NoteInfo` for
    `<vault>/gone.md`; assert `delete_chunks` called for that path.
21. `test_reconcile_skips_when_titan_down`: `mock_client.health.side_effect = httpx.ConnectError`;
    assert `list_notes`/`ingest_file` NOT called.

## Tracking (multi-repo feature)
The implementer points workspace `docs/ai/CURRENT_TASK.md` at this plan, and each touched repo's
`docs/ai/CURRENT_TASK.md` (titan, then brain-mcp) back at it; writes `HANDOFF.md` if interrupted
between stages (workspace rule 2). The natural handoff point is **between Stage 1 and Stage 2**.

## Verification
- **Stage 1 static:** `cd repos/titan && make check` (ruff + mypy-strict + pytest, incl. the 2 new
  integration tests).
- **Stage 1 runtime (required — this is a contract change):** titan + Qdrant **up**. Ingest a note,
  `GET /notes` shows a real `content_hash`. Then from the workspace `./workspace.sh contracts` →
  titan **OK** (live `/openapi.json` now carries `content_hash`, matches the committed contract).
  Static green ≠ contract verified.
- **Stage 2 static:** `cd repos/brain-mcp && make check` (incl. the 5 new reconcile tests).
- **Stage 2 runtime (the real proof):** full stack up. With the watcher **stopped**, edit a note
  and delete another; start `brain-watcher`; confirm the edited note is re-ingested and the deleted
  note's chunks are removed (check logs + `GET /notes`), while unchanged notes are NOT re-embedded.
- `./workspace.sh check` green overall after each stage.

## Out of scope
- Hashing PDF/CLI ingests (`upsert_to_qdrant`) — PDFs aren't watcher-managed.
- A persisted/incremental baseline — reconcile reads each `.md` once at startup (fine for a
  personal vault of tens–hundreds of notes).
- Retrying reconcile later if titan is down at startup (v1 is one best-effort attempt).
- Any mtime-based optimization, `/notes` pagination, or a dashboard view of drift.

## Files to touch (checklist)
**Stage 1 — titan + contract**
- [ ] `repos/titan/src/titan/service/schemas.py` — `NoteInfo.content_hash`
- [ ] `repos/titan/src/titan/ingest.py` — `make_point` param + payload key
- [ ] `repos/titan/src/titan/service/routes.py` — hash compute + `make_point` call + both notes handlers
- [ ] `repos/titan/tests/integration/test_service.py` — 2 tests
- [ ] `contracts/titan.openapi.yaml` — `content_hash` on `/notes` + `/domains/{domain}/notes`
- [ ] `docs/ai/CONTRACTS.md` — titan surface lines
**Stage 2 — brain-mcp**
- [ ] `repos/brain-mcp/src/brain_mcp/schemas.py` — `NoteInfo.content_hash`
- [ ] `repos/brain-mcp/src/brain_mcp/watcher.py` — `_reconcile()` + call in `_worker()`
- [ ] `repos/brain-mcp/tests/test_watcher.py` — 5 tests
