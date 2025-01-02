#!/usr/bin/env python3
"""
Author: Clive Bostock
Date: 2024-12-31
Description: Script to initialise config and template files from resources/templates.
"""

import argparse
import shutil
from configparser import ConfigParser

from setuptools.command.setopt import config_file

from lib.file_system_utils import project_home
from pathlib import Path


def compare_config_files(config_file_path: Path, config_sample_file: Path) -> None:
    """
    Compares the OraTAPI.ini file with the OraTAPI.ini.sample file to report
    new sections/keys and deprecated sections/keys.

    :param config_file_path: Path to the target configuration file.
    :param config_sample_file: Path to the sample configuration file.
    """
    print('\nChecking for OraTAPI.ini updates/deprecations...')
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

    # If no changes found in sections
    if not new_sections and not deprecated_sections:
        print("\nNo config changes introduced with release.")

    for section in sample_config.sections():
        if section not in current_config:
            print(f"WARNING: New section introduced: [{section}] - not yet implemented in current config.")
            continue

        new_keys = set(sample_config[section].keys()) - set(current_config[section].keys())
        deprecated_keys = set(current_config[section].keys()) - set(sample_config[section].keys())

        if new_keys:
            print(f"WARNING: New keys introduced for section [{section}]: {', '.join(new_keys)}")

        if deprecated_keys:
            print(f"WARNING: Deprecated keys from section [{section}]: {', '.join(deprecated_keys)}")

    for section in current_config.sections():
        if section not in sample_config:
            print(f"WARNING: Deprecated section found: [{section}] - persists in current config.")

    if 'logger' in deprecated_sections:
        print("Deprecated section: [logger]")

    print('\nOraTAPI.ini checks complete.\n')


def update_version_from_sample(sample_file, target_file):
    """
    Reads the version from the OraTAPI.ini.sample file and updates it in the target OraTAPI.ini file.

    :param sample_file: Path to the sample configuration file.
    :param target_file: Path to the target configuration file.
    """
    sample_config = ConfigParser()
    sample_config.read(sample_file)

    if "OraTAPI" in sample_config and "version" in sample_config["OraTAPI"]:
        version = sample_config["OraTAPI"]["version"]

        target_config = ConfigParser()
        if target_file.exists():
            target_config.read(target_file)
        else:
            target_config.add_section("OraTAPI")

        target_config["OraTAPI"]["version"] = version

        with target_file.open("w", encoding="utf-8") as f:
            target_config.write(f)

        print(f"Updated version in {target_file.relative_to(project_home())} to {version}.")
    else:
        print(f"Version not found in {sample_file.relative_to(project_home())}.")


def migrate_files(previous_install_dir: Path) -> None:
    """
    Migrate `OraTAPI.ini`, `pi_columns.csv`, and template files from the previous installation's resources/config and
    resources/templates sub-folders to the new installation.
    """
    files_migrated = 0
    new_install_resources = project_home() / 'resources'
    config_dir = new_install_resources / 'config'
    templates_dir = new_install_resources / 'templates'  # Corrected to the new path
    previous_install_resources = previous_install_dir / 'resources'

    # Handle the config directory
    config_sample = config_dir / "samples" / "OraTAPI.ini.sample"
    previous_config_dir = previous_install_resources / "config"
    previous_install_config_file = previous_config_dir / "OraTAPI.ini"
    config_target = config_dir / "OraTAPI.ini"

    shutil.copyfile(previous_install_config_file, config_target)
    files_migrated += 1

    ora_tapi_csv_previous = previous_config_dir / "OraTAPI.csv"
    ora_tapi_csv_new = config_dir / "OraTAPI.csv"
    if ora_tapi_csv_previous.exists():
        shutil.copyfile(ora_tapi_csv_previous, ora_tapi_csv_new)
        files_migrated += 1

    pi_columns_csv_previous = previous_config_dir /  "pi_columns.csv"
    pi_columns_csv_new = config_dir / "pi_columns.csv"
    shutil.copyfile(pi_columns_csv_previous, pi_columns_csv_new)
    files_migrated += 1
    update_version_from_sample(config_sample, config_target)
    print(f"Migrated: {pi_columns_csv_previous.absolute()} -> {pi_columns_csv_new.absolute()}")


    # Template directories to migrate from previous installation
    previous_templates_dir = previous_install_dir / 'resources' / 'templates'

    templates_dirs = [
        templates_dir / "misc" / "trigger",
        templates_dir / "misc" / "view",
        templates_dir / "packages" / "body",
        templates_dir / "packages" / "spec",
        templates_dir / "packages" / "procedures",
        templates_dir / "column_expressions" / "inserts",
        templates_dir / "column_expressions" / "updates"
    ]

    # Loop through the templates directories to copy all .tpt files
    for template_dir in templates_dirs:
        # Ensure the target directory exists
        template_dir.mkdir(parents=True, exist_ok=True)

        # Search for all .tpt files in the corresponding subdirectory of the previous installation
        source_template_dir = previous_templates_dir / template_dir.relative_to(templates_dir)
        if source_template_dir.exists() and source_template_dir.is_dir():
            for tpt_file in source_template_dir.rglob('*.tpt'):
                target_file = template_dir / tpt_file.name
                shutil.copy2(tpt_file, target_file)
                files_migrated += 1
                print(
                    f"Migrated: {tpt_file.relative_to(previous_install_dir)} -> {target_file.relative_to(project_home())}")

    print(f"Total files migrated: {files_migrated}")

    compare_config_files(config_sample_file=config_sample, config_file_path=config_target)


def main() -> None:
    """
    Main function to parse arguments and initiate file copying.
    """
    print('OraTAPI config migration started...')
    parser = argparse.ArgumentParser(description="Migrate configuration files (OraTAPI.ini, CSV and templates) from a previous installation.")
    parser.add_argument(
        "-o", "--old_install_dir",
        required=True,
        help="Specify the old OraTAPI installation directory."
    )

    args = parser.parse_args()

    migrate_files(Path(args.old_install_dir))
    print('OraTAPI migration complete.')


if __name__ == "__main__":
    main()
