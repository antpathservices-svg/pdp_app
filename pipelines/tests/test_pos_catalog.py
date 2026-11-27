import json
from pathlib import Path

from pipelines.pos_etl.catalog import PosCatalog


def test_catalog_contains_expected_pos_products():
    catalog = PosCatalog()
    assert len(catalog.products) == 14


def test_all_pos_select_contracts_match_json():
    root = Path(__file__).resolve().parents[2]
    catalog = PosCatalog()
    for product_id, product in catalog.products.items():
        names = catalog.attribute_names(product)
        assert names
        assert product["tabla"]
        if product["inc"]:
            assert product["inc"] in names
        assert len(names) == len(set(names)), product_id
