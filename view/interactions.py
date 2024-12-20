__author__ = "Clive Bostock"
__date__ = "2024-11-09"
__description__ = "Module responsible for user interactions, including argument processing."

import argparse

from lib.config_manager import ConfigManager
from pathlib import Path

from view.console_display import MsgLvl, ConsoleMgr


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

        # Argument parser setup
        parser = argparse.ArgumentParser(description="Oracle Table API Generator")

        parser.add_argument('-A', '--app_name', type=str, help="Application name - included to the package header.",
                            default=default_app_name)
        parser.add_argument('-a', '--tapi_author', type=str, help="TAPI author", default='OraTAPI generator')
        parser.add_argument('-c', '--conn_name', type=str, help="Connection name for saved configuration")
        parser.add_argument('-d', '--dsn', type=str, help="Database data source name (TNS name)")
        parser.add_argument('-g', '--staging_area_dir', type=Path, default="staging",
                            help="Directory for staging area (default: <APP_HOME>/staging)")
        parser.add_argument('-p', '--db_password', type=str, help="Database password")

        parser.add_argument('-s', '--save_connection', action='store_true', default=False,
                            help="Save/update the connection for future use. Connections are only saved after a successful connection.")
        parser.add_argument('-To', '--table_owner', type=str, help="Database schema name of the tables from which to generate the code.",
                            default=table_owner)

        parser.add_argument('-t', '--table_names', type=str, help="Comma separated list of table names (default: all)",
                            default='%')

        parser.add_argument('-po', '--package_owner', type=str, default=package_owner,
                            help="Database schema in which to place the TAPI package.")

        parser.add_argument('-to', '--trigger_owner', type=str, help="The schema in which owns the generated triggers.",
                            default=trigger_owner)

        parser.add_argument('-vo', '--view_owner', type=str, help="The schema in which owns the generated views.",
                            default=view_owner)

        parser.add_argument('-u', '--db_username', type=str, help="Database username")
        parser.add_argument('-T', '--api_types', type=str, default=default_api_types,
                            help="Comma-separated list of API types (e.g., create,read). Must be one or more of: create, read, update, upsert,delete, merge.")

        args = parser.parse_args()

        # Convert api_types to a list
        if args.api_types:
            args.api_types = [api_type.strip() for api_type in args.api_types.split(',')]

        # Extract parameters for validation
        conn_name = args.conn_name
        dsn = args.dsn
        db_username = args.db_username
        db_password = args.db_password
        save_connection = args.save_connection

        # Validation logic
        if save_connection:
            # save_connection requires conn_name and all connection parameters
            missing_params = [param for param in ['conn_name', 'dsn', 'db_username', 'db_password'] if
                              not getattr(args, param)]
            if missing_params:
                parser.error(
                    f"'save_connection' requires the following parameters: {', '.join(missing_params)}")

        elif conn_name:
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
