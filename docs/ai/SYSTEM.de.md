# Systemkarte — rag-system (AUSGEFÜLLTES BEISPIEL)

> Eine reale Instanziierung: charlies lokaler RAG-Stack. Vier unabhängige Repos in ~/projects,
> nur durch titans HTTP-API und ein gemeinsames Vault-Notiz-Format verbunden.

## Was dieses System macht

Ein lokales Wissenssystem für eine einzelne Workstation. Dokumente (Markdown-Notizen, PDFs und Inbox-
Dateien wie PDF/DOCX/URLs) werden in eine durchsuchbare Vektordatenbank verwandelt und Claude
zugänglich gemacht. titan ist die Engine; brain-mcp brückt sie zu Claude; brain-dashboard betreibt sie;
obsidian-inbox-watcher speist Rohdokumente ein. Alles läuft lokal — kein Cloud-RAG.

## Services

| Service (`repos/<name>`) | Rolle | Konsumiert | Stellt bereit | Port |
|--------------------------|------|----------|---------|------|
| **titan** | RAG-Engine: Ingest + hybride Suche über Qdrant | — (Qdrant, GPU) | HTTP-API (`contracts/titan.openapi.yaml`) | 8765 (127.0.0.1) |
| **brain-mcp** | MCP-Server + Vault-Watcher; macht Notizen für Claude durchsuchbar | titan | MCP-Tools (`contracts/brain-mcp.tools.json`) | 9100 (0.0.0.0) |
| **brain-dashboard** | Web-Control-Panel: Status, Logs, Start/Stopp | titan (`/health`) | Web-UI (kein Contract) | 9200 |
| **obsidian-inbox-watcher** | Rohdokumente → Gemini → Vault-Notiz | — | Vault-Notiz-Format | — (Worker) |
| **workspace-mcp** | Read-only-MCP-Server, der Workspace-Karte, Routing, Contracts, Graph für Planungs-Chats bereitstellt | — | MCP-Tools (`contracts/workspace-mcp.tools.json`) | 9300 (0.0.0.0) |

## Abhängigkeitsgraph

```
brain-dashboard ──▶ titan ◀── brain-mcp
                                  ▲
                                  │ (überwacht Vault notes/inbox/)
                    obsidian-inbox-watcher

workspace-mcp (steht neben dem Runtime-Graphen als Planungszeit-Introspektions-Tool)
```

- `brain-mcp` und `brain-dashboard` rufen **titan über HTTP** auf. titan hängt von keinem Repo ab —
  nur von lokaler Infra (Qdrant-Container, das BGE-M3-Modell auf der GPU).
- `obsidian-inbox-watcher` ruft niemanden auf; es **schreibt Markdown-Notizen** in die Vault-
  Inbox. Die *Watcher*-Komponente von brain-mcp ingestet sie dann in titan. Die Kopplung ist das
  **Vault-Notiz-Format** (ein `domain:`-Frontmatter-Feld), kein API-Aufruf.
- `workspace-mcp` ist ein **Design-Zeit-Introspektions-Server**, der das Workspace-Meta-Repo einem Planungs-Chat bereitstellt. Es ist nicht Teil des RAG-Runtime-Pfads und hängt von keinen laufenden Services ab.

## End-to-end-Datenfluss

**Ingest (Notiz-Pfad):** ein `.md` im Vault editieren/ablegen → brain-mcps `brain-watcher` debouncet
30 s → `POST titan /ingest/file` → Docling/Markdown-Read → Header-Chunking → BGE-M3 Late
Chunking (dense+sparse+colbert) → Upsert in Qdrant.

**Ingest (Dokument-Pfad):** PDF/DOCX/URL in die Inbox legen → obsidian-inbox-watcher extrahiert
Text → Gemini klassifiziert/fasst zusammen → schreibt ein `.md` mit `domain:` nach `notes/inbox/` →
(schließt sich oben dem Notiz-Pfad via brain-watcher an).

**Query:** Claude ruft ein MCP-Tool auf brain-mcp auf (`query_knowledge`) → brain-mcp →
`POST titan /search` (hybrid dense+sparse+ColBERT, RRF) → gerankte Chunks → Claude komponiert
die Antwort.

**Betrieb:** brain-dashboard pollt `titan /health` alle 3 s, streamt systemd-/Qdrant-Logs
via SSE und startet/stoppt den Stack — es beobachtet und steuert, es ist nicht im Datenpfad.

## Grenzen & Invarianten

- **titan ist der einzige Writer von Qdrant.** Kein anderes Repo berührt die Vektor-DB direkt.
- **`domain:`-Frontmatter ist obligatorisch**, damit eine Notiz indexiert wird; es ist der gemeinsame
  Identifikator, der den Output des Inbox-Watchers an titans Domain-Filter und -Cache bindet.
- **Re-Ingest ist upsert-before-delete** (neue `run_id`, alte Chunks danach entfernt) — kein Repo
  darf annehmen, dass die Chunks einer Notiz mitten im Update verschwinden.
- **Service-Startreihenfolge:** Qdrant (Docker) → titan → brain-mcp / brain-watcher. Ein
  Konsument, der „Titan unreachable" bekommt, bedeutet, die Kette darunter ist nicht oben.

## Deployment-Topologie

- Alle Services laufen in **WSL2 (Ubuntu)** als systemd-User-Services auf der Workstation
  `<workstation>`. Qdrant läuft in **Docker Desktop auf Windows** (`qdrant_workstation`, Ports
  6333/6334).
- titan bindet `127.0.0.1:8765` (nur lokal, by design). brain-mcp bindet `0.0.0.0:9100` und
  ist öffentlich via **Tailscale Funnel** exponiert (`<your-tailnet-host>.ts.net`), abgesichert durch
  GitHub-OAuth-Allowlist — der einzige von außen erreichbare Service.
- Externe Abhängigkeiten (keine Repos): Qdrant, das BGE-M3-Modell (GPU), die Gemini-API
  (nur Inbox-Watcher), Tailscale.
