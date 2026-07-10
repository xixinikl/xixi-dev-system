#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
SKILL_TARGET="$CODEX_HOME/skills/xixi-dev-system"
AGENTS_TARGET="$CODEX_HOME/AGENTS.md"

if [[ -e "$SKILL_TARGET" ]]; then
  echo "Refusing to overwrite existing skill: $SKILL_TARGET" >&2
  exit 1
fi

mkdir -p "$CODEX_HOME/skills"
cp -R "$ROOT/skills/xixi-dev-system" "$SKILL_TARGET"

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
echo "Added global routing rule to $AGENTS_TARGET"
