---
name: oratapi-readme-audit
description: Audit OraTAPI README content for inconsistencies, missing prerequisites, and unclear installation or upgrade guidance.
---

When this skill is relevant, audit README and related install files for:
- contradictions between README sections
- missing prerequisites
- unclear installation, upgrade, or migration steps
- mismatches between documented entry points and actual code/package metadata
- stale references to scripts, paths, or module names

Working rules:
- classify findings as confirmed issue, likely issue, or suggestion
- prefer confirmed evidence from pyproject.toml, README.md, setup scripts, and controller entry points
- do not modify files unless explicitly asked
- present findings in a concise, structured form
- exclude src/nlib unless the user explicitly asks for migration analysis
