---

# OraTAPI - Oracle Table API Generator

<b>WORK IN PROGRESS!!!</b>

OraTAPI is a Python-based tool that generates PL/SQL APIs for Oracle database tables. This tool simplifies the process of interacting with database tables by creating customizable and standardized APIs for common database operations like `insert`, `update`, `delete`, `select`, and more.  

OraTAPI connects to an Oracle database, retrieves table and column metadata, and generates the API package files in a staging area. These files can then be deployed to the database.

---

## Features


- **Metadata-Driven**: Automatically generates PL/SQL APIs using Oracle database metadata.
- **Customizable APIs**: Define API names, signatures, and behavior through a configuration file.
- **Optimistic Locking Support**: Includes `row_version` support for concurrency control.
- **Column-Specific Logic**: Exclude trigger-maintained columns and manage column defaults efficiently.
- **Directory Configuration**: Output files are neatly organized into staging directories for easy deployment.
- **Error Handling**: Configurable behavior for missing tables (skip or stop processing).

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/<username>/oratapi.git
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure access to an Oracle database and configure your `TNS` entries or connection settings.

---

## Configuration

OraTAPI is controlled by an `.ini` configuration file. Below is a summary of the main sections and their settings.

### **[behaviour]**
- `skip_on_missing_table`: `true` to skip missing tables, or `false` to terminate processing.

### **[copyright]**
- `company_name`: Your company name for package headers.
- `copyright_year`: Use `current` for the current year or a static value.

### **[formatting]**
- `indent_spaces`: Number of spaces for code indentation.

### **[file_controls]**
- `default_staging_dir`: Root directory for generated files.
- `spec_dir` and `body_dir`: Subdirectories for package specifications and bodies.

### **[api_controls]**
- Define API procedure names and behaviors for operations like `insert`, `update`, and `delete`.
- `trigger_maintained`: Specify columns maintained by triggers to exclude them from certain APIs.
- `signature_types`: Use `rowtype` or `coltype` signatures for parameter handling.
- `default_api_types`: Comma-separated list of default API types to include (e.g., `insert, select`).
- `noop_column_string`: Default string to signal no operation for non-key columns.

For detailed descriptions, refer to the comments in the `oratapi.ini` file.

---

## Usage

Run OraTAPI from the command line with the desired options.

### Basic Example:
```bash
python oratapi.py -P APP_OWNER -S HR -t EMPLOYEES,DEPARTMENTS
```

### Full Command-Line Arguments:
| Argument                     | Description                                                                                 | Default                  |
|------------------------------|---------------------------------------------------------------------------------------------|--------------------------|
| `-A`, `--app_name`           | Application name included in the package header.                                            | `Undefined`             |
| `-a`, `--tapi_author`        | Author name for the package header.                                                        | `OraTAPI generator`     |
| `-c`, `--conn_name`          | Connection name for saved configuration.                                                   |                          |
| `-d`, `--dsn`                | Database Data Source Name (TNS entry).                                                     |                          |
| `-g`, `--staging_area_dir`   | Directory for the staging area.                                                            | `./staging`             |
| `-p`, `--db_password`        | Database password.                                                                          |                          |
| `-P`, `--package_owner`      | Schema to own the generated TAPI packages (required).                                       |                          |
| `-s`, `--save_connection`    | Save connection details for future use.                                                    | `False`                 |
| `-S`, `--schema_name`        | Schema containing the target tables (required).                                            |                          |
| `-t`, `--table_names`        | Comma-separated list of tables (use `%` for all tables).                                   | `%`                      |
| `-u`, `--db_username`        | Database username.                                                                          |                          |
| `-F`, `--force_overwrite`    | Overwrite existing files in the staging area.                                              | `False`                 |
| `-T`, `--api_types`          | Comma-separated list of API types (e.g., `create, read`).                                  | Configured default types |

---

## Output Structure

Generated files are written to the staging area and organized into subdirectories:
- **Package Specification (`spec_dir`)**: Contains `.sql` files defining the PL/SQL package interface.
- **Package Body (`body_dir`)**: Contains `.sql` files implementing the PL/SQL package logic.

Each API package is customized based on the `.ini` configuration and command-line options.

---

## Examples

### Sample Configuration:
```ini
[api_controls]
delete_procname = del
insert_procname = ins
update_procname = upd
select_procname = get
default_api_types = insert, select, update, delete
signature_types = rowtype, coltype
trigger_maintained = created_by, created_on, updated_by, updated_on
row_vers_column_name = row_version
```

### Sample Generated API:
For a table `employees`:
```sql
create or replace package agr_api.employees_tapi
authid definer
as
--------------------------------------------------------------------------------
--
-- Copyright(C) 05-Dec-2024, Clive`s Software Emporium
-- All Rights Reserved
--
--------------------------------------------------------------------------------
-- Application      :   Undefined
-- Sub-module       :   %sub_module%
-- Source file name :   employees_tapi.sql
-- Purpose          :   Table API (TAPI) for table employees
--
-- HAS COMMITS      :   NO
-- HAS ROLLBACKS    :   NO
--
-- Notes            :   Generated by Clive on 05-Dec-2024
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
   -- Upsert TAPI for: aut.employees
   -----------------------------------------------------------------------------
   procedure ups
   (
        p_employee_id         in       employees.employee_id%type
      , p_row                 in out   employees%rowtype
   );



   -----------------------------------------------------------------------------
   -- Upsert TAPI for: aut.employees
   -----------------------------------------------------------------------------
   procedure ups
   (
        p_employee_id         in out   employees.employee_id%type
      , p_first_name          in       employees.first_name%type                    := '#NO~OP#'
      , p_last_name           in       employees.last_name%type                     := '#NO~OP#'
      , p_email               in out   employees.email%type
      , p_phone_number        in       employees.phone_number%type                  := '#NO~OP#'
      , p_hire_date           in       employees.hire_date%type                     := '#NO~OP#'
      , p_job_id              in       employees.job_id%type                        := '#NO~OP#'
      , p_salary              in       employees.salary%type                        := '#NO~OP#'
      , p_commission_pct      in       employees.commission_pct%type                := '#NO~OP#'
      , p_manager_id          in       employees.manager_id%type                    := '#NO~OP#'
      , p_department_id       in       employees.department_id%type                 := '#NO~OP#'
      , p_row_version            out   employees.row_version%type
   );

end employees_tapi;
/

```

```sql
create or replace package body agr_api.employees_tapi
as
--------------------------------------------------------------------------------
--
-- Copyright(C) 05-Dec-2024, Clive`s Software Emporium
-- All Rights Reserved
--
--------------------------------------------------------------------------------
-- Application      :   Undefined
-- Sub-module       :   %sub_module%
-- Package          :   aut.employees_tapi
-- Source file name :   employees_tapi..sql
-- Purpose          :   Table API (TAPI) for table employees
--
-- Notes            :   Generated using OraTAPI, by Clive on 05-Dec-2024.
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
   -- Select TAPI for: aut.employees
   -----------------------------------------------------------------------------
   procedure ups
   (
        p_employee_id         in       employees.employee_id%type
      , p_row                    out   employees%rowtype
   )
   is
   -- #upsert#
   %begin

      update employees
      set
           first_name                     = p_row.first_name
         , last_name                      = p_row.last_name
         , email                          = p_row.email
         , phone_number                   = p_row.phone_number
         , hire_date                      = p_row.hire_date
         , job_id                         = p_row.job_id
         , salary                         = p_row.salary
         , commission_pct                 = p_row.commission_pct
         , manager_id                     = p_row.manager_id
         , department_id                  = p_row.department_id
         , created_by                     = p_row.created_by
         , created_on                     = p_row.created_on
      where
           employee_id = p_employee_id
      returning 
           employee_id
         , email
         , row_version;
      into 
              p_row.employee_id
            , p_row.email
            , p_row.row_version;

      if sql%rowcount = 0
      then
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
            , created_by
            , created_on
            , row_version
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
            , p_row.created_by
            , p_row.created_on
            , p_row.row_version
            )
         returning %return_column_list_lc%;
         into 
              p_row.employee_id
            , p_row.email
            , p_row.row_version;
      end if;

   end ups;

   -----------------------------------------------------------------------------
   -- Select TAPI for: aut.employees
   -----------------------------------------------------------------------------
   procedure ups
   (
        p_employee_id         in out   employees.employee_id%type
      , p_first_name             out   employees.first_name%type
      , p_last_name              out   employees.last_name%type
      , p_email               in out   employees.email%type
      , p_phone_number           out   employees.phone_number%type
      , p_hire_date              out   employees.hire_date%type
      , p_job_id                 out   employees.job_id%type
      , p_salary                 out   employees.salary%type
      , p_commission_pct         out   employees.commission_pct%type
      , p_manager_id             out   employees.manager_id%type
      , p_department_id          out   employees.department_id%type
      , p_row_version            out   employees.row_version%type
   )
   is
   -- #upsert#
   %begin

      update employees
      set
           first_name                     = p_first_name
         , last_name                      = p_last_name
         , email                          = p_email
         , phone_number                   = p_phone_number
         , hire_date                      = p_hire_date
         , job_id                         = p_job_id
         , salary                         = p_salary
         , commission_pct                 = p_commission_pct
         , manager_id                     = p_manager_id
         , department_id                  = p_department_id
         , created_by                     = p_created_by
         , created_on                     = p_created_on
      where
           employee_id = p_employee_id
      returning 
           employee_id
         , email
         , row_version;
      into 
              p_employee_id
            , p_email
            , p_row_version;

      if sql%rowcount = 0
      then
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
            , created_by
            , created_on
            , row_version
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
            , p_created_by
            , p_created_on
            , p_row_version
            )
         returning %return_column_list_lc%;
         into 
              p_employee_id
            , p_email
            , p_row_version;
      end if;

   end ups;
end employees_tapi;
/
```

---


## License

OraTAPI is licensed under the [MIT License](LICENSE).

---

This README covers the tool's purpose, usage, configuration, and output, providing a clear guide for potential users. Let me know if you'd like any adjustments!