#!/usr/bin/env bash
set -euo pipefail

CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
rm -rf "$CODEX_HOME/skills/xixi-dev-system"
AGENTS_TARGET="$CODEX_HOME/AGENTS.md"
if [[ -f "$AGENTS_TARGET" ]]; then
  sed -i.bak '/^# xixi-dev-system:start$/,/^# xixi-dev-system:end$/d' "$AGENTS_TARGET"
  rm -f "$AGENTS_TARGET.bak"
fi
echo "Removed xixi-dev-system local installation"
