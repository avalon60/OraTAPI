__author__ = "Clive Bostock"
__date__ = "2026-04-04"
__description__ = "CLI for managing OraTAPI configuration profiles."

from controller import __version__
import argparse
from pathlib import Path

from lib.profile_manager import ProfileManager

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
    group.add_argument("-e", "--export", nargs=2, metavar=("PROFILE", "ZIP_PATH"), help="Export a profile to a ZIP file.")
    group.add_argument("-i", "--import-profile", metavar="ZIP_PATH", help="Import a profile from a ZIP file.")
    group.add_argument("-m", "--migrate-old", nargs=2, metavar=("OLD_INSTALL_DIR", "TARGET_PROFILE"),
                       help="Migrate a legacy install tree into a named profile.")

    args = parser.parse_args()
    profile_manager = ProfileManager()

    try:
        if args.list:
            profile_manager.list_profiles()
        elif args.show_active:
            profile_manager.show_active_profile()
        elif args.create:
            profile_manager.create_profile(args.create)
        elif args.copy:
            profile_manager.copy_profile(args.copy[0], args.copy[1])
        elif args.delete:
            profile_manager.delete_profile(args.delete)
        elif args.activate:
            profile_manager.activate_profile(args.activate)
        elif args.export:
            profile_manager.export_profile(args.export[0], Path(args.export[1]))
        elif args.import_profile:
            profile_manager.import_profile(Path(args.import_profile))
        elif args.migrate_old:
            profile_manager.migrate_old_install(Path(args.migrate_old[0]), args.migrate_old[1])
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
