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
from pathlib import Path
from configparser import ConfigParser
from lib.file_system_utils import project_home

PROG_NAME = Path(__file__).name


def extract_tarball(tarball_path: Path, extract_to: Path) -> Path:
    """
    Extracts a tarball to a specified directory.

    :param tarball_path: Path to the tarball file.
    :param extract_to: Path to the directory where the tarball will be unpacked.
    :returns: Path to the root of the unpacked directory.
    """
    print(f"Extracting {tarball_path} to {extract_to}...")
    with tarfile.open(tarball_path, 'r:gz') as tar:
        tar.extractall(path=extract_to)
    unpacked_root = extract_to / tar.getnames()[0].split('/')[0]
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

    # Upgrade config samples
    config_samples_dir = upgrade_resources / "config" / "samples"
    if config_samples_dir.exists():
        for sample_file in config_samples_dir.rglob("*"):
            target_file = current_resources / "config" / sample_file.relative_to(config_samples_dir)
            target_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sample_file, target_file)
            files_upgraded += 1
            print(f"Upgraded: {sample_file} -> {target_file}")

    # Upgrade templates
    templates_dir = upgrade_resources / "templates"
    if templates_dir.exists():
        for template_file in templates_dir.rglob("*"):
            target_file = current_resources / "templates" / template_file.relative_to(templates_dir)
            target_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(template_file, target_file)
            files_upgraded += 1
            print(f"Upgraded: {template_file} -> {target_file}")

    # Upgrade src directory
    src_dir = upgrade_resources / "src"
    if src_dir.exists():
        for src_file in src_dir.rglob("*"):
            target_file = project_home() / "src" / src_file.relative_to(src_dir)
            target_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, target_file)
            files_upgraded += 1
            print(f"Upgraded: {src_file} -> {target_file}")

    print(f"Total files upgraded: {files_upgraded}")


def compare_config_files(config_file_path: Path, config_sample_file: Path) -> None:
    """
    Compare configuration files to detect changes.

    :param config_file_path: Path to the current config file.
    :param config_sample_file: Path to the sample config file.
    """
    print('\nChecking for OraTAPI.ini updates/obsolescence...')
    current_config = ConfigParser()
    sample_config = ConfigParser()

    current_config.read(config_file_path)
    sample_config.read(config_sample_file)

    new_sections = set(sample_config.sections()) - set(current_config.sections())
    deprecated_sections = set(current_config.sections()) - set(sample_config.sections())

    if new_sections:
        print(f"New sections found in supplied OraTAPI.ini.sample: {', '.join(new_sections)}")
    if deprecated_sections:
        print(f"Deprecated sections: {', '.join(deprecated_sections)}")

    for section in sample_config.sections():
        if section not in current_config:
            print(f"WARNING: New section introduced: [{section}]")
            continue

        new_keys = set(sample_config[section].keys()) - set(current_config[section].keys())
        deprecated_keys = set(current_config[section].keys()) - set(sample_config[section].keys())

        if new_keys:
            print(f"WARNING: New keys in section [{section}]: {', '.join(new_keys)}")
        if deprecated_keys:
            print(f"WARNING: Deprecated keys in section [{section}]: {', '.join(deprecated_keys)}")

    print('\nOraTAPI.ini checks complete.\n')


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

    # Extract the tarball
    unpacked_dir = extract_tarball(tarball_path, extract_to)

    # Upgrade files
    try:
        upgrade_files(unpacked_dir)
    finally:
        # Clean up the unpacked directory
        print(f"Cleaning up unpacked directory: {unpacked_dir}")
        shutil.rmtree(unpacked_dir, ignore_errors=True)

    print('OraTAPI upgrade complete.')


if __name__ == "__main__":
    main()
