from pathlib import Path
from zipfile import ZipFile

from oratapi.controller.quick_config import bootstrap_builtin_profiles
from oratapi.lib.fsutils import configured_active_profile_name, profile_home
from oratapi.lib.profile_manager import ProfileManager


def test_profile_export_and_import_round_trip(monkeypatch, tmp_path) -> None:
    home_dir = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home_dir))

    bootstrap_builtin_profiles(selected_profile="basic", force=False)

    manager = ProfileManager(current_version="9.9.9")
    export_path = tmp_path / "basic-profile.zip"
    manager.export_profile("basic", export_path)

    imported_profile_name = "basic_imported"
    imported_archive = tmp_path / "basic-imported.zip"
    imported_root = tmp_path / imported_profile_name
    imported_root.mkdir()
    for source in profile_home("basic").rglob("*"):
        if source.is_file():
            target = imported_root / source.relative_to(profile_home("basic"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())

    from zipfile import ZipFile, ZIP_DEFLATED

    with ZipFile(imported_archive, "w", ZIP_DEFLATED) as archive:
        for file_path in imported_root.rglob("*"):
            if file_path.is_file():
                archive.write(file_path, Path(imported_profile_name) / file_path.relative_to(imported_root))

    monkeypatch.setattr(ProfileManager, "_confirm_action", staticmethod(lambda _message: True))
    manager.import_profile(imported_archive, purpose_text="Imported profile")

    imported_profile = profile_home(imported_profile_name)
    assert imported_profile.exists()
    assert (imported_profile / "resources" / "config" / "OraTAPI.ini").exists()
    assert (imported_profile / "purpose.md").read_text(encoding="utf-8").strip() == "Imported profile"
    assert configured_active_profile_name() == imported_profile_name


def test_profile_export_excludes_oracle_client(monkeypatch, tmp_path) -> None:
    home_dir = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home_dir))

    bootstrap_builtin_profiles(selected_profile="basic", force=False)

    profile_path = profile_home("basic")
    client_dir = profile_path / "oracle_client" / "instantclient_23_8"
    client_dir.mkdir(parents=True, exist_ok=True)
    (client_dir / "libclntsh.so").write_text("placeholder", encoding="utf-8")

    manager = ProfileManager(current_version="9.9.9")
    export_path = tmp_path / "basic-profile.zip"
    manager.export_profile("basic", export_path)

    with ZipFile(export_path, "r") as archive:
        archived_names = archive.namelist()

    assert "basic/resources/config/OraTAPI.ini" in archived_names
    assert not any(name.startswith("basic/oracle_client/") for name in archived_names)


def test_invalid_profile_name_is_rejected() -> None:
    try:
        ProfileManager._validate_profile_name("bad/name")
    except ValueError as exc:
        assert "Invalid profile name" in str(exc)
    else:
        raise AssertionError("Expected invalid profile name to raise ValueError")
