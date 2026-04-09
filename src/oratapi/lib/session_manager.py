# Author: Clive Bostock
# Date: 2024-11-09
# Description: Manages the database connection and provides various convenience methods for querying Oracle.
from time import time_ns

from oratapi.lib.framework_errors import PLSQLScriptError, DatabaseConnectionError
from oratapi.lib.fsutils import resolve_path
import os
import platform
import oracledb
from pathlib import Path
import tempfile
import zipfile
from typing import Any
import re

CRITICAL = '❌'
INFO = 'ℹ️'
ERROR = '❗'
WARNING = '⚠️'


class DBSession(oracledb.Connection):
    """
    A database session class subclassing `oracledb.Connection`,
    with methods to execute queries and fetch results in different formats.
    """

    def __init__(self, wallet_zip_path: str = '', verbose: bool = True, **kwargs):
        """
        Initialises the DBSession with optional wallet support.

        Args:
            wallet_zip_path (str): Path to the zipped Oracle wallet.
            **kwargs: Parameters passed to oracledb.Connection.
        """
        self.connection_succeeded = False
        self.verbose = verbose

        try:

            self.user = kwargs.get("user")
            self.password = kwargs.get("password")
            self.dsn_string = kwargs.get("dsn")

            wallet_path = None
            if wallet_zip_path.strip():
                expanded_path = os.path.expandvars(wallet_zip_path.strip())
                candidate = Path(expanded_path).expanduser()
                if candidate.is_file():
                    wallet_path = candidate.resolve(strict=False)

            if wallet_path:
                wallet_dir = self.extract_wallet(wallet_path)
                os.environ["TNS_ADMIN"] = str(wallet_dir)
                kwargs["config_dir"] = str(wallet_dir)
                # for item in wallet_dir.iterdir():
                #    print(item)

                if not self.validate_dsn_alias(wallet_dir, self.dsn_string):
                    raise ValueError(f"DSN alias '{self.dsn_string}' not found in wallet tnsnames.ora.")

                if oracledb.is_thin_mode():
                    oracledb.defaults.thick_mode_dsn_passthrough = False
                    params = oracledb.ConnectParams(
                        config_dir=str(wallet_dir),
                        wallet_location=str(wallet_dir),
                    )
                    params.parse_connect_string(self.dsn_string)
                    kwargs["params"] = params
                    kwargs.pop("dsn", None)
            else:
                tns_admin = os.environ.get("TNS_ADMIN")
                if tns_admin:
                    kwargs["config_dir"] = str(tns_admin)
            # Handle dsn prefixed with 'ldap:' - resolve into full LDAP DSN
            if self.dsn_string and self.dsn_string.lower().startswith("ldap:"):
                alias = self.dsn_string[5:]
                sqlnet_path = Path(
                    kwargs.get("config_dir", os.environ.get("TNS_ADMIN", r"C:\oracle\tns_admin"))) / "sqlnet.ora"
                ldap_ora = Path(
                    kwargs.get("config_dir", os.environ.get("TNS_ADMIN", r"C:\oracle\tns_admin"))) / "ldap.ora"

                def extract_default_admin_context(path: Path) -> str:
                    if path.exists():
                        match = re.search(r"DEFAULT_ADMIN_CONTEXT\s*=\s*\"?([\w=,. -]+)\"?", path.read_text(),
                                          re.IGNORECASE)
                        return match.group(1).strip() if match else ""
                    return ""

                def extract_ldap_host(path: Path, fallback_text: str = "") -> str:
                    pattern = re.compile(r"DIRECTORY_SERVERS\s*=\s*\(([^):\s]+)", re.IGNORECASE)
                    if path.exists():
                        for line in path.read_text().splitlines():
                            match = pattern.search(line)
                            if match:
                                return match.group(1)
                    match = pattern.search(fallback_text)
                    return match.group(1) if match else ""

                fallback_sqlnet_text = sqlnet_path.read_text() if sqlnet_path.exists() else ""
                base_dn = extract_default_admin_context(sqlnet_path) or "dc=xgbu-ace,dc=com"
                ldap_host = extract_ldap_host(ldap_ora, fallback_sqlnet_text) or "xgbu-ace-api.appoci.oraclecorp.com"
                ldap_url = f"ldap://{ldap_host}/{alias},cn=OracleContext,{base_dn}"

                if self.verbose:
                    print(f"{INFO} DSN resolved from alias '{alias}' to full LDAP URL:\n  {ldap_url}\n")

                kwargs["dsn"] = ldap_url

            super().__init__(**kwargs)
            self.connection_succeeded = True

        except oracledb.DatabaseError as e:
            self.connection_succeeded = False
            raise self._translate_connection_error(e) from e

    def _translate_connection_error(self, error: oracledb.DatabaseError) -> Exception:
        """Return a more actionable OraTAPI error for common connection failures."""
        error_text = str(error)

        if "DPY-4027" in error_text:
            dsn_display = self.dsn_string or "<not supplied>"
            tns_admin = os.environ.get("TNS_ADMIN", "")
            config_dir = tns_admin or "<not set>"
            message = (
                "Unable to resolve the database connect identifier.\n"
                f"Connection DSN/TNS alias: {dsn_display}\n"
                f"TNS_ADMIN: {config_dir}\n"
                "OraTAPI is trying to connect using a TNS alias, but Oracle Net configuration is not available to "
                "this process.\n"
                "Set TNS_ADMIN to the directory containing tnsnames.ora, use a wallet-backed connection, or switch "
                "the saved DSN to an Easy Connect string.\n"
                "If you are running from PyCharm, add TNS_ADMIN to the Run/Debug configuration environment variables."
            )
            return DatabaseConnectionError(message)

        return error

    def extract_wallet(self, wallet_zip_path: Path) -> Path:
        """
        Extract the wallet ZIP file to a temporary directory and patch sqlnet.ora with actual (temp) path.

        Args:
            wallet_zip_path (Path): Path to the wallet ZIP file.

        Returns:
            Path: Path to the extracted temporary directory.
        """
        if not wallet_zip_path.is_file():
            raise FileNotFoundError(f"{CRITICAL} Wallet zip file not found: {wallet_zip_path}")

        temp_dir = Path(tempfile.mkdtemp(prefix="oracle_wallet_"))
        with zipfile.ZipFile(wallet_zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # Patch sqlnet.ora
        # Patch sqlnet.ora
        sqlnet_path = temp_dir / "sqlnet.ora"
        if sqlnet_path.exists():
            content = sqlnet_path.read_text()
            if "?/network/admin" in content:
                # We need to modify the contents of the extracted sqlnet.ora file, replacing the directory reference of
                # ?/network/admin to the temp_dir location. Unfortunately, couldn't get it working any other way.
                content = content.replace("?/network/admin", str(temp_dir).replace("\\", "/"))
                sqlnet_path.write_text(content)

                if self.verbose:
                    print(f"{INFO} Patched sqlnet.ora to use wallet directory:\n  {sqlnet_path}\n")

            # ✅ Print final contents for confirmation (optional)
            # print(f"{INFO} Final sqlnet.ora content:\n{'-'*40}\n{sqlnet_path.read_text()}\n{'-'*40}")

        return temp_dir

    @staticmethod
    def is_thick_mode() -> bool:
        """
        Returns whether the current session is using Oracle thick mode.

        :returns: True if using thick mode, False otherwise.
        """
        return not oracledb.is_thin_mode()

    @staticmethod
    def get_client_mode_info() -> str:
        """
        Returns a string indicating the Oracle client mode and platform details.

        :returns: A string with mode and library info if available.
        """
        mode = "Thick" if not oracledb.is_thin_mode() else "Thin"
        lib_hint = ""
        if mode == "Thick":
            import ctypes.util
            lib_hint = ctypes.util.find_library("clntsh") or "(library not found)"
        return f"{INFO} Oracle client mode: {mode} {lib_hint}"

    def run_test_query(self) -> None:
        """
        Runs a test SQL query to verify connectivity.
        """
        try:
            with self.cursor() as cursor:
                cursor.execute("SELECT 'Hello world!' FROM dual")
                result = cursor.fetchone()
                print(result[0])  # Expected "Hello world!"
        except oracledb.DatabaseError as e:
            print("Error executing test query:", e)

    def _tns_connect_string(self) -> str:
        """
        Returns the connection string for internal usage.
        """
        return f"{self.user}/{self.password}@{self.dsn_string}"

    def fetch_as_dicts(self, sql_query: str, bind_mappings: dict = None) -> list[dict]:
        """
        Executes a SELECT query with optional binds and returns rows as a list of dictionaries.
        """
        try:
            with self.cursor() as cursor:
                if bind_mappings:
                    cursor.execute(sql_query, bind_mappings)
                else:
                    cursor.execute(sql_query)
                rows = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]
                return [dict(zip(column_names, row)) for row in rows]
        except oracledb.DatabaseError as e:
            print(f'Error executing SQL SELECT statement: {sql_query}')
            raise

    def fetch_as_lists(self, sql_query: str, bind_mappings: dict = None) -> list[list]:
        """
        Executes a SELECT query with optional binds and returns rows as a list of lists.
        """
        try:
            with self.cursor() as cursor:
                if bind_mappings:
                    cursor.execute(sql_query, bind_mappings)
                else:
                    cursor.execute(sql_query)
                rows = cursor.fetchall()
                return [list(row) for row in rows]
        except oracledb.DatabaseError as e:
            print(f'{CRITICAL} Error executing SQL SELECT statement: {sql_query}')
            raise

    def run_plsql_block(
            self,
            plsql_block: str,
            bind_mappings: dict = None
    ) -> int | None:
        """
        Executes an anonymous PL/SQL block in the database, optionally with bind variables.

        If a `b_status` bind variable is present:
          - If `exception_on_error` is True and `b_status` is non-zero, a DatabaseError is raised.
          - Otherwise, the value of `b_status` is returned as an integer.

        Args:
            plsql_block (str): The anonymous PL/SQL code to be executed. E.g.:
                \"\"\"
                BEGIN
                    ...
                END;
                \"\"\"
            bind_mappings (dict, optional): Dictionary of bind variables to pass to the PL/SQL block.
            exception_on_error (bool): Whether to raise an exception on a non-zero `b_status`. Defaults to True.

        Returns:
            int | None: Returns the value of `b_status` if present, or None otherwise.

        Raises:
            oracledb.DatabaseError: If execution fails or if b_status is non-zero and exception_on_error is True.

        Example:
            block = '''
            BEGIN
                INSERT INTO employees (employee_id, first_name, last_name, department_id)
                VALUES (:emp_id, :f_name, :l_name, :dept_id);
            END;
            '''

            binds = {
                "emp_id": 999,
                "f_name": "New",
                "l_name": "Hire",
                "dept_id": 10
            }

            db_session.run_plsql_block(plsql_block=block, bind_mappings=binds)
        """

        with self.cursor() as cursor:
            # Copy to avoid mutating caller's bind_mappings
            actual_binds = dict(bind_mappings) if bind_mappings else {}

            # Register b_status as OUT bind
            if "b_status" in actual_binds:
                b_status_var = cursor.var(int)
                actual_binds["b_status"] = b_status_var
            else:
                b_status_var = None

            cursor.execute(plsql_block, actual_binds)
            self.commit()

            if b_status_var:
                status = int(b_status_var.getvalue())

                # Optionally update original bind_mappings (if provided)
                if bind_mappings is not None:
                    bind_mappings["b_status"] = status

            if status != 0:
                raise PLSQLScriptError(f'PLSQL block:\n"{plsql_block}"\nfailed with status {status}.')

    def commit_changes(self):
        """Commit outstanding changes to the database."""
        self.commit()

    def execute(self, sql: str, bind_vars: dict = None, auto_commit: bool = True) -> None:
        """Simple wrapper for executing DML SQL (INSERT, UPDATE, DELETE)."""
        with self.cursor() as cursor:
            cursor.execute(sql, bind_vars or {})
            if auto_commit:
                self.commit()

    def dict_sql_dataset(self, sql: str, bind_vars: dict = None) -> list[dict]:
        """
        Executes a SQL SELECT statement and returns the result as a list of dictionaries.

        Each dictionary in the returned list represents a single row, with column names
        as keys and corresponding column values as values.

        :param sql: SQL SELECT statement to execute.
        :type sql: str
        :param bind_vars: Dictionary of bind variables for the SQL statement.
        :type bind_vars: dict[str, Any] | None
        :return: List of rows represented as dictionaries.
        :rtype: list[dict[str, Any]]

        :example:
            sql = "SELECT employee_id, first_name FROM employees WHERE department_id = :dept"
            bind_vars = {"dept": 10}
            dict_sql_dataset(sql, bind_vars)
            [{'EMPLOYEE_ID': 100, 'FIRST_NAME': 'Steven'}, {'EMPLOYEE_ID': 101, 'FIRST_NAME': 'Neena'}]
        """
        bind_vars = bind_vars or {}
        return self.fetch_as_dicts(sql_query=sql, bind_mappings=bind_vars)

    def column_sql_dataset(self, sql: str, bind_vars: dict = None) -> list[Any]:
        """
        Executes a SQL SELECT and returns a simplified list of column values.

        If the query returns exactly one column, the result is flattened to a 1D list.
        Otherwise, a list of rows (as lists) is returned.

        :param sql: SQL SELECT statement to execute.
        :type sql: str
        :param bind_vars: Dictionary of bind variables for the SQL query.
        :type bind_vars: dict[str, Any] | None
        :return: A list of values if a single column is returned, else a list of rows (each as a list).
        :rtype: list[Any] | list[list[Any]]

        :example:
            column_sql_dataset("select employee_id from employees where department_id = :dept", {"dept": 10})
            [100, 101, 102]

            column_sql_dataset("select first_name, last_name from employees where department_id = :dept", {"dept": 10})
            [["Steven", "King"], ["Neena", "Kochhar"]]
        """
        bind_vars = bind_vars or {}
        rows = self.fetch_as_lists(sql_query=sql, bind_mappings=bind_vars)
        return [r[0] for r in rows] if rows and len(rows[0]) == 1 else rows

    def validate_dsn_alias(self, wallet_dir: Path, alias: str) -> bool:
        """
        Validates whether a given DSN alias exists in the extracted wallet's tnsnames.ora file.

        Args:
            wallet_dir (Path): Path to the provided wallet directory (wallet_dir).
            alias (str): The DSN alias to look for (case-insensitive).

        Returns:
            bool: True if alias exists, False otherwise.
        """
        tns_path = wallet_dir / "tnsnames.ora"
        if not tns_path.exists():
            print(f"{CRITICAL} No tnsnames.ora found in wallet directory: {wallet_dir}")
            return False

        try:
            lines = tns_path.read_text(encoding="utf-8").splitlines()
            aliases = [
                line.split("=")[0].strip().lower()
                for line in lines
                if "=" in line and not line.lstrip().startswith("(")
            ]
            if alias.lower() in aliases:
                if self.verbose:
                    print(f"{INFO} Alias '{alias}' found in tnsnames.ora.")
                return True
            else:
                if self.verbose:
                    print(f"{CRITICAL} Alias '{alias}' not found in tnsnames.ora.")
                return False
        except Exception as e:
            print(f"{ERROR} Error reading or parsing tnsnames.ora: {e}")
            return False

    def __del__(self):
        try:
            if self.connection_succeeded:
                self.close()
        except oracledb.DatabaseError as e:
            print("Error closing the database connection:", e)


def _looks_like_instant_client(path: str) -> bool:
    """
    Checks if the given path contains expected Instant Client files for the current platform.
    """
    expected_files = {
        "Windows": "oci.dll",
        "Linux": "libclntsh.so",
        "Darwin": "libclntsh.dylib"
    }
    platform_key = platform.system()
    marker = expected_files.get(platform_key)

    if not marker:
        print(f"{WARNING} Unsupported platform: {platform_key}")
        return False

    return os.path.isfile(os.path.join(path, marker))


def try_init_thick_mode(verbose:bool = False, lib_dir: Path = None) -> bool:
    client_dir = os.getenv("ORACLE_IC_HOME") if lib_dir is None else lib_dir
    if client_dir and os.path.isdir(client_dir) and _looks_like_instant_client(client_dir):
        source = "ORACLE_IC_HOME"
    else:
        fallback_dir = str(resolve_path("oracle_client"))
        if os.path.isdir(fallback_dir) and _looks_like_instant_client(fallback_dir):
            client_dir = fallback_dir
            source = "active profile oracle_client"
        else:
            if verbose:
                print(f"{INFO} No valid Oracle Instant Client found — falling back to thin mode")
            return False

    # ✅ SET TNS_ADMIN *BEFORE* initializing thick mode
    if "TNS_ADMIN" not in os.environ:
        os.environ["TNS_ADMIN"] = "C:\\oracle\\tns_admin"

    try:
        oracledb.init_oracle_client(lib_dir=client_dir)
        if verbose:
            print(f"{INFO} Thick mode initialised from {source}: {client_dir}")
        return True
    except Exception as e:
        print(f"{WARNING} Failed to initialise thick mode from {source}: {e}")
        return False



if __name__ == "__main__":
    # Example usage
    _dsn = os.getenv("DB_DSN", "localhost:1245/UTPLSQL")
    username = os.getenv("DB_USER", "example_user")
    password = os.getenv("DB_PASS", "example_pass")

    if try_init_thick_mode():
        print("Initializing thick mode")
    else:
        print("Initializing thin mode")
    exit(0)

    db_session = DBSession(dsn=_dsn, user=username, password=password)
    db_session.run_test_query()

    # Running an anonymous PL/SQL block
    block = """
    BEGIN
        DBMS_OUTPUT.PUT_LINE('Hello from anonymous block!');
    END;
    """
    db_session.run_plsql_block(plsql_block=block)

    # Example of using bind variables
    block_with_binds = """
    BEGIN
        INSERT INTO employees (employee_id, first_name, last_name, department_id)
        VALUES (:emp_id, :f_name, :l_name, :dept_id);
    END;
    """
    binds = {
        "emp_id": 999,
        "f_name": "New",
        "l_name": "Hire",
        "dept_id": 10
    }

    db_session.run_plsql_block(plsql_block=block_with_binds, bind_mappings=binds)
