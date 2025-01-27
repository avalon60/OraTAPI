import configparser
from pathlib import Path
import getpass
from model.user_security import UserSecurity


class ConnectMgr:
    def __init__(self, project_identifier:str, config_pathname: Path, credential_type: str):
        """
        Initialize the ConnectMgr object.
        :project_identifier: Unique string identifying the project. Used to formulate the ~.<project_identifier> folder name.
        :param config_pathname: Path to the configuration file
        :param credential_type: Type of credential (e.g. 'dsn')
        """
        self.config_pathname = config_pathname
        self.credential_type = credential_type
        self.config = configparser.ConfigParser()
        self.user_security = UserSecurity(project_identifier=project_identifier, credential_type=credential_type)
        self._ensure_config_file()
        self.config.read(self.config_pathname)

    def _ensure_config_file(self):
        """Ensure the configuration file exists."""
        if not self.config_pathname.parent.exists():
            self.config_pathname.parent.mkdir(parents=True)
        if not self.config_pathname.exists():
            self.config_pathname.touch()
            print(f"Created configuration file at {self.config_pathname}")

    def list_connections(self):
        """List all connections."""
        sections = self.config.sections()
        if sections:
            print("Database connections:")
            name = 'Name'
            print(f"Pos {name:<20}  DSN")
            under20 = "=" * 20
            under60 = "=" * 60
            print(f"=== {under20:<20}  {under60:<20}")
            for id, section in enumerate(sections, start=1):
                dsn = self.config[section].get('dsn', 'No DSN provided')
                print(f"  {id} {section:<20}  {dsn}")
        else:
            print("No database connections found.")

    def delete_connection(self, connection_name: str):
        """Delete a connection."""
        if self.config.has_section(connection_name):
            confirm = input(f"Are you sure you want to delete the connection '{connection_name}'? (y/n): ").lower()
            if confirm == 'y':
                self.config.remove_section(connection_name)
                self._save_config()
                print(f"Connection '{connection_name}' deleted.")
            else:
                print("Deletion cancelled.")
        else:
            print(f"Connection '{connection_name}' does not exist.")

    def edit_connection(self, name: str):
        """Edit an existing connection."""
        if not self.config.has_section(name):
            print(f"Connection '{name}' does not exist.")
            return

        db_username, db_password, dsn = self.user_security.named_connection_creds(connection_name=name)

        print(f"Editing connection '{name}'...")
        username = input(f"Enter username [{db_username}]: ") or db_username
        password = getpass.getpass("Enter new password (leave blank to keep current): ") or db_password
        dsn = input(f"Enter DSN [{self.config[name]['dsn']}]: ") or dsn

        confirm = input(f"Save changes to connection '{name}'? (y/n): ").lower()
        if confirm == 'y':
            self.user_security.update_named_connection(connection_name=name, username=username, password=password, dsn=dsn)
            print(f"Connection '{name}' updated.")
        else:
            print("Edit cancelled.")

    def create_connection(self, name: str):
        """Create a new connection."""
        if self.config.has_section(name):
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
            self.config.add_section(name)
            self.user_security.update_named_connection(connection_name=name, username=username, password=password, dsn=dsn)
            print(f"Connection '{name}' created.")
        else:
            print("Creation cancelled.")

    def _save_config(self):
        """Save the configuration to the file."""
        with self.config_pathname.open('w') as config_file:
            self.config.write(config_file)
