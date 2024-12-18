---

# OraTAPI - Oracle Table API Generator 

## Version: 1.0.6

<b>WORK IN PROGRESS!!!</b>

OraTAPI is a Python-based tool that generates PL/SQL APIs for Oracle database tables. This tool simplifies the process of interacting with Oracle database tables by creating customisable and standardised APIs for common database operations like `insert`, `update`, `delete`, `select`, operations and more.  

OraTAPI connects to an Oracle database, retrieves table and column metadata, and generates the API package files in a staging area. These files can then be deployed to an Oracle database.

---

## Features


- **Metadata-Driven**: Automatically generates PL/SQL APIs using Oracle database metadata.
- **Table Triggers**: Generates customisable table level trigger code.
- **Views**: Generates view DDL scripts.
- **Customisable APIs**: Define API names, signatures, and behavior through a configuration file.
- **Optimistic Locking Support**: Includes `row_version` support for concurrency control.
- **Column-Specific Logic**: Exclude trigger-maintained columns and manage column defaults efficiently.
- **Directory Configuration**: Output files are neatly organised into staging directories for easy deployment.
- **Error Handling**: Configurable behavior for missing tables (skip or stop processing).

---

## Installation

1. Download the OraTAPI.tar.gz Artefact to a staging directory.

2. Open a Terminal Window and Extrract the Contents:
   For MacOS / Linux
   ```bash
   tar -xzvf <sdist_file>.tar.gz -C <path-to-installation-folder>
   ```

   For windows:
   Open a command Window and enter the command:
      ```bash
      7z x <sdist_file>.tar.gz -o<path-to-installation-folder>
   ```

   NOTE: The <path-to-installation-folder> should include an Ora_TAPI directory at the end. This does, not need to be pre-created, but including OraTAPI is to allow it to be easily recognised.

3. Complete the Installation:  
   MacOS / Linux
   ```bash
   cd <path-to-installation-folder>
   chmod 750 setup.sh
   ./setup.sh
   ```
   Windows:
   ```bash
   cd <path-to-installation-folder>
   chmod 750 setup.sh
   ./setup.bat
   ```


4. Ensure access to an Oracle database and configure your `TNS` entries or connection settings. 

Limitations: As of this release, database connections are basic - cloud wallets are not yet supported.

---

## The Primary Components

The OraTAPI too consists of 3 major components:

- The ora_tapi command line tool.
- Code templates.
- The OraTAPI.ini configuration file

The `ora_tapi` command line tool is used to launch the code generation process.

The code templates form the basic shape of the generated source code files. There are various templates which are read at runtime and constitute regions such as package file headers, footers and procedures. You can also implement view and trigger templates, and sample templates are provided for you to copy and modify. You should not amend the original sample files. These have a suffix of `.tpt.sample`. There are also `column expression` templates. These will be discussed in more detail later.

Finally, much of the behaviour of OraTAPI is governed by the configuration of the `OraTAPI.ini` file, which is located in the `config` directory. The OraTAPI.ini file consists of property/value pairs, which are located into various sections, which are used to categorise their purpose. Section names are enclosed in square brackets (<i>e.g. [<api_controls]</i>). For the purposes of the OraTAPI, each property name in the file must be globally unique, irrespective of which section it belongs to.

### Command Line Tools
Launching the command line tools, varies slightly depending on your target operating system. There are two tools that you will need to work with, `conn_mgr` and `ora_tapi`. The latter of these will be used more frequently.

In respect of the `conn_mgr` tool, this is used to securely store database connections (credentials and DSNs).

The following launcher commands are provided:

#### Windows:
- ora_tapi.ps1
- conn_mgr.ps1

#### MacOS / Linux:
- ora_tapi.sh
- conn_mgr.sh

These are located in the `<OraTAPI-Home>/bin` directory. 

To get command line help, you can simply type something like:

```
cd <OraTAPI-home>
./bin/ora_tapi.sh -h

usage: ora_tapi.py [-h] [-A APP_NAME] [-a TAPI_AUTHOR] [-c CONN_NAME] [-d DSN] [-g STAGING_AREA_DIR] [-p DB_PASSWORD] [-s] [-To TABLE_OWNER] [-t TABLE_NAMES] [-po PACKAGE_OWNER] [-to TRIGGER_OWNER]
                   [-vo VIEW_OWNER] [-u DB_USERNAME] [-T API_TYPES]

Oracle Table API Generator

options:
  -h, --help            show this help message and exit
  -A APP_NAME, --app_name APP_NAME
                        Application name - included to the package header.
  -a TAPI_AUTHOR, --tapi_author TAPI_AUTHOR
                        TAPI author
  -c CONN_NAME, --conn_name CONN_NAME
                        Connection name for saved configuration
  -d DSN, --dsn DSN     Database data source name (TNS name)
  -g STAGING_AREA_DIR, --staging_area_dir STAGING_AREA_DIR
                        Directory for staging area (default: <APP_HOME>/staging)
  -p DB_PASSWORD, --db_password DB_PASSWORD
                        Database password
  -s, --save_connection
                        Save/update the connection for future use. Connections are only saved after a successful connection.
  -To TABLE_OWNER, --table_owner TABLE_OWNER
                        Database schema name of the tables from which to generate the code.
  -t TABLE_NAMES, --table_names TABLE_NAMES
                        Comma separated list of table names (default: all)
  -po PACKAGE_OWNER, --package_owner PACKAGE_OWNER
                        Database schema in which to place the TAPI package.
  -to TRIGGER_OWNER, --trigger_owner TRIGGER_OWNER
                        The schema in which owns the generated triggers.
  -vo VIEW_OWNER, --view_owner VIEW_OWNER
                        The schema in which owns the generated views.
  -u DB_USERNAME, --db_username DB_USERNAME
                        Database username
  -T API_TYPES, --api_types API_TYPES
                        Comma-separated list of API types (e.g., create,read). Must be one or more of: create, read, update, upsert,delete, merge.

```

## Usage

Run OraTAPI from the command line with the desired options.

### Basic Example:
```bash
ora_tapi.sh -P APP_OWNER -S HR -t EMPLOYEES,DEPARTMENTS
```

### Full Command-Line Arguments:
| Argument                     | Description                                                                                 | Default                  |
|------------------------------|---------------------------------------------------------------------------------------------|--------------------------|
| `-A`, `--app_name`           | Application name included in the package header.                                            | `Undefined`              |
| `-a`, `--tapi_author`        | Author name for the package header.                                                         | `OraTAPI generator`      |
| `-c`, `--conn_name`          | Connection name for saved configuration.                                                    |                          |
| `-d`, `--dsn`                | Database Data Source Name (TNS entry).                                                      |                          |
| `-g`, `--staging_area_dir`   | Directory for the staging area.                                                             | `./staging`              |
| `-p`, `--db_password`        | Database password.                                                                          |                          |
| `-P`, `--package_owner`      | Schema to own the generated TAPI packages (required).                                       |                          |
| `-s`, `--save_connection`    | Save connection details for future use.                                                     | `False`                  |
| `-S`, `--schema_name`        | Schema containing the target tables (required).                                             |                          |
| `-t`, `--table_names`        | Comma-separated list of tables (use `%` for all tables).                                    | `%`                      |
| `-to`, `--trigger_owner`     | The schema in which the generated scripts should create the triggers.                       |                          |
| `-vo`, `--view_owner`        | The schema in which the generated scripts should create the views.                          |                          |
| `-u`, `--db_username`        | Database username.                                                                          |                          |
| `-T`, `--api_types`          | Comma-separated list of API types (e.g., `create, read`).                                   | Configured default types |

---

## Output Structure

Generated files are written to the staging area and organised into subdirectories:
- **Package Specification (`spec_dir`)**: Contains `.sql` files defining the PL/SQL package interface.
- **Package Body (`body_dir`)**: Contains `.sql` files implementing the PL/SQL package logic.
- **View (`view`)**: Contains `.sql` files implementing any generated view scripts.
- **Trigger (`view`)**: Contains `.sql` files implementing any generated trigger scripts.

Each API package is customised based on a combination of the `.ini` configuration, command-line options and template files.

The majority of command line options have defaults which can be set via the OraTAPI.ini configuration file. 

---

These are just a few of the controls. Read on for 

### Configuration Settings for OraTAPI.ini

This document explains the different sections and parameters of the configuration file used by **OraTAPI**.

---

#### [OraTAPI]
- **version**: Specifies the version of the OraTAPI being used.
  - Example: `version = 1.0.6`
  - **Purpose**: Tracks the version of the tool for compatibility and updates. 

  THIS SETTING SHOULD NOT BE MODIFIED!

---

#### [project]
- **default_app_name**: Defines the default name of the application, used as a reference when generating API names.
  - Example: `default_app_name = Human Resources`
  - **Purpose**: Helps identify the application context for the generated APIs.

---

#### [copyright]
- **company_name**: Specifies the company name for the copyright information.
  - Example: `company_name = Clive's Software Emporium`
  - **Purpose**: Customises the copyright message in the generated code.
  
- **copyright_year**: Sets the year for the copyright, either as a static year or the word "current" to reflect the generation date.
  - Example: `copyright_year = current`
  - **Purpose**: Dynamically reflects the year when the TAPI was generated.

---

#### [behaviour]
- **skip_on_missing_table**: Determines whether missing tables are skipped or cause an error.
  - Example: `skip_on_missing_table = true`
  - **Purpose**: Controls error handling when a table specified in the API generation process is missing. If true, processing continues; if false, an error halts the process.

---

#### [formatting]
- **indent_spaces**: Defines the number of spaces for indentation in the generated SQL files.
  - Example: `indent_spaces = 3`
  - **Purpose**: Controls the indentation style to ensure consistent formatting across generated code.

  NOTE: The templates have embedded %STAB% substitution placeholders, which are replaced with the number of spaces as defined by the `indent_spaces` property.

---

#### [file_controls]
- **default_staging_dir**: Specifies the root directory where the generated files will be written.
  - Example: `default_staging_dir = /u02/projects/demo/staging`
  - **Purpose**: Defines the folder where all generated files will be placed by default. The default location is `staging` and is located directliy below the OraTAPI installation root folder. You can specvify a pathname relative to the OraTAPI installation root folder, or a full pathname. This can be overridden at runtime, using the `-g/--staging_area_dir` argument.
  
  Sub-directories are created at run-time, as required, to host the generated code. The names of the sub-directories are configurable (read on).
  
- **body_suffix** & **spec_suffix**: Set the file suffix for the package body and specification files.
  - Examples:   
  `spec_suffix = .pks`   
  `body_suffix = .pkb`  
  - **Purpose**: Specifies the file extension for generated SQL files. The default for these is `.sql`.

- **spec_dir** & **body_dir**: Define the directories for package specification and package body files.
  - Example: `spec_dir = package_spec`
  - **Purpose**: Organises generated files in a specific staging sub-directory for clarity and structure.

- **trigger_dir**: Define the directory for trigger files.
  - Example: `trigger_dir = trigger`
  - **Purpose**: Organises generated trigger source files in a specific staging sub-directory for clarity and structure.

- **view_dir**:  Define the directory for view source files.
  - Example: `view_dir = view`
  - **Purpose**:  Organises generated view source files in a specific staging sub-directory for clarity and structure.

- **ora_tapi_csv_dir**: Defines the directory for the OraTAPI CSV file.
  - Example: `ora_tapi_csv_dir = `
  - **Purpose**: Used to control which files should be generated based on the CSV configuration file. This allows fine grain control of which files should be generated and written. New file entries are automatically added when tables are processed and no corresponding entry is found.

---

#### [api_controls]
- **delete_procname**: Specifies the procedure name to be used for the delete API.
  - Example: `delete_procname = del`
  - **Purpose**: Customises the naming conventions for the delete procedure.

- **select_procname**: Specifies the procedure name to be used for select API.
  - Example: `select_procname = get`
  - **Purpose**: Customises the naming conventions for the select procedure.

- **insert_procname**: Specifies the procedure name to be used for insert API.
  - Example: `insert_procname = ins`
  - **Purpose**: Customises the naming conventions for the insert procedure.

- **merge_procname**: Specifies the procedure name to be used formerge API.
  - Example: `merge_procname = mrg`
  - **Purpose**: Customises the naming conventions for the merge procedure.

- **update_procname**: Specifies the procedure name to be used for update API.
  - Example: `update_procname = upd`
  - **Purpose**: Customises the naming conventions for the update procedure.

- **upsert_procname**: Specifies the procedure name to be used for upsert API.
  - Example: `upsert_procname = ups`
  - **Purpose**: Customises the naming conventions for the upsert procedure.

- **auto_maintained_cols**: A comma-separated list of columns managed automatically by triggers or column expressions (e.g., timestamps, user fields).
  - Example: `auto_maintained_cols = created_by, created_on, updated_by, updated_on`
  - **Purpose**: Prevents these columns from being included in data modification APIs, but they are returned in select APIs. These are assumed to be maintained by triggers, or OraTAPI column expressions.

- **col_auto_maintain_method**: Defines how auto-maintained columns maintained.
  - Example: `col_auto_maintain_method = trigger`
  - **Purpose**: Specifies whether column values are managed via database triggers or column expressions. For column expressions, the setting is `expression`.

- **row_vers_column_name**: Defines the column name used for optimistic locking.
  - Example: `row_vers_column_name = row_version`
  - **Purpose**: Enables optimistic locking by tracking changes to rows using a version number. Setting this for a common table column name, results in the inclusion of an `out` parameter, wherever the named column is found in a table..

- **signature_types**: Defines the API signature types (rowtype or coltype).
  - Example: `signature_types = rowtype, coltype`
  - **Purpose**: Determines whether to generate APIs which implement parameters as rowtypes (p_row) or column types (one parameter for each column). This must be set to `coltype` and / or `rowtype`.

- **include_defaults**: Includes default values for insert APIs.
  - Example: `include_defaults = true`
  - **Purpose**: Ensures that default values for table columns are included in insert APIs.

- **noop_column_string**: Defines a string to be used for non-key, character string type column parameter defaults.
  - Example: `noop_column_string = auto`
  - **Purpose**: Helps avoid passing unnecessary parameters by preserving existing values. Comment out of remove value assigned to disable. The value can be set to a character string, the value `auto`, or `dynamic`. Setting to `dynamic` involves a slight resource overhead at runtime.

- **default_api_types**: Specifies which types of APIs should be included by default.
  - Example: `default_api_types = insert, select, update, delete`
  - **Purpose**: Controls which API types are generated by default. Options are insert, select, update, delete, upsert, and merge. These can be overridden at runtime via the `-T/--api_types` command line argument.
P
- **return_pk_columns**: Determines whether primary or unique key columns are included as in/out parameters in the generated APIs.
  - Example: `return_pk_columns = true`
  - **Purpose**: Ensures primary/unique key columns are returned in APIs that modify data.

- **include_commit**: Defines whether a commit parameter should be included.
  - Example: `include_commit = true`
  - **Purpose**: Includes a commit parameter to control transaction behavior.

---

#### [schemas]
- **default_table_owner**: Specifies the default schema for tables.
  - Example: `default_table_owner = aut`
  - **Purpose**: Sets the default schema for tables, which can be overridden by command-line arguments.

- **default_package_owner**: Specifies the default schema for packages.
  - Example: `default_package_owner = aut`
  - **Purpose**: Sets the default schema for packages, which can be overridden by command-line arguments.

- **default_view_owner**: Specifies the default schema for views.
  - Example: `default_view_owner = aut`
  - **Purpose**: Sets the default schema for views, which can be overridden by command-line arguments.

- **default_trigger_owner**: Specifies the default schema for triggers.
  - Example: `default_trigger_owner = aut`
  - **Purpose**: Sets the default schema for triggers, which can be overridden by command-line arguments.

---

#### [misc]
- **view_name_suffix**: Defines a suffix that is added to the derived view name.
  - Example: `view_name_suffix = _v`
  - **Purpose**: Customises the name of generated views by appending the suffix.

---

#### [console]
- **INFO_COLOUR**, **WARN_COLOUR**, **ERR_COLOUR**, **CRIT_COLOUR**, **HIGH_COLOUR**: Defines color schemes for different output categories.
  - Example: `INFO_COLOUR = white`
  - **Purpose**: Customises the colors used in the console output for different log levels (info, warning, error, etc.).

- **colour_console**: Enables or disables color output in the console.
  - Example: `colour_console = true`
  - **Purpose**: Controls whether colored output is shown in the console.

---

#### Example configuration file:

```
[OraTAPI]
version = 1.0.6

[project]
default_app_name = Human Resources

[copyright]
# company_name: Modify company name to reflect your company
company_name = Clive`s Software Emporium
# copyright_year: set to a static year or the word current, to reflect the date the TAPI was generated.
copyright_year = current

[behaviour]
# skip_on_missing_table: If set to true and a specified table is not found, then report the table as missing
# but continue processing. If set to false, and error is reported and processing is terminated. Only pertinent
# when using the -t/--table_names argument.
skip_on_missing_table = true

[formatting]
indent_spaces = 3

[file_controls]
# The root location where the generated files are to be written. A simple directory name is assumed to be located
# below the OraTAPI root folder. Full path-names are permissible.
default_staging_dir = staging
# The suffix properties are appended to the respective files.
body_suffix = .sql
spec_suffix = .sql

# spec_dir/body_dir: these define the locations where the package specification and package body files are to be
# written. Simple names (no slashes) are assumed to below the install home directory of OraTAPI.
spec_dir = package_spec
body_dir = package_body
# Set the trigger_dir property to have any triggers generated from the trigger templates.
trigger_dir = trigger
# Set the view_dir property to have any triggers generated from the view templates.
view_dir = view

# Set the directory pathname to locate the OraTAPI.csv file. If unset it is assumed to be located under the OraTAPI
# install directory. This file is used to fine control which files should be generated.
ora_tapi_csv_dir =

[api_controls]
# API naming properties follow. Set these to the preferred procedure names, of the APIs
delete_procname = del
select_procname = get
insert_procname = ins
merge_procname  = mrg
update_procname = upd
upsert_procname = ups

# auto_maintained_cols is a comma separated list of columns which are not to be set by the TAPI parameters.
# These are columns typically auto-maintained by triggers or column expressions. As such they are not included in APIs
# responsible for data modifications. However they are included in select API return parameters.
auto_maintained_cols = created_by, created_on, updated_by, updated_on

# col_auto_maintain_method: Set to `trigger` or `expression`, it is assumed that your table triggers
# are to manage the modification of the columns. However, if set to `expression`, you must define a column expression
# for each of the named columns.
col_auto_maintain_method = trigger

# row_vers_column_name: For optimistic locking (optional). Name the optimistic column name.
# Leave empty or comment out, if not implemented. Update TAPIs, return this as an "out" parameter.
row_vers_column_name = row_version

# signature_types: One of more comma separated values. Valid values: rowtype, coltype. Default is rowtype.
# coltype causes parameter signatures with a parameter for each table column, for the select, insert, update and
# merge APIs. rowtype, causes signatures based on primary keys and a table rowtype.
signature_types = rowtype, coltype

# include_defaults: Set to true, to have parameter defaults included to insert APIs,
# reflect those in the data dictionary.
include_defaults = true

# noop_column_string: If set, parameter defaults for non-key column parameters are defined as <no_column_op_string>.
# If the default is detected, then the column value in the database is preserved. This provides a mechanism of
# avoiding to pass all parameters unnecessarily. This only applies to the "coltype" signature types (see the
# signature_types property). Set to auto, to have a (static) generated, enhanced GUID (42 characters in total) Set to
dynamic to have the NOOP character string (partly, by sys_guid()) dynamically generated on a per-session basis.
# noop_column_string = auto
# noop_column_string = #NO~OP#

# default_api_types: Specifies the default of which APIs to include to the package.
# Comma separated - must be one or more of insert, select, update, delete, upsert, merge.
# default_api_types = insert, select, update, delete, upsert, merge
default_api_types = insert

# return_pk_columns: If set to true, causes primary/unique keys to be in/out parameters. Returning the values.
# This applies to APIs which modify data.
return_key_columns = true
return_pk_columns = true
return_ak_columns = false
# Include p_commit boolean parameter (in). Should be set to true or false. Typically this would be set to false.
include_commit = true

[schemas]
# Set default owners. These can be overridden on the command line.
# default_table_owner can be overridden using the -to / --table_owner argument.
default_table_owner = aut

# default_package_owner can be overridden using the -po / --package_owner argument.
default_package_owner = aut

# default_view_owner can be overridden using the -vo / --view_owner argument.
default_view_owner = aut

# default_trigger_owner can be overridden using the -to / --trigger_owner argument.
default_trigger_owner = aut

[misc]
# The view_name_suffix is appended to the end of the derived view name
view_name_suffix = _v

[console]
INFO_COLOUR = white
WARN_COLOUR = bold yellow
ERR_COLOUR = bold red
CRIT_COLOUR = bold red
HIGH_COLOUR = bold blue
# Set colour_console to false, to disable colour output.
colour_console = true

```


### Sample Generated API:
For a table `employees`:
```sql
g`"authid definer
as
--------------------------------------------------------------------------------
--
-- Copyright(C) 15-Dec-2024, Clive`s Software Emporium
-- All Rights Reserved
--
--------------------------------------------------------------------------------
-- Application      :   Human Resources
-- Sub-module       :   %sub_module%
-- Source file name :   employees_tapi.sql
-- Purpose          :   Table API (TAPI) for table employees
--
-- HAS COMMITS      :   NO
-- HAS ROLLBACKS    :   NO
--
-- Notes            :   Generated by cbostock on 15-Dec-2024
--  
--------------------------------------------------------------------------------

--------------------------------------------------------------------------------
--< PUBLIC TYPES AND GLOBALS >--------------------------------------------------

   subtype ty_row is employees%rowtype;

   g_row ty_row;

--------------------------------------------------------------------------------

--------------------------------------------------------------------------------
--< PUBLIC METHODS >------------------------------------------------------------



   -----------------------------------------------------------------------------
   -- Insert TAPI for: aut.employees
   -----------------------------------------------------------------------------
   procedure ins
   (
        p_employee_id         in       employees.employee_id%type
      , p_row                 in out   employees%rowtype
      , p_commit              in       boolean                                 := false
   );



   -----------------------------------------------------------------------------
   -- Insert TAPI for: aut.employees
   -----------------------------------------------------------------------------
   procedure ins
   (
        p_employee_id         in out   employees.employee_id%type
      , p_first_name          in       employees.first_name%type
      , p_last_name           in       employees.last_name%type
      , p_email               in       employees.email%type
      , p_phone_number        in       employees.phone_number%type
      , p_hire_date           in       employees.hire_date%type                := current_date
      , p_job_id              in       employees.job_id%type
      , p_salary              in       employees.salary%type
      , p_commission_pct      in       employees.commission_pct%type
      , p_manager_id          in       employees.manager_id%type
      , p_department_id       in       employees.department_id%type            := 210
      , p_row_version            out   employees.row_version%type
      , p_commit              in       boolean                                 := false
   );

end employees_tapi;
/

```

```sql
create or replace package body aut.employees_tapi
as
--------------------------------------------------------------------------------
--
-- Copyright(C) 15-Dec-2024, Clive`s Software Emporium
-- All Rights Reserved
--
--------------------------------------------------------------------------------
-- Application      :   Human Resources
-- Sub-module       :   %sub_module%
-- Package          :   %schema_name_lc%.employees_tapi
-- Source file name :   employees_tapi.sql
-- Purpose          :   Table API (TAPI) for table employees
--
-- Notes            :   Generated using OraTAPI, by cbostock on 15-Dec-2024.
--------------------------------------------------------------------------------

--------------------------------------------------------------------------------
--< PRIVATE TYPES AND GLOBALS >-------------------------------------------------
--------------------------------------------------------------------------------

--------------------------------------------------------------------------------
--< PRIVATE METHODS >-----------------------------------------------------------
--------------------------------------------------------------------------------

--------------------------------------------------------------------------------
--< PUBLIC METHODS >------------------------------------------------------------


   -----------------------------------------------------------------------------
   -- Insert TAPI for: aut.employees
   -----------------------------------------------------------------------------
   procedure ins
   (
        p_employee_id         in       employees.employee_id%type
      , p_row                 in out   employees%rowtype
      , p_commit              in       boolean                                 := false
   )
   is
   -- #insert#
   begin

      insert into employees
         (
              employee_id
            , first_name
            , last_name
            , email
            , phone_number
            , hire_date
            , job_id
            , salary
            , commission_pct
            , manager_id
            , department_id
         )
      values
         (
              p_row.employee_id
            , p_row.first_name
            , p_row.last_name
            , p_row.email
            , p_row.phone_number
            , p_row.hire_date
            , p_row.job_id
            , p_row.salary
            , p_row.commission_pct
            , p_row.manager_id
            , p_row.department_id
         )
      returning
              employee_id
            , row_version
            into
              p_row.employee_id
            , p_row.row_version;

      if p_commit
      then
         commit;
      end if;

   end ins;

   -----------------------------------------------------------------------------
   -- Insert TAPI for: aut.employees
   -----------------------------------------------------------------------------
   procedure ins
   (
        p_employee_id         in out   employees.employee_id%type
      , p_first_name          in       employees.first_name%type
      , p_last_name           in       employees.last_name%type
      , p_email               in       employees.email%type
      , p_phone_number        in       employees.phone_number%type
      , p_hire_date           in       employees.hire_date%type                := current_date
      , p_job_id              in       employees.job_id%type
      , p_salary              in       employees.salary%type
      , p_commission_pct      in       employees.commission_pct%type
      , p_manager_id          in       employees.manager_id%type
      , p_department_id       in       employees.department_id%type            := 210
      , p_row_version            out   employees.row_version%type
      , p_commit              in       boolean                                 := false
   )
   is
   -- #insert#
   begin

      insert into employees
         (
              employee_id
            , first_name
            , last_name
            , email
            , phone_number
            , hire_date
            , job_id
            , salary
            , commission_pct
            , manager_id
            , department_id
         )
      values
         (
              p_employee_id
            , p_first_name
            , p_last_name
            , p_email
            , p_phone_number
            , p_hire_date
            , p_job_id
            , p_salary
            , p_commission_pct
            , p_manager_id
            , p_department_id
         )
      returning
              employee_id
            , row_version
            into
              p_employee_id
            , p_row_version;

      if p_commit
      then
         commit;
      end if;

   end ins;
end employees_tapi;
/

```
---

## Auto Column Management
Under the `api_controls` section of `OraTAPI.ini`, there are two entries, pertaining to auto managed columns. These allow you to configure how you manage your auto-managed columns. These are typically columns which you wish to be managed either by triggers or via the table APIs, and as such there are no input parameters to populate them. For example, you may have columns which are used to track, who created or last updated a row. The entries that control the bahaviour are:

- col_auto_maintain_method
- auto_maintained_cols
- row_vers_column_name

### The col_auto_maintain_method Property
If you are using columns which you want to be automatically updated during DML operations, you should set this property value to one of: 

- trigger
- expression

#### Trigger Maintained
If you set the `col_auto_maintain_method` proprty to <i>trigger</i>, you should ensure that your trigger template(s) is designed to make appropriate updates, for on the columns that you list. Example:

```
create or replace trigger %trigger_owner_lc%.%table_name_lc%_biu
before insert or update on %table_owner_lc%.%table_name_lc%
for each row
begin

   if inserting then
      :new.row_version := 1;
   elsif updating then
      :new.updated_on := current_timestamp;
      :new.updated_by := coalesce(sys_context('APEX$SESSION','APP_USER'), sys_context('USERENV', 'PROXY_USER'), sys_context('USERENV','SESSION_USER'), user);
      :new.row_version := :old.row_version + 1;
   end if;

end;
/
```
#### Column Expression Maintained
Column expressions are maintained, via special templates. These are located in the `templates/column_expressions` directory.
This has twoo sub-directories:

- inserts
- updates

If the `col_auto_maintain_method` property, is set to `expression`, then for each column listed in the `auto_maintained_cols` and `row_vers_column_name` proprties, a template entry is needed for each column in th `inserts` and `updates` directories. These expressions are injected into assignment statements for the generated API procedures. For example, assume we have a column called `row_version`, we would expect to find a `row_version.tpt` file in each of the `inserts` and `updates` directories. The contents of these might look like this:

inserts\row_version.tpt:
```
1
```
updates\row_version.tpt:
```
row_version + 1
```


### The auto_maintained_cols Property
This is a comma separated list of columns which are maintained either by table triggers or by use of column expressions, configured to appear within the generated TAPIs (more on these a little later).

This list should not include the column included to the `row_version_column_name` property (if one is set).

### The row_version_column_name Property
The row_version_column_name, need not be set, if you are not interested in the optimistic locking aspects of the TAPI generation, however, if it is set, <b>ensure that the row_version_column_name column name is not included to the `auto_maintained_cols` list of columns</b>. 



## Connection Manager

The connection manager allows you to treat database connections in a similar manner to named connections in `SQLcl`. Connection credentials and DNS (TNS) strings can be stored and retrieved locally, by use of a conventient name. Credentials are transparrently encrypted/decrypted from a locally maintained store. The `ora_tapi` command allows you to save credentials and a connect string, by using a combination of the following command line arguments:

- -p / --db_password
- -u / --db_username
- -d / --dsn
- -s / --save_connection

However, for more complete control, you need to use the `conn_mgr` command. This allows you to:

- List your connections
- Add new connections
- Update connections
- Delete connections

The Add and Update options cause the `conn_mgr` to enter an interactive dialog mode.

Synopsis:

```
cd <OraTAPI-home>
./bin/conn_mgr.sh -h

usage: conn_mgr.py [-h] (-c | -e | -d | -l) [-n NAME]

Database connection manager.

options:
  -h, --help            show this help message and exit
  -c, --create          Create a new connection.
  -e, --edit            Edit an existing connection.
  -d, --delete          Delete an existing connection.
  -l, --list            List all connections.
  -n NAME, --name NAME  Name of the connection.

Used to create/edit/delete or store named database connections.Database connections are stored, encrypted, in a local store.

```
The `-n/--name` option is mandatory in conjunction with all other options, with the exception of the `-l/--list` option. Also the `-c/--create`, `-e/--edit`, `-d/--delete` options are mutually exclusive.

Connection credentials are stored with 256 bit AES encryption, to a local store, at: `<USER_HOME_DIR>/.OraTAPI/dsn_credentials.ini`.  

<b>NOTE: The credentials store is non-transportable. If you try to use it on a computer on which it was not maintained, the decryption will fail.</b>

## License

OraTAPI is licensed under the [MIT License](LICENSE).

---

This README covers the tool's purpose, usage, configuration, and output, providing a clear guide for potential users. Let me know if you'd like any adjustments!
