# Xixi Dev System

One entry point for Xixi's Codex projects. It routes project onboarding,
collaboration-update reports, isolated previews, quality evidence, and memory
promotion without making the user remember separate repositories.

## One command

```bash
bin/xixi-dev-system doctor --project .
```

```bash
bin/xixi-dev-system onboard --project /path/to/project --name "Project" --repo "https://github.com/owner/repo"
bin/xixi-dev-system updates --project /path/to/project --date 2026-07-11
bin/xixi-dev-system runtime prepare --project /path/to/project
bin/xixi-dev-system automation install --project /path/to/project
bin/xixi-dev-system workspace create --project /path/to/project --branch feature/example
bin/xixi-dev-system preview start --project /path/to/project
```

The installed `xixi-dev-system` skill is the agent-facing entry point. The CLI
is the deterministic implementation behind it.

## Rules

- GitHub commits, branch heads, and open PRs are the collaboration fact source.
- Update collection is read-only and never runs unmerged branch code.
- Preview uses a project-level runtime contract, dynamic ports, and a distinct
  data namespace. It does not modify system Python.
- Low-risk repair is always a verified, separate PR. It never writes directly
  to the default branch.
