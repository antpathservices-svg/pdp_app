from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


class PosCatalog:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = Path(__file__).resolve().parents[2] / "sharepoint" / "productos.json"
        with path.open("r", encoding="utf-8") as handle:
            document = json.load(handle)
        self.products = {
            product["id"]: product
            for product in document["productos"]
            if product["origen"] == "pos"
        }

    def get(self, product_id: str) -> dict:
        try:
            return self.products[product_id]
        except KeyError as exc:
            raise KeyError(f"Producto POS desconocido: {product_id}") from exc

    def iter_ids(self, pattern: str = "*") -> Iterator[str]:
        import fnmatch

        yield from sorted(
            product_id
            for product_id in self.products
            if fnmatch.fnmatchcase(product_id, pattern)
        )

    def attribute_names(self, product: dict) -> list[str]:
        names: list[str] = []
        for entity in product["ent"]:
            for attribute in entity["a"]:
                names.append(attribute[0])
        return names
