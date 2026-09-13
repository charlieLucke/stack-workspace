# Plan: Verständlichkeit der Repos für die Bewerbung

> **Status: umgesetzt, Juni 2026. Die Kästchen unten sind nicht nachgepflegt —
> sie zeigen den Plan, wie er geschrieben wurde.** Was daraus wurde, steht in der
> Vault-Notiz `bewerbung-repos-aufbereitung-2026-06`: READMEs, Mermaid-Diagramme,
> System-Map, MIT-Lizenz und die GitHub-Metadaten sind gesetzt. Zwei Punkte aus
> Phase 0 sind bewusst *nicht* erledigt: die Repos sind weiterhin privat, weil das
> Umschalten unumkehrbar ist, und die Pin-Reihenfolge im Profil folgt danach.
>
> Zwei Annahmen des Plans haben sich seither überholt und werden hier nicht
> nachträglich korrigiert, weil ein Plan ein Dokument seiner Zeit ist: er spricht
> von *drei* Repos (inzwischen sind es zehn), und er schlägt vor, den
> „Working with AI Tools"-Block nach hinten zu kürzen — geblieben ist er, weil
> genau dieser Block zeigt, wie hier gearbeitet wird.


> Ziel: Ein Empfänger der Initiativbewerbung, der **noch nie von „Titan"
> gehört hat**, soll in ~30 Sekunden pro Repo verstehen, *was* es macht,
> *warum* es technisch stark ist und *wie* die drei Teile zusammengehören.
> Maßstab ist nicht der Code (den liest niemand), sondern die README-Landingpage.

---

## Leitprinzipien (gelten für alle drei Repos)

1. **Kalter Leser zuerst.** Jeder Begriff, der nicht Allgemeinwissen ist
   (allen voran „Titan"), wird beim ersten Auftreten in einem Satz erklärt.
2. **System vor Einzelteil.** Die drei Repos sind *ein* System. Jedes Repo
   sagt oben, wo es im Gesamtbild steht, und verlinkt die anderen zwei.
3. **Substanz nach oben.** Die beeindruckenden Architektur-Details gehören
   auf die README-Startseite, nicht versteckt in `docs/ai/`.
4. **Engineering statt „nur für mich".** Formulierungen wie „meine Notizen"
   oder „ausschließlich persönlicher Einsatz" raus — die übertragbare
   Ingenieurleistung betonen.
5. **Internes Gerüst nach hinten.** Der „Working with AI Tools"-Block
   (CLAUDE.md/AGENTS.md/GEMINI.md) ist Entwickler-Workflow, kein Portfolio —
   ans Ende kürzen oder in `docs/` verschieben.

---

## Phase 0 — Vorbereitung (Pflicht, vor allem anderen)

- [ ] **Sichtbarkeit prüfen.** Alle drei Repos auf **public** stellen und im
      Inkognito-Browser öffnen — vorher kamen 404. Ein toter Link in der Mail
      ist schlimmer als kein Link.
- [ ] **Repo-Beschreibung & Topics setzen.** GitHub „About"-Feld pro Repo
      (ein Satz) + Topics (z. B. `rag`, `qdrant`, `bge-m3`, `mcp`, `fastapi`).
      Das ist das Erste, was in Suchergebnissen und Profil sichtbar ist.
- [ ] **Reihenfolge im Profil.** titan als Pinned-Repo Nr. 1, dann brain-mcp,
      dann obsidian-inbox-watcher.

---

## Phase 1 — titan (Flaggschiff, größter Hebel)

titan ist die „Hauptseite" deines Portfolios. Hier steckt die meiste
Substanz und hier ist die Lücke am größten.

### 1.1 README komplett neu strukturieren

Der aktuelle README springt von einem Einzeiler direkt zu „Setup". Neue
Gliederung (von oben nach unten):

1. **Titel + ein starker Satz** — was es ist und was es kann.
   Beispiel-Richtung: *„Lokales RAG-System auf einer einzelnen Workstation:
   indexiert PDFs und Notizen multi-vektoriell und beantwortet Fragen mit
   hybrider Suche + lokalem LLM — komplett offline, ohne Cloud."*
2. **Was ist RAG / warum das hier besonders ist** — 2–3 Sätze, damit auch
   ein nicht-spezialisierter Leser andockt.
3. **Architektur-Überblick** — das Diagramm + die Kernbausteine direkt hier,
   nicht erst in `docs/ai/ARCHITECTURE.md`:
   - BGE-M3 Multi-Vektor-Embeddings (dense + sparse + ColBERT)
   - Qdrant als Vektor-DB
   - Late Chunking
   - Hybrid Search mit Reciprocal Rank Fusion + ColBERT-MaxSim-Reranking
   - Phi-4 via Ollama als Generator
   - FastAPI-Service mit dauerhaftem Modell im VRAM + GPU-Lock
   - Semantic Cache, LLM-as-Judge-Evaluation
4. **Konkretes Beispiel** — eine echte Frage → gekürzte Antwort, oder ein
   `curl`-Aufruf gegen `/search` mit Beispiel-JSON. Macht das Abstrakte greifbar.
5. **Teil eines größeren Systems** — kurzer Abschnitt mit Diagramm:
   `obsidian-inbox-watcher` (Ingest) → titan (RAG-Kern) → `brain-mcp`
   (Claude-Anbindung). Mit Links zu beiden Repos.
6. **Setup / Development / Tooling** — der bestehende Inhalt, nach unten.
7. **„Working with AI Tools"** — auf 2–3 Zeilen kürzen oder nach `docs/`.

- [ ] README nach obiger Gliederung neu schreiben
- [ ] Architektur-Diagramm einbauen (Mermaid, wie es obsidian-inbox-watcher
      schon vormacht — rendert direkt auf GitHub)
- [ ] Mindestens ein Beispiel (Query→Antwort oder curl) ergänzen
- [ ] System-Map mit Links zu den anderen zwei Repos

### 1.2 Framing korrigieren

- [ ] „Zielgruppe: ausschließlich persönlicher Einsatz" in `CONTEXT.md`
      neutraler fassen (z. B. „Single-Workstation-Deployment, kein
      Multi-User") — die Aussage „nur für mich" entwertet die Arbeit.

---

## Phase 2 — brain-mcp

### 2.1 Opener entpersonalisieren + Titan erklären

- [ ] Erste Zeile umschreiben: statt „make **my** Obsidian notes searchable"
      → was es technisch ist (ein MCP-Server, der ein RAG-Backend als Custom
      Connector an Claude anbindet).
- [ ] Beim ersten „Titan" einen Halbsatz ergänzen: *„Titan (separates Repo,
      Link) — das lokale RAG-System, das die eigentliche Suche übernimmt."*

### 2.2 Die leere ARCHITECTURE.md beheben (wichtig!)

`docs/ai/ARCHITECTURE.md` ist aktuell ein **leeres Template** mit
Platzhaltern. Wer da klickt, hält das Projekt für unfertig. Die echte
Architektur (mit dem schönen ASCII-Diagramm) steht stattdessen in `CONTEXT.md`.

- [ ] Entweder: Inhalt aus `CONTEXT.md` (Architektur-Block, 4 MCP-Tools,
      Datenfluss) nach `ARCHITECTURE.md` übertragen und ausformulieren
- [ ] Oder: das Template löschen, damit kein „leerer Raum" sichtbar ist
- [ ] Die 4 MCP-Tools (`query_knowledge`, `ingest_note`, `list_domains`,
      `find_related`) im README kurz mit je einer Zeile beschreiben — das ist
      die nach außen sichtbare Funktionalität.

### 2.3 Substanz nach oben

- [ ] Das technisch Interessante (Tailscale Funnel, GitHub-OAuth-Proxy mit
      Allowlist, WSL2-`0.0.0.0`-Bind-Problematik) kurz im README anreißen —
      das zeigt Deployment-/Security-Kompetenz, nicht nur „Tool gebaut".
- [ ] System-Map + Links zu titan und obsidian-inbox-watcher.

---

## Phase 3 — obsidian-inbox-watcher (leichtester Aufwand)

Der beste der drei READMEs — hier nur Feinschliff.

- [ ] Beim ersten „Titan" denselben erklärenden Halbsatz + Link einfügen.
- [ ] System-Map / Links zu den anderen zwei Repos ergänzen (Konsistenz).
- [ ] Das vorhandene Mermaid-Diagramm aus `ARCHITECTURE.md` ggf. auch im
      README zeigen — es ist gut und verkauft das Projekt.

---

## Phase 4 — Übergreifender Feinschliff (alle drei)

- [ ] **License setzen.** Überall steht „License: TBD" — wirkt unfertig.
      Eine MIT-License-Datei reicht und signalisiert „fertig & teilbar".
- [ ] **Konsistente System-Map.** Dasselbe kleine Diagramm in allen drei
      READMEs, je mit „du bist hier"-Markierung. Erzeugt sofort das Bild
      eines durchdachten Gesamtsystems.
- [ ] **Optionaler Screenshot/GIF.** Eine Claude-Konversation, in der das
      brain-mcp-Tool eine Frage aus dem Vault beantwortet — das ist der
      „Wow"-Beleg, dass alles wirklich läuft. (Nur wenn das System gerade
      hochfahrbar ist.)

---

## Phase 5 — Bewerbung scharf schalten

- [ ] GitHub-Links in die E-Mail-Signatur (Profil + die drei Repos einzeln).
- [ ] Eine Mail-Variante (technisch detailliert vs. Problem-Aufhänger) final
      wählen — die Repos sind dann der klickbare Beleg dafür.
- [ ] Optional: Demo-Bereitschaft. Falls jemand antwortet, das System für
      eine Live-Demo stabil hochfahren können.

---

## Empfohlene Reihenfolge

```
Phase 0 (Sichtbarkeit)  →  Phase 1 (titan-README)  →  Phase 2 (brain-mcp)
   →  Phase 3 (watcher)  →  Phase 4 (Politur)  →  Phase 5 (Mail raus)
```

Wenn die Zeit knapp ist: **Phase 0 + Phase 1.1 sind das Minimum.** Ein
starker titan-README mit Architektur und System-Map trägt die anderen zwei
mit, selbst wenn die noch nicht perfekt sind.

---

## Definition of Done — der 30-Sekunden-Test

Ein Außenstehender öffnet *irgendeines* der drei Repos und kann ohne
Scrollen in den Code beantworten:

- [ ] Was macht dieses Projekt? (ein Satz, ganz oben)
- [ ] Warum ist es technisch anspruchsvoll? (Architektur sichtbar)
- [ ] Wie sieht das im Einsatz aus? (Beispiel/Diagramm)
- [ ] Wie hängt es mit den anderen Teilen zusammen? (System-Map + Links)
- [ ] Ist das ein fertiges, teilbares Projekt? (License, keine leeren Templates)

Erst wenn alle fünf Punkte für **jedes** Repo erfüllt sind, ist es
bewerbungsreif.
