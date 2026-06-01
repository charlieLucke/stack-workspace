#!/usr/bin/env python3
"""Read repos.yaml and answer queries for workspace.sh.

Pure standard library. Uses PyYAML if it happens to be installed, otherwise falls
back to a tiny parser that understands exactly the subset of YAML this template's
repos.yaml uses (top-level scalars, a `defaults`/`template` mapping, and a
`services:` list of mappings whose values are scalars or inline `[a, b]` lists).

Subcommands (all read repos.yaml in the current working directory):
  names                 -> one service name per line
  url <name>            -> clone URL (expands short names via defaults)
  path <name>           -> checkout path under repos/
  field <name> <key>    -> a single field value ("" if unset)
  consumers <name>      -> names of services that list <name> in `consumes`
  consumes <name>       -> names of services that <name> lists in `consumes`
  graph                 -> "consumer -> provider" edges, one per line
  template-url          -> the single-repo template clone URL
  defaults <key>        -> a value from the `defaults` mapping
  check                 -> validate the manifest; exit non-zero with errors
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def _strip(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
        value = value[1:-1]
    return value


def _scalar(value: str) -> Any:
    value = value.strip()
    if value in ("", "null", "~", "[]"):
        return [] if value == "[]" else None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [_strip(x) for x in inner.split(",")] if inner else []
    return _strip(value)


def _fallback_load(text: str) -> dict[str, Any]:
    """Parse the narrow repos.yaml subset without PyYAML."""
    root: dict[str, Any] = {}
    cur_map: dict[str, Any] | None = None  # active top-level mapping (defaults/template)
    services: list[dict[str, Any]] = []
    cur_svc: dict[str, Any] | None = None
    in_services = False

    for raw in text.splitlines():
        line = raw.split(" #")[0].rstrip() if " #" in raw else raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0:
            in_services = False
            cur_map = None
            cur_svc = None
            if stripped.endswith(":"):
                key = stripped[:-1].strip()
                if key == "services":
                    in_services = True
                else:
                    cur_map = {}
                    root[key] = cur_map
            elif ":" in stripped:
                key, _, val = stripped.partition(":")
                root[key.strip()] = _scalar(val)
            continue

        if in_services:
            if stripped.startswith("- "):
                cur_svc = {}
                services.append(cur_svc)
                stripped = stripped[2:].strip()
                if not stripped:
                    continue
            if cur_svc is not None and ":" in stripped:
                key, _, val = stripped.partition(":")
                cur_svc[key.strip()] = _scalar(val)
            continue

        if cur_map is not None and ":" in stripped:
            key, _, val = stripped.partition(":")
            cur_map[key.strip()] = _scalar(val)

    root["services"] = services
    return root


def load() -> dict[str, Any]:
    text = Path("repos.yaml").read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore[import-untyped]

        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except ImportError:
        return _fallback_load(text)


def _services(data: dict[str, Any]) -> list[dict[str, Any]]:
    svcs = data.get("services") or []
    return [s for s in svcs if isinstance(s, dict) and s.get("name")]


def _find(data: dict[str, Any], name: str) -> dict[str, Any]:
    for s in _services(data):
        if s.get("name") == name:
            return s
    raise SystemExit(f"manifest: no service named {name!r}")


def _url(data: dict[str, Any], svc: dict[str, Any]) -> str:
    if svc.get("url"):
        return str(svc["url"])
    d = data.get("defaults") or {}
    host = d.get("host", "github.com")
    owner = d.get("owner", "")
    return f"https://{host}/{owner}/{svc['name']}.git"


def _consumes(svc: dict[str, Any]) -> list[str]:
    c = svc.get("consumes") or []
    if isinstance(c, str):
        return [c]
    return [str(x) for x in c]


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    data = load()
    cmd, args = argv[0], argv[1:]

    if cmd == "names":
        for s in _services(data):
            print(s["name"])
    elif cmd == "url":
        print(_url(data, _find(data, args[0])))
    elif cmd == "path":
        s = _find(data, args[0])
        print(s.get("path") or f"repos/{s['name']}")
    elif cmd == "field":
        print(_find(data, args[0]).get(args[1], "") or "")
    elif cmd == "consumers":
        target = args[0]
        for s in _services(data):
            if target in _consumes(s):
                print(s["name"])
    elif cmd == "consumes":
        for provider in _consumes(_find(data, args[0])):
            print(provider)
    elif cmd == "graph":
        for s in _services(data):
            for provider in _consumes(s):
                print(f"{s['name']} -> {provider}")
    elif cmd == "template-url":
        print((data.get("template") or {}).get("url", ""))
    elif cmd == "defaults":
        print((data.get("defaults") or {}).get(args[0], "") or "")
    elif cmd == "check":
        names = {s["name"] for s in _services(data)}
        errors: list[str] = []
        for s in _services(data):
            for provider in _consumes(s):
                if provider not in names:
                    errors.append(f"{s['name']} consumes unknown service {provider!r}")
        if not data.get("system"):
            errors.append("manifest has no `system:` name")
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1 if errors else 0
    else:
        print(f"manifest: unknown query {cmd!r}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
