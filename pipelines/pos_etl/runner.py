from __future__ import annotations

import fnmatch
import json
import time
from datetime import datetime

from .catalog import PosCatalog
from .config import PosEtlConfig
from .extractor import PosExtractor


def run_pos_etl(
    config: PosEtlConfig,
    *,
    product_pattern: str = "raw_pos_*",
    dry_run: bool = False,
) -> dict:
    catalog = PosCatalog()
    extractor = PosExtractor(
        sql_uri=config.sql_uri,
        lake_root=config.lake_root,
        catalog=catalog,
        query_timeout_seconds=config.query_timeout_seconds,
    )

    product_ids = [
        product_id
        for product_id in catalog.iter_ids()
        if fnmatch.fnmatchcase(product_id, product_pattern)
    ]
    if not product_ids:
        raise ValueError(f"No hay productos POS que coincidan con: {product_pattern}")

    started = time.monotonic()
    results = []
    for product_id in product_ids:
        try:
            result = extractor.extract(
                product_id,
                config.run_from,
                config.run_to,
                config.company_id,
                dry_run=dry_run,
            )
            results.append(
                {
                    "product": result.product_id,
                    "rows": result.row_count,
                    "duration_seconds": round(result.duration_seconds, 3),
                    "output": str(result.output_path) if result.output_path else None,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "product": product_id,
                    "rows": None,
                    "duration_seconds": None,
                    "output": None,
                    "error": str(exc),
                }
            )

    failures = [item for item in results if "error" in item]
    summary = {
        "status": "failed" if failures else "ok",
        "run_from": config.run_from.isoformat(),
        "run_to": config.run_to.isoformat(),
        "company_id": config.company_id,
        "duration_seconds": round(time.monotonic() - started, 3),
        "dry_run": dry_run,
        "products": results,
        "failures": len(failures),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary
