from pathlib import Path

from oratapi.controller import update_ora_tapi


def test_install_home_resolves_repo_root() -> None:
    expected_root = Path(__file__).resolve().parents[1]
    assert update_ora_tapi.install_home() == expected_root
