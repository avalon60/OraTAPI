# OraTAPI Wheel And PyPI Deployment Assessment

## Current Status

Phase 1, the package namespace refactor, has now been completed in the codebase.

Completed in this phase:

- introduced a single top-level package namespace: `oratapi`
- moved the former top-level packages under that namespace:
  - `oratapi.controller`
  - `oratapi.lib`
  - `oratapi.model`
  - `oratapi.view`
  - `oratapi.ora_tapi_package_data`
- updated internal Python imports to use the `oratapi.*` namespace
- updated `pyproject.toml` so packaging now installs the single `oratapi` package
- updated console script entry points to target `oratapi.controller.*`
- updated resource loading to use the namespaced packaged-resource anchor
- updated the legacy `bin/*.sh` and `bin/*.ps1` wrappers so they still work against the source tree after the move
- added a root package `__main__` module and fixed controller module-launch wiring
- simplified config seed packaging by moving shipped config samples from `resources/config/samples/` to `resources/config/`
- updated README and CLI guidance so wheel installation and installed console scripts are now the primary documented path
- updated runtime error/deprecation messages to recommend `ora_tapi`, `quick_config`, and `profile_mgr` rather than `bin/` wrappers

Validated in this phase:

- `poetry check`
- `poetry build`
- wheel contents now include `oratapi/...` modules and resources
- console script metadata in the wheel now points at `oratapi.controller.*`
- clean wheel installation and bootstrap smoke tests succeeded with the installed console scripts
- extracted source-distribution installation still works as a legacy path, but is no longer the preferred deployment model

Not completed in this phase:

- the mutable install/update tooling (`setup.sh`, `setup.ps1`, `update_ora_tapi`) has not yet been redesigned
- duplicated resource trees still exist and have not yet been consolidated
- template resources still use the older `samples/` convention and have not yet been simplified in the way config samples now have
- runtime/bootstrap flow has intentionally not yet been redesigned
- no backward-compatibility shim packages were added for external code importing `controller`, `lib`, `model`, or `view`
- the README still documents legacy extracted-install and in-place upgrade flows because they remain available, but they are now explicitly secondary

## 1. High-Confidence Findings

- The wheel/PyPI deployment model is viable in principle, and the repository is already partly aligned with it.
  Evidence:
  [src/oratapi/lib/fsutils.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/lib/fsutils.py) already treats packaged defaults as read-only resources via `importlib.resources`, and runtime state already lives under `~/OraTAPI`.

- The current code already separates packaged defaults from user-owned runtime data.
  Evidence:
  [src/oratapi/lib/fsutils.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/lib/fsutils.py) defines:
  - packaged defaults via `resolve_default_path(...)`
  - runtime profile state via `runtime_home()`, `profile_home(...)`, `active_profile_home()`, `resolve_path(...)`

- Runtime bootstrapping is already explicit, not installer-driven.
  Evidence:
  [src/oratapi/controller/quick_config.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/controller/quick_config.py) copies packaged sample config/templates into `~/OraTAPI/configs/<profile>/resources` and sets `~/OraTAPI/active_config`.

- The main application already runs against runtime-owned config/templates, not install-tree config/templates.
  Evidence:
  [src/oratapi/controller/ora_tapi.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/controller/ora_tapi.py), [src/oratapi/model/tapi_generator.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/model/tapi_generator.py), and [src/oratapi/model/utplsql_generator.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/model/utplsql_generator.py) resolve `resources/...` paths through `resolve_path(...)`, which points into the active profile.

- The wheel already contains Python modules, packaged resources, and console-script entry points.
  Evidence:
  `poetry build --format wheel` succeeded and the built wheel contains:
  - a single top-level package namespace, `oratapi`
  - subpackages under `oratapi/...`
  - packaged defaults under `oratapi/ora_tapi_package_data/resources/...`
  - console scripts `ora_tapi`, `quick_config`, `profile_mgr`, `conn_mgr`, `migrate_config`, `update_ora_tapi`

- The current install/update/deployment tooling is still built around an extracted installation tree.
  Evidence:
  [setup.sh](/home/clive/PycharmProjects/OraTAPI/setup.sh), [setup.ps1](/home/clive/PycharmProjects/OraTAPI/setup.ps1), [src/oratapi/controller/update_ora_tapi.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/controller/update_ora_tapi.py), [README.md](/home/clive/PycharmProjects/OraTAPI/README.md), and all `bin/*.sh` / `bin/*.ps1` wrappers assume a visible install root.

- `update_ora_tapi` is not compatible with a read-only wheel install.
  Evidence:
  [src/oratapi/controller/update_ora_tapi.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/controller/update_ora_tapi.py) copies files directly into `install_home()` and assumes `resources/`, `src/`, `bin/`, `setup.sh`, and `setup.ps1` are writable.

- The current import/package layout is poor for PyPI distribution.
  Evidence:
  before the namespace refactor, [pyproject.toml](/home/clive/PycharmProjects/OraTAPI/pyproject.toml) installed generic top-level packages named `controller`, `lib`, `model`, and `view`. That specific issue has now been addressed by introducing the `oratapi` root package.

- There is legacy duplication of packaged resources.
  Evidence:
  the repo contains both root-level `resources/...` and package-data under `src/oratapi/ora_tapi_package_data/resources/...`. Runtime bootstrap uses the packaged copy via `resolve_default_path(...)`, not the root tree.

- Some user-facing messages are still hardcoded to wrapper scripts instead of console scripts.
  Evidence:
  This was true before the latest wheel-first documentation pass, but the main runtime/deprecation guidance has now been updated to prefer console scripts.

## 2. Tentative Inferences

- A wheel-based internal deployment could work with relatively modest changes if you keep the current package layout for now and simply stop depending on extracted-tree install/update flows.

- Public PyPI distribution is also viable, but I would not recommend publishing it in the current namespace layout because `controller`, `lib`, `model`, and `view` are too generic.

- The best replacement for installer-time setup is an explicit bootstrap/init command, not first-run implicit initialization.
  Reason:
  initialization requires creating profile directories, selecting a built-in profile, and potentially overwriting runtime files. That is operationally explicit state management, not something `pip install` should trigger.

- `quick_config` is already very close to the right shape for that explicit bootstrap command. It may only need renaming/aliasing and some messaging changes rather than a brand-new mechanism.

## 3. Main Entry Points

- Packaging:
  [pyproject.toml](/home/clive/PycharmProjects/OraTAPI/pyproject.toml)

- Console scripts already defined:
  - `ora_tapi`
  - `quick_config`
  - `profile_mgr`
  - `conn_mgr`
  - `migrate_config`
  - `update_ora_tapi`

- Primary controller CLIs:
  [src/oratapi/controller/ora_tapi.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/controller/ora_tapi.py)
  [src/oratapi/controller/quick_config.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/controller/quick_config.py)
  [src/oratapi/controller/profile_mgr.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/controller/profile_mgr.py)
  [src/oratapi/controller/conn_mgr.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/controller/conn_mgr.py)
  [src/oratapi/controller/update_ora_tapi.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/controller/update_ora_tapi.py)

- Legacy/extracted-tree wrappers:
  [bin/ora_tapi.sh](/home/clive/PycharmProjects/OraTAPI/bin/ora_tapi.sh)
  [bin/ora_tapi.ps1](/home/clive/PycharmProjects/OraTAPI/bin/ora_tapi.ps1)
  and similar `bin/*`

- Legacy install bootstrap:
  [setup.sh](/home/clive/PycharmProjects/OraTAPI/setup.sh)
  [setup.ps1](/home/clive/PycharmProjects/OraTAPI/setup.ps1)

## 4. Key Modules And Responsibilities

- Runtime/resource location:
  [src/oratapi/lib/fsutils.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/lib/fsutils.py)
  Handles runtime home, active profile, packaged defaults, and path resolution.

- Main application flow:
  [src/oratapi/controller/ora_tapi.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/controller/ora_tapi.py)
  Validates runtime initialization, loads config, opens DB session, invokes generators.

- Profile/bootstrap management:
  [src/oratapi/controller/quick_config.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/controller/quick_config.py)
  [src/oratapi/lib/profile_manager.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/lib/profile_manager.py)

- Config handling:
  [src/oratapi/lib/config_mgr.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/lib/config_mgr.py)

- Generation logic:
  [src/oratapi/model/tapi_generator.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/model/tapi_generator.py)
  [src/oratapi/model/utplsql_generator.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/model/utplsql_generator.py)

- CSV runtime state:
  [src/oratapi/model/ora_tapi_csv.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/model/ora_tapi_csv.py)

- Connection storage:
  [src/oratapi/lib/connection_mgr.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/lib/connection_mgr.py)
  Stores credentials under `~/.OraTAPI`.

- Upgrade logic tied to unpacked installs:
  [src/oratapi/controller/update_ora_tapi.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/controller/update_ora_tapi.py)

## 5. Important Control And Data Flows

- Base execution flow today:
  console script or shell wrapper -> controller CLI -> active profile lookup in `~/OraTAPI/active_config` -> config/templates loaded from `~/OraTAPI/configs/<profile>/resources/...` -> output written to staging directories

- Bootstrap flow:
  `quick_config` -> packaged sample files loaded via `resolve_default_path(...)` -> copied into runtime home -> active profile pointer written

- Profile migration flow:
  `profile_mgr --migrate-old` -> reads old extracted install tree -> copies its `resources/config` and `resources/templates` into runtime home

- Resource flow:
  packaged resources are not edited in place; they are copied into runtime-owned profile directories before normal operation

- Upgrade flow today:
  `update_ora_tapi` -> unpacks tarball or downloads release -> copies files into existing install root
  This flow is incompatible with a wheel installed into `site-packages`.

## 6. Fragile Or High-Risk Areas

- Legacy mutable-install assumptions.
  [src/oratapi/controller/update_ora_tapi.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/controller/update_ora_tapi.py)
  [setup.sh](/home/clive/PycharmProjects/OraTAPI/setup.sh)
  [setup.ps1](/home/clive/PycharmProjects/OraTAPI/setup.ps1)
  These remain the biggest mismatch with a read-only wheel install.

- Resource duplication.
  Root `resources/...` vs packaged `src/oratapi/ora_tapi_package_data/resources/...`
  This creates drift risk and muddies which tree is authoritative.

- Template resource layout remains more complex than the config seed layout.
  Config seed files are now simplified under `resources/config/*.sample`, but templates still rely on the older `resources/templates/**/samples/...` convention.

- Broken or inconsistent module entrypoint.
  This was true before the namespace refactor, but [src/oratapi/__main__.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/__main__.py) and [src/oratapi/controller/__main__.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/controller/__main__.py) have now been corrected.

- Oracle Instant Client docs and runtime model do not line up cleanly.
  [README.md](/home/clive/PycharmProjects/OraTAPI/README.md#L101)
  previously said “place it below the root OraTAPI directory”, but [src/oratapi/lib/session_manager.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/lib/session_manager.py) actually falls back to `resolve_path("oracle_client")`, which is under the active runtime profile, not an install root. The README guidance has now been updated to match the runtime model.

## 7. Questions You Still Have

- Whether you want PyPI publication only for distribution, or also to support `pip install oratapi` as the primary end-user install story.
  This affects how aggressively to remove extracted-tree tooling.

- Whether `update_ora_tapi` should survive in any form.
  In a wheel/PyPI world, the natural upgrade path is `pip install --upgrade oratapi`, not a self-updating CLI.

- Whether the public command names should remain `quick_config` / `profile_mgr`, or be consolidated into a clearer command set such as `oratapi-init` and `oratapi-profile`.

- Whether you want to preserve source-tarball/offline install support alongside wheel/PyPI support.

## Assessment Of Viability

Yes, the model is viable.

The core runtime architecture already fits it well:
- packaged defaults can live inside the installed wheel
- user-owned runtime data already lives outside the package
- bootstrap is already explicit
- wheel entry points already exist

What does not fit is the surrounding operational model:
- extracted-tree setup scripts
- shell wrappers
- self-update by copying files into the install root
- generic package namespace

So this is more a deployment/tooling migration than a fundamental runtime redesign.

## Packaging Changes Required

- Move to a proper single package namespace.
  Recommended direction:
  - `oratapi/...` or `ora_tapi/...`
  - retain the existing organisational split by nesting the current modules beneath that parent package, for example:
    - `oratapi/controller/...`
    - `oratapi/lib/...`
    - `oratapi/model/...`
    - `oratapi/view/...`
  - then update all imports from `controller`, `lib`, `model`, `view` to that namespace
  - the goal is not to flatten the codebase, but to stop installing generic top-level packages directly into the Python environment

- Keep console scripts in `pyproject.toml`, but point them at namespaced modules after the refactor.

- Treat wheel resources as authoritative package data.
  The `src/oratapi/ora_tapi_package_data/resources/...` tree is already the relevant one for wheel installs.

- Decide whether to keep `setup.sh`, `setup.ps1`, and `bin/*` only for sdist/offline installs or retire them entirely from the primary distribution story.

- If publishing to PyPI, add standard metadata hygiene:
  - homepage/docs/issues URLs
  - license expression review
  - classifiers for supported OS/Python versions
  - probably a tighter package layout before first publish

## Code Changes Required

- Namespace refactor across the whole codebase.
  This has now been completed. Internal imports now use `oratapi.lib...`, `oratapi.model...`, `oratapi.controller...`, and `oratapi.view...`.

- Replace wrapper-oriented help text with console-script-oriented help text.
  This has now been completed for the main runtime/deprecation guidance in [src/oratapi/controller/ora_tapi.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/controller/ora_tapi.py) and [src/oratapi/controller/migrate_config.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/controller/migrate_config.py), and the README now documents console scripts as the primary interface.

- Fix inconsistent module entrypoints.
  This has now been completed in [src/oratapi/__main__.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/__main__.py) and [src/oratapi/controller/__main__.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/controller/__main__.py).

- Deprecate or redesign `update_ora_tapi`.
  In a wheel/PyPI model it should not mutate the installed package tree.
  Likely options:
  - deprecate it entirely
  - repurpose it to upgrade runtime content only
  - replace with documentation pointing users to `pip install --upgrade`

- Review whether any remaining secondary docs/examples should keep showing wrapper-script forms, or whether they should be reduced further.

## Runtime Path And Resource-Loading Changes Required

- Core resource loading is already mostly correct.
  [src/oratapi/lib/fsutils.py](/home/clive/PycharmProjects/OraTAPI/src/oratapi/lib/fsutils.py) is the right pattern for wheel installs.

- Packaged defaults should continue to be located only through `resolve_default_path(...)`.
  That part should stay.

- Runtime files should continue to be resolved only through `resolve_path(...)`.
  That part should also stay.

- The bootstrap command should remain explicit.
  Best fit:
  keep `quick_config` as the init step, or add an alias such as `oratapi-init` that calls the same logic.

- Remove the concept of “chosen installation directory” from the user-facing model.
  In a wheel install, the Python environment owns the package location.

- Update any docs/help text that refer to install-root-relative assets.
  That includes the Oracle Instant Client guidance.

## Risks, Drawbacks, And Edge Cases

- End users lose the visible extracted install tree.
  Some current workflows assume “cd into install dir and run scripts”.

- `update_ora_tapi` becomes the wrong upgrade mechanism.

- Shell wrappers become secondary or obsolete in a wheel install.
  That may confuse existing users if not documented carefully.

- Root-level `resources/` duplication can drift from packaged resource data.

- First-run automatic bootstrap is a bad fit.
  It would create runtime state implicitly and still would not eliminate the need to choose or activate a profile.

- Offline installs may still want an sdist/archive flow, even if PyPI/wheel becomes the default.

## Migration Steps Needed

1. Keep packaged defaults inside the installable package and treat them as the only authoritative defaults.
2. Continue consolidating duplicated resources, especially the template tree.
3. Keep `quick_config` as the explicit bootstrap step, or add a clearer alias.
4. Deprecate `setup.sh`, `setup.ps1`, and `update_ora_tapi` for the wheel/PyPI path.
5. Keep `profile_mgr --migrate-old` as the migration bridge from existing extracted installs.
6. Update docs to describe:
   - `pip install oratapi`
   - `quick_config` or `oratapi-init`
   - `ora_tapi` / `profile_mgr` / `conn_mgr`
   - `pip install --upgrade oratapi`

## Recommended Implementation Order

1. Formalize bootstrap as an explicit post-install step.
   Reuse `quick_config` or wrap it in a clearer init command.

2. Remove mutable-install assumptions.
   Deprecate `setup.sh`, `setup.ps1`, and `update_ora_tapi` for wheel installs.

3. Eliminate resource duplication.
   Pick the packaged resource tree as the single source of truth and simplify the remaining template sample layout.

4. Add migration guidance for existing users.
   Keep `profile_mgr --migrate-old` as the bridge from extracted installs.

5. Only then publish to PyPI.
   The namespace cleanup and console-script-first documentation are now in place, so the remaining blockers are mainly mutable-install assumptions and resource-tree cleanup.

## Recommendation

Proceed with the wheel model, but do not publish to PyPI until the mutable-install tooling question is settled and the duplicated packaged-resource trees are consolidated.

That recommendation should now be read as:

- the namespace cleanup has been completed
- the wheel-first and console-script-first documentation work has been completed
- the next work should focus on removal or redesign of mutable-install tooling and consolidation of packaged resources before public PyPI publication
