from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class PosEtlConfig:
    sql_uri: str
    lake_root: Path
    run_from: datetime
    run_to: datetime
    company_id: int = 1
    timeout_seconds: int = 300
    query_timeout_seconds: int = 240

    @classmethod
    def from_environment(
        cls,
        *,
        run_from: datetime | None = None,
        run_to: datetime | None = None,
        lake_root: str | None = None,
        allow_missing_sql_uri: bool = False,
    ) -> "PosEtlConfig":
        load_dotenv()

        sql_uri = os.getenv("POS_SQL_URI", "").strip()
        if not sql_uri and not allow_missing_sql_uri:
            raise ValueError("POS_SQL_URI es obligatorio")
        if not sql_uri:
            sql_uri = "mssql://dry-run"

        from_value = run_from or cls._parse_datetime(os.getenv("PDP_RUN_FROM"))
        to_value = run_to or cls._parse_datetime(os.getenv("PDP_RUN_TO"))
        if from_value is None or to_value is None:
            raise ValueError("PDP_RUN_FROM y PDP_RUN_TO son obligatorios")
        if to_value <= from_value:
            raise ValueError("PDP_RUN_TO debe ser posterior a PDP_RUN_FROM")

        timeout_seconds = cls._positive_int("PDP_TIMEOUT_SECONDS", 300)
        query_timeout_seconds = cls._positive_int("PDP_QUERY_TIMEOUT_SECONDS", 240)
        company_id = cls._positive_int("PDP_COMPANY_ID", 1)
        lake_url = lake_root or os.getenv("PDP_LAKE_ROOT", "data/lake")

        return cls(
            sql_uri=sql_uri,
            lake_root=Path(lake_url),
            run_from=from_value,
            run_to=to_value,
            company_id=company_id,
            timeout_seconds=timeout_seconds,
            query_timeout_seconds=query_timeout_seconds,
        )

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        return datetime.fromisoformat(normalized)

    @staticmethod
    def _positive_int(name: str, default: int) -> int:
        value = os.getenv(name)
        if value is None:
            return default
        parsed = int(value)
        if parsed <= 0:
            raise ValueError(f"{name} debe ser mayor que cero")
        return parsed
