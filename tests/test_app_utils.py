"""Tests for OraTAPI application utility helpers."""

# Author: Clive Bostock
# Date: 2026-04-21
# Description: Tests for OraTAPI application utility helpers.

from requests import RequestException

from oratapi.lib import app_utils


class _FakeResponse:
    """Minimal response stub for PyPI version lookup tests."""

    def __init__(self, version: str) -> None:
        self._version = version

    def raise_for_status(self) -> None:
        """Simulate a successful HTTP response."""

    def json(self) -> dict[str, dict[str, str]]:
        """Return a PyPI-like JSON document."""
        return {"info": {"version": self._version}}


def test_get_latest_pypi_version_uses_requested_timeout(monkeypatch) -> None:
    """The PyPI version lookup should pass through the configured timeout."""
    captured: dict[str, object] = {}

    def fake_get(url: str, timeout: float) -> _FakeResponse:
        captured["url"] = url
        captured["timeout"] = timeout
        return _FakeResponse("9.9.9")

    monkeypatch.setattr(app_utils.requests, "get", fake_get)

    version = app_utils.get_latest_pypi_version("oratapi", timeout=2.5)

    assert version == "9.9.9"
    assert captured == {
        "url": "https://pypi.org/pypi/oratapi/json",
        "timeout": 2.5,
    }


def test_get_latest_pypi_version_returns_none_on_request_failure(monkeypatch) -> None:
    """Network failures should be treated as a silent no-update result."""

    def fake_get(url: str, timeout: float) -> _FakeResponse:
        raise RequestException("offline")

    monkeypatch.setattr(app_utils.requests, "get", fake_get)

    assert app_utils.get_latest_pypi_version("oratapi", timeout=2.5) is None
