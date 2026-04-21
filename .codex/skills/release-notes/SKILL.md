---
name: generate-release-notes
description: Generate release notes for OraTAPI by checking for uncommitted changes, verifying the release version in .bumpversion.cfg, and appending the standard installation and upgrade footer.
---

When requested to generate release notes:

1. Check whether the repository has outstanding modifications. If the worktree is dirty, tell the user that the release notes may not reflect all uncommitted changes and confirm whether the notes should be based on the current working tree or only on committed changes.
2. Check that the application version has already been bumped to the intended release version before drafting the notes. For OraTAPI, treat `.bumpversion.cfg` as the authoritative release-version source unless the user explicitly says otherwise. If `.bumpversion.cfg` has not yet been updated, warn the user that version-specific wording, artifact names, and upgrade guidance may be inaccurate until the version bump is complete.
3. Append the following footer text after the release-specific notes. Replace placeholders such as `x.y.z` with the actual release version where applicable.

------------------------------------ Footer Text - Cut Here --------------------------------------------------
Please see [README.md](https://github.com/avalon60/OraTAPI/blob/develop/README.md) for installation, upgrade, and usage guidance.

## Compatibility Notes

- Existing users should run `quick_config` to initialise runtime profiles in the new layout.
- Users who run `migrate_config` in newer releases are redirected to `profile_mgr`.

## Usage
Please refer to [README.md](https://github.com/avalon60/OraTAPI/blob/develop/README.md)

## Install Quick Start 

**On Linux / macOS:**
python -m venv .venv
source .venv/bin/activate
pip install oratapi

**On Windows PowerShell:**
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install oratapi


If you are new to OraTAPI, please read the [OraTAPI - Oracle Table API Generator](https://github.com/avalon60/OraTAPI#oratapi---oracle-table-api-generator) documentation.

------------------------------------ Footer Text - Cut Here --------------------------------------------------
