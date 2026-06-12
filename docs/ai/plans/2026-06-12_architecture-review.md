# Architektur-Review & Entwicklungsplan — rag-system (2026-06-12)

Review-Umfang: titan, brain-mcp, brain-dashboard, obsidian-inbox-watcher, workspace-mcp.
Ziel: Produktionsreife, Skalierbarkeit, Robustheit. Erstellt aus vollständiger Lektüre der
Runtime-Pfade aller fünf Repos.

---

## 0. Gesamtbild

Das System ist für ein Ein-Personen-Projekt ungewöhnlich reif: Multi-Repo-Architektur mit
Contracts + System-Map + Dependency-Graph, strict mypy, ruff, pre-commit, CI und Tests in
jedem Repo (brain-mcp hat mehr Test- als Produktions-LOC), keine Secrets in git,
Path-Traversal-Schutz an jeder Eingangstür, Dead-Letter-Pattern, Retry mit
Transient-Klassifizierung, Reconcile-Loop, Upsert-before-Delete mit run_id.

Die Schwachstellen konzentrieren sich auf **einen** Service: titan ist als CLI-Skript
geboren und zum Service umgebaut worden — das sieht man an Modul-Level-Konfiguration,
untypisierten dict-Pipelines und sync-Code in async-Handlern. Die anderen vier Repos sind
strukturell sauber.

---

## 1. Kritische Befunde (P0 — vor allem anderen beheben)

### P0.1 — titan blockiert den Event-Loop (Produktionsrisiko)
`routes.py` deklariert alle Endpoints als `async def`, ruft aber synchron blockierenden
Code auf:
- `/search` → `titan.search.search()`: GPU-Encode, Ollama-`requests.post(timeout=30)`,
  synchroner Qdrant-gRPC-Client.
- `/ingest/file` → `late_chunk_and_embed()`: sekundenlange GPU-Arbeit.

In FastAPI blockiert ein `async def`-Handler mit Sync-Code den **gesamten** Event-Loop:
Während eines Ingests antwortet `/health` nicht → Dashboard meldet "down", brain-mcp-Tools
laufen in Timeouts. Mit `use_decompose=True` und totem Ollama hängt jeder `/search` bis zu
30 s den ganzen Service auf.

**Fix:** Handler zu `def` machen (FastAPI-Threadpool) oder `await asyncio.to_thread(...)`
— wie es brain-dashboard in `app.py` bereits korrekt vormacht. **Wichtig:** Dadurch wird
echte Parallelität möglich → gleichzeitig ein explizites Lock einführen (P0.2).

### P0.2 — Ingest hat keine Serialisierung (Race Condition nach P0.1-Fix)
`ingest_file_endpoint` macht read → embed → upsert → delete-old → counter-update ohne
Lock. Zwei parallele Ingests derselben Datei erzeugen zwei run_ids; der jeweils spätere
Delete löscht die Chunks des anderen teilweise. `state.domain_counts`-Updates sind nicht
atomar. Heute wird das vom Event-Loop-Blocking "versehentlich" serialisiert — nach dem
P0.1-Fix nicht mehr. **Fix:** ein globales `threading.Lock`/`asyncio.Lock` um den
Ingest-Pfad (GPU ist ohnehin seriell), mindestens aber ein Lock pro Datei.

### P0.3 — Zwei Payload-Schemata in einer Collection (Datenintegrität)
- CLI-Pfad `ingest.upsert_to_qdrant()`: Payload mit `source` (nur Dateiname!), ohne
  `source_path`, `run_id`, `content_hash`.
- Service-Pfad `ingest.make_point()`: Payload mit `source_path`, `run_id`, `content_hash`.

Folgen: PDF-Chunks sind in `/notes` unsichtbar (Filter auf `source_path`), per
`DELETE /chunks` nicht löschbar, und ein PDF-Re-Ingest mit weniger Chunks hinterlässt
Orphans (kein run_id-Delete; `stable_uuid` überschreibt nur gleiche chunk_ids).
**Fix:** `upsert_to_qdrant` auf `make_point` umstellen (ein Schema, ein Codepfad),
Alt-Bestand einmalig re-ingestieren.

### P0.4 — `as_completed(timeout=300)` bricht den ganzen Batch ab
`ingest.parse_pdfs_parallel()`: Der `timeout=300` auf `as_completed` wirft beim
**Iterieren** TimeoutError — der `except TimeoutError` im Loop fängt nur
`future.result(timeout=120)`. Läuft der Gesamtbatch länger als 300 s (12 Worker, große
PDFs ⇒ realistisch), bricht die Schleife ab und bereits fertige Ergebnisse gehen verloren.
Zudem: `future.cancel()` wirkt bei laufenden ProcessPool-Tasks nicht.
**Fix:** Gesamttimeout entfernen, nur Per-Future-Timeout behalten; Abbruch-Erwartungen an
`cancel()` streichen.

### P0.5 — Fehlende `domain` ⇒ HTTP 500 statt 422
`read_markdown()` wirft `ValueError`, `ingest_file_endpoint` fängt ihn nicht → 500.
Der Watcher loggt "HTTP 500" und verwirft das Event — die eigentliche Ursache (Frontmatter
unvollständig) ist im falschen Log. **Fix:** `ValueError` in routes fangen → 422 mit
Klartext; der Watcher behandelt 4xx als permanent (heute korrekt: kein Requeue).

---

## 2. Architektur, Struktur & Design Patterns (P1)

### Gut gelöst (beibehalten und als Vorlage nutzen)
- **Schichtung in titan/service**: app (Lifespan) / routes / schemas (Pydantic als
  API-Contract) / state / stats.
- **Facade**: `TitanClient` in brain-mcp — dünn, typisiert, mit tenacity-Retry nur auf
  Transport-Fehler.
- **Factory**: `select_observer()` im inbox-watcher (fstype-basiert) — lehrbuchhaft.
- **Circuit-Breaker light**: `_titan_dead_until`-Cool-down im VaultWatcher.
- **TTL-Cache + Double-Checked Locking**: connectors.py im Dashboard.
- **Atomic Writes**: mkstemp + os.replace in factory.py.
- **Dead Letter Queue**: `_dead_letter()` mit Error-Sidecar im inbox-watcher.

### Befund A — titan: Konfiguration ist 4-fach dupliziert und import-gebunden
`COLLECTION_NAME`/`QDRANT_*` werden in ingest.py, search.py, app.py **und** routes.py
jeweils per `os.getenv` auf Modulebene gelesen; `load_dotenv()` läuft beim Import.
Konsequenzen: Tests müssen monkeypatchen statt injizieren; Drift-Gefahr zwischen den vier
Stellen; brain-mcp/brain-dashboard machen es mit pydantic-settings bereits richtig.
**Maßnahme:** `titan/config.py` mit `BaseSettings` (env_prefix `TITAN_`), Import-Zeit-Reads
entfernen, Settings explizit durchreichen.

### Befund B — titan: `dict[str, Any]` als Domänenmodell
Chunks laufen als untypisierte Dicts durch die gesamte Pipeline (`chunk["dense"] = ...`).
mypy strict ist aktiv, prüft hier aber faktisch nichts (alles `Any`).
**Maßnahme:** `@dataclass Chunk` (text, header, section_id, …, optional dense/sparse/
colbert) — macht strict mode wirksam und Refactorings sicher.

### Befund C — titan: fehlendes Repository für Qdrant
routes.py spricht Qdrant direkt an: 6× lazy `from qdrant_client.models import
FieldCondition, Filter, MatchValue`, copy-paste Scroll-Aggregation (`list_notes` und
`list_domain_notes` sind ~90 % identisch), Delete-Filter-Konstruktion wiederholt sich.
Außerdem existieren `load_bge_m3_model()` und `build_qdrant_client()` je **dreimal**
(ingest.py, search.py, app.py).
**Maßnahme:** `titan/infra/qdrant_repo.py` (upsert_note, delete_note, count_chunks,
iter_notes(domain=None), invalidate_cache) + `titan/infra/embedder.py` (eine
Modell-Factory). Routes werden zu dünnen Adaptern → Hexagonal/Ports-&-Adapters light.

### Befund D — titan: CLI-/Service-Doppelpfad in `search()`
`_own_lock/_own_model/_own_client`-Flags mischen zwei Lebenszyklen in einer Funktion.
**Maßnahme:** Kern `_search_with(model, client, …)` + zwei schmale Einstiege
(`search_cli()` mit Lock/Loading, Service ruft Kern direkt). Gleiches Muster für ingest.

### Befund E — brain-mcp: 6× identischer Error-Boilerplate
Jedes MCP-Tool wiederholt denselben `except httpx.ConnectError / HTTPStatusError`-Block.
**Maßnahme:** Decorator `@_titan_errors` (oder Wrapper-Funktion) — ein Ort für die
Fehlertexte. Nebenbei: `ingest_note(force=...)` ist dokumentiert wirkungslos → entfernen
oder implementieren (API-Hygiene).

### Befund F — obsidian-inbox-watcher: 700-Zeilen-Monolith
`main.py` enthält Config-Loading, FS-Heuristik, vier Extraktoren, Prompt, LLM-Call,
Note-Rendering, Archivierung, Watchdog-Handler und Main-Loop. `process_file()` allein hat
~200 Zeilen.
**Maßnahme:** Aufteilen in `extractors.py` (Registry `dict[ext, Callable]` —
Strategy-Pattern; neue Formate = ein Eintrag), `note_builder.py`, `pipeline.py`,
`watcher.py`. Die Registry ersetzt die if/elif-Kette in `_extract_text`.

### Befund G — inbox-watcher: Frontmatter per f-String (YAML-Injection)
Ein Gemini-Titel/Source mit `"` oder `:` kann das YAML brechen → Titan wirft dann
"domain fehlt"-Fehler für eine eigentlich valide Note.
**Maßnahme:** Frontmatter mit `yaml.safe_dump`/python-frontmatter erzeugen, nicht per
String-Interpolation. (Gemini-Output zudem mit einem Pydantic-Modell validieren statt
`result.get(...)`-Kaskade.)

---

## 3. Robustheit, Datenintegrität & Fehlertoleranz

Über die P0-Punkte hinaus:

- **Watcher-Eventverlust bei 5xx:** `_ingest()` requeued nur bei `ConnectError`; ein
  transienter 503/429 von titan verwirft das Event (bis zum nächsten Reconcile beim
  Neustart). → 5xx/429 wie ConnectError behandeln (requeue mit Zähler, nach N Versuchen
  dead-letter-Log).
- **Semantic Cache wächst unbegrenzt:** TTL wird nur beim Lookup gefiltert;
  `cache_cleanup` existiert nur als manueller CLI-Befehl. → periodischer Cleanup-Task im
  Service-Lifespan (asyncio-Task, 1×/Tag reicht).
- **`sanitize()` ist Symbolschutz:** Ersetzen von `"=== "`/`"---"` stoppt keine ernsthafte
  Prompt-Injection. Entweder als Best-Effort dokumentieren (ehrlich) oder beim
  LLM-Aufruf strukturell trennen (Kontext in XML-Tags, Anweisung im System-Prompt).
- **`domain_counts`-Drift:** CLI-Ingest am Service vorbei macht den in-memory Counter
  falsch bis zum Neustart. Mit dem Repository (Befund C) kann `/domains` alternativ ein
  Qdrant-Facet-Count nutzen — dann gibt es nur noch eine Wahrheit.
- **Dashboard ohne Auth auf 0.0.0.0:9200:** Das Dashboard kann systemd-Units steuern,
  Windows-Prozesse starten (`factory/start`) und killen (`taskkill /F /T`). In WSL
  mirrored mode ist der Port im LAN erreichbar. → Bind auf die Tailscale-IP, oder ein
  statisches Bearer-Token (Middleware, 10 Zeilen), oder Windows-Firewall-Regel.
- **`.url`-Fetch = kleine SSRF-Fläche:** Der inbox-watcher folgt beliebigen URLs aus
  Dateien (auch via Telegram-Capture angeliefert). Für ein Einzelplatzsystem akzeptabel —
  bewusst entscheiden und ggf. private IP-Ranges blocken.
- **Logging/Observability:** Konsistentes stdlib-Logging + journald ist für diesen Betrieb
  angemessen; `/stats` mit p50/p95 ist ein gutes Muster. Nächste Stufe erst bei Bedarf:
  ein Request-ID-Middleware in titan, damit sich ein MCP-Call durch brain-mcp → titan im
  Journal korrelieren lässt.
- **Implizite Dependency:** `ingest.late_chunk_embed` importiert `packaging` — fehlt in
  `pyproject.toml` (kommt heute transitiv). Explizit deklarieren.

---

## 4. Performance, Ressourcen & Skalierung (P2)

- **Quick Win — Sub-Queries batchen:** `search()` ruft `embed_query()` pro Sub-Query
  einzeln (GPU, batch_size=1). Alle 3–4 Sub-Queries in **einem** `model.encode()`-Call
  → spart 2–3 GPU-Roundtrips pro Suche.
- **`section_full_text` ist toter Ballast:** wird in jedes Chunk-Dict gelegt
  (bei Sub-Chunks: der komplette Abschnittstext **pro** Sub-Chunk → O(n·m) RAM), aber nie
  in den Payload geschrieben. Entfernen.
- **ColBERT `tolist()`:** (seq_len × 128)-Matrizen als Python-Listen sind RAM-teuer;
  qdrant-client akzeptiert numpy-Arrays direkt.
- **`/notes`-Vollscan:** O(N) Python-Aggregation pro Aufruf. Bei 10× Datenmenge:
  Qdrant-Facet-API für Counts nutzen oder eine kleine Notes-Registry (SQLite) als
  Sekundärindex pflegen — Letzteres löst auch `/domains`-Drift.
- **Skalierungsbild gesamt:** Bei 10× Daten hält Qdrant problemlos mit; die Engpässe sind
  (a) der eine GPU-Slot (BGE-M3 seriell — bewusste Architekturentscheidung, gut
  dokumentiert) und (b) synchroner Ingest im Request. Wenn PDFs je in den Service-Pfad
  kommen: Ingest als Job-Queue (asyncio.Queue + Worker-Task reicht; kein Celery nötig)
  mit `202 Accepted` + Status-Endpoint.
- **workspace-mcp `list_repos`:** N+1-Subprozess-Aufrufe von manifest.py (einer pro
  Repo-Feld). Ein `manifest dump --json`-Subcommand macht es zu einem Call. Unkritisch,
  aber leicht.

---

## 5. Testbarkeit & Wartbarkeit

Stark: brain-mcp (1 245 Test-LOC / 1 034 Src-LOC), Dashboard und Watcher mit injizierbaren
Parametern (`debounce_seconds`, `skip_reconcile`) — sichtbar für Tests designt.

Lücke: titan-Kern. 855 Test-LOC auf 4 734 Src-LOC, und die testen v. a. Service/Utils —
die eigentliche Pipeline (chunk_markdown, _group_into_windows, _split_text, rrf_fusion,
decompose_query-Parsing, cache_lookup-Filterlogik) ist **pure-function-testbar ohne GPU**
und ungetestet. Genau dort sitzen die subtilen Bugs (Offsets, Overlaps, Fenstergrenzen).

Maßnahmen:
1. Golden-Tests für `chunk_markdown` (Header-Kombinationen, Riesen-Abschnitte, kein
   Header, leere Abschnitte) und `rrf_fusion`.
2. `_group_into_windows` mit Fake-Tokenizer (Längenfunktion) testen.
3. `decompose_query`: Ollama-Antwortvarianten (Array, Dict, Müll) als Parametrize-Tests —
   der Parser hat viele Zweige.
4. Nach Befund A/C: Settings + Repository injizieren statt monkeypatchen; Protocol-Klassen
   für Embedder/Repo erlauben handgeschriebene Fakes statt Mock-Orgien.
5. Property-based Testing (hypothesis) für `_split_text`: Invariante "Konkatenation der
   Sub-Chunks ohne Overlap == Originaltext" und "kein Sub-Chunk > MAX_CHARS".

---

## 6. Priorisierter Maßnahmenplan

| Prio | Maßnahme | Repo | Aufwand |
|------|----------|------|---------|
| P0.1 | ✅ 2026-06-12 — Event-Loop-Blocking: alle Handler → sync `def` (Threadpool) | titan | S |
| P0.2 | ✅ 2026-06-12 — `state.work_lock` um Search/Ingest/Delete-Mutationen | titan | S |
| P0.3 | ✅ 2026-06-12 — `upsert_files_to_qdrant()` nutzt make_point; Legacy-Cleanup beim nächsten PDF-Re-Ingest | titan | M |
| P0.4 | ✅ 2026-06-12 — `as_completed`-Gesamttimeout entfernt | titan | S |
| P0.5 | ✅ 2026-06-12 — ValueError/YAMLError → 422 (+ Integrationstest) | titan | S |

P0 komplett umgesetzt: mypy strict grün, 17 Unit- + 24 Integrationstests grün
(echtes Qdrant + GPU), Service neu gestartet und live verifiziert (/health ok,
/search 95 ms). Nebenbei: implizite `packaging`-Dependency deklariert,
`types-pyyaml` als dev-Dependency ergänzt. Änderungen sind noch nicht committet.
| P1.1 | ✅ 2026-06-12 — titan.config (pydantic-settings) + titan.infra (Factory-Dedup); Test-Fixture patcht jetzt alle Alias-Stellen (schloss latente Lücke: Suche lief je nach Importreihenfolge gegen die echte Collection) | titan | M |
| P1.2 | QdrantRepository + Chunk-Dataclass (Factory-Dedup bereits in P1.1 erledigt) | titan | L |
| P1.3 | ✅ 2026-06-12 — @_titan_errors-Decorator; `force` hat jetzt echte Bedeutung (Content-Hash-Skip in titan, IDEAS-Eintrag 2026-06-06 umgesetzt). Bonus-Fix: tenacity-Retry hatte keinen retry=-Filter und hat auch 4xx retried | brain-mcp | S |
| P1.4 | inbox-watcher modularisieren, Extractor-Registry | inbox-watcher | M |
| P1.5 | ✅ 2026-06-12 — Frontmatter via yaml.safe_dump, Gemini-Antwort als Pydantic-Modell (GeminiNote), Test mit feindseligem Titel | inbox-watcher | S |
| P1.6 | ✅ 2026-06-12 — optionales BRAIN_DASH_AUTH_TOKEN (ASGI-Middleware, Cookie-Login via /?token=…, Bearer für API; leer = No-op). Aktivierung: Token in .env setzen + Restart | brain-dashboard | S |
| P1.7 | ✅ 2026-06-12 — Watcher requeued Timeout/5xx/429 (max. 5 Versuche/Pfad, Reset bei Erfolg); 4xx bleibt permanent | brain-mcp | S |
| P2.1 | ✅ 2026-06-12 — embed_queries(): ein encode()-Batch für alle Sub-Queries; CLI-main() dedupliziert (delegiert an search()) | titan | S |
| P2.2 | ✅ 2026-06-12 — section_full_text + tote _compute_section_hash entfernt. (colbert→numpy verworfen: PointStruct ist Pydantic, akzeptiert kein ndarray) | titan | S |
| P2.3 | ✅ 2026-06-12 — täglicher cache_cleanup-Task im Lifespan (läuft auch einmal beim Start) | titan | S |
| P2.4 | /notes via Facet oder Registry (erst bei Wachstum) | titan | M |
| P3.1 | Pure-Function-Tests Pipeline-Kern | titan | M |
| P3.2 | hypothesis für _split_text | titan | S |
| P3.3 | Request-ID-Korrelation (bei Bedarf) | titan/brain-mcp | M |

**Offen sind damit nur noch die zwei großen Struktur-Refactorings (P1.2, P1.4)
und die P3-Testtiefe** — alle als eigene fokussierte Session empfohlen.
Zusätzlich umgesetzt (nicht im Original-Plan): Content-Hash-Skip in titan
(`skipped_reason: "unchanged"`, `force=true` umgeht ihn).

Empfohlene Reihenfolge: P0 als ein fokussierter Sprint (alles titan, zusammen testbar),
dann P1.1+P1.2 als ein Refactoring (Settings und Repository bedingen sich), Rest nach
Gelegenheit.

---

## 7. Persönlicher Lern-Fahrplan

Stilbild aus dem Code: stark in defensiver Programmierung, Fehlerpfaden,
Begründungs-Kommentaren ("warum", nicht "was" — selten auf diesem Niveau), Security-
Bewusstsein und Test-Disziplin in den neueren Repos. Das Muster, das dich vom nächsten
Level trennt: **Skript-DNA im Servicekern** — Modul-Level-Konfiguration, dict-Pipelines,
Funktionen, die zwei Lebenszyklen (CLI + Service) gleichzeitig bedienen, Sync-Code in
async-Kontexten. Die neueren Repos (brain-mcp, dashboard) zeigen, dass du die besseren
Muster schon kennst — sie fehlen nur im ältesten/größten Modul.

Priorisierte Lernliste (jeweils mit direktem Anwendungsfall im eigenen Code):

1. **FastAPI/asyncio-Ausführungsmodell** — wann blockiert ein `async def`, Threadpool vs.
   Event-Loop, `asyncio.to_thread`, Locks, Backpressure. Anwenden: P0.1/P0.2.
   (FastAPI-Doku "Concurrency and async/await"; danach: warum brain-dashboard's
   `asyncio.gather(to_thread(...))` korrekt ist.)
2. **Dependency Injection & Composition Root** — Konfiguration und Ressourcen werden am
   Programmstart gebaut und explizit durchgereicht; keine Import-Zeit-Seiteneffekte.
   Anwenden: P1.1. (Buch: "Architecture Patterns with Python" / cosmicpython.com,
   Kapitel Bootstrap/DI — kostenlos online.)
3. **Repository-Pattern & Ports/Adapters** — Persistenz hinter einer Schnittstelle,
   Domänenkern ohne Framework-Importe. Anwenden: P1.2. (cosmicpython Kap. 2;
   dein eigener `TitanClient` ist bereits ein Adapter — gleiche Idee für Qdrant.)
4. **Typisierte Domänenmodelle statt dict[str, Any]** — dataclasses/Pydantic im Kern,
   `Any` als Code-Smell unter mypy strict. Anwenden: Chunk-Dataclass.
5. **Strategy/Registry & Plugin-Architektur** — Verhalten als Daten (dict ext→Extractor).
   Anwenden: P1.4. Du hast das Muster in `select_observer()` schon gebaut — jetzt bewusst
   benennen und wiederverwenden.
6. **Property-based Testing (hypothesis)** — Invarianten statt Beispiele, ideal für
   Chunking/Parsing. Anwenden: P3.2.
7. **Später, bei echtem Bedarf:** Job-Queues (arq/asyncio-Worker), strukturiertes Logging
   (structlog) + Metriken (Prometheus), OpenTelemetry-Grundlagen. Erst wenn das System
   Mehrbenutzer- oder Mehr-Maschinen-Betrieb bekommt — vorher ist es Overhead.

Bewusst **nicht** auf der Liste: Microservice-Frameworks, Kubernetes, Event-Sourcing,
CQRS — die Repo-Granularität und die HTTP/MCP-Grenzen dieses Systems sind für den
Einsatzzweck bereits richtig dimensioniert.
