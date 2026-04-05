__author__ = "Clive Bostock"
__date__ = "2024-12-11"
__description__ = "Application utilities"

import re
import sys
import platform
from pathlib import Path
from os import get_terminal_size, system
from datetime import datetime
from platform import platform
import uuid
import requests
from urllib.parse import urlsplit


MESSAGE_RIGHT_PAD=15
MESSAGE_MIN_LEN=40

def get_latest_dist_url(repo_owner: str, repo_name: str) -> str:
    """
    Fetches the latest release distribution file path of a GitHub repository.
    This assumes that the tarball file name is of the form oratapi-X.Y.Z.tar.gz,
    where the X.Y.Z represents the version or OraTAPI.

    :param repo_owner: The owner of the repository (e.g. 'avalon60')
    :param repo_name: The name of the repository (e.g. 'OraTAPI')
    :return: The latest release version or download URL
    """
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        tag_name = data.get("tag_name", "")  # e.g., "v1.4.20"
        version = tag_name[1:] if tag_name.startswith("v") else tag_name
        expected_asset_name = f"oratapi-{version}.tar.gz"

        for asset in data.get("assets", []):
            if asset.get("name") == expected_asset_name:
                return asset["browser_download_url"]

        return (
            f"Version: {tag_name} (No matching tar.gz asset found. "
            f"Expected asset name: {expected_asset_name})"
        )
    else:
        return f"Failed to fetch latest release. HTTP Status: {response.status_code}"

def get_latest_version(repo_owner: str, repo_name: str) -> str:
    """
    Fetches the latest release version of a GitHub repository.

    :param repo_owner: The owner of the repository (e.g., 'avalon60')
    :param repo_name: The name of the repository (e.g., 'OraTAPI')
    :return: Version
    """
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        version = data.get("tag_name")  # e.g., "v1.4.20"
        return version

def download_file(url: str, save_dir: Path) -> Path:
    """
    Downloads a file from a URL and saves it to a specified local directory.

    :param url: str, The URL of the file to download.
    :param save_dir: str, The local directory where the file should be saved.
    :returns: Path, The full path to the downloaded file.
    :raises: Exception if the download fails.
    """
    # Extract the file name from the URL
    file_name = Path(urlsplit(url).path).name

    # Ensure the save directory exists
    save_path = Path(save_dir)  # Convert save_dir to a Path object
    save_path.mkdir(parents=True, exist_ok=True)  # Create directory if it doesn't exist

    # Full path where the file will be saved
    file_path = save_path / file_name

    # Download the file
    try:
        print(f"Downloading {url}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an HTTPError for bad responses

        # Write the file to the specified location
        with file_path.open(mode='wb') as file:  # Use Path's `open` method
            for chunk in response.iter_content(chunk_size=8192):  # Download in chunks
                file.write(chunk)

        print(f"File downloaded successfully: {file_path}")
        return file_path
    except Exception as e:
        print(f"Error downloading file: {e}")
        raise


class SystemCommandError(Exception):
    """This exception is raised when we detect a failure when attempting to execute an operating system command, or
    bash shell script, via a Python system() call."""

    def __init__(self, message):
        self.message = message
        super().__init__(message)

# When running in an IDE the following causes an exception.
try:
    MESSAGE_PAD_LENGTH = MESSAGE_MIN_LEN if (get_terminal_size()[0] - MESSAGE_RIGHT_PAD) < MESSAGE_MIN_LEN else get_terminal_size()[0] - MESSAGE_RIGHT_PAD
except:
    MESSAGE_PAD_LENGTH = 15

def current_timestamp() -> str:
    """
    Returns the current timestamp with the detected timezone.

    :return: A formatted ("%Y-%m-%d %H:%M:%S %z") timestamp string.
    """

    # Get the local datetime
    now = datetime.now()

    # Determine the local timezone
    local_tz = now.astimezone().tzinfo

    # Convert to a timezone-aware datetime
    local_dt = now.astimezone(local_tz)

    # Format the timestamp
    timestamp_str = local_dt.strftime("%Y-%m-%d %H:%M:%S %z")
    return timestamp_str

def current_dttm() -> str:
    """
    Returns the current date/time with the detected timezone.

    :return: A formatted ("%Y-%m-%d %H:%M %z") date/time string.
    """

    # Get the local datetime
    now = datetime.now()

    # Determine the local timezone
    local_tz = now.astimezone().tzinfo

    # Convert to a timezone-aware datetime
    local_dt = now.astimezone(local_tz)

    # Format the timestamp
    timestamp_str = local_dt.strftime("%Y-%m-%d %H:%M %z")
    return timestamp_str

def dotted_print(text: str, pad_length: int = MESSAGE_PAD_LENGTH) -> None:
    """Print a message which is right padded with dots, to a specified length.
    :param text: Text to print
    :type text: str
    :param pad_length: Length to right pad the string, using dots
    :type pad_length:
    """

    _message = text.ljust(pad_length, '.')
    sys.stdout.write(_message)
    sys.stdout.flush()

def text_to_boolean(value: str) -> bool:
    """Converts a string to a boolean value.
    :param value: String value to convert
    :return: Boolean representation
    """
    true_values = {"true", "1", "yes", "on"}
    false_values = {"false", "0", "no", "off"}

    value = str(value).strip().lower()
    if value in true_values:
        return True
    elif value in false_values:
        return False
    raise ValueError(f"Invalid boolean string: {value}")


def text_to_boolean(value: str) -> bool:
    """
    Converts a string value into a boolean based on common boolean representations.

    :param value: str, The string value to convert (e.g., 'yes', 'no', 'true', 'false', etc.)
    :return: bool, The corresponding boolean value
    """
    # List of strings considered as "True" or "False"
    return value.strip().lower() in ['yes', 'true', '1']

def escaped_md_chars(log_message: str) -> str:
    """
    Escapes special characters like '<' and '>' in a log message for markdown output.

    :param log_message: Log message string to escape
    :type log_message: str
    Parameters:
    log_message (str): The log message to escape.

    :return: The log message with special characters escaped.
    :rtype: str
    """
    # Replace special characters with HTML entities
    escaped_message = log_message.replace('<', '&lt;').replace('>', '&gt;')

    return escaped_message

def exec_bash_command(command:str, git_bash_path:Path = None):
    """Executes a bash command. If this is on Windows we assume we have Git bash installed. If this is not Windows,
    we execute the command using the native bash.

    :param command: The bash command to be executed.
    :param git_bash_path: """
    _platform = platform()

    if _platform == 'Windows':
        command_line = f'{git_bash_path} -c "source /etc/profile; exec {command}"'
    else:
        command_line = f'bash -c "exec {command}"'

    return_code = system(command_line)
    if return_code != 0:
        _message = f'Error executing command: "{command}" ["{command_line}"]'
        raise SystemCommandError(_message)

def format_elapsed_time(start_ts: int, end_ts: int) -> str:
    """
    Calculates and formats the elapsed time between two epoch timestamps.
    E.g.  
        epoc_start_ts = int(time.time())
        ...
        epoc_end_ts = int(time.time())
        el_time =  format_elapsed_time(start_time=epoch_start_td, end_time=epoch_end_ts)
        
        
    Args:
        start_time (int): The start epoch timestamp. 
        end_time (int): The end epoch timestamp.

    Returns:
        str: The formatted elapsed time as a string in the format "HH:MM:SS".

        :param start_ts:  The start epoch timestamp (int).
        :param end_ts: The end epoch timestamp (int).
        :return: Formatted elapsed time.
    """
    elapsed_seconds = end_ts - start_ts

    # Calculate hours, minutes, and seconds
    hours = elapsed_seconds // 3600
    minutes = (elapsed_seconds % 3600) // 60
    seconds = elapsed_seconds % 60

    # Format the result as "HH:MM:SS"
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def strip_log_ansi(log_text):
    """Function to strip ANSI colour coding characters from the captured log output.

    :param log_text: Loguru log text
    :return: Loguru log text without colour encoding.
    """

    # ANSI escape codes pattern
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', log_text)


import string
import random


def random_string(length: int) -> str:
    """
    Generate a random string of the specified length without single quotes.

    :param length: The length of the string to generate.
    :type length: int
    :return: A randomly generated string.
    :rtype: str
    """
    if length < 1:
        raise ValueError("Length must be at least 1.")

    # Combine lowercase, uppercase letters, and digits (explicitly excluding single quotes)
    characters = (string.ascii_letters + string.digits).replace("'", "~")

    # Combine lowercase, uppercase letters, and digits (explicitly excluding | characters)
    characters = (string.ascii_letters + string.digits).replace("|", "@")

    # Generate a random string
    return ''.join(random.choices(characters, k=length))


def enhanced_guid(extend_by:int = 4) -> str:

    random_string1 = random_string(length=extend_by)
    guid = sys_guid()
    random_string2 = random_string(length=extend_by)
    _enhanced_guid = random_string1 + guid + random_string2

    return _enhanced_guid


def sys_guid() -> str:
    """
    Generates a GUID equivalent to Oracle's SYS_GUID().

    :return: str, a globally unique identifier in the same hexadecimal format as SYS_GUID.
    """
    # Generate a UUID and convert it to uppercase hexadecimal string without dashes
    return uuid.uuid4().hex.upper()


if __name__ == '__main__':
    this_platform = platform()
    print(f'OS: {this_platform}')
