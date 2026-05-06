import pytest
from types import SimpleNamespace

from oratapi.model.tapi_generator import ApiGenerator


class _StubTable:
    def __init__(self) -> None:
        self.columns_list = ["ID", "DOC", "GEOM", "NAME"]
        self.pk_columns_list_lc = ["id"]
        self.schema_name_lc = "hr"
        self.table_name_lc = "demo_table"
        self._metadata = {
            "ID": {
                "data_type": "NUMBER",
                "data_type_owner": None,
                "is_pk_column": True,
            },
            "DOC": {
                "data_type": "CLOB",
                "data_type_owner": None,
                "is_pk_column": False,
            },
            "GEOM": {
                "data_type": "SDO_GEOMETRY",
                "data_type_owner": "MDSYS",
                "is_pk_column": False,
            },
            "NAME": {
                "data_type": "VARCHAR2",
                "data_type_owner": None,
                "is_pk_column": False,
            },
        }

    def column_property_value(self, column_name: str, property_name: str):
        return self._metadata[column_name.upper()][property_name]


class _InsertSignatureStubTable:
    def __init__(self, return_identity: bool) -> None:
        self.columns_list = ["ID", "NAME"]
        self.in_out_column_list = ["ID"] if return_identity else []
        self.out_column_list = []
        self.in_out_column_list_lc = ["id"] if return_identity else []
        self.out_column_list_lc = []
        self.max_col_name_len = 4
        self.col_count = len(self.columns_list)
        self._metadata = {
            "ID": {
                "default_value": None,
                "is_key_column": True,
                "is_row_version_column": False,
                "is_pk_column": True,
                "is_ak_column": False,
            },
            "NAME": {
                "default_value": None,
                "is_key_column": False,
                "is_row_version_column": False,
                "is_pk_column": False,
                "is_ak_column": False,
            },
        }

    def column_property_value(self, column_name: str, property_name: str):
        return self._metadata[column_name.upper()][property_name]

    @staticmethod
    def is_identity(column_name: str) -> bool:
        return column_name.upper() == "ID"

    @staticmethod
    def is_identity_always(column_name: str) -> bool:
        return False


def _build_generator(mode: str = "omit") -> ApiGenerator:
    generator = ApiGenerator.__new__(ApiGenerator)
    generator.auto_maintained_cols_lc = []
    generator.row_vers_column_name = ""
    generator.table = _StubTable()
    generator.logger_pkg = "logger"
    generator.logger_skip_data_types = {"CLOB", "MDSYS.SDO_GEOMETRY"}
    generator.logger_skip_data_types_mode = mode
    generator.pi_column_manager = SimpleNamespace(check_column=lambda **_kwargs: False)
    return generator


def _build_insert_signature_generator(return_identity: bool) -> ApiGenerator:
    generator = ApiGenerator.__new__(ApiGenerator)
    generator.auto_maintained_cols = []
    generator.global_substitutions = {"STAB": "   "}
    generator.api_target_name_lc = "demo_table"
    generator.table = _InsertSignatureStubTable(return_identity=return_identity)
    generator.indent_spaces = 3
    generator.include_defaults = False
    generator.include_commit = False
    generator.return_pk_columns = return_identity
    generator.return_ak_columns = False
    generator.comment_tapi = lambda tapi_description: f"-- {tapi_description}\n"
    return generator


def test_parse_data_type_list_normalises_entries() -> None:
    assert ApiGenerator._parse_data_type_list(" clob, long   raw, MDSYS.sdo_geometry ") == {
        "CLOB",
        "LONG RAW",
        "MDSYS.SDO_GEOMETRY",
    }


def test_logger_appends_skip_configured_data_types() -> None:
    generator = _build_generator()

    appends = generator._logger_appends(signature_type="coltype", soft_tabs=2)

    assert "* p_id" in appends
    assert "  p_name" in appends
    assert "p_doc" not in appends
    assert "p_geom" not in appends


def test_logger_appends_comment_mode_emits_comment_for_blocked_data_types() -> None:
    generator = _build_generator(mode="comment")

    appends = generator._logger_appends(signature_type="coltype", soft_tabs=2)

    assert "* p_id" in appends
    assert "  p_name" in appends
    assert "-- skipped logger append for p_doc (CLOB)" in appends
    assert "-- skipped logger append for p_geom (MDSYS.SDO_GEOMETRY)" in appends


def test_logger_appends_redact_mode_emits_placeholder_for_blocked_data_types() -> None:
    generator = _build_generator(mode="redact")

    appends = generator._logger_appends(signature_type="coltype", soft_tabs=2)

    assert "* p_id" in appends
    assert "  p_name" in appends
    assert "'  p_doc', '[datatype skipped: CLOB]'" in appends
    assert "'  p_geom', '[datatype skipped: MDSYS.SDO_GEOMETRY]'" in appends


def test_normalise_logger_skip_data_types_mode_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="skip_logged_data_types_mode"):
        ApiGenerator._normalise_logger_skip_data_types_mode("drop")


def test_insert_coltype_identity_pk_is_output_only_when_returned() -> None:
    generator = _build_insert_signature_generator(return_identity=True)

    signature = generator._insert_api_coltype_sig(package_spec=True, inc_comments=False)
    id_line = next(line for line in signature.splitlines() if "p_id" in line)

    assert "p_id" in signature
    assert "in out" not in id_line
    assert "   out" in id_line


def test_insert_coltype_identity_pk_is_omitted_when_not_returned() -> None:
    generator = _build_insert_signature_generator(return_identity=False)

    signature = generator._insert_api_coltype_sig(package_spec=True, inc_comments=False)

    assert "p_id" not in signature
    assert "p_name" in signature
