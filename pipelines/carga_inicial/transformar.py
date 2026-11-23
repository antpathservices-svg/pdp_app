"""Transforma los Parquet del volcado a jsonl tipado para cargar a SharePoint (D7/D8).

Copia fiel: solo la decodificacion imprescindible para SharePoint.
- texto: tal cual (las llaves tipo 01001 siguen siendo texto). "" y NULL se omiten.
- entero/decimal: se quita el relleno, punto decimal, sin redondeo. El decimal conserva sus
  digitos como literal numerico (no pasa por float).
- booleano: 0/1 -> false/true.
- fecha-hora: 'aaaa-mm-dd hh:mm:ss.fff' en TZ_POS (America/Matamoros, con horario de verano)
  -> UTC ISO 8601. Horas ambiguas (cambio de horario de otono) = primera ocurrencia.
- Un valor que no se puede convertir NO se escribe y se reporta con ejemplos.

Salida: <RUTA_CARGA>/<lista>.jsonl, una fila por linea, en el orden del archivo:
    {"_ord": 1, "v": {"folio": 442431, "fecha": "2026-07-01T15:21:27.000Z", ...}}
`_ord` es el ordinal 1-based; si el mapeo declara `ordinal`, tambien va como atributo.
Escribe _resumen_transformacion.json con el reporte por lista. Es idempotente: reescribe
los jsonl (escritura temporal + renombrado), nunca toca el Parquet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import polars as pl

try:  # ejecucion como modulo o como script
    from . import config as cfg
except ImportError:  # pragma: no cover
    import config as cfg  # type: ignore

EJEMPLOS = 5
RE_ENTERO = r"^[+-]?\d+(\.0+)?$"
RE_DECIMAL = r"^[+-]?(\d+(\.\d+)?|\.\d+)$"
RE_FECHAHORA = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d{1,3})?$"
RE_FECHA = r"^\d{4}-\d{2}-\d{2}$"


def _tipos_producto(ruta: Path) -> dict[str, dict[str, str]]:
    d = json.loads(ruta.read_text(encoding="utf-8"))
    out: dict[str, dict[str, str]] = {}
    for p in d["productos"]:
        out[p["id"]] = {a[0]: a[1] for e in p["ent"] for a in e["a"]}
    return out


def _sel(expr: pl.Expr) -> pl.Series:
    return pl.select(expr).to_series()


def _convertir(s: pl.Series, tipo: str, tz: str) -> tuple[pl.Series, pl.Series, dict]:
    """Devuelve (valor tipado, mascara de error, avisos). Vacios -> nulo sin error."""
    avisos: dict[str, int] = {}
    noerr = pl.Series([False] * len(s))
    if tipo in ("texto", "lista"):
        vacio = (s.is_null() | (s == "")).fill_null(True)
        solo_esp = (~vacio) & (s.str.strip_chars() == "")
        if solo_esp.sum():
            avisos["solo_espacios_omitido"] = int(solo_esp.sum())
        espacios = (~vacio) & (s != s.str.strip_chars()) & ~solo_esp
        if espacios.sum():
            avisos["espacios_en_extremos_conservados"] = int(espacios.sum())
        val = s.set(vacio | solo_esp, None)
        return val, noerr, avisos

    t = s.str.strip_chars()
    vacio = (t.is_null() | (t == "")).fill_null(True)
    if tipo == "entero":
        ok = t.str.contains(RE_ENTERO).fill_null(False)
        limpio = t.str.replace(r"^\+", "").str.replace(r"\.0+$", "")
        val = limpio.cast(pl.Int64, strict=False)
        err = (~vacio) & (~ok | val.is_null())
        return val.set(err | vacio, None), err, avisos
    if tipo == "decimal":
        ok = t.str.contains(RE_DECIMAL).fill_null(False)
        lit = (
            t.str.replace(r"^\+", "")
            .str.replace(r"^(-?)\.", "${1}0.")
            .str.replace(r"^(-?)0+(\d)", "${1}${2}")
        )
        cifras = t.str.replace_all(r"[^0-9]", "").str.replace(r"^0+", "").str.len_chars()
        largas = ok & (cifras > 15)
        if largas.sum():
            avisos["mas_de_15_cifras_significativas"] = int(largas.sum())
        err = (~vacio) & ~ok
        return lit.set(err | vacio, None), err, avisos
    if tipo == "booleano":
        err = (~vacio) & ~t.is_in(["0", "1"]).fill_null(False)
        val = pl.Series([None if (e or v) else (x == "1") for x, e, v in zip(t, err, vacio)], dtype=pl.Boolean)
        return val, err, avisos
    if tipo == "fecha":
        ok = t.str.contains(RE_FECHA).fill_null(False)
        err = (~vacio) & ~ok
        return t.set(err | vacio, None), err, avisos
    if tipo == "fecha-hora":
        ok = t.str.contains(RE_FECHAHORA).fill_null(False)
        # Normaliza a 3 decimales para parsear con un solo formato
        base = t.set(~ok, None)
        norm = pl.Series([
            None if x is None else (x + ".000" if "." not in x else (x.split(".")[0] + "." + x.split(".")[1].ljust(3, "0")))
            for x in base
        ], dtype=pl.Utf8)
        naive = norm.str.to_datetime("%Y-%m-%d %H:%M:%S%.f", strict=False)
        a = naive.dt.replace_time_zone(tz, ambiguous="earliest", non_existent="null")
        b = naive.dt.replace_time_zone(tz, ambiguous="latest", non_existent="null")
        amb = (a.dt.epoch("us") != b.dt.epoch("us")).fill_null(False)
        if amb.sum():
            avisos["hora_ambigua_primera_ocurrencia"] = int(amb.sum())
        utc = a.dt.convert_time_zone("UTC")
        err = (~vacio) & (~ok | utc.is_null())
        txt = utc.dt.strftime("%Y-%m-%dT%H:%M:%S%.3fZ")
        return txt.set(err | vacio, None), err, avisos
    raise ValueError(f"tipo no soportado: {tipo}")


def _lit(v, tipo: str) -> str:
    if tipo == "booleano":
        return "true" if v else "false"
    if tipo == "entero":
        return str(v)
    if tipo == "decimal":
        return v
    return json.dumps(v, ensure_ascii=False)


def transformar_lista(nombre: str, m: dict, tipos: dict[str, str], c: cfg.Config) -> dict:
    t0 = time.perf_counter()
    ruta = c.ruta_raw / f"{m['tabla']}.parquet"
    mapa: dict[str, str] = m["columnas"]
    df = pl.read_parquet(ruta)
    n = df.height
    atributos = list(tipos)
    rep = {
        "lista": nombre, "tabla": m["tabla"], "filas_parquet": n,
        "columnas_lista": len(atributos), "columnas_mapeadas": len(mapa),
        "errores": {}, "avisos": {},
    }
    cols: list[tuple[str, str, pl.Series]] = []
    sin_dato, omitidos = [], {}
    indexado = df.with_row_index("o", offset=1)
    for attr, col in mapa.items():
        tipo = tipos[attr]
        val, err, avisos = _convertir(df[col], tipo, c.tz_pos)
        if err.sum():
            ej = indexado.filter(err)
            rep["errores"][attr] = {
                "columna_parquet": col, "tipo": tipo, "n": int(err.sum()),
                "ejemplos": [{"ordinal": r["o"], "valor": r[col]} for r in ej.head(EJEMPLOS).to_dicts()],
            }
        if avisos:
            rep["avisos"][attr] = avisos
        n_con = int(val.is_not_null().sum())
        omitidos[attr] = n - n_con
        if n_con == 0:
            sin_dato.append(attr)
        cols.append((attr, tipo, val))
    if m.get("ordinal"):
        cols.append((m["ordinal"], tipos.get(m["ordinal"], "entero"), pl.Series(range(1, n + 1), dtype=pl.Int64)))
    con_dato = [a for a, _, v in cols if v.is_not_null().any()]
    rep["columnas_con_dato"] = con_dato
    rep["columnas_sin_mapeo"] = [a for a in atributos if a not in mapa and a != m.get("ordinal")]
    rep["columnas_mapeadas_sin_dato"] = sin_dato
    rep["columnas_lista_sin_dato"] = [a for a in atributos if a not in con_dato]
    rep["columnas_parquet_no_cargadas"] = [x for x in df.columns if x not in mapa.values()]
    rep["valores_omitidos_por_columna"] = {a: k for a, k in omitidos.items() if k}

    claves = [json.dumps(a, ensure_ascii=False) for a, _, _ in cols]
    tps = [t for _, t, _ in cols]
    listas = [v.to_list() for _, _, v in cols]
    destino = c.ruta_carga / f"{nombre}.jsonl"
    tmp = destino.with_suffix(".jsonl.tmp")
    vacias = 0
    h = hashlib.sha256()
    with open(tmp, "wb") as f:
        for i in range(n):
            partes = [
                f"{claves[j]}:{_lit(col[i], tps[j])}"
                for j, col in enumerate(listas) if col[i] is not None
            ]
            if not partes:
                vacias += 1
            linea = (f'{{"_ord":{i + 1},"v":{{' + ",".join(partes) + "}}\n").encode("utf-8")
            h.update(linea)
            f.write(linea)
    tmp.replace(destino)
    rep["filas_jsonl"] = n
    rep["filas_sin_ningun_dato"] = vacias
    rep["sha256_jsonl"] = h.hexdigest()
    rep["segundos"] = round(time.perf_counter() - t0, 2)
    return rep


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Parquet del volcado -> jsonl tipado por lista de SharePoint.")
    ap.add_argument("--listas", nargs="*", help="nombres de lista (por defecto todas)")
    ap.add_argument("--env", type=Path, help="ruta del .env")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    c = cfg.cargar(a.env)
    mapeo = json.loads(c.mapeo.read_text(encoding="utf-8"))
    tipos = _tipos_producto(c.productos)
    c.ruta_carga.mkdir(parents=True, exist_ok=True)
    nombres = [n for n in mapeo["orden_carga"] if not a.listas or n in a.listas]
    if a.listas:
        faltan = set(a.listas) - set(nombres)
        if faltan:
            print(f"Listas sin mapeo: {sorted(faltan)}", file=sys.stderr)
            return 2
    reps, hay_errores = [], False
    print(f"{'lista':44}{'filas':>8}{'mapeadas':>10}{'con_dato':>10}{'lista':>7}{'errores':>9}")
    for nombre in nombres:
        r = transformar_lista(nombre, mapeo["listas"][nombre], tipos[nombre], c)
        reps.append(r)
        ne = sum(e["n"] for e in r["errores"].values())
        hay_errores |= ne > 0
        print(f"{nombre:44}{r['filas_jsonl']:>8}{r['columnas_mapeadas']:>10}"
              f"{len(r['columnas_con_dato']):>10}{r['columnas_lista']:>7}{ne:>9}")
    ruta_res = c.ruta_carga / "_resumen_transformacion.json"
    previo = {}
    if a.listas and ruta_res.is_file():
        previo = {x["lista"]: x for x in json.loads(ruta_res.read_text(encoding="utf-8"))["listas"]}
    for r in reps:
        previo[r["lista"]] = r
    orden = {n: i for i, n in enumerate(mapeo["orden_carga"])}
    resumen = {
        "generado_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tz_pos": c.tz_pos, "ruta_raw": str(c.ruta_raw),
        "listas": sorted(previo.values(), key=lambda x: orden[x["lista"]]),
    }
    tmp = ruta_res.with_suffix(".tmp")
    tmp.write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(ruta_res)
    for r in reps:
        if r["errores"] or r["avisos"]:
            print(f"\n[{r['lista']}]")
            for attr, e in r["errores"].items():
                print(f"  ERROR {attr} ({e['tipo']}, <- {e['columna_parquet']}): {e['n']} valores. Ejemplos: {e['ejemplos']}")
            for attr, av in r["avisos"].items():
                print(f"  aviso {attr}: {av}")
    print(f"\nResumen: {ruta_res}")
    return 1 if hay_errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
