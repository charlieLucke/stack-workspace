# Gemeinsame Agenten-Regeln

> Kanonisches Konventionsfragment. Die `CLAUDE.md` des Single-Repo-Templates trägt bereits die
> Per-Repo-Regeln; diese Datei ist das **systemweite** Delta, das jedes Child-Repo zusätzlich
> einhalten muss. `./workspace.sh sync-shared` hängt diesen Block in der `docs/ai/SYSTEM_LINK.md`
> jedes Childs an bzw. aktualisiert ihn. Bearbeite ihn **nur hier** — niemals pro Repo.

## Du bist Teil eines größeren Systems

Dieses Repo steht nicht für sich allein. Es ist ein Service in `stack-workspace`. Bevor du etwas
änderst, das ein anderes Repo beobachten kann:

- Prüfe, ob die Änderung einen **Contract** kreuzt. Falls ja — anhalten: das ist eine Entscheidung
  auf Workspace-Ebene (Opus-Ebene), keine lokale. Sprich sie an.
- Deine Inputs und Outputs an der Grenze sind in den Workspace-`contracts/` definiert.
  Behandle sie als fix, sofern ein Workspace-Plan nichts anderes sagt.
- Halte dieses Repo **eigenständig lauffähig**: importiere keinen Code eines anderen Service;
  sprich mit ihm nur über seinen Contract.

## Was lokal bleibt vs. nach oben geht

- Eine Entscheidung über die Interna *dieses* Repos → lokale `docs/ai/DECISIONS.md`.
- Eine Entscheidung darüber, wie dieses Repo mit anderen spricht → Workspace `docs/ai/DECISIONS.md`.
- Eine Out-of-Scope-Idee, die nur dieses Repo betrifft → lokale `IDEAS.md`; betrifft sie andere →
  Workspace `IDEAS.md`.

## Grenzdisziplin

- Erweitere die öffentliche Oberfläche dieses Repos nicht leichtfertig — jeder neue Endpunkt/jedes Feld ist ein Contract.
- Lies nicht direkt die Datenbank, Dateien oder Interna eines anderen Service.
- Wenn du Verhalten an der Grenze änderst, landet die Contract-Änderung *zusammen mit* dem Code,
  und jeder Konsument wird im selben Workspace-Feature aktualisiert.
