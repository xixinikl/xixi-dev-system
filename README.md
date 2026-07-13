# Xixi Dev System

## Repository identity

| Item | Meaning |
|---|---|
| Type | System entry repository: the only user-facing gateway for project onboarding, runtime, reports, preferences, and learning promotion. |
| Works with | Syncs `xixi-agent-profile`, enforces `standard-project-workflow`, invokes acceptance capabilities, and publishes conclusions to `quality-hub`. |
| Open it routinely? | Only for first-time installation or system maintenance; normal work is routed automatically by the installed Skill. |
| Status | Active and authoritative for the unified personal development system. |
| Restore on a new computer | Clone this repository and run `bin/install-local.sh`; the installed entry then restores the command and personal Profile. |

One entry point for Xixi's Codex projects. It routes project onboarding,
collaboration-update reports, isolated previews, quality evidence, and memory
promotion without making the user remember separate repositories.

## One command

Install once on a new computer:

```bash
git clone https://github.com/xixinikl/xixi-dev-system.git
cd xixi-dev-system
bin/install-local.sh
```

To restore the complete multi-repository system, including the Profile,
formal-workflow Skill, acceptance Skill, and Monday weekly automation:

```bash
bin/bootstrap-new-machine.sh --workspace "/path/to/your/Codex/workspace"
bin/system-doctor.sh
```

The authoritative repository and installation inventory is
[`system/system-manifest.json`](system/system-manifest.json). The weekly prompt
is versioned in [`automations/`](automations/) instead of living only on one
computer.

Codex then uses `~/.codex/bin/xixi-dev-system` as the stable command path. To
update an existing installation, pull this repository and run
`bin/install-local.sh --upgrade`; it replaces only xixi-dev-system-owned files.
At the start of coding work, the entry skill runs `profile sync` so the latest
personal preferences are read from GitHub without a separate user command.

```bash
xixi-dev-system onboard
```

Run it inside a new project. It detects the project name, GitHub remote,
default branch, package manager, common start command, and common quality
command. Nothing is overwritten. Then verify the adapter with:

```bash
xixi-dev-system doctor --project .
```

```bash
bin/xixi-dev-system onboard
bin/xixi-dev-system updates --project /path/to/project --date 2026-07-11
bin/xixi-dev-system runtime prepare --project /path/to/project
bin/xixi-dev-system automation install --project /path/to/project
bin/xixi-dev-system workspace create --project /path/to/project --branch feature/example
bin/xixi-dev-system preview start --project /path/to/project
```

## Project preview center

Register the projects that should appear on this computer, then open one local
page for project and branch previews. Machine-specific paths stay under
`~/.codex/xixi-dev-system/` and are never committed to this repository.

```bash
bin/xixi-dev-system dashboard register \
  --project /path/to/project --id project-id --name "Project name"
bin/xixi-dev-system dashboard start --open
```

The dashboard reports the current checkout and recent local/remote branches.
Starting a branch reuses its existing worktree when possible, otherwise creates
a detached preview worktree. Every running preview receives a unique localhost
port and `XDS_DATA_NAMESPACE`. Project adapters may declare or locally override
the preview command and label the result as isolated, shared-data, or
frontend-only; the dashboard displays that status instead of overstating the
environment.

Discover only local working copies owned by a GitHub account, without reading
remote repository contents, then build a read-only evidence portfolio for the
projects deliberately selected as learning sources:

```bash
bin/xixi-dev-system projects discover --owner xixinikl \
  --root /path/to/workspace --output /tmp/projects.json
bin/xixi-dev-system learning portfolio --owner xixinikl \
  --project /path/to/project-a --project /path/to/project-b \
  --output /tmp/evidence-portfolio.json
```

The installed `xixi-dev-system` skill is the agent-facing entry point. The CLI
is the deterministic implementation behind it.

## Standard goals

Long-running work uses one bounded Goal with dependency-ordered tasks and
evidence-gated progress. The visible Codex Goal is the active execution view;
`.xds/goals/` is the durable project state used across threads.

```bash
xixi-dev-system goal create --project . \
  --spec /path/to/goal.json
xixi-dev-system goal show --project . --goal canvas-storm-mvp-first
xixi-dev-system goal task start --project . \
  --goal canvas-storm-mvp-first --task T1
xixi-dev-system goal task verify --project . \
  --goal canvas-storm-mvp-first --task T1 \
  --evidence-type file --evidence "docs/spec.md"
```

Progress is calculated only from verified tasks. Dependencies, one-running-task
discipline, blockers, runs, and evidence are stored in the same state file.
The contract is documented by `system/goal-state-v1.schema.json`; a complete
CanvasStorm planning example lives in `examples/goals/`.

For a plain-Chinese explanation of which repository does what, read
[`docs/repository-map.zh-CN.md`](docs/repository-map.zh-CN.md).

For long-running CDS-style Goals, keep a human-readable authoritative document
beside the executable JSON and lint both before starting:

```bash
bin/xixi-dev-system goal lint \
  --document docs/goals/example.md \
  --spec examples/goals/example.json
```

The lint checks structure; it never substitutes for business verification or
the completion audit described by the Goal.

## Retrospective ingestion

The system can harvest structured candidates from `错误复盘.md`,
`RETROSPECTIVE.md`, and `doc/retrospectives/` without modifying source
projects:

```bash
bin/xixi-dev-system learning harvest --owner xixinikl \
  --project /path/to/project \
  --registry /path/to/project/.xds/learning/registry.json
```

Harvesting preserves source evidence, records stable source and content
fingerprints, marks missing fields, updates changed entries to
`needs_re_review`, and is idempotent when content is unchanged. An empty
retrospective set is a valid zero state.

Promotion is intentionally two-step. `learning review` requires either support
from two different origins or an explicit high-impact owner correction present
in source evidence. `learning publish` accepts only reviewed
`approved_for_profile` candidates and uses the candidate id to prevent duplicate
Profile entries. Automated harvesting never implies approval.

## Personal learning automation

When this repository is cloned or opened, Agents follow `AGENTS.md` and ensure
the versioned personal learning automation exists:

```bash
bin/xixi-dev-system automation ensure-learning \
  --workspace /path/to/local/workspace
```

The command uses the stable id `weekly-personal-dev-system`, updates an existing
instance, preserves its creation time, and refuses to proceed when duplicates
already exist. `bootstrap-new-machine.sh` invokes the same command after install,
so clone, restore, and upgrade do not create parallel automation variants.

## Rules

- GitHub commits, branch heads, and open PRs are the collaboration fact source.
- Update collection is read-only and never runs unmerged branch code.
- Preview uses a project-level runtime contract, dynamic ports, and a distinct
  data namespace. It does not modify system Python.
- Low-risk repair is always a verified, separate PR. It never writes directly
  to the default branch.
