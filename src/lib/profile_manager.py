__author__ = "Clive Bostock"
__date__ = "2026-04-04"
__description__ = "Manage OraTAPI configuration profiles."

import shutil
import zipfile
from pathlib import Path
from posixpath import normpath

from lib.config_mgr import compare_config_files
from lib.fsutils import (
    active_profile_home,
    active_profile_name,
    available_profiles,
    ensure_runtime_home,
    is_valid_dir_name,
    profile_home,
    resolve_default_path,
    write_active_profile,
)


class ProfileManager:
    def __init__(self):
        ensure_runtime_home()

    @staticmethod
    def _validate_profile_name(profile_name: str) -> str:
        profile_name = profile_name.strip()
        if not is_valid_dir_name(profile_name):
            raise ValueError(f"Invalid profile name: '{profile_name}'")
        if profile_name in {".", ".."}:
            raise ValueError(f"Invalid profile name: '{profile_name}'")
        return profile_name

    @staticmethod
    def _profile_path(profile_name: str) -> Path:
        return profile_home(profile_name)

    @staticmethod
    def _confirm_action(message: str) -> bool:
        response = input(f"{message} [y/N]: ").strip().lower()
        return response in {"y", "yes"}

    def _ensure_profile_exists(self, profile_name: str) -> Path:
        profile_name = self._validate_profile_name(profile_name)
        profile_path = self._profile_path(profile_name)
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile '{profile_name}' does not exist.")
        return profile_path

    def _prepare_target_profile(self, profile_name: str) -> Path:
        profile_name = self._validate_profile_name(profile_name)
        target_path = self._profile_path(profile_name)
        if target_path.exists():
            if not self._confirm_action(f"Overwrite existing profile '{profile_name}'?"):
                raise ValueError("Operation cancelled.")
            shutil.rmtree(target_path)
        return target_path

    def _prompt_activate_profile(self, profile_name: str) -> None:
        if self._confirm_action(f"Activate profile '{profile_name}'?"):
            write_active_profile(profile_name)
            print(f"Activated profile: {profile_name}")

    @staticmethod
    def _validate_archive_member(member_name: str) -> tuple[str, Path]:
        normalised_name = normpath(member_name.replace("\\", "/"))
        if normalised_name.startswith("../") or normalised_name == ".." or normalised_name.startswith("/"):
            raise ValueError(f"Unsafe archive member: {member_name}")
        parts = Path(normalised_name).parts
        if not parts:
            raise ValueError("Archive contains an invalid entry.")
        profile_name = parts[0]
        relative_path = Path(*parts[1:]) if len(parts) > 1 else Path()
        return profile_name, relative_path

    def _archive_profile_name(self, archive_path: Path) -> str:
        if not archive_path.exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")

        archive_profile_names: set[str] = set()
        file_entries = 0
        with zipfile.ZipFile(archive_path, "r") as zip_file:
            for member in zip_file.infolist():
                if not member.filename or member.filename.endswith("/"):
                    continue
                file_entries += 1
                profile_name, relative_path = self._validate_archive_member(member.filename)
                if not str(relative_path):
                    raise ValueError("Archive entries must be stored beneath a single top-level profile directory.")
                archive_profile_names.add(profile_name)

        if file_entries == 0:
            raise ValueError("Archive is empty.")
        if len(archive_profile_names) != 1:
            raise ValueError("Archive must contain exactly one top-level profile directory.")

        profile_name = archive_profile_names.pop()
        return self._validate_profile_name(profile_name)

    def export_profile(self, profile_name: str, export_path: Path) -> None:
        profile_path = self._ensure_profile_exists(profile_name)
        export_path = Path(export_path).expanduser()
        export_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in profile_path.rglob("*"):
                if file_path.is_file():
                    archive_name = Path(profile_name) / file_path.relative_to(profile_path)
                    zip_file.write(file_path, archive_name.as_posix())

        print(f"Exported profile '{profile_name}' to {export_path}")

    def import_profile(self, import_path: Path) -> None:
        import_path = Path(import_path).expanduser()
        profile_name = self._archive_profile_name(import_path)
        target_path = self._prepare_target_profile(profile_name)
        target_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(import_path, "r") as zip_file:
            for member in zip_file.infolist():
                if not member.filename or member.filename.endswith("/"):
                    continue
                _, relative_path = self._validate_archive_member(member.filename)
                destination_path = target_path / relative_path
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                with zip_file.open(member, "r") as source_file, destination_path.open("wb") as target_file:
                    shutil.copyfileobj(source_file, target_file)

        print(f"Imported profile '{profile_name}' from {import_path}")
        config_sample = resolve_default_path(Path("resources") / "config" / "samples" / "OraTAPI.ini.sample")
        config_target = target_path / "resources" / "config" / "OraTAPI.ini"
        if config_target.exists():
            compare_config_files(config_sample_file=config_sample, config_file_path=config_target)
        self._prompt_activate_profile(profile_name)

    def migrate_old_install(self, old_install_dir: Path, target_profile: str) -> None:
        old_install_dir = Path(old_install_dir).expanduser()
        if not old_install_dir.exists():
            raise FileNotFoundError(f"Old install directory '{old_install_dir}' does not exist.")

        target_profile = self._validate_profile_name(target_profile)
        target_path = self._prepare_target_profile(target_profile)
        new_install_resources = target_path / "resources"
        config_dir = new_install_resources / "config"
        templates_dir = new_install_resources / "templates"
        previous_install_resources = old_install_dir / "resources"
        previous_config_dir = previous_install_resources / "config"

        previous_install_config_file = previous_config_dir / "OraTAPI.ini"
        pi_columns_csv_previous = previous_config_dir / "pi_columns.csv"
        if not previous_install_config_file.exists():
            raise FileNotFoundError(f"Missing legacy config file: {previous_install_config_file}")
        if not pi_columns_csv_previous.exists():
            raise FileNotFoundError(f"Missing legacy PI columns file: {pi_columns_csv_previous}")

        config_dir.mkdir(parents=True, exist_ok=True)
        templates_dir.mkdir(parents=True, exist_ok=True)

        files_migrated = 0
        config_sample = resolve_default_path(Path("resources") / "config" / "samples" / "OraTAPI.ini.sample")
        config_target = config_dir / "OraTAPI.ini"
        shutil.copyfile(previous_install_config_file, config_target)
        print(f"Migrated: {previous_install_config_file.absolute()} -> {config_target.absolute()}")
        files_migrated += 1

        ora_tapi_csv_previous = previous_config_dir / "OraTAPI.csv"
        ora_tapi_csv_new = config_dir / "OraTAPI.csv"
        if ora_tapi_csv_previous.exists():
            shutil.copyfile(ora_tapi_csv_previous, ora_tapi_csv_new)
            print(f"Migrated: {ora_tapi_csv_previous.absolute()} -> {ora_tapi_csv_new.absolute()}")
            files_migrated += 1

        pi_columns_csv_new = config_dir / "pi_columns.csv"
        shutil.copyfile(pi_columns_csv_previous, pi_columns_csv_new)
        print(f"Migrated: {pi_columns_csv_previous.absolute()} -> {pi_columns_csv_new.absolute()}")
        files_migrated += 1

        previous_templates_dir = old_install_dir / 'resources' / 'templates'
        templates_dirs = [
            templates_dir / "misc" / "trigger",
            templates_dir / "misc" / "view",
            templates_dir / "packages" / "body",
            templates_dir / "packages" / "spec",
            templates_dir / "packages" / "procedures",
            templates_dir / "column_expressions" / "inserts",
            templates_dir / "column_expressions" / "updates",
            templates_dir / "ut_packages" / "body",
            templates_dir / "ut_packages" / "spec"
        ]

        for template_dir in templates_dirs:
            template_dir.mkdir(parents=True, exist_ok=True)
            source_template_dir = previous_templates_dir / template_dir.relative_to(templates_dir)
            if source_template_dir.exists() and source_template_dir.is_dir():
                for tpt_file in source_template_dir.rglob('*.tpt'):
                    target_file = template_dir / tpt_file.name
                    shutil.copy2(tpt_file, target_file)
                    files_migrated += 1
                    print(f"Migrated: {tpt_file.relative_to(old_install_dir)} -> {target_file.relative_to(target_path)}")

        print(f"Total files migrated: {files_migrated}")
        compare_config_files(config_sample_file=config_sample, config_file_path=config_target)
        self._prompt_activate_profile(target_profile)

    def list_profiles(self) -> None:
        current_profile = active_profile_name()
        profiles = available_profiles()
        if not profiles:
            print("No OraTAPI profiles found.")
            return

        print("OraTAPI profiles:")
        for profile_name in profiles:
            marker = "*" if profile_name == current_profile else " "
            print(f"{marker} {profile_name}")

    def show_active_profile(self) -> None:
        profile_name = active_profile_name()
        print(f"Active profile: {profile_name}")
        print(f"Profile directory: {self._profile_path(profile_name)}")

    def activate_profile(self, profile_name: str) -> None:
        profile_name = self._ensure_profile_exists(profile_name).name
        write_active_profile(profile_name)
        print(f"Activated profile: {profile_name}")

    def create_profile(self, profile_name: str) -> None:
        profile_name = self._validate_profile_name(profile_name)
        target_path = self._profile_path(profile_name)
        if target_path.exists():
            raise FileExistsError(f"Profile '{profile_name}' already exists.")

        source_path = active_profile_home()
        if not source_path.exists():
            raise FileNotFoundError(
                f"Active profile '{active_profile_name()}' does not exist. Run quick_config first."
            )

        shutil.copytree(source_path, target_path)
        print(f"Created profile '{profile_name}' from active profile '{active_profile_name()}'.")

    def copy_profile(self, source_profile: str, target_profile: str) -> None:
        source_profile = self._ensure_profile_exists(source_profile).name
        target_profile = self._validate_profile_name(target_profile)
        source_path = self._profile_path(source_profile)
        target_path = self._profile_path(target_profile)
        if target_path.exists():
            raise FileExistsError(f"Profile '{target_profile}' already exists.")

        shutil.copytree(source_path, target_path)
        print(f"Copied profile '{source_profile}' to '{target_profile}'.")

    def delete_profile(self, profile_name: str) -> None:
        profile_name = self._validate_profile_name(profile_name)
        if profile_name == active_profile_name():
            raise ValueError("Cannot delete the active profile.")

        profile_path = self._profile_path(profile_name)
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile '{profile_name}' does not exist.")

        shutil.rmtree(profile_path)
        print(f"Deleted profile: {profile_name}")
