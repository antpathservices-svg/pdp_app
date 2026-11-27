# Pipelines POS

Implementación inicial del pipeline RAW para las 14 tablas POS de Soft Restaurant 10.

## Instalación

Desde la raíz del repositorio:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r pipelines/requirements.txt
```

Copia `.env.example` a `.env` y completa `POS_SQL_URI`. El archivo `.env` está ignorado por Git.

## Ejecución

Vista previa sin conectar al POS:

```powershell
.venv\Scripts\python -m pipelines.pos_etl --from 2026-10-29T00:00:00 --to 2026-10-30T00:00:00 --dry-run
```

Ejecutar todos los productos POS:

```powershell
.venv\Scripts\python -m pipelines.pos_etl --from 2026-10-29T00:00:00 --to 2026-10-30T00:00:00
```

Ejecutar con autenticación integrada contra una instancia local de Windows:

```powershell
py -3 -m pipelines.pos_etl --sql-uri 'integrated:localhost\NATIONALSOFT' --from 2026-11-21T00:00:00 --to 2026-11-22T00:00:00
```

Ejecutar una familia:

```powershell
.venv\Scripts\python -m pipelines.pos_etl --product raw_pos_venta_* --from 2026-10-29T00:00:00 --to 2026-10-30T00:00:00
```

## Comportamiento

- Lee `sharepoint/productos.json` como contrato POS.
- Genera una consulta por producto y aplica el rango `[desde, hasta)` solo a productos con columna incremental.
- Valida que las columnas recibidas coincidan exactamente con el contrato.
- Escribe RAW en `data/lake/raw/pos/<producto>/idempresa=<x>/fecha=<fecha>/`.
- Usa un archivo por rango de fechas y reemplaza ese archivo de forma determinista en una reejecución.
- Registra conteo de filas, duración y estado por producto.
- No usa `READ UNCOMMITTED`, DML ni DDL.

## Pruebas

```powershell
.venv\Scripts\python -m pytest pipelines/tests -q
```
