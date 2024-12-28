#!/usr/bin/env python3
"""
Author: Clive Bostock
Date: 2024-12-27
Description: Script to initialise config and template files from resources/templates.
"""

import argparse
import os
import shutil
from pathlib import Path


def copy_files(template_category: str, force: bool) -> None:
    """
    This copies `.sample` files from the resources directory to
    target locations, based on the template_category, and specific copying rules.
    We initialise by copying only when files do not exist, unless `force` is specified.

    :param template_category: The template category ("liquibase" or "basic").
    :type template_category: str
    :param force: Whether to overwrite existing files.
    :type force: bool
    """
    base_dir = Path("resources")
    config_dir = base_dir / "config"
    templates_dir = base_dir / "templates"

    # Handle the config directory
    config_sample = config_dir / "OraTAPI.ini.sample"
    config_target = config_dir / "OraTAPI.ini"
    if config_sample.exists() and (force or not config_target.exists()):
        shutil.copyfile(config_sample, config_target)
        print(f"Copied: {config_sample} -> {config_target}")

    # Directories with special rules
    special_dirs = [
        templates_dir / "column_expressions" / "inserts",
        templates_dir / "column_expressions" / "updates",
        templates_dir / "packages" / "procedures"
    ]

    for special_dir in special_dirs:
        if special_dir.exists():
            for sample_file in special_dir.glob("*.sample"):
                target_file = special_dir / sample_file.stem
                if force or not target_file.with_suffix(".tpt").exists():
                    shutil.copyfile(sample_file, target_file.with_suffix(".tpt"))
                    print(f"Copied: {sample_file} -> {target_file.with_suffix('.tpt')}")

    # Handle the other directories
    for root, _, files in os.walk(templates_dir):
        root_path = Path(root)
        # Skip special directories
        if any(root_path == special_dir for special_dir in special_dirs):
            continue

        for file in files:
            if file.endswith(f"{template_category}.sample"):
                sample_file = root_path / file
                target_file = root_path / (file.replace(f".{template_category}.sample", ".tpt"))
                if force or not target_file.exists():
                    shutil.copyfile(sample_file, target_file)
                    print(f"Copied: {sample_file} -> {target_file}")


def main() -> None:
    """
    Main function to parse arguments and initiate file copying.
    """
    parser = argparse.ArgumentParser(description="Copy template files based on template category.")
    parser.add_argument(
        "-t", "--template_category",
        choices=["liquibase", "basic"],
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


if __name__ == "__main__":
    main()
