# Author: cbostock / DGGIU
# Date: 09-Sep-2026
# Description: Verifies OCI IAM token connection storage and driver argument preparation.

import configparser
from pathlib import Path

import pytest

from oratapi.lib import session_manager, user_security
from oratapi.lib.connection_mgr import ConnectMgr
from oratapi.lib.framework_errors import DatabaseConnectionError
from oratapi.lib.user_security import (
    NamedConnection,
    OCI_IAM_TOKEN_AUTHENTICATION,
    PASSWORD_AUTHENTICATION,
    UserSecurity,
)


def _security_store(monkeypatch, tmp_path: Path) -> UserSecurity:
    monkeypatch.setattr(user_security, "_system_id", lambda: "test-system-id")
    security = UserSecurity.__new__(UserSecurity)
    security.user_config_file_path = tmp_path / "dsn_credentials.ini"
    security.user_config_file_path.touch()
    return security


def test_legacy_named_connection_defaults_to_password_authentication(monkeypatch, tmp_path) -> None:
    security = _security_store(monkeypatch, tmp_path)
    config = configparser.ConfigParser()
    config["legacy"] = {
        "username": user_security._encrypted_user_credential("legacy_user"),
        "password": user_security._encrypted_user_credential("legacy_password"),
        "dsn": "LEGACY_DB",
        "wallet_zip_path": "/wallet/legacy.zip",
    }
    with security.user_config_file_path.open("w", encoding="utf-8") as config_file:
        config.write(config_file)

    connection = security.named_connection("legacy")

    assert connection.authentication_type == PASSWORD_AUTHENTICATION
    assert connection.username == "legacy_user"
    assert connection.password == "legacy_password"
    assert connection.dsn == "LEGACY_DB"
    assert connection.wallet_path == "/wallet/legacy.zip"
    assert security.connection_property("legacy", "authentication_type") == PASSWORD_AUTHENTICATION


def test_iam_connection_omits_database_credentials(monkeypatch, tmp_path) -> None:
    security = _security_store(monkeypatch, tmp_path)

    security.update_named_connection(
        connection_name="iam",
        username=None,
        password=None,
        dsn="IAM_DB_HIGH",
        authentication_type=OCI_IAM_TOKEN_AUTHENTICATION,
        wallet_path="/wallet/iam.zip",
        wallet_password="wallet-secret",
        token_location="/tokens/iam",
    )

    config = configparser.ConfigParser()
    config.read(security.user_config_file_path)
    assert not config.has_option("iam", "username")
    assert not config.has_option("iam", "password")
    assert config.get("iam", "wallet_password") != "wallet-secret"
    connection = security.named_connection("iam")
    assert connection.authentication_type == OCI_IAM_TOKEN_AUTHENTICATION
    assert connection.username is None
    assert connection.password is None
    assert connection.wallet_password == "wallet-secret"
    assert connection.token_location == "/tokens/iam"


def test_converting_iam_connection_to_password_removes_token_settings(monkeypatch, tmp_path) -> None:
    security = _security_store(monkeypatch, tmp_path)
    security.update_named_connection(
        connection_name="convert",
        username=None,
        password=None,
        dsn="DB_HIGH",
        authentication_type=OCI_IAM_TOKEN_AUTHENTICATION,
        wallet_path="/wallet/iam.zip",
        wallet_password="wallet-secret",
        token_location="/tokens/iam",
    )

    security.update_named_connection(
        connection_name="convert",
        username="database_user",
        password="database_password",
        dsn="DB_HIGH",
        authentication_type=PASSWORD_AUTHENTICATION,
    )

    config = configparser.ConfigParser()
    config.read(security.user_config_file_path)
    assert not config.has_option("convert", "token_location")
    assert not config.has_option("convert", "wallet_password")
    assert not config.has_option("convert", "wallet_path")
    assert security.named_connection_creds("convert") == (
        "database_user",
        "database_password",
        "DB_HIGH",
    )


def test_invalid_password_connection_does_not_create_partial_entry(monkeypatch, tmp_path) -> None:
    security = _security_store(monkeypatch, tmp_path)

    with pytest.raises(ValueError, match="require a username and password"):
        security.update_named_connection(
            connection_name="invalid",
            username=None,
            password=None,
            dsn="DB_HIGH",
        )

    config = configparser.ConfigParser()
    config.read(security.user_config_file_path)
    assert not config.has_section("invalid")


def test_token_provider_preserves_pem_in_thin_mode(monkeypatch, tmp_path) -> None:
    token_dir = tmp_path / "db-token"
    token_dir.mkdir()
    (token_dir / "token").write_text("signed-token\n", encoding="utf-8")
    private_key = "-----BEGIN PRIVATE KEY-----\nprivate-key-data\n-----END PRIVATE KEY-----\n"
    (token_dir / "oci_db_key.pem").write_text(private_key, encoding="utf-8")
    monkeypatch.setattr(session_manager.oracledb, "is_thin_mode", lambda: True)

    token, returned_key = session_manager.OCIIAMTokenProvider(token_dir)(refresh=False)

    assert token == "signed-token"
    assert returned_key == private_key.strip()


def test_token_provider_strips_pem_markers_in_thick_mode(monkeypatch, tmp_path) -> None:
    token_dir = tmp_path / "db-token"
    token_dir.mkdir()
    (token_dir / "token").write_text("signed-token", encoding="utf-8")
    (token_dir / "oci_db_key.pem").write_text(
        "-----BEGIN PRIVATE KEY-----\nprivate-key-data\n-----END PRIVATE KEY-----\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(session_manager.oracledb, "is_thin_mode", lambda: False)

    _, returned_key = session_manager.OCIIAMTokenProvider(token_dir)(refresh=False)

    assert returned_key == "private-key-data"


def test_token_provider_reports_user_managed_renewal_without_running_a_command(tmp_path) -> None:
    with pytest.raises(DatabaseConnectionError, match="does not renew tokens automatically"):
        session_manager.OCIIAMTokenProvider(tmp_path)(refresh=True)


def test_token_provider_reports_missing_files(tmp_path) -> None:
    with pytest.raises(DatabaseConnectionError, match="token material is incomplete"):
        session_manager.OCIIAMTokenProvider(tmp_path)(refresh=False)


def test_authentication_arguments_differ_by_driver_mode(monkeypatch, tmp_path) -> None:
    thin_kwargs = {"user": "", "password": "", "dsn": "DB_HIGH"}
    monkeypatch.setattr(session_manager.oracledb, "is_thin_mode", lambda: True)
    thin_result = session_manager.DBSession._configure_authentication(
        authentication_type=OCI_IAM_TOKEN_AUTHENTICATION,
        token_location=str(tmp_path),
        connection_kwargs=thin_kwargs,
    )
    assert "user" not in thin_result
    assert "password" not in thin_result
    assert isinstance(thin_result["access_token"], session_manager.OCIIAMTokenProvider)
    assert "externalauth" not in thin_result

    thick_kwargs = {"user": "", "password": "", "dsn": "DB_HIGH"}
    monkeypatch.setattr(session_manager.oracledb, "is_thin_mode", lambda: False)
    thick_result = session_manager.DBSession._configure_authentication(
        authentication_type=OCI_IAM_TOKEN_AUTHENTICATION,
        token_location=str(tmp_path),
        connection_kwargs=thick_kwargs,
    )
    assert thick_result["externalauth"] is True

    password_kwargs = {"user": "user", "password": "password", "dsn": "DB"}
    password_result = session_manager.DBSession._configure_authentication(
        authentication_type=PASSWORD_AUTHENTICATION,
        token_location="",
        connection_kwargs=password_kwargs,
    )
    assert password_result == password_kwargs


@pytest.mark.parametrize(
    ("thin_mode", "wallet_filename", "expect_externalauth"),
    (
        (True, "ewallet.pem", False),
        (False, "cwallet.sso", True),
    ),
)
def test_iam_connection_passes_mode_specific_arguments_to_driver(
        monkeypatch,
        tmp_path,
        thin_mode,
        wallet_filename,
        expect_externalauth,
) -> None:
    wallet_dir = tmp_path / "wallet"
    wallet_dir.mkdir()
    (wallet_dir / "tnsnames.ora").write_text(
        "DB_HIGH=(DESCRIPTION=(ADDRESS=(PROTOCOL=tcps)(HOST=localhost)(PORT=1522))"
        "(CONNECT_DATA=(SERVICE_NAME=db))(SECURITY=(SSL_SERVER_DN_MATCH=yes)(TOKEN_AUTH=OCI_TOKEN)))",
        encoding="utf-8",
    )
    if wallet_filename == "ewallet.pem":
        (wallet_dir / wallet_filename).write_text("wallet", encoding="utf-8")
    else:
        (wallet_dir / wallet_filename).write_bytes(b"wallet")

    token_dir = tmp_path / "db-token"
    token_dir.mkdir()
    (token_dir / "token").write_text("signed-token", encoding="utf-8")
    (token_dir / "oci_db_key.pem").write_text(
        "-----BEGIN PRIVATE KEY-----\nprivate-key-data\n-----END PRIVATE KEY-----\n",
        encoding="utf-8",
    )

    captured_kwargs = {}
    captured_params_kwargs = {}
    actual_connect_params = session_manager.oracledb.ConnectParams

    class RecordingConnectParams:
        def __init__(self, **kwargs):
            captured_params_kwargs.update(kwargs)
            self.delegate = actual_connect_params(**kwargs)

        def parse_connect_string(self, connect_string):
            self.delegate.parse_connect_string(connect_string)

    monkeypatch.setattr(session_manager.oracledb, "is_thin_mode", lambda: thin_mode)
    monkeypatch.setattr(session_manager.oracledb, "ConnectParams", RecordingConnectParams)
    monkeypatch.setattr(
        session_manager.oracledb.Connection,
        "__init__",
        lambda self, **kwargs: captured_kwargs.update(kwargs),
    )

    session = session_manager.DBSession(
        dsn="DB_HIGH",
        user=None,
        password=None,
        authentication_type=OCI_IAM_TOKEN_AUTHENTICATION,
        wallet_path=str(wallet_dir),
        wallet_password="wallet-password",
        token_location=str(token_dir),
        verbose=False,
    )
    session.connection_succeeded = False

    assert "user" not in captured_kwargs
    assert "password" not in captured_kwargs
    assert "dsn" not in captured_kwargs
    assert isinstance(captured_kwargs["access_token"], session_manager.OCIIAMTokenProvider)
    assert captured_kwargs.get("externalauth", False) is expect_externalauth
    assert captured_params_kwargs["wallet_location"] == str(wallet_dir)
    expected_wallet_password = "wallet-password" if thin_mode else None
    assert captured_params_kwargs.get("wallet_password") == expected_wallet_password


def test_password_connection_passes_credentials_without_access_token(monkeypatch) -> None:
    captured_kwargs = {}
    monkeypatch.delenv("TNS_ADMIN", raising=False)
    monkeypatch.setattr(
        session_manager.oracledb.Connection,
        "__init__",
        lambda self, **kwargs: captured_kwargs.update(kwargs),
    )

    session = session_manager.DBSession(
        dsn="localhost/service",
        user="database_user",
        password="database_password",
        verbose=False,
    )
    session.connection_succeeded = False

    assert captured_kwargs == {
        "dsn": "localhost/service",
        "user": "database_user",
        "password": "database_password",
    }


def test_iam_connection_requires_a_wallet(tmp_path) -> None:
    with pytest.raises(DatabaseConnectionError, match="requires an Oracle wallet"):
        session_manager.DBSession(
            dsn="DB_HIGH",
            authentication_type=OCI_IAM_TOKEN_AUTHENTICATION,
            token_location=str(tmp_path),
            verbose=False,
        )


def test_wallet_validation_requires_mode_specific_files_and_password(monkeypatch, tmp_path) -> None:
    wallet_dir = tmp_path / "wallet"
    wallet_dir.mkdir()
    (wallet_dir / "tnsnames.ora").write_text("DB_HIGH=(DESCRIPTION=())", encoding="utf-8")
    (wallet_dir / "ewallet.pem").write_text(
        "-----BEGIN ENCRYPTED PRIVATE KEY-----\nwallet-data",
        encoding="utf-8",
    )
    (wallet_dir / "cwallet.sso").write_bytes(b"wallet")

    monkeypatch.setattr(session_manager.oracledb, "is_thin_mode", lambda: True)
    with pytest.raises(DatabaseConnectionError, match="no wallet password is saved"):
        session_manager.DBSession._validate_wallet_for_mode(wallet_dir, wallet_password="")
    session_manager.DBSession._validate_wallet_for_mode(wallet_dir, wallet_password="wallet-password")

    (wallet_dir / "cwallet.sso").unlink()
    monkeypatch.setattr(session_manager.oracledb, "is_thin_mode", lambda: False)
    with pytest.raises(DatabaseConnectionError, match="does not contain cwallet.sso"):
        session_manager.DBSession._validate_wallet_for_mode(wallet_dir, wallet_password="")


def test_extract_wallet_rejects_a_non_zip_file(tmp_path) -> None:
    wallet_file = tmp_path / "wallet.zip"
    wallet_file.write_text("not a ZIP", encoding="utf-8")
    session = session_manager.DBSession.__new__(session_manager.DBSession)
    session.connection_succeeded = False
    session.verbose = False

    with pytest.raises(DatabaseConnectionError, match="not a valid ZIP file"):
        session.extract_wallet(wallet_file)


def test_iam_list_never_prints_wallet_password_ciphertext(capsys) -> None:
    manager = ConnectMgr.__new__(ConnectMgr)
    manager.credential_type = "dsn"
    manager.config = configparser.ConfigParser()
    manager.config["iam"] = {
        "authentication_type": OCI_IAM_TOKEN_AUTHENTICATION,
        "resource_id": "DB_HIGH",
        "wallet_path": "/wallet/iam.zip",
        "wallet_password": "encrypted-wallet-secret",
    }

    manager.list_connections(inc_creds=True)

    output = capsys.readouterr().out
    assert "wallet password saved" in output
    assert "encrypted-wallet-secret" not in output

    manager.list_connections()

    output = capsys.readouterr().out
    assert OCI_IAM_TOKEN_AUTHENTICATION in output
    assert "wallet password saved" in output
    assert "encrypted-wallet-secret" not in output


def test_create_iam_connection_collects_token_settings(monkeypatch, tmp_path) -> None:
    manager = ConnectMgr.__new__(ConnectMgr)
    manager.credential_type = "dsn"
    manager.config = configparser.ConfigParser()
    captured = {}
    manager.user_security = type(
        "RecordingSecurity",
        (),
        {"update_named_connection": lambda self, **kwargs: captured.update(kwargs)},
    )()
    manager.config_pathname = tmp_path / "unused.ini"
    monkeypatch.setattr(manager, "_reload_config", lambda: None)
    monkeypatch.setattr(manager, "_prompt_wallet_path", lambda **kwargs: "/wallet/iam.zip")
    monkeypatch.setattr(manager, "_prompt_wallet_password", lambda *args: "wallet-secret")
    responses = iter(("DB_HIGH", "/tokens/iam", "y"))
    monkeypatch.setattr("builtins.input", lambda prompt: next(responses))

    manager.create_connection("iam", authentication_type=OCI_IAM_TOKEN_AUTHENTICATION)

    assert captured == {
        "connection_name": "iam",
        "username": None,
        "password": None,
        "dsn": "DB_HIGH",
        "authentication_type": OCI_IAM_TOKEN_AUTHENTICATION,
        "wallet_path": "/wallet/iam.zip",
        "wallet_password": "wallet-secret",
        "token_location": "/tokens/iam",
    }


def test_edit_iam_connection_keeps_authentication_type(monkeypatch, tmp_path) -> None:
    manager = ConnectMgr.__new__(ConnectMgr)
    manager.credential_type = "dsn"
    manager.config = configparser.ConfigParser()
    manager.config["iam"] = {}
    captured = {}
    existing_connection = NamedConnection(
        name="iam",
        authentication_type=OCI_IAM_TOKEN_AUTHENTICATION,
        dsn="DB_HIGH",
        wallet_path="/wallet/iam.zip",
        wallet_password="wallet-secret",
        token_location="/tokens/iam",
    )
    manager.user_security = type(
        "RecordingSecurity",
        (),
        {
            "named_connection": lambda self, connection_name: existing_connection,
            "update_named_connection": lambda self, **kwargs: captured.update(kwargs),
        },
    )()
    manager.config_pathname = tmp_path / "unused.ini"
    monkeypatch.setattr(manager, "_reload_config", lambda: None)
    monkeypatch.setattr(manager, "_prompt_wallet_path", lambda **kwargs: "/wallet/iam.zip")
    monkeypatch.setattr(manager, "_prompt_wallet_password", lambda *args: "wallet-secret")
    responses = iter(("DB_HIGH_NEW", "", "y"))
    monkeypatch.setattr("builtins.input", lambda prompt: next(responses))

    manager.edit_connection("iam")

    assert captured["authentication_type"] == OCI_IAM_TOKEN_AUTHENTICATION
    assert captured["dsn"] == "DB_HIGH_NEW"
    assert captured["username"] is None
    assert captured["password"] is None
    assert captured["token_location"] == "/tokens/iam"
