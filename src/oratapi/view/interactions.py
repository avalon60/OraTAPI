__author__ = "Clive Bostock"
__date__ = "2024-11-09"
__description__ = "Module responsible for user interactions, including argument processing."

import argparse

from oratapi.lib.config_mgr import ConfigManager
from pathlib import Path

from oratapi.model.framework_errors import InvalidParameter
from oratapi.view.console_display import MsgLvl, ConsoleMgr
from oratapi.lib.fsutils import resolve_path, runtime_home
import os
import getpass

proj_home = runtime_home()

VALID_API_TYPES = ["insert", "select", "update", "delete", "upsert", "merge"]

default_tapi_author =  getpass.getuser()

class MissingParameterError(Exception):
    """Exception raised for missing parameters."""
    def __init__(self, parameter_name: str):
        super().__init__(f"Missing required parameter: {parameter_name}")

class InvalidParameterError(Exception):
    """Exception raised for missing parameters."""
    """Exception raised for missing parameters."""
    def __init__(self, message: str):
        super().__init__(f"invalid parameter: {message}")

class Interactions:
    def __init__(self, controller, config_file_path: Path):
        self.controller = controller
        self.console_manager = ConsoleMgr(config_file_path=config_file_path)
        self.config_file_path = config_file_path
        self.config_manager = ConfigManager(config_file_path=self.config_file_path)


        args = self.parse_arguments()
        self.args_dict = vars(args)


    def print_console(self, text: str, msg_level: MsgLvl = MsgLvl.info):
        """
        Print a message to the console based on its message level.

        :param text: str, The message text to print
        :param msg_level: MsgLevel, The level of the message
        """
        self.console_manager.print_console(text=text, msg_level=msg_level)

    def write_file(self, staging_dir:Path, directory:Path, file_name, code:str):
        file_path = staging_dir / directory / file_name
        try:
            with open(file_path, 'w') as f:
                f.write(code)
        except Exception as e:
            print(f"An error occurred writing {file_path} : {e}")
            exit (0)


    def parse_arguments(self) -> argparse.Namespace:
        """
        Parse command-line arguments.

        :rtype: argparse.Namespace
        :returns: Parsed arguments for the application
        """
        default_api_types = self.config_manager.config_value(config_section="api_controls",
                                                             config_key="default_api_types").strip()

        default_app_name = self.config_manager.config_value(config_section="project",
                                                            config_key="default_app_name",
                                                            default='Undefined')

        table_owner = self.config_manager.config_value(config_section="schemas",
                                                         config_key="default_table_owner",
                                                         default=None)


        package_owner = self.config_manager.config_value(config_section="schemas",
                                                         config_key="default_package_owner",
                                                         default=None)

        trigger_owner = self.config_manager.config_value(config_section="schemas",
                                                         config_key="default_trigger_owner",
                                                         default=None)

        view_owner = self.config_manager.config_value(config_section="schemas",
                                                      config_key="default_view_owner",
                                                      default=None)

        default_staging_dir = self.config_manager.config_value(config_section="file_controls",
                                                                    config_key="default_staging_dir",
                                                                    default=None)

        default_ut_staging_dir = self.config_manager.config_value(config_section="file_controls",
                                                                  config_key="default_ut_staging_dir",
                                                                  default=None)

        # Argument parser setup
        parser = argparse.ArgumentParser(description="Oracle Table API Generator",
                                         epilog="The majority of defaults can be changed via the OraTAPI.ini file.")

        help_text = f"Application name - included to the package header. Default: {default_app_name}"
        parser.add_argument('-A', '--app_name', type=str, help=help_text, default=default_app_name)

        parser.add_argument('-a', '--tapi_author', type=str, help="TAPI author", default=default_tapi_author)

        parser.add_argument('-c', '--conn_name', type=str, help="Database connection name (created via OraTAPI connection manager).")

        parser.add_argument('-d', '--dsn', type=str, help="Database data source name (TNS name).")

        parser.add_argument('--oracle-client-dir', type=Path,
                            help="Path to an Oracle Instant Client directory to use for this run.")

        help_text = f"Directory for staging area. Default: {proj_home}/{default_staging_dir}"
        parser.add_argument('-g', '--staging_dir', type=Path, default=default_staging_dir,
                            help=help_text)

        help_text = f"Directory for unit tests staging area. Default: {proj_home}/{default_ut_staging_dir}"
        parser.add_argument('-G', '--ut_staging_dir', type=Path, default=default_ut_staging_dir,
                            help=help_text)

        parser.add_argument('-u', '--db_username', type=str, help="Database connection username.")

        parser.add_argument('-p', '--db_password', type=str, help="Database connection password.")

        help_text = f"Database schema name of the tables from which to generate the code. Default: {table_owner}"
        parser.add_argument('-To', '--table_owner', type=str, help=help_text, default=table_owner)

        help_text = f"Database schema in which to place the TAPI packages. Default: {package_owner}"
        parser.add_argument('-po', '--package_owner', type=str, default=package_owner, help=help_text)

        help_text = f"The schema in which to place the generated triggers. Default: {trigger_owner}"
        parser.add_argument('-to', '--trigger_owner', type=str, help=help_text, default=trigger_owner)

        help_text = f"The schema in which to place the generated views. Default: {view_owner}"
        parser.add_argument('-vo', '--view_owner', type=str, help=help_text, default=view_owner)

        parser.add_argument('-t', '--table_names', type=str, help="A space separated list of table names. Default: all",
                            nargs="+", default='%')

        api_types = default_api_types.replace(' ','').split(',')
        help_text = f"Space-separated list of API types. Valid options: insert, select, update, upsert, delete or merge.\n (Default setting: {default_api_types})"
        parser.add_argument('-T', '--api_types', type=str, default=api_types, help=help_text, nargs="+")

        help_text = f"Space-separated list of unit test API types. Valid options: insert, select, update, upsert, delete or merge.\n (Default setting: {default_api_types})"
        parser.add_argument('-U', '--ut_api_types', type=str, default=api_types, help=help_text, nargs="+")

        args = parser.parse_args()

        for api_type in args.api_types:
            if api_type not in VALID_API_TYPES:
                raise InvalidParameter(f'Invalid option "{api_type} specified with ""-T/--api_types')

        for api_type in args.ut_api_types:
            if api_type not in VALID_API_TYPES:
                raise InvalidParameter(f'Invalid option "{api_type} specified with ""-U/--ut_api_types')

        # Extract parameters for validation
        conn_name = args.conn_name
        dsn = args.dsn
        db_username = args.db_username
        db_password = args.db_password
        save_connection = False

        if not conn_name and not (db_username and db_password and dsn):
            raise MissingParameterError('You must specify a named connection or provide a dsn with credentials!')

        # Validation
        if conn_name:
            # conn_name alone is valid (to retrieve connection details)
            if dsn or db_username or db_password:
                # If any connection parameters are provided with conn_name, all must be provided
                missing_params = [param for param in ['dsn', 'db_username', 'db_password'] if not getattr(args, param)]
                if missing_params:
                    parser.error(
                        f"If 'conn_name' is provided with connection parameters, all the following must be included: {', '.join(missing_params)}")

        else:
            # If conn_name is not provided, ensure all connection parameters are specified together
            if dsn or db_username or db_password:
                missing_params = [param for param in ['dsn', 'db_username', 'db_password'] if not getattr(args, param)]
                if missing_params:
                    parser.error(
                        f"If any of 'dsn', 'db_username', or 'db_password' is provided, all three must be included: {', '.join(missing_params)}")

        return args


if __name__ == "__main__":
    # Create a dummy instance of Interactions to parse arguments
    class DummyController:
        pass

    config_file_path = resolve_path(Path("resources") / "config" / "OraTAPI.ini")

    try:
        interactions = Interactions(controller=DummyController(), config_file_path=config_file_path)
        # Explicitly invoke argparse's help behavior by parsing arguments
        interactions.parse_arguments()
    except SystemExit as e:
        # argparse will call sys.exit() for -h or missing arguments.
        # Catch this to avoid abrupt termination in some environments.
        pass
