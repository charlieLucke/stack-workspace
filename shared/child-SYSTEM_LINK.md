# SYSTEM_LINK — dieses Repo ist Teil eines Systems

> Wird von `./workspace.sh new` als `docs/ai/SYSTEM_LINK.md` in jedes Child-Repo abgelegt und
> von `./workspace.sh sync-shared` synchron gehalten. Es teilt einem Agenten, der *innerhalb*
> dieses Repos arbeitet, mit, dass es zu einem größeren System gehört und wo das System-Hirn liegt.

## Dieses Repo
- **Service-Name:** <name>
- **Rolle:** <Verantwortung in einer Zeile>
- **Konsumiert:** <andere Services, die dieses Repo per Contract aufruft>
- **Stellt bereit:** <Contract, den dieses Repo veröffentlicht>
- **Port (lokal):** <Port oder —>

## Wo das System-Hirn liegt
Das koordinierende Workspace-Repo hält das Repo-übergreifende Gesamtbild:
- Systemkarte & Abhängigkeitsgraph → Workspace `docs/ai/SYSTEM.md`
- Welches Repo was besitzt → Workspace `docs/ai/ROUTING.md`
- Die Contracts, die dieses Repo einhalten muss → Workspace `docs/ai/CONTRACTS.md` + `contracts/`
- Repo-übergreifende Entscheidungen → Workspace `docs/ai/DECISIONS.md`

## Regeln, die nichts überschreiben, aber eine Sache ergänzen
Folge für alle lokale Arbeit der eigenen `CLAUDE.md` dieses Repos. Die einzige Ergänzung daraus,
Teil eines Systems zu sein: **eine Änderung an der Grenze dieses Repos (seinem exponierten Contract)
ist eine Entscheidung auf Workspace-Ebene** — anhalten und ansprechen, statt das Interface hier zu ändern.

<!-- SHARED-AGENT-RULES:START (synced from workspace shared/agent-rules.md — do not edit here) -->
<!-- SHARED-AGENT-RULES:END -->
