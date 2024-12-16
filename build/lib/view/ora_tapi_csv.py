__author__ = "Clive Bostock"
__date__ = "2024-11-09"
__description__ = "Module responsible for managing the Ora TAPI table control csv file."

import atexit
from lib.config_manager import ConfigManager
from pathlib import Path
from lib.app_utils import text_to_boolean
import csv
from view.console_display import MsgLvl, ConsoleMgr
app_home = Path(__file__).resolve().parent.parent
config_path = app_home / 'config' / 'OraTAPI.ini'
CSV_HEADERS = ["Schema Name", "Table Name", "Packages Enabled", "Views Enabled", "Triggers Enabled"]

class CSVManager:
    def __init__(self, csv_pathname: Path, config_file_path: Path):
        """
        Initializes the CSVManager with the given path to the CSV file.
        :param csv_pathname: Path to the CSV file
        """
        # self.config_manager = ConfigManager(config_file_path=config_file_path)
        self.console_manager = ConsoleMgr(config_file_path=config_file_path)
        self.success:bool = True
        self.csv_pathname = csv_pathname
        self.data = {}  # Initialize an empty dictionary for managing CSV data
        self.init_csv()
        self.read_csv_to_dict()
        atexit.register(self._cleanup)  # Register the cleanup method


    def init_csv(self):
        """
        Initializes a CSV file with specific headers if it does not exist.
        If the file exists, checks whether it has the expected headers.
        """
        if not self.csv_pathname.exists():
            # File does not exist, create it with headers
            try:
                with self.csv_pathname.open(mode='w', newline='', encoding='utf-8') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(CSV_HEADERS)
                self.console_manager.print_console(text=f"CSV control file not found.",
                                                   msg_level=MsgLvl.warning)
                self.console_manager.print_console(text=f"Instantiating new CSV control file: {self.csv_pathname.absolute()}",
                                                   msg_level=MsgLvl.warning)

            except Exception as e:
                self.console_manager.print_console(text=f"An error occurred while creating the CSV file: {e}", msg_level=MsgLvl.critical)
                print()
        else:
            # File exists, validate its headers
            try:
                with self.csv_pathname.open(mode='r', newline='', encoding='utf-8') as csv_file:
                    reader = csv.reader(csv_file)
                    headers = next(reader, None)  # Read the first row (header row)
                    if headers != CSV_HEADERS:
                        self.success = False
                        raise ValueError(f"Invalid CSV headers. Expected {CSV_HEADERS}, but got {headers}.")
                    self.console_manager.print_console(text="CSV file located and headers are valid.")
            except Exception as e:
                self.console_manager.print_console(text=f"An error occurred while validating the CSV file: {e}",
                                                   msg_level=MsgLvl.critical)

    def read_csv_to_dict(self):
        """
        Reads a CSV file into a dictionary keyed on schema_name and table_name.
        """
        if not self.success:
            print("Cannot read CSV to dict: invalid headers.")
            return  # Abort if headers are invalid

        try:
            with self.csv_pathname.open(mode='r', newline='', encoding='utf-8') as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    key = (row["Schema Name"], row["Table Name"])
                    self.data[key] = {
                        "Packages Enabled": text_to_boolean(row["Packages Enabled"]),
                        "Views Enabled": text_to_boolean(row["Views Enabled"]),
                        "Triggers Enabled": text_to_boolean(row["Triggers Enabled"])
                    }
        except Exception as e:
            self.console_manager.print_console(text=f"An error occurred while reading the CSV file: {e}",
                                               msg_level=MsgLvl.critical)

    def csv_dict_property(self, schema_name: str, table_name: str, property_selector: str) -> bool:
        """
        Creates an entry in the dictionary based on the schema_name, table_name, and property_selector,
        and returns the requested property value. Initializes properties with default values if entry doesn't exist.

        :param schema_name: str, The schema name for the table
        :param table_name: str, The table name
        :param property_selector: str, The property to retrieve, should be one of 'package', 'view', or 'trigger'
        :rtype: bool, The value of the requested property
        """
        if not self.success:
            raise RuntimeError("Cannot modify data due to invalid CSV headers.")

        # Default values for the properties
        default_values = {
            "Packages Enabled": True,
            "Views Enabled": True,
            "Triggers Enabled": True
        }

        # Initialize the entry if it doesn't exist
        if (schema_name, table_name) not in self.data:
            self.data[(schema_name, table_name)] = default_values.copy()

        entry = self.data[(schema_name, table_name)]

        # Map the property_selector to the corresponding property
        property_map = {
            "package": "Packages Enabled",
            "view": "Views Enabled",
            "trigger": "Triggers Enabled"
        }

        # Ensure the property_selector is valid
        if property_selector not in property_map:
            raise ValueError("Invalid property_selector. Use 'package', 'view', or 'trigger'.")

        # Return the value of the requested property
        property_key = property_map[property_selector]
        return entry[property_key]

    def write_dict_to_csv(self):
        """
        Writes the dictionary back to the CSV file if the headers are valid.
        """
        if not self.success:
            print("Skipping writing to CSV as headers are invalid.")
            self.console_manager.print_console(text="Skipping writing to CSV as headers are invalid.",
                                               msg_level=MsgLvl.critical)
            return

        try:
            with self.csv_pathname.open(mode='w', newline='', encoding='utf-8') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(CSV_HEADERS)

                for (schema_name, table_name), values in self.data.items():
                    writer.writerow([
                        schema_name,
                        table_name,
                        values.get("Packages Enabled", ""),
                        values.get("Views Enabled", ""),
                        values.get("Triggers Enabled", "")
                    ])
        except Exception as e:
            self.console_manager.print_console(text=f"An error occurred while writing to the CSV file: {e}",
                                               msg_level=MsgLvl.critical)

    def _cleanup(self):
        """
        Cleanup method to automatically save the data to the CSV file on program exit.
        """
        if not self.success:
            print("Skipping cleanup: invalid headers.")
            self.console_manager.print_console(text="Skipping cleanup: invalid headers.",
                                               msg_level=MsgLvl.warning)
            return

        self.console_manager.print_console(text=f"Exiting: Updating CSV control file: {self.csv_pathname.absolute()}",
                                           msg_level=MsgLvl.highlight)
        self.write_dict_to_csv()


# Example usage
if __name__ == "__main__":
    csv_path = Path("/tmp/example.csv")
    csv_mgr = CSVManager(csv_pathname=csv_path, config_file_path=config_path)
    csv_mgr.csv_dict_property("TestSchema", "TestTable", "package")
