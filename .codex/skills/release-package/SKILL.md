---
name: release-package
description: Prepare a release artefact for this project by bumping the requested semantic version level and running the packaging script. Use when the user asks to bump a major, minor, or patch release and package or create a release artefact. Do not use for ordinary build or test tasks.
---

When this skill is used:
1. Determine whether the user requested `major`, `minor`, or `patch`.
2. Run exactly one of:
   - `./utils/bump_major.sh`
   - `./utils/bump_minor.sh`
   - `./utils/bump_patch.sh`
3. Then run:
   - `./utils/package.sh`
4. Report:
   - which bump command was run
   - the resulting version
   - the packaging result
   - the artefact path or filename if available

Safety rules:
- Do not commit, tag, or push unless explicitly instructed.
- Do not guess the bump level.
- If packaging fails, report the failure and relevant output.
