from pathlib import Path

import oratapi

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib


def test_package_has_descriptive_docstring() -> None:
    assert oratapi.__doc__ is not None
    assert "Oracle" in oratapi.__doc__
    assert "PL/SQL" in oratapi.__doc__


def test_package_version_is_exposed() -> None:
    assert isinstance(oratapi.__version__, str)
    assert oratapi.__version__


def test_console_script_aliases_include_oratapi() -> None:
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    pyproject_data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    scripts = pyproject_data["project"]["scripts"]

    assert scripts["oratapi"] == "oratapi.controller.ora_tapi:main"
    assert scripts["ora_tapi"] == "oratapi.controller.ora_tapi:main"
    assert scripts["ora-tapi"] == "oratapi.controller.ora_tapi:main"
