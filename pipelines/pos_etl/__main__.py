from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime

from .config import PosEtlConfig
from .runner import run_pos_etl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ETL raw de datos POS")
    parser.add_argument("--from", dest="run_from", help="Inicio ISO-8601")
    parser.add_argument("--to", dest="run_to", help="Fin ISO-8601")
    parser.add_argument("--product", default="raw_pos_*", help="Patrón de producto")
    parser.add_argument("--lake-root", help="Raíz local o ruta del lago")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--sql-uri",
        help="URI SQL; use integrated:SERVIDOR para autenticación integrada",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_from = datetime.fromisoformat(args.run_from) if args.run_from else None
    run_to = datetime.fromisoformat(args.run_to) if args.run_to else None
    config = PosEtlConfig.from_environment(
        run_from=run_from,
        run_to=run_to,
        lake_root=args.lake_root,
        allow_missing_sql_uri=args.dry_run or bool(args.sql_uri),
    )
    if args.sql_uri:
        config = replace(config, sql_uri=args.sql_uri)
    summary = run_pos_etl(
        config,
        product_pattern=args.product,
        dry_run=args.dry_run,
    )
    return 1 if summary["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
