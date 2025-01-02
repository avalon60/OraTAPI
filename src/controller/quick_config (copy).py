#!/usr/bin/env python3
"""
Author: Clive Bostock
Date: 2025-01-01
Description: Script to initialise config and template files from resources/templates.
"""

import argparse
import shutil
from configparser import ConfigParser
from pathlib import Path
from lib.file_system_utils import project_home

CONFIG_LOCATION = project_home() / 'resources' / 'config'
TEMPLATES_LOCATION = project_home() / 'resources' / 'templates'
config_file_path = CONFIG_LOCATION / 'OraTAPI.ini'


def update_version_from_sample(sample_file: Path, target_file: Path) -> None:
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


def compare_config_files(config_file: Path, config_sample_file: Path) -> None:
    """
    Compares the OraTAPI.ini file with the OraTAPI.ini.sample file to report
    new sections/keys and deprecated sections/keys.

    :param config_file: Path to the target configuration file.
    :param config_sample_file: Path to the sample configuration file.
    """
    current_config = ConfigParser()
    sample_config = ConfigParser()

    current_config.read(config_file)
    sample_config.read(config_sample_file)

    new_sections = set(sample_config.sections()) - set(current_config.sections())
    deprecated_sections = set(current_config.sections()) - set(sample_config.sections())
    print(f"New sections found in sample: {', '.join(new_sections)}")
    print(f"Deprecated sections: {', '.join(deprecated_sections)}")

    for section in sample_config.sections():
        if section not in current_config:
            print(f"Section [{section}] not found in current config.")
            continue

        new_keys = set(sample_config[section].keys()) - set(current_config[section].keys())
        deprecated_keys = set(current_config[section].keys()) - set(sample_config[section].keys())

        if new_keys:
            print(f"New keys found in section [{section}]: {', '.join(new_keys)}")

        if deprecated_keys:
            print(f"Deprecated keys in section [{section}]: {', '.join(deprecated_keys)}")

        for key in new_keys:
            print(f"New key in [{section}]: {key} = {sample_config[section][key]}")
        for key in deprecated_keys:
            print(f"Deprecated key in [{section}]: {key} = {current_config[section][key]}")

    if 'logger' in deprecated_sections:
        print("Deprecated section: [logger]")


def copy_files(template_category: str, force: bool, transfer_dir: Path = None) -> None:
    """
    Copies `.sample` files from a `samples` subdirectory to target locations, based on the
    template_category, and specific copying rules. Ensures OraTAPI.ini version consistency.

    :param template_category: The template category ("basic", "liquibase" or "llogger").
    :type template_category: str
    :param force: Whether to overwrite existing files.
    :type force: bool
    :param transfer_dir: Directory path to transfer files from a previous installation.
    :type transfer_dir: Path, optional
    """
    files_copied = 0

    config_sample = CONFIG_LOCATION / "samples" / "OraTAPI.ini.sample"
    if transfer_dir:
        transfer_config = Path(transfer_dir) / "resources" / "config"
        transfer_templates = Path(transfer_dir) / "resources" / "templates"

        for file_name in ["OraTAPI.ini", "pi_columns.csv"]:
            source_file = transfer_config / file_name
            target_file = CONFIG_LOCATION / file_name
            if source_file.exists() and (force or not target_file.exists()):
                shutil.copyfile(source_file, target_file)
                files_copied += 1
                print(f"Copied: {source_file} -> {target_file}")
            if file_name == "OraTAPI.ini":
                update_version_from_sample(config_sample, target_file)

        for subdir in ["column_expressions", "misc", "packages"]:
            source_subdir = transfer_templates / subdir
            target_subdir = TEMPLATES_LOCATION / subdir

            if source_subdir.exists():
                for source_file in source_subdir.rglob("*"):
                    if source_file.is_file():
                        relative_path = source_file.relative_to(transfer_templates)
                        target_file = TEMPLATES_LOCATION / relative_path

                        if force or not target_file.exists():
                            target_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copyfile(source_file, target_file)
                            files_copied += 1
                            print(f"Copied: {source_file} -> {target_file}")
    else:
        config_sample = CONFIG_LOCATION / "samples" / "OraTAPI.ini.sample"
        config_target = CONFIG_LOCATION / "OraTAPI.ini"

        if config_sample.exists():
            if force or not config_target.exists():
                shutil.copyfile(config_sample, config_target)
                files_copied += 1
                print(f"Copied: {config_sample.relative_to(project_home())} -> {config_target.relative_to(project_home())}")
            update_version_from_sample(config_sample, config_target)

        config_sample = CONFIG_LOCATION / "samples" / "pi_columns.csv.sample"
        config_target = CONFIG_LOCATION / "pi_columns.csv"
        if config_sample.exists() and (force or not config_target.exists()):
            shutil.copyfile(config_sample, config_target)
            files_copied += 1
            print(f"Copied: {config_sample.relative_to(project_home())} -> {config_target.relative_to(project_home())}")

        for subdir in ["column_expressions", "misc", "packages"]:
            samples_dir = TEMPLATES_LOCATION / subdir / "samples"
            if samples_dir.exists():
                for sample_file in samples_dir.glob(f"*.{template_category}.sample"):
                    target_file = TEMPLATES_LOCATION / subdir / sample_file.stem
                    if force or not target_file.with_suffix(".tpt").exists():
                        shutil.copyfile(sample_file, target_file.with_suffix(".tpt"))
                        files_copied += 1
                        print(f"Copied: {sample_file.relative_to(project_home())} -> {target_file.with_suffix('.tpt').relative_to(project_home())}")

    print(f"{files_copied} files instantiated.")


def main() -> None:
    """
    Main function to parse arguments and initiate file copying.
    """
    print('OraTAPI quick config started...')
    parser = argparse.ArgumentParser(description="Copy template files based on template category.")
    parser.add_argument(
        "-t", "--template_category",
        choices=["liquibase", "basic", "llogger"],
        help="Specify the template category ('liquibase', 'basic', or 'llogger')."
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite existing files."
    )
    parser.add_argument(
        "-T", "--transfer_dir",
        type=Path,
        help="Path to the previous installation directory to transfer resources."
    )
    args = parser.parse_args()

    if not args.transfer_dir and not args.template_category:
        parser.error("Either --template_category or --transfer_dir must be specified.")

    copy_files(args.template_category, args.force, args.transfer_dir)

    config_file = CONFIG_LOCATION / 'OraTAPI.ini'
    config_sample_file = CONFIG_LOCATION / 'samples' / 'OraTAPI.ini.sample'
    compare_config_files(config_file, config_sample_file)

    print('OraTAPI quick config complete.')


if __name__ == "__main__":
    main()
