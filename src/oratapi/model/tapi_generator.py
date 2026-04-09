# api_controller.py

__author__ = "Clive Bostock"
__date__ = "2024-11-09"
__description__ = "Generates the API code."

import copy
import re

from oratapi.lib.fsutils import resolve_path
from oratapi.lib.config_mgr import ConfigManager
from oratapi.model.db_objects import Table
from oratapi.lib.session_manager import DBSession
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from copy import deepcopy
from itertools import chain
from oratapi.lib.app_utils import enhanced_guid, random_string
from oratapi.model.ora_tapi_csv import CSVManager
from oratapi.model.pi_csv import PIColumnsManager


# Define our substitution placeholder string for indent spaces.
# The number of spaces for an indent tab, is defined in OraTAPI.ini
IDNT = '%indent_spaces%'

TEMPLATES_LOCATION = Path("resources") / "templates"
CONFIG_LOCATION = Path("resources") / "config"

# Get the current date
date_now = datetime.now()

# Format the date as DD-Mon-YYYY
current_date = date_now.strftime("%d-%b-%Y")
current_year = date_now.strftime("%Y")

# Define the list of noop_column_string supported data-types.
NO_OP_DATA_TYPES = (
    "VARCHAR2",  # Variable-length character data
    "CHAR",      # Fixed-length character data
    "NCHAR",     # Fixed-length national character set data
    "NVARCHAR2", # Variable-length national character set data
    "CLOB",      # Character Large Object
    "NCLOB"      # National Character Large Object
)

def inject_values(substitutions: Dict[str, Any], target_string: str, stab_spaces:int = 3) -> str:
    """
    Recursively walk through a nested dictionary to replace placeholders in the text template.

    :param stab_spaces:
    :param substitutions: The dictionary of substitutions (optionally nested).
    :type substitutions: (Dict[str, Any])
    :param target_string: A string with %key% placeholders, for substitutions based on the supplied dictionary.
    :type target_string: Str
    :return: The template contents with placeholders replaced by corresponding values.
    :rtype: Str
    """
    _substitutions = copy.deepcopy(substitutions)
    _substitutions["STAB"] = ' ' * stab_spaces
    for key, value in substitutions.items():
        if isinstance(value, dict):
            # Recursively walk the nested dictionary
            target_string = inject_values(value, target_string, stab_spaces=stab_spaces)
        else:
            # Replace the placeholder with the value
            placeholder = f"%{key}%"
            target_string = target_string.replace(placeholder, str(value))
    target_string.replace('%STAB%', ' ' * stab_spaces)
    return target_string

class ApiGenerator:
    def __init__(self,
                 database_session: DBSession,
                 table_owner: str,
                 table_name: str,
                 config_manager: ConfigManager,
                 options_dict: dict,
                 trace: bool = False):
        """
            Generates Table APIs (TAPI) for Oracle databases.

    This class uses configuration files, templates, and database metadata to create PL/SQL
    procedures (and potentially other database objects like views and triggers) that
    interact with a specified table.It supports generating APIs for common
    database operations (insert, update, delete, merge, select, upsert) and provides
    flexibility through configuration options and command-line arguments.

    Attributes:
        proj_home (Path): The project's home directory.
        column_expressions_dir (Path): Directory containing column expression templates.
        view_template_dir (Path): Directory containing view templates.
        trigger_template_dir (Path): Directory containing trigger templates.
        options_dict (dict): Dictionary of command-line options.
        config_manager (ConfigManager): Manages application configuration.
        table_owner (str): Schema (owner) of the target table.
        table (Table): Object representing the target table and its metadata.
        auto_maintained_cols (list): List of auto-maintained column names.
        signature_types (list): List of signature types ('rowtype', 'coltype').
        indent_spaces (int): Number of spaces for indentation.
        sig_file_ext (str): File extension for specification files.
        body_file_ext (str): File extension for body files.
        include_defaults (bool): Whether to include default values in APIs.
        return_pk_columns (bool): Whether to return primary key columns.
        return_ak_columns (bool): Whether to return alternate key columns.
        include_commit (bool): Whether to include a COMMIT statement in APIs.
        noop_column_string (str): String used for "no-operation" updates.
        row_vers_column_name (str): Name of the row version column.
        col_auto_maintain_method (str): Method for auto-maintaining columns.
        delete_procname (str): Name for delete procedures.
        select_procname (str): Name for select procedures.
        insert_procname (str): Name for insert procedures.
        merge_procname (str): Name for merge procedures.
        update_procname (str): Name for update procedures.
        upsert_procname (str): Name for upsert procedures.
        view_name_suffix (str): Suffix for view names.
        logger_pkg (str): Name of the logger package.
        logger_logs (str): Name of the logger logs table/procedure.
        csv_manager (CSVManager): Manages CSV data.
        pi_column_manager (PIColumnsManager): Manages PI column data.
        view_name_suffix_lc (str): Lowercase version of view_name_suffix.
        global_substitutions (dict): Dictionary of global template substitutions.
        merged_dict (dict): Merged dictionary of global substitutions and options.
        column_insert_expressions (dict): Dictionary of insert column expressions.
        column_update_expressions (dict): Dictionary of update column expressions.

    Methods:
        load_column_expressions() -> list: Loads column expressions from template files.
        _logger_appends(signature_type: str, soft_tabs: int, skip_list: list = None) -> str: Generates logger append code.
        _noop_assignment(column_name: str, soft_tabs: int) -> str: Generates no-op assignment code.
        _column_expression(signature_type: str, operation_type: str, column_name: str) -> str: Determines column expression.
        _params_string(signature_type: str, soft_tabs: int = 4) -> str: Generates parameter string.
        _returning_columns(skip_list: list = None, soft_tabs: int = 4) -> str: Generates returning columns clause.
        _into_parameters(signature_type: str, skip_list: list = None, soft_tabs: int = 4) -> str: Generates into parameters clause.
        _returning_into_clause(signature_type: str, skip_list: list = None, soft_tabs: int = 4) -> str: Generates returning into clause.
        _mrg_param_alias_list_string(signature_type: str, operation_type: str = 'create', skip_list: list = None, soft_tabs: int = 4) -> str: Generates merge parameter alias list.
        _mrg_predicates_string(soft_tabs: int = 4) -> str: Generates merge predicates string.
        _mrg_update_assignments_string(signature_type: str, operation_type: str, skip_list: list = None, soft_tabs: int = 4) -> str: Generates merge update assignments string.
        _mrg_src_column_list_string(signature_type: str, operation_type: str = 'create', skip_list: list = None, soft_tabs: int = 4) -> str: Generates merge source column list.

        :param database_session: A DBSession instance for connecting to the database.
        :param table_owner: Schema Name of the table.
        :param table_name: Table name of the table for which we need to generate a TAPI
        :param config_manager: A ConfigManager as established by the controller.
        :param options_dict: The dictionary of our command line options.
        :param trace: Enables trace/debug output when set to True.
        """
        proj_config_file = resolve_path(CONFIG_LOCATION / 'OraTAPI.ini')
        self.column_expressions_dir = resolve_path(TEMPLATES_LOCATION / 'column_expressions')
        self.view_template_dir = resolve_path(TEMPLATES_LOCATION / 'misc' / 'view')
        self.trigger_template_dir = resolve_path(TEMPLATES_LOCATION / 'misc' / 'trigger')
        self.options_dict = deepcopy(options_dict)
        self.config_manager = config_manager
        self.table_owner = table_owner
        package_owner_lc = options_dict["package_owner"].lower()


        self.config_manager = ConfigManager(config_file_path=proj_config_file)
        self.table = Table(database_session=database_session, table_owner=self.table_owner,
                           table_name=table_name, config_manager=config_manager, trace=trace)

        # Cache identity columns (lowercase) for quick skip decisions (any generation type)
        self.identity_cols_lc = [col.lower() for col in self.table.columns_list if self.table.is_identity(col)]

        auto_maintained_cols = self.config_manager.config_value(config_section="api_controls",
                                                            config_key="auto_maintained_cols")
        auto_maintained_cols = auto_maintained_cols.replace(' ', '')
        self.auto_maintained_cols = auto_maintained_cols.lower().split(',')

        signature_types = self.config_manager.config_value(config_section="api_controls",
                                                           config_key="signature_types",
                                                           default='rowtype, coltype')

        signature_types = signature_types.replace(' ', '')
        self.signature_types = signature_types.lower().split(',')

        self.indent_spaces = self.config_manager.config_value(config_section="formatting", config_key="indent_spaces")
        try:
            self.indent_spaces = int(self.indent_spaces)
        except ValueError:
            message = f'The formatting.indent_spaces value, "{self.indent_spaces}", retrieved from OraTAPI.ini, is non-integer!'
            raise ValueError(message)

        # These next 2 are used in template substitutions.
        self.sig_file_ext = self.config_manager.config_value(config_section="file_controls", config_key="spec_file_ext")
        self.body_file_ext = self.config_manager.config_value(config_section="file_controls", config_key="body_file_ext")

        self.include_defaults = self.config_manager.bool_config_value(config_section="api_controls",
                                                                 config_key="include_defaults")

        self.return_pk_columns = self.config_manager.bool_config_value(config_section="api_controls",
                                                                       config_key="return_pk_columns",
                                                                       default=False)

        self.return_ak_columns = self.config_manager.bool_config_value(config_section="api_controls",
                                                                       config_key="return_ak_columns",
                                                                       default=False)

        # api_surface: controls whether generated API targets base table or passthrough view
        # Valid values: table, view. Default: view
        self.api_surface = self.config_manager.config_value(
            config_section="api_controls",
            config_key="api_surface",
            default="view",
            valid_values=["table", "view"],
        ).lower()

        self.include_commit = self.config_manager.bool_config_value(config_section="api_controls",
                                                                    config_key="include_commit")

        self.noop_column_string = self.config_manager.config_value(config_section="api_controls",
                                                                   config_key="noop_column_string",
                                                                   default='')

        self.row_vers_column_name = self.config_manager.config_value(config_section="api_controls",
                                                                     config_key="row_vers_column_name",
                                                                     default=None)
        self.col_auto_maintain_method = self.config_manager.config_value(config_section="api_controls",
                                                                     config_key="col_auto_maintain_method",
                                                                     default='trigger')

        auto_maintained_cols = self.config_manager.config_value(config_section="api_controls",
                                                                config_key="auto_maintained_cols",
                                                                default='')
        # Split the string and strip whitespace
        self.auto_maintained_cols = [col.strip() for col in auto_maintained_cols.split(",")]
        self.auto_maintained_cols_lc = [col.lower() for col in self.auto_maintained_cols]

        # API naming properties follow. Set these to the preferred procedure names, of the APIs
        self.delete_procname = self.config_manager.config_value(config_section="api_controls",
                                                                config_key="delete_procname",
                                                                default="del")
        self.select_procname = self.config_manager.config_value(config_section="api_controls",
                                                                config_key="select_procname",
                                                                default="del")
        self.insert_procname = self.config_manager.config_value(config_section="api_controls",
                                                                config_key="insert_procname",
                                                                default="del")
        self.merge_procname = self.config_manager.config_value(config_section="api_controls",
                                                               config_key="merge_procname",
                                                               default="del")
        self.update_procname = self.config_manager.config_value(config_section="api_controls",
                                                                config_key="update_procname",
                                                                default="del")

        self.upsert_procname = self.config_manager.config_value(config_section="api_controls",
                                                                config_key="upsert_procname",
                                                                default="ups")

        self.view_name_suffix = self.config_manager.config_value(config_section="misc",
                                                                config_key="view_name_suffix",
                                                                default="_v")

        self.logger_pkg = self.config_manager.config_value(config_section="logger",
                                                                config_key="logger_pkg",
                                                                default="logger")

        self.logger_logs = self.config_manager.config_value(config_section="logger",
                                                                config_key="logger_logs",
                                                                default="logger_logs")

        pi_columns_csv_dir = self.config_manager.config_value(config_section="file_controls",
                                                                config_key="pi_columns_csv_dir",
                                                                default="resources/config")

        ora_tapi_csv_dir = self.config_manager.config_value(config_section='file_controls',
                                                    config_key='ora_tapi_csv_dir',
                                                    default="resources/config")
        ora_tapi_csv_dir = resolve_path(ora_tapi_csv_dir)
        self.csv_manager = CSVManager(csv_pathname=ora_tapi_csv_dir / 'OraTAPI.csv',
                                      config_file_path=self.config_manager.config_file_path,
                                      cleanup=False)

        pi_csv_file_path = Path(pi_columns_csv_dir) / 'pi_columns.csv'
        pi_csv_file_path = resolve_path(pi_csv_file_path)
        self.pi_column_manager = PIColumnsManager(pi_columns_csv_path=pi_csv_file_path)
        self.view_name_suffix_lc = self.view_name_suffix.lower()
        # Populate self.global_substitutions with the .ini file contents.
        # We will use these to inject values into the templates.
        self.global_substitutions = self.config_manager.config_dictionary()

        # Set soft tabs spaces for indent
        self.global_substitutions["STAB"] = ' ' * int(self.global_substitutions["indent_spaces"])
        self.global_substitutions["package_owner_lc"] = package_owner_lc


        self.merged_dict = self.global_substitutions | self.options_dict
        # Check to see if the copyright date is expected to be set to today's date.
        # If not set as "current_date", we assume it's a static date.
        if self.global_substitutions["copyright_year"] == "current":
            self.global_substitutions["copyright_year"] = current_year

        if self.noop_column_string == 'auto':
            self.noop_column_string = f"~{enhanced_guid()}~"
            self.global_substitutions["noop_column_string"] = self.noop_column_string

        if self.noop_column_string == 'dynamic':
            rand_text1 = random_string(length=8)
            rand_text2 = random_string(length=8)
            self.noop_column_string = f"~{rand_text1}' || sys_guid() || '~  ' || sys_guid() || '{rand_text2}~"
            self.global_substitutions["noop_column_string"] = self.noop_column_string


        table_domain = self.csv_manager.csv_dict_property(schema_name=self.table.schema_name_lc,
                                                             table_name=table_name,
                                                             property_selector='domain')
        table_domain_lc = str(table_domain).lower()

        self.global_substitutions["sig_file_ext"] = self.sig_file_ext
        self.global_substitutions["body_file_ext"] = self.body_file_ext
        self.global_substitutions["run_date_time"] = current_date
        self.global_substitutions["table_name_lc"] = table_name.lower()
        self.global_substitutions["table_owner_lc"] = self.table_owner.lower()
        self.global_substitutions["table_owner"] = self.table_owner
        self.global_substitutions["table_domain"] = table_domain
        self.global_substitutions["table_domain_lc"] = table_domain_lc
        self.global_substitutions["tapi_author"] = options_dict["tapi_author"]
        self.global_substitutions["tapi_author_lc"] = options_dict["tapi_author"].lower()
        self.global_substitutions["view_owner_lc"] = options_dict["view_owner"].lower()
        self.global_substitutions["view_owner"] = options_dict["view_owner"]
        self.global_substitutions["trigger_owner_lc"] = options_dict["trigger_owner"].lower()
        self.global_substitutions["trigger_owner"] = options_dict["trigger_owner"]
        self.global_substitutions["view_name_suffix_lc"] = self.view_name_suffix.lower()
        self.global_substitutions["view_name_suffix"] = self.view_name_suffix
        self.global_substitutions["tapi_pkg_name_postfix_lc"] = self.global_substitutions["tapi_pkg_name_postfix"]
        self.global_substitutions["tapi_pkg_name_prefix_lc"] = self.global_substitutions["tapi_pkg_name_prefix"]


        self.table = Table(database_session=database_session,
                           table_owner=table_owner,
                           table_name=table_name,
                           config_manager=config_manager,
                           trace=trace)

        # Derive API target object name (metadata stays on base table). When api_surface=view, target is passthrough view.
        view_suffix = self.view_name_suffix.lower()
        self.base_table_name_lc = self.table.table_name_lc
        self.api_target_name_lc = self.base_table_name_lc + view_suffix if self.api_surface == "view" else self.base_table_name_lc
        self.api_target_owner = options_dict["package_owner"] if self.api_surface == "view" else self.table_owner

        # Override substitution for emitted code targets; metadata uses base table internals
        self.global_substitutions["api_target_name_lc"] = self.api_target_name_lc
        # Keep table_name* bound to the base table for naming/changesets; use api_target* for DML/rowtype surface
        self.global_substitutions["table_name_lc"] = self.base_table_name_lc
        self.global_substitutions["table_name"] = self.base_table_name_lc.upper()
        self.global_substitutions["base_table_name_lc"] = self.base_table_name_lc

        # The column expressions properties are used to store the contents of the column expressions
        # found in the templates/column_expressions directories.
        self.column_insert_expressions = {}
        self.column_update_expressions = {}

    def load_column_expressions(self) -> list:
        messages = []
        # Use pathlib to get all files in the templates directory that match the pattern
        inserts_expressions_dir = self.column_expressions_dir / 'inserts'
        updates_expressions_dir = self.column_expressions_dir / 'updates'

        inserts_files = inserts_expressions_dir.glob('*[a-z0-9_]*.tpt')
        updates_files = updates_expressions_dir.glob('*[a-z0-9_]*.tpt')

        # Filter out any files that might accidentally have uppercase characters
        insert_expression_files = [
            file for file in inserts_files
            if re.match(r'^[a-z0-9_]+\.tpt$', file.name)  # Using `file.name` to match the filename only
        ]

        # Loop through the valid column expression files and load them to the self.column_expressions dictionary.
        for expression_path in insert_expression_files:
            with open(expression_path, 'r') as ce:
                expression = ce.read()

            expression_file = Path(expression_path).name
            self.column_insert_expressions[expression_file.replace('.tpt', '')] = expression

        # Filter out any files that might accidentally have uppercase characters
        update_expression_files = [
            file for file in updates_files
            if re.match(r'^[a-z0-9_]+\.tpt$', file.name)  # Using `file.name` to match the filename only
        ]

        # Loop through the valid column expression files and load them to the self.column_expressions dictionary.
        for expression_path in update_expression_files:
            with open(expression_path, 'r') as ce:
                expression = ce.read()

            expression_file = Path(expression_path).name
            self.column_update_expressions[expression_file.replace('.tpt', '')] = expression

        # Cross-check expression column template entries, with the auto maintained column list.
        missing_expressions = []
        auto_columns = self.auto_maintained_cols[:]
        if self.row_vers_column_name:
            auto_columns.append(self.row_vers_column_name)
        for column_name in auto_columns:
            if column_name not in self.column_update_expressions:
                missing_expressions.append(column_name)

        if len(missing_expressions) > 0:
            message = f"The following columns have missing column insert expression templates:\n{', '.join(missing_expressions)}"
            message += '\nExpression template files should be placed under templates/column_expressions/inserts.\n'
            message += 'Also ensure that expression templates are provided and placed under templates/column_expressions/updates.'
            raise FileNotFoundError(message)

        missing_expressions = []
        for column_name in auto_columns:
            if column_name not in self.column_update_expressions:
                missing_expressions.append(column_name)

        if len(missing_expressions) > 0:
            message = f"The following columns have missing column update expression templates:\n{', '.join(missing_expressions)}"
            message += 'Template files should be placed under templates/column_expressions/updates'
            raise FileNotFoundError(message)

        return messages

    def _logger_appends(self, signature_type: str, soft_tabs:int, skip_list: list = None,) -> str:
        # Normalise skip list (lowercase) so callers can pass None or mixed-case lists
        if skip_list is None:
            skip_list = []
        skip_list = [item.lower() for item in skip_list]

        logger_appends = ''
        tabs = "%STAB%" * soft_tabs
        col_id = 0
        for column_name in self.table.columns_list:
            column_name_lc = column_name.lower()
            if column_name_lc in self.auto_maintained_cols_lc or column_name_lc == self.row_vers_column_name.lower():
                continue
            parameter_name_lc = 'p_' + column_name_lc if signature_type == 'coltype'  or column_name_lc in self.table.pk_columns_list_lc else 'p_row.' + column_name_lc
            data_type = self.table.column_property_value(column_name=column_name, property_name='data_type')
            is_pk_column = self.table.column_property_value(column_name=column_name, property_name='is_pk_column')
            param_prefix = '* ' if is_pk_column else '  '
            if data_type == 'CLOB' or column_name_lc in skip_list:
                continue

            is_pi = self.pi_column_manager.check_column(schema_name=self.table.schema_name_lc,
                                                        table_name=self.table.table_name_lc,
                                                        column_name=column_name_lc)
            comment = '-- PI column: ' if is_pi else ''
            col_id += 1
            if col_id == 1:
                logger_appends = f"{comment}{self.logger_pkg}.append_param(l_params, '{param_prefix}{parameter_name_lc}', {parameter_name_lc});\n"
            else:
                logger_appends += f"{tabs}{comment}{self.logger_pkg}.append_param(l_params, '{param_prefix}{parameter_name_lc}', {parameter_name_lc});\n"

        return logger_appends


    def _noop_assignment(self, column_name, soft_tabs:int) -> str:
        """The _noop_assignment method should only be called for update APIs. It is used to generate cases statements
        for columns where the parameter is defaulted to the noop_column_string property setting in OraTAPI.ini."""
        if self.table.column_property_value(column_name=column_name, property_name='default_value'):
            return ""
        if self.table.column_property_value(column_name=column_name, property_name='data_type') not in NO_OP_DATA_TYPES:
            return ''

        block_list = self.table.in_out_column_list + [self.table.row_vers_column_name.upper()]
        if column_name.upper() in block_list:
            return ""

        column_name_lc = column_name.lower()

        tabs = "%STAB%" * soft_tabs
        noop_assignment = f"case\n"
        noop_assignment += f"{tabs}%STAB%  when p_{column_name_lc} = NOOP then {column_name_lc}\n"
        noop_assignment += f"{tabs}%STAB%  else p_{column_name_lc}\n"
        noop_assignment += f"{tabs}  end"

        return noop_assignment

    def _column_expression(self, signature_type:str, operation_type: str, column_name: str):
        """The _column_expression method, resolves the assignment for a specific column, for use in an insert (create),
        update (modify), upsert (create/modify/merge_create/merge_modify), or merge (create/modify) APIs.
        :param operation_type: Must be "create" or "modify"
        :param column_name: The table column name.
        :return: """
        block_list = self.table.in_out_column_list + [self.table.row_vers_column_name.upper()]

        valid_operations_list = [ "create", "modify", "merge_create", "merge_modify", "select"]
        valid_operations_list = [ "create", "modify", "merge_create", "merge_modify", "select"]
        valid_operations = ', '.join(valid_operations_list)
        if operation_type not in valid_operations_list:
            message = f'Invalid operation type, "{operation_type}". Valid operation types: {valid_operations}'
            raise ValueError(message)
        column_name_lc = column_name.lower()
        assignment = 'DEADBEEF'
        if operation_type == "create":
            assignment = ''
            if (self.col_auto_maintain_method == "expression" and
                    column_name_lc in chain(self.auto_maintained_cols, [self.row_vers_column_name])):
                assignment = self.column_insert_expressions[column_name]
            if not assignment:
                if self.table.is_identity(column_name):
                    return ''
                if signature_type == "coltype":
                    assignment = f'p_{column_name_lc}'
                elif signature_type == "rowtype" and column_name_lc in self.auto_maintained_cols_lc:
                    assignment = column_name_lc
                else:
                    if column_name_lc in self.table.pk_columns_list_lc:
                        assignment = f'p_{column_name_lc}'
                    else:
                        assignment = f'p_row.{column_name_lc}'
        elif operation_type == 'modify':
            assignment = ''
            if (self.col_auto_maintain_method == "expression" and
                    column_name_lc in chain(self.auto_maintained_cols, [self.row_vers_column_name])):
                assignment = self.column_update_expressions[column_name]
            if not assignment:
                if signature_type == "coltype":
                    assignment = f'p_{column_name_lc}'
                elif signature_type == "rowtype" and column_name_lc in self.auto_maintained_cols_lc:
                    assignment = column_name_lc
                else:
                    if column_name_lc in self.table.pk_columns_list_lc:
                        assignment = f'p_{column_name_lc}'
                    else:
                        assignment = f'p_row.{column_name_lc}'

        elif operation_type == "merge_create":
            assignment = ''
            if (self.col_auto_maintain_method == "expression" and
                    column_name_lc in chain(self.auto_maintained_cols, [self.row_vers_column_name])):
                assignment = self.column_insert_expressions[column_name]
            if not assignment:
                assignment = f'src.{column_name_lc}'
        elif operation_type == 'merge_modify':
            assignment = ''
            if (self.col_auto_maintain_method == "expression" and
                    column_name_lc in chain(self.auto_maintained_cols, [self.row_vers_column_name])):
                assignment = self.column_update_expressions[column_name]
            if not assignment:
                assignment = f'src.{column_name_lc}'
        elif operation_type == 'select':
            assignment = f'p_{column_name_lc}' if signature_type == "coltype" else f'p_row.{column_name_lc}'
        elif operation_type == 'select':
            assignment = f'p_{column_name_lc}' if signature_type == "coltype" else f'p_row.{column_name_lc}'

        return assignment

    def _params_string(self, signature_type:str, soft_tabs:int = 4) -> str:
        """Returns a comma separated list of parameters"""
        tabs = "%STAB%" * soft_tabs  # The number of STABs in the respective template.
        if signature_type == "coltype":
            params_out = ""
            for column_id, column_name in enumerate(self.table.columns_list, start=1):
                # The first column has it's indent defined in the template
                params_out += f"  p_{column_name}\n" if column_id == 1 else  f"{tabs}, p_{column_name}\n"
        elif signature_type == "rowtype":
            params_out = ""
            for column_id, column_name in enumerate(self.table.columns_list, start=1):
                # The first column has it's indent defined in the template
                params_out += f"  p_row.{column_name}\n" if column_id == 1 else f"{tabs}, p_row.{column_name}\n"
        else:
            message = f'Expected signature_type to be either, "coltype" or "rowtype", but got "{signature_type}".'
            raise ValueError(message)

        return params_out

    def _returning_columns(self, skip_list:list = None, soft_tabs:int = 4) -> str:
        """The _returning_columns function provides the returning clause complete with columns"""
        if skip_list is None:
            skip_list = []
        tabs = "%STAB%" * soft_tabs  # The number of STABs in the respective template.
        return_columns = f"returning\n"
        column_list = self.table.in_out_column_list + self.table.out_column_list
        for column_id, column_name in enumerate(column_list, start=1):
            column_name_lc = column_name.lower()
            if column_name_lc in skip_list:
                continue
            # The first column has it's indent defined in the template
            return_columns += f"{tabs}  {column_name_lc}\n" if column_id == 1 else f"{tabs}, {column_name_lc}\n"
        return return_columns

    def _into_parameters(self, signature_type: str, skip_list:list = None, soft_tabs: int = 4) -> str:
        if skip_list is None:
            skip_list = []
        tabs = "%STAB%" * soft_tabs  # The number of STABs in the respective template.
        into_tabs = "%STAB%" * soft_tabs
        into_params = f"{into_tabs}into\n"
        column_list = column_list = self.table.in_out_column_list + self.table.out_column_list
        if signature_type == "coltype":
            column_id = 1
            for column_name in column_list:
                column_name_lc = column_name.lower()
                if column_name_lc in skip_list:
                    continue
                into_params += f"{tabs}  p_{column_name_lc}" if column_id == 1 else f"\n{tabs}, p_{column_name_lc}"
                # The first column has it's indent defined in the template
                column_id += 1
        elif signature_type == "rowtype":
            column_id = 1
            for column_name in column_list:
                column_name_lc = column_name.lower()
                if column_name_lc in skip_list:
                    continue
                # The first column has it's indent defined in the template
                into_params += f"{tabs}  p_row.{column_name_lc}" if column_id == 1 else f"\n{tabs}, p_row.{column_name_lc}"
                column_id += 1
        else:
            message = f'Expected signature_type to be either, "coltype" or "rowtype", but got "{signature_type}".'
            raise ValueError(message)

        return into_params

    def _returning_into_clause(self, signature_type: str, skip_list:list = None, soft_tabs: int = 4) -> str:
        if skip_list is None:
            skip_list = []
        returning_into_clause = self._returning_columns(skip_list=skip_list,  soft_tabs=soft_tabs)

        returning_into_clause += self._into_parameters(signature_type=signature_type, skip_list=skip_list,
                                                       soft_tabs=soft_tabs)
        return returning_into_clause

    def _mrg_param_alias_list_string(self, signature_type: str, operation_type: str = 'create', skip_list:list = None
                                     , soft_tabs: int = 4) -> str:
        """Returns a line separated (\n) list of merge parameters aliased to columns."""

        if skip_list is None:
            skip_list = []
        tabs = "%STAB%" * soft_tabs  # The number of STABs in the respective template.
        assignment = ''
        if signature_type == "coltype":
            params_out = ""
            column_id = 1
            for column_name in self.table.columns_list:
                column_name_lc = column_name.lower()
                if column_name_lc in skip_list:
                    continue
                # The first column has it's indent defined in the template
                params_out += f"  p_{column_name_lc:<30} as {column_name_lc}" if column_id == 1 else  f"\n{tabs}, p_{column_name_lc:<30} as {column_name_lc}"
                column_id += 1
        elif signature_type == "rowtype":
            params_out = ""
            column_id = 1
            for column_name in self.table.columns_list:
                column_name_lc = column_name.lower()
                if column_name_lc in skip_list:
                    continue
                # The first column has it's indent defined in the template
                if column_name_lc in self.table.pk_columns_list_lc:
                    params_out += f"  p_{column_name_lc:<34} as {column_name_lc}" if column_id == 1 else f"\n{tabs}, p_{column_name_lc:<34} as {column_name_lc}"
                else:
                    params_out += f"  p_row.{column_name_lc:<30} as {column_name_lc}" if column_id == 1 else  f"\n{tabs}, p_row.{column_name_lc:<30} as {column_name_lc}"
                column_id += 1
        else:
            message = f'Expected signature_type to be either, "coltype" or "rowtype", but got "{signature_type}".'
            raise ValueError(message)

        return params_out

    def _mrg_predicates_string(self, soft_tabs:int = 4) -> str:
        """Returns a line separated (\n) list of the predicates"""
        tabs = "%STAB%" * soft_tabs  # The number of STABs in the respective template.
        predicates_out = ""
        for column_id, column_name in enumerate(self.table.pk_columns_list, start=1):
            column_name_lc = column_name.lower()
            # The first column has it's indent defined in the template
            predicates_out += f"  tgt.{column_name_lc} = src.{column_name_lc}" if column_id == 1 else f"\n{tabs}and tgt.{column_name_lc} = src.{column_name_lc}"

        return predicates_out

    def _mrg_update_assignments_string(self, signature_type:str, operation_type:str,
                                       skip_list:list = None, soft_tabs:int = 4) -> str:
        """Returns a line separated (\n) list of the predicates"""
        if skip_list is None:
            skip_list = []
        tabs = "%STAB%" * soft_tabs  # The number of STABs in the respective template.

        set_string = ""
        column_id = 0
        for column_name in self.table.columns_list:
            column_name_lc = column_name.lower()
            if column_name in self.table.pk_columns_list:
                continue
            if column_name_lc in skip_list:
                continue
            column_id += 1
            assignment = self._column_expression(signature_type=signature_type, operation_type=operation_type,
                                                 column_name=column_name_lc)
            # The first column has it's indent defined in the template
            set_string += f"  {column_name_lc:<30} = {assignment}" if column_id == 1 else  f"\n{tabs}, {column_name_lc:<30} = {assignment}"


        return set_string

    def _mrg_src_column_list_string(self, signature_type: str, operation_type: str = 'create', skip_list:list = None,
                                    soft_tabs: int = 4) -> str:
        """Returns a line separated (\n) insert column list of the merge statement."""

        tabs = "%STAB%" * soft_tabs  # The number of STABs in the respective template.
        if skip_list is None:
            skip_list = []
        if signature_type == "coltype":
            params_out = ""
            column_id = 1
            for column_name in self.table.columns_list:
                column_name_lc = column_name.lower()
                if column_name_lc in skip_list:
                    continue
                assignment = self._column_expression(signature_type=signature_type, operation_type=operation_type,
                                                     column_name=column_name_lc)
                # The first column has it's indent defined in the template
                params_out += f"  {assignment}" if column_id == 1 else f"\n{tabs}, {assignment}"
                column_id += 1
        elif signature_type == "rowtype":
            params_out = ""
            column_id = 1
            for column_name in self.table.columns_list:
                column_name_lc = column_name.lower()
                if column_name_lc in skip_list:
                    continue
                assignment = self._column_expression(signature_type=signature_type, operation_type=operation_type,
                                                     column_name=column_name_lc)
                # The first column has it's indent defined in the template
                params_out += f"  {assignment}" if column_id == 1 else f"\n{tabs}, {assignment}"
                column_id += 1
        else:
            message = f'Expected signature_type to be either, "coltype" or "rowtype", but got "{signature_type}".'
            raise ValueError(message)

        return params_out


    def _column_list_string(self, skip_list = None, soft_tabs:int = 4, column_prefix:str = '', skip_identity: bool = True)-> str:
        """Returns a line separated (\n) list of columns.

        skip_identity=True is appropriate for insert/merge-create paths; set to False for select/get so identity PKs
        are included in the projection.
        """
        if skip_list is None:
            skip_list = []
        if skip_identity:
            skip_list = [*skip_list, *self.identity_cols_lc]

        tabs = "%STAB%" * soft_tabs  # The number of STABs in the respective template.
        columns_out = ""
        column_id = 1
        for column_name in self.table.columns_list:
            column_name_lc = column_name.lower()
            if column_name_lc in skip_list:
                continue
            # The first column has it's indent defined in the template
            columns_out += f"  {column_prefix}{column_name_lc}" if column_id == 1 else  f"\n{tabs}, {column_prefix}{column_name_lc}"
            column_id += 1

        return columns_out


    def _parameter_list_string(self, signature_type:str,
                               operation_type:str = 'select',
                               skip_list: list = None,
                               soft_tabs:int = 4,
                               skip_identity: bool = True) -> str:
        """Returns a line separated (\n) list of select columns"""

        if skip_list is None:
            skip_list = []
        # Skip identity columns for parameter/value lists when inserting/merging; include them for select
        if skip_identity:
            skip_list = [*skip_list, *self.identity_cols_lc]

        tabs = "%STAB%" * soft_tabs  # The number of STABs in the respective template.
        if signature_type == "coltype":
            params_out = ""
            column_id = 1
            for column_name in self.table.columns_list:
                column_name_lc = column_name.lower()
                if column_name_lc in skip_list:
                    continue

                assignment = self._column_expression(signature_type=signature_type, operation_type=operation_type,
                                                     column_name=column_name_lc)

                # The first column has it's indent defined in the template
                params_out += f"  {assignment}" if column_id == 1 else  f"\n{tabs}, {assignment}"
                column_id += 1
        elif signature_type == "rowtype":
            params_out = ""
            column_id = 1
            for column_name in self.table.columns_list:
                column_name_lc = column_name.lower()
                if column_name_lc in skip_list:
                    continue
                assignment = self._column_expression(signature_type=signature_type, operation_type=operation_type,
                                                     column_name=column_name_lc)
                # The first column has it's indent defined in the template
                params_out += f"  {assignment}" if column_id == 1 else f"\n{tabs}, {assignment}"
                column_id += 1
        else:
            message = f'Expected signature_type to be either, "coltype" or "rowtype", but got "{signature_type}".'
            raise ValueError(message)

        return params_out

    def _predicates_string(self, soft_tabs:int = 4) -> str:
        """Returns a line separated (\n) list of the predicates"""
        tabs = "%STAB%" * soft_tabs  # The number of STABs in the respective template.
        predicates_out = ""
        for column_id, column_name in enumerate(self.table.pk_columns_list, start=1):
            column_name_lc = column_name.lower()
            # The first column has it's indent defined in the template
            predicates_out += f"   {column_name_lc} = p_{column_name_lc}" if column_id == 1 else f"\n{tabs}  and {column_name_lc} = p_{column_name_lc}"

        return predicates_out

    def _update_assignments_string(self, signature_type:str, operation_type:str,
                                   skip_list:list = None, soft_tabs:int = 4) -> str:
        """Returns a line separated (\n) list of the predicates"""
        _operation_type = 'modify' if operation_type == 'update' else operation_type
        if skip_list is None:
            skip_list = []
        # Skip identity columns when building update assignments (insert paths not here)
        skip_list = [*skip_list, *self.identity_cols_lc]
        tabs = "%STAB%" * soft_tabs  # The number of STABs in the respective template.
        if signature_type == "coltype":
            set_string = ""
            column_id = 0
            for column_name in self.table.columns_list:
                column_name_lc = column_name.lower()
                if column_name in self.table.pk_columns_list:
                    continue
                if column_name_lc in skip_list:
                    continue
                column_id += 1
                noop_assignment = ""
                if self.noop_column_string and operation_type == 'update' and column_name_lc not in self.auto_maintained_cols_lc:
                    noop_assignment = self._noop_assignment(column_name=column_name_lc, soft_tabs=14)
                if not noop_assignment:
                    assignment = self._column_expression(signature_type=signature_type, operation_type=_operation_type,
                                                         column_name=column_name_lc)
                else:
                    assignment = noop_assignment
                # The first column has it's indent defined in the template
                set_string += f" {column_name_lc:<30} = {assignment}" if column_id == 1 else  f"\n{tabs}, {column_name_lc:<30} = {assignment}"
        elif signature_type == "rowtype":
            set_string = ""
            column_id = 0
            for column_name in self.table.columns_list:
                column_name_lc = column_name.lower()
                if column_name in self.table.pk_columns_list:
                    continue
                # Skip trigger-maintained audit columns and row version when using triggers
                if self.col_auto_maintain_method == 'trigger' and (column_name_lc in self.auto_maintained_cols_lc or column_name_lc == self.table.row_vers_column_name):
                    continue
                column_id += 1

                assignment = self._column_expression(signature_type=signature_type, operation_type=_operation_type,
                                                     column_name=column_name_lc)
                # The first column has it's indent defined in the template
                set_string += f" {column_name_lc:<30} = {assignment}" if column_id == 1 else  f"\n{tabs}, {column_name_lc:<30} = {assignment}"
        else:
            message = f'Expected signature_type to be either, "coltype" or "rowtype", but got "{signature_type}".'
            raise ValueError(message)

        return set_string

    def _return_parameter_list(self, signature_type:str, soft_tabs:int = 4) -> str:
        """Returns a comma separated list of the parameters into which to return the "out and "in out" values following
        an insert/update operation."""
        tabs = "%STAB%" * soft_tabs  # The number of STABs in the respective template.
        returns_out = ""
        if signature_type == "coltype":
            for column_id, column_name in enumerate(chain(self.table.in_out_column_list,
                                                          self.table.out_column_list), start=1):
                column_name_lc = column_name.lower()
                # The first column has it's indent defined in the template
                returns_out += f"\n{tabs}  p_{column_name_lc}" if column_id == 1 else  f"\n{tabs}, p_{column_name_lc}"
        elif signature_type == "rowtype":
            for column_id, column_name in enumerate(chain(self.table.in_out_column_list,
                                                          self.table.out_column_list), start=1):
                column_name_lc = column_name.lower()
                # The first column has it's indent defined in the template
                returns_out += f"\n{tabs}  p_row.{column_name_lc}" if column_id == 1 else f"\n{tabs}, p_row.{column_name_lc}"
        else:
            message = f'Expected signature_type to be either, "coltype" or "rowtype", but got "{signature_type}".'
            raise ValueError(message)
        return returns_out

    def _return_columns_list(self, soft_tabs:int = 4) -> str:
        """Returns a comma separated list of the columns from which to return the "out and "in out" values following an
        insert/update operation."""
        tabs = "%STAB%" * soft_tabs  # The number of STABs in the respective template.
        returns_out = ""

        for column_id, column_name in enumerate(chain(self.table.in_out_column_list,
                                                      self.table.out_column_list), start=1):
            column_name_lc = column_name.lower()
            # The first column has it's indent defined in the template
            returns_out += f"\n{tabs}  {column_name_lc}" if column_id == 1 else  f"\n{tabs}, {column_name_lc}"

        return returns_out

    def _package_api_template(self, template_category: str, template_type: str, template_name: str) -> str:
        """
        Reads and returns the content of a specified template file. The "package" templates are used to format the
        package header and footer components.

        :param template_category: Maps to one of the templates' subdirectories (e.g., "package", "procedures").
        :type template_category: str
        :param template_type: The template type, e.g., "body" or "spec".
        :type template_type: str
        :param template_name: The name of the template file to read.
        :type template_name: str
        :return: The content of the template file.
        :rtype: str
        :raises FileNotFoundError: If the template file is not found.
        :raises IOError: If the file cannot be read for any reason.
        """

        # Define the template file path
        template_name = str(template_name).replace(".tpt", "")
        template_name += ".tpt"
        template_path = resolve_path(TEMPLATES_LOCATION / template_category / template_type / template_name)

        try:
            # Read the template file
            return template_path.read_text()
        except FileNotFoundError:
            raise FileNotFoundError(f"Template file not found: {template_path}")
        except IOError as e:
            raise IOError(f"Failed to read template file: {template_path}. Error: {e}")

    def comment_tapi(self, tapi_description:str):
        STAB = self.global_substitutions["STAB"]
        ts_len = len(STAB)
        dash_line = 80 - ts_len

        comment = "\n\n"
        comment += f"{STAB}" + "-" * dash_line + "\n"
        comment += f"{STAB}-- {tapi_description} TAPI for: {self.table_owner.lower()}.{self.table.table_name.lower()}\n"
        comment += f"{STAB}" + "-" * dash_line + "\n"
        return comment

    def _delete_api_sig(self,
                        signature_type: str,
                        package_spec: bool = True,
                        inc_comments: bool = True,
                        procedure_name:str = 'del') -> str:
        """
        Processes the `delete` API specification.

        This function is called to generate an API signature. As such it is shared for package specification and
        package body code generation.

        For deletes, the signature_type has no effect.


        :param signature_type: Defines the type of signature.
        :param package_spec: Set to True for a package spec; False for package body (omits semicolon)
        :param inc_comments: Set to true to include generated comments before procedure declaration.
        :param procedure_name: The name assigned to the delete procedure.
        :return: A string containing the `delete` API fragment
        :rtype: str
        """
        STAB = self.global_substitutions["STAB"]

        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Delete')

        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.api_target_name_lc
        predicate_num = 0
        for col_position, column_name in enumerate(self.table.columns_list, start = 1):
            column_name_lc = column_name.lower()
            # if not column_name in self.table.pk_columns_list and column_name_lc != self.table.row_vers_column_name:
            if column_name not in self.table.in_out_column_list and column_name not in self.table.out_column_list:
                continue
            predicate_num += 1
            leader = f', ' if predicate_num > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{column_name_lc.ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            if column_name_lc in self.table.in_out_column_list_lc:
                in_out = f'{STAB}in out'
            elif column_name_lc in self.table.out_column_list_lc:
                in_out = f'{STAB}   out'
            else:
                in_out = f'{STAB}in    '
            param += in_out
            param += f"{STAB}{table_name_lc}.{column_name_lc}%type"
            signature += param + '\n'
            param = ''

        if self.include_commit:
            leader = f', ' if self.table.col_count > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{"commit".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in    '
            param += in_out
            param += f'{STAB}boolean'
            param = f"{param:<99}"
            param += f'{STAB} := false'
            signature += param + '\n'


        if package_spec:
            signature += f'{STAB})'
            signature += ';\n'
        else:
            signature += f'{STAB})\n'
            signature += f'{STAB}is'

        return signature

    def _insert_api_coltype_sig(self,
                               package_spec: bool = True,
                               inc_comments: bool = True,
                               procedure_name:str = 'ins') -> str:
        """
        Processes the `insert` coltype API signature.

        This function is called to generate an API signature. As such it is shared for package specification and
        package body code generation.

        :param package_spec: Set to True for a package spec; False for package body (omits semicolon)
        :param inc_comments: Set to true to include generated comments before procedure declaration.
        :param procedure_name: The name assigned to the insert procedure.
        :return: A string containing the `insert` API fragment
        :rtype: str
        """

        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Insert')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.api_target_name_lc

        processed_columns = 0

        for col_position, column_name in enumerate(self.table.columns_list, start = 1):
            column_name_lc = column_name.lower()
            if column_name_lc in self.auto_maintained_cols:
                continue
            if self.table.is_identity_always(column_name):
                continue

            processed_columns += 1
            is_key_col = self.table.column_property_value(column_name=column_name, property_name="is_key_column")
            is_row_version_column = self.table.column_property_value(column_name=column_name,
                                                                     property_name="is_row_version_column")
            default_value = self.table.column_property_value(column_name=column_name, property_name="default_value")
            leader = f', ' if processed_columns > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{column_name_lc.ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'

            if column_name_lc in self.table.in_out_column_list_lc:
                in_out = f'{STAB}in out'
            elif column_name_lc in self.table.out_column_list_lc:
                in_out = f'{STAB}   out'
            else:
                in_out = f'{STAB}in    '

            param += in_out
            param += f"{STAB}{table_name_lc}.{column_name_lc}%type"
            if self.include_defaults and default_value and column_name not in self.table.out_column_list \
                    and column_name not in self.table.in_out_column_list:
                param = f"{param:<99}"
                param += f'{STAB} := {default_value}'

            signature += param + '\n'
            param = ''

        if self.include_commit:
            leader = f', ' if self.table.col_count > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{"commit".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in    '
            param += in_out
            param += f'{STAB}boolean'
            param = f"{param:<99}"
            param += f'{STAB} := false'
            signature += param + '\n'

        if package_spec:
            signature += f'{STAB})'
            signature += ';\n'
        else:
            signature += f'{STAB})\n'
            signature += f'{STAB}is'

        return signature

    def _insert_api_rowtype_sig(self,
                               package_spec: bool = True,
                               inc_comments: bool = True,
                               procedure_name:str = 'ins') -> str:
        """
        Processes the `insert` rowtype API signature.

        This function is called to generate an API signature. As such it is shared for package specification and
        package body code generation.

        :param package_spec: Set to True for a package spec; False for package body (omits semicolon)
        :param inc_comments: Set to true to include generated comments before procedure declaration.
        :param procedure_name: The name assigned to the insert procedure.
        :return: A string containing the `insert` API fragment
        :rtype: str
        """
        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Insert')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.api_target_name_lc

        processed_columns = 0

        for col_position, column_name in enumerate(self.table.pk_columns_list, start = 1):
            if column_name.lower() in self.auto_maintained_cols:
                continue
            if self.table.is_identity(column_name):
                continue
            processed_columns += 1
            column_name_lc = column_name.lower()
            default_value = self.table.column_property_value(column_name=column_name, property_name="default_value")
            leader = f', ' if processed_columns > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{column_name_lc.ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in    '
            param += in_out
            param += f"{STAB}{table_name_lc}.{column_name_lc}%type"
            if self.include_defaults and default_value:
                param = f"{param:<99}"
                param += f'{STAB} := {default_value}'


            signature += param + '\n'
            param = ''

        # If no PK params were emitted (e.g. identity PK skipped), start p_row without a leading comma
        leader = f', ' if processed_columns > 0 else f'  '
        param = f'{STAB}{STAB}{leader}p_{"row".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
        in_out = f'{STAB}in out'
        param += in_out
        param += f'{STAB}{table_name_lc}%rowtype'
        signature += param + '\n'

        if self.include_commit:
            leader = f', ' if self.table.col_count > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{"commit".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in    '
            param += in_out
            param += f'{STAB}boolean'
            param = f"{param:<99}"
            param += f'{STAB} := false'
            signature += param + '\n'

        if package_spec:
            signature += f'{STAB})'
            signature += ';\n'
        else:
            signature += f'{STAB})\n'
            signature += f'{STAB}is'

        return signature

    def _insert_api_sig(self,
                        signature_type: str,
                        package_spec: bool = True,
                        inc_comments: bool = True,
                        procedure_name:str = 'ins') -> str:
        """
        Processes the `insert` API signature.

        This function is called to generate an API signature. As such it is shared for package specification and
        package body code generation.

        The signature_type defines the type of signature: "rowtype" indicates that the procedure signature is based, on
        all column parameters contained in a %rowtype container. If set to "coltype" then there is a parameter per
        table column.

        :param signature_type: This should be presented a "rowtype" or "coltype".
        :param package_spec: Set to True for a package spec; False for package body (omits semicolon)
        :param inc_comments: Set to true to include generated comments before procedure declaration.
        :param procedure_name: The name assigned to the insert procedure.
        :return: A string containing the `insert` API fragment
        :rtype: str
        """
        signature = ''
        if signature_type == 'coltype':
            signature = self._insert_api_coltype_sig(package_spec=package_spec,
                                                     inc_comments=inc_comments,
                                                     procedure_name=procedure_name)
        else:
            signature = self._insert_api_rowtype_sig(package_spec=package_spec,
                                                     inc_comments=inc_comments,
                                                     procedure_name=procedure_name)


        return signature

    def _select_api_coltype_sig(self,
                               package_spec: bool = True,
                               inc_comments: bool = True,
                               procedure_name:str = 'sel') -> str:

        """
        Processes the `select` coltype API specification.

        This function is called to generate an API signature. As such it is shared for package specification and
        package body code generation.

        :param package_spec: If set to True, the generated code snippet, is for a procedure specification.
        :param inc_comments: Set to True to include basic comments before the procedure.
        :param procedure_name: The name to assign to the select procedure.
        :return: A string containing the `select` API signature fragment
        :rtype: str"""

        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Select')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.api_target_name_lc

        processed_columns = 0

        for col_position, column_name in enumerate(self.table.columns_list, start = 1):

            processed_columns += 1
            column_name_lc = column_name.lower()

            leader = f', ' if processed_columns > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{column_name_lc.ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'

            if column_name_lc in self.table.in_out_column_list_lc:
                in_out = f'{STAB}in out'
            elif column_name_lc in self.table.out_column_list_lc:
                in_out = f'{STAB}   out'
            else:
                in_out = f'{STAB}   out'

            param += in_out
            param += f"{STAB}{table_name_lc}.{column_name_lc}%type"

            signature += param + '\n'
            param = ''

        if package_spec:
            signature += f'{STAB})'
            signature += ';\n'
        else:
            signature += f'{STAB})\n'
            signature += f'{STAB}is'

        return signature

    def _select_api_rowtype_sig(self,
                               package_spec: bool = True,
                               inc_comments: bool = True,
                               procedure_name:str = 'sel') -> str:
        """
        Processes the `select` rowtype API specification.

        This function is called to generate an API signature. As such it is shared for package specification and
        package body code generation.

        :param package_spec: If set to True, the generated code snippet, is for a procedure specification.
        :param inc_comments: Set to True to include basic comments before the procedure.
        :param procedure_name: The name to assign to the select procedure.
        :return: A string containing the `select` API signature fragment
        :rtype: str"""

        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Select')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'

        signature += f'{STAB}(\n'
        table_name_lc = self.api_target_name_lc

        processed_columns = 0

        for col_position, column_name in enumerate(self.table.columns_list, start = 1):
            if column_name.lower() in self.auto_maintained_cols:
                continue
            # keep identity PKs in select predicates
            if not self.table.column_property_value(column_name=column_name, property_name='is_pk_column'):
                continue
            processed_columns += 1

            column_name_lc = column_name.lower()
            leader = f', ' if processed_columns > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{column_name_lc.ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in    '
            param += in_out
            param += f"{STAB}{table_name_lc}.{column_name_lc}%type"


            signature += param + '\n'
            param = ''

        leader = f', '
        param = f'{STAB}{STAB}{leader}p_{"row".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
        in_out = f'{STAB}   out'
        param += in_out
        param += f'{STAB}{table_name_lc}%rowtype'
        signature += param + '\n'

        if package_spec:
            signature += f'{STAB})'
            signature += ';\n'
        else:
            signature += f'{STAB})\n'
            signature += f'{STAB}is'

        return signature

    def _select_api_sig(self,
                        signature_type: str,
                        package_spec: bool = True,
                        inc_comments: bool = True,
                        procedure_name:str = 'get') -> str:
        """
        Processes the `select` API specification.

        This function is called to generate an API signature. As such it is shared for package specification and
        package body code generation.

        The signature_type defines the type of signature: "rowtype" indicates that the procedure signature is based, on
        all column parameters contained in a %rowtype container. If set to "coltype" then there is a parameter per
        table column.

        :param signature_type: This should be presented a "rowtype" or "coltype".
        :param package_spec: If set to True, the generated code snippet, is for a procedure specification.
        :param inc_comments: Set to True to include basic comments before the procedure.
        :param procedure_name: The name to assign to the select procedure.
        :return: A string containing the `select` API signature fragment
        :rtype: str
        """

        signature = ''
        if signature_type == 'coltype':
            signature = self._select_api_coltype_sig(package_spec=package_spec,
                                                     inc_comments=inc_comments,
                                                     procedure_name=procedure_name)
        else:
            signature = self._select_api_rowtype_sig(package_spec=package_spec,
                                                     inc_comments=inc_comments,
                                                     procedure_name=procedure_name)


        return signature

    def _update_api_coltype_sig(self,
                                package_spec: bool = True,
                                inc_comments: bool = True,
                                procedure_name:str = 'upd') -> str:
        """
        Processes the `update` coltype API signature.

        This function is called to generate a rowtype API signature. As such it is shared for package specification and
        package body code generation.

        :param package_spec: Set to True for a package spec; False for package body (omits semicolon)
        :param inc_comments: Set to true to include generated comments before procedure declaration.
        :param procedure_name: The name assigned to the update procedure.
        :return: A string containing the `update` API fragment
        :rtype: str
        """
        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Update')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.api_target_name_lc

        processed_columns = 0

        for col_position, column_name in enumerate(self.table.columns_list, start = 1):
            column_name_lc = column_name.lower()
            if column_name_lc in self.auto_maintained_cols:
                continue

            processed_columns += 1

            leader = f', ' if processed_columns > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{column_name_lc.ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'

            if column_name_lc in self.table.in_out_column_list_lc:
                in_out = f'{STAB}in out'
            elif column_name_lc in self.table.out_column_list_lc:
                in_out = f'{STAB}   out'
            else:
                in_out = f'{STAB}in    '

            param += in_out
            param += f"{STAB}{table_name_lc}.{column_name_lc}%type"
            block_list = self.table.in_out_column_list + [self.table.row_vers_column_name.upper()]

            data_type = self.table.column_property_value(column_name=column_name, property_name='data_type')
            if self.noop_column_string and column_name not in block_list and data_type in NO_OP_DATA_TYPES:
                param = f"{param:<99}"
                param += f"{STAB} := NOOP"

            signature += param + '\n'
            param = ''

        if self.include_commit:
            leader = f', ' if self.table.col_count > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{"commit".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in    '
        if self.include_commit:
            leader = f', ' if self.table.col_count > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{"commit".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in    '
            param += in_out
            param += f'{STAB}boolean'
            param = f"{param:<99}"
            param += f'{STAB} := false'
            signature += param + '\n'

        if package_spec:
            signature += f'{STAB})'
            signature += ';\n'
        else:
            signature += f'{STAB})\n'
            signature += f'{STAB}is'

        return signature

    def _update_api_rowtype_sig(self,
                               package_spec: bool = True,
                               inc_comments: bool = True,
                               procedure_name:str = 'upd') -> str:
        """
        Processes the `update` rowtype API signature.

        This function is called to generate a rowtype API signature. As such it is shared for package specification and
        package body code generation.

        :param package_spec: Set to True for a package spec; False for package body (omits semicolon)
        :param inc_comments: Set to true to include generated comments before procedure declaration.
        :param procedure_name: The name assigned to the update procedure.
        :return: A string containing the `update` API fragment
        :rtype: str
        """
        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Update')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.api_target_name_lc

        processed_columns = 0

        for col_position, column_name in enumerate(self.table.columns_list, start = 1):
            if column_name.lower() in self.auto_maintained_cols:
                continue
            # keep identity PKs as update predicates
            if not self.table.column_property_value(column_name=column_name, property_name='is_pk_column'):
                continue
            processed_columns += 1
            is_key_col = self.table.column_property_value(column_name=column_name, property_name="is_key_column")
            column_name_lc = column_name.lower()
            leader = f', ' if processed_columns > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{column_name_lc.ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in    '
            param += in_out
            param += f"{STAB}{table_name_lc}.{column_name_lc}%type"

            signature += param + '\n'
            param = ''

        leader = f', '
        param = f'{STAB}{STAB}{leader}p_{"row".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
        in_out = f'{STAB}in out'
        param += in_out
        param += f'{STAB}{table_name_lc}%rowtype'
        signature += param + '\n'

        if self.include_commit:
            leader = f', ' if self.table.col_count > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{"commit".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in    '
            param += in_out
            param += f'{STAB}boolean'
            param = f"{param:<99}"
            param += f'{STAB} := false'
            signature += param + '\n'

        if package_spec:
            signature += f'{STAB})'
            signature += ';\n'
        else:
            signature += f'{STAB})\n'
            signature += f'{STAB}is'

        return signature

    def _update_api_sig(self,
                        signature_type: str,
                        package_spec: bool = True,
                        inc_comments: bool = True,
                        procedure_name:str = 'upd') -> str:
        """
        Processes the `update` API signature.

        This function is called to generate an API signature. As such it is shared for package specification and
        package body code generation.

        The signature_type defines the type of signature: "rowtype" indicates that the procedure signature is based, on
        all column parameters contained in a %rowtype container. If set to "coltype" then there is a parameter per
        table column.

        :param signature_type: This should be presented a "rowtype" or "coltype".
        :param package_spec: Set to True for a package spec; False for package body (omits semicolon)
        :param inc_comments: Set to true to include generated comments before procedure declaration.
        :param procedure_name: The name assigned to the update procedure.
        :return: A string containing the `update` API fragment
        :rtype: str
        """
        signature = ''
        if signature_type == 'coltype':
            signature = self._update_api_coltype_sig(package_spec=package_spec,
                                                     inc_comments=inc_comments,
                                                     procedure_name=procedure_name)
        else:
            signature = self._update_api_rowtype_sig(package_spec=package_spec,
                                                     inc_comments=inc_comments,
                                                     procedure_name=procedure_name)


        return signature

    def _upsert_api_coltype_sig(self,
                                package_spec: bool = True,
                                inc_comments: bool = True,
                                procedure_name:str = 'ups') -> str:
        """
        Processes the `upsert` coltype API signature.

        This function is called to generate an API signature. As such it is shared for package specification and
        package body code generation.

        :param package_spec: Set to True for a package spec; False for package body (omits semicolon)
        :param inc_comments: Set to true to include generated comments before procedure declaration.
        :param procedure_name: The name assigned to the insert procedure.
        :return: A string containing the `insert` API fragment
        :rtype: str
        """
        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Upsert')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.api_target_name_lc

        processed_columns = 0

        for col_position, column_name in enumerate(self.table.columns_list, start = 1):
            if column_name.lower() in self.auto_maintained_cols:
                continue

            processed_columns += 1
            is_key_col = self.table.column_property_value(column_name=column_name, property_name="is_key_column")
            is_row_version_column = self.table.column_property_value(column_name=column_name,
                                                                     property_name="is_row_version_column")
            column_name_lc = column_name.lower()
            leader = f', ' if processed_columns > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{column_name_lc.ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'

            if column_name_lc in self.table.in_out_column_list_lc:
                in_out = f'{STAB}in out'
            elif column_name_lc in self.table.out_column_list_lc:
                in_out = f'{STAB}   out'
            else:
                in_out = f'{STAB}in    '

            param += in_out
            param += f"{STAB}{table_name_lc}.{column_name_lc}%type"

            signature += param + '\n'
            param = ''

        if self.include_commit:
            leader = f', ' if self.table.col_count > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{"commit".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in    '
            param += in_out
            param += f'{STAB}boolean'
            param = f"{param:<99}"
            param += f'{STAB} := false'
            signature += param + '\n'

        if package_spec:
            signature += f'{STAB})'
            signature += ';\n'
        else:
            signature += f'{STAB})\n'
            signature += f'{STAB}is'

        return signature

    def _upsert_api_rowtype_sig(self,
                               package_spec: bool = True,
                               inc_comments: bool = True,
                               procedure_name:str = 'ups') -> str:
        """
        Processes the `upsert` rowtype API signature.

        This function is called to generate an API signature. As such it is shared for package specification and
        package body code generation.

        :param package_spec: Set to True for a package spec; False for package body (omits semicolon)
        :param inc_comments: Set to true to include generated comments before procedure declaration.
        :param procedure_name: The name assigned to the insert procedure.
        :return: A string containing the `insert` API fragment
        :rtype: str
        """

        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Upsert')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.api_target_name_lc

        processed_columns = 0

        for col_position, column_name in enumerate(self.table.columns_list, start = 1):
            if column_name.lower() in self.auto_maintained_cols:
                continue
            if not self.table.column_property_value(column_name=column_name, property_name='is_pk_column'):
                continue
            processed_columns += 1
            column_name_lc = column_name.lower()
            leader = f', ' if processed_columns > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{column_name_lc.ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in    '
            param += in_out
            param += f"{STAB}{table_name_lc}.{column_name_lc}%type"


            signature += param + '\n'
            param = ''

        leader = f', '
        param = f'{STAB}{STAB}{leader}p_{"row".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
        in_out = f'{STAB}in out'
        param += in_out
        param += f'{STAB}{table_name_lc}%rowtype'
        signature += param + '\n'

        if self.include_commit:
            leader = f', ' if self.table.col_count > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{"commit".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in    '
            param += in_out
            param += f'{STAB}boolean'
            param = f"{param:<99}"
            param += f'{STAB} := false'
            signature += param + '\n'

        if package_spec:
            signature += f'{STAB})'
            signature += ';\n'
        else:
            signature += f'{STAB})\n'
            signature += f'{STAB}is'

        return signature


    def _upsert_api_sig(self,
                        signature_type: str,
                        package_spec: bool = True,
                        inc_comments: bool = True,
                        procedure_name:str = 'ups') -> str:
        """
        Processes the `upsert` API signature.

        This function is called to generate an API signature. As such it is shared for package specification and
        package body code generation.

        The signature_type defines the type of signature: "rowtype" indicates that the procedure signature is based, on
        all column parameters contained in a %rowtype container. If set to "coltype" then there is a parameter per
        table column.

        :param signature_type: This should be presented a "rowtype" or "coltype".
        :param package_spec: Set to True for a package spec; False for package body (omits semicolon)
        :param inc_comments: Set to true to include generated comments before procedure declaration.
        :param procedure_name: The name assigned to the insert procedure.
        :return: A string containing the `insert` API fragment
        :rtype: str
        """
        signature = ''
        if signature_type == 'coltype':
            signature = self._upsert_api_coltype_sig(package_spec=package_spec,
                                                     inc_comments=inc_comments,
                                                     procedure_name=procedure_name)
        else:
            signature = self._upsert_api_rowtype_sig(package_spec=package_spec,
                                                     inc_comments=inc_comments,
                                                     procedure_name=procedure_name)


        return signature

    def _merge_api_coltype_sig(self,
                                package_spec: bool = True,
                                inc_comments: bool = True,
                                procedure_name: str = 'mrg') -> str:
        """
         Processes the `merge` coltype API signature.

         This function is called to generate an API signature. As such it is shared for package specification and
         package body code generation.


         :param package_spec: Set to True for a package spec; False for package body (omits semicolon)
         :param inc_comments: Set to true to include generated comments before procedure declaration.
         :param procedure_name: The name assigned to the insert procedure.
         :return: A string containing the `insert` API fragment
         :rtype: str
         """

        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Merge')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.api_target_name_lc

        processed_columns = 0

        for col_position, column_name in enumerate(self.table.columns_list, start=1):
            if column_name.lower() in self.auto_maintained_cols:
                continue

            processed_columns += 1
            is_key_col = self.table.column_property_value(column_name=column_name, property_name="is_key_column")
            is_row_version_column = self.table.column_property_value(column_name=column_name,
                                                                     property_name="is_row_version_column")
            column_name_lc = column_name.lower()

            leader = f', ' if processed_columns > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{column_name_lc.ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'


            in_out = f'{STAB}in    '

            param += in_out
            param += f"{STAB}{table_name_lc}.{column_name_lc}%type"

            signature += param + '\n'
            param = ''

        if self.include_commit:
            leader = f', ' if self.table.col_count > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{"commit".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in    '
        if self.include_commit:
            leader = f', ' if self.table.col_count > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{"commit".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in    '
            param += in_out
            param += f'{STAB}boolean'
            param = f"{param:<99}"
            param += f'{STAB} := false'
            signature += param + '\n'

        if package_spec:
            signature += f'{STAB})'
            signature += ';\n'
        else:
            signature += f'{STAB})\n'
            signature += f'{STAB}is'

        return signature

    def _merge_api_rowtype_sig(self,
                                package_spec: bool = True,
                                inc_comments: bool = True,
                                procedure_name: str = 'mrg') -> str:
        """
         Processes the `merge` rowtype API signature.

         This function is called to generate an API signature. As such it is shared for package specification and
         package body code generation.


         :param package_spec: Set to True for a package spec; False for package body (omits semicolon)
         :param inc_comments: Set to true to include generated comments before procedure declaration.
         :param procedure_name: The name assigned to the insert procedure.
         :return: A string containing the `insert` API fragment
         :rtype: str
         """

        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Merge')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.api_target_name_lc

        processed_columns = 0

        for col_position, column_name in enumerate(self.table.columns_list, start=1):
            if column_name.lower() in self.auto_maintained_cols:
                continue
            if not self.table.column_property_value(column_name=column_name, property_name='is_pk_column'):
                continue
            processed_columns += 1
            is_key_col = self.table.column_property_value(column_name=column_name, property_name="is_key_column")
            column_name_lc = column_name.lower()
            default_value = self.table.column_property_value(column_name=column_name, property_name="default_value")
            leader = f', ' if processed_columns > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{column_name_lc.ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in    '
            param += in_out
            param += f"{STAB}{table_name_lc}.{column_name_lc}%type"

            signature += param + '\n'
            param = ''

        leader = f', '
        param = f'{STAB}{STAB}{leader}p_{"row".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
        in_out = f'{STAB}in    '
        param += in_out
        param += f'{STAB}{table_name_lc}%rowtype'
        signature += param + '\n'


        if self.include_commit:
            leader = f', ' if self.table.col_count > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{"commit".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in    '
            param += in_out
            param += f'{STAB}boolean'
            param = f"{param:<99}"
            param += f'{STAB} := false'
            signature += param + '\n'

        if package_spec:
            signature += f'{STAB})'
            signature += ';\n'
        else:
            signature += f'{STAB})\n'
            signature += f'{STAB}is'

        return signature

    def _merge_api_sig(self,
                        signature_type: str,
                        package_spec: bool = True,
                        inc_comments: bool = True,
                        procedure_name: str = 'mrg') -> str:
        """
        Processes the `merge` API signature.

        This function is called to generate an API signature. As such it is shared for package specification and
        package body code generation.

        The signature_type defines the type of signature: "rowtype" indicates that the procedure signature is based, on
        all column parameters contained in a %rowtype container. If set to "coltype" then there is a parameter per
        table column.

        :param signature_type: This should be presented a "rowtype" or "coltype".
        :param package_spec: Set to True for a package spec; False for package body (omits semicolon)
        :param inc_comments: Set to true to include generated comments before procedure declaration.
        :param procedure_name: The name assigned to the insert procedure.
        :return: A string containing the `insert` API fragment
        :rtype: str
        """
        signature = ''
        if signature_type == 'coltype':
            signature = self._merge_api_coltype_sig(package_spec=package_spec,
                                                    inc_comments=inc_comments,
                                                    procedure_name=procedure_name)
        else:
            signature = self._merge_api_rowtype_sig(package_spec=package_spec,
                                                    inc_comments=inc_comments,
                                                    procedure_name=procedure_name)

        return signature


    def _insert_api_body(self, signature_type: str, procedure_name:str = 'ins') -> str:
        """Put together the "insert" procedure and its body"""
        procedure_signature = self._insert_api_sig(signature_type=signature_type, package_spec=False,
                                                   procedure_name=procedure_name) + ""
        procedure_body_template = self._package_api_template(template_category="packages", template_type='procedures',
                                                             template_name=f"insert")
        if self.include_commit:
            procedure_body_template = self._inject_commit_logic(procedure_template=procedure_body_template)

        skip_column_list = []
        if self.col_auto_maintain_method == 'trigger':
            skip_column_list = self.auto_maintained_cols[:]
            skip_column_list.append(self.table.row_vers_column_name)

        column_list_string = self._column_list_string(skip_list=skip_column_list, soft_tabs=4)
        # Get the inserted / parameters and expressions
        parameter_list_string_lc = self._parameter_list_string(operation_type='create',
                                                               signature_type=signature_type,
                                                               skip_list=skip_column_list,
                                                               soft_tabs=4)
        parameter_list_string = parameter_list_string_lc.upper()

        logger_skip_list = [*skip_column_list, *self.identity_cols_lc]
        logger_params_append_lc = self._logger_appends(signature_type=signature_type, soft_tabs=2, skip_list=logger_skip_list)

        returning_clause_lc = ''
        if self.return_pk_columns or self.return_ak_columns:
            returning_clause_lc = self._returning_into_clause(signature_type=signature_type, soft_tabs=4)

        substitutions_dict = {
                              "key_predicates_string": column_list_string.upper(),
                              "column_list_string_lc": column_list_string,
                              "logger_params_append_lc": logger_params_append_lc,
                              "parameter_list_string_lc": parameter_list_string_lc,
                              "parameter_list_string": parameter_list_string,
                              "returning_clause_lc": returning_clause_lc,
                              "returning_clause": returning_clause_lc.upper(),
                              "procedure_signature": procedure_signature,
                              "procedure_name": procedure_name,
                              "procname": procedure_name,
                              "table_name_lc": self.api_target_name_lc,
                              "table_name": self.api_target_name_lc.upper()}

        procedure_body_template = inject_values(substitutions=substitutions_dict,
                                                target_string=procedure_body_template,
                                                stab_spaces=self.indent_spaces)

        return procedure_body_template

    def _select_api_body(self, signature_type: str, procedure_name:str = 'ins') -> str:
        """Put together the "select" procedure and its body"""
        procedure_signature = self._select_api_sig(signature_type=signature_type, package_spec=False,
                                                   procedure_name=procedure_name) + ""
        procedure_body_template = self._package_api_template(template_category="packages", template_type='procedures',
                                                             template_name=f"select")

        column_list_string_lc = self._column_list_string(soft_tabs=3, skip_identity=False)

        parameter_list_string_lc = self._parameter_list_string(signature_type=signature_type,
                                                               operation_type='select',
                                                               soft_tabs=3,
                                                               skip_identity=False)
        parameter_list_string = parameter_list_string_lc.upper()

        # Convert to lowercase for comparison, return lowercase results. We want a list of columns which are
        # not primary key columns.
        skip_list = [item.lower() for item in self.table.columns_list if item.lower() not in [entry.lower() for entry in self.table.pk_columns_list]]
        logger_params_append_lc = self._logger_appends(signature_type=signature_type, soft_tabs=2,
                                                       skip_list=skip_list)

        key_predicates_string = self._predicates_string(soft_tabs=2)

        substitutions_dict = {"column_list_string": column_list_string_lc.upper(),
                              "column_list_string_lc": column_list_string_lc,
                              "key_predicates_string": key_predicates_string.upper(),
                              "key_predicates_string_lc": key_predicates_string,
                              "logger_params_append_lc": logger_params_append_lc,
                              "parameter_list_string_lc": parameter_list_string_lc,
                              "parameter_list_string": parameter_list_string,
                              "procedure_signature": procedure_signature,
                              "procedure_name": procedure_name,
                              "procname": procedure_name,
                              "table_name_lc": self.api_target_name_lc,
                              "table_name": self.api_target_name_lc.upper()}

        procedure_body_template = inject_values(substitutions=substitutions_dict,
                                                target_string=procedure_body_template,
                                                stab_spaces=self.indent_spaces)

        return procedure_body_template


    def _update_api_body(self, signature_type: str, procedure_name:str = 'ins') -> str:
        """Put together the "update" procedure and its body"""
        procedure_signature = self._update_api_sig(signature_type=signature_type, package_spec=False,
                                                   procedure_name=procedure_name) + ""
        procedure_body_template = self._package_api_template(template_category="packages", template_type='procedures',
                                                             template_name=f"update")
        if self.include_commit:
            procedure_body_template = self._inject_commit_logic(procedure_template=procedure_body_template)

        skip_column_list = []
        if self.col_auto_maintain_method == 'trigger':
            skip_column_list = self.auto_maintained_cols[:]
            skip_column_list.append(self.table.row_vers_column_name)

        key_predicates_string = self._predicates_string(soft_tabs=3)

        update_assignments_string = self._update_assignments_string(signature_type=signature_type,
                                                                    skip_list=skip_column_list,
                                                                    operation_type='update', soft_tabs=3)

        logger_params_append_lc = self._logger_appends(signature_type=signature_type, soft_tabs=2,
                                                       skip_list=skip_column_list)
        skip_column_list = []
        if self.table.row_vers_column_name and self.col_auto_maintain_method == 'trigger':
            skip_column_list = self.auto_maintained_cols[:]
            skip_column_list.append(self.table.row_vers_column_name)

        returning_clause_lc = ''
        if self.return_pk_columns or self.return_ak_columns:
            returning_clause_lc = self._returning_into_clause(signature_type=signature_type, soft_tabs=4)

        substitutions_dict = {"key_predicates_string": key_predicates_string.upper(),
                              "key_predicates_string_lc": key_predicates_string,
                              "logger_params_append_lc":logger_params_append_lc,
                              "update_assignments_string": update_assignments_string.upper(),
                              "update_assignments_string_lc": update_assignments_string,
                              "returning_clause": returning_clause_lc.upper(),
                              "returning_clause_lc": returning_clause_lc,
                              "procedure_signature": procedure_signature,
                              "procedure_name": procedure_name,
                              "procname": procedure_name,
                              "table_name_lc": self.api_target_name_lc,
                              "table_name": self.api_target_name_lc.upper()}

        procedure_body_template = inject_values(substitutions=substitutions_dict,
                                                target_string=procedure_body_template,
                                                stab_spaces=self.indent_spaces)


        return procedure_body_template


    def _upsert_api_body(self, signature_type: str, procedure_name:str = 'ins') -> str:
        """Construct the "upsert" procedure and its body
        :param signature_type: Signature format: "coltype" or "rowtype"
        :param procedure_name: The name to assign the procedure.
        :return: The procedure body of an upsert operation.
        """
        procedure_signature = self._upsert_api_sig(signature_type=signature_type, package_spec=False,
                                                   procedure_name=procedure_name) + ""
        procedure_body_template = self._package_api_template(template_category="packages", template_type='procedures',
                                                             template_name=f"upsert")

        if self.include_commit:
            procedure_body_template = self._inject_commit_logic(procedure_template=procedure_body_template)

        skip_column_list = []
        if self.table.row_vers_column_name and self.col_auto_maintain_method == 'trigger':
            skip_column_list = self.auto_maintained_cols[:]
            skip_column_list.append(self.table.row_vers_column_name)

        column_list_string = self._column_list_string(skip_list=skip_column_list, soft_tabs=4)

        parameter_list_string_lc = self._parameter_list_string(operation_type='create',
                                                               signature_type=signature_type,
                                                               skip_list=skip_column_list,
                                                               soft_tabs=4)
        parameter_list_string = parameter_list_string_lc.upper()

        key_predicates_string = self._predicates_string(soft_tabs=3)
        update_assignments_string = self._update_assignments_string(signature_type=signature_type,
                                                                    operation_type='modify',
                                                                    skip_list=skip_column_list, soft_tabs=3)

        logger_skip_list = [*skip_column_list, *self.identity_cols_lc]
        logger_params_append_lc = self._logger_appends(signature_type=signature_type, soft_tabs=2,
                                                       skip_list=logger_skip_list)

        upd_returning_clause_lc = ''
        if self.return_pk_columns or self.return_ak_columns:
            upd_returning_clause_lc = self._returning_into_clause(signature_type=signature_type, soft_tabs=3)

        ins_returning_clause_lc = ''
        if self.return_pk_columns or self.return_ak_columns:
            ins_returning_clause_lc = self._returning_into_clause(signature_type=signature_type, soft_tabs=3)


        substitutions_dict = {"column_list_string_lc": column_list_string,
                              "parameter_list_string_lc": parameter_list_string_lc,
                              "parameter_list_string": parameter_list_string,
                              "key_predicates_string": key_predicates_string.upper(),
                              "key_predicates_string_lc": key_predicates_string,
                              "update_assignments_string": update_assignments_string.upper(),
                              "update_assignments_string_lc": update_assignments_string,
                              "ins_returning_clause": ins_returning_clause_lc.upper(),
                              "ins_returning_clause_lc": ins_returning_clause_lc,
                              "logger_params_append_lc": logger_params_append_lc,
                              "upd_returning_clause": upd_returning_clause_lc.upper(),
                              "upd_returning_clause_lc": upd_returning_clause_lc,
                              "procedure_signature": procedure_signature,
                              "procedure_name": procedure_name,
                              "procname": procedure_name,
                              "table_name_lc": self.api_target_name_lc,
                              "table_name": self.api_target_name_lc.upper()}

        procedure_body_template = inject_values(substitutions=substitutions_dict,
                                                target_string=procedure_body_template,
                                                stab_spaces=self.indent_spaces)


        return procedure_body_template


    def _delete_api_body(self, signature_type: str, procedure_name:str = 'ins') -> str:
        """Construct the "delete" procedure and its body
        :param signature_type: Signature format: "coltype" or "rowtype"
        :param procedure_name: The name to assign the procedure.
        :return: The procedure body of a delete operation.
        """
        procedure_signature = self._delete_api_sig(signature_type=signature_type, package_spec=False,
                                                   procedure_name=procedure_name) + ""
        procedure_body_template = self._package_api_template(template_category="packages", template_type='procedures',
                                                             template_name=f"delete")
        if self.include_commit:
            procedure_body_template = self._inject_commit_logic(procedure_template=procedure_body_template)

        procedure_body_template = procedure_body_template.replace('%procedure_signature%', procedure_signature)
        procedure_body_template = procedure_body_template.replace('%procedure_name%', procedure_name)
        key_predicates_string = self._predicates_string(soft_tabs=3)

        column_skip_list = self.table.ak_columns_list_lc
        returning_clause_lc = ''
        if self.return_pk_columns or self.return_ak_columns:
            returning_clause_lc = ''
            returning_clause_lc = self._returning_into_clause(signature_type=signature_type,
                                                              skip_list=column_skip_list, soft_tabs=4)

        skip_column_list = []
        k = ["A", "b", "C"]
        c = ["a", "B", "c", "d", "e", "F"]

        # Convert to lowercase for comparison, return lowercase results. We want a list of columns which are
        # not primary key columns.
        skip_list = [item.lower() for item in self.table.columns_list if item.lower() not in [entry.lower() for entry in self.table.pk_columns_list]]

        logger_params_append_lc = self._logger_appends(signature_type=signature_type, soft_tabs=2,
                                                       skip_list=skip_list)

        substitutions_dict = {"key_predicates_string": key_predicates_string.upper(),
                              "key_predicates_string_lc": key_predicates_string,
                              "logger_params_append_lc": logger_params_append_lc,
                              "returning_clause": returning_clause_lc.upper(),
                              "returning_clause_lc": returning_clause_lc,
                              "procedure_signature": procedure_signature,
                              "procedure_name": procedure_name,
                              "procname": procedure_name,
                              "table_name_lc": self.api_target_name_lc,
                              "table_name": self.api_target_name_lc.upper()}

        procedure_body_template = inject_values(substitutions=substitutions_dict,
                                                target_string=procedure_body_template,
                                                stab_spaces=self.indent_spaces)


        return procedure_body_template

    def _merge_api_body(self, signature_type: str, procedure_name:str = 'ins') -> str:
        """Construct the "merge" procedure and its body
        :param signature_type: Signature format: "coltype" or "rowtype"
        :param procedure_name: The name to assign the procedure.
        :return: The procedure body of a merge operation.
        """
        procedure_signature = self._merge_api_sig(signature_type=signature_type, package_spec=False,
                                                   procedure_name=procedure_name) + ""
        procedure_body_template = self._package_api_template(template_category="packages", template_type='procedures',
                                                             template_name=f"merge")

        if self.include_commit:
            procedure_body_template = self._inject_commit_logic(procedure_template=procedure_body_template)

        skip_column_list = self.auto_maintained_cols[:]
        skip_column_list.append(self.table.row_vers_column_name)


        mrg_param_alias_list_lc = self._mrg_param_alias_list_string(operation_type='merge_create',
                                                                    signature_type=signature_type,
                                                                    skip_list=skip_column_list,
                                                                    soft_tabs=6)


        mrg_predicates_string = self._mrg_predicates_string(soft_tabs=5)

        mrg_update_assignments_string = self._mrg_update_assignments_string(operation_type='merge_modify',
                                                                            signature_type=signature_type,
                                                                            skip_list=skip_column_list,
                                                                            soft_tabs=4)

        column_list_string = self._column_list_string(skip_list=skip_column_list, soft_tabs=5, column_prefix = '')
        src_skip_list = [*skip_column_list, *self.identity_cols_lc]
        mrg_src_column_list_string = self._mrg_src_column_list_string(signature_type=signature_type,
                                                                      skip_list=src_skip_list,
                                                                      soft_tabs=5)

        logger_skip_list = [*skip_column_list, *self.identity_cols_lc]
        logger_params_append_lc = self._logger_appends(signature_type=signature_type, soft_tabs=2,
                                                       skip_list=logger_skip_list)

        substitutions_dict = {"mrg_param_alias_list_lc": mrg_param_alias_list_lc,
                              "mrg_param_alias_list": mrg_param_alias_list_lc.upper(),
                              "mrg_predicates_string_lc": mrg_predicates_string,
                              "mrg_predicates_string": mrg_predicates_string.upper(),
                              "key_predicates_string": mrg_predicates_string.upper(),
                              "logger_params_append_lc": logger_params_append_lc,
                              "key_predicates_string_lc": mrg_predicates_string,
                              "update_assignments_string": mrg_update_assignments_string.upper(),
                              "update_assignments_string_lc": mrg_update_assignments_string,
                              "column_list_string": column_list_string.upper(),
                              "column_list_string_lc": column_list_string,
                              "mrg_src_column_list_string": mrg_src_column_list_string.upper(),
                              "mrg_src_column_list_string_lc": mrg_src_column_list_string,
                              "procedure_signature": procedure_signature,
                              "procedure_name": procedure_name,
                              "procname": procedure_name,
                              "table_name_lc": self.api_target_name_lc,
                              "table_name": self.api_target_name_lc.upper()}

        procedure_body_template = inject_values(substitutions=substitutions_dict,
                                                target_string=procedure_body_template,
                                                stab_spaces=self.indent_spaces)

        return procedure_body_template

    def _create_trigger_code(self, trigger_template:str) -> str:
        """Construct table trigger creation code"""

        _trigger_template = trigger_template
        column_list_string_lc = self._column_list_string(soft_tabs=3)

        substitutions_dict = {"column_list_string": column_list_string_lc.upper(),
                              "column_list_string_lc": column_list_string_lc,
                              "table_name_lc": self.table.table_name_lc.lower(),
                              "table_name": self.table.table_name.upper()}

        _trigger_template = inject_values(substitutions=substitutions_dict,
                                       target_string=_trigger_template,
                                       stab_spaces=self.indent_spaces)

        return _trigger_template

    def _create_view_code(self, view_template:str) -> str:
        """Construct view creation code."""

        _view_template = view_template
        column_list_string_lc = self._column_list_string(soft_tabs=3)

        substitutions_dict = {"column_list_string": column_list_string_lc.upper(),
                              "column_list_string_lc": column_list_string_lc,
                              "table_name_lc": self.table.table_name_lc.lower(),
                              "table_name": self.table.table_name.upper()}

        _view_template = inject_values(substitutions=substitutions_dict,
                                       target_string=_view_template,
                                       stab_spaces=self.indent_spaces)

        return _view_template

    def gen_package_body(self) -> str:
        """
        Generates the package body for the APIs listed in the options dictionary.

        This function is called to generate an API signature. As such it is shared for package specification and
        package body code generation.

        :return: A string containing the complete package specification.
        :rtype: str
        """

        # Map API types to corresponding methods
        api_function_map = {
            "insert": {"sig_function": self._insert_api_sig, "body_function": self._insert_api_body, "procedure_name": self.insert_procname},
            "select": {"sig_function": self._select_api_sig, "body_function": self._select_api_body, "procedure_name": self.select_procname},
            "update": {"sig_function": self._update_api_sig, "body_function": self._update_api_body, "procedure_name": self.update_procname},
            "upsert": {"sig_function": self._update_api_sig, "body_function": self._upsert_api_body, "procedure_name": self.upsert_procname},
            "delete": {"sig_function": self._delete_api_sig, "body_function": self._delete_api_body, "procedure_name": self.delete_procname},
            "merge": {"sig_function": self._merge_api_sig,"body_function": self._merge_api_body, "procedure_name": self.merge_procname}
        }

        # Load the package header and footer templates
        package_header_template = self._package_api_template(
            template_category="packages",
            template_type='body',
            template_name="package_header"
        )


        package_footer_template = self._package_api_template(
            template_category="packages",
            template_type='body',
            template_name="package_footer"
        )

        # Merge global and options dictionary substitutions
        merged_dict = self.merged_dict

        # Replace placeholders in the header and footer templates
        package_header_template = inject_values(
            substitutions=self.global_substitutions,
            target_string=package_header_template,
            stab_spaces = self.indent_spaces
        )
        package_footer_template = inject_values(
            substitutions=self.global_substitutions,
            target_string=package_footer_template,
            stab_spaces=self.indent_spaces
        )

        # Start building the package specification
        package_body = package_header_template


        # Generate API fragments for each specified API in the options
        api_types = self.options_dict.get("api_types", [])
        for api_type in api_types:
            mapping = api_function_map.get(api_type)
            sig_func = mapping["sig_function"]
            body_func = mapping["body_function"]
            procedure_name = mapping["procedure_name"]
            for sig_count, sig_type in enumerate(self.signature_types, start=1):
                if sig_count > 1 and api_type == "delete":
                    continue
                elif api_type == "delete":
                    sig_type = 'coltype'
                if sig_func:
                    package_body += body_func(signature_type=sig_type,
                                              procedure_name=procedure_name)
                else:
                    package_body += f"-- Unknown API type: {api_type}\n"
            package_body = inject_values(
                                            substitutions=merged_dict,
                                            target_string=package_body,
                                            stab_spaces=self.indent_spaces
                                        )

        # Append the package footer
        package_body += '\n' + package_footer_template

        return package_body


    def gen_package_spec(self) -> str:
        """
        Generates the package specification for the APIs listed in the options dictionary.

        This function is called to generate an API signature. As such it is shared for package specification and
        package body code generation.

        :return: A string containing the complete package specification.
        :rtype: str
        """

        # Map API types to corresponding methods
        api_function_map = {
            "insert": {"function": self._insert_api_sig, "procedure_name": self.insert_procname},
            "select": {"function": self._select_api_sig, "procedure_name": self.select_procname},
            "update": {"function": self._update_api_sig, "procedure_name": self.update_procname},
            "upsert": {"function": self._upsert_api_sig, "procedure_name": self.upsert_procname},
            "delete": {"function": self._delete_api_sig, "procedure_name": self.delete_procname},
            "merge": {"function": self._merge_api_sig, "procedure_name": self.merge_procname}
        }

        # Load the package header and footer templates
        package_header_template = self._package_api_template(
            template_category="packages",
            template_type='spec',
            template_name="package_header"
        )

        if self.noop_column_string:
            noop_constant = "\n\n%STAB%NOOP%STAB%constant varchar2(128) := '%noop_column_string%';"
            package_header_template += noop_constant

        package_footer_template = self._package_api_template(
            template_category="packages",
            template_type='spec',
            template_name="package_footer"
        )

        # Merge global and options dictionary substitutions
        merged_dict = self.merged_dict

        # Replace placeholders in the header and footer templates
        package_header_template = inject_values(
            substitutions=self.global_substitutions,
            target_string=package_header_template,
            stab_spaces=self.indent_spaces
        )
        if self.api_surface == "view":
            pattern = re.compile(
                r"^(\s*subtype\s+ty_row\s+is\s+)([^\s;]+)(\s*%rowtype\s*;)",
                re.IGNORECASE | re.MULTILINE,
            )
            package_header_template = pattern.sub(
                lambda match: f"{match.group(1)}{self.api_target_name_lc}{match.group(3)}",
                package_header_template,
                count=1,
            )
        package_footer_template = inject_values(
            substitutions=self.global_substitutions,
            target_string=package_footer_template,
            stab_spaces=self.indent_spaces
        )

        # Start building the package specification
        package_spec = package_header_template

        # Generate API fragments for each specified API in the options
        api_types = self.options_dict.get("api_types", [])
        for api_type in api_types:
            mapping = api_function_map.get(api_type)
            func = mapping["function"]
            procedure_name = mapping["procedure_name"]
            for sig_count, sig_type in enumerate(self.signature_types, start=1):
                if sig_count > 1 and api_type == "delete":
                    continue
                if func:
                    package_spec += func(signature_type=sig_type, package_spec=True, procedure_name=procedure_name) + "\n"  # Append the generated API fragment
                else:
                    package_spec += f"-- Unknown API type: {api_type}\n"
            package_spec = inject_values(
                                            substitutions=merged_dict,
                                            target_string=package_spec,
                                            stab_spaces=self.indent_spaces
                                        )

        # Append the package footer
        package_spec += package_footer_template

        return package_spec

    def gen_views(self):
        # Load the package header and footer templates
        view_code_dict = {}
        view_dir = self.view_template_dir

        templates = view_dir.glob('*[a-z0-9_]*.tpt')

        for template in templates:
            source_file_name = template.name
            source_file_name = str(source_file_name).replace('.tpt', '').replace('view', self.table.table_name_lc)
            source_file_name += self.view_name_suffix_lc
            source_file_name = source_file_name +'.sql'
            view_template = self._package_api_template(
                    template_category="misc",
                    template_type='view',
                    template_name=template
                )


            view_template = self._create_view_code(view_template=view_template)
            view_template = inject_values(
                substitutions=self.global_substitutions,
                target_string=view_template,
                stab_spaces=self.indent_spaces
            )
            view_code_dict[source_file_name] = view_template

        return view_code_dict

    @staticmethod
    def _inject_commit_logic(procedure_template: str) -> str:
        """
        Injects commit logic into the given procedure template before the line containing "%STAB%end".

        :param procedure_template: str, the input multi-line template string
        :return: str, the modified template with injected commit logic
        """
        # Commit logic to be injected
        inject_string = "%STAB%%STAB%if p_commit\n"
        inject_string += "%STAB%%STAB%then\n"
        inject_string += "%STAB%%STAB%%STAB%commit;\n"
        inject_string += "%STAB%%STAB%end if;\n"

        # Split the template into lines
        lines = procedure_template.splitlines()

        # Find the index of the line containing "%STAB%end"
        for i, line in enumerate(lines):
            if line.strip().startswith("%STAB%end"):
                # Insert the inject_string before this line
                lines.insert(i, inject_string)
                break

        # Reassemble the template
        injected_template = "\n".join(lines)

        return injected_template

    def gen_triggers(self):
        # Load the package header and footer templates
        trigger_code_dict = {}
        trigger_dir = self.trigger_template_dir

        templates = trigger_dir.glob('*[a-z0-9_]*.tpt')

        for template in templates:
            source_file_name: str = template.name
            source_file_name = str(source_file_name).replace('.tpt', '').replace('table_name', self.table.table_name_lc)
            source_file_name = source_file_name +'.sql'
            trigger_template = self._package_api_template(
                    template_category="misc",
                    template_type='trigger',
                    template_name=template
                )


            trigger_template = self._create_trigger_code(trigger_template=trigger_template)
            trigger_template = inject_values(
                substitutions=self.global_substitutions,
                target_string=trigger_template,
                stab_spaces=self.indent_spaces
            )
            trigger_code_dict[source_file_name] = trigger_template

        return trigger_code_dict

if __name__ == "__main__":
    # Connection parameters
    print('INFO: No tests setup for tapi_generator.py')
    pass
