---
name: xixi-dev-system
description: Route every Xixi coding task through the unified development system. Use for new or existing projects, collaboration updates, previews, acceptance, quality reports, repair PRs, project memory, or cross-computer setup.
---

# Xixi Dev System

Use this as the single entry point. Do not ask the user to choose among profile,
acceptance factory, dashboard, or preview tools.

Resolve the deterministic command as
`${CODEX_HOME:-$HOME/.codex}/bin/xixi-dev-system`. Do not depend on the user's
shell `PATH` containing the command.

1. Run `profile sync` through the deterministic command, then read the synced
   Profile before making cross-project workflow, writing, or preference
   decisions. The Profile repository remains the preference source of truth;
   the user does not manually invoke it.
   Treat visual preferences as guidance, never as permission to copy another
   product's colors, typography, layout, or components. Visual consistency is
   scoped to the current product unless the user explicitly requests reuse.
2. Locate `.xixi-dev-system.json`. If absent, run `xixi-dev-system onboard`
   from the project root. It auto-detects common project facts and never
   overwrites an existing adapter. Only ask for values detection cannot safely
   infer.
3. Run `doctor` before changing code. Treat remote commits, branch heads, and
   open PRs as collaboration facts; do not assume a default branch is active.
4. For daily work, run `updates` first. Read its compact report before choosing
   checks. Do not execute arbitrary unmerged branch code for reporting.
5. Use a worktree and configured runtime for implementation. Start previews
   through the system so ports and data namespaces are unique.
6. Low-risk fixes require evidence, a rerun, and a separate PR. High-risk areas
   are report-only. Daily observations only become shared learning after weekly
   evidence review.
7. For a reviewed, repeated or high-impact finding, create a project learning
   candidate first. Promote it into the shared Profile only with an explicit
   rule, evidence, and scope.

## Goal execution contract

When the user says "run a goal", "continue autonomously", or asks for a task
list that should keep progressing, do not improvise a loose checklist.

1. Create one bounded host Goal when the host exposes Goal tools. The objective
   must describe one verifiable vertical slice, not an entire product roadmap.
2. Publish a plan of 3-8 dependency-ordered tasks. Every task needs a concrete
   acceptance statement and must be small enough to verify independently.
3. Persist the same plan with `xixi-dev-system goal create`. The project-local
   `.xds/goals/` state is the durable source across threads and computers.
4. Keep only one task running. Start it with `goal task start` and update the
   visible host plan at the same transition.
5. A task may become verified only through `goal task verify` with command,
   test, file, URL, screenshot, or explicit review evidence. Agent confidence
   is not evidence.
6. Progress is derived from verified tasks. Never hand-edit a percentage or
   mark several tasks complete at the end without their individual evidence.
7. On a blocker or failure, record the reason immediately and keep the next
   action visible. Do not hide it in narrative status updates.

Recommended commands:

```bash
xixi-dev-system goal create --project . --spec goal.json
xixi-dev-system goal show --project . --goal <goal-id>
xixi-dev-system goal task start --project . --goal <goal-id> --task <task-id>
xixi-dev-system goal task verify --project . --goal <goal-id> --task <task-id> \
  --evidence-type test --evidence "9 tests passed"
```

For a formal multi-stage Goal, maintain one authoritative Markdown document
with current facts, scope and non-scope, ordered phases, evidence slots, stop
conditions, delivery boundaries, a launch prompt, and a completion audit. Run
`goal lint --document ... --spec ...` before `goal create`. A small one-command
task can stay lightweight, but it still needs truthful acceptance evidence.

## Evidence-driven system learning

When the Profile owner asks to learn from "my projects", use local Git origins
as the ownership boundary. `projects discover --owner <owner> --root <path>` is
read-only and does not grant permission to read remote repository content.
Record multiple local working copies even when they share one origin.

Use `learning portfolio` only for deliberately selected source projects. It
indexes governance, status, handoff, audit, method, workflow, and Goal evidence
with hashes and headings. Automation may discover, index, lint, and create
candidates; it must not promote into the shared Profile without human review.

Every promotion candidate needs source paths, the repeated pattern, proposed
scope, enforcement mode, a counterexample or limit, and verification. Keep
one-project facts in that project; promote stable cross-project rules to the
Profile; implement deterministic checks and automation in xixi-dev-system.

When entering a project with `错误复盘.md`, `RETROSPECTIVE.md`, or
`doc/retrospectives/`, harvest into the project-local
`.xds/learning/registry.json`. Do not commit that raw registry by default.
Legacy entries may be incomplete; mark them `needs_completion` instead of
inventing fields. A changed source becomes `needs_re_review`; unchanged sources
remain idempotent; zero entries are valid.

`learning review` is the required human gate. Profile promotion needs evidence
from two distinct origins, or source evidence of an owner correction plus an
explicit high-impact reviewer decision. `learning publish` may write only an
`approved_for_profile` candidate and must remain idempotent. Never infer owner
approval from the existence of a retrospective.

On first entry to or clone of the xixi-dev-system repository, follow its
`AGENTS.md` and run `automation ensure-learning` for the Profile owner's local
workspace. Use the stable automation id and update it; never create a duplicate
task. If multiple matching automations exist, stop for review.
