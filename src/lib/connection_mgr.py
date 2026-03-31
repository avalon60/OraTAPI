__author__ = "Clive Bostock"
__date__ = "2025-01-27"
__description__ = ("Module for managing database and application connection entries in a configuration file. Two "
                   "variations of file are maintained. One for DSNs and another for URLs. These are auto-created (if "
                   "required) and maintained based on the credential_type initialisation parameter.")
import configparser
from pathlib import Path
import getpass
from lib.user_security import UserSecurity


class ConnectMgr:
    RESOURCE_WIDTH = 50
    AUX_WIDTH = 60

    def __init__(self, project_identifier:str, credential_type: str):
        """
        Initialize the ConnectMgr object.
        :project_identifier: Unique string identifying the project. Used to formulate the .<project_identifier> folder name.
        :param config_pathname: Path to the configuration file
        :param credential_type: Type of credential (e.g. 'dsn')
        """
        config_pathname = Path.home() / f".OraTAPI/{credential_type}_credentials.ini"
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

    def list_connections(self, inc_creds: bool = False):
        """List all connections."""
        sections = self.config.sections()
        if sections:
            print("Database connections:")
            name = 'Name'
            if inc_creds:
                print(f"Pos {name:<20}  {'DSN/TNS':<{self.RESOURCE_WIDTH}}  Credentials")
                under20 = "=" * 20
                under60 = "=" * self.RESOURCE_WIDTH
                under_creds = "=" * 35
                print(f"=== {under20:<20}  {under60:<{self.RESOURCE_WIDTH}}  {under_creds}")
            elif self.credential_type == 'dsn':
                print(f"Pos {name:<20}  {'DSN/TNS':<{self.RESOURCE_WIDTH}}  Wallet Pathname")
                under20 = "=" * 20
                under60 = "=" * self.RESOURCE_WIDTH
                under_wallet = "=" * self.AUX_WIDTH
                print(f"=== {under20:<20}  {under60:<{self.RESOURCE_WIDTH}}  {under_wallet}")
            else:
                print(f"Pos {name:<20}  DSN")
                under20 = "=" * 20
                under60 = "=" * 60
                print(f"=== {under20:<20}  {under60:<20}")
            for id, section in enumerate(sections, start=1):
                dsn = self.config[section].get('resource_id', self.config[section].get('dsn', 'No DSN provided'))
                if inc_creds:
                    try:
                        username = self.user_security.user_credential(connection_name=section, credential_key="username")
                    except Exception:
                        username = "<unreadable>"
                    try:
                        password = self.user_security.user_credential(connection_name=section, credential_key="password")
                    except Exception:
                        password = "<unreadable>"
                    print(f"  {id} {section:<20}  {dsn:<50}  [{username} / {password}]")
                elif self.credential_type == 'dsn':
                    wallet_zip_path = self.config[section].get('wallet_zip_path', 'No wallet')
                    print(f"  {id} {section:<20}  {dsn:<50}  {wallet_zip_path}")
                else:
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
        stored_dsn = self.config[name].get('resource_id', self.config[name].get('dsn', dsn))
        dsn = input(f"Enter DSN [{stored_dsn}]: ") or dsn
        wallet_zip_path = ""
        if self.credential_type == 'dsn':
            existing_wallet = self.config[name].get('wallet_zip_path', '')
            while True:
                raw_wallet_path = input(
                    f"Enter wallet ZIP path [{existing_wallet}] (leave blank to keep current): ").strip()
                if not raw_wallet_path:
                    wallet_zip_path = existing_wallet
                    break
                validated = self._validate_wallet_path(raw_wallet_path)
                if validated:
                    wallet_zip_path = validated
                    break
                print("Please enter a valid ZIP file path or press Enter to retain existing value.")

        confirm = input(f"Save changes to connection '{name}'? (y/n): ").lower()
        if confirm == 'y':
            self.user_security.update_named_connection(connection_name=name, username=username, password=password,
                                                       dsn=dsn, wallet_zip_path=wallet_zip_path)
            self.config.read(self.config_pathname)
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
        wallet_zip_path = ""
        if self.credential_type == 'dsn':
            while True:
                raw_wallet_path = input("Enter path to wallet ZIP file (optional, leave blank to skip): ").strip()
                if not raw_wallet_path:
                    break
                validated = self._validate_wallet_path(raw_wallet_path)
                if validated:
                    wallet_zip_path = validated
                    break
                print("Please enter a valid ZIP file path or press Enter to skip.")

        confirm = input(f"Save connection '{name}'? (y/n): ").lower()
        if confirm == 'y':
            self.config.add_section(name)
            self.user_security.update_named_connection(connection_name=name, username=username, password=password,
                                                       dsn=dsn, wallet_zip_path=wallet_zip_path)
            self.config.read(self.config_pathname)
            print(f"Connection '{name}' created.")
        else:
            print("Creation cancelled.")

    def _save_config(self):
        """Save the configuration to the file."""
        with self.config_pathname.open('w') as config_file:
            self.config.write(config_file)

    @staticmethod
    def _validate_wallet_path(path_str: str) -> str:
        """Validate that the given wallet path exists and is a ZIP file."""
        wallet_path = Path(path_str).expanduser().resolve()
        if not wallet_path.exists():
            print(f"Wallet path '{wallet_path}' does not exist.")
            return ""
        if wallet_path.suffix.lower() != ".zip":
            print(f"Wallet path '{wallet_path}' is not a ZIP file.")
            return ""
        return str(wallet_path)
