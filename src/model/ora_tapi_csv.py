__author__ = "Clive Bostock"
__date__ = "2024-11-09"
__description__ = "Module responsible for managing the Ora TAPI table control CSV file."

import atexit
from pathlib import Path
from lib.app_utils import text_to_boolean
import csv
from view.console_display import MsgLvl, ConsoleMgr

app_home = Path(__file__).resolve().parent.parent
config_path = app_home / 'config' / 'OraTAPI.ini'
CSV_HEADERS = ["Schema Name", "Table Name", "Domain", "Packages Enabled", "Views Enabled", "Triggers Enabled"]


class CSVManager:
    def __init__(self, csv_pathname: Path, config_file_path: Path, cleanup: bool=True):
        self.console_manager = ConsoleMgr(config_file_path=config_file_path)
        self.success: bool = True
        self.csv_pathname = csv_pathname
        self.data = {}  # Initialize an empty dictionary for managing CSV data
        self.init_csv()
        self.read_csv_to_dict()
        atexit.register(self._cleanup)  # Register the cleanup method
        self.cleanup = cleanup

    def init_csv(self):
        """Open the OraTAPI.csv file. If it doesn't exist, instantiate it."""
        if not self.csv_pathname.exists():
            try:
                with self.csv_pathname.open(mode='w', newline='', encoding='utf-8') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(CSV_HEADERS)
                self.console_manager.print_console(text=f"CSV control file not found.",
                                                   msg_level=MsgLvl.warning)
                self.console_manager.print_console(text=f"Instantiating new CSV control file: {self.csv_pathname.absolute()}",
                                                   msg_level=MsgLvl.warning)
            except Exception as e:
                self.console_manager.print_console(text=f"An error occurred while creating the CSV file: {e}",
                                                   msg_level=MsgLvl.critical)
        else:
            try:
                with self.csv_pathname.open(mode='r', newline='', encoding='utf-8') as csv_file:
                    reader = csv.reader(csv_file)
                    headers = next(reader, None)  # Read the first row (header row)
                    if headers != CSV_HEADERS:
                        self.success = False
                        raise ValueError(f"Invalid CSV headers. Expected {CSV_HEADERS}, but got {headers}.")
            except Exception as e:
                self.console_manager.print_console(text=f"An error occurred while validating the CSV file: {e}",
                                                   msg_level=MsgLvl.critical)

    def read_csv_to_dict(self):
        """Read the OraTAPI.csv file, into a dictionary, keyed on schema name and table name."""
        if not self.success:
            print("Cannot read CSV to dict: invalid headers.")
            return

        try:
            with self.csv_pathname.open(mode='r', newline='', encoding='utf-8') as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    key = (row["Schema Name"], row["Table Name"])
                    self.data[key] = {
                        "Domain": row.get("Domain", "Undefined"),
                        "Packages Enabled": text_to_boolean(row["Packages Enabled"]),
                        "Views Enabled": text_to_boolean(row["Views Enabled"]),
                        "Triggers Enabled": text_to_boolean(row["Triggers Enabled"])
                    }
        except Exception as e:
            self.console_manager.print_console(text=f"An error occurred while reading the CSV file: {e}",
                                               msg_level=MsgLvl.critical)

    def csv_dict_property(self, schema_name: str, table_name: str, property_selector: str) -> str:
        """Returns the requested property value, associated with property_selector, from the OraTAPI.csv data.
        :param schema_name: Table schema name
        :param table_name: Table name
        :param property_selector: The property key
        :return: The property value
        """
        if not self.success:
            raise RuntimeError("Cannot modify data due to invalid CSV headers.")

        # Default values for the properties
        default_values = {
            "Domain": "Undefined",
            "Packages Enabled": True,
            "Views Enabled": True,
            "Triggers Enabled": True
        }

        if (schema_name, table_name) not in self.data:
            self.data[(schema_name, table_name)] = default_values.copy()

        entry = self.data[(schema_name, table_name)]

        property_map = {
            "domain": "Domain",
            "package": "Packages Enabled",
            "view": "Views Enabled",
            "trigger": "Triggers Enabled"
        }

        if property_selector not in property_map:
            raise ValueError("Invalid property_selector. Use 'domain', 'package', 'view', or 'trigger'.")

        property_key = property_map[property_selector]
        return entry[property_key]

    def write_dict_to_csv(self):
        """Update the CSV file from our in-memory dictionary."""
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
                        values.get("Domain", "Undefined"),
                        values.get("Packages Enabled", ""),
                        values.get("Views Enabled", ""),
                        values.get("Triggers Enabled", "")
                    ])
        except Exception as e:
            self.console_manager.print_console(text=f"An error occurred while writing to the CSV file: {e}",
                                               msg_level=MsgLvl.critical)

    def _cleanup(self):
        """If instantiated with cleanup = True, we perform a cleanup on exit. There are cases where we don't want to
        performa a cleanup. For example, we instantiate a CSVManager, from the api_generator.py, just for reading
        the table domain mappings. We don't want to update the  CSV file after every table is processed."""
        if not self.cleanup:
            return
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
