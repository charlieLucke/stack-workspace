# System-Entscheidungs-Log

> Architecture Decision Records nur für **Repo-übergreifende** Entscheidungen. Entscheidungen über die
> Interna eines einzelnen Repos gehören in dessen `docs/ai/DECISIONS.md`. Nur anhängen.

## Format

```
## JJJJ-MM-TT: Kurztitel
**Entscheidung:** Was wir entschieden haben
**Begründung:** Warum
**Erwogene Alternativen:** Was wir verworfen haben und warum
**Konsequenzen:** Was das für die Zukunft bedeutet
```

---

## Anfangsentscheidungen (Template-Defaults)

## 2026-XX-XX: Multi-Repo statt Monorepo
**Entscheidung:** Das System ist ein Satz unabhängiger Repos, durch Contracts verbunden, koordiniert von
diesem Workspace-Meta-Repo — kein einzelnes Monorepo.
**Begründung:** Services deployen und versionieren unabhängig; jedes bleibt eigenständig lauffähig und
klein genug, dass ein Agent es im Kontext halten kann; Grenzen werden durch Contracts erzwungen, nicht
durch Konvention.
**Erwogene Alternativen:** Monorepo (einfacheres Repo-übergreifendes Refactoring, aber koppelt Deploys und
verwischt Eigentümerschaft). Git-Submodule (reproduzierbar, aber schmerzhafte UX; Agenten stolpern über Detached
HEAD).
**Konsequenzen:** Repos werden über das `repos.yaml`-Manifest nach `repos/` (gitignored) geklont.
Repo-übergreifende Koordination läuft über Contracts, Workspace-Pläne und `workspace.sh`.

## 2026-XX-XX: Contracts sind die einzige Kopplung
**Entscheidung:** Repos dürfen nur über Schnittstellen voneinander abhängen, die in
`docs/ai/CONTRACTS.md` + `contracts/` festgehalten sind. Kein Hineingreifen in die Interna eines anderen Repos.
**Begründung:** Hält Repos austauschbar und unabhängig testbar; macht Brüche erkennbar
(`workspace.sh contracts`) statt still.
**Konsequenzen:** Jede veröffentlichte Schnittstelle braucht einen Contract-Eintrag; Contract-Änderungen sind
Opus-Ebene und müssen alle Konsumenten aktualisieren.

## 2026-XX-XX: Jeder Service wird aus dem Single-Repo-Template gebaut
**Entscheidung:** Neue Services werden aus `charlieLucke/python-template` via
`./workspace.sh new` gescaffoldet und erben uv + ruff + mypy-strict + pytest + pre-commit + CI und den
`docs/ai/`-Workflow.
**Begründung:** Ein Satz Konventionen und ein Quality-Gate pro Repo; der Workspace ergänzt nur
die Systemschicht obendrauf, statt Per-Repo-Tooling neu zu erfinden.
**Konsequenzen:** Per-Repo-Konventionen leben in `shared/` und werden hereingezogen, nicht von Hand kopiert.

## 2026-06-02: Neuer Service `workspace-mcp` für Design-Zeit-Introspektion
**Entscheidung:** Wir führen ein neues Repository/Service `workspace-mcp` ein, das als read-only MCP-Server dient und die Struktur, Konfiguration und den Code des Workspace-Meta-Repos bereitstellt.
**Begründung:** Um Planungs-Agenten (wie Opus) zu erlauben, die Workspace-Struktur, Routing, Contracts und Repository-Code zu inspizieren, ohne manuelles Copy-Pasting. Es läuft nur zur Design-Zeit, getrennt vom RAG-Runtime-Pfad, und hält die RAG-Services sauber und entkoppelt.
**Erwogene Alternativen:** Die Workspace-Tools in `brain-mcp` zu legen (verworfen, weil `brain-mcp` das Runtime-Vault-RAG behandelt und keine Workspace-Level-Entwicklungs-/Introspektions-Fähigkeiten enthalten sollte; anderer Lebenszyklus/Deployment-Takt).
**Konsequenzen:** Ein neuer Service wird in `repos.yaml` auf Port 9300 registriert. Er muss eine strikte Read-Only-Grenze erzwingen, um Remote-Code-Execution oder unautorisierte Repository-Mutationen zu vermeiden.

## 2026-10-24: titan-Contract additiv um `kompakt` erweitert; Late Chunking aus
**Entscheidung:** `POST /search` nimmt zusätzlich `kompakt` (Default `false`) und
`kompakt_zeichen` (Default 600). Additiv: Ein Aufrufer, der die Felder nicht kennt,
bekommt dieselbe Antwort wie vorher. brain-mcp nutzt sie vorerst nicht. Unabhängig
davon bettet titan seit demselben Tag jeden Chunk einzeln mit Kopfzeile ein statt per
Late Chunking — eine titan-interne Entscheidung (ROUTING: Maschineninternes), hier nur
vermerkt, weil sie die Trefferqualität des Connectors bestimmt.
**Begründung:** Gemessen in titan mit einem Goldset von 196 Fragen
(`titan.eval.vault_eval`): Die richtige Stelle unter den ersten fünf Treffern stieg von
38 % auf 81 %. Mit dieser Quote reicht der Connector-Default `top_k = 5`, und `kompakt`
ist eine Option zum Sparen, kein Ausgleich mehr. Details in
`repos/titan/docs/ai/DECISIONS.md`.
**Konsequenzen:** Wer `kompakt` in brain-mcp einschaltet, kauft rund 45 % weniger
Tokens je Suche gegen 2 bis 3 Punkte Trefferquote und ~300 ms Latenz; das ist eine
eigene Entscheidung, noch nicht getroffen.
