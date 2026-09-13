# Gemeinsame Konventionen

> Die Konventionen, die über jeden Service in `stack-workspace` hinweg identisch sein
> müssen. Die `docs/ai/CONTEXT.md` jedes Child-Repos soll „Konventionen: siehe Workspace
> `shared/conventions.md`" sagen, statt sie zu kopieren — damit es eine einzige Wahrheit
> gibt. Nur hier bearbeiten.

## Stack (jeder Service)
- **Sprache:** Python 3.12+
- **Paketmanager:** uv (`uv add` / `uv remove`, niemals die Abhängigkeiten in `pyproject` von Hand editieren)
- **Lint/Format:** ruff — Zeilenlänge 100, doppelte Anführungszeichen (siehe `shared/ruff.toml`)
- **Typprüfer:** mypy strict
- **Tests:** pytest mit Coverage
- **CI:** GitHub Actions je Repo plus die System-CI hier
- **Pre-commit:** ruff, mypy, Hygiene-Prüfungen

## Regeln für Konsistenz über Service-Grenzen
- **Fehler an den Grenzen:** Services geben strukturierte Fehler zurück, niemals rohe
  Tracebacks über einen Contract hinweg. Jedes Repo bildet interne Ausnahmen auf die
  Fehlerform seines Contracts ab.
- **Logging:** stdlib `logging`, strukturiert dort, wo es eine Grenze überschreitet;
  niemals `print()`.
- **Bezeichner:** IDs, die zwischen Services reisen, werden einmal im Contract definiert
  und lokal nie umgedeutet.
- **Zeit:** UTC überall auf der Leitung; lokalisiert wird erst am Rand.
- **Versionierung:** additive Contract-Änderungen sind rückwärtskompatibel; Entfernungen
  brauchen eine Migration, die beim Konsumenten beginnt und in einem Workspace-Plan
  festgehalten ist.

## Commit- und Branch-Konventionen (jedes Repo)
- Commit-Format: `<typ>: <betreff>` (feat, fix, refactor, test, docs, chore), Imperativ.
- Eine logische Änderung pro Commit; niemals eine Contract-Änderung mit unbeteiligtem
  Refactoring mischen.
