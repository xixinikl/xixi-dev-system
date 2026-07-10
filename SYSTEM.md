# System Contract

## Public Surface

The only user-facing system name is `xixi-dev-system`.

| Surface | Purpose |
|---|---|
| Global skill | Routes every coding task into this system. |
| `bin/xixi-dev-system` | Deterministic commands for projects and automation. |
| `.xixi-dev-system.json` | Per-project adapter contract. |
| `.xds/` | Generated local runtime state, reports, logs, and worktrees. |

Existing profile, acceptance factory, and quality hub repositories are internal
dependencies or display surfaces, not separate commands the user must remember.

## Operational Rules

1. Daily flow fetches remote refs, records all new commits across branches,
   maps commits to branches, and never executes unmerged branch code.
2. Preview flow creates a worktree, assigns a free localhost port and a unique
   data namespace, then stores the PID and URL in `.xds/runtime/`.
3. Daily reports are observations. Weekly review promotes only repeated or
   high-impact, evidenced rules into shared learning.

## Isolated Python

Python projects use `uv` to download the adapter's exact Python version and
create `.xds/venvs/<name>/`. `runtime prepare` installs dependencies into that
environment only. Preview refuses to fall back to system Python. A project can
use `{python}` in `runtime.startCommand`; it resolves to the managed interpreter.
