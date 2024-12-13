__author__ = "Clive Bostock"
__date__ = "2024-11-09"
__description__ = "Module responsible for managing the Ora TAPI table control csv file."

from pathlib import Path
import csv
CSV_HEADERS = ["Schema Name", "Table Name", "Packages Enabled", "Views Enabled", "Triggers Enabled"]

def init_csv(csv_pathname: Path):
    """
    Initializes a CSV file with specific headers if it does not exist.

    :param csv_pathname: Path, Path to the CSV file to initialize
    """
    # Define the header columns

    # Check if the file exists
    if not csv_pathname.exists():
        # Create and write the header if the file does not exist
        try:
            with csv_pathname.open(mode='w', newline='', encoding='utf-8') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(CSV_HEADERS)
            print(f"CSV file initialized at: {csv_pathname}")
        except Exception as e:
            print(f"An error occurred while creating the CSV file: {e}")


def get_boolean_value(value: str) -> bool:
    """
    Converts a string value into a boolean based on common boolean representations.

    :param value: str, The string value to convert (e.g., 'yes', 'no', 'true', 'false', etc.)
    :return: bool, The corresponding boolean value
    """
    # List of strings considered as "True" or "False"
    return value.strip().lower() in ['yes', 'true', '1']


def read_csv_to_dict(csv_pathname: Path):
    """
    Reads a CSV file into a dictionary keyed on schema_name and table_name,
    converting the textual boolean values into actual booleans.

    :param csv_pathname: Path, Path to the CSV file
    :return: dict, Dictionary of CSV contents excluding the headers
    """
    result_dict = {}

    try:
        with csv_pathname.open(mode='r', newline='', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                key = (row["Schema Name"], row["Table Name"])
                result_dict[key] = {
                    "Packages Enabled": get_boolean_value(row["Packages Enabled"]),
                    "Views Enabled": get_boolean_value(row["Views Enabled"]),
                    "Triggers Enabled": get_boolean_value(row["Triggers Enabled"])
                }
    except Exception as e:
        print(f"An error occurred while reading the CSV file: {e}")

    return result_dict

def update_property_in_csv_dict(data: dict, schema_name: str, table_name: str, csv_property: str, property_value: bool):
    """
    Updates or creates an entry in the dictionary based on the schema_name, table_name, and property.
    If the entry exists, it updates the specific property with the given value.
    If the entry does not exist, it creates a new entry with default values for all properties.

    :param data: dict, Dictionary containing the data
    :param schema_name: str, The schema name
    :param table_name: str, The table name
    :param csv_property: str, The property to update ("package", "view", "trigger")
    :param property_value: bool, The value to set for the property
    :return: tuple, The updated values for "Packages Enabled", "Views Enabled", "Triggers Enabled"
    """
    # Default properties if entry doesn't exist
    default_values = {
        "Packages Enabled": True,
        "Views Enabled": True,
        "Triggers Enabled": True
    }

    # Check if the schema_name and table_name exist in the dictionary
    if (schema_name, table_name) not in data:
        # If not, create the entry with default values
        data[(schema_name, table_name)] = default_values.copy()

    # Retrieve the current entry for the specific (schema_name, table_name)
    entry = data[(schema_name, table_name)]

    # Update the specific property based on the input
    if csv_property == "package":
        entry["Packages Enabled"] = property_value
    elif csv_property == "view":
        entry["Views Enabled"] = property_value
    elif csv_property == "trigger":
        entry["Triggers Enabled"] = property_value
    else:
        raise ValueError("Invalid property. Use 'package', 'view', or 'trigger'.")

    # Return the updated values as a tuple
    return entry["Packages Enabled"], entry["Views Enabled"], entry["Triggers Enabled"]


def write_dict_to_csv(csv_pathname: Path, data: dict):
    """
    Writes a dictionary back to the CSV file, replacing its contents (except for the headers).

    :param csv_pathname: Path, Path to the CSV file
    :param data: dict, Dictionary to write to the file
    """

    try:
        # Open the CSV file in write mode, which clears the file's existing content
        with csv_pathname.open(mode='w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(CSV_HEADERS)  # Write the headers

            # Write each row from the dictionary
            for (schema_name, table_name), values in data.items():
                writer.writerow([
                    schema_name,
                    table_name,
                    values.get("Packages Enabled", ""),
                    values.get("Views Enabled", ""),
                    values.get("Triggers Enabled", "")
                ])
    except Exception as e:
        print(f"An error occurred while writing to the CSV file: {e}")




# Example usage
if __name__ == "__main__":
    csv_path = Path("/tmp/example.csv")
    init_csv(csv_path)