"""
Author: Clive Bostock
Date: 2024-12-30
Description: A class for managing personal information (PI) columns from a CSV file.
"""

import csv
from typing import Dict, Tuple
from pathlib import Path


class PIColumnsManager:
    """
    Manages PI columns by reading a CSV file into a dictionary and providing
    methods to check column existence and retrieve descriptions based on specified criteria.

    :param pi_columns_csv_path: The path to the CSV file containing PI column information.
    """

    def __init__(self, pi_columns_csv_path: Path):
        """
        Initialises the PIColumnsManager with the specified CSV file.

        :param pi_columns_csv_path: Path - Path to the CSV file.
        """
        self.pi_columns_csv_path = pi_columns_csv_path
        self.pi_columns_dict: Dict[Tuple[str, str, str], str] = {}

        # Ensure the CSV file exists and load it
        self._ensure_csv_file()
        self._load_csv()

    def _ensure_csv_file(self) -> None:
        """
        Ensures the CSV file exists. If not, creates the file and populates it with headers.
        """
        if not self.pi_columns_csv_path.exists():
            with open(self.pi_columns_csv_path, mode="w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                # Write headers
                writer.writerow(["Schema Name", "Table Name", "Column Name", "Description"])

    def _load_csv(self) -> None:
        """
        Loads the CSV file into a dictionary keyed on the combination of schema_name, table_name, and column_name.
        """
        with open(self.pi_columns_csv_path, mode="r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            # Normalise headers to lowercase with underscores replacing spaces
            reader.fieldnames = [header.strip().lower().replace(" ", "_") for header in reader.fieldnames]

            for row in reader:
                # Convert the first three keys to lowercase for normalisation
                key = (
                    row["schema_name"].strip().lower(),
                    row["table_name"].strip().lower(),
                    row["column_name"].strip().lower(),
                )
                self.pi_columns_dict[key] = row.get("description", "").strip()

    def check_column(self, schema_name: str, table_name: str, column_name: str) -> bool:
        """
        Checks if a column matches the specified criteria.

        :param schema_name: str - Schema name to check.
        :param table_name: str - Table name to check.
        :param column_name: str - Column name to check.
        :return: bool - True if a match is found, False otherwise.
        """
        return self.get_description(schema_name, table_name, column_name) != ""

    def get_description(self, schema_name: str, table_name: str, column_name: str) -> str:
        """
        Retrieves the description (comment) of a column based on specified criteria.

        :param schema_name: str - Schema name to check.
        :param table_name: str - Table name to check.
        :param column_name: str - Column name to check.
        :return: str - The description if a match is found, otherwise an empty string.
        """
        schema_name = schema_name.lower()
        table_name = table_name.lower()
        column_name = column_name.lower()

        # Check exact match
        if (schema_name, table_name, column_name) in self.pi_columns_dict:
            return self.pi_columns_dict[(schema_name, table_name, column_name)]

        # Check wildcard combinations
        wildcard_values = {"%", "*", "all"}
        for schema_wildcard in wildcard_values:
            for table_wildcard in wildcard_values:
                for column_wildcard in wildcard_values:
                    if (schema_name, table_wildcard, column_name) in self.pi_columns_dict:
                        return self.pi_columns_dict[(schema_name, table_wildcard, column_name)]
                    if (schema_wildcard, table_name, column_name) in self.pi_columns_dict:
                        return self.pi_columns_dict[(schema_wildcard, table_name, column_name)]
                    if (schema_wildcard, table_wildcard, column_name) in self.pi_columns_dict:
                        return self.pi_columns_dict[(schema_wildcard, table_wildcard, column_name)]
                    if (schema_wildcard, table_wildcard, column_wildcard) in self.pi_columns_dict:
                        return self.pi_columns_dict[(schema_wildcard, table_wildcard, column_wildcard)]

        # No match found
        return ""


# Example usage:
# pi_manager = PIColumnsManager(Path("path/to/pi_columns.csv"))
# description = pi_manager.get_description("schema1", "*", "column1")
# print(description)  # The description or an empty string if not found.
