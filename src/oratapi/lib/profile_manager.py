__author__ = "Clive Bostock"
__date__ = "2026-04-04"
__description__ = "Manage OraTAPI configuration profiles."

import re
import shutil
import zipfile
from pathlib import Path
from posixpath import normpath

from oratapi.lib.config_mgr import compare_config_files
from oratapi.lib.fsutils import (
    active_profile_home,
    available_profiles,
    configured_active_profile_name,
    ensure_runtime_home,
    is_valid_dir_name,
    profile_home,
    resolve_default_path,
    write_active_profile,
)


class ProfileManager:
    PURPOSE_FILENAME = "purpose.md"
    CREATED_VERSION_FILENAME = "created_version.md"
    WINDOWS_RESERVED_PROFILE_NAMES = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    }

    def __init__(self, current_version: str | None = None):
        ensure_runtime_home()
        self.current_version = current_version

    @classmethod
    def _validate_profile_name(cls, profile_name: str) -> str:
        profile_name = profile_name.strip()
        if not is_valid_dir_name(profile_name):
            raise ValueError(f"Invalid profile name: '{profile_name}'")
        if profile_name in {".", ".."}:
            raise ValueError(f"Invalid profile name: '{profile_name}'")
        if re.search(r'[\\/:*?"<>|]', profile_name):
            raise ValueError(f"Invalid profile name: '{profile_name}'")
        if profile_name.endswith((" ", ".")):
            raise ValueError(f"Invalid profile name: '{profile_name}'")
        if profile_name.upper() in cls.WINDOWS_RESERVED_PROFILE_NAMES:
            raise ValueError(f"Invalid profile name: '{profile_name}'")
        return profile_name

    @staticmethod
    def _profile_path(profile_name: str) -> Path:
        return profile_home(profile_name)

    @staticmethod
    def _confirm_action(message: str) -> bool:
        response = input(f"{message} [y/N]: ").strip().lower()
        return response in {"y", "yes"}

    @staticmethod
    def _purpose_path(profile_path: Path) -> Path:
        return profile_path / ProfileManager.PURPOSE_FILENAME

    @staticmethod
    def _created_version_path(profile_path: Path) -> Path:
        return profile_path / ProfileManager.CREATED_VERSION_FILENAME

    @staticmethod
    def _normalise_purpose(purpose_text: str | None) -> str | None:
        if purpose_text is None:
            return None
        purpose_text = re.sub(r"\s+", " ", purpose_text.strip())
        return purpose_text or None

    def _read_profile_metadata(self, profile_path: Path) -> tuple[str | None, str | None]:
        purpose_path = self._purpose_path(profile_path)
        created_version_path = self._created_version_path(profile_path)
        purpose = purpose_path.read_text(encoding="utf-8").strip() if purpose_path.exists() else None
        created_version = (
            created_version_path.read_text(encoding="utf-8").strip() if created_version_path.exists() else None
        )
        return purpose or None, created_version or None

    def _write_profile_metadata(
        self,
        profile_path: Path,
        purpose_text: str | None = None,
        created_version: str | None = None,
        preserve_existing: bool = False,
    ) -> None:
        purpose_path = self._purpose_path(profile_path)
        created_version_path = self._created_version_path(profile_path)
        normalised_purpose = self._normalise_purpose(purpose_text)

        if normalised_purpose is not None:
            purpose_path.write_text(normalised_purpose + "\n", encoding="utf-8")
        elif not preserve_existing and purpose_path.exists():
            purpose_path.unlink()

        version_to_write = created_version if created_version is not None else self.current_version
        if version_to_write and (not preserve_existing or not created_version_path.exists()):
            created_version_path.write_text(version_to_write.strip() + "\n", encoding="utf-8")

    def _profile_display_row(self, profile_name: str, current_profile: str | None) -> tuple[str, str, str, str]:
        profile_path = self._profile_path(profile_name)
        purpose, created_version = self._read_profile_metadata(profile_path)
        marker = "*" if profile_name == current_profile else " "
        return marker, profile_name, created_version or "Unknown", purpose or "Unknown"

    def ensure_profile_metadata(
        self,
        profile_name: str,
        purpose_text: str | None = None,
        created_version: str | None = None,
        preserve_existing: bool = True,
    ) -> None:
        self._write_profile_metadata(
            self._profile_path(profile_name),
            purpose_text=purpose_text,
            created_version=created_version,
            preserve_existing=preserve_existing,
        )

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

    def import_profile(self, import_path: Path, purpose_text: str | None = None) -> None:
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

        if purpose_text is not None:
            _, existing_version = self._read_profile_metadata(target_path)
            self._write_profile_metadata(
                target_path,
                purpose_text=purpose_text,
                created_version=existing_version,
                preserve_existing=True,
            )
        else:
            self._write_profile_metadata(target_path, preserve_existing=True)

        print(f"Imported profile '{profile_name}' from {import_path}")
        config_sample = resolve_default_path(Path("resources") / "config" / "OraTAPI.ini.sample")
        config_target = target_path / "resources" / "config" / "OraTAPI.ini"
        if config_target.exists():
            compare_config_files(config_sample_file=config_sample, config_file_path=config_target)
        self._prompt_activate_profile(profile_name)

    def migrate_old_install(self, old_install_dir: Path, target_profile: str, purpose_text: str | None = None) -> None:
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
        config_sample = resolve_default_path(Path("resources") / "config" / "OraTAPI.ini.sample")
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
        default_purpose = f"Migrated from legacy install {old_install_dir.name}."
        self._write_profile_metadata(target_path, purpose_text=purpose_text or default_purpose)
        compare_config_files(config_sample_file=config_sample, config_file_path=config_target)
        self._prompt_activate_profile(target_profile)

    def list_profiles(self) -> None:
        current_profile = configured_active_profile_name()
        profiles = available_profiles()
        if not profiles:
            print("No OraTAPI profiles found.")
            return

        print("OraTAPI profiles:")
        rows = [self._profile_display_row(profile_name, current_profile) for profile_name in profiles]
        active_width = max(len("Active"), max(len(row[0]) for row in rows))
        profile_width = max(len("Profile"), max(len(row[1]) for row in rows))
        version_width = max(len("Created With"), max(len(row[2]) for row in rows))

        header = (
            f"{'Active':<{active_width}}  "
            f"{'Profile':<{profile_width}}  "
            f"{'Created With':<{version_width}}  "
            f"Purpose"
        )
        divider = (
            f"{'-' * active_width}  "
            f"{'-' * profile_width}  "
            f"{'-' * version_width}  "
            f"{'-' * len('Purpose')}"
        )
        print(header)
        print(divider)
        for active_marker, profile_name, created_version, purpose in rows:
            print(
                f"{active_marker:<{active_width}}  "
                f"{profile_name:<{profile_width}}  "
                f"{created_version:<{version_width}}  "
                f"{purpose}"
            )

    def show_active_profile(self) -> None:
        profile_name = configured_active_profile_name()
        if not profile_name:
            raise FileNotFoundError(
                "No active profile is configured. Run quick_config, or use profile_mgr -a <profile>."
            )
        active_marker, _, created_version, purpose = self._profile_display_row(profile_name, profile_name)
        profile_path = self._profile_path(profile_name)
        active_width = len("Active")
        profile_width = max(len("Profile"), len(profile_name))
        version_width = max(len("Created With"), len(created_version))

        print("Active profile:")
        print(
            f"{'Active':<{active_width}}  "
            f"{'Profile':<{profile_width}}  "
            f"{'Created With':<{version_width}}  "
            f"Purpose"
        )
        print(
            f"{'-' * active_width}  "
            f"{'-' * profile_width}  "
            f"{'-' * version_width}  "
            f"{'-' * len('Purpose')}"
        )
        print(
            f"{active_marker:<{active_width}}  "
            f"{profile_name:<{profile_width}}  "
            f"{created_version:<{version_width}}  "
            f"{purpose}"
        )
        print(f"Profile directory: {profile_path}")

    def activate_profile(self, profile_name: str) -> None:
        profile_name = self._ensure_profile_exists(profile_name).name
        write_active_profile(profile_name)
        print(f"Activated profile: {profile_name}")

    def create_profile(self, profile_name: str, purpose_text: str | None = None) -> None:
        profile_name = self._validate_profile_name(profile_name)
        target_path = self._profile_path(profile_name)
        if target_path.exists():
            raise FileExistsError(f"Profile '{profile_name}' already exists.")

        current_profile = configured_active_profile_name()
        if not current_profile:
            raise FileNotFoundError(
                "No active profile is configured. Run quick_config first, or activate an existing profile with profile_mgr -a <profile>."
            )

        source_path = active_profile_home()
        if not source_path.exists():
            raise FileNotFoundError(
                f"Active profile '{current_profile}' does not exist. Run quick_config first."
            )

        shutil.copytree(source_path, target_path)
        source_purpose, _ = self._read_profile_metadata(source_path)
        self._write_profile_metadata(target_path, purpose_text=purpose_text if purpose_text is not None else source_purpose)
        print(f"Created profile '{profile_name}' from active profile '{current_profile}'.")

    def copy_profile(self, source_profile: str, target_profile: str, purpose_text: str | None = None) -> None:
        source_profile = self._ensure_profile_exists(source_profile).name
        target_profile = self._validate_profile_name(target_profile)
        source_path = self._profile_path(source_profile)
        target_path = self._profile_path(target_profile)
        if target_path.exists():
            raise FileExistsError(f"Profile '{target_profile}' already exists.")

        shutil.copytree(source_path, target_path)
        source_purpose, _ = self._read_profile_metadata(source_path)
        self._write_profile_metadata(target_path, purpose_text=purpose_text if purpose_text is not None else source_purpose)
        print(f"Copied profile '{source_profile}' to '{target_profile}'.")

    def set_profile_purpose(self, profile_name: str, purpose_text: str | None) -> None:
        profile_path = self._ensure_profile_exists(profile_name)
        created_version = self._read_profile_metadata(profile_path)[1]
        normalised_purpose = self._normalise_purpose(purpose_text)
        if normalised_purpose:
            self._write_profile_metadata(
                profile_path,
                purpose_text=normalised_purpose,
                created_version=created_version,
                preserve_existing=True,
            )
            print(f"Updated purpose for profile '{profile_path.name}'.")
        else:
            purpose_path = self._purpose_path(profile_path)
            if purpose_path.exists():
                purpose_path.unlink()
            print(f"Cleared purpose for profile '{profile_path.name}'.")

    def delete_profile(self, profile_name: str) -> None:
        profile_name = self._validate_profile_name(profile_name)
        current_profile = configured_active_profile_name()
        if current_profile and profile_name == current_profile:
            raise ValueError("Cannot delete the active profile.")

        profile_path = self._profile_path(profile_name)
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile '{profile_name}' does not exist.")

        shutil.rmtree(profile_path)
        print(f"Deleted profile: {profile_name}")
