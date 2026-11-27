from datetime import datetime
from pathlib import Path

from pipelines.pos_etl.catalog import PosCatalog
from pipelines.pos_etl.extractor import PosExtractor


def test_incremental_query_is_parameterized(tmp_path):
    extractor = PosExtractor(
        sql_uri="mssql://unused",
        lake_root=tmp_path,
    )
    product = PosCatalog().get("raw_pos_venta_cuenta")
    query = extractor.build_query(
        product,
        datetime(2026, 10, 29),
        datetime(2026, 10, 30),
    )
    assert "SELECT" in query
    assert "FROM dbo.cheques" in query
    assert "cierre >= '2026-10-29 00:00:00'" in query
    assert "AND cierre < '2026-10-30 00:00:00'" in query
    assert "2026-10-29" in query


def test_catalog_query_references_only_catalog_columns(tmp_path):
    catalog = PosCatalog()
    extractor = PosExtractor(
        sql_uri="mssql://unused",
        lake_root=tmp_path,
        catalog=catalog,
    )
    product = catalog.get("raw_pos_producto")
    query = extractor.build_query(
        product,
        datetime(2026, 10, 29),
        datetime(2026, 10, 30),
    )
    for name in catalog.attribute_names(product):
        assert name in query


def test_company_filter_is_added_when_contract_has_idempresa(tmp_path):
    catalog = PosCatalog()
    extractor = PosExtractor(
        sql_uri="mssql://unused",
        lake_root=tmp_path,
        catalog=catalog,
    )
    product = catalog.get("raw_pos_venta_cuenta")
    query = extractor.build_query(
        product,
        datetime(2026, 10, 29),
        datetime(2026, 10, 30),
        company_id=7,
    )
    assert "WHERE idempresa = 7" in query
