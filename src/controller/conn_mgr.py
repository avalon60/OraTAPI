__author__ = "Clive Bostock"
__date__ = "2024-12-10"
__description__ = "Command-line tool for managing database connection entries in a configuration file."

from controller.ora_tapi import __version__
import argparse
import configparser
from pathlib import Path
import getpass
from model.user_security import UserSecurity
from lib.connecttion_mgr import ConnectMgr
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

    parser.add_argument('-n', '--name', type=str, help="Name of the connection.")
    parser.add_argument('-t', '--credential-type', type=str, choices=['dsn', 'url'], default='dsn',
                        help="Type of credential to use (default: dsn).")

    args = parser.parse_args()
    config_file = Path.home() / f".OraTAPI/{args.credential_type}_credentials.ini"

    conn_mgr = ConnectMgr(project_identifier='OraTAPI', config_pathname=config_file, credential_type=args.credential_type)

    if args.list:
        conn_mgr.list_connections()
    elif args.create:
        if not args.name:
            print("The --name option is required for creating a connection.")
        else:
            conn_mgr.create_connection(args.name)
    elif args.edit:
        if not args.name:
            print("The --name option is required for editing a connection.")
        else:
            conn_mgr.edit_connection(args.name)
    elif args.delete:
        if not args.name:
            print("The --name option is required for deleting a connection.")
        else:
            conn_mgr.delete_connection(args.name)


if __name__ == "__main__":
    main()
