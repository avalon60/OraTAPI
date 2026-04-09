import oratapi


def test_package_has_descriptive_docstring() -> None:
    assert oratapi.__doc__ is not None
    assert "Oracle" in oratapi.__doc__
    assert "PL/SQL" in oratapi.__doc__


def test_package_version_is_exposed() -> None:
    assert isinstance(oratapi.__version__, str)
    assert oratapi.__version__
