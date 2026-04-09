#!/usr/bin/env python3
"""
Author: Clive Bostock
Date: 2026-04-04
Description: Compatibility wrapper redirecting migration/export/import operations to profile_mgr.
"""
__author__ = "Clive Bostock"
__date__ = "2026-04-04"
__description__ = "Compatibility wrapper redirecting migration/export/import operations to profile_mgr."

from oratapi import __version__

import argparse
from pathlib import Path

PROG_NAME = Path(__file__).name


def main() -> None:
    print(f"{PROG_NAME}: OraTAPI migration/export/import utility version: {__version__}")
    parser = argparse.ArgumentParser(
        description="Deprecated compatibility wrapper. Use profile_mgr for profile export/import and legacy migration."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-o", "--old_install_dir", help="Specify the old OraTAPI installation directory.")
    group.add_argument("-e", "--export", metavar="<export_zip_path>", help="Export resources to a ZIP file.")
    group.add_argument("-i", "--import_resources", metavar="<import_zip_path>", help="Import resources from a ZIP file.")
    args = parser.parse_args()

    print("ERROR: migrate_config is deprecated.")
    if args.old_install_dir:
        print("Use profile_mgr instead:")
        print(f"  profile_mgr --migrate-old {args.old_install_dir} <target-profile>")
    elif args.export:
        print("Use profile_mgr instead:")
        print(f"  profile_mgr --export <profile-name> {args.export}")
    elif args.import_resources:
        print("Use profile_mgr instead:")
        print(f"  profile_mgr --import-profile {args.import_resources}")
    print("\nWrapper scripts under bin/ remain available for source checkouts and extracted legacy installs.")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
