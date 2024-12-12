"""
__author__ = "Clive Bostock"
__date__ = "2024-11-09"
__description__ = "Home of the table metadata APIs. Here we model Table classes. This is utilised by the api.py module when generating the TAPIs."
"""

# DBSession is a sub-class of oracledb.Connection which has a self.cursor() attribute.
from lib.config_manager import ConfigManager
from model.session_manager import DBSession



class Table:
    def __init__(self, database_session: DBSession, schema_name: str, table_name: str, config_manager: ConfigManager, trace: bool = False):
        """
        Initialize the Table object.

        :param database_session: A database session object connected to Oracle.
        :type database_session: DBSession
        :param schema_name: The schema name of the table.
        :type schema_name: str
        :param table_name: The name of the table.
        :type table_name: str
        :param trace: Enables tracing/debugging if True.
        :type trace: bool
        """
        self.schema_name = schema_name.upper()
        self.table_name = table_name.upper()
        self.table_name_lc = table_name.lower()
        self.trace = trace
        self.db_session = database_session
        self.columns_dict = {}
        self.columns_list = []
        self.max_col_name_len = 0
        self.col_count = 0

        self.row_vers_column_name = config_manager.config_value(config_section="api_controls",
                                                                config_key="row_vers_column_name")


        self.in_out_column_list = []
        self.out_column_list = []
        self.pk_columns_list = []
        self.ak_columns_list = []
        self.in_out_column_list_lc = []
        self.out_column_list_lc = []
        self.pk_columns_list_lc = []
        self.ak_columns_list_lc = []

        self.tab_col_metadata()

    def tab_col_metadata(self) -> dict:
        """
        Queries the Oracle data dictionary for column metadata and returns a nested dictionary.

        :return: A dictionary of dictionaries containing column metadata.
                 Outer key: column_name
                 Inner dictionary keys: 'data_type', 'default_value', 'nullable'
        :rtype: dict
        """
        query = """
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                DATA_DEFAULT,
                NULLABLE
            FROM 
                ALL_TAB_COLUMNS
            WHERE 
                OWNER = :schema_name
                AND TABLE_NAME = :table_name
            ORDER BY column_id
        """
        column_metadata_dict = {}
        column_list = []
        try:
            with self.db_session.cursor() as cursor:
                if self.trace:
                    print(f"Executing query: {query}")
                    print(f"Parameters: schema_name={self.schema_name}, table_name={self.table_name}")
                cursor.execute(query, schema_name=self.schema_name, table_name=self.table_name)
                # For performance reason - resisted the temptation to implement a TableColumn class.
                for row in cursor:
                    column_name, data_type, data_default, nullable = row
                    # Record whether this is part of a PK or UK
                    column_keyed = self._is_column_keyed(column_name=column_name)
                    is_pk_column = self._is_pk_col(column_name=column_name)

                    is_nullable = True if nullable == 'Y' else False

                    self.max_col_name_len = len(column_name) if len(column_name) > self.max_col_name_len else self.max_col_name_len
                    is_ak_column = True if not is_pk_column and column_keyed else False
                    is_row_version_column = True if column_name.lower() == self.row_vers_column_name.lower() else False
                    column_metadata_dict[column_name] = {
                        "data_type": data_type,
                        "default_value": data_default,
                        "is_nullable": is_nullable,
                        "is_pk_column": is_pk_column,
                        "is_ak_column": is_ak_column,
                        "is_key_column": column_keyed,
                        "is_row_version_column": is_row_version_column
                    }
                    if is_pk_column:
                        self.pk_columns_list.append(column_name)
                        self.pk_columns_list_lc.append(column_name.lower())
                    if is_ak_column:
                        self.ak_columns_list.append(column_name)
                        self.ak_columns_list_lc.append(column_name.lower())
                    if column_keyed:
                        self.in_out_column_list.append(column_name)
                        self.in_out_column_list_lc.append(column_name.lower())
                    if is_row_version_column:
                        self.out_column_list.append(column_name)
                        self.out_column_list_lc.append(column_name.lower())


                    column_list.append(column_name)
                    self.col_count += 1
            self.columns_dict = column_metadata_dict
            self.columns_list = column_list

        except Exception as e:
            if self.trace:
                print(f"Error fetching column metadata: {e}")
            raise
        return column_metadata_dict

    def column_property_value(self, column_name:str, property_name:str) -> str:
        """Returns the value of the requested column property from the self.columns_dict. The property_name can be one
         of 'data_type', 'default_value', 'is_nullable' or 'is_key_column'

        :param column_name: Name of the table column to interrogate.
        :param property_name: The property (key) for which the value is to be returned.
        :return:
        """
        _column_name = column_name.upper()
        column_dict = self.columns_dict[_column_name]
        property_value = column_dict[property_name.lower()]
        return property_value

    def _is_column_keyed(self, column_name: str) -> bool:
        """
        Checks if a column is referenced in a primary key constraint or unique index.

        :param column_name: The name of the column to check.
        :type column_name: str
        :return: True if the column is part of a primary key or unique index, otherwise False.
        :rtype: bool
        """
        query = """
            SELECT 1
            FROM ALL_CONS_COLUMNS acc
            JOIN ALL_CONSTRAINTS ac
                ON acc.OWNER = ac.OWNER
                AND acc.CONSTRAINT_NAME = ac.CONSTRAINT_NAME
            WHERE acc.OWNER = :schema_name
                AND acc.TABLE_NAME = :table_name
                AND acc.COLUMN_NAME = :column_name
                AND ac.CONSTRAINT_TYPE IN ('P', 'U')
        """
        try:
            with self.db_session.cursor() as cursor:
                if self.trace:
                    print(f"Executing query: {query}")
                    print(f"Parameters: schema_name={self.schema_name}, table_name={self.table_name}, column_name={column_name.upper()}")
                cursor.execute(
                    query,
                    schema_name=self.schema_name,
                    table_name=self.table_name,
                    column_name=column_name.upper()
                )
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            if self.trace:
                print(f"Error checking if column is keyed: {e}")
            raise

    def _is_pk_col(self, column_name: str) -> bool:
        """
        Checks if a column is referenced in a primary key constraint or unique index.

        :param column_name: The name of the column to check.
        :type column_name: str
        :return: True if the column is part of a primary key or unique index, otherwise False.
        :rtype: bool
        """
        query = """
            SELECT 1
            FROM ALL_CONS_COLUMNS acc
            JOIN ALL_CONSTRAINTS ac
                ON acc.OWNER = ac.OWNER
                AND acc.CONSTRAINT_NAME = ac.CONSTRAINT_NAME
            WHERE acc.OWNER = :schema_name
                AND acc.TABLE_NAME = :table_name
                AND acc.COLUMN_NAME = :column_name
                AND ac.CONSTRAINT_TYPE = 'P'
        """
        try:
            with self.db_session.cursor() as cursor:
                if self.trace:
                    print(f"Executing query: {query}")
                    print(f"Parameters: schema_name={self.schema_name}, table_name={self.table_name}, column_name={column_name.upper()}")
                cursor.execute(
                    query,
                    schema_name=self.schema_name,
                    table_name=self.table_name,
                    column_name=column_name.upper()
                )
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            if self.trace:
                print(f"Error checking if column is keyed: {e}")
            raise

    def __repr__(self):
        """
        Returns a string representation of the Table object, showing its schema and table names,
        along with a summary of the table's column metadata.

        :return: A string representing the Table object.
        :rtype: str
        """
        return (f"Table(schema_name={self.schema_name!r}, table_name={self.table_name!r}, "
                f"columns_count={len(self.columns_dict)}, trace={self.trace})")

if __name__ == "__main__":
    # Connection parameters
    dsn = "localhost:1245/UTPLSQL"
    username = "aut"
    password = "Wibble123"

    # Initialize the DB session
    db_session = DBSession(dsn=dsn, db_username=username, db_password=password)

    # Instantiate the Table class
    table = Table(database_session=db_session, schema_name="AUT", table_name="EMPLOYEES", trace=False)
    metadata = table.tab_col_metadata()
    print(metadata)
    # Check if a column is keyed
    is_keyed = table._is_column_keyed("EMPLOYEE_ID")
    print(f"Is 'EMPLOYEE_ID' keyed? {is_keyed}")
    print(f'Data type property of employees.employee_id : {table.column_property_value("employee_id", "data_type" )}')
