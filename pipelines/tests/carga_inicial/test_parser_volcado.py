"""Pruebas del parser del volcado sobre datos 100 % sinteticos (sin datos del POS).

El parser valida contra el contrato real de 36 tablas; aqui se sustituye por un contrato
de 3 tablas ficticias con monkeypatch. El volcado minimo vive en datos_sinteticos/.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from pipelines.carga_inicial import parser_volcado as pv

DATOS = Path(__file__).parent / "datos_sinteticos"
ORDEN = ["ta", "tb", "tc"]
COLUMNAS = {"ta": ["id", "nombre", "monto"], "tb": ["solo"], "tc": ["k", "v"]}
FILAS = {"ta": 4, "tb": 2, "tc": 1}


def bloque(columnas, filas, anchos):
    """Texto de un bloque ancho fijo: encabezado, guiones, filas (relleno derecho salvo ultima)."""
    def fmt(vals):
        return " ".join(str(v).ljust(w) for v, w in zip(vals, anchos)).rstrip()
    lineas = [" ".join(c.ljust(w) for c, w in zip(columnas, anchos)),
              " ".join("-" * w for w in anchos)]
    lineas += [fmt(f) for f in filas]
    return "\n".join(lineas) + "\n\n"


def resumen(filas_hoy, contrato=FILAS):
    cab = "orden tabla filas_hoy filas_contrato"
    guiones = "----- ----- --------- --------------"
    cuerpo = "".join(f"{i} {t} {filas_hoy[t]} {contrato[t]}\n" for i, t in enumerate(ORDEN, 1))
    return cab + "\n" + guiones + "\n" + cuerpo + "\n"


TA = bloque(["id", "nombre", "monto"],
            [["1", "Pizza", "  10.50"], ["2", "NULL", "   3.00"],
             ["3", "", "NULL"], ["4", "Ñandú", "   0.00"]],
            [4, 8, 8])
TB = bloque(["solo"], [["a"], ["NULL"]], [6])
TC = bloque(["k", "v"], [["x", "corta"]], [3, 10])
VOLCADO = resumen(FILAS) + TA + TB + TC + "Hora de finalización: 2026-10-29T02:19:12.9897697-05:00\n"


@pytest.fixture(autouse=True)
def contrato(monkeypatch):
    monkeypatch.setattr(pv, "ORDEN", ORDEN)
    monkeypatch.setattr(pv, "COLUMNAS", COLUMNAS)
    monkeypatch.setattr(pv, "FILAS_CONTRATO", FILAS)


def escribir(tmp_path, texto):
    p = tmp_path / "volcado.txt"
    p.write_bytes(texto.encode("utf-8"))
    return p


def test_archivo_sintetico_versionado_coincide():
    assert (DATOS / "volcado_minimo.txt").read_text(encoding="utf-8") == VOLCADO


def test_encabezado_y_guiones_definen_columnas(tmp_path):
    d = pv.leer_volcado(escribir(tmp_path, VOLCADO))
    assert list(d) == ORDEN
    assert d["ta"].columns == COLUMNAS["ta"]
    assert all(t == pl.String for t in d["ta"].dtypes)
    assert [d[t].height for t in ORDEN] == [4, 2, 1]


def test_null_es_nulo_y_blanco_es_cadena_vacia(tmp_path):
    ta = pv.leer_volcado(escribir(tmp_path, VOLCADO))["ta"]
    assert ta["nombre"].to_list() == ["Pizza", None, "", "Ñandú"]
    assert ta["monto"].to_list()[2] is None


def test_espacios_iniciales_se_conservan_y_solo_se_quita_relleno_derecho(tmp_path):
    ta = pv.leer_volcado(escribir(tmp_path, VOLCADO))["ta"]
    assert ta["monto"].to_list() == ["  10.50", "   3.00", None, "   0.00"]


def test_una_sola_columna(tmp_path):
    tb = pv.leer_volcado(escribir(tmp_path, VOLCADO))["tb"]
    assert tb.columns == ["solo"]
    assert tb["solo"].to_list() == ["a", None]


def test_fila_corta_ultima_columna_sin_relleno(tmp_path):
    tc = pv.leer_volcado(escribir(tmp_path, VOLCADO))["tc"]
    assert tc.row(0) == ("x", "corta")


def test_fila_corta_que_no_llega_a_la_ultima_columna_se_rellena_como_vacio(tmp_path):
    # Fila "x" sin ultima columna: se lee como cadena vacia, no como error.
    texto = VOLCADO.replace("x   corta", "x")
    tc = pv.leer_volcado(escribir(tmp_path, texto))["tc"]
    assert tc.row(0) == ("x", "")


def test_conteo_distinto_de_filas_hoy_falla(tmp_path):
    malo = resumen({"ta": 5, "tb": 2, "tc": 1}) + TA + TB + TC
    with pytest.raises(pv.VolcadoError, match="filas_hoy"):
        pv.leer_volcado(escribir(tmp_path, malo))


def test_conteo_distinto_en_filas_contrato_falla(tmp_path):
    malo = resumen(FILAS, {"ta": 9, "tb": 2, "tc": 1}) + TA + TB + TC
    with pytest.raises(pv.VolcadoError, match="filas_contrato"):
        pv.leer_volcado(escribir(tmp_path, malo))


def test_salto_de_linea_incrustado_falla(tmp_path):
    # "Pizza\nmedia" parte la fila 1 en dos lineas: la segunda ya no encaja en ancho/conteo.
    malo = VOLCADO.replace("1    Pizza", "1    Pizza\nmedia", 1)
    with pytest.raises(pv.VolcadoError):
        pv.leer_volcado(escribir(tmp_path, malo))


def test_salto_de_linea_incrustado_que_forma_linea_en_blanco_falla(tmp_path):
    malo = VOLCADO.replace("1    Pizza", "1    Pizza\n\n", 1)  # corta el bloque antes de tiempo
    with pytest.raises(pv.VolcadoError):
        pv.leer_volcado(escribir(tmp_path, malo))


def test_columnas_distintas_al_contrato_fallan(tmp_path):
    malo = VOLCADO.replace("nombre", "nomber", 1)
    with pytest.raises(pv.VolcadoError, match="columnas"):
        pv.leer_volcado(escribir(tmp_path, malo))


def test_main_escribe_parquet_y_manifiesto_con_filas_hoy(tmp_path):
    import json
    src, out = escribir(tmp_path, VOLCADO), tmp_path / "salida"
    assert pv.main(["--volcado", str(src), "--salida", str(out)]) == 0
    man = json.loads((out / "_manifiesto.json").read_text(encoding="utf-8"))
    assert {t["tabla"]: (t["filas"], t["filas_hoy"]) for t in man["tablas"]} == {
        "ta": (4, 4), "tb": (2, 2), "tc": (1, 1)}
    assert pl.read_parquet(out / "ta.parquet").height == 4
    assert pv.main(["--volcado", str(src), "--salida", str(out)]) == 2  # append-only: no pisa
