# Aktuelle Repo-übergreifende Aufgabe

> Nur für Features, die mehr als ein Repo überspannen. Single-Repo-Arbeit wird in der
> eigenen CURRENT_TASK.md des jeweiligen Repos getrackt. Kurz halten.

## Ziel
Einen einmaligen Startup-Reconcile-Pass in brain-watcher (brain-mcp) implementieren, der den Vault gegen titans Index diffed und nur das Delta neu-ingestet/löscht, wobei content_hash als Drift-Signal genutzt wird.

## Workspace-Plan
[2026-06-02_vault-index-startup-reconcile.md](file:///home/charl/projects/rag-workspace/docs/ai/plans/2026-06-02_vault-index-startup-reconcile.md)

## Per-Repo-Teilschritte (in Landing-Reihenfolge: Provider vor Konsumenten)
- [x] repos/titan — `content_hash`-Payload-Key beim Ingest + auf GET `/notes` und GET `/domains/{domain}/notes` bereitstellen (+ Contract aktualisieren)
- [x] repos/brain-mcp — `content_hash` im Schema spiegeln, `_reconcile()` implementieren, beim Start aufrufen und Tests ergänzen

## Contract-Checkliste
- [x] contracts/ aktualisiert
- [x] CONTRACTS.md aktualisiert
- [x] alle Konsumenten aktualisiert
- [x] `./workspace.sh contracts` grün

## Blocker
Keine. Das Feature ist vollständig gelandet, verifiziert, committet, und `./workspace.sh check` ist grün.
