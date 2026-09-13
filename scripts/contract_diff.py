#!/usr/bin/env python3
"""Compare a committed OpenAPI contract against a service's live spec.

Detects *drift*: operations (METHOD + path) that exist in one but not the other. This
catches the classic multi-repo failure - a provider changes an endpoint and the committed
contract (which consumers rely on) silently falls out of sync.

Usage:
  contract_diff.py <committed-contract> <live-source>

  <committed-contract>  Path to the contract file (.yaml/.yml/.json).
  <live-source>         An http(s) URL serving the live OpenAPI JSON
                        (e.g. http://127.0.0.1:8765/openapi.json) or a local file path.

Exit codes: 0 = in sync, 1 = drift detected, 2 = could not check (skipped).

Notes:
  - Parsing committed YAML needs PyYAML. If it is absent and the contract is YAML, the
    check is skipped (exit 2) rather than failing. JSON contracts need no extra dependency.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

HTTP_METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}


def _load_spec_text(text: str, is_yaml: bool) -> dict[str, Any] | None:
    if not is_yaml:
        return json.loads(text)
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return None
    data = yaml.safe_load(text)
    return data if isinstance(data, dict) else {}


def _load_committed(path: Path) -> dict[str, Any] | None:
    is_yaml = path.suffix.lower() in (".yaml", ".yml")
    return _load_spec_text(path.read_text(encoding="utf-8"), is_yaml)


def _load_live(source: str) -> dict[str, Any]:
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=5) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    p = Path(source)
    spec = _load_spec_text(
        p.read_text(encoding="utf-8"), p.suffix.lower() in (".yaml", ".yml")
    )
    if spec is None:
        raise RuntimeError("live source is YAML but PyYAML is unavailable")
    return spec


def operations(spec: dict[str, Any]) -> set[str]:
    """Return the set of METHOD /path operations defined in an OpenAPI spec."""
    ops: set[str] = set()
    for path, item in (spec.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method in item:
            if method.lower() in HTTP_METHODS:
                ops.add(f"{method.upper()} {path}")
    return ops


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    contract_path, live_source = Path(argv[0]), argv[1]

    committed = _load_committed(contract_path)
    if committed is None:
        print(f"  SKIP {contract_path.name}: YAML contract but PyYAML not installed")
        return 2
    try:
        live = _load_live(live_source)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"  SKIP {contract_path.name}: live source unreachable ({exc})")
        return 2

    committed_ops, live_ops = operations(committed), operations(live)
    missing = sorted(committed_ops - live_ops)
    added = sorted(live_ops - committed_ops)

    if not missing and not added:
        print(
            f"  OK {contract_path.name}: {len(committed_ops)} operations match the live service"
        )
        return 0

    print(f"  DRIFT {contract_path.name}:")
    for op in missing:
        print(f"    - {op}   (in contract, missing from service)")
    for op in added:
        print(f"    + {op}   (in service, not in contract)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
