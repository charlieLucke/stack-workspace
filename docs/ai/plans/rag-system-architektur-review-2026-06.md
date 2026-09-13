---
domain: system
created: 2026-06-12
tags: [architektur, review, refactoring, titan, rag-system]
source: docs/ai/plans/2026-06-12_architecture-review.md
---
# RAG-System Architektur-Review & Refactoring (Juni 2026)

Am 12.06.2026 wurde das gesamte RAG-System (titan, brain-mcp, brain-dashboard,
obsidian-inbox-watcher, workspace-mcp) einem Architektur-Review unterzogen und
der Maßnahmenkatalog in derselben Session fast vollständig umgesetzt. Der
vollständige Plan mit allen Befunden liegt in
[`2026-06-12_architecture-review.md`](2026-06-12_architecture-review.md) nebenan.

## Kernbefund

Vier der fünf Repos waren strukturell sauber. Die kritischen Probleme saßen
konzentriert in [[projekt-titan]], das als CLI-Skript geboren und zum Service
umgebaut wurde: synchroner GPU-/Ollama-/Qdrant-Code in `async def`-Handlern
blockierte den kompletten Event-Loop (während eines Ingests war `/health`
unerreichbar), und der CLI-PDF-Pfad schrieb ein anderes Qdrant-Payload-Schema
als der Service-Pfad (PDF-Chunks unsichtbar in `/notes`, Orphans bei
Re-Ingest).

## Was umgesetzt wurde (alles committet, getestet, deployed)

**titan** (5 Commits):
- Alle Endpoints sync (Threadpool) + `work_lock` für GPU/Index-Mutationen —
  der Service bleibt während Ingests erreichbar.
- Ein Payload-Schema für CLI- und Service-Ingest (`source_path`, `run_id`,
  `content_hash` überall); Legacy-PDF-Chunks werden beim nächsten Re-Ingest
  der jeweiligen Datei aufgeräumt.
- Zentrale Konfiguration `titan/config.py` (pydantic-settings, env-Namen
  unverändert) + `titan/infra.py` als einzige Modell-/Client-Factory.
- **Content-Hash-Skip:** unveränderte Datei-Bytes → kein GPU-Re-Embed
  (`skipped_reason: "unchanged"`); `force=true` erzwingt Re-Ingest.
- Performance: alle Sub-Queries in einem GPU-Batch, täglicher
  Cache-Cleanup-Task, toter Ballast entfernt. Such-Latenz live: ~46 ms.
- `Chunk`-Dataclass statt `dict[str, Any]` durch die Pipeline +
  `QdrantRepository` — Routes machen nur noch HTTP/Locking/Mapping.
- Fehlende `domain` im Frontmatter → 422 statt 500.

**brain-mcp:** Error-Decorator statt 6× Copy-Paste; tenacity-Retry-Bug
gefixt (retried keine 4xx mehr); Watcher requeued 5xx/Timeout begrenzt
(max. 5 Versuche pro Datei) statt Events zu verlieren.

**obsidian-inbox-watcher:** Frontmatter via `yaml.safe_dump` (Titel mit
`:` oder `"` brechen das YAML nicht mehr); Gemini-Antwort läuft durch ein
Pydantic-Modell (`GeminiNote`). Außerdem komplett modularisiert (P1.4):
`config` / `retrying` / `extractors` (Registry statt if/elif — neue Formate
sind ein Eintrag) / `note_builder` / `pipeline` / `watcher`; `main.py` ist
nur noch Entry-Point + Re-Exports.

**brain-dashboard:** Optionales Token-Gate (`BRAIN_DASH_AUTH_TOKEN` in
`.env` + Restart; Login einmalig via `/?token=<wert>`). Default aus —
solange das Token leer ist, verhält sich alles wie vorher. Siehe auch
[[projekt-brain-dashboard]].

**Testtiefe:** Pipeline-Kern (Chunking, Fensterung, RRF, Decompose-Parsing)
ist jetzt ohne GPU/Qdrant getestet; die Integrations-Fixture isoliert Test-
und Produktiv-Collections sauber (vorher konnte die Suche im Test je nach
Importreihenfolge gegen die echte Collection laufen).

## Bewusst offen (als Ideen geparkt, mit Plan-Verweis)

- **P2.4** — `/notes`-Aggregation auf Qdrant-Facets/Registry, erst bei
  Vault-Wachstum (`titan/docs/ai/IDEAS.md`).
- **P3.2** — hypothesis-Tests für `_split_text` (`titan/docs/ai/IDEAS.md`).
- **P3.3** — Request-ID-Korrelation titan ↔ brain-mcp, bei Bedarf
  (`titan/docs/ai/IDEAS.md`).

## Verwandte Notizen

[[rag-system-architektur]] · [[rag-system-runbook]] · [[projekt-titan]] ·
[[projekt-brain-mcp]] · [[projekt-obsidian-inbox-watcher]]
