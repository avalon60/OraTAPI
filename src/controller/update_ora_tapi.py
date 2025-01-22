#!/usr/bin/env python3
"""
Author: Clive Bostock
Date: 2025-01-21
Description: Script to upgrade OraTAPI by extracting a tarball and copying files from an unpacked upgrade folder.
"""
__author__ = "Clive Bostock"
__date__ = "2025-01-21"
__description__ = "Script to upgrade OraTAPI by extracting a tarball and copying files from an unpacked upgrade folder."
__version__ = "1.4.22"

import argparse
import shutil
import tarfile
import re
from pathlib import Path
from packaging.version import Version
from lib.file_system_utils import project_home

PROG_NAME = Path(__file__).name


def extract_version_from_tarball(tarball_path: Path) -> str:
    """
    Extracts the version from the tarball file name.

    :param tarball_path: Path to the tarball file.
    :return: Extracted version as a string.
    """
    match = re.search(r'oratapi-(\d+\.\d+\.\d+)\.tar\.gz$', tarball_path.name)
    if match:
        return match.group(1)
    raise ValueError(f"Invalid tarball name: {tarball_path.name}")


def confirm_action(message: str) -> bool:
    """
    Prompts the user to confirm an action.

    :param message: The confirmation message.
    :return: True if the user confirms, False otherwise.
    """
    while True:
        response = input(f"{message} [y/n]: ").strip().lower()
        if response in {"y", "yes"}:
            return True
        elif response in {"n", "no"}:
            return False


def extract_tarball(tarball_path: Path, extract_to: Path) -> Path:
    """
    Extracts a tarball to a specified directory with safety checks to avoid overwriting the current installation.

    :param tarball_path: Path to the tarball file.
    :param extract_to: Path to the directory where the tarball will be unpacked.
    :returns: Path to the root of the unpacked directory.
    """
    print(f"Extracting {tarball_path} to {extract_to}...")

    with tarfile.open(tarball_path, 'r:gz') as tar:
        # Get the root directory of the tarball
        root_dir_name = tar.getnames()[0].split('/')[0]
        unpacked_root = extract_to / root_dir_name

        # Safety check: Prevent overwriting the current installation directory
        current_installation_dir = project_home()
        if unpacked_root == current_installation_dir:
            raise RuntimeError(
                f"Extraction aborted! The tarball root directory ({unpacked_root}) matches the current installation directory. "
                f"To avoid overwriting, please move the tarball or extract it to a different location."
            )

        # Proceed with extraction
        tar.extractall(path=extract_to)

    print(f"Extraction complete. Root unpacked directory: {unpacked_root}")
    return unpacked_root


def upgrade_files(upgrade_dir: Path) -> None:
    """
    Upgrade files by copying from the upgrade directory to the existing installation.

    :param upgrade_dir: Path to the upgrade directory.
    """
    files_upgraded = 0
    current_resources = project_home() / 'resources'
    upgrade_resources = upgrade_dir / 'resources'
    root_install_dir = project_home()

    # Upgrade config samples
    config_samples_dir = upgrade_resources / "config" / "samples"
    if config_samples_dir.exists():
        for sample_file in config_samples_dir.rglob("*"):
            if sample_file.is_file():  # Ensure it is a file
                target_file = current_resources / "config" / sample_file.relative_to(config_samples_dir)
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(sample_file, target_file)
                relative_target = target_file.relative_to(root_install_dir)
                files_upgraded += 1
                print(f"Upgraded: {sample_file} -> {relative_target}")

    # Upgrade templates
    templates_dir = upgrade_resources / "templates"
    if templates_dir.exists():
        for template_file in templates_dir.rglob("*"):
            if template_file.is_file():  # Ensure it is a file
                target_file = current_resources / "templates" / template_file.relative_to(templates_dir)
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(template_file, target_file)
                relative_target = target_file.relative_to(root_install_dir)
                files_upgraded += 1
                print(f"Upgraded: {template_file} -> {relative_target}")

    # Upgrade src directory
    src_dir = upgrade_resources / "src"
    if src_dir.exists():
        for src_file in src_dir.rglob("*"):
            if src_file.is_file():  # Ensure it is a file
                target_file = root_install_dir / "src" / src_file.relative_to(src_dir)
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, target_file)
                relative_target = target_file.relative_to(root_install_dir)
                files_upgraded += 1
                print(f"Upgraded: {src_file} -> {relative_target}")

    print(f"Total files upgraded: {files_upgraded}")



def main() -> None:
    """
    Main function to parse arguments and perform actions.
    """
    print(f"{PROG_NAME}: OraTAPI upgrade utility version: {__version__}")
    print('OraTAPI upgrade started...')
    parser = argparse.ArgumentParser(
        description="Upgrade OraTAPI by unpacking a tarball and copying files to the existing installation."
    )
    parser.add_argument(
        "-t", "--tarball",
        required=True,
        help="Specify the path to the tarball file."
    )

    args = parser.parse_args()
    tarball_path = Path(args.tarball)
    extract_to = tarball_path.parent

    # Extract version from tarball
    try:
        tarball_version = Version(extract_version_from_tarball(tarball_path))
        current_version = Version(__version__)
        print(f"Current OraTAPI version: {current_version}")
        print(f"Tarball OraTAPI version: {tarball_version}")

        if tarball_version == current_version:
            print("Error: OraTAPI is already at the target version.")
            exit(1)
        elif tarball_version > current_version:
            if not confirm_action("A newer version of OraTAPI is available. Do you want to proceed with the upgrade?"):
                print("Upgrade canceled.")
                exit(0)
        else:
            print("Warning: The tarball version is older than the current version.")
            if not confirm_action("Do you still want to proceed?"):
                print("Upgrade canceled.")
                exit(0)
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)

    # Extract the tarball
    unpacked_dir = extract_tarball(tarball_path, extract_to)

    # Upgrade files
    try:
        upgrade_files(unpacked_dir)
    finally:
        print(f"Cleaning up unpacked directory: {unpacked_dir}")
        shutil.rmtree(unpacked_dir, ignore_errors=True)

    print('OraTAPI upgrade complete.')


if __name__ == "__main__":
    main()
