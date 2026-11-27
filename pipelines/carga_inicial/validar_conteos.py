"""Puerta 1 de la carga inicial: conteos y unicidad de llaves (solo lectura).

1. Filas del Parquet == filas_hoy del manifiesto (36 tablas).
2. Por cada lista a cargar (D7/D8): filas, llaves duplicadas, filas con llave nula o vacia.
   La llave se compara quitando SOLO el relleno izquierdo de espacios (numeros alineados a la
   derecha); no se aplica ningun otro cambio.
3. Si la pk no es unica, propone la llave minima unica con columnas ya existentes en la tabla.

Uso: python -m pipelines.carga_inicial.validar_conteos [--carpeta data/raw/pos_volcado_2026-10-28]
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import polars as pl

RAIZ = Path(__file__).resolve().parents[2]
CARPETA = RAIZ / "data" / "raw" / "pos_volcado_2026-10-28"
PRODUCTOS = RAIZ / "sharepoint" / "productos.json"

# lista -> tabla origen (D7/D8) para las raw_inv_*; las raw_pos_* usan "tabla" de productos.json.
ORIGEN_INV = {
    "raw_inv_almacen": "almacen",
    "raw_inv_unidad": "udsmedida",
    "raw_inv_movimiento_concepto": "conceptos",
    "raw_inv_proveedor": "proveedores",
    "raw_inv_insumo": "insumos",
    "raw_inv_insumo_categoria": "gruposi",
    "raw_inv_compra": "compras",
    "raw_inv_compra_partida": "comprasmovtos",
    "raw_inv_conteo_fisico": "invfisico",
    "raw_inv_conteo_fisico_partida": "invfisicomovtos",
    "raw_inv_movimiento": "movsinv",
}
# Columna de la tabla origen cuando el nombre de la pk de la lista no coincide (D8).
PK_COLUMNA = {
    ("raw_inv_insumo_categoria", "id"): "idgruposi",
    ("raw_inv_unidad", "unidad"): "idunidad",
}
# Excepcion conocida: (tabla, columna) con NULL en todas sus filas.
EXCEPCIONES = {("motivoscancelacion", "idmotivocancela")}


def cargar_listas(ruta: Path = PRODUCTOS) -> list[dict]:
    """[{lista, tabla, pk:[columnas de la tabla origen]}] segun productos.json y D7/D8."""
    prod = json.loads(ruta.read_text(encoding="utf-8"))["productos"]
    out = []
    for p in prod:
        if p["origen"] == "pos":
            tabla = p["tabla"]
        elif p["id"] in ORIGEN_INV:
            tabla = ORIGEN_INV[p["id"]]
        else:
            continue
        pk = [PK_COLUMNA.get((p["id"], k.strip()), k.strip()) for k in p["pk"].split(",")]
        out.append({"lista": p["id"], "tabla": tabla, "pk": pk})
    return out


def normalizar(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """Solo quita el relleno izquierdo (espacios); los nulos se conservan como nulos."""
    return df.select([pl.col(c).str.strip_chars_start(" ").alias(c) for c in cols])


def revisar_llave(df: pl.DataFrame, pk: list[str]) -> dict:
    k = normalizar(df, pk)
    nulas = k.filter(pl.any_horizontal([pl.col(c).is_null() | (pl.col(c) == "") for c in pk]))
    validas = k.filter(~pl.any_horizontal([pl.col(c).is_null() | (pl.col(c) == "") for c in pk]))
    g = validas.group_by(pk).len().filter(pl.col("len") > 1).sort("len", descending=True)
    ejemplos = [
        {"llave": [r[c] for c in pk], "veces": r["len"]} for r in g.head(3).iter_rows(named=True)
    ]
    return {
        "filas": df.height,
        "llaves_duplicadas": g.height,  # llaves distintas repetidas
        "filas_en_duplicados": int(g["len"].sum()) if g.height else 0,
        "ejemplos": ejemplos,
        "llaves_nulas": nulas.height,
    }


def proponer_llave(df: pl.DataFrame, pk: list[str], max_cols: int = 5) -> list[str] | None:
    """Menor combinacion de columnas existentes, sin nulos/vacios, unica. Prefiere incluir la pk."""
    cols = df.columns
    n = df.height
    norm = normalizar(df, cols)
    ok = [c for c in cols if norm[c].null_count() == 0 and (norm[c] == "").sum() == 0]
    for tam in range(1, max_cols + 1):
        cands = [list(c) for c in itertools.combinations(ok, tam)]
        cands.sort(key=lambda c: not set(pk) <= set(c))  # las que contienen la pk primero
        for c in cands:
            if norm.select(c).n_unique() == n:
                return c
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--carpeta", type=Path, default=CARPETA)
    ap.add_argument("--productos", type=Path, default=PRODUCTOS)
    a = ap.parse_args(argv)

    man = json.loads((a.carpeta / "_manifiesto.json").read_text(encoding="utf-8"))
    fallas = 0

    print("== 1. Conteo Parquet vs filas_hoy ==")
    dfs: dict[str, pl.DataFrame] = {}
    for t in man["tablas"]:
        df = pl.read_parquet(a.carpeta / f"{t['tabla']}.parquet")
        dfs[t["tabla"]] = df
        if df.height != t["filas_hoy"]:
            fallas += 1
            print(f"  FALLA {t['tabla']}: parquet {df.height} != filas_hoy {t['filas_hoy']}")
    print(f"  tablas={len(man['tablas'])} discrepancias={fallas}")

    print("== 2. Llaves por lista ==")
    resultados = []
    for it in cargar_listas(a.productos):
        df = dfs[it["tabla"]]
        faltan = [c for c in it["pk"] if c not in df.columns]
        if faltan:
            fallas += 1
            print(f"  FALLA {it['lista']}: columnas de llave ausentes en {it['tabla']}: {faltan}")
            continue
        r = revisar_llave(df, it["pk"])
        exc = (
            r["llaves_nulas"] == r["filas"]
            and len(it["pk"]) == 1
            and (it["tabla"], it["pk"][0]) in EXCEPCIONES
        )
        if exc:
            ver = "EXCEPCION conocida (llave 100% NULL)"
        elif r["llaves_duplicadas"] or r["llaves_nulas"]:
            ver = "FALLA"
            fallas += 1
        else:
            ver = "OK"
        prop = None
        if (r["llaves_duplicadas"] or r["llaves_nulas"]) and not exc:
            prop = proponer_llave(df, it["pk"])
        resultados.append({**it, **r, "veredicto": ver, "propuesta": prop})

    print(f"{'lista':44}{'tabla':22}{'pk':40}{'filas':>7}{'dup':>6}{'nulas':>7}  veredicto")
    for r in resultados:
        print(
            f"{r['lista']:44}{r['tabla']:22}{','.join(r['pk']):40}{r['filas']:>7}"
            f"{r['llaves_duplicadas']:>6}{r['llaves_nulas']:>7}  {r['veredicto']}"
        )
    for r in resultados:
        if r["ejemplos"]:
            print(f"  ejemplos {r['lista']} (filas en duplicados={r['filas_en_duplicados']}): {r['ejemplos']}")
        if r["propuesta"] is not None or r["veredicto"] == "FALLA":
            print(f"  llave minima unica propuesta {r['lista']}: {r['propuesta'] or 'NINGUNA hasta 5 columnas'}")

    print(f"== Resultado: {'RECHAZADO' if fallas else 'APROBADO'} ({fallas} fallas) ==")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
