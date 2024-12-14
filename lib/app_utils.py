__author__ = "Clive Bostock"
__date__ = "2024-12-11"
__description__ = "Application utilities"

import re
import sys
import time
import platform
from pathlib import Path
from os import get_terminal_size, system
from datetime import datetime
from platform import platform
import uuid

MESSAGE_RIGHT_PAD=15
MESSAGE_MIN_LEN=40

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