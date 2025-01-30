"""
__author__ = "Clive Bostock"
__date__ = "2024-11-09"
__description__ = "Home of the table metadata APIs. Here we model Table classes. This is utilised by the api.py module when generating the TAPIs."
"""

# DBSession is a subclass of oracledb.Connection which has a self.cursor() attribute.
from lib.config_mgr import ConfigManager
from model.session_manager import DBSession


def get_constraint_description(constraint_type:str) -> str:
    """
    Returns a description for a given Oracle constraint type code.

    :param constraint_type: A single-character string representing the constraint type.
    :type constraint_type: str
    :return: A description of the constraint type.
    :rtype: str
    """
    _constraint_type = constraint_type.upper()
    constraint_descriptions = {
        'P': 'Primary Key constraint',
        'U': 'Unique Key constraint',
        'R': 'Referential (Foreign Key) constraint',
        'C': 'Check constraint',
        'N': 'Not Null constraint'
    }

    return constraint_descriptions.get(_constraint_type, 'Unsupported constraint type')


class Table:
    def __init__(self, database_session: DBSession, table_owner: str, table_name: str, config_manager: ConfigManager, trace: bool = False):
        """
        Initialize the Table object.

        :param database_session: A database session object connected to Oracle.
        :type database_session: DBSession
        :param table_owner: The schema name of the table.
        :type table_owner: str
        :param table_name: The name of the table.
        :type table_name: str
        :param trace: Enables tracing/debugging if True.
        :type trace: bool
        """
        self.schema_name = table_owner.upper()
        self.schema_name_lc = table_owner.lower()
        self.table_name = table_name.upper()
        self.table_name_lc = table_name.lower()
        self.trace = trace
        self.db_session = database_session
        self.columns_dict = {}
        self.columns_list = []
        self.max_col_name_len = 0
        self.col_count = 0

        self.row_vers_column_name = config_manager.config_value(config_section="api_controls",
                                                                config_key="row_vers_column_name")

        self.return_pk_key_columns = config_manager.bool_config_value(config_section="api_controls",
                                                                     config_key="return_pk_key_columns",
                                                                     default=True)

        self.return_ak_key_columns = config_manager.bool_config_value(config_section="api_controls",
                                                                     config_key="return_ak_key_columns",
                                                                     default=False)

        self.in_out_column_list = []
        self.out_column_list = []
        self.pk_columns_list = []
        self.ak_columns_list = []
        self.in_out_column_list_lc = []
        self.out_column_list_lc = []
        self.pk_columns_list_lc = []
        self.ak_columns_list_lc = []

        self.tab_col_metadata()

    def tab_col_metadata(self) -> dict:
        """
        Queries the Oracle data dictionary for column metadata and returns a nested dictionary.

        :return: A dictionary of dictionaries containing column metadata.
                 Outer key: column_name
                 Inner dictionary keys: 'data_type', 'default_value', 'nullable'
        :rtype: dict
        """
        query = """
                select 
                    column_name,
                    data_type,
                    data_default,
                    nullable
                from 
                    all_tab_columns
                where 
                    owner = :schema_name
                    and table_name = :table_name
                order by column_id
        """
        column_metadata_dict = {}
        column_list = []
        try:
            with self.db_session.cursor() as cursor:
                if self.trace:
                    print(f"Executing query: {query}")
                    print(f"Parameters: schema_name={self.schema_name}, table_name={self.table_name}")
                cursor.execute(query, schema_name=self.schema_name, table_name=self.table_name)
                # For performance reason - resisted the temptation to implement a TableColumn class.
                for row in cursor:
                    column_name, data_type, data_default, nullable = row
                    # Record whether this is part of a PK or UK
                    if data_default is not None:
                        data_default = str(data_default).strip()
                    column_keyed = self._is_column_keyed(column_name=column_name)
                    is_pk_column = self._is_pk_col(column_name=column_name)

                    is_nullable = True if nullable == 'Y' else False

                    self.max_col_name_len = len(column_name) if len(column_name) > self.max_col_name_len else self.max_col_name_len
                    is_ak_column = True if not is_pk_column and column_keyed else False
                    is_row_version_column = True if column_name.lower() == self.row_vers_column_name.lower() else False
                    column_metadata_dict[column_name] = {
                        "data_type": data_type,
                        "default_value": data_default,
                        "is_nullable": is_nullable,
                        "is_pk_column": is_pk_column,
                        "is_ak_column": is_ak_column,
                        "is_key_column": column_keyed,
                        "is_row_version_column": is_row_version_column
                    }
                    if is_pk_column:
                        self.pk_columns_list.append(column_name.upper())
                        self.pk_columns_list_lc.append(column_name.lower())
                    if is_ak_column:
                        self.ak_columns_list.append(column_name.upper())
                        self.ak_columns_list_lc.append(column_name.lower())
                    if is_pk_column and self.return_pk_key_columns and not is_row_version_column:
                        self.in_out_column_list.append(column_name.upper())
                        self.in_out_column_list_lc.append(column_name.lower())
                    elif is_ak_column and self.return_ak_key_columns and not is_row_version_column:
                        self.in_out_column_list.append(column_name.upper())
                        self.in_out_column_list_lc.append(column_name.lower())
                    elif is_row_version_column:
                        self.out_column_list.append(column_name.upper())
                        self.out_column_list_lc.append(column_name.lower())


                    column_list.append(column_name)
                    self.col_count += 1
            self.columns_dict = column_metadata_dict
            self.columns_list = column_list

        except Exception as e:
            if self.trace:
                print(f"Error fetching column metadata: {e}")
            raise
        return column_metadata_dict

    def column_property_value(self, column_name:str, property_name:str) -> str:
        """Returns the value of the requested column property from the self.columns_dict. The property_name can be one
         of 'data_type', 'default_value', 'is_nullable' or 'is_key_column'

        :param column_name: Name of the table column to interrogate.
        :param property_name: The property (key) for which the value is to be returned.
        :return:
        """
        _column_name = column_name.upper()
        column_dict = self.columns_dict[_column_name]
        property_value = column_dict[property_name.lower()]
        return property_value

    def _is_column_keyed(self, column_name: str) -> bool:
        """
        Checks if a column is referenced in a primary key constraint or unique index.

        :param column_name: The name of the column to check.
        :type column_name: str
        :return: True if the column is part of a primary key or unique index, otherwise False.
        :rtype: bool
        """
        query = """
                select 1
                from all_cons_columns acc
                join all_constraints ac
                    on acc.owner = ac.owner
                    and acc.constraint_name = ac.constraint_name
                where acc.owner = :schema_name
                    and acc.table_name = :table_name
                    and acc.column_name = :column_name
                    and ac.constraint_type in ('P', 'U')
        """
        try:
            with self.db_session.cursor() as cursor:
                if self.trace:
                    print(f"Executing query: {query}")
                    print(f"Parameters: schema_name={self.schema_name}, table_name={self.table_name}, column_name={column_name.upper()}")
                cursor.execute(
                    query,
                    schema_name=self.schema_name,
                    table_name=self.table_name,
                    column_name=column_name.upper()
                )
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            if self.trace:
                print(f"Error checking if column is keyed: {e}")
            raise

    def _is_ak_col(self, column_name: str) -> bool:
        """
        Checks if a column is referenced in an alternate key / unique constraint.

        :param column_name: The name of the column to check.
        :type column_name: str
        :return: True if the column is part of a primary key or unique index, otherwise False.
        :rtype: bool
        """
        query = """
                select 1
                from all_cons_columns acc
                join all_constraints ac
                    on acc.owner = ac.owner
                    and acc.constraint_name = ac.constraint_name
                where acc.owner = :schema_name
                    and acc.table_name = :table_name
                    and acc.column_name = :column_name
                    and ac.constraint_type in ('U');
        """
        try:
            with self.db_session.cursor() as cursor:
                if self.trace:
                    print(f"Executing query: {query}")
                    print(f"Parameters: schema_name={self.schema_name}, table_name={self.table_name}, column_name={column_name.upper()}")
                cursor.execute(
                    query,
                    schema_name=self.schema_name,
                    table_name=self.table_name,
                    column_name=column_name.upper()
                )
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            if self.trace:
                print(f"Error checking if column is keyed: {e}")
            raise

    def _is_pk_col(self, column_name: str) -> bool:
        """
        Checks if a column is referenced in a primary key constraint or unique index.

        :param column_name: The name of the column to check.
        :type column_name: str
        :return: True if the column is part of a primary key or unique index, otherwise False.
        :rtype: bool
        """
        query = """
                select 1
                from all_cons_columns acc
                join all_constraints ac
                    on acc.owner = ac.owner
                    and acc.constraint_name = ac.constraint_name
                where acc.owner = :schema_name
                    and acc.table_name = :table_name
                    and acc.column_name = :column_name
                    and ac.constraint_type = 'P'
        """
        try:
            with self.db_session.cursor() as cursor:
                if self.trace:
                    print(f"Executing query: {query}")
                    print(f"Parameters: schema_name={self.schema_name}, table_name={self.table_name}, column_name={column_name.upper()}")
                cursor.execute(
                    query,
                    schema_name=self.schema_name,
                    table_name=self.table_name,
                    column_name=column_name.upper()
                )
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            if self.trace:
                print(f"Error checking if column is keyed: {e}")
            raise

class TableConstraints:
    def __init__(self, database_session: DBSession, table_owner: str, table_name: str,
                 config_manager: ConfigManager, trace: bool = False):
        """
        Initialize the Table object.

        :param database_session: A database session object connected to Oracle.
        :type database_session: DBSession
        :param table_owner: The schema name of the table.
        :type table_owner: str
        :param table_name: The name of the table.
        :type table_name: str
        :param trace: Enables tracing/debugging if True.
        :type trace: bool
        """
        self.db_session = database_session
        self.schema_name = table_owner.upper()
        self.schema_name_desc = table_owner.replace('_', ' ').title()
        self.table_name = table_name.upper()
        self.table_name_desc = table_name.replace('_', ' ').title()
        self.config_manager = config_manager
        self.trace = trace

        # Initialize the metadata dictionary as an instance attribute
        self.constraint_metadata_dict = {}
        self.constraint_list = []
        self.fk_tables_list = []
        self.fk_tables = ''
        self._table_constraints()

    def _table_constraints(self) -> None:
        """
        Queries the Oracle data dictionary for column metadata and returns a nested dictionary.

        :return: A dictionary of dictionaries containing constraint metadata.
                 Outer key: constraint_name
                 Inner dictionary keys:
                     'search_condition', 'columns', 'columns_lc', 'constraint_type', 'status'
        :rtype: dict
        """
        query = """
                select 
                    constraint_name,
                    search_condition_vc,
                    columns,
                    columns_lc,
                    constraint_type,
                    status
                from (
                    select 
                        ac.constraint_name,
                        ac.search_condition_vc,
                        listagg(acc.column_name, ', ') within group (order by acc.position) as columns,
                        listagg(lower(acc.column_name), ', ') within group (order by acc.position) as columns_lc,
                        case 
                            when ac.constraint_type = 'C' and ac.search_condition_vc like '%NOT NULL%' then 'N'
                            else ac.constraint_type
                        end as constraint_type,
                        ac.status
                    from 
                        all_constraints ac
                    join 
                        all_cons_columns acc
                    on 
                        ac.constraint_name = acc.constraint_name 
                        and ac.owner       = acc.owner
                    where 
                        ac.table_name      = :table_name 
                        and ac.owner       = :schema_name
                        and ac.constraint_type in ('P', 'U', 'R', 'C')
                    group by 
                        ac.owner, ac.table_name, ac.search_condition_vc, ac.constraint_name, ac.constraint_type, ac.status, ac.deferrable, ac.deferred
                )
                order by 
                    case 
                        when constraint_type = 'P' then 1  -- Primary key
                        when constraint_type = 'U' then 2  -- Unique key
                        when constraint_type = 'R' then 3  -- Foreign key
                        when constraint_type = 'C' then 4  -- Regular check constraints
                        when constraint_type = 'N' then 5  -- Not null constraints
                        else 6
                    end,
                    constraint_name
        """
        try:
            with self.db_session.cursor() as cursor:
                if self.trace:
                    print(f"Executing query: {query}")
                    print(f"Parameters: schema_name={self.schema_name}, table_name={self.table_name}")
                cursor.execute(query, schema_name=self.schema_name, table_name=self.table_name)

                # Process the query result to populate the nested dictionary
                for row in cursor:
                    constraint_name, search_condition, cons_columns, cons_columns_lc, constraint_type, status = row
                    constraint_name_desc = constraint_name.replace('_', ' ').title()
                    constraint_name_lc = constraint_name.lower()
                    if search_condition:
                        search_condition = search_condition.replace('"', '')
                        search_condition = f"(condition = '{str(search_condition)}')"
                    else:
                        search_condition = ''
                    self.constraint_list.append(constraint_name)
                    # Store the data in the dictionary with constraint_name as the outer key
                    self.constraint_metadata_dict[constraint_name] = {
                        'constraint_name': constraint_name,
                        'constraint_name_lc': constraint_name_lc,
                        'constraint_name_desc': constraint_name_desc,
                        'search_condition': search_condition,
                        'cons_columns': cons_columns,
                        'cons_columns_lc': cons_columns_lc,
                        'constraint_type': constraint_type,
                        'constraint_type_desc': get_constraint_description(constraint_type=constraint_type),
                        'status': status
                    }

        except Exception as e:
            if self.trace:
                print(f"Error fetching constraint metadata: {e}")
            raise


        query = """
                select distinct
                    t2.table_name,
                    d2.owner
                from
                    all_constraints c1,
                    all_constraints c2,
                    all_tables t1,
                    all_tables t2,
                    dba_tables d2
                where
                    c1.table_name            = t1.table_name
                    and c2.table_name        = t2.table_name
                    and c1.constraint_type   = 'R'
                    and c2.constraint_type   = 'P'
                    and c1.r_constraint_name = c2.constraint_name
                    and t1.table_name        = :table_name
                    and t1.owner             = :schema_name
                    and t2.table_name        = d2.table_name
        """
        try:
            with self.db_session.cursor() as cursor:
                if self.trace:
                    print(f"Executing query: {query}")
                    print(f"Parameters: schema_name={self.schema_name}, table_name={self.table_name}")
                cursor.execute(query, schema_name=self.schema_name, table_name=self.table_name)

                # Process the query result to populate the nested dictionary
                for row in cursor:
                    fk_table_name, fk_table_owner = row
                    fk_table_ref = fk_table_owner + '.' + fk_table_name
                    self.fk_tables_list.append(fk_table_ref)

        except Exception as e:
            if self.trace:
                print(f"Error fetching foreign key metadata: {e}")
            raise

        self.fk_tables = ', '.join(self.fk_tables_list)

if __name__ == "__main__":
    # Connection parameters
    dsn = "localhost:1245/UTPLSQL"
    username = "aut"
    password = "Wibble123"

    # Initialize the DB session
    db_session = DBSession(dsn=dsn, db_username=username, db_password=password)

    # Instantiate the Table class
    table = Table(database_session=db_session, table_owner="AUT", table_name="EMPLOYEES", trace=False)
    metadata = table.tab_col_metadata()
    print(metadata)
    # Check if a column is keyed
    is_keyed = table._is_column_keyed("EMPLOYEE_ID")
    print(f"Is 'EMPLOYEE_ID' keyed? {is_keyed}")
    print(f'Data type property of employees.employee_id : {table.column_property_value("employee_id", "data_type" )}')
