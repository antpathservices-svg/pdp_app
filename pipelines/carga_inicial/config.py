"""Configuracion unica de la carga inicial (D7/D8).

Orden de precedencia: variables de entorno > archivo .env > valores por defecto.
Sin secretos: SITE_URL y CLIENT_ID no lo son; la autenticacion es interactiva.
Las rutas relativas se resuelven contra la raiz del repositorio.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DIR_CARGA = Path(__file__).resolve().parent

DEFECTOS = {
    "SITE_URL": "",
    "CLIENT_ID": "",
    "TZ_POS": "America/Matamoros",
    "RUTA_VOLCADO": "data/raw/resultado contrato bronze.txt",
    "RUTA_RAW": "data/raw/pos_volcado_2026-10-28",
    "RUTA_CARGA": "data/carga",
    "TAMANO_LOTE": "100",
    "PAUSA_ENTRE_LOTES": "1",
}


def _leer_env(ruta: Path) -> dict[str, str]:
    datos: dict[str, str] = {}
    if not ruta.is_file():
        return datos
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, v = linea.split("=", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        datos[k.strip()] = v
    return datos


def _ruta(valor: str) -> Path:
    p = Path(valor)
    return p if p.is_absolute() else RAIZ / p


@dataclass(frozen=True)
class Config:
    site_url: str
    client_id: str
    tz_pos: str
    ruta_volcado: Path
    ruta_raw: Path
    ruta_carga: Path
    tamano_lote: int
    pausa_entre_lotes: float
    mapeo: Path
    productos: Path


def cargar(env_path: Path | None = None) -> Config:
    vals = dict(DEFECTOS)
    vals.update(_leer_env(env_path or RAIZ / ".env"))
    for k in DEFECTOS:
        if os.environ.get(k):
            vals[k] = os.environ[k]
    lote = int(vals["TAMANO_LOTE"])
    if not 1 <= lote <= 1000:
        raise ValueError(f"TAMANO_LOTE fuera de rango: {lote}")
    return Config(
        site_url=vals["SITE_URL"],
        client_id=vals["CLIENT_ID"],
        tz_pos=vals["TZ_POS"],
        ruta_volcado=_ruta(vals["RUTA_VOLCADO"]),
        ruta_raw=_ruta(vals["RUTA_RAW"]),
        ruta_carga=_ruta(vals["RUTA_CARGA"]),
        tamano_lote=lote,
        pausa_entre_lotes=float(vals["PAUSA_ENTRE_LOTES"]),
        mapeo=DIR_CARGA / "mapeo_listas.json",
        productos=RAIZ / "sharepoint" / "productos.json",
    )
