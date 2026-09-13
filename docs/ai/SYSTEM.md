# Systemkarte — stack-workspace

> Umbenannt von `rag-workspace` am 04.09.2026. Der alte Name beschrieb, was hier
> zufällig zuerst lag. Ein Workspace ist eine **Entwicklungs**-Koordinationsschicht,
> keine Deployment-Einheit — es spricht nichts dagegen, dass lokal laufende und
> anderswo laufende Dienste darin stehen.
>
> Übernommene und beibehaltene Konvention: **keine Tailnet-Hostnamen oder -Adressen in
> diesem Repo.** Platzhalter wie `<workstation>` und `<your-tailnet-host>.ts.net` sind
> Absicht; die echten Werte stehen im Vault, der privat ist — dieses Repo ist es nur
> *heute*.

## Was dieses System tut

Zwei Hälften, die immer schon dieselbe Person betrieben hat und die jetzt an einer
Stelle koordiniert werden:

- **Ein lokales Wissenssystem.** Dokumente (Markdown-Notizen, PDFs, Inbox-Dateien)
  werden zu einer durchsuchbaren Vektordatenbank und Claude zugänglich gemacht. titan
  ist die Maschine, brain-mcp die Brücke, obsidian-inbox-watcher die Zuführung. Alles
  lokal — kein Cloud-RAG.
- **Die Werkzeuge rund um die Auftragsarbeit.** meeting-tickets macht aus
  aufgezeichneten Kundengesprächen geprüfte Ticket-Entwürfe auf einem Planka-Board;
  planka-mcp gibt Claude Code dieses Board zurück zum Abarbeiten. Zusammen schließen sie
  den Kreis vom gesprochenen Satz bis zum Code.

Über beidem steht **homebase**, die eine Oberfläche. Sie liegt in keinem Datenpfad —
sie beobachtet und steuert.

## Dienste

| Dienst (`repos/<name>`) | Rolle | Konsumiert | Stellt bereit | Port |
|--------------------------|-------|------------|---------------|------|
| **titan** | RAG-Maschine: Ingest + hybride Suche über Qdrant | — (Qdrant, GPU) | HTTP-API (`contracts/titan.openapi.yaml`) | 8765 (127.0.0.1) |
| **brain-mcp** | MCP-Server + Vault-Watcher; macht Notizen für Claude durchsuchbar | titan | MCP-Werkzeuge (`contracts/brain-mcp.tools.json`) | 9100 (0.0.0.0) |
| **homebase** | Die Oberfläche: Status, Logs, Start/Stopp — wächst zur Front über alles hier | titan (`/health`) | Web-UI (kein Contract) | 9200 |
| **obsidian-inbox-watcher** | Rohdokumente → Gemini → Vault-Notiz | — | Vault-Notizformat | — (Worker) |
| **workspace-mcp** | Nur-lesender MCP-Server, der den Workspace für Planungs-Chats öffnet | — | MCP-Werkzeuge (`contracts/workspace-mcp.tools.json`) | 9300 (0.0.0.0) |
| **meeting-tickets** | Aufgezeichnete Kundengespräche → geprüfte Ticket-Entwürfe → Planka-Karten | — (Planka-HTTP-API) | eine CLI, kein Dienst | — |
| **planka-mcp** | Gibt Claude Code ein Planka-Board: ansehen, beanspruchen, abarbeiten, zurückgeben | — (Planka-HTTP-API) | MCP-Werkzeuge (noch kein Contract extrahiert) | 9101 |

`homebase` hieß bis zum 04.09.2026 `brain-dashboard`. Python-Paket, Env-Präfix
`BRAIN_DASH_` und Unit-Name tragen weiterhin den alten Namen; das ändert Phase 2 von
`plan-zentrales-dashboard`.

## Abhängigkeitsgraph

```
homebase ──▶ titan ◀── brain-mcp
                           ▲
                           │ (beobachtet vault notes/inbox/)
             obsidian-inbox-watcher

meeting-tickets ──▶ Planka ◀── planka-mcp        (Planka ist Infrastruktur auf
                                                   dem Hub, kein Repo hier)

workspace-mcp (Introspektion zur Planungszeit, neben dem Laufzeitgraph)
```

- `brain-mcp` und `homebase` rufen **titan über HTTP**. titan hängt von keinem Repo ab —
  nur von lokaler Infrastruktur (Qdrant-Container, BGE-M3 auf der GPU).
- `obsidian-inbox-watcher` ruft niemanden; er **schreibt Markdown-Notizen** in die
  Vault-Inbox, und brain-mcps Watcher indiziert sie. Die Kopplung ist das
  **Vault-Notizformat** (das `domain:`-Frontmatter), kein API-Aufruf.
- `meeting-tickets` und `planka-mcp` sprechen **nicht** miteinander. Beide sprechen mit
  derselben Planka-Instanz — eines schreibt Karten, das andere liest und bewegt sie. Das
  Board ist die Schnittstelle dazwischen, und genau deshalb *ist* das Verschieben einer
  Karte die Rückmeldung.
- `workspace-mcp` ist ein Server zur **Entwurfszeit**, der dieses Meta-Repo einem
  Planungs-Chat öffnet. Er liegt in keinem Laufzeitpfad.

## Datenfluss Ende zu Ende

**Ingest (Notizweg):** `.md` im Vault ändern/ablegen → brain-mcps `brain-watcher`
entprellt 30 s → `POST titan /ingest/file` → Docling/Markdown-Lesen → Header-Chunking →
BGE-M3 Late Chunking (dense+sparse+colbert) → Upsert in Qdrant.

**Ingest (Dokumentweg):** PDF/DOCX/URL in die Inbox → obsidian-inbox-watcher extrahiert
Text → Gemini klassifiziert/fasst zusammen → schreibt `.md` mit `domain:` nach
`notes/inbox/` → mündet in den Notizweg oben.

**Abfrage:** Claude ruft `query_knowledge` auf brain-mcp → `POST titan /search` (hybrid
dense+sparse+ColBERT, RRF) → gerankte Chunks → Claude formuliert die Antwort.

**Auftragsarbeit:** aufgezeichnetes Gespräch → meeting-tickets → geprüfte
Ticket-Entwürfe → Planka-Karten → planka-mcp reicht eine an Claude Code → Arbeit →
zurück aufs Board zum Review.

**Betrieb:** homebase pollt `titan /health` alle 3 s, streamt systemd-/Qdrant-Logs per
SSE und startet/stoppt den Stack — es beobachtet und steuert, es liegt nicht im
Datenpfad.

## Grenzen & Invarianten

- **titan ist der einzige Schreiber von Qdrant.** Kein anderes Repo fasst die
  Vektordatenbank direkt an.
- **`domain:`-Frontmatter ist Pflicht**, damit eine Notiz indiziert wird; es ist der
  gemeinsame Bezeichner zwischen der Ausgabe des Inbox-Watchers und titans
  Domain-Filter und -Cache.
- **Re-Ingest ist Upsert-vor-Löschen** (neue `run_id`, alte Chunks danach entfernt) —
  kein Repo darf annehmen, dass die Chunks einer Notiz mitten im Update verschwinden.
- **Startreihenfolge:** Qdrant (Docker) → titan → brain-mcp / brain-watcher. Wer
  „Titan unreachable" sieht, hat die Kette darunter nicht oben.
- **Das Planka-Board ist die Prüfoberfläche für Ticket-Entwürfe.** Eine zweite
  Review-UI in homebase wäre die ADR-Verletzung vom 07.08.2026 noch einmal. homebase
  darf das Board *zeigen*; es wird kein Ort, an dem Entwürfe abgenommen werden.
- **homebase ist ein Codeblock, nicht ein Prozess.** Seine Module brauchen
  verschiedene Laufzeitrechte — RAG will `systemctl --user` in WSL, das Weck-Modul
  Host-Netz und die SSH-Schlüssel des Hosts, Minecraft den Docker-Socket. Ein
  gemeinsames Image ist möglich, eine gemeinsame Rechtemenge nicht — sonst trägt jeder
  Prozess die Rechte aller drei.

## Deployment-Topologie

Drei Maschinen, weil die Hardware es erzwingt — nicht aus Bequemlichkeit:

| Wo | Was dort läuft | Warum es nicht umziehen kann |
|---|---|---|
| Workstation `<workstation>` (WSL2) | titan, brain-mcp, homebase, workspace-mcp, caddy | die GPU (BGE-M3, faster-whisper `large-v3`) und `systemctl --user` über den Stack |
| Hub (always-on Mini-PC) | obsidian-inbox-watcher, Planka, der Weck-Endpunkt | Wake-on-LAN ist ein **LAN-Broadcast**, und was die Workstation weckt, darf nicht von ihr abhängen |
| Minecraft-Host | das Minecraft-Modul, sobald es existiert | Docker-Socket und RCON im internen Netz |

- titan bindet `127.0.0.1:8765` (bewusst nur lokal). brain-mcp bindet `0.0.0.0:9100`
  und ist über den **Tailscale-Funnel** hinter einer GitHub-OAuth-Allowlist erreichbar.
  Ein caddy auf 8088 verteilt auf brain-mcp, workspace-mcp (`/ws`) und planka-mcp
  (`/planka`); **alle drei antworten nur, solange die Workstation an ist.**
- 🔴 **homebase ist noch nicht öffentlichkeitsfähig.** Es bindet `0.0.0.0`, kann
  systemd-Units steuern und Windows-Prozesse beenden, und `BRAIN_DASH_AUTH_TOKEN` ist
  **standardmäßig leer**, womit die Middleware ein No-op ist. Der Auth-Umbau kommt vor
  jeder Erreichbarkeit, nicht danach.
- Externe Abhängigkeiten (keine Repos): Qdrant, BGE-M3 auf der GPU, die Gemini-API (nur
  Inbox-Watcher), Planka, Tailscale.
