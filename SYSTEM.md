# System Contract

## Public Surface

The only user-facing system name is `xixi-dev-system`.

| Surface | Purpose |
|---|---|
| Global skill | Routes every coding task into this system. |
| `bin/xixi-dev-system` | Deterministic commands for projects and automation. |
| `.xixi-dev-system.json` | Per-project adapter contract. |
| `.xds/` | Generated local runtime state, reports, logs, and worktrees. |

## Goal state authority

`xixi-dev-system goal` is the single durable authority for long-running task
state. A Goal contains ordered Tasks, execution Runs, Evidence, and Blockers.
The CLI derives current task, next task, terminal status, and progress. Reports
and dashboards may render this state but must not maintain a parallel status.

The host Codex Goal and plan provide the live progress surface. Agents must
mirror each start, verify, block, and fail transition into `.xds/goals/` so a
new thread can continue without reconstructing state from chat.

Existing profile, acceptance factory, and quality hub repositories are internal
dependencies or display surfaces, not separate commands the user must remember.

## Operational Rules

1. Daily flow fetches remote refs, records all new commits across branches,
   maps commits to branches, and never executes unmerged branch code.
2. Preview flow creates a worktree, assigns a free localhost port and a unique
   data namespace, then stores the PID and URL in `.xds/runtime/`.
3. Daily reports are observations. Weekly review promotes only repeated or
   high-impact, evidenced rules into shared learning.

`automation install` vendors the collector into `.xds-system/` and creates a
daily GitHub Actions workflow. The workflow writes only an Actions summary and
90-day artifact; it never checks out a collaboration branch for execution.

## Acceptance Gate

Projects declare `quality.acceptanceCommand` and optionally a low-risk autofix
command. The system runs the command only in the checked-out worktree. Auto-fix
is prohibited whenever the update ledger has high-risk paths; otherwise it must
rerun the acceptance command and records its evidence in the report.

## Learning Promotion

`learning candidate` converts a non-pass or repaired acceptance report into a
project retrospective candidate. `learning promote` writes a reviewed rule to
the shared Profile `LEARNINGS.md`. Promotion is deliberately explicit: one-off
failures cannot automatically change cross-project guidance.

## Isolated Python

Python projects use `uv` to download the adapter's exact Python version and
create `.xds/venvs/<name>/`. `runtime prepare` installs dependencies into that
environment only. Preview refuses to fall back to system Python. A project can
use `{python}` in `runtime.startCommand`; it resolves to the managed interpreter.
