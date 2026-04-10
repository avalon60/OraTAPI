import os
from pathlib import Path

from oratapi.lib.connection_mgr import ConnectMgr
from oratapi.lib import session_manager


def test_validate_wallet_path_falls_back_to_tns_admin(monkeypatch, tmp_path) -> None:
    tns_admin = tmp_path / "tns_admin"
    tns_admin.mkdir()
    wallet_zip = tns_admin / "example-wallet.zip"
    wallet_zip.write_text("placeholder", encoding="utf-8")

    monkeypatch.setenv("TNS_ADMIN", str(tns_admin))

    resolved = ConnectMgr._validate_wallet_path("example-wallet.zip")

    assert resolved == str(wallet_zip.resolve())


def test_dbsession_wallet_path_falls_back_to_tns_admin(monkeypatch, tmp_path) -> None:
    tns_admin = tmp_path / "tns_admin"
    tns_admin.mkdir()
    wallet_zip = tns_admin / "example-wallet.zip"
    wallet_zip.write_text("placeholder", encoding="utf-8")

    monkeypatch.setenv("TNS_ADMIN", str(tns_admin))

    captured = {}

    def fake_extract_wallet(self, wallet_path: Path):
        captured["wallet_path"] = wallet_path
        raise RuntimeError("stop after wallet resolution")

    monkeypatch.setattr(session_manager.DBSession, "extract_wallet", fake_extract_wallet)

    try:
        session_manager.DBSession(
            user="user",
            password="password",
            dsn="MYALIAS",
            wallet_zip_path="example-wallet.zip",
            verbose=False,
        )
    except RuntimeError as exc:
        assert str(exc) == "stop after wallet resolution"
    else:
        raise AssertionError("Expected test sentinel exception to stop DBSession initialisation")

    assert captured["wallet_path"] == wallet_zip.resolve()
