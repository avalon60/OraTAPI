#!/usr/bin/env python3
"""
Author: Clive Bostock
Date: 2024-12-31
Description: Bootstrap utility to initialise config and template files from resources/templates.
"""
__author__ = "Clive Bostock"
__date__ = "2024-12-31"
__description__ = "Configuration bootstrap utility for OraTAPI"
from controller import __version__

import argparse
import shutil

from lib.fsutils import profile_home, resolve_default_path, runtime_home, write_active_profile
from pathlib import Path
from itertools import chain
from lib.config_mgr import compare_config_files

BUILTIN_PROFILES = ("basic", "liquibase", "logger", "llogger")
PROG_NAME = Path(__file__).name


def _profile_resources_home(profile_name: str) -> Path:
    return profile_home(profile_name) / "resources"


def copy_files(profile_name: str, template_category: str, force: bool, templates_only: bool=False) -> None:
    """
    Copies `.sample` files from a `samples` subdirectory to target locations, based on the
    template_category, and specific copying rules. Ensures OraTAPI.ini version consistency.

    :param profile_name: The profile to instantiate.
    :param template_category: The template category ("basic", "liquibase", "logger" or "llogger").
    :type template_category: str
    :param force: Whether to overwrite existing files.
    :type force: bool
    :param templates_only: Only instantiate the sample templates.
    """
    files_copied = 0
    resources_home = _profile_resources_home(profile_name)
    config_dir = resources_home / 'config'
    templates_dir = resources_home / 'templates'
    config_dir.mkdir(parents=True, exist_ok=True)
    templates_dir.mkdir(parents=True, exist_ok=True)

    # Handle the config directory
    config_sample = resolve_default_path(Path("resources") / "config" / "samples" / "OraTAPI.ini.sample")
    config_target = config_dir / "OraTAPI.ini"

    if config_sample.exists() and (force or not config_target.exists()) and not templates_only:
        shutil.copyfile(config_sample, config_target)
        files_copied += 1
        print(f"[{profile_name}] Copied: {config_sample} -> {config_target.relative_to(runtime_home())}")

    csv_sample = resolve_default_path(Path("resources") / "config" / "samples" / "pi_columns.csv.sample")
    csv_target = config_dir / "pi_columns.csv"
    if csv_sample.exists() and ((force and not templates_only) or not csv_target.exists()):
        shutil.copyfile(csv_sample, csv_target)
        files_copied += 1
        print(f"[{profile_name}] Copied: {csv_sample} -> {csv_target.relative_to(runtime_home())}")

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
        templates_dir / "ut_packages" / "body",
        templates_dir / "ut_packages" / "spec"
    ]

    # Handle special directories
    for special_dir in special_dirs:
        relative_special_dir = special_dir.relative_to(templates_dir)
        samples_dir = resolve_default_path(Path("resources") / "templates" / relative_special_dir / "samples")
        if samples_dir.exists():
            special_dir.mkdir(parents=True, exist_ok=True)
            for sample_file in samples_dir.glob("*.sample"):
                target_file = special_dir / sample_file.stem
                if force or not target_file.with_suffix(".tpt").exists():
                    shutil.copyfile(sample_file, target_file.with_suffix(".tpt"))
                    files_copied += 1
                    print(f"[{profile_name}] Copied: {sample_file} -> {target_file.with_suffix('.tpt').relative_to(runtime_home())}")

    # Handle regular directories
    for regular_dir in regular_dirs:
        relative_regular_dir = regular_dir.relative_to(templates_dir)
        samples_dir = resolve_default_path(Path("resources") / "templates" / relative_regular_dir / "samples")
        if samples_dir.exists():
            regular_dir.mkdir(parents=True, exist_ok=True)
            for sample_file in chain(samples_dir.glob(f"*.{template_category}.sample"),
                                     samples_dir.glob("*.common.sample")):
                target_file = regular_dir / sample_file.stem
                if force or not target_file.with_suffix(".tpt").exists():
                    shutil.copyfile(sample_file, target_file.with_suffix(".tpt"))
                    files_copied += 1
                    print(f"[{profile_name}] Copied: {sample_file} -> {target_file.with_suffix('.tpt').relative_to(runtime_home())}")
    print(f"[{profile_name}] {files_copied} files instantiated.")
    if config_target.exists():
        compare_config_files(config_file_path=config_target, config_sample_file=config_sample)


def bootstrap_builtin_profiles(selected_profile: str, force: bool, templates_only: bool = False) -> None:
    for profile_name in BUILTIN_PROFILES:
        copy_files(profile_name=profile_name,
                   template_category=profile_name,
                   force=force,
                   templates_only=templates_only)
    write_active_profile(selected_profile)
    print(f"Active profile set to: {selected_profile}")


def main() -> None:
    """
    Main function to parse arguments and initiate file copying.
    """
    parser = argparse.ArgumentParser(
        description="Initialise OraTAPI profiles under ~/OraTAPI/configs and activate the selected built-in profile.",
        epilog=(
            "Template categories:\n"
            "  basic     - No Liquibase directives or logging\n"
            "  liquibase - Generated code includes Liquibase directives\n"
            "  logger    - Generated PL/SQL includes logger logging calls for parameter values and related diagnostics\n"
            "  llogger   - Includes both Liquibase directives and logger logging\n\n"
            "This command instantiates the control files OraTAPI.ini and pi_columns.csv for profiles basic,\n"
            "liquibase, logger, and llogger, then points ~/OraTAPI/active_config at the selected profile.\n"
            "For template categories logger and llogger, the logger utility must already be deployed to the database."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-t", "--template_category",
        choices=["liquibase", "basic", "logger", "llogger"],
        required=True,
        help="Built-in profile to activate after bootstrapping all provided profiles."
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

    print(f"{PROG_NAME}: OraTAPI config utility version: {__version__}")
    print('OraTAPI quick config started...')
    bootstrap_builtin_profiles(args.template_category, args.force, templates_only=args.templates_only)
    print('OraTAPI quick config complete.')


if __name__ == "__main__":
    main()
