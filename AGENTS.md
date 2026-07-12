# Xixi Dev System Agent Entry

This repository is the executable entry for the Profile owner's personal development system.

When an Agent opens or clones this repository:

1. Read `README.md`, `SYSTEM.md`, `STATE.md`, and `skills/xixi-dev-system/SKILL.md`.
2. Inspect Git status and preserve existing work.
3. Run `python3 -m unittest discover -s tests -v` before publishing system changes.
4. Ensure the single personal learning automation exists and is current:

   ```bash
   bin/xixi-dev-system automation ensure-learning \
     --workspace /path/to/the/Profile-owner-workspace
   ```

   Discover the workspace from the current saved project or ask only when it cannot be inferred. The command is idempotent and must update the stable automation instead of creating duplicates. If duplicates already exist, stop and report them for review.
5. The automation may discover owner-scoped local projects, harvest retrospective candidates, and lint Goals. It must not automatically publish a lesson into `xixi-agent-profile`; publication requires a recorded human review that passes the promotion gate.
6. New machine restoration must use `bin/bootstrap-new-machine.sh`, which installs the Skill, command, Profile, supporting repositories, and the same versioned automation prompt.

Project data, user secrets, raw retrospective registries, and `.xds/` runtime state must remain local unless a reviewed artifact explicitly belongs in this repository.
