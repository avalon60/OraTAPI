__author__ = "Clive Bostock"
__date__ = "2024-06-14"
__doc__ = "This is a library module provides the APIs for config parameters."

from configparser import ConfigParser, ExtendedInterpolation
import configparser
import os
from pathlib import Path

APP_HOME = os.path.dirname(os.path.realpath(__file__))
APP_HOME = Path(os.path.dirname(APP_HOME))
CONFIG_DIR = APP_HOME / 'config'
OHAI_TEST_INI = CONFIG_DIR / 'config.ini'


def check_for_config_file() -> None:
    """Function tests to see if the main config file, config.ini, file exists. If the config file is
    missing/inaccessible, a ``FileNotFoundError`` exception is raised."""
    if not OHAI_TEST_INI.exists():
        print(f'Unable to locate the config file: {OHAI_TEST_INI}')
        raise FileNotFoundError


def config_property(config_section: str, config_property: str, default: str = None) -> str:
    """Function to return a value for a specific property from the OHAI config ini (Configparser) file.

    :param config_section: The config file section of the property to retrieve.
    :type config_section: str
    :param config_property: Key to the value which is to be returned.
    :type config_property: str
    :param default: If the value is not found in the property file, return this default.
    :type default: str

    :return: Value of the property
    :rtype: str
    """
    check_for_config_file()
    return config_value(config_section=config_section, config_key=config_property, default=default)


def config_value(config_section: str, config_key: str, config_filename: str = "config.ini",
                 default: str = None) -> str:
    """
    Retrieve a value from a user configparser file.

    :param config_section: Section of the config file.
    :param config_key: Key to retrieve the value for.
    :param config_filename: Name of the config file (e.g. "config.ini" - not a pathname).
    :param default: The default value to be returned if the key/value is not found.
    :return: Value associated with the key.
    """
    config_file_path = get_config_file_path(config_filename)
    config = configparser.ConfigParser(interpolation=ExtendedInterpolation())

    if not os.path.exists(config_file_path):
        raise FileNotFoundError(f"The config file {config_file_path} does not exist.")

    config.read(config_file_path)

    if not config.has_option(config_section, config_key) and default is not None:
        return default

    if not config.has_section(config_section) or not config.has_option(config_section, config_key):
        message = f"The key {config_section}.{config_key} does not exist in the config file ({config_filename})."
        raise KeyError(f"{message}")

    return config.get(config_section, config_key)


def get_config_file_path(config_filename: str) -> Path:
    """
    Get the full path of the config file in the config directory located in the project config directory.

    :param config_filename: Name of the config file in the project config directory.
    :type config_filename: str
    :return: Full pathname to the config file.
    :rtype: Path
    """
    config_dir_path = CONFIG_DIR
    if not os.path.exists(config_dir_path):
        os.makedirs(config_dir_path)
    return Path(os.path.join(config_dir_path, config_filename))


def print_config_section(config_section: str) -> None:
    """Print the contents of a specified config section.

    :param config_section: The config section to print the contents of.
    :type config_section: str
    """
    check_for_config_file()
    parser = ConfigParser(interpolation=ExtendedInterpolation())
    parser.read(OHAI_TEST_INI)
    if not parser.has_section(config_section):
        print(f'Invalid section specified: {config_section}\n')
        print('Valid sections:\n')
        for sect in parser.sections():
            print(sect)
        print('\n*** End of Sections List ***')
        return
    print(f'Section Listing: {config_section}\n', )
    for property_name, property_value in parser.items(config_section):
        print(f'  {property_name} = {property_value}')
    print('\n*** End of Section ***')


def print_config():
    """Print the entire contents of the config file, config.ini."""
    check_for_config_file()
    parser = ConfigParser(interpolation=ExtendedInterpolation())
    parser.read(OHAI_TEST_INI)
    for section in parser.sections():
        print('*** Config Listing ***')
        for config_section in parser.sections():
            print(f'\nSection: {section}')
            for property_name, property_value in parser.items(config_section):
                print(f'  {property_name} = {property_value}')
        print('\n*** End of Config ***')


if __name__ == '__main__':
    print('Test config file existence...')
    check_for_config_file()
    print('Test property value lookup...')
    test_property_value = config_property(config_section='sanity', config_property='check')
    print(f'Look-up: {test_property_value}')
    print('Test config section ("sanity" section) listing...')
    print_config_section('sanity')
    print('Test whole config listing...')
    print_config()
