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
-- Package Specification
CREATE OR REPLACE PACKAGE hr.pkg_employees IS
   PROCEDURE ins_employees(p_row IN hr.employees%ROWTYPE);
   PROCEDURE upd_employees(p_row IN hr.employees%ROWTYPE);
   PROCEDURE del_employees(p_id IN NUMBER);
   PROCEDURE get_employees(p_id IN NUMBER, p_row OUT hr.employees%ROWTYPE);
END pkg_employees;
/
```

```sql
-- Package Body
CREATE OR REPLACE PACKAGE BODY hr.pkg_employees IS
   PROCEDURE ins_employees(p_row IN hr.employees%ROWTYPE) IS
   BEGIN
      INSERT INTO hr.employees VALUES p_row;
   END ins_employees;

   PROCEDURE upd_employees(p_row IN hr.employees%ROWTYPE) IS
   BEGIN
      UPDATE hr.employees SET ... WHERE employee_id = p_row.employee_id;
   END upd_employees;

   PROCEDURE del_employees(p_id IN NUMBER) IS
   BEGIN
      DELETE FROM hr.employees WHERE employee_id = p_id;
   END del_employees;

   PROCEDURE get_employees(p_id IN NUMBER, p_row OUT hr.employees%ROWTYPE) IS
   BEGIN
      SELECT * INTO p_row FROM hr.employees WHERE employee_id = p_id;
   END get_employees;
END pkg_employees;
/
```

---


## License

OraTAPI is licensed under the [MIT License](LICENSE).

---

This README covers the tool's purpose, usage, configuration, and output, providing a clear guide for potential users. Let me know if you'd like any adjustments!