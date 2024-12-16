__author__ = "Clive Bostock"
__date__ = "2024-11-09"
__description__ = "Main controller to parse command-line arguments and coordinate API generation flow."
__version__ = "1.0.5"
import copy
import time

from model.api_generator import ApiGenerator
from lib.config_manager import ConfigManager
from model.session_manager import DBSession
from lib.file_system_utils import project_home
from lib.app_utils import current_timestamp, current_dttm, format_elapsed_time
from model.user_security import UserSecurity
from view.interactions import Interactions, MsgLvl
from pathlib import Path
from os import chdir
from view.ora_tapi_csv import CSVManager

RUN_ID = int(time.time())
prog_bin = Path(__file__).resolve().parent
app_home = prog_bin.parent

prog_name = Path(__file__).name

VALID_API_TYPES = ["insert", "select", "update", "delete", "upsert", "merge"]


class TAPIController:
    def __init__(self, trace: bool = False):
        proj_home = project_home()  # project_home returns a Path object
        chdir(proj_home)
        config_file_path = proj_home / 'config' / 'OraTAPI.ini'
        self.view = Interactions(controller=self, config_file_path=config_file_path)
        args_dict = self.view.args_dict

        options_dict = copy.deepcopy(args_dict)

        exec_start_timestamp = current_timestamp()
        self.view.print_console(text=f'{prog_name}: Version: {__version__}',
                                msg_level=MsgLvl.highlight)
        self.view.print_console(text=f'{prog_name}: Run Id: {RUN_ID} started at: {exec_start_timestamp}',
                                msg_level=MsgLvl.highlight)
        epoc_start_ts = int(time.time())
        self.view.print_console(text=f'{prog_name}: Command line parameters:-',
                                msg_level=MsgLvl.highlight)
        self.view.print_console(msg_level=MsgLvl.highlight, text=f"=" * 80)
        for key in sorted(options_dict.keys()):  # Sort the keys
            value = options_dict[key]
            if key == 'db_password':
                value = '***************'
            self.view.print_console(msg_level=MsgLvl.highlight, text=f"{key:<40} = {value}")
        self.view.print_console(msg_level=MsgLvl.highlight, text=f"=" * 80)


        options_dict["config_file_path"] = config_file_path
        self.options_dict = options_dict
        self.api_types = self.validate_api_types(options_dict.get('api_types'))
        self.config_file_path = options_dict["config_file_path"]
        self.tapi_author = options_dict['tapi_author']
        self.db_username = options_dict['db_username']
        self.db_password = options_dict['db_password']
        self.package_owner = options_dict['package_owner']
        self.package_owner = options_dict['package_owner']
        self.dsn = options_dict['dsn']
        self.save_connection = options_dict['save_connection']
        self.table_owner = str(options_dict['table_owner']).upper()
        self.table_names = str(options_dict['table_names']).upper()
        self.conn_name = options_dict['conn_name']
        self.staging_area_dir = Path(options_dict['staging_area_dir'])


        self.trace = trace
        self.proj_home = project_home()

        self.config_manager = ConfigManager(config_file_path=self.config_file_path)
        csv_path = self.config_manager.config_value(config_section='file_controls',
                                                    config_key='ora_tapi_csv_dir',
                                                    default=str(app_home / 'OraTAPI.csv'))
        csv_path = Path(csv_path)

        self.csv_manager = CSVManager(csv_pathname=csv_path / 'OraTAPI.csv', config_file_path=config_file_path)

        self.ora_tapi_version = self.config_manager.config_value(config_section='OraTAPI',
                                                                 config_key='version')

        self.skip_on_missing_table = self.config_manager.bool_config_value(config_section='behaviour',
                                                                           config_key='skip_on_missing_table')

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

        self.body_suffix = self.config_manager.config_value(config_section='file_controls',
                                                            config_key='body_suffix')

        self.spec_suffix = self.config_manager.config_value(config_section='file_controls',
                                                            config_key='spec_suffix')


        if not self.staging_area_dir.exists():
            self.view.print_console(msg_level=MsgLvl.error, text=f'Staging directory, "{self.staging_area_dir}", does not exist - bailing out!')
            exit(0)

        if not self.staging_area_dir.is_dir():
            self.view.print_console(msg_level=MsgLvl.error, text=f'Staging pathname provide, "{self.staging_area_dir}", is not a directory - bailing out!')
            exit(0)

        if self.spec_dir == self.body_dir and self.spec_suffix == self.body_suffix:
            self.view.print_console(msg_level=MsgLvl.error, text=f'Conflicting OratAPI.ini properties. The spec_dir and body_dir must be distinct when spec_suffix and body_suffix are the same!')
            exit(0)

        for directory in (self.spec_dir, self.body_dir, self.trigger_dir, self.view_dir):
            dir_path = self.staging_area_dir / directory
            if directory and not dir_path.exists():
                self.view.print_console(msg_level=MsgLvl.info, text=f"Creating staging sub directory: {dir_path}")
                dir_path.mkdir(parents=False, exist_ok=True)

        # Process table names as a list
        self.table_names_list = [name.strip() for name in self.table_names.split(',')]

        user_security = UserSecurity(project_identifier="OraTAPI")
        if self.conn_name:
            self.db_username, self.db_password, self.dsn \
                = user_security.named_connection_creds(connection_name=self.conn_name)

        # Database session setup
        self.db_session: DBSession = DBSession(dsn=self.dsn, db_username=self.db_username, db_password=self.db_password)
        self.view.print_console(msg_level=MsgLvl.info, text="Database session established successfully.")

        # Now check to see if we have a --save_connection flag submitted.
        if self.save_connection:
            user_security.update_named_connection(connection_name=self.conn_name,
                                                  username=self.db_username,
                                                  password=self.db_password,
                                                  dsn=self.dsn)
            self.view.print_console(msg_level=MsgLvl.info, text=f"Connection saved as: {self.conn_name}")


        # Validate table names and process
        self.process_table_names()


        exec_end_timestamp = current_timestamp()
        epoc_end_ts = int(time.time())
        self.view.print_console(text=f'{prog_name}: Run Id: {RUN_ID} completed at: {exec_end_timestamp}',
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

    def process_table_names(self):
        """
        Process the provided table names, ensuring they exist in the database.
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

        for table_name in self.table_names_list:
            package_enabled = self.csv_manager.csv_dict_property(self.package_owner, table_name=table_name,
                                                                 property_selector='package')
            view_enabled = self.csv_manager.csv_dict_property(self.package_owner, table_name=table_name,
                                                                 property_selector='view')
            trigger_enabled = self.csv_manager.csv_dict_property(self.package_owner, table_name=table_name,
                                                                 property_selector='trigger')

            exists_status = self.check_table_exists(schema_name=self.table_owner, table_name=table_name)
            if not exists_status and self.skip_on_missing_table:
                self.view.print_console(text=f'Table {self.table_owner}.{table_name} does not exist - skipping!',
                                        msg_level=MsgLvl.warning)
            elif not self.skip_on_missing_table:
                self.view.print_console(text=f'Table {self.table_owner}.{table_name} does not exist - bailing out!',
                                        msg_level=MsgLvl.error)
                exit(1)
            else:
                if package_enabled:
                    self.generate_api_for_table(table_name)
                if view_enabled:
                    self.generate_views_for_table(table_name)
                if trigger_enabled:
                    self.generate_triggers_for_table(table_name)


    def generate_api_for_table(self, table_name: str):
        """
        Generate APIs for a specified table.

        :param table_name: str, The table name to generate APIs for
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

        tapi_name = f"{table_name_lc}_tapi"
        self.view.print_console(msg_level=MsgLvl.info, text=f"Generating TAPI package: {tapi_name.upper()}")
        staging_realpath = self.staging_area_dir.resolve()

        package_spec_code = api_controller.gen_package_spec()
        spec_file_name = f"{tapi_name}{self.spec_suffix}"
        self.view.write_file(staging_dir=staging_realpath, directory=self.spec_dir, file_name=spec_file_name,
                             code=package_spec_code)

        package_body_code = api_controller.gen_package_body()
        body_file_name = f"{tapi_name}{self.body_suffix}"
        self.view.write_file(staging_dir=staging_realpath, directory=self.body_dir, file_name=body_file_name,
                             code=package_body_code)


    def generate_triggers_for_table(self, table_name: str):
        staging_realpath = self.staging_area_dir.resolve()
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
            self.view.print_console(msg_level=MsgLvl.info, text=f"Generating trigger script for {trigger_file_name.upper().replace('.SQL', '')}")
            self.view.write_file(staging_dir=staging_realpath, directory=self.trigger_dir, file_name=trigger_file_name,
                                 code=code)


    def generate_views_for_table(self, table_name: str):
        staging_realpath = self.staging_area_dir.resolve()
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
            self.view.print_console(msg_level=MsgLvl.info, text=f"Generating view view script for {view_file_name.upper().replace('.SQL', '')}")
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
    TAPIController()

if __name__ == "__main__":
    main()
