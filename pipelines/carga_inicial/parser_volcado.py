"""Parser del volcado de texto de SQL Server (salida de bronze_snapshot_full.sql).

Formato: un bloque resumen (orden, tabla, filas_hoy, filas_contrato) y 36 bloques de
tabla en el orden del contrato. Cada bloque: encabezado, linea de guiones (un tramo por
columna, separados por un espacio; el ancho del tramo es el ancho de la columna), filas
de ancho fijo y una linea en blanco.

Decodificacion de ancho fijo (NO es TRIM): cada fila se corta por posicion usando los
anchos de la linea de guiones. Solo se quita el relleno de la derecha que SQL Server
agrego para completar el ancho; los espacios iniciales se conservan (p. ej. los numeros
alineados a la derecha y las llaves con espacios que Bronze debe copiar fielmente).
Todas las columnas quedan como string. El literal NULL (relleno quitado) pasa a nulo; un
valor en blanco pasa a cadena vacia. Limitacion: una cadena real 'NULL' es
indistinguible de un nulo en este formato.

filas_hoy se lee en tiempo de ejecucion del bloque resumen del propio volcado (no se
copia en el contrato); filas_contrato del resumen se contrasta con el contrato.

Se lee en streaming, linea a linea (solo el DataFrame por tabla vive en memoria).
Lectura unicamente; el archivo fuente nunca se modifica.
"""

from __future__ import annotations

import argparse
import codecs
import hashlib
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from .contrato_volcado import COLUMNAS, FILAS_CONTRATO, ORDEN

CHUNK = 1 << 20
ENIE = "Ñ"  # N con tilde
E_AGUDA = "É"  # E con acento
A_TILDE = "Ã"  # A con tilde: marca de mojibake de UTF-8 leido como cp1252


class VolcadoError(Exception):
    """El volcado no cumple el contrato."""


def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def detectar_codificacion(ruta: Path) -> tuple[str, dict]:
    """BOM primero; luego UTF-8 estricto en streaming; si falla, cp1252.

    Verifica con N-tilde/E-acento: cuenta apariciones y rechaza mojibake.
    Devuelve (codificacion, evidencia).
    """
    with open(ruta, "rb") as f:
        inicio = f.read(4)
    bom = None
    if inicio.startswith(codecs.BOM_UTF8):
        bom, cand = "utf-8-sig", ["utf-8-sig"]
    elif inicio.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        bom, cand = "utf-16", ["utf-16"]
    else:
        cand = ["utf-8", "cp1252"]
    ultimo_error = None
    for enc in cand:
        dec = codecs.getincrementaldecoder(enc)(errors="strict")
        n_enie = n_e = n_moji = 0
        try:
            with open(ruta, "rb") as f:
                while chunk := f.read(CHUNK):
                    t = dec.decode(chunk)
                    n_enie += t.count(ENIE)
                    n_e += t.count(E_AGUDA)
                    n_moji += t.count(A_TILDE)
            dec.decode(b"", final=True)
        except UnicodeDecodeError as e:
            ultimo_error = e
            continue
        if enc == "cp1252" and n_moji:
            raise VolcadoError("Codificacion ambigua: cp1252 produce mojibake de UTF-8.")
        return enc, {"bom": bom, "n_tilde": n_enie, "e_acento": n_e, "mojibake": n_moji}
    raise VolcadoError(f"No se pudo decodificar el volcado ({ultimo_error}).")


def _tramos(guiones: str) -> list[tuple[int, int]]:
    """Posiciones (ini, fin) de cada columna a partir de la linea de guiones."""
    if not guiones or set(guiones) - {"-", " "}:
        raise VolcadoError(f"Linea de guiones invalida: {guiones[:80]!r}")
    tramos, i, n = [], 0, len(guiones)
    while i < n:
        if guiones[i] != "-":
            raise VolcadoError("Separador de columnas inesperado en la linea de guiones.")
        j = i
        while j < n and guiones[j] == "-":
            j += 1
        tramos.append((i, j))
        i = j + 1  # salta el espacio separador
    return tramos


class _Lector:
    def __init__(self, f):
        self.f = f
        self.n = 0

    def linea(self) -> str | None:
        raw = self.f.readline()
        if raw == "":
            return None
        self.n += 1
        raw = raw[:-1] if raw.endswith("\n") else raw
        return raw[:-1] if raw.endswith("\r") else raw


def _leer_resumen(lec: _Lector) -> dict[str, dict]:
    enc = lec.linea()
    if enc is None or enc.split() != ["orden", "tabla", "filas_hoy", "filas_contrato"]:
        raise VolcadoError(f"Se esperaba el bloque resumen; encabezado: {enc!r}")
    lec.linea()  # guiones
    resumen: dict[str, dict] = {}
    while (l := lec.linea()) is not None and l.strip():
        p = l.split()
        if len(p) != 4 or not (p[2].isdigit() and p[3].isdigit()):
            raise VolcadoError(f"Fila de resumen invalida (linea {lec.n}): {l!r}")
        resumen[p[1]] = {"orden": p[0], "filas_hoy": int(p[2]), "filas_contrato": int(p[3])}
    return resumen


def leer_resumen(ruta: str | Path) -> dict[str, dict]:
    """filas_hoy y filas_contrato del bloque resumen (leidos en tiempo de ejecucion)."""
    enc, _ = detectar_codificacion(Path(ruta))
    with open(ruta, encoding=enc, newline="\n") as f:
        return _leer_resumen(_Lector(f))


def _leer(ruta: Path, enc: str, stats: dict | None = None) -> dict[str, pl.DataFrame]:
    out: dict[str, pl.DataFrame] = {}
    anomalias = stats["anomalias"] if stats is not None else []
    with open(ruta, encoding=enc, newline="\n") as f:
        lec = _Lector(f)
        resumen = _leer_resumen(lec)
        if list(resumen) != ORDEN:
            raise VolcadoError(f"Tablas/orden del resumen no coinciden con el contrato: {list(resumen)}")
        for t, r in resumen.items():
            if r["filas_contrato"] != FILAS_CONTRATO[t]:
                raise VolcadoError(
                    f"{t}: filas_contrato del resumen {r['filas_contrato']} != contrato {FILAS_CONTRATO[t]}"
                )
        for tabla in ORDEN:
            t0 = time.perf_counter()
            enc_l, gui = lec.linea(), lec.linea()
            if enc_l is None or gui is None:
                raise VolcadoError(f"{tabla}: fin de archivo antes del bloque.")
            tramos = _tramos(gui)
            ancho = len(gui)
            if len(enc_l.rstrip()) > ancho:
                raise VolcadoError(f"{tabla}: el encabezado excede el ancho de la linea de guiones.")
            nombres = [enc_l[a:b].rstrip() for a, b in tramos]
            if nombres != list(COLUMNAS[tabla]):
                raise VolcadoError(f"{tabla}: columnas {nombres} != contrato {list(COLUMNAS[tabla])}")
            cols: list[list[str | None]] = [[] for _ in tramos]
            filas = cortas = sospechosas = 0
            while (l := lec.linea()) is not None and l != "":
                if len(l) > ancho:
                    raise VolcadoError(
                        f"{tabla}: fila en linea {lec.n} excede el ancho ({len(l)} > {ancho}); "
                        "posible salto de linea incrustado o columna desalineada."
                    )
                if len(l) < ancho:
                    # SQL Server no rellena la ultima columna: es esperado (relleno final recortado).
                    # Solo es sospechosa (posible truncamiento) si la fila no llega al inicio de la ultima columna.
                    cortas += 1
                    if len(l) < tramos[-1][0] - 1:
                        sospechosas += 1
                        if sospechosas <= 5:
                            anomalias.append(
                                f"{tabla}: fila posiblemente truncada en linea {lec.n} "
                                f"({len(l)} chars; la ultima columna inicia en {tramos[-1][0]})"
                            )
                    l = l.ljust(ancho)
                for c, (a, b) in zip(cols, tramos):
                    v = l[a:b].rstrip()  # solo relleno derecho (decodificacion de ancho fijo)
                    c.append(None if v == "NULL" else v)
                filas += 1
            esperado = resumen[tabla]["filas_hoy"]
            if filas != esperado:
                raise VolcadoError(f"{tabla}: {filas} filas leidas != filas_hoy {esperado}")
            out[tabla] = pl.DataFrame(dict(zip(nombres, cols)), schema={n: pl.String for n in nombres})
            if stats is not None:
                stats["tablas"][tabla] = {
                    "filas_hoy": esperado,
                    "filas_relleno_final_recortado": cortas,
                    "filas_sospechosas": sospechosas,
                    "segundos": round(time.perf_counter() - t0, 3),
                }
        while (extra := lec.linea()) is not None and not extra.strip():
            pass  # lineas en blanco finales
        if extra is not None and extra.startswith("Hora de finalizaci"):
            # pie que agrega SSMS ("Hora de finalizacion: <iso>"); se registra, no es dato
            if stats is not None:
                stats["pie"] = extra
            while (extra := lec.linea()) is not None and not extra.strip():
                pass
        if extra is not None:
            raise VolcadoError(f"Contenido inesperado tras la tabla 36 (linea {lec.n}): {extra[:80]!r}")
    return out


def leer_volcado(ruta: str | Path) -> dict[str, pl.DataFrame]:
    """Devuelve {tabla: DataFrame} (todo string, NULL -> nulo). Falla si algo no cuadra."""
    ruta = Path(ruta)
    enc, _ = detectar_codificacion(ruta)
    return _leer(ruta, enc)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Volcado SQL Server -> Parquet por tabla (raw, append-only).")
    ap.add_argument("--volcado", required=True, type=Path)
    ap.add_argument("--salida", required=True, type=Path)
    ap.add_argument("--forzar", action="store_true", help="reemplaza la carpeta de salida si existe")
    a = ap.parse_args(argv)

    if a.salida.exists() and not a.forzar:
        print(f"ERROR: {a.salida} ya existe (raw es append-only). Usa --forzar para reemplazar.", file=sys.stderr)
        return 2
    t0 = time.perf_counter()
    try:
        sha = _sha256(a.volcado)
        enc, evid = detectar_codificacion(a.volcado)
        stats: dict = {"tablas": {}, "anomalias": []}
        dfs = _leer(a.volcado, enc, stats)
        if _sha256(a.volcado) != sha:
            raise VolcadoError("El sha256 del fuente cambio durante la lectura.")
    except VolcadoError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    tmp = a.salida.with_name(a.salida.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    for t, df in dfs.items():
        df.write_parquet(tmp / f"{t}.parquet")
    manifiesto = {
        "fuente": a.volcado.name,
        "sha256_fuente": sha,
        "codificacion": enc,
        "evidencia_codificacion": evid,
        "generado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duracion_s": round(time.perf_counter() - t0, 2),
        "pie_fuente": stats.get("pie"),
        "anomalias": stats["anomalias"],
        "tablas": [
            {"tabla": t, "columnas": df.columns, "filas": df.height, **stats["tablas"][t]}
            for t, df in dfs.items()
        ],
    }
    (tmp / "_manifiesto.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    if a.salida.exists():
        shutil.rmtree(a.salida)
    tmp.rename(a.salida)
    print(f"OK {len(dfs)} tablas, codificacion={enc}, sha256={sha}, {manifiesto['duracion_s']} s -> {a.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
