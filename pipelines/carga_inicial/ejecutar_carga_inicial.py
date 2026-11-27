"""Orquesta la carga inicial (D7/D8): [parser] -> transformar -> cargar_sharepoint.ps1.

Por defecto SOLO hace prueba en seco: nunca escribe en SharePoint sin --ejecutar.

    python -m pipelines.carga_inicial.ejecutar_carga_inicial                 # transformar + dry-run
    python -m pipelines.carga_inicial.ejecutar_carga_inicial --conectar      # dry-run validando contra el sitio
    python -m pipelines.carga_inicial.ejecutar_carga_inicial --ejecutar --piloto
    python -m pipelines.carga_inicial.ejecutar_carga_inicial --ejecutar
    python -m pipelines.carga_inicial.ejecutar_carga_inicial --ejecutar --saltar-transformar   # reanudar
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from . import config as cfg
    from . import parser_volcado, transformar
except ImportError:  # pragma: no cover
    import config as cfg  # type: ignore
    import parser_volcado  # type: ignore
    import transformar  # type: ignore


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ejecutar", action="store_true", help="carga de verdad (sin esto: dry-run)")
    ap.add_argument("--conectar", action="store_true", help="en dry-run, validar contra el sitio (abre sesion)")
    ap.add_argument("--piloto", action="store_true")
    ap.add_argument("--listas", nargs="*", help="comodines de lista, p. ej. 'raw_inv_*'")
    ap.add_argument("--forzar", action="store_true", help="levanta la marca de corrida cerrada")
    ap.add_argument("--regenerar-parquet", action="store_true", help="corre parser_volcado antes (usa RUTA_VOLCADO)")
    ap.add_argument("--saltar-transformar", action="store_true", help="reusa los jsonl existentes")
    ap.add_argument("--env", type=Path)
    a = ap.parse_args(argv)
    c = cfg.cargar(a.env)

    if a.regenerar_parquet:
        rc = parser_volcado.main(["--volcado", str(c.ruta_volcado), "--salida", str(c.ruta_raw), "--forzar"])
        if rc:
            return rc
    if not a.saltar_transformar:
        targs = (["--env", str(a.env)] if a.env else [])
        rc = transformar.main(targs)
        if rc:
            print("transformar.py reporto errores de conversion: corrija antes de cargar.", file=sys.stderr)
            return rc

    pwsh = shutil.which("pwsh")
    if not pwsh:
        print("No se encontro pwsh (PowerShell 7.5+).", file=sys.stderr)
        return 2
    cmd = [pwsh, "-NoProfile", "-File", str(cfg.DIR_CARGA / "cargar_sharepoint.ps1")]
    cmd.append("-Ejecutar" if a.ejecutar else "-DryRun")
    if a.conectar and not a.ejecutar:
        cmd.append("-Conectar")
    if a.piloto:
        cmd.append("-Piloto")
    if a.forzar:
        cmd.append("-Forzar")
    if a.env:
        cmd += ["-EnvPath", str(a.env)]
    if a.listas:
        cmd += ["-Listas", ",".join(a.listas)]
    print("->", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
