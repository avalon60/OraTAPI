__author__ = "Clive Bostock"
__date__ = "2024-11-09"
__description__ = "Manages the configuration data via configparser."
from pathlib import Path
from configparser import ConfigParser, ExtendedInterpolation
import configparser
import os


def load_config(file_path: Path) -> configparser.ConfigParser:
    """
    Loads a configuration file and returns a ConfigParser object.

    :param file_path: Path to the configuration file
    :return: ConfigParser object containing the configuration data
    """
    config = configparser.ConfigParser()
    config.read(file_path)
    return config

def compare_config_files(config_file_path: Path, config_sample_file: Path) -> None:
    """
    Compares two configuration files and reports new and obsolete properties.

    :param config_file_path: Path to the actual configuration file
    :param config_sample_file: Path to the sample configuration file
    """
    print("Checking for config file updates...")
    print(f"\nComparing (current): {config_file_path}")
    print(f"      with (latest): {config_sample_file}\n")
    config_file = load_config(config_file_path)
    config_sample = load_config(config_sample_file)

    new_properties = []
    obsolete_properties = []

    # Get all sections from both config files
    all_sections = set(config_file.sections()).union(set(config_sample.sections()))

    for section in all_sections:
        # Strip leading/trailing spaces from section names
        section = section.strip()

        # Get options from both sections, if they exist
        file_options = set(option.strip() for option in config_file.options(section)) if config_file.has_section(section) else set()
        sample_options = set(option.strip() for option in config_sample.options(section)) if config_sample.has_section(section) else set()

        # Determine new and obsolete options
        new_in_sample = sample_options - file_options
        obsolete_in_file = file_options - sample_options

        # Collect results for new and obsolete options
        for option in new_in_sample:
            new_properties.append(f"[NEW] {section}.{option} is present in sample but missing from actual config")
        for option in obsolete_in_file:
            obsolete_properties.append(f"[OBSOLETE] {section}.{option} is present in actual config but missing from sample")

    # Output results
    if new_properties:
        print("New properties:")
        print("\n".join(new_properties))
    else:
        print("No new properties found.")

    if obsolete_properties:
        print("\nObsolete properties:")
        print("\n".join(obsolete_properties))
    else:
        print("\nNo obsolete properties found.")


class ConfigManager:
    def __init__(self, config_file_path:Path):
        self.config_file_path = Path(config_file_path)

        self.check_for_config_file()
        self.config = configparser.ConfigParser(interpolation=ExtendedInterpolation())
        self.config.read(self.config_file_path)
        self.global_substitutions = {}
        self._hydrate_dictionary()


    def check_for_config_file(self) -> None:
        """Function tests to see if the main config file, config.ini, file exists. If the config file is
        missing/inaccessible, a ``FileNotFoundError`` exception is raised."""
        if not self.config_file_path.exists():
            print(f'Unable to locate the config file: {self.config_file_path}')
            raise FileNotFoundError

    def config_value(self, config_section: str, config_key: str,
                     default: str = None) -> str:
        """
        Retrieve a value from a user configparser file.

        :param config_section: Section of the config file.
        :param config_key: Key to retrieve the value for.
        :param config_filename: Name of the config file (e.g. "config.ini" - not a pathname).
        :param default: The default value to be returned if the key/value is not found.
        :return: Value associated with the key.
        """

        if not self.config.has_option(config_section, config_key) and default is not None:
            return default

        if not self.config.has_section(config_section) or not self.config.has_option(config_section, config_key):
            message = f"The key {config_section}.{config_key} does not exist in the config file ({self.config_file_path })."
            raise KeyError(f"{message}")

        return self.config.get(config_section, config_key)


    def bool_config_value(self, config_section: str, config_key: str,
                          default: bool = None) -> bool:
        """
        Retrieve a value from a user configparser file.

        :param config_section: Section of the config file.
        :param config_key: Key to retrieve the value for.
        :param config_filename: Name of the config file (e.g. "config.ini" - not a pathname).
        :param default: The default value to be returned if the key/value is not found.
        :return: Value associated with the key.
        """

        if not self.config.has_option(config_section, config_key) and default is not None:
            return default

        if not self.config.has_section(config_section) or not self.config.has_option(config_section, config_key):
            message = f"The key {config_section}.{config_key} does not exist in the config file ({self.config_file_path })."
            raise KeyError(f"{message}")

        return self.config.getboolean(section=config_section, option=config_key)

    def config_dictionary(self):
        return self.global_substitutions

    def _hydrate_dictionary(self):
        # Read all sections from the config file
        for section in self.config.sections():
            # Update self.global_substitutions with key-value pairs from each section
            self.global_substitutions.update(dict(self.config.items(section)))

    def path_config_value(self, config_section: str, config_key: str,
                          default: str = None, suppress_warnings: bool = False) -> Path:
        """
        Retrieve a value from a user configparser file and return it as a Path object.

        :param config_section: Section of the config file.
        :type config_section: str
        :param config_key: Key to retrieve the value for.
        :type config_key: str
        :param default: The default value to be returned if the key/value is not found.
        :type default: str, optional
        :param suppress_warnings: Whether to suppress warnings for non-path-like values.
        :type suppress_warnings: bool, optional
        :return: Path object derived from the associated value.
        :rtype: Path
        """
        # Retrieve the configuration value
        path_name = self.config_value(config_section=config_section, config_key=config_key, default=default)

        # Check if the value looks like a pathname and optionally warn
        if not os.path.isabs(path_name) and ('/' not in path_name and '\\' not in path_name) and not suppress_warnings:
            print(
                f"WARNING: Expected a pathname from config_section: {config_section} / config_key: {config_key}, but got '{path_name}'")

        # Convert the value to a Path object and return
        return Path(path_name)

    def print_config(self):
        """Print the entire contents of the config file, config.ini."""

        for section in self.config.sections():
            print('*** Config Listing ***')
            for config_section in self.config.sections():
                print(f'\nSection: {section}')
                for property_name, property_value in self.config.items(config_section):
                    print(f'  {property_name} = {property_value}')
            print('\n*** End of Config ***')


    def __repr__(self) -> str:
        """
        Return a string representation of the ConfigManager instance.

        :return: str - Formatted representation of the object with config file path
        """
        return f"<ConfigManager(config_file_path='{self.config_file_path}')>"


if __name__ == '__main__':
    actual_config_path = Path('/home/clive/PycharmProjects/stage/oratapi-1.4.16/resources/config/OraTAPI.ini')
    sample_config_path = Path('/home/clive/PycharmProjects/stage/oratapi-1.4.16/resources/config/samples/OraTAPI.ini.sample')

    # Run the comparison with debug output
    compare_config_files(actual_config_path, sample_config_path)
