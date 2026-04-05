__author__ = "Clive Bostock"
__date__ = "2024-11-09"
__description__ = "Main controller to parse command-line arguments and coordinate API generation flow."
from controller import __version__
import copy
import sys
import time

from model.tapi_generator import ApiGenerator, inject_values
from model.utplsql_generator import UtPLSQLGenerator
from lib.config_mgr import ConfigManager, load_config
from lib.session_manager import DBSession
from lib.fsutils import (
    active_profile_home,
    active_profile_name,
    available_profiles,
    configured_active_profile_name,
    missing_runtime_paths,
    resolve_default_path,
    resolve_path,
    runtime_home,
)
from lib.app_utils import current_timestamp, format_elapsed_time
from lib.user_security import UserSecurity
from view.interactions import Interactions, MsgLvl, MissingParameterError
from pathlib import Path
from model.ora_tapi_csv import CSVManager
from model.framework_errors import UnsupportedOption
from lib.app_utils import get_latest_dist_url, get_latest_version
from lib.framework_errors import DatabaseConnectionError
from packaging.version import Version

CONFIG_LOCATION = Path("resources") / "config"

RUN_ID = int(time.time())
prog_bin = Path(__file__).resolve().parent

PROG_NAME = Path(__file__).name

VALID_API_TYPES = ["insert", "select", "update", "delete", "upsert", "merge"]


def resolve_runtime_relative_path(path_name: Path) -> Path:
    expanded_path = Path(path_name).expanduser()
    if expanded_path.is_absolute():
        return expanded_path
    return runtime_home() / expanded_path


def print_runtime_initialisation_message() -> None:
    configured_profile = configured_active_profile_name()
    if not configured_profile:
        print("ERROR: No active OraTAPI profile is configured.")
        profiles = available_profiles()
        if profiles:
            print("\nAvailable profiles:")
            for profile_name in profiles:
                print(f"  - {profile_name}")
            print("\nPlease activate one of the existing profiles with:")
            print("  Linux / macOS:")
            print("    ./bin/profile_mgr.sh -a <profile-name>")
            print("  Windows:")
            print("    .\\bin\\profile_mgr.ps1 -a <profile-name>")
        else:
            print("\nNo OraTAPI profiles were found under ~/OraTAPI/configs.")
            print("Please run one of the following commands to create and activate the built-in profiles:")
            print("  Linux / macOS:")
            print("    ./bin/quick_config.sh -t <template-category>")
            print("  Windows:")
            print("    .\\bin\\quick_config.ps1 -t <template-category>")
            print("\nValid template categories: basic, liquibase, logger, llogger")
        return

    missing_paths = missing_runtime_paths()
    print(f"ERROR: OraTAPI runtime files have not been initialised for profile '{configured_profile}'.")
    print(f"Active profile directory: {active_profile_home()}")
    print("\nMissing runtime files include:")
    for missing_path in missing_paths[:8]:
        print(f"  - {missing_path}")
    if len(missing_paths) > 8:
        print(f"  - ... and {len(missing_paths) - 8} more")

    print("\nPlease run one of the following commands to initialise the runtime files:")
    print("  Linux / macOS:")
    print("    ./bin/quick_config.sh -t <template-category>")
    print("  Windows:")
    print("    .\\bin\\quick_config.ps1 -t <template-category>")
    print("\nValid template categories: basic, liquibase, logger, llogger")
    print("\n1.  basic     - No Liquibase directives or logging")
    print("2.  liquibase - Generated code includes Liquibase directives")
    print("3.  logger    - Generated PL/SQL includes logger logging calls for logging parameter values etc.")
    print("4.  llogger   - Include Liquibase and logger logging (2 + 3)")
    print("\nNOTE: For options 3 and 4, you must have the logger utility deployed to the database.")


def help_requested(argv: list[str] | None = None) -> bool:
    args = sys.argv[1:] if argv is None else argv
    return "-h" in args or "--help" in args


def warn_on_default_profile_identity(view: Interactions, config_file_path: Path) -> None:
    sample_config_path = resolve_default_path(Path("resources") / "config" / "samples" / "OraTAPI.ini.sample")
    if not sample_config_path.exists():
        return

    active_config = load_config(config_file_path)
    sample_config = load_config(sample_config_path)
    current_profile = active_profile_name()
    default_matches = []

    checks = (
        ("project", "default_app_name", "project.default_app_name"),
        ("copyright", "company_name", "copyright.company_name"),
    )

    for section, option, label in checks:
        if not active_config.has_option(section, option) or not sample_config.has_option(section, option):
            continue
        if active_config.get(section, option).strip() == sample_config.get(section, option).strip():
            default_matches.append(label)

    if default_matches:
        matched_settings = ", ".join(default_matches)
        view.print_console(
            msg_level=MsgLvl.warning,
            text=(
                f"Profile '{current_profile}' is still using the shipped default values for {matched_settings}. "
                f"Code is being generated with the defaults. Consider updating these settings for the "
                f"'{current_profile}' profile configuration."
            ),
        )


class CodeManager:
    """PLSQL code generation manager class"""
    def __init__(self, trace: bool = False):
        if not help_requested() and (not configured_active_profile_name() or missing_runtime_paths()):
            print_runtime_initialisation_message()
            exit(1)

        config_file_path = resolve_path(CONFIG_LOCATION / 'OraTAPI.ini')
        if not config_file_path.exists():
            print(f'ERROR: Unable to locate config file: {config_file_path}')
            print(f'This is possibly due to an incomplete installation. Did you run the quick config command?')
            exit(1)
        try:
            self.view = Interactions(controller=self, config_file_path=config_file_path)
        except MissingParameterError as e:
            print(
                f"\n[ERROR] {e}\n\nRequired:\n\n    <ora_tapi> -c CONN_NAME\n    or\n    <ora_tapi> -d "
                f"DSN -u DB_USERNAME -p DB_PASSWORD\n"

                f"\nYou must specify at least one of the two above to connect to a database, along with any other "
                f"optional arguments.\n\nDepending on your platform, you should replace <ora_tapi> with either of "
                f"ora_tapi.sh (Linux/macOS/Git Bash) or\nora_tapi.ps1/ora_tapi (Windows PowerShell).\n"
                f"\nUse -h for help."
            )
            exit(1)  # Exit with an error status
        args_dict = self.view.args_dict

        options_dict = copy.deepcopy(args_dict)
        config_manager = ConfigManager(config_file_path=config_file_path)
        options_dict["api_surface"] = config_manager.config_value(
            config_section="api_controls",
            config_key="api_surface",
            default="view"
        )

        exec_start_timestamp = current_timestamp()
        self.view.print_console(text=f'{PROG_NAME}: Version: {__version__}',
                                msg_level=MsgLvl.highlight)
        self.view.print_console(text=f'{PROG_NAME}: Run Id: {RUN_ID} started at: {exec_start_timestamp}',
                                msg_level=MsgLvl.highlight)
        epoc_start_ts = int(time.time())
        self.view.print_console(text=f'{PROG_NAME}: Command line parameters:-',
                                msg_level=MsgLvl.highlight)
        self.view.print_console(msg_level=MsgLvl.highlight, text=f"=" * 79)
        for key in sorted(options_dict.keys()):  # Sort the keys
            value = options_dict[key]
            if key == 'db_password':
                value = '***************'
            elif isinstance(value, list):
                value = ', '.join(str(item) for item in value)
            self.view.print_console(msg_level=MsgLvl.highlight, text=f"{key:<40} = {value}")
        self.view.print_console(msg_level=MsgLvl.highlight, text=f"=" * 79)


        options_dict["config_file_path"] = config_file_path
        self.options_dict = options_dict
        self.options_dict["version"] = __version__
        self.api_types = self.validate_api_types(options_dict.get('api_types'))
        self.config_file_path = options_dict["config_file_path"]
        self.tapi_author = options_dict['tapi_author']
        self.db_username = options_dict['db_username']
        self.db_password = options_dict['db_password']
        self.package_owner:str = options_dict['package_owner']
        self.package_owner_lc = self.package_owner.lower()
        self.view_owner:str = options_dict['view_owner']
        self.view_owner_lc = self.view_owner.lower()
        self.trigger_owner:str = options_dict['trigger_owner']
        self.trigger_owner_lc = self.trigger_owner .lower()
        self.dsn = options_dict['dsn']
        self.table_owner = str(options_dict['table_owner']).upper()
        self.table_owner_lc = self.table_owner.lower()
        self.table_names = options_dict['table_names']
        self.conn_name = options_dict['conn_name']
        self.staging_dir = Path(options_dict['staging_dir'])
        self.ut_staging_dir = Path(options_dict['ut_staging_dir'])

        self.trace = trace
        self.runtime_home = active_profile_home()

        self.config_manager = config_manager
        warn_on_default_profile_identity(view=self.view, config_file_path=config_file_path)
        ora_tapi_csv_dir = self.config_manager.config_value(config_section='file_controls',
                                                    config_key='ora_tapi_csv_dir',
                                                    default="resources/config")
        ora_tapi_csv_dir = resolve_path(ora_tapi_csv_dir)

        self.csv_manager = CSVManager(csv_pathname=ora_tapi_csv_dir / 'OraTAPI.csv', config_file_path=config_file_path)

        self.ora_tapi_version = __version__

        self.skip_on_missing_table = self.config_manager.bool_config_value(config_section='behaviour',
                                                                           config_key='skip_on_missing_table')

        check_github_for_updates = self.config_manager.bool_config_value(config_section='behaviour',
                                                                         config_key='check_github_for_updates',
                                                                         default=True)

        self.col_auto_maintain_method = self.config_manager.config_value(config_section='api_controls',
                                                                         config_key='col_auto_maintain_method')

        self.spec_dir = Path(self.config_manager.config_value(config_section='file_controls',
                                                              config_key='spec_dir'))

        self.body_dir = Path(self.config_manager.config_value(config_section='file_controls',
                                                              config_key='body_dir'))

        self.trigger_dir = Path(self.config_manager.config_value(config_section='file_controls',
                                                                 config_key='trigger_dir'))

        self.view_dir = Path(self.config_manager.config_value(config_section='file_controls',
                                                              config_key='view_dir'))

        self.body_file_ext = self.config_manager.config_value(config_section='file_controls',
                                                              config_key='body_file_ext')

        self.spec_file_ext = self.config_manager.config_value(config_section='file_controls',
                                                              config_key='spec_file_ext')

        self.tapi_pkg_name_prefix = self.config_manager.config_value(config_section='api_controls',
                                                                     config_key='tapi_pkg_name_prefix',
                                                                     default='')

        self.tapi_pkg_name_postfix = self.config_manager.config_value(config_section='api_controls',
                                                                      config_key='tapi_pkg_name_postfix',
                                                                      default='_tapi')

        self.ut_pkg_name_prefix = self.config_manager.config_value(config_section='ut_controls',
                                                                   config_key='ut_pkg_name_prefix',
                                                                   default='')

        self.ut_pkg_name_postfix = self.config_manager.config_value(config_section='ut_controls',
                                                                    config_key='ut_pkg_name_postfix',
                                                                    default='_tapi')

        self.enable_ut_code_generation = self.config_manager.bool_config_value(config_section='ut_controls',
                                                                               config_key='enable_ut_code_generation',
                                                                               default=False)

        enable_tapis_when_ut_enabled = self.config_manager.bool_config_value(config_section='behaviour',
                                                                              config_key='enable_tapis_when_ut_enabled',
                                                                              default=False)

        self.skip_on_missing_pk = self.config_manager.bool_config_value(config_section='behaviour',
                                                                               config_key='skip_on_missing_pk',
                                                                               default=True)

        if self.enable_ut_code_generation and  enable_tapis_when_ut_enabled:
            self.enable_tapi_generation = True
        elif self.enable_ut_code_generation and not enable_tapis_when_ut_enabled:
            self.enable_tapi_generation = False
        elif not self.enable_ut_code_generation:
            self.enable_tapi_generation = True
        else:
            self.enable_tapi_generation = False

        if self.col_auto_maintain_method == 'expression':
            self.view.print_console(msg_level=MsgLvl.info, text=f"Auto-maintained columns are maintained by column expressions.")
            self.view.print_console(msg_level=MsgLvl.info, text=f"Loading with auto-maintained column expressions")
        elif self.col_auto_maintain_method == 'trigger':
            self.view.print_console(msg_level=MsgLvl.info, text=f"Auto-maintained columns are maintained by column trigger.")

        self.staging_dir = resolve_runtime_relative_path(self.staging_dir)
        self.ut_staging_dir = resolve_runtime_relative_path(self.ut_staging_dir)

        if not self.staging_dir.exists():
            self.view.print_console(msg_level=MsgLvl.info, text=f"Creating staging root directory: {self.staging_dir}")
            self.staging_dir.mkdir(parents=True, exist_ok=True)

        if not self.ut_staging_dir.exists() and self.enable_ut_code_generation:
            self.view.print_console(msg_level=MsgLvl.info, text=f"Creating unit test staging root directory: {self.ut_staging_dir}")
            self.ut_staging_dir.mkdir(parents=True, exist_ok=True)

        if not self.staging_dir.is_dir():
            self.view.print_console(msg_level=MsgLvl.error, text=f'TAPI staging pathname provide, "{self.staging_dir}", is not a directory - bailing out!')
            exit(0)

        if not self.ut_staging_dir.is_dir() and self.enable_ut_code_generation:
            self.view.print_console(msg_level=MsgLvl.error, text=f'Unit test staging pathname provide, "{self.staging_dir}", is not a directory - bailing out!')
            exit(0)

        if self.spec_dir == self.body_dir and self.spec_file_ext == self.body_file_ext:
            self.view.print_console(msg_level=MsgLvl.error, text=f'Conflicting OraTAPI.ini properties. The spec_dir and body_dir must be distinct when spec_file_ext and body_file_ext are the same!')
            exit(0)

        for directory in (self.spec_dir, self.body_dir, self.trigger_dir, self.view_dir):
            dir_path = self.staging_dir / directory
            if directory and not dir_path.exists():
                self.view.print_console(msg_level=MsgLvl.info, text=f"Creating staging sub directory: {dir_path}")
                dir_path.mkdir(parents=False, exist_ok=True)

        if self.enable_ut_code_generation:
            for directory in (self.spec_dir, self.body_dir):
                dir_path = self.ut_staging_dir / directory
                if directory and not dir_path.exists():
                    self.view.print_console(msg_level=MsgLvl.info, text=f"Creating ut staging sub directory: {dir_path}")
                    dir_path.mkdir(parents=False, exist_ok=True)

        # Process table names as a list
        self.table_names_list = self.table_names

        user_security = UserSecurity(project_identifier="OraTAPI")
        wallet_zip_path = ""
        if self.conn_name:
            self.db_username, self.db_password, self.dsn \
                = user_security.named_connection_creds(connection_name=self.conn_name)
            wallet_zip_path = user_security.connection_property(connection_name=self.conn_name,
                                                                property_key="wallet_zip_path",
                                                                default_value="")

        # Database session setup
        try:
            self.db_session: DBSession = DBSession(dsn=self.dsn, user=self.db_username, password=self.db_password,
                                                   wallet_zip_path=wallet_zip_path)
        except DatabaseConnectionError as e:
            self.view.print_console(msg_level=MsgLvl.error, text=str(e))
            exit(1)
        self.view.print_console(msg_level=MsgLvl.success, text="Database session established successfully.")

        if not self.schema_exists(schema_name=self.table_owner):
            self.view.print_console(msg_level=MsgLvl.error,
                                    text=f"Cannot find table schema by the name of: {self.table_owner}")
            exit(0)

        if not self.table_schema_has_tables():
            self.view.print_console(msg_level=MsgLvl.error,
                                    text=f"The nominated table owner schema, {self.table_owner}, has no tables!")
            exit(0)

        # Validate table names and process. We get a dictionary of results returned.
        results = self.process_table_names()

        self.view.print_console(msg_level=MsgLvl.highlight, text=f"Results stats follow, as governed by OraTAPI.csv rules.")
        self.view.print_console(msg_level=MsgLvl.highlight, text=f"=" * 79)
        self.view.print_console(text=f'Packages generated: {results["packages_generated"]}',
                                msg_level=MsgLvl.success)

        self.view.print_console(text=f'  Packages skipped: {results["packages_skipped"]}',
                                msg_level=MsgLvl.warning)

        self.view.print_console(text=f'UT packages generated: {results["ut_packages_generated"]}',
                                msg_level=MsgLvl.success)

        self.view.print_console(text=f'  UT packages skipped: {results["ut_packages_skipped"]}',
                                msg_level=MsgLvl.warning)

        self.view.print_console(text=f'   Views generated: {results["views_generated"]}',
                                msg_level=MsgLvl.success)

        self.view.print_console(text=f'     Views skipped: {results["views_skipped"]}',
                                msg_level=MsgLvl.warning)

        self.view.print_console(text=f'Triggers generated: {results["triggers_generated"]}',
                                msg_level=MsgLvl.success)

        self.view.print_console(text=f'  Triggers skipped: {results["triggers_skipped"]}',
                                msg_level=MsgLvl.warning)
        self.view.print_console(msg_level=MsgLvl.highlight, text=f"=" * 79)
        if check_github_for_updates:
            latest_version = get_latest_version(repo_owner='avalon60', repo_name='OraTAPI')
            latest_url = get_latest_dist_url(repo_owner='avalon60', repo_name='OraTAPI')
            if Version(latest_version) > Version(__version__):
                self.view.print_console(text=f'A newer version, {latest_version}, of OraTAPI is available.',
                                        msg_level=MsgLvl.warning)
                self.view.print_console(text=f'Run the update oratapi command to download and install.',
                                        msg_level=MsgLvl.warning)

        exec_end_timestamp = current_timestamp()
        epoc_end_ts = int(time.time())
        self.view.print_console(text=f'{PROG_NAME}: Run Id: {RUN_ID} completed at: {exec_end_timestamp}',
                                msg_level=MsgLvl.highlight)
        elapsed_time = format_elapsed_time(start_ts=epoc_start_ts, end_ts=epoc_end_ts)
        self.view.print_console(text=f'Elapsed time: {elapsed_time}',
                                msg_level=MsgLvl.highlight)


    @staticmethod
    def validate_api_types(api_types: list[str]) -> list[str]:
        """
        Validate and parse the API types provided as a command-line argument.

        :param api_types: str, Comma-separated API types
        :rtype: list[str]
        :returns: List of validated API types
        :raises ValueError: If an invalid API type is provided
        """
        if not api_types:
            return []

        invalid_types = [api for api in api_types if api not in VALID_API_TYPES]
        if invalid_types:
            raise ValueError(f"Invalid API types specified: {', '.join(invalid_types)}. "
                             f"Valid options are: {', '.join(VALID_API_TYPES)}")
        return api_types

    def process_table_names(self) -> dict:
        """
        Here we process the provided table names, ensuring they exist in the database.
        """

        table_list = []
        if self.table_names_list[0] == '%':
            table_list_sql = 'select table_name from all_tables where owner = upper(:schema_name)'
            binds = {'schema_name': self.table_owner}
            result_list = self.db_session.fetch_as_lists(sql_query=table_list_sql, bind_mappings=binds)
            for row in result_list:
                table_list.append(row[0])
            self.table_names_list = table_list

        table_count = len(self.table_names_list)
        self.view.print_console(text=f'{table_count} tables selected.', msg_level=MsgLvl.info)
        packages_skipped = 0
        views_skipped = 0
        triggers_skipped = 0

        packages_generated = 0
        views_generated = 0
        triggers_generated = 0
        ut_packages_generated = 0
        ut_packages_skipped = 0

        schemas = {"Package Owner": self.package_owner,
                   "View Owner": self.view_owner,
                   "Trigger Owner": self.trigger_owner}

        for descriptor, schema_name in schemas.items():  # Use .items() to iterate over key-value pairs
            if not self.schema_exists(schema_name=schema_name):
                self.view.print_console(
                    text=f'The {descriptor} schema ("{schema_name}") was not found in this database.',
                    msg_level=MsgLvl.warning
                )

        for table_name in self.table_names_list:
            package_enabled = self.csv_manager.csv_dict_property(self.table_owner_lc, table_name=table_name,
                                                                 property_selector='package')
            view_enabled = self.csv_manager.csv_dict_property(self.table_owner_lc, table_name=table_name,
                                                                 property_selector='view')
            trigger_enabled = self.csv_manager.csv_dict_property(self.table_owner_lc, table_name=table_name,
                                                                 property_selector='trigger')

            exists_status = self.check_table_exists(schema_name=self.table_owner, table_name=table_name)
            if not exists_status and self.skip_on_missing_table:
                self.view.print_console(text=f'Table {self.table_owner.lower()}.{table_name} does not exist - skipping!',
                                        msg_level=MsgLvl.warning)
            elif not exists_status and not self.skip_on_missing_table:
                self.view.print_console(text=f'Table {self.table_owner.lower()}.{table_name} does not exist - bailing out!',
                                        msg_level=MsgLvl.error)
                exit(1)
            elif not self.table_has_pk(table_name=table_name) and self.skip_on_missing_pk:
                self.view.print_console(text=f'Table {self.table_owner.lower()}.{table_name} has no primary key - skipping!',
                                        msg_level=MsgLvl.warning)
            else:
                if package_enabled and self.enable_tapi_generation:
                    self.generate_api_for_table(table_name)
                    packages_generated += 1
                else:
                    packages_skipped += 1
                if view_enabled and self.enable_tapi_generation:
                    self.generate_views_for_table(table_name)
                    views_generated += 1
                else:
                    views_skipped += 1
                if trigger_enabled and self.enable_tapi_generation:
                    self.generate_triggers_for_table(table_name)
                    triggers_generated += 1
                else:
                    triggers_skipped += 1

                if self.enable_ut_code_generation and package_enabled:
                    self.generate_ut_for_table(table_name)
                    ut_packages_generated += 1
                else:
                    ut_packages_skipped += 1


        result = {
            "packages_generated": packages_generated,
            "packages_skipped": packages_skipped,
            "ut_packages_generated": ut_packages_generated,
            "ut_packages_skipped": ut_packages_skipped,
            "views_generated": views_generated,
            "views_skipped": views_skipped,
            "triggers_generated": triggers_generated,
            "triggers_skipped": triggers_skipped,
        }

        return result

    def schema_exists(self, schema_name: str) -> bool:
        """
        Checks if a schema exists in the Oracle database.

        :param schema_name: The name of the schema to check.
        :return: True if the schema exists, False otherwise.
        """
        query = """SELECT COUNT(*)
                   FROM all_users
                   WHERE username = :schema_name"""

        try:
            # print(f"[TRACE] db_session is None? {self.db_session is None}")
            if self.db_session is not None:
                # some drivers have is_healthy(); if absent, this is harmless
                ok = getattr(self.db_session, "is_healthy", lambda: "unknown")()
                try:
                    who = self.db_session.cursor().execute(
                        "select user, sys_context('userenv','service_name') from dual"
                    ).fetchone()
                except Exception as e:
                    print(f"ERROR: cursor precheck failed: {type(e).__name__}: {e}")
                    raise

            with self.db_session.cursor() as cursor:
                if self.trace:
                    print(f"Executing query: {query}")
                    print(f"Parameters: schema_name={schema_name}")

                # Bind schema_name to the query
                cursor.execute(query, {"schema_name": schema_name.upper()})

                result = cursor.fetchone()
                schema_count = result[0] if result else 0

                return schema_count > 0
        except Exception as e:
            if self.trace:
                print(f"An error occurred: {e}")
            return False

    def table_schema_has_tables(self) -> bool:
        """
        Check if the nominated table owner schema actually has any tables.

        :return: True if the schema has one or more tables, otherwise False.
        :rtype: bool

        This method executes an SQL query to count the number of tables in the specified schema.
        It uses the `all_tables` view to retrieve the count of tables where the owner matches
        the given schema name. The query result is processed, and if the count is greater than 0,
        the method returns True, indicating that the schema contains tables.

        Example SQL Query:
            select count(*) from all_tables where owner = upper(:schema_name)

        Raises:
            Exception: If the database query fails or if the connection is not established.
        """
        count_tables_sql = 'select count(*) from all_tables where owner = upper(:schema_name)'
        binds = {'schema_name': self.table_owner}
        result = self.db_session.fetch_as_lists(sql_query=count_tables_sql, bind_mappings=binds)
        table_count = result[0][0] if result else 0  # Fetch the count from the first row, first column
        if table_count > 0:
            return True
        else:
            return False

    def table_has_pk(self, table_name: str) -> bool:
        """
        Determine whether the specified table has a primary key.

        :param table_name: Name of the table to check.
        :type table_name: str

        :return: True if the table has a primary key defined, False otherwise.
        :rtype: bool

        This method executes an SQL query against the Oracle data dictionary view `all_constraints`
        to verify the existence of a primary key constraint for the given table within the specified schema.

        Example SQL Query:
            select count(*) from all_constraints
            where constraint_type = 'P'
              and owner = upper(:schema_name)
              and table_name = upper(:table_name)

        Raises:
            Exception: If the database query fails or if the connection is not established.
        """
        pk_check_sql = """
            select count(*) from all_constraints
            where constraint_type = 'P'
              and owner = upper(:schema_name)
              and table_name = upper(:table_name)
        """
        binds = {'schema_name': self.table_owner, 'table_name': table_name}
        result = self.db_session.fetch_as_lists(sql_query=pk_check_sql, bind_mappings=binds)
        pk_count = result[0][0] if result else 0  # Fetch the count from the first row, first column

        return pk_count > 0

    def generate_api_for_table(self, table_name: str):
        """
        Generate APIs for a specified table.

        :param table_name: str, The table name to generate APIs for.
        """
        table_name_lc = table_name.lower()
        api_controller = ApiGenerator(
            database_session=self.db_session,
            table_owner=self.table_owner,
            table_name=table_name,
            config_manager=self.config_manager,
            options_dict=self.options_dict,
            trace=self.trace
        )

        if self.col_auto_maintain_method == 'expression':
            expressions_messages = api_controller.load_column_expressions()
            for message in expressions_messages:
                self.view.print_console(msg_level=MsgLvl.warning, text=message)

        elif self.col_auto_maintain_method == 'trigger':
            pass
        else:
            error_text = f"Invalid auto_maintain_method: {self.col_auto_maintain_method}"
            raise UnsupportedOption(message=error_text)

        self.view.print_console(msg_level=MsgLvl.info, text=f"    Generating TAPI package for table: {table_name_lc.upper()}")

        table_domain    = table_name[:table_name.find("_")]
        table_domain_lc = table_name[:table_name.find("_")].lower()
        path_dict = {"table_domain": table_domain, "table_domain_lc": table_domain_lc}

        staging_dir = str(self.staging_dir)
        staging_dir = Path(inject_values(substitutions=path_dict, target_string=staging_dir))

        staging_realpath = staging_dir.resolve()

        package_spec_code = api_controller.gen_package_spec()
        spec_file_name = f"{self.tapi_pkg_name_prefix}{table_name_lc}{self.tapi_pkg_name_postfix }{self.spec_file_ext}"
        self.view.write_file(staging_dir=staging_realpath, directory=self.spec_dir, file_name=spec_file_name,
                             code=package_spec_code)

        package_body_code = api_controller.gen_package_body()
        body_file_name = f"{self.tapi_pkg_name_prefix}{table_name_lc}{self.tapi_pkg_name_postfix}{self.body_file_ext}"
        self.view.write_file(staging_dir=staging_realpath, directory=self.body_dir, file_name=body_file_name,
                             code=package_body_code)

    def generate_ut_for_table(self, table_name: str):
        """
        Generate ut package for a specified table.

        :param table_name: str, The table name to generate unit test package for.
        """
        table_name_lc = table_name.lower()
        ut_controller = UtPLSQLGenerator(
            database_session=self.db_session,
            table_owner=self.table_owner,
            table_name=table_name,
            config_manager=self.config_manager,
            options_dict=self.options_dict,
            trace=self.trace
        )

        table_domain = table_name[:table_name.find("_")]
        table_domain_lc = table_name[:table_name.find("_")].lower()
        path_dict = {"table_domain": table_domain, "table_domain_lc": table_domain_lc}

        ut_staging_dir = str(self.ut_staging_dir)
        ut_staging_dir = Path(inject_values(substitutions=path_dict, target_string=ut_staging_dir))

        ut_staging_dir = ut_staging_dir.resolve()

        self.view.print_console(msg_level=MsgLvl.info, text=f"      Generating UT package for table: {table_name_lc.upper()}")
        staging_realpath = ut_staging_dir.resolve()

        package_spec_code = ut_controller.gen_package_spec()
        spec_file_name = f"{self.ut_pkg_name_prefix}{table_name_lc}{self.ut_pkg_name_postfix }{self.spec_file_ext}"
        self.view.write_file(staging_dir=staging_realpath, directory=self.spec_dir, file_name=spec_file_name,
                             code=package_spec_code)

        package_body_code = ut_controller.gen_package_body()
        body_file_name = f"{self.ut_pkg_name_prefix}{table_name_lc}{self.ut_pkg_name_postfix}{self.body_file_ext}"
        self.view.write_file(staging_dir=staging_realpath, directory=self.body_dir, file_name=body_file_name,
                             code=package_body_code)


    def generate_triggers_for_table(self, table_name: str):
        table_name_lc = table_name.lower()

        table_domain = table_name[:table_name.find("_")]
        table_domain_lc = table_name[:table_name.find("_")].lower()
        path_dict = {"table_domain": table_domain, "table_domain_lc": table_domain_lc}

        staging_dir = str(self.staging_dir)
        staging_dir = Path(inject_values(substitutions=path_dict, target_string=staging_dir))

        staging_dir = staging_dir.resolve()

        staging_realpath = staging_dir.resolve()


        staging_realpath = self.staging_dir.resolve()
        api_controller = ApiGenerator(
            database_session=self.db_session,
            table_owner=self.table_owner,
            table_name=table_name,
            config_manager=self.config_manager,
            options_dict=self.options_dict,
            trace=self.trace
        )
        triggers_dict = api_controller.gen_triggers()
        for trigger_file_name, code in triggers_dict.items():
            self.view.print_console(
                msg_level=MsgLvl.info,
                text=f"      Generating trigger script for trigger: "
                     f"{trigger_file_name.upper().replace('.SQL', '')} -> {table_name_lc.upper()}"
            )
            self.view.write_file(staging_dir=staging_realpath, directory=self.trigger_dir, file_name=trigger_file_name,
                                 code=code)


    def generate_views_for_table(self, table_name: str):
        table_name_lc = table_name.lower()

        table_domain = table_name[:table_name.find("_")]
        table_domain_lc = table_name[:table_name.find("_")].lower()

        path_dict = {"table_domain": table_domain, "table_domain_lc": table_domain_lc}

        staging_dir = str(self.staging_dir)
        staging_dir = Path(inject_values(substitutions=path_dict, target_string=staging_dir))

        staging_dir = staging_dir.resolve()

        staging_realpath = staging_dir.resolve()

        api_controller = ApiGenerator(
            database_session=self.db_session,
            table_owner=self.table_owner,
            table_name=table_name,
            config_manager=self.config_manager,
            options_dict=self.options_dict,
            trace=self.trace
        )

        views_dict = api_controller.gen_views()

        for view_file_name, code in views_dict.items():
            self.view.print_console(
                msg_level=MsgLvl.info,
                text=f"      Generating view script for view: "
                     f"{view_file_name.upper().replace('.SQL', '')} -> {table_name_lc.upper()}"
            )
            self.view.write_file(staging_dir=staging_realpath, directory=self.view_dir, file_name=view_file_name,
                                 code=code)

    def check_table_exists(self, schema_name, table_name) -> bool:
        """
        Check if a table exists in the specified schema.

        :param schema_name: str, The schema name
        :param table_name: str, The table name to check
        :returns: bool, True if the table exists, False otherwise
        """
        query = """
            select count(*)
            from all_tables
            where owner = :schema_name and table_name = :table_name
        """
        with self.db_session.cursor() as cursor:
            cursor.execute(query, {'schema_name': schema_name.upper(), 'table_name': table_name.upper()})
            result = cursor.fetchone()
            return result[0] > 0

def main():
    CodeManager()

if __name__ == "__main__":
    main()
