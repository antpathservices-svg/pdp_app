"""Pruebas del reconciliador sobre una exportacion sintetica (sin tocar SharePoint)."""

from __future__ import annotations

import json

import pytest

from pipelines.carga_inicial import reconciliar_sharepoint as rs

LISTA = "raw_pos_venta_partida"  # pk: foliodet, movimiento


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    carga = tmp_path / "carga"
    carga.mkdir()
    jl = [
        {"_ord": 1, "v": {"foliodet": 10, "movimiento": 1, "idproducto": "02016", "precio": "209.0000",
                          "pagado": True, "hora": "2026-08-15T22:34:50.000Z"}},
        {"_ord": 2, "v": {"foliodet": 10, "movimiento": 2, "idproducto": "02017", "precio": "0.0803",
                          "pagado": False, "hora": "2026-08-15T22:35:50.000Z"}},
    ]
    (carga / f"{LISTA}.jsonl").write_text("\n".join(json.dumps(r) for r in jl) + "\n", encoding="utf-8")
    monkeypatch.setattr(rs, "CARGA", carga)
    exp = tmp_path / "exp"
    exp.mkdir()
    sp = [
        {"_id": 1, "foliodet": 10.0, "movimiento": 1.0, "idproducto": "02016", "precio": 209.0,
         "pagado": True, "hora": "2026-08-15T22:34:50Z", "descuento": None},
        {"_id": 2, "foliodet": 10.0, "movimiento": 2.0, "idproducto": "02017", "precio": 0.0803,
         "pagado": False, "hora": "2026-08-15T22:35:50Z", "descuento": None},
    ]
    return exp, sp


def correr(exp, sp, conteos=None):
    (exp / f"{LISTA}.json").write_text(json.dumps(sp), encoding="utf-8")
    return rs.reconciliar(LISTA, exp, ["foliodet", "movimiento"], 200, conteos or {})


def test_coincidencia_exacta(entorno):
    assert correr(*entorno, {LISTA: 2})["problemas"] == []


def test_duplicado_por_reintento_de_lote(entorno):
    exp, sp = entorno
    r = correr(exp, sp + [dict(sp[1], _id=3)])
    assert any("repetidas" in p for p in r["problemas"]) and any("filas 3 != jsonl 2" in p for p in r["problemas"])


def test_fila_faltante_y_sobrante(entorno):
    exp, sp = entorno
    sp[1]["movimiento"] = 9.0
    r = correr(exp, sp)
    assert any("faltantes" in p for p in r["problemas"]) and any("de mas" in p for p in r["problemas"])


def test_item_count_distinto(entorno):
    assert any("ItemCount" in p for p in correr(*entorno, {LISTA: 3})["problemas"])


def test_valor_redondeado_texto_sin_cero_y_fecha_distinta(entorno):
    exp, sp = entorno
    sp[0]["precio"] = 209.01
    sp[0]["idproducto"] = "2016"          # perdio el cero a la izquierda
    sp[1]["hora"] = "2026-08-15T17:35:50Z"  # sin convertir a UTC
    p = " ".join(correr(exp, sp)["problemas"])
    assert "3 diferencias" in p


def test_atributo_omitido_debe_quedar_vacio(entorno):
    exp, sp = entorno
    sp[0]["descuento"] = 0.0  # el origen era NULL (omitido) y quedo 0
    assert any("diferencias" in p for p in correr(exp, sp)["problemas"])


def test_booleano_omitido_en_origen_llega_false_no_es_diferencia(entorno):
    # D8: Si/No vacio en el origen == False en SharePoint
    exp, sp = entorno
    sp[0]["cancelado"] = False
    assert correr(exp, sp)["problemas"] == []


def test_booleano_omitido_en_origen_llega_true_si_es_diferencia(entorno):
    exp, sp = entorno
    sp[0]["cancelado"] = True
    assert any("diferencias" in p for p in correr(exp, sp)["problemas"])


def test_exportador_lee_site_url_de_la_configuracion(tmp_path, monkeypatch):
    from pipelines.carga_inicial import exportar_sharepoint as ex
    assert not hasattr(ex, "SITE")
    env = tmp_path / ".env"
    env.write_text("SITE_URL=https://ejemplo.sharepoint.com/sites/X\n", encoding="utf-8")
    monkeypatch.delenv("SITE_URL", raising=False)
    assert ex.cfg.cargar(env).site_url == "https://ejemplo.sharepoint.com/sites/X"
