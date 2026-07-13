# Current State

- Goal: build one portable Xixi development system for onboarding, collaboration
  updates, isolated previews, acceptance, repair PRs, reports, and learning.
- Decision: GitHub remote updates are the collaboration fact source; `main` is
  not assumed to be the active development line.
- Completed: new private `xixi-dev-system` repository, single-entry skill,
  project adapter CLI, read-only remote update ledger, worktree command, dynamic
  port preview command, local install/uninstall scripts, and uv-only runtime
  preparation that refuses system-Python fallback.
- Verified: disposable Git repository produced a multi-branch update report;
  preview received an unused localhost port and data namespace, served HTTP, and
  stopped cleanly.
- Goal kernel v1 implemented: bounded Goal specs, dependency-ordered Tasks,
  execution Runs, evidence-gated verification, blockers, derived progress, and
  CDS Goal lint are covered by tests.
- Evidence learning v1 implemented: owner-scoped local project discovery,
  read-only evidence portfolios, retrospective harvesting, stable fingerprints,
  missing/change/zero-state handling, human promotion gates, and idempotent
  Profile publication are available on `cx/goal-state-kernel-v1`.
- Automation restore implemented: repository `AGENTS.md`, install artifacts,
  and new-machine bootstrap converge on one versioned personal learning task.
- Branch preview dashboard implemented on `cx/branch-preview-dashboard`: local
  project registration, recent branch facts, worktree reuse/creation, dynamic
  ports, data namespace disclosure, one-click start/open/stop, and responsive UI.
- Gongtu: adapter and isolated SQLite namespace configuration are in PR #10;
  runtime start is correctly blocked until uv prepares Python 3.11.
- Not yet complete: automatic PR merge policy, quality hub integration, and a
  fresh second-machine acceptance run outside temporary-directory simulation.
- Safety: Gongtu PR #9 remains open and unmerged. Do not merge it while the
  system redesign is in progress.
