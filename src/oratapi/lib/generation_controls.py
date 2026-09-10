# Author: cbostock / DGGIU
# Created: 10-Sep-2026
# Resolve output filters and validate generation profiles without side effects.

from pathlib import Path, PureWindowsPath
import csv
import re

from oratapi.lib.config_mgr import ConfigManager
from oratapi.lib.fsutils import RUNTIME_REQUIRED_RELATIVE_PATHS, profile_home, use_profile


OUTPUT_CATEGORIES = ("tapi", "utplsql", "view", "trigger")


def select_outputs(config: ConfigManager, requested=None) -> tuple[str, ...]:
    ut_enabled = config.bool_config_value("ut_controls", "enable_ut_code_generation", False)
    tapi_enabled = not ut_enabled or config.bool_config_value(
        "behaviour", "enable_tapis_when_ut_enabled", False
    )
    allowed = set(OUTPUT_CATEGORIES if tapi_enabled else ())
    if ut_enabled:
        allowed.add("utplsql")
    else:
        allowed.discard("utplsql")
    if requested is not None:
        invalid = set(requested) - allowed
        if invalid:
            raise ValueError("Outputs are unknown or disabled by this profile: " + ", ".join(sorted(invalid)))
        if not requested:
            raise ValueError("At least one output category is required.")
        allowed.intersection_update(requested)
    return tuple(item for item in OUTPUT_CATEGORIES if item in allowed)


def validate_output_layout(config: ConfigManager, outputs) -> None:
    """Ensure component output cannot escape staging or collide across categories."""
    keys = []
    if set(outputs) & {"tapi", "utplsql"}:
        keys.extend(("spec_dir", "body_dir"))
    if "view" in outputs:
        keys.append("view_dir")
    if "trigger" in outputs:
        keys.append("trigger_dir")
    locations = []
    for key in keys:
        value = config.config_value("file_controls", key)
        path = Path(value)
        if (not value.strip() or path.is_absolute() or PureWindowsPath(value).drive
                or ".." in path.parts or "\\" in value or "%" in value or path == Path(".")):
            raise ValueError(f"file_controls.{key} must be a relative staging subdirectory: {value!r}")
        folded = Path(value.casefold())
        if any(folded == previous or folded in previous.parents or previous in folded.parents for previous in locations):
            raise ValueError(f"Overlapping output subdirectories: {value!r}")
        locations.append(folded)
    for key in ("spec_file_ext", "body_file_ext"):
        value = config.config_value("file_controls", key)
        if not re.fullmatch(r"\.[A-Za-z0-9_.-]+", value):
            raise ValueError(f"Invalid file_controls.{key}: {value!r}")
    for section, keys in (("api_controls", ("tapi_pkg_name_prefix", "tapi_pkg_name_postfix")),
                          ("ut_controls", ("ut_pkg_name_prefix", "ut_pkg_name_postfix")),
                          ("misc", ("view_name_suffix",))):
        for key in keys:
            value = config.config_value(section, key, "")
            if not re.fullmatch(r"[A-Za-z0-9_$#]*", value):
                raise ValueError(f"Invalid package filename setting {section}.{key}: {value!r}")


def inspect_profile(name: str, outputs) -> ConfigManager:
    """Read an existing profile, never bootstrapping it or creating its CSV."""
    with use_profile(name):
        root = profile_home(name)
        missing = [str(path) for path in RUNTIME_REQUIRED_RELATIVE_PATHS if not (root / path).is_file()]
        if missing:
            raise ValueError(f"Profile {name!r} is missing required files: " + ", ".join(missing))
        config = ConfigManager(root / "resources/config/OraTAPI.ini")
        # These values are read without defaults by the controller or generators.
        required = {
            'schemas': ('default_table_owner', 'default_package_owner', 'default_view_owner', 'default_trigger_owner'),
            'file_controls': ('default_staging_dir', 'default_ut_staging_dir', 'spec_dir', 'body_dir',
                              'view_dir', 'trigger_dir', 'spec_file_ext', 'body_file_ext'),
            'api_controls': ('default_api_types', 'col_auto_maintain_method', 'row_vers_column_name',
                             'tapi_pkg_name_prefix', 'tapi_pkg_name_postfix'),
            'behaviour': ('skip_on_missing_table',),
            'console': ('colour_console', 'info_colour', 'warn_colour', 'err_colour', 'crit_colour',
                        'high_colour', 'success_colour'),
            'formatting': ('indent_spaces',),
        }
        if set(outputs) & {'tapi', 'view', 'trigger'}:
            required['api_controls'] += ('include_defaults', 'include_commit')
        if 'utplsql' in outputs:
            required['ut_controls'] = ('ut_pkg_name_prefix', 'ut_pkg_name_postfix')
        for section, keys in required.items():
            for key in keys:
                config.config_value(section, key)
        if 'copyright_year' not in config.config_dictionary():
            raise ValueError('Missing copyright_year template setting.')
        # Validate known operational values without interpreting custom template text as controls.
        booleans = {
            'behaviour': ('enable_tapis_when_ut_enabled', 'skip_on_missing_table', 'skip_on_missing_pk',
                          'check_pypi_for_updates', 'check_github_for_updates'),
            'ut_controls': ('enable_ut_code_generation',),
            'api_controls': ('include_defaults', 'include_commit', 'return_pk_columns', 'return_ak_columns',
                             'return_pk_key_columns', 'return_ak_key_columns'),
            'console': ('colour_console',),
        }
        for section, keys in booleans.items():
            for key in keys:
                if config.config.has_option(section, key):
                    config.config.getboolean(section, key)
        if int(config.config_value('formatting', 'indent_spaces')) < 0:
            raise ValueError('formatting.indent_spaces cannot be negative.')
        for key, choices, default in (('api_surface', {'table', 'view'}, 'view'),
                                      ('col_auto_maintain_method', {'trigger', 'expression'}, 'trigger'),
                                      ('signature_types', {'rowtype', 'coltype'}, 'rowtype,coltype'),
                                      ('default_api_types', {'insert', 'select', 'update', 'delete', 'merge', 'upsert'}, None)):
            value = config.config_value('api_controls', key, default)
            if key == 'signature_types':
                value = value.lower()
            values = {item.strip() for item in value.split(',')}
            if not values or not values <= choices:
                raise ValueError(f'Invalid api_controls.{key}: {values}')
        logger_mode = config.config_value('logger', 'skip_logged_data_types_mode', 'omit').strip().lower() or 'omit'
        if logger_mode not in {'omit', 'comment', 'redact'}:
            raise ValueError(f'Invalid logger.skip_logged_data_types_mode: {logger_mode}')
        select_outputs(config, outputs)
        validate_output_layout(config, outputs)
        for path in (root / "resources/templates").rglob("*.tpt"):
            path.read_text(encoding="utf-8")
        csv_dir = Path(config.config_value("file_controls", "ora_tapi_csv_dir", "resources/config")).expanduser()
        csv_path = (csv_dir if csv_dir.is_absolute() else root / csv_dir) / "OraTAPI.csv"
        if not csv_path.parent.is_dir():
            raise ValueError(f'CSV control directory does not exist: {csv_path.parent}')
        if csv_path.exists():
            with csv_path.open(encoding="utf-8", newline="") as stream:
                reader = csv.reader(stream)
                expected = ["Schema Name", "Table Name", "Domain", "Packages Enabled", "Views Enabled", "Triggers Enabled"]
                if next(reader, None) != expected:
                    raise ValueError(f"Invalid CSV header in {csv_path}")
                for row in reader:
                    if row and len(row) < len(expected):
                        raise ValueError(f"Incomplete CSV row at {csv_path}:{reader.line_num}")
        if set(outputs) & {'tapi', 'view', 'trigger'}:
            pi_dir = Path(config.config_value('file_controls', 'pi_columns_csv_dir', 'resources/config')).expanduser()
            pi_path = (pi_dir if pi_dir.is_absolute() else root / pi_dir) / 'pi_columns.csv'
            if not pi_path.parent.is_dir():
                raise ValueError(f'PI CSV control directory does not exist: {pi_path.parent}')
            if pi_path.exists():
                with pi_path.open(encoding='utf-8', newline='') as stream:
                    reader = csv.DictReader(stream)
                    reader.fieldnames = [key.strip().lower().replace(' ', '_') for key in reader.fieldnames or []]
                    required_headers = {'schema_name', 'table_name', 'column_name', 'description'}
                    if not required_headers <= set(reader.fieldnames):
                        raise ValueError(f'Invalid PI CSV header in {pi_path}')
                    for row in reader:
                        if any(row.get(key) is None for key in required_headers):
                            raise ValueError(f'Incomplete PI CSV row at {pi_path}:{reader.line_num}')
        return config
