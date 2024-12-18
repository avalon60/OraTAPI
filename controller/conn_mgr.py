__author__ = "Clive Bostock"
__date__ = "2024-12-10"
__description__ = "Command-line tool for managing database connection entries in a configuration file."

import argparse
import configparser
from pathlib import Path
import getpass
from model.user_security import UserSecurity

CONFIG_PATH = Path.home() / ".OraTAPI/dsn_credentials.ini"

user_security = UserSecurity(project_identifier="OraTAPI")

def ensure_config_file():
    """
    Ensure the configuration file exists.
    """
    if not CONFIG_PATH.parent.exists():
        CONFIG_PATH.parent.mkdir(parents=True)

    if not CONFIG_PATH.exists():
        CONFIG_PATH.touch()
        print(f"Created configuration file at {CONFIG_PATH}")


def list_connections(config):
    """
    List all connection names and their DSNs in the config file.

    :param config: ConfigParser object
    """
    sections = config.sections()
    if sections:
        print("Database connections:")
        name = 'Name'
        print(f"Pos {name:<20}  DSN")
        under20 = "=" * 20
        under60 = "=" * 60
        print(f"=== {under20:<20}  {under60:<20}")
        for id, section in enumerate(sections, start=1):
            dsn = config[section].get('dsn', 'No DSN provided')
            print(f"  {id} {section:<20}  {dsn}")
    else:
        print("No database connections found.")


def delete_connection(config, name):
    """
    Delete a connection from the config file after confirmation.

    :param config: ConfigParser object
    :param name: Name of the connection to delete
    """
    if config.has_section(name):
        confirm = input(f"Are you sure you want to delete the connection '{name}'? (y/n): ").lower()
        if confirm == 'y':
            config.remove_section(name)
            save_config(config)
            print(f"Connection '{name}' deleted.")
        else:
            print("Deletion cancelled.")
    else:
        print(f"Connection '{name}' does not exist.")


def edit_connection(config, name):
    """
    Edit an existing connection interactively.

    :param config: ConfigParser object
    :param name: Name of the connection to edit
    """
    if not config.has_section(name):
        print(f"Connection '{name}' does not exist.")
        return

    db_username, db_password, dsn \
        = user_security.named_connection_creds(connection_name=name)

    print(f"Editing connection '{name}'...")
    username = input(f"Enter username [{db_username}]: ") or db_username
    password = getpass.getpass("Enter new password (leave blank to keep current): ") or db_password
    dsn = input(f"Enter DSN [{config[name]['dsn']}]: ") or dsn

    confirm = input(f"Save changes to connection '{name}'? (y/n): ").lower()
    if confirm == 'y':
        user_security.update_named_connection(connection_name=name, username=username, password=password, dsn=dsn)
        print(f"Connection '{name}' updated.")
    else:
        print("Edit cancelled.")


def create_connection(config, name):
    """
    Create a new connection interactively.

    :param config: ConfigParser object
    :param name: Name of the new connection
    """
    if config.has_section(name):
        print(f"Connection '{name}' already exists.")
        return

    print(f"Creating connection '{name}'...")
    username = input("Enter username: ")
    while True:
        password = getpass.getpass("Enter password: ")
        confirm_password = getpass.getpass("Re-enter password: ")
        if password == confirm_password:
            break
        print("Passwords do not match. Please try again.")
    dsn = input("Enter DSN: ")

    confirm = input(f"Save connection '{name}'? (y/n): ").lower()
    if confirm == 'y':
        config.add_section(name)
        user_security.update_named_connection(connection_name=name, username=username, password=password, dsn=dsn)
        print(f"Connection '{name}' created.")
    else:
        print("Creation cancelled.")


def save_config(config):
    """
    Save the configuration file.

    :param config: ConfigParser object
    """
    with CONFIG_PATH.open('w') as configfile:
        config.write(configfile)


def main():
    ensure_config_file()

    parser = argparse.ArgumentParser(description="Database connection manager.",
                                     epilog="Used to create/edit/delete or store named database connections."
                                            "Database connections are stored, encrypted, in a local store.")


    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-c', '--create', action='store_true', help="Create a new connection.")
    group.add_argument('-e', '--edit', action='store_true', help="Edit an existing connection.")
    group.add_argument('-d', '--delete', action='store_true', help="Delete an existing connection.")
    group.add_argument('-l', '--list', action='store_true', help="List all connections.")

    parser.add_argument('-n', '--name', type=str, help="Name of the connection.")

    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)

    if args.list:
        list_connections(config)
    elif args.create:
        if not args.name:
            print("The --name option is required for creating a connection.")
        else:
            create_connection(config, args.name)
    elif args.edit:
        if not args.name:
            print("The --name option is required for editing a connection.")
        else:
            edit_connection(config, args.name)
    elif args.delete:
        if not args.name:
            print("The --name option is required for deleting a connection.")
        else:
            delete_connection(config, args.name)


if __name__ == "__main__":
    main()
