"""
__author__: Clive Bostock
__date__: 2024-05-23
__description__: User/Security module. This is responsible for managing developer specific settings; primarily
                 password encryption/decryption and configuration settings.

                 Passwords are located to the $HOME/<sanitised_project_name>/<typ>_credentials.ini file.

                 Typically, <type> would be dsn."
"""

from base64 import b64encode, b64decode
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from model.framework_errors import UnsupportedPlatform
from lib.file_system_utils import sanitise_dir_name
from pathlib import Path

import configparser
import os
import subprocess
import platform

APP_HOME = os.path.dirname(os.path.realpath(__file__))
APP_HOME = Path(os.path.dirname(APP_HOME))
CONFIG_DIR = APP_HOME / 'config'
OHAI_TEST_INI = CONFIG_DIR / 'config.ini'
REPORTS_DIR = APP_HOME / "reports"
LOGS_DIR = APP_HOME / "logs"
SCREENSHOTS_DIR = APP_HOME / "screenshots"
# Define constant USER_CONFIG_DIR, which names the directory below $HOME, where user config is located.
# The primary use is to locate encrypted secrets.
USER_CONFIG_DIR = '.bdds'
USER_SECRETS_INI = 'secrets.ini'


def _system_id():
    """
    Retrieves a unique system identifier based on the operating system.

    This function detects the operating system and then executes appropriate
    commands to fetch a unique identifier for the system. The method of fetching
    the identifier varies based on whether the system is macOS (Darwin), Windows,
    or Linux. If the operating system is not one of these, a default identifier
    is returned.

    Returns:
        str: A unique system identifier or a default string if the OS is unsupported.
    """
    # Determine the operating system
    operating_system = platform.system()

    if operating_system == 'Darwin':
        # macOS: Use ioreg and awk to fetch the IOPlatformUUID
        command = "ioreg -d2 -c IOPlatformExpertDevice"
        # Run ioreg command to get platform details
        ioreg_cmd = subprocess.run(["ioreg", "-d2", "-c", "IOPlatformExpertDevice"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Run awk command to extract the IOPlatformUUID
        awk_cmd = subprocess.run(["awk", '-F\"', "'/IOPlatformUUID/{print $(NF-1)}'"],
                                 input=ioreg_cmd.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Decode the output to get the system UID
        system_uid = awk_cmd.stdout.decode()

    elif operating_system == 'Windows':
        # Windows: Use wmic to get the UUID
        # Run wmic command to get the system UUID
        wmic_cmd = subprocess.run(["wmic", "path", "win32_computersystemproduct", "get", "UUID"],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Decode and clean up the output to get the system UID
        system_uid = str(wmic_cmd.stdout.decode())
        system_uid = system_uid.replace('UUID ', '').replace('\r', '').replace('\n', '').replace(' ', '')

    elif operating_system == 'Linux':
        # Linux: Read the machine-id file
        # Run cat command to read the /etc/machine-id file
        cat_cmd = subprocess.run(["cat", "/etc/machine-id"],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Decode the output to get the system UID
        system_uid = cat_cmd.stdout.decode()

    else:
        # Unsupported OS: Return a default identifier
        raise UnsupportedPlatform(operating_system)

    return system_uid

class UserSecurity:
    def __init__(self, project_identifier:str, credential_type:str = "dsn"):
        """Initialise a UserSec object.
        :param project_identifier: An alphanumeric string which identifies the project. This is used to create a hidden .<project_identifier>  directory, in the users home directory.
        :param credential_type: Defines the type of credentials we are working with. We store one credential type per config file.
        """

        sanitised_dir_name = sanitise_dir_name(directory_name=project_identifier)
        self.config_file_name = f'{credential_type}_credentials.ini'
        self.config_dir_name = '.' + sanitised_dir_name
        # Here we call get_user_config_file_path to construct our path to the config file.
        # Note that get_user_config_file_path will create the required directory, based on
        # the sanitised project name, under the user's home directory if required.
        self.user_config_file_path = Path(self._get_user_config_file_path())
        self._create_user_credentials_file()

    def named_connection_creds(self, connection_name: str) -> tuple[str, str, str]:
        """
        Returns the decrypted username, decrypted password, and the DSN for a given connection name.

        :param connection_name: The name of the stored database connection.
        :return: A tuple containing decrypted username, decrypted password, and DSN.
        :raises FileNotFoundError: If the credentials configuration file does not exist.
        :raises KeyError: If the connection name does not exist in the credentials configuration file.
        """
        # Check if the configuration file exists
        if not self.user_config_file_path.exists():
            raise FileNotFoundError(f"Configuration file '{self.user_config_file_path}' not found.")

        # Load the configuration file
        config = configparser.ConfigParser()
        config.read(self.user_config_file_path)

        # Get all valid connection names (sections in the config)
        valid_connection_names = config.sections()

        # Check if the connection name exists in the configuration
        if connection_name not in valid_connection_names:
            valid_keys_str = ", ".join(valid_connection_names) if valid_connection_names else "No connection names have been saved."
            raise KeyError(
                f"Connection '{connection_name}' does not exist in the credentials store. "
                f"Valid connection names are: {valid_keys_str}."
            )

        # Retrieve and decrypt the username and password
        encrypted_username = config.get(connection_name, "username")
        encrypted_password = config.get(connection_name, "password")
        dsn = config.get(connection_name, "dsn")

        username = _decrypted_user_credential(encrypted_credential=encrypted_username)
        password = _decrypted_user_credential(encrypted_credential=encrypted_password)

        return username, password, dsn

    def update_named_connection(self, connection_name:str, username: str, password:str, dsn: str):
        """Create (or update, if already exists) a connection entry, fo the supplied connection details.
        :param connection_name: The named connection.This is effectively a section in a config file.
        :param username: The username to encrypt and store.
        :param password: The password to encrypt and store.
        :param dsn: The data source name (TNS string)
        """

        self._create_new_connection_section(connection_name= connection_name)
        encrypted_username = _encrypted_user_credential(credential=username)
        encrypted_password = _encrypted_user_credential(credential=password)
        self._update_credential_entry(connection_name=connection_name, credential_key="username", credential_value=encrypted_username)
        self._update_credential_entry(connection_name=connection_name, credential_key="password", credential_value=encrypted_password)
        self._update_credential_entry(connection_name=connection_name, credential_key="dsn", credential_value=dsn)

    def _create_user_credentials_file(self, new_connection_name: str | None = None) -> None:
        """
        Create a configparser file in the user's .bdds directory.
        If the file already exists, do nothing. If an initial_section is passed, add it to the file.

        :param new_connection_name: Initial connection name to add to the credentials config file.
        """
        if os.path.exists(self.user_config_file_path):
            return

        config = configparser.ConfigParser()
        if new_connection_name:
            config.add_section(new_connection_name)

        with open(str(self.user_config_file_path), 'w', encoding='utf-8') as config_file:
            config.write(config_file)
            config_file.close()


    def _create_new_connection_section(self, connection_name: str) -> None:
        """
        Create a new section in the configparser file if it does not already exist.

        :param config_filename: Name of the config file.
        :param connection_name: Section to add to the config file.
        """
        config = configparser.ConfigParser()

        if not os.path.exists(self.user_config_file_path):
            raise FileNotFoundError(f"The config file {self.user_config_file_path} does not exist.")

        config.read(self.user_config_file_path)
        if not config.has_section(connection_name):
            config.add_section(connection_name)
            with open(self.user_config_file_path, 'w') as config_file:
                config.write(config_file)

    def _get_user_config_file_path(self) -> Path:
        """
        Get the full path of the config file in the directory located in the user's home directory.
        if the config_directory path doesn't exist, then create it.
        """
        home_dir = os.path.expanduser("~")
        config_dir_path = os.path.join(home_dir, self.config_dir_name )
        if not os.path.exists(config_dir_path):
            os.makedirs(config_dir_path)
        return Path(os.path.join(config_dir_path, self.config_file_name))

    def _update_credential_entry(self, connection_name: str, credential_key: str, credential_value: str) -> None:
        """
        Write a key/value pair to the configparser file. If the key already exists, update the value and print a message.

        :param connection_name: Config file section name.
        :param credential_key: Key to add/update in the credentials config file.
        :param credential_value: Value to associate with the key.
        """
        config = configparser.ConfigParser()

        # Read the existing configuration (if the file exists)
        if os.path.exists(self.user_config_file_path):
            config.read(self.user_config_file_path)

        if not os.path.exists(self.user_config_file_path):
            raise FileNotFoundError(f"The config file {self.user_config_file_path} does not exist.")

        if not config.has_section(connection_name):
            config.add_section(connection_name)

        if config.has_option(connection_name, credential_key):
            print(f"Updating existing user config value for: {credential_key}")
        else:
            print(f"Creating user config value for: {credential_key}")

        config.set(connection_name, credential_key, credential_value)

        with open(self.user_config_file_path, 'w') as config_file:
            config.write(config_file)


    def _user_credential_value(self, connection_name: str, credential_key: str,
                               default: str = None) -> str:
        """
        Retrieve a value from a user configparser file.

        :param connection_name: Section of the config file.
        :param credential_key: Key to retrieve the value for.
        :param default: The default value to be returned if the key/value is not found.
        :return: Value associated with the key.
        """

        config = configparser.ConfigParser()

        if not os.path.exists(self.user_config_file_path):
            raise FileNotFoundError(f"The config file {self.user_config_file_path} does not exist.")

        config.read(self.user_config_file_path)

        if not config.has_option(connection_name, credential_key) and default is not None:
            return default

        if not config.has_section(connection_name) or not config.has_option(connection_name, credential_key):
            raise KeyError(f"The key {credential_key} does not exist in the config file.")

        return config.get(connection_name, credential_key)

    def user_credential(self, connection_name: str, credential_key: str = 'password'):
        """Returns the selected (by credential_key) password in plain text. :param credential_key: Used to specify which
        password or username we wish to retrieve from the credentials section of the ini file.
        :type credential_key: str
        :return: Plain text password.
        :rtype: str
        """

        encrypted_password = self._user_credential_value(connection_name=connection_name,
                                                         credential_key=credential_key)
        password = _decrypted_user_credential(encrypted_credential=encrypted_password)
        return password


    def _decrypted_username(self, connection_name: str):
        """Returns the selected (by username_key) username in plain text.
        :param connection_name: The name of the stored database connection.
        :return: Plain text username.
        :rtype: str
        """
        username = self.user_credential(connection_name=connection_name,
                                        credential_key='username')

        return username


    def _decrypted_password(self, connection_name: str):
        """Returns the selected (by username_key) username in plain text.
        :param connection_name: The name of the stored database connection.
        :return: Plain text username.
        :rtype: str
        """

        password = self.user_credential(connection_name=connection_name,
                                        credential_key='password')

        return password



# Don't leave a @log_call here
def _derive_key(encryption_password: str, salt: bytes) -> bytes:
    """
    Derives a 256-bit key from the given password and salt using PBKDF2HMAC.

    Args:
        encryption_password (str): The password to derive the key from.
        salt (bytes): The salt to use in the key derivation function.

    Returns:
        bytes: The derived 256-bit key.
    """
    # Initialize the key derivation function with the provided parameters
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bits
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    # Derive the key from the password and salt
    key = kdf.derive(encryption_password.encode())
    return key


# Don't leave a @log_call here
def _encrypted_user_credential(credential: str) -> str:
    """The encrypted_user_password function accepts a username, or password, and returns the encrypted form,
    which is locked in (encrypted) to the users machine.

    Args:
        password (str): The plaintext password.

    Returns:
        str: The base64-encoded encrypted username/password, including the salt, IV, tag, and ciphertext.
     """
    system_identifier = _system_id()
    encrypted_password = _data_encrypt(data_to_encrypt=credential, encryption_password=system_identifier)
    return encrypted_password


# Don't leave a @log_call here
def _decrypted_user_credential(encrypted_credential: str) -> str:
    """The decrypted_user_credential function, accepts an encrypted username or password, previously encrypted by the
    encrypted_user_password function, and returns the decrypted password.

    Args: encrypted_password (str): The base64-encoded encrypted username/password, including the salt, IV, tag,
    and ciphertext.

    Returns:
        str:  The plaintext password.
    """
    system_identifier = _system_id()
    decrypted_credential = _data_decrypt(encrypted_data=encrypted_credential, encryption_password=system_identifier)
    return decrypted_credential


# Don't leave a @log_call here
def _data_encrypt(data_to_encrypt: str, encryption_password: str) -> str:
    """
    Encrypts the provided data using AES-256-GCM.

    Args:
        data_to_encrypt (str): The plaintext data to encrypt.
        encryption_password (str): The password to derive the encryption key from.

    Returns:
        str: The base64-encoded encrypted data, including the salt, IV, tag, and ciphertext.
    """
    # Generate a random salt and IV
    salt = os.urandom(16)
    iv = os.urandom(12)

    # Derive the encryption key using the password and salt
    key = _derive_key(encryption_password, salt)

    # Initialize the AES-GCM encryptor with the derived key and IV
    encryptor = Cipher(
        algorithms.AES(key),
        modes.GCM(iv),
        backend=default_backend()
    ).encryptor()

    # Encrypt the data
    ciphertext = encryptor.update(data_to_encrypt.encode()) + encryptor.finalize()

    # Concatenate the salt, IV, tag, and ciphertext, and base64-encode the result
    encrypted_result = b64encode(salt + iv + encryptor.tag + ciphertext).decode('utf-8')
    return encrypted_result


def _data_decrypt(encrypted_data: str, encryption_password: str) -> str:
    """
    Decrypts the provided encrypted data using AES-256-GCM.

    Args:
        encrypted_data (str): The base64-encoded encrypted data to decrypt.
        encryption_password (str): The password to derive the decryption key from.

    Returns:
        str: The decrypted plaintext data.
    """
    # Base64-decode the encrypted data to extract the salt, IV, tag, and ciphertext
    encrypted_data_bytes = b64decode(encrypted_data.encode('utf-8'))
    salt = encrypted_data_bytes[:16]
    iv = encrypted_data_bytes[16:28]
    tag = encrypted_data_bytes[28:44]
    ciphertext = encrypted_data_bytes[44:]

    # Derive the decryption key using the password and salt
    key = _derive_key(encryption_password, salt)

    # Initialize the AES-GCM decryptor with the derived key, IV, and tag
    decryptor = Cipher(
        algorithms.AES(key),
        modes.GCM(iv, tag),
        backend=default_backend()
    ).decryptor()

    # Decrypt the data
    decrypted_data = decryptor.update(ciphertext) + decryptor.finalize()

    return decrypted_data.decode('utf-8')





if __name__ == "__main__":
    # Example data_encrypt()/data_decrypt() usage:
    original_data = "This is a secret message."
    passwd = "strongpassword123"

    # Encrypt the data
    encrypted = _data_encrypt(original_data, passwd)
    print(f"Encrypted: {encrypted}")

    # Decrypt the data
    decrypted = _data_decrypt(encrypted, passwd)
    print(f"Decrypted: {decrypted}")
    user_security = UserSecurity(project_identifier='UserSecurity')
    user_security.update_named_connection(connection_name="bozzy", username='clive', password='Wibble', dsn='bozzy_tns')
    db_username = user_security._decrypted_username(connection_name='bozzy')
    db_password = user_security._decrypted_password(connection_name='bozzy')

    print(f'Retrieved Username: {db_username}; password: {db_password}')

