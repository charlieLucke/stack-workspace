#!/usr/bin/env bash
# Workspace driver for a multi-repo system. Reads repos.yaml (the manifest) and
# operates over every service repo under repos/.
#
# Usage: ./workspace.sh <command> [args]
# Run with no command (or `help`) to list commands.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

MANIFEST() { python3 "$ROOT/scripts/manifest.py" "$@"; }

c_blue=$'\033[34m'; c_green=$'\033[32m'; c_red=$'\033[31m'; c_dim=$'\033[2m'; c_off=$'\033[0m'
info() { printf '%s→%s %s\n' "$c_blue" "$c_off" "$*"; }
ok()   { printf '%s✓%s %s\n' "$c_green" "$c_off" "$*"; }
err()  { printf '%s✗%s %s\n' "$c_red" "$c_off" "$*" >&2; }
hr()   { printf '%s──── %s ────%s\n' "$c_dim" "$*" "$c_off"; }

require_repo() {
  local path="$1" name="$2"
  if [ ! -d "$path/.git" ]; then
    err "repos/$name not cloned. Run: ./workspace.sh clone"
    return 1
  fi
}

cmd_clone() {  ## Clone every service in repos.yaml into repos/
  local any=0
  for name in $(MANIFEST names); do
    any=1
    local url path
    url="$(MANIFEST url "$name")"; path="$(MANIFEST path "$name")"
    if [ -d "$path/.git" ]; then
      ok "$name already present ($path)"
    else
      info "cloning $name → $path"
      git clone -q "$url" "$path" && ok "cloned $name"
    fi
  done
  [ "$any" = 1 ] || info "no services in repos.yaml yet — add some with: ./workspace.sh new <name> \"<desc>\""
}

cmd_sync() {  ## git pull --ff-only every service
  for name in $(MANIFEST names); do
    local path; path="$(MANIFEST path "$name")"
    require_repo "$path" "$name" || continue
    info "syncing $name"
    git -C "$path" pull --ff-only --quiet && ok "$name up to date" || err "$name: pull failed (diverged?)"
  done
}

cmd_status() {  ## Short git status of every service
  for name in $(MANIFEST names); do
    local path; path="$(MANIFEST path "$name")"
    if [ ! -d "$path/.git" ]; then printf '%-24s %s(not cloned)%s\n' "$name" "$c_dim" "$c_off"; continue; fi
    local branch dirty
    branch="$(git -C "$path" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
    dirty="$(git -C "$path" status --porcelain | wc -l | tr -d ' ')"
    if [ "$dirty" = 0 ]; then printf '%-24s %s%s%s clean\n' "$name" "$c_green" "$branch" "$c_off"
    else printf '%-24s %s%s%s %s uncommitted\n' "$name" "$c_red" "$branch" "$c_off" "$dirty"; fi
  done
}

cmd_foreach() {  ## Run a shell command in every service repo: foreach '<cmd>'
  [ -n "${1:-}" ] || { err "usage: ./workspace.sh foreach '<command>'"; return 2; }
  local rc=0
  for name in $(MANIFEST names); do
    local path; path="$(MANIFEST path "$name")"
    require_repo "$path" "$name" || { rc=1; continue; }
    hr "$name"
    ( cd "$path" && eval "$1" ) || { err "$name: command failed"; rc=1; }
  done
  return $rc
}

cmd_new() {  ## Scaffold a new service from the template and register it: new <name> "<desc>"
  local name="${1:-}" desc="${2:-A new service}"
  [ -n "$name" ] || { err "usage: ./workspace.sh new <name> \"<description>\""; return 2; }
  local path="repos/$name"
  [ -e "$path" ] && { err "$path already exists"; return 1; }
  local tmpl; tmpl="$(MANIFEST template-url)"
  [ -n "$tmpl" ] || { err "no template.url in repos.yaml"; return 1; }
  info "scaffolding $name from $tmpl"
  git clone -q "$tmpl" "$path"
  rm -rf "$path/.git"
  ( cd "$path" && ./init-project.sh "$name" "$desc" )
  # drop the system-link doc so the new repo knows it's part of this system
  if [ -f shared/child-SYSTEM_LINK.md ]; then
    sed "s/<name>/$name/g" shared/child-SYSTEM_LINK.md > "$path/docs/ai/SYSTEM_LINK.md"
  fi
  ( cd "$path" && git init -q -b main && git add -A && git commit -qm "chore: scaffold $name from template" )
  ok "created repos/$name"
  printf '%s\n' "Next: add it to repos.yaml under services: (name/role/consumes/exposes/port), then ./workspace.sh check"
}

cmd_adopt() {  ## Link existing child repos into the system: generate their docs/ai/SYSTEM_LINK.md
  # For repos created outside `new` (or pre-existing). Generates SYSTEM_LINK.md from the
  # manifest + shared/, and adds a 'read SYSTEM_LINK.md' line to each child's CLAUDE.md.
  # Idempotent and additive — it never touches the child's existing code. Pass a service
  # name to adopt just one; no arg adopts all.
  local only="${1:-}"
  for name in $(MANIFEST names); do
    [ -z "$only" ] || [ "$only" = "$name" ] || continue
    local path; path="$(MANIFEST path "$name")"
    require_repo "$path" "$name" || continue
    hr "adopt $name"
    python3 "$ROOT/scripts/adopt.py" "$path" "$name"
  done
  ok "adoption complete (review the new files, then commit them in each child repo)"
}

cmd_sync_shared() {  ## Refresh the shared agent-rules block inside every child's SYSTEM_LINK.md
  local block; block="$(cat shared/agent-rules.md)"
  for name in $(MANIFEST names); do
    local path; path="$(MANIFEST path "$name")"
    local target="$path/docs/ai/SYSTEM_LINK.md"
    [ -f "$target" ] || continue
    python3 - "$target" "shared/agent-rules.md" <<'PY'
import sys, pathlib
target, src = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
text = target.read_text(encoding="utf-8")
start = "<!-- SHARED-AGENT-RULES:START"
end = "<!-- SHARED-AGENT-RULES:END -->"
block = src.read_text(encoding="utf-8").strip()
new = f"{start} (synced from workspace shared/agent-rules.md — do not edit here) -->\n\n{block}\n\n{end}"
import re
if start in text and end in text:
    text = re.sub(re.escape(start) + r".*?" + re.escape(end), new, text, flags=re.S)
else:
    text = text.rstrip() + "\n\n" + new + "\n"
target.write_text(text, encoding="utf-8")
print(f"  synced {target}")
PY
  done
  ok "shared agent-rules propagated"
}

cmd_check() {  ## System quality gate: each repo's `make check` + contract verify
  local rc=0
  for name in $(MANIFEST names); do
    local path; path="$(MANIFEST path "$name")"
    require_repo "$path" "$name" || { rc=1; continue; }
    hr "check $name"
    if [ -f "$path/Makefile" ] && grep -q '^check:' "$path/Makefile"; then
      ( cd "$path" && make check ) || { err "$name: make check failed"; rc=1; }
    else
      err "$name: no 'check' target in Makefile"; rc=1
    fi
  done
  hr "contracts"
  cmd_contracts || rc=1
  [ "$rc" = 0 ] && ok "system green" || err "system NOT green"
  return $rc
}

cmd_contracts() {  ## Verify each service still matches its published contract
  # Two levels: (1) the declared contract file exists; (2) if the service sets a
  # `contract_source:` (a live /openapi.json URL or a spec file), diff the live
  # operations against the committed contract to catch drift. Drift fails the gate;
  # an unreachable source is a SKIP, not a failure (the service may just be down).
  local rc=0 any=0
  for name in $(MANIFEST names); do
    local exposes; exposes="$(MANIFEST field "$name" exposes)"
    [ -n "$exposes" ] || continue
    any=1
    if [ ! -f "$exposes" ]; then
      err "$name declares exposes: $exposes but the file is missing"; rc=1; continue
    fi
    local source; source="$(MANIFEST field "$name" contract_source)"
    if [ -n "$source" ]; then
      info "$name: diffing $exposes against $source"
      local drc=0
      python3 "$ROOT/scripts/contract_diff.py" "$exposes" "$source" || drc=$?
      # contract_diff exits: 0 in sync, 1 drift (fail), 2 skipped (source down → tolerate)
      if [ "$drc" -eq 1 ]; then err "$name: contract drift"; rc=1; fi
    else
      ok "$name → $exposes present (presence-only; set contract_source for drift checks)"
    fi
  done
  [ "$any" = 1 ] || info "no contracts declared yet"
  return $rc
}

cmd_lock() {  ## Pin each service to its current HEAD commit in repos.lock
  : > repos.lock
  for name in $(MANIFEST names); do
    local path; path="$(MANIFEST path "$name")"
    require_repo "$path" "$name" || continue
    local sha; sha="$(git -C "$path" rev-parse HEAD)"
    printf '%s %s\n' "$name" "$sha" >> repos.lock
  done
  ok "wrote repos.lock"
}

cmd_graph() {  ## Print the dependency graph (consumer -> provider) from repos.yaml
  local edges; edges="$(MANIFEST graph)"
  if [ -z "$edges" ]; then info "no dependency edges declared"; else printf '%s\n' "$edges"; fi
}

cmd_doctor() {  ## Validate repos.yaml and the workspace setup
  info "validating repos.yaml"
  MANIFEST check && ok "manifest valid"
  command -v git >/dev/null || err "git not found"
  command -v python3 >/dev/null || err "python3 not found (needed to read the manifest)"
}

cmd_help() {  ## Show this help
  printf 'workspace.sh — multi-repo system driver\n\nCommands:\n'
  grep -E '^cmd_[a-z_]+\(\) \{  ##' "${BASH_SOURCE[0]}" \
    | sed -E 's/^cmd_([a-z_]+)\(\) \{  ## (.*)/\1|\2/' \
    | awk -F'|' '{gsub("_","-",$1); printf "  \033[36m%-14s\033[0m %s\n", $1, $2}'
}

main() {
  local cmd="${1:-help}"; shift || true
  case "$cmd" in
    clone) cmd_clone "$@";;
    sync) cmd_sync "$@";;
    status) cmd_status "$@";;
    foreach) cmd_foreach "$@";;
    new) cmd_new "$@";;
    adopt) cmd_adopt "$@";;
    sync-shared) cmd_sync_shared "$@";;
    check) cmd_check "$@";;
    contracts) cmd_contracts "$@";;
    lock) cmd_lock "$@";;
    graph) cmd_graph "$@";;
    doctor) cmd_doctor "$@";;
    help|-h|--help) cmd_help;;
    *) err "unknown command: $cmd"; cmd_help; exit 2;;
  esac
}

main "$@"
