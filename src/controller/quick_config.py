#!/usr/bin/env python3
"""
Author: Clive Bostock
Date: 2024-12-31
Description: Script to initialise config and template files from resources/templates.
"""

import argparse
import shutil
from configparser import ConfigParser

from lib.file_system_utils import project_home
from pathlib import Path

CONFIG_LOCATION = project_home() / 'resources' / 'config'
TEMPLATES_LOCATION = project_home() / 'resources' / 'templates'
CONFIG_FILE_PATH = CONFIG_LOCATION / 'OraTAPI.ini'

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

def copy_files(template_category: str, force: bool, templates_only: bool=False) -> None:
    """
    Copies `.sample` files from a `samples` subdirectory to target locations, based on the
    template_category, and specific copying rules. Ensures OraTAPI.ini version consistency.

    :param template_category: The template category ("basic", "liquibase", "logger" or "llogger").
    :type template_category: str
    :param force: Whether to overwrite existing files.
    :type force: bool
    :param templates_only: Only instantiate the sample templates.
    """
    files_copied = 0
    config_dir = CONFIG_LOCATION
    templates_dir = TEMPLATES_LOCATION

    # Handle the config directory
    config_sample = config_dir / "samples" / "OraTAPI.ini.sample"
    config_target = config_dir / "OraTAPI.ini"

    if config_sample.exists() and (force or not config_target.exists()) and not templates_only:
        shutil.copyfile(config_sample, config_target)
        files_copied += 1
        print(f"Copied: {config_sample.relative_to(project_home())} -> {config_target.relative_to(project_home())}")
    else:
        update_version_from_sample(config_sample, config_target)

    csv_sample = config_dir / "samples" / "pi_columns.csv.sample"
    csv_target = config_dir / "pi_columns.csv"
    if config_sample.exists() and ((force and not templates_only) or not csv_target.exists()):
        shutil.copyfile(csv_sample, csv_target)
        files_copied += 1
        print(f"Copied: {csv_sample.relative_to(project_home())} -> {csv_target.relative_to(project_home())}")

    # Directories with special rules
    special_dirs = [
        templates_dir / "column_expressions" / "inserts",
        templates_dir / "column_expressions" / "updates"
    ]

    # These directories have files reflecting "basic", "liquibase" or "llogger" template samples.
    regular_dirs = [
        templates_dir / "misc" / "trigger",
        templates_dir / "misc" / "view",
        templates_dir / "packages" / "body",
        templates_dir / "packages" / "spec",
        templates_dir / "packages" / "procedures",
    ]

    # Handle special directories
    for special_dir in special_dirs:
        samples_dir = special_dir / "samples"
        if samples_dir.exists():
            for sample_file in samples_dir.glob("*.sample"):
                target_file = special_dir / sample_file.stem
                if force or not target_file.with_suffix(".tpt").exists():
                    shutil.copyfile(sample_file, target_file.with_suffix(".tpt"))
                    files_copied += 1
                    print(f"Copied: {sample_file.relative_to(project_home())} -> {target_file.with_suffix('.tpt').relative_to(project_home())}")

    # Handle regular directories
    for regular_dir in regular_dirs:
        samples_dir = regular_dir / "samples"
        if samples_dir.exists():
            for sample_file in samples_dir.glob(f"*.{template_category}.sample"):
                target_file = regular_dir / sample_file.stem
                if force or not target_file.with_suffix(".tpt").exists():
                    shutil.copyfile(sample_file, target_file.with_suffix(".tpt"))
                    files_copied += 1
                    print(f"Copied: {sample_file.relative_to(project_home())} -> {target_file.with_suffix('.tpt').relative_to(project_home())}")
    print(f"{files_copied} files instantiated.")
    compare_config_files(config_file_path=config_target, config_sample_file=config_sample)

def main() -> None:
    """
    Main function to parse arguments and initiate file copying.
    """
    parser = argparse.ArgumentParser(description="Copy template files based on template category.",
                                     epilog=" This also instantiates the control files: OraTAPI.ini, pi_columns.csv")
    parser.add_argument(
        "-t", "--template_category",
        choices=["liquibase", "basic", "logger", "llogger"],
        required=True,
        help="Specify the template category ('liquibase' or 'basic')."
    )
    parser.add_argument(
        "-T", "--templates_only",
        action="store_true",
        required=False,
        default=False,
        help="Only instantiate templates (Do not overwrite control files)."
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite existing files."
    )
    args = parser.parse_args()

    if args.templates_only and not args.force:
        print("ERROR: The -T/--templates_only argument must accompany -f/--force (Doesn't overwrite config files)")
        exit(1)

    print('OraTAPI quick config started...')
    copy_files(args.template_category, args.force, templates_only=args.templates_only)
    print('OraTAPI quick config complete.')


if __name__ == "__main__":
    main()
