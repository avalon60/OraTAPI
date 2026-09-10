import os
from pathlib import Path
import zipfile

from oratapi.lib.connection_mgr import ConnectMgr
from oratapi.lib import session_manager


def _create_wallet_zip(wallet_zip: Path) -> None:
    with zipfile.ZipFile(wallet_zip, "w") as archive:
        archive.writestr("tnsnames.ora", "MYALIAS=(DESCRIPTION=(ADDRESS=(PROTOCOL=TCPS)))")
        archive.writestr("ewallet.pem", "-----BEGIN ENCRYPTED PRIVATE KEY-----")


def test_validate_wallet_path_falls_back_to_tns_admin(monkeypatch, tmp_path) -> None:
    tns_admin = tmp_path / "tns_admin"
    tns_admin.mkdir()
    wallet_zip = tns_admin / "example-wallet.zip"
    _create_wallet_zip(wallet_zip)

    monkeypatch.setenv("TNS_ADMIN", str(tns_admin))

    resolved = ConnectMgr._validate_wallet_path("example-wallet.zip")

    assert resolved == str(wallet_zip.resolve())


def test_validate_wallet_path_accepts_extracted_directory(tmp_path) -> None:
    wallet_dir = tmp_path / "wallet"
    wallet_dir.mkdir()
    (wallet_dir / "tnsnames.ora").write_text("MYALIAS=(DESCRIPTION=(ADDRESS=(PROTOCOL=TCPS)))")
    (wallet_dir / "cwallet.sso").write_bytes(b"wallet")

    resolved = ConnectMgr._validate_wallet_path(str(wallet_dir))

    assert resolved == str(wallet_dir.resolve())


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


def test_thick_mode_initialisation_accepts_path_objects(monkeypatch, tmp_path, capsys) -> None:
    client_dir = tmp_path / "instant_client"
    client_dir.mkdir()
    monkeypatch.setattr(session_manager, "_looks_like_instant_client", lambda path: True)
    monkeypatch.setenv("TNS_ADMIN", str(tmp_path))
    captured = {}

    def fake_init_oracle_client(*, lib_dir):
        # The native driver encodes the path and does not accept pathlib.Path.
        lib_dir.encode()
        captured["lib_dir"] = lib_dir

    monkeypatch.setattr(session_manager.oracledb, "init_oracle_client", fake_init_oracle_client)

    assert session_manager.try_init_thick_mode(verbose=True, lib_dir=client_dir)
    assert captured["lib_dir"] == str(client_dir)
    assert "explicit client directory" in capsys.readouterr().out
