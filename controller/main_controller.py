__author__ = "Clive Bostock"
__date__ = "2024-11-09"
__description__ = "Main controller to parse command-line arguments and coordinate API generation flow."

import copy
from model.api_generator import ApiGenerator
from model.config_manager import ConfigManager
from model.session_manager import DBSession
from lib.file_system_utils import project_home
from model.user_security import UserSecurity
from view.interactions import Interactions, MsgLvl


VALID_API_TYPES = ["insert", "select", "update", "delete", "upsert", "merge"]


class TAPIController:
    def __init__(self, trace: bool = False):
        proj_home = project_home()  # project_home returns a Path object
        config_file_path = proj_home / 'config' / 'OraTAPI.ini'
        self.view = Interactions(config_file_path=config_file_path)
        args = self.view.parse_arguments()
        args_dict = vars(args)

        options_dict = copy.deepcopy(args_dict)
        options_dict["config_file_path"] = config_file_path
        self.options_dict = options_dict
        self.force_overwrite = options_dict['force_overwrite']
        self.api_types = self.validate_api_types(options_dict.get('api_types'))
        self.config_file_path = options_dict["config_file_path"]
        self.tapi_author = options_dict['tapi_author']
        self.db_username = options_dict['db_username']
        self.db_password = options_dict['db_password']
        self.package_owner = options_dict['package_owner']
        self.dsn = options_dict['dsn']
        self.save_connection = options_dict['save_connection']
        self.schema_name = str(options_dict['schema_name']).upper()
        self.table_names = str(options_dict['table_names']).upper()
        self.conn_name = options_dict['conn_name']
        self.staging_area_dir = options_dict['staging_area_dir']
        self.trace = trace
        self.proj_home = project_home()

        self.config_manager = ConfigManager(config_file_path=self.config_file_path)

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
            binds = {'schema_name': self.schema_name}
            result_list = self.db_session.fetch_as_lists(sql_query=table_list_sql, bind_mappings=binds)
            for row in result_list:
                table_list.append(row[0])
            self.table_names_list = table_list

        table_count = len(self.table_names_list)
        self.view.print_console(text=f'{table_count} tables selected.', msg_level=MsgLvl.info)

        for table_name in self.table_names_list:
            exists_status = self.check_table_exists(schema_name=self.schema_name, table_name=table_name)
            if not exists_status:
                self.view.print_console(text=f'Table {self.schema_name}.{table_name} does not exist - skipping!',
                                        msg_level=MsgLvl.warning)
            else:
                self.generate_api_for_table(table_name)

    def generate_api_for_table(self, table_name: str):
        """
        Generate APIs for a specified table.

        :param table_name: str, The table name to generate APIs for
        """
        api_controller = ApiGenerator(
            database_session=self.db_session,
            schema_name=self.schema_name,
            table_name=table_name,
            config_manager=self.config_manager,
            options_dict=self.options_dict,
            trace=self.trace
        )

        package_spec = api_controller.gen_package_spec()
        print(package_spec)

        package_body = api_controller.gen_package_body()
        print(package_body)

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
