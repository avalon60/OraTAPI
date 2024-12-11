# api_controller.py

__author__ = "Clive Bostock"
__date__ = "2024-11-09"
__description__ = "Generates the API code."

import copy
import re

from lib.config_manager import ConfigManager
from model.db_objects import Table
from model.session_manager import DBSession
from lib.file_system_utils import project_home
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from copy import deepcopy
from itertools import chain


# Define our substitution placeholder string for indent spaces.
# The number of spaces for an indent tab, is defined in OraTAPI.ini
IDNT = '%indent_spaces%'

# Get the current date
date_now = datetime.now()

# Format the date as DD-Mon-YYYY
current_date = date_now.strftime("%d-%b-%Y")


def inject_values(substitutions: Dict[str, Any], target_string: str, stab_spaces:int = 3) -> str:
    """
    Recursively walk through a nested dictionary to replace placeholders in the text template.

    :param stab_spaces:
    :param substitutions: The dictionary of substitutions (optionally nested).
    :type substitutions: (Dict[str, Any])
    :param target_string: A string with %key% placeholders, for substitutions based on the supplied dictionary.
    :type target_string: str
    :return: The template contents with placeholders replaced by corresponding values.
    :rtype: str
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
    return target_string

class ApiGenerator:
    def __init__(self,
                 database_session: DBSession,
                 schema_name: str,
                 table_name: str,
                 config_manager: ConfigManager,
                 options_dict: dict,
                 trace: bool = False):
        """
        :param database_session: A DBSession instance for connecting to the database.
        :param schema_name: Schema Name of the table.
        :param table_name: Table name of the table for which we need to generate a TAPI
        :param config_manager: A ConfigManager as established by the controller.
        :param options_dict: The dictionary of our command line options.
        :param trace: Enables trace/debug output when set to True.
        """
        self.proj_home = project_home()  # project_home returns a Path object
        proj_config_file = self.proj_home / 'config' / 'OraTAPI.ini'
        self.column_expressions_dir = self.proj_home / 'templates' / 'column_expressions'
        self.options_dict = deepcopy(options_dict)
        self.config_manager = config_manager
        self.schema_name = schema_name
        package_owner_lc = options_dict["package_owner"].lower()


        self.config_manager = ConfigManager(config_file_path=proj_config_file)
        self.table = Table(database_session=database_session, schema_name=self.schema_name ,
                           table_name=table_name, config_manager=config_manager, trace=trace)

        auto_maintained_cols = self.config_manager.config_value(config_section="api_controls",
                                                            config_key="auto_maintained_cols")
        auto_maintained_cols = auto_maintained_cols.replace(' ', '')
        self.auto_maintained_cols = auto_maintained_cols.lower().split(',')

        signature_types = self.config_manager.config_value(config_section="api_controls",
                                                            config_key="signature_types")

        signature_types = signature_types.replace(' ', '')
        self.signature_types = signature_types.lower().split(',')

        self.indent_spaces = self.config_manager.config_value(config_section="formatting", config_key="indent_spaces")
        try:
            self.indent_spaces = int(self.indent_spaces)
        except ValueError:
            message = f'The formatting.indent_spaces value, "{self.indent_spaces}", retrieved from OraTAPI.ini, is non-integer!'
            raise ValueError(message)

        # These next 2 are used in template substitutions.
        self.sig_suffix = self.config_manager.config_value(config_section="file_controls", config_key="spec_suffix")
        self.body_suffix = self.config_manager.config_value(config_section="file_controls", config_key="body_suffix")

        self.include_defaults = self.config_manager.bool_config_value(config_section="api_controls",
                                                                 config_key="include_defaults")

        self.return_key_columns = self.config_manager.bool_config_value(config_section="api_controls",
                                                                   config_key="return_key_columns")

        self.noop_column_string = self.config_manager.config_value(config_section="api_controls",
                                                                   config_key="noop_column_string",
                                                                   default='')

        self.row_vers_column_name = self.config_manager.config_value(config_section="api_controls",
                                                                     config_key="row_vers_column_name",
                                                                     default=None)
        self.col_auto_maintain_method = self.config_manager.config_value(config_section="api_controls",
                                                                     config_key="col_auto_maintain_method",
                                                                     default='trigger')

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

        # Populate self.global_substitutions with the .ini file contents.
        # We will use these to inject values into the templates.
        self.global_substitutions = self.config_manager.config_dictionary()
        self.include_rowid = self.global_substitutions["include_rowid"]
        self.include_rowid = True if self.include_rowid == 'true' else False
        # Set soft tabs spaces for indent
        self.global_substitutions["STAB"] = ' ' * int(self.global_substitutions["indent_spaces"])
        self.global_substitutions["package_owner_lc"] = package_owner_lc


        self.merged_dict = self.global_substitutions | self.options_dict
        # Check to see if the copyright date is expected to be set to today's date.
        # If not set as "current_date", we assume it's a static date.
        if self.global_substitutions["copyright_year"] == "current":
            self.global_substitutions["copyright_year"] = current_date

        self.global_substitutions["spec_suffix"] = self.sig_suffix
        self.global_substitutions["body_suffix"] = self.body_suffix
        self.global_substitutions["run_date_time"] = current_date
        self.global_substitutions["table_name_lc"] = table_name.lower()
        self.global_substitutions["schema_name_lc"] = self.schema_name.lower()


        self.table = Table(database_session=database_session,
                           schema_name=schema_name,
                           table_name=table_name,
                           config_manager=config_manager,
                           trace=trace)

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
            messages.append(f"Loading column expression template file: inserts/{expression_file}")
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
            messages.append(f"Loading column expression template file: updates/{expression_file}")
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

    def _noop_assignment(self, column_name, soft_tabs:int) -> str:
        """The _noop_assignment method should only be called for update APIs. It is used to generate cases statements
        for columns where the parameter is defaulted to the noop_column_string property setting in OraTAPI.ini."""
        if self.table.column_property_value(column_name=column_name, property_name='default_value'):
            return ""
        block_list = self.table.in_out_column_list + [self.table.row_vers_column_name.upper()]
        if column_name.upper() in block_list:
            return ""

        column_name_lc = column_name.lower()

        tabs = "%STAB%" * soft_tabs
        noop_assignment = f"case\n"
        noop_assignment += f"{tabs}%STAB%  when p_{column_name_lc} = '{self.noop_column_string}' then {column_name_lc}\n"
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

        valid_operations_list = [ "create", "modify", "merge_create", "merge_modify"]
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
                assignment = f'p_{column_name_lc}'if signature_type == "coltype" else f'p_row.{column_name_lc}'
        elif operation_type == 'modify':
            assignment = ''
            if (self.col_auto_maintain_method == "expression" and
                    column_name_lc in chain(self.auto_maintained_cols, [self.row_vers_column_name])):
                assignment = self.column_update_expressions[column_name]
            if not assignment:
                assignment = f'p_{column_name_lc}'if signature_type == "coltype" else f'p_row.{column_name_lc}'

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
                params_out += f"  p_row.{column_name_lc:<30} as {column_name_lc}" if column_id == 1 else  f"\n{tabs}, p_row.{column_name_lc:<30} as {column_name_lc}"
                column_id += 1
        else:
            message = f'Expected signature_type to be either, "coltype" or "rowtype", but got "{signature_type}".'
            raise ValueError(message)

        return params_out

    def _mrg_predicates_string(self, signature_type:str, soft_tabs:int = 4) -> str:
        """Returns a line separated (\n) list of the predicates"""
        tabs = "%STAB%" * soft_tabs  # The number of STABs in the respective template.
        if signature_type == "coltype":
            predicates_out = ""
            for column_id, column_name in enumerate(self.table.pk_columns_list, start=1):
                column_name_lc = column_name.lower()
                # The first column has it's indent defined in the template
                predicates_out += f"  tgt.{column_name_lc} = src.{column_name_lc}" if column_id == 1 else  f"\n{tabs}and tgt.{column_name_lc} = src.{column_name_lc}"
        elif signature_type == "rowtype":
            predicates_out = ""
            for column_id, column_name in enumerate(self.table.pk_columns_list, start=1):
                column_name_lc = column_name.lower()
                # The first column has it's indent defined in the template
                predicates_out += f"  tgt.{column_name_lc} = src.{column_name_lc}" if column_id == 1 else  f"\n{tabs}and tgt.{column_name_lc} = src.{column_name_lc}"
        else:
            message = f'Expected signature_type to be either, "coltype" or "rowtype", but got "{signature_type}".'
            raise ValueError(message)

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


    def _column_list_string(self, skip_list = None, soft_tabs:int = 4, column_prefix:str = '')-> str:
        """Returns a line separated (\n) list of select columns"""
        if skip_list is None:
            skip_list = []

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

    def _parameter_list_string(self, signature_type:str, operation_type:str = 'create', skip_list: list = None, soft_tabs:int = 4)-> str:
        """Returns a line separated (\n) list of select columns"""

        if skip_list is None:
            skip_list = []

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

    def _predicates_string(self, signature_type:str, soft_tabs:int = 4) -> str:
        """Returns a line separated (\n) list of the predicates"""
        tabs = "%STAB%" * soft_tabs  # The number of STABs in the respective template.
        if signature_type == "coltype":
            predicates_out = ""
            for column_id, column_name in enumerate(self.table.pk_columns_list, start=1):
                column_name_lc = column_name.lower()
                # The first column has it's indent defined in the template
                predicates_out += f"   {column_name_lc} = p_{column_name_lc}" if column_id == 1 else  f"\n{tabs}  and {column_name_lc} = p_{column_name_lc}"
        elif signature_type == "rowtype":
            predicates_out = ""
            for column_id, column_name in enumerate(self.table.pk_columns_list, start=1):
                column_name_lc = column_name.lower()
                # The first column has it's indent defined in the template
                predicates_out += f"   {column_name_lc} = p_row.{column_name_lc}" if column_id == 1 else  f"\n{tabs}  and {column_name_lc} = p_row.{column_name_lc}"
        else:
            message = f'Expected signature_type to be either, "coltype" or "rowtype", but got "{signature_type}".'
            raise ValueError(message)

        return predicates_out

    def _update_assignments_string(self, signature_type:str, operation_type:str,
                                   skip_list:list = None, soft_tabs:int = 4) -> str:
        """Returns a line separated (\n) list of the predicates"""
        _operation_type = 'modify' if operation_type == 'update' else operation_type
        if skip_list is None:
            skip_list = []
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
                if self.noop_column_string and operation_type == 'update':
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
                if column_name_lc == self.table.row_vers_column_name and self.col_auto_maintain_method == 'trigger':
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
        template_name = template_name.replace(".tpt", "") + ".tpt"
        proj_templates = self.proj_home / 'templates' /  template_category / template_type
        template_path = proj_templates / template_name

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
        comment += f"{STAB}-- {tapi_description} TAPI for: {self.schema_name.lower()}.{self.table.table_name.lower()}\n"
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
        table_name_lc = self.table.table_name.lower()
        for col_position, column_name in enumerate(self.table.columns_list, start = 1):
            column_name_lc = column_name.lower()
            is_pk_column = self.table.column_property_value(column_name=column_name, property_name="is_pk_column")
            if not column_name in self.table.pk_columns_list and column_name_lc != self.table.row_vers_column_name:
                continue

            default_value = self.table.column_property_value(column_name=column_name, property_name="default_value")
            leader = f', ' if col_position > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{column_name_lc.ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in out'
            param += in_out
            param += f"{STAB}{table_name_lc}.{column_name_lc}%type"
            if self.include_defaults and default_value:
                param += f'{STAB} := {default_value}'
            signature += param + '\n'
            param = ''


        if self.include_rowid:
            leader = f',{STAB}' if self.table.col_count > 1 else f' {STAB}'
            param = f'{STAB}{STAB}{leader}p_{"rowid".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in out'
            param += in_out
            param += f'{STAB}rowid'
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
        """Formulates and returns the API's signature, for "coltype" signatures."""
        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Insert')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.table.table_name.lower()

        processed_columns = 0

        for col_position, column_name in enumerate(self.table.columns_list, start = 1):
            column_name_lc = column_name.lower()
            if column_name_lc in self.auto_maintained_cols:
                continue

            processed_columns += 1
            is_key_col = self.table.column_property_value(column_name=column_name, property_name="is_key_column")
            is_row_version_column = self.table.column_property_value(column_name=column_name,
                                                                     property_name="is_row_version_column")
            default_value = self.table.column_property_value(column_name=column_name, property_name="default_value")
            leader = f', ' if processed_columns > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{column_name_lc.ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'

            if is_key_col:
                in_out = f'{STAB}in out'
            elif is_row_version_column:
                in_out = f'{STAB}   out'
            else:
                in_out = f'{STAB}in    '

            param += in_out
            param += f"{STAB}{table_name_lc}.{column_name_lc}%type"
            if self.include_defaults and default_value and column_name not in self.table.out_column_list:
                param = f"{param:<75}"
                param += f'{STAB} := {default_value}'

            signature += param + '\n'
            param = ''

        if self.include_rowid:
            leader = f',{STAB}' if self.table.col_count > 1 else f' {STAB}'
            param = f'{STAB}{STAB}{leader}p_{"rowid".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in out'
            param += in_out
            param += f'{STAB}rowid'
            signature += param + '\n'

            leader = f',{STAB}' if self.table.col_count > 1 else f' {STAB}'
            param = f'{STAB}{STAB}{leader}p_{"rowid".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in out'
            param += in_out
            param += f'{STAB}rowid'
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
        """Formulates and returns the API's signature, for "rowtype" signatures."""
        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Insert')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.table.table_name.lower()

        processed_columns = 0

        for col_position, column_name in enumerate(self.table.columns_list, start = 1):
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

        if self.include_rowid:
            leader = f',{STAB}' if self.table.col_count > 1 else f' {STAB}'
            param = f'{STAB}{STAB}{leader}p_{"rowid".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in out'
            param += in_out
            param += f'{STAB}rowid'
            signature += param + '\n'

        leader = f', '
        param = f'{STAB}{STAB}{leader}p_{"row".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
        in_out = f'{STAB}in out'
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
        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Select')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.table.table_name.lower()

        processed_columns = 0

        for col_position, column_name in enumerate(self.table.columns_list, start = 1):

            processed_columns += 1
            is_key_col = self.table.column_property_value(column_name=column_name, property_name="is_key_column")
            is_row_version_column = self.table.column_property_value(column_name=column_name,
                                                                     property_name="is_row_version_column")
            column_name_lc = column_name.lower()

            leader = f', ' if processed_columns > 1 else f'  '
            param = f'{STAB}{STAB}{leader}p_{column_name_lc.ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'

            if is_key_col:
                in_out = f'{STAB}in out'
            else:
                in_out = f'{STAB}   out'

            param += in_out
            param += f"{STAB}{table_name_lc}.{column_name_lc}%type"

            signature += param + '\n'
            param = ''

        if self.include_rowid:
            leader = f',{STAB}' if self.table.col_count > 1 else f' {STAB}'
            param = f'{STAB}{STAB}{leader}p_{"rowid".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in out'
            param += in_out
            param += f'{STAB}rowid'
            signature += param + '\n'

            leader = f',{STAB}' if self.table.col_count > 1 else f' {STAB}'
            param = f'{STAB}{STAB}{leader}p_{"rowid".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in out'
            param += in_out
            param += f'{STAB}rowid'
            signature += param + '\n'

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
        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Select')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'

        signature += f'{STAB}(\n'
        table_name_lc = self.table.table_name.lower()

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

        if self.include_rowid:
            leader = f',{STAB}' if self.table.col_count > 1 else f' {STAB}'
            param = f'{STAB}{STAB}{leader}p_{"rowid".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in out'
            param += in_out
            param += f'{STAB}rowid'
            signature += param + '\n'

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
        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Update')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.table.table_name.lower()

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

            if is_key_col:
                in_out = f'{STAB}in out'
            elif is_row_version_column:
                in_out = f'{STAB}   out'
            else:
                in_out = f'{STAB}in    '

            param += in_out
            param += f"{STAB}{table_name_lc}.{column_name_lc}%type"
            block_list = self.table.in_out_column_list + [self.table.row_vers_column_name.upper()]
            if self.noop_column_string and column_name not in block_list:
                param = f"{param:<75}"
                param += f"{STAB} := '{self.noop_column_string}'"

            signature += param + '\n'
            param = ''

        if self.include_rowid:
            leader = f',{STAB}' if self.table.col_count > 1 else f' {STAB}'
            param = f'{STAB}{STAB}{leader}p_{"rowid".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in out'
            param += in_out
            param += f'{STAB}rowid'
            signature += param + '\n'

            leader = f',{STAB}' if self.table.col_count > 1 else f' {STAB}'
            param = f'{STAB}{STAB}{leader}p_{"rowid".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in out'
            param += in_out
            param += f'{STAB}rowid'
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
        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Update')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.table.table_name.lower()

        processed_columns = 0

        for col_position, column_name in enumerate(self.table.columns_list, start = 1):
            if column_name.lower() in self.auto_maintained_cols:
                continue
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

        if self.include_rowid:
            leader = f',{STAB}' if self.table.col_count > 1 else f' {STAB}'
            param = f'{STAB}{STAB}{leader}p_{"rowid".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in out'
            param += in_out
            param += f'{STAB}rowid'
            signature += param + '\n'

        leader = f', '
        param = f'{STAB}{STAB}{leader}p_{"row".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
        in_out = f'{STAB}in out'
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

    def _update_api_sig(self,
                        signature_type: str,
                        package_spec: bool = True,
                        inc_comments: bool = True,
                        procedure_name:str = 'upd') -> str:
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
        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Upsert')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.table.table_name.lower()

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

            if is_key_col:
                in_out = f'{STAB}in out'
            elif is_row_version_column:
                in_out = f'{STAB}   out'
            else:
                in_out = f'{STAB}in    '

            param += in_out
            param += f"{STAB}{table_name_lc}.{column_name_lc}%type"

            signature += param + '\n'
            param = ''

        if self.include_rowid:
            leader = f',{STAB}' if self.table.col_count > 1 else f' {STAB}'
            param = f'{STAB}{STAB}{leader}p_{"rowid".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in out'
            param += in_out
            param += f'{STAB}rowid'
            signature += param + '\n'

            leader = f',{STAB}' if self.table.col_count > 1 else f' {STAB}'
            param = f'{STAB}{STAB}{leader}p_{"rowid".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in out'
            param += in_out
            param += f'{STAB}rowid'
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
        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Upsert')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.table.table_name.lower()

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

        if self.include_rowid:
            leader = f',{STAB}' if self.table.col_count > 1 else f' {STAB}'
            param = f'{STAB}{STAB}{leader}p_{"rowid".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in out'
            param += in_out
            param += f'{STAB}rowid'
            signature += param + '\n'

        leader = f', '
        param = f'{STAB}{STAB}{leader}p_{"row".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
        in_out = f'{STAB}in out'
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
        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Merge')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.table.table_name.lower()

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

            if is_key_col:
                in_out = f'{STAB}in out'
            elif is_row_version_column:
                in_out = f'{STAB}   out'
            else:
                in_out = f'{STAB}in    '

            param += in_out
            param += f"{STAB}{table_name_lc}.{column_name_lc}%type"

            signature += param + '\n'
            param = ''

        if self.include_rowid:
            leader = f',{STAB}' if self.table.col_count > 1 else f' {STAB}'
            param = f'{STAB}{STAB}{leader}p_{"rowid".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in out'
            param += in_out
            param += f'{STAB}rowid'
            signature += param + '\n'

            leader = f',{STAB}' if self.table.col_count > 1 else f' {STAB}'
            param = f'{STAB}{STAB}{leader}p_{"rowid".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in out'
            param += in_out
            param += f'{STAB}rowid'
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
        signature = ""
        if inc_comments:
            signature += self.comment_tapi(tapi_description='Merge')

        STAB = self.global_substitutions["STAB"]
        signature += f'{STAB}procedure {procedure_name}\n'
        signature += f'{STAB}(\n'
        table_name_lc = self.table.table_name.lower()

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

        if self.include_rowid:
            leader = f',{STAB}' if self.table.col_count > 1 else f' {STAB}'
            param = f'{STAB}{STAB}{leader}p_{"rowid".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
            in_out = f'{STAB}in out'
            param += in_out
            param += f'{STAB}rowid'
            signature += param + '\n'

        leader = f', '
        param = f'{STAB}{STAB}{leader}p_{"row".ljust(self.table.max_col_name_len + self.indent_spaces, " ")}'
        in_out = f'{STAB}in out'
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

        returning_clause_lc = ''
        if self.return_key_columns:
            returning_clause_lc = self._returning_into_clause(signature_type=signature_type, soft_tabs=4)

        substitutions_dict = {
                              "key_predicates_string": column_list_string.upper(),
                              "column_list_string_lc": column_list_string,
                              "parameter_list_string_lc": parameter_list_string_lc,
                              "parameter_list_string": parameter_list_string,
                              "returning_clause_lc": returning_clause_lc,
                              "returning_clause": returning_clause_lc.upper(),
                              "procedure_signature": procedure_signature,
                              "procedure_name": procedure_name,
                              "table_name_lc": self.table.table_name_lc.lower(),
                              "table_name": self.table.table_name.upper()}

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

        column_list_string_lc = self._column_list_string(soft_tabs=3)

        parameter_list_string_lc = self._parameter_list_string(signature_type=signature_type,
                                                               soft_tabs=3)
        parameter_list_string = parameter_list_string_lc.upper()

        key_predicates_string = self._predicates_string(signature_type=signature_type, soft_tabs=2)

        substitutions_dict = {"column_list_string": column_list_string_lc.upper(),
                              "column_list_string_lc": column_list_string_lc,
                              "key_predicates_string": key_predicates_string.upper(),
                              "key_predicates_string_lc": key_predicates_string,
                              "parameter_list_string_lc": parameter_list_string_lc,
                              "parameter_list_string": parameter_list_string,
                              "procedure_signature": procedure_signature,
                              "procedure_name": procedure_name,
                              "table_name_lc": self.table.table_name_lc.lower(),
                              "table_name": self.table.table_name.upper()}

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

        skip_column_list = []
        if self.col_auto_maintain_method == 'trigger':
            skip_column_list = self.auto_maintained_cols[:]
            skip_column_list.append(self.table.row_vers_column_name)

        key_predicates_string = self._predicates_string(signature_type=signature_type, soft_tabs=3)

        update_assignments_string = self._update_assignments_string(signature_type=signature_type,
                                                                    skip_list=skip_column_list,
                                                                    operation_type='update', soft_tabs=3)
        return_columns_list = self._return_columns_list(soft_tabs=3)

        return_parameter_list = self._return_parameter_list(signature_type=signature_type,
                                                            soft_tabs=3)

        skip_column_list = []
        if self.table.row_vers_column_name and self.col_auto_maintain_method == 'trigger':
            skip_column_list = self.auto_maintained_cols[:]
            skip_column_list.append(self.table.row_vers_column_name)

        returning_clause_lc = ''
        if self.return_key_columns:
            returning_clause_lc = self._returning_into_clause(signature_type=signature_type, soft_tabs=4)

        substitutions_dict = {"key_predicates_string": key_predicates_string.upper(),
                              "key_predicates_string_lc": key_predicates_string,
                              "update_assignments_string": update_assignments_string.upper(),
                              "update_assignments_string_lc": update_assignments_string,
                              "returning_clause": returning_clause_lc.upper(),
                              "returning_clause_lc": returning_clause_lc,
                              "return_columns_list": return_columns_list.upper(),
                              "return_columns_list_lc": return_columns_list,
                              "return_parameter_list": return_parameter_list.upper(),
                              "return_parameter_list_lc": return_parameter_list,
                              "procedure_signature": procedure_signature,
                              "procedure_name": procedure_name,
                              "table_name_lc": self.table.table_name_lc.lower(),
                              "table_name": self.table.table_name.upper()}

        procedure_body_template = inject_values(substitutions=substitutions_dict,
                                                target_string=procedure_body_template,
                                                stab_spaces=self.indent_spaces)


        return procedure_body_template


    def _upsert_api_body(self, signature_type: str, procedure_name:str = 'ins') -> str:
        """Put together the "upsert" procedure and its body"""
        procedure_signature = self._upsert_api_sig(signature_type=signature_type, package_spec=False,
                                                   procedure_name=procedure_name) + ""
        procedure_body_template = self._package_api_template(template_category="packages", template_type='procedures',
                                                             template_name=f"upsert")

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

        key_predicates_string = self._predicates_string(signature_type=signature_type, soft_tabs=3)
        update_assignments_string = self._update_assignments_string(signature_type=signature_type,
                                                                    operation_type='modify',
                                                                    skip_list=skip_column_list, soft_tabs=3)

        upd_returning_clause_lc = ''
        if self.return_key_columns:
            upd_returning_clause_lc = self._returning_into_clause(signature_type=signature_type, soft_tabs=3)

        ins_returning_clause_lc = ''
        if self.return_key_columns:
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
                              "upd_returning_clause": upd_returning_clause_lc.upper(),
                              "upd_returning_clause_lc": upd_returning_clause_lc,
                              "procedure_signature": procedure_signature,
                              "procedure_name": procedure_name,
                              "table_name_lc": self.table.table_name_lc.lower(),
                              "table_name": self.table.table_name.upper()}

        procedure_body_template = inject_values(substitutions=substitutions_dict,
                                                target_string=procedure_body_template,
                                                stab_spaces=self.indent_spaces)


        return procedure_body_template


    def _delete_api_body(self, signature_type: str, procedure_name:str = 'ins') -> str:
        """Put together the "delete" procedure and its body"""
        procedure_signature = self._delete_api_sig(signature_type=signature_type, package_spec=False,
                                                   procedure_name=procedure_name) + ""
        procedure_body_template = self._package_api_template(template_category="packages", template_type='procedures',
                                                             template_name=f"delete")
        procedure_body_template = procedure_body_template.replace('%procedure_signature%', procedure_signature)
        procedure_body_template = procedure_body_template.replace('%procedure_name%', procedure_name)
        key_predicates_string = self._predicates_string(signature_type='coltype', soft_tabs=3)

        column_skip_list = self.table.ak_columns_list_lc
        returning_clause_lc = ''
        if self.return_key_columns:
            returning_clause_lc = ''
            returning_clause_lc = self._returning_into_clause(signature_type=signature_type,
                                                              skip_list=column_skip_list, soft_tabs=4)

        substitutions_dict = {"key_predicates_string": key_predicates_string.upper(),
                              "key_predicates_string_lc": key_predicates_string,
                              "returning_clause": returning_clause_lc.upper(),
                              "returning_clause_lc": returning_clause_lc,
                              "procedure_signature": procedure_signature,
                              "procedure_name": procedure_name,
                              "table_name_lc": self.table.table_name_lc.lower(),
                              "table_name": self.table.table_name.upper()}

        procedure_body_template = inject_values(substitutions=substitutions_dict,
                                                target_string=procedure_body_template,
                                                stab_spaces=self.indent_spaces)


        return procedure_body_template

    def _merge_api_body(self, signature_type: str, procedure_name:str = 'ins') -> str:
        """Put together the "merge" procedure and its body"""
        procedure_signature = self._merge_api_sig(signature_type=signature_type, package_spec=False,
                                                   procedure_name=procedure_name) + ""
        procedure_body_template = self._package_api_template(template_category="packages", template_type='procedures',
                                                             template_name=f"merge")



        skip_column_list = self.auto_maintained_cols[:]
        skip_column_list.append(self.table.row_vers_column_name)


        mrg_param_alias_list_lc = self._mrg_param_alias_list_string(operation_type='merge_create',
                                                                    signature_type=signature_type,
                                                                    skip_list=skip_column_list,
                                                                    soft_tabs=6)


        mrg_predicates_string = self._mrg_predicates_string(signature_type=signature_type, soft_tabs=5)

        mrg_update_assignments_string = self._mrg_update_assignments_string(operation_type='merge_modify',
                                                                            signature_type=signature_type,
                                                                            skip_list=skip_column_list,
                                                                            soft_tabs=4)

        column_list_string = self._column_list_string(skip_list=skip_column_list, soft_tabs=5, column_prefix = '')
        mrg_src_column_list_string = self._mrg_src_column_list_string(signature_type=signature_type,
                                                                      skip_list=skip_column_list,
                                                                      soft_tabs=5)

        substitutions_dict = {"mrg_param_alias_list_lc": mrg_param_alias_list_lc,
                              "mrg_param_alias_list": mrg_param_alias_list_lc.upper(),
                              "mrg_predicates_string_lc": mrg_predicates_string,
                              "mrg_predicates_string": mrg_predicates_string.upper(),
                              "key_predicates_string": mrg_predicates_string.upper(),
                              "key_predicates_string_lc": mrg_predicates_string,
                              "update_assignments_string": mrg_update_assignments_string.upper(),
                              "update_assignments_string_lc": mrg_update_assignments_string,
                              "column_list_string": column_list_string.upper(),
                              "column_list_string_lc": column_list_string,
                              "mrg_src_column_list_string": mrg_src_column_list_string.upper(),
                              "mrg_src_column_list_string_lc": mrg_src_column_list_string,
                              "procedure_signature": procedure_signature,
                              "procedure_name": procedure_name,
                              "table_name_lc": self.table.table_name_lc.lower(),
                              "table_name": self.table.table_name.upper()}

        procedure_body_template = inject_values(substitutions=substitutions_dict,
                                                target_string=procedure_body_template,
                                                stab_spaces=self.indent_spaces)

        return procedure_body_template

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


if __name__ == "__main__":
    # Connection parameters
    print('INFO: No tests setup for api_generator.py')
    pass
