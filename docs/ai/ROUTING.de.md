# Routing — rag-system (AUSGEFÜLLTES BEISPIEL)

> Wohin eine Änderung gehört. Vor dem Editieren irgendeines Repos hier nachschlagen.

## Eigentümerschaft nach Verantwortung

| Wenn die Änderung … betrifft | Repo | Notizen |
|-------------------------|------|-------|
| Chunking, Embeddings, Late Chunking, BGE-M3 | **titan** | Engine-Interna — lokale Entscheidung |
| Hybride Suche / RRF / Ranking | **titan** | wenn sich die `/search`-Response-Form ändert → Contract |
| Qdrant-Collection / Vektoren / Payload-Index | **titan** | nur titan schreibt Qdrant |
| titans HTTP-Endpunkte (jeder Pfad/Param/jede Response) | **titan** | **Contract-Änderung** → `contracts/titan.openapi.yaml` + brain-mcp + brain-dashboard aktualisieren |
| Name/Args/Result eines MCP-Tools | **brain-mcp** | **Contract-Änderung** → `contracts/brain-mcp.tools.json` (Claude ist der Konsument) |
| Vault-Watcher / Debounce / welche Dateien ingestet werden | **brain-mcp** | ruft titan `/ingest/file` auf |
| GitHub-OAuth-Allowlist, Funnel-Auth | **brain-mcp** | lokal zu brain-mcp |
| Dashboard-UI, Status-Polling, Log-Streaming, Start/Stopp | **brain-dashboard** | liest nur titan `/health` |
| Inbox-Extraktion, Gemini-Prompt, Notiz-Schreiben | **obsidian-inbox-watcher** | Output muss `domain:`-Frontmatter behalten |
| Das Vault-Notiz-Format / die Semantik des `domain:`-Felds | **system** | geteilt von inbox-watcher + brain-mcp + titan → Workspace-Entscheidung |
| Planungszeit-Introspektion / den Workspace einem Planungs-Chat bereitstellen | **workspace-mcp** | Design-Zeit-Tool — lokale Entscheidung |

## Repo-übergreifende Änderungen (reale Beispiele)

- **„Ein neues Feld zu titans `/search`-Response hinzufügen"** → Contract-Änderung.
  `contracts/titan.openapi.yaml` aktualisieren, dann brain-mcp (den Konsumenten) im selben Feature.
  brain-dashboard ist nicht betroffen (nutzt nur `/health`).
- **„Die `domain:`-Frontmatter-Regeln ändern"** → berührt inbox-watcher (Writer), brain-mcp
  (Watcher/Reader) und titan (Filter/Cache). Workspace-Plan + Entscheidung erforderlich.
- **„Ein MCP-Tool umbenennen"** → brain-mcp-Contract; der Konsument ist Claude selbst, also
  `contracts/brain-mcp.tools.json` und etwaige Tool-Beschreibungen aktualisieren.

## Schneller Entscheidungsbaum

- Engine-intern (Chunking, Ranking, Qdrant)? → **titan**, lokale Regeln.
- Ändert einen titan-Endpunkt? → Contract → titan + brain-mcp aktualisieren (+ Dashboard, falls `/health`).
- MCP-Tool-Oberfläche? → **brain-mcp**-Contract.
- Notiz-Format / `domain:`? → **systemweit** → erst Workspace-Plan.
