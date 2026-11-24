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
- Estado `incierto` (cualquier otro error de lote; puede haber filas aplicadas) o `error`: la lista se bloquea. Si `ItemCount` = 0, reintentar con `-Ejecutar -Reiniciar <lista>` (solo procede con `ItemCount` = 0 y deja el intento previo en `estado.json > reinicios`). Si no, comparar `ItemCount` con `filas_cargadas`; si hay filas de más, borrar las del último lote (columna `renglon_carga` o `Created`) o vaciar la lista y quitar su entrada de `estado.json`, y reanudar. `ItemCount` puede tardar unos minutos en reflejar cambios.
- Existe `data/carga/.carga.lock` mientras corre; si una corrida murió, borrarlo.
- **Timeout** («HttpClient.Timeout of 100 seconds», cancelaciones, errores de red): el script espera, lee `ItemCount` (dos lecturas iguales seguidas) y decide solo. Si `ItemCount` = filas antes del lote, lo reintenta (hasta 3 veces, con retroceso y mitad de lote desde el 2.o intento); si = antes + lote, lo da por aplicado; cualquier otro valor deja la lista en `incierto`. Cada caso queda en `estado.json > lotes[].eventos`. `ItemCount` es eventualmente consistente: si hay duda, no reanude sin conciliar. PnP.PowerShell 3.5 no tiene `-RequestTimeout`; el script sube `Context.RequestTimeout` a `-TimeoutSegundos` (300 s) pero el lote usa el `HttpClient` de PnP.Core (100 s fijos), por eso conviene bajar `TAMANO_LOTE` si hay timeouts frecuentes.
- **Retomar una lista `incierto` tras comprobar que el lote no se aplicó:** `-Ejecutar -Confirmar <lista>` solo procede si `ItemCount` = `filas_cargadas`; la regresa a `en_curso`, registra el evento en `estado.json > confirmaciones` y se reanuda desde `filas_cargadas + 1` con el mismo comando de la masiva. Si `ItemCount` es distinto, aborta sin tocar nada: hay que conciliar llaves.
- Una lista con filas y sin entrada en `estado.json` se salta (guarda previa): no se duplica.
- `-Forzar` solo levanta `corrida_cerrada`; no salta la guarda ni recarga listas completas. Para recargar: vaciar la lista y quitar su entrada de `estado.json`.

### 6. Verificación

1. `ItemCount` de cada lista = `filas_jsonl` del resumen (guardado en `estado.json` como `item_count_final`).
2. Dry-run con `-Conectar` posterior: todas `ya cubierta`.
3. Muestreo contra el Parquet: primer y último registro de cada lista, `renglon_carga` consecutivo, una fecha en horario de verano y una en invierno, un decimal con 4 decimales.
4. Totales de negocio: suma de `total` en `raw_pos_venta_cuenta` y número de folios contra el POS.
5. Actualizar `sharepoint/README.md` (Despliegues) y la bitácora de abajo.

## Bitácora de corridas

| Fecha (UTC) | Quién | Modo | Alcance | Filas | Duración | 429 | Resultado / notas |
|---|---|---|---|---|---|---|---|
| 2026-11-23 ~21:45 | Claude (líder) | `-DryRun -Conectar` | 25 listas | 105,685 | ~1 min | — | 0 problemas; todas las listas destino vacías. |
| 2026-11-23 22:08 | Claude (líder) | `-Ejecutar -Piloto` | `raw_pos_venta_area` | 0 | 27 s | 0 | Falló el 1.er lote: «No se puede convertir un valor primitivo en el tipo esperado 'Edm.String'» (enteros Int64 en lotes PnP). Estado `incierto`, `ItemCount` 0. Corregido: valores como primitivos según el tipo de `productos.json`. |
| 2026-11-23 22:17:30 | Claude (líder) | `-Ejecutar -Reiniciar raw_pos_venta_area -Piloto` | `raw_pos_venta_area` | 3 | 1.3 s | 0 | OK. Leído de vuelta: `idarearestaurant` "01" (texto), `idtiposervicio` 1. |
| 2026-11-23 ~22:18 | Claude (líder) | `-Ejecutar -Piloto` | 200 de `raw_pos_venta_cuenta` | 200 | 22.5 s | 0 | OK. Fechas (09:21:27 Matamoros → 14:21:27Z), booleanos e importes revisados. ~0.06 s/fila. |
| 2026-11-23 22:17–23:2x | Claude (líder) | `-Ejecutar` (masiva 1) | 25 listas | 22 listas completas + 19,400 de `raw_pos_venta_partida` | ~70 min | 0 | Se detuvo en `raw_pos_venta_partida`, lote 19401–19500: «HttpClient.Timeout of 100 seconds». `ItemCount` 19,400 = `filas_cargadas`: el lote no se aplicó. |
| 2026-11-23 23:32:30 | Claude (líder) | `-Ejecutar -Confirmar raw_pos_venta_partida` (masiva 2) | 3 listas restantes | resto hasta 105,685 | 65.2 min | 0 | Confirmada la lista y reanudada desde 19,401. Corrida cerrada 2026-11-24 00:33:32. |

**Resultado de la carga (2026-11-24):**

- Corte de los datos: 2026-10-28 (volcado `resultado contrato bronze.txt`, sha256 `f2c9053919355fd7a8b2a76f4d57347dde2221584478a3ff76ec86e9a75f476a`). Sitio: DEPRITAM, Marketplace v1.6.
- Parámetros: `TAMANO_LOTE` 100, `PAUSA_ENTRE_LOTES` 1 s. Velocidad real ~0.06 s/fila en las listas grandes (el supuesto del dry-run era 0.15 s/fila).
- 25 listas completas, 105,685 filas; 0 respuestas 429/503; 1 reinicio (`raw_pos_venta_area`), 1 confirmación (`raw_pos_venta_partida`), 1 lote con timeout no aplicado.
- Puerta 3 (etl-pos-validador, exportación de solo lectura del 2026-11-24 en `data/reconciliacion/`): en las 25 listas `ItemCount` = filas del jsonl = `filas_hoy`; llaves únicas sin faltantes ni sobrantes; comparación de valores sobre **todas** las filas con 0 diferencias; la zona 19,300–19,600 de `raw_pos_venta_partida` sin duplicados ni huecos. 178 pruebas de `pipelines/tests` pasan. Aprobado por supervisor-evaluador.
- Pendiente: totales de negocio contra el POS (verificación, paso 4); requiere acceso al POS.
- `-Confirmar` y el reintento automático por timeout se agregaron durante la corrida, después del commit `a2c1196`. El lote 19401–19500 se resolvió con `-Confirmar`, no con el reintento automático.

**Evidencias (locales, no versionadas):** `data/carga/estado.json`, `data/carga/logs/` (`dryrun-conectar.log`, `piloto*.log`, `carga-masiva.log`, `carga-masiva-2.log`, `deploy-v16.log`) y `data/reconciliacion/`.
