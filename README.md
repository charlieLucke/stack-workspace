# stack-workspace

Die Koordinationsschicht über den Repos, die ich betreibe: ein lokaler RAG-Stack, die
Werkzeuge rund um die Kundenarbeit und die eine Bedienoberfläche (homebase), die nach
und nach vor alles davon tritt.

> Umbenannt von `rag-workspace` am 04.09.2026. Der alte Name beschrieb, was hier
> zufällig zuerst lag. Ein Workspace ist eine **Entwicklungs**-Koordinationsschicht,
> keine Deployment-Einheit — es spricht nichts dagegen, dass lokal laufende und
> anderswo laufende Dienste darin stehen.


## Was das ist

Ein System wird aus **unabhängigen Service-Repos** gebaut, die nur durch explizite
**Contracts** verbunden sind (HTTP-APIs, Message-Schemas). Jedes Repo ist eigenständig lauffähig und besitzt
seine eigenen Tests, CI und `docs/ai/`. Dieser Workspace ergänzt die Schicht, die kein einzelnes Repo
halten kann:

| Schicht | Lebt in | Besitzt |
|-------|----------|------|
| **System** | dieses Repo | Architektur über Repos hinweg, Contracts, Repo-übergreifende Pläne/Handoff, gemeinsame Konventionen, System-Quality-Gate |
| **Service** | `repos/<name>/` | eine abgegrenzte Verantwortung, eigener Code/Tests/CI und lokales `docs/ai/` |

## Aufbau

```
repos.yaml            Manifest: jeder Service, seine Rolle, Contracts, Abhängigkeitskanten
workspace.sh          clone-all · sync · for-each · check · new · contracts
init-workspace.sh     Einmalig: Platzhalter füllen, git init, Selbstlöschung
docs/ai/              System-Level-Agenten-Hirn (siehe unten)
  SYSTEM.md           Die Karte: alle Services, Abhängigkeitsgraph, End-to-end-Datenfluss
  ROUTING.md          „Welches Repo besitzt was / wo eine Änderung machen"
  CONTRACTS.md        Menschliche Source-of-Truth für Inter-Service-APIs
  DECISIONS.md        Nur Repo-übergreifende ADRs (Per-Repo-Entscheidungen bleiben lokal)
  CURRENT_TASK.md     Das aktive Feature, das Repos überspannt
  HANDOFF.md          System-Handoff: welche Repos bei welchem Commit
  IDEAS.md            Parkplatz
  plans/              Opus-erstellte Pläne, die mehrere Repos koordinieren
contracts/            Maschinenlesbare Contracts (OpenAPI, JSON Schema, …)
shared/               DRY-Konventionsfragmente, in jedes Child-Repo gezogen
repos/                Geklonte Child-Repos (gitignored, jedes ein eigenes git-Repo)
.github/workflows/    Orchestrierende CI: Per-Repo-Check + Contract-Verify + Smoke
examples/rag-system/  Ein vollständig ausgefülltes Beispielsystem
```

## Befehle

```bash
./workspace.sh clone            # jeden Service aus repos.yaml nach repos/ klonen
./workspace.sh sync             # git pull --ff-only für jeden Service
./workspace.sh status           # kurzer git-Status jedes Service
./workspace.sh new <name> <desc># einen neuen Service aus dem Template scaffolden + registrieren
./workspace.sh foreach '<cmd>'  # einen Shell-Befehl in jedem Service-Repo ausführen
./workspace.sh check            # Per-Repo-`make check` + Contract-Verify (das Gate)
./workspace.sh contracts        # prüfen, ob jeder Service noch zu seinem veröffentlichten Contract passt
./workspace.sh lock             # repos.lock schreiben, das jeden Service auf seinen HEAD-Commit pinnt
./workspace.sh graph            # den Abhängigkeitsgraphen aus repos.yaml ausgeben
```

## Arbeiten mit KI-Tools

Zuerst `CLAUDE.md` lesen (gespiegelt als `AGENTS.md` / `GEMINI.md`). Sie definiert die
**Multi-Repo-Betriebsregeln**, die über den eigenen Agenten-Regeln jedes Child-Repos liegen:
Locate-before-editing via `ROUTING.md`, Contracts-are-Law, One-Feature-One-Plan und
das System-Quality-Gate. Child-Repos behalten ihre eigene `CLAUDE.md` für lokale Arbeit.

## Lizenz

MIT — siehe [LICENSE](LICENSE).
