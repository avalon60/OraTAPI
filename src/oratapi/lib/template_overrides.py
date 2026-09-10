# Author: cbostock / DGGIU
# Created: 10-Sep-2026
# Validate per-run template definitions and overlay them on rendering substitutions.

from collections.abc import Iterable, Mapping
from copy import deepcopy
from pathlib import Path
import re
from typing import Any


METADATA_NAMES = frozenset({
    "app_name", "tapi_author", "company_name", "copyright_year",
    "ut_suite", "ut_prod_code", "ut_prod_sub_domain_code",
})
LOWERCASE_METADATA_NAMES = {f"{name}_lc": name for name in METADATA_NAMES}

# Built-in configuration/CLI controls and generator-owned substitutions. Keep new
# control and SQL-fragment names here so custom templates cannot override them.
_PROTECTED_BASE_NAMES = frozenset("""
    default_app_name skip_on_missing_table skip_on_missing_pk
    enable_tapis_when_ut_enabled check_pypi_for_updates check_github_for_updates
    indent_spaces STAB default_staging_dir default_ut_staging_dir body_file_ext
    spec_file_ext sig_file_ext spec_dir body_dir trigger_dir view_dir
    ora_tapi_csv_dir pi_columns_csv_dir api_surface delete_procname select_procname
    insert_procname merge_procname update_procname upsert_procname
    col_auto_maintain_method auto_maintained_cols row_vers_column_name
    signature_types include_defaults noop_column_string default_api_types
    tapi_pkg_name_prefix tapi_pkg_name_postfix return_pk_columns return_ak_columns
    return_pk_key_columns return_ak_key_columns
    include_commit enable_ut_code_generation ut_pkg_name_prefix ut_pkg_name_postfix
    ut_uk_test_throws ut_parent_fk_test_throws ut_cc_test_throws ut_nn_test_throws
    logger_pkg logger_logs skip_logged_data_types skip_logged_data_types_mode
    default_table_owner default_package_owner default_view_owner default_trigger_owner
    view_name_suffix info_colour warn_colour err_colour crit_colour high_colour
    success_colour colour_console help conn_name dsn oracle_client_dir staging_dir
    ut_staging_dir db_username db_password table_owner package_owner trigger_owner
    view_owner table_names api_types ut_api_types config_file_path version trace
    define template_overrides active_profile profile outputs run_report run_id run_date_time
    api_target_name api_target_owner base_table_name table_name table_domain
    api_type api_type_desc column_list_string fk_tables ins_returning_clause
    key_predicates_string logger_params_append mrg_param_alias_list
    mrg_predicates_string mrg_src_column_list_string parameter_list_string
    procedure_basename procedure_name procedure_signature procname returning_clause
    table_desc_title throws_code upd_returning_clause update_assignments_string
    cons_columns constraint_name constraint_name_desc constraint_type
    constraint_type_desc search_condition r_owner r_constraint_name status
""".split())
PROTECTED_NAMES = _PROTECTED_BASE_NAMES | frozenset(
    f"{name}_lc" for name in _PROTECTED_BASE_NAMES
)

_NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_PLACEHOLDER_PATTERN = re.compile(r"%([A-Za-z_][A-Za-z0-9_]*)%")


def discover_template_names(template_root: Path) -> set[str]:
    """Read instantiated templates once, including those not selected this run."""
    names = set()
    for template in template_root.rglob("*.tpt"):
        if any(part.lower() in {"sample", "samples"}
               for part in template.relative_to(template_root).parts[:-1]):
            continue
        if template.is_file():
            names.update(_PLACEHOLDER_PATTERN.findall(template.read_text(encoding="utf-8")))
    return names


def parse_template_definitions(definitions: Iterable[str], template_root: Path) -> dict[str, str]:
    """Validate definitions without altering configuration or accessing a database."""
    overrides = {}
    for definition in definitions:
        name, separator, value = definition.partition("=")
        if not separator or not _NAME_PATTERN.fullmatch(name):
            raise ValueError(
                f"Invalid definition name {name!r}: use --define NAME=VALUE with an "
                "identifier such as release_label, without % delimiters or an INI section prefix."
            )
        if name in LOWERCASE_METADATA_NAMES:
            raise ValueError(
                f"Cannot define {name!r}: define {LOWERCASE_METADATA_NAMES[name]!r} instead; "
                "its lower-case substitution is derived automatically."
            )
        if name in PROTECTED_NAMES:
            guidance = "use --define app_name=VALUE" if name == "default_app_name" else (
                "use the corresponding OraTAPI.ini setting or supported CLI option; "
                "generator-owned identifiers and SQL fragments cannot be overridden"
            )
            raise ValueError(f"Cannot define protected name {name!r}: {guidance}.")
        overrides[name] = value

    if overrides:
        template_names = discover_template_names(template_root)
        for name in overrides:
            if name not in METADATA_NAMES and name not in template_names:
                raise ValueError(
                    f"Unknown definition {name!r}: check the spelling or add %{name}% "
                    "to an instantiated .tpt file in the active profile's templates directory."
                )
    return overrides


def apply_template_overrides(
    substitutions: Mapping[str, Any], overrides: Mapping[str, str],
) -> dict[str, Any]:
    """Copy a rendering map and give definitions precedence, including nested maps."""
    effective_overrides = dict(overrides)
    for name, value in overrides.items():
        if name in METADATA_NAMES:
            effective_overrides[f"{name}_lc"] = value.lower()

    def overlay(source: Mapping[str, Any]) -> dict[str, Any]:
        result = {name: overlay(value) if isinstance(value, dict) else deepcopy(value)
                  for name, value in source.items()}
        result.update(effective_overrides)
        return result

    return overlay(substitutions)
