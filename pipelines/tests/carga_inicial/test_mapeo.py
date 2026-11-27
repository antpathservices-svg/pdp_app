"""Puerta 2: verificacion independiente de mapeo_listas.json y de data/carga/*.jsonl.

Reimplementa la conversion con Decimal y zoneinfo (no usa transformar.py) y la compara
contra el Parquet del volcado. Solo lectura. Se salta si faltan los artefactos locales.
"""

from __future__ import annotations

import json
import random
import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl
import pytest

RAIZ = Path(__file__).resolve().parents[3]
MAPEO = RAIZ / "pipelines" / "carga_inicial" / "mapeo_listas.json"
PRODUCTOS = RAIZ / "sharepoint" / "productos.json"
RAW = RAIZ / "data" / "raw" / "pos_volcado_2026-10-28"
CARGA = RAIZ / "data" / "carga"
TZ = ZoneInfo("America/Matamoros")
MUESTRA = 200
TIPOS_OK = {"texto", "lista", "entero", "decimal", "booleano", "fecha", "fecha-hora"}
EXCEPCIONES_PK = {"raw_pos_venta_motivo_cancelacion"}
SIN_LISTA = {"empresas", "acumuladoinsumos", "costos", "elaborados", "insumosdetalle",
             "insumospresentaciones", "insumospresentacionesdetalle", "movtosalmacen",
             "stockinsumos", "tipoproveedores", "traspasosalmacen"}

pytestmark = pytest.mark.skipif(
    not (MAPEO.is_file() and RAW.is_dir() and CARGA.is_dir()), reason="faltan artefactos locales")

MAPEO_J = json.loads(MAPEO.read_text(encoding="utf-8")) if MAPEO.is_file() else {"listas": {}}
PROD = {p["id"]: p for p in json.loads(PRODUCTOS.read_text(encoding="utf-8"))["productos"]}
LISTAS = list(MAPEO_J["listas"])


def tipos(lista):
    return {a[0]: a[1] for e in PROD[lista]["ent"] for a in e["a"]}


def pk(lista):
    return [k.strip() for k in PROD[lista]["pk"].split(",")]


def leer_jsonl(lista):
    # parse_float=str conserva el literal decimal exacto (nada pasa por float)
    with open(CARGA / f"{lista}.jsonl", encoding="utf-8") as f:
        return [json.loads(l, parse_float=str) for l in f]


def parquet(lista):
    return pl.read_parquet(RAW / f"{MAPEO_J['listas'][lista]['tabla']}.parquet")


# ---------------------------------------------------------------- 1. mapeo vs productos.json
def test_son_25_listas_y_todas_existen_en_productos():
    assert len(LISTAS) == 25
    assert set(MAPEO_J["orden_carga"]) == set(LISTAS)
    assert not [l for l in LISTAS if l not in PROD]


@pytest.mark.parametrize("lista", LISTAS)
def test_columnas_del_mapeo_existen_con_tipo_valido(lista):
    m, t = MAPEO_J["listas"][lista], tipos(lista)
    sin_attr = [a for a in m["columnas"] if a not in t]
    assert not sin_attr, f"atributos que no estan en el producto: {sin_attr}"
    assert all(t[a] in TIPOS_OK for a in m["columnas"])
    if m.get("ordinal"):
        assert t.get(m["ordinal"]) == "entero"
    sin_col = [c for c in m["columnas"].values() if c not in parquet(lista).columns]
    assert not sin_col, f"columnas que no estan en el Parquet: {sin_col}"
    assert all(k in m["columnas"] or k == m.get("ordinal") for k in pk(lista)), "pk sin mapear"


@pytest.mark.parametrize("lista", LISTAS)
def test_tabla_origen_coincide_con_el_producto_pos(lista):
    if PROD[lista]["origen"] == "pos":
        assert MAPEO_J["listas"][lista]["tabla"] == PROD[lista]["tabla"]


def test_empresas_y_tablas_sin_lista_no_se_cargan():
    usadas = [m["tabla"] for m in MAPEO_J["listas"].values()]
    assert "empresas" not in usadas
    assert not (set(usadas) & SIN_LISTA), set(usadas) & SIN_LISTA
    assert len(set(usadas)) == 25
    assert sorted(p.stem for p in CARGA.glob("raw_*.jsonl")) == sorted(LISTAS)


def test_insumo_solo_cuatro_columnas_d8():
    m = MAPEO_J["listas"]["raw_inv_insumo"]
    assert m["columnas"] == {"idinsumo": "idinsumo", "descripcion": "descripcion",
                             "presentacion": "unidad", "idcategoria": "idgruposi"}
    for r in leer_jsonl("raw_inv_insumo"):
        assert set(r["v"]) <= {"idinsumo", "descripcion", "presentacion", "idcategoria"}


@pytest.mark.parametrize("lista", LISTAS)
def test_jsonl_no_trae_atributos_fuera_del_mapeo(lista):
    m = MAPEO_J["listas"][lista]
    permitidos = set(m["columnas"]) | ({m["ordinal"]} if m.get("ordinal") else set())
    vistos = set()
    for r in leer_jsonl(lista):
        vistos |= set(r["v"])
    assert vistos <= permitidos, vistos - permitidos


# ---------------------------------------------------------------- 2. conteos y ordinal
@pytest.mark.parametrize("lista", LISTAS)
def test_conteo_jsonl_igual_a_parquet_y_filas_hoy(lista):
    tabla = MAPEO_J["listas"][lista]["tabla"]
    man = {t["tabla"]: t for t in json.loads((RAW / "_manifiesto.json").read_text(encoding="utf-8"))["tablas"]}
    filas = leer_jsonl(lista)
    n = parquet(lista).height
    assert len(filas) == n == man[tabla]["filas_hoy"]
    assert [r["_ord"] for r in filas] == list(range(1, n + 1))


@pytest.mark.parametrize("lista", ["raw_inv_movimiento", "raw_inv_compra_partida"])
def test_renglon_carga_consecutivo_sin_huecos_ni_repetidos(lista):
    assert pk(lista) == ["renglon_carga"]
    filas = leer_jsonl(lista)
    assert [r["v"]["renglon_carga"] for r in filas] == list(range(1, len(filas) + 1))


# ---------------------------------------------------------------- 3. muestreo contra el Parquet
def esperado(valor, tipo):
    """(presente, valor esperado) segun D8, calculado de forma independiente."""
    if valor is None or valor == "" or (tipo in ("texto", "lista") and valor.strip() == ""):
        return False, None
    if tipo in ("texto", "lista"):
        return True, valor
    v = valor.strip()
    if v == "":
        return False, None
    if tipo == "entero":
        return True, int(Decimal(v))
    if tipo == "decimal":
        return True, Decimal(v)
    if tipo == "booleano":
        assert v in ("0", "1"), v
        return True, v == "1"
    if tipo == "fecha":
        return True, v
    if tipo == "fecha-hora":
        base, _, fr = v.partition(".")
        naive = datetime.strptime(base, "%Y-%m-%d %H:%M:%S").replace(microsecond=int((fr or "0").ljust(6, "0")))
        a = naive.replace(tzinfo=TZ, fold=0)
        if a.astimezone(timezone.utc).astimezone(TZ).replace(tzinfo=None) != naive:
            return "inexistente", None
        u = a.astimezone(timezone.utc)
        return True, u.strftime("%Y-%m-%dT%H:%M:%S.") + f"{u.microsecond // 1000:03d}Z"
    raise AssertionError(tipo)


def comparar(lista, idx):
    m, t = MAPEO_J["listas"][lista], tipos(lista)
    df = parquet(lista)
    filas = leer_jsonl(lista)
    difs = []
    for i in idx:
        fila, pq = filas[i]["v"], df.row(i, named=True)
        for attr, col in m["columnas"].items():
            ok, exp = esperado(pq[col], t[attr])
            got = fila.get(attr)
            if ok == "inexistente":
                if attr in fila:
                    difs.append((i + 1, attr, pq[col], got, "hora inexistente escrita"))
                continue
            if not ok:
                if attr in fila:
                    difs.append((i + 1, attr, pq[col], got, "debia omitirse"))
                continue
            if attr not in fila:
                difs.append((i + 1, attr, pq[col], None, "falta"))
                continue
            tp = t[attr]
            if tp == "decimal":
                dec_src = len(pq[col].strip().lstrip("+-").partition(".")[2])
                if not isinstance(got, str) or Decimal(got) != exp or len(got.partition(".")[2]) != dec_src:
                    difs.append((i + 1, attr, pq[col], got, "decimal distinto o redondeado"))
            elif tp == "entero":
                if not isinstance(got, int) or isinstance(got, bool) or got != exp:
                    difs.append((i + 1, attr, pq[col], got, "entero distinto"))
            elif tp == "booleano":
                if got is not exp:
                    difs.append((i + 1, attr, pq[col], got, "booleano distinto"))
            elif got != exp:
                difs.append((i + 1, attr, pq[col], got, "texto/fecha distinto"))
    return difs


@pytest.mark.parametrize("lista", LISTAS)
def test_muestreo_200_filas_contra_parquet(lista):
    n = parquet(lista).height
    rng = random.Random(20261028)
    idx = list(range(n)) if n <= MUESTRA else sorted(set(rng.sample(range(n), MUESTRA - 2)) | {0, n - 1})
    difs = comparar(lista, idx)
    assert not difs, f"{len(difs)} diferencias; ejemplos: {difs[:3]}"


def test_llaves_con_ceros_a_la_izquierda_intactas():
    pq = pl.read_parquet(RAW / "insumos.parquet")["idinsumo"].to_list()
    js = [r["v"]["idinsumo"] for r in leer_jsonl("raw_inv_insumo")]
    assert js == pq
    assert any(re.match(r"^0\d", x) for x in js)


def test_horas_de_todo_el_volcado_sin_ambiguas_ni_inexistentes():
    """Exhaustivo: cada fecha-hora mapeada se revisa contra los cambios de horario."""
    ambiguas, inexistentes, total, verano, invierno = [], [], 0, 0, 0
    for lista, m in MAPEO_J["listas"].items():
        t = tipos(lista)
        df = parquet(lista)
        for attr, col in m["columnas"].items():
            if t[attr] != "fecha-hora":
                continue
            for v in df[col].drop_nulls().unique().to_list():
                v = v.strip()
                if not v:
                    continue
                total += 1
                naive = datetime.strptime(v.split(".")[0], "%Y-%m-%d %H:%M:%S")
                a, b = naive.replace(tzinfo=TZ, fold=0), naive.replace(tzinfo=TZ, fold=1)
                if a.utcoffset() != b.utcoffset():
                    ambiguas.append((lista, attr, v))
                if a.astimezone(timezone.utc).astimezone(TZ).replace(tzinfo=None) != naive:
                    inexistentes.append((lista, attr, v))
                if a.utcoffset().total_seconds() == -5 * 3600:
                    verano += 1
                else:
                    invierno += 1
    print(f"fechas-hora distintas={total} verano(UTC-5)={verano} invierno(UTC-6)={invierno} "
          f"ambiguas={len(ambiguas)} inexistentes={len(inexistentes)}")
    assert total > 0
    assert not ambiguas, ambiguas[:3]
    assert not inexistentes, inexistentes[:3]


def test_conversion_dst_y_cambios_de_horario_sinteticos():
    assert esperado("2026-07-01 09:21:27.000", "fecha-hora")[1] == "2026-07-01T14:21:27.000Z"  # CDT
    assert esperado("2026-01-15 09:21:27.000", "fecha-hora")[1] == "2026-01-15T15:21:27.000Z"  # CST
    assert esperado("2026-03-08 02:30:00.000", "fecha-hora")[0] == "inexistente"
    # 2026-11-01 01:30 existe dos veces: primera ocurrencia (CDT = UTC-5), como declara D8
    assert esperado("2026-11-01 01:30:00.000", "fecha-hora")[1] == "2026-11-01T06:30:00.000Z"


# ---------------------------------------------------------------- 4. llaves unicas
@pytest.mark.parametrize("lista", LISTAS)
def test_llaves_unicas_segun_pk_de_productos(lista):
    claves = pk(lista)
    filas = leer_jsonl(lista)
    if lista in EXCEPCIONES_PK:
        assert len(filas) == 4
        assert all("idmotivocancela" not in r["v"] for r in filas)
        return
    llaves = []
    for r in filas:
        faltan = [k for k in claves if k not in r["v"]]
        assert not faltan, f"fila {r['_ord']} sin {faltan}"
        llaves.append(tuple(r["v"][k] for k in claves))
    assert len(set(llaves)) == len(llaves), f"{len(llaves) - len(set(llaves))} llaves repetidas"


# ---------------------------------------------------------------- 5. documentacion y guardas
def test_doc_y_cargador_describen_guarda_bitacora_reanudacion_y_piloto():
    doc = (RAIZ / "docs" / "carga-inicial.md").read_text(encoding="utf-8").lower()
    ps1 = (RAIZ / "pipelines" / "carga_inicial" / "cargar_sharepoint.ps1").read_text(encoding="utf-8")
    for clave in ("guarda previa", "estado.json", "bit", "reanudaci", "piloto", "dry-run", "-forzar", "corrida_cerrada"):
        assert clave in doc, clave
    for clave in ("ItemCount", "estado.json", "-DryRun", "-Piloto", ".carga.lock", "corrida_cerrada"):
        assert clave in ps1, clave
    assert MAPEO_J["piloto"]["listas"] == ["raw_pos_venta_area", "raw_pos_venta_cuenta"]
    assert MAPEO_J["piloto"]["limite_filas"] == {"raw_pos_venta_cuenta": 200}
