# Author: cbostock / DGGIU
# Created: 10-Sep-2026
# Exercise profile bundles, schema isolation, generation reports and CLI compatibility.

from configparser import ConfigParser
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from oratapi.controller import ora_tapi
from oratapi.lib import fsutils, orchestration
from oratapi.lib.config_mgr import ConfigManager
from oratapi.lib.generation_controls import inspect_profile, select_outputs
from oratapi.model import tapi_generator, utplsql_generator
from oratapi.model.tapi_generator import ApiGenerator
from oratapi.view.interactions import Interactions


PROJECT = Path(__file__).resolve().parents[1]


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    root = tmp_path / 'runtime'
    monkeypatch.setattr(fsutils, 'runtime_home', lambda: root)
    monkeypatch.setattr(orchestration, 'runtime_home', lambda: root)
    monkeypatch.setattr(ora_tapi, 'runtime_home', lambda: root)
    return root


def make_profile(runtime, name, owner='DEFAULT_API', ut=False, surface='table', prefix=''):
    root = runtime / 'configs' / name
    shutil.copytree(fsutils.resolve_default_path('resources'), root / 'resources')
    path = root / 'resources/config/OraTAPI.ini'
    config = ConfigParser(interpolation=None)
    config.read(path)
    changes = {
        'schemas': {'default_table_owner': 'STALE_CORE', 'default_package_owner': owner,
                    'default_view_owner': 'DEFAULT_VIEWS', 'default_trigger_owner': 'DEFAULT_TRIGGERS'},
        'ut_controls': {'enable_ut_code_generation': str(ut), 'ut_pkg_name_prefix': 'ut_',
                        'ut_pkg_name_postfix': '_tapi', 'tested_tapi_owner': 'API_SCHEMA' if ut else ''},
        'behaviour': {'enable_tapis_when_ut_enabled': 'false', 'check_pypi_for_updates': 'false',
                      'check_github_for_updates': 'false'},
        'file_controls': {'spec_dir': 'package_spec', 'body_dir': 'package_body',
                          'spec_file_ext': '.sql', 'body_file_ext': '.sql'},
        'api_controls': {'default_api_types': 'insert', 'signature_types': 'coltype',
                         'api_surface': surface, 'tapi_pkg_name_prefix': prefix,
                         'tapi_pkg_name_postfix': '_tapi', 'row_vers_column_name': '',
                         'auto_maintained_cols': '', 'col_auto_maintain_method': 'trigger',
                         'return_pk_columns': 'false', 'return_ak_columns': 'false',
                         'noop_column_string': '', 'include_commit': 'false',
                         'insert_procname': 'create_row' if prefix else 'ins'},
    }
    for section, values in changes.items():
        for key, value in values.items():
            config.set(section, key, value)
    with path.open('w', encoding='utf-8') as stream:
        config.write(stream)
    return root


def write_bundle(runtime, entries, name='demo'):
    directory = runtime / 'bundles'
    directory.mkdir(parents=True, exist_ok=True)
    text = 'version = 1\n'
    for entry in entries:
        text += '\n[[components]]\n'
        text += ''.join(f'{key} = {json.dumps(value)}\n' for key, value in entry.items())
    (directory / f'{name}.toml').write_text(text, encoding='utf-8')


@pytest.fixture
def bundle(runtime):
    make_profile(runtime, 'api', surface='view')
    make_profile(runtime, 'du', owner='DATA_UTILITY', prefix='du_')
    make_profile(runtime, 'tests', owner='UNIT_TEST', ut=True)
    entries = [
        {'name': 'tapi', 'profile': 'api', 'outputs': ['tapi', 'view', 'trigger'],
         'package_owner': 'API_SCHEMA', 'view_owner': 'API_SCHEMA', 'trigger_owner': 'SOURCE_CORE'},
        {'name': 'utility', 'profile': 'du', 'outputs': ['tapi']},
        {'name': 'tests', 'profile': 'tests', 'outputs': ['utplsql']},
    ]
    write_bundle(runtime, entries)
    (runtime / 'active_config').write_text('api', encoding='utf-8')
    return entries


def snapshot(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob('*') if path.is_file()}


def test_dry_run_has_no_side_effects(runtime, bundle, capsys):
    before = snapshot(runtime)
    def unexpected(*args, **kwargs):
        pytest.fail('Dry run must not start a generation process')
    assert orchestration.run_bundle('demo', 'named', 'SOURCE_CORE', ['DEMO'], dry_run=True, runner=unexpected) == 0
    assert snapshot(runtime) == before
    output = capsys.readouterr().out
    assert 'package_owner=API_SCHEMA' in output
    assert 'package_owner=DATA_UTILITY' in output
    assert 'package_owner=UNIT_TEST' in output
    assert 'tested_tapi_owner=API_SCHEMA' in output
    assert '--profile tests' in output
    assert '-To SOURCE_CORE' in output
    assert not (runtime / 'staging').exists()


def test_component_owner_overrides_are_independent(runtime, bundle):
    components = orchestration.load_bundle('demo')
    assert [item.package_owner for item in components] == ['API_SCHEMA', 'DATA_UTILITY', 'UNIT_TEST']
    assert [item.view_owner for item in components] == ['API_SCHEMA', 'DEFAULT_VIEWS', 'DEFAULT_VIEWS']
    assert [item.tested_tapi_owner for item in components] == [None, None, 'API_SCHEMA']
    for item in components:
        command = item.command('named', 'SOURCE_CORE', ['DEMO'], runtime / 'output')
        assert command[0] == sys.executable
        assert command[command.index('-po') + 1] == item.package_owner
        assert command[command.index('-To') + 1] == 'SOURCE_CORE'


def test_tested_owner_is_never_inferred_from_source_or_test_owner(runtime, bundle):
    path = runtime / 'configs/tests/resources/config/OraTAPI.ini'
    config = ConfigParser(interpolation=None)
    config.read(path)
    config.remove_option('ut_controls', 'tested_tapi_owner')
    with path.open('w') as stream:
        config.write(stream)
    component = orchestration.load_bundle('demo')[-1]
    assert component.package_owner == 'UNIT_TEST'
    assert component.tested_tapi_owner is None


@pytest.mark.parametrize('problem', ['missing_profile', 'disabled', 'duplicate_name', 'duplicate_view',
                                   'mixed_packages', 'invalid_owner', 'absolute_dir', 'parent_dir',
                                   'overlap', 'bad_prefix', 'missing_template', 'unknown_field'])
def test_invalid_bundle_fails_before_staging(runtime, bundle, problem):
    if problem == 'missing_profile':
        bundle[-1]['profile'] = 'absent'
    elif problem == 'disabled':
        bundle[0]['outputs'] = ['utplsql']
    elif problem == 'duplicate_name':
        bundle[-1]['name'] = 'tapi'
    elif problem == 'duplicate_view':
        bundle[1]['outputs'].append('view')
    elif problem == 'mixed_packages':
        bundle[0]['outputs'].append('utplsql')
    elif problem == 'invalid_owner':
        bundle[-1]['package_owner'] = 'wrong.schema'
    elif problem == 'unknown_field':
        bundle[-1]['package_owmer'] = 'TYPO'
    elif problem == 'missing_template':
        (runtime / 'configs/tests/resources/templates/ut_packages/body/api_test.tpt').unlink()
    else:
        path = runtime / 'configs/tests/resources/config/OraTAPI.ini'
        config = ConfigParser(interpolation=None)
        config.read(path)
        if problem == 'bad_prefix':
            config.set('ut_controls', 'ut_pkg_name_prefix', '../')
        else:
            value = {'absolute_dir': '/outside', 'parent_dir': '../outside', 'overlap': 'package_body'}[problem]
            config.set('file_controls', 'spec_dir', value)
        with path.open('w') as stream:
            config.write(stream)
    write_bundle(runtime, bundle)
    before = snapshot(runtime)
    with pytest.raises(ValueError):
        orchestration.run_bundle('demo', 'named', 'SOURCE_CORE', ['DEMO'])
    assert snapshot(runtime) == before


@pytest.mark.parametrize('name', ['../demo', '/tmp/demo', 'demo/other', '', 'NUL'])
def test_bundle_name_cannot_escape_runtime(runtime, name):
    with pytest.raises(ValueError):
        orchestration.load_bundle(name)
    assert not runtime.exists()


def test_bad_toml_and_bad_csv_are_preflight_errors(runtime):
    root = make_profile(runtime, 'api')
    write_bundle(runtime, [{'name': 'api', 'profile': 'api', 'outputs': ['tapi']}])
    csv_path = root / 'resources/config/OraTAPI.csv'
    csv_path.write_text('invalid,header\n')
    with pytest.raises(ValueError, match='CSV header'):
        orchestration.load_bundle('demo')
    (runtime / 'bundles/demo.toml').write_text('version = [')
    with pytest.raises(ValueError):
        orchestration.load_bundle('demo')


@pytest.mark.parametrize('key,value', [('signature_types', 'unknown'), ('default_api_types', 'wrong'),
                                     ('col_auto_maintain_method', 'other'), ('include_commit', 'maybe')])
def test_invalid_profile_controls_fail_preflight(runtime, key, value):
    root = make_profile(runtime, 'api')
    path = root / 'resources/config/OraTAPI.ini'
    config = ConfigParser(interpolation=None)
    config.read(path)
    config.set('api_controls', key, value)
    with path.open('w') as stream:
        config.write(stream)
    with pytest.raises(ValueError):
        inspect_profile('api', ['tapi'])


def test_custom_template_text_is_not_validated_as_boolean(runtime):
    root = make_profile(runtime, 'api')
    path = root / 'resources/config/OraTAPI.ini'
    with path.open('a') as stream:
        stream.write('\n[custom]\ninclude_text = This is descriptive text\n')
    inspect_profile('api', ['tapi'])


@pytest.mark.parametrize('section,key', [('behaviour', 'skip_on_missing_table'),
                                       ('api_controls', 'include_commit'), ('console', 'info_colour')])
def test_missing_profile_settings_fail_before_any_component(runtime, bundle, section, key):
    path = runtime / 'configs/du/resources/config/OraTAPI.ini'
    config = ConfigParser(interpolation=None)
    config.read(path)
    config.remove_option(section, key)
    with path.open('w') as stream:
        config.write(stream)
    before = snapshot(runtime)
    with pytest.raises(ValueError, match='Component utility'):
        orchestration.run_bundle('demo', 'named', 'SOURCE_CORE', ['DEMO'])
    assert snapshot(runtime) == before


def test_optional_profile_defaults_still_work(runtime):
    root = make_profile(runtime, 'api')
    path = root / 'resources/config/OraTAPI.ini'
    config = ConfigParser(interpolation=None)
    config.read(path)
    config.remove_option('api_controls', 'api_surface')
    config.remove_option('api_controls', 'signature_types')
    config.set('logger', 'skip_logged_data_types_mode', 'redact')
    with path.open('w') as stream:
        config.write(stream)
    inspect_profile('api', ['tapi'])


@pytest.mark.parametrize('filename,contents', [
    ('OraTAPI.csv', 'Schema Name,Table Name,Domain,Packages Enabled,Views Enabled,Triggers Enabled\nsource,table\n'),
    ('pi_columns.csv', 'invalid,header\n'),
    ('pi_columns.csv', 'Schema Name,Table Name,Column Name,Description\nsource,table\n'),
])
def test_incomplete_csv_controls_fail_preflight(runtime, filename, contents):
    root = make_profile(runtime, 'api')
    (root / 'resources/config' / filename).write_text(contents)
    with pytest.raises(ValueError, match='CSV'):
        inspect_profile('api', ['tapi'])


def report_runner(calls, fail_at=None, invalid=False):
    def run(command, check):
        assert check is False
        def value(flag):
            return command[command.index(flag) + 1]
        profile = value('--profile')
        calls.append(command)
        directory = Path(value('-g'))
        (directory / 'partial.sql').write_text('-- generated fixture\n')
        outputs = command[command.index('--outputs') + 1:command.index('-c')]
        tables = command[command.index('-t') + 1:command.index('-po')]
        if tables == ['%']:
            tables = ['FIRST', 'SECOND']
        failing = len(calls) == fail_at
        report = {
            'status': 'incomplete' if failing or invalid else 'complete', 'profile': profile,
            'source_table_owner': value('-To'), 'package_owner': value('-po'),
            'view_owner': value('-vo'), 'trigger_owner': value('-to'), 'outputs': outputs,
            'tested_tapi_owner': 'API_SCHEMA' if 'utplsql' in outputs else None,
            'generated_files': [str(directory / 'partial.sql')], 'counts': {},
            'skipped_objects': [], 'selected_tables': tables,
            'db_password': 'must-not-be-copied',
        }
        Path(value('--run-report')).write_text(json.dumps(report))
        return SimpleNamespace(returncode=4 if failing else 0)
    return run


def read_summary(runtime):
    path = next((runtime / 'staging/demo').glob('*/run-summary.json'))
    return path, json.loads(path.read_text())


def test_failure_preserves_partial_output_and_stops(runtime, bundle):
    calls = []
    assert orchestration.run_bundle('demo', 'named', 'SOURCE_CORE', ['DEMO'],
                                    runner=report_runner(calls, fail_at=2)) == 1
    path, summary = read_summary(runtime)
    assert len(calls) == 2
    assert summary['status'] == 'incomplete'
    assert [item['status'] for item in summary['components']] == ['complete', 'failed', 'pending']
    assert (path.parent / 'utility/partial.sql').exists()
    assert 'must-not-be-copied' not in path.read_text()
    assert (runtime / 'active_config').read_text() == 'api'


@pytest.mark.parametrize('failure', ['missing_report', 'incomplete_report', 'launch', 'interrupt'])
def test_incomplete_or_missing_report_is_not_success(runtime, bundle, failure):
    calls = []
    def run(command, check):
        if failure == 'interrupt':
            raise KeyboardInterrupt
        if failure == 'launch':
            raise OSError('cannot start child')
        if failure == 'missing_report':
            return SimpleNamespace(returncode=0)
        return report_runner(calls, invalid=True)(command, check)
    assert orchestration.run_bundle('demo', 'named', 'SOURCE_CORE', ['DEMO'], runner=run) != 0
    _, summary = read_summary(runtime)
    assert summary['status'] == 'incomplete'
    assert summary['components'][1]['status'] == 'pending'


def test_wildcard_is_resolved_by_first_child_then_shared(runtime, bundle):
    calls = []
    assert orchestration.run_bundle('demo', 'named', 'SOURCE_CORE', ['%'], runner=report_runner(calls)) == 0
    assert calls[0][calls[0].index('-t') + 1] == '%'
    for command in calls[1:]:
        assert command[command.index('-t') + 1:command.index('-po')] == ['FIRST', 'SECOND']


@pytest.mark.parametrize('field,value', [('selected_tables', ['DIFFERENT']), ('package_owner', 'WRONG_OWNER'),
                                       ('generated_files', ['/outside/component.sql']), ('tested_tapi_owner', 1)])
def test_inconsistent_child_reports_cannot_complete_a_run(runtime, bundle, field, value):
    calls = []
    def run(command, check):
        result = report_runner(calls)(command, check)
        path = Path(command[command.index('--run-report') + 1])
        report = json.loads(path.read_text())
        report[field] = value
        path.write_text(json.dumps(report))
        return result
    assert orchestration.run_bundle('demo', 'named', 'SOURCE_CORE', ['DEMO'], runner=run) == 1
    _, summary = read_summary(runtime)
    assert len(calls) == 1
    assert summary['status'] == 'incomplete'


def test_repeated_runs_do_not_overwrite_earlier_edits(runtime, bundle):
    assert orchestration.run_bundle('demo', 'named', 'SOURCE_CORE', ['DEMO'], runner=report_runner([])) == 0
    path, _ = read_summary(runtime)
    earlier = path.parent / 'tapi/partial.sql'
    earlier.write_text('engineer correction')
    assert orchestration.run_bundle('demo', 'named', 'SOURCE_CORE', ['DEMO'], runner=report_runner([])) == 0
    assert earlier.read_text() == 'engineer correction'
    assert len(list((runtime / 'staging/demo').iterdir())) == 2


class StubTable:
    def __init__(self, table_owner, table_name, **kwargs):
        assert table_owner == 'SOURCE_CORE'
        self.schema_name_lc = table_owner.lower()
        self.table_name = table_name.upper()
        self.table_name_lc = table_name.lower()
        self.columns_list = ['ID', 'NAME']
        self.pk_columns_list_lc = ['id']
        self.in_out_column_list = []
        self.row_vers_column_name = ''

    @staticmethod
    def is_identity(column):
        return False


@pytest.fixture
def simulated_database(monkeypatch):
    # Run real controllers and templates, substituting only database-dependent assembly.
    monkeypatch.setattr(tapi_generator, 'Table', StubTable)
    monkeypatch.setattr(utplsql_generator, 'Table', StubTable)
    monkeypatch.setattr(utplsql_generator, 'TableConstraints', lambda **kwargs: SimpleNamespace(
        fk_tables='SOURCE_CORE.PARENT', constraint_list=['DEMO_PK'],
        constraint_metadata_dict={'DEMO_PK': {
            'constraint_name_lc': 'demo_pk', 'cons_columns': 'ID', 'cons_columns_lc': 'id',
            'constraint_type': 'P', 'constraint_type_desc': 'Primary Key', 'search_condition': '',
        }},
    ))
    monkeypatch.setattr(ApiGenerator, '_insert_api_sig', lambda self, **kw: f"procedure {kw['procedure_name']};\n")
    monkeypatch.setattr(ApiGenerator, '_column_list_string', lambda self, **kw: 'id, name')
    monkeypatch.setattr(ApiGenerator, '_parameter_list_string', lambda self, **kw: "1, 'Lorem ipsum'")
    monkeypatch.setattr(ApiGenerator, '_logger_appends', lambda self, **kw: '')
    monkeypatch.setattr(ora_tapi.CodeManager, 'schema_exists', lambda self, **kw: True)
    monkeypatch.setattr(ora_tapi.CodeManager, 'table_schema_has_tables', lambda self: True)
    monkeypatch.setattr(ora_tapi.CodeManager, 'check_table_exists', lambda self, **kw: kw['table_name'] != 'MISSING')
    monkeypatch.setattr(ora_tapi.CodeManager, 'table_has_pk', lambda self, **kw: kw['table_name'] != 'NO_PK')
    monkeypatch.setattr(ora_tapi.CodeManager, '_report_available_update', lambda *args, **kw: None)
    monkeypatch.setattr(ora_tapi, 'try_init_thick_mode', lambda **kw: None)
    class Session:
        def __init__(self, **kwargs):
            pass
        @staticmethod
        def get_client_mode_info():
            return 'Simulated database'
    monkeypatch.setattr(ora_tapi, 'DBSession', Session)
    connection = SimpleNamespace(authentication_type='password', username='INSPECTOR', password='not-for-reports',
                                 dsn='test-only', wallet_path='', wallet_password='', token_location='')
    monkeypatch.setattr(ora_tapi, 'UserSecurity', lambda **kw: SimpleNamespace(named_connection=lambda **kw: connection))
    monkeypatch.setattr('oratapi.model.ora_tapi_csv.atexit.register', lambda callback: None)


@pytest.mark.parametrize('saved_active_profile', [True, False])
def test_three_schemas_real_controllers_and_templates(runtime, bundle, simulated_database, monkeypatch, saved_active_profile):
    if not saved_active_profile:
        (runtime / 'active_config').unlink()
    # Confirm wrapper filtering still applies when the TAPI profile also enables UT.
    path = runtime / 'configs/api/resources/config/OraTAPI.ini'
    text = path.read_text().replace('enable_ut_code_generation = False', 'enable_ut_code_generation = true')
    path.write_text(text.replace('enable_tapis_when_ut_enabled = false', 'enable_tapis_when_ut_enabled = true'))
    for name in ('api', 'du', 'tests'):
        csv_path = runtime / f'configs/{name}/resources/config/OraTAPI.csv'
        csv_path.write_text('Schema Name,Table Name,Domain,Packages Enabled,Views Enabled,Triggers Enabled\n'
                            'source_core,excluded,Domain,False,False,False\n')
    before = snapshot(runtime)
    calls = []
    def execute(command, check):
        calls.append(command)
        with monkeypatch.context() as child:
            child.setattr(sys, 'argv', ['oratapi', *command[3:]])
            ora_tapi.main()
        return SimpleNamespace(returncode=0)
    assert orchestration.run_bundle('demo', 'named', 'SOURCE_CORE', ['DEMO', 'EXCLUDED', 'MISSING', 'NO_PK'], runner=execute) == 0
    path, summary = read_summary(runtime)
    output = path.parent
    assert 'package api_schema.demo_tapi' in (output / 'tapi/package_spec/demo_tapi.sql').read_text()
    assert 'package data_utility.du_demo_tapi' in (output / 'utility/package_spec/du_demo_tapi.sql').read_text()
    assert 'package unit_test.ut_demo_tapi' in (output / 'tests/package_spec/ut_demo_tapi.sql').read_text()
    assert 'insert into demo_v' in (output / 'tapi/package_body/demo_tapi.sql').read_text()
    assert 'insert into demo\n' in (output / 'utility/package_body/du_demo_tapi.sql').read_text()
    assert 'null;' in (output / 'tests/package_body/ut_demo_tapi.sql').read_text()
    assert not (output / 'utility/view').exists()
    assert not (output / 'tests/trigger').exists()
    assert not list((output / 'tapi').rglob('ut_*.sql'))
    for component in summary['components']:
        assert {item['reason'] for item in component['skipped_objects']} == {'csv_disabled', 'missing_table', 'missing_primary_key'}
        assert component['status'] == 'complete'
    assert 'not-for-reports' not in path.read_text()
    assert summary['source_table_owner'] == 'SOURCE_CORE'
    assert summary['components'][-1]['package_owner'] == 'UNIT_TEST'
    assert summary['components'][-1]['tested_tapi_owner'] == 'API_SCHEMA'
    if saved_active_profile:
        assert (runtime / 'active_config').read_text() == 'api'
    else:
        assert not (runtime / 'active_config').exists()
    for filename, contents in before.items():
        assert (runtime / filename).read_bytes() == contents


def test_process_profile_selection_without_active_config(runtime, bundle, monkeypatch, capsys):
    (runtime / 'active_config').unlink()
    monkeypatch.setattr(sys, 'argv', ['oratapi', '--profile=du', '--help'])
    with pytest.raises(SystemExit) as result:
        ora_tapi.main()
    assert result.value.code == 0
    assert 'DATA_UTILITY' in capsys.readouterr().out
    assert fsutils.selected_profile_name() is None
    assert not (runtime / 'active_config').exists()


def test_explicit_profile_is_visible_in_subprocess_help(runtime, bundle):
    script = (
        'import sys; from pathlib import Path; from oratapi.lib import fsutils; '
        'fsutils.runtime_home = lambda root=Path(sys.argv[1]): root; '
        'sys.argv = ["oratapi", "--profile", "du", "--help"]; '
        'from oratapi.controller.ora_tapi import main; main()'
    )
    env = dict(os.environ, PYTHONPATH=str(PROJECT / 'src'))
    result = subprocess.run([sys.executable, '-c', script, str(runtime)], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'DATA_UTILITY' in result.stdout
    assert (runtime / 'active_config').read_text() == 'api'


@pytest.mark.parametrize('selected,enabled', [('api', ('tapi', 'view', 'trigger')), ('tests', ('utplsql',))])
def test_filter_does_not_enable_disabled_generation(runtime, bundle, selected, enabled):
    config = ConfigManager(runtime / f'configs/{selected}/resources/config/OraTAPI.ini')
    assert select_outputs(config) == enabled
    with pytest.raises(ValueError, match='disabled'):
        select_outputs(config, ['utplsql'] if selected == 'api' else ['tapi'])


def test_write_failure_is_nonzero(tmp_path):
    occupied = tmp_path / 'not_a_directory'
    occupied.write_text('keep')
    view = Interactions.__new__(Interactions)
    view.controller = None
    with pytest.raises(SystemExit) as result:
        view.write_file(occupied, Path('spec'), 'demo.sql', 'code')
    assert result.value.code == 1


@pytest.mark.parametrize('failure', ['missing_schema', 'empty_schema'])
def test_source_schema_failures_exit_nonzero(runtime, bundle, simulated_database, monkeypatch, failure):
    if failure == 'missing_schema':
        monkeypatch.setattr(ora_tapi.CodeManager, 'schema_exists', lambda self, **kw: False)
    else:
        monkeypatch.setattr(ora_tapi.CodeManager, 'table_schema_has_tables', lambda self: False)
    report = runtime / 'failed-generation.json'
    monkeypatch.setattr(sys, 'argv', ['oratapi', '--profile', 'du', '-c', 'named', '-To', 'SOURCE_CORE',
                                    '-t', 'DEMO', '--outputs', 'tapi', '--run-report', str(report)])
    with pytest.raises(SystemExit) as result:
        ora_tapi.main()
    assert result.value.code == 1
    assert json.loads(report.read_text())['status'] == 'incomplete'


def test_packaged_example_matches_source():
    assert (PROJECT / 'resources/bundles/agr.toml.sample').read_bytes() == fsutils.resolve_default_path(
        'resources/bundles/agr.toml.sample').read_bytes()


def test_orchestrator_source_wrappers():
    env = dict(os.environ, ORATAPI_PYTHON=sys.executable)
    result = subprocess.run(['bash', str(PROJECT / 'bin/oratapi_orc.sh'), '--help'],
                            env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert '--bundle' in result.stdout and '--dry-run' in result.stdout
    result = subprocess.run(['bash', str(PROJECT / 'bin/oratapi_orc.sh'), '--unknown'],
                            env=env, text=True, capture_output=True)
    assert result.returncode != 0
    powershell = shutil.which('pwsh')
    if powershell:
        result = subprocess.run([powershell, '-NoProfile', '-File', str(PROJECT / 'bin/oratapi_orc.ps1'), '--help'],
                                env=env, text=True, capture_output=True)
        assert result.returncode == 0, result.stderr
