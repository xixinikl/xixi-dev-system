---
name: xixi-dev-system
description: Route every Xixi coding task through the unified development system. Use for new or existing projects, collaboration updates, previews, acceptance, quality reports, repair PRs, project memory, or cross-computer setup.
---

# Xixi Dev System

Use this as the single entry point. Do not ask the user to choose among profile,
acceptance factory, dashboard, or preview tools.

1. Locate `.xixi-dev-system.json`. If absent, run system `onboard` without
   overwriting existing project files.
2. Run `doctor` before changing code. Treat remote commits, branch heads, and
   open PRs as collaboration facts; do not assume a default branch is active.
3. For daily work, run `updates` first. Read its compact report before choosing
   checks. Do not execute arbitrary unmerged branch code for reporting.
4. Use a worktree and configured runtime for implementation. Start previews
   through the system so ports and data namespaces are unique.
5. Low-risk fixes require evidence, a rerun, and a separate PR. High-risk areas
   are report-only. Daily observations only become shared learning after weekly
   evidence review.
6. For a reviewed, repeated or high-impact finding, create a project learning
   candidate first. Promote it into the shared Profile only with an explicit
   rule, evidence, and scope.
