from pathlib import Path

from oratapi.controller.quick_config import BUILTIN_PROFILES, bootstrap_builtin_profiles
from oratapi.lib.fsutils import active_profile_pointer_file, missing_runtime_paths, profile_home


def test_bootstrap_builtin_profiles_creates_runtime_files(monkeypatch, tmp_path) -> None:
    home_dir = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home_dir))

    bootstrap_builtin_profiles(selected_profile="basic", force=False)

    assert active_profile_pointer_file().read_text(encoding="utf-8").strip() == "basic"

    for profile_name in BUILTIN_PROFILES:
        profile_root = profile_home(profile_name)
        assert profile_root.exists()
        config_file = profile_root / "resources" / "config" / "OraTAPI.ini"
        assert config_file.exists()
        assert "skip_logged_data_types" in config_file.read_text(encoding="utf-8")
        assert (profile_root / "resources" / "config" / "pi_columns.csv").exists()
        assert (profile_root / "resources" / "templates" / "packages" / "procedures" / "select.tpt").exists()
        assert (profile_root / "purpose.md").exists()
        assert (profile_root / "created_version.md").exists()

    assert missing_runtime_paths() == []


def test_templates_only_requires_existing_control_files(monkeypatch, tmp_path) -> None:
    home_dir = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home_dir))

    bootstrap_builtin_profiles(selected_profile="logger", force=False)

    basic_ini = profile_home("basic") / "resources" / "config" / "OraTAPI.ini"
    original_contents = basic_ini.read_text(encoding="utf-8")
    basic_ini.write_text(original_contents + "\n# local customisation\n", encoding="utf-8")

    bootstrap_builtin_profiles(selected_profile="logger", force=True, templates_only=True)

    assert "# local customisation" in basic_ini.read_text(encoding="utf-8")
