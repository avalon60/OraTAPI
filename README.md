

# OraTAPI - Oracle Table API Generator 

Version 1.4.20

- [OraTAPI - Oracle Table API Generator](#oratapi---oracle-table-api-generator)
  - [About OraTAPI](#about-oratapi)
  - [Features \& Limitations](#features--limitations)
    - [Features](#features)
    - [Limitations](#limitations)
    - [Documentation](#documentation)
  - [Preinstallation](#preinstallation)
    - [Preparing the Environment](#preparing-the-environment)
    - [Familiarisation with the Layout](#familiarisation-with-the-layout)
  - [Installation](#installation)
  - [Post Installation](#post-installation)
  - [Performing Upgrades](#performing-upgrades)
  - [The Primary Components](#the-primary-components)
    - [Command-line Tools](#command-line-tools)
      - [Windows:](#windows)
      - [macOS / Linux:](#macos--linux)
  - [Usage](#usage)
    - [Examples](#examples)
      - [Basic Example](#basic-example)
      - [More Advanced Example](#more-advanced-example)
      - [Explicitly Specifying Credentials](#explicitly-specifying-credentials)
    - [Full Command-Line Arguments:](#full-command-line-arguments)
  - [Output Structure](#output-structure)
  - [Configuration Settings](#configuration-settings)
    - [Control Files](#control-files)
    - [The OraTAPI.ini File](#the-oratapiini-file)
      - [\[OraTAPI\]](#oratapi)
      - [\[project\]](#project)
      - [\[copyright\]](#copyright)
      - [\[behaviour\]](#behaviour)
      - [\[formatting\]](#formatting)
      - [\[file\_controls\]](#file_controls)
      - [\[api\_controls\]](#api_controls)
      - [\[logger\]](#logger)
      - [\[schemas\]](#schemas)
      - [\[misc\]](#misc)
      - [\[ut\_control\]](#ut_control)
      - [\[console\]](#console)
      - [Example configuration file:](#example-configuration-file)
    - [Fine-Grained File Controls](#fine-grained-file-controls)
      - [Controlling File Updates](#controlling-file-updates)
      - [PI (Personal Information) Columns \& Logging](#pi-personal-information-columns--logging)
  - [Auto Column Management](#auto-column-management)
    - [What are Auto-managed Columns?](#what-are-auto-managed-columns)
    - [Configuring the Column Management Method](#configuring-the-column-management-method)
    - [The col\_auto\_maintain\_method Property](#the-col_auto_maintain_method-property)
      - [Maintained by Trigger](#maintained-by-trigger)
      - [Maintained by Column Expression](#maintained-by-column-expression)
    - [The auto\_maintained\_cols Property](#the-auto_maintained_cols-property)
    - [The row\_version\_column\_name Property](#the-row_version_column_name-property)
  - [utPLSQL Support](#utplsql-support)
    - [Overview](#overview)
    - [Controls](#controls)
  - [Template Substitution Strings](#template-substitution-strings)
  - [Connection Manager](#connection-manager)
  - [Sample Generated Table API Packages:](#sample-generated-table-api-packages)
    - [Basic Templates Example](#basic-templates-example)
    - [Logger Templates Example](#logger-templates-example)
  - [License](#license)


## About OraTAPI
OraTAPI is a Python-based tool that generates PL/SQL APIs for Oracle database tables. This tool simplifies the process of interacting with Oracle database tables by creating customisable and standardised APIs for common database operations like `insert`, `update`, `delete`, `select`, operations and more.  

OraTAPI connects to an Oracle database, retrieves table and column metadata, and generates the API package files in a staging area. These files can then be deployed to an Oracle database.

---

## Features & Limitations
### Features
OraTAPI is a versatile tool that offers the following configurable options:

- **Metadata-Driven**: Automatically generates PL/SQL APIs based on Oracle database metadata.  
- **Customisable APIs**: Allows you to define API names, signatures, and behaviours through a configuration file.  
- **Table Triggers**: Generates customisable table-level trigger code.  
- **View Generation**: Automatically generates view DDL scripts.  
- **utPLSQL Support**: Generate utPLSQL package spec and starter body for utPLSQL tests 
- **Template-Based Customisation**: Code generation is largely template-driven, with example templates provided, offering extensive customisation capabilities.  
- **Optimistic Locking Support**: Supports concurrency control with "row version" columns for implementing optimistic locking.  
- **PL/SQL Logger Integration**: Easily integrates with the [PLSQL logging utility](https://github.com/OraOpenSource/Logger), including mechanisms to blocklist specific columns from being logged.  
- **Liquibase** Liquibase templates are provided as an option.
- **Fine-Grained Control**: Provides detailed control over which components are generated for specific tables.  
- **Auto-Maintained Column Support**: Offers a flexible solution for managing auto-maintained columns, either through generated triggers or configurable column expressions.  
- **Organised Output**: Output files are neatly arranged in staging directories for streamlined deployment.  
- **Error Handling**: Configurable behaviour for handling missing tables, with options to skip or halt processing.  
- **Connection Manager**: Includes a connection manager (similar to named connections in SQLcl), allowing credentials to be securely stored and used transparently.  

### Limitations
- As of this release, database connections are basic - cloud wallets are not supported.
---

### Documentation
Please note that if you are working with the latest minor version of OraTAPI, it's always worth selecting the 
`develop` branch from the GitHub OraTAPI page Code tab. This will ensure that you are looking at the latest 
version of the README.md. Alternatively, you should be able to navigate straight to the "develop" branch documentation, 
from [here](https://github.com/avalon60/OraTAPI/tree/develop?tab=readme-ov-file#oratapi---oracle-table-api-generator).

## Preinstallation
### Preparing the Environment

In order to make OraTAPI installable, you need to ensure that you have Python 3.10 or 3.11 installed.  
On macOS, you can install Python using:  

`brew install python3` # Install the latest version

`brew install python@3.11` # Install Python 3.11 - safer choice.

On Windows, ensure that you obtain Python from: https://www.python.org/downloads/windows/
you should preferably download Python 3.11. 

### Familiarisation with the Layout

The file system layout for an OraTAPI installation, looks similar to what we see here:

```
ora_tapi.1.1.19
├── bin
│   ├── conn_mgr.ps1
│   ├── conn_mgr.sh
│   ├── migrate_config.ps1
│   ├── migrate_config.sh
│   ├── ora_tapi.ps1
│   ├── ora_tapi.sh
│   ├── quick_config.ps1
│   └── quick_config.sh
├── resources
│   ├── config
│   │   ├── OraTAPI.csv
│   │   ├── OraTAPI.ini
│   │   └── pi_columns.csv
│   └── templates
│       ├── column_expressions
│       │   ├── inserts
│       │   │   ├── created_by.tpt
│       │   │   ├── created_on.tpt
│       │   │   ├── row_version.tpt
│       │   │   ├── updated_by.tpt
│       │   │   └── updated_on.tpt
│       │   └── updates
│       │       ├── created_by.tpt
│       │       ├── created_on.tpt
│       │       ├── row_version.tpt
│       │       ├── updated_by.tpt
│       │       └── updated_on.tpt
│       ├── misc
│       │   ├── trigger
│       │   │   └── table_name_biu.tpt
│       │   └── view
│       │       └── view.tpt
│       └── packages
│           ├── body
│           │   ├── package_footer.tpt
│           │   └── package_header.tpt
│           ├── procedures
│           │   ├── delete.tpt
│           │   ├── insert.tpt
│           │   ├── merge.tpt
│           │   ├── select.tpt
│           │   ├── update.tpt
│           │   └── upsert.tpt
│           └── spec
│               ├── package_footer.tpt
│               └── package_header.tpt
├── setup.ps1
└── setup.sh

```
For simplicity some subdirectories have been omitted, but these aren't particularly important right now. However, it's 
worth mentioning that sample (template) configuration files are provided and leveraged during setup. They are not shown, as they 
would clutter the display. These are implemented as subdirectories within the various `resources/templates` and 
`resources/config` subdirectories. For example the `resources/templates/packages/body` and 
`resources/templates/packages/spec` directories, each have a `samples` subdirectory.

The key take-away from the above (no, not Quattro Formaggi;) is the config directory which is where the OraTAPI.ini is located, as well as a couple 
of CSV files which are all used to influence the behaviour of OraTAPI. The various template files `.tpt` also influence 
the behaviour, in as much as they shape the code and content of the generated files.

## Installation

1. Download the oratapi-X.Y.Z.tar.gz artefact to a staging directory. You can obtain the artefacts from the [OraTAPI Releases](https://github.com/avalon60/OraTAPI/releases) page. Ensure not to download one of the two source code files.

   2. Open a Terminal Window and Extract the Contents:
      For macOS / Linux
      ```bash
      mkdir <path-to-installation-folder>
      tar -xzvf <sdist_file>.tar.gz -C <path-to-installation-folder>
      ```

      For windows:
      Open a **Windows PowerShell Terminal** and enter the command:
      ```powershell
      mkdir <path-to-installation-folder>
      tar -xzvf <sdist_file>.tar.gz -C <path-to-installation-folder>
      ```
      The tar command should be supplied with Windows PowerShell.    

          NOTE: The source distribution file, includes an `oratapi-<x.y.z>` root folder, you may wish to account for this, when constructing <path-to-installation-folder>.  
                Renaming the `oratapi-<x.y.z>`directory is entirely a matter of choice.

3. Complete the Installation:  
   macOS / Linux
   ```bash
   cd <path-to-installation-folder>
   chmod 750 setup.sh
   ./setup.sh
   ```
   Windows PowerShell:
   ```ps1
   cd <path-to-installation-folder>
   .\setup.ps1
   ```
    The Windows command must be run from a Windows PowerShell terminal.  

## Post Installation
The next step is to configure the `OraTAP.ini` file and your template files. Samples of these files are provided, and 
you could navigate through the various directories to manually instantiate all your files by copying the samples to the 
required file names and directories. However, a `quick_config` tool is available to help you set up more quickly. Several 
options are available to choose from:

- Basic
- Liquibase
- Logger
- Liquibase & Logger

The respective parameters passed need to be in lowercase (`basic`, `liquibase`, `logger` `llogger`).

If you opt for the `llogger` templates, you will need to install the [PLSQL logging utility](https://github.com/OraOpenSource/Logger).  

Here we are configuring for Liquibase.  

   macOS / Linux
   ```bash
   cd <path-to-installation-folder>
   ./bin/quick_config.sh -t liquibase
   ```
   Windows PowerShell:
   ```ps1
   cd <path-to-installation-folder>
   .\bin\quick_config.ps1 -t liquibase
   ```

Assuming we were to configure for "Liquibase with Logger", the output should look similar to this:

```
$ bin/quick_config.sh -t llogger
OraTAPI quick config started...
Copied: resources/config/samples/OraTAPI.ini.sample -> resources/config/OraTAPI.ini
Copied: resources/templates/column_expressions/inserts/samples/updated_on.tpt.sample -> resources/templates/column_expressions/inserts/updated_on.tpt
Copied: resources/templates/column_expressions/inserts/samples/updated_by.tpt.sample -> resources/templates/column_expressions/inserts/updated_by.tpt
Copied: resources/templates/column_expressions/inserts/samples/created_by.tpt.sample -> resources/templates/column_expressions/inserts/created_by.tpt
Copied: resources/templates/column_expressions/inserts/samples/created_on.tpt.sample -> resources/templates/column_expressions/inserts/created_on.tpt
Copied: resources/templates/column_expressions/inserts/samples/row_version.tpt.sample -> resources/templates/column_expressions/inserts/row_version.tpt
Copied: resources/templates/column_expressions/updates/samples/updated_on.tpt.sample -> resources/templates/column_expressions/updates/updated_on.tpt
Copied: resources/templates/column_expressions/updates/samples/updated_by.tpt.sample -> resources/templates/column_expressions/updates/updated_by.tpt
Copied: resources/templates/column_expressions/updates/samples/created_by.tpt.sample -> resources/templates/column_expressions/updates/created_by.tpt
Copied: resources/templates/column_expressions/updates/samples/created_on.tpt.sample -> resources/templates/column_expressions/updates/created_on.tpt
Copied: resources/templates/column_expressions/updates/samples/row_version.tpt.sample -> resources/templates/column_expressions/updates/row_version.tpt
Copied: resources/templates/misc/trigger/samples/table_name_biu.llogger.sample -> resources/templates/misc/trigger/table_name_biu.tpt
Copied: resources/templates/misc/view/samples/view.llogger.sample -> resources/templates/misc/view/view.tpt
Copied: resources/templates/packages/body/samples/package_footer.llogger.sample -> resources/templates/packages/body/package_footer.tpt
Copied: resources/templates/packages/body/samples/package_header.llogger.sample -> resources/templates/packages/body/package_header.tpt
Copied: resources/templates/packages/spec/samples/package_footer.llogger.sample -> resources/templates/packages/spec/package_footer.tpt
Copied: resources/templates/packages/spec/samples/package_header.llogger.sample -> resources/templates/packages/spec/package_header.tpt
Copied: resources/templates/packages/procedures/samples/insert.llogger.sample -> resources/templates/packages/procedures/insert.tpt
Copied: resources/templates/packages/procedures/samples/merge.llogger.sample -> resources/templates/packages/procedures/merge.tpt
Copied: resources/templates/packages/procedures/samples/delete.llogger.sample -> resources/templates/packages/procedures/delete.tpt
Copied: resources/templates/packages/procedures/samples/update.llogger.sample -> resources/templates/packages/procedures/update.tpt
Copied: resources/templates/packages/procedures/samples/upsert.llogger.sample -> resources/templates/packages/procedures/upsert.tpt
Copied: resources/templates/packages/procedures/samples/select.llogger.sample -> resources/templates/packages/procedures/select.tpt
23 files instantiated.
OraTAPI quick config complete.
```
Note that in this example, we are opting for the "Liquibase with Logger" templates.  

To underscore the point, you should either specify `-t basic`, `-t liquibase`,  `-t logger` or `-t llogger`. Optionally, specify `--template_category` 
instead of `-t`.  

If you run the command more than once, it will have no effect. This is to prevent you from overwriting any later 
customisations to the configuration. However, you can force an overwriting, by adding the `-f/--force` flag. Example:

   ```bash
   cd <path-to-installation-folder>
   ./bin/quick_config.sh -t liquibase --force
   ```

The full command synopsis is:
```
$ bin/quick_config.sh -h
usage: quick_config.py [-h] -t {liquibase,basic,llogger} [-T] [-f]

Copy template files based on template category.

options:
  -h, --help            show this help message and exit
  -t {liquibase,basic,llogger}, --template_category {liquibase,basic,llogger}
                        Specify the template category ('liquibase' or 'basic').
  -T, --templates_only  Only instantiate templates (Do not overwrite control files).
  -f, --force           Overwrite existing files.

This also instantiates the control files: OraTAPI.ini, pi_columns.csv
```
Note that the `-T/--templates_only` can be used in conjunction with the `-f/--force option`, to re-instantiate the templates.
This may be useful if you have started configuring your control files, but wish to switch to a different template set 
to that originally chosen, assuming that you don't wish to reset your bespoke config.

Finally, ensure that you have access to an Oracle database and configure your `TNS` entries or connection settings. 
You should test your connection to the database, via SQLcl or SQL Developer, before attempting with OraTAPI.


NOTES:   
If you are on Windows and have Git Bash installed, the Linux/macOS instructions should also work in a Git Bash terminal. 
OraTAPI can be used via PowerShell or Git Bash. 

## Performing Upgrades
It's worth noting that when you unzip the installation archive file, it creates a directory, whose name is of the form 
`oratapi-M.m.p`, where the M, m and p, represent the major, minor and patch components of the version. This means 
that you should be able to locate the archive and unzip it from the same location as you did for previous your installation(s), 
and it will automatically extract to its own directory.  


To complete the installation and migrate your previous settings, perform these steps:

1. Download the new release of OraTAPI
2. Unpack as outlined previously.
3. Run the `setup` command as outlined previously
4. Run `migrate_config` command as per the example below.

```
   cd <path-to-installation-folder>
   ./bin/migrate_config.sh -o <path_to_old_install_dir>
```
This will result in your old OraTAPI.ini file, CSV files, and templates, being copied to the new installation.  

Note that there is also a `migrate_config.ps1` command for Windows PowerShell.

If new config settings are introduced, then you will get feedback from the migration tool. It will list any new 
OraTAPI.ini sections that you have missing as well as any properties. In addition, it will inform you if there are 
any obsolete entries. You can view the settings in context by looking at the resources/config/samples/ORATapi.ini.sample file.  

Any previously configured named database connections (see [Connection Manager](#connection-manager)) are preserved since they are located under the directory 
$HOME/.OraTAPI.  

The synopsis for the `migrate_config` command is:

```
usage: migrate_config.py [-h] (-o OLD_INSTALL_DIR | -e <export_zip_path> | -i <import_zip_path>)

Migrate, export, or import OraTAPI configuration and template files.

options:
  -h, --help            show this help message and exit
  -o OLD_INSTALL_DIR, --old_install_dir OLD_INSTALL_DIR
                        Specify the old OraTAPI installation directory.
  -e <export_zip_path>, --export <export_zip_path>
                        Export resources to a ZIP file.
  -i <import_zip_path>, --import_resources <import_zip_path>
                        Import resources from a ZIP file.
```
Hopefully you will have noticed that `migrate_config`, also has export / import options. 
You can use this to back-up / restore or transport settings. These also constitute an alternative to 
using the `-o / --old_install_dir` option, since you can take an export of your old configuration, 
and import from the export file to your new installation.

Example export:
```
$ bin/migrate_config.sh --export /tmp/mig.zip
OraTAPI config migration started...
Exported resources to /tmp/mig.zip
OraTAPI operation complete.
```

Example import:
```
$ bin/migrate_config.sh --import /tmp/mig.zip
OraTAPI config migration started...
Imported resources from /tmp/mig.zip
Updated version in resources/config/OraTAPI.ini to 1.1.19.

Checking for OraTAPI.ini updates/obsolescence...

No config changes introduced with release.

OraTAPI.ini checks complete.

OraTAPI operation complete.
```

---

## The Primary Components
The OraTAPI tools consist of three major parts:

- The ora_tapi command line tool.
- Code templates.
- The OraTAPI.ini configuration file

The `ora_tapi` command line tool is used to launch the code generation process.

The code templates form the basic shape of the generated source code files. There are various templates that are read 
at runtime and constitute regions such as package file headers, footers, and procedures. You can also implement view and 
trigger templates, and sample templates are provided for you to copy and modify. You should not amend the original sample 
files. These have a suffix of `.tpt.sample`. There are also `column expression` templates. These are discussed in 
the [Maintained by Column Expression](#maintained-by-column-expression) section.

Finally, much of the behaviour of OraTAPI is governed by the configuration of the `OraTAPI.ini` file, which is located 
in the `config` directory. The OraTAPI.ini file consists of property/value pairs, which are located into various 
sections, which are used to categorise their purpose. Section names are enclosed in square brackets 
(<i>e.g. [<api_controls]</i>). Specifically, for the OraTAPI framework, each property name in the file must be globally unique, 
irrespective of which section it belongs to.

### Command-line Tools
Launching the command line tools, varies slightly depending on your target operating system. There are two tools that you will need to work with, `conn_mgr` and `ora_tapi`. The latter of these will be used more frequently.

In respect of the `conn_mgr` tool (see [Connection Manager](#connection-manager)), this is used to securely store 
database connections (credentials and DSNs). Such connections are named and can be used in conjunction with the 
`-c/--conn_name` option of the `ora_tapi` command. This is a secure alternative to specifying the `-u/--db_username`, 
`-p/--db_password` and `-d/--dsn` options.

The following launcher commands are provided:

#### Windows:
- ora_tapi.ps1
- conn_mgr.ps1

#### macOS / Linux:
- ora_tapi.sh
- conn_mgr.sh

These are located in the `<OraTAPI-Home>/bin` directory. 

To get command line help, you can simply type something like:

```
cd <OraTAPI-home>
./bin/ora_tapi.sh -h

usage: ora_tapi.py [-h] [-A APP_NAME] [-a TAPI_AUTHOR] [-c CONN_NAME] [-d DSN]
                   [-g STAGING_DIR] [-G UT_STAGING_DIR] [-u DB_USERNAME]
                   [-p DB_PASSWORD] [-To TABLE_OWNER] [-po PACKAGE_OWNER]
                   [-to TRIGGER_OWNER] [-vo VIEW_OWNER] [-t TABLE_NAMES]
                   [-T API_TYPES] [-U UT_API_TYPES]

Oracle Table API Generator

options:
  -h, --help            show this help message and exit
  -A APP_NAME, --app_name APP_NAME
                        Application name - included to the package header.
                        Default: Human Resources
  -a TAPI_AUTHOR, --tapi_author TAPI_AUTHOR
                        TAPI author
  -c CONN_NAME, --conn_name CONN_NAME
                        Database connection name (created via OraTAPI
                        connection manager).
  -d DSN, --dsn DSN     Database data source name (TNS name).
  -g STAGING_DIR, --staging_dir STAGING_DIR
                        Directory for staging area. Default:
                        /home/clive/PycharmProjects/OraTAPI/ut_staging
  -G UT_STAGING_DIR, --ut_staging_dir UT_STAGING_DIR
                        Directory for unit tests staging area. Default:
                        /home/clive/PycharmProjects/OraTAPI/ut_staging
  -u DB_USERNAME, --db_username DB_USERNAME
                        Database connection username.
  -p DB_PASSWORD, --db_password DB_PASSWORD
                        Database connection password.
  -To TABLE_OWNER, --table_owner TABLE_OWNER
                        Database schema name of the tables from which to
                        generate the code. Default: aut
  -po PACKAGE_OWNER, --package_owner PACKAGE_OWNER
                        Database schema in which to place the TAPI packages.
                        Default: aut
  -to TRIGGER_OWNER, --trigger_owner TRIGGER_OWNER
                        The schema in which to place the generated triggers.
                        Default: aut
  -vo VIEW_OWNER, --view_owner VIEW_OWNER
                        The schema in which to place the generated views.
                        Default: aut
  -t TABLE_NAMES, --table_names TABLE_NAMES
                        Comma separated list of table names. Default: all
  -T API_TYPES, --api_types API_TYPES
                        Comma-separated list of API types. Valid options:
                        insert, select, update, upsert, delete, merge.
                        (Default setting: insert, select, update, delete)
  -U UT_API_TYPES, --ut_api_types UT_API_TYPES
                        Comma-separated list of unit test API types. Valid
                        options: insert, select, update, upsert, delete,
                        merge. (Default setting: insert, select, update,
                        delete)

The majority of defaults can be changed via the OraTAPI.ini file.
```
The DB_USERNAME database user, must have sufficient privileges to view the TABLE_OWNER's database objects via the 
Oracle `ALL_` data dictionary views.

## Usage

Run OraTAPI from the command line with the desired options.

### Examples
In the following examples, we are assuming that we are running with a macOS/Linux type environment. For Windows 
PowerShell, you need to assume the commands have a `.ps1` extension, instead of `.sh`.  

The examples also assume that you have navigated to the root install directory of OraTAPI.

#### Basic Example
```bash
bin/ora_tapi.sh --table_owner HR --table_names employees,departments --conn_name dev_db --tapi_author cbostock
```
Using the terse flags, this is equivalent to:
```bash
bin/ora_tapi.sh -To HR -t employees,departments -c dev_db -a cbostock
```
#### More Advanced Example
Here we want to override the default target schemas for the packages, views, and triggers:
```bash
bin/ora_tapi.sh -To HR -t employees,departments -c dev_db -a cbostock -po logic -to core -vo logic
```

Based on this last example, the DDL statements in the generated scripts will place the packages and views in the logic 
schema, and the triggers in the core schema.  



Remember that when these flags are not provided, the defaults are retrieved from the `resources/config/OraTAPI.ini` file.

#### Explicitly Specifying Credentials
In the previous examples, we relied on the `OraTAPI` connection manager, in as much as we were using the `--conn_name` 
argument to specify a connection. This took advantage of a stored, named connection, called dev_db.  

If we don't want to use a named connection, the alternative is to specify:  

- db_username
- db_password
- dsn/TNS connect string

Taking the basic example, we can modify this to:
```bash
ora_tapi.sh -To HR -t employees,departments -c dev_db -a cbostock -u cbostock -p <my_password> -d dev-db
```
In this example, we assume that the dev-db is a TNS Names entry.  

**It is recommended that you use the connection manager approach.**

### Full Command-Line Arguments:
| Argument                   | Description                                                                                | Default                  |
|----------------------------|--------------------------------------------------------------------------------------------|--------------------------|
| `-A`, `--app_name`         | Application name included in the package header.                                           | `Undefined`              |
| `-a`, `--tapi_author`      | Author name for the package header.                                                        | `OraTAPI generator`      |
| `-c`, `--conn_name`        | Connection name for saved configuration.                                                   |                          |
| `-d`, `--dsn`              | Database Data Source Name (TNS entry).                                                     |                          |
| `-g`, `--staging_dir` | Directory for the staging area.                                                            | `./staging`              |
| `-p`, `--db_password`      | Database password.                                                                         |                          |
| `-P`, `--package_owner`    | Schema to own the generated TAPI packages (required).                                      |                          |
| `-S`, `--schema_name`      | Schema containing the target tables (required).                                            |                          |
| `-t`, `--table_names`      | Comma-separated list of tables (use `%` for all tables).                                   | `%`                      |
| `-To`, `--table_owner`     | The table owner/schema on whose tables the generated APIs are to be based.                 |                          |
| `-to`, `--trigger_owner`   | The schema in which the generated scripts should create the triggers.                      |                          |
| `-vo`, `--view_owner`      | The schema in which the generated scripts should create the views.                         |                          |
| `-u`, `--db_username`      | Database username.                                                                         |                          |
| `-T`, `--api_types`        | Comma-separated list of API types (e.g., `insert, select, update, delete, upsert, merge`). | Configured default types |

---

## Output Structure

Generated files are written to the staging area and organised into subdirectories:
- **Package Specification (`spec_dir`)**: Contains DDL source files defining the PL/SQL package interface.
- **Package Body (`body_dir`)**: Contains DDL source files implementing the PL/SQL package logic.
- **View (`view`)**: Contains DDL source files implementing any generated view scripts.
- **Trigger (`view`)**: Contains DDL source files implementing any generated trigger scripts.

Each API package is customised based on a combination of the `.ini` configuration, command-line options and template 
files. File extensions for package spec and body source files can be configured via the 
OraTAPI.ini file, under the `file_controls` section. Look for the `body_file_ext` and
`spec_file_ext` properties.

The majority of command line options have defaults which can be set via the OraTAPI.ini configuration file. 

---

These are just a few of the controls. Read on for further detail.

## Configuration Settings
### Control Files
As well as tailoring the templates to your requirements, the behaviour of OraTAPI, is governed by 3 files:
- OraTAPI.ini
- OraTAPI.csv
- pi_columns.csv


The last 2 of these are covered in subsequent sections, under [Fine-Grained File Controls](#fine-grained-file-controls). Here we cover the first of these files, the OraTAPI.ini file.

### The OraTAPI.ini File
The OraTAPI.ini provides the main controls for governing the OraTAPI behaviour.  

The OraTAPI.ini file is made up of named sections. The sections are denoted by square brackets in which the 
section name is enclosed. Within each section is one or more properties, used to control the behaviour in one way or 
another, of the `ora_tapi` command.  

As a reminder, the file is located as `<raTAPI_HOME/resources/config/OraTAPI.ini`. When OraTAPI starts up, it 
initialises settings, based upon the contents of this file.  

Here we cover the various sections and properties.
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
  - **Purpose**: Defines the folder where all generated files will be placed. The default location is `staging` and is located directly below the OraTAPI installation root folder. You can specify a pathname relative to the OraTAPI installation root folder, or a full pathname. This can be overridden at runtime, using the `-g/--staging_dir` argument.
  
  Sub-directories are created at run-time, as required, to host the generated code. The names of the sub-directories are configurable (read on).
  
-  **spec_file_ext** & **body_file_ext**: Set the file suffix for the package body and specification files.
  - Examples:   
  `spec_file_ext = .pks`   
  `body_file_ext = .pkb`  
  - **Purpose**: Specifies the file extension for generated SQL files. The default for these is `.sql`.  
  

    NOTE: If the spec_dir and the body_dir are defined as the same directory, **spec_file_ext**  and **body_file_ext**  must be different.

- **spec_dir** & **body_dir**: Define the directories for package specification and package body files.
  - Example: `spec_dir = package_spec`
  - **Purpose**: Organises generated files in a specific staging subdirectory for clarity and structure.

- **trigger_dir**: Define the directory for trigger files.
  - Example: `trigger_dir = trigger`
  - **Purpose**: Organises generated trigger source files in a specific staging subdirectory for clarity and structure.

- **view_dir**:  Define the directory for view source files.
  - Example: `view_dir = view`
  - **Purpose**:  Organises generated view source files in a specific staging subdirectory for clarity and structure.

- **ora_tapi_csv_dir**: Defines the directory for the OraTAPI CSV file.
  - Example: `ora_tapi_csv_dir = resources/config`
  - **Purpose**: Used to control which files should be generated based on the CSV configuration file. This allows fine grain control of which files should be generated and written/overwritten. New file entries are automatically added when tables are processed and no corresponding entry is found. In addition this also allows table domains (%table_domain_lc%) to be configured.

- **pi_columns_csv_dir**: Defines the directory for the OraTAPI CSV file.
  - Example: `pi_columns_csv_dir = resources/config`
  - **Purpose**: Used to control which columns should be omitted from parameter logging when the `llogger` templates are active. This is provided to avoid PI (personal information) columns being logged.
---

#### [api_controls]
- **delete_procname**: Specifies the procedure name to be used for the delete API.
  - Example: `delete_procname = del`
  - **Purpose**: Customises the naming conventions for the delete procedure.

- **select_procname**: Specifies the procedure name to be used for select API.
z  - Example: `select_procname = get`
  - **Purpose**: Customises the naming conventions for the select procedure.

- **insert_procname**: Specifies the procedure name to be used for insert API.
  - Example: `insert_procname = ins`
  - **Purpose**: Customises the naming conventions for the insert API procedures.

- **merge_procname**: Specifies the procedure name to be used for merge API procedures.
  - Example: `merge_procname = mrg`
  - **Purpose**: Customises the naming conventions for the merge API procedures.

- **update_procname**: Specifies the procedure name to be used for update API procedures.
  - Example: `update_procname = upd`
  - **Purpose**: Customises the naming conventions for the update API procedures.

- **upsert_procname**: Specifies the procedure name to be used for upsert API procedures.
  - Example: `upsert_procname = ups`
  - **Purpose**: Customises the naming conventions for the upsert API procedures.

- **auto_maintained_cols**: A comma-separated list of columns managed automatically by triggers or column expressions (e.g., timestamps, user fields).
  - Example: `auto_maintained_cols = created_by, created_on, updated_by, updated_on`
  - **Purpose**: Prevents these columns from being included in data modification APIs, but they are returned in select APIs. These are assumed to be maintained by triggers, or OraTAPI column expressions.

- **col_auto_maintain_method**: Defines how auto-maintained columns maintained.
  - Example: `col_auto_maintain_method = trigger`
  - **Purpose**: Specifies whether column values are managed via database triggers or column expressions. For column expressions, the setting is `expression`.

- **row_vers_column_name**: Defines the column name used for optimistic locking.
  - Example: `row_vers_column_name = row_version`
  - **Purpose**: Supports optimistic locking column used for tracking changes to rows using a version number. Setting this for a common table column name, results in the inclusion of an `out` parameter, wherever the named column is found in a table. In addition column expressions (see later) can be used to maintain the column. Alternatively triggers can be used.

- **signature_types**: Defines the API signature types (rowtype or coltype).
  - Example: `signature_types = rowtype, coltype`
  - **Purpose**: Determines whether to generate APIs which implement parameters as rowtypes (p_row) or column types (one parameter for each column). This must be set to `coltype` and / or `rowtype`.

- **include_defaults**: Includes default values for insert APIs.
  - Example: `include_defaults = true`
  - **Purpose**: Ensures that default values for table columns are included in insert APIs.

- **noop_column_string**: Defines a string to be used for non-key, character string type column parameter defaults.
  - Example: `noop_column_string = auto`
  - **Purpose**: Helps avoid passing unnecessary parameters by preserving existing values. Comment out or remove value assigned to disable the feature. The value can be set to a character string, the value `auto`, or `dynamic`. Setting to `dynamic` involves a slight resource overhead at runtime. Only works for character string columns (VARCHAR2, CLOB etc.)

- **default_api_types**: Specifies which types of APIs should be included by default.
  - Example: `default_api_types = insert, select, update, delete`
  - **Purpose**: Controls which API types are generated by default. Options are insert, select, update, delete, upsert, and merge. These can be overridden at runtime via the `-T/--api_types` command line argument.

- **return_pk_columns**: Determines whether primary key columns are included as in/out parameters in the generated APIs.
  - Example: `return_pk_columns = true`
  - **Purpose**: Ensures primary/unique key columns are returned in APIs that modify data.

- **return_ak_columns**: Determines whether unique key constraint columns are included as in/out parameters in the generated APIs.
  - Example: `return_ak_columns = true`
  - **Purpose**: Ensures primary/unique key columns are returned in APIs that modify data.

- **include_commit**: Defines whether a commit parameter should be included.
  - Example: `include_commit = true`
  - **Purpose**: Includes a commit parameter to implement a transactional behaviour.
  - 
---
#### [logger]
- **logger_pkg**: Specifies the name/alias of the logger package.
  - Example: `logger_pkg = logger`
  - **Purpose**: Defines the logger package name (optionally prefixed by the owning schema, e.g. logger_user.logger).
- **logger_logs**: Specifies the logger_logs table.
  - Example: `logger_logs = logger_logs`
  - **Purpose**: Defines the logger_logs table name (optionally prefixed by the owning schema, e.g. logger_user.logger_logs). This is used purely for data typing inside the generated package code.
---
#### [schemas]
- **default_table_owner**: Specifies the default schema for tables.
  - Example: `default_table_owner = aut`
  - **Purpose**: Defines the default schema for tables on which APIs are based. This can be overridden by command-line argument (e.f.`-To <schema_name>`).

- **default_package_owner**: Specifies the default schema for packages.
  - Example: `default_package_owner = aut`
  - **Purpose**: Defines the default target schema for package creation. This can be overridden by command-line argument (e.g. `-po <schema_name>`).

- **default_view_owner**: Specifies the default schema for views.
  - Example: `default_view_owner = aut`
  - **Purpose**: Defines the default target schema for view creation. This can be overridden by command-line arguments (e.g. `-vo <schema_name>`).

- **default_trigger_owner**: Specifies the default schema for triggers.
  - Example: `default_trigger_owner = aut`
  - **Purpose**: Defines the default schema for trigger creation. This can be overridden by command-line argument (e.g. `-to <schema_name>`).

---

#### [misc]
- **view_name_suffix**: Defines a suffix to be added to the derived view name.
  - Example: `view_name_suffix = _v`
  - **Purpose**: Customises the name of generated views by appending the suffix.

---

#### [ut_control]
- **enable_ut_code_generation**: Enables / disables code generation of utPLSQL packages.
  - Example: `enable_ut_code_generation = true`
  - **Purpose**: When set to true / on, utPLSQL code generation is switched on. When set to false / off utPLSQL code generation is disabled.

- **ut_suite**: Specify a string for the %suite annotation
  - Example: `ut_suite = HR`
  - **Purpose**: See utPLSQL documentation for more details on [annotations](https://www.utplsql.org/utPLSQL/v3.0.4/userguide/annotations.html).

- **ut_prod_code**: Specify a string for the first (dot separated) component of the %suitepath annotation
  - Example: `ut_prod_code = hr`
  - **Purpose**: See utPLSQL documentation for more details on [annotations](https://www.utplsql.org/utPLSQL/v3.0.4/userguide/annotations.html).

- **ut_prod_sub_domain_code**: Specify a string for the second (dot separated) component of the %suitepath annotation
  - Example: `ut_prod_sub_domain_code = dept`
  - **Purpose**: If set to the value `auto_table`, the first characters of the table name, leading up to the first underscore are assumed. Otherwise 
    the value is taken as a literal. See utPLSQL documentation for more details on [annotations](https://www.utplsql.org/utPLSQL/v3.0.4/userguide/annotations.html).

- **ut_pkg_name_prefix**: Specify a string to be used as a prefix in formulating the generated package name. 
  - Example: `ut_pkg_name_prefix = ut_`
  - **Purpose**: Allows you to define a character string with which to append when generating the utPLSQL package names (<prefix_string><table_name><postfix_string>).

- **ut_pkg_name_postfix**: Specify a string to be used as a postfix when formulating the generated package name. 
  - Example: `ut_pkg_name_postfix = _tapi`
  - **Purpose**: Allows you to define a character string with which to append when generating the utPLSQL package names (<prefix_string><table_name><postfix_string>).

- **ut_uk_test_throws**: Specify a throws code to be used with procedures used to test key constraints. 
  - Example: `ut_uk_test_throws = dup_val_on_index`
  - **Purpose**: This provides the means for you to define an Oracle exception/error code to associate with the \%throws() annotation, associated 
                 with primary or unique key constraint test procedures.

- **ut_parent_fk_test_throws**: Specify a throws code to be used with procedures used to test parent key constraints. 
  - Example: `ut_parent_fk_test_throws = -02291`
  - **Purpose**: This provides the means for you to define an Oracle exception/error code to associate with the \%throws() annotation, associated 
                 with (parent) foreign key constraint test procedures.

- **ut_cc_test_throws**: Specify a throws code to be used with procedures used to test check constraints. 
  - Example: `ut_cc_test_throws = -02290`
  - **Purpose**: This provides the means for you to define an Oracle exception/error code to associate with the \%throws() annotation, associated 
                 with check constraint test procedures.

- **ut_nn_test_throws**: Specify a throws code to be used with procedures used to testing not null constraints. 
  - Example: `ut_nn_test_throws = -01400`
  - **Purpose**: This provides the means for you to define an Oracle exception/error code to associate with the \%throws() annotation, associated 
                 with not null, check constraint testing procedures.


---

#### [console]
- **INFO_COLOUR**, **WARN_COLOUR**, **ERR_COLOUR**, **CRIT_COLOUR**, **HIGH_COLOUR**: Defines colour schemes for different output categories.
  - Example: `INFO_COLOUR = white`
  - **Purpose**: Customises the colours used in the console output for different message priority levels (info, warning, error, etc.).

- **colour_console**: Enables or disables colour output in the console.
  - Example: `colour_console = true`
  - **Purpose**: Controls whether coloured output is shown in the console.

---

#### Example configuration file:

```ini
[OraTAPI]
version = 1.1.9

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
# The file extension properties are appended to the respective files.
body_file_ext = .sql
spec_file_ext = .sql

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
ora_tapi_csv_dir = resources/config

# Set the path to the OraTAPI pi_columns.csv file. This CSV file is used to flag columns as personal information.
# Such columns are not logged when using the llogger format templates.
pi_columns_csv_dir = resources/config

[api_controls]
# API naming properties follow. Set these to the preferred procedure names of the respective APIs
delete_procname = del
select_procname = get
insert_procname = ins
merge_procname  = mrg
update_procname = upd
upsert_procname = ups

# col_auto_maintain_method: Set to `trigger` or `expression`, it is assumed that your table triggers
# are to manage the modification of the columns. However, if set to `expression`, you must define a column expression
# for each of the named columns.
col_auto_maintain_method = trigger

# auto_maintained_cols is a comma separated list of columns which are not to be set by the TAPI parameters.
# These are columns typically auto-maintained by triggers or column expressions. As such they are not included in APIs
# responsible for data modifications. However they are included in select API return parameters.
auto_maintained_cols = created_by, created_on, updated_by, updated_on

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
# dynamic to have the NOOP character string (partly, by sys_guid()) dynamically generated on a per-session basis.
# noop_column_string = auto
# noop_column_string = #NO~OP#

# default_api_types: Specifies the default of which APIs to include to the package.
# Comma separated - must be one or more of insert, select, update, delete, upsert, merge.
# default_api_types = insert, select, update, delete, upsert, merge
default_api_types = insert, select, update, delete

# The parameters influence the generated name packages.
# The default package name format is <table_name_lc>_tapi
tapi_pkg_name_prefix =
tapi_pkg_name_postfix = _tapi

# return_pk_columns: If set to true, causes primary/unique keys to be in/out parameters. Returning the values.
# This applies to APIs which modify data.
return_pk_columns = true
return_ak_columns = false
# Include p_commit boolean parameter (in). Should be set to true or false. Typically this would be set to false.
include_commit = false

[logger]
# If you have not set up synonyms, we need prefix with the schema where logger is installed.
# By default we assume logger_user. If you have run create_logger_synonyms.sql, you don't need to
# prefix these. If these are absent, defaults are assumed to be `logger` and `logger_logs`. The `llogger` sample
# templates take advantage of these settings.
logger_pkg = logger_user.logger
logger_logs = logger_user.logger_logs

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

### Fine-Grained File Controls

The OraTAPI.ini file has been covered in the previous sections. Here we look at the CSV controls.

#### Controlling File Updates
Fine-grained control over which files can or cannot be updated, is implemented via the OrtTAPI.csv file. The location of 
this file is determined via the `ora_tapi_csv_dir` property, which resides in the `file_controls` section of the 
`OraTAPI.ini` file. If the associated property is unset, `ora_tapi` will assume its 
location as the root folder of the OraTAPI installation. The supplied OraTAPI.ini sample,
sets ths location to `resources/config`.  

The OraTAPI.csv file is not provided at installation time. Rather, it is created and populated 
on you run your first run of the  `ora_tapi` command. The file contents should be maintained as a spreadsheet, but 
ensure that it is saved as a CSV file when exporting it from the spreadsheet application.

Each row represents a schema / table. The following 
columns are represented:

- Schema Name
- Table Name
- Domain
- Packages Enabled
- Views Enabled
- Triggers Enabled

The file is auto-populated when you generate scripts. If a schema/table combination is missing, a row is automatically 
added. Once rows are added, you can maintain the last 3 columns. Setting these to `True`, `1`, or `On` instructs OraTAPI 
that the respective files can be created/overwritten. Setting these to `False`, `0` or `Off` will instruct OraTAPI to not 
create/overwrite the file.  

Note that OraTAPI updates the file after each run and all settings are normalised to either 
`True` or `False`.

The `Domain` column is provided so that table domain mappings can be recorded. These are then automatically substituted 
to the %table_domain_lc% substitution string in the templates.

#### PI (Personal Information) Columns & Logging
If you wish to avoid logging PI data, you can leverage the pi_columns.csv file to achieve this.  
This is only pertinent, if you are working with the `logger` or `llogger` based templates (or similar).  

The file contains the following columns:

- Schema Name
- Table Name
- Column Name
- Description

This allows you to map out the columns that should be omitted from logging. You can set exact matches for `Schema Name` 
and / or `Table Name`, or you can wild-card the entries with any of the following: `%`, `*` or `all`. You must always 
enter an exact column name. The Description is optional, but allows you to describe why the column has been entered to 
the list.  

When generating the parameter logging commands, a check is made to see if a match is found. If a match is found, then the parameter logging statement is commented out, and prepened with the string `PI column: `. Example:  

```
logger_user.logger.append_param(l_params, '* p_row.employee_id', p_row.employee_id);
logger_user.logger.append_param(l_params, '  p_row.first_name', p_row.first_name);
-- PI column: logger_user.logger.append_param(l_params, '  p_row.last_name', p_row.last_name);
-- PI column: logger_user.logger.append_param(l_params, '  p_row.email', p_row.email);
-- PI column: logger_user.logger.append_param(l_params, '  p_row.phone_number', p_row.phone_number);
logger_user.logger.append_param(l_params, '  p_row.hire_date', p_row.hire_date);
logger_user.logger.append_param(l_params, '  p_row.job_id', p_row.job_id);
logger_user.logger.append_param(l_params, '  p_row.salary', p_row.salary);
```
The pi_columns.csv file contents should be maintained as a spreadsheet, but ensure that it is saved as a CSV file when 
exporting it from the spreadsheet application.

---

## Auto Column Management
### What are Auto-managed Columns?
In this context, the term auto-managed columns, refers to columns whose data are not managed directly via the application. 
Rather, they are populated/updated by table triggers, default values or expressions which are effectively virtualised 
by the API.  


### Configuring the Column Management Method
Under the `api_controls` section of `OraTAPI.ini`, there are two entries pertaining to auto managed columns. These allow 
you to configure how you manage your auto-managed columns. Because the management is made almost transparent to the 
developer, there are no input parameters to populate them via the API. For example, you may have columns which are used 
to track who created, or last updated a row. The entries that control the behaviour are:

- col_auto_maintain_method
- auto_maintained_cols
- row_vers_column_name

### The col_auto_maintain_method Property
If you are using columns which you want to be automatically updated during DML operations, you should set this property 
value to one of: 

- trigger
- expression

#### Maintained by Trigger 
If you set the `col_auto_maintain_method` property to <i>trigger</i>, you should ensure that your trigger template(s) 
are designed to make appropriate updates to the columns that are listed via this property.
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
#### Maintained by Column Expression
Column expressions are configured using special templates located in the resources/templates/column_expressions 
directory. This directory contains two subdirectories, allowing you to differentiate column expressions for 
inserts and updates. The subdirectories are listed here:

- inserts
- updates

If the col_auto_maintain_method property is set to expression, then for each column listed in the auto_maintained_cols 
and row_vers_column_name properties, a corresponding template entry is required in both the inserts and updates 
directories. These expressions are injected into assignment statements for the generated API procedures.

For example, assume we have a column called row_version. We would expect to find a row_version.tpt file in both the 
inserts and updates directories. The contents of these files might look like this:

inserts/row_version.tpt:
```
1
```
updates/row_version.tpt:
```
row_version + 1
```
When it comes to the "who" columns, we have to be slightly creative. For example, take the `created_by` column; we 
might have something like this:

inserts/created_by.tpt:
```
current_user
```
updates/created_by.tpt:
```
created_by
```
Because we must satisfy the requirement to include an `updates\created_by.tpt` entry, we just have it set the column to 
its current value.

### The auto_maintained_cols Property
This is a comma separated list of column names which are maintained either by table triggers or by use of column 
expressions, configured to appear within the generated TAPIs (more on these a little later).

This list should not include the column included to the `row_version_column_name` property (if one is set).

### The row_version_column_name Property
The row_version_column_name, need not be set, if you are not interested in the optimistic locking aspects of the TAPI 
generation, however, if it is set, <b>ensure that the row_version_column_name column name is not included to the 
`auto_maintained_cols` list of columns</b>.

## utPLSQL Support
### Overview
OraTAPI provides some support for utPLSQL package generation, providing tests for generated table APIs. This support provides for 
the generation of the package spec, which includes requisite utPLSQL annotations and configurable %throws codes for table column 
constraints.  

When generated, the generated package specs are more or less complete (depending on your specific requirements).
The generated package body, includes a matching set of procedures with stubbed bodies.
Hints, by the way of comments, are included to each, providing details such as columns associated with constraints,
search conditions and parent tables (foreign key related) are listed.

### Controls
For the most part the utPLSQL code generation is controlled by properties in the `ut_controls` section of the `OraTAPI.ini` file.
There is also a related property, `enable_tapis_when_ut_enabled` under the `behaviour` section. This should be set to false, if
you wish to disable generation of TAPI, View and Trigger code whilst generating utPLSQL package code.
The control properties associated with utPLSQL package generation are described under the [\[ut\_control\]](#ut_control) 
subsection.


## Template Substitution Strings
Any properties from the OraTAPI.ini file may be interpolated into the templates.  

**When embedding into the templates, the substitution strings must be delimited by a pair of % characters**.  

In addition, the following may be used.

| Substitition String      | Description                                                                                      |
|--------------------------|--------------------------------------------------------------------------------------------------|
| STAB                     | Indent Tab-space (%STAB% is converted to [OraTAPI.ini specified] indent_spaces number of spaces) |
| package_owner_lc         | The (lowercase) target schema in which the generated package(s) will be placed                   |
| table_domain_lc          | The table domain mapping (maintained in OraTAPI.csv)     
| table_name_lc            | Table name (in lowercase)                                                                        |
| table_owner_lc           | Table schema (in lowercase)                                                                      |
| tapi_author_lc           | TAPI author (in lowercase)                                                                       |
| tapi_pkg_name_prefix_lc  | Package name prefix (in lowercase)                                                               |
| tapi_pkg_name_postfix_lc | Package name postfix (in lowercase)                                                              |
| trigger_owner_lc         | Target trigger schema (in lowercase)                                                             |
| view_name_suffix_lc      | View name postfix (in lowercase)                                                                 |
| view_owner_lc            | Target Table schema (in lowercase)                                                               |


## Connection Manager

The connection manager allows you to treat database connections in a similar manner to named connections in `SQLcl`. Connection credentials and DNS (TNS) strings can be stored and retrieved locally, by use of a conventient name. Credentials are transparrently encrypted/decrypted from a locally maintained store. The `conn_mgr` command allows you to save credentials and a connect string, by using a combination of the following command line arguments:

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
Here’s a revised version of your sentence with improved grammar and clarity:

The `-n/--name` option is mandatory when used with all other options, except for the `-l/--list` option. Additionally, the `-c/--create`, `-e/--edit`, and `-d/--delete` options are mutually exclusive.
Connection credentials are stored with 256-bit AES encryption, to a local store, at: `<USER_HOME_DIR>/.OraTAPI/dsn_credentials.ini`.  

<b>NOTE: The credential store is non-transportable. If you try to use it on a computer on which it was not maintained, the decryption will fail.</b>


## Sample Generated Table API Packages:

Here we see examples og TAPI packages, based on the `jobs` table, and using the `basic` and `logger` 
templates.

The `jobs` table:
```
Name        Null?    Type                        
----------- -------- --------------------------- 
JOB_ID      NOT NULL VARCHAR2(10)                
JOB_TITLE   NOT NULL VARCHAR2(35)                
MIN_SALARY           NUMBER(6)                   
MAX_SALARY           NUMBER(6)                   
CREATED_BY           VARCHAR2(60)                
CREATED_ON           TIMESTAMP(6) WITH TIME ZONE 
ROW_VERSION          NUMBER          
```

The command:
```
bin/ora_tapi.sh --package_owner aut --conn_name TAPI  --tapi_author cbostock
```
In the above command, the connection name, `TAPI`, has been configured using the OraTAPI `conn_mgr` command.

### Basic Templates Example
Generated package body using the `basic` templates:
```
create or replace package body aut.jobs_tapi
as
--------------------------------------------------------------------------------
--
-- Copyright(C) 2025, Clive`s Software Emporium
-- All Rights Reserved
--
--------------------------------------------------------------------------------
-- Application      :   Human Resources
-- Domain           :   undefined
-- Package          :   jobs_tapi
-- Source file name :   jobs_tapi.sql
-- Purpose          :   Table API (TAPI) for table jobs
--
-- Notes            :   Generated using OraTAPI, by cbostock on 08-Jan-2025.
--                  :   From basic sample
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
   -- Insert TAPI for: aut.jobs
   -----------------------------------------------------------------------------
   procedure ins
   (
        p_job_id           in       jobs.job_id%type
      , p_row              in out   jobs%rowtype
   )
   is
   begin

      insert into jobs
         (
              job_id
            , job_title
            , min_salary
            , max_salary
         )
      values
         (
              p_row.job_id
            , p_row.job_title
            , p_row.min_salary
            , p_row.max_salary
         )
      returning
              job_id
            , row_version
            into
              p_row.job_id
            , p_row.row_version;

   end ins;

   -----------------------------------------------------------------------------
   -- Insert TAPI for: aut.jobs
   -----------------------------------------------------------------------------
   procedure ins
   (
        p_job_id           in out   jobs.job_id%type
      , p_job_title        in       jobs.job_title%type
      , p_min_salary       in       jobs.min_salary%type
      , p_max_salary       in       jobs.max_salary%type
      , p_row_version         out   jobs.row_version%type
   )
   is
   begin

      insert into jobs
         (
              job_id
            , job_title
            , min_salary
            , max_salary
         )
      values
         (
              p_job_id
            , p_job_title
            , p_min_salary
            , p_max_salary
         )
      returning
              job_id
            , row_version
            into
              p_job_id
            , p_row_version;

   end ins;

   -----------------------------------------------------------------------------
   -- Select TAPI for: aut.jobs
   -----------------------------------------------------------------------------
   procedure get
   (
        p_job_id           in       jobs.job_id%type
      , p_row                 out   jobs%rowtype
   )
   is
   begin

      select
           job_id
         , job_title
         , min_salary
         , max_salary
         , created_by
         , created_on
         , row_version
        into
           p_row.job_id
         , p_row.job_title
         , p_row.min_salary
         , p_row.max_salary
         , p_row.created_by
         , p_row.created_on
         , p_row.row_version
       from jobs
      where
            job_id = p_job_id;

   end get;

   -----------------------------------------------------------------------------
   -- Select TAPI for: aut.jobs
   -----------------------------------------------------------------------------
   procedure get
   (
        p_job_id           in out   jobs.job_id%type
      , p_job_title           out   jobs.job_title%type
      , p_min_salary          out   jobs.min_salary%type
      , p_max_salary          out   jobs.max_salary%type
      , p_created_by          out   jobs.created_by%type
      , p_created_on          out   jobs.created_on%type
      , p_row_version         out   jobs.row_version%type
   )
   is
   begin

      select
           job_id
         , job_title
         , min_salary
         , max_salary
         , created_by
         , created_on
         , row_version
        into
           p_job_id
         , p_job_title
         , p_min_salary
         , p_max_salary
         , p_created_by
         , p_created_on
         , p_row_version
       from jobs
      where
            job_id = p_job_id;

   end get;

   -----------------------------------------------------------------------------
   -- Update TAPI for: aut.jobs
   -----------------------------------------------------------------------------
   procedure upd
   (
        p_job_id           in       jobs.job_id%type
      , p_row              in out   jobs%rowtype
   )
   is
   begin

      update jobs
      set
           job_title                      = p_row.job_title
         , min_salary                     = p_row.min_salary
         , max_salary                     = p_row.max_salary
         , created_by                     = p_row.created_by
         , created_on                     = p_row.created_on
      where
            job_id = p_job_id
      returning
              job_id
            , row_version
            into
              p_row.job_id
            , p_row.row_version;

   end upd;


   -----------------------------------------------------------------------------
   -- Update TAPI for: aut.jobs
   -----------------------------------------------------------------------------
   procedure upd
   (
        p_job_id           in out   jobs.job_id%type
      , p_job_title        in       jobs.job_title%type
      , p_min_salary       in       jobs.min_salary%type
      , p_max_salary       in       jobs.max_salary%type
      , p_row_version         out   jobs.row_version%type
   )
   is
   begin

      update jobs
      set
           job_title                      = p_job_title
         , min_salary                     = p_min_salary
         , max_salary                     = p_max_salary
      where
            job_id = p_job_id
      returning
              job_id
            , row_version
            into
              p_job_id
            , p_row_version;

   end upd;


   -----------------------------------------------------------------------------
   -- Delete TAPI for: aut.jobs
   -----------------------------------------------------------------------------
   procedure del
   (
        p_job_id           in out   jobs.job_id%type
      , p_row_version         out   jobs.row_version%type
   )
   is

   begin

        delete
          from jobs
         where
               job_id = p_job_id
      returning
              job_id
            , row_version
            into
              p_job_id
            , p_row_version;

--          if sql%rowcount = 0
--          then
--             raise NO_DATA_FOUND;
--          end if;

   end del;
end jobs_tapi;
/
```
### Logger Templates Example
Generated package body using the `logger` templates:
```sql
create or replace package body aut.jobs_tapi
as
--------------------------------------------------------------------------------
--
-- Copyright(C) 2025, Clive`s Software Emporium
-- All Rights Reserved
--
--------------------------------------------------------------------------------
-- Application      :   Human Resources
-- Domain           :   undefined
-- Package          :   jobs_tapi
-- Source file name :   jobs_tapi.sql
-- Purpose          :   Table API (TAPI) for table jobs
--
-- HAS COMMITS      :   NO
-- HAS ROLLBACKS    :   NO
--
-- Notes            :   Generated by cbostock on 08-Jan-2025
--                  :   From Liquibase/Logger sample
--  
--------------------------------------------------------------------------------

--------------------------------------------------------------------------------
--< PUBLIC TYPES AND GLOBALS >--------------------------------------------------

   gc_unit_prefix       constant varchar(64) := lower($$pls_unit) || '.';

--------------------------------------------------------------------------------

--------------------------------------------------------------------------------
--< PUBLIC METHODS >------------------------------------------------------------


   -----------------------------------------------------------------------------
   -- Insert TAPI for: aut.jobs
   -----------------------------------------------------------------------------
   procedure ins
   (
        p_job_id           in       jobs.job_id%type
      , p_row              in out   jobs%rowtype
   )
   is

      l_scope           logger_user.logger_logs.scope%type    := gc_unit_prefix || 'del';
      l_params          logger_user.logger.tab_param;

   begin

      -- We don't log any CLOB parameters here.
      logger_user.logger.append_param(l_params, '* p_row.job_id', p_row.job_id);
      logger_user.logger.append_param(l_params, '  p_row.job_title', p_row.job_title);
      logger_user.logger.append_param(l_params, '  p_row.min_salary', p_row.min_salary);
      logger_user.logger.append_param(l_params, '  p_row.max_salary', p_row.max_salary);

      logger.log('START', l_scope, null, l_params);

      insert into jobs
         (
              job_id
            , job_title
            , min_salary
            , max_salary
         )
      values
         (
              p_row.job_id
            , p_row.job_title
            , p_row.min_salary
            , p_row.max_salary
         )
      returning
              job_id
            , row_version
            into
              p_row.job_id
            , p_row.row_version;

      logger.log('END', l_scope);

   exception
      when others then
         logger_user.logger.log_error('Unhandled exception ', l_scope, null, l_params);
         raise;

   end ins;


   -----------------------------------------------------------------------------
   -- Insert TAPI for: aut.jobs
   -----------------------------------------------------------------------------
   procedure ins
   (
        p_job_id           in out   jobs.job_id%type
      , p_job_title        in       jobs.job_title%type
      , p_min_salary       in       jobs.min_salary%type
      , p_max_salary       in       jobs.max_salary%type
      , p_row_version         out   jobs.row_version%type
   )
   is

      l_scope           logger_user.logger_logs.scope%type    := gc_unit_prefix || 'del';
      l_params          logger_user.logger.tab_param;

   begin

      -- We don't log any CLOB parameters here.
      logger_user.logger.append_param(l_params, '* p_job_id', p_job_id);
      logger_user.logger.append_param(l_params, '  p_job_title', p_job_title);
      logger_user.logger.append_param(l_params, '  p_min_salary', p_min_salary);
      logger_user.logger.append_param(l_params, '  p_max_salary', p_max_salary);

      logger.log('START', l_scope, null, l_params);

      insert into jobs
         (
              job_id
            , job_title
            , min_salary
            , max_salary
         )
      values
         (
              p_job_id
            , p_job_title
            , p_min_salary
            , p_max_salary
         )
      returning
              job_id
            , row_version
            into
              p_job_id
            , p_row_version;

      logger.log('END', l_scope);

   exception
      when others then
         logger_user.logger.log_error('Unhandled exception ', l_scope, null, l_params);
         raise;

   end ins;


   -----------------------------------------------------------------------------
   -- Select TAPI for: aut.jobs
   -----------------------------------------------------------------------------
   procedure get
   (
        p_job_id           in       jobs.job_id%type
      , p_row                 out   jobs%rowtype
   )
   is

      l_scope           logger_user.logger_logs.scope%type    := gc_unit_prefix || 'del';
      l_params          logger_user.logger.tab_param;

   begin

      -- We don't log any CLOB parameters here.
      logger_user.logger.append_param(l_params, '* p_row.job_id', p_row.job_id);

      logger.log('START', l_scope, null, l_params);

      select
           job_id
         , job_title
         , min_salary
         , max_salary
         , created_by
         , created_on
         , row_version
        into
           p_row.job_id
         , p_row.job_title
         , p_row.min_salary
         , p_row.max_salary
         , p_row.created_by
         , p_row.created_on
         , p_row.row_version
       from jobs
      where
            job_id = p_job_id;

      logger.log('END', l_scope);

   exception
      when others then
         logger_user.logger.log_error('Unhandled exception ', l_scope, null, l_params);
         raise;

   end get;


   -----------------------------------------------------------------------------
   -- Select TAPI for: aut.jobs
   -----------------------------------------------------------------------------
   procedure get
   (
        p_job_id           in out   jobs.job_id%type
      , p_job_title           out   jobs.job_title%type
      , p_min_salary          out   jobs.min_salary%type
      , p_max_salary          out   jobs.max_salary%type
      , p_created_by          out   jobs.created_by%type
      , p_created_on          out   jobs.created_on%type
      , p_row_version         out   jobs.row_version%type
   )
   is

      l_scope           logger_user.logger_logs.scope%type    := gc_unit_prefix || 'del';
      l_params          logger_user.logger.tab_param;

   begin

      -- We don't log any CLOB parameters here.
      logger_user.logger.append_param(l_params, '* p_job_id', p_job_id);

      logger.log('START', l_scope, null, l_params);

      select
           job_id
         , job_title
         , min_salary
         , max_salary
         , created_by
         , created_on
         , row_version
        into
           p_job_id
         , p_job_title
         , p_min_salary
         , p_max_salary
         , p_created_by
         , p_created_on
         , p_row_version
       from jobs
      where
            job_id = p_job_id;

      logger.log('END', l_scope);

   exception
      when others then
         logger_user.logger.log_error('Unhandled exception ', l_scope, null, l_params);
         raise;

   end get;


   -----------------------------------------------------------------------------
   -- Update TAPI for: aut.jobs
   -----------------------------------------------------------------------------
   procedure upd
   (
        p_job_id           in       jobs.job_id%type
      , p_row              in out   jobs%rowtype
   )
   is

      l_scope           logger_user.logger_logs.scope%type    := gc_unit_prefix || 'del';
      l_params          logger_user.logger.tab_param;

   begin

      -- We don't log any CLOB parameters here.
      logger_user.logger.append_param(l_params, '* p_row.job_id', p_row.job_id);
      logger_user.logger.append_param(l_params, '  p_row.job_title', p_row.job_title);
      logger_user.logger.append_param(l_params, '  p_row.min_salary', p_row.min_salary);
      logger_user.logger.append_param(l_params, '  p_row.max_salary', p_row.max_salary);

      logger.log('START', l_scope, null, l_params);

      update jobs
      set
           job_title                      = p_row.job_title
         , min_salary                     = p_row.min_salary
         , max_salary                     = p_row.max_salary
         , created_by                     = p_row.created_by
         , created_on                     = p_row.created_on
      where
            job_id = p_job_id
      returning
              job_id
            , row_version
            into
              p_row.job_id
            , p_row.row_version;

      logger.log('END', l_scope);

   exception
      when others then
         logger_user.logger.log_error('Unhandled exception ', l_scope, null, l_params);
         raise;

   end upd;


   -----------------------------------------------------------------------------
   -- Update TAPI for: aut.jobs
   -----------------------------------------------------------------------------
   procedure upd
   (
        p_job_id           in out   jobs.job_id%type
      , p_job_title        in       jobs.job_title%type
      , p_min_salary       in       jobs.min_salary%type
      , p_max_salary       in       jobs.max_salary%type
      , p_row_version         out   jobs.row_version%type
   )
   is

      l_scope           logger_user.logger_logs.scope%type    := gc_unit_prefix || 'del';
      l_params          logger_user.logger.tab_param;

   begin

      -- We don't log any CLOB parameters here.
      logger_user.logger.append_param(l_params, '* p_job_id', p_job_id);
      logger_user.logger.append_param(l_params, '  p_job_title', p_job_title);
      logger_user.logger.append_param(l_params, '  p_min_salary', p_min_salary);
      logger_user.logger.append_param(l_params, '  p_max_salary', p_max_salary);

      logger.log('START', l_scope, null, l_params);

      update jobs
      set
           job_title                      = p_job_title
         , min_salary                     = p_min_salary
         , max_salary                     = p_max_salary
      where
            job_id = p_job_id
      returning
              job_id
            , row_version
            into
              p_job_id
            , p_row_version;

      logger.log('END', l_scope);

   exception
      when others then
         logger_user.logger.log_error('Unhandled exception ', l_scope, null, l_params);
         raise;

   end upd;


   -----------------------------------------------------------------------------
   -- Delete TAPI for: aut.jobs
   -----------------------------------------------------------------------------
   procedure del
   (
        p_job_id           in out   jobs.job_id%type
      , p_row_version         out   jobs.row_version%type
   )
   is

      l_scope           logger_user.logger_logs.scope%type    := gc_unit_prefix || 'del';
      l_params          logger_user.logger.tab_param;

   begin

      -- We don't log any CLOB parameters here.
      logger_user.logger.append_param(l_params, '* p_job_id', p_job_id);

      logger.log('START', l_scope, null, l_params);

        delete
          from jobs
         where
               job_id = p_job_id
      returning
              job_id
            , row_version
            into
              p_job_id
            , p_row_version;

      logger.log('END', l_scope);

   exception
      when others then
         logger_user.logger.log_error('Unhandled exception ', l_scope, null, l_params);
         raise;

   end del;

end jobs_tapi;
/
```


## License

OraTAPI is licensed under the [MIT License](LICENSE).

---

This README covers the tool's purpose, usage, configuration, and output, providing a clear guide for potential users. Let me know if you'd like any adjustments!
