# Plan: `GET /domains/{domain}/notes` (titan)

- **Datum:** 2026-06-02
- **Autor:** Opus (Planung)
- **Implementierer-Ziel:** Sonnet
- **Status:** ready

## Ziel
Einen additiven Read-Endpunkt zu titan hinzufügen, der die indexierten Notizen innerhalb einer
einzelnen Domain auflistet. Er spiegelt das bestehende `GET /notes`, aber gefiltert auf eine Domain.
Ermöglicht Per-Domain-Ansichten (Dashboard-Panel, Inspektion, gezieltes Cleanup) mit einem Aufruf.

## Warum das ein Plan auf Workspace-Ebene ist
Die Änderung ist additiv *innerhalb* von titan, aber titans HTTP-Oberfläche ist ein veröffentlichter
**Contract** (`contracts/titan.openapi.yaml`). Sie berührt also zwei Repos: `titan` (Code)
und diesen Workspace (den Contract). **Kein Konsument muss sich ändern** — der Endpunkt ist rein
additiv (brain-mcp und brain-dashboard sind nicht betroffen). Ein künftiges Dashboard-Panel KANN
ihn später konsumieren; das ist hier out of scope.

## Betroffene Repos & Landing-Reihenfolge
1. `repos/titan` (Provider) — Endpunkt + Tests implementieren.
2. Workspace — `contracts/titan.openapi.yaml` + `docs/ai/CONTRACTS.md` aktualisieren.

Die Reihenfolge ist nicht kritisch (additiv), aber titan zuerst, dann den Contract synchronisieren.

## Bereits getroffene Entscheidungen — NICHT neu entscheiden
- **Pfad:** `GET /domains/{domain}/notes` (REST-Nesting unter dem bestehenden `/domains`).
- **Schema-Wiederverwendung:** `NoteInfo` (schemas.py:104) und `NotesResponse` (schemas.py:110) wiederverwenden.
  **Kein** neues Schema hinzufügen.
- **Filterung:** einen Qdrant-`scroll_filter` auf dem `domain`-Payload-Feld nutzen. Die
  Filter-Konstruktion spiegeln, die bereits in `src/titan/search.py` genutzt wird:
  `Filter(must=[FieldCondition(key="domain", match=MatchValue(value=domain))])`.
  Der `domain`-Payload-Index existiert bereits, das ist also effizient und konsistent.
  **Nicht** alle Chunks scannen und in Python nachfiltern.
- **Unbekannte / leere Domain:** `200` mit `notes=[]`, `total=0` zurückgeben (NICHT 404) —
  konsistent damit, dass `/domains` eine leere Liste zurückgibt, und einfacher für Konsumenten.
- **503-Guard:** wenn `state.qdrant_client is None`, `HTTPException(503, ...)` werfen, genau
  wie `list_notes` es tut.

## Schritte

### titan — Endpunkt (`src/titan/service/routes.py`)
1. Eine neue Route unmittelbar nach `list_notes` hinzufügen (nach ~Zeile 470), in einem eigenen Sektions-
   Kommentar. Signatur: `async def list_domain_notes(domain: str) -> NotesResponse`.
   Dekorator: `@router.get("/domains/{domain}/notes", response_model=NotesResponse)`.
2. Body: die Scroll-and-Aggregate-Schleife aus `list_notes` kopieren, aber
   `scroll_filter=<der obige Domain-Filter>` an `state.qdrant_client.scroll(...)` übergeben.
   `Filter, FieldCondition, MatchValue` aus `qdrant_client.models` *lokal innerhalb
   der Funktion* importieren (gleicher Stil wie search.py) — kein neuer Top-Level-Import.
3. Den 503-Guard, die 256-Seiten-Scroll-Schleife, das `with_payload=["source_path",
   "domain"]` und das finale `NotesResponse(notes=nach-source_path-sortiert, total=len)`
   exakt wie in `list_notes` behalten.
4. Die Modul-Docstring-Endpunkt-Liste am Anfang von `routes.py` aktualisieren (eine Zeile ergänzen).

### titan — Tests (`tests/integration/test_service.py`)
5. `test_domain_notes_isolation` hinzufügen, das `test_search_domain_isolation` spiegelt: eine
   Notiz in Domain A und eine in Domain B via das bestehende `tmp_vault` + `/ingest/file`-
   Pattern ingesten, dann `app_client.get("/domains/<A>/notes")` und prüfen: Status 200, jede
   zurückgegebene Notiz hat `domain == A`, und `total` entspricht der Notiz-Anzahl von A.
6. `test_domain_notes_unknown` hinzufügen: `GET /domains/zzz/notes` → 200 mit `notes == []`,
   `total == 0`.

### Workspace — Contract
7. In `contracts/titan.openapi.yaml` den Pfad `/domains/{domain}/notes` hinzufügen: einen erforderlichen
   `domain`-Pfad-Parameter (String) und eine 200-Response, deren Body den `/notes`-
   Eintrag spiegelt (Array von `{source_path, domain, chunk_count}` + `total`).
8. In `docs/ai/CONTRACTS.md` den neuen Endpunkt zu titans „Oberfläche"-Liste hinzufügen.

## Verifikation (das Gate)
- `cd repos/titan && make check` → ruff + mypy (strict) + pytest alle grün, inklusive der
  zwei neuen Tests.
- Mit laufendem titan (`titan-service` + Qdrant oben): aus dem Workspace,
  `./workspace.sh contracts` → titan zeigt **OK** (kein DRIFT): das Live-`/openapi.json` enthält jetzt
  den neuen Pfad und passt zum committeten Contract. (Ist titan unten, wird es ge-SKIPpt —
  kein Fehler, aber der Live-Check ist der echte Beweis.)
- `./workspace.sh check` insgesamt grün.

## Out of Scope
- Ein brain-mcp-MCP-Tool für diesen Endpunkt.
- Ein brain-dashboard-UI-Panel.
- Pagination / Optimierung für große Collections (der Vault ist klein; ein gefilterter Scroll reicht).

## Zu berührende Dateien (Checkliste)
- [ ] `repos/titan/src/titan/service/routes.py` — neue Route + Docstring-Zeile
- [ ] `repos/titan/tests/integration/test_service.py` — 2 Tests
- [ ] `contracts/titan.openapi.yaml` — neuer Pfad
- [ ] `docs/ai/CONTRACTS.md` — titan-Oberflächen-Zeile
