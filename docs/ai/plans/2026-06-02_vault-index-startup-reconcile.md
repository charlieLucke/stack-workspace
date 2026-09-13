# Plan: Startup-Reconcile für den Vault-Index (titan Note-Hash → brain-watcher-Reconcile)

- **Datum:** 2026-06-02
- **Autor:** Opus (Planung)
- **Implementierer-Ziel:** Sonnet
- **Status:** ready
- **Verfolgt IDEAS.md:** „Startup reconcile for the vault index" (2026-06-02)

## Ziel
Nach einem Kaltstart werden Notizen, die **editiert, erstellt oder gelöscht wurden, während brain-watcher
unten war**, nie reconciled — `PollingObserver` snapshottet den Baum bei `start()` und emittiert nur
*nachfolgende* Events (`watcher.py:142` macht keinen Baseline-Scan). Edits, die gemacht wurden, während der Stack
aus war, bleiben also in titans Index veraltet, bis ein manuelles `touch`/`ingest_note` erfolgt. Dieses Feature ergänzt einen
**einmaligen Reconcile-Pass beim Watcher-Start**, der den Vault gegen titans Index diffed und
**nur das Delta** neu-ingestet/löscht.

Das günstige, exakte Drift-Signal ist ein **Per-Notiz-Content-Hash**, den titan in `GET /notes` bereitstellt.
Der Watcher berechnet denselben Hash lokal und vergleicht.

## Warum das ein Plan auf Workspace-Ebene ist
Es kreuzt eine Repo-Grenze **und** ändert einen veröffentlichten Contract:
- **titan** erhält ein neues Payload-Feld und ein neues **additives** Feld auf seinen `/notes`- +
  `/domains/{domain}/notes`-Responses → `contracts/titan.openapi.yaml` ändert sich.
- **brain-mcp** konsumiert dieses neue Feld.

Nur additiv — kein Konsument bricht. Aber der Konsument (brain-mcp) kann nicht verifiziert werden, bis das
Provider-Feld in titans **Live**-`/openapi.json` existiert, daher landet das **Provider-first** und
wird in zwei Stages implementiert.

## Betroffene Repos & Landing-Reihenfolge
1. **Stage 1 — `repos/titan` (Provider).** `content_hash` beim Ingest zum Chunk-Payload hinzufügen +
   auf den Notes-Responses bereitstellen. `contracts/titan.openapi.yaml` + `docs/ai/CONTRACTS.md` aktualisieren.
   Muss **landen und grün werden (mit laufendem titan)**, bevor Stage 2.
2. **Stage 2 — `repos/brain-mcp` (Konsument).** Das Feld im lokalen Schema spiegeln, den
   Reconcile-Pass zu `VaultWatcher` hinzufügen, Tests ergänzen.

Jede Stage lässt `./workspace.sh check` für sich grün.

## Bereits getroffene Entscheidungen — NICHT neu entscheiden

### Das Drift-Signal ist ein Content-Hash, NICHT mtime
- **`content_hash = sha256 der rohen Bytes der Notiz-Datei auf der Platte`**, Hex-Digest.
- **Warum Hash, nicht mtime:** der Vault liegt auf einem 9p-Mount (`/mnt/f`). mtime ist über
  die Windows↔WSL-Grenze unzuverlässig und ändert sich bei `touch`/Kopie ohne Inhaltsänderung → falsches Drift.
  Ein Content-Hash ist exakt: identischer Inhalt ⇒ identischer Hash; Drift nur bei einem echten Edit.
- **Die ROHEN Datei-Bytes hashen** (`hashlib.sha256(file_path.read_bytes()).hexdigest()`), nicht den
  frontmatter-bereinigten Body. Das ist der Contract, dem beide Seiten zustimmen müssen: titan hasht die
  Datei, die ihm übergeben wurde; der Watcher hasht dieselbe Datei von der Platte — keine Notwendigkeit, titans
  Frontmatter-Parsing oder Chunking zu replizieren, um einen passenden Hash zu bekommen.

### titan-Seite
- **Den Hash einmal pro Ingest berechnen** in `ingest_file_endpoint` (routes.py), nicht pro Chunk.
  Ihn an `make_point` übergeben; unter dem Payload-Key `"content_hash"` speichern.
- **Die `make_point`-Signatur erhält einen erforderlichen `content_hash: str`-Parameter.** Ihr einziger Aufrufer ist
  `routes.py:291`; diesen einen Call aktualisieren. Der CLI/PDF-Pfad (`upsert_to_qdrant`) ist **out of scope**
  — PDFs sind nicht watcher-verwaltet (der Watcher behandelt nur `.md` via `/ingest/file`), ihre
  Chunks tragen also einfach keinen Hash.
- **`NoteInfo` erhält `content_hash: str | None = None`** (schemas.py:104). Optional + nullable, sodass
  Chunks, die *vor* dieser Änderung ingestet wurden (kein Hash im Payload), und PDF-Chunks `null` zurückgeben.
- **Sowohl** `GET /notes` (routes.py:434) **als auch** `GET /domains/{domain}/notes` (routes.py:476) fügen
  `"content_hash"` zu ihrer `with_payload`-Liste und zur Per-`source_path`-Aggregation hinzu (den
  Wert des ersten Chunks via `setdefault` nehmen). Symmetrisch halten.
- **Sonst keine `/notes`-Verhaltensänderung** — gleiche Scroll-Schleife, gleicher 503-Guard, gleiche Sortierung.

### brain-mcp-Seite
- **Das Feld spiegeln**: `content_hash: str | None = None` zu brain-mcps lokalem `NoteInfo`
  (schemas.py:61) hinzufügen. (Die lokale Kopie ist bewusste Entkopplung — siehe den eigenen Docstring der Datei.)
- **Reconcile läuft einmal, auf dem Worker-Thread, vor der Debounce-Schleife.** Eine `_reconcile()`-
  Methode hinzufügen und sie ganz oben in `_worker()` aufrufen (watcher.py:195), in try/except gewickelt, sodass ein
  Reconcile-Fehler den Worker nie killen kann. Begründung: es läuft *nachdem* `start()` den Observer bereits
  gestartet hat (sodass Live-Events nebenläufig erfasst werden und nichts verpasst wird), es
  blockiert nicht `start()`/Signal-Handling, und es serialisiert natürlich mit den eigenen Ingests des Workers.
- **Ein Versuch, Best-Effort.** Ist `_ensure_titan_available()` zur Reconcile-Zeit False, loggen und
  zurückkehren — nicht loopen. Reconcile ist Downtime-Catch-up, kein Critical Path; der Live-Watcher +
  Cooldown handhaben laufende Edits. (Retry-wenn-titan-sich-erholt ist explizit out of scope für v1.)
- **Delta-Regeln** (vergleichen auf `str(path.resolve())`; titan speichert absolutes `source_path` und beide
  `VAULT_ROOT`s lösen zu `/mnt/f/vault` auf, die Strings passen also):
  - **Auf der Platte, nicht im Index** → ingesten (`self._ingest(path)`).
  - **Im Index, Hash weicht ab ODER Index-Hash ist `null`** → ingesten. (Null ⇒ Legacy/PDF oder
    Pre-Hash-Chunk; Re-Ingest ist ein sicheres idempotentes upsert-before-delete und füllt den Hash nach.
    Akzeptieren, dass der **erste** Reconcile nach dem Deploy jede noch-nicht-gehashte Notiz einmal neu-ingestet.)
  - **Hash passt** → überspringen (genau der Sinn — kein unnötiges Re-Embedding).
  - **Im Index, Datei weg** → löschen (`self._handle_delete(path)`), **aber nur wenn** der
    `source_path` unter `vault_root` liegt **und** auf `.md` endet. Dieser Guard schützt CLI-ingestete
    PDFs und etwaige Out-of-Vault-Einträge davor, vom Watcher gelöscht zu werden.
- **Bestehende Interna für die Aktionen wiederverwenden**: `_ingest` (hat seinen eigenen titan-Guard +
  Reschedule-on-Error) und `_handle_delete` (queued, wenn titan unten). `_reconcile` *berechnet* nur
  das Delta und dispatcht; es reimplementiert nicht Ingest/Delete oder HTTP-Handling.
- **Ignorierte Pfade überspringen** via das bestehende `_should_ignore(path, vault_root)` beim Durchlaufen des Vaults.

## Schritte

### Stage 1 — titan (Provider)

**`repos/titan/src/titan/service/schemas.py`**
1. `content_hash: str | None = None` zu `NoteInfo` hinzufügen (nach `chunk_count`, Zeile ~107).

**`repos/titan/src/titan/ingest.py`**
2. `make_point(chunk, file_path, domain, run_id)` ändern → `content_hash: str`-Param hinzufügen
   (def in Zeile 781). Im zurückgegebenen `PointStruct`-Payload (Zeile ~818)
   `"content_hash": content_hash,` ergänzen.

**`repos/titan/src/titan/service/routes.py`**
3. `import hashlib` zu den Top-Level-Importen hinzufügen (Zeile ~20-Block).
4. In `ingest_file_endpoint`, nach dem File-Exists-Check und vor/nach `read_markdown`
   (um Zeile 252), einmal berechnen:
   `content_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()`.
   (Nur auf dem Nicht-Skip-Pfad — `indexed:false` löscht, es ingestet nicht, also kein Hash nötig.)
5. Den Call in Zeile 291 aktualisieren: `make_point(c, file_path, domain, run_id, content_hash)`.
6. In `list_notes` (Zeile 434): `"content_hash"` zu `with_payload=[...]` (Zeile 453) hinzufügen; eine
   `hashes: dict[str, str | None] = {}`-Map und `hashes.setdefault(source_path, payload.get("content_hash"))`
   innerhalb der Schleife; `NoteInfo(..., content_hash=hashes[sp])` bauen.
7. Die **gleichen** drei Edits auf `list_domain_notes` (Zeile 476) anwenden: `with_payload` (Zeile 499),
   die `hashes`-Map und die `NoteInfo(...)`-Konstruktion. Die zwei Handler symmetrisch halten.
8. Die Modul-Docstring-Endpunkt-Liste nur aktualisieren, wenn die Formulierung es braucht (kein neuer Endpunkt, also wahrscheinlich
   keine Änderung).

**`repos/titan/tests/integration/test_service.py`** (alle `@pytest.mark.integration`)
9. `test_notes_include_content_hash`: eine Notiz via das bestehende `tmp_vault` +
   `patch("titan.service.routes.VAULT_ROOT", tmp_vault)` + `POST /ingest/file`-Pattern ingesten (spiegelt
   `test_ingest_new_note`, Zeile 212). Dann `GET /notes`; prüfen, dass der `content_hash` der Notiz ein
   64-Zeichen-Hex-String ist und `hashlib.sha256(note.read_bytes()).hexdigest()` entspricht.
10. `test_content_hash_changes_on_edit`: ingesten, Hash lesen; die Datei mit neuem Inhalt überschreiben,
    neu-ingesten, `GET /notes`; prüfen, dass sich der `content_hash` geändert hat.

**Workspace-Contract**
11. In `contracts/titan.openapi.yaml` `content_hash: { type: string, nullable: true }` zum
    Note-Objekt unter **beiden** `/notes`- und `/domains/{domain}/notes`-200-Response-Schemas hinzufügen
    (der `/notes`-Eintrag hat aktuell nur eine Einzeiler-Beschreibung — ihn auf das explizite
    Schema erweitern, das `/domains/{domain}/notes` spiegelt, während das Feld hinzugefügt wird, sodass beide das Feld listen).
12. In `docs/ai/CONTRACTS.md` die titan-„Oberfläche"-Zeilen für `/notes` und
    `/domains/{domain}/notes` aktualisieren, sodass sie `content_hash` erwähnen (sha256 der rohen Bytes der Notiz; null für
    Legacy-/PDF-Chunks).

### Stage 2 — brain-mcp (Konsument) — erst nachdem Stage 1 live & grün ist

**`repos/brain-mcp/src/brain_mcp/schemas.py`**
13. `content_hash: str | None = None` zu `NoteInfo` hinzufügen (Zeile 61).

**`repos/brain-mcp/src/brain_mcp/watcher.py`**
14. `import hashlib` hinzufügen (Dateianfang).
15. Eine `_reconcile(self) -> None`-Methode hinzufügen, die die obigen Delta-Regeln implementiert:
    - `if not self._ensure_titan_available(): log.info(...); return`.
    - `indexed = {n.source_path: n for n in self.titan_client.list_notes().notes}`.
    - `self.vault_root.rglob("*.md")` durchlaufen, `_should_ignore(p, self.vault_root)` überspringen;
      `on_disk = {str(p.resolve()): p}` und `local_hash = hashlib.sha256(p.read_bytes()).hexdigest()` bauen.
    - Ingest-Set: Pfade auf der Platte, wo `key not in indexed` ODER
      `indexed[key].content_hash != local_hash` (das deckt den Null-Hash-Fall ab).
    - Delete-Set: `key in indexed` und `key not in on_disk` und key endet mit `.md` und
      `Path(key).is_relative_to(self.vault_root)`.
    - Dispatch: `self._ingest(p)` für Ingests, `self._handle_delete(Path(key))` für Deletes.
    - Eine Einzeiler-Zusammenfassung loggen (`reconcile: N ingested, M deleted, K unchanged`).
16. `self._reconcile()` ganz oben in `_worker()` (Zeile ~196) aufrufen, innerhalb eines `try/except Exception`,
    das loggt und in die `while`-Schleife fortfährt. Absichern, sodass es einmal läuft.

**`repos/brain-mcp/tests/test_watcher.py`** (die `mock_client` + `vault_root`-Fixtures wiederverwenden)
17. `test_reconcile_ingests_missing_note`: `a.md` in `vault_root` schreiben;
    `mock_client.list_notes.return_value = NotesResponse(notes=[], total=0)`;
    `watcher._reconcile()` aufrufen; prüfen, dass `mock_client.ingest_file` mit `a.md`s aufgelöstem Pfad aufgerufen wird.
18. `test_reconcile_reingests_changed_note`: `a.md` schreiben; `list_notes` stubben, sodass es ein `NoteInfo`
    für `a.md` mit einem **falschen** `content_hash` zurückgibt; prüfen, dass `ingest_file` aufgerufen wird.
19. `test_reconcile_skips_unchanged_note`: `list_notes` mit dem **korrekten**
    `sha256(a.md.read_bytes())` stubben; prüfen, dass `ingest_file` NICHT aufgerufen wird.
20. `test_reconcile_deletes_orphan`: keine Datei auf der Platte; `list_notes` gibt ein `NoteInfo` für
    `<vault>/gone.md` zurück; prüfen, dass `delete_chunks` für diesen Pfad aufgerufen wird.
21. `test_reconcile_skips_when_titan_down`: `mock_client.health.side_effect = httpx.ConnectError`;
    prüfen, dass `list_notes`/`ingest_file` NICHT aufgerufen werden.

## Tracking (Multi-Repo-Feature)
Der Implementierer zeigt die Workspace-`docs/ai/CURRENT_TASK.md` auf diesen Plan und die
`docs/ai/CURRENT_TASK.md` jedes berührten Repos (titan, dann brain-mcp) zurück darauf; schreibt `HANDOFF.md`, falls unterbrochen
zwischen den Stages (Workspace-Regel 2). Der natürliche Handoff-Punkt ist **zwischen Stage 1 und Stage 2**.

## Verifikation
- **Stage 1 statisch:** `cd repos/titan && make check` (ruff + mypy-strict + pytest, inkl. der 2 neuen
  Integrationstests).
- **Stage 1 Runtime (erforderlich — das ist eine Contract-Änderung):** titan + Qdrant **oben**. Eine Notiz ingesten,
  `GET /notes` zeigt einen echten `content_hash`. Dann aus dem Workspace `./workspace.sh contracts` →
  titan **OK** (Live-`/openapi.json` trägt jetzt `content_hash`, passt zum committeten Contract).
  Statisch grün ≠ Contract-verifiziert.
- **Stage 2 statisch:** `cd repos/brain-mcp && make check` (inkl. der 5 neuen Reconcile-Tests).
- **Stage 2 Runtime (der echte Beweis):** voller Stack oben. Mit dem Watcher **gestoppt**, eine Notiz editieren
  und eine andere löschen; `brain-watcher` starten; bestätigen, dass die editierte Notiz neu-ingestet und die gelöschte
  Notiz-Chunks entfernt werden (Logs + `GET /notes` prüfen), während unveränderte Notizen NICHT neu-eingebettet werden.
- `./workspace.sh check` insgesamt grün nach jeder Stage.

## Out of Scope
- PDF-/CLI-Ingests hashen (`upsert_to_qdrant`) — PDFs sind nicht watcher-verwaltet.
- Eine persistierte/inkrementelle Baseline — Reconcile liest jede `.md` einmal beim Start (in Ordnung für einen
  persönlichen Vault von zehn–hundert Notizen).
- Reconcile später erneut versuchen, wenn titan beim Start unten ist (v1 ist ein Best-Effort-Versuch).
- Jede mtime-basierte Optimierung, `/notes`-Pagination oder eine Dashboard-Ansicht von Drift.

## Zu berührende Dateien (Checkliste)
**Stage 1 — titan + Contract**
- [ ] `repos/titan/src/titan/service/schemas.py` — `NoteInfo.content_hash`
- [ ] `repos/titan/src/titan/ingest.py` — `make_point`-Param + Payload-Key
- [ ] `repos/titan/src/titan/service/routes.py` — Hash-Berechnung + `make_point`-Call + beide Notes-Handler
- [ ] `repos/titan/tests/integration/test_service.py` — 2 Tests
- [ ] `contracts/titan.openapi.yaml` — `content_hash` auf `/notes` + `/domains/{domain}/notes`
- [ ] `docs/ai/CONTRACTS.md` — titan-Oberflächen-Zeilen
**Stage 2 — brain-mcp**
- [ ] `repos/brain-mcp/src/brain_mcp/schemas.py` — `NoteInfo.content_hash`
- [ ] `repos/brain-mcp/src/brain_mcp/watcher.py` — `_reconcile()` + Call in `_worker()`
- [ ] `repos/brain-mcp/tests/test_watcher.py` — 5 Tests
