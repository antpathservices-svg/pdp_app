"""Exporta las 25 listas de SharePoint en SOLO LECTURA (solo GET) para reconciliar_sharepoint.py.

Usa la sesion de la CLI de Microsoft 365 (`m365 login` previo) para obtener un token; el token
no se imprime ni se guarda. Escribe <salida>/<lista>.json (arreglo de objetos con claves = atributo
de productos.json, ya adaptadas a los nombres internos del sitio: _raw, _x0063_...) y
<salida>/_conteos.json con ItemCount por lista.

Uso: python -m pipelines.carga_inicial.exportar_sharepoint [--salida data/reconciliacion] [--listas a b]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

import requests

from . import config as cfg

RAIZ = Path(__file__).resolve().parents[2]
RESERVADOS = {"id", "title", "version", "order", "created", "modified", "author", "editor",
              "contenttype", "attachments", "edit", "linktitle", "docicon", "path"}
PAGINA = 5000


def token(site: str) -> str:
    exe = shutil.which("m365")
    if not exe:
        raise SystemExit("No se encontro m365 en PATH.")
    r = subprocess.run([exe, "util", "accesstoken", "get", "--resource", "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(site))],
                       capture_output=True, text=True)
    t = r.stdout.strip().strip('"')
    if r.returncode or not t:
        raise SystemExit("No se pudo obtener el token (m365 login).")
    return t


def get(s: requests.Session, url: str) -> dict:
    for intento in range(4):
        r = s.get(url, timeout=120)
        if r.status_code in (429, 503):
            import time
            time.sleep(int(r.headers.get("Retry-After", 5 * (intento + 1))))
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()
    return {}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", type=Path, default=RAIZ / "data" / "reconciliacion")
    ap.add_argument("--listas", nargs="*")
    ap.add_argument("--env", type=Path)
    a = ap.parse_args(argv)
    site = cfg.cargar(a.env).site_url.rstrip("/")
    if not site:
        raise SystemExit("SITE_URL no esta configurado (.env o variable de entorno).")
    prod = {p["id"]: p for p in json.loads((RAIZ / "sharepoint" / "productos.json").read_text(encoding="utf-8"))["productos"]}
    orden = json.loads((Path(__file__).with_name("mapeo_listas.json")).read_text(encoding="utf-8"))["orden_carga"]
    a.salida.mkdir(parents=True, exist_ok=True)
    conteos, rc = {}, 0
    for lista in [l for l in orden if not a.listas or l in a.listas]:
        s = requests.Session()
        s.headers.update({"Authorization": f"Bearer {token(site)}", "Accept": "application/json;odata=nometadata"})
        base = f"{site}/_api/web/lists/getbytitle('{urllib.parse.quote(lista)}')"
        conteos[lista] = get(s, base + "?$select=ItemCount")["ItemCount"]
        campos = get(s, base + "/fields?$filter=Hidden eq false&$select=InternalName,StaticName,Title,TypeAsString,ReadOnlyField")["value"]
        attrs = [x[0] for e in prod[lista]["ent"] for x in e["a"]]
        res: dict[str, str] = {}
        for at in attrs:
            esp = f"{at}_raw" if at.lower() in RESERVADOS else at
            f = next((c for c in campos if c["StaticName"] == esp), None) \
                or next((c for c in campos if c["InternalName"] == esp), None) \
                or next((c for c in campos if c["Title"] == at and not c["ReadOnlyField"]
                         and c["InternalName"].lower() not in RESERVADOS), None)
            if f:
                res[at] = f["InternalName"]
        sin = [at for at in attrs if at not in res]
        sel = ",".join(["ID"] + sorted(set(res.values())))
        url = f"{base}/items?$select={sel}&$orderby=ID&$top={PAGINA}"
        filas, paginas = [], 0
        while url:
            d = get(s, url)
            paginas += 1
            for it in d["value"]:
                fila = {"_id": it["ID"]}
                for at, interno in res.items():
                    fila[at] = it.get(interno)
                filas.append(fila)
            url = d.get("odata.nextLink") or d.get("@odata.nextLink")
        tmp = a.salida / f"{lista}.json.tmp"
        tmp.write_text(json.dumps(filas, ensure_ascii=False), encoding="utf-8")
        tmp.replace(a.salida / f"{lista}.json")
        print(f"{lista:44} ItemCount={conteos[lista]:>7} exportadas={len(filas):>7} paginas={paginas} sin_campo={sin}")
        if sin:
            rc = 1
    cf = a.salida / "_conteos.json"
    previo = json.loads(cf.read_text(encoding="utf-8")) if cf.is_file() else {}
    previo.update(conteos)
    cf.write_text(json.dumps(previo, indent=1), encoding="utf-8")
    return rc


if __name__ == "__main__":
    sys.exit(main())
