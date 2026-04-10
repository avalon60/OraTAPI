from types import SimpleNamespace

import pytest

from oratapi.lib import user_security


def _completed(stdout: str, returncode: int = 0):
    return SimpleNamespace(stdout=stdout.encode("utf-8"), returncode=returncode)


def test_windows_system_id_prefers_powershell_cim(monkeypatch) -> None:
    calls = []

    def fake_run(command, input_bytes=None):
        calls.append(command)
        if command[:3] == ["powershell", "-NoProfile", "-Command"]:
            return _completed("1234-ABCD\n")
        raise AssertionError(f"Unexpected fallback command: {command}")

    monkeypatch.setattr(user_security, "_run_command", fake_run)

    assert user_security._windows_system_id() == "1234-ABCD"
    assert calls == [["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystemProduct).UUID"]]


def test_windows_system_id_falls_back_to_wmic(monkeypatch) -> None:
    calls = []

    def fake_run(command, input_bytes=None):
        calls.append(command)
        if command[-1] == "(Get-CimInstance Win32_ComputerSystemProduct).UUID":
            return _completed("", returncode=1)
        if command[-1] == "(Get-WmiObject Win32_ComputerSystemProduct).UUID":
            raise FileNotFoundError
        if command[0] == "wmic":
            return _completed("UUID\nABCD-1234\n")
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr(user_security, "_run_command", fake_run)

    assert user_security._windows_system_id() == "ABCD-1234"
    assert calls[-1][0] == "wmic"


def test_windows_system_id_raises_when_all_strategies_fail(monkeypatch) -> None:
    def fake_run(command, input_bytes=None):
        raise FileNotFoundError

    monkeypatch.setattr(user_security, "_run_command", fake_run)

    with pytest.raises(RuntimeError, match="Unable to determine the Windows system UUID"):
        user_security._windows_system_id()
