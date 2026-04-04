
__author__ = "Clive Bostock"
__date__ = "2024-11-09"
__description__ = "Manages the database connection/close."

import platform
import re
from contextlib import ExitStack
from functools import lru_cache
from importlib import resources
from pathlib import Path
import shutil


RUNTIME_HOME_DIRNAME = "OraTAPI"
PACKAGE_RESOURCE_ANCHOR = "ora_tapi_package_data"
_PACKAGE_HOME_STACK = ExitStack()
DEFAULT_PROFILE_NAME = "default"
CONFIGS_DIRNAME = "configs"
ACTIVE_PROFILE_FILENAME = "active_config"
RUNTIME_REQUIRED_RELATIVE_PATHS = [
    Path("resources/config/OraTAPI.ini"),
    Path("resources/config/pi_columns.csv"),
    Path("resources/templates/column_expressions/inserts/created_by.tpt"),
    Path("resources/templates/column_expressions/inserts/created_on.tpt"),
    Path("resources/templates/column_expressions/inserts/updated_by.tpt"),
    Path("resources/templates/column_expressions/inserts/updated_on.tpt"),
    Path("resources/templates/column_expressions/inserts/row_version.tpt"),
    Path("resources/templates/column_expressions/updates/created_by.tpt"),
    Path("resources/templates/column_expressions/updates/created_on.tpt"),
    Path("resources/templates/column_expressions/updates/updated_by.tpt"),
    Path("resources/templates/column_expressions/updates/updated_on.tpt"),
    Path("resources/templates/column_expressions/updates/row_version.tpt"),
    Path("resources/templates/misc/trigger/table_name_biu.tpt"),
    Path("resources/templates/misc/view/view.tpt"),
    Path("resources/templates/packages/body/package_header.tpt"),
    Path("resources/templates/packages/body/package_footer.tpt"),
    Path("resources/templates/packages/spec/package_header.tpt"),
    Path("resources/templates/packages/spec/package_footer.tpt"),
    Path("resources/templates/packages/procedures/insert.tpt"),
    Path("resources/templates/packages/procedures/select.tpt"),
    Path("resources/templates/packages/procedures/update.tpt"),
    Path("resources/templates/packages/procedures/delete.tpt"),
    Path("resources/templates/packages/procedures/upsert.tpt"),
    Path("resources/templates/packages/procedures/merge.tpt"),
    Path("resources/templates/ut_packages/body/package_header.tpt"),
    Path("resources/templates/ut_packages/body/package_footer.tpt"),
    Path("resources/templates/ut_packages/body/before.tpt"),
    Path("resources/templates/ut_packages/body/after.tpt"),
    Path("resources/templates/ut_packages/body/api_test.tpt"),
    Path("resources/templates/ut_packages/body/constraint_test.tpt"),
    Path("resources/templates/ut_packages/spec/package_header.tpt"),
    Path("resources/templates/ut_packages/spec/package_footer.tpt"),
    Path("resources/templates/ut_packages/spec/before.tpt"),
    Path("resources/templates/ut_packages/spec/after.tpt"),
    Path("resources/templates/ut_packages/spec/api_test.tpt"),
    Path("resources/templates/ut_packages/spec/constraint_test.tpt"),
]


def runtime_home() -> Path:
    return Path.home() / RUNTIME_HOME_DIRNAME


def runtime_configs_home() -> Path:
    return runtime_home() / CONFIGS_DIRNAME


def active_profile_pointer_file() -> Path:
    return runtime_home() / ACTIVE_PROFILE_FILENAME


def active_profile_name() -> str:
    pointer_file = active_profile_pointer_file()
    if not pointer_file.exists():
        return DEFAULT_PROFILE_NAME

    profile_name = pointer_file.read_text(encoding="utf-8").strip()
    return profile_name or DEFAULT_PROFILE_NAME


def profile_home(profile_name: str) -> Path:
    return runtime_configs_home() / profile_name


def active_profile_home() -> Path:
    return profile_home(active_profile_name())


def ensure_runtime_home() -> Path:
    runtime_root = runtime_home()
    runtime_root.mkdir(parents=True, exist_ok=True)
    runtime_configs_home().mkdir(parents=True, exist_ok=True)
    return runtime_root


def write_active_profile(profile_name: str) -> None:
    ensure_runtime_home()
    active_profile_pointer_file().write_text(profile_name.strip(), encoding="utf-8")


def available_profiles() -> list[str]:
    configs_root = runtime_configs_home()
    if not configs_root.exists():
        return []
    return sorted(path.name for path in configs_root.iterdir() if path.is_dir())


@lru_cache(maxsize=1)
def package_home() -> Path:
    traversable = resources.files(PACKAGE_RESOURCE_ANCHOR)
    return Path(_PACKAGE_HOME_STACK.enter_context(resources.as_file(traversable)))


def resolve_path(path_name: str | Path) -> Path:
    candidate_path = Path(path_name).expanduser()
    if candidate_path.is_absolute():
        return candidate_path

    return active_profile_home() / candidate_path


def resolve_default_path(path_name: str | Path) -> Path:
    candidate_path = Path(path_name)
    if candidate_path.is_absolute():
        return candidate_path

    return package_home() / candidate_path


def missing_runtime_paths() -> list[Path]:
    profile_root = active_profile_home()
    return [profile_root / relative_path for relative_path in RUNTIME_REQUIRED_RELATIVE_PATHS
            if not (profile_root / relative_path).exists()]

def is_valid_dir_name(directory_name: str) -> bool:
    """
    Checks if a string is a valid directory name for the current operating system.

    :param directory_name: The input string to check.
    :type directory_name: str
    :return: True if the string is valid, False otherwise.
    :rtype: bool
    """
    # Determine the invalid characters based on the OS
    if platform.system() == "Windows":
        # Windows restrictions: \ / : * ? " < > |
        invalid_pattern = r'[\\/:*?"<>|]'
    else:
        # Unix-like systems restrictions: /
        invalid_pattern = r'[\/]'

    # Check for invalid characters
    if re.search(invalid_pattern, directory_name):
        return False

    # Optional: Ensure it's not empty or just whitespace
    if not directory_name.strip():
        return False

    return True


def sanitise_dir_name(directory_name: str) -> str:
    """
    Sanitises a string to make it a valid directory name by removing invalid characters.

    :param directory_name: The input string to sanitise.
    :type directory_name: str
    :return: A sanitised directory name.
    :rtype: str
    """
    # Determine the invalid characters based on the OS

    # invalid_chars = r'[\/]'       # Linux
    invalid_chars = r'[\\/:*?"<>|]' # We adopt Windows invalid characters

    # Replace invalid characters with an underscore or another safe character
    sanitised_name = re.sub(invalid_chars, '', directory_name)

    # Remove any leading or trailing whitespace
    sanitised_name = sanitised_name.strip()

    # Optional: Ensure the directory name is not empty after sanitisation
    if not sanitised_name:
        raise ValueError("The directory name is empty after sanitisation.")

    return sanitised_name

def zip_directory(zip_source_dir: Path, zip_file_name, destination_dir: Path = None):
    """Zips a directory and its contents into a zip file. If a destination_dir is provided, the generated zip file is
    relocated to destination_dir.

      :param zip_source_dir: The path to the directory to zip.
      :type zip_source_dir: Path
      :param zip_file_name: The path to the output zip file.
      :type zip_file_name: str
      :param destination_dir: The place to locate the generated zip file.
      :type destination_dir:
    """

    # The make_archive method automatically adds a .zip extension. So we remove it.
    _zip_file = zip_file_name.replace('.zip', '')
    shutil.make_archive(_zip_file, 'zip', zip_source_dir)

    if destination_dir:
        if not destination_dir.exists():
            destination_dir.mkdir()
        shutil.move(_zip_file + '.zip', destination_dir)

if __name__ == "__main__":

    dir_name = '?[abc\/?'
    sanitised_dir_name = sanitise_dir_name(directory_name=dir_name)
    print(f"sanitised directory name: {sanitised_dir_name}")
    print(f'Runtime Home: {runtime_home()}')
    print(f'Configs Home: {runtime_configs_home()}')
    print(f'Active Profile Name: {active_profile_name()}')
    print(f'Active Profile Home: {active_profile_home()}')
    print(f'Package Home: {package_home()}')
