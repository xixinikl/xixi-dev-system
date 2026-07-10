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
- Gongtu: adapter and isolated SQLite namespace configuration are in PR #10;
  runtime start is correctly blocked until uv prepares Python 3.11.
- Not yet complete: scheduled ledger/report publishing, scoped acceptance,
  repair PR policy integration, weekly promotion, quality hub integration, and
  fresh-machine portability test.
- Safety: Gongtu PR #9 remains open and unmerged. Do not merge it while the
  system redesign is in progress.
