#!/usr/bin/env python3
"""
Author: Clive Bostock
Date: 2024-12-27
Description: Script to initialise config and template files from resources/templates.
"""

import argparse
import shutil
from lib.file_system_utils import project_home

CONFIG_LOCATION = project_home() / 'resources' / 'config'
TEMPLATES_LOCATION = project_home() / 'resources' / 'templates'
config_file_path = CONFIG_LOCATION / 'OraTAPI.ini'

def copy_files(template_category: str, force: bool) -> None:
    """
    This copies `.sample` files from a `samples` subdirectory to
    target locations, based on the template_category, and specific copying rules.
    We initialise by copying only when files do not exist, unless `force` is specified.

    :param template_category: The template category ("basic", "liquibase" or "llogger").
    :type template_category: str
    :param force: Whether to overwrite existing files.
    :type force: bool
    """
    files_copied = 0
    config_dir = CONFIG_LOCATION
    templates_dir = TEMPLATES_LOCATION

    # Handle the config directory
    config_sample = config_dir / "samples" / "OraTAPI.ini.sample"
    config_target = config_dir / "OraTAPI.ini"
    if config_sample.exists() and (force or not config_target.exists()):
        shutil.copyfile(config_sample, config_target)
        files_copied += 1
        print(f"Copied: {config_sample.relative_to(project_home())} -> {config_target.relative_to(project_home())}")

    # Directories with special rules
    special_dirs = [
        templates_dir / "column_expressions" / "inserts",
        templates_dir / "column_expressions" / "updates"
    ]

    # These directories have files reflecting "basic", "liquibase" ot "llogger" template samples.
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

def main() -> None:
    """
    Main function to parse arguments and initiate file copying.
    """
    print('OraTAPI quick config started...')
    parser = argparse.ArgumentParser(description="Copy template files based on template category.")
    parser.add_argument(
        "-t", "--template_category",
        choices=["liquibase", "basic", "llogger"],
        required=True,
        help="Specify the template category ('liquibase' or 'basic')."
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite existing files."
    )
    args = parser.parse_args()

    copy_files(args.template_category, args.force)
    print('OraTAPI quick config complete.')


if __name__ == "__main__":
    main()
