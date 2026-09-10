# Author: cbostock / DGGIU
# Created: 10-Sep-2026
# Verify CLI template definitions, validation boundaries and generated output.

from configparser import ConfigParser
from copy import deepcopy
import re
import shlex
import shutil
import sys
from types import SimpleNamespace

import pytest

from oratapi.controller.ora_tapi import CodeManager, warn_on_default_profile_identity
from oratapi.lib.config_mgr import ConfigManager
from oratapi.lib.fsutils import profile_home, resolve_default_path, write_active_profile
from oratapi.lib import template_overrides
from oratapi.lib.template_overrides import (
    LOWERCASE_METADATA_NAMES, METADATA_NAMES, PROTECTED_NAMES,
    apply_template_overrides, discover_template_names, parse_template_definitions,
)
from oratapi.model import tapi_generator, utplsql_generator
from oratapi.model.tapi_generator import ApiGenerator, inject_values
from oratapi.model.utplsql_generator import UtPLSQLGenerator
from oratapi.view.interactions import Interactions


@pytest.fixture
def profile(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    write_active_profile("override_test")
    root = profile_home("override_test")
    shutil.copytree(resolve_default_path("resources"), root / "resources")
    config_path = root / "resources/config/OraTAPI.ini"
    config = ConfigParser(interpolation=None)
    config.read(config_path)
    config.set("ut_controls", "enable_ut_code_generation", "true")
    config.set("ut_controls", "ut_suite", "ProfileSuite")
    config.set("ut_controls", "ut_prod_code", "ProfileProduct")
    config.set("ut_controls", "ut_prod_sub_domain_code", "auto_table")
    config.set("api_controls", "auto_maintained_cols", "name")
    config.set("api_controls", "row_vers_column_name", "")
    config.set("api_controls", "col_auto_maintain_method", "expression")
    config.set("api_controls", "signature_types", "coltype")
    config.set("api_controls", "api_surface", "view")
    config.set("api_controls", "return_pk_columns", "false")
    config.set("api_controls", "return_ak_columns", "false")
    config.set("api_controls", "noop_column_string", "")
    config.add_section("custom")
    config.set("custom", "release_label", "ProfileRelease")
    with config_path.open("w", encoding="utf-8") as stream:
        config.write(stream)
    return root, config_path


def test_definition_values_and_last_occurrence_win(tmp_path):
    result = parse_template_definitions([
        "ut_suite=first", "company_name=  A=B, C  ", "ut_suite=", "tapi_author=Mixed Case",
    ], tmp_path)
    assert result == {"ut_suite": "", "company_name": "  A=B, C  ", "tapi_author": "Mixed Case"}


@pytest.mark.parametrize("definition", ["ut_suite", "=x", "%ut_suite%=x", "ut_controls.ut_suite=x", "ut-suite=x", "9name=x", "ut_suite =x"])
def test_malformed_definitions(definition, tmp_path):
    with pytest.raises(ValueError, match="use --define NAME=VALUE"):
        parse_template_definitions([definition], tmp_path)


@pytest.mark.parametrize("name", [
    "enable_ut_code_generation", "table_name", "table_name_lc", "db_password",
    "table_owner", "package_owner_lc", "api_surface", "ut_pkg_name_prefix_lc",
    "include_commit", "procedure_signature", "status", "STAB", "version",
    "default_app_name", "skip_on_missing_pk",
])
def test_protected_names_stay_protected_in_custom_templates(name, tmp_path):
    (tmp_path / "custom.tpt").write_text(f"%{name}%", encoding="utf-8")
    with pytest.raises(ValueError, match="protected name"):
        parse_template_definitions([f"{name}=override"], tmp_path)


@pytest.mark.parametrize("name,base", LOWERCASE_METADATA_NAMES.items())
def test_derived_metadata_names_require_base_name(name, base, tmp_path):
    with pytest.raises(ValueError, match=f"define '{base}' instead"):
        parse_template_definitions([f"{name}=override"], tmp_path)


def test_custom_names_are_discovered_once_and_match_case(monkeypatch, tmp_path):
    unused = tmp_path / "misc/unused"
    unused.mkdir(parents=True)
    (unused / "header.tpt").write_text("%Release_Label% %release_label%", encoding="utf-8")
    calls = []

    def discover(root):
        calls.append(root)
        return discover_template_names(root)

    monkeypatch.setattr(template_overrides, "discover_template_names", discover)
    assert parse_template_definitions(["Release_Label=Upper", "release_label=lower"], tmp_path) == {
        "Release_Label": "Upper", "release_label": "lower",
    }
    assert calls == [tmp_path]
    with pytest.raises(ValueError, match="Unknown definition 'RELEASE_LABEL'"):
        parse_template_definitions(["RELEASE_LABEL=wrong"], tmp_path)


def test_samples_do_not_qualify_custom_names(tmp_path):
    samples = tmp_path / "packages/spec/samples"
    samples.mkdir(parents=True)
    (samples / "header.tpt").write_text("%sample_only%", encoding="utf-8")
    (tmp_path / "header.tpt.sample").write_text("%sample_only%", encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown definition 'sample_only'"):
        parse_template_definitions(["sample_only=x"], tmp_path)


def test_registry_covers_shipped_configuration_and_template_names():
    config = ConfigParser(interpolation=None)
    config.read(resolve_default_path("resources/config/OraTAPI.ini.sample"))
    known = METADATA_NAMES | PROTECTED_NAMES | LOWERCASE_METADATA_NAMES.keys()
    for section in config.sections():
        assert set(config.options(section)) <= known
    assert discover_template_names(resolve_default_path("resources/templates")) <= known


def test_overrides_are_copied_and_cover_nested_maps():
    source = {"ut_suite": "Default", "nested": {"ut_prod_code_lc": "default"}, "table_name": "EMP"}
    before = deepcopy(source)
    overrides = {"ut_suite": "Agriculture", "ut_prod_code": "AGR"}
    rendered = inject_values(apply_template_overrides(source, overrides), "%ut_suite%|%ut_prod_code_lc%|%table_name%")
    assert rendered == "Agriculture|agr|EMP"
    assert source == before
    assert overrides == {"ut_suite": "Agriculture", "ut_prod_code": "AGR"}


@pytest.mark.parametrize("arguments", [
    '-A Default -a Default -D app_name="A=B, September release" --define tapi_author=Writer',
    '-D app_name="A=B, September release" --define tapi_author=Writer -A Default -a Default',
])
def test_cli_keeps_definitions_separate_from_control_options(profile, monkeypatch, arguments):
    _, config_path = profile
    monkeypatch.setattr(sys, "argv", ["oratapi", "-c", "unused", *shlex.split(arguments)])
    view = Interactions(controller=None, config_file_path=config_path)
    assert view.args_dict["app_name"] == "Default"
    assert view.args_dict["tapi_author"] == "Default"
    assert "define" not in view.args_dict
    assert "template_overrides" not in view.args_dict
    result = inject_values(apply_template_overrides(view.args_dict, view.template_overrides), "%app_name%|%tapi_author_lc%")
    assert result == "A=B, September release|writer"


@pytest.mark.parametrize("definition", ["enable_ut_code_generation=true", "table_name=OTHER_TABLE", "typo=x", "ut_suite"])
def test_invalid_cli_definitions_stop_before_connection_or_output(profile, monkeypatch, capsys, definition):
    root, _ = profile
    before = {file: file.read_bytes() for file in root.rglob("*") if file.is_file()}
    def unexpected(*args, **kwargs):
        pytest.fail("Invalid definitions must not reach connection setup or output creation")
    monkeypatch.setattr("oratapi.controller.ora_tapi.DBSession", unexpected)
    monkeypatch.setattr("oratapi.controller.ora_tapi.UserSecurity", unexpected)
    monkeypatch.setattr(Interactions, "write_file", unexpected)
    monkeypatch.setattr(sys, "argv", ["oratapi", "-c", "unused", "-D", definition])
    with pytest.raises(SystemExit) as exc:
        CodeManager()
    assert exc.value.code == 2
    assert definition.split("=")[0] in capsys.readouterr().err
    assert {file: file.read_bytes() for file in root.rglob("*") if file.is_file()} == before
    assert not (root.parents[1] / "staging").exists()


class _StubTable:
    def __init__(self, table_owner, table_name, **kwargs):
        self.schema_name_lc = table_owner.lower()
        self.table_name = table_name.upper()
        self.table_name_lc = table_name.lower()
        self.columns_list = ["ID", "NAME"]
        self.pk_columns_list_lc = ["id"]
        self.in_out_column_list = []
        self.row_vers_column_name = ""

    @staticmethod
    def is_identity(column_name):
        return False


def _stub_constraints(**kwargs):
    return SimpleNamespace(
        fk_tables="", constraint_list=["DEMO_PK"],
        constraint_metadata_dict={"DEMO_PK": {
            "constraint_name_lc": "demo_pk", "cons_columns": "ID", "constraint_type": "P",
        }},
    )


def _write_probe_templates(root):
    probe = "%app_name%|%tapi_author%|%company_name%|%copyright_year%|%release_label%|%ut_prod_code_lc%"
    templates = root / "resources/templates"
    for category in ("packages", "ut_packages"):
        for kind in ("spec", "body"):
            for name in ("package_header", "package_footer"):
                (templates / category / kind / f"{name}.tpt").write_text(
                    f"-- {category}/{kind}/{name}: {probe}\n", encoding="utf-8"
                )
    header = templates / "ut_packages/spec/package_header.tpt"
    with header.open("a", encoding="utf-8") as stream:
        stream.write("--%suite(%ut_suite%)\n--%suitepath(%ut_prod_code_lc%.%ut_prod_sub_domain_code%)\n")
    for kind in ("body", "spec"):
        for name in ("api_test", "constraint_test"):
            (templates / "ut_packages" / kind / f"{name}.tpt").write_text(
                f"-- {name}: {probe}\nprocedure %procedure_name%;\n", encoding="utf-8"
            )
    for name in ("before", "after"):
        (templates / "ut_packages/body" / f"{name}.tpt").write_text(f"-- {name}: {probe}\n", encoding="utf-8")
    (templates / "packages/procedures/insert.tpt").write_text(
        f"-- procedure: {probe}\ninsert into %table_name_lc% values (%parameter_list_string_lc%);\n", encoding="utf-8"
    )
    (templates / "misc/view/view.tpt").write_text(
        f"-- view: {probe}\nselect %column_list_string_lc% from %table_name_lc%;\n", encoding="utf-8"
    )
    (templates / "misc/trigger/table_name_biu.tpt").write_text(
        f"-- trigger: {probe}\n-- table %table_name_lc%\n", encoding="utf-8"
    )
    for kind in ("inserts", "updates"):
        (templates / "column_expressions" / kind / "name.tpt").write_text("'%release_label%'", encoding="utf-8")


def test_generators_render_overrides_consistently_and_preserve_profiles(profile, monkeypatch):
    root, config_path = profile
    _write_probe_templates(root)
    monkeypatch.setattr(tapi_generator, "Table", _StubTable)
    monkeypatch.setattr(utplsql_generator, "Table", _StubTable)
    monkeypatch.setattr(utplsql_generator, "TableConstraints", _stub_constraints)
    # Keep database-dependent signature/SQL assembly small while exercising the
    # real constructors, template readers, expression selection and render passes.
    monkeypatch.setattr(ApiGenerator, "_insert_api_sig", lambda self, **kwargs: "procedure ins;\n")
    monkeypatch.setattr(ApiGenerator, "_column_list_string", lambda self, **kwargs: "id, name")
    monkeypatch.setattr(ApiGenerator, "_logger_appends", lambda self, **kwargs: "")
    monkeypatch.setattr(ApiGenerator, "_parameter_list_string", lambda self, **kwargs: self._column_expression("coltype", "create", "name"))

    definitions = [
        "app_name=RunApp", "tapi_author=Writer", "company_name=RunCompany",
        "copyright_year=2099", "ut_suite=Agriculture", "ut_prod_code=AGR",
        "ut_prod_sub_domain_code=applications", "release_label=RunRelease",
    ]
    overrides = parse_template_definitions(definitions, root / "resources/templates")
    expected = "RunApp|Writer|RunCompany|2099|RunRelease|agr"
    options = {
        "app_name": "CLIApp", "tapi_author": "CLIAuthor", "package_owner": "LOGIC",
        "view_owner": "LOGIC", "trigger_owner": "CORE", "api_types": ["insert"],
        "ut_api_types": ["insert"],
    }
    options_before = deepcopy(options)
    # Prevent the existing CSV manager from creating a file during construction.
    csv_path = root / "resources/config/OraTAPI.csv"
    if not csv_path.exists():
        csv_path.write_text("Schema Name,Table Name,Domain,Packages Enabled,Views Enabled,Triggers Enabled\n", encoding="utf-8")
    files_before = {file: file.read_bytes() for file in root.rglob("*") if file.is_file()}

    def generate(table, definitions=None):
        config = ConfigManager(config_file_path=config_path)
        config_before = deepcopy(config.config_dictionary())
        api = ApiGenerator(object(), "AGR_CORE", table, config, options, template_overrides=definitions)
        ut = UtPLSQLGenerator(object(), "AGR_CORE", table, config, options, template_overrides=definitions)
        api.load_column_expressions()
        result = {
            "spec": api.gen_package_spec(), "body": api.gen_package_body(),
            "ut_spec": ut.gen_package_spec(), "ut_body": ut.gen_package_body(),
            **api.gen_views(), **api.gen_triggers(),
        }
        assert config.config_dictionary() == config_before
        assert api.options_dict == options_before
        assert api.config_manager.config_value("custom", "release_label") == "ProfileRelease"
        assert api.api_target_name_lc == table.lower() + "_v"
        return result

    baseline = generate("AGR_FIRST")
    for table in ("AGR_FIRST", "PAY_SECOND"):
        output = generate(table, overrides)
        for text in output.values():
            assert expected in text
            assert not re.search(r"%(?:app_name|tapi_author|company_name|copyright_year|release_label|ut_prod_code_lc)%", text)
            assert "RunRelease" in text
            assert "ProfileRelease" not in text
        assert f"insert into {table.lower()}_v values ('RunRelease');" in output["body"]
        assert f"from {table.lower()};" in output[f"{table.lower()}_v.sql"]
        assert f"-- table {table.lower()}" in output[f"{table.lower()}_biu.sql"]
        assert "--%suite(Agriculture)\n--%suitepath(agr.applications)" in output["ut_spec"]
        assert f"-- before: {expected}" in output["ut_body"]
        assert f"-- after: {expected}" in output["ut_body"]
        assert f"-- api_test: {expected}" in output["ut_body"]
        assert f"-- constraint_test: {expected}" in output["ut_body"]
    assert generate("AGR_FIRST", {}) == baseline
    assert generate("AGR_FIRST") == baseline
    assert options == options_before
    assert {file: file.read_bytes() for file in root.rglob("*") if file.is_file()} == files_before


def test_special_looking_values_remain_text(tmp_path):
    overrides = parse_template_definitions(["copyright_year=current", "ut_prod_sub_domain_code=auto_table"], tmp_path)
    substitutions = {"copyright_year": "2026", "ut_prod_sub_domain_code": "AGR"}
    assert inject_values(apply_template_overrides(substitutions, overrides), "%copyright_year%|%ut_prod_sub_domain_code%") == "current|auto_table"


@pytest.mark.parametrize("overrides,expected_names", [
    ({}, ["project.default_app_name", "copyright.company_name"]),
    ({"app_name": "RunApp"}, ["copyright.company_name"]),
    ({"app_name": "RunApp", "company_name": "RunCompany"}, []),
])
def test_identity_warning_does_not_claim_overridden_values_are_defaults(profile, overrides, expected_names):
    _, config_path = profile
    shutil.copyfile(resolve_default_path("resources/config/OraTAPI.ini.sample"), config_path)
    messages = []
    view = SimpleNamespace(print_console=lambda **kwargs: messages.append(kwargs["text"]))
    warn_on_default_profile_identity(view, config_path, template_overrides=overrides)
    if not expected_names:
        assert messages == []
    else:
        assert len(messages) == 1
        for name in expected_names:
            assert name in messages[0]
        if "app_name" in overrides:
            assert "project.default_app_name" not in messages[0]
