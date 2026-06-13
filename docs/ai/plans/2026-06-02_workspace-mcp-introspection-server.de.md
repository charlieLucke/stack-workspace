# Plan: `workspace-mcp` — read-only Workspace-Introspektions-MCP-Server (NEUES REPO)

- **Datum:** 2026-06-02
- **Autor:** Opus (Planung)
- **Implementierer-Ziel:** Sonnet
- **Status:** ready
- **Verfolgt IDEAS.md:** „Read-only workspace-introspection MCP server" (2026-06-02)

## Ziel
Ein kleiner **read-only** MCP-Server, der das *Workspace-Meta-Repo selbst* bereitstellt — Systemkarte,
Routing, Contracts, Abhängigkeitsgraph, gescopte File-Reads — für einen Planungs-Chat. Er schließt die Lücke,
die `PLANNING.md` explizit benennt („Kein Repo-Zugriff? ... bitte den Nutzer, die Dateien einzufügen"): ein
Planungsmodell (Opus, über dasselbe Connector-Pattern, das brain-mcp bereits nutzt) kann dann **das
System direkt lesen**, statt dass du `SYSTEM.md`/`ROUTING.md`/`CONTRACTS.md`/Code von Hand einfügst.

Das ist ein **neuer Service**, kein Edit an einem bestehenden Repo (siehe „Warum ein neues Repo").

## Warum das ein Plan auf Workspace-Ebene ist
Es erstellt eine **neue Modulgrenze** — selbst eine Entscheidung auf Workspace-Ebene (in
`docs/ai/DECISIONS.md` festhalten) — und registriert einen neuen Knoten in `repos.yaml` + `SYSTEM.md` + `ROUTING.md`.

## Warum ein neues Repo (kein Modul in brain-mcp)
Andere abgegrenzte Verantwortung und Lebenszyklus:
- **brain-mcp** liefert die *Vault-Inhalte* an Claude für Q&A zur **Runtime**.
- **workspace-mcp** liefert das *Workspace-Meta-Repo* (Docs, Manifest, Contracts) an einen *Planungs*-
  Chat zur **Design-Zeit**. Es besitzt keinen Vault, kein Qdrant, keine GPU; es deployt/released im eigenen
  Takt und wäre peinlich, an die RAG-Runtime gekoppelt zu sein.
Sie teilen ein Transport-*Pattern*, kein Deployment. Unabhängiger Lebenszyklus ⇒ neues Repo. (Auch die
gegenteilige Falle widerstehend: es ist tatsächlich ein separates Anliegen, nicht „brain-mcp, aber größer".)

## Betroffene Repos & Landing-Reihenfolge
Ein neuer Provider, den **nichts sonst konsumiert**, also landet er einfach und wird für sich grün:
1. Workspace: Repo scaffolden + registrieren, seinen Contract entwerfen, die Entscheidung festhalten.
2. `repos/workspace-mcp`: den read-only-Server + Tests implementieren.

Kein bestehendes Repo ändert sich. (titan wird nur *optional* für das Drift-Tool gelesen — siehe Stretch.)

## Bereits getroffene Entscheidungen — NICHT neu entscheiden

### Read-only ist eine harte Security-Grenze
- **Nur Read-Tools.** Niemals `new`/`adopt`/`check`/`commit`/Scaffold-/Shell-Mutations-Tools.
  Dieser Server soll über den **gleichen öffentlichen Pfad wie brain-mcp** erreichbar sein (Tailscale-
  Funnel + GitHub-OAuth-Allowlist). Ein öffentlicher Connector, der das Repo schreiben oder beliebige
  Befehle ausführen kann, ist inakzeptabel. Jedes Tool ist ein reiner Read.
- **Auth + Transport spiegeln brain-mcp exakt.** Das Pattern in
  `repos/brain-mcp/src/brain_mcp/{mcp_server.py,auth.py,config.py}` wiederverwenden: `FastMCP`,
  `OAuthProxy` via einen `build_github_auth`-Helper, `GitHubAllowlistVerifier`, eine pydantic-settings-
  `Settings` mit Env-Präfix `WORKSPACE_`, und ein `main()`, das zwischen `stdio`/`http`-Transport umschaltet.
  auth.py (~30 Zeilen) ins neue Repo kopieren — Repos bleiben entkoppelt (gleiche Begründung wie brain-mcps
  lokale Schema-Kopie); in einem Kommentar notieren, dass es `brain-mcp/auth.py` spiegelt.
- **Port 9300.** 8765 (titan), 9100 (brain-mcp), 9200 (Dashboard) sind belegt; 9300 ist frei.

### Konfiguration
- `WORKSPACE_ROOT: Path` — der Workspace-Meta-Repo-Root (das Verzeichnis, das `repos.yaml` enthält).
  Default: vom Paket aus aufwärts auflösen oder eine Env-Var akzeptieren; im Deployment zeigt es auf
  `~/projects/rag-workspace`. **Aller Dateizugriff wurzelt hier.**
- Die Standard-brain-mcp-Auth/Transport-Settings wiederverwenden (`WORKSPACE_MCP_TRANSPORT`,
  `_HOST`, `_PORT`, `_MCP_AUTH`, `_MCP_BASE_URL`, `WORKSPACE_GITHUB_CLIENT_ID/_SECRET/_ALLOWED_LOGINS`).

### `scripts/manifest.py` wiederverwenden (Manifest-Logik nicht duplizieren)
- Für Graph/Konsumenten/Namen **shellen** zum eigenen Skript des Workspaces:
  `python3 {WORKSPACE_ROOT}/scripts/manifest.py <subcommand>` (z. B. `graph`, `names`,
  `consumers <name>`). Das verwendet die echte, getestete Logik wieder, statt YAML neu zu parsen.
- Für Doc-/Contract-**Inhalte** die Dateien direkt lesen (`WORKSPACE_ROOT/docs/ai/*.md`,
  `WORKSPACE_ROOT/contracts/*`). Sie sind Plain Text.

### `read_repo_file` ist das eine Tool mit Angriffsfläche — die Sandbox festnageln
- Signatur: `read_repo_file(repo: str, relpath: str) -> str`.
- `repo` muss einer der Service-Namen des Manifests sein (sonst ablehnen).
- `base = (WORKSPACE_ROOT/"repos"/repo).resolve()` auflösen (das folgt dem Symlink zum echten
  Repo) und `target = (base / relpath).resolve()`; **ablehnen**, außer `target.is_relative_to(base)`
  (blockiert `..`/absolute Escapes — titans `_path_check` spiegeln, routes.py:202).
- Read-only; Nicht-Dateien verweigern; auf eine vernünftige Größe deckeln (z. B. 200 KB) und nur Text zurückgeben.

### Tool-Set (final, alle read-only)
1. `list_repos()` → Service-Namen + Rollen (aus `manifest.py names` + `field <name> role`).
2. `get_system_map()` → `docs/ai/SYSTEM.md`.
3. `get_routing()` → `docs/ai/ROUTING.md`.
4. `get_contracts_overview()` → `docs/ai/CONTRACTS.md`.
5. `list_contracts()` → Dateinamen in `contracts/`.
6. `get_contract(name)` → Inhalt von `contracts/<name>` (auf das `contracts/`-Verzeichnis gesandboxt).
7. `dependency_graph()` → Ausgabe von `manifest.py graph` (Konsument → Provider-Kanten).
8. `read_repo_file(repo, relpath)` → gescopter Read (oben).
9. **(Stretch, optional)** `contract_drift(service)` → `scripts/contract_diff.py` gegen die
   Live-Spec des Service shellen; gibt in-sync / drift / skipped zurück. Braucht den laufenden Service, also
   klar als Best-Effort markieren und nur shippen, wenn Stage 2 Platz hat.

## Schritte

### Stage 1 — Scaffold, Contract, Registrierung (Workspace)
1. `./workspace.sh new workspace-mcp "Read-only MCP server exposing the workspace to planning chats"`
   — scaffoldet aus `charlieLucke/python-template` nach `repos/workspace-mcp`.
2. **Zuerst den Contract entwerfen** (Grenze vor Code):
   - `contracts/workspace-mcp.tools.json` erstellen, das die Form von
     `contracts/brain-mcp.tools.json` spiegelt — jeden Tool-Namen + eine Einzeiler-Beschreibung + Args auflisten.
   - Einen Abschnitt **„Contract: workspace-mcp MCP-Tools"** zu `docs/ai/CONTRACTS.md` hinzufügen
     (Provider: repos/workspace-mcp; Konsument: ein Planungs-Chat über den Connector; Transport: MCP
     über HTTP `:9300`, GitHub-OAuth-gegatet; Invariante: **read-only**).
3. In `repos.yaml` registrieren:
   ```
   - name: workspace-mcp
     role: Read-only MCP server exposing the workspace (map, routing, contracts, graph) to planning chats
     consumes: []          # liest Workspace-Dateien; keine Runtime-Abhängigkeit von anderen Services
     exposes: contracts/workspace-mcp.tools.json
     port: 9300
   ```
   (Ist das Stretch-Drift-Tool enthalten, `consumes: [titan]` setzen und notieren, dass es `/openapi.json` liest.)
4. `docs/ai/SYSTEM.md` aktualisieren: workspace-mcp zur Services-Tabelle hinzufügen und eine Einzeiler-Notiz im
   Graph-/Datenfluss-Abschnitt (es sitzt *neben* dem Runtime-Graphen — ein Design-Zeit-Leser des Repos,
   nicht im Datenpfad; das explizit sagen, damit es nicht für eine Runtime-Abhängigkeit gehalten wird).
5. `docs/ai/ROUTING.md` aktualisieren: eine Zeile ergänzen — „Planungszeit-Introspektion / den Workspace
   einem Planungs-Chat bereitstellen → **workspace-mcp**".
6. `./workspace.sh adopt workspace-mcp` — legt `repos/workspace-mcp/docs/ai/SYSTEM_LINK.md` ab und
   patcht sein CLAUDE/AGENTS/GEMINI „Read These First".
7. Die Entscheidung in `docs/ai/DECISIONS.md` festhalten (neue Modulgrenze: warum ein separates Repo, die
   Read-only-Einschränkung, das geteilte Connector-/Auth-Pattern).

### Stage 2 — den Server implementieren (repos/workspace-mcp)
8. `src/workspace_mcp/config.py` — `Settings(BaseSettings)` mit `env_prefix="WORKSPACE_"`:
   `workspace_root: Path`, Transport/Host/Port (Default 9300) und die GitHub-OAuth-Felder.
   `brain_mcp/config.py` spiegeln.
9. `src/workspace_mcp/auth.py` — `brain_mcp/auth.py` kopieren (`GitHubAllowlistVerifier` +
   `build_github_auth`); kommentieren, dass es brain-mcp spiegelt.
10. `src/workspace_mcp/server.py` — `FastMCP("workspace", auth=_build_auth())` (spiegelt
    `mcp_server.py:_build_auth`), plus die obigen read-only-Tools. Helper:
    - `_read(rel: str) -> str` — eine Datei unter `WORKSPACE_ROOT` lesen, via `is_relative_to` gesandboxt.
    - `_manifest(*args) -> str` — `subprocess.run([sys.executable, str(WORKSPACE_ROOT/"scripts/manifest.py"), *args], cwd=WORKSPACE_ROOT, capture_output=True, text=True, check=True)`, stdout zurückgeben.
    - Jedes Tool wickelt diese und gibt Markdown/Text zurück; bei Fehler einen kurzen `"Error: ..."`-
      String zurückgeben (brain-mcps Tool-Fehler-Stil spiegeln — nie zum Transport werfen).
11. `src/workspace_mcp/main.py` (oder `__main__`) — `main()`, das zwischen stdio/http-Transport umschaltet,
    `mcp_server.py:main` spiegeln.
12. **Tests** (`tests/`): eine `tmp_workspace`-Fixture bauen, die ein minimales `repos.yaml` + ein paar
    `docs/ai/*.md` + ein `contracts/foo.yaml` + ein Fake-`repos/<svc>/`-Verzeichnis schreibt, `WORKSPACE_ROOT` darauf
    zeigen und prüfen, dass jedes Tool den erwarteten Inhalt zurückgibt. **Erforderlich:** ein Path-Traversal-Test —
    `read_repo_file("titan", "../../secret")` und `get_contract("../config")` werden abgelehnt. Den
    Offline-/Mocked-Stil von `brain-mcp/tests/test_mcp_tools.py` spiegeln.
13. `repos/workspace-mcp/docs/ai/CONTEXT.md` knapp füllen (was das Repo ist, die Read-only-Regel).

## Tracking
Workspace-`docs/ai/CURRENT_TASK.md` → dieser Plan; `CURRENT_TASK.md` des neuen Repos → zurück darauf.
Natürlicher Handoff-Punkt: zwischen Stage 1 (Repo existiert, registriert, Contract entworfen) und Stage 2.

## Verifikation
- **Stage 1:** `repos/workspace-mcp` existiert mit Template-Tooling; `./workspace.sh status` listet es;
  `./workspace.sh check` (Manifest validiert — `workspace-mcp` vorhanden, Contract-Datei existiert) grün;
  `repos.yaml`/`SYSTEM.md`/`ROUTING.md`/`CONTRACTS.md`/`DECISIONS.md` aktualisiert.
- **Stage 2 statisch:** `cd repos/workspace-mcp && make check` (ruff + mypy-strict + pytest, inkl. der
  Tool-Tests + des Path-Traversal-Ablehnungs-Tests).
- **Stage 2 Runtime:** `workspace-mcp` über **stdio** lokal laufen lassen (`WORKSPACE_ROOT` → der Workspace)
  und die Tools durchspielen (FastMCP dev/inspector oder ein Smoke-Skript): `get_system_map`,
  `dependency_graph`, `read_repo_file("titan","README.md")` geben echten Inhalt zurück; ein `..`-Pfad wird
  verweigert. (Öffentliches HTTP-/Funnel-Deployment ist ein separater Ops-Schritt, nicht Teil dieses Plans.)
- `./workspace.sh check` insgesamt grün.

## Out of Scope
- Jede Schreib-/Mutations-Fähigkeit (Scaffold, Adopt, Commit, Run) — by design dauerhaft draußen.
- Öffentliches Funnel-/systemd-Deployment + das GitHub-OAuth-App-Setup (ein Ops-Follow-up).
- Ein Vektor-Index über die Docs / semantische Suche des Workspaces (das sind nur strukturelle Reads).
- Das Auto-Sync der Contract-JSON aus der Live-Tool-Liste (vorerst handgepflegt, wie brain-mcp).
- Das `contract_drift`-Tool, außer Stage 2 hat Platz (es ist das einzige, das einen laufenden Service braucht).

## Zu berührende Dateien (Checkliste)
**Stage 1 — Workspace**
- [ ] `repos.yaml` — neuer `workspace-mcp`-Service-Eintrag
- [ ] `contracts/workspace-mcp.tools.json` — Tool-Contract
- [ ] `docs/ai/CONTRACTS.md` — neuer Contract-Abschnitt
- [ ] `docs/ai/SYSTEM.md` — Services-Tabelle + Notiz
- [ ] `docs/ai/ROUTING.md` — Eigentümerschafts-Zeile
- [ ] `docs/ai/DECISIONS.md` — Neue-Modulgrenze-Entscheidung
- [ ] `repos/workspace-mcp/docs/ai/SYSTEM_LINK.md` — via `./workspace.sh adopt`
**Stage 2 — repos/workspace-mcp**
- [ ] `src/workspace_mcp/config.py`
- [ ] `src/workspace_mcp/auth.py`
- [ ] `src/workspace_mcp/server.py`
- [ ] `src/workspace_mcp/main.py` (Einstiegspunkt)
- [ ] `tests/` — Per-Tool-Tests + Path-Traversal-Ablehnungs-Test
- [ ] `repos/workspace-mcp/docs/ai/CONTEXT.md`
