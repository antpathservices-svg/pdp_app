# Carga inicial del volcado del POS a SharePoint (D7/D8)

Carga única de 25 listas (14 `raw_pos_*` y 11 `raw_inv_*`) desde `data/raw/pos_volcado_2026-10-28/*.parquet`. Corte: 2026-10-28. No se cargan `empresas` ni las tablas sin lista. No se usa Power Automate ni conectores premium: escribe PnP.PowerShell con tu sesión.

## Piezas

| Archivo | Qué hace |
|---|---|
| `pipelines/carga_inicial/mapeo_listas.json` | Lista ← tabla; atributo ← columna del Parquet; orden de carga; alcance del piloto. Los tipos salen de `sharepoint/productos.json`. |
| `pipelines/carga_inicial/transformar.py` | Parquet → `data/carga/<lista>.jsonl` (tipado, nulos omitidos, orden del archivo, ordinal `_ord`) y `_resumen_transformacion.json`. |
| `pipelines/carga_inicial/cargar_sharepoint.ps1` | jsonl → SharePoint por lotes; `-DryRun`, `-Ejecutar`, `-Piloto`, `-Listas`, `-Forzar`. Bitácora `data/carga/estado.json`. |
| `pipelines/carga_inicial/ejecutar_carga_inicial.py` | Encadena transformar y el cargador. Sin `--ejecutar` solo hace dry-run. |
| `pipelines/carga_inicial/config.py`, `.env.example` | Configuración (`SITE_URL`, `CLIENT_ID`, `TZ_POS`, `RUTA_VOLCADO`, `RUTA_RAW`, `RUTA_CARGA`, `TAMANO_LOTE`, `PAUSA_ENTRE_LOTES`). |

## Reglas de conversión (D8)

- Texto tal cual (`01001` sigue siendo texto). `NULL` y `""` se omiten: SharePoint no distingue nulo de vacío.
- Entero/decimal: sin relleno, punto decimal, sin redondeo (el decimal conserva sus dígitos).
- Booleano `0/1` → `false/true`.
- Fecha-hora: se interpreta en `America/Matamoros` (con horario de verano) y se envía en UTC ISO 8601. Una hora ambigua (cambio de otoño) toma la primera ocurrencia; una inexistente no se escribe y se reporta.
- Un valor que no se convierte no se escribe y queda en el reporte con ejemplos (`transformar.py` sale con código 1).
- `renglon_carga` (`raw_inv_movimiento`, `raw_inv_compra_partida`) = ordinal 1-based de la fila en su tabla; es la llave. Los nombres internos de columna (`_raw`, `_x0063_`) se leen del sitio con `Get-PnPField` al cargar; sin sesión se calculan igual que `Deploy-Listas.ps1`.

## Requisitos

1. `Deploy-Listas.ps1` ya corrió con `productos.json` v1.6 (columnas nuevas y llaves `renglon_carga`) y las 25 listas están **vacías**.
2. PowerShell 7.5+ (usa `ConvertFrom-Json -DateKind`) y PnP.PowerShell 3.x.
3. `.env` en la raíz copiado de `.env.example` (no va al repo). Sin secretos: el inicio de sesión es interactivo.
4. Permiso de escritura en el sitio DEPRITAM.

## Procedimiento

### 1. Transformar y revisar

```powershell
.venv\Scripts\python -m pipelines.carga_inicial.transformar
```

Revisar la tabla final: errores = 0. Ver `data/carga/_resumen_transformacion.json` (columnas sin dato, avisos).

### 2. Dry-run (no escribe)

```powershell
pwsh ./pipelines/carga_inicial/cargar_sharepoint.ps1 -DryRun               # contra productos.json
pwsh ./pipelines/carga_inicial/cargar_sharepoint.ps1 -DryRun -Conectar     # contra el sitio real (solo lee)
```

Con `-Conectar` valida que cada columna exista, su tipo y que la lista esté vacía (guarda previa). Debe terminar con 0 problemas. El tiempo estimado usa un supuesto de 0.15 s/fila; se calibra con el piloto.

### 3. Piloto

```powershell
pwsh ./pipelines/carga_inicial/cargar_sharepoint.ps1 -Ejecutar -Piloto
```

Carga `raw_pos_venta_area` y las primeras 200 filas de `raw_pos_venta_cuenta`. Verificar en SharePoint: conteos (3 y 200), un folio contra el POS (horas en UTC, 5 h o 6 h de diferencia según la fecha), números sin redondeo, Sí/No. Anotar los segundos por fila reales (`estado.json`) y ajustar `TAMANO_LOTE` y `PAUSA_ENTRE_LOTES`. El piloto es un prefijo de la carga: la masiva continúa en la fila 201.

### 4. Carga masiva

```powershell
pwsh ./pipelines/carga_inicial/cargar_sharepoint.ps1 -Ejecutar
```

Orden: catálogos pequeños, luego `compras`, `invfisico`, `cancela`, `comprasmovtos`, y al final `cheques`, `cheqdet`, `movsinv`, `invfisicomovtos`. Solo `-Listas` para un subconjunto (`-Listas 'raw_inv_*'`). Al terminar las 25 listas se marca `corrida_cerrada`.

### 5. Reanudación

Volver a correr el mismo comando. Cada lista continúa desde `filas_cargadas` (último ordinal confirmado) si `ItemCount` coincide con ese valor.

- 429/503: el script espera `Retry-After` (o retroceso exponencial) y reintenta; con 429 repetido parte el lote a la mitad. Se asume que un 429 no aplicó nada.
- Estado `incierto` (cualquier otro error de lote; puede haber filas aplicadas) o `error`: la lista se bloquea. Comparar `ItemCount` con `filas_cargadas`; si hay filas de más, borrar las del último lote (columna `renglon_carga` o `Created`) o vaciar la lista y quitar su entrada de `estado.json`, y reanudar. `ItemCount` puede tardar unos minutos en reflejar cambios.
- Existe `data/carga/.carga.lock` mientras corre; si una corrida murió, borrarlo.
- Una lista con filas y sin entrada en `estado.json` se salta (guarda previa): no se duplica.
- `-Forzar` solo levanta `corrida_cerrada`; no salta la guarda ni recarga listas completas. Para recargar: vaciar la lista y quitar su entrada de `estado.json`.

### 6. Verificación

1. `ItemCount` de cada lista = `filas_jsonl` del resumen (guardado en `estado.json` como `item_count_final`).
2. Dry-run con `-Conectar` posterior: todas `ya cubierta`.
3. Muestreo contra el Parquet: primer y último registro de cada lista, `renglon_carga` consecutivo, una fecha en horario de verano y una en invierno, un decimal con 4 decimales.
4. Totales de negocio: suma de `total` en `raw_pos_venta_cuenta` y número de folios contra el POS.
5. Actualizar `sharepoint/README.md` (Despliegues) y la bitácora de abajo.

## Bitácora de corridas

| Fecha | Quién | Modo | Alcance | Filas | Duración | 429 | Resultado / notas |
|---|---|---|---|---|---|---|---|
| | | | | | | | |
