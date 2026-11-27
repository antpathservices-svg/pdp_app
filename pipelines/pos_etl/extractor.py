from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import time

import polars as pl
import connectorx as cx

from .catalog import PosCatalog


@dataclass(frozen=True)
class ExtractionResult:
    product_id: str
    row_count: int
    duration_seconds: float
    output_path: Path | None


class PosExtractor:
    def __init__(
        self,
        *,
        sql_uri: str,
        lake_root: Path,
        catalog: PosCatalog | None = None,
        query_timeout_seconds: int = 240,
    ) -> None:
        self.sql_uri = sql_uri
        self.lake_root = lake_root
        self.catalog = catalog or PosCatalog()
        self.query_timeout_seconds = query_timeout_seconds

    def build_query(
        self,
        product: dict,
        run_from: datetime,
        run_to: datetime,
        company_id: int = 1,
    ) -> str:
        columns = self.catalog.attribute_names(product)
        if not columns:
            raise ValueError(f"El producto {product['id']} no tiene atributos")

        column_sql = ",\n    ".join(columns)
        query = f"SELECT\n    {column_sql}\nFROM dbo.{product['tabla']}"
        conditions: list[str] = []
        columns = self.catalog.attribute_names(product)
        if "idempresa" in columns:
            conditions.append(f"idempresa = {company_id}")
        incremental_column = product.get("inc")
        if incremental_column:
            if incremental_column not in columns:
                raise ValueError(
                    f"{product['id']} declara inc={incremental_column} inexistente"
                )
            start = run_from.strftime("%Y-%m-%d %H:%M:%S")
            end = run_to.strftime("%Y-%m-%d %H:%M:%S")
            conditions.append(
                f"{incremental_column} >= '{start}' AND {incremental_column} < '{end}'"
            )
        if conditions:
            query += "\nWHERE " + " AND ".join(conditions)
        if product.get("orden"):
            query += f"\nORDER BY {product['orden']}"
        query += ";"
        return query

    def extract(
        self,
        product_id: str,
        run_from: datetime,
        run_to: datetime,
        company_id: int,
        dry_run: bool = False,
    ) -> ExtractionResult:
        product = self.catalog.get(product_id)
        query = self.build_query(product, run_from, run_to, company_id)

        if dry_run:
            print(query)
            return ExtractionResult(product_id, 0, 0.0, None)

        started = time.monotonic()
        frame = self._read_sql(query)
        duration = time.monotonic() - started

        if not isinstance(frame, pl.DataFrame):
            frame = pl.from_pandas(frame)

        expected = self.catalog.attribute_names(product)
        if frame.columns != expected:
            raise RuntimeError(
                f"Contrato roto en {product_id}: "
                f"esperadas={expected}, recibidas={frame.columns}"
            )

        output_path = self.raw_output_path(
            product_id,
            company_id,
            run_from,
            run_to,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_suffix(".parquet.tmp")
        frame.write_parquet(temporary_path)
        temporary_path.replace(output_path)

        return ExtractionResult(
            product_id=product_id,
            row_count=frame.height,
            duration_seconds=duration,
            output_path=output_path,
        )

    def _read_sql(self, query: str) -> pl.DataFrame:
        if self.sql_uri.startswith("integrated:"):
            import pyodbc

            server = self.sql_uri.removeprefix("integrated:")
            connection_string = (
                "DRIVER={ODBC Driver 18 for SQL Server};"
                f"SERVER={server};DATABASE=softrestaurant10;"
                "Trusted_Connection=yes;"
                "TrustServerCertificate=yes;"
            )
            with pyodbc.connect(
                connection_string,
                timeout=self.query_timeout_seconds,
            ) as connection:
                cursor = connection.cursor()
                cursor.execute(query)
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()
            if not rows:
                return pl.DataFrame(schema={column: pl.Null for column in columns})
            return pl.DataFrame(
                {
                    column: [row[index] for row in rows]
                    for index, column in enumerate(columns)
                }
            )

        frame = cx.read_sql(
            conn=self.sql_uri,
            query=query,
            return_type="polars",
        )
        if isinstance(frame, pl.DataFrame):
            return frame
        return pl.from_pandas(frame)

    def raw_output_path(
        self,
        product_id: str,
        company_id: int,
        run_from: datetime,
        run_to: datetime,
    ) -> Path:
        range_key = f"{run_from.isoformat()}_{run_to.isoformat()}"
        digest = sha256(range_key.encode("utf-8")).hexdigest()[:12]
        date = run_to.date().isoformat()
        return (
            self.lake_root
            / "raw"
            / "pos"
            / product_id
            / f"idempresa={company_id}"
            / f"fecha={date}"
            / f"batch-{digest}.parquet"
        )
