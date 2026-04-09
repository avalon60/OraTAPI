__author__ = "Clive Bostock"
__date__ = "2026-04-04"
__description__ = "CLI for managing OraTAPI configuration profiles."

from oratapi import __version__
import argparse
from pathlib import Path

from oratapi.lib.profile_manager import ProfileManager

PROG_NAME = Path(__file__).name


def main():
    print(f"{PROG_NAME}: OraTAPI profile manager utility version: {__version__}")

    parser = argparse.ArgumentParser(
        description="Manage OraTAPI configuration profiles stored under ~/OraTAPI/configs."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-l", "--list", action="store_true", help="List available profiles.")
    group.add_argument("-s", "--show-active", action="store_true", help="Show the active profile.")
    group.add_argument("-c", "--create", metavar="PROFILE", help="Create a new profile by cloning the active profile.")
    group.add_argument("-C", "--copy", nargs=2, metavar=("SOURCE", "TARGET"), help="Copy an existing profile.")
    group.add_argument("-d", "--delete", metavar="PROFILE", help="Delete a profile.")
    group.add_argument("-a", "--activate", metavar="PROFILE", help="Activate a profile.")
    group.add_argument("-P", "--set-purpose", nargs=2, metavar=("PROFILE", "PURPOSE"),
                       help="Set or replace the one-line purpose text for a profile.")
    group.add_argument("-e", "--export", nargs=2, metavar=("PROFILE", "ZIP_PATH"), help="Export a profile to a ZIP file.")
    group.add_argument("-i", "--import-profile", metavar="ZIP_PATH", help="Import a profile from a ZIP file.")
    group.add_argument("-m", "--migrate-old", nargs=2, metavar=("OLD_INSTALL_DIR", "TARGET_PROFILE"),
                       help="Migrate a legacy install tree into a named profile.")
    parser.add_argument(
        "-p", "--purpose",
        metavar="PURPOSE_TEXT",
        help="Purpose text to store with a newly created, copied, imported, or migrated profile."
    )

    args = parser.parse_args()
    profile_manager = ProfileManager(current_version=__version__)

    if args.purpose and not (args.create or args.copy or args.import_profile or args.migrate_old):
        parser.error("--purpose can only be used with --create, --copy, --import-profile, or --migrate-old")

    try:
        if args.list:
            profile_manager.list_profiles()
        elif args.show_active:
            profile_manager.show_active_profile()
        elif args.create:
            profile_manager.create_profile(args.create, purpose_text=args.purpose)
        elif args.copy:
            profile_manager.copy_profile(args.copy[0], args.copy[1], purpose_text=args.purpose)
        elif args.delete:
            profile_manager.delete_profile(args.delete)
        elif args.activate:
            profile_manager.activate_profile(args.activate)
        elif args.set_purpose:
            profile_manager.set_profile_purpose(args.set_purpose[0], args.set_purpose[1])
        elif args.export:
            profile_manager.export_profile(args.export[0], Path(args.export[1]))
        elif args.import_profile:
            profile_manager.import_profile(Path(args.import_profile), purpose_text=args.purpose)
        elif args.migrate_old:
            profile_manager.migrate_old_install(
                Path(args.migrate_old[0]),
                args.migrate_old[1],
                purpose_text=args.purpose,
            )
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
