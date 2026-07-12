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
