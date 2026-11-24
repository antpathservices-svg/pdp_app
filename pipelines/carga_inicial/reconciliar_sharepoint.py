"""Puerta 3: reconciliacion de lo cargado en SharePoint contra data/carga/*.jsonl (solo lectura).

No abre sesion ni toca el sitio. Trabaja sobre una exportacion de lectura de cada lista
(`<exportacion>/<lista>.json`: arreglo de objetos con los valores de los campos por nombre
interno, p. ej. con PnP: Get-PnPListItem -List <lista> -PageSize 500 -Fields ... |
ForEach { $_.FieldValues } | ConvertTo-Json). Opcionalmente `<exportacion>/_conteos.json`
con {"<lista>": ItemCount}.

Comprueba por lista:
  - filas exportadas == filas del jsonl (== ItemCount si se entrega);
  - llaves (pk de productos.json) sin repetidos ni faltantes frente al jsonl;
  - muestreo de hasta N filas (por llave): valores iguales al jsonl (numeros sin redondeo
    mas alla de la precision doble de SharePoint, fechas UTC, booleanos);
  - sin filas de mas ni de menos (duplicados por reintentos de lote).
El nombre de un campo se acepta como `attr`, `attr_raw` o la forma codificada que use el
sitio (`_x0063_` etc.) si se pasa en --alias; la comparacion ignora mayusculas.

Uso:
  python -m pipelines.carga_inicial.reconciliar_sharepoint --exportacion <carpeta> [--listas a b] [--muestra 200]
Sale con 1 si hay alguna diferencia.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CARGA = RAIZ / "data" / "carga"
PRODUCTOS = RAIZ / "sharepoint" / "productos.json"
MAPEO = Path(__file__).with_name("mapeo_listas.json")
EXCEPCIONES_PK = {"raw_pos_venta_motivo_cancelacion"}


def _vacio(v) -> bool:
    """Regla D8: nulo, "" y, para Si/No, False equivalen a vacio.

    SharePoint no distingue NULL de vacio ni de 0 en Si/No: un booleano omitido en el origen
    llega como False y no cuenta como diferencia.
    """
    return v is None or v == "" or v is False


def _k(v) -> str:
    """Valor de llave comparable: SharePoint devuelve los numeros como double (442431.0)."""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _norm(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        k = k.lower()
        out[k] = v
        if k.endswith("_raw"):
            out.setdefault(k[:-4], v)
    return out


def _igual(esp, got) -> bool:
    if esp is None:
        return got in (None, "")
    if isinstance(esp, bool):
        return got is esp or got == int(esp) or str(got).lower() in (("true", "1") if esp else ("false", "0"))
    if isinstance(esp, int):
        try:
            return int(Decimal(str(got))) == esp and Decimal(str(got)) == esp
        except Exception:
            return False
    if isinstance(esp, str) and esp.lstrip("-")[:1].isdigit() and "." in esp:
        try:  # decimal literal; SharePoint guarda doble
            return math.isclose(float(esp), float(got), rel_tol=1e-12, abs_tol=0.0)
        except (TypeError, ValueError):
            pass
    if isinstance(esp, str) and esp.endswith("Z") and isinstance(got, str):
        return got.rstrip("Z")[:19] == esp.rstrip("Z")[:19]
    return esp == got


def reconciliar(lista: str, carpeta: Path, pk: list[str], muestra: int, conteos: dict) -> dict:
    jl = [json.loads(l, parse_float=str) for l in open(CARGA / f"{lista}.jsonl", encoding="utf-8")]
    ruta = carpeta / f"{lista}.json"
    res = {"lista": lista, "filas_jsonl": len(jl), "problemas": []}
    if not ruta.is_file():
        res["problemas"].append("sin exportacion")
        return res
    sp = [_norm(r) for r in json.loads(ruta.read_text(encoding="utf-8"))]
    res["filas_sharepoint"] = len(sp)
    if len(sp) != len(jl):
        res["problemas"].append(f"filas {len(sp)} != jsonl {len(jl)}")
    if lista in conteos and conteos[lista] != len(jl):
        res["problemas"].append(f"ItemCount {conteos[lista]} != jsonl {len(jl)}")
    sin_llave = lista in EXCEPCIONES_PK
    if not sin_llave:
        def llave(d):
            return tuple(_k(d.get(k.lower())) for k in pk)
        idx: dict = {}
        for r in sp:
            idx.setdefault(llave(r), []).append(r)
        dup = {k: len(v) for k, v in idx.items() if len(v) > 1}
        if dup:
            res["problemas"].append(f"{len(dup)} llaves repetidas, ej. {list(dup.items())[:3]}")
        esperadas = {tuple(_k(r["v"].get(k)) for k in pk) for r in jl}
        faltan, sobran = esperadas - set(idx), set(idx) - esperadas
        if faltan:
            res["problemas"].append(f"{len(faltan)} llaves faltantes, ej. {sorted(faltan)[:3]}")
        if sobran:
            res["problemas"].append(f"{len(sobran)} llaves de mas, ej. {sorted(sobran)[:3]}")
        rng = random.Random(1)
        n = len(jl)
        pos = list(range(n)) if n <= muestra else sorted(set(rng.sample(range(n), muestra - 2)) | {0, n - 1})
        difs = []
        for i in pos:
            esp = jl[i]["v"]
            reales = idx.get(tuple(_k(esp.get(k)) for k in pk))
            if not reales:
                continue
            got = reales[0]
            for attr, v in esp.items():
                if not _igual(v, got.get(attr.lower())):
                    difs.append({"ord": jl[i]["_ord"], "attr": attr, "esperado": v, "sharepoint": got.get(attr.lower())})
            # atributos omitidos en el jsonl (NULL o vacio en el origen) deben quedar vacios en el sitio
            for attr, v in got.items():
                if attr in esp or attr in ("_id",) or attr.endswith("_raw"):
                    continue
                if not _vacio(v):
                    difs.append({"ord": jl[i]["_ord"], "attr": attr, "esperado": "(omitido)", "sharepoint": v})
        res["muestreadas"] = len(pos)
        if difs:
            res["problemas"].append(f"{len(difs)} diferencias de valor, ej. {difs[:3]}")
    elif sin_llave:
        # sin llave utilizable (4 filas): se compara el conjunto de filas completo
        def firma(d):
            return json.dumps({k: (_k(v)) for k, v in sorted(d.items()) if not _vacio(v)}, sort_keys=True)
        esp = sorted(firma({k.lower(): v for k, v in r["v"].items()}) for r in jl)
        got = sorted(firma({k: v for k, v in r.items() if k != "_id" and not k.endswith("_raw")}) for r in sp)
        res["muestreadas"] = len(jl)
        if esp != got:
            res["problemas"].append(f"contenido distinto en lista sin llave: {esp[:2]} vs {got[:2]}")
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exportacion", required=True, type=Path)
    ap.add_argument("--listas", nargs="*")
    ap.add_argument("--muestra", type=int, default=200)
    a = ap.parse_args(argv)
    prod = {p["id"]: p for p in json.loads(PRODUCTOS.read_text(encoding="utf-8"))["productos"]}
    orden = json.loads(MAPEO.read_text(encoding="utf-8"))["orden_carga"]
    listas = [l for l in orden if not a.listas or l in a.listas]
    cf = a.exportacion / "_conteos.json"
    conteos = json.loads(cf.read_text(encoding="utf-8")) if cf.is_file() else {}
    malas = 0
    print(f"{'lista':44}{'jsonl':>8}{'sharepoint':>12}  resultado")
    for l in listas:
        pk = [k.strip() for k in prod[l]["pk"].split(",")]
        r = reconciliar(l, a.exportacion, pk, a.muestra, conteos)
        malas += bool(r["problemas"])
        print(f"{l:44}{r['filas_jsonl']:>8}{r.get('filas_sharepoint', '-'):>12}  {'OK' if not r['problemas'] else 'FALLA'}")
        for p in r["problemas"]:
            print(f"    - {p}")
    print(f"== {'RECHAZADO' if malas else 'APROBADO'} ({malas} listas con problemas) ==")
    return 1 if malas else 0


if __name__ == "__main__":
    sys.exit(main())
