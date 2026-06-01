#!/usr/bin/env python3
"""Link an existing child repo into the system.

For one service it: (1) generates docs/ai/SYSTEM_LINK.md from
shared/child-SYSTEM_LINK.md, filling role/consumes/exposes/port from repos.yaml and
injecting shared/agent-rules.md; (2) adds a single 'read SYSTEM_LINK.md' line to the
child's CLAUDE.md / AGENTS.md / GEMINI.md under 'Read These First'. Idempotent.

Usage: adopt.py <repo_path> <service_name>   (run from the workspace root)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import manifest  # sibling module in scripts/

READ_LINE = "`docs/ai/SYSTEM_LINK.md` — if this repo is part of a larger system, read it first"
START = "<!-- SHARED-AGENT-RULES:START"
END = "<!-- SHARED-AGENT-RULES:END -->"


def _fill_system_link(name: str, role: str, consumes: str, exposes: str, port: str) -> str:
    tmpl = Path("shared/child-SYSTEM_LINK.md").read_text(encoding="utf-8")
    repl = {
        "<name>": name,
        "<one-line responsibility>": role or "—",
        "<other services this repo calls, by contract>": consumes or "—",
        "<contract this repo publishes>": exposes or "—",
        "<port or n/a>": port or "n/a",
    }
    for k, v in repl.items():
        tmpl = tmpl.replace(k, v)
    # inject the shared agent-rules block
    block = Path("shared/agent-rules.md").read_text(encoding="utf-8").strip()
    new = (
        f"{START} (synced from workspace shared/agent-rules.md — do not edit here) -->\n\n"
        f"{block}\n\n{END}"
    )
    if START in tmpl and END in tmpl:
        tmpl = re.sub(re.escape(START) + r".*?" + re.escape(END), new, tmpl, flags=re.S)
    return tmpl


def _patch_read_first(path: Path) -> bool:
    """Add the SYSTEM_LINK read-line under 'Read These First'. Returns True if changed."""
    text = path.read_text(encoding="utf-8")
    if "SYSTEM_LINK.md" in text:
        return False  # already linked
    lines = text.splitlines()
    # find the 'Read These First' heading
    head = next((i for i, ln in enumerate(lines) if "Read These First" in ln), None)
    if head is None:
        return False
    # find the contiguous numbered list after the heading
    item = re.compile(r"^(\s*)(\d+)\.\s")
    last, last_num, indent = None, 0, ""
    for i in range(head + 1, len(lines)):
        m = item.match(lines[i])
        if m:
            last, last_num, indent = i, int(m.group(2)), m.group(1)
        elif last is not None and lines[i].strip() == "":
            break  # list ended
    if last is None:
        return False
    lines.insert(last + 1, f"{indent}{last_num + 1}. {READ_LINE}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    repo_path, name = Path(argv[0]), argv[1]
    data = manifest.load()
    svc = next((s for s in manifest._services(data) if s.get("name") == name), None)
    if svc is None:
        print(f"adopt: no service named {name!r} in repos.yaml", file=sys.stderr)
        return 1

    consumes = ", ".join(manifest._consumes(svc))
    content = _fill_system_link(
        name,
        str(svc.get("role", "")),
        consumes,
        str(svc.get("exposes") or ""),
        "" if svc.get("port") in (None, "null") else str(svc.get("port")),
    )
    target = repo_path / "docs" / "ai" / "SYSTEM_LINK.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    existed = target.exists()
    target.write_text(content, encoding="utf-8")
    print(f"  {'updated' if existed else 'created'} {target}")

    for fname in ("CLAUDE.md", "AGENTS.md", "GEMINI.md"):
        f = repo_path / fname
        if f.exists() and _patch_read_first(f):
            print(f"  linked {f} (added SYSTEM_LINK read-line)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
