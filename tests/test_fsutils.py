from pathlib import Path

from oratapi.lib import fsutils


def test_resolve_default_path_locates_packaged_config_sample() -> None:
    sample_path = fsutils.resolve_default_path(Path("resources") / "config" / "OraTAPI.ini.sample")

    assert sample_path.exists()
    assert sample_path.name == "OraTAPI.ini.sample"
    assert "oratapi" in str(sample_path)


def test_runtime_home_tracks_home_directory(monkeypatch, tmp_path) -> None:
    home_dir = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home_dir))

    assert fsutils.runtime_home() == home_dir / "OraTAPI"
    assert fsutils.runtime_configs_home() == home_dir / "OraTAPI" / "configs"
