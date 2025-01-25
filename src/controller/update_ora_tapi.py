#!/usr/bin/env python3
"""
Author: Clive Bostock
Date: 2025-01-21
Description: Script to upgrade OraTAPI by extracting a tarball and copying files from an unpacked upgrade folder or by downloading the latest version from GitHub.
"""
__author__ = "Clive Bostock"
__date__ = "2025-01-21"
__description__ = "Script to upgrade OraTAPI by extracting a tarball and copying files from an unpacked upgrade folder or by downloading the latest version from GitHub."
from controller.ora_tapi import __version__

import argparse
import shutil
import tarfile
import re
from pathlib import Path
from packaging.version import Version
from lib.file_system_utils import project_home
from lib.app_utils import get_latest_version, get_latest_dist_url, download_file
import os
import subprocess
import platform

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
    src_dir = upgrade_dir / "src"
    if src_dir.exists():
        for src_file in src_dir.rglob("*"):
            if src_file.is_file():  # Ensure it is a file
                target_file = root_install_dir / "src" / src_file.relative_to(src_dir)
                target_file.parent.mkdir(parents=True, exist_ok=True)
                relative_target = target_file.relative_to(root_install_dir)
                try:
                    shutil.copy2(src_file, target_file)
                except PermissionError:
                    print(f'File busy, skipped: {relative_target}')
                files_upgraded += 1
                print(f"Upgraded: {src_file} -> {relative_target}")

    # Upgrade bin directory
    src_dir = upgrade_dir / "bin"
    if src_dir.exists():
        for src_file in src_dir.rglob("*"):
            if src_file.is_file():  # Ensure it is a file
                target_file = root_install_dir / "bin" / src_file.relative_to(src_dir)
                target_file.parent.mkdir(parents=True, exist_ok=True)
                relative_target = target_file.relative_to(root_install_dir)
                try:
                    shutil.copy2(src_file, target_file)
                except PermissionError:
                    print(f'File busy, skipped: {relative_target}')
                files_upgraded += 1
                print(f"Upgraded: {src_file} -> {relative_target}")

    # Copy pyproject.toml and requirements.txt from the upgrade directory
    for filename in ['pyproject.toml', 'requirements.txt', 'setup.sh', 'setup.ps1', 'LICENSE', 'README.md']:
        upgrade_file = upgrade_dir / filename
        if upgrade_file.exists() and upgrade_file.is_file():
            target_file = root_install_dir / filename
            shutil.copy2(upgrade_file, target_file)
            print(f"Upgraded: {upgrade_file} -> {target_file}")
            files_upgraded += 1

    print(f"Total files upgraded: {files_upgraded}")


def validate_staging_directory(staging_dir: Path) -> None:
    """
    Ensures the specified staging directory exists.

    :param staging_dir: Path to the staging directory.
    :raises: ValueError if the directory does not exist.
    """
    if not staging_dir.is_dir():
        raise ValueError(f"Error: Staging directory '{staging_dir}' does not exist.")


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

def set_setup_perms():
    """
    Runs the setup script (either `setup.ps1` on Windows or `setup.sh` on Linux/macOS).

    """
    # Determine the operating system
    is_windows = platform.system() == "Windows"

    # Select the appropriate setup script based on the OS
    if not is_windows:
        setup_script = project_home() / 'setup.sh'

        # Adjust file permissions (chmod 750)
        print(f"Adjusting permissions for: {setup_script}")
        setup_script.chmod(0o750)

def run_setup():
    """
    Runs the setup script (either `setup.ps1` on Windows or `setup.sh` on Linux/macOS).

    """
    # Determine the operating system
    is_windows = platform.system() == "Windows"

    # Select the appropriate setup script based on the OS
    if is_windows:
        setup_script = project_home() / 'setup.ps1'
        print(f"Running setup script: {setup_script}")

        # Execute the PowerShell script using subprocess
        try:
            subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(setup_script)], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running setup script: {e}")
            raise
    else:
        setup_script = project_home() / 'setup.sh'

        # Adjust file permissions (chmod 750)
        print(f"Adjusting permissions for: {setup_script}")
        setup_script.chmod(0o750)

        # Execute the shell script
        print(f"Running setup script: {setup_script}")
        try:
            subprocess.run(["bash", str(setup_script)], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running setup script: {e}")
            raise

def main() -> None:
    """
    Main function to parse arguments and perform actions.
    """
    print(f"{PROG_NAME}: OraTAPI upgrade utility version: {__version__}")
    print('OraTAPI upgrade started...')
    parser = argparse.ArgumentParser(
        description="Upgrade OraTAPI by unpacking a tarball or downloading the latest version from GitHub."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-t", "--tarball",
        type=str,
        help="Specify the path to the tarball file."
    )
    group.add_argument(
        "-s", "--staging-dir",
        type=str,
        help="Specify a staging directory to download the latest version from GitHub."
    )

    args = parser.parse_args()

    if args.tarball:
        tarball_path = Path(args.tarball)
        extract_to = tarball_path.parent

        try:
            tarball_version = Version(extract_version_from_tarball(tarball_path))
            current_version = Version(__version__)
            print(f"Current OraTAPI version: {current_version}")
            print(f"Tarball OraTAPI version: {tarball_version}")

            if tarball_version == current_version:
                print("Error: OraTAPI is already at the target version.")
                exit(1)
            elif tarball_version > current_version:
                if not confirm_action(
                        "A newer version of OraTAPI is available. Do you want to proceed with the upgrade?"):
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

    elif args.staging_dir:
        staging_dir = Path(args.staging_dir)
        validate_staging_directory(staging_dir)

        try:
            # Get the latest version from GitHub
            latest_version = Version(get_latest_version("avalon60", "OraTAPI"))
            current_version = Version(__version__)
            print(f"Current OraTAPI version: {current_version}")
            print(f"Latest OraTAPI version on GitHub: {latest_version}")

            if latest_version == current_version:
                print("OraTAPI is already up to date.")
                exit(0)
            elif latest_version > current_version:
                if not confirm_action("A newer version is available on GitHub. Do you want to download it?"):
                    print("Download canceled.")
                    exit(0)

                tarball_url = get_latest_dist_url("avalon60", "OraTAPI")

                # Validate the URL before proceeding
                if not tarball_url or "http" not in tarball_url:
                    print(f"Error: Failed to fetch the tarball URL. Details: {tarball_url}")
                    exit(1)

                tarball_path = staging_dir / Path(tarball_url).name
                print(f"Downloading to: {tarball_path}")
                download_file(url=tarball_url, save_dir=staging_dir)

                if not confirm_action("Download complete. Do you want to proceed with the upgrade?"):
                    print("Upgrade canceled.")
                    exit(0)
            else:
                print("Warning: The latest version on GitHub is older than the current version.")
                exit(0)

        except Exception as e:
            print(f"Error: Unable to fetch the latest version or download the tarball. Details: {e}")
            exit(1)

        # Extract the tarball
        unpacked_dir = extract_tarball(tarball_path, staging_dir)

        # Upgrade files
        try:
            upgrade_files(unpacked_dir)
        finally:
            print(f"Cleaning up unpacked directory: {unpacked_dir}")
            shutil.rmtree(unpacked_dir, ignore_errors=True)


    is_windows = platform.system() == "Windows"

    if is_windows:
        print("Please run the setup.ps1 script to complete the upgrade.")
    else:
        set_setup_perms()
        print("Please run the setup.sh script to complete the upgrade.")


if __name__ == "__main__":
    main()
