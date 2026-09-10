# Author: cbostock / DGGIU
# Created: 10-Sep-2026
# Verify connection-manager action arguments without accessing stored credentials.

import sys
from unittest.mock import Mock, call

import pytest

from oratapi.controller import conn_mgr


@pytest.fixture
def manager_class(monkeypatch):
    mocked = Mock()
    monkeypatch.setattr(conn_mgr, "ConnectMgr", mocked)
    return mocked


def run_cli(monkeypatch, *args, program="conn-mgr"):
    monkeypatch.setattr(sys, "argv", [program, *args])
    conn_mgr.main()


@pytest.mark.parametrize("program", ["conn_mgr", "conn-mgr"])
@pytest.mark.parametrize("name", ["dev", "development database"])
@pytest.mark.parametrize("option,expected", [
    ("-c", "create"), ("--create", "create"),
    ("-e", "edit"), ("--edit", "edit"),
    ("-d", "delete"), ("--delete", "delete"),
])
def test_action_dispatch(monkeypatch, manager_class, program, name, option, expected):
    run_cli(monkeypatch, option, name, program=program)
    manager_class.assert_called_once_with(project_identifier="OraTAPI", credential_type="dsn")
    expected_calls = {
        "create": call.create_connection(name, authentication_type="password"),
        "edit": call.edit_connection(name, authentication_type=None),
        "delete": call.delete_connection(name),
    }
    assert manager_class.return_value.mock_calls == [expected_calls[expected]]


@pytest.mark.parametrize("action", ["create", "edit"])
@pytest.mark.parametrize("auth_type", ["password", "oci_iam_token"])
def test_explicit_settings(monkeypatch, manager_class, action, auth_type):
    run_cli(monkeypatch, f"--{action}", "dev", "--auth-type", auth_type, "-t", "url")
    manager_class.assert_called_once_with(project_identifier="OraTAPI", credential_type="url")
    getattr(manager_class.return_value, f"{action}_connection").assert_called_once_with(
        "dev", authentication_type=auth_type,
    )


@pytest.mark.parametrize("args", [
    [],
    *[[flag] for flag in ("-c", "--create", "-e", "--edit", "-d", "--delete")],
    *[[flag, ""] for flag in ("-c", "--create", "-e", "--edit", "-d", "--delete")],
    ["-c", "dev", "-e", "dev"],
    ["-c", "dev", "-d", "dev"],
    ["-e", "dev", "-d", "dev"],
    ["-c", "dev", "-l"],
    ["-e", "dev", "-l"],
    ["-d", "dev", "-l"],
    ["-c", "-n", "dev"],
    ["--create", "--name", "dev"],
    ["-c", "dev", "-n", "other"],
    ["--create", "dev", "--name", "other"],
])
def test_invalid_arguments_do_not_open_store(monkeypatch, manager_class, capsys, args):
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, *args)
    assert exc.value.code == 2
    assert "usage:" in capsys.readouterr().err
    manager_class.assert_not_called()


@pytest.mark.parametrize("option", ["-l", "--list"])
@pytest.mark.parametrize("extra", [[], ["-C"], ["--print-creds"]])
def test_list(monkeypatch, manager_class, option, extra):
    run_cli(monkeypatch, option, *extra)
    assert manager_class.return_value.mock_calls == [
        call.list_connections(inc_creds=bool(extra)),
    ]


def test_print_creds_without_list_retains_error(monkeypatch, manager_class, capsys):
    run_cli(monkeypatch, "-c", "dev", "-C")
    assert "Error: --print-creds must be used with --list." in capsys.readouterr().out
    assert manager_class.return_value.mock_calls == []


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help(monkeypatch, manager_class, capsys, flag):
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, flag)
    assert exc.value.code == 0
    output = capsys.readouterr().out
    for short, long in (("-c", "--create"), ("-e", "--edit"), ("-d", "--delete")):
        assert f"{short} NAME, {long} NAME" in output
    assert "-n NAME" not in output
    assert "--name" not in output
    manager_class.assert_not_called()
