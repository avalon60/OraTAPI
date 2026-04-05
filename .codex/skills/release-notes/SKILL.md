When requested to generate release notes:

1. Check whether the repository has outstanding modifications. If the worktree is dirty, tell the user that the release notes may not reflect all uncommitted changes and confirm whether the notes should be based on the current working tree or only on committed changes.
2. Check that the application version has already been bumped to the intended release version before drafting the notes. For OraTAPI, treat `.bumpversion.cfg` as the authoritative release-version source unless the user explicitly says otherwise. If `.bumpversion.cfg` has not yet been updated, warn the user that version-specific wording, artifact names, and upgrade guidance may be inaccurate until the version bump is complete.
3. Append the following footer text after the release-specific notes. Replace placeholders such as `x.y.z` with the actual release version where applicable.


```
Please see [README.md](https://github.com/avalon60/OraTAPI/blob/develop/README.md) for installation, upgrade, and usage guidance.

## Download and Upgrade

To upgrade to the latest available OraTAPI release, use:

`bin/update_ora_tapi.sh -t /tmp` on macOS/Linux  
`bin/update_ora_tapi.ps1 -t <staging_path>` on Windows PowerShell

To install this specific release instead of upgrading to the latest available release, download the `oratapi-x.y.z.tar.gz` artifact from the Assets section for this release.

If you are new to OraTAPI, please read the [OraTAPI - Oracle Table API Generator](https://github.com/avalon60/OraTAPI#oratapi---oracle-table-api-generator) documentation.

If you already have OraTAPI installed, see [Performing Upgrades](https://github.com/avalon60/OraTAPI#performing-upgrades).
```
