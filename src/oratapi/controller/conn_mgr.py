__author__ = "Clive Bostock"
__date__ = "2024-12-10"
__description__ = "Module for managing database connection and application entries in a configuration file."

from oratapi import __version__
import argparse
from pathlib import Path
from oratapi.lib.connection_mgr import ConnectMgr
from oratapi.lib.user_security import (
    PASSWORD_AUTHENTICATION,
    SUPPORTED_AUTHENTICATION_TYPES,
)
PROG_NAME = Path(__file__).name



def main():
    print(f"{PROG_NAME}: OraTAPI connection manager utility version: {__version__}")
    parser = argparse.ArgumentParser(
        description="Database connection manager.",
        epilog="Used to create/edit/delete or store named database connections. "
               "Database connections are stored, encrypted, in a local store.")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-c', '--create', action='store_true', help="Create a new connection.")
    group.add_argument('-e', '--edit', action='store_true', help="Edit an existing connection.")
    group.add_argument('-d', '--delete', action='store_true', help="Delete an existing connection.")
    group.add_argument('-l', '--list', action='store_true', help="List all connections.")

    parser.add_argument(
        '-C',
        '--print-creds',
        action='store_true',
        help="If used with --list, includes decrypted password credentials; IAM secrets are never displayed.",
    )
    parser.add_argument('-n', '--name', type=str, help="Name of the connection.")
    parser.add_argument('-t', '--credential-type', type=str, choices=['dsn', 'url'], default='dsn',
                        help="Type of credential to use (default: dsn).")
    parser.add_argument(
        '--auth-type',
        choices=SUPPORTED_AUTHENTICATION_TYPES,
        help=(
            "Authentication type. New connections default to password; existing connections retain their stored "
            "type unless this option is supplied."
        ),
    )

    args = parser.parse_args()


    conn_mgr = ConnectMgr(project_identifier='OraTAPI', credential_type=args.credential_type)

    if args.list:
        conn_mgr.list_connections(inc_creds=args.print_creds)
    elif args.print_creds:
        print("Error: --print-creds must be used with --list.")
    elif args.create:
        if not args.name:
            print("The --name option is required for creating a connection.")
        else:
            conn_mgr.create_connection(args.name, authentication_type=args.auth_type or PASSWORD_AUTHENTICATION)
    elif args.edit:
        if not args.name:
            print("The --name option is required for editing a connection.")
        else:
            conn_mgr.edit_connection(args.name, authentication_type=args.auth_type)
    elif args.delete:
        if not args.name:
            print("The --name option is required for deleting a connection.")
        else:
            conn_mgr.delete_connection(args.name)


if __name__ == "__main__":
    main()
