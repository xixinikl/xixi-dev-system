#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
SKILL_TARGET="$CODEX_HOME/skills/xixi-dev-system"
TOOL_TARGET="$CODEX_HOME/tools/xixi-dev-system"
COMMAND_TARGET="$CODEX_HOME/bin/xixi-dev-system"
AGENTS_TARGET="$CODEX_HOME/AGENTS.md"
UPGRADE="${1:-}"

if [[ -e "$SKILL_TARGET" || -e "$TOOL_TARGET" || -e "$COMMAND_TARGET" ]] && [[ "$UPGRADE" != "--upgrade" ]]; then
  echo "Existing installation found. Re-run with --upgrade to replace only xixi-dev-system files." >&2
  exit 1
fi

if [[ "$UPGRADE" == "--upgrade" ]]; then
  rm -rf "$SKILL_TARGET" "$TOOL_TARGET"
  rm -f "$COMMAND_TARGET"
fi

mkdir -p "$CODEX_HOME/skills" "$CODEX_HOME/tools" "$CODEX_HOME/bin"
cp -R "$ROOT/skills/xixi-dev-system" "$SKILL_TARGET"
mkdir -p "$TOOL_TARGET/bin" "$TOOL_TARGET/scripts" "$TOOL_TARGET/automations" "$TOOL_TARGET/web"
cp "$ROOT/bin/xixi-dev-system" "$TOOL_TARGET/bin/xixi-dev-system"
cp "$ROOT/scripts/xds.py" "$TOOL_TARGET/scripts/xds.py"
cp "$ROOT/scripts/dashboard_server.py" "$TOOL_TARGET/scripts/dashboard_server.py"
cp -R "$ROOT/web/dashboard" "$TOOL_TARGET/web/dashboard"
cp "$ROOT/automations/weekly-personal-dev-system.prompt.md" "$TOOL_TARGET/automations/weekly-personal-dev-system.prompt.md"
ln -s "$TOOL_TARGET/bin/xixi-dev-system" "$COMMAND_TARGET"

MARKER_START="# xixi-dev-system:start"
MARKER_END="# xixi-dev-system:end"
if [[ ! -f "$AGENTS_TARGET" ]] || ! rg -Fq "$MARKER_START" "$AGENTS_TARGET"; then
  cat >> "$AGENTS_TARGET" <<EOF

$MARKER_START
For any coding, project, preview, quality, or cross-computer task, invoke the
xixi-dev-system skill first. Use its project adapter and commands as the single
entry point; do not require the user to choose internal profile or factory tools.
$MARKER_END
EOF
fi

echo "Installed xixi-dev-system skill into $SKILL_TARGET"
echo "Installed command runner at $COMMAND_TARGET"
echo "Added global routing rule to $AGENTS_TARGET"
