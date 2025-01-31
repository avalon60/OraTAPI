# api_controller.py

__author__ = "Clive Bostock"
__date__ = "2024-11-09"
__description__ = "Generates the utPLSQL test skeleton code - package spec & package body."

import copy

from lib.config_mgr import ConfigManager
from model.db_objects import Table
from model.db_objects import TableConstraints
from model.session_manager import DBSession
from lib.file_system_utils import project_home
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from model.tapi_generator import inject_values
from model.framework_errors import InconsistentRequest
from model.ora_tapi_csv import CSVManager
from copy import deepcopy


# Define our substitution placeholder string for indent spaces.
# The number of spaces for an indent tab is defined in OraTAPI.ini
IDNT = '%indent_spaces%'

APP_HOME = project_home()
TEMPLATES_LOCATION = APP_HOME / 'resources' / 'templates'
CONFIG_LOCATION = APP_HOME / 'resources' / 'config'

# Get the current date
date_now = datetime.now()

# Format the date as DD-Mon-YYYY
current_date = date_now.strftime("%d-%b-%Y")
current_year = date_now.strftime("%Y")

class UtPLSQLGenerator:
    def __init__(self,
                 database_session: DBSession,
                 table_owner: str,
                 table_name: str,
                 config_manager: ConfigManager,
                 options_dict: dict,
                 trace: bool = False):
        """
        :param database_session: A DBSession instance for connecting to the database.
        :param table_owner: Schema Name of the table.
        :param table_name: Table name of the table for which we need to generate a TAPI
        :param config_manager: A ConfigManager as established by the controller.
        :param options_dict: The dictionary of our command line options.
        :param trace: Enables trace/debug output when set to True.
        """
        self.proj_home = project_home()  # project_home returns a Path object
        proj_config_file = CONFIG_LOCATION/ 'OraTAPI.ini'

        self.options_dict = deepcopy(options_dict)
        self.config_manager = config_manager
        self.table_owner = table_owner

        package_owner_lc = options_dict["package_owner"].lower()

        self.config_manager = ConfigManager(config_file_path=proj_config_file)
        self.table = Table(database_session=database_session, table_owner=self.table_owner,
                           table_name=table_name, config_manager=config_manager, trace=trace)


        self.enable_ut_code_generation = self.config_manager.bool_config_value(config_section='ut_controls',
                                                                               config_key='enable_ut_code_generation',
                                                                               default=False)

        if not self.enable_ut_code_generation:
            raise InconsistentRequest("Attempted instantiation of utPLSQLGenerator, when utPLSQL code generation is disabled.")

        self.indent_spaces = self.config_manager.config_value(config_section="formatting", config_key="indent_spaces")
        try:
            self.indent_spaces = int(self.indent_spaces)
        except ValueError:
            message = f'The formatting.indent_spaces value, "{self.indent_spaces}", retrieved from OraTAPI.ini, is non-integer!'
            raise ValueError(message)

        # These next 2 are used in template substitutions.
        self.sig_file_ext = self.config_manager.config_value(config_section="file_controls", config_key="spec_file_ext")
        self.body_file_ext = self.config_manager.config_value(config_section="file_controls", config_key="body_file_ext")


        row_vers_column_name = self.config_manager.config_value(config_section="api_controls",
                                                                     config_key="row_vers_column_name",
                                                                     default=None)

        self.col_auto_maintain_method = self.config_manager.config_value(config_section="api_controls",
                                                                         config_key="col_auto_maintain_method",
                                                                         default='trigger')

        self.row_vers_column_name = row_vers_column_name.upper()

        auto_maintained_cols = self.config_manager.config_value(config_section="api_controls",
                                                                config_key="auto_maintained_cols",
                                                                default='')

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

        # Split the string and strip whitespace
        self.auto_maintained_cols = [col.strip() for col in auto_maintained_cols.split(",")]
        self.auto_maintained_cols_lc = [col.lower() for col in self.auto_maintained_cols]


        # Populate self.global_substitutions with the .ini file contents.
        # We will use these to inject values into the templates.
        self.global_substitutions = self.config_manager.config_dictionary()

        # Set soft tabs spaces for indent
        self.global_substitutions["STAB"] = ' ' * int(self.global_substitutions["indent_spaces"])
        self.global_substitutions["package_owner_lc"] = package_owner_lc

        # Check to see if the copyright date is expected to be set to today's date.
        # If not set as "current_date", we assume it's a static date.
        if self.global_substitutions["copyright_year"] == "current":
            self.global_substitutions["copyright_year"] = current_year

        ora_tapi_csv_dir = self.config_manager.config_value(config_section='file_controls',
                                                            config_key='ora_tapi_csv_dir',
                                                            default=str(APP_HOME / 'OraTAPI.csv'))

        auto_maintained_cols = self.config_manager.config_value(config_section='api_controls',
                                                            config_key='auto_maintained_cols',
                                                            default=str(APP_HOME / 'OraTAPI.csv'))
        self.auto_maintained_cols = auto_maintained_cols.replace(' ','').upper().split(',')

        row_vers_column_name = self.config_manager.config_value(config_section='api_controls',
                                                            config_key='row_vers_column_name',
                                                            default=str(APP_HOME / 'OraTAPI.csv'))



        ora_tapi_csv_dir = Path(ora_tapi_csv_dir)
        self.csv_manager = CSVManager(csv_pathname=ora_tapi_csv_dir / 'OraTAPI.csv',
                                      config_file_path=self.config_manager.config_file_path,
                                      cleanup=False)

        table_domain = self.csv_manager.csv_dict_property(schema_name=self.table.schema_name_lc,
                                                          table_name=table_name,
                                                          property_selector='domain')
        table_domain_lc = str(table_domain).lower()

        self.ut_pkg_name_prefix = self.config_manager.config_value(config_section='ut_controls',
                                                                   config_key='ut_pkg_name_prefix',
                                                                   default='ut_')

        self.ut_pkg_name_postfix = self.config_manager.config_value(config_section='ut_controls',
                                                                   config_key='ut_pkg_name_postfix',
                                                                   default='_tapi')

        self.ut_uk_test_throws = self.config_manager.config_value(config_section='ut_controls',
                                                                  config_key='ut_uk_test_throws',
                                                                  default='dup_val_on_index')

        self.ut_parent_fk_test_throws = self.config_manager.config_value(config_section='ut_controls',
                                                                         config_key='ut_parent_fk_test_throws',
                                                                         default='-02291')

        self.ut_nn_test_throws = self.config_manager.config_value(config_section='ut_controls',
                                                                  config_key='ut_nn_test_throws',
                                                                  default='-01400')

        self.ut_cc_test_throws = self.config_manager.config_value(config_section='ut_controls',
                                                                  config_key='ut_cc_test_throws',
                                                                  default='0')

        self.ut_suite = self.config_manager.config_value(config_section='ut_controls',
                                                         config_key='ut_suite',
                                                         default='')

        self.ut_prod_code = self.config_manager.config_value(config_section='ut_controls',
                                                                  config_key='ut_prod_code',
                                                                  default='UPDATE_THIS')

        ut_prod_sub_domain_code = self.config_manager.config_value(config_section='ut_controls',
                                                                  config_key='ut_prod_sub_domain_code',
                                                                  default='UPDATE_THIS')




        self.constraint_exceptions_map = {'P': self.ut_uk_test_throws, 'U': self.ut_uk_test_throws,
                                          'C': self.ut_cc_test_throws, 'N': self.ut_nn_test_throws,
                                          'R': self.ut_parent_fk_test_throws}

        self.global_substitutions["ut_suite"] = self.ut_suite
        self.global_substitutions["ut_suite_lc"] = self.ut_suite.lower()
        self.global_substitutions["ut_prod_code"] = self.ut_prod_code
        self.global_substitutions["ut_prod_code_lc"] = self.ut_prod_code.lower()

        if ut_prod_sub_domain_code.lower() == 'auto_schema':
            self.global_substitutions["ut_prod_sub_domain_code"]  = table_owner[:table_owner.find("_")]
        elif ut_prod_sub_domain_code.lower() == 'auto_table':
            self.global_substitutions["ut_prod_sub_domain_code"] = table_name[:table_name.find("_")]
        else:
            self.global_substitutions["ut_prod_sub_domain_code"] = ut_prod_sub_domain_code

        self.global_substitutions["ut_prod_sub_domain_code_lc"] = self.global_substitutions["ut_prod_sub_domain_code"].lower()

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

        self.global_substitutions["tapi_pkg_name_postfix_lc"] = str(self.global_substitutions["tapi_pkg_name_postfix"]).lower()
        self.global_substitutions["tapi_pkg_name_prefix_lc"] = str(self.global_substitutions["tapi_pkg_name_prefix"]).lower()

        self.global_substitutions["ut_pkg_name_postfix_lc"] = str(self.global_substitutions["ut_pkg_name_postfix"]).lower()
        self.global_substitutions["ut_pkg_name_prefix_lc"] = str(self.global_substitutions["ut_pkg_name_prefix"]).lower()

        self.merged_dict = self.global_substitutions | self.options_dict

        self.table = Table(database_session=database_session,
                           table_owner=table_owner,
                           table_name=table_name,
                           config_manager=config_manager,
                           trace=trace)

        self.table_constraints = TableConstraints(database_session=database_session,
                                                  table_owner=table_owner,
                                                  table_name=table_name,
                                                  config_manager=config_manager,
                                                  trace=trace)

        self.api_function_map = {
            "insert": {"procedure_name": self.insert_procname, "procedure_basename": self.insert_procname},
            "select": {"procedure_name": self.select_procname, "procedure_basename": self.insert_procname},
            "update": {"procedure_name": self.update_procname, "procedure_basename": self.insert_procname},
            "upsert": {"procedure_name": self.upsert_procname, "procedure_basename": self.insert_procname},
            "upsert_insert": {"procedure_name": self.upsert_procname + "_insert", "procedure_basename": self.upsert_procname},
            "upsert_update": {"procedure_name": self.upsert_procname + "_update", "procedure_basename": self.upsert_procname},
            "delete": {"procedure_name": self.delete_procname, "procedure_basename": self.insert_procname},
            "merge": {"procedure_name": self.merge_procname, "procedure_basename": self.insert_procname},
            "merge_insert": {"procedure_name": self.merge_procname + "_insert", "procedure_basename": self.merge_procname},
            "merge_update": {"procedure_name": self.merge_procname + "_update", "procedure_basename": self.merge_procname}
        }

        self.constraint_description_map = {
            "P": {"description": "primary Key constraint"},
            "U": {"description": "Unique Key constraint"},
            "R": {"description": "Referential Integrity constraint"},
            "C": {"description": "Check constraint"},
            "N": {"description": "Not Null constraint"}
        }

    def gen_package_body(self) -> str:
        """
        Generates the ut package body for the APIs listed in the options dictionary.

        This function is called to generate an API signature. As such it is shared for package specification and
        package body code generation.

        :return: A string containing the complete package specification.
        :rtype: str
        """


        # Load the package header and footer templates
        package_header_template = self._package_api_template(
            template_category="ut_packages",
            template_type='body',
            template_name="package_header"
        )


        package_footer_template = self._package_api_template(
            template_category="ut_packages",
            template_type='body',
            template_name="package_footer"
        )

        before_template = self._package_api_template(
            template_category="ut_packages",
            template_type='body',
            template_name="before"
        )

        after_template = self._package_api_template(
            template_category="ut_packages",
            template_type='body',
            template_name="after"
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



        # Start building the package body
        package_body = package_header_template
        package_body += before_template

        # Generate API fragments for each body API in the options
        # Get the list of API types from the options dictionary
        ut_api_types = self.options_dict.get("ut_api_types", [])

        # Create a new list to store the updated API types
        updated_api_types = []

        # Iterate over the current list and expand "merge" and "upsert"
        for api_type in ut_api_types:
            if api_type == "merge":
                updated_api_types.extend(["merge_insert", "merge_update"])
            elif api_type == "upsert":
                updated_api_types.extend(["upsert_insert", "upsert_update"])
            else:
                updated_api_types.append(api_type)

        # Replace the original list with the updated list
        ut_api_types = updated_api_types

        _package_procedure = ''
        table_desc_title = self.table.table_name.replace('_', ' ').title()
        merged_dict["table_desc_title"] = table_desc_title

        for _api_type in ut_api_types:
            mapping = self.api_function_map.get(_api_type)
            _procedure_name = mapping["procedure_name"]
            _procedure_basename = mapping["procedure_basename"]

            _package_procedure = self._construct_api_test(procedure_basename=_api_type,
                                                          procedure_name=_procedure_name,
                                                          template_type='body')

            api_type_desc = str(_api_type).title().replace('_', '-')
            merged_dict["api_type_desc"] = api_type_desc
            merged_dict["api_type_lc"] = str(_api_type).lower()
            merged_dict["procedure_name"] = _procedure_name
            merged_dict["procedure_name_lc"] = _procedure_name.lower()
            merged_dict["procedure_basename"] = _procedure_basename
            merged_dict["procedure_basename_lc"] = _procedure_basename.lower()
            merged_dict["fk_tables"] = self.table_constraints.fk_tables
            merged_dict["fk_tables_lc"] = self.table_constraints.fk_tables.lower()

            package_body += "\n" + _package_procedure
            package_body = inject_values(
                substitutions=merged_dict,
                target_string=package_body,
                stab_spaces=self.indent_spaces
            )
            pass

        for constraint in self.table_constraints.constraint_list:
            constraint_dict = self.table_constraints.constraint_metadata_dict[constraint]

            cons_columns = str(constraint_dict["cons_columns"]).replace(' ', '').upper().split(',')
            if not set(cons_columns).isdisjoint(self.auto_maintained_cols) or self.row_vers_column_name in cons_columns:
                continue

            _procedure_name = constraint_dict["constraint_name_lc"]
            constraint_type = constraint_dict["constraint_type"]
            if 'sys_' in _procedure_name and constraint_type == 'N':
                _procedure_name = f"{cons_columns[0].lower()}_not_null"

            merged_dict["throws_code"] = self.constraint_exceptions_map[constraint_type]



            _package_procedure = self._construct_constraint_test(procedure_basename=constraint,
                                                                 procedure_name=_procedure_name,
                                                                 constraint_dict=constraint_dict,
                                                                 template_type='body')

            package_body += "\n" + _package_procedure
            package_body = inject_values(
                substitutions=merged_dict,
                target_string=package_body,
                stab_spaces=self.indent_spaces
            )

        # Append the package footer
        package_body += after_template
        package_body += package_footer_template
        package_body = inject_values(
            substitutions=self.global_substitutions,
            target_string=package_body,
            stab_spaces=self.indent_spaces
        )

        return package_body



    def gen_package_spec(self) -> str:
        """
        Generates the ut package specification for the APIs listed in the options dictionary.

        This function is called to generate an API signature. As such it is shared for package specification and
        package body code generation.

        :return: A string containing the complete package specification.
        :rtype: str
        """

        # Load the package header and footer templates
        package_header_template = self._package_api_template(
            template_category="ut_packages",
            template_type='spec',
            template_name="package_header"
        )


        package_footer_template = self._package_api_template(
            template_category="ut_packages",
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
        ut_api_types = self.options_dict.get("ut_api_types", [])

        # Create a new list to store the updated API types
        updated_api_types = []

        # Iterate over the current list and expand "merge" and "upsert"
        for api_type in ut_api_types:
            if api_type == "merge":
                updated_api_types.extend(["merge_insert", "merge_update"])
            elif api_type == "upsert":
                updated_api_types.extend(["upsert_insert", "upsert_update"])
            else:
                updated_api_types.append(api_type)

        # Replace the original list with the updated list
        ut_api_types = updated_api_types

        _package_procedure = ''
        table_desc_title = self.table.table_name.replace('_', ' ').title()
        merged_dict["table_desc_title"] = table_desc_title

        for _api_type in ut_api_types:
            mapping = self.api_function_map.get(_api_type)
            _procedure_name = mapping["procedure_name"]
            _procedure_basename = mapping["procedure_basename"]

            _package_procedure = self._construct_api_test(procedure_basename=_api_type,
                                                          procedure_name=_procedure_name,
                                                          template_type='spec')

            api_type_desc = str(_api_type).title().replace('_', '-')
            merged_dict["api_type_desc"] = api_type_desc
            merged_dict["api_type_lc"] = str(_api_type).lower()
            merged_dict["procedure_name"] = _procedure_name
            merged_dict["procedure_name_lc"] = _procedure_name.lower()
            merged_dict["procedure_basename"] = _procedure_basename
            merged_dict["procedure_basename_lc"] = _procedure_basename.lower()
            merged_dict["fk_tables"] = self.table_constraints.fk_tables
            merged_dict["fk_tables_lc"] = self.table_constraints.fk_tables.lower()

            package_spec += "\n" + _package_procedure
            package_spec = inject_values(
                substitutions=merged_dict,
                target_string=package_spec,
                stab_spaces=self.indent_spaces
            )
            pass

        for constraint in self.table_constraints.constraint_list:
            constraint_dict = self.table_constraints.constraint_metadata_dict[constraint]

            cons_columns = str(constraint_dict["cons_columns"]).replace(' ', '').upper().split(',')
            if not set(cons_columns).isdisjoint(self.auto_maintained_cols) or self.row_vers_column_name in cons_columns:
                continue

            _procedure_name = constraint_dict["constraint_name_lc"]
            constraint_type = constraint_dict["constraint_type"]
            if 'sys_' in _procedure_name and constraint_type == 'N':
                _procedure_name = f"{cons_columns[0].lower()}_not_null"

            merged_dict["throws_code"] = self.constraint_exceptions_map[constraint_type]

            _package_procedure = self._construct_constraint_test(procedure_basename=constraint,
                                                                 procedure_name=_procedure_name,
                                                                 constraint_dict=constraint_dict)

            package_spec += "\n" + _package_procedure
            package_spec = inject_values(
                substitutions=merged_dict,
                target_string=package_spec,
                stab_spaces=self.indent_spaces
            )

        # Append the package footer
        package_spec += package_footer_template
        package_spec = inject_values(
            substitutions=self.global_substitutions,
            target_string=package_spec,
            stab_spaces=self.indent_spaces
        )

        return package_spec

    def _construct_api_test(self, procedure_basename: str, procedure_name: str, template_type:str = 'spec') -> str:

        procedure = self._package_api_template(template_category="ut_packages", template_type=template_type,
                                               template_name='api_test')
        subst_dict = {"api_type": procedure_basename, "procedure_name": procedure_name}

        procedure = inject_values(substitutions=subst_dict,
                                  target_string=procedure,
                                  stab_spaces=self.indent_spaces)

        return procedure

    def _construct_constraint_test(self, procedure_basename: str, procedure_name: str, constraint_dict:dict,
                                   template_type:str = 'spec') -> str:


        procedure = self._package_api_template(template_category="ut_packages", template_type=template_type,
                                               template_name='constraint_test')
        _constraint_dict = copy.deepcopy(constraint_dict)

        _constraint_dict["constraint_name"] = procedure_name.upper()
        _constraint_dict["constraint_name_lc"] = procedure_name.lower()
        subst_dict = {"api_type": procedure_basename, "procedure_name": procedure_name} | _constraint_dict


        procedure = inject_values(substitutions=subst_dict,
                                  target_string=procedure,
                                  stab_spaces=self.indent_spaces)

        return procedure


    def _package_api_template(self, template_category: str, template_type: str, template_name: str) -> str:
        """
        Reads and returns the content of a specified ut template file. The "package" templates are used to format the
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
        proj_templates = self.proj_home / TEMPLATES_LOCATION /  template_category / template_type
        template_path = proj_templates / template_name

        try:
            # Read the template file
            return template_path.read_text()
        except FileNotFoundError:
            raise FileNotFoundError(f"Template file not found: {template_path}")
        except IOError as e:
            raise IOError(f"Failed to read template file: {template_path}. Error: {e}")