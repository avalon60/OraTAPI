#!/usr/bin/env python3
"""
Author: Clive Bostock
Date: 2024-12-31
Description: Script to migrate, export, or import configuration and template files for OraTAPI.
"""
__author__ = "Clive Bostock"
__date__ = "2024-12-31"
__description__ = "Script to migrate, export, or import configuration and template files for OraTAPI."
__version__ = "1.4.4"

import argparse
import shutil
import zipfile
from configparser import ConfigParser
from pathlib import Path

from lib.file_system_utils import project_home

PROG_NAME = Path(__file__).name

def export_resources(export_path: Path) -> None:
    """
    Export the resources directory (excluding 'samples') to a ZIP file.

    :param export_path: Path to the export ZIP file.
    """
    resources_dir = project_home() / "resources"
    with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in resources_dir.rglob('*'):
            if "samples" in file.parts:
                continue
            relative_path = file.relative_to(resources_dir)
            zipf.write(file, relative_path)
    print(f"Exported resources to {export_path}")


def import_resources(import_path: Path) -> None:
    """
    Import a ZIP archive into the resources' directory.

    :param import_path: Path to the import ZIP file.
    """
    resources_dir = project_home() / "resources"
    with zipfile.ZipFile(import_path, 'r') as zipf:
        zipf.extractall(resources_dir)
    print(f"Imported resources from {import_path}")

    config_sample = resources_dir / "config" / "samples" / "OraTAPI.ini.sample"
    config_target = resources_dir / "config" / "OraTAPI.ini"
    compare_config_files(config_sample_file=config_sample, config_file_path=config_target)


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
            print(f"WARNING: Obsoleted keys from section [{section}]: {', '.join(deprecated_keys)}")

    for section in current_config.sections():
        if section not in sample_config:
            print(f"WARNING: Obsoleted section found: [{section}] - persists in current config.")

    if 'logger' in deprecated_sections:
        print("Deprecated section: [logger]")

    print('\nOraTAPI.ini checks complete.\n')


def migrate_files(previous_install_dir: Path) -> None:
    """
    Migrate files from the previous installation.

    :param previous_install_dir: Path to the previous installation directory.
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
    print(f"Migrated: {previous_install_config_file.absolute()} -> {config_target.absolute()}")
    files_migrated += 1

    ora_tapi_csv_previous = previous_config_dir / "OraTAPI.csv"
    ora_tapi_csv_new = config_dir / "OraTAPI.csv"
    if ora_tapi_csv_previous.exists():
        shutil.copyfile(ora_tapi_csv_previous, ora_tapi_csv_new)
        print(f"Migrated: {ora_tapi_csv_previous.absolute()} -> {ora_tapi_csv_new.absolute()}")
        files_migrated += 1

    pi_columns_csv_previous = previous_config_dir /  "pi_columns.csv"
    pi_columns_csv_new = config_dir / "pi_columns.csv"
    shutil.copyfile(pi_columns_csv_previous, pi_columns_csv_new)
    files_migrated += 1

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
        templates_dir / "column_expressions" / "updates",
        templates_dir / "ut_packages" / "body",
        templates_dir / "ut_packages" / "spec"
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
    Main function to parse arguments and perform actions.
    """
    print(f"{PROG_NAME}: OraTAPI migration/export/import utility version: {__version__}")
    print('OraTAPI config migration started...')
    parser = argparse.ArgumentParser(
        description="Migrate, export, or import OraTAPI configuration and template files."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-o", "--old_install_dir",
        help="Specify the old OraTAPI installation directory."
    )
    group.add_argument(
        "-e", "--export",
        metavar="<export_zip_path>",
        help="Export resources to a ZIP file."
    )
    group.add_argument(
        "-i", "--import_resources",
        metavar="<import_zip_path>",
        help="Import resources from a ZIP file."
    )

    args = parser.parse_args()

    if args.old_install_dir:
        migrate_files(Path(args.old_install_dir))
    elif args.export:
        export_resources(Path(args.export))
    elif args.import_resources:
        import_resources(Path(args.import_resources))

    print('OraTAPI operation complete.')


if __name__ == "__main__":
    main()
