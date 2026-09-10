__author__ = "Clive Bostock"
__date__ = "2025-01-27"
__description__ = ("Module for managing database and application connection entries in a configuration file. Two "
                   "variations of file are maintained. One for DSNs and another for URLs. These are auto-created (if "
                   "required) and maintained based on the credential_type initialisation parameter.")
import configparser
from pathlib import Path
import getpass
import os
import zipfile
from oratapi.lib.user_security import (
    DEFAULT_OCI_TOKEN_LOCATION,
    OCI_IAM_TOKEN_AUTHENTICATION,
    PASSWORD_AUTHENTICATION,
    SUPPORTED_AUTHENTICATION_TYPES,
    UserSecurity,
)


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
            auth_heading = "Authentication"
            if inc_creds:
                print(
                    f"Pos {name:<20}  {auth_heading:<14}  "
                    f"{'DSN/TNS':<{self.RESOURCE_WIDTH}}  Credentials"
                )
                under20 = "=" * 20
                under_auth = "=" * 14
                under60 = "=" * self.RESOURCE_WIDTH
                under_creds = "=" * 35
                print(
                    f"=== {under20:<20}  {under_auth:<14}  "
                    f"{under60:<{self.RESOURCE_WIDTH}}  {under_creds}"
                )
            elif self.credential_type == 'dsn':
                print(
                    f"Pos {name:<20}  {auth_heading:<14}  "
                    f"{'DSN/TNS':<{self.RESOURCE_WIDTH}}  Wallet Path"
                )
                under20 = "=" * 20
                under_auth = "=" * 14
                under60 = "=" * self.RESOURCE_WIDTH
                under_wallet = "=" * self.AUX_WIDTH
                print(
                    f"=== {under20:<20}  {under_auth:<14}  "
                    f"{under60:<{self.RESOURCE_WIDTH}}  {under_wallet}"
                )
            else:
                print(f"Pos {name:<20}  {auth_heading:<14}  DSN")
                under20 = "=" * 20
                under_auth = "=" * 14
                under60 = "=" * 60
                print(f"=== {under20:<20}  {under_auth:<14}  {under60:<20}")
            for position, section in enumerate(sections, start=1):
                dsn = self.config[section].get('resource_id', self.config[section].get('dsn', 'No DSN provided'))
                authentication_type = self.config[section].get(
                    'authentication_type',
                    PASSWORD_AUTHENTICATION,
                )
                if inc_creds:
                    if authentication_type == OCI_IAM_TOKEN_AUTHENTICATION:
                        wallet_password_status = (
                            "saved" if self.config[section].get("wallet_password", "") else "not saved"
                        )
                        credentials = f"[OCI IAM token; wallet password {wallet_password_status}]"
                    else:
                        try:
                            username = self.user_security.user_credential(
                                connection_name=section,
                                credential_key="username",
                            )
                        except Exception:
                            username = "<unreadable>"
                        try:
                            password = self.user_security.user_credential(
                                connection_name=section,
                                credential_key="password",
                            )
                        except Exception:
                            password = "<unreadable>"
                        credentials = f"[{username} / {password}]"
                    print(
                        f"  {position} {section:<20}  {authentication_type:<14}  "
                        f"{dsn:<50}  {credentials}"
                    )
                elif self.credential_type == 'dsn':
                    wallet_path = self.config[section].get(
                        'wallet_path',
                        self.config[section].get('wallet_zip_path', 'No wallet'),
                    )
                    if authentication_type == OCI_IAM_TOKEN_AUTHENTICATION:
                        wallet_password_status = (
                            "saved" if self.config[section].get("wallet_password", "") else "not saved"
                        )
                        wallet_path = f"{wallet_path} [wallet password {wallet_password_status}]"
                    print(
                        f"  {position} {section:<20}  {authentication_type:<14}  "
                        f"{dsn:<50}  {wallet_path}"
                    )
                else:
                    print(f"  {position} {section:<20}  {authentication_type:<14}  {dsn}")
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

    def edit_connection(self, name: str, authentication_type: str | None = None):
        """Edit an existing connection."""
        if not self.config.has_section(name):
            print(f"Connection '{name}' does not exist.")
            return

        connection = self.user_security.named_connection(connection_name=name)
        authentication_type = authentication_type or connection.authentication_type
        if not self._authentication_type_is_valid(authentication_type):
            return
        if self.credential_type != "dsn" and authentication_type == OCI_IAM_TOKEN_AUTHENTICATION:
            print("OCI IAM token authentication is only supported for DSN connections.")
            return

        print(f"Editing connection '{name}'...")
        username = None
        password = None
        if authentication_type == PASSWORD_AUTHENTICATION:
            existing_username = connection.username or ""
            username = input(f"Enter username [{existing_username}]: ") or existing_username
            if connection.authentication_type == PASSWORD_AUTHENTICATION:
                password = getpass.getpass("Enter new password (leave blank to keep current): ") \
                    or connection.password
            else:
                password = self._prompt_confirmed_secret(
                    prompt="Enter password: ",
                    confirmation_prompt="Re-enter password: ",
                )

        dsn = input(f"Enter DSN [{connection.dsn}]: ") or connection.dsn
        wallet_path = ""
        wallet_password = ""
        if self.credential_type == 'dsn':
            wallet_path = self._prompt_wallet_path(
                existing_wallet=connection.wallet_path,
                required=authentication_type == OCI_IAM_TOKEN_AUTHENTICATION,
            )
            if wallet_path:
                wallet_password = self._prompt_wallet_password(connection.wallet_password)

        token_location = ""
        if authentication_type == OCI_IAM_TOKEN_AUTHENTICATION:
            existing_token_location = connection.token_location or str(DEFAULT_OCI_TOKEN_LOCATION)
            raw_token_location = input(
                f"Enter OCI IAM token directory [{existing_token_location}]: "
            ).strip()
            token_location = self._normalise_path(raw_token_location or existing_token_location)

        confirm = input(f"Save changes to connection '{name}'? (y/n): ").lower()
        if confirm == 'y':
            self.user_security.update_named_connection(
                connection_name=name,
                username=username,
                password=password,
                dsn=dsn,
                authentication_type=authentication_type,
                wallet_path=wallet_path,
                wallet_password=wallet_password,
                token_location=token_location,
            )
            self._reload_config()
            print(f"Connection '{name}' updated.")
        else:
            print("Edit cancelled.")

    def create_connection(self, name: str, authentication_type: str = PASSWORD_AUTHENTICATION):
        """Create a new connection."""
        if self.config.has_section(name):
            print(f"Connection '{name}' already exists.")
            return
        if not self._authentication_type_is_valid(authentication_type):
            return
        if self.credential_type != "dsn" and authentication_type == OCI_IAM_TOKEN_AUTHENTICATION:
            print("OCI IAM token authentication is only supported for DSN connections.")
            return

        print(f"Creating connection '{name}'...")
        username = None
        password = None
        if authentication_type == PASSWORD_AUTHENTICATION:
            username = input("Enter username: ")
            password = self._prompt_confirmed_secret(
                prompt="Enter password: ",
                confirmation_prompt="Re-enter password: ",
            )
        dsn = input("Enter DSN: ")
        wallet_path = ""
        wallet_password = ""
        if self.credential_type == 'dsn':
            wallet_path = self._prompt_wallet_path(
                required=authentication_type == OCI_IAM_TOKEN_AUTHENTICATION,
            )
            if wallet_path:
                wallet_password = self._prompt_wallet_password()

        token_location = ""
        if authentication_type == OCI_IAM_TOKEN_AUTHENTICATION:
            raw_token_location = input(
                f"Enter OCI IAM token directory [{DEFAULT_OCI_TOKEN_LOCATION}]: "
            ).strip()
            token_location = self._normalise_path(raw_token_location or str(DEFAULT_OCI_TOKEN_LOCATION))

        confirm = input(f"Save connection '{name}'? (y/n): ").lower()
        if confirm == 'y':
            self.user_security.update_named_connection(
                connection_name=name,
                username=username,
                password=password,
                dsn=dsn,
                authentication_type=authentication_type,
                wallet_path=wallet_path,
                wallet_password=wallet_password,
                token_location=token_location,
            )
            self._reload_config()
            print(f"Connection '{name}' created.")
        else:
            print("Creation cancelled.")

    def _save_config(self):
        """Save the configuration to the file."""
        with self.config_pathname.open('w') as config_file:
            self.config.write(config_file)

    def _reload_config(self) -> None:
        """Reload the configuration without retaining options removed on disk."""
        self.config = configparser.ConfigParser()
        self.config.read(self.config_pathname)

    @staticmethod
    def _authentication_type_is_valid(authentication_type: str) -> bool:
        if authentication_type in SUPPORTED_AUTHENTICATION_TYPES:
            return True
        supported = ", ".join(SUPPORTED_AUTHENTICATION_TYPES)
        print(f"Unsupported authentication type '{authentication_type}'. Expected one of: {supported}.")
        return False

    @staticmethod
    def _prompt_confirmed_secret(prompt: str, confirmation_prompt: str) -> str:
        while True:
            secret = getpass.getpass(prompt)
            confirmed_secret = getpass.getpass(confirmation_prompt)
            if secret == confirmed_secret:
                return secret
            print("Passwords do not match. Please try again.")

    @classmethod
    def _prompt_wallet_path(cls, existing_wallet: str = "", required: bool = False) -> str:
        while True:
            if existing_wallet:
                prompt = f"Enter wallet ZIP or directory [{existing_wallet}] (leave blank to keep current): "
            elif required:
                prompt = "Enter wallet ZIP or directory: "
            else:
                prompt = "Enter wallet ZIP or directory (optional, leave blank to skip): "

            raw_wallet_path = input(prompt).strip()
            if not raw_wallet_path:
                if existing_wallet:
                    return existing_wallet
                if not required:
                    return ""
                print("A wallet ZIP or directory is required for OCI IAM token authentication.")
                continue

            validated = cls._validate_wallet_path(raw_wallet_path)
            if validated:
                return validated
            print("Please enter a valid Oracle wallet ZIP or directory.")

    @staticmethod
    def _prompt_wallet_password(existing_wallet_password: str = "") -> str:
        if existing_wallet_password:
            return getpass.getpass(
                "Enter new wallet password (leave blank to keep current): "
            ) or existing_wallet_password

        while True:
            wallet_password = getpass.getpass(
                "Enter wallet password (optional; required for encrypted PEM wallets in thin mode): "
            )
            if not wallet_password:
                return ""
            if getpass.getpass("Re-enter wallet password: ") == wallet_password:
                return wallet_password
            print("Passwords do not match. Please try again.")

    @staticmethod
    def _normalise_path(path_str: str) -> str:
        expanded_path = os.path.expandvars(path_str.strip())
        return str(Path(expanded_path).expanduser().resolve(strict=False))

    @staticmethod
    def _validate_wallet_path(path_str: str) -> str:
        """Validate an Oracle wallet ZIP or extracted wallet directory.

        If the supplied value is not an existing path, try resolving it relative
        to TNS_ADMIN before rejecting it.
        """
        expanded_path = os.path.expandvars(path_str.strip())
        candidate = Path(expanded_path).expanduser()
        wallet_path = candidate.resolve() if candidate.exists() else None

        if wallet_path is None:
            tns_admin = os.environ.get("TNS_ADMIN", "").strip()
            if tns_admin:
                tns_wallet = (Path(tns_admin).expanduser() / path_str).resolve()
                if tns_wallet.exists():
                    wallet_path = tns_wallet

        if wallet_path is None:
            wallet_path = candidate.resolve()
        if not wallet_path.exists():
            print(f"Wallet path '{wallet_path}' does not exist.")
            return ""

        if wallet_path.is_dir():
            wallet_files = {item.name.lower() for item in wallet_path.iterdir() if item.is_file()}
        elif wallet_path.is_file() and wallet_path.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(wallet_path) as wallet_zip:
                    wallet_files = {
                        Path(member).name.lower()
                        for member in wallet_zip.namelist()
                        if not member.endswith("/")
                    }
            except zipfile.BadZipFile:
                print(f"Wallet path '{wallet_path}' is not a valid ZIP file.")
                return ""
        else:
            print(f"Wallet path '{wallet_path}' is neither a directory nor a ZIP file.")
            return ""

        if "tnsnames.ora" not in wallet_files:
            print(f"Wallet path '{wallet_path}' does not contain tnsnames.ora.")
            return ""
        if not {"ewallet.pem", "cwallet.sso"}.intersection(wallet_files):
            print(
                f"Wallet path '{wallet_path}' contains neither ewallet.pem for thin mode "
                "nor cwallet.sso for thick mode."
            )
            return ""
        return str(wallet_path)
