# config_loader.py

__author__ = "Clive Bostock"
__date__ = "2024-11-09"
__description__ = "Manages the database connection/close."

import oracledb


class DBSession(oracledb.Connection):
    def __init__(self, dsn: str, db_username: str, db_password: str):
        """
        Initialises the database session as an Oracle Connection subclass.

        :param dsn: str - Oracle Data Source Name (DSN), typically in the form 'hostname:port/service_name'
        :param db_username: str - Oracle database username
        :param db_password: str - Oracle database password
        """
        try:
            # Initialise the parent class with connection parameters
            super().__init__(user=db_username, password=db_password, dsn=dsn)
            self.dsn_string = dsn
            self.db_username = db_username
            self.db_password = db_password

        except oracledb.DatabaseError as e:
            print("Failed to initialise database session:", e)

    def run_test_query(self) -> None:
        """
        Runs a test SQL query on the Oracle database to verify the connection.

        :return: None
        """
        try:
            with self.cursor() as cursor:
                # Execute the SQL query
                cursor.execute("select 'Hello world!' from dual")

                # Fetch and print the result
                result = cursor.fetchone()
                print(result[0])  # Expected output: "Hello world!"

        except oracledb.DatabaseError as e:
            print("Error executing test query:", e)


    def _tns_connect_string(self) -> str:
        """A private function to return the connect string. This is for use when storing a connection."""
        return f"{self.db_username}/{self.db_password}@{self.dsn_string}"

    def fetch_as_dicts(self, sql_query: str, bind_mappings: dict = None) -> list[dict]:
        """
        Executes a SELECT query with optional bind parameters and returns the result as a list of dictionaries.

        :param sql_query: The SQL SELECT statement to execute.
        :type sql_query: str
        :param bind_mappings: Optional dictionary of bind variables to be used in the query.
        :type bind_mappings: dict, optional
        :return: A list of dictionaries, where each dictionary represents a row and maps column names to values.
        :rtype: list[dict]
        """
        try:
            with self.cursor() as cursor:
                # Execute the query with bind parameters if provided
                if bind_mappings:
                    cursor.execute(sql_query, bind_mappings)
                else:
                    cursor.execute(sql_query)

                # Fetch all rows
                rows = cursor.fetchall()

                # Get column names
                column_names = [desc[0] for desc in cursor.description]

                # Map rows to column names dictionary entries
                result = [dict(zip(column_names, row)) for row in rows]

                return result

        except oracledb.DatabaseError as e:
            print(f'Error executing SQL SELECT statement: {sql_query}')
            raise

    def fetch_as_lists(self, sql_query: str, bind_mappings: dict = None) -> list[list]:
        """
        Executes a SELECT query with optional bind parameters and returns the result as a list of lists.

        :param sql_query: The SQL SELECT statement to execute.
        :type sql_query: str
        :param bind_mappings: Optional dictionary of bind variables to be used in the query.
        :type bind_mappings: dict, optional
        :return: A list of lists, where each inner list represents a row and contains column values.
        :rtype: list[list]
        """
        try:
            with self.cursor() as cursor:
                # Execute the query with bind parameters if provided
                if bind_mappings:
                    cursor.execute(sql_query, bind_mappings)
                else:
                    cursor.execute(sql_query)

                # Fetch all rows
                rows = cursor.fetchall()

                # Directly return rows as a list of lists (each row is a list)
                result = [list(row) for row in rows]

                return result

        except oracledb.DatabaseError as e:
            print(f'[CRITICAL]: Error executing SQL SELECT statement: {sql_query}')
            raise

    def __del__(self):
        """
        Ensures the connection is closed upon deletion of the DBSession instance.

        :return: None
        """
        try:
            self.close()
        except oracledb.DatabaseError as e:
            print("Error closing the database connection:", e)

if __name__ == "__main__":
    # Connection parameters
    dsn = "localhost:1245/UTPLSQL"
    username = "aut"
    password = "Wibble123"

    # Initialise the DB session
    db_session = DBSession(dsn=dsn, db_username=username, db_password=password)
    binds = {'employee_id': 117}

    # Test the new method
    sql = "SELECT employee_id, first_name, last_name, department_id, salary FROM employees where employee_id = :employee_id"
    result = db_session.fetch_as_dicts(sql_query=sql, bind_mappings=binds)

    for row in result:
        print(row)

    result = db_session.fetch_as_lists(sql_query=sql, bind_mappings=binds)

    for row in result:
        print(row)

    # Example output:
    # {'EMPLOYEE_ID': 101, 'FIRST_NAME': 'John', 'LAST_NAME': 'Doe'}
    # {'EMPLOYEE_ID': 102, 'FIRST_NAME': 'Jane', 'LAST_NAME': 'Smith'}
