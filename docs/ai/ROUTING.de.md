# Routing — stack-workspace

> Wohin eine Änderung gehört. Vor jeder Bearbeitung eines Repos hier nachsehen.
>
> Die Prüffrage, die `plan-zentrales-dashboard` an diese Datei stellt: **beantwortet sie
> eine Änderungsfrage, die man sonst hätte raten müssen?** Eine Zeile, die nur den Namen
> eines Repos wiederholt, trägt nichts. Die Zeilen unten sind gegen die Fragen
> geschrieben, die bei sieben Repos tatsächlich mehrdeutig waren.

## Zuständigkeit nach Verantwortung

| Wenn die Änderung … betrifft | Repo | Anmerkung |
|------------------------------|------|-----------|
| Chunking, Embeddings, Late Chunking, BGE-M3 | **titan** | Maschineninternes — lokale Entscheidung |
| Hybride Suche / RRF / Ranking | **titan** | ändert sich die `/search`-Antwortform → Contract |
| Qdrant-Collection / Vektoren / Payload-Index | **titan** | nur titan schreibt Qdrant |
| titans HTTP-Endpunkte (Pfad/Parameter/Antwort) | **titan** | **Contract-Änderung** → `contracts/titan.openapi.yaml` + brain-mcp + homebase |
| Name/Argumente/Ergebnis eines MCP-Werkzeugs | **brain-mcp** | **Contract-Änderung** → `contracts/brain-mcp.tools.json` (Claude ist der Konsument) |
| Vault-Watcher / Entprellung / welche Dateien indiziert werden | **brain-mcp** | ruft titan `/ingest/file` |
| GitHub-OAuth-Allowlist, Funnel-Auth | **brain-mcp** | lokal zu brain-mcp |
| Dashboard-UI, Status-Polling, Log-Streaming, Start/Stopp | **homebase** | liest nur titan `/health` |
| Inbox-Extraktion, Gemini-Prompt, Notiz-Schreiben | **obsidian-inbox-watcher** | die Ausgabe muss das `domain:`-Frontmatter behalten |
| Das Vault-Notizformat / die Bedeutung von `domain:` | **System** | geteilt von Inbox-Watcher + brain-mcp + titan → Workspace-Entscheidung |
| Introspektion zur Planungszeit / den Workspace einem Chat öffnen | **workspace-mcp** | Entwurfszeit-Werkzeug — lokale Entscheidung |
| Transkription, Ticket-Extraktion, den Prompt, der ein Ticket entwirft | **meeting-tickets** | die Ausgabe landet auf dem Board, nicht in einem anderen Repo |
| Eine Karte lesen, beanspruchen oder verschieben | **planka-mcp** | das Board ist die Schnittstelle; die beiden Planka-Repos rufen einander nie |
| Ob ein Ticket-Entwurf *abgenommen* ist | **das Planka-Board** | kein Repo. Eine Review-UI in homebase wäre die ADR-Verletzung vom 07.08.2026 |
| Die Listen-/Spaltenstruktur des Boards | **System** | beide Planka-Repos kodieren sie → Workspace-Entscheidung, nicht die eines Repos |
| Eine caddy-Route oder ein neuer Pfad unter dem einen Funnel | **workspace-mcp** | der Caddyfile liegt in `repos/workspace-mcp/deploy/`, obwohl er drei Server bedient |

## Die Zeilen, die es erst seit dem 04.09.2026 gibt

`plan-zentrales-dashboard` hat drei fremde Codebasen nach homebase importiert. Bis
Phase 2 sie zu Modulen macht, liegen sie unangetastet unter `imported/` — und das zieht
Grenzen, die es vorher nicht gab:

| Wenn die Änderung … betrifft | Wohin | Anmerkung |
|------------------------------|-------|-----------|
| Irgendetwas unter `homebase/imported/` | **noch nirgends** | es ist *unverändert* importiert und muss bis Phase 2 byte-identisch bleiben. ruff ist dort bewusst ausgeschlossen. Wer vor Phase 2 einen Fehler darin behebt, macht den Import zu etwas anderem, als er behauptet |
| Den Wake-on-LAN-**Knopf** | **homebase** | „alles an einem Ort" gilt für die Bedienung |
| Den Wake-on-LAN-**Sender** | **den Hub**, nicht dieses Repo | ein VPS kann nicht ins Heimnetz broadcasten, und was die Workstation weckt, darf nie von ihr abhängen |
| Kaltstart / vollständiges Herunterfahren des Stacks | **bleibt `.bat`-Skript** | homebase läuft *innerhalb* von WSL: es kann Docker Desktop nicht starten, und `wsl --shutdown` brächte den eigenen Aufrufer um |
| Erreichbarkeitsampeln, Statusansichten aus den Skripten | **homebase** | die prüfende und meldende Hälfte ist genau das, was eine Weboberfläche gut kann — Phase 5 |
| Eine interaktive SSH-Sitzung (`Mini-PC`, `coolify-prod`) | **bleibt `.bat`-Skript** | das im Browser nachzubauen heißt, ein Web-Terminal zu betreiben — eine Angriffsfläche ohne Verhältnis zu einer Verknüpfung |
| Auf welcher Maschine ein homebase-Modul läuft | **System** | von Laufzeitrechten erzwungen, nicht von Vorliebe → Workspace-Entscheidung. Siehe SYSTEM.de.md, „Deployment-Topologie" |
| Einen echten Tailnet-Host, eine Adresse oder einen Loginnamen | **den Vault, nie ein Repo** | Repos tragen nur Platzhalter. Der Vault ist privat; ein Repo ist es nur heute |

## Repo-übergreifende Änderungen (echte Beispiele)

- **„Ein neues Feld in titans `/search`-Antwort"** → Contract-Änderung.
  `contracts/titan.openapi.yaml` aktualisieren, dann brain-mcp (den Konsumenten) im
  selben Feature. homebase ist nicht betroffen (nutzt nur `/health`).
- **„Die `domain:`-Frontmatter-Regeln ändern"** → betrifft Inbox-Watcher (Schreiber),
  brain-mcp (Watcher/Leser) und titan (Filter/Cache). Workspace-Plan + Entscheidung.
- **„Ein MCP-Werkzeug umbenennen"** → brain-mcp-Contract; der Konsument ist Claude
  selbst, also `contracts/brain-mcp.tools.json` und die Werkzeugbeschreibungen mitziehen.
- **„Eine Spalte aufs Planka-Board"** → sowohl meeting-tickets (schreibt Karten hinein)
  als auch planka-mcp (liest und bewegt sie) kodieren die Struktur. Keines besitzt sie
  allein.
- **„homebase von außen erreichbar machen"** → gar keine Routing-Frage. Es hängt am
  Auth-Umbau: das Token-Gate ist standardmäßig leer und der Dienst steuert systemd.

## Schneller Entscheidungsbaum

- Maschinenintern (Chunking, Ranking, Qdrant)? → **titan**, lokale Regeln.
- Ändert einen titan-Endpunkt? → Contract → titan + brain-mcp (+ homebase bei `/health`).
- MCP-Werkzeugfläche? → **brain-mcp**- (oder **planka-mcp**-)Contract.
- Notizformat / `domain:`? → **systemweit** → erst Workspace-Plan.
- Betrifft die Form des Boards? → **systemweit** → beide Planka-Repos.
- Unter `homebase/imported/`? → **auf Phase 2 warten.**
- Braucht einen echten Host oder eine Adresse? → **den Vault.**
