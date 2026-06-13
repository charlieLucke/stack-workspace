# System-Ideen

> Out-of-Scope-, Repo-übergreifende Ideen, die während der Arbeit festgehalten werden, um sie später wieder aufzugreifen.
> Single-Repo-Ideen gehören in die IDEAS.md des jeweiligen Repos. Nichts hier ist verbindliche Arbeit.

## Format
- [ ] **JJJJ-MM-TT:** Ideenbeschreibung. Welche Repos sie berühren würde. Warum sie wichtig ist. Grober Aufwand.

---

## Ausstehend

- [ ] **2026-06-02:** Read-only **Workspace-Introspektions-MCP-Server** (neues Repo
  `workspace-mcp`). Stellt das System einem Planungs-Chat bereit (Opus, über das bestehende
  Connector-Pattern): `get_system_map`, `get_routing`, `get_contract` / `list_contracts`,
  `dependency_graph`, `read_repo_file` (gescopt, read-only), `contract_drift`.
  **Warum:** schließt die `PLANNING.md`-Lücke, wo Opus in einem reinen Chat das Repo nicht lesen kann
  (heute fügt man Dateien von Hand ein). **Scope:** nur read-only — kein Scaffold/Check/Commit
  über einen öffentlichen Connector (Security). **Berührt:** neues Repo; verwendet `scripts/manifest.py` wieder.
  **Aufwand:** ~ein Nachmittag, kleiner als brain-mcp (keine Vektor-DB / GPU). **Tun, wenn:** du
  die Reibung des Datei-Einfügens in Planungs-Chats tatsächlich spürst — nicht vorher (Gold-Plating).

- [ ] **2026-06-02:** **Startup-Reconcile für den Vault-Index.** Nach einem Kaltstart werden Notizen,
  die editiert wurden, während brain-watcher *unten* war, nie neu indexiert — es ist ein Live-only-watchdog-
  Observer ohne Baseline-Catch-up (`brain-mcp/src/brain_mcp/watcher.py` `start()` macht keinen
  Scan; `PollingObserver` snapshottet beim Start und emittiert nur spätere Events). Ein Reconcile-Pass beim
  Start sollte den Vault gegen titans Index diffen und **nur das Delta** neu-ingesten.
  **Berührt (repo-übergreifend):** brain-mcp (die Reconcile-Schleife in brain-watcher — die Hauptarbeit)
  **und** titan (Enabling-Teil: einen Per-Notiz-Content-Hash oder mtime in `GET /notes` bereitstellen, sodass der
  Watcher Drift günstig erkennt, ohne jede Datei neu zu lesen). **Warum:** Edits während der
  Stack unten ist, bleiben still veraltet im Index — heute getroffen (die neuen Vault-Notizen indexieren sich beim Neustart nicht
  automatisch; sie brauchen ein manuelles `touch`/`ingest_note`). **Landing-Reihenfolge:** titan
  zuerst (additiver Hash in `/notes` = Contract-Änderung), dann konsumiert brain-mcp ihn.
  **Aufwand:** klein–mittel.
