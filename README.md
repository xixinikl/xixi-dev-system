# Xixi Dev System

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

The installed `xixi-dev-system` skill is the agent-facing entry point. The CLI
is the deterministic implementation behind it.

For a plain-Chinese explanation of which repository does what, read
[`docs/repository-map.zh-CN.md`](docs/repository-map.zh-CN.md).

## Rules

- GitHub commits, branch heads, and open PRs are the collaboration fact source.
- Update collection is read-only and never runs unmerged branch code.
- Preview uses a project-level runtime contract, dynamic ports, and a distinct
  data namespace. It does not modify system Python.
- Low-risk repair is always a verified, separate PR. It never writes directly
  to the default branch.
