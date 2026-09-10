# Author: cbostock / DGGIU
# Created: 10-Sep-2026
# Validate named profile bundles and collect isolated generation runs.

from dataclasses import dataclass
from configparser import Error as ConfigError
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
from uuid import uuid4

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

from oratapi import __version__
from oratapi.lib.fsutils import runtime_home
from oratapi.lib.generation_controls import OUTPUT_CATEGORIES, inspect_profile


def simple_name(value, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value):
        raise ValueError(f"{label} must contain only letters, digits, underscores or hyphens: {value!r}")
    if value.upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                         *(f"LPT{i}" for i in range(1, 10))}:
        raise ValueError(f"{label} is a reserved filename: {value!r}")
    return value


def schema_name(value, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_$#]{0,127}", value):
        raise ValueError(f"{label} must be an unquoted Oracle identifier: {value!r}")
    return value


@dataclass(frozen=True)
class Component:
    name: str
    profile: str
    outputs: tuple[str, ...]
    package_owner: str
    view_owner: str
    trigger_owner: str
    tested_tapi_owner: str | None = None

    def command(self, connection: str, source_owner: str, tables: list[str], directory: Path) -> list[str]:
        return [
            sys.executable, '-m', 'oratapi.controller.ora_tapi',
            '--profile', self.profile, '--outputs', *self.outputs,
            '-c', connection, '-To', source_owner, '-t', *tables,
            '-po', self.package_owner, '-vo', self.view_owner, '-to', self.trigger_owner,
            '-g', str(directory), '-G', str(directory),
            '--run-report', str(directory / '.generation-report.json'),
        ]


def load_bundle(name: str) -> list[Component]:
    simple_name(name, 'Bundle name')
    path = runtime_home() / 'bundles' / f'{name}.toml'
    with path.open('rb') as stream:
        data = tomllib.load(stream)
    unknown = set(data) - {'version', 'description', 'components'}
    if unknown:
        raise ValueError('Unknown bundle fields: ' + ', '.join(sorted(unknown)))
    if type(data.get('version', 1)) is not int or data.get('version', 1) != 1:
        raise ValueError('Only bundle version 1 is supported.')
    items = data.get('components')
    if not isinstance(items, list) or not items:
        raise ValueError('A bundle must contain at least one [[components]] entry.')
    components = []
    names = set()
    exclusive_outputs = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('Each component must be a TOML table.')
        unknown = set(item) - {'name', 'profile', 'outputs', 'package_owner', 'view_owner', 'trigger_owner'}
        if unknown:
            raise ValueError('Unknown component fields: ' + ', '.join(sorted(unknown)))
        component_name = simple_name(item.get('name'), 'Component name')
        if component_name.casefold() in names:
            raise ValueError(f'Duplicate component name: {component_name}')
        names.add(component_name.casefold())
        profile = item.get('profile')
        if not isinstance(profile, str):
            raise ValueError(f'Component {component_name}: profile must be a name.')
        outputs = item.get('outputs')
        if (not isinstance(outputs, list) or not outputs
                or any(not isinstance(output, str) or output not in OUTPUT_CATEGORIES for output in outputs)
                or len(set(outputs)) != len(outputs)):
            raise ValueError(f'Component {component_name}: outputs must be a non-empty, unique list of {OUTPUT_CATEGORIES}.')
        # One process has one package owner. Different package families belong in separate components.
        if {'tapi', 'utplsql'} <= set(outputs):
            raise ValueError('Use separate components for TAPI and utPLSQL packages.')
        ancillary = set(outputs) & {'view', 'trigger'}
        if ancillary & exclusive_outputs:
            raise ValueError('Views and triggers must each have only one designated component.')
        exclusive_outputs.update(ancillary)
        try:
            config = inspect_profile(profile, outputs)
        except (OSError, ValueError, KeyError, ConfigError) as exc:
            raise ValueError(f'Component {component_name}, profile {profile!r}: {exc}') from exc
        owners = {}
        for key in ('package_owner', 'view_owner', 'trigger_owner'):
            value = item.get(key, config.config_value('schemas', f'default_{key}', ''))
            owners[key] = schema_name(value, f'{component_name}.{key}')
        tested_owner = None
        if 'utplsql' in outputs:
            value = config.config_value('ut_controls', 'tested_tapi_owner', '').strip()
            if value:
                tested_owner = schema_name(value, f'{component_name}.tested_tapi_owner')
        components.append(Component(component_name, profile, tuple(outputs), **owners,
                                    tested_tapi_owner=tested_owner))
    return components


def _write_summary(path: Path, summary: dict) -> None:
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def _collect_report(directory: Path, record: dict, source_owner: str) -> list[str]:
    """Copy a whitelist of machine results; never copy console output or arbitrary fields."""
    with (directory / '.generation-report.json').open(encoding='utf-8') as stream:
        report = json.load(stream)
    if not isinstance(report, dict) or report.get('profile') != record['profile']:
        raise ValueError('Missing or inconsistent component report.')
    for key, expected in (('source_table_owner', source_owner), ('package_owner', record['package_owner']),
                          ('view_owner', record['view_owner']), ('trigger_owner', record['trigger_owner'])):
        if str(report.get(key, '')).upper() != expected.upper():
            raise ValueError(f'Component report has an inconsistent {key}.')
    if sorted(report.get('outputs', [])) != sorted(record['outputs']):
        raise ValueError('Component report has inconsistent output categories.')
    tested_owner = report.get('tested_tapi_owner')
    if ((tested_owner is not None and not isinstance(tested_owner, str))
            or (tested_owner or '').upper() != (record['tested_tapi_owner'] or '').upper()):
        raise ValueError('Component report has an inconsistent tested TAPI owner.')
    files = []
    for filename in report.get('generated_files', []):
        path = Path(filename).resolve()
        files.append(str(path.relative_to(directory)))
        if not path.is_file():
            raise ValueError('A reported generated file is missing.')
    record['generated_files'] = files
    record['skipped_objects'] = report.get('skipped_objects', [])
    record['counts'] = report.get('counts', {})
    record['generation_status'] = report.get('status')
    tables = report.get('selected_tables')
    if not isinstance(tables, list) or any(not isinstance(table, str) for table in tables):
        raise ValueError('Component report has no valid table selection.')
    return tables


def run_bundle(name: str, connection: str, source_owner: str, tables: list[str],
               staging_root: Path | None = None, dry_run: bool = False, runner=None) -> int:
    schema_name(source_owner, 'Source table owner')
    if not tables:
        raise ValueError('Select at least one table, or use % alone to select all tables.')
    if tables != ['%']:
        for table in tables:
            schema_name(table, 'Table name')
    components = load_bundle(name)  # All configuration preflight precedes filesystem writes.
    root = (staging_root or runtime_home() / 'staging').expanduser()
    if not root.is_absolute():
        root = runtime_home() / root
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid4().hex[:12]
    run_dir = (root / name / run_id).resolve()
    print(f"Bundle: {name}; source table owner: {source_owner}; staging: {run_dir}")
    records = []
    for component in components:
        directory = run_dir / component.name
        print(f"  {component.name}: profile={component.profile}; package_owner={component.package_owner}; "
              f"view_owner={component.view_owner}; trigger_owner={component.trigger_owner}")
        if 'utplsql' in component.outputs:
            print(f"    tested_tapi_owner={component.tested_tapi_owner or 'unspecified (profile references/synonyms)'}")
        if dry_run:
            print('    ' + shlex.join(component.command(connection, source_owner, tables, directory)))
        records.append({
            'name': component.name, 'profile': component.profile, 'outputs': list(component.outputs),
            'package_owner': component.package_owner, 'view_owner': component.view_owner,
            'trigger_owner': component.trigger_owner, 'directory': component.name,
            'tested_tapi_owner': component.tested_tapi_owner,
            'status': 'pending', 'generated_files': [], 'skipped_objects': [],
        })
    if dry_run:
        print('Dry run: no connection opened and no files written. Run directory is provisional.')
        return 0
    run_dir.mkdir(parents=True, exist_ok=False)
    summary_path = run_dir / 'run-summary.json'
    summary = {
        'version': 1, 'oratapi_version': __version__, 'bundle': name, 'run_id': run_id,
        'status': 'running', 'source_table_owner': source_owner,
        'requested_tables': tables, 'selected_tables': None, 'components': records,
    }
    _write_summary(summary_path, summary)
    selected_tables = list(tables)
    execute = runner or subprocess.run
    for component, record in zip(components, records):
        directory = run_dir / component.name
        record['status'] = 'running'
        returncode = 1
        try:
            directory.mkdir()
            _write_summary(summary_path, summary)
            print(f'Generating component {component.name}...', flush=True)
            process = execute(component.command(connection, source_owner, selected_tables, directory), check=False)
            returncode = process.returncode
            record['exit_code'] = returncode
            resolved_tables = _collect_report(directory, record, source_owner)
            if selected_tables != ['%'] and [t.upper() for t in resolved_tables] != [t.upper() for t in selected_tables]:
                raise ValueError('Component report has changed the shared table selection.')
            if returncode == 0 and record['generation_status'] != 'complete':
                raise ValueError('Generation returned success without a complete report.')
            if not resolved_tables and returncode == 0:
                raise ValueError('No tables were selected.')
            if returncode == 0:
                selected_tables = resolved_tables
                summary['selected_tables'] = selected_tables
        except KeyboardInterrupt:
            returncode = 130
            record['error'] = 'Generation interrupted.'
        except (OSError, ValueError, TypeError, KeyError):
            # Do not persist exception text, which may originate from external processes.
            returncode = returncode or 1
            record['error'] = 'Generation failed or did not provide a valid report; inspect the component output.'
        record['status'] = 'complete' if returncode == 0 else 'failed'
        if returncode:
            record['generated_files'] = sorted(
                str(path.relative_to(directory)) for path in directory.rglob('*')
                if path.is_file() and path.name != '.generation-report.json'
            )
            summary['status'] = 'incomplete'
            _write_summary(summary_path, summary)
            print(f'Bundle incomplete at {component.name}. Partial output and summary: {summary_path}')
            return 130 if returncode == 130 else 1
        _write_summary(summary_path, summary)
    summary['status'] = 'complete'
    _write_summary(summary_path, summary)
    print(f'Bundle complete. Summary: {summary_path}')
    return 0
