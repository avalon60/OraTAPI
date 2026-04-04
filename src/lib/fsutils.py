
__author__ = "Clive Bostock"
__date__ = "2024-11-09"
__description__ = "Manages the database connection/close."


import os
import platform
import re
from contextlib import ExitStack
from functools import lru_cache
from importlib import resources
from pathlib import Path
import shutil
from typing import Iterable


PROJECT_HOME_ENV = "ORATAPI_PROJECT_HOME"
RUNTIME_HOME_DIRNAME = "OraTAPI"
PACKAGE_RESOURCE_ANCHOR = "ora_tapi_package_data"
_PACKAGE_HOME_STACK = ExitStack()
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


def _candidate_project_override_homes() -> Iterable[Path]:
    project_home_env = os.getenv(PROJECT_HOME_ENV, "").strip()
    if project_home_env:
        yield Path(project_home_env).expanduser()

    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / "resources").is_dir() and ((candidate / "src").is_dir() or (candidate / "pyproject.toml").exists()):
            yield candidate
            break


def project_override_home() -> Path | None:
    for candidate in _candidate_project_override_homes():
        if candidate.exists():
            return candidate
    return None


@lru_cache(maxsize=1)
def package_home() -> Path:
    traversable = resources.files(PACKAGE_RESOURCE_ANCHOR)
    return Path(_PACKAGE_HOME_STACK.enter_context(resources.as_file(traversable)))


def resolve_path(path_name: str | Path) -> Path:
    candidate_path = Path(path_name).expanduser()
    if candidate_path.is_absolute():
        return candidate_path

    project_home_dir = project_override_home()
    search_roots = [root for root in (project_home_dir, runtime_home(), package_home()) if root is not None]
    for root in search_roots:
        resolved = root / candidate_path
        if resolved.exists():
            return resolved

    return runtime_home() / candidate_path


def resolve_default_path(path_name: str | Path) -> Path:
    candidate_path = Path(path_name)
    if candidate_path.is_absolute():
        return candidate_path

    project_home_dir = project_override_home()
    search_roots = [root for root in (project_home_dir, package_home()) if root is not None]
    for root in search_roots:
        resolved = root / candidate_path
        if resolved.exists():
            return resolved

    return package_home() / candidate_path


def missing_runtime_paths() -> list[Path]:
    runtime_root = runtime_home()
    return [runtime_root / relative_path for relative_path in RUNTIME_REQUIRED_RELATIVE_PATHS
            if not (runtime_root / relative_path).exists()]

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
    print(f'Project Override Home: {project_override_home()}')
    print(f'Runtime Home: {runtime_home()}')
    print(f'Package Home: {package_home()}')
