#!/usr/bin/env bash
# Create a workspace (the folder you start your AI in) wired to this kit and a profile.
#   scripts/new-workspace.sh <workspace-dir> <profile>      e.g.  ~/freelance freelance
# Safe to re-run: existing files are left alone (profile files, jobs, lessons are never overwritten).
set -euo pipefail

[ $# -eq 2 ] || { echo "usage: $0 <workspace-dir> <profile>  (profiles: $(ls "$(dirname "$0")/../profiles" | tr '\n' ' '))" >&2; exit 1; }
KIT="$(cd "$(dirname "$0")/.." && pwd)"
WS="$1"; PROFILE="$2"
SRC="$KIT/profiles/$PROFILE"
[ -d "$SRC" ] || { echo "no such profile: $PROFILE" >&2; exit 1; }
case "$(cd "$(dirname "$WS")" 2>/dev/null && pwd)/" in "$KIT"/*) echo "put the workspace outside the kit repo" >&2; exit 1;; esac

mkdir -p "$WS"/{profile,lessons,timelog,.claude/skills}
WS="$(cd "$WS" && pwd)"

copy_new() { [ -e "$2" ] && echo "  keep   ${2#$WS/}" || { cp "$1" "$2"; echo "  create ${2#$WS/}"; }; }
render() { sed -e "s|{{KIT}}|$KIT|g" -e "s|{{PROFILE}}|$PROFILE|g" "$1"; }

echo "Workspace $WS (profile: $PROFILE)"
for f in "$SRC"/*; do case "$f" in *.example.yaml) continue;; esac; copy_new "$f" "$WS/profile/$(basename "$f")"; done
[ -f "$SRC/clients.example.yaml" ] && copy_new "$SRC/clients.example.yaml" "$WS/profile/clients.yaml"

if grep -qE '^\s*connector:\s*markdown' "$WS/profile/profile.yaml"; then
  mkdir -p "$WS/jobs"
  [ -f "$WS/profile/job-template.md" ] || cp "$KIT/profiles/_template/job-template.md" "$WS/profile/"
fi

[ -e "$WS/AGENTS.md" ] && echo "  keep   AGENTS.md" || { render "$KIT/adapters/generic/AGENTS.workspace.md" > "$WS/AGENTS.md"; echo "  create AGENTS.md"; }
[ -e "$WS/CLAUDE.md" ] && echo "  keep   CLAUDE.md" || { printf '@AGENTS.md\n' > "$WS/CLAUDE.md"; echo "  create CLAUDE.md"; }
[ -e "$WS/.claude/skills/team" ] || { ln -s "$KIT/adapters/claude-code/skills/team" "$WS/.claude/skills/team"; echo "  link   .claude/skills/team"; }
[ -e "$WS/.claude/settings.json" ] && echo "  keep   .claude/settings.json (merge hooks from adapters/claude-code/settings.example.json by hand)" \
  || { render "$KIT/adapters/claude-code/settings.example.json" > "$WS/.claude/settings.json"; echo "  create .claude/settings.json"; }
[ -e "$WS/.gitignore" ] || printf 'timelog/\nprofile/clients.yaml\n*.local.*\n.agent-team/\n' > "$WS/.gitignore"

echo "Done. Next: edit $WS/profile/profile.yaml (and clients.yaml), then start your AI in $WS."
